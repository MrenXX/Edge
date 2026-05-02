import json
import logging
import queue
import threading
import time
from datetime import datetime, UTC
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent / ".env")
except ImportError:
    pass

import paho.mqtt.client as mqtt
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from config import config
from database import (
    init_db,
    insert_reading,
    get_recent_readings,
    get_all_anomalies,
    get_iot_aggregates,
)
from models import HealthResponse

logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Eco-Edge MQTT merge", version="1.0.1")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

mqtt_client: Optional[mqtt.Client] = None
mqtt_connected = False

# Never block the Paho network thread with SQLite I/O — broker will drop the client on keepalive timeout.
_write_queue: "queue.Queue[Optional[Tuple[str, str, Dict[str, Any], bool, Optional[Dict[str, Any]]]]]" = queue.Queue(
    maxsize=2000
)
_writer_thread: Optional[threading.Thread] = None
_writer_shutdown = threading.Event()


def _writer_loop() -> None:
    while not _writer_shutdown.is_set() or not _write_queue.empty():
        try:
            item = _write_queue.get(timeout=0.5)
        except queue.Empty:
            continue
        if item is None:
            break
        timestamp, device_id, sensors, edge_anomaly, meta = item
        try:
            rid = insert_reading(
                timestamp=timestamp,
                device_id=device_id,
                sensors=sensors,
                edge_anomaly=edge_anomaly,
                meta=meta,
            )
            if edge_anomaly:
                logger.warning(
                    "edge_anomaly stored id=%s device=%s ts=%s", rid, device_id, timestamp
                )
        except Exception as e:
            logger.exception("DB writer failed: %s", e)


def _start_writer_thread() -> threading.Thread:
    t = threading.Thread(target=_writer_loop, name="iot-db-writer", daemon=True)
    t.start()
    return t


def _coerce_bool(v: object) -> bool:
    if isinstance(v, bool):
        return v
    if v is None:
        return False
    if isinstance(v, (int, float)):
        return v != 0
    if isinstance(v, str):
        return v.strip().lower() in ("1", "true", "yes", "on")
    return bool(v)


def on_connect(client, userdata, flags, rc):  # noqa: ANN001
    global mqtt_connected
    if rc == 0:
        mqtt_connected = True
        logger.info("Connected to MQTT %s:%s", config.MQTT_BROKER_HOST, config.MQTT_BROKER_PORT)
        client.subscribe(config.MQTT_TOPIC)
        logger.info("Subscribed to %s", config.MQTT_TOPIC)
    else:
        mqtt_connected = False
        logger.error("MQTT connect failed rc=%s", rc)


def on_disconnect(client, userdata, rc):  # noqa: ANN001
    global mqtt_connected
    mqtt_connected = False
    logger.warning("MQTT disconnected rc=%s", rc)


def on_message(client, userdata, msg):  # noqa: ANN001
    raw = ""
    try:
        raw = msg.payload.decode("utf-8", errors="replace").strip()
        if not raw:
            return
        payload = json.loads(raw)
        timestamp = payload.get("timestamp")
        device_id = payload.get("device_id", "unknown")
        sensors = payload.get("sensors", {})
        if not isinstance(sensors, dict):
            sensors = {}
        edge_anomaly = _coerce_bool(payload.get("edge_anomaly", False))
        meta = payload.get("meta")
        if meta is not None and not isinstance(meta, dict):
            meta = None

        if not timestamp:
            logger.debug("Skipping non-telemetry payload topic=%s keys=%s", msg.topic, list(payload.keys())[:5])
            return

        item = (
            str(timestamp),
            str(device_id),
            sensors,
            edge_anomaly,
            meta,
        )
        try:
            _write_queue.put_nowait(item)
        except queue.Full:
            logger.error("IoT write queue full (>%s); dropping message", _write_queue.maxsize)

    except json.JSONDecodeError:
        logger.debug("Ignoring non-JSON MQTT payload topic=%s preview=%s", msg.topic, raw[:120] if len(raw) > 120 else raw)
    except Exception as e:
        logger.error("Message handler: %s", e)


def start_mqtt_subscriber() -> None:
    global mqtt_client

    client_id = f"ecoedge-merge-{int(datetime.now(UTC).timestamp())}"
    try:
        mqtt_client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION1,
            client_id=client_id,
        )
    except (AttributeError, TypeError):
        mqtt_client = mqtt.Client(client_id=client_id)

    if config.MQTT_USERNAME and config.MQTT_PASSWORD:
        mqtt_client.username_pw_set(config.MQTT_USERNAME, config.MQTT_PASSWORD)

    try:
        mqtt_client.reconnect_delay_set(min_delay=1, max_delay=60)
    except (AttributeError, TypeError):
        pass

    mqtt_client.on_connect = on_connect
    mqtt_client.on_disconnect = on_disconnect
    mqtt_client.on_message = on_message

    try:
        logger.info("Connecting MQTT %s:%s", config.MQTT_BROKER_HOST, config.MQTT_BROKER_PORT)
        mqtt_client.connect(config.MQTT_BROKER_HOST, config.MQTT_BROKER_PORT, keepalive=60)
        mqtt_client.loop_start()
    except Exception as e:
        logger.error("MQTT connect error: %s", e)
        logger.warning("API will run without MQTT until broker is available")


@app.on_event("startup")
async def startup_event() -> None:
    global _writer_thread
    init_db()
    _writer_shutdown.clear()
    _writer_thread = _start_writer_thread()
    thread = threading.Thread(target=start_mqtt_subscriber, daemon=True, name="mqtt-subscriber")
    thread.start()


@app.on_event("shutdown")
async def shutdown_event() -> None:
    global mqtt_client, _writer_thread
    if mqtt_client:
        mqtt_client.loop_stop()
        mqtt_client.disconnect()
    time.sleep(0.15)
    _writer_shutdown.set()
    try:
        _write_queue.put_nowait(None)
    except queue.Full:
        pass
    if _writer_thread and _writer_thread.is_alive():
        _writer_thread.join(timeout=15.0)
    _writer_thread = None


@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    agg = get_iot_aggregates()
    ac = int(agg.get("anomaly_count") or 0)
    rate = float(agg.get("anomaly_rate") or 0.0)
    if not mqtt_connected:
        status = "degraded"
    elif ac > 0:
        status = "attention"
    else:
        status = "healthy"
    return HealthResponse(
        status=status,
        mqtt_connected=mqtt_connected,
        database="connected",
        version="1.0.1",
        anomaly_count=ac,
        anomaly_rate=rate,
    )


@app.get("/readings")
async def get_readings(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> dict:
    readings = get_recent_readings(limit=limit, offset=offset)
    return {"readings": readings, "count": len(readings)}


@app.get("/anomalies")
async def get_anomalies(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> dict:
    anomalies = get_all_anomalies(limit=limit, offset=offset)
    return {"anomalies": anomalies, "count": len(anomalies)}


@app.get("/unified/iot")
async def get_unified_iot() -> dict:
    return {
        "aggregates": get_iot_aggregates(),
        "recent_readings": get_recent_readings(limit=40),
    }


@app.get("/")
async def root() -> dict:
    return {
        "service": "Eco-Edge MQTT merge",
        "version": "1.0.1",
        "docs": "/docs",
        "endpoints": ["/health", "/readings", "/anomalies", "/unified/iot"],
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=config.API_HOST, port=config.API_PORT)
