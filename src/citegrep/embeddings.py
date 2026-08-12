"""Embedding models: dense (BGE-M3) and sparse (BM25).

Two representations because meaning and words are different signals:
- Dense (BGE-M3, 1024-dim) captures semantics/paraphrase but blurs rare tokens.
- Sparse (BM25) captures exact terms — acronyms, dataset names, method jargon —
  weighted by corpus rarity (IDF).

Hybrid retrieval (Phase 3) fuses both. This module only produces the vectors;
storage and fusion live in index.py and the retriever.

Both loaders are wrapped behind small classes with a stable interface so tests
can substitute fakes and so a future swap (e.g. to a TEI HTTP service) touches
one file. The heavy model imports happen lazily inside the classes, so importing
this module is cheap and unit tests that inject fakes never load a model.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

DENSE_MODEL = "BAAI/bge-m3"
DENSE_DIM = 1024
SPARSE_MODEL = "Qdrant/bm25"


@dataclass
class SparseVector:
    """A sparse vector as parallel index/value lists — Qdrant's expected shape."""

    indices: list[int]
    values: list[float]


class DenseEmbedder(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...


class SparseEmbedder(Protocol):
    def embed(self, texts: list[str]) -> list[SparseVector]: ...
    def embed_query(self, text: str) -> SparseVector: ...


class BGEM3Dense:
    """Dense embedder backed by BGE-M3 via sentence-transformers.

    Loads on GPU when available. The model (~2GB) downloads from Hugging Face
    on first use and is cached; later runs are instant.
    """

    def __init__(self, device: str | None = None, batch_size: int = 32) -> None:
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(DENSE_MODEL, device=device)
        self._batch_size = batch_size
        # Report the device actually in use — guards against silent CPU fallback.
        self.device = str(self._model.device)

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        vecs = self._model.encode(
            texts,
            batch_size=self._batch_size,
            normalize_embeddings=True,  # cosine-ready
            show_progress_bar=False,
        )
        return [v.tolist() for v in vecs]


class BM25Sparse:
    """Sparse embedder backed by fastembed's classic BM25 (corpus-IDF).

    Note: BM25 is a document/query encoder — queries use embed_query so the
    library applies query-appropriate handling.
    """

    def __init__(self) -> None:
        from fastembed import SparseTextEmbedding

        self._model = SparseTextEmbedding(model_name=SPARSE_MODEL)

    def embed(self, texts: list[str]) -> list[SparseVector]:
        out: list[SparseVector] = []
        for emb in self._model.embed(texts):
            out.append(SparseVector(indices=emb.indices.tolist(), values=emb.values.tolist()))
        return out

    def embed_query(self, text: str) -> SparseVector:
        emb = next(self._model.query_embed(text))
        return SparseVector(indices=emb.indices.tolist(), values=emb.values.tolist())
