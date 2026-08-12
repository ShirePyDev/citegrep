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
