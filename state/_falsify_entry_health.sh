#!/bin/bash
# Falsifier: non-zero when the entry-health claim HOLDS.
set -e
python3 - <<'PY'
import json
from pathlib import Path
p = Path("state/entry_health_20261127T165953Z.json")
d = json.loads(p.read_text()) if p.exists() else {}
holds = (
    d.get("ok") is True
    and d.get("stuck_before") is True
    and d.get("relaunched") is True
    and d.get("entry") == "enter_match_v2"
    and d.get("pid_changed") is True
    and d.get("in_match_after") is True
    and d.get("game_pid_before") != d.get("game_pid_after")
)
raise SystemExit(1 if holds else 0)
PY