"""Retrieval metrics: Recall@k, MRR, nDCG. Pure functions, no dependencies.

A result is "relevant" if the retrieved chunk's page(s) overlap the gold
answer_pages. Page-level (not chunk-level) so labels survive re-chunking.
"""

from __future__ import annotations

import math


def _is_hit(retrieved_pages: list[int], gold_pages: set[int]) -> bool:
    return bool(set(retrieved_pages) & gold_pages)


def recall_at_k(retrieved: list[list[int]], gold: set[int], k: int) -> float:
    """1.0 if any of the top-k retrieved chunks is on a gold page, else 0.0."""
    return 1.0 if any(_is_hit(r, gold) for r in retrieved[:k]) else 0.0


def reciprocal_rank(retrieved: list[list[int]], gold: set[int]) -> float:
    """1/rank of the first relevant chunk (rank 1-based); 0 if none."""
    for i, r in enumerate(retrieved, start=1):
        if _is_hit(r, gold):
            return 1.0 / i
    return 0.0


def ndcg_at_k(retrieved: list[list[int]], gold: set[int], k: int) -> float:
    """Binary-relevance nDCG@k. DCG rewards relevant chunks ranked higher;
    normalized by the ideal ordering."""
    dcg = 0.0
    for i, r in enumerate(retrieved[:k], start=1):
        if _is_hit(r, gold):
            dcg += 1.0 / math.log2(i + 1)
    # ideal: as many relevant as we could have, all at the top
    n_rel = min(sum(1 for r in retrieved[:k] if _is_hit(r, gold)), k)
    idcg = sum(1.0 / math.log2(i + 1) for i in range(1, n_rel + 1))
    return dcg / idcg if idcg > 0 else 0.0
