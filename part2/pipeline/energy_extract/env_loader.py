"""Load .env from repo root, part2/, then part2/pipeline/ (later files override)."""

from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

# energy_extract/env_loader.py -> parents: energy_extract, pipeline, part2, repo
_PIPELINE_ROOT = Path(__file__).resolve().parent.parent
_PART2_ROOT = _PIPELINE_ROOT.parent
_REPO_ROOT = _PART2_ROOT.parent


def load_all_dotenv() -> None:
    """Load optional .env files so GEMINI_API_KEY is found wherever the team put it."""
    for path in (
        _REPO_ROOT / ".env",
        _PART2_ROOT / ".env",
        _PIPELINE_ROOT / ".env",
    ):
        if path.is_file():
            load_dotenv(path, override=True)
