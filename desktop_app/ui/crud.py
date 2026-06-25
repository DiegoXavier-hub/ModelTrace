from __future__ import annotations

import json
from typing import Any

import pandas as pd
import streamlit as st

from core.collections import COLLECTION_NAMES, get_meta
from core.ids import new_id, now_iso
from core.store import DEFAULT_DATA_PATH, SyncDocumentStore, get_nested
from ui.theme import hero_header, kpi_cards, record_cards


# ----------------------------------------------------------------------
# Acesso ao store
# ----------------------------------------------------------------------
def get_store() -> SyncDocumentStore:
    """Store novo a cada execução do script -> sempre reflete o disco."""
    return SyncDocumentStore(DEFAULT_DATA_PATH, COLLECTION_NAMES)


# ----------------------------------------------------------------------
# Helpers de exibição e conversão
# ----------------------------------------------------------------------
def _stringify(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        text = json.dumps(value, ensure_ascii=False)
        return text if len(text) <= 80 else text[:77] + "..."
    return value


def to_dataframe(docs: list[dict[str, Any]], columns: list[str]) -> pd.DataFrame:
    cols = ["_id", *columns]
    rows = [{col: _stringify(get_nested(doc, col)) for col in cols} for doc in docs]
    return pd.DataFrame(rows, columns=cols)


def _parse_scalar(text: str) -> Any:
    """Converte texto de busca em int/float/bool quando possível, senão string."""
    raw = text.strip()
    low = raw.lower()
    if low in {"true", "false"}:
        return low == "true"
    for caster in (int, float):
        try:
            return caster(raw)
        except (ValueError, TypeError):
            continue
    return raw


def _parse_value(text: str) -> Any:
    """Para UPDATE: tenta JSON (objetos/arrays/números), senão escalar/string."""
    raw = text.strip()
    if raw == "":
        return ""
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return _parse_scalar(raw)


def _show_results(docs: list[dict[str, Any]], meta: dict[str, Any], key: str) -> None:
    kpi_cards([{"label": "Resultados encontrados", "value": len(docs), "tone": "info"}])
    if not docs:
        st.info("Nenhum documento corresponde à busca.")
        return
    view = st.radio(
        "Visualização",
        ["🗂️ Cartões", "📋 Tabela"],
        horizontal=True,
        key=f"{key}_view",
        label_visibility="collapsed",
    )
    if view.startswith("🗂️"):
        record_cards(docs, meta)
    else:
        st.dataframe(
            to_dataframe(docs, meta["display_columns"]),
            use_container_width=True,
            hide_index=True,
        )
    max_json = 30
    with st.expander(f"Ver JSON dos primeiros {min(len(docs), max_json)} documentos"):
        for doc in docs[:max_json]:
            st.markdown(f"**`{doc.get('_id', '—')}`**")
            st.json(doc, expanded=False)
    if len(docs) > max_json:
        st.caption(f"... e mais {len(docs) - max_json} documento(s) não exibidos no JSON.")


def _template_for(store: SyncDocumentStore, meta: dict[str, Any]) -> dict[str, Any]:
    """Template de INSERT: parte de um doc existente (realista) ou dos campos-chave."""
    existing = store.find_many(meta["name"], limit=1)
    if existing:
        template = existing[0]
        template["_id"] = new_id(meta["name"])
        template["created_at"] = now_iso()
        return template
    template = {"_id": new_id(meta["name"]), "created_at": now_iso()}
    for field in meta["key_fields"]:
        default = field.get("default")
        template[field["name"]] = default if default is not None else ""
    return template


# ----------------------------------------------------------------------
# FIND
# ----------------------------------------------------------------------
def render_find(store: SyncDocumentStore, meta: dict[str, Any]) -> None:
    name = meta["name"]
    st.subheader("🔍 FIND — consultar documentos")
    mode = st.radio(
        "Modo de busca",
        ["Todos", "Por _id", "Por campo = valor"],
        horizontal=True,
        key=f"{name}_find_mode",
    )

    if mode == "Todos":
        limit = st.slider("Limite de resultados", 1, 200, 25, key=f"{name}_find_limit")
        docs = store.find_many(name, limit=limit, sort=[("created_at", -1)])
        _show_results(docs, meta, f"{name}_find_all")

    elif mode == "Por _id":
        doc_id = st.text_input("_id do documento", key=f"{name}_find_id")
        if doc_id.strip():
            doc = store.find_one(name, {"_id": doc_id.strip()})
            _show_results([doc] if doc else [], meta, f"{name}_find_byid")
        else:
            st.caption("Digite um _id para buscar.")

    else:  # Por campo = valor
        col1, col2 = st.columns(2)
        field = col1.selectbox("Campo", meta["search_fields"], key=f"{name}_find_field")
        value = col2.text_input("Valor", key=f"{name}_find_value")
        if value.strip():
            docs = store.find_many(name, {field: _parse_scalar(value)}, limit=200)
            _show_results(docs, meta, f"{name}_find_field_res")
        else:
            st.caption("Digite um valor para filtrar.")


# ----------------------------------------------------------------------
# INSERT
# ----------------------------------------------------------------------
def _insert_form_mode(store: SyncDocumentStore, meta: dict[str, Any]) -> None:
    name = meta["name"]
    with st.form(key=f"{name}_insert_form"):
        st.caption("Preencha os campos principais. O _id e created_at são gerados.")
        custom_id = st.text_input("_id (opcional, gerado se vazio)", key=f"{name}_ins_id")
        values: dict[str, Any] = {}
        for field in meta["key_fields"]:
            fname, label, ftype = field["name"], field["label"], field["type"]
            wkey = f"{name}_ins_{fname}"
            if ftype == "choice":
                options = field["options"] or []
                default = field.get("default")
                index = options.index(default) if default in options else 0
                values[fname] = st.selectbox(label, options, index=index, key=wkey)
            elif ftype == "bool":
                values[fname] = st.checkbox(label, value=bool(field.get("default")), key=wkey)
            elif ftype == "int":
                values[fname] = st.number_input(label, step=1, value=int(field.get("default") or 0), key=wkey)
            elif ftype == "float":
                values[fname] = st.number_input(label, value=float(field.get("default") or 0.0), key=wkey)
            elif ftype == "json":
                default_text = json.dumps(field.get("default") or {}, ensure_ascii=False, indent=2)
                values[fname] = st.text_area(f"{label}", value=default_text, key=wkey, height=100)
            else:  # str
                values[fname] = st.text_input(label, key=wkey, help=field.get("help"))
        submitted = st.form_submit_button("➕ Inserir", type="primary")

    if not submitted:
        return

    doc: dict[str, Any] = {}
    errors: list[str] = []
    for field in meta["key_fields"]:
        fname, ftype = field["name"], field["type"]
        raw = values[fname]
        if ftype == "json":
            text = str(raw).strip()
            if text in {"", "{}", "[]"}:
                if field.get("required"):
                    errors.append(f"Campo obrigatório vazio: {field['label']}")
                continue
            try:
                doc[fname] = json.loads(text)
            except json.JSONDecodeError as exc:
                errors.append(f"JSON inválido em {field['label']}: {exc}")
        elif ftype in {"str", "choice"}:
            if str(raw).strip() == "":
                if field.get("required"):
                    errors.append(f"Campo obrigatório vazio: {field['label']}")
                continue
            doc[fname] = raw
        else:
            doc[fname] = raw

    if errors:
        for err in errors:
            st.error(err)
        return

    doc["_id"] = custom_id.strip() or new_id(name)
    doc.setdefault("created_at", now_iso())
    if store.exists(name, doc["_id"]):
        st.error(f"Já existe um documento com _id = {doc['_id']}.")
        return

    store.insert_one(name, doc)
    st.success(f"Documento inserido com _id = {doc['_id']}")
    st.json(doc)


def _insert_json_mode(store: SyncDocumentStore, meta: dict[str, Any]) -> None:
    name = meta["name"]
    template = _template_for(store, meta)
    text = st.text_area(
        "Documento JSON completo",
        value=json.dumps(template, ensure_ascii=False, indent=2),
        height=320,
        key=f"{name}_ins_json",
    )
    if st.button("➕ Inserir JSON", type="primary", key=f"{name}_ins_json_btn"):
        try:
            doc = json.loads(text)
        except json.JSONDecodeError as exc:
            st.error(f"JSON inválido: {exc}")
            return
        if not isinstance(doc, dict):
            st.error("O documento deve ser um objeto JSON.")
            return
        doc_id = str(doc.get("_id") or "").strip() or new_id(name)
        doc["_id"] = doc_id
        doc.setdefault("created_at", now_iso())
        if store.exists(name, doc_id):
            st.error(f"Já existe um documento com _id = {doc_id}.")
            return
        store.insert_one(name, doc)
        st.success(f"Documento inserido com _id = {doc_id}")
        st.json(doc)


def render_insert(store: SyncDocumentStore, meta: dict[str, Any]) -> None:
    name = meta["name"]
    st.subheader("➕ INSERT — inserir documento")
    mode = st.radio(
        "Modo de inserção",
        ["Formulário", "JSON completo"],
        horizontal=True,
        key=f"{name}_ins_mode",
    )
    if mode == "Formulário":
        _insert_form_mode(store, meta)
    else:
        _insert_json_mode(store, meta)


# ----------------------------------------------------------------------
# UPDATE
# ----------------------------------------------------------------------
def render_update(store: SyncDocumentStore, meta: dict[str, Any]) -> None:
    name = meta["name"]
    st.subheader("✏️ UPDATE — atualizar documento")
    ids = store.ids(name)
    if not ids:
        st.info("Não há documentos para atualizar. Insira um primeiro.")
        return

    selected = st.selectbox("Selecione o _id", ids, key=f"{name}_upd_id")
    current = store.find_one(name, {"_id": selected})
    if current is None:
        st.warning("Documento não encontrado (recarregue a página).")
        return

    with st.expander("Documento atual", expanded=False):
        st.json(current)

    mode = st.radio(
        "Modo de atualização",
        ["Definir campo ($set)", "Substituir documento (JSON)"],
        horizontal=True,
        key=f"{name}_upd_mode",
    )

    if mode == "Definir campo ($set)":
        col1, col2 = st.columns(2)
        path = col1.text_input(
            "Campo (caminho com ponto)", key=f"{name}_upd_path",
            help="ex: status  ou  prediction.score",
        )
        value = col2.text_input("Novo valor", key=f"{name}_upd_value")
        if st.button("✏️ Aplicar $set", type="primary", key=f"{name}_upd_set_btn"):
            if not path.strip():
                st.error("Informe o campo a atualizar.")
                return
            parsed = _parse_value(value)
            ok = store.update_one(name, {"_id": selected}, {"$set": {path.strip(): parsed}})
            if ok:
                st.success(f"Campo '{path.strip()}' atualizado para {parsed!r}.")
                st.json(store.find_one(name, {"_id": selected}))
            else:
                st.error("Falha ao atualizar.")
    else:
        text = st.text_area(
            "Documento JSON (o _id é preservado)",
            value=json.dumps(current, ensure_ascii=False, indent=2),
            height=320,
            key=f"{name}_upd_json",
        )
        if st.button("✏️ Substituir documento", type="primary", key=f"{name}_upd_json_btn"):
            try:
                doc = json.loads(text)
            except json.JSONDecodeError as exc:
                st.error(f"JSON inválido: {exc}")
                return
            if not isinstance(doc, dict):
                st.error("O documento deve ser um objeto JSON.")
                return
            doc["_id"] = selected  # preserva a identidade
            ok = store.replace_one(name, {"_id": selected}, doc)
            if ok:
                st.success("Documento substituído.")
                st.json(doc)
            else:
                st.error("Falha ao substituir.")


# ----------------------------------------------------------------------
# DELETE
# ----------------------------------------------------------------------
def render_delete(store: SyncDocumentStore, meta: dict[str, Any]) -> None:
    name = meta["name"]
    st.subheader("🗑️ DELETE — excluir documento")
    ids = store.ids(name)
    if not ids:
        st.info("Não há documentos para excluir.")
        return

    selected = st.selectbox("Selecione o _id", ids, key=f"{name}_del_id")
    current = store.find_one(name, {"_id": selected})
    if current is not None:
        with st.expander("Documento que será excluído", expanded=True):
            st.json(current)

    confirm = st.checkbox("Confirmo a exclusão deste documento", key=f"{name}_del_confirm")
    if st.button("🗑️ Excluir", type="primary", disabled=not confirm, key=f"{name}_del_btn"):
        ok = store.delete_one(name, {"_id": selected})
        if ok:
            st.success(f"Documento {selected} excluído.")
        else:
            st.error("Falha ao excluir (documento não encontrado).")


# ----------------------------------------------------------------------
# Página completa
# ----------------------------------------------------------------------
def _page_kpis(store: SyncDocumentStore, collection: str, meta: dict[str, Any]) -> None:
    docs = store.all(collection)
    total = len(docs)
    items: list[dict[str, Any]] = [
        {"label": "Documentos", "value": f"{total:,}".replace(",", "."), "tone": "accent",
         "hint": "na coleção"},
    ]
    sample = docs[:50]
    if any("severity" in d for d in sample):
        high = sum(1 for d in docs if str(d.get("severity", "")).lower() in ("high", "critical"))
        items.append({"label": "Severidade alta", "value": high,
                     "tone": "danger" if high else "muted", "hint": "high + critical"})
    if any("status" in d for d in sample):
        from collections import Counter
        counter = Counter(str(d.get("status")) for d in docs if d.get("status"))
        if counter:
            top, top_n = counter.most_common(1)[0]
            good = top in ("active", "resolved", "production")
            items.append({"label": f"Status: {top}", "value": top_n,
                         "tone": "success" if good else "info", "hint": "mais comum"})
    items.append({"label": "Campos no doc", "value": len(docs[0]) if docs else 0,
                 "tone": "info", "hint": "do 1º documento"})
    kpi_cards(items[:4])


def render_page(collection: str) -> None:
    """Renderiza a tela de uma coleção. set_page_config/tema são centralizados no app.py."""
    meta = get_meta(collection)
    store = get_store()

    hero_header(
        title=meta["label"],
        subtitle=meta["description"],
        icon=meta["icon"],
        kicker=f"COLEÇÃO · {collection}",
    )
    _page_kpis(store, collection, meta)
    st.divider()

    tab_find, tab_insert, tab_update, tab_delete = st.tabs(
        ["🔍 FIND", "➕ INSERT", "✏️ UPDATE", "🗑️ DELETE"]
    )
    with tab_find:
        render_find(store, meta)
    with tab_insert:
        render_insert(store, meta)
    with tab_update:
        render_update(store, meta)
    with tab_delete:
        render_delete(store, meta)
