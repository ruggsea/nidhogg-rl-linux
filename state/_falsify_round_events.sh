#!/bin/bash
# Falsifier: non-zero when the event-tied outcome claim HOLDS.
set -e
cd "$(dirname "$0")/.."
OUT=$(python3 code_pau/tools/outcome_events_test.py)
python3 - "$OUT" <<'PY'
import json, sys, glob
d = json.loads(sys.argv[1])
s = d["summary"]
holds = (d["deaths_n"] == 1 and s["rounds"] == 1 and s["kills"] == 1
         and s["deaths"] == 0 and d["rounds_left_arena"] == 1)
live = sorted(glob.glob("state/round_source_proof_*.json"))
if live:
    l = json.loads(open(live[-1]).read())
    holds = holds and l.get("match") is True and l.get("mem_room") == l.get("spy_room")
raise SystemExit(1 if holds else 0)
PY