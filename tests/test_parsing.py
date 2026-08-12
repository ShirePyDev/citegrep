"""Parser and no-text-layer guard."""

from __future__ import annotations

from pathlib import Path

import pytest

from citegrep.parsing import NoTextLayerError, parse_pdf


def test_parses_pages_and_words(text_pdf: Path) -> None:
    doc = parse_pdf(text_pdf)
    assert len(doc.pages) == 2
    assert doc.total_words > 0
    assert all(p.number == i + 1 for i, p in enumerate(doc.pages))  # 1-based


def test_words_have_bounding_boxes(text_pdf: Path) -> None:
    doc = parse_pdf(text_pdf)
    w = doc.pages[0].words[0]
    assert w.text
    assert w.x1 > w.x0 and w.y1 > w.y0  # a real, non-degenerate box


def test_scanned_pdf_is_rejected(scanned_pdf: Path) -> None:
    with pytest.raises(NoTextLayerError):
        parse_pdf(scanned_pdf)
