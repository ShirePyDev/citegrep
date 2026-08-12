"""Shared test fixtures. PDFs are generated in-code so no binary files are
committed and tests stay fast and self-contained."""

from __future__ import annotations

from pathlib import Path

import pymupdf
import pytest


@pytest.fixture
def text_pdf(tmp_path: Path) -> Path:
    """A 2-page PDF with real, selectable text laid out line by line."""
    doc = pymupdf.open()
    line = "Prompt injection is a documented attack against language model agents."
    for _ in range(2):
        page = doc.new_page()
        y = 80
        for _ in range(30):
            page.insert_text((72, y), line, fontsize=10)
            y += 18
    path = tmp_path / "text.pdf"
    doc.save(path)
    return path


@pytest.fixture
def scanned_pdf(tmp_path: Path) -> Path:
    """A PDF whose only content is a filled rectangle — no text layer."""
    doc = pymupdf.open()
    doc.new_page().draw_rect(pymupdf.Rect(80, 80, 500, 700), fill=(0.8, 0.8, 0.8))
    path = tmp_path / "scanned.pdf"
    doc.save(path)
    return path
