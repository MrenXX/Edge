"""
Streamlit dashboard: extraction JSON from disk + optional MQTT merge API.
Palette / layout: hybrid (Design 1 tables + Design 2 sand field). See design-hybrid-clarte-elegance.html.
Adds: drag-and-drop real-time OCR via Gemini for ad-hoc bills / SCADA shots.
"""

from __future__ import annotations

import json
import math
import os
import sys
import tempfile
from html import escape as html_escape
from io import StringIO
from pathlib import Path

import altair as alt
import pandas as pd
import requests
import streamlit as st
import streamlit.components.v1 as components

from io_documents import (
    audit_latest_per_source,
    default_out_dir,
    load_extracted_documents,
    parse_audit_tail,
)

_PIPELINE = Path(__file__).resolve().parent.parent / "pipeline"
_PART2_ROOT = _PIPELINE.parent
if str(_PIPELINE) not in sys.path:
    sys.path.insert(0, str(_PIPELINE))
if str(_PART2_ROOT) not in sys.path:
    sys.path.insert(0, str(_PART2_ROOT))

# Load API keys before any pipeline import (Streamlit reruns this file often).
def _bootstrap_env() -> None:
    paths = (
        _PART2_ROOT.parent / ".env",
        _PIPELINE / ".env",
        _PART2_ROOT / ".env",
    )
    try:
        from dotenv import load_dotenv

        for _env_path in paths:
            if _env_path.is_file():
                load_dotenv(_env_path, override=True)
    except ImportError:
        for _env_path in paths:
            if not _env_path.is_file():
                continue
            for line in _env_path.read_text(encoding="utf-8").splitlines():
                s = line.strip()
                if not s or s.startswith("#") or "=" not in s:
                    continue
                key, _, val = s.partition("=")
                key, val = key.strip(), val.strip().strip('"').strip("'")
                if key and val:
                    os.environ[key] = val


_bootstrap_env()

from core.co2_engine import Co2Engine  # noqa: E402
from core.conversion_engine import ConversionEngine  # noqa: E402

try:
    from api.unified_builder import build_normalized_rollups  # noqa: E402
except ImportError:
    build_normalized_rollups = None  # type: ignore[assignment]

# Optional: real-time OCR uses google-genai + pymupdf (pipeline deps).
# Wrap the import so the dashboard still loads even if the user only installed
# the bare dashboard requirements; we then surface a friendly hint in the UI.
try:
    from energy_extract.gemini_extract import extract_document_path  # noqa: E402

    _OCR_AVAILABLE = True
    _OCR_IMPORT_ERROR: str | None = None
except Exception as _ocr_err:  # pragma: no cover - depends on local install
    extract_document_path = None  # type: ignore[assignment]
    _OCR_AVAILABLE = False
    _OCR_IMPORT_ERROR = str(_ocr_err)


ROLE_FR = {
    "grid_injection": "Injection réseau",
    "onsite_generation": "Production site (tri-gén.)",
    "grid_import": "Achat réseau",
    "unknown": "Rôle inconnu",
}

FAMILY_FR = {
    "electricity_steg": "Électricité STEG",
    "gas_steg": "Gaz STEG",
    "water_sonede": "Eau SONEDE",
    "scada_alarms": "SCADA / alarmes",
    "unknown": "Document",
}


