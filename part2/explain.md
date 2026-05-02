# Part 2 extraction → frontend handoff (`explain.md`)

This document is for the **dashboard / frontend** agent: where structured bill data lives today, the **JSON contract**, and **real outputs** from successful PDF runs (hackathon path: Gemini vision → one JSON file per source document).

There is **no HTTP API for extraction yet** (FastAPI `/ingest` / `/unified` from [plan_part2.md](plan_part2.md) is still to-do). Until then, the UI should treat **`part2/pipeline/out/*.json`** as the backend result surface (static files, copy into `public/`, or serve via a tiny static file server / future API).

---

## 1) How results are produced today

| Step | What runs | Output |
|------|-----------|--------|
| Batch PDFs in folder | `python -m energy_extract` from [part2/pipeline](pipeline/README.md) | One `*.json` per PDF under [part2/pipeline/out/](pipeline/out/) + append-only [part2/pipeline/out/extraction_audit.jsonl](pipeline/out/extraction_audit.jsonl) |
| Explicit files (PDF / JPEG / …) | `python -m energy_extract --files path1 path2 … --parallel 3` | Same layout under `--out-dir` (e.g. `out_whatsapp/`) |

**Source of truth for field names / types:** Pydantic models in [part2/pipeline/energy_extract/models.py](pipeline/energy_extract/models.py).

**Extraction implementation:** [part2/pipeline/energy_extract/gemini_extract.py](pipeline/energy_extract/gemini_extract.py) (Gemini → JSON → validate).

**CLI entry:** [part2/pipeline/energy_extract/cli.py](pipeline/energy_extract/cli.py).

**Product / rubric context:** [part2/plan_part2.md](plan_part2.md), official [cahier_de_charge.md](../cahier_de_charge.md).

**Live IoT (Part 1) for unified dashboard:** MQTT JSON from [sketch.ino](../sketch.ino), documented in [README.md](../README.md) — separate stream; merge in UI or future `/unified` API per plan.

---

## 2) Top-level JSON contract (per document)

Each successful run writes **one file**: `out/<original_basename_without_ext>.json`.

Common keys (see `ExtractedDocument` in [models.py](pipeline/energy_extract/models.py)):

| Field | Type | Notes |
|-------|------|--------|
| `source_file` | string | Original filename |
| `document_family` | string | `gas_steg` \| `electricity_steg` \| `water_sonede` \| `scada_alarms` \| `unknown` |
| `supplier`, `site_name`, `period_label`, `period_start`, `period_end` | string or null | |
| `confidence_0_1` | number or null | 0–1 |
| `electricity_meters` | array | STEG electricity; empty `[]` for gas-only docs |
| `gas` | object or null | Gas bill block |
| `water` | object or null | SONEDE-style block |
| `scada_alarms` | array | Alarm rows; empty if N/A |
| `raw_warnings` | array of strings | |
| `parser_path` | string | e.g. `gemini_vision` |
| `prompt_version` | string | e.g. `gemini_vision_v1` |

**UI routing:** branch on `document_family`, then render `gas`, `electricity_meters`, `water`, or `scada_alarms` panels. `gas` and `water` may be `null` on non-matching docs.

### Gas block (`gas_steg`)

Fields on `gas` object (`GasBillFields` in models):

- `nm3_delta`, `pcs`, `th_total`, `debit_souscrit_th_h`
- `total_cost_ht_tnd`, `total_net_a_payer_ttc_tnd`, `period_label`

### Electricity (`electricity_steg`)

`electricity_meters[]` each has:

- `ctr_number` (string), `meter_role` (`grid_import` \| `grid_injection` \| `onsite_generation` \| …), `section_title`, `purchase_or_sale`
- `rows[]`: `time_slot`, `tariff_code`, `ancien_index`, `nouveau_index`, `delta_active_kwh`, reactive flags, etc.

### Audit log (optional for UI “ingestion status”)

[part2/pipeline/out/extraction_audit.jsonl](pipeline/out/extraction_audit.jsonl): **one JSON object per line**, fields like `ok`, `source_file`, `document_family`, `output_json`, `error`, `detail`, `ts`.

---

## 3) Example outputs (successful PDF runs — copy into UI mocks)

These four files are committed under [part2/pipeline/out/](pipeline/out/) from working extractions.

### 3.1 Gas — [part2/pipeline/out/data 2.0.json](pipeline/out/data%202.0.json)

```json
{
  "source_file": "data 2.0.pdf",
  "document_family": "gas_steg",
  "supplier": "STEG",
  "site_name": "SIDI DAOUD 2046",
  "period_label": "05/2025",
  "confidence_0_1": 0.95,
  "electricity_meters": [],
  "gas": {
    "nm3_delta": 177851.0,
    "pcs": 10.083,
    "th_total": 1793272.0,
    "debit_souscrit_th_h": 6000.0,
    "total_cost_ht_tnd": 111064.21,
    "total_net_a_payer_ttc_tnd": 134408.0,
    "period_label": "05/2025"
  },
  "water": null,
  "scada_alarms": [],
  "parser_path": "gemini_vision",
  "prompt_version": "gemini_vision_v1"
}
```

### 3.2 Gas — [part2/pipeline/out/data faxtuees.json](pipeline/out/data%20faxtuees.json)

