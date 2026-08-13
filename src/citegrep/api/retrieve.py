"""Retrieval endpoints.

/debug/retrieve is a portfolio centerpiece: it returns EACH arm's ranked list
(dense-only, BM25-only, fused, reranked) side by side, so you can see hybrid
search and reranking actually changing the ranking — the visible proof that this
beats naive top-k similarity.

Models load once at app startup (they are heavy). In this phase they are wired
lazily via a module-level holder so importing the router does not load models,
keeping tests fast.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query
from pydantic import BaseModel
from qdrant_client import QdrantClient, models

from citegrep.embeddings import BGEM3Dense, BM25Sparse
from citegrep.index import DENSE_NAME, SPARSE_NAME
from citegrep.retrieval import BGEReranker, RetrievedChunk, hybrid_search, retrieve

router = APIRouter(tags=["retrieval"])


class _Models:
    """Lazy singleton holder so models load once, on first query, not at import."""

    dense: BGEM3Dense | None = None
    sparse: BM25Sparse | None = None
    reranker: BGEReranker | None = None

    @classmethod
    def load(cls) -> None:
        if cls.dense is None:
            cls.dense = BGEM3Dense()
            cls.sparse = BM25Sparse()
            cls.reranker = BGEReranker()


class ChunkOut(BaseModel):
    chunk_id: str
    doc_id: str
    pages: list[int]
    score: float
    text: str


def _out(chunks: list[RetrievedChunk]) -> list[ChunkOut]:
    return [
        ChunkOut(
            chunk_id=c.chunk_id, doc_id=c.doc_id, pages=c.pages, score=c.score, text=c.text[:300]
        )
        for c in chunks
    ]


class DebugRetrieveOut(BaseModel):
    query: str
    dense_only: list[ChunkOut]
    bm25_only: list[ChunkOut]
    fused_rrf: list[ChunkOut]
    reranked: list[ChunkOut]


def _single_arm(client: QdrantClient, collection: str, query_vec, using: str, limit: int):
    res = client.query_points(
        collection_name=collection, query=query_vec, using=using, limit=limit, with_payload=True
    )
    from citegrep.retrieval import _to_chunk

    return [_to_chunk(p, p.score) for p in res.points]


@router.get("/debug/retrieve", response_model=DebugRetrieveOut)
def debug_retrieve(
    q: Annotated[str, Query(description="search query")],
    collection: str = "chunks",
    candidates: int = 20,
    top_k: int = 5,
    qdrant_url: str = "http://localhost:6333",
) -> DebugRetrieveOut:
    _Models.load()
    client = QdrantClient(url=qdrant_url)

    dvec = _Models.dense.embed([q])[0]
    svec = _Models.sparse.embed_query(q)
    sparse_vec = models.SparseVector(indices=svec.indices, values=svec.values)

    dense_only = _single_arm(client, collection, dvec, DENSE_NAME, top_k)
    bm25_only = _single_arm(client, collection, sparse_vec, SPARSE_NAME, top_k)
    fused = hybrid_search(
        client, collection, q, _Models.dense, _Models.sparse, candidates=candidates
    )
    reranked = retrieve(
        client,
        collection,
        q,
        _Models.dense,
        _Models.sparse,
        _Models.reranker,
        candidates=candidates,
        top_k=top_k,
    )
    return DebugRetrieveOut(
        query=q,
        dense_only=_out(dense_only),
        bm25_only=_out(bm25_only),
        fused_rrf=_out(fused[:top_k]),
        reranked=_out(reranked),
    )
