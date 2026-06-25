from __future__ import annotations

import html
from typing import Any

import streamlit as st

from core.store import get_nested

# Tokens de cor do design system (docs/design-system.md, seção 3).
BRAND = {
    "bg": "#07090d",
    "bg_grid": "#0a0d12",
    "surface": "#0e1218",
    "surface_2": "#131922",
    "surface_3": "#181f2a",
    "border": "#1d2633",
    "border_strong": "#283344",
    "text": "#e6e9ef",
    "text_strong": "#f4f6fb",
    "text_muted": "#9aa6b8",
    "text_subtle": "#6b7689",
    "accent": "#7c5cff",
    "accent_strong": "#9b82ff",
    "success": "#10b981",
    "warning": "#f59e0b",
    "danger": "#ef4444",
    "info": "#38bdf8",
}

# Logo da marca: marca de "sinal/órbita" em SVG inline (sem dependência externa).
LOGO_SVG = """
<svg width="38" height="38" viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
  <rect x="1" y="1" width="38" height="38" rx="11" fill="url(#mtg)" stroke="#7c5cff" stroke-opacity="0.5"/>
  <circle cx="20" cy="20" r="3.4" fill="#9b82ff"/>
  <path d="M20 9c6.1 0 11 4.9 11 11" stroke="#7c5cff" stroke-width="2" stroke-linecap="round"/>
  <path d="M20 14c3.3 0 6 2.7 6 6" stroke="#38bdf8" stroke-width="2" stroke-linecap="round"/>
  <circle cx="31" cy="20" r="1.7" fill="#38bdf8"/>
  <defs>
    <linearGradient id="mtg" x1="0" y1="0" x2="40" y2="40" gradientUnits="userSpaceOnUse">
      <stop stop-color="#151b27"/><stop offset="1" stop-color="#0b0e14"/>
    </linearGradient>
  </defs>
</svg>
"""

_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap');

:root {
  --mt-bg:#07090d; --mt-surface:#0e1218; --mt-surface-2:#131922; --mt-surface-3:#181f2a;
  --mt-border:#1d2633; --mt-border-strong:#283344;
  --mt-text:#e6e9ef; --mt-text-strong:#f4f6fb; --mt-muted:#9aa6b8; --mt-subtle:#6b7689;
  --mt-accent:#7c5cff; --mt-accent-strong:#9b82ff;
  --mt-success:#10b981; --mt-warning:#f59e0b; --mt-danger:#ef4444; --mt-info:#38bdf8;
  --mt-radius:14px; --mt-mono:'IBM Plex Mono',ui-monospace,monospace;
}

/* ---- base / fundo ---- */
.stApp {
  background:
    radial-gradient(1200px 600px at 80% -10%, rgba(124,92,255,.10), transparent 60%),
    radial-gradient(900px 500px at -10% 10%, rgba(56,189,248,.06), transparent 55%),
    var(--mt-bg);
  font-family:'Inter',system-ui,sans-serif;
  color:var(--mt-text);
}
.block-container { padding-top:2.4rem; max-width:1280px; }
[data-testid="stHeader"] { background:transparent; }
.stDeployButton, [data-testid="stToolbar"] { display:none !important; }

h1,h2,h3,h4 { font-family:'Inter',sans-serif !important; color:var(--mt-text-strong) !important;
  letter-spacing:-0.02em; font-weight:700; }
h3 { letter-spacing:-0.011em; }
a { color:var(--mt-accent-strong); }
hr { border-color:var(--mt-border) !important; }
code, pre, [data-testid="stJson"] { font-family:var(--mt-mono) !important; }
[data-testid="stCaptionContainer"], .stCaption { color:var(--mt-muted) !important; }

