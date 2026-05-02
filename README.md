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

## Energy harvesting — wanted it, didn’t ship it

We had a **production-style** idea on paper: strap a **piezo** (or similar) on the chiller, rectify/regulate (e.g. something in the **LTC3588** family), **supercap** buffer, ESP32 in **deep sleep** most of the time and only wake to sample + burst MQTT — no wall wart, no battery swaps, fits the “waste energy → useful node” story.

We’re **not** claiming that in this repo. Wokwi can’t meaningfully simulate a harvester or cap bank, and we were already on **sim + USB** for Part 1, so we parked the power story and put effort into telemetry + the ring buffer. If a judge asks “what’s next on hardware,” self-power on the machine is still the honest stretch goal — it just isn’t built or demo’d here.

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

## Real hardware

Same pins if you flash a physical ESP32: I²C 21/22, pot 34, LEDs 4 & 2. Put your WiFi + broker in the sketch.

---

## License

Team code for the competition. Libs: Arduino-ESP32, PubSubClient, RTClib, Adafruit MPU6050 + Unified Sensor — their licenses apply.
