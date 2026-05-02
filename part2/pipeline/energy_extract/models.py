"""Pydantic models for unified extraction JSON (STEG, SONEDE, gas, SCADA)."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator, model_validator


class ElectricitySlotRow(BaseModel):
    time_slot: str | None = None  # Jour, Pointe, Soir, Soire, Nuit, ...
    tariff_code: str | None = None  # e.g. 2.8.3
    ancien_index: float | None = None
    nouveau_index: float | None = None
    delta_active_kwh: float | None = None
    is_reactive: bool = False
    reactive_delta: float | None = None
    reactive_unit: str | None = None  # kVArh if known
    unit_raw: str | None = None
    notes: str | None = None


class ElectricityMeter(BaseModel):
    ctr_number: str | None = None  # N°CTR
    meter_role: str = "unknown"  # grid_injection | onsite_generation | grid_import | unknown
    section_title: str | None = None
    purchase_or_sale: str | None = None  # Achat / Vente if printed
    rows: list[ElectricitySlotRow] = Field(default_factory=list)

    @field_validator("ctr_number", mode="before")
    @classmethod
    def _ctr_to_str(cls, v: object) -> str | None:
        if v is None:
            return None
        if isinstance(v, bool):
            return str(v)
        if isinstance(v, int):
            return str(v)
        if isinstance(v, float):
            if v.is_integer():
                return str(int(v))
            return str(v)
        return str(v)


class GasBillFields(BaseModel):
    nm3_delta: float | None = None
    pcs: float | None = None
    th_total: float | None = None
    debit_souscrit_th_h: float | None = None
    total_cost_ht_tnd: float | None = None
    total_net_a_payer_ttc_tnd: float | None = None
    period_label: str | None = None


class WaterBillFields(BaseModel):
    volume_m3: float | None = None
    frais_consommation_eau_ht_tnd: float | None = None
    frais_assainissement_ht_tnd: float | None = None
    total_net_a_payer_ttc_tnd: float | None = None
    period_label: str | None = None


class ScadaAlarm(BaseModel):
    timestamp: str | None = None
    severity: str = "unknown"  # critical | warning | info | unknown
    code: str | None = None
    message: str | None = None
    subsystem: str | None = None  # Chiller, engine, network, ...


class ExtractedDocument(BaseModel):
    source_file: str
    document_family: str = "unknown"  # electricity_steg | gas_steg | water_sonede | scada_alarms | unknown
    supplier: str | None = None
    site_name: str | None = None
    period_label: str | None = None
    period_start: str | None = None
    period_end: str | None = None
    confidence_0_1: float | None = Field(None, ge=0.0, le=1.0)
    electricity_meters: list[ElectricityMeter] = Field(default_factory=list)
    gas: GasBillFields | None = None
    water: WaterBillFields | None = None
    scada_alarms: list[ScadaAlarm] = Field(default_factory=list)
    raw_warnings: list[str] = Field(default_factory=list)
    parser_path: str = "gemini_vision"
    prompt_version: str = ""

    @model_validator(mode="before")
    @classmethod
    def _coerce_null_lists(cls, data: object) -> object:
        if not isinstance(data, dict):
            return data
        for key in ("electricity_meters", "scada_alarms", "raw_warnings"):
            if data.get(key) is None:
                data[key] = []
        return data
