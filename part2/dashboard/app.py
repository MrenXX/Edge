"""
Streamlit dashboard: extraction JSON from disk + optional MQTT merge API.
Palette / layout: hybrid (Design 1 tables + Design 2 sand field). See design-hybrid-clarte-elegance.html.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import pandas as pd
import requests
import streamlit as st

from io_documents import (
    audit_latest_per_source,
    default_out_dir,
    load_extracted_documents,
    parse_audit_tail,
)

_PIPELINE = Path(__file__).resolve().parent.parent / "pipeline"
if str(_PIPELINE) not in sys.path:
    sys.path.insert(0, str(_PIPELINE))

from core.conversion_engine import ConversionEngine  # noqa: E402

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

          /* Remove “success green” feel on metrics / values */
          [data-testid="stMetricValue"], [data-testid="stMetricLabel"] {
            color: #282A3A !important;
          }

          /* Dataframes: no accent-green text; palette only */
          [data-testid="stDataFrame"] *, [data-testid="stDataFrame"] [role="gridcell"] {
            color: #282A3A !important;
          }
          [data-testid="stDataFrame"] a { color: #776B5D !important; text-decoration: underline; }
          [data-testid="stDataFrame"] { border: 1px solid rgba(40,42,58,0.2) !important; border-radius: 4px; }

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
        </style>
        """,
        unsafe_allow_html=True,
    )


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


