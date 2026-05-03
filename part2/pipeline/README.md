# Part 2 — document extraction (Gemini)

PDFs → PNG (PyMuPDF) → **Gemini** (`google-genai`) → validated JSON per [plan_part2.md](../plan_part2.md).

## Setup

```powershell
cd d:\jects\Edge\part2\pipeline
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

Copy [`.env.example`](.env.example) to `.env` and set **`GEMINI_API_KEY`** or **`GOOGLE_API_KEY`** (required for live calls).

## Run

Default input folder: repo `data factures et diverses-…/data factures et diverses`.

```powershell
python -m energy_extract
```

**Explicit files (PDF / JPEG / PNG / WebP), parallel:**

```powershell
python -m energy_extract --files "D:\jects\Edge\a.jpeg" "D:\jects\Edge\b.jpeg" --out-dir .\out --parallel 3
```

Options: `--data-dir`, `--out-dir`, `--max-pages`, `--model`, `--files`, `--parallel`.

Outputs: `out/<pdf-stem>.json` and `out/extraction_audit.jsonl`.

Env: **`GEMINI_API_KEY` or `GOOGLE_API_KEY`** (required), **`GEMINI_MODEL`** (default `gemini-flash-latest`; try `gemini-2.0-flash` if quota or routing issues), **`GEMINI_MAX_PAGES`**.

## Layout

- `energy_extract/models.py` — schema
- `energy_extract/pdf_render.py` — PDF → PNG
- `energy_extract/gemini_extract.py` — API + JSON
- `energy_extract/env_loader.py` — optional `.env` (repo / part2 / pipeline)
- `energy_extract/pipeline.py`, `energy_extract/cli.py`
