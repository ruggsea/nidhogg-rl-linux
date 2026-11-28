#!/bin/bash
# Claim: a round boundary is read from the verified room index, not the FLAG_P1/P2
# death debounce. Fixture (code_pau/tools/round_outcome_test.py): 29->20 is a match end,
# 29->35 / 35->29 are arena advances, every menu/lobby transition is None. The old
# death fixture (outcome_events_test.py) must still read its one flag death. If a live
# state/round_outcome_proof_*.json is present it must carry >=1 room boundary event.
set -e
cd "$(dirname "$0")/.."
RO=$(python3 code_pau/tools/round_outcome_test.py)
DE=$(python3 code_pau/tools/outcome_events_test.py)
python3 - "$RO" "$DE" <<'PY'
import json, sys, glob
ro = json.loads(sys.argv[1])
de = json.loads(sys.argv[2])
assert ro["all_expectations_match"] is True, ro
assert ro["n_boundaries"] == 3 and ro["n_advance"] == 2 and ro["n_match_end"] == 1, ro
assert ro["n_navigation"] == 5, ro
assert de["deaths_n"] == 1 and de["summary"]["rounds"] == 1, de
live = sorted(glob.glob("state/round_outcome_proof_*.json"))
assert live, "no live round_outcome_proof json in state/"
l = json.loads(open(live[-1]).read())
assert len(l.get("events") or []) >= 1, l
assert l.get("room_start") is not None and l.get("room_end") is not None, l
print("OK", {"fixture_boundaries": ro["n_boundaries"], "live": live[-1],
             "via": l.get("via"), "room_start": l["room_start"], "room_end": l["room_end"],
             "events": len(l["events"])})
PY