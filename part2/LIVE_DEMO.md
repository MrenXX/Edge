# Live demo — one JPEG that exists on disk

Use this file for **Streamlit drag-and-drop** or the CLI smoke script (same path):

`D:\jects\Edge\WhatsApp Image 2026-04-27 at 21.39.25 (51).jpeg`

## Preconditions

1. `part2/.env` with `GEMINI_API_KEY` or `GOOGLE_API_KEY` (gitignored).
2. `pip install -r part2/dashboard/requirements.txt` (or pipeline `requirements.txt`) including **`google-genai`**.
3. In `part2/.env`, set **`GEMINI_MODEL=gemini-flash-latest`** if **`gemini-2.0-flash`** returns **429** (free-tier quota is per-model).
4. If the venue network is flaky, optionally set **`GEMINI_QUICK=1`** and **`GEMINI_HTTP_TIMEOUT_MS=90000`** (milliseconds).

## CLI smoke (writes `part2/pipeline/out/<stem>.json`)

```powershell
cd D:\jects\Edge
$env:GEMINI_QUICK="1"
$env:GEMINI_HTTP_TIMEOUT_MS="90000"
python part2\scripts\demo_extract_image.py "D:\jects\Edge\WhatsApp Image 2026-04-27 at 21.39.25 (51).jpeg"
```

## Streamlit

```powershell
cd D:\jects\Edge\part2\dashboard
$env:PYTHONPATH="D:\jects\Edge\part2\dashboard;D:\jects\Edge\part2\pipeline"
python -m streamlit run app.py
```

Drop the same JPEG in the **Glisser-déposer** area.
