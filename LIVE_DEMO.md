# Live demo + evidence (Part 1) — fast checklist

## 1) Log MQTT JSON to a file (another PC)

**Linux / macOS (bash)** — log only:

```bash
mosquitto_sub -h broker.hivemq.com -p 1883 -t 'telemetry/#' -v > ecoedge_telemetry.log 2>&1
```

**Linux / macOS** — watch terminal **and** log:

```bash
mosquitto_sub -h broker.hivemq.com -p 1883 -t 'telemetry/#' -v 2>&1 | tee ecoedge_telemetry.log
```

**Windows PowerShell** — log only:

```powershell
mosquitto_sub -h broker.hivemq.com -p 1883 -t 'telemetry/#' -v *> ecoedge_telemetry.log
```

**Windows CMD** — log only:

```cmd
mosquitto_sub -h broker.hivemq.com -p 1883 -t telemetry/# -v > ecoedge_telemetry.log 2>&1
```

- Start logging **before** the jury window / soak test; note **start time** on screen (phone photo or OS clock).
- For **uptime / 5‑minute windows**, keep the log running **≥30–60 minutes** if possible; you can later count lines per 5‑minute bucket (spreadsheet is enough).

---

## 2) What changed in firmware (bonus buffer)

[sketch.ino](sketch.ino) now has a **small RAM ring (8 × 768 bytes)**:

- If **MQTT is disconnected** or **`publish()` fails**, the JSON line is **`[buffer] queued`** instead of dropped.
- On **reconnect**, **`ringFlush()`** publishes **oldest first**; Serial shows **`[buffer] flushed`**.

**Demo stunt (30–60 s):** pause/stop internet path (or disconnect broker side if you control it) → watch Serial for `queued` → restore → watch `flushed` and subscriber catching burst + live lines.

---

## 3) Live demo order (suggested, ~3–5 minutes)

| Step | What you show | Evidence |
|------|----------------|----------|
| 1 | **Wokwi** running, **Serial** 115200 | JSON every ~2 s |
| 2 | **Second PC** `mosquitto_sub` or **log file** | Same payloads arriving |
| 3 | **Move MPU / pot** | JSON fields change; **red LED** on `edge_anomaly` |
| 4 | **Buffer** (optional 60 s) | Serial: `queued` then after restore `flushed`; subscriber sees backlog |
| 5 | **README / slide** | Topic, broker, “Wokwi + staff-approved sim”, **four sensor channels** + units |

---

## 4) Git backup / push

Remote: **https://github.com/MrenXX/Edge**

```bash
git add .
git status
git commit -m "Part1: Wokwi MQTT, ring buffer, docs"
git push -u origin main
```

First-time setup (if clone empty):

```bash
git init
git branch -M main
git remote add origin https://github.com/MrenXX/Edge.git
git add .
git commit -m "Initial: Part 1 Wokwi + docs"
git push -u origin main
```

`git push` requires GitHub auth (HTTPS token or SSH key).
