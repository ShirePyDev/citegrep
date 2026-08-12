"""PDF parsing: text extraction with per-word bounding boxes.

Why bounding boxes from the start: citegrep's promise is citations you can
verify — a retrieved chunk highlighted on the exact page region it came from.
That requires knowing where every word sits on the page. We capture those
coordinates at parse time (nearly free) because reconstructing them later is
near-impossible.

We rely on PyMuPDF's default reading order. This was validated against the
real arXiv corpus (see scripts/diagnose_corpus.py): two-column papers extract
in correct order without custom column handling. If a future corpus needs it,
this is where column-aware reflow would go.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pymupdf


class NoTextLayerError(Exception):
    """Raised when a PDF has no extractable text on any page (e.g. scanned
    images). We reject loudly rather than silently index nothing."""


@dataclass
class Word:
    """One extracted word and its bounding box on the page.

    The box is PDF user-space coordinates: (x0, y0) top-left, (x1, y1)
    bottom-right, origin at the page's top-left. These feed citation
    highlighting downstream."""

    text: str
    x0: float
    y0: float
    x1: float
    y1: float


@dataclass
class Page:
    number: int  # 1-based page number, as a human would cite it
    width: float
    height: float
    words: list[Word] = field(default_factory=list)

    @property
    def text(self) -> str:
        return " ".join(w.text for w in self.words)


@dataclass
class ParsedDocument:
    path: Path
    pages: list[Page]

    @property
    def total_words(self) -> int:
        return sum(len(p.words) for p in self.pages)


def parse_pdf(path: str | Path) -> ParsedDocument:
    """Extract every page's words with bounding boxes.

    Raises NoTextLayerError if the whole document has no text layer.
    A document with *some* empty pages (figures) is fine — those pages
    simply contribute no words.
    """
    path = Path(path)
    doc = pymupdf.open(path)
    pages: list[Page] = []
    for i, page in enumerate(doc):
        raw = page.get_text("words")  # list of (x0,y0,x1,y1, word, block, line, word_no)
        words = [Word(text=w[4], x0=w[0], y0=w[1], x1=w[2], y1=w[3]) for w in raw]
        pages.append(
            Page(number=i + 1, width=page.rect.width, height=page.rect.height, words=words)
        )

    if all(len(p.words) == 0 for p in pages):
        raise NoTextLayerError(
            f"{path.name}: no text layer on any of {len(pages)} page(s). "
            "This looks like a scanned PDF; OCR is out of scope for citegrep."
        )
    return ParsedDocument(path=path, pages=pages)