def inject_css() -> None:
    st.markdown(
        r"""
        <style>
          @import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,600&family=Newsreader:opsz,wght@6..72,400;6..72,600&display=swap');

          .stApp {
            font-family: "Newsreader", Georgia, serif !important;
          }
          .stApp, .main {
            color: #282A3A !important;
          }

          .stApp, [data-testid="stAppViewContainer"] {
            background-color: #BBAB8C !important;
          }

          [data-testid="stAppViewContainer"] > .main .block-container {
            background-color: transparent !important;
            padding-top: 1.25rem;
            max-width: 1400px;
          }

          h1, h2, h3, h4, [data-testid="stMarkdownContainer"] h1,
          [data-testid="stMarkdownContainer"] h2,
          [data-testid="stMarkdownContainer"] h3 {
            font-family: "Fraunces", Georgia, serif !important;
            color: #282A3A !important;
          }

          /* Header / toolbar — paper strip, not dark */
          header[data-testid="stHeader"] {
            background: rgba(255,255,255,0.22) !important;
            border-bottom: 1px solid rgba(40,42,58,0.12) !important;
          }
          [data-testid="stDecoration"] { display: none; }

          /* Sidebar — light paper (hybrid), not terminal */
          section[data-testid="stSidebar"] {
            background: rgba(255,255,255,0.38) !important;
            border-right: 1px solid rgba(40,42,58,0.14) !important;
          }
          section[data-testid="stSidebar"] p, section[data-testid="stSidebar"] span,
          section[data-testid="stSidebar"] label, section[data-testid="stSidebar"] .stMarkdown {
            color: #282A3A !important;
          }
          section[data-testid="stSidebar"] .stTextInput label { color: #776B5D !important; }
          section[data-testid="stSidebar"] input {
            background: rgba(255,255,255,0.55) !important;
            color: #282A3A !important;
            border-color: #776B5D !important;
          }
          section[data-testid="stSidebar"] [data-baseweb="base-input"] input {
            background: rgba(255,255,255,0.55) !important;
          }

          /* Remove "success green" feel on metrics / values */
          [data-testid="stMetricValue"], [data-testid="stMetricLabel"] {
            color: #282A3A !important;
          }

          /* Inline `code` (markdown backticks) — palette umber, not the default green */
          [data-testid="stMarkdownContainer"] code,
          [data-testid="stCaptionContainer"] code,
          .stMarkdown code {
            color: #776B5D !important;
            background: rgba(40,42,58,0.06) !important;
            padding: 1px 5px;
            border-radius: 3px;
            font-family: ui-monospace, "Cascadia Code", monospace;
            font-size: 0.88em;
          }

          /* Streamlit dataframe — bordered grid; font colors unchanged above */
          [data-testid="stDataFrame"] {
            border: 1px solid rgba(40,42,58,0.32) !important;
            border-radius: 4px !important;
            background: transparent !important;
          }
          [data-testid="stDataFrame"] [role="gridcell"],
          [data-testid="stDataFrame"] [role="columnheader"] {
            border-left: 1px solid rgba(40,42,58,0.18) !important;
            border-top: 1px solid rgba(40,42,58,0.18) !important;
          }
          [data-testid="stDataFrame"] *,
          [data-testid="stDataFrame"] [role="gridcell"] {
            color: #282A3A !important;
          }
          [data-testid="stDataFrame"] [role="columnheader"],
          [data-testid="stDataFrame"] [role="columnheader"] *,
          [data-testid="stDataFrame"] thead th,
          [data-testid="stDataFrame"] thead th * {
            color: #282A3A !important;
            font-weight: 700 !important;
            font-family: "Fraunces", Georgia, serif !important;
          }
          [data-testid="stDataFrame"] a { color: #776B5D !important; text-decoration: underline; }

          /* HTML extraction tables — bordered grid */
          .extract-table {
            width: 100%;
            border-collapse: collapse;
            margin: 0.35rem 0 0.9rem 0;
            background: transparent;
            font-family: "Newsreader", Georgia, serif;
            border: 1px solid rgba(40,42,58,0.32);
          }
          .extract-table thead th {
            color: #282A3A !important;
            font-weight: 700;
            font-family: "Fraunces", Georgia, serif;
            text-align: left;
            padding: 8px 12px;
            background: rgba(40,42,58,0.10);
            border: 1px solid rgba(40,42,58,0.26);
            font-size: 0.92rem;
            letter-spacing: 0.01em;
          }
          .extract-table tbody td {
            color: #282A3A;
            padding: 7px 12px;
            border: 1px solid rgba(40,42,58,0.22);
            font-size: 0.95rem;
          }
          .extract-table tbody tr:hover td { background: rgba(255,255,255,0.30); }

          /* Markdown-rendered key/value tables (gas / amount blocks) */
          [data-testid="stMarkdownContainer"] table {
            border-collapse: collapse;
            width: 100%;
            border: 1px solid rgba(40,42,58,0.32) !important;
            background: transparent !important;
          }
          [data-testid="stMarkdownContainer"] table thead th {
            color: #282A3A !important;
            font-weight: 700 !important;
            font-family: "Fraunces", Georgia, serif !important;
            background: rgba(40,42,58,0.10) !important;
            border: 1px solid rgba(40,42,58,0.26) !important;
            text-align: left !important;
            padding: 7px 10px !important;
          }
          [data-testid="stMarkdownContainer"] table tbody td {
            color: #282A3A !important;
            border: 1px solid rgba(40,42,58,0.22) !important;
            padding: 6px 10px !important;
          }

          /* Global links — not Streamlit default green */
          a[href] { color: #776B5D !important; }
          a[href]:hover { color: #282A3A !important; }

          /* Progress: umber bar */
          .stProgress > div > div > div > div {
            background-color: #776B5D !important;
          }

          .doc-card {
            background: rgba(255,255,255,0.34);
            border: 1px solid rgba(40,42,58,0.12);
            border-radius: 4px;
            padding: 1rem 1.15rem;
            margin-bottom: 1.25rem;
            box-shadow: 0 1px 0 rgba(255,255,255,0.45) inset;
          }
          .ocr-card {
            background: rgba(255,255,255,0.42);
            border: 1px dashed rgba(40,42,58,0.30);
            border-radius: 6px;
            padding: 1rem 1.2rem 0.6rem 1.2rem;
            margin-bottom: 1.4rem;
          }
          .ocr-card h3 {
            margin-top: 0 !important;
            color: #282A3A !important;
          }
          .ocr-card p {
            color: #776B5D !important;
            margin-bottom: 0.4rem;
          }

          /* File uploader — paper, not steel-blue */
          [data-testid="stFileUploaderDropzone"] {
            background: rgba(255,255,255,0.55) !important;
            border: 2px dashed rgba(40,42,58,0.35) !important;
            border-radius: 5px !important;
          }
          [data-testid="stFileUploaderDropzone"] * {
            color: #282A3A !important;
          }

          /* Native Streamlit charts — paper frame like extract tables */
          [data-testid="stChart"] {
            border: 1px solid rgba(40,42,58,0.28) !important;
            border-radius: 4px !important;
            background: rgba(255,255,255,0.22) !important;
            padding: 0.35rem !important;
          }

          .mqtt-rail {
            background: #282A3A;
            color: #BBAB8C;
            padding: 1rem 1.1rem;
            border-radius: 4px;
            border: 1px solid rgba(187,171,140,0.28);
            min-height: 200px;
          }
          .mqtt-rail h3 { color: #BBAB8C !important; font-size: 1.05rem !important; margin-top: 0; }
          .mqtt-rail code, .mqtt-rail .mono {
            font-family: ui-monospace, "Cascadia Code", monospace;
            font-size: 11px;
            color: #BBAB8C;
          }
          .role-pill {
            display: inline-block;
            background: #282A3A;
            color: #BBAB8C;
            font-size: 11px;
            padding: 2px 10px;
            border-radius: 3px;
            margin-right: 6px;
            font-family: ui-monospace, monospace;
          }

          /* Edge telemetry: anomaly rows */
          .extract-table tbody tr.edge-anomaly-row td {
            background: rgba(200, 60, 60, 0.22) !important;
            border-color: rgba(140, 30, 30, 0.42) !important;
            color: #3a1212 !important;
            font-weight: 600;
          }
          .extract-table tbody tr.edge-anomaly-row:hover td {
            background: rgba(200, 60, 60, 0.30) !important;
          }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_html_table(df: pd.DataFrame) -> None:
    """Render a dataframe as a styled HTML table (clear dark headers, no outer border)."""
    if df.empty:
        st.caption("— aucune ligne —")
        return
    head_cells = "".join(f"<th>{html_escape(str(c))}</th>" for c in df.columns)
    body_rows: list[str] = []
    for _, row in df.iterrows():
        cells = "".join(
            f"<td>{html_escape('' if pd.isna(v) else str(v))}</td>" for v in row.tolist()
        )
        body_rows.append(f"<tr>{cells}</tr>")
    html = (
        '<table class="extract-table">'
        f"<thead><tr>{head_cells}</tr></thead>"
        f"<tbody>{''.join(body_rows)}</tbody>"
        "</table>"
    )
    st.markdown(html, unsafe_allow_html=True)


def fmt_num(v: float | int | None, decimals: int = 0) -> str:
    if v is None:
        return "—"
    if decimals:
        return f"{float(v):.{decimals}f}".replace(".", ",")
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    return f"{int(v):,}".replace(",", "\u202f")


def family_label(fam: str) -> str:
    return FAMILY_FR.get(fam, fam)


def role_label(role: str) -> str:
    return ROLE_FR.get(role, role)


def sort_key_doc(doc) -> tuple[int, str]:
    order = {
        "electricity_steg": 0,
        "gas_steg": 1,
        "water_sonede": 2,
        "scada_alarms": 3,
        "unknown": 9,
    }
    return (order.get(doc.document_family, 5), doc.source_file or "")


def _parse_period_mmyyyy(label: str | None) -> tuple[int, int] | None:
    """Return (year, month) for sorting from labels like 05/2025; None if unknown."""
    if not label or not isinstance(label, str):
        return None
    s = label.strip()
    for sep in ("/", "-", "."):
        if sep not in s:
            continue
        parts = [p.strip() for p in s.split(sep) if p.strip()]
        if len(parts) != 2:
            continue
        try:
            a, b = int(parts[0]), int(parts[1])
        except ValueError:
            continue
        if 1 <= a <= 12 and 2000 <= b <= 2100:
            return (b, a)
        if 1 <= b <= 12 and 2000 <= a <= 2100:
            return (a, b)
    return None


def maybe_render_gas_cost_over_time(docs: list) -> None:
    """Simple TTC trend for gas STEG bills (period_label on disk JSON)."""
    agg: dict[tuple[int, int], float] = {}
    for d in docs:
        if getattr(d, "document_family", "") != "gas_steg" or not getattr(d, "gas", None):
            continue
        g = d.gas
        pl = g.period_label or getattr(d, "period_label", None)
        key = _parse_period_mmyyyy(pl)
        ttc = g.total_net_a_payer_ttc_tnd
        if key is None or ttc is None:
            continue
        try:
            agg[key] = agg.get(key, 0.0) + float(ttc)
        except (TypeError, ValueError):
            continue
    if not agg:
        return
    ordered = sorted(agg.items())
    df = pd.DataFrame(
        [{"Période (facture)": f"{m:02d}/{y}", "TTC (TND)": v} for (y, m), v in ordered]
    )
    st.subheader("Gaz STEG — net à payer (TTC) dans le temps")
    st.caption("Périodes d’après `period_label` des JSON chargés ; même mois additionné.")
    periods = df["Période (facture)"].tolist()
    line_color = "#9B2C2C"
    base = alt.Chart(df).encode(
        x=alt.X("Période (facture):O", sort=periods, title="Période (facture)"),
        y=alt.Y("TTC (TND):Q", title="TTC (TND)"),
    )
    chart = (
        base.mark_line(color=line_color, strokeWidth=2.75, interpolate="monotone")
        + base.mark_point(
            color=line_color,
            filled=True,
            size=70,
            stroke="#FFFDF8",
            strokeWidth=1.5,
        )
    ).properties(height=280)
    st.altair_chart(chart, use_container_width=True)


def df_electricity_meter(m) -> pd.DataFrame:
    rows = []
    for r in m.rows:
        rows.append(
            {
                "Créneau": r.time_slot or "—",
                "Code": r.tariff_code or "—",
                "Ancien": fmt_num(r.ancien_index) if r.ancien_index is not None else "—",
                "Nouveau": fmt_num(r.nouveau_index) if r.nouveau_index is not None else "—",
                "Δ kWh actif": fmt_num(r.delta_active_kwh) if r.delta_active_kwh is not None else "—",
                "Réactif": "oui" if r.is_reactive else "",
                "Δ réactif": fmt_num(r.reactive_delta) if r.reactive_delta is not None else "—",
                "Unité réact.": r.reactive_unit or "—",
            }
        )
    return pd.DataFrame(rows)


@st.cache_resource
def conversion_engine() -> ConversionEngine:
    return ConversionEngine()


@st.cache_resource
def co2_engine() -> Co2Engine:
    return Co2Engine()


def _meter_non_reactive_active_kwh_sum(m) -> float:
    total = 0.0
    for r in m.rows or []:
        if r.delta_active_kwh is not None and not r.is_reactive:
            total += float(r.delta_active_kwh)
    return total


def render_gas_block(gas) -> None:
    engine = conversion_engine()
    kwh_r = engine.gas_bill_to_kwh(
        th_total=gas.th_total,
        nm3_delta=gas.nm3_delta,
        pcs=gas.pcs,
    )
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Volumes & énergie**")
        kwh_line = fmt_num(kwh_r.converted_value_kwh, 0) if kwh_r else "—"
        gas_df = pd.DataFrame(
            [
                ["Δ NM³", fmt_num(gas.nm3_delta)],
                ["PCS", fmt_num(gas.pcs, 3)],
                ["TH total", fmt_num(gas.th_total)],
                ["Débit souscrit (th/h)", fmt_num(gas.debit_souscrit_th_h)],
                ["kWh (canonical)", kwh_line],
                ["factor_source", (kwh_r.factor_source if kwh_r else "—")],
            ],
            columns=["Champ", "Valeur"],
        )
        render_html_table(gas_df)
        if kwh_r and kwh_r.notes:
            st.caption(kwh_r.notes)
    with c2:
        st.markdown("**Montants TND**")
        amounts_df = pd.DataFrame(
            [
                ["Coût HT", fmt_num(gas.total_cost_ht_tnd, 3) if gas.total_cost_ht_tnd else "—"],
                ["Net à payer TTC", fmt_num(gas.total_net_a_payer_ttc_tnd, 3) if gas.total_net_a_payer_ttc_tnd else "—"],
                ["Période (bloc gaz)", gas.period_label or "—"],
            ],
            columns=["Champ", "Valeur"],
        )
        render_html_table(amounts_df)
    c_co2 = co2_engine()
    if kwh_r and kwh_r.converted_value_kwh is not None:
        try:
            gk = float(kwh_r.converted_value_kwh)
        except (TypeError, ValueError):
            gk = 0.0
        if gk > 0:
            g_co2 = c_co2.from_gas_kwh(gk)
            if g_co2:
                st.markdown("#### CO₂ gaz (indicatif)")
                co2_gas_df = pd.DataFrame(
                    [
                        ["Émissions approx. (kg CO₂eq)", fmt_num(g_co2.kg_co2, 1)],
                        ["Facteur (kg/kWh)", f"{g_co2.kg_co2_per_kwh:.4f}".replace(".", ",")],
                        ["Source facteur", g_co2.source],
                    ],
                    columns=["Indicateur", "Valeur"],
                )
                render_html_table(co2_gas_df)
    if c_co2.method_note:
        st.caption(c_co2.method_note)
    if (
        gas.th_total is not None
        and gas.nm3_delta is not None
        and gas.pcs is not None
        and gas.th_total > 0
        and gas.nm3_delta > 0
    ):
        v = engine.validate_th_nm3(float(gas.th_total), float(gas.nm3_delta), float(gas.pcs))
        if v["is_valid"]:
            st.caption(f"TH vs NM³×PCS check: OK (deviation {v['deviation_percent']:.2f}%)")
        else:
            st.warning(
                f"TH vs NM³×PCS deviation {v['deviation_percent']:.2f}% — review bill / PCS."
            )


def render_water_block(water) -> None:
    st.markdown("**SONEDE · eau**")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Volume m³", fmt_num(water.volume_m3) if water.volume_m3 is not None else "—")
    with c2:
        st.metric(
            "Frais consommation eau HT",
            fmt_num(water.frais_consommation_eau_ht_tnd, 3) if water.frais_consommation_eau_ht_tnd else "—",
        )
    with c3:
        st.metric(
            "Frais assainissement HT",
            fmt_num(water.frais_assainissement_ht_tnd, 3) if water.frais_assainissement_ht_tnd else "—",
        )
    st.metric(
        "Net à payer TTC",
        fmt_num(water.total_net_a_payer_ttc_tnd, 3) if water.total_net_a_payer_ttc_tnd else "—",
    )
    a = water.frais_consommation_eau_ht_tnd
    b = water.frais_assainissement_ht_tnd
    if a is not None and b is not None and (a + b) > 0:
        st.progress(a / (a + b), text="Répartition HT (consommation vs assainissement)")


def render_scada(alarms) -> None:
    rows = []
    for a in alarms:
        rows.append(
            {
                "Sévérité": (a.severity or "unknown").upper(),
                "Code": a.code or "—",
                "Sous-système": a.subsystem or "—",
                "Horodatage": a.timestamp or "—",
                "Message": a.message or "—",
            }
        )
    if rows:
        render_html_table(pd.DataFrame(rows))


def render_document(doc) -> None:
    fam = family_label(doc.document_family)
    conf = f"{doc.confidence_0_1:.0%}" if doc.confidence_0_1 is not None else "—"
    st.markdown(
        f'<div class="doc-card">'
        f"<h3 style='margin-top:0;color:#282A3A'>{html_escape(doc.source_file or '')}</h3>"
        f"<p><span class='role-pill'>{html_escape(fam)}</span>"
        f"<span class='role-pill'>confidence {conf}</span>"
        f"<span class='role-pill'>{html_escape(doc.parser_path or '')}</span>"
        f"<span class='role-pill'>{html_escape(doc.prompt_version or '—')}</span></p>"
        f"<p style='opacity:.88;color:#776B5D'>{html_escape(doc.site_name or '')} · {html_escape(doc.period_label or '')}</p></div>",
        unsafe_allow_html=True,
    )

    if doc.raw_warnings:
        for w in doc.raw_warnings:
            st.warning(w)

    if doc.electricity_meters:
        st.markdown("#### Électricité · compteurs")
        ce = co2_engine()
        co2_note_shown = False
        for m in doc.electricity_meters:
            ctr = m.ctr_number or "—"
            st.markdown(
                f"**CTR {html_escape(ctr)}** — _{html_escape(role_label(m.meter_role))}_ · "
                f"{html_escape(m.section_title or '')} · {html_escape(m.purchase_or_sale or '')}",
                unsafe_allow_html=True,
            )
            render_html_table(df_electricity_meter(m))
            kwh_net = _meter_non_reactive_active_kwh_sum(m)
            est = ce.from_meter_role_kwh(kwh_net, m.meter_role)
            if est and kwh_net > 0:
                tonnes = est.kg_co2 / 1000.0
                role = (m.meter_role or "").strip()
                if role == "grid_injection":
                    st.markdown(
                        f"*CO₂ **évité** (ordre de grandeur, injection) : **{fmt_num(tonnes, 3)}** t équ.*"
                    )
                    label_kg = "CO₂ évité approx. (kg CO₂eq)"
                elif role == "onsite_generation":
                    st.markdown(
                        f"*CO₂ **associé** (proxy site / tri-gén.) : **{fmt_num(tonnes, 3)}** t équ.*"
                    )
                    label_kg = "CO₂ associé proxy (kg CO₂eq)"
                else:
                    st.markdown(
                        f"*CO₂ **associé** à l'achat réseau (indicatif) : **{fmt_num(tonnes, 3)}** t équ.*"
                    )
                    label_kg = "CO₂ associé approx. (kg CO₂eq)"
                co2_el_df = pd.DataFrame(
                    [
                        ["Σ Δ kWh actif (hors réactif)", fmt_num(kwh_net, 0)],
                        [label_kg, fmt_num(est.kg_co2, 1)],
                        ["Facteur (kg/kWh)", f"{est.kg_co2_per_kwh:.4f}".replace(".", ",")],
                        ["Clé facteur", est.factor_key],
                        ["Source facteur", est.source],
                    ],
                    columns=["Indicateur", "Valeur"],
                )
                render_html_table(co2_el_df)
                if ce.method_note and not co2_note_shown:
                    st.caption(ce.method_note)
                    co2_note_shown = True

    if doc.gas:
        st.markdown("#### Gaz")
        render_gas_block(doc.gas)

    if doc.water:
        st.markdown("#### Eau")
        render_water_block(doc.water)

    if doc.scada_alarms:
        st.markdown("#### SCADA")
        render_scada(doc.scada_alarms)


# ---------------------------------------------------------------------------
# Real-time OCR upload section
# ---------------------------------------------------------------------------

_OCR_ACCEPTED = ["pdf", "png", "jpg", "jpeg", "webp"]


def _run_ocr_on_upload(uploaded_file) -> "tuple[object | None, str | None]":
    """Persist upload to a temp file, run extract_document_path, return (doc, error)."""
    if not _OCR_AVAILABLE or extract_document_path is None:
        return None, _OCR_IMPORT_ERROR or "OCR pipeline not available."
    suffix = Path(uploaded_file.name).suffix.lower() or ".bin"
    tmp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(uploaded_file.getbuffer())
            tmp_path = Path(tmp.name)
        doc = extract_document_path(tmp_path)
        try:
            doc.source_file = uploaded_file.name
        except Exception:
            pass
        return doc, None
    except Exception as e:  # noqa: BLE001 — user-facing surface
        return None, str(e)
    finally:
        if tmp_path is not None:
            try:
                tmp_path.unlink(missing_ok=True)
            except Exception:
                pass


def render_ocr_upload_section() -> None:
    st.markdown(
        '<div class="ocr-card">'
        "<h3>Glisser-déposer · extraction temps réel</h3>"
        "<p>Déposez une facture (STEG / SONEDE), un PDF de relevé ou une capture SCADA. "
        "Le pipeline Gemini renverra un document structuré au-dessous.</p>"
        "</div>",
        unsafe_allow_html=True,
    )

    if not _OCR_AVAILABLE:
        st.error(
            "Real-time OCR n'est pas disponible — installez le SDK dans **le même Python** que Streamlit : "
            "`pip install google-genai` ou `pip install -r part2/dashboard/requirements.txt`."
        )
        if _OCR_IMPORT_ERROR:
            with st.expander("Détails de l'import"):
                st.code(_OCR_IMPORT_ERROR)
        return

    uploaded = st.file_uploader(
        "Déposez un fichier ici (PDF, PNG, JPG, JPEG, WEBP)",
        type=_OCR_ACCEPTED,
        accept_multiple_files=False,
        key="ocr_uploader",
        label_visibility="collapsed",
    )
    if uploaded is None:
        return

    # Cache by file content so re-renders don't re-bill the API.
    file_bytes = uploaded.getbuffer().tobytes()
    cache: dict[int, object] = st.session_state.setdefault("_ocr_cache", {})
    cache_key = hash(file_bytes)

    if cache_key not in cache:
        with st.spinner(f"Extraction Gemini de **{uploaded.name}**…"):
            doc, err = _run_ocr_on_upload(uploaded)
        if err:
            st.error(f"Échec de l'extraction : {err}")
            return
        cache[cache_key] = doc  # type: ignore[assignment]
    else:
        doc = cache[cache_key]

    fam = family_label(getattr(doc, "document_family", "unknown"))
    conf_val = getattr(doc, "confidence_0_1", None)
    conf_str = f"{conf_val:.0%}" if conf_val is not None else "n/a"
    st.success(f"OK · famille **{fam}** · confiance **{conf_str}**")
    render_document(doc)
    st.divider()


def _accel_norm_g(sensors: dict) -> str:
    try:
        ax = sensors.get("accel_x_g")
        ay = sensors.get("accel_y_g")
        az = sensors.get("accel_z_g")
        if ax is None or ay is None or az is None:
            return "—"
        n = math.sqrt(float(ax) ** 2 + float(ay) ** 2 + float(az) ** 2)
        return f"{n:.3f}g"
    except (TypeError, ValueError):
        return "—"


def fetch_iot_bundle(api_base: str, timeout: float = 2.0) -> tuple[dict | None, str | None]:
    base = api_base.rstrip("/")
    try:
        h = requests.get(f"{base}/health", timeout=timeout)
        h.raise_for_status()
        u = requests.get(f"{base}/unified/iot", timeout=timeout)
        u.raise_for_status()
        return {"health": h.json(), "unified": u.json()}, None
    except Exception as e:
        return None, str(e)


def _accel_norm_float(sensors: dict) -> float | None:
    try:
        ax = sensors.get("accel_x_g")
        ay = sensors.get("accel_y_g")
        az = sensors.get("accel_z_g")
        if ax is None or ay is None or az is None:
            return None
        return float(math.sqrt(float(ax) ** 2 + float(ay) ** 2 + float(az) ** 2))
    except (TypeError, ValueError):
        return None


def _edge_anomaly_truthy(val: object) -> bool:
    if val is True:
        return True
    if val is False or val is None:
        return False
    if isinstance(val, (int, float)) and int(val) == 1:
        return True
    if isinstance(val, str) and val.strip().lower() in ("1", "true", "yes"):
        return True
    return False


def _reading_stable_id(row: dict) -> str:
    rid = row.get("id")
    if rid is not None:
        return str(rid)
    return f"{row.get('device_id')}|{row.get('timestamp')}|{row.get('received_at')}"


def _inject_anomaly_notifications(alerts: list[dict]) -> None:
    if not alerts:
        return
    payload: list[dict[str, str]] = []
    for row in alerts:
        dev = row.get("device_id") if row.get("device_id") is not None else "?"
        ts = row.get("timestamp") if row.get("timestamp") is not None else row.get("received_at") or ""
        payload.append(
            {
                "title": f"Edge anomaly · {dev}",
                "body": f"{ts} — open Edge Telemetry tab for details.",
                "tag": f"edge-anom-{_reading_stable_id(row)}",
            }
        )
    alerts_json = json.dumps(payload)
    components.html(
        f"""
<script>
const __edgeAlerts = {alerts_json};
(function () {{
  const root = window.parent ?? window;
  if (!root.Notification) return;
  function showOne(a) {{
    try {{
      const opts = {{ body: a.body, tag: a.tag }};
      if (root.Notification.permission === "granted") {{
        new root.Notification(a.title, opts);
      }} else if (root.Notification.permission === "default") {{
        root.Notification.requestPermission().then(function (p) {{
          if (p === "granted") new root.Notification(a.title, opts);
        }});
      }}
    }} catch (e) {{}}
  }}
  __edgeAlerts.forEach(showOne);
}})();
</script>
        """,
        height=0,
    )


def maybe_notify_new_edge_anomalies(recent: list) -> None:
    """Browser desktop notifications for new edge_anomaly rows (runs from sidebar rail on any main tab)."""
    if not recent:
        return
    notified: set[str] = st.session_state.setdefault("edge_anomaly_notified_ids", set())
    boot = st.session_state.setdefault("_edge_anomaly_notify_bootstrapped", False)
    ids_now = {_reading_stable_id(r) for r in recent if _edge_anomaly_truthy(r.get("edge_anomaly"))}
    if not boot:
        notified.update(ids_now)
        st.session_state["_edge_anomaly_notify_bootstrapped"] = True
        return
    fresh: list[dict] = []
    for row in recent:
        if not _edge_anomaly_truthy(row.get("edge_anomaly")):
            continue
        sid = _reading_stable_id(row)
        if sid in notified:
            continue
        notified.add(sid)
        fresh.append(row)
    if fresh:
        _inject_anomaly_notifications(fresh)
        for row in fresh:
            st.toast(
                f"Edge anomaly · {row.get('device_id') or '?'} — see Edge Telemetry",
                icon="🔺",
            )


def render_telemetry_readings_table(df: pd.DataFrame, row_anomaly: list[bool]) -> None:
    if df.empty:
        st.caption("— aucune ligne —")
        return
    if len(row_anomaly) != len(df):
        render_html_table(df)
        return
    head_cells = "".join(f"<th>{html_escape(str(c))}</th>" for c in df.columns)
    body_rows: list[str] = []
    for (_, row), is_anom in zip(df.iterrows(), row_anomaly, strict=True):
        tr_cls = ' class="edge-anomaly-row"' if is_anom else ""
        cells = "".join(
            f"<td>{html_escape('' if pd.isna(v) else str(v))}</td>" for v in row.tolist()
        )
        body_rows.append(f"<tr{tr_cls}>{cells}</tr>")
    html = (
        '<table class="extract-table">'
        f"<thead><tr>{head_cells}</tr></thead>"
        f"<tbody>{''.join(body_rows)}</tbody>"
        "</table>"
    )
    st.markdown(html, unsafe_allow_html=True)


def render_mqtt_summary(api_base: str) -> None:
    data, err = fetch_iot_bundle(api_base)
    if err or not data:
        st.markdown(
            f"""
            <div class="mqtt-rail">
            <h3>Live telemetry (Part 1)</h3>
            <p>Merge API not reachable at <code>{html_escape(api_base)}</code>.</p>
            <p class="mono" style="opacity:.85">{html_escape(err or "unknown error")}</p>
            <p class="mono">Start the merge service on port 8000, or use Docker Compose in part2/mqtt_merge.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    health = data["health"]
    uni = data["unified"]
    agg = uni.get("aggregates") or {}
    recent = uni.get("recent_readings") or []

    h_ac = int(health.get("anomaly_count") or agg.get("anomaly_count") or 0)
    h_rate = float(health.get("anomaly_rate") if health.get("anomaly_rate") is not None else agg.get("anomaly_rate") or 0.0)

    st.markdown(
        f"""
        <div class="mqtt-rail">
        <h3>Live telemetry (Part 1)</h3>
        <p>API <strong>{html_escape(api_base)}</strong> · MQTT <strong>{health.get("mqtt_connected")}</strong> ·
        status <strong>{health.get("status")}</strong></p>
        <p class="mono">readings: {agg.get("total_readings", 0)} · anomalies: {h_ac} · rate: {h_rate:.2%}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not recent and health.get("mqtt_connected") and agg.get("total_readings", 0) == 0:
        st.info(
            "Merge API is up and MQTT is connected, but the database has no readings yet. "
            "Ensure Wokwi publishes valid JSON to telemetry/ADWYA-CHILLER-01 (matches merge subscription). "
            "After changing merge settings, restart the merge service once."
        )
    elif recent:
        maybe_notify_new_edge_anomalies(recent)
        st.caption(
            f"{len(recent)} recent messages — open the **Edge Telemetry** tab for the full table and CSV export."
        )
    elif agg.get("total_readings", 0) > 0:
        st.warning(
            f"Database reports {agg.get('total_readings')} readings but /unified/iot returned no rows "
            "— try restarting the merge API (SQLite query / serialization issue)."
        )


def render_telemetry_tab(api_base: str) -> None:
    data, err = fetch_iot_bundle(api_base)
    if err or not data:
        st.error(f"Merge API not reachable at {api_base}: {err}")
        return

    health = data["health"]
    uni = data["unified"]
    agg = uni.get("aggregates") or {}
    recent = uni.get("recent_readings") or []

    h_ac = int(health.get("anomaly_count") or agg.get("anomaly_count") or 0)
    h_rate = float(health.get("anomaly_rate") if health.get("anomaly_rate") is not None else agg.get("anomaly_rate") or 0.0)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("MQTT connected", str(health.get("mqtt_connected")))
    with c2:
        st.metric("Total readings", fmt_num(agg.get("total_readings", 0)))
    with c3:
        st.metric("Anomalies", fmt_num(h_ac))
    with c4:
        st.metric("Anomaly rate", f"{h_rate:.2%}")

    st.divider()

    if not recent and health.get("mqtt_connected") and agg.get("total_readings", 0) == 0:
        st.info(
            "Merge API is up and MQTT is connected, but the database has no readings yet. "
            "Ensure Wokwi publishes valid JSON to telemetry/ADWYA-CHILLER-01 (matches merge subscription). "
            "After changing merge settings, restart the merge service once."
        )
        return

    if not recent and agg.get("total_readings", 0) > 0:
        st.warning(
            f"Database reports {agg.get('total_readings')} readings but /unified/iot returned no rows "
            "— try restarting the merge API (SQLite query / serialization issue)."
        )
        return

    if recent:
        st.subheader("Recent messages (newest first)")
        tbl: list[dict] = []
        row_anomaly: list[bool] = []
        for row in recent[:50]:
            sns = row.get("sensors") or {}
            is_anom = _edge_anomaly_truthy(row.get("edge_anomaly"))
            row_anomaly.append(is_anom)
            tbl.append(
                {
                    "id": row.get("id"),
                    "timestamp": row.get("timestamp"),
                    "device_id": row.get("device_id"),
                    "temp_c": sns.get("temp_c"),
                    "accel_norm_g": _accel_norm_float(sns),
                    "edge_anomaly": row.get("edge_anomaly"),
                    "received_at": row.get("received_at"),
                }
            )
        df = pd.DataFrame(tbl)
        if not df.empty:
            csv_buffer = StringIO()
            df.to_csv(csv_buffer, index=False)
            st.download_button(
                label="Export to CSV",
                data=csv_buffer.getvalue().encode("utf-8"),
                file_name="edge_telemetry.csv",
                mime="text/csv",
                key="telemetry_csv_download",
            )
        render_telemetry_readings_table(df, row_anomaly)


@st.fragment(run_every=4.0)
def mqtt_summary_auto_refresh() -> None:
    base = str(st.session_state.get("mqtt_api_base") or "http://127.0.0.1:8000")
    render_mqtt_summary(base)


@st.fragment(run_every=4.0)
def mqtt_telemetry_auto_refresh() -> None:
    base = str(st.session_state.get("mqtt_api_base") or "http://127.0.0.1:8000")
    render_telemetry_tab(base)


def main() -> None:
    try:
        from energy_extract.env_loader import load_all_dotenv

        load_all_dotenv()
    except Exception:
        pass

    st.set_page_config(page_title="Eco-Edge · Unified view", layout="wide", initial_sidebar_state="expanded")
    inject_css()

    st.markdown("# Unified statement — documents & edge")
    st.caption("Warm-field layout matching the hybrid mock. Documents from disk + drag-and-drop OCR + live MQTT.")

    with st.sidebar:
        st.markdown("### Settings")
        default = str(default_out_dir())
        out_dir_s = st.text_input("Extraction JSON directory", value=default)
        out_dir = Path(out_dir_s)
        api_default = "http://127.0.0.1:8000"
        api_base = st.text_input(
            "MQTT merge API base URL (HTTP)",
            value=api_default,
            help="FastAPI merge service (port 8000), not MQTT 1883.",
        )
        st.session_state["mqtt_api_base"] = api_base
        st.checkbox(
            "Auto-refresh live telemetry every 4s",
            value=True,
            key="mqtt_live_autorefresh",
        )
        st.caption(
            "Wokwi → broker.hivemq.com · topic telemetry/ADWYA-CHILLER-01 "
            "(merge service subscribes only to that topic)."
        )
        show_audit = st.checkbox("Show extraction audit (JSONL)", value=True)

    docs, load_errors = load_extracted_documents(out_dir)

    col_main, col_rail = st.columns([2.15, 1], gap="large")

    with col_main:
        tab_docs, tab_telemetry = st.tabs(["Documents", "Edge Telemetry"])

        with tab_docs:
            render_ocr_upload_section()

            if load_errors:
                with st.expander("Skipped JSON files (validation / parse)", expanded=False):
                    for name, errmsg in load_errors:
                        st.text(f"{name}: {errmsg}")

            if not docs:
                st.error("No valid documents on disk yet. Use the upload box above, or run the extraction CLI.")
            else:
                summary = []
                for d in docs:
                    summary.append(
                        {
                            "File": d.source_file,
                            "Family": family_label(d.document_family),
                            "Period": d.period_label or "—",
                            "Confidence": f"{d.confidence_0_1:.0%}" if d.confidence_0_1 is not None else "—",
                        }
                    )
                st.subheader("Loaded files")
                render_html_table(pd.DataFrame(summary))
                if build_normalized_rollups is not None:
                    roll = build_normalized_rollups(docs)
                    co2blk = roll.get("co2_estimates_kg") or {}
                    synth: list[list[str]] = []
                    gk = roll.get("gas_bill_kwh_total")
                    if gk is not None:
                        synth.append(["Énergie gaz (kWh canoniques, Σ factures)", fmt_num(float(gk), 0)])
                    ek = roll.get("electricity_delta_active_kwh_sum")
                    if ek is not None:
                        synth.append(["Σ Δ kWh actif élec. (hors réactif)", fmt_num(float(ek), 0)])
                    if co2blk.get("natural_gas_from_bills") is not None:
                        synth.append(["CO₂ gaz · kg CO₂eq (indicatif)", fmt_num(float(co2blk["natural_gas_from_bills"]), 0)])
                    if co2blk.get("electricity_grid_import") is not None:
                        synth.append(
                            ["CO₂ élec. achat réseau · kg CO₂eq", fmt_num(float(co2blk["electricity_grid_import"]), 0)]
                        )
                    if co2blk.get("electricity_grid_export_avoided") is not None:
                        synth.append(
                            [
                                "CO₂ élec. évité (injection) · kg CO₂eq",
                                fmt_num(float(co2blk["electricity_grid_export_avoided"]), 0),
                            ]
                        )
                    if co2blk.get("electricity_onsite_proxy") is not None:
                        synth.append(
                            ["CO₂ élec. site (proxy) · kg CO₂eq", fmt_num(float(co2blk["electricity_onsite_proxy"]), 0)]
                        )
                    if synth:
                        st.subheader("Synthèse énergie / CO₂ (disque)")
                        render_html_table(pd.DataFrame(synth, columns=["Indicateur", "Valeur"]))
                        if roll.get("co2_method_note"):
                            st.caption(str(roll["co2_method_note"]))
                        if roll.get("method_note"):
                            st.caption(str(roll["method_note"]))

                maybe_render_gas_cost_over_time(docs)

            if show_audit:
                audit_path = out_dir / "extraction_audit.jsonl"
                if audit_path.is_file():
                    tail = parse_audit_tail(audit_path, max_lines=120)
                    latest = audit_latest_per_source(tail)
                    if latest:
                        st.subheader("Latest run per source (audit)")
                        rows = []
                        for r in latest:
                            rows.append(
                                {
                                    "File": r.get("source_file", "—"),
                                    "OK": "\u2713" if r.get("ok") else "\u2717",
                                    "Error": (r.get("error") or "")[:48],
                                    "Time": r.get("ts", "—"),
                                    "Output JSON": Path(str(r.get("output_json", ""))).name if r.get("output_json") else "—",
                                }
                            )
                        render_html_table(pd.DataFrame(rows))

            st.divider()
            for doc in sorted(docs, key=sort_key_doc):
                render_document(doc)

        with tab_telemetry:
            if st.session_state.get("mqtt_live_autorefresh", True):
                mqtt_telemetry_auto_refresh()
            else:
                render_telemetry_tab(str(st.session_state.get("mqtt_api_base") or api_base))

    with col_rail:
        if st.session_state.get("mqtt_live_autorefresh", True):
            mqtt_summary_auto_refresh()
        else:
            render_mqtt_summary(str(st.session_state.get("mqtt_api_base") or api_base))


if __name__ == "__main__":
    main()
