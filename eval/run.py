"""Evaluation harness: score each retrieval arm against the gold set.

Runs dense-only, BM25-only, RRF-fused, and RRF+rerank over every gold question
and reports Recall@k, MRR, nDCG@k for each — the table that proves (or
disproves) that hybrid+rerank beats single-method retrieval.

Split-aware: --split dev or test. Tune on dev; report final numbers on test.

Usage:
    uv run python eval/run.py eval/gold.jsonl --split test
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

from qdrant_client import QdrantClient, models

from citegrep.embeddings import BGEM3Dense, BM25Sparse
from citegrep.index import DENSE_NAME, SPARSE_NAME
from citegrep.retrieval import BGEReranker, hybrid_search, retrieve

sys.path.insert(0, str(Path(__file__).parent))
from metrics import ndcg_at_k, recall_at_k, reciprocal_rank


def load_gold(path: Path, split: str | None) -> list[dict]:
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    if split:
        rows = [r for r in rows if r.get("split", "test") == split]
    return rows


def _pages_lists(chunks) -> list[list[int]]:
    return [c.pages for c in chunks]


def evaluate(gold: list[dict], client, collection, dense, sparse, reranker, k=5, candidates=20):
    arms = {"dense_only": [], "bm25_only": [], "rrf": [], "rrf_rerank": []}
    for row in gold:
        q = row["question"]
        gold_pages = set(row["answer_pages"])

        dvec = dense.embed([q])[0]
        svec = sparse.embed_query(q)
        sparse_vec = models.SparseVector(indices=svec.indices, values=svec.values)

        d = client.query_points(
            collection_name=collection, query=dvec, using=DENSE_NAME, limit=k, with_payload=True
        ).points
        b = client.query_points(
            collection_name=collection,
            query=sparse_vec,
            using=SPARSE_NAME,
            limit=k,
            with_payload=True,
        ).points
        fused = hybrid_search(client, collection, q, dense, sparse, candidates=candidates)
        reranked = retrieve(
            client, collection, q, dense, sparse, reranker, candidates=candidates, top_k=k
        )

        for name, chunks in [
            ("dense_only", [(p.payload.get("pages", [])) for p in d]),
            ("bm25_only", [(p.payload.get("pages", [])) for p in b]),
            ("rrf", _pages_lists(fused[:k])),
            ("rrf_rerank", _pages_lists(reranked)),
        ]:
            arms[name].append(
                {
                    "recall": recall_at_k(chunks, gold_pages, k),
                    "mrr": reciprocal_rank(chunks, gold_pages),
                    "ndcg": ndcg_at_k(chunks, gold_pages, k),
                }
            )
    return arms


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("gold", type=Path)
    ap.add_argument("--split", default=None, help="dev | test | (all if omitted)")
    ap.add_argument("--collection", default="chunks")
    ap.add_argument("--qdrant-url", default="http://localhost:6333")
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--candidates", type=int, default=20)
    args = ap.parse_args(argv)

    gold = load_gold(args.gold, args.split)
    if not gold:
        print(f"No gold rows for split={args.split}", file=sys.stderr)
        return 1
    print(
        f"Evaluating {len(gold)} questions (split={args.split or 'all'}, k={args.k})...",
        file=sys.stderr,
    )

    dense, sparse, reranker = BGEM3Dense(), BM25Sparse(), BGEReranker()
    client = QdrantClient(url=args.qdrant_url)
    arms = evaluate(
        gold, client, args.collection, dense, sparse, reranker, k=args.k, candidates=args.candidates
    )

    print(f"\n{'arm':<14} {'Recall@' + str(args.k):>10} {'MRR':>8} {'nDCG@' + str(args.k):>9}")
    print("-" * 44)
    for name, scores in arms.items():
        r = statistics.mean(s["recall"] for s in scores)
        m = statistics.mean(s["mrr"] for s in scores)
        n = statistics.mean(s["ndcg"] for s in scores)
        print(f"{name:<14} {r:>10.3f} {m:>8.3f} {n:>9.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
