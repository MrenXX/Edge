import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

DB_PATH = Path(__file__).parent / "iot_data.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS iot_readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            device_id TEXT NOT NULL,
            sensors TEXT NOT NULL,
            edge_anomaly INTEGER NOT NULL DEFAULT 0,
            meta TEXT,
            received_at TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_readings_timestamp ON iot_readings(timestamp)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_readings_device ON iot_readings(device_id)
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS anomalies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            device_id TEXT NOT NULL,
            anomaly_type TEXT DEFAULT 'edge_anomaly',
            raw_data TEXT NOT NULL,
            received_at TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_anomalies_timestamp ON anomalies(timestamp)
    """)

    conn.commit()
    conn.close()


def insert_reading(timestamp: str, device_id: str, sensors: Dict[str, Any],
                   edge_anomaly: bool, meta: Optional[Dict[str, Any]] = None) -> int:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO iot_readings (timestamp, device_id, sensors, edge_anomaly, meta, received_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        timestamp,
        device_id,
        json.dumps(sensors),
        1 if edge_anomaly else 0,
        json.dumps(meta) if meta else None,
        datetime.utcnow().isoformat()
    ))

    reading_id = cursor.lastrowid

    if edge_anomaly:
        cursor.execute("""
            INSERT INTO anomalies (timestamp, device_id, anomaly_type, raw_data, received_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            timestamp,
            device_id,
            "edge_anomaly",
            json.dumps({"sensors": sensors, "meta": meta}),
            datetime.utcnow().isoformat()
        ))

    conn.commit()
    conn.close()
    return reading_id


def get_recent_readings(limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, timestamp, device_id, sensors, edge_anomaly, meta, received_at
        FROM iot_readings
        ORDER BY timestamp DESC
        LIMIT ? OFFSET ?
    """, (limit, offset))

    rows = cursor.fetchall()
    conn.close()

    return [
        {
            "id": row["id"],
            "timestamp": row["timestamp"],
            "device_id": row["device_id"],
            "sensors": json.loads(row["sensors"]),
            "edge_anomaly": bool(row["edge_anomaly"]),
            "meta": json.loads(row["meta"]) if row["meta"] else None,
            "received_at": row["received_at"]
        }
        for row in rows
    ]


def get_all_anomalies(limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, timestamp, device_id, anomaly_type, raw_data, received_at
        FROM anomalies
        ORDER BY timestamp DESC
        LIMIT ? OFFSET ?
    """, (limit, offset))

    rows = cursor.fetchall()
    conn.close()

    return [
        {
            "id": row["id"],
            "timestamp": row["timestamp"],
            "device_id": row["device_id"],
            "anomaly_type": row["anomaly_type"],
            "raw_data": json.loads(row["raw_data"]),
            "received_at": row["received_at"]
        }
        for row in rows
    ]


def get_iot_aggregates() -> Dict[str, Any]:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            COUNT(*) as total_readings,
            SUM(edge_anomaly) as anomaly_count,
            MIN(timestamp) as first_reading,
            MAX(timestamp) as last_reading
        FROM iot_readings
    """)

    row = cursor.fetchone()
    conn.close()

    if row["total_readings"] == 0:
        return {
            "total_readings": 0,
            "anomaly_count": 0,
            "anomaly_rate": 0.0,
            "first_reading": None,
            "last_reading": None
        }

    return {
        "total_readings": row["total_readings"],
        "anomaly_count": row["anomaly_count"],
        "anomaly_rate": row["anomaly_count"] / row["total_readings"],
        "first_reading": row["first_reading"],
        "last_reading": row["last_reading"]
    }