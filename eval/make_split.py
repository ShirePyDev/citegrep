"""Assign dev/test splits to a gold file (70/30 by default), deterministically.

Usage: uv run python eval/make_split.py eval/gold.jsonl --test-frac 0.3
Writes the split back into each row's "split" field (stable via seeded shuffle).
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("gold", type=Path)
    ap.add_argument("--test-frac", type=float, default=0.3)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args(argv)

    rows = [json.loads(x) for x in args.gold.read_text().splitlines() if x.strip()]
    rng = random.Random(args.seed)
    rng.shuffle(rows)
    n_test = round(len(rows) * args.test_frac)
    for i, r in enumerate(rows):
        r["split"] = "test" if i < n_test else "dev"
    rows.sort(key=lambda r: r["id"])
    args.gold.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n")
    print(f"Assigned {n_test} test / {len(rows) - n_test} dev (seed={args.seed})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
