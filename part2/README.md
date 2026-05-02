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

5. **Pipeline (`part2/pipeline/`)** — `energy_extract` CLI uses Gemini (see `pipeline/README.md`) to turn PDF bills into structured JSON; optional **`ConversionEngine`** + `config/conversions.yaml` normalizes gas TH → kWh, etc.

---

## Run locally (quick)

| Step | Command / URL |
|------|----------------|
| Merge API | `cd part2/mqtt_merge` → copy `.env.example` to `.env` if needed → `python -m uvicorn main:app --host 127.0.0.1 --port 8000` |
| Dashboard | `cd part2/dashboard` → `python -m streamlit run app.py` → open the URL Streamlit prints (often `http://127.0.0.1:8501`) |
| Docker merge | `cd part2/mqtt_merge` → `docker compose up --build` (API on host port **8000**) |

In the dashboard **sidebar**, set **MQTT merge API base URL** to match where uvicorn listens (same machine: `http://127.0.0.1:8000`). Start **Wokwi** with the root `diagram.json` + `sketch.ino` so publishes hit the same broker/topic as the merge service.

---

## Repo layout (Part 2)

| Path | Role |
|------|------|
| [`plan_part2.md`](plan_part2.md) | Architecture, rubric, checklist vs cahier |
| [`explain.md`](explain.md) | JSON contract for the UI, `out/` layout |
| [`example_images_data_factures_et_diverses.md`](example_images_data_factures_et_diverses.md) | Sample bill / SCADA shapes for prompts |
| `dashboard/` | Streamlit app, hybrid styling, MQTT rail |
| `mqtt_merge/` | FastAPI + paho-mqtt + SQLite |
| `pipeline/` | Extraction CLI, `out/*.json`, conversions |

**Also at repo root:** [`cahier_de_charge.md`](../cahier_de_charge.md), [`plan.md`](../plan.md), Part 1 [`README.md`](../README.md).

---

## Branch `part-2`

Git branch **`part-2`** is the line of development that adds and integrates the above. Use **`version`** in `/health` to confirm the merge service matches this README (e.g. `1.0.1`).
