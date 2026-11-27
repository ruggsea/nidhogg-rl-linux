#!/bin/bash
# Falsifier: non-zero when LIVE plan03 train_win fitness claim HOLDS.
set -e
python3 - <<'PY'
import json
from pathlib import Path
tw = Path("train_win.py").read_text() if Path("train_win.py").exists() else ""
p = Path("state/plan03_train_win_fit.jsonl")
rows = [json.loads(l) for l in p.read_text().splitlines() if l.strip()] if p.exists() else []
s = next((r for r in rows[::-1] if r.get("phase") == "summary" and r.get("live") is True), None)
tr = (s or {}).get("transitions") or []
holds = (
  s is not None
  and "def fitness_delta_on_room_change" in tw
  and s.get("source") == "train_win_live_probe"
  and s.get("fitness_delta") not in (0, None)
  and s.get("fitness_before") != s.get("fitness_after")
  and tr and tr[0].get("kind") == "room_change"
  and tr[0].get("source") == "train_win.room_change_round"
)
raise SystemExit(1 if holds else 0)
PY