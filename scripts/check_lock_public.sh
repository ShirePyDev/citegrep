#!/usr/bin/env bash
# Guard: fail if uv.lock points at the campus mirror instead of public PyPI.
# The lock records package source URLs; on the campus network those become
# repo.ai.gato, which only resolves on-campus, breaking CI and external clones.
set -euo pipefail
if grep -q "repo.ai.gato" uv.lock; then
  echo "ERROR: uv.lock contains campus mirror URLs (repo.ai.gato)."
  echo "Fix:   UV_INDEX_URL=https://pypi.org/simple uv lock"
  exit 1
fi
