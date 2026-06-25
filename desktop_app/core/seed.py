from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from core.collections import COLLECTION_NAMES
from core.store import BACKEND_SOURCE_PATH, DEFAULT_DATA_PATH

TRIM_COLLECTIONS = {"predictions": 150, "audit_events": 150}


def _load_backend(source: Path) -> dict[str, list[dict[str, Any]]]:
    if not source.exists():
        raise FileNotFoundError(
            f"Banco do backend não encontrado em {source}. "
            "Rode o seed do backend antes, ou use --empty."
        )
    return json.loads(source.read_text(encoding="utf-8"))


def _trim(docs: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    """Mantém os 'limit' docs mais recentes (por created_at quando existir)."""
    ordered = sorted(docs, key=lambda d: str(d.get("created_at", "")), reverse=True)
    return ordered[:limit]


def build_dataset(
    source: Path = BACKEND_SOURCE_PATH,
    limit_overrides: dict[str, int] | None = None,
) -> dict[str, list[dict[str, Any]]]:
    raw = _load_backend(source)
    trims = {**TRIM_COLLECTIONS, **(limit_overrides or {})}
    dataset: dict[str, list[dict[str, Any]]] = {}
    for name in COLLECTION_NAMES:
        docs = list(raw.get(name, []))
        if name in trims:
            docs = _trim(docs, trims[name])
        dataset[name] = docs
    return dataset


def seed(
    target: Path = DEFAULT_DATA_PATH,
    source: Path = BACKEND_SOURCE_PATH,
    force: bool = False,
    empty: bool = False,
    limit_overrides: dict[str, int] | None = None,
) -> dict[str, int]:
    """Popula o banco do app. Retorna a contagem por coleção."""
    target = Path(target)
    if target.exists() and not force:
        existing = json.loads(target.read_text(encoding="utf-8"))
        if any(existing.get(name) for name in COLLECTION_NAMES):
            return {name: len(existing.get(name, [])) for name in COLLECTION_NAMES}

    if empty:
        dataset = {name: [] for name in COLLECTION_NAMES}
    else:
        dataset = build_dataset(source=source, limit_overrides=limit_overrides)

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(dataset, ensure_ascii=False, indent=2), encoding="utf-8")
    return {name: len(dataset[name]) for name in COLLECTION_NAMES}


def main() -> None:
    parser = argparse.ArgumentParser(description="Popula o banco do ModelTrace Desktop.")
    parser.add_argument("--force", action="store_true", help="recria do zero")
    parser.add_argument("--empty", action="store_true", help="cria coleções vazias")
    parser.add_argument("--limit", type=int, default=None,
                        help="limite para predictions e audit_events")
    args = parser.parse_args()

    overrides = None
    if args.limit is not None:
        overrides = {"predictions": args.limit, "audit_events": args.limit}

    counts = seed(force=args.force, empty=args.empty, limit_overrides=overrides)
    total = sum(counts.values())
    print(f"Banco populado em: {DEFAULT_DATA_PATH}")
    for name, count in counts.items():
        print(f"  {name:20s} {count:5d}")
    print(f"  {'TOTAL':20s} {total:5d}")


if __name__ == "__main__":
    main()
