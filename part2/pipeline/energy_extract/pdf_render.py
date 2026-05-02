"""Render PDF pages to PNG bytes for vision models."""

from __future__ import annotations

from pathlib import Path

import fitz  # PyMuPDF


def pdf_to_png_pages(
    pdf_path: Path,
    *,
    max_pages: int = 8,
    dpi: float = 144.0,
) -> list[bytes]:
    """Return PNG bytes per page, first `max_pages` only."""
    doc = fitz.open(pdf_path)
    try:
        n = min(doc.page_count, max_pages)
        zoom = dpi / 72.0
        mat = fitz.Matrix(zoom, zoom)
        out: list[bytes] = []
        for i in range(n):
            page = doc.load_page(i)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            out.append(pix.tobytes("png"))
        return out
    finally:
        doc.close()
