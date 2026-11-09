#!/bin/bash
# keeper_artemis.sh — keep the elastic worker pool at its target size.
#
# The fleet notes are blunt about why this exists: three loops died when their tmux sessions did and
# stayed dead for 21 hours because a watcher reported the death but nothing restarted it. Here the keeper
# is a reconciler: every pass it (a) restarts dead workers, (b) compacts any worker whose context has
# grown past the threshold (pi has no CLI compact, so compaction = restart with fresh context; state lives
# in files), and (c) leaves the COUNT alone — that is the elastic dial, set with workers.py scale N.
set -uo pipefail
REPO="${LOOP_REPO:-$HOME/nidhogg-pau}"
INTERVAL="${KEEPER_INTERVAL:-300}"
export PATH="$HOME/.local/bin:$HOME/nodejs/bin:/usr/bin:/bin:$PATH"
while :; do
  cd "$REPO" || exit 1
  [ -f loop/VERDICT.md ] && { echo "[$(date -Is)] verdict present, idle"; sleep 3600; continue; }
  python3 tools/workers.py reap >> loop/keeper.log 2>&1
  sleep "$INTERVAL"
done
