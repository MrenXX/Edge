from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List


class SensorsData(BaseModel):
    accel_x_g: Optional[float] = None
    accel_y_g: Optional[float] = None
    accel_z_g: Optional[float] = None
    gyro_x_dps: Optional[float] = None
    gyro_y_dps: Optional[float] = None
    gyro_z_dps: Optional[float] = None
    temp_c: Optional[float] = None
    current_amps: Optional[float] = None


class MetaData(BaseModel):
    fw: Optional[str] = None
    uptime_s: Optional[int] = None


class IoTReading(BaseModel):
    id: Optional[int] = None
    timestamp: str
    device_id: str
    sensors: SensorsData
    edge_anomaly: bool = False
    meta: Optional[MetaData] = None
    received_at: Optional[str] = None


class AnomalyRecord(BaseModel):
    id: Optional[int] = None
    timestamp: str
    device_id: str
    anomaly_type: str = "edge_anomaly"
    raw_data: Dict[str, Any]
    received_at: Optional[str] = None


class IoTAggregates(BaseModel):
    total_readings: int
    anomaly_count: int
    anomaly_rate: float
    first_reading: Optional[str] = None
    last_reading: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    mqtt_connected: bool
    database: str
    version: str = "1.0.0"