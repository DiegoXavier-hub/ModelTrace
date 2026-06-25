from __future__ import annotations

import secrets
from datetime import datetime, timezone

ID_PREFIXES: dict[str, str] = {
    "organizations": "org",
    "users": "user",
    "projects": "proj",
    "models": "model",
    "model_versions": "version",
    "predictions": "pred",
    "metrics_snapshots": "metric",
    "alerts": "alert",
    "api_keys": "key",
    "audit_events": "audit",
}


def new_id(collection: str) -> str:
    """Gera um _id novo no padrão da coleção (fallback 'doc' se desconhecida)."""
    prefix = ID_PREFIXES.get(collection, "doc")
    return f"{prefix}_{secrets.token_hex(6)}"


def now_iso() -> str:
    """Timestamp UTC no formato usado pelo projeto: 2026-05-20T00:44:20Z."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
