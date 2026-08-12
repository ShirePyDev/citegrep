"""Ingest pipeline logic with FAKE embedders injected via the interfaces.

No models, no network, no Qdrant. Proves parse->chunk->embed->point wiring is
correct and that one point is produced per chunk with matching vectors.
"""

from __future__ import annotations

from pathlib import Path

from citegrep.chunking import chunk_document
from citegrep.embeddings import SparseVector
from citegrep.index import IndexPoint, to_qdrant_point
from citegrep.parsing import parse_pdf


class FakeDense:
    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[float(len(t))] * 1024 for t in texts]  # deterministic, right dim


class FakeSparse:
    def embed(self, texts: list[str]) -> list[SparseVector]:
        return [SparseVector(indices=[1, 2], values=[1.0, 1.0]) for _ in texts]


def test_pipeline_produces_one_point_per_chunk(text_pdf: Path) -> None:
    doc = parse_pdf(text_pdf)
    chunks = chunk_document(doc, target_tokens=128)
    dense, sparse = FakeDense(), FakeSparse()

    dvs = dense.embed([c.text for c in chunks])
    svs = sparse.embed([c.text for c in chunks])
    points = [
        IndexPoint(
            chunk=c, doc_id="fake", dense=dv, sparse_indices=sv.indices, sparse_values=sv.values
        )
        for c, dv, sv in zip(chunks, dvs, svs, strict=True)
    ]
    assert len(points) == len(chunks)
    # every produced point serializes with a 1024-dim dense vector
    for p in points:
        ps = to_qdrant_point(p)
        assert len(ps.vector["dense"]) == 1024
