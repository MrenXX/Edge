# Wokwi — exact steps (Eco-Edge Part 1)

This folder is a **Wokwi Arduino** project: [diagram.json](diagram.json) + [sketch.ino](sketch.ino) + [libraries.txt](libraries.txt).  
**Overview & rubric mapping:** see [README.md](README.md).

## 1. Create or open the project on Wokwi

1. Go to [https://wokwi.com](https://wokwi.com) and sign in (optional but useful to save).
2. **New project** → pick **ESP32** (or “Import” if you use Git).
3. Delete the default `diagram.json` content and **paste your** `diagram.json` from this repo (or clone the repo and open the folder in VS Code with the Wokwi extension).

You must have **three files in the same Wokwi project**:

- `diagram.json` (hardware)
- `sketch.ino` (firmware)
- `libraries.txt` (dependencies — Wokwi reads this automatically in many setups; if not, use **Library Manager** in the UI and add each line manually)

## 2. Libraries (if Wokwi does not auto-install from `libraries.txt`)

In the Wokwi editor: **Libraries** (or “+”) → search and add:

- **Adafruit MPU6050**
- **Adafruit Unified Sensor** (often pulled in automatically)
- **RTClib**
- **PubSubClient**

(JSON is built with `snprintf` in firmware — no ArduinoJson dependency.)

Then **Build** / **Run simulation**.

**If you see “Unknown builder: arduino”:** the ESP32 part in `diagram.json` must **not** set `"builder": "arduino"` — use `"attrs": {}` (fixed in this repo).

## 3. WiFi in the browser simulator

Wokwi gives you a virtual AP:

- **SSID:** `Wokwi-GUEST`
- **Password:** *(empty)*

The sketch uses these by default so **WiFi works without editing** in the public simulator.

## 4. MQTT broker (important)

- **Public Wokwi internet gateway:** your simulated ESP **cannot** see `localhost` on your laptop. Use a **public** broker for a quick test, or Wokwi’s **Private IoT Gateway** to reach **Mosquitto on your PC**.

Default in `sketch.ino`:

- `MQTT_HOST` = `broker.hivemq.com` (anonymous MQTT, good for “does it publish?”).

**To hit your own Mosquitto:**

1. Install [Wokwi Private IoT Gateway](https://docs.wokwi.com/guides/esp32-wifi#private-gateway) on your PC.
2. In Wokwi: **F1** → **Enable Private Wokwi IoT Gateway**.
3. Set `MQTT_HOST` in `sketch.ino` to your PC’s **LAN IP** (e.g. `192.168.1.50`) where Mosquitto listens on `1883`.

## 5. First successful test

1. Click **Start simulation**.
2. Open **Serial Monitor** (115200 baud in code).
3. You should see: WiFi connected, MQTT connected, and JSON lines or “Published …”.
4. On your PC (if broker reachable):  
   `mosquitto_sub -h broker.hivemq.com -p 1883 -t telemetry/# -v`  
   (change host if you use your own broker)

## 6. Hardware behavior in this diagram

| Signal | Pin / bus |
|--------|-----------|
| I²C SDA | GPIO **21** |
| I²C SCL | GPIO **22** |
| MPU6050 address | **0x69** (because **AD0 → 3V3** in `diagram.json`) |
| DS1307 | **0x68** on same bus (no clash) |
| Pot (“current” proxy) | GPIO **34** (ADC1) |
| LED green | GPIO **4** |
| LED red | GPIO **2** |

## 7. If something fails

- **MPU not found:** confirm `imu1:AD0` → `3V3` in the diagram and `MPU_I2C_ADDR 0x69` in code.
- **RTC not found:** check DS1307 wiring; RTC library prints errors on Serial.
- **WiFi stuck:** SSID must be exactly `Wokwi-GUEST` in the default public sim.
- **MQTT never connects:** try `broker.hivemq.org` vs `broker.hivemq.com` per current HiveMQ docs, or switch to `test.mosquitto.org`.

We cannot run Wokwi from Cursor; if you paste **Serial output** or **compiler errors**, we can adjust the sketch.

## 8. MQTT log file + jury demo script

See **[LIVE_DEMO.md](LIVE_DEMO.md)** for:

- `mosquitto_sub` **redirect / tee** commands (bash + PowerShell)
- **Ring buffer** demo (Serial `queued` / `flushed`) for Part 1 **bonus innovation**
- Suggested **live demo order** and a minimal **git** backup snippet
