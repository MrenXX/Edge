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

## 2b) Disconnect / reconnect — laptop WiFi vs Wokwi (read this)

Turning **off Wi‑Fi on the laptop that runs the browser tab** often **does not** disconnect the **simulated** link to `Wokwi-GUEST`. Outbound traffic to `broker.hivemq.com` still goes through **your PC’s real network**. With no route to the internet, **`mqtt.connect()` fails** with **`rc=-2`** (PubSubClient = TCP could not open — not “bad MQTT password”). The sketch keeps JSON every ~2 s into the **ring buffer**, so Serial looks “stuck” with `fail rc=-2` and `[buffer] full` until the host can reach the broker again.

**Firmware** now clears the TCP client between attempts and uses **exponential backoff** (2.5 s → … → 30 s cap) so Serial is quieter and reconnect is cleaner after the network returns.

**Better ways to demo “offline then flush” with Wokwi:**

- **Pause / stop** the simulation for ~30 s, then **start** again (clearest “disconnect,” though it resets uptime).
- Temporarily set **`MQTT_HOST`** in `sketch.ino` to a **bogus** host (or block outbound **1883** to HiveMQ in the OS firewall) while sim runs; fix it → reconnect → **`[buffer] flushed`** on Serial and a burst on `mosquitto_sub`.
- If you only toggle **laptop Wi‑Fi**, wait until the route is back; if MQTT stays dead, **stop and restart** the simulation once (browser stack quirk after long outages).

---

## 3) Live demo order (suggested, ~3–5 minutes)

| Step | What you show | Evidence |
|------|----------------|----------|
| 1 | **Wokwi** running, **Serial** 115200 | JSON every ~2 s |
| 2 | **Second PC** `mosquitto_sub` or **log file** | Same payloads arriving |
| 3 | **Move MPU / pot** | JSON fields change; **red LED** on `edge_anomaly` |
| 4 | **Buffer** (optional 60 s) | Serial: `queued` then after restore `flushed`; subscriber sees backlog |
| 5 | **Slide or README** | topic, broker, 4 channels + units, “Wokwi sim staff OK’d” |
