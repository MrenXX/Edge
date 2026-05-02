import os
from typing import Optional


class Config:
    # Defaults match Wokwi + public HiveMQ (same as sketch / mosquitto_sub -h broker.hivemq.com)
    MQTT_BROKER_HOST: str = os.getenv("MQTT_BROKER_HOST", "broker.hivemq.com")
    MQTT_BROKER_PORT: int = int(os.getenv("MQTT_BROKER_PORT", "1883"))
    # Device-specific topic avoids junk from other publishers on public HiveMQ (#).
    MQTT_TOPIC: str = os.getenv("MQTT_TOPIC", "telemetry/ADWYA-CHILLER-01")
    MQTT_USERNAME: Optional[str] = os.getenv("MQTT_USERNAME")
    MQTT_PASSWORD: Optional[str] = os.getenv("MQTT_PASSWORD")

    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))

    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")


config = Config()
