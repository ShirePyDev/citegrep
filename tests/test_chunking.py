"""Chunker: sizing, overlap, and span/page integrity."""

from __future__ import annotations

from pathlib import Path

from citegrep.chunking import chunk_document
from citegrep.parsing import parse_pdf


def test_produces_chunks_with_spans(text_pdf: Path) -> None:
    doc = parse_pdf(text_pdf)
    chunks = chunk_document(doc, target_tokens=128, overlap_ratio=0.15)
    assert chunks
    for c in chunks:
        assert c.text
        assert c.pages
        # every page a chunk claims must have a matching span
        assert {s.page for s in c.spans} == set(c.pages)


def test_every_word_has_a_box(text_pdf: Path) -> None:
    doc = parse_pdf(text_pdf)
    chunks = chunk_document(doc, target_tokens=128)
    for c in chunks:
        word_count = len(c.text.split())
        box_count = sum(len(s.quads) for s in c.spans)
        assert word_count == box_count


def test_consecutive_chunks_overlap(text_pdf: Path) -> None:
    doc = parse_pdf(text_pdf)
    chunks = chunk_document(doc, target_tokens=128, overlap_ratio=0.25)
    if len(chunks) < 2:
        return  # corpus too small to overlap; nothing to assert
    tail = chunks[0].text.split()[-5:]
    head = chunks[1].text.split()
    assert any(tail == head[i : i + 5] for i in range(max(1, len(head) - 5)))


def test_empty_document_yields_no_chunks() -> None:
    from citegrep.parsing import ParsedDocument

    empty = ParsedDocument(path=Path("empty.pdf"), pages=[])
    assert chunk_document(empty) == []
