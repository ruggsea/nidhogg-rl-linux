#!/bin/bash
# Claim: the train entry path is now tools/entry_health.ensure_entry -> nidstate.enter_match_v2,
# driven through InstanceManager.run_entry (T175018Z). Helper relaunched the stuck instance
# (pid 3966635 -> 3988773) and a round started under the new route.
set -e
python3 - <<'PY'
import json
from pathlib import Path
p = Path("state/entry_swap_20261127T175018Z.json")
d = json.loads(p.read_text())
assert d.get("run_entry_ok") is True, d
assert d.get("pid_changed") is True, d
assert d.get("pid_before") != d.get("pid_after_entry"), d
assert d.get("round_started") is True, d
assert d.get("has_players") is True, d
assert "entry_health" in d.get("entry", ""), d
assert "enter_match_v2" in d.get("entry", ""), d
print("OK", {k: d.get(k) for k in ("probe", "stamp", "pid_before", "pid_after_entry",
      "pid_changed", "run_entry_ok", "has_players", "room_at_round", "round_started")})
PY