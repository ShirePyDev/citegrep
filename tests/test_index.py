"""Index module: deterministic ids, idempotency, payload shape.

These tests need no models and no running Qdrant — they test the pure logic:
id determinism and the PointStruct payload. The live-Qdrant integration is
exercised separately (and was validated manually against Qdrant 1.19.0).
"""

from __future__ import annotations

from citegrep.chunking import Chunk, Span
from citegrep.index import IndexPoint, point_id, to_qdrant_point


def _chunk() -> Chunk:
    return Chunk(
        id="doc::0",
        text="EICU-AC restricts access control.",
        est_tokens=8,
        pages=[4],
        spans=[Span(page=4, quads=[(1.0, 2.0, 3.0, 4.0)])],
    )


def test_point_id_is_deterministic() -> None:
    a = point_id("doc", "doc::0", "same text")
    b = point_id("doc", "doc::0", "same text")
    assert a == b  # same inputs -> same id (idempotency foundation)


def test_point_id_changes_with_text() -> None:
    a = point_id("doc", "doc::0", "text one")
    b = point_id("doc", "doc::0", "text two")
    assert a != b  # edited content -> new id


def test_payload_carries_spans_for_citation() -> None:
    p = IndexPoint(
        chunk=_chunk(),
        doc_id="guardagent",
        dense=[0.0] * 1024,
        sparse_indices=[1, 2],
        sparse_values=[0.5, 0.7],
    )
    ps = to_qdrant_point(p)
    assert ps.payload["doc_id"] == "guardagent"
    assert ps.payload["pages"] == [4]
    assert ps.payload["spans"] == [{"page": 4, "quads": [(1.0, 2.0, 3.0, 4.0)]}]
    # both vectors present under their named keys
    assert "dense" in ps.vector
    assert "bm25" in ps.vector
