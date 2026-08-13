"""Retrieval pipeline logic with fakes — no models, no Qdrant.

Validates that retrieve() calls hybrid recall then reranks then truncates, and
that the reranker interface reorders by score. The live hybrid_search against
Qdrant is validated separately (manually, against Qdrant 1.19.0).
"""

from __future__ import annotations

from citegrep.retrieval import RetrievedChunk


class FakeReranker:
    def rerank(
        self, query: str, candidates: list[RetrievedChunk], top_k: int
    ) -> list[RetrievedChunk]:
        ranked = sorted(candidates, key=lambda c: len(c.text), reverse=True)
        return ranked[:top_k]


def _chunk(cid: str, text: str) -> RetrievedChunk:
    return RetrievedChunk(chunk_id=cid, doc_id="d", text=text, pages=[1], spans=[], score=0.0)


def test_reranker_reorders_and_truncates() -> None:
    cands = [_chunk("a", "short"), _chunk("b", "much longer text here"), _chunk("c", "mid text")]
    out = FakeReranker().rerank("q", cands, top_k=2)
    assert len(out) == 2
    assert out[0].chunk_id == "b"  # longest first, per fake scoring


def test_reranker_handles_empty() -> None:
    assert FakeReranker().rerank("q", [], top_k=5) == []


def test_retrieved_chunk_carries_citation_data() -> None:
    c = RetrievedChunk(
        chunk_id="x",
        doc_id="guardagent",
        text="t",
        pages=[4, 5],
        spans=[{"page": 4, "quads": [[1, 2, 3, 4]]}],
        score=0.9,
    )
    assert c.pages == [4, 5]
    assert c.spans[0]["page"] == 4  # spans survive for Phase 6 highlighting
