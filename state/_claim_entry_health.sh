#!/bin/bash
# Claim: entry health gate relaunched the stuck instance (fv=false wall=null yel=0)
# and enter_match_v2 then reached a fresh live match with a NEW game pid (T165953Z).
set -e
python3 - <<'PY'
import json
from pathlib import Path
p = Path("state/entry_health_20261127T165953Z.json")
d = json.loads(p.read_text())
assert d.get("ok") is True, d
assert d.get("stuck_before") is True, d
assert d.get("relaunched") is True, d
assert d.get("entry") == "enter_match_v2", d
assert d.get("pid_changed") is True, d
assert d.get("in_match_after") is True, d
assert d.get("game_pid_before") != d.get("game_pid_after"), d
print("OK", {k: d.get(k) for k in ("probe", "stamp", "stuck_before", "relaunched",
      "game_pid_before", "game_pid_after", "entry", "entered", "in_match_after")})
PY