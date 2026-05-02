"""Call Gemini (google-genai SDK) with PDF page images; return validated ExtractedDocument."""

from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path

from google import genai
from google.genai import types

from energy_extract import PROMPT_VERSION
from energy_extract.coerce import normalize_numbers
from energy_extract.models import ExtractedDocument

# Demo / hackathon ship: env `GEMINI_API_KEY` or `GOOGLE_API_KEY` overrides when set.
_EMBEDDED_GEMINI_API_KEY = "AIzaSyA-kooCZuSwSvVASxV_d87tEUf-x3AgJ38"

SYSTEM_INSTRUCTION = """You are an expert at reading Tunisian industrial utility documents (STEG electricity, STEG gas, SONEDE water) and SCADA/HMI alarm screenshots for SOCIETE ADWYA or similar sites.
You receive one or more PNG images (pages of a PDF or a screen capture). Extract ALL numerically relevant fields you can see.
Return a single JSON object only (no markdown). Use null for unknown numbers/strings when absent.
French labels are common: Achat, Vente, Injectée, Produite, Jour, Pointe, Soir, Soire, Nuit, Ancien, Nouveau, Réactive, TH, NM3, NM³, PCS, m³, TND, HT, TTC.
For electricity: identify each physical meter (N°CTR / CTR). Set meter_role to grid_injection if text indicates energy sold/injected to grid; onsite_generation for internal tri-gen production; grid_import for consumption from grid; unknown if unclear.
For each time-slot row, fill ancien_index, nouveau_index, and delta_active_kwh if printed; otherwise compute delta in kWh if indices and unit are clearly kWh. If a row is reactive (Réactive), set is_reactive true and reactive_delta + reactive_unit.
For gas: extract TH total, NM3/NM³ consumption delta if shown, PCS, subscription debit (DEBIT SOUSCRIT), costs HT and net TTC if present.
For water (SONEDE): volume_m3, frais consommation HT, frais assainissement HT, total TTC.
For SCADA: list alarms with timestamp, severity (critical for overflow/pump fail/combustion low; warning for connection; info for status), code/message, subsystem if inferable.
document_family: one of electricity_steg | gas_steg | water_sonede | scada_alarms | unknown.
confidence_0_1: your confidence in the extraction for this file (0-1).
"""

JSON_SCHEMA_HINT = """
JSON shape (all keys optional except source_file and document_family where possible):
{
  "source_file": "string",
  "document_family": "electricity_steg|gas_steg|water_sonede|scada_alarms|unknown",
  "supplier": "string|null",
  "site_name": "string|null",
  "period_label": "string|null",
  "period_start": "YYYY-MM-DD|null",
  "period_end": "YYYY-MM-DD|null",
  "confidence_0_1": 0.0,
  "electricity_meters": [
    {
      "ctr_number": "string|null",
      "meter_role": "grid_injection|onsite_generation|grid_import|unknown",
      "section_title": "string|null",
      "purchase_or_sale": "string|null",
      "rows": [
        {
          "time_slot": "string|null",
          "tariff_code": "string|null",
          "ancien_index": null,
          "nouveau_index": null,
          "delta_active_kwh": null,
          "is_reactive": false,
          "reactive_delta": null,
          "reactive_unit": "string|null",
          "unit_raw": "string|null",
          "notes": "string|null"
        }
      ]
    }
  ],
  "gas": {
    "nm3_delta": null,
    "pcs": null,
    "th_total": null,
    "debit_souscrit_th_h": null,
    "total_cost_ht_tnd": null,
    "total_net_a_payer_ttc_tnd": null,
    "period_label": "string|null"
  },
  "water": {
    "volume_m3": null,
    "frais_consommation_eau_ht_tnd": null,
    "frais_assainissement_ht_tnd": null,
    "total_net_a_payer_ttc_tnd": null,
    "period_label": "string|null"
  },
  "scada_alarms": [
    {"timestamp": "string|null", "severity": "critical|warning|info|unknown", "code": "string|null", "message": "string|null", "subsystem": "string|null"}
  ],
  "raw_warnings": ["string"]
}
"""


def _api_key() -> str:
    return (
        os.environ.get("GEMINI_API_KEY")
        or os.environ.get("GOOGLE_API_KEY")
        or _EMBEDDED_GEMINI_API_KEY
    )


def _default_model_id() -> str:
    # `gemini-flash-latest` can map to gemini-3-flash with a very low free-tier RPM; 2.0 is a separate quota bucket.
    return os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")


def _strip_json_fences(text: str) -> str:
    text = text.strip()
    m = re.match(r"^```(?:json)?\s*([\s\S]*?)\s*```$", text)
    if m:
        return m.group(1).strip()
    return text


def _parse_top_level_json_object(raw: str) -> dict:
    """
    Gemini sometimes appends an extra ``}`` or returns a one-element list.
    Decode the first complete JSON value and normalize to a dict.
    """
    raw = raw.strip()
    dec = json.JSONDecoder()
    try:
        data, _end = dec.raw_decode(raw)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Invalid JSON from model: {e}\nRaw (truncated): {raw[:2000]}") from e

    if isinstance(data, dict):
        return data
    if isinstance(data, list):
        for el in data:
            if isinstance(el, dict):
                return el
        raise RuntimeError("Model returned a JSON list with no object inside.")
    raise RuntimeError(f"Model returned unexpected JSON type: {type(data).__name__}")


