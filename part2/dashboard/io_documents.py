"""Load extraction JSON from disk (backend surface until FastAPI exists)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

_PIPELINE_ROOT = Path(__file__).resolve().parent.parent / "pipeline"
import sys

if str(_PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(_PIPELINE_ROOT))

from energy_extract.models import ExtractedDocument  # noqa: E402


def default_out_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "pipeline" / "out"


def default_audit_path() -> Path:
    return default_out_dir() / "extraction_audit.jsonl"


def load_extracted_documents(out_dir: Path) -> tuple[list[ExtractedDocument], list[tuple[str, str]]]:
    """Return (valid documents, list of (filename, error) for skipped files)."""
    errors: list[tuple[str, str]] = []
    docs: list[ExtractedDocument] = []
    if not out_dir.is_dir():
        return [], [("<dir>", f"Not a directory: {out_dir}")]

    for path in sorted(out_dir.glob("*.json")):
        try:
            raw = path.read_text(encoding="utf-8")
            data = json.loads(raw)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as e:
            errors.append((path.name, str(e)))
            continue
        try:
            docs.append(ExtractedDocument.model_validate(data))
        except ValidationError as e:
            errors.append((path.name, str(e)[:500]))

    return docs, errors


def parse_audit_tail(audit_path: Path, max_lines: int = 80) -> list[dict[str, Any]]:
    """Last N non-empty lines of extraction_audit.jsonl (most recent at bottom)."""
    if not audit_path.is_file():
        return []
    lines = audit_path.read_text(encoding="utf-8", errors="replace").splitlines()
    rows: list[dict[str, Any]] = []
    for line in lines[-max_lines:]:
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            rows.append({"raw": line, "parse_error": True})
    return rows


def audit_latest_per_source(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep last entry per source_file (audit log is append-only)."""
    by_src: dict[str, dict[str, Any]] = {}
    for r in rows:
        src = r.get("source_file")
        if isinstance(src, str):
            by_src[src] = r
    return sorted(by_src.values(), key=lambda x: str(x.get("ts", "")))