```json
{
  "source_file": "data faxtuees.pdf",
  "document_family": "gas_steg",
  "supplier": "STEG",
  "site_name": "SOCIETE ADWYA",
  "period_label": "01/2026",
  "confidence_0_1": 0.98,
  "electricity_meters": [],
  "gas": {
    "nm3_delta": 235633.0,
    "pcs": 10.158,
    "th_total": 2393560.0,
    "debit_souscrit_th_h": 6000.0,
    "total_cost_ht_tnd": 148162.008,
    "total_net_a_payer_ttc_tnd": 179304.74,
    "period_label": "01/2026"
  },
  "water": null,
  "scada_alarms": [],
  "parser_path": "gemini_vision",
  "prompt_version": "gemini_vision_v1"
}
```

### 3.3 Electricity (truncated) — [part2/pipeline/out/doc 2.json](pipeline/out/doc%202.json)

Full file is large (multiple meters and slots). Shape:

- `document_family`: `"electricity_steg"`
- `electricity_meters`: array of meters with `ctr_number`, `meter_role` (e.g. `grid_import`, `grid_injection`, `onsite_generation`), `rows` for Jour / Pointe / Nuit / Soire / Réactive, etc.

Open the linked file for the complete nested structure used by the jury demo.

### 3.4 Electricity (truncated) — [part2/pipeline/out/fiche releve donne .json](pipeline/out/fiche%20releve%20donne%20.json)

Same schema as §3.3; `period_label` example: `"novembre-25"`. Use the file on disk for full meters/rows.

---

## 4) What the frontend agent should implement (minimal)

1. **Load** all `*.json` from the agreed directory (today: `part2/pipeline/out/`, or copy them into the dashboard app as fixtures).
2. **Parse** each file as the schema above; handle `null` for `gas` / `water`.
3. **Cards / tables:**
   - Gas KPIs: TH, NM³, PCS, HT, TTC, period.
   - Electricity: per meter TOU table + role badge (`grid_injection` vs `grid_import` vs `onsite_generation`).
4. **Optional:** read `extraction_audit.jsonl` for a simple “last run” status table (success/fail per file).
5. **Later:** replace directory reads with `GET /documents` / `GET /unified` once the FastAPI layer exists ([plan_part2.md](plan_part2.md) §15).

**Streamlit UI (reads `out/*.json` today):** `pip install -r part2/dashboard/requirements.txt` then `python -m streamlit run part2/dashboard/app.py` from the repo root (or `cd part2/dashboard` then `python -m streamlit run app.py`). Under PowerShell use `;` instead of `&&` between commands. Sidebar: path to `out/`, MQTT merge API URL (default `http://127.0.0.1:8000`). Layout uses the hybrid palette (`#BBAB8C` / `#776B5D` / `#282A3A`): sand main column, **dark ink rail only** for live telemetry.

**MQTT merge + normalization (from branches `part2-mqtt-merge` / `step11`, integrated under `part2/`):**

- **MQTT FastAPI + SQLite:** `part2/mqtt_merge/` — `GET /health`, `/readings`, `/anomalies`, `/unified/iot`. Defaults: **`broker.hivemq.com:1883`**, subscribe **`telemetry/ADWYA-CHILLER-01`** (device-only topic; avoids invalid JSON from other clients on `telemetry/#`). Run: `cd part2/mqtt_merge && uvicorn main:app --host 0.0.0.0 --port 8000` (install `part2/mqtt_merge/requirements.txt`), or `docker compose -f part2/mqtt_merge/docker-compose.yml up --build`. Then Streamlit sidebar → **MQTT merge API** = `http://127.0.0.1:8000` (HTTP, not 1883); enable auto-refresh for live rail.
- **kWh normalization:** `part2/pipeline/config/conversions.yaml` + `part2/pipeline/core/conversion_engine.py` (PyYAML). The dashboard uses this for **canonical kWh** on gas bills and TH vs NM³×PCS checks when all fields exist.

---

## 5) File index (quick links)

| Path | Role |
|------|------|
| [part2/explain.md](explain.md) | This handoff doc |
| [part2/plan_part2.md](plan_part2.md) | Full Part 2 plan + dashboard merge story |
| [part2/pipeline/README.md](pipeline/README.md) | How to run extraction CLI |
| [part2/pipeline/energy_extract/models.py](pipeline/energy_extract/models.py) | JSON schema (Pydantic) |
| [part2/pipeline/energy_extract/cli.py](pipeline/energy_extract/cli.py) | CLI flags (`--files`, `--parallel`, …) |
| [part2/pipeline/out/](pipeline/out/) | Example successful JSON outputs |
| [part2/pipeline/out/extraction_audit.jsonl](pipeline/out/extraction_audit.jsonl) | Per-file run log |
| [part2/dashboard/app.py](dashboard/app.py) | Streamlit extraction viewer |
| [part2/dashboard/requirements.txt](dashboard/requirements.txt) | `streamlit`, `pandas`, `pydantic`, `requests` |
| [part2/mqtt_merge/](mqtt_merge/) | MQTT → SQLite → FastAPI (`/unified/iot`) |
| [part2/pipeline/core/conversion_engine.py](pipeline/core/conversion_engine.py) | TH/NM³ → kWh (`conversions.yaml`) |
| [README.md](../README.md) | Part 1 MQTT / topic for live strip |
| [sketch.ino](../sketch.ino) | Telemetry JSON fields |

---

*End of explain.md — link this file plus `part2/pipeline/out/*.json` into the frontend agent context.*
