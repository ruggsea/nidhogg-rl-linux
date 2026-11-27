#!/bin/bash
# Falsifier: non-zero when the entry-swap claim HOLDS.
set -e
python3 - <<'PY'
import json
from pathlib import Path
p = Path("state/entry_swap_20261127T175018Z.json")
d = json.loads(p.read_text()) if p.exists() else {}
holds = (
    d.get("run_entry_ok") is True
    and d.get("pid_changed") is True
    and d.get("pid_before") != d.get("pid_after_entry")
    and d.get("round_started") is True
    and d.get("has_players") is True
    and "entry_health" in d.get("entry", "")
    and "enter_match_v2" in d.get("entry", "")
)
raise SystemExit(1 if holds else 0)
PY