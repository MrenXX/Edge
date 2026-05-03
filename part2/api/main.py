"""Eco-Edge Part 2 unified API: documents on disk + MQTT merge upstream."""

from __future__ import annotations

import logging
import os
import subprocess
import sys
from datetime import UTC, datetime
from typing import Annotated

import httpx
from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from api import config
from api.document_store import (
    audit_tail_last_ts,
    iter_json_paths,
    load_all_documents,
    load_document_by_stem,
)
from api.unified_builder import (
    build_iot_live_strip,
    build_iot_period_aggregates,
    build_normalized_rollups,
    build_validation_summary,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Eco-Edge Part 2 API",
    version=config.API_VERSION,
    description="Unified extraction JSON + IoT (plan_part2.md §15). MQTT data via merge service.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


async def _fetch_merge_health(client: httpx.AsyncClient) -> dict:
    try:
        r = await client.get(f"{config.MQTT_MERGE_URL}/health", timeout=3.0)
        if r.status_code == 200:
            return r.json()
        return {"reachable": True, "http_status": r.status_code}
    except Exception as e:
        return {"reachable": False, "error": str(e)}


async def _fetch_iot_payload(client: httpx.AsyncClient) -> tuple[dict | None, str | None]:
    try:
        r = await client.get(f"{config.MQTT_MERGE_URL}/unified/iot", timeout=5.0)
        r.raise_for_status()
        return r.json(), None
    except Exception as e:
        return None, str(e)


async def _fetch_readings(client: httpx.AsyncClient, limit: int = 500) -> list[dict]:
    try:
        r = await client.get(
            f"{config.MQTT_MERGE_URL}/readings",
            params={"limit": limit},
            timeout=8.0,
        )
        r.raise_for_status()
        return r.json().get("readings") or []
    except Exception as e:
        logger.warning("readings fetch failed: %s", e)
        return []


@app.get("/health")
async def health() -> dict:
    documents = load_all_documents()
    merge: dict = {"url": config.MQTT_MERGE_URL}
    async with httpx.AsyncClient() as client:
        mh = await _fetch_merge_health(client)
        merge.update(mh)

    api_status = "healthy"
    if merge.get("reachable") is False:
        api_status = "degraded"

    return {
        "status": api_status,
        "version": config.API_VERSION,
        "dataset": {
            "out_dir": str(config.OUT_DIR),
            "validated_documents": len(documents),
            "json_files": len(iter_json_paths()),
        },
        "mqtt_merge": merge,
    }


@app.get("/documents")
def get_documents(
    summary: bool = Query(False, description="If true, return slim rows only."),
    q: str | None = Query(None, description="Filter by substring of source_file."),
) -> dict:
    docs = load_all_documents()
    if q:
        ql = q.lower()
        docs = [d for d in docs if ql in (d.source_file or "").lower()]
    if summary:
        items = []
        for d in docs:
            items.append(
                {
                    "source_file": d.source_file,
                    "document_family": d.document_family,
                    "period_label": d.period_label,
                    "confidence_0_1": d.confidence_0_1,
                    "parser_path": d.parser_path,
                }
            )
        return {"count": len(docs), "items": items}
    return {"count": len(docs), "documents": [d.model_dump() for d in docs]}


@app.get("/documents/{stem}")
def get_document(stem: str) -> dict:
    doc = load_document_by_stem(stem)
    if doc is None:
        raise HTTPException(status_code=404, detail=f"No document `{stem}.json` in out dir.")
    return doc.model_dump()


def _require_gemini() -> None:
    if not os.getenv("GOOGLE_API_KEY"):
        raise HTTPException(
            status_code=503,
            detail="GOOGLE_API_KEY not configured — set in .env for live extraction.",
        )


@app.post("/ingest")
async def post_ingest(
    files: Annotated[list[UploadFile], File()] = [],
    run_pdf_folder: bool = Form(False),
) -> dict:
    """Upload PDFs/images or batch-run all PDFs in `PDF_BATCH_DIR` via `energy_extract`."""
    _require_gemini()
    config.INCOMING_DIR.mkdir(parents=True, exist_ok=True)
    config.OUT_DIR.mkdir(parents=True, exist_ok=True)
    config.PDF_BATCH_DIR.mkdir(parents=True, exist_ok=True)

    env = {**os.environ, "PYTHONPATH": str(config.PIPELINE_ROOT)}

    if run_pdf_folder:
        if not config.PDF_BATCH_DIR.is_dir():
            raise HTTPException(status_code=400, detail=f"PDF_BATCH_DIR not found: {config.PDF_BATCH_DIR}")
        pdfs = list(config.PDF_BATCH_DIR.glob("*.pdf"))
        if not pdfs:
            raise HTTPException(status_code=400, detail="No .pdf files in PDF_BATCH_DIR")
        cmd = [
            sys.executable,
            "-m",
            "energy_extract",
            "--data-dir",
            str(config.PDF_BATCH_DIR),
            "--out-dir",
            str(config.OUT_DIR),
        ]
        logger.info("ingest batch folder %s", config.PDF_BATCH_DIR)
    elif files:
        paths: list[str] = []
        for uf in files:
            if not uf.filename:
                continue
            dest = config.INCOMING_DIR / uf.filename
            dest.write_bytes(await uf.read())
            paths.append(str(dest.resolve()))
        if not paths:
            raise HTTPException(status_code=400, detail="No usable uploaded files")
        cmd = [
            sys.executable,
            "-m",
            "energy_extract",
            "--files",
            *paths,
            "--out-dir",
            str(config.OUT_DIR),
            "--parallel",
            "2",
        ]
        logger.info("ingest upload %s file(s)", len(paths))
    else:
        raise HTTPException(
            status_code=400,
            detail="Send multipart files or form field run_pdf_folder=true",
        )

    proc = subprocess.run(
        cmd,
        cwd=str(config.PIPELINE_ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=900,
    )
    if proc.returncode != 0:
        logger.error("ingest failed rc=%s stderr=%s", proc.returncode, proc.stderr[-2000:])
        raise HTTPException(
            status_code=500,
            detail={
                "returncode": proc.returncode,
                "stderr_tail": (proc.stderr or "")[-6000:],
                "stdout_tail": (proc.stdout or "")[-2000:],
            },
        )
    return {
        "ok": True,
        "returncode": proc.returncode,
        "stdout_tail": (proc.stdout or "")[-800:],
    }


@app.get("/metrics")
async def get_metrics() -> dict:
    docs = load_all_documents()
    n_json = len(iter_json_paths())
    iot: dict = {}
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(f"{config.MQTT_MERGE_URL}/unified/iot", timeout=4.0)
            if r.status_code == 200:
                iot = r.json()
        except Exception as e:
            iot = {"error": str(e)}
    agg = iot.get("aggregates") or {}
    return {
        "api_version": config.API_VERSION,
        "documents_validated": len(docs),
        "json_files_on_disk": n_json,
        "iot_total_readings": agg.get("total_readings"),
        "iot_anomaly_count": agg.get("anomaly_count"),
        "iot_anomaly_rate": agg.get("anomaly_rate"),
        "mqtt_merge_url": config.MQTT_MERGE_URL,
    }


@app.get("/unified")
async def get_unified() -> dict:
    documents = load_all_documents()
    audit_ts = audit_tail_last_ts()

    async with httpx.AsyncClient() as client:
        merge_health = await _fetch_merge_health(client)
        iot_payload, iot_err = await _fetch_iot_payload(client)
        readings = await _fetch_readings(client, limit=500)
    if not readings and iot_payload:
        readings = iot_payload.get("recent_readings") or []

    generated_at = datetime.now(UTC).replace(microsecond=0).isoformat()

    return {
        "generated_at": generated_at,
        "health": {
            "api": {"status": "healthy", "version": config.API_VERSION},
            "mqtt_merge": merge_health,
            "dataset_out_dir": str(config.OUT_DIR),
            "iot_fetch_error": iot_err,
        },
        "documents": [d.model_dump() for d in documents],
        "validation_summary": build_validation_summary(documents, audit_ts),
        "normalized_rollups": build_normalized_rollups(documents),
        "iot_period_aggregates": build_iot_period_aggregates(documents, readings),
        "iot_live_strip": build_iot_live_strip(readings, limit=80),
        "openapi_url": "/docs",
    }


@app.get("/")
async def root() -> dict:
    return {
        "service": "Eco-Edge Part 2 API",
        "version": config.API_VERSION,
        "docs": "/docs",
        "endpoints": [
            "/health",
            "/ingest",
            "/documents",
            "/unified",
            "/metrics",
        ],
        "mqtt_merge": config.MQTT_MERGE_URL,
    }
