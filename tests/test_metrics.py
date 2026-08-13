"""Metric correctness on hand-checkable cases."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "eval"))
from metrics import ndcg_at_k, recall_at_k, reciprocal_rank


def test_recall_hit_and_miss() -> None:
    r = [[2], [8], [4], [1]]  # hit at rank 3 (page 4)
    assert recall_at_k(r, {4}, 5) == 1.0
    assert recall_at_k(r, {4}, 2) == 0.0


def test_mrr_rank_position() -> None:
    assert reciprocal_rank([[4], [2]], {4}) == 1.0
    assert reciprocal_rank([[2], [4]], {4}) == 0.5
    assert round(reciprocal_rank([[1], [2], [4]], {4}), 3) == 0.333
    assert reciprocal_rank([[1], [2]], {4}) == 0.0


def test_ndcg_rewards_higher_rank() -> None:
    high = ndcg_at_k([[4], [1], [2]], {4}, 3)
    low = ndcg_at_k([[1], [2], [4]], {4}, 3)
    assert high > low  # same hit, but ranked higher scores better


def test_multipage_gold() -> None:
    assert recall_at_k([[5], [7]], {7, 8}, 5) == 1.0  # overlap on page 7
