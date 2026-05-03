"""Build `GET /unified` envelope (documents + IoT strip / period stats)."""

from __future__ import annotations

import math
from collections import Counter
from datetime import datetime
from typing import Any

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
    kwh_sum = 0.0
    slot_rows = 0
    for d in documents:
        for m in d.electricity_meters:
            for row in m.rows:
                if row.delta_active_kwh is not None and not row.is_reactive:
                    kwh_sum += float(row.delta_active_kwh)
                    slot_rows += 1
    return {
        "electricity_delta_active_kwh_sum": kwh_sum if slot_rows else None,
        "electricity_non_reactive_slot_row_count": slot_rows,
        "document_families": dict(families),
        "method_note": (
            "Sums delta_active_kwh for non-reactive STEG slot rows; extend with "
            "ConversionEngine + co2_factors per plan_part2.md."
        ),
    }
