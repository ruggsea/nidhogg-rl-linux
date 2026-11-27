#!/bin/bash
# Falsifier: non-zero when the press-map claim HOLDS.
set -e
cd "$(dirname "$0")/.."
python3 - <<'PY'
import json
from pathlib import Path
p = Path("state/press_map_proof_20261127T210314Z.json")
d = json.loads(p.read_text()) if p.exists() else {}
holds = (
    d.get("jump_y_moved") is True
    and d.get("jump_anim_new") is True
    and d.get("atk_anim_new") is True
    and d.get("keys_file_written") is False
    and d.get("entered") is True
)
raise SystemExit(1 if holds else 0)
PY