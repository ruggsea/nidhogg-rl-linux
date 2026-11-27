#!/bin/bash
# Claim: train_state.press routes F (70, attack) and G (71, jump) into the game.
# A live measurement (T210314Z) shows a discrete press of each code moving NidState:
# jump sweeps p1_y 144 -> 176; attack adds animation values absent from the idle
# baseline; and no /tmp/nid_keys_*.txt is written (the old, dead route).
set -e
cd "$(dirname "$0")/.."
python3 - <<'PY'
import json
from pathlib import Path
p = Path("state/press_map_proof_20261127T210314Z.json")
d = json.loads(p.read_text())
assert d.get("jump_y_moved") is True, d
assert d.get("jump_anim_new") is True, d
assert d.get("atk_anim_new") is True, d
assert d.get("keys_file_written") is False, d
assert d.get("entered") is True, d
print("OK", {k: d[k] for k in ("stamp", "base_y", "jump_y", "jump_y_moved",
      "jump_anim_new", "atk_anim_new", "keys_file_written")})
PY