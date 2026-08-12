#!/usr/bin/env python3
"""Read-only corpus diagnostic for citegrep Phase 1.

Purpose: decide FROM EVIDENCE whether our PDF corpus needs column-aware
extraction, and confirm every file has a real text layer (the ingest guard).
Reads the PDFs only; writes nothing, indexes nothing.

Run:  uv run python scripts/diagnose_corpus.py data/corpus/*.pdf

For each file it reports page count, words, no-text-layer pages, a TENTATIVE
column guess, and — most importantly — the first lines of a body page in
PyMuPDF's default reading order, so YOU can see whether columns read cleanly
or splice together. Trust your eyes over the heuristic.
"""

from __future__ import annotations

import sys
from pathlib import Path

try:
    import pymupdf
except ImportError:
    sys.exit("pymupdf not installed. Run:  uv add pymupdf")


def column_guess(page: pymupdf.Page) -> str:
    """Tentative layout label for one page. This is a HINT only; the printed
    sample text is the real evidence, so we return just the label."""
    words = page.get_text("words")
    n = len(words)
    if n == 0:
        return "NO-TEXT-LAYER"
    width = page.rect.width or 1.0
    centers = [((w[0] + w[2]) / 2) / width for w in words]
    mid = sum(1 for c in centers if 0.42 <= c <= 0.58) / n
    left = sum(1 for c in centers if c < 0.5)
    right = n - left
    balance = min(left, right) / max(left, right) if max(left, right) else 0.0
    if mid < 0.15 and balance > 0.4:
        return "two-column?"
    return "single-column?"


def body_sample(page: pymupdf.Page, lines: int = 5) -> list[str]:
    text = page.get_text().strip()
    return [ln for ln in text.splitlines() if ln.strip()][:lines]


def main(paths: list[str]) -> int:
    pdfs = sorted(Path(p) for p in paths)
    if not pdfs:
        print("No PDFs given. Usage: python scripts/diagnose_corpus.py data/corpus/*.pdf")
        return 1

    summary: list[tuple[str, str]] = []
    for pdf in pdfs:
        print("=" * 72)
        print(f"FILE: {pdf.name}")
        try:
            doc = pymupdf.open(pdf)
        except Exception as e:  # a diagnostic must survive any malformed file
            print(f"  !! could not open: {e}")
            summary.append((pdf.name, "OPEN-FAILED"))
            continue

        pages = doc.page_count
        empty = 0
        words_total = 0
        guesses: dict[str, int] = {}
        for pg in doc:
            label = column_guess(pg)
            words_total += len(pg.get_text("words"))
            if label == "NO-TEXT-LAYER":
                empty += 1
            else:
                guesses[label] = guesses.get(label, 0) + 1

        print(f"  pages: {pages} | words: {words_total} | no-text-layer pages: {empty}")
        if guesses:
            print(f"  column guess tally (HEURISTIC, verify by eye): {guesses}")

        body_idx = min(3, pages - 1)
        print(f"  --- default reading order, page {body_idx + 1} (first 5 lines) ---")
        for ln in body_sample(doc[body_idx]):
            print(f"    | {ln[:90]}")
        print("    ^ Do these read as clean, continuous sentences? Or do two unrelated")
        print("      sentences splice together mid-line? That answer decides column handling.")

        if empty == pages:
            verdict = "REJECT — no text layer (scanned)"
        elif empty:
            verdict = f"MOSTLY-OK — {empty} image page(s), likely figures"
        else:
            verdict = "TEXT-OK"
        print(f"  VERDICT: {verdict}")
        summary.append((pdf.name, verdict))

    print("=" * 72)
    print("SUMMARY")
    for name, v in summary:
        print(f"  {name:<46} {v}")
    print("\nNext: paste this whole output back. We read the sample lines together")
    print("and decide — evidence first — whether column-aware extraction is needed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