/* ---- sidebar ---- */
[data-testid="stSidebar"] {
  background:linear-gradient(180deg,#0b0e14,#080a0f);
  border-right:1px solid var(--mt-border);
}
[data-testid="stSidebarNav"] { padding-top:.4rem; }
[data-testid="stSidebarNav"] a {
  border-radius:9px; margin:1px 8px; padding:6px 12px;
  color:var(--mt-muted) !important; font-size:13px; font-weight:500;
  transition:all .15s ease;
}
[data-testid="stSidebarNav"] a:hover { background:var(--mt-surface-2); color:var(--mt-text) !important; }
[data-testid="stSidebarNav"] a[aria-current="page"] {
  background:linear-gradient(135deg, rgba(124,92,255,.20), rgba(124,92,255,.04));
  color:var(--mt-text-strong) !important;
  box-shadow:inset 2px 0 0 var(--mt-accent);
}

/* ---- hero header ---- */
.mt-hero {
  position:relative; overflow:hidden; border-radius:18px;
  border:1px solid var(--mt-border-strong);
  background:linear-gradient(135deg, rgba(124,92,255,.16), rgba(14,18,24,.4) 55%), var(--mt-surface);
  padding:22px 26px; margin-bottom:18px;
}
.mt-hero__glow {
  position:absolute; inset:-60% 40% auto -10%; height:240px;
  background:radial-gradient(circle at 30% 30%, rgba(124,92,255,.35), transparent 60%);
  filter:blur(20px); pointer-events:none;
}
.mt-hero__row { position:relative; display:flex; align-items:center; gap:16px; }
.mt-hero__logo { flex:0 0 auto; display:flex; }
.mt-hero__body { flex:1 1 auto; min-width:0; }
.mt-hero__title { margin:2px 0 4px !important; font-size:30px; line-height:1.1; }
.mt-hero__subtitle { margin:0; color:var(--mt-muted); font-size:13.5px; max-width:74ch; }
.mt-kicker {
  font-family:var(--mt-mono); font-size:11px; letter-spacing:.16em; text-transform:uppercase;
  color:var(--mt-accent-strong); font-weight:600;
}
.mt-hero__live {
  flex:0 0 auto; align-self:flex-start; display:inline-flex; align-items:center; gap:7px;
  font-family:var(--mt-mono); font-size:11px; letter-spacing:.1em; color:var(--mt-success);
  border:1px solid rgba(16,185,129,.3); background:rgba(16,185,129,.08);
  padding:4px 10px; border-radius:999px;
}
.mt-dot { width:7px; height:7px; border-radius:50%; background:var(--mt-success);
  box-shadow:0 0 0 0 rgba(16,185,129,.6); animation:mtpulse 1.8s infinite; }
@keyframes mtpulse {
  0% { box-shadow:0 0 0 0 rgba(16,185,129,.5); }
  70% { box-shadow:0 0 0 7px rgba(16,185,129,0); }
  100% { box-shadow:0 0 0 0 rgba(16,185,129,0); }
}

/* ---- KPI cards ---- */
.mt-kpi-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(160px,1fr)); gap:12px; margin:4px 0 8px; }
.mt-kpi {
  position:relative; border:1px solid var(--mt-border); border-radius:var(--mt-radius);
  background:linear-gradient(160deg, var(--mt-surface-2), var(--mt-surface));
  padding:14px 16px; transition:transform .15s ease, border-color .15s ease;
}
.mt-kpi:hover { transform:translateY(-2px); border-color:var(--mt-border-strong); }
.mt-kpi::before { content:""; position:absolute; left:0; top:12px; bottom:12px; width:3px;
  border-radius:3px; background:var(--mt-accent); }
.mt-kpi--success::before { background:var(--mt-success); }
.mt-kpi--warning::before { background:var(--mt-warning); }
.mt-kpi--danger::before  { background:var(--mt-danger); }
.mt-kpi--info::before    { background:var(--mt-info); }
.mt-kpi__label { font-size:11px; letter-spacing:.06em; text-transform:uppercase; color:var(--mt-muted); }
.mt-kpi__value { font-family:var(--mt-mono); font-feature-settings:"tnum"; font-size:30px;
  font-weight:600; color:var(--mt-text-strong); line-height:1.15; margin-top:2px; }
