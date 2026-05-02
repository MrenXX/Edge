"""Batch extract PDFs to JSON (+ JSONL audit)."""

from __future__ import annotations

import json
import sys
import threading
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from energy_extract.env_loader import load_all_dotenv
from energy_extract.gemini_extract import extract_document_path, extract_pdf_file
from energy_extract.models import ExtractedDocument


@dataclass
class BatchResult:
    succeeded: int
    total: int
    outputs: list[Path]
    audit_path: Path


def run_pdf_folder(
    data_dir: Path,
    out_dir: Path,
    *,
    max_pages: int = 8,
    model_name: str | None = None,
    jsonl_path: Path | None = None,
    log_print: bool = True,
) -> BatchResult:
    """
    Extract every PDF in ``data_dir`` (non-recursive). Writes ``<stem>.json`` per success.
    Appends one JSON line per file to ``jsonl_path`` (default ``out_dir/extraction_audit.jsonl``).
    """
    load_all_dotenv()
    out_dir.mkdir(parents=True, exist_ok=True)
    audit_path = jsonl_path or (out_dir / "extraction_audit.jsonl")
    outputs: list[Path] = []
    pdfs = sorted(p for p in data_dir.iterdir() if p.is_file() and p.suffix.lower() == ".pdf")
    ok = 0
    for pdf in pdfs:
        try:
            doc: ExtractedDocument = extract_pdf_file(
                pdf,
                max_pages=max_pages,
                model_name=model_name,
            )
            out = out_dir / f"{pdf.stem}.json"
            out.write_text(doc.model_dump_json(indent=2), encoding="utf-8")
            outputs.append(out)
            rec = {
                "source_file": pdf.name,
                "ok": True,
                "document_family": doc.document_family,
                "parser_path": doc.parser_path,
                "prompt_version": doc.prompt_version,
                "confidence_0_1": doc.confidence_0_1,
                "output_json": str(out),
                "ts": datetime.now(UTC).isoformat(),
            }
            with audit_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            if log_print:
                print(f"OK  {pdf.name} -> {out.name} ({doc.document_family})")
            ok += 1
        except Exception as e:
            rec = {
                "source_file": pdf.name,
                "ok": False,
                "error": type(e).__name__,
                "detail": str(e),
                "ts": datetime.now(UTC).isoformat(),
            }
            with audit_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            if log_print:
                print(f"FAIL {pdf.name}: {e}", file=sys.stderr)

    return BatchResult(succeeded=ok, total=len(pdfs), outputs=outputs, audit_path=audit_path)


def _append_audit_line(audit_path: Path, rec: dict, lock: threading.Lock) -> None:
    line = json.dumps(rec, ensure_ascii=False) + "\n"
    with lock:
        with audit_path.open("a", encoding="utf-8") as f:
            f.write(line)


def run_paths_parallel(
    paths: list[Path],
    out_dir: Path,
    *,
    max_pages: int = 8,
    model_name: str | None = None,
    max_workers: int = 3,
    jsonl_path: Path | None = None,
    log_print: bool = True,
) -> BatchResult:
    """Extract several PDFs/images in parallel (thread pool)."""
    from concurrent.futures import ThreadPoolExecutor, as_completed

    load_all_dotenv()
    out_dir.mkdir(parents=True, exist_ok=True)
    audit_path = jsonl_path or (out_dir / "extraction_audit.jsonl")
    lock = threading.Lock()
    outputs: list[Path] = []

    def _one(p: Path) -> tuple[bool, Path | None, str]:
        try:
            doc = extract_document_path(p, max_pages=max_pages, model_name=model_name)
            out = out_dir / f"{p.stem}.json"
            out.write_text(doc.model_dump_json(indent=2), encoding="utf-8")
            rec = {
                "source_file": p.name,
                "ok": True,
                "document_family": doc.document_family,
                "parser_path": doc.parser_path,
                "prompt_version": doc.prompt_version,
                "confidence_0_1": doc.confidence_0_1,
                "output_json": str(out),
                "ts": datetime.now(UTC).isoformat(),
            }
            _append_audit_line(audit_path, rec, lock)
            return True, out, doc.document_family
        except Exception as e:
            rec = {
                "source_file": p.name,
                "ok": False,
                "error": type(e).__name__,
                "detail": str(e),
                "ts": datetime.now(UTC).isoformat(),
            }
            _append_audit_line(audit_path, rec, lock)
            return False, None, str(e)

    workers = max(1, min(max_workers, len(paths)))
    ok = 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = {pool.submit(_one, p): p for p in paths}
        for fut in as_completed(futs):
            success, outp, info = fut.result()
            p = futs[fut]
            if success:
                ok += 1
                assert outp is not None
                outputs.append(outp)
                if log_print:
                    print(f"OK  {p.name} -> {outp.name} ({info})")
            else:
                if log_print:
                    print(f"FAIL {p.name}: {info}", file=sys.stderr)

    return BatchResult(succeeded=ok, total=len(paths), outputs=outputs, audit_path=audit_path)
