# citegrep

PDF retrieval with page-level provenance: extracted chunks retain their source pages and word bounding boxes.

Retrieval combines dense embeddings and BM25 with reciprocal rank fusion (RRF), then reranks candidates with a cross-encoder.

<<<<<<< HEAD
**Implemented scope: Phases 0–3; Phase 4 evaluation tooling is in place, but results have not been published.** The repository contains the parsing, indexing, and retrieval pipeline, plus a 92-question labeled set (64 dev / 28 test). No retrieval-metrics table is included because a reproducible run against the indexed evaluation corpus has not been recorded. The PDF corpus and an indexed Qdrant collection are not included, so the scores cannot be reproduced from this checkout alone.
=======
**Implemented scope: Phases 0–4.** The repository contains the parsing, indexing, and retrieval pipeline, plus Phase 4 evaluation tooling and a 92-question labeled set (64 dev / 28 test). It does not contain a saved retrieval-metrics report.
>>>>>>> 6789f651ad3773a84ce48593093d97016764ccbc

### Phase status

- **Phase 0 — scaffold:** FastAPI app, health probes, project tooling, and CI.
- **Phase 1 — PDF parsing and chunking:** extract text with word bounding boxes; split it into chunks; inspect results with the parse CLI.
- **Phase 2 — embeddings and indexing:** BGE-M3 dense and BM25 sparse embeddings, Qdrant collection/upsert logic, and an ingest CLI.
- **Phase 3 — retrieval:** dense and BM25 search fused with RRF, cross-encoder reranking, and a `/debug/retrieve` endpoint exposing the retrieval arms.
<<<<<<< HEAD
- **Phase 4 — evaluation in progress:** the evaluator computes Recall@k, MRR, and nDCG for four retrieval arms; page-level gold labels and a dev/test split are checked in. The repository does not include retrieval results.
=======
- **Phase 4 — evaluation:** Recall@k, MRR, and nDCG evaluation across four retrieval arms, with page-level gold labels and a dev/test split.
>>>>>>> 6789f651ad3773a84ce48593093d97016764ccbc

The current API provides `/healthz`, `/readyz`, and `/debug/retrieve`. The retrieval endpoint returns ranked chunk snippets and page numbers; it is not an answer-generation endpoint, and this repository does not include a UI that highlights citations in a PDF. The stored bounding boxes provide provenance data for such a feature, but do not themselves render citations.

The evaluation harness and labels are checked in, but the CI workflow runs lint and unit tests—not the corpus retrieval evaluation. Run the evaluation separately against a Qdrant collection containing the indexed evaluation corpus. The current metrics compare page numbers with the gold `answer_pages`; they do not scope relevance checks by `doc_id`, so interpret results as page-level measurements.

```bash
uv run python eval/run.py eval/gold.jsonl --split dev
uv run python eval/run.py eval/gold.jsonl --split test
```

Use the dev split for tuning and reserve the test split for final reporting.
<<<<<<< HEAD
=======

## Stack

Python 3.12 · FastAPI · Qdrant · BGE-M3 · BM25 · uv · Docker or Podman

## Quickstart

```bash
make install   # create venv, install pinned dependencies
make up        # start Qdrant in Docker or Podman
make dev       # run the API on :8000
```

From another terminal, parse a PDF and ingest it into Qdrant:

```bash
uv run python -m citegrep.cli.parse path/to/paper.pdf
uv run python -m citegrep.cli.ingest path/to/paper.pdf
```

First use may download and cache the BGE-M3 and BM25 models during ingestion; the cross-encoder reranker is loaded when `/debug/retrieve` is called. The repository does not include a PDF corpus. Ingestion stores chunk text, vectors, and source metadata in Qdrant, not the original PDF files.

Check the health probes and inspect retrieval results:

```bash
curl http://localhost:8000/healthz
curl http://localhost:8000/readyz
curl "http://localhost:8000/debug/retrieve?q=your%20question"
>>>>>>> 6789f651ad3773a84ce48593093d97016764ccbc

## Stack

Python 3.12 · FastAPI · Qdrant · BGE-M3 · BM25 · uv · Docker or Podman

## Quickstart

```bash
make install   # create venv, install pinned dependencies
make up        # start Qdrant in Docker or Podman
make dev       # run the API on :8000
```

From another terminal, parse a PDF and ingest it into Qdrant:

```bash
uv run python -m citegrep.cli.parse path/to/paper.pdf
uv run python -m citegrep.cli.ingest path/to/paper.pdf
```

First use may download and cache the BGE-M3 and BM25 models during ingestion; the cross-encoder reranker is loaded when `/debug/retrieve` is called. The repository does not include a PDF corpus. Ingestion stores chunk text, vectors, and source metadata in Qdrant, not the original PDF files.

Check the health probes and inspect retrieval results:

```bash
curl http://localhost:8000/healthz
curl http://localhost:8000/readyz
curl "http://localhost:8000/debug/retrieve?q=your%20question"
```

## Development

```bash
make check     # lint + tests, exactly what CI runs
make format    # auto-fix style
make help      # list all targets
```

Design decisions are logged in [docs/DECISIONS.md](docs/DECISIONS.md). Mistakes worth remembering go in [FAILURES.md](FAILURES.md).

## License

This project is licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE).
