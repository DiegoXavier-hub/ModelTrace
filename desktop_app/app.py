"""
Execução:
    streamlit run app.py
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from core.collections import COLLECTION_NAMES, COLLECTIONS, get_meta
from core.seed import seed
from core.store import DEFAULT_DATA_PATH
from ui.crud import get_store, render_page
from ui.theme import BRAND, hero_header, inject_theme, kpi_cards, section_label

st.set_page_config(page_title="ModelTrace", page_icon="🛰️", layout="wide")
inject_theme()


# ----------------------------------------------------------------------
# Visão geral
# ----------------------------------------------------------------------
def overview_page() -> None:
    store = get_store()
    counts = store.collection_counts()
    total = sum(counts.values())

    hero_header(
        title="Visão geral",
        subtitle="Monitoramento, governança e auditoria de modelos de machine learning em produção.",
        icon="🛰️",
        kicker="OBSERVABILIDADE DE MODELOS",
    )

    kpi_cards([
        {"label": "Coleções", "value": len(COLLECTIONS), "tone": "accent", "hint": "monitoradas"},
        {"label": "Registros", "value": f"{total:,}".replace(",", "."), "tone": "info", "hint": "no acervo"},
        {"label": "Predições", "value": counts.get("predictions", 0), "tone": "success", "hint": "decisões"},
        {"label": "Alertas", "value": counts.get("alerts", 0), "tone": "warning", "hint": "operacionais"},
        {"label": "Auditoria", "value": counts.get("audit_events", 0), "tone": "danger", "hint": "eventos"},
    ])

    st.divider()

    section_label("Fonte de dados")
    left, right = st.columns([3, 2])
    with left:
        st.caption(f"Acervo local · `{DEFAULT_DATA_PATH.name}`")
    with right:
        b1, b2 = st.columns(2)
        with b1:
            if st.button("📥 Carregar", use_container_width=True):
                seed(force=False)
                st.rerun()
        with b2:
            if st.button("♻️ Restaurar amostra", use_container_width=True):
                try:
                    seed(force=True)
                    st.rerun()
                except FileNotFoundError as exc:
                    st.error(str(exc))

    st.divider()

    section_label("Distribuição por coleção")
    overview = pd.DataFrame(
        [
            {
                "Coleção": get_meta(name)["label"],
                "Registros": counts.get(name, 0),
                "Descrição": COLLECTIONS[name]["description"],
            }
            for name in COLLECTION_NAMES
        ]
    )
    st.dataframe(overview, use_container_width=True, hide_index=True)
    st.bar_chart(overview.set_index("Coleção")["Registros"], color=BRAND["accent"], height=300)


# ----------------------------------------------------------------------
# Navegação
# ----------------------------------------------------------------------
def _collection_runner(collection: str):
    def _run() -> None:
        render_page(collection)
    return _run


overview = st.Page(overview_page, title="Visão geral", icon="🛰️", default=True)
collection_pages = [
    st.Page(
        _collection_runner(name),
        title=get_meta(name)["label"],
        icon=get_meta(name)["icon"],
        url_path=name,
    )
    for name in COLLECTION_NAMES
]

st.navigation({"": [overview], "Coleções": collection_pages}).run()
