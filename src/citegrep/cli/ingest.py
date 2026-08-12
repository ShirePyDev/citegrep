"""`ingest` CLI: parse -> chunk -> embed -> upsert a corpus into Qdrant.

This is the full ingestion pipeline. Run it on data/corpus/ to make every paper
searchable. It loads BGE-M3 (dense) and BM25 (sparse) once, then processes each
PDF: parse with bounding boxes, chunk with spans, embed both ways, upsert.

First run downloads the models (~2GB dense, few MB sparse) and caches them.
It reports the device actually in use, so a silent CPU fallback is visible.

Usage:
    uv run python -m citegrep.cli.ingest data/corpus/*.pdf
    uv run python -m citegrep.cli.ingest data/corpus/*.pdf --recreate
    uv run python -m citegrep.cli.ingest data/corpus/*.pdf --collection chunks --device cuda
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from qdrant_client import QdrantClient

from citegrep.chunking import chunk_document
from citegrep.embeddings import BGEM3Dense, BM25Sparse
from citegrep.index import IndexPoint, ensure_collection, upsert_points
from citegrep.parsing import NoTextLayerError, parse_pdf


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="citegrep-ingest", description=__doc__)
    ap.add_argument("pdfs", type=Path, nargs="+", help="PDF paths (globs expand in the shell)")
    ap.add_argument("--collection", default="chunks", help="Qdrant collection name")
    ap.add_argument("--qdrant-url", default="http://localhost:6333")
    ap.add_argument("--device", default=None, help="cuda | cpu | None (auto)")
    ap.add_argument("--tokens", type=int, default=512)
    ap.add_argument("--overlap", type=float, default=0.15)
    ap.add_argument("--recreate", action="store_true", help="drop and rebuild the collection")
    args = ap.parse_args(argv)

    print("Loading models (first run downloads ~2GB; cached after)...", file=sys.stderr)
    dense = BGEM3Dense(device=args.device)
    sparse = BM25Sparse()
    print(f"Dense model device: {dense.device}", file=sys.stderr)

    client = QdrantClient(url=args.qdrant_url)
    ensure_collection(client, args.collection, recreate=args.recreate)

    total_chunks = 0
    for pdf in args.pdfs:
        try:
            doc = parse_pdf(pdf)
        except NoTextLayerError as e:
            print(f"SKIP {pdf.name}: {e}", file=sys.stderr)
            continue
        chunks = chunk_document(doc, target_tokens=args.tokens, overlap_ratio=args.overlap)
        if not chunks:
            print(f"SKIP {pdf.name}: no chunks", file=sys.stderr)
            continue

        texts = [c.text for c in chunks]
        dense_vecs = dense.embed(texts)
        sparse_vecs = sparse.embed(texts)
        doc_id = pdf.stem

        points = [
            IndexPoint(
                chunk=c,
                doc_id=doc_id,
                dense=dv,
                sparse_indices=sv.indices,
                sparse_values=sv.values,
            )
            for c, dv, sv in zip(chunks, dense_vecs, sparse_vecs, strict=True)
        ]
        n = upsert_points(client, args.collection, points)
        total_chunks += n
        print(f"  {pdf.name}: {len(doc.pages)} pages -> {n} chunks indexed", file=sys.stderr)

    count = client.count(collection_name=args.collection).count
    print(
        f"\nDone. {total_chunks} chunks ingested; collection now holds {count} points.",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
