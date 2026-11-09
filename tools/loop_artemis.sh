#!/bin/bash
# loop_artemis.sh — keep the nidhogg worker working on artemis with nobody attached.
#
# Why this exists instead of just leaving a pi TUI in tmux: pi is not self-driving. A TUI sits at its
# prompt when it finishes a turn and waits for a human, which is exactly the failure the fleet notes
# describe ("a loop that can only be revived by a human is not an autonomous loop"). So this wrapper
# owns the tmux pane and spawns a FRESH bounded pi per tick; memory lives in loop/PI_TICKLOG.md,
# state/plan.json and state/claims.jsonl, not in a conversation.
#
# Deliberately NOT using ~/claude-code-config/bin/engines/pi.sh: that adapter runs bare `pi`, which here
# defaults to an OpenRouter model that answers 402 (out of credits, needs 65536 tokens vs 12084 available).
# Measured: only the explicit flags work, so they are pinned below.
#
#   tmux new -d -s nidhogg-loop "bash ~/nidhogg-pau/tools/loop_artemis.sh >> ~/nidhogg-pau/loop/agent_loop.log 2>&1"
#
# Stop: touch loop/VERDICT.md   (clean)   |   tmux kill-session -t nidhogg-loop   (hard)

set -uo pipefail
REPO="${LOOP_REPO:-$HOME/nidhogg-pau}"
PROMPT_FILE="$REPO/loop/driver_prompt.md"
VERDICT="$REPO/loop/VERDICT.md"
TICKLOG="$REPO/loop/PI_TICKLOG.md"
SLEEP="${LOOP_TICK_SLEEP:-600}"
MAX_TICKS="${LOOP_MAX_TICKS:-0}"
PROVIDER="${LOOP_PROVIDER:-deepseek}"
MODEL="${LOOP_MODEL:-deepseek-v4-pro}"
NOTIFY="$HOME/claude-code-config/bin/notify.sh"

export PATH="$HOME/.local/bin:$HOME/nodejs/bin:/usr/local/bin:/usr/bin:/bin:$PATH"
cd "$REPO" || { echo "no repo at $REPO"; exit 1; }

log() { echo "[$(date -Is)] $*"; }
mkdir -p "$REPO/loop"

TICK=0
while :; do
  [ -f "$VERDICT" ] && { log "VERDICT present - stopping cleanly"; break; }
  TICK=$((TICK + 1))
  if [ "$MAX_TICKS" != "0" ] && [ "$TICK" -gt "$MAX_TICKS" ]; then log "tick cap reached"; break; fi

  START=$(date +%s)
  log "===== TICK $TICK START ($PROVIDER/$MODEL) ====="

  PROMPT="$(cat "$PROMPT_FILE" 2>/dev/null)"
  if [ -z "$PROMPT" ]; then log "driver prompt missing at $PROMPT_FILE"; break; fi
  PROMPT="TICK=$TICK of the nidhogg loop. $PROMPT"

  OUT=$(printf '%s' "$PROMPT" | timeout 2400 pi --provider "$PROVIDER" --model "$MODEL" -p 2>&1)
  RC=$?
  DUR=$(( $(date +%s) - START ))

  # keep the raw output: a tick that "did nothing" must be auditable afterwards
  printf '%s\n' "$OUT" > "$REPO/loop/last_tick.txt"
  log "===== TICK $TICK END dur=${DUR}s rc=$RC ====="
  if [ $RC -ne 0 ]; then
    log "tick failed (rc=$RC); first error line:"
    printf '%s\n' "$OUT" | grep -viE "warning|pi-web-access" | tail -3
    # two consecutive failures usually mean credits, auth or a broken prompt - worth a human's attention
    FAILS=$(( ${FAILS:-0} + 1 ))
    if [ "$FAILS" -ge 3 ]; then
      [ -x "$NOTIFY" ] && "$NOTIFY" mail "nidhogg loop on artemis: 3 consecutive tick failures (rc=$RC). Last output: $(printf '%s' "$OUT" | tail -2)" "nidhogg loop stalled" 2>/dev/null
      log "notified after 3 consecutive failures; continuing"
    fi
  else
    FAILS=0
  fi

  sleep "$SLEEP"
done
log "loop stopped"
