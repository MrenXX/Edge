# Re·Tech Fusion — Implementation plan (Eco-Edge / ADWYA)

**Purpose:** A new agent or teammate with **no chat history** can read **only this file** (plus the repo spec files the human attaches) and understand scope, priorities, architecture, and scoring alignment.

**Team:** 3 members (challenge allows up to 5). **Product codename:** Eco-Edge.

---

## 0. Read these files first (human provides them in the repo)

| File | What it contains |
|------|------------------|
| [cahier_de_charge.md](cahier_de_charge.md) | Official challenge: Parts 1–3 objectives, **deliverables**, **scoring tables**, deadlines, pitch format. **Authoritative** for points and rules. |
| [rapport_audit.md](rapport_audit.md) | Factory knowledge base: ADWYA pharma context, boilers/cleanrooms/compressors, tri-gen, **waste heat** angles for optional Track B, **quantifiable** numbers for pitch. |
| [example_images_data_factures_et_diverses.md](example_images_data_factures_et_diverses.md) | Shapes of real data: STEG electricity (4 slots, achat/vente), gas NM³/TH, SONEDE m³, SCADA-style alarms. Guides Part 2 extraction and anomalies. |
| [plan_alpha.md](plan_alpha.md) | Earlier **narrative draft** (MQTT, buffer, Streamlit idea). Some hardware text is **outdated**—this `plan.md` **supersedes** hardware and JSON decisions. |
| [grill-me.md](grill-me.md) | Optional process: resolve ambiguous design choices **one question at a time** with the human. |

If any of the above are missing, ask the human to add them before changing challenge-facing behavior.

---

## 1. What hackathon is this (one paragraph)

**Re·Tech Fusion** (INSAT): build an **end-to-end** industrial energy story—**Part 1** continuous IoT telemetry to a server, **Part 2** extract and normalize heterogeneous energy documents to **kWh**, estimate **CO₂**, forecast, optional anomalies, **Dockerized** pipeline + **working dashboard**, **Part 3** either **Track A** (edge ML on device, <200 ms inference) or **Track B** (waste heat recovery design), then **pitch** for top teams. Sponsor narrative: heterogeneous formats, reconciliation, resilience at the edge.

---

## 2. Condensed rubric (from cahier — verify in source file)

**Part 1 (IoT):** functional delivery (30) · multi-sensor coordination (25) · protocol/security incl. reconnect/TLS optional (15) · uptime in 5-min windows (15) · data quality (10) · bonus innovation +15 (e.g. device-side buffering). Prefer **≥3 distinct sensor types** simultaneously with correct units.

**Part 2:** document extraction (40) · unit normalization (25) · CO₂ quality (15) · dashboard (20) · Docker + API docs (20) · optional anomaly +15 · optional innovation +25.

**Part 3 Track A:** model size (15) · latency (10) · prediction MAE (25) · working on hardware (25) · optional multi-sensor model +15.

**Pitch (if selected):** technical depth (35) · scalability/industrial relevance (25).

**Strategy:** depth on high-weight rows; one **coherent demo path** (device → broker → pipeline → dashboard → offline edge) beats disconnected features.

---

## 3. Product story (one sentence)

**ADWYA (pharma)** energy and resilience: live **edge** telemetry (compressor/chiller **proxy** on the bench) + **unified** utility-style documents → **kWh** + **CO₂** on a dashboard; when the network fails, the **ESP32** still **flags / predicts locally** and **syncs a backlog**—aligned with audit themes (gaps in central monitoring, tri-gen/SCADA fragility).

---

## 4. Build order and scope (latest team decisions)

### 4.1 Priority: core Part 1 first

1. **Bring up ESP32 + DS3231 (RTC) + MPU-6050 (I²C)** until readings are stable (timestamps, accel, gyro, temperature).
2. **MQTT** to a broker with a **frozen JSON schema** (section 7).
3. **Reconnect + ring buffer** (innovation / continuity).
4. **Part 3** edge model and LEDs once the loop is reliable.

**Do not block Part 1 on optional hardware.** Optional pieces plug in later (section 8).

### 4.2 Out of scope for v1 (explicit)

| Item | Reason |
|------|--------|
| **HW-072 / lux / any light sensor** | Team dropped this to reduce risk; **not** in BOM, firmware, or JSON. |
| **OTA updates** | Time risk; document as future work if needed. |
| **Second physical device** | Not planned. |
| **Full Track B interactive tool** | Optional thin doc/spreadsheet only if time (section 12). |
| **HTTP transport for telemetry** | MQTT only unless venue blocks it (then revisit). |
| **SONEDE water as kWh** | Water stays a **parallel KPI** (m³/cost), not merged into energy kWh without a defended model. |

