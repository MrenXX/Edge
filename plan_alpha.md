# Eco-Edge: Predictive Maintenance & Energy Reconciliation Pipeline
**Hackathon Master Blueprint - Parts 1, 2, and 3**

## The Core Narrative (The Pitch)
Industrial machines waste massive amounts of energy (and generate excess CO2) right before they break down. Friction increases, motors vibrate, heat builds up, and the machines draw extra power. 

**Our Solution:** A closed-loop system. We place an Edge-AI node on the factory machinery (Part 1 & 3) to detect physical failure instantly. We pipe this live data into a centralized dashboard (Part 2) that has automatically ingested and normalized the factory's paper energy bills (STEG/SONEDE). Plant managers can now correlate physical machine health directly to financial energy waste and carbon emissions.

---

## Phase 1: The Edge Node (The Nerves)
**Goal:** Gather physical data, timestamp it precisely, and handle network drops.

**Hardware Setup & Sensor Scenarios:**
The core of our board is the ESP32 (Microcontroller) and the DS3231 (RTC for millisecond-accurate timestamps independent of WiFi). How we handle the sensors depends on availability:

*   **Scenario A: The Current Sensor is Acquired (The Holy Trinity)**
    If the organizers provide the current sensor (like an ACS712) in a few hours, we achieve the perfect 3-sensor industrial story. We track the chain reaction of a failing motor: 
    1. Vibration increases (MPU-6050 Accelerometer).
    2. Friction causes overheating (MPU-6050 Internal Temperature Sensor).
    3. The motor struggles and draws more electricity (Current Sensor).

*   **Scenario B: No Current Sensor (The Fallback)**
    If we do not get the current sensor, we discard the useless HW-072 color sensor and rely entirely on the MPU-6050. Because the MPU-6050 has a built-in digital thermometer, we still have two distinct physical metrics (Vibration and Temperature). The story shifts slightly: *We detect the physical degradation (vibration/heat) as an early warning system before it manifests as wasted energy on the monthly STEG bill.*

**Firmware Logic (C++ / Arduino IDE):**
1. Read the sensors every 2 seconds.
2. Package into a JSON payload. *Crucial: We program a dummy variable for the current sensor right now so the software team can build the dashboard immediately. If we get the sensor later, we just plug it in and replace the dummy value.*
3. Transmit via MQTT to the local broker. 
4. **Innovation (+15pts):** If the MQTT connection drops, push the JSON strings into a local circular buffer array in the ESP32's RAM. Upon reconnection, publish the entire backlog to prevent data loss.

**Target JSON Payload:**
```json
{
  "timestamp": "2026-05-02 03:45:12.710", 
  "device_id": "ADWYA-CHILLER-01",
  "sensors": {
    "accel_x": 0.04,
    "accel_y": -0.01,
    "accel_z": 1.02,
    "temp_c": 35.5,
    "current_amps": 0.00 
  },
  "edge_anomaly": false
}
```

---

## Phase 2: Data Unification & Dashboard (The Brain)
**Goal:** Extract heterogeneous document data, normalize it, and visualize it alongside live IoT data.

**1. Document Extraction (Python / LLM API):**
*   Because the provided STEG bills are photos/scans, standard PDF text parsers will fail.
*   **The Hack:** Use the OpenAI API (GPT-4o) or Anthropic Claude API. Pass the image to the API with a strict prompt: *"Extract the Total Energy, Unit (TH, NM3, or kWh), Supplier (STEG/SONEDE), and Date from this Tunisian utility bill. Return ONLY a valid JSON."*

**2. Unit Normalization (Python):**
*   **Electricity:** Keep as kWh.
*   **Gas:** The bill gives Thermies (TH). Multiply by 1.163 to get kWh.
*   **CO2 Calculation:** Multiply total unified kWh by the Tunisian grid emission factor (approx. 0.43 kg CO2/kWh).

**3. The Command Center (Streamlit):**
*   Build a local web app using Streamlit.
*   **Macro View (Top):** Bar charts showing historical Energy Consumption and CO2 emissions based on the parsed bills.
*   **Micro View (Bottom):** Live, auto-updating line charts subscribing to the MQTT broker, showing the ESP32's live sensor data.

---

## Phase 3: Edge ML Anomaly Detection (The Reflex)
**Goal:** Track A - Deploy local intelligence so the machine protects itself even if the WiFi router dies.

**Execution Steps (Edge Impulse):**
1. Install Edge Impulse Data Forwarder on a PC.
2. Connect the ESP32 via USB and stream the MPU-6050 data (Vibration/Temp) to the platform.
3. Record 2 minutes of "Normal Running" (letting the breadboard sit still).
4. Record 2 minutes of "Anomaly" (tapping/shaking the breadboard to simulate a broken bearing).
5. Train a K-Means Anomaly Detection model.
6. Export the model as an Arduino Library (.zip) and include it in Phase 1's code.

**The Trigger:**
*   When the ESP32's internal model detects shaking, it changes `"edge_anomaly": true` in the JSON, and turns on the RED LED on the breadboard (Local Alert).
*   The Streamlit dashboard reads the `true` flag and flashes a massive red UI alert (Command Center Alert).