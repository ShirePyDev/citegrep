# Decision log

Short records of decisions that shaped the project. Format: context, decision, why, what it cost. Newest at the bottom.

## 001 — No RAG framework (2026-08)

LangChain/LlamaIndex hide the retrieval mechanics this project exists to demonstrate and measure. The pipeline is small enough to own directly. Cost: we write plumbing (loaders, fusion calls) ourselves.

## 002 — uv + committed lockfile (2026-08)

`pyproject.toml` declares intent (version floors); `uv.lock` records the exact resolved set so every machine and CI run installs identical versions. Cost: one extra file to keep in sync (`uv sync` does it).

## 003 — src/ layout (2026-08)

Code lives in `src/documind/` and is installed into the venv, so tests import the installed package the same way production would. Prevents the classic "works from the repo root only" import bug. Cost: a build-system block in pyproject.

## 004 — Split /healthz (liveness) from /readyz (readiness) (2026-08)

Liveness never checks dependencies; readiness checks Qdrant and returns 503 when it is unreachable. A liveness probe that checks dependencies makes orchestrators restart healthy processes during a dependency outage. Cost: two endpoints instead of one.

## 005 — Pin the Qdrant image tag (2026-08)

`qdrant/qdrant:v1.19.0`, not `latest`. Same reasoning as the lockfile: an unpinned tag means the infrastructure can change under us between two runs. Cost: we upgrade deliberately, by editing the tag.

## 006 — App runs on the host during development; only infrastructure is containerized (2026-08)

The API process needs direct CUDA access from Phase 3 (embedder + reranker in-process) and fast reload during development. Qdrant runs in Compose from day one. A fully containerized app profile is a Phase 7 deliverable. Cost: "works on my machine" risk until Phase 7 closes it.

## 007 — Container-runtime portability: direct `run` commands, Podman-first (2026-08)

The target DGX is a shared machine running rootless Podman behind a `docker` CLI shim, and its legacy compose provider is broken system software we won't (and can't, without root) repair. While the stack is a single service, the Makefile drives containers directly and auto-detects `podman` or `docker`. `docker-compose.yml` stays in the repo for Docker users and as the spec we consolidate on in Phase 5, when vLLM makes it a multi-service stack (likely via podman-compose installed in our own venv). Cost: the Qdrant run configuration temporarily lives in two places (Makefile and compose file) — accepted drift risk, with a scheduled resolution point.

## 008 — Default PDF extraction, no column handling (2026-08)

Evidence-first: `scripts/diagnose_corpus.py` ran on all 8 real arXiv papers and their body text extracted as clean, continuous prose in PyMuPDF's default reading order — no column interleaving. We therefore ship default extraction and do NOT build column-aware reflow. Cost: a future non-arXiv corpus with hard two-column layouts may need it; the parser has a documented seam where it would go.

## 009 — Chunk size 512 tokens, ~15% overlap, both configurable (2026-08)

512 balances retrieval precision (small enough to be one coherent idea) against context (large enough to be a complete thought) for BGE-M3. Overlap keeps a boundary-straddling thought whole in at least one chunk. Both are config args because Phase 4 tunes them against the gold set. Token counts are a word-based estimate, not BGE-M3's exact tokenizer — fine for boundaries, not for embedding-limit budgeting.

## 010 — Known limitation: hyphenated line-breaks not rejoined (2026-08)

PyMuPDF preserves words split across line-ends as "label- ing" with the hyphen intact. This is correct extraction (right reading order) but slightly degrades retrieval: "label- ing" embeds and BM25-matches differently from "labeling". Deferred, not fixed: we measure its impact in Phase 4 evaluation before deciding whether de-hyphenation logic earns its complexity. Filed as a measured-decision item, not a blind fix.

## 011 — Hybrid embeddings: BGE-M3 dense + fastembed BM25 sparse (2026-08)

Dense (BGE-M3 via sentence-transformers, 1024-dim, cosine) captures semantics; sparse (fastembed Qdrant/bm25, IDF modifier) captures exact rare terms (acronyms, dataset names). Two separate encoders behind Protocol interfaces so each is swappable and unit tests inject fakes without loading models. Chose classic BM25 over BGE-M3's own learned sparse for cleaner corpus-IDF and native Qdrant integration; BGE-M3-sparse and ColBERT are Phase 8 experiments. Validated the full schema+upsert+RRF flow against Qdrant 1.19.0.

## 012 — Idempotent ingestion via content-hash point ids (2026-08)

A point's id is a deterministic UUID from sha256(doc_id, chunk_id, text). Re-ingesting overwrites the same ids instead of duplicating, so ingestion is safe to re-run during development. Verified against real Qdrant: re-upsert kept the point count stable.
