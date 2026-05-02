"""Canonical kWh normalization from bill units (YAML-driven)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

_DEFAULT_CONFIG = Path(__file__).resolve().parent.parent / "config" / "conversions.yaml"


@dataclass
class ConversionResult:
    original_value: float
    original_unit: str
    converted_value_kwh: float
    factor_used: float
    factor_source: str
    notes: str | None = None


class ConversionEngine:
    def __init__(self, config_path: Path | None = None) -> None:
        self._path = Path(config_path) if config_path else _DEFAULT_CONFIG
        self._config: dict[str, Any] = {}
        if self._path.is_file():
            raw = yaml.safe_load(self._path.read_text(encoding="utf-8"))
            self._config = raw if isinstance(raw, dict) else {}

    def th_to_kwh(self, th: float) -> ConversionResult:
        conv = self._config.get("conversions") or {}
        th_entry = conv.get("TH") or {}
        factor = float(th_entry.get("factor", 1.163))
        src = str(th_entry.get("source", "default"))
        return ConversionResult(th, "TH", th * factor, factor, src, None)

    def nm3_pcs_to_kwh(self, nm3: float, pcs: float) -> ConversionResult:
        """When TH is missing: treat NM³×PCS as thermies equivalent, then × kWh/TH."""
        th_equiv = float(nm3) * float(pcs)
        r = self.th_to_kwh(th_equiv)
        kwh_per_nm3 = r.converted_value_kwh / nm3 if nm3 else 0.0
        return ConversionResult(
            nm3,
            "NM3",
            r.converted_value_kwh,
            kwh_per_nm3,
            r.factor_source,
            f"TH_equiv=NM³×PCS={th_equiv:.0f}; PCS={pcs}",
        )

    def gas_bill_to_kwh(
        self,
        th_total: float | None,
        nm3_delta: float | None,
        pcs: float | None,
    ) -> ConversionResult | None:
        """Prefer printed TH; else NM³ × PCS chain."""
        if th_total is not None and th_total > 0:
            return self.th_to_kwh(float(th_total))
        if nm3_delta is not None and pcs is not None:
            default_pcs = float((self._config.get("pcs_factors") or {}).get("default", 10.079))
            return self.nm3_pcs_to_kwh(float(nm3_delta), float(pcs if pcs is not None else default_pcs))
        return None

    def validate_th_nm3(self, th: float, nm3: float, pcs: float) -> dict[str, Any]:
        calc_th = nm3 * pcs
        dev = abs(th - calc_th) / calc_th * 100 if calc_th else 0.0
        tol = (self._config.get("tolerances") or {}).get("th_vs_nm3_pcs") or {}
        max_pct = float(tol.get("max_deviation_percent", 2.0))
        return {
            "is_valid": dev <= max_pct,
            "deviation_percent": dev,
            "calculated_th_from_nm3_pcs": calc_th,
            "th_printed": th,
        }
