#!/bin/bash
# artemis_up.sh — prove the game is actually up and rendering on THIS host.
#
# Why this exists: three launches today left no process and no log while appearing to "start", and a
# detached launch that silently dies is exactly how this project spent a day training against a title
# screen. So the launch is only "done" when this script says so, and it exits non-zero otherwise.
#
# Checks, in order:
#   1. Xvfb for $DISP is running
#   2. the Nidhogg.exe process exists under wine
#   3. a frame can be grabbed from $DISP and it is NOT blank (mean brightness above a floor)
#
# Usage:  ./tools/artemis_up.sh [display]      (default :99)
# Exit:   0 = up and rendering, 1 = not proven up

set -u
DISP="${1:-:99}"
LOGDIR="$HOME/nidlogs"
mkdir -p "$LOGDIR"
FRAME="/tmp/art_frame_${DISP#:}.png"
fail() { echo "FAIL: $*"; exit 1; }

# 1. display
pgrep -f "Xvfb ${DISP} " >/dev/null || fail "no Xvfb on ${DISP} (start one: Xvfb ${DISP} -screen 0 640x480x24 -nolisten tcp &)"
echo "ok: Xvfb ${DISP} running"

# 2. process
PID=$(pgrep -f "nidfarm/game/Nidhogg.exe" | head -1)
if [ -z "${PID:-}" ]; then
  PID=$(pgrep -f "nidhogg_win/Nidhogg.exe" | head -1)
fi
[ -n "${PID:-}" ] || fail "no Nidhogg.exe process under wine"
echo "ok: Nidhogg.exe pid $PID"

# 3. real frame, not a blank screen
DISPLAY="$DISP" ffmpeg -y -loglevel error -f x11grab -video_size 640x480 -i "$DISP" -frames:v 1 "$FRAME" 2>/dev/null \
  || fail "could not grab a frame from ${DISP}"
[ -s "$FRAME" ] || fail "frame grab produced an empty file"

# mean brightness via ffmpeg's signalstats, so a black screen cannot pass
MEAN=$(ffmpeg -loglevel error -i "$FRAME" -vf "signalstats,metadata=print:key=lavfi.signalstats.YAVG" -f null - 2>&1 \
       | grep -oE "YAVG=[0-9.]+" | head -1 | cut -d= -f2)
echo "frame mean brightness: ${MEAN:-unknown}"
python3 - "${MEAN:-0}" <<'PY' || fail "frame is blank (mean brightness below 5) - the game is up but not rendering"
import sys
sys.exit(0 if float(sys.argv[1] or 0) > 5.0 else 1)
PY
echo "VERDICT: UP AND RENDERING on ${DISP} (frame ${FRAME})"
exit 0
