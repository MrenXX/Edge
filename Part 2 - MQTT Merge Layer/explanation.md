# Part 2 - MQTT Merge Layer & Anomaly Detection

## Overview

This is **Step 13** from the Re·Tech Fusion hackathon challenge (Part 2). We built the **logic layer** that receives IoT telemetry from the edge device (Part 1 - Wokwi/ESP32 simulator) and prepares it to be fed to the dashboard.

## What We Built

A middleware service that:
1. **Subscribes to MQTT broker** (HiveMQ) to receive real-time data from the edge device
2. **Stores all telemetry** in a local SQLite database
3. **Detects anomalies** when the edge device sends `edge_anomaly: true`
4. **Exposes APIs** for the future dashboard to consume

## Architecture

```
[Wokwi/ESP32 Device] --MQTT--> [HiveMQ Broker] --> [Pipeline] --> [SQLite]
                                                                    |
                                                                    v
                                                              [FastAPI Endpoints]
                                                                    |
                                                                    v
                                                               [Dashboard]
```

## How It Works

### 1. MQTT Connection
- Connects to `broker.hivemq.com` on port 1883
- Subscribes to topic: `telemetry/#` (all devices)
- Automatically reconnects if connection is lost

### 2. Data Storage
Every incoming message is stored in SQLite with:
- `timestamp` - When the reading was taken
- `device_id` - Which device sent it (e.g., "ADWYA-CHILLER-01")
- `sensors` - All sensor values (accel, gyro, temp, current)
- `edge_anomaly` - Boolean flag for anomaly detection
- `meta` - Device info (firmware, uptime)

### 3. Anomaly Detection
When the edge device detects an anomaly locally, it sends:
```json
{
  "edge_anomaly": true,
  "sensors": {...}
}
```

The pipeline:
- Stores this in the `readings` table with `edge_anomaly: 1`
- Also creates a record in the `anomalies` table for easy access

This enables the dashboard to show a **red notification** with "Warning" when anomalies occur.

## API Endpoints

| Endpoint | Purpose |
|----------|---------|
| `GET /health` | Service status (MQTT connected, DB status) |
| `GET /readings` | All IoT data with anomaly flags |
| `GET /anomalies` | Only anomaly records (for dashboard warnings) |
| `GET /unified/iot` | Aggregated stats + recent readings |

## Running the Service

### Option 1: With Docker
```bash
cd "Part 2 - MQTT Merge Layer"
docker-compose up --build
```

### Option 2: Direct Python
```bash
cd "Part 2 - MQTT Merge Layer/pipeline"
pip install -r requirements.txt
python main.py
```

The API runs on `http://localhost:8000`

## Testing

1. Start the pipeline
2. Run your Wokwi/ESP32 simulator to send MQTT messages
3. Check endpoints:
   - `curl http://localhost:8000/health` - Should show "healthy"
   - `curl http://localhost:8000/readings` - Shows all data
   - `curl http://localhost:8000/anomalies` - Shows warnings when `edge_anomaly: true`

## Dashboard Integration

When the dashboard is built, it can:

1. **Show red warning notification** by polling `/anomalies`
2. **Display live sensor strip** using `/unified/iot`
3. **Filter anomaly data** using `?edge_anomaly=true` in readings

## Files Included

- `pipeline/main.py` - FastAPI app + MQTT subscriber
- `pipeline/database.py` - SQLite operations
- `pipeline/models.py` - Data schemas
- `pipeline/config.py` - Configuration
- `docker-compose.yml` - Docker setup (Mosquitto + Pipeline)
- `.env.example` - Environment variables template

## Tech Stack

- **FastAPI** - Web framework
- **paho-mqtt** - MQTT client
- **SQLite** - Local database
- **Python 3.11** - Runtime

## Status

✅ Working - Tested with real Wokwi simulator data  
✅ MQTT connected to HiveMQ  
✅ Anomaly detection functional  
✅ API endpoints ready for dashboard

---

*Built during Re·Tech Fusion Hackathon - INSAT*