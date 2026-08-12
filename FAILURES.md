# Failure log

Real mistakes made while building this, kept on purpose. Each entry: date, what broke, root cause, fix, lesson. This file is part of the portfolio — a system whose failure modes are known and documented is more trustworthy than one that claims to have none.

## 2026-08 — Deploy assumed Docker; the target machine runs Podman

**What broke:** `make up` failed on the DGX with a traceback from `/usr/local/bin/docker-compose` (`ModuleNotFoundError: No module named 'dotenv'`).

**Root cause:** on this machine, `docker` is Podman's compatibility shim, and `docker compose` delegates to an abandoned Python docker-compose v1 script whose own dependencies are broken. The runtime was never Docker at all.

**Fix:** runtime-agnostic Makefile that drives containers directly and auto-detects `podman`/`docker`; Compose deferred until the stack has more than one service (DECISIONS 007).

**Lesson:** the CLI name does not identify the runtime. `docker --version` on day zero would have said "podman" and saved the surprise. Verify the platform, not the command.

## 2026-08 — uv's Python download blocked by an unreachable campus mirror

**What broke:** `uv sync` needed CPython 3.12 (not present on the system), tried to download a managed build, and failed with `Connection refused`.

**Root cause:** the machine is configured to fetch Python builds through a campus mirror (`repo.ai.gato`) that refused connections. General egress was fine — the uv installer itself had just downloaded from upstream.

**Fix:** point `UV_PYTHON_INSTALL_MIRROR` back at the upstream `python-build-standalone` release URL for this user.

**Lesson:** read layered errors bottom-up. The `Caused by:` chain ended in `Connection refused` plus a URL naming a host we never asked for — those two lines were the entire diagnosis.

## 2026-08 — Reran the fixed plan against the unfixed file

**What broke:** after the Podman fix was prepared, `make up` on the DGX failed with the exact same compose traceback as before.

**Root cause:** the hotfix was never applied to the target machine — the transfer step was skipped, so make executed the old recipe. The plan was fixed; the artifact was not.

**Fix:** apply the new Makefile, then gate on evidence before retrying: `make -n up` must print the podman commands, and the file checksum must match the reference.

**Lesson:** after deploying a fix, verify the artifact actually changed (dry-run, version, or hash) before rerunning the test. "I fixed it" is a claim about the repo; the machine only knows what is on its disk.

## 2026-08 — uv.lock leaked the campus mirror; CI couldn't resolve packages

**What broke:** after fixing the action pin, CI failed at `uv sync --frozen` — uv tried to fetch from `http://repo.ai.gato/...` and hit a DNS error on the runner.

**Root cause:** uv.lock records not just versions but the source URL of every package. Generated on the campus network, it baked the internal mirror repo.ai.gato into 437 entries. That host resolves only inside the university, so any clone off-campus (CI, an interviewer's laptop) cannot install.

**Fix:** regenerate against public PyPI — `UV_INDEX_URL=https://pypi.org/simple uv lock` — verify zero repo.ai.gato refs remain, commit the clean lock. Same versions and hashes, public sources.

**Lesson:** a lockfile can leak local infrastructure and destroy reproducibility for everyone outside your network. When committing a lock generated behind a corporate/campus proxy, verify its source URLs are public before pushing.

## 2026-08 — insert_textbox silently dropped test text

**What broke:** a chunker test fixture built with PyMuPDF `insert_textbox` produced a PDF the parser rejected as having no text layer.

**Root cause:** `insert_textbox` returns a negative value and renders nothing when the text overflows the box. The overflowing fixture text was silently discarded, so the "text" PDF genuinely had no text.

**Fix:** build fixtures with `insert_text` and explicit line positions. Caught by the parser's own guard during testing.

**Lesson:** the no-text-layer guard earned its keep on day one — it caught a malformed input before it could produce silently-empty chunks. Fail-loud beats fail-silent.

## 2026-08 — The mirror leak recurred a third time; fixed with a guard, not a note

**What broke:** Phase 1 CI failed at `uv sync --frozen` — uv.lock again pointed at repo.ai.gato (449 entries). Same root cause as two earlier entries.

**Root cause:** a `uv lock`/`uv sync` ran on the campus network without the public-index override, rewriting the lock with mirror URLs, and it got committed. Documenting the lesson twice did not prevent a third occurrence.

**Fix:** regenerate against public PyPI, AND add a pre-commit hook (scripts/check_lock_public.sh) that fails any commit whose uv.lock contains repo.ai.gato. The lesson is now enforced by tooling, not memory.

**Lesson:** a recurring mistake is a missing guardrail, not a knowledge gap. When the same failure happens twice, stop writing it down and start making it impossible.