.mt-kpi__hint { font-size:11.5px; color:var(--mt-subtle); margin-top:1px; }

/* ---- badges / chips ---- */
.mt-badge { display:inline-flex; align-items:center; gap:5px; font-family:var(--mt-mono);
  font-size:10.5px; font-weight:600; letter-spacing:.04em; text-transform:uppercase;
  padding:2px 8px; border-radius:999px; border:1px solid transparent; }
.mt-badge--accent  { color:#c5b6ff; background:rgba(124,92,255,.14); border-color:rgba(124,92,255,.3); }
.mt-badge--success { color:#5ee9bf; background:rgba(16,185,129,.13); border-color:rgba(16,185,129,.3); }
.mt-badge--warning { color:#fbcf72; background:rgba(245,158,11,.13); border-color:rgba(245,158,11,.3); }
.mt-badge--danger  { color:#fca5a5; background:rgba(239,68,68,.14); border-color:rgba(239,68,68,.32); }
.mt-badge--info    { color:#8fd6f7; background:rgba(56,189,248,.12); border-color:rgba(56,189,248,.3); }
.mt-badge--muted   { color:var(--mt-muted); background:var(--mt-surface-3); border-color:var(--mt-border); }

/* ---- record cards (modo cartões) ---- */
.mt-card-grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(330px,1fr)); gap:12px; }
.mt-card {
  position:relative; overflow:hidden; border:1px solid var(--mt-border); border-radius:var(--mt-radius);
  background:linear-gradient(160deg, var(--mt-surface-2), var(--mt-surface));
  padding:14px 16px 13px; transition:transform .15s ease, border-color .15s ease;
}
.mt-card:hover { transform:translateY(-2px); border-color:var(--mt-border-strong); }
.mt-card::after { content:""; position:absolute; left:0; top:0; bottom:0; width:3px; background:var(--mt-accent); }
.mt-card--success::after { background:var(--mt-success); }
.mt-card--warning::after { background:var(--mt-warning); }
.mt-card--danger::after  { background:var(--mt-danger); }
.mt-card--info::after    { background:var(--mt-info); }
.mt-card__head { display:flex; align-items:center; justify-content:space-between; gap:8px; margin-bottom:7px; }
.mt-card__id { font-family:var(--mt-mono); font-size:11px; color:var(--mt-subtle); overflow-wrap:anywhere; }
.mt-card__badges { display:flex; gap:5px; flex-wrap:wrap; justify-content:flex-end; }
.mt-card__title { font-size:15px; font-weight:600; color:var(--mt-text-strong); margin-bottom:9px;
  line-height:1.25; overflow-wrap:anywhere; }
.mt-card__fields { display:flex; flex-wrap:wrap; gap:6px; }
.mt-chip { font-size:11px; color:var(--mt-text); background:var(--mt-surface-3); border:1px solid var(--mt-border);
  padding:2px 8px; border-radius:7px; overflow-wrap:anywhere; }
.mt-chip b { color:var(--mt-muted); font-weight:600; font-size:10px; text-transform:uppercase;
  letter-spacing:.04em; margin-right:4px; }

/* ---- tabs ---- */
[data-baseweb="tab-list"] { gap:4px; border-bottom:1px solid var(--mt-border) !important; }
[data-baseweb="tab"] { font-weight:600 !important; color:var(--mt-muted) !important; border-radius:9px 9px 0 0; }
[data-baseweb="tab"][aria-selected="true"] { color:var(--mt-text-strong) !important; }
[data-baseweb="tab-highlight"] { background:var(--mt-accent) !important; height:3px !important; }

/* ---- métrica nativa (fallback) ---- */
[data-testid="stMetricValue"] { font-family:var(--mt-mono) !important; font-feature-settings:"tnum"; color:var(--mt-text-strong) !important; }
[data-testid="stMetricLabel"] p { text-transform:uppercase; letter-spacing:.06em; font-size:11px !important; color:var(--mt-muted) !important; }

/* ---- inputs / selects ---- */
.stTextInput input, .stTextArea textarea, [data-baseweb="input"], [data-baseweb="select"] > div {
  background:var(--mt-surface) !important; border-color:var(--mt-border) !important; color:var(--mt-text) !important;
  border-radius:10px !important; font-family:'Inter',sans-serif;
}
.stTextInput input:focus, .stTextArea textarea:focus { border-color:var(--mt-accent) !important;
  box-shadow:0 0 0 3px rgba(124,92,255,.22) !important; }
.stTextArea textarea { font-family:var(--mt-mono) !important; font-size:12.5px !important; }

/* ---- botões ---- */
.stButton > button, .stFormSubmitButton > button, [data-testid="stBaseButton-secondary"] {
  border-radius:10px !important; font-weight:600 !important; border:1px solid var(--mt-border-strong) !important;
  background:var(--mt-surface-2) !important; color:var(--mt-text) !important; transition:all .15s ease;
}
.stButton > button:hover { border-color:var(--mt-accent) !important; color:var(--mt-text-strong) !important; }
[data-testid="stBaseButton-primary"], .stFormSubmitButton > button {
  background:linear-gradient(135deg, var(--mt-accent), var(--mt-accent-strong)) !important;
  border:1px solid transparent !important; color:#fff !important;
  box-shadow:0 8px 24px rgba(124,92,255,.28) !important;
}
[data-testid="stBaseButton-primary"]:hover { filter:brightness(1.07); }

/* ---- containers de dados ---- */
[data-testid="stDataFrame"] { border:1px solid var(--mt-border); border-radius:var(--mt-radius); overflow:hidden; }
[data-testid="stExpander"] { border:1px solid var(--mt-border) !important; border-radius:11px !important;
  background:var(--mt-surface) !important; }
[data-testid="stExpander"] summary { font-family:var(--mt-mono); font-size:12px; color:var(--mt-muted); }
[data-testid="stJson"] { background:var(--mt-surface) !important; border:1px solid var(--mt-border);
  border-radius:11px; padding:8px 10px; }

/* ---- alerts (success/info/warning/error) ---- */
[data-testid="stAlert"] { border-radius:11px !important; border:1px solid var(--mt-border) !important; }

/* ---- radios horizontais como "segmented" ---- */
.stRadio [role="radiogroup"] { gap:6px; }

/* ---- divisor de seção ---- */
.mt-sec { font-family:var(--mt-mono); font-size:11px; letter-spacing:.14em; text-transform:uppercase;
  color:var(--mt-subtle); margin:14px 0 6px; }
</style>
"""


def inject_theme() -> None:
    """Injeta o CSS da marca. Chamar uma vez no topo de cada página."""
    st.markdown(_CSS, unsafe_allow_html=True)


# ----------------------------------------------------------------------
# Componentes de marca (HTML)
# ----------------------------------------------------------------------
def _esc(value: Any) -> str:
    return html.escape(str(value))


def hero_header(title: str, subtitle: str, icon: str = "", kicker: str = "MODELTRACE") -> None:
    st.markdown(
        f"""
        <div class="mt-hero">
          <div class="mt-hero__glow"></div>
          <div class="mt-hero__row">
            <div class="mt-hero__logo">{LOGO_SVG}</div>
            <div class="mt-hero__body">
              <div class="mt-kicker">{_esc(kicker)}</div>
              <h1 class="mt-hero__title">{_esc(icon)} {_esc(title)}</h1>
              <p class="mt-hero__subtitle">{_esc(subtitle)}</p>
            </div>
            <div class="mt-hero__live"><span class="mt-dot"></span> LIVE</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def kpi_cards(items: list[dict[str, Any]]) -> None:
    """items: [{label, value, tone?, hint?}]. tone: accent|success|warning|danger|info."""
    cards = []
    for item in items:
        tone = item.get("tone", "accent")
        hint = item.get("hint", "")
        hint_html = f'<div class="mt-kpi__hint">{_esc(hint)}</div>' if hint else ""
        cards.append(
            f'<div class="mt-kpi mt-kpi--{_esc(tone)}">'
            f'<div class="mt-kpi__label">{_esc(item["label"])}</div>'
            f'<div class="mt-kpi__value">{_esc(item["value"])}</div>'
            f"{hint_html}</div>"
        )
    st.markdown(f'<div class="mt-kpi-grid">{"".join(cards)}</div>', unsafe_allow_html=True)


def badge(text: str, tone: str = "muted") -> str:
    return f'<span class="mt-badge mt-badge--{_esc(tone)}">{_esc(text)}</span>'


def section_label(text: str) -> None:
    st.markdown(f'<div class="mt-sec">{_esc(text)}</div>', unsafe_allow_html=True)


# ---- mapeamento de tom semântico -------------------------------------
_SEVERITY_TONE = {"low": "info", "medium": "warning", "high": "danger", "critical": "danger"}
_STATUS_TONE = {
    "active": "success", "open": "warning", "acknowledged": "info", "resolved": "success",
    "suspended": "danger", "disabled": "danger", "revoked": "danger", "archived": "muted",
    "deprecated": "muted", "invited": "info", "staging": "warning", "production": "success",
}


def tone_for_doc(doc: dict[str, Any]) -> str:
    sev = str(doc.get("severity", "")).lower()
    if sev in _SEVERITY_TONE:
        return _SEVERITY_TONE[sev]
    status = str(doc.get("status", "")).lower()
    if status in _STATUS_TONE:
        return _STATUS_TONE[status]
    return "accent"


def _doc_title(doc: dict[str, Any]) -> str:
    for field in ("name", "title", "event_type", "version"):
        value = doc.get(field)
        if value:
            return str(value)
    return str(doc.get("_id", "—"))


def _doc_badges(doc: dict[str, Any]) -> str:
    out = []
    sev = str(doc.get("severity", "")).lower()
    if sev:
        out.append(badge(sev, _SEVERITY_TONE.get(sev, "muted")))
    status = str(doc.get("status", "")).lower()
    if status:
        out.append(badge(status, _STATUS_TONE.get(status, "muted")))
    for field, tone in (("plan", "accent"), ("role", "info"), ("problem_type", "accent"),
                        ("type", "muted"), ("algorithm", "info")):
        value = doc.get(field)
        if value and field not in ("severity", "status"):
            out.append(badge(str(value), tone))
    return "".join(out[:3])


def record_cards(docs: list[dict[str, Any]], meta: dict[str, Any]) -> None:
    """Renderiza documentos como cartões on-brand (modo cartões do FIND)."""
    title_field = _doc_title  # função
    cards = []
    chip_fields = [c for c in meta["display_columns"] if c not in ("created_at",)][:4]
    for doc in docs:
        tone = tone_for_doc(doc)
        chips = []
        for field in chip_fields:
            value = get_nested(doc, field)
            if value in (None, "", [], {}):
                continue
            text = value if not isinstance(value, (dict, list)) else "…"
            label = field.split(".")[-1]
            chips.append(f'<span class="mt-chip"><b>{_esc(label)}</b>{_esc(text)}</span>')
        created = doc.get("created_at")
        if created:
            chips.append(f'<span class="mt-chip"><b>criado</b>{_esc(created)}</span>')
        cards.append(
            f'<div class="mt-card mt-card--{tone}">'
            f'<div class="mt-card__head">'
            f'<span class="mt-card__id">{_esc(doc.get("_id","—"))}</span>'
            f'<span class="mt-card__badges">{_doc_badges(doc)}</span>'
            f"</div>"
            f'<div class="mt-card__title">{_esc(title_field(doc))}</div>'
            f'<div class="mt-card__fields">{"".join(chips)}</div>'
            f"</div>"
        )
    st.markdown(f'<div class="mt-card-grid">{"".join(cards)}</div>', unsafe_allow_html=True)
