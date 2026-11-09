#!/bin/bash
# keeper_artemis.sh — resurrect the nidhogg loop if its tmux session dies.
#
# The fleet notes are blunt about why this exists: three loops died when their tmux sessions did and
# stayed dead for 21 hours, including one working against a deadline, because a stall watcher reported
# the death but nothing restarted it. So: check, and restart, unconditionally.
#
#   tmux new -d -s nidhogg-keeper "bash ~/nidhogg-pau/tools/keeper_artemis.sh"
set -uo pipefail
REPO="${LOOP_REPO:-$HOME/nidhogg-pau}"
SESS="${LOOP_SESSION:-nidhogg-loop}"
INTERVAL="${KEEPER_INTERVAL:-300}"
while :; do
  if ! tmux has-session -t "$SESS" 2>/dev/null; then
    [ -f "$REPO/loop/VERDICT.md" ] && { echo "[$(date -Is)] verdict present, not restarting"; sleep 3600; continue; }
    echo "[$(date -Is)] $SESS dead -> restarting"
    tmux new -d -s "$SESS" "LOOP_TICK_SLEEP=${LOOP_TICK_SLEEP:-600} bash $REPO/tools/loop_artemis.sh >> $REPO/loop/agent_loop.log 2>&1"
  fi
  sleep "$INTERVAL"
done
