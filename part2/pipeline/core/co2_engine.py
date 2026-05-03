"""Indicative CO2eq (kg) from normalized kWh using YAML factors."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

_DEFAULT = Path(__file__).resolve().parent.parent / "config" / "co2_factors.yaml"


@dataclass
class Co2Estimate:
    kg_co2: float
    kg_co2_per_kwh: float
    factor_key: str
    source: str


class Co2Engine:
    def __init__(self, config_path: Path | None = None) -> None:
        self._path = Path(config_path) if config_path else _DEFAULT
        raw: dict[str, Any] = {}
        if self._path.is_file():
            loaded = yaml.safe_load(self._path.read_text(encoding="utf-8"))
            raw = loaded if isinstance(loaded, dict) else {}
        self._factors = raw.get("factors") or {}
        self.method_note: str = str(raw.get("method_note") or "").strip()

    def _kg_per_kwh(self, key: str) -> tuple[float, str]:
        entry = self._factors.get(key) or {}
        v = float(entry.get("kg_co2_per_kwh", 0.0))
        src = str(entry.get("source", key))
        return v, src

    def from_gas_kwh(self, kwh: float) -> Co2Estimate | None:
        if kwh is None or kwh <= 0:
            return None
        rate, src = self._kg_per_kwh("natural_gas_combustion")
        if rate <= 0:
            return None
        return Co2Estimate(kwh * rate, rate, "natural_gas_combustion", src)

    def from_meter_role_kwh(self, kwh: float, meter_role: str) -> Co2Estimate | None:
        if kwh is None or kwh <= 0:
            return None
        role = (meter_role or "unknown").strip()
        if role == "grid_import":
            rate, src = self._kg_per_kwh("grid_import")
            return Co2Estimate(kwh * rate, rate, "grid_import", src)
        if role == "grid_injection":
            rate, src = self._kg_per_kwh("grid_export_avoided")
            return Co2Estimate(abs(kwh * rate), rate, "grid_export_avoided", src)
        if role == "onsite_generation":
            rate, src = self._kg_per_kwh("onsite_generation_proxy")
            return Co2Estimate(kwh * rate, rate, "onsite_generation_proxy", src)
        return None
