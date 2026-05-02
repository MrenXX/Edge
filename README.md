# Edge — Eco-Edge (Re·Tech Fusion Part 1)

INSAT **Re·Tech Fusion** — Part 1 (IoT + protocol). Real board died mid-prep; we run the same firmware in **Wokwi** and ship JSON over MQTT so Part 2 can still ingest it.

Repo: [github.com/MrenXX/Edge](https://github.com/MrenXX/Edge)

---

## Files

| File | What it is |
|------|------------|
| [diagram.json](diagram.json) | Wokwi: ESP32 DevKit-C, MPU6050 @ **0x69** (AD0→3V3), DS1307, pot → GPIO34, green LED 4 / red 2 + 220Ω |
| [sketch.ino](sketch.ino) | Arduino: read sensors, build JSON, MQTT; small ring buffer if broker drops |
| [libraries.txt](libraries.txt) | Library names for Wokwi / Arduino |
| [WOKWI.md](WOKWI.md) | How to open sim, fix libs, WiFi/MQTT gotchas |
| [LIVE_DEMO.md](LIVE_DEMO.md) | `mosquitto_sub`, logging to disk, demo order |
| [plan.md](plan.md) | Rest of hackathon (P2/P3) — still the master plan |
| [cahier_de_charge.md](cahier_de_charge.md) | Official spec |
| [rapport_audit.md](rapport_audit.md), [example_images_data_factures_et_diverses.md](example_images_data_factures_et_diverses.md) | ADWYA context for later parts |

---

## Wokwi quick run

1. [wokwi.com](https://wokwi.com) → new ESP32 project  
2. Drop in `diagram.json`, `sketch.ino`, `libraries.txt`  
3. Add libs (see `libraries.txt` or WOKWI)  
4. Simulate, Serial **115200**

More detail: [WOKWI.md](WOKWI.md)

---

## Hardware and wiring

Everything below matches [diagram.json](diagram.json) (Wokwi) so the **sim and a real breadboard** are the same story: one **ESP32 DevKit-C** as the controller, **3V3** and **GND** as the rails.

**I²C bus (shared)** — **GPIO21 = SDA**, **GPIO22 = SCL**. Two slaves on the same pair of wires:

| Part | Role | Power | Notes |
|------|------|-------|--------|
| **MPU6050** | accel + gyro + die temp | VCC→3V3, GND→GND | **AD0 → 3V3** so the chip answers at **0x69** (sketch matches). |
| **DS1307** RTC | wall-clock for JSON `timestamp` | **5V pin** tied to **3V3** in the sim (same as diagram); GND common; SDA/SCL as above. Address **0x68**. |

**Potentiometer (load proxy)** — one end **3V3**, the other **GND**, **wiper → GPIO34**. That pin is **ADC-only** on the ESP32 (good for a voltage divider read). Firmware maps the reading to **0–20 A** for demo, not a true shunt.

**LEDs (status)** — each LED needs a **220 Ω** resistor in series so the GPIO does not source too much current:

- **Green:** **GPIO4** → resistor → LED **anode (+)** → LED **cathode (−)** → **GND**. **On** when **WiFi and MQTT** are both up; **off** if either drops.  
- **Red:** **GPIO2** → resistor → LED **anode** → **cathode** → **GND**. **On** when **`edge_anomaly`** is true (motion or “amps” over threshold).

**What is not on the board** — no separate ACS712, no display, no relay: Part 1 is **edge sensing + MQTT** with the parts listed above. Serial **115200** is the usual debug view.

---

## MQTT defaults

| | |
|--|--|
| WiFi (sim) | `Wokwi-GUEST` / empty password |
| Broker | `broker.hivemq.com` **:** `1883` |
| Topic | `telemetry/ADWYA-CHILLER-01` |

**Not encrypted:** traffic is **plain MQTT** on port 1883 (no TLS on the wire). The cahier lists TLS/HTTPS as *optional* for the protocol row — we didn’t implement them to save time. GitHub / doc URLs use `https://`; that’s normal for the web, **not** the same as encrypting this MQTT stream. **HTTPS** is just HTTP run over **TLS**; our firmware doesn’t speak HTTP at all, so “turn on HTTPS” here really means **MQTTS** (MQTT over TLS, often port 8883) or a separate **HTTPS REST** client — both need `WiFiClientSecure`, trust/certs, and a broker or API that supports TLS. Doable, but it’s a real chunk of work, not a one-line swap from 1883.

Own broker on LAN: Wokwi [Private IoT Gateway](https://docs.wokwi.com/guides/esp32-wifi) + change `MQTT_HOST` in the sketch.

---

## JSON (roughly every 2 s)

- `timestamp` — DS1307 (+01:00 string in code)  
- `device_id`  
- `sensors`: accel (g), gyro (°/s), temp (°C), `current_amps` from pot mapping 0–20 A (demo proxy)  
- `edge_anomaly` — simple thresholds on motion / “amps”  
- `meta`: fw string, uptime_s  

---

## Ring buffer (hackathon bonus line)

8 slots × 768 bytes. Push when MQTT down or publish fails; flush FIFO oldest-first after reconnect. Serial prints `[buffer] queued` / `flushed`.

---

## Energy harvesting — idea we didn’t implement

Industrial chillers vibrate whenever they run. The idea was to treat that vibration as a **tiny power source** instead of running the node from the wall or a disposable battery.

Rough chain we had in mind: a **piezoelectric** patch (or similar harvester) on the casing turns vibration into **small AC** → a dedicated **PMIC** (parts like the **LTC3588** are built for this) **rectifies and steps** it to a stable low DC → a **supercapacitor** (farads, not microfarads) soaks up energy over minutes or hours because harvest power is in the **milliwatt** range, not enough to hold WiFi continuously. The ESP32 would spend almost all its time in **deep sleep** (microamps), wake on a timer or when the cap voltage crosses a threshold, **read the sensors once**, open WiFi, **publish one MQTT JSON burst**, then sleep again. Same firmware logic as today; only the **power budget** and wake cadence change.

We’re **not** claiming any of that in this submission. **Wokwi** has no honest model for a harvester, PMIC, or cap bank, and we prioritized a **clear MQTT + buffer** story on **USB** in the sim. If someone asks what we’d do on a real install, the answer stays: **self-power from machine vibration** is the long-term picture — it’s just not wired, measured, or simulated here.

---

## Prove “server gets it” (30 pts line)

Second machine:

```bash
mosquitto_sub -h broker.hivemq.com -p 1883 -t 'telemetry/#' -v
```

Log to file: [LIVE_DEMO.md](LIVE_DEMO.md) §1.

---

## Part 1 rubric (short)

| Row | How we argue it |
|-----|-----------------|
| Works | Laptop runs `mosquitto_sub`, sees JSON on schedule |
| Multi-sensor | accel + gyro + temp + pot “amps”, one payload |
| Protocol | reconnect + `mqtt.loop`; **no** TLS in this branch |
| Uptime | long run + log file; count 5‑min windows if they ask |
| Data quality | no -999, sane ranges |
| +bonus | RAM buffer |

---

## Live demo (3–5 min)

Same table as [LIVE_DEMO.md](LIVE_DEMO.md) §3: Wokwi + Serial → second PC subscriber → wiggle MPU/pot / red LED → optional buffer stunt → one slide with topic + broker.

---

## Real hardware (flash off Wokwi)

Use the same pins as [Hardware and wiring](#hardware-and-wiring). Set **WiFi SSID/password** and **MQTT host** in `sketch.ino` for your network.

---

## License

Team code for the competition. Libs: Arduino-ESP32, PubSubClient, RTClib, Adafruit MPU6050 + Unified Sensor — their licenses apply.
