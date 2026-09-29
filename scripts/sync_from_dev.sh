#!/bin/sh
# Re-copy connector/, skills/ and agents/ from the development sources, then run the offline tests in the
# repo copy. Idempotent: a second run with unchanged sources changes nothing. Never commits or pushes.
#   scripts/sync_from_dev.sh            sync + tests
#   scripts/sync_from_dev.sh --no-tests sync only
# Sources and the test interpreter come from scripts/sync.local.env (git-ignored; see sync.env.example).
set -eu
REPO="$(cd "$(dirname "$0")/.." && pwd)"
[ -f "$REPO/scripts/sync.local.env" ] && . "$REPO/scripts/sync.local.env"
export CONNECTOR_SRC="${CONNECTOR_SRC:-}" SKILLS_SRC="${SKILLS_SRC:-}" AGENTS_SRC="${AGENTS_SRC:-}"
python3 "$REPO/scripts/sync/sync.py"
[ "${1:-}" = "--no-tests" ] && exit 0

PY="${PYTHON:-$REPO/connector/.venv/bin/python}"
[ -x "$PY" ] || { echo "sync: no test interpreter ($PY); set PYTHON in scripts/sync.local.env" >&2; exit 1; }
WORK="$(mktemp -d "${TMPDIR:-/tmp}/ofm_tests.XXXXXX")"
trap 'rm -rf "$WORK"' EXIT
cd "$REPO/connector"
FUSION_MCP_SKILLS_ROOT="$REPO/skills" FUSION_MCP_OUT_DIR="$WORK/out" FUSION_MCP_CACHE_DIR="$WORK/cache" \
PYTHONDONTWRITEBYTECODE=1 PYTHONWARNINGS=ignore::ResourceWarning "$PY" -m unittest tests.test_offline tests.test_layout
