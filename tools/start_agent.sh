#!/bin/bash
# start_agent.sh — bring up the nidhogg agent on artemis with a SELF-LOOP armed.
#
# The loop is pi's own `loop` tool (project-local .pi/extensions/self-loop.ts), not a shell wrapper:
# every N minutes it re-injects loop/self_tick.md as a message if the agent is idle, and it stops on a
# goal condition (loop/VERDICT.md). The session keeps its context between ticks, so a tick does not have
# to re-derive hard-won facts from files - but the tick message still points at plan/claims/ticklog so a
# fresh process can recover.
#
# NOTE: do NOT keep a project-local copy of self-loop.ts. The extension already exists at
# ~/.pi/agent/extensions/self-loop.ts, and a second copy makes pi exit immediately with
# 'Tool "loop" conflicts with ...' - measured, and it cost a confusing blank-pane detour.
#
# Usage: bash tools/start_agent.sh [minutes]
set -uo pipefail
REPO="${LOOP_REPO:-$HOME/nidhogg-pau}"
SESS="${LOOP_SESSION:-nidhogg-agent}"
MIN="${1:-10}"
PROVIDER="${LOOP_PROVIDER:-deepseek}"
MODEL="${LOOP_MODEL:-deepseek-v4-pro}"
export PATH="$HOME/.local/bin:$HOME/nodejs/bin:/usr/bin:/bin:$PATH"
cd "$REPO" || exit 1

tmux kill-session -t "$SESS" 2>/dev/null
tmux new -d -s "$SESS" -c "$REPO" \
  "pi --provider $PROVIDER --model $MODEL --append-system-prompt loop/driver_prompt.md"
sleep 12

# Arm the self-loop and start tick 1. Sent as a message so the agent owns the loop, not a wrapper script.
tmux send-keys -t "$SESS" "Arm pi's self-loop now: call the loop tool with action=start, minutes=$MIN, untilFile=$REPO/loop/VERDICT.md, and message set to the exact contents of loop/self_tick.md (read that file first). Then begin tick 1 immediately by following that message." Enter
if ! tmux has-session -t "$SESS" 2>/dev/null; then
  echo "FAIL: session $SESS did not survive startup - check /tmp/pi_tui.log (a duplicate extension makes pi exit)"
  exit 1
fi
echo "agent started in tmux $SESS with a ${MIN}min self-loop"
