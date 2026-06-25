from __future__ import annotations

from typing import Any


def _field(
    name: str,
    label: str,
    type_: str = "str",
    *,
    options: list[Any] | None = None,
    default: Any = None,
    required: bool = False,
    help_: str | None = None,
) -> dict[str, Any]:
    return {
        "name": name,
        "label": label,
        "type": type_,
        "options": options,
        "default": default,
        "required": required,
        "help": help_,
    }


COLLECTIONS: dict[str, dict[str, Any]] = {
    "organizations": {
        "label": "Organizações",
        "icon": "🏢",
        "description": "Organizações (tenants) que agrupam usuários, projetos e modelos.",
        "key_fields": [
            _field("name", "Nome", "str", required=True),
            _field("slug", "Slug", "str", help_="identificador curto, ex: minha-org"),
            _field("plan", "Plano", "choice",
                   options=["free", "pro", "enterprise", "enterprise-simulation"],
                   default="pro"),
            _field("owner_id", "ID do dono", "str", help_="_id de um usuário"),
            _field("status", "Status", "choice", options=["active", "suspended"], default="active"),
        ],
        "display_columns": ["name", "slug", "plan", "status", "created_at"],
        "search_fields": ["name", "slug", "plan", "status", "owner_id"],
    },
    "users": {
        "label": "Usuários",
        "icon": "👤",
        "description": "Usuários que operam a plataforma dentro de uma organização.",
        "key_fields": [
            _field("name", "Nome", "str", required=True),
            _field("email", "E-mail", "str", required=True),
            _field("role", "Papel", "choice",
                   options=["owner", "admin", "analyst", "viewer"], default="analyst"),
            _field("org_id", "ID da organização", "str"),
            _field("department", "Departamento", "str"),
            _field("status", "Status", "choice", options=["active", "invited", "disabled"],
                   default="active"),
        ],
        "display_columns": ["name", "email", "role", "org_id", "status"],
        "search_fields": ["name", "email", "role", "org_id", "status"],
    },
    "projects": {
        "label": "Projetos",
        "icon": "📁",
        "description": "Projetos de ML que agrupam modelos, predições e alertas.",
        "key_fields": [
            _field("name", "Nome", "str", required=True),
            _field("slug", "Slug", "str"),
            _field("problem_type", "Tipo de problema", "choice",
                   options=["classification", "regression", "ranking"], default="classification"),
            _field("domain", "Domínio", "str", help_="ex: education, finance"),
            _field("org_id", "ID da organização", "str"),
            _field("owner_id", "ID do dono", "str"),
            _field("status", "Status", "choice", options=["active", "archived"], default="active"),
        ],
        "display_columns": ["name", "slug", "problem_type", "domain", "status"],
        "search_fields": ["name", "slug", "problem_type", "org_id", "status"],
    },
    "models": {
        "label": "Modelos",
        "icon": "🤖",
        "description": "Contratos de modelo: alvo, métricas e versão em produção.",
        "key_fields": [
            _field("name", "Nome", "str", required=True),
            _field("slug", "Slug", "str"),
            _field("problem_type", "Tipo de problema", "choice",
                   options=["classification", "regression", "ranking"], default="classification"),
            _field("target_name", "Alvo (target)", "str"),
            _field("primary_metric", "Métrica principal", "str", help_="ex: auc, f1, rmse"),
            _field("project_id", "ID do projeto", "str"),
            _field("org_id", "ID da organização", "str"),
            _field("status", "Status", "choice", options=["active", "deprecated"], default="active"),
        ],
        "display_columns": ["name", "slug", "problem_type", "primary_metric", "status"],
        "search_fields": ["name", "project_id", "problem_type", "status"],
    },
    "model_versions": {
        "label": "Versões de Modelo",
        "icon": "🧩",
        "description": "Versões treinadas de um modelo, com algoritmo e métricas offline.",
        "key_fields": [
            _field("version", "Versão", "str", required=True, help_="ex: v1, v2"),
            _field("algorithm", "Algoritmo", "str", help_="ex: lightgbm, xgboost"),
            _field("model_id", "ID do modelo", "str"),
            _field("project_id", "ID do projeto", "str"),
            _field("status", "Status", "choice",
                   options=["staging", "production", "deprecated"], default="staging"),
        ],
        "display_columns": ["version", "algorithm", "model_id", "status", "created_at"],
        "search_fields": ["model_id", "algorithm", "status", "version"],
    },
    "predictions": {
        "label": "Predições",
        "icon": "🎯",
        "description": "Documento transacional central: decisão, features, score e feedback.",
        "key_fields": [
            _field("model_id", "ID do modelo", "str", required=True),
            _field("project_id", "ID do projeto", "str"),
            _field("model_version", "Versão do modelo", "str", default="v1"),
            _field("entity", "Entidade (JSON)", "json", default={"id": ""},
                   help_="ex: {\"id\": \"aluno_123\"}"),
            _field("prediction", "Predição (JSON)", "json",
                   default={"label": "", "score": 0.0},
                   help_="ex: {\"label\": \"churn\", \"score\": 0.81}"),
        ],
        "display_columns": ["model_id", "model_version", "prediction.label",
                            "prediction.score", "created_at"],
        "search_fields": ["model_id", "project_id", "model_version", "prediction.label"],
    },
    "metrics_snapshots": {
        "label": "Métricas (Snapshots)",
        "icon": "📊",
        "description": "Materializações de métricas por período para leitura rápida.",
        "key_fields": [
            _field("model_id", "ID do modelo", "str", required=True),
            _field("project_id", "ID do projeto", "str"),
            _field("model_version", "Versão do modelo", "str", default="v1"),
            _field("period", "Período (JSON)", "json",
                   default={"granularity": "day", "start": "", "end": ""}),
            _field("performance", "Performance (JSON)", "json", default={}),
        ],
        "display_columns": ["model_id", "model_version", "period.granularity", "computed_at"],
        "search_fields": ["model_id", "project_id", "model_version"],
    },
    "alerts": {
        "label": "Alertas",
        "icon": "🚨",
        "description": "Alertas operacionais gerados por regras (drift, performance, etc.).",
        "key_fields": [
            _field("title", "Título", "str", required=True),
            _field("type", "Tipo", "str", help_="ex: drift, feedback_rate_low"),
            _field("severity", "Severidade", "choice",
                   options=["low", "medium", "high", "critical"], default="medium"),
            _field("status", "Status", "choice",
                   options=["open", "acknowledged", "resolved"], default="open"),
            _field("metric", "Métrica", "str"),
            _field("model_id", "ID do modelo", "str"),
            _field("project_id", "ID do projeto", "str"),
        ],
        "display_columns": ["title", "type", "severity", "status", "metric", "created_at"],
        "search_fields": ["severity", "status", "type", "model_id", "project_id"],
    },
    "api_keys": {
        "label": "API Keys",
        "icon": "🔑",
        "description": "Chaves de API por projeto. Só o hash é persistido (key_hash).",
        "key_fields": [
            _field("name", "Nome", "str", required=True),
            _field("prefix", "Prefixo", "str", help_="ex: mt_live_"),
            _field("project_id", "ID do projeto", "str"),
            _field("org_id", "ID da organização", "str"),
            _field("scopes", "Escopos (JSON)", "json", default=["read"]),
            _field("status", "Status", "choice", options=["active", "revoked"], default="active"),
        ],
        "display_columns": ["name", "prefix", "project_id", "status", "created_at"],
        "search_fields": ["name", "project_id", "status"],
    },
    "audit_events": {
        "label": "Auditoria",
        "icon": "📜",
        "description": "Trilha de auditoria: quem fez o quê, em qual recurso, quando.",
        "key_fields": [
            _field("event_type", "Tipo de evento", "str", required=True,
                   help_="ex: model.created, alert.resolved"),
            _field("actor", "Ator (JSON)", "json",
                   default={"type": "user", "id": ""}),
            _field("resource", "Recurso (JSON)", "json",
                   default={"type": "", "id": ""}),
            _field("project_id", "ID do projeto", "str"),
            _field("org_id", "ID da organização", "str"),
        ],
        "display_columns": ["event_type", "actor.type", "actor.id", "project_id", "created_at"],
        "search_fields": ["event_type", "project_id", "org_id"],
    },
}

COLLECTION_NAMES: list[str] = list(COLLECTIONS.keys())


def get_meta(collection: str) -> dict[str, Any]:
    meta = COLLECTIONS[collection]
    return {"name": collection, **meta}
