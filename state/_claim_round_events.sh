#!/bin/bash
# Claim: the bridge's kills/deaths/round counter are event-tied, not a motion heuristic.
# Fixture (code_pau/tools/outcome_events_test.py): a one-sample P1 flag drop is a flicker
# and does not count; a four-sample P2 flag drop is one death, one round, one kill, winner
# P1; a room 29 -> 20 change is a round-boundary room event. If a live
# state/round_source_proof_*.json is present, the spy's tracked room must equal the direct
# ROOM_OFF read at the same pid.
set -e
cd "$(dirname "$0")/.."
OUT=$(python3 code_pau/tools/outcome_events_test.py)
python3 - "$OUT" <<'PY'
import json, sys, glob
d = json.loads(sys.argv[1])
s = d["summary"]
assert d["deaths_n"] == 1, d
assert s["rounds"] == 1 and s["kills"] == 1 and s["deaths"] == 0, s
assert d["deaths"][0]["who"] == "P2" and d["deaths"][0]["winner"] == "P1", d["deaths"]
assert d["rounds_left_arena"] == 1, d
live = sorted(glob.glob("state/round_source_proof_*.json"))
assert live, "no live round_source_proof json in state/"
l = json.loads(open(live[-1]).read())
assert l.get("match") is True and l.get("mem_room") == l.get("spy_room"), l
print("OK", {"fixture": s, "live": live[-1], "mem_room": l["mem_room"], "spy_room": l["spy_room"]})
PY