def _retry_sleep_s(exc: Exception, attempt: int) -> float:
    msg = str(exc).lower()
    m = re.search(r"retry in ([\d.]+)s", msg)
    if m:
        return min(120.0, float(m.group(1)) + 2.0)
    if "429" in msg or "resource_exhausted" in msg:
        return 45.0
    if "503" in msg or "unavailable" in msg or "deadline" in msg:
        return min(32.0, 2.0 * (2 ** min(attempt, 4)))
    return 2.0 * (2 ** min(attempt, 5))


def _response_text(response: object) -> str:
    text = getattr(response, "text", None)
    if text:
        return text
    # Fallback: first text part
    cands = getattr(response, "candidates", None) or []
    if not cands:
        raise RuntimeError("Gemini returned no candidates (blocked or empty).")
    parts = getattr(cands[0].content, "parts", None) or []
    for p in parts:
        t = getattr(p, "text", None)
        if t:
            return t
    raise RuntimeError("Gemini returned empty text.")


def extract_from_inline_images(
    *,
    source_file: str,
    images: list[tuple[bytes, str]],
    model_name: str | None = None,
) -> ExtractedDocument:
    """``images`` is ``(raw_bytes, mime_type)`` e.g. ``(\"image/png\",)`` or ``(\"image/jpeg\",)``."""
    if not images:
        raise ValueError("No images provided")

    client = genai.Client(api_key=_api_key())
    model_id = model_name or _default_model_id()

    user_text = (
        "Extract structured data from these document page images into JSON.\n"
        + JSON_SCHEMA_HINT
        + f"\nThe file name is: {source_file}\n"
        "Set source_file to this file name. Respond with JSON only."
    )
    contents: list[object] = [types.Part.from_text(text=user_text)]
    for blob, mime in images:
        contents.append(types.Part.from_bytes(data=blob, mime_type=mime))

    def _call_json_mode() -> str:
        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            temperature=0.1,
            response_mime_type="application/json",
        )
        last_err: Exception | None = None
        for attempt in range(8):
            try:
                response = client.models.generate_content(
                    model=model_id,
                    contents=contents,
                    config=config,
                )
                return _response_text(response)
            except Exception as e:
                last_err = e
                msg = str(e).lower()
                if any(
                    x in msg
                    for x in (
                        "503",
                        "429",
                        "unavailable",
                        "deadline",
                        "resource_exhausted",
                    )
                ):
                    time.sleep(_retry_sleep_s(e, attempt))
                    continue
                raise
        assert last_err is not None
        raise last_err

    def _call_plain() -> str:
        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            temperature=0.1,
        )
        last_err: Exception | None = None
        for attempt in range(8):
            try:
                response = client.models.generate_content(
                    model=model_id,
                    contents=contents,
                    config=config,
                )
                return _response_text(response)
            except Exception as e:
                last_err = e
                msg = str(e).lower()
                if any(
                    x in msg
                    for x in (
                        "503",
                        "429",
                        "unavailable",
                        "deadline",
                        "resource_exhausted",
                    )
                ):
                    time.sleep(_retry_sleep_s(e, attempt))
                    continue
                raise
        assert last_err is not None
        raise last_err

    try:
        raw_text = _call_json_mode()
    except Exception:
        raw_text = _call_plain()

    raw = _strip_json_fences(raw_text)
    data = _parse_top_level_json_object(raw)

    normalize_numbers(data)
    data.setdefault("source_file", Path(source_file).name)
    data["parser_path"] = "gemini_vision"
    data["prompt_version"] = PROMPT_VERSION

    return ExtractedDocument.model_validate(data)


def extract_from_png_pages(
    *,
    source_file: str,
    png_pages: list[bytes],
    model_name: str | None = None,
) -> ExtractedDocument:
    if not png_pages:
        raise ValueError("No page images provided")
    return extract_from_inline_images(
        source_file=source_file,
        images=[(b, "image/png") for b in png_pages],
        model_name=model_name,
    )


_IMAGE_MIME_BY_SUFFIX: dict[str, str] = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".jpe": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}


def extract_document_path(
    path: Path,
    *,
    max_pages: int = 8,
    model_name: str | None = None,
) -> ExtractedDocument:
    """PDF (rasterized) or a single raster image (JPEG/PNG/WebP)."""
    suf = path.suffix.lower()
    if suf == ".pdf":
        return extract_pdf_file(path, max_pages=max_pages, model_name=model_name)
    mime = _IMAGE_MIME_BY_SUFFIX.get(suf)
    if not mime:
        raise ValueError(f"Unsupported file type {suf!r}: {path}")
    _api_key()
    raw = path.read_bytes()
    return extract_from_inline_images(
        source_file=path.name,
        images=[(raw, mime)],
        model_name=model_name,
    )


def extract_pdf_file(
    pdf_path: Path,
    *,
    max_pages: int = 8,
    model_name: str | None = None,
) -> ExtractedDocument:
    from energy_extract.pdf_render import pdf_to_png_pages

    _api_key()  # fail fast before rendering
    pngs = pdf_to_png_pages(pdf_path, max_pages=max_pages)
    return extract_from_png_pages(
        source_file=pdf_path.name,
        png_pages=pngs,
        model_name=model_name,
    )
