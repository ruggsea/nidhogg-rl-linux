#!/bin/bash
# Falsifier: rc=1 when the room-index round-boundary claim HOLDS.
set -e
cd "$(dirname "$0")/.."
RO=$(python3 code_pau/tools/round_outcome_test.py)
DE=$(python3 code_pau/tools/outcome_events_test.py)
python3 - "$RO" "$DE" <<'PY'
import json, sys, glob
ro = json.loads(sys.argv[1])
de = json.loads(sys.argv[2])
holds = (ro["all_expectations_match"] is True and ro["n_boundaries"] == 3
         and ro["n_advance"] == 2 and ro["n_match_end"] == 1 and ro["n_navigation"] == 5
         and de["deaths_n"] == 1 and de["summary"]["rounds"] == 1)
live = sorted(glob.glob("state/round_outcome_proof_*.json"))
if live:
    l = json.loads(open(live[-1]).read())
    holds = holds and len(l.get("events") or []) >= 1
raise SystemExit(1 if holds else 0)
PY