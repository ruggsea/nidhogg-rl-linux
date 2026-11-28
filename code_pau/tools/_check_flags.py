#!/usr/bin/env python3
"""Shared check for the flags-constant claim/falsifier (step 2 cut).

claim:   exit 0 iff the live alive flags never drop AND the tracker still fires on a
         forced drop (so the finding is not "the death path is broken").
falsify: exit 1 iff the claim holds, 0 otherwise.

  python3 code_pau/tools/_check_flags.py claim|falsify <live.json> <fixture.json>
"""
import json
import sys

mode, live_path, fix_path = sys.argv[1], sys.argv[2], sys.argv[3]
live = json.load(open(live_path))
fix = json.loads(fix_path)
assert live.get("entered") and live.get("bound"), live
# every live sample had both flags set -> no death can fire from live input
flags_constant = live.get("flags_seen") == [[1, 1]]
# the tracker still fires on a forced 4-sample drop -> the mechanism works, the input is inert
fix_fires = (fix["deaths_n"] == 1 and fix["summary"]["kills"] == 1
             and fix["summary"]["deaths"] == 0)
holds = flags_constant and fix_fires
print("OK" if holds else "NOT_HOLDING",
      {"live": live_path, "flags_seen": live.get("flags_seen"),
       "room_changes": live.get("room_changes"), "fix_fires": fix_fires,
       "fix_summary": fix["summary"]})
if mode == "falsify":
    raise SystemExit(1 if holds else 0)
raise SystemExit(0 if holds else 1)