### 4.3 Part 1 “three distinct sensor types” (no lux)

All from **one MPU-6050**, documented as **three measurement types** in `edge/README.md` for judges:

1. **Accelerometer** — linear acceleration (e.g. g or m/s² per axis).  
2. **Gyroscope** — angular rate (e.g. °/s per axis).  
3. **Temperature** — MPU die temperature (°C), used as a **thermal** channel.

This satisfies “distinct sensor types” as **three physical quantities** with different units and roles. If a judge interprets “three chips,” the README should state clearly that the rubric examples (IMU, etc.) map to **modalities**, not package count.

---

## 5. Repository layout (monorepo — not one undifferentiated app)

| Path | Responsibility |
|------|----------------|
| `edge/` | ESP32 firmware: MPU, DS3231, MQTT, ring buffer, Part 3 model, LEDs. |
| `pipeline/` | Document extract, normalize to kWh, CO₂, forecast, submissions, API, `Dockerfile`. |
| `dashboard/` | UI only (e.g. Streamlit): pipeline HTTP + live MQTT; **no** document parsing here. |
| **Root** | `README.md`, `docker-compose.yml`, demo script, optional `DECISIONS.md` for overrides. |

---

## 6. Locked technical defaults (implement unless `DECISIONS.md` says otherwise)

| Topic | Decision |
|-------|----------|
| Transport | **MQTT** topic pattern `telemetry/{device_id}` (Mosquitto, often in Docker). |
| Timestamps | **DS3231** is the authority for the JSON `timestamp`; **sync from NTP** when Wi-Fi works, then write RTC. Document timezone (e.g. Africa/Tunis). |
| Broker / TLS | **Mosquitto in docker-compose** on demo laptop; add **MQTTS** (self-signed) if time before Part 1 deadline, else plain MQTT + README “TLS roadmap.” |
| Part 2 extraction | **Hybrid:** structured parsers for Excel/PDF text where possible; **OCR + rules** for scans; **LLM vision** only as pinned fallback (model + prompt version in repo). |
| Compose | `docker compose up` brings **broker + pipeline API** (+ optional DB); dashboard in compose or documented “run on host” on same network. |
| Part 3 | **Track A** primary. **Track B** only as thin appendix if Part 2 mandatory path is done (section 12). |
| Edge ML | **Edge Impulse or TFLite Micro** + a **small forecaster** (e.g. AR/linear on ‖accel‖ or temp) for **MAE**; log **latency ms** and **model KB**. |
| Demo | Assign **Demo Captain** (compose, HDMI) and **Submit Captain** (GitHub/platform); **hotspot backup** for Wi-Fi. |

---

## 7. MQTT JSON schema (v1 — no lux)

- Publish every **~2 s** (jitter OK if documented).  
- **Never** use `0` for “missing” current—use **`null`** or omit the key (pick one convention and keep it).

```json
{
  "timestamp": "2026-05-02T03:45:12.710+01:00",
  "device_id": "ADWYA-CHILLER-01",
  "sensors": {
    "accel_x_g": 0.04,
    "accel_y_g": -0.01,
    "accel_z_g": 1.02,
    "gyro_x_dps": 0.0,
    "gyro_y_dps": 0.0,
    "gyro_z_dps": 0.0,
    "temp_c": 35.5,
    "current_amps": null
  },
  "edge_anomaly": false,
  "meta": { "fw": "1.0.0", "uptime_s": 12345 }
}
```

When ACS712 is wired and calibrated, set **`current_amps`** to a float; firmware can use a compile flag `FEATURE_CURRENT` or runtime detection so **one codebase** supports both lab builds.

### LEDs (suggested)

- **Green:** MQTT connected and backlog empty.  
- **Red:** `edge_anomaly == true` **or** non-empty offline backlog.

### Part 1 README (submission requirement)

Photo/wiring, **units** for every field, broker host/topic, how to run a **5-minute soak**, reconnect + **buffer drain** behavior, list of **three sensor types** as above.

---

## 8. Optional current sensor (ACS712) — modular add-on

**Goal:** Implement current **in isolation** when cables + sensor exist; **no redesign** of Part 2 when it is missing.

| Layer | Rule |
|-------|------|
| **Firmware** | Read ADC only when feature enabled / pins defined; else **`current_amps`: `null`** (or omit key). Do not send fake zeros. |
| **Pipeline** | Ingest MQTT as optional field; **no** requirement for current on CO₂ or bill normalization paths. |
| **Dashboard** | Show a **current** chart or card **only if** recent messages have non-null current; else show **“Current sensor not installed”** or hide the panel. |

This is intentionally **additive**: turning the sensor on only fills data; it does not change dashboard layout contracts beyond one optional block.

---

## 9. Part 2 — Pipeline and dashboard (summary)

- **Ingest:** `DATASET_ROOT` env for hackathon dataset; optional MQTT subscriber stores IoT time series for merge with document timestamps.  
- **Extract:** STEG electricity (4 slots, achat/vente, indices), gas NM³/TH/PCS, SONEDE m³ + fees (parallel KPI), alarms if present—see example data doc.  
- **Normalize:** canonical **kWh**; **TH → kWh** commonly ×**1.163** unless bill states otherwise (document in code). Separate **grid vs gas** CO₂ factors in config.  
- **Forecast:** simple short-term model acceptable if documented.  
- **Docker (20 pts):** cold `docker compose up --build`, `GET /health`, documented batch/ingest and `GET /unified` (or equivalent) for the dashboard.  
- **Dashboard:** doc KPIs, optional 4-slot / tri-gen story for innovation, **live IoT strip**, optional anomaly list.

---

## 10. Part 3 — Track A (edge)

- **On-device** model under RAM/flash limits; **average inference <200 ms** (log on serial).  
- **MAE / ratio** as per organizer method—train/eval with held-out sequences; tiny **predictor + residual** anomaly is safer than clustering-only.  
- **Demo:** Wi-Fi off → local anomaly + LED → reconnect → **buffer flush**.  
- **Bonus +15:** multi-output model (e.g. ‖accel‖ + temp).

---

## 11. Pitch (if team qualifies)

8 min: problem, architecture, key trade-offs, what you’d do with more time. 7 min Q&A.  
**Live line:** device → broker → pipeline → dashboard → **cable pull** → edge still alerts.  
Use **audit numbers** with explicit assumptions (money/CO₂); admit **failures and fixes** (jury credibility).

---

## 12. Optional Track B (thin only)

If Part 2 core is done: `docs/heat_recovery.md` (or similar) + **three** scenarios grounded in [rapport_audit.md](rapport_audit.md) (compressors heat, tri-gen loss, boiler stack/purge). Link from dashboard. **Not** a second full product.

---

## 13. Timeline (from cahier — confirm times in source)

| Gate | Typical hackathon time | “Done” definition |
|------|-------------------------|-------------------|
| Part 1 | Day 2 ~14:00 | Stable MQTT, README, buffer, **accel+gyro+temp** live. |
| Part 2 | Day 3 ~00:00 | Extract + norm + CO₂ + dashboard + compose + demo assets. |
| Part 3 | Day 3 ~05:00 | Edge evidence: size, latency, local anomaly without cloud. |
| Presentation | Day 3 morning | Deck/video per rules. |
| Pitch | Day 3 ~09:00+ | Dry-run completed once. |

---

## 14. Three-person split

| Person | Owns |
|--------|------|
| **Edge** | `edge/`, I²C bring-up, RTC, MQTT, buffer, LEDs, Edge Impulse + forecaster glue. |
| **Pipeline** | `pipeline/`, extractors, kWh, CO₂, Docker, platform JSON submissions. |
| **UI / ML** | `dashboard/`, compose wiring, latency/MAE measurement scripts, pitch deck. |

**Daily:** ~30 min joint—broker IP, schema version, `docker compose up`.

---

## 15. Success checklist (binary)

- [ ] MQTT JSON received in >90% of self-test 5-minute windows.  
- [ ] README lists **three types**: accel, gyro, temp (units + wiring photo).  
- [ ] Reconnect + **ring buffer drain** visible in log.  
- [ ] `docker compose up` + documented API.  
- [ ] ≥1 document family through extract → kWh.  
- [ ] Dashboard: **bills + live IoT** (optional current UI gated on non-null).  
- [ ] Edge: anomaly with Wi-Fi off + inference **<200 ms** logged.  
- [ ] Pitch dry-run including **Wi-Fi fail** demo.

---

## 16. Contradictions resolved (for agents reading old docs)

| Old text | This plan |
|----------|-----------|
| [plan_alpha.md](plan_alpha.md) Scenario B: only vibration + temp, or drop HW-072 | **Invalid for rubric:** must include **gyro** (or a third modality). **Lux dropped entirely.** |
| plan_alpha: LLM-only for all scans | Prefer **hybrid** for reproducibility and Docker (section 6). |
| plan_alpha: K-means only for Part 3 | Add **small predictor** for MAE row (section 10). |

---

*End of implementation plan. Challenge details and point formulas: always re-check [cahier_de_charge.md](cahier_de_charge.md).*
