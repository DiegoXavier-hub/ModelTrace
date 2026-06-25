from __future__ import annotations

import copy
import json
import threading
from pathlib import Path
from typing import Any

APP_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = APP_ROOT.parent
DEFAULT_DATA_PATH = APP_ROOT / "data" / "modeltrace_desktop.json"
BACKEND_SOURCE_PATH = PROJECT_ROOT / "backend" / ".data" / "modeltrace.json"


def get_nested(document: dict[str, Any], path: str, default: Any = None) -> Any:
    """Lê um campo aninhado por caminho com ponto, ex: 'prediction.score'."""
    current: Any = document
    for part in path.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return default
    return current


def set_nested(document: dict[str, Any], path: str, value: Any) -> None:
    """Grava um campo aninhado por caminho com ponto, criando dicts no caminho."""
    parts = path.split(".")
    current = document
    for part in parts[:-1]:
        existing = current.get(part)
        if not isinstance(existing, dict):
            existing = {}
            current[part] = existing
        current = existing
    current[parts[-1]] = value


def _matches(document: dict[str, Any], filter_: dict[str, Any] | None) -> bool:
    """Mesma lógica de match do JsonDocumentStore (igualdade + operadores)."""
    if not filter_:
        return True
    for key, expected in filter_.items():
        actual = get_nested(document, key)
        if isinstance(expected, dict):
            for op, value in expected.items():
                if op == "$gte" and not (actual is not None and actual >= value):
                    return False
                if op == "$lte" and not (actual is not None and actual <= value):
                    return False
                if op == "$gt" and not (actual is not None and actual > value):
                    return False
                if op == "$lt" and not (actual is not None and actual < value):
                    return False
                if op == "$ne" and actual == value:
                    return False
                if op == "$in" and actual not in value:
                    return False
                if op == "$exists" and ((actual is not None) != bool(value)):
                    return False
        elif actual != expected:
            return False
    return True


class SyncDocumentStore:
    """Store documental síncrono sobre um arquivo JSON único."""

    def __init__(self, path: str | Path, collections: list[str]) -> None:
        self.path = Path(path)
        self.collections = list(collections)
        self._lock = threading.Lock()
        self._data: dict[str, list[dict[str, Any]]] = {name: [] for name in self.collections}
        self._load()

    # ---- persistência -------------------------------------------------
    def _load(self) -> None:
        if self.path.exists():
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            self._data = {name: list(raw.get(name, [])) for name in self.collections}
        else:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self._save()

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(self._data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def _bucket(self, collection: str) -> list[dict[str, Any]]:
        if collection not in self._data:
            self._data[collection] = []
        return self._data[collection]

    # ---- leitura ------------------------------------------------------
    def all(self, collection: str) -> list[dict[str, Any]]:
        return copy.deepcopy(self._bucket(collection))

    def ids(self, collection: str) -> list[str]:
        return [str(doc.get("_id")) for doc in self._bucket(collection) if doc.get("_id") is not None]

    def count(self, collection: str, filter_: dict[str, Any] | None = None) -> int:
        return sum(1 for doc in self._bucket(collection) if _matches(doc, filter_))

    def collection_counts(self) -> dict[str, int]:
        return {name: len(self._bucket(name)) for name in self.collections}

    def find_one(self, collection: str, filter_: dict[str, Any]) -> dict[str, Any] | None:
        for document in self._bucket(collection):
            if _matches(document, filter_):
                return copy.deepcopy(document)
        return None

    def find_many(
        self,
        collection: str,
        filter_: dict[str, Any] | None = None,
        sort: list[tuple[str, int]] | None = None,
        limit: int = 100,
        skip: int = 0,
    ) -> list[dict[str, Any]]:
        results = [doc for doc in self._bucket(collection) if _matches(doc, filter_)]
        if sort:
            for field, direction in reversed(sort):
                results.sort(
                    key=lambda item: (get_nested(item, field) is None, get_nested(item, field)),
                    reverse=direction < 0,
                )
        if skip:
            results = results[skip:]
        if limit:
            results = results[:limit]
        return copy.deepcopy(results)

    # ---- escrita ------------------------------------------------------
    def insert_one(self, collection: str, document: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            doc = copy.deepcopy(document)
            self._bucket(collection).append(doc)
            self._save()
            return copy.deepcopy(doc)

    def update_one(
        self, collection: str, filter_: dict[str, Any], update: dict[str, Any]
    ) -> bool:
        with self._lock:
            for document in self._bucket(collection):
                if not _matches(document, filter_):
                    continue
                if "$set" in update or "$inc" in update:
                    for path, value in update.get("$set", {}).items():
                        set_nested(document, path, value)
                    for path, value in update.get("$inc", {}).items():
                        current = get_nested(document, path, 0) or 0
                        set_nested(document, path, current + value)
                else:
                    document.clear()
                    document.update(copy.deepcopy(update))
                self._save()
                return True
        return False

    def replace_one(
        self, collection: str, filter_: dict[str, Any], document: dict[str, Any]
    ) -> bool:
        with self._lock:
            bucket = self._bucket(collection)
            for index, existing in enumerate(bucket):
                if _matches(existing, filter_):
                    bucket[index] = copy.deepcopy(document)
                    self._save()
                    return True
        return False

    def delete_one(self, collection: str, filter_: dict[str, Any]) -> bool:
        with self._lock:
            bucket = self._bucket(collection)
            for index, document in enumerate(bucket):
                if _matches(document, filter_):
                    del bucket[index]
                    self._save()
                    return True
        return False

    def delete_many(self, collection: str, filter_: dict[str, Any]) -> int:
        with self._lock:
            bucket = self._bucket(collection)
            before = len(bucket)
            kept = [doc for doc in bucket if not _matches(doc, filter_)]
            self._data[collection] = kept
            deleted = before - len(kept)
            if deleted:
                self._save()
            return deleted

    def exists(self, collection: str, doc_id: str) -> bool:
        return self.find_one(collection, {"_id": doc_id}) is not None
