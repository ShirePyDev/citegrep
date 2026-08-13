#!/usr/bin/env python3
"""Helper for labeling: find which page(s) contain a phrase, to fill answer_pages.

While writing a gold question, you often remember a fact but not its page.
This searches the INGESTED chunks in Qdrant for your phrase and shows the
matching chunks with their page numbers — so you can fill answer_pages
accurately instead of hunting through the PDF.

Usage:
    uv run python eval/find_page.py "316 examples"
    uv run python eval/find_page.py "access control" --doc "GuardAgent paper"
"""

from __future__ import annotations

import argparse

from qdrant_client import QdrantClient, models


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("phrase", help="text to search for (substring match)")
    ap.add_argument("--doc", default=None, help="restrict to one doc_id")
    ap.add_argument("--collection", default="chunks")
    ap.add_argument("--qdrant-url", default="http://localhost:6333")
    ap.add_argument("--limit", type=int, default=10)
    args = ap.parse_args(argv)

    client = QdrantClient(url=args.qdrant_url)

    # Scroll all points (small corpus) and substring-match locally — simple and
    # exact, which is what you want when locating a known phrase.
    flt = None
    if args.doc:
        flt = models.Filter(
            must=[models.FieldCondition(key="doc_id", match=models.MatchValue(value=args.doc))]
        )

    needle = args.phrase.lower()
    hits = []
    offset = None
    while True:
        points, offset = client.scroll(
            collection_name=args.collection,
            scroll_filter=flt,
            limit=256,
            offset=offset,
            with_payload=True,
        )
        for p in points:
            text = p.payload.get("text", "")
            if needle in text.lower():
                hits.append(
                    (
                        p.payload.get("doc_id"),
                        p.payload.get("pages"),
                        p.payload.get("chunk_id"),
                        text,
                    )
                )
        if offset is None:
            break

    if not hits:
        print(f"No chunk contains: {args.phrase!r}")
        return 1
    for doc, pages, cid, text in hits[: args.limit]:
        idx = text.lower().find(needle)
        snippet = text[max(0, idx - 40) : idx + 60].replace("\n", " ")
        print(f"[{doc}] pages={pages} ({cid})")
        print(f"    ...{snippet}...")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
