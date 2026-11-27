#!/bin/bash
# After a successful tools/plan03_live_fit.py run, record the LIVE accept claim (does not close plan 03).
set -e
cd "$(dirname "$0")/.."
python3 tools/claim.py record \
  "PLAN03 LIVE: train_win round-term fitness delta on observed room_change (live probe)" \
  --cmd "bash state/_claim_plan03_live_fit.sh" \
  --falsifier "bash state/_falsify_plan03_live_fit.sh"