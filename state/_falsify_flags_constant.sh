#!/bin/bash
# Falsifier: non-zero when the flags-constant claim HOLDS (same check, inverted exit).
set -e
cd "$(dirname "$0")/.."
LIVE=$(ls -t state/score_hunt_*.json | head -1)
FIX=$(python3 code_pau/tools/outcome_events_test.py)
python3 code_pau/tools/_check_flags.py falsify "$LIVE" "$FIX"