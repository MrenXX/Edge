"""One-shot Gemini extract for live demo (JPEG/PDF path as argv). Loads part2/.env then pipeline/.env."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

_PIPELINE = Path(__file__).resolve().parent.parent / "pipeline"
_PART2 = _PIPELINE.parent
_REPO = _PART2.parent


def _load_env() -> None:
    for p in (_REPO / ".env", _PIPELINE / ".env", _PART2 / ".env"):
        if not p.is_file():
            continue
        try:
            from dotenv import load_dotenv

            load_dotenv(p, override=True)
        except ImportError:
            for line in p.read_text(encoding="utf-8").splitlines():
                s = line.strip()
                if not s or s.startswith("#") or "=" not in s:
                    continue
                k, _, v = s.partition("=")
                k, v = k.strip(), v.strip().strip('"').strip("'")
                if k and v:
                    os.environ[k] = v


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python demo_extract_image.py <path-to.jpg|png|pdf>", file=sys.stderr)
        return 2
    src = Path(sys.argv[1]).resolve()
    if not src.is_file():
        print(f"Not a file: {src}", file=sys.stderr)
        return 2

    _load_env()
    sys.path.insert(0, str(_PIPELINE))
    from energy_extract.gemini_extract import extract_document_path

    out_dir = _PIPELINE / "out"
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Extracting {src.name} …", flush=True)
    doc = extract_document_path(src)
    out_path = out_dir / f"{src.stem}.json"
    out_path.write_text(doc.model_dump_json(indent=2), encoding="utf-8")
    print(f"OK -> {out_path}", flush=True)
    print(f"family={doc.document_family} confidence={doc.confidence_0_1}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
