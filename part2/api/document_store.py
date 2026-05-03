"""Load and validate extraction JSON from disk (pipeline `ExtractedDocument` schema)."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from energy_extract.models import ExtractedDocument

from api.config import OUT_DIR

logger = logging.getLogger(__name__)


def ensure_out_dir() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)


def iter_json_paths() -> list[Path]:
    ensure_out_dir()
    if not OUT_DIR.is_dir():
        return []
    paths = sorted(p for p in OUT_DIR.glob("*.json") if p.is_file())
    return paths


def load_all_documents() -> list[ExtractedDocument]:
    docs: list[ExtractedDocument] = []
    for path in iter_json_paths():
        try:
            raw = path.read_text(encoding="utf-8")
            data = json.loads(raw)
            docs.append(ExtractedDocument.model_validate(data))
        except Exception as e:
            logger.warning("Skip invalid JSON %s: %s", path.name, e)
    return docs


def load_document_by_stem(stem: str) -> ExtractedDocument | None:
    path = OUT_DIR / f"{stem}.json"
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return ExtractedDocument.model_validate(data)
    except Exception as e:
        logger.warning("Invalid document %s: %s", path.name, e)
        return None


def audit_tail_last_ts() -> str | None:
    """Best-effort last `ts` from extraction_audit.jsonl."""
    audit = OUT_DIR / "extraction_audit.jsonl"
    if not audit.is_file():
        return None
    try:
        lines = audit.read_text(encoding="utf-8").strip().splitlines()
        if not lines:
            return None
        last = json.loads(lines[-1])
        return last.get("ts")
    except Exception:
        return None
