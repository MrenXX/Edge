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

## 2) Ring buffer (bonus)

In [sketch.ino](sketch.ino): **8 × 768 byte** ring. MQTT down or `publish()` fails → line goes to RAM, Serial prints `[buffer] queued`. After link back, `ringFlush()` spits oldest first → `[buffer] flushed`.

Quick demo: kill path / wait for drops → `queued` → bring it back → burst on `mosquitto_sub`.

---

## 3) Live demo order (suggested, ~3–5 minutes)

| Step | What you show | Evidence |
|------|----------------|----------|
| 1 | **Wokwi** running, **Serial** 115200 | JSON every ~2 s |
| 2 | **Second PC** `mosquitto_sub` or **log file** | Same payloads arriving |
| 3 | **Move MPU / pot** | JSON fields change; **red LED** on `edge_anomaly` |
| 4 | **Buffer** (optional 60 s) | Serial: `queued` then after restore `flushed`; subscriber sees backlog |
| 5 | **Slide or README** | topic, broker, 4 channels + units, “Wokwi sim staff OK’d” |

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
