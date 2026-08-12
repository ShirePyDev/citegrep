"""`parse` CLI: turn a PDF into inspectable JSONL, one line per chunk.

This exists so you can SEE what the machine sees — open the JSONL and read how
a real paper gets carved into retrieval units, with page numbers and box counts.
It is the human check that no test can replace.

Usage:
    uv run python -m citegrep.cli.parse data/corpus/paper.pdf
    uv run python -m citegrep.cli.parse data/corpus/paper.pdf --out chunks.jsonl
    uv run python -m citegrep.cli.parse data/corpus/paper.pdf --tokens 400 --overlap 0.2
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys
from pathlib import Path

from citegrep.chunking import Chunk, chunk_document
from citegrep.parsing import NoTextLayerError, parse_pdf


def _chunk_to_dict(chunk: Chunk) -> dict:
    d = dataclasses.asdict(chunk)
    # quads are long; in JSONL we keep page + a box COUNT for readability,
    # plus the full quads under "spans" for downstream use.
    d["span_summary"] = [{"page": s["page"], "boxes": len(s["quads"])} for s in d["spans"]]
    return d


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="citegrep-parse", description=__doc__)
    ap.add_argument("pdf", type=Path, help="path to a PDF")
    ap.add_argument("--out", type=Path, help="write JSONL here (default: stdout)")
    ap.add_argument("--tokens", type=int, default=512, help="target tokens per chunk")
    ap.add_argument("--overlap", type=float, default=0.15, help="overlap ratio [0,1)")
    args = ap.parse_args(argv)

    try:
        doc = parse_pdf(args.pdf)
    except NoTextLayerError as e:
        print(f"REJECTED: {e}", file=sys.stderr)
        return 2
    except FileNotFoundError:
        print(f"No such file: {args.pdf}", file=sys.stderr)
        return 2

    chunks = chunk_document(doc, target_tokens=args.tokens, overlap_ratio=args.overlap)

    out = args.out.open("w") if args.out else sys.stdout
    try:
        for c in chunks:
            out.write(json.dumps(_chunk_to_dict(c), ensure_ascii=False) + "\n")
    finally:
        if args.out:
            out.close()

    print(
        f"{args.pdf.name}: {doc.total_words} words -> {len(chunks)} chunks "
        f"(~{args.tokens} tok, {int(args.overlap * 100)}% overlap)"
        + (f" -> {args.out}" if args.out else ""),
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
