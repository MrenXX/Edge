"""CLI: batch Gemini extraction for PDFs in a folder or explicit files (parallel)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from energy_extract.env_loader import load_all_dotenv
from energy_extract.pipeline import run_paths_parallel, run_pdf_folder


PIPELINE_ROOT = Path(__file__).resolve().parent.parent


def main(argv: list[str] | None = None) -> int:
    load_all_dotenv()

    p = argparse.ArgumentParser(
        description="Extract STEG/SONEDE/gas/SCADA fields from PDFs or images (JPEG/PNG/WebP) via Gemini."
    )
    p.add_argument(
        "--files",
        nargs="+",
        type=Path,
        default=None,
        metavar="PATH",
        help="Explicit PDF or image paths; processed in parallel (ignores --data-dir).",
    )
    p.add_argument(
        "--parallel",
        type=int,
        default=3,
        help="Max parallel workers when using --files (default 3).",
    )
    p.add_argument(
        "--data-dir",
        type=Path,
        default=PIPELINE_ROOT.parent.parent
        / "data factures et diverses-20260501T231107Z-3-001"
        / "data factures et diverses",
        help="Folder containing PDFs only (non-recursive). Used when --files is omitted.",
    )
    p.add_argument(
        "--out-dir",
        type=Path,
        default=PIPELINE_ROOT / "out",
        help="Directory for per-file JSON + extraction_audit.jsonl",
    )
    p.add_argument("--max-pages", type=int, default=int(__import__("os").environ.get("GEMINI_MAX_PAGES", "8")))
    p.add_argument("--model", type=str, default=None, help="Override GEMINI_MODEL")
    args = p.parse_args(argv)

    out_dir = args.out_dir.resolve()

    if args.files:
        paths = [x.resolve() for x in args.files]
        for path in paths:
            if not path.is_file():
                print(f"ERROR: not a file: {path}", file=sys.stderr)
                return 2
        res = run_paths_parallel(
            paths,
            out_dir,
            max_pages=args.max_pages,
            model_name=args.model,
            max_workers=args.parallel,
        )
    else:
        data_dir = args.data_dir.resolve()
        if not data_dir.is_dir():
            print(f"ERROR: data dir not found: {data_dir}", file=sys.stderr)
            return 2
        res = run_pdf_folder(
            data_dir,
            out_dir,
            max_pages=args.max_pages,
            model_name=args.model,
        )

    print(f"Done. {res.succeeded}/{res.total} succeeded. Audit: {res.audit_path}")
    return 0 if res.succeeded == res.total else 1


if __name__ == "__main__":
    raise SystemExit(main())
