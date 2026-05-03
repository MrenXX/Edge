"""Build `GET /unified` envelope (documents + IoT strip / period stats)."""

from __future__ import annotations

import math
from collections import Counter
from datetime import datetime
from typing import Any

from core.co2_engine import Co2Engine
from core.conversion_engine import ConversionEngine
from energy_extract.models import ExtractedDocument


def _parse_ts(s: str | None) -> datetime | None:
    if not s or not isinstance(s, str):
        return None
    t = s.strip()
    if t.endswith("Z"):
        t = t[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(t)
    except ValueError:
        return None


def _accel_norm(sensors: dict[str, Any]) -> float | None:
    try:
        ax = sensors.get("accel_x_g")
        ay = sensors.get("accel_y_g")
        az = sensors.get("accel_z_g")
        if ax is None or ay is None or az is None:
            return None
        return float(math.sqrt(float(ax) ** 2 + float(ay) ** 2 + float(az) ** 2))
    except (TypeError, ValueError):
        return None


def build_iot_live_strip(recent_readings: list[dict], limit: int = 80) -> list[dict]:
    strip: list[dict] = []
    for row in recent_readings[:limit]:
        sns = row.get("sensors") or {}
        strip.append(
            {
                "timestamp": row.get("timestamp"),
                "temp_c": sns.get("temp_c"),
                "accel_norm": _accel_norm(sns),
                "edge_anomaly": bool(row.get("edge_anomaly")),
            }
        )
    return strip


def build_iot_period_aggregates(
    documents: list[ExtractedDocument], readings: list[dict]
) -> list[dict]:
    if not readings:
        return []
    out: list[dict] = []
    for d in documents:
        ps = _parse_ts(d.period_start)
        pe = _parse_ts(d.period_end)
        if not ps or not pe:
            continue
        if ps > pe:
            ps, pe = pe, ps
        bucket: list[dict] = []
        for row in readings:
            t = _parse_ts(str(row.get("timestamp")) if row.get("timestamp") is not None else None)
            if t and ps <= t <= pe:
                bucket.append(row)
        if not bucket:
            continue
        temps: list[float] = []
        norms: list[float] = []
        anomalies = 0
        for row in bucket:
            sns = row.get("sensors") or {}
            tc = sns.get("temp_c")
            if tc is not None:
                try:
                    temps.append(float(tc))
                except (TypeError, ValueError):
                    pass
            n = _accel_norm(sns)
            if n is not None:
                norms.append(n)
            if row.get("edge_anomaly"):
                anomalies += 1
        out.append(
            {
                "period_start": d.period_start,
                "period_end": d.period_end,
                "source_file": d.source_file,
                "document_family": d.document_family,
                "reading_count": len(bucket),
                "mean_temp_c": sum(temps) / len(temps) if temps else None,
                "max_accel_norm": max(norms) if norms else None,
                "anomaly_rate": anomalies / len(bucket),
            }
        )
    return out


def build_validation_summary(documents: list[ExtractedDocument], audit_last_ts: str | None) -> dict:
    warn_docs = sum(1 for d in documents if d.raw_warnings)
    total_warns = sum(len(d.raw_warnings or []) for d in documents)
    return {
        "documents_loaded": len(documents),
        "documents_with_warnings": warn_docs,
        "total_raw_warnings": total_warns,
        "last_extraction_audit_ts": audit_last_ts,
    }


def build_normalized_rollups(documents: list[ExtractedDocument]) -> dict[str, Any]:
    families = Counter(d.document_family for d in documents)
    conv = ConversionEngine()
    co2 = Co2Engine()
    kwh_sum = 0.0
    slot_rows = 0
    gas_kwh_total = 0.0
    gas_co2_kg = 0.0
    el_co2_import_kg = 0.0
    el_co2_export_avoided_kg = 0.0
    el_co2_onsite_kg = 0.0
    for d in documents:
        if d.gas:
            kr = conv.gas_bill_to_kwh(d.gas.th_total, d.gas.nm3_delta, d.gas.pcs)
            if kr:
                gk = float(kr.converted_value_kwh)
                gas_kwh_total += gk
                gco = co2.from_gas_kwh(gk)
                if gco:
                    gas_co2_kg += gco.kg_co2
        for m in d.electricity_meters:
            kwh_m = 0.0
            for row in m.rows:
                if row.delta_active_kwh is not None and not row.is_reactive:
                    dv = float(row.delta_active_kwh)
                    kwh_sum += dv
                    kwh_m += dv
                    slot_rows += 1
            eco = co2.from_meter_role_kwh(kwh_m, m.meter_role)
            if eco and kwh_m > 0:
                if m.meter_role == "grid_import":
                    el_co2_import_kg += eco.kg_co2
                elif m.meter_role == "grid_injection":
                    el_co2_export_avoided_kg += eco.kg_co2
                elif m.meter_role == "onsite_generation":
                    el_co2_onsite_kg += eco.kg_co2
    return {
        "electricity_delta_active_kwh_sum": kwh_sum if slot_rows else None,
        "electricity_non_reactive_slot_row_count": slot_rows,
        "document_families": dict(families),
        "gas_bill_kwh_total": gas_kwh_total if gas_kwh_total else None,
        "co2_estimates_kg": {
            "natural_gas_from_bills": gas_co2_kg if gas_kwh_total else None,
            "electricity_grid_import": el_co2_import_kg if el_co2_import_kg else None,
            "electricity_grid_export_avoided": el_co2_export_avoided_kg if el_co2_export_avoided_kg else None,
            "electricity_onsite_proxy": el_co2_onsite_kg if el_co2_onsite_kg else None,
        },
        "co2_method_note": co2.method_note,
        "method_note": (
            "Sums delta_active_kwh for non-reactive STEG slot rows; gas kWh from "
            "ConversionEngine; CO2 from config/co2_factors.yaml (indicatif)."
        ),
    }