def render_gas_block(gas) -> None:
    engine = conversion_engine()
    th = gas.th_total
    kwh_r = engine.gas_bill_to_kwh(
        th_total=gas.th_total,
        nm3_delta=gas.nm3_delta,
        pcs=gas.pcs,
    )
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Volumes & énergie**")
        kwh_line = fmt_num(kwh_r.converted_value_kwh, 0) if kwh_r else "—"
        note = ""
        if kwh_r and kwh_r.notes:
            note = f" _({kwh_r.notes})_"
        st.markdown(
            f"| | |\n|-|-|\n"
            f"| Δ NM³ | {fmt_num(gas.nm3_delta)} |\n"
            f"| PCS | {fmt_num(gas.pcs, 3)} |\n"
            f"| TH total | {fmt_num(gas.th_total)} |\n"
            f"| Débit souscrit (th/h) | {fmt_num(gas.debit_souscrit_th_h)} |\n"
            f"| **kWh (canonical)** | **{kwh_line}** |\n"
            f"| factor_source | {kwh_r.factor_source if kwh_r else '—'} |{note}\n",
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown("**Montants TND**")
        st.markdown(
            f"| | |\n|-|-|\n"
            f"| Coût HT | {fmt_num(gas.total_cost_ht_tnd, 3) if gas.total_cost_ht_tnd else '—'} |\n"
            f"| Net à payer TTC | {fmt_num(gas.total_net_a_payer_ttc_tnd, 3) if gas.total_net_a_payer_ttc_tnd else '—'} |\n"
            f"| Période (bloc gaz) | {gas.period_label or '—'} |\n",
            unsafe_allow_html=True,
        )
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
    st.caption("Normalization: `part2/pipeline/config/conversions.yaml` + `ConversionEngine` (step11).")


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
    for a in alarms:
        sev = (a.severity or "unknown").upper()
        st.markdown(
            f"**{a.code or '—'}** · _{a.subsystem or '—'}_ · `{sev}`  \n"
            f"<small>{a.timestamp or ''} — {a.message or ''}</small>",
            unsafe_allow_html=True,
        )


def render_document(doc) -> None:
    fam = family_label(doc.document_family)
    conf = f"{doc.confidence_0_1:.0%}" if doc.confidence_0_1 is not None else "—"
    st.markdown(
        f'<div class="doc-card">'
        f"<h3 style='margin-top:0;color:#282A3A'>{doc.source_file}</h3>"
        f"<p><span class='role-pill'>{fam}</span>"
        f"<span class='role-pill'>confidence {conf}</span>"
        f"<span class='role-pill'>{doc.parser_path}</span>"
        f"<span class='role-pill'>{doc.prompt_version or '—'}</span></p>"
        f"<p style='opacity:.88;color:#776B5D'>{doc.site_name or ''} · {doc.period_label or ''}</p></div>",
        unsafe_allow_html=True,
    )

    if doc.raw_warnings:
        for w in doc.raw_warnings:
            st.warning(w)

    if doc.electricity_meters:
        st.markdown("#### Électricité · compteurs")
        for m in doc.electricity_meters:
            ctr = m.ctr_number or "—"
            st.markdown(
                f"**CTR {ctr}** — _{role_label(m.meter_role)}_ · {m.section_title or ''} · {m.purchase_or_sale or ''}"
            )
            st.dataframe(df_electricity_meter(m), use_container_width=True, hide_index=True)

    if doc.gas:
        st.markdown("#### Gaz")
        render_gas_block(doc.gas)

    if doc.water:
        st.markdown("#### Eau")
        render_water_block(doc.water)

    if doc.scada_alarms:
        st.markdown("#### SCADA")
        render_scada(doc.scada_alarms)


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


def render_mqtt_rail(api_base: str) -> None:
    data, err = fetch_iot_bundle(api_base)
    if err or not data:
        st.markdown(
            f"""
            <div class="mqtt-rail">
            <h3>Live telemetry (Part 1)</h3>
            <p>Merge API not reachable at <code>{api_base}</code>.</p>
            <p class="mono" style="opacity:.85">{err or "unknown error"}</p>
            <p class="mono">Start: <code>cd part2/mqtt_merge && uvicorn main:app --port 8000</code>
            or Docker Compose in that folder.</p>
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
        <p>API <strong>{api_base}</strong> · MQTT <strong>{health.get("mqtt_connected")}</strong> ·
        status <strong>{health.get("status")}</strong></p>
        <p class="mono">readings: {agg.get("total_readings", 0)} · anomalies: {h_ac} · rate: {h_rate:.2%}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not recent and health.get("mqtt_connected") and agg.get("total_readings", 0) == 0:
        st.info(
            "Merge API is up and MQTT is connected, but the database has no readings yet. "
            "Ensure Wokwi publishes **valid JSON** to **telemetry/ADWYA-CHILLER-01** (matches merge subscription). "
            "After changing merge settings, restart the merge service once."
        )

    if recent:
        st.subheader("Recent messages (newest first)")
        tbl = []
        for row in recent[:25]:
            sns = row.get("sensors") or {}
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
        st.dataframe(pd.DataFrame(tbl), use_container_width=True, hide_index=True)
    elif agg.get("total_readings", 0) > 0:
        st.warning(
            f"Database reports {agg.get('total_readings')} readings but `/unified/iot` returned no rows "
            "— try restarting the merge API (SQLite query / serialization issue)."
        )


@st.fragment(run_every=4.0)
def mqtt_rail_auto_refresh() -> None:
    base = str(st.session_state.get("mqtt_api_base") or "http://127.0.0.1:8000")
    render_mqtt_rail(base)


def main() -> None:
    st.set_page_config(page_title="Eco-Edge · Unified view", layout="wide", initial_sidebar_state="expanded")
    inject_css()

    st.markdown("# Unified statement — documents & edge")
    st.caption("Warm-field layout matching the hybrid mock. Extraction: `out/*.json`. Live strip: MQTT merge API.")

    with st.sidebar:
        st.markdown("### Settings")
        default = str(default_out_dir())
        out_dir_s = st.text_input("Extraction JSON directory", value=default)
        out_dir = Path(out_dir_s)
        api_default = "http://127.0.0.1:8000"
        api_base = st.text_input(
            "MQTT merge API base URL (HTTP)",
            value=api_default,
            help="FastAPI merge service (port 8000), not MQTT 1883. Run: cd part2/mqtt_merge && uvicorn main:app --port 8000",
        )
        st.session_state["mqtt_api_base"] = api_base
        st.checkbox(
            "Auto-refresh live telemetry every 4s",
            value=True,
            key="mqtt_live_autorefresh",
        )
        st.caption(
            "Wokwi → broker.hivemq.com · topic **telemetry/ADWYA-CHILLER-01** "
            "(merge service subscribes to that topic only — avoids garbage on `telemetry/#`)."
        )
        show_audit = st.checkbox("Show extraction audit (JSONL)", value=True)
        st.divider()
        st.caption("Schema: `energy_extract.models.ExtractedDocument` · `part2/explain.md`")

    docs, load_errors = load_extracted_documents(out_dir)

    col_main, col_rail = st.columns([2.15, 1], gap="large")

    with col_main:
        if load_errors:
            with st.expander("Skipped JSON files (validation / parse)", expanded=False):
                for name, errmsg in load_errors:
                    st.text(f"{name}: {errmsg}")

        if not docs:
            st.error("No valid documents. Check the directory or run the extraction CLI.")
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
            st.dataframe(pd.DataFrame(summary), use_container_width=True, hide_index=True)

        if show_audit:
            audit_path = out_dir / "extraction_audit.jsonl"
            if audit_path.is_file():
                tail = parse_audit_tail(audit_path, max_lines=120)
                latest = audit_latest_per_source(tail)
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
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        st.divider()
        for doc in sorted(docs, key=sort_key_doc):
            render_document(doc)

    with col_rail:
        if st.session_state.get("mqtt_live_autorefresh", True):
            mqtt_rail_auto_refresh()
        else:
            render_mqtt_rail(str(st.session_state.get("mqtt_api_base") or api_base))


if __name__ == "__main__":
    main()
