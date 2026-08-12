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
