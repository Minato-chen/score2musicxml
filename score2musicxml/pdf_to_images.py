"""Rasterize a PDF's pages into images homr can consume."""
from __future__ import annotations

from pathlib import Path

import fitz  # PyMuPDF

IMAGE_SUFFIX = ".png"


def render_pdf_to_images(pdf_path: Path, out_dir: Path, dpi: int = 300) -> list[Path]:
    """Render each page of pdf_path into out_dir as page-0001.png, page-0002.png, ...

    Returns the list of image paths in page order.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    zoom = dpi / 72.0
    matrix = fitz.Matrix(zoom, zoom)

    image_paths: list[Path] = []
    with fitz.open(pdf_path) as doc:
        for page_index, page in enumerate(doc, start=1):
            pixmap = page.get_pixmap(matrix=matrix)
            image_path = out_dir / f"page-{page_index:04d}{IMAGE_SUFFIX}"
            pixmap.save(str(image_path))
            image_paths.append(image_path)
    return image_paths


def is_pdf(path: Path) -> bool:
    return path.suffix.lower() == ".pdf"
