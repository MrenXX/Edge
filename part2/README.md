# Part 2 — unified documents + live edge telemetry

This branch carries **Part 2** of Eco-Edge (Re·Tech Fusion): bill/SCADA **extraction to JSON**, a **Streamlit** “unified statement” UI, and a small **MQTT merge service** that persists Part 1 **Wokwi / ESP32** telemetry so the dashboard can show **live** readings next to extracted documents.

---

## What is happening (end-to-end)

1. **Part 1 (repo root)** — [`sketch.ino`](../sketch.ino) runs on Wokwi or hardware. Every ~2s it publishes JSON to the public broker **`broker.hivemq.com:1883`**, topic **`telemetry/ADWYA-CHILLER-01`**. Payload includes `timestamp`, `device_id`, `sensors` (accel/gyro/temp/current proxy), `edge_anomaly`, and `meta`.

2. **MQTT merge (`part2/mqtt_merge/`)** — A FastAPI app subscribes to that **exact topic** (not `telemetry/#`, to avoid garbage on HiveMQ). Valid JSON rows are written to **SQLite** (`iot_data.db` next to the service, or path from `MQTT_MERGE_DB_PATH`). Inserts run on a **background writer queue** so the MQTT client thread never blocks on the DB (which previously caused the broker to drop the client after a short burst of messages). SQLite uses **WAL** and a long busy timeout so HTTP reads and MQTT writes coexist cleanly.

3. **HTTP API** — Same process exposes:
   - `GET /health` — MQTT connectivity, DB, **`anomaly_count` / `anomaly_rate`**, `status` (`healthy` / `attention` / `degraded`), **`version`** (e.g. `1.0.1` confirms you are on current code).
   - `GET /unified/iot` — aggregates + recent readings for the dashboard rail.

4. **Streamlit dashboard (`part2/dashboard/`)** — Loads validated extraction JSON from `part2/pipeline/out/*.json` (see [`explain.md`](explain.md)). The right column calls the merge API (default **`http://127.0.0.1:8000`**) on a short interval and shows readings, anomaly rate, and a **recent messages** table.

5. **Unified Part 2 API (`part2/api/`)** — FastAPI service (plan §15) with **`GET /health`**, **`GET /documents`**, **`GET /unified`** (documents + IoT strip + rollups), **`GET /metrics`**, **`POST /ingest`** (Gemini extraction — needs `GOOGLE_API_KEY`), **`/docs`**. It reads JSON from `pipeline/out/` and pulls live IoT aggregates from the **MQTT merge** service over HTTP (`MQTT_MERGE_URL`).

6. **Pipeline (`part2/pipeline/`)** — `energy_extract` CLI uses Gemini (see `pipeline/README.md`) to turn PDF bills into structured JSON; optional **`ConversionEngine`** + `config/conversions.yaml` normalizes gas TH → kWh, etc.

---

## Run locally (quick)

| Step | Command / URL |
|------|----------------|
| **Compose (recommended)** | From **`part2/`**: copy [`.env.example`](.env.example) → `.env`, set `GOOGLE_API_KEY` if you need **`POST /ingest`**, then **`docker compose up --build`**. **Merge** → [http://127.0.0.1:8000](http://127.0.0.1:8000) · **Unified API** → [http://127.0.0.1:8080](http://127.0.0.1:8080) · OpenAPI → [http://127.0.0.1:8080/docs](http://127.0.0.1:8080/docs) |
| Merge only | `cd part2/mqtt_merge` → `python -m uvicorn main:app --host 127.0.0.1 --port 8000` |
| Unified API only | `cd part2` → `$env:PYTHONPATH=".;./pipeline"` (PowerShell) or `export PYTHONPATH=.:./pipeline` → `python -m uvicorn api.main:app --host 127.0.0.1 --port 8080` (merge must be reachable at `MQTT_MERGE_URL`) |
| Dashboard | `cd part2/dashboard` → `python -m streamlit run app.py` → open the URL Streamlit prints (often `http://127.0.0.1:8501`) |

Compose mounts **`./pipeline/out` → `/data/out`** (read/write extraction JSON), **`./data/incoming`** uploads, **`./data/pdfs`** for batch ingest. Optional **Mosquitto** remains available via [`mqtt_merge/docker-compose.yml`](mqtt_merge/docker-compose.yml) profiles if you switch the firmware off public HiveMQ.

In the dashboard **sidebar**, keep the **MQTT merge** base URL at **`http://127.0.0.1:8000`** when compose exposes both ports; wire the **unified** `GET /unified` to **`http://127.0.0.1:8080`** when you integrate the new frontend.

---

## Repo layout (Part 2)

| Path | Role |
|------|------|
| [`plan_part2.md`](plan_part2.md) | Architecture, rubric, checklist vs cahier |
| [`explain.md`](explain.md) | JSON contract for the UI, `out/` layout |
| [`example_images_data_factures_et_diverses.md`](example_images_data_factures_et_diverses.md) | Sample bill / SCADA shapes for prompts |
| `dashboard/` | Streamlit (disk JSON + **drag-and-drop Gemini OCR**); install `dashboard/requirements.txt` for live upload |
| `api/` | Unified FastAPI: `/unified`, `/documents`, `/ingest`, `/metrics`, `/docs` |
| `mqtt_merge/` | FastAPI + paho-mqtt + SQLite (telemetry persistence) |
| `pipeline/` | Extraction CLI, `out/*.json`, conversions |
| [`docker-compose.yml`](docker-compose.yml) | **mqtt_merge** + **api** (§15 cold start) |

**Also at repo root:** [`cahier_de_charge.md`](../cahier_de_charge.md), [`plan.md`](../plan.md), Part 1 [`README.md`](../README.md).

---

## Branch `part-2`

Git branch **`part-2`** is the line of development that adds and integrates the above. Use **`version`** in `/health` to confirm the merge service matches this README (e.g. `1.0.1`).
