#!/bin/bash
# Claim: LIVE row in plan03_train_win_fit.jsonl (train_win probe, not hand-written hook summary).
set -e
python3 - <<'PY'
import json
from pathlib import Path
tw = Path("train_win.py").read_text()
assert "def fitness_delta_on_room_change" in tw, "train_win.py missing fitness_delta_on_room_change"
p = Path("state/plan03_train_win_fit.jsonl")
rows = [json.loads(l) for l in p.read_text().splitlines() if l.strip()]
live = [r for r in rows[::-1] if r.get("phase") == "summary" and r.get("live") is True]
assert live, (
    "no live:true summary in plan03_train_win_fit.jsonl — "
    "run tools/plan03_live_fit.py --forfeit on pau86 (or --poll-only during transition)"
)
s = live[0]
assert s.get("source") == "train_win_live_probe", s
assert s.get("probe") == "tools/plan03_live_fit.py", s
assert s.get("fitness_delta") not in (0, None) and s["fitness_before"] != s["fitness_after"], s
tr = s.get("transitions") or []
assert tr and tr[0].get("kind") == "room_change", tr
assert tr[0].get("source") == "train_win.room_change_round", tr
print("OK", {k: s[k] for k in ("live", "fitness_before", "fitness_after", "fitness_delta", "transitions", "probe")})
PY