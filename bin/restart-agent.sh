#!/usr/bin/env bash
# Restart the Nidhogg agent as a fresh pi session with the rebuilt harness.
#
# Why: the previous session accumulated a 42 MB transcript, was compacted twice, and kept
# re-deriving facts it had already established. A fresh session that starts from
# state/facts.json + loop/CONTINUE.md and uses tools/{doctor,attest,claim,gameslot}.py is cheaper
# and far less likely to repeat the day's failure modes.
#
#   bin/restart-agent.sh            # run in this terminal
#   bin/restart-agent.sh --tmux     # detach into a tmux session called nidhogg-agent
set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO"

MODEL="${NID_AGENT_MODEL:-deepseek-v4-pro}"
PROVIDER="${NID_AGENT_PROVIDER:-deepseek}"
PROMPT="$REPO/loop/CONTINUE.md"

if [[ ! -f "$PROMPT" ]]; then echo "missing $PROMPT" >&2; exit 1; fi
if [[ ! -f "$REPO/state/facts.json" ]]; then echo "missing state/facts.json" >&2; exit 1; fi

# environment check before spending tokens
python3 tools/doctor.py || echo "(doctor reported a problem - read it before trusting any result)"

if [[ "${1:-}" == "--tmux" ]]; then
  tmux kill-session -t nidhogg-agent 2>/dev/null || true
  tmux new -d -s nidhogg-agent \
    "cd '$REPO' && pi --provider '$PROVIDER' --model '$MODEL' --append-system-prompt '$PROMPT'"
  echo "started tmux session nidhogg-agent (model $PROVIDER/$MODEL)"
  exit 0
fi

exec pi --provider "$PROVIDER" --model "$MODEL" --append-system-prompt "$PROMPT"
