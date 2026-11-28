#!/bin/bash
# Claim (step 2 cut): on the live game the spy's alive flags never drop, so the bridge's
# event-tied death (outcome_events.OutcomeTracker) cannot fire from live input. Evidence:
# state/score_hunt_*.json from a 150 s live match reports flags_seen == [[1,1]] (both flags
# set in every observed sample). The fixture still fires on a forced drop, so the check is
# not vacuous. The tracker's room half stays valid (spy score slot == ROOM_OFF read).
set -e
cd "$(dirname "$0")/.."
LIVE=$(ls -t state/score_hunt_*.json | head -1)
FIX=$(python3 code_pau/tools/outcome_events_test.py)
python3 code_pau/tools/_check_flags.py claim "$LIVE" "$FIX"