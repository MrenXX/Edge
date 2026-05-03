"""Runtime config for the unified Eco-Edge API (reads env / .env)."""

from __future__ import annotations

import os
from pathlib import Path

_PART2 = Path(__file__).resolve().parent.parent

try:
    from dotenv import load_dotenv

    load_dotenv(_PART2 / ".env")
except ImportError:
    pass

# Docker: set DATASET_ROOT=/data (layout: out/, incoming/, pdfs/). Local default ties out/ to pipeline/out.
DATASET_ROOT = Path(os.getenv("DATASET_ROOT", str(_PART2 / "pipeline"))).resolve()
OUT_DIR = Path(os.getenv("OUT_DIR", str(DATASET_ROOT / "out"))).resolve()
INCOMING_DIR = Path(os.getenv("INCOMING_DIR", str(_PART2 / "data" / "incoming"))).resolve()
PDF_BATCH_DIR = Path(os.getenv("PDF_BATCH_DIR", str(_PART2 / "data" / "pdfs"))).resolve()
MQTT_MERGE_URL = os.getenv("MQTT_MERGE_URL", "http://127.0.0.1:8000").rstrip("/")
API_VERSION = os.getenv("API_VERSION", "0.1.0")
PIPELINE_ROOT = Path(os.getenv("PIPELINE_ROOT", str(_PART2 / "pipeline"))).resolve()
