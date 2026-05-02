# Edge — Eco-Edge (Re·Tech Fusion Part 1)

Hackathon **Re·Tech Fusion** (INSAT) — **Part 1: IoT device & protocol**.  
Physical ESP32 was unavailable; this repo implements an **approved Wokwi simulation** (virtual ESP32 + real schematic) that publishes the same **MQTT JSON** the Part 2 pipeline expects.

**Remote:** [https://github.com/MrenXX/Edge](https://github.com/MrenXX/Edge)

---

## What’s in this repo

| File | Purpose |
|------|---------|
| [diagram.json](diagram.json) | Wokwi circuit: ESP32 DevKit-C, **MPU6050** (I²C **0x69**, AD0→3V3), **DS1307** RTC (0x68), **potentiometer** on GPIO34, **green LED** GPIO4 / **red** GPIO2 with 220 Ω series resistors |
| [sketch.ino](sketch.ino) | Arduino firmware: sensors → JSON → **MQTT**; **WiFi** `Wokwi-GUEST`; **ring buffer** when offline / publish fail |
| [libraries.txt](libraries.txt) | Wokwi / Arduino Library Manager dependencies |
| [WOKWI.md](WOKWI.md) | Step-by-step: open project, libraries, WiFi, MQTT troubleshooting |
| [LIVE_DEMO.md](LIVE_DEMO.md) | `mosquitto_sub` log commands, buffer demo hint, **live demo script** |
| [plan.md](plan.md) | Full hackathon plan (Parts 1–3 + rubric notes) |
| [cahier_de_charge.md](cahier_de_charge.md) | Official challenge spec (source of rubric) |
| [rapport_audit.md](rapport_audit.md), [example_images_data_factures_et_diverses.md](example_images_data_factures_et_diverses.md) | Factory / dataset context for Part 2 |

---

## Quick start (Wokwi)

1. [wokwi.com](https://wokwi.com) → new **ESP32** project.  
2. Copy **`diagram.json`**, **`sketch.ino`**, **`libraries.txt`** into the project (same folder).  
3. Add libraries from **`libraries.txt`** (or use Wokwi Library Manager).  
4. **Simulate** — Serial **115200** baud.

Details: **[WOKWI.md](WOKWI.md)**.

---

## MQTT configuration (default)

| Setting | Value |
|--------|--------|
| WiFi (browser sim) | SSID `Wokwi-GUEST`, password *(empty)* |
| Broker | `broker.hivemq.com` port **1883** |
| Topic | `telemetry/ADWYA-CHILLER-01` |
| Device ID in JSON | `ADWYA-CHILLER-01` |

To use **your own Mosquitto** on a PC, use [Wokwi Private IoT Gateway](https://docs.wokwi.com/guides/esp32-wifi) and set `MQTT_HOST` in `sketch.ino` to that PC’s LAN IP.

---

## JSON payload (every ~2 s)

One line per publish, UTF-8 JSON:

- **`timestamp`** — from **DS1307** (ISO-like string with `+01:00`; adjust in code if needed)  
- **`device_id`** — `ADWYA-CHILLER-01`  
- **`sensors`:** `accel_x_g`, `accel_y_g`, `accel_z_g` (g), `gyro_x_dps`… (°/s), `temp_c` (°C), `current_amps` (mapped from **ADC pot** 0–20 A proxy)  
- **`edge_anomaly`** — `true` when vibration / gyro / “current” exceeds thresholds (see sketch)  
- **`meta`:** `fw`, `uptime_s`

---

## Ring buffer (Part 1 **bonus innovation** — device-side buffering)

Implemented in [sketch.ino](sketch.ino):

- **8 × 768 byte** FIFO in RAM.  
- **`ringPush`:** MQTT disconnected **or** `publish()` fails → message queued; Serial `[buffer] queued`.  
- **`ringFlush`:** after **MQTT connect** and while connected in `loop()` — publishes **oldest first**; Serial `[buffer] flushed`.  
- If buffer full, **oldest dropped** (`dropped oldest`).

---

## Verify on a second machine (30 pt “server receives data”)

Subscribe (needs [Eclipse Mosquitto](https://mosquitto.org/) client or equivalent):

```bash
mosquitto_sub -h broker.hivemq.com -p 1883 -t 'telemetry/#' -v
```

Log to file (commands for bash / PowerShell / CMD): **[LIVE_DEMO.md](LIVE_DEMO.md)** §1.

---

## Rubric alignment (Part 1 — summary)

| Criterion | How this repo supports it |
|-----------|-----------------------------|
| Delivered & functional | Stable MQTT JSON to a **participant PC** via public broker (or your broker + Private Gateway) |
| Multi-sensor | **Accel, gyro, temp** (MPU6050) + **current proxy** (pot), same payload |
| Protocol | WiFi + MQTT **reconnect**; `mqtt.loop()` around traffic |
| Uptime / continuity | Steady ~2 s cadence + **optional** long `mosquitto_sub` log for 5‑min window evidence |
| Data quality | Plausible ranges; no `-999`; no fake nulls for required numerics |
| Bonus innovation | **RAM ring buffer** + README + demo script |

---

## Live demo — showcase order (~3–5 min)

Use this order in front of jury / camera (full detail: **[LIVE_DEMO.md](LIVE_DEMO.md)** §3).

1. **Wokwi** sim running + **Serial** @ 115200 — show JSON every ~2 s.  
2. **Second laptop** — `mosquitto_sub` (or **log file**) proving same JSON on the network.  
3. **Interact** — change MPU / pot in Wokwi; JSON updates; **red LED** when `edge_anomaly: true`.  
4. **Buffer (optional ~60 s)** — break path / disconnect → Serial `queued` → restore → `flushed` + subscriber burst.  
5. **One slide or README tab** — topic, broker, four channels + units, “Wokwi digital twin / staff-approved sim”.

---

## Build / flash notes

- **Wokwi:** no USB flash; simulate in browser or VS Code extension.  
- **Real ESP32:** same `sketch.ino` targets **GPIO 21/22** I²C, **34** ADC, **4/2** LEDs; copy `diagram.json` wiring to breadboard; set WiFi credentials and broker in code.

---

## License / hackathon

Original team work for Re·Tech Fusion. Third-party libs: **Arduino-ESP32**, **PubSubClient**, **RTClib**, **Adafruit MPU6050**, **Adafruit Unified Sensor** — see each library’s license.
