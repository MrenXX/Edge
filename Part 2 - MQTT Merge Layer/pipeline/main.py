import json
import logging
import threading
from datetime import datetime
from typing import Optional

import paho.mqtt.client as mqtt
from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse

from config import config
from database import (
    init_db,
    insert_reading,
    get_recent_readings,
    get_all_anomalies,
    get_iot_aggregates
)
from models import (
    IoTReading,
    AnomalyRecord,
    IoTAggregates,
    HealthResponse,
    SensorsData,
    MetaData
)

logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Eco-Edge Part 2 Pipeline", version="1.0.0")

mqtt_client: Optional[mqtt.Client] = None
mqtt_connected = False


def on_connect(client, userdata, flags, rc):
    global mqtt_connected
    if rc == 0:
        mqtt_connected = True
        logger.info(f"Connected to MQTT broker at {config.MQTT_BROKER_HOST}:{config.MQTT_BROKER_PORT}")
        client.subscribe(config.MQTT_TOPIC)
        logger.info(f"Subscribed to topic: {config.MQTT_TOPIC}")
    else:
        mqtt_connected = False
        logger.error(f"Failed to connect to MQTT broker, return code: {rc}")


def on_disconnect(client, userdata, rc):
    global mqtt_connected
    mqtt_connected = False
    logger.warning(f"Disconnected from MQTT broker, return code: {rc}")


def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        logger.debug(f"Received MQTT message: {payload.get('timestamp', 'unknown')}")

        timestamp = payload.get("timestamp")
        device_id = payload.get("device_id", "unknown")
        sensors = payload.get("sensors", {})
        edge_anomaly = payload.get("edge_anomaly", False)
        meta = payload.get("meta")

        if not timestamp:
            logger.warning("Ignoring message without timestamp")
            return

        insert_reading(
            timestamp=timestamp,
            device_id=device_id,
            sensors=sensors,
            edge_anomaly=edge_anomaly,
            meta=meta
        )

        if edge_anomaly:
            logger.warning(f"ANOMALY DETECTED - Device: {device_id}, Time: {timestamp}")

    except json.JSONDecodeError as e:
        logger.error(f"Failed to decode MQTT message: {e}")
    except Exception as e:
        logger.error(f"Error processing MQTT message: {e}")


def start_mqtt_subscriber():
    global mqtt_client

    client_id = f"pipeline-subscriber-{int(datetime.utcnow().timestamp())}"
    mqtt_client = mqtt.Client(client_id)

    if config.MQTT_USERNAME and config.MQTT_PASSWORD:
        mqtt_client.username_pw_set(config.MQTT_USERNAME, config.MQTT_PASSWORD)

    mqtt_client.on_connect = on_connect
    mqtt_client.on_disconnect = on_disconnect
    mqtt_client.on_message = on_message

    try:
        logger.info(f"Connecting to MQTT broker {config.MQTT_BROKER_HOST}:{config.MQTT_BROKER_PORT}")
        mqtt_client.connect(config.MQTT_BROKER_HOST, config.MQTT_BROKER_PORT, keepalive=60)
        mqtt_client.loop_start()
    except Exception as e:
        logger.error(f"Failed to connect to MQTT broker: {e}")
        logger.warning("Continuing without MQTT - will retry on reconnection")


@app.on_event("startup")
async def startup_event():
    logger.info("Initializing database...")
    init_db()
    logger.info("Database initialized")

    logger.info("Starting MQTT subscriber in background...")
    mqtt_thread = threading.Thread(target=start_mqtt_subscriber, daemon=True)
    mqtt_thread.start()


@app.on_event("shutdown")
async def shutdown_event():
    global mqtt_client
    if mqtt_client:
        logger.info("Stopping MQTT client...")
        mqtt_client.loop_stop()
        mqtt_client.disconnect()


@app.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(
        status="healthy" if mqtt_connected else "degraded",
        mqtt_connected=mqtt_connected,
        database="connected",
        version="1.0.0"
    )


@app.get("/readings")
async def get_readings(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    readings = get_recent_readings(limit=limit, offset=offset)
    return {"readings": readings, "count": len(readings)}


@app.get("/anomalies")
async def get_anomalies(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    anomalies = get_all_anomalies(limit=limit, offset=offset)
    return {"anomalies": anomalies, "count": len(anomalies)}


@app.get("/unified/iot")
async def get_unified_iot():
    aggregates = get_iot_aggregates()
    recent = get_recent_readings(limit=10)
    return {
        "aggregates": aggregates,
        "recent_readings": recent
    }


@app.get("/")
async def root():
    return {
        "service": "Eco-Edge Part 2 Pipeline",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": ["/health", "/readings", "/anomalies", "/unified/iot"]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=config.API_HOST, port=config.API_PORT)