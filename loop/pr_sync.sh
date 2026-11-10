#!/bin/bash
# pr_sync.sh — post verified progress to the PR if anything verified has changed.
# Runs from the self-loop; silent unless tools/pr_update.py finds a new, corroborated fact.
set -uo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO" || exit 0
PY="${NID_PYTHON:-$HOME/Projects/nidhogg-rl/.venv/bin/python}"
"$PY" tools/pr_update.py 2>&1 | tail -3
