"""Chunking: group parsed words into retrieval units that remember their place.

A chunk is the unit we embed and retrieve. Design goals:
- Size targeted near an embedding-friendly token budget (default 512), because
  a chunk should hold one coherent idea: too small fragments an argument, too
  large blurs distinct points into one averaged vector.
- Overlap between consecutive chunks (default ~15%), so a thought split across
  a boundary still lives complete in at least one chunk.
- Every chunk carries spans: which page(s) it covers and the bounding boxes of
  its words, so a retrieved chunk can be highlighted on the source page.

Token counting here is a fast word-based ESTIMATE, not BGE-M3's exact
tokenizer. That is fine for choosing boundaries; exact token budgeting only
matters at embedding time (staying under the model's context limit).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from citegrep.parsing import ParsedDocument, Word

# Rough tokens-per-word for English academic prose. Real tokenizers split some
# words into multiple tokens; ~1.3 is a safe, consistent approximation for
# boundary decisions.
TOKENS_PER_WORD = 1.3


@dataclass
class Span:
    """The footprint of a chunk's words on one page: the page number and the
    bounding boxes (quads) of each word on that page."""

    page: int
    quads: list[tuple[float, float, float, float]] = field(default_factory=list)


@dataclass
class Chunk:
    id: str  # stable within a document: "<doc_stem>::<index>"
    text: str
    est_tokens: int
    pages: list[int]
    spans: list[Span]


def _est_tokens(word_count: int) -> int:
    return round(word_count * TOKENS_PER_WORD)


def _flat_words(doc: ParsedDocument) -> list[tuple[Word, int]]:
    """All words in reading order, each tagged with its 1-based page number."""
    out: list[tuple[Word, int]] = []
    for page in doc.pages:
        for w in page.words:
            out.append((w, page.number))
    return out


def _spans_for(words: list[tuple[Word, int]]) -> list[Span]:
    """Group a chunk's (word, page) pairs into per-page spans with quads."""
    by_page: dict[int, list[tuple[float, float, float, float]]] = {}
    for w, page in words:
        by_page.setdefault(page, []).append((w.x0, w.y0, w.x1, w.y1))
    return [Span(page=p, quads=q) for p, q in sorted(by_page.items())]


def chunk_document(
    doc: ParsedDocument,
    target_tokens: int = 512,
    overlap_ratio: float = 0.15,
) -> list[Chunk]:
    """Split a parsed document into overlapping, span-carrying chunks."""
    if not 0.0 <= overlap_ratio < 1.0:
        raise ValueError("overlap_ratio must be in [0, 1)")

    words = _flat_words(doc)
    if not words:
        return []

    target_words = max(1, round(target_tokens / TOKENS_PER_WORD))
    step = max(1, round(target_words * (1 - overlap_ratio)))
    stem = doc.path.stem

    chunks: list[Chunk] = []
    start = 0
    idx = 0
    while start < len(words):
        window = words[start : start + target_words]
        text = " ".join(w.text for w, _ in window)
        pages = sorted({page for _, page in window})
        chunks.append(
            Chunk(
                id=f"{stem}::{idx}",
                text=text,
                est_tokens=_est_tokens(len(window)),
                pages=pages,
                spans=_spans_for(window),
            )
        )
        idx += 1
        if start + target_words >= len(words):
            break  # this window reached the end; don't emit a trailing overlap-only chunk
        start += step
    return chunks
