# Edge

An ESP32 **edge-sensing node** that reads vibration/motion and load telemetry and publishes it as JSON over MQTT. Built for industrial-equipment monitoring scenarios (e.g. chiller health); developed and simulated in [Wokwi](https://wokwi.com), and runs on real hardware with the same wiring.

## What it does

- **MPU6050** — accelerometer + gyroscope + die temperature over I²C.
- **Potentiometer → GPIO34** — stand-in for a 0–20 A current sensor (load proxy; swap in an ACS712 for real measurements).
- **DS1307 RTC** — wall-clock timestamp for every payload.
- **MQTT publishing** (~every 2 s) with a small **ring buffer** that queues readings while the broker is unreachable and flushes oldest-first on reconnect.
- **Status LEDs** — green: WiFi + MQTT connected; red: anomaly threshold tripped (motion or overcurrent).

## Repo layout

| File | What it is |
|------|------------|
| [diagram.json](diagram.json) | Wokwi circuit: ESP32 DevKit-C, MPU6050 @ `0x69`, DS1307, pot → GPIO34, LEDs on GPIO4/GPIO2 |
| [sketch.ino](sketch.ino) | Firmware: sensors → JSON → MQTT, reconnect logic, ring buffer |
| [libraries.txt](libraries.txt) | Library list for Wokwi / Arduino |
| [WOKWI.md](WOKWI.md) | Simulator setup notes and WiFi/MQTT gotchas |
| [LIVE_DEMO.md](LIVE_DEMO.md) | Subscribing with `mosquitto_sub` and logging to disk |

## Run it in Wokwi

1. Open [wokwi.com](https://wokwi.com) → new ESP32 project.
2. Paste in `diagram.json`, `sketch.ino`, `libraries.txt`.
3. Install the listed libraries.
4. Start the simulation and watch the Serial monitor at **115200** baud.

To verify end-to-end, subscribe from any machine:

```bash
mosquitto_sub -h broker.hivemq.com -p 1883 -t 'telemetry/#' -v
```

## Wiring

One **ESP32 DevKit-C** controller; **3V3**/**GND** rails. Shared I²C bus on **GPIO21 (SDA)** / **GPIO22 (SCL)**:

| Part | Power | Notes |
|------|-------|-------|
| **MPU6050** | VCC→3V3, GND | AD0 → 3V3 so the chip answers at address **0x69**. |
| **DS1307 RTC** | VCC→5V-tied-to-3V3 (sim), GND | Address **0x68**; provides the JSON `timestamp`. |

- **Potentiometer**: ends to 3V3/GND, wiper → **GPIO34** (ADC-only pin). Firmware maps the reading to 0–20 A as a demo proxy.
- **Green LED**: GPIO4 → 220 Ω → LED → GND. On when WiFi and MQTT are both up.
- **Red LED**: GPIO2 → 220 Ω → LED → GND. On when an anomaly is flagged.

On real hardware, use the same pins and set your WiFi SSID/password and MQTT host in `sketch.ino`.

## MQTT defaults

| | |
|--|--|
| WiFi (sim) | `Wokwi-GUEST` / empty password |
| Broker | `broker.hivemq.com` : `1883` |
| Topic | `telemetry/ADWYA-CHILLER-01` |

Traffic is plain MQTT (no TLS). For your own LAN broker use the Wokwi [Private IoT Gateway](https://docs.wokwi.com/guides/esp32-wifi) and change `MQTT_HOST` in the sketch.

## Payload

JSON roughly every 2 s:

- `timestamp` — from the DS1307
- `device_id`
- `sensors` — accel (g), gyro (°/s), temp (°C), `current_amps` (pot-mapped 0–20 A proxy)
- `edge_anomaly` — boolean from simple thresholds on motion / current
- `meta` — firmware string, uptime

## Roadmap

- **MQTTS** — TLS transport (port 8883) via `WiFiClientSecure`.
- **Real current sensing** — replace the pot proxy with an ACS712.
- **Energy harvesting** — self-powering node: piezoelectric harvester on the machine casing → PMIC (e.g. LTC3588) → supercapacitor buffer, with the ESP32 in deep sleep between short wake/publish cycles. Same firmware logic, different power budget.

## License

[MIT](LICENSE). Third-party libraries (Arduino-ESP32, PubSubClient, RTClib, Adafruit MPU6050 + Unified Sensor) remain under their own licenses.
