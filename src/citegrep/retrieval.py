"""Hybrid retrieval + cross-encoder reranking.

Two-stage search:
1. Recall (cheap, wide): dense (BGE-M3) and sparse (BM25) each retrieve
   candidates; Qdrant fuses them with RRF in one call. The bi-encoders embedded
   everything ahead of time, so this is fast over the whole collection.
2. Precision (expensive, narrow): a cross-encoder re-scores the fused top-k by
   reading query and passage TOGETHER, which judges real relevance rather than
   vector proximity. Too slow for the whole collection, perfect for ~20.

The retriever returns ranked results carrying the payload (text, pages, spans)
so the caller can answer and cite. Reranking is behind an interface so tests
inject a fake and never load the model.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from qdrant_client import QdrantClient, models

from citegrep.embeddings import DenseEmbedder, SparseEmbedder
from citegrep.index import DENSE_NAME, SPARSE_NAME


@dataclass
class RetrievedChunk:
    chunk_id: str
    doc_id: str
    text: str
    pages: list[int]
    spans: list[dict]
    score: float  # rerank score if reranked, else the fusion score


class Reranker(Protocol):
    def rerank(
        self, query: str, candidates: list[RetrievedChunk], top_k: int
    ) -> list[RetrievedChunk]: ...


def _to_chunk(point, score: float) -> RetrievedChunk:
    p = point.payload
    return RetrievedChunk(
        chunk_id=p.get("chunk_id", ""),
        doc_id=p.get("doc_id", ""),
        text=p.get("text", ""),
        pages=p.get("pages", []),
        spans=p.get("spans", []),
        score=score,
    )


def hybrid_search(
    client: QdrantClient,
    collection: str,
    query: str,
    dense: DenseEmbedder,
    sparse: SparseEmbedder,
    candidates: int = 20,
) -> list[RetrievedChunk]:
    """Dense + BM25 prefetch, fused with RRF, returning `candidates` results.

    This is the recall stage. Uses Qdrant's Query API to run both arms and fuse
    server-side in a single round trip.
    """
    dense_q = dense.embed([query])[0]
    sparse_q = sparse.embed_query(query)

    res = client.query_points(
        collection_name=collection,
        prefetch=[
            models.Prefetch(query=dense_q, using=DENSE_NAME, limit=candidates),
            models.Prefetch(
                query=models.SparseVector(indices=sparse_q.indices, values=sparse_q.values),
                using=SPARSE_NAME,
                limit=candidates,
            ),
        ],
        query=models.FusionQuery(fusion=models.Fusion.RRF),
        limit=candidates,
        with_payload=True,
    )
    return [_to_chunk(p, p.score) for p in res.points]


def retrieve(
    client: QdrantClient,
    collection: str,
    query: str,
    dense: DenseEmbedder,
    sparse: SparseEmbedder,
    reranker: Reranker,
    candidates: int = 20,
    top_k: int = 5,
) -> list[RetrievedChunk]:
    """Full pipeline: hybrid recall -> cross-encoder rerank -> top_k."""
    fused = hybrid_search(client, collection, query, dense, sparse, candidates=candidates)
    if not fused:
        return []
    return reranker.rerank(query, fused, top_k=top_k)


class BGEReranker:
    """Cross-encoder reranker (BAAI/bge-reranker-v2-m3) via sentence-transformers.

    Reads [query, passage] pairs jointly and scores relevance. Runs on CPU;
    reranking ~20 candidates takes a second or two, which is fine per query.
    """

    MODEL = "BAAI/bge-reranker-v2-m3"

    def __init__(self, device: str | None = None) -> None:
        from sentence_transformers import CrossEncoder

        self._model = CrossEncoder(self.MODEL, device=device)

    def rerank(
        self, query: str, candidates: list[RetrievedChunk], top_k: int
    ) -> list[RetrievedChunk]:
        if not candidates:
            return []
        pairs = [(query, c.text) for c in candidates]
        scores = self._model.predict(pairs)
        rescored = [
            RetrievedChunk(
                chunk_id=c.chunk_id,
                doc_id=c.doc_id,
                text=c.text,
                pages=c.pages,
                spans=c.spans,
                score=float(s),
            )
            for c, s in zip(candidates, scores, strict=True)
        ]
        rescored.sort(key=lambda c: c.score, reverse=True)
        return rescored[:top_k]
