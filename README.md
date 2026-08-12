# DocuMind

RAG over your PDFs with citations you can actually check: every answer links back to the exact passage, highlighted on the source page.

Retrieval is hybrid (dense embeddings + BM25, fused with RRF) followed by a cross-encoder reranking stage. Answers that the corpus cannot support are refused instead of guessed.

**Status: Phase 0 — project scaffold.** The API currently exposes health probes only. Parsing, indexing, retrieval, and generation land in the next phases, each gated by tests and (from Phase 4) retrieval metrics on a hand-labeled gold set.

## Stack

Python 3.12 · FastAPI · Qdrant · uv · Docker Compose

## Quickstart

```bash
make install   # create venv, install pinned dependencies
make up        # start Qdrant in Docker
make dev       # run the API on :8000
```

Then:

```bash
curl localhost:8000/healthz   # liveness: process is up
curl localhost:8000/readyz    # readiness: Qdrant reachable (503 if not)
```

## Development

```bash
make check     # lint + tests, exactly what CI runs
make format    # auto-fix style
make help      # list all targets
```

Design decisions are logged in [docs/DECISIONS.md](docs/DECISIONS.md). Mistakes worth remembering go in [FAILURES.md](FAILURES.md).
