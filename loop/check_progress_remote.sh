#!/usr/bin/env bash
# check_progress_remote.sh — the REAL check, run ON artemis where the state, the workers and the game live.
#
# It must run there, not on the Mac: measured twice that checking from the Mac produced false milestones
# ("3 generations" from a day-old /tmp log, "0 workers alive" because tmux was inspecting the wrong
# machine). Silently logs every check to state/progress_history.jsonl; emails only on a milestone.
set -uo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO" || exit 0
PY=python3
OUT="$("$PY" tools/milestones.py --json 2>&1)" || { echo "milestone check failed: $OUT"; exit 0; }
NEW="$(PROG_JSON="$OUT" "$PY" -c 'import json,os;print(",".join(json.loads(os.environ["PROG_JSON"])["new"]))')"
if [ -z "$NEW" ]; then
  echo "no milestone - silent"
  exit 0
fi
BODY="$(PROG_JSON="$OUT" "$PY" -c 'import json,os;print(json.loads(os.environ["PROG_JSON"])["body"])')"
echo "MILESTONE: $NEW"
printf '%s\n' "$BODY"
~/claude-code-config/bin/notify.sh mail "$BODY" "nidhogg: $NEW" && echo "(emailed)" || echo "(email failed)"
