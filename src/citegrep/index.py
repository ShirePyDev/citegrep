"""Qdrant indexing: collection schema and idempotent upsert.

The collection holds one point per chunk with TWO vectors (dense + sparse) and
a payload carrying everything retrieval needs to answer and cite: the text, the
document id, the page numbers, and the bounding-box spans for highlighting.

Idempotency: a point's id is a deterministic hash of (doc_id, chunk_id, text).
Re-ingesting the same corpus overwrites the same ids instead of duplicating, so
ingestion can be re-run freely during development. This schema and flow were
validated against Qdrant 1.19.0.
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass

from qdrant_client import QdrantClient, models

from citegrep.chunking import Chunk
from citegrep.embeddings import DENSE_DIM

DENSE_NAME = "dense"
SPARSE_NAME = "bm25"


@dataclass
class IndexPoint:
    """A chunk plus its two vectors, ready to upsert."""

    chunk: Chunk
    doc_id: str
    dense: list[float]
    sparse_indices: list[int]
    sparse_values: list[float]


def point_id(doc_id: str, chunk_id: str, text: str) -> str:
    """Deterministic UUID so re-ingesting overwrites rather than duplicates."""
    digest = hashlib.sha256(f"{doc_id}\x00{chunk_id}\x00{text}".encode()).hexdigest()
    return str(uuid.UUID(digest[:32]))


def ensure_collection(client: QdrantClient, name: str, recreate: bool = False) -> None:
    """Create the collection with the validated dense+sparse schema if needed."""
    exists = client.collection_exists(name)
    if exists and recreate:
        client.delete_collection(name)
        exists = False
    if not exists:
        client.create_collection(
            collection_name=name,
            vectors_config={
                DENSE_NAME: models.VectorParams(size=DENSE_DIM, distance=models.Distance.COSINE)
            },
            sparse_vectors_config={
                SPARSE_NAME: models.SparseVectorParams(modifier=models.Modifier.IDF)
            },
        )


def to_qdrant_point(p: IndexPoint) -> models.PointStruct:
    return models.PointStruct(
        id=point_id(p.doc_id, p.chunk.id, p.chunk.text),
        vector={
            DENSE_NAME: p.dense,
            SPARSE_NAME: models.SparseVector(indices=p.sparse_indices, values=p.sparse_values),
        },
        payload={
            "doc_id": p.doc_id,
            "chunk_id": p.chunk.id,
            "text": p.chunk.text,
            "pages": p.chunk.pages,
            "spans": [{"page": s.page, "quads": s.quads} for s in p.chunk.spans],
        },
    )


def upsert_points(client: QdrantClient, name: str, points: list[IndexPoint]) -> int:
    if not points:
        return 0
    client.upsert(collection_name=name, points=[to_qdrant_point(p) for p in points])
    return len(points)
