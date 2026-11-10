#!/bin/bash
# launch_linux.sh — robust headless launcher for Nidhogg on artemis.
#
# Starts Xvfb (from our proot rootfs, so it has xkbcomp + XKB data + libXfont2) and
# the patched game under GE-Proton, then PROVES the launch with tools/artemis_up.sh
# (process alive, log written, real non-blank frame). Returns non-zero if any proof
# fails. Idempotent: if the instance is already proven up it just reports and exits 0.
#
# Usage:  ./tools/launch_linux.sh [display]    (default :99)
# Exit:   0 = up and rendering (proven), 1 = not proven up

set -u
DISP="${1:-:99}"
N="${DISP#:}"
HERE="$(cd "$(dirname "$0")" && pwd)"
GAME="$HOME/nidfarm/game/Nidhogg.exe"
PROTON="$HOME/.local/opt/GE-Proton11-12-x86_64/proton"
PREFIX="$HOME/nidpfx"
LOGDIR="$HOME/nidlogs"
LOG="$LOGDIR/inst_${N}.log"
PROOT="$HOME/nidroot/proot"
ROOTFS="$HOME/nidroot/rootfs"
XFB="/usr/bin/Xvfb"   # path INSIDE the rootfs, not the host path
SPY="$HERE/../spy/nidspy.so"   # in-process memory spy (LD_PRELOAD); enables /proc-free state reads
mkdir -p "$LOGDIR"

# already proven up? report and leave it alone
if "$HERE/artemis_up.sh" "$DISP" >/dev/null 2>&1; then
  "$HERE/artemis_up.sh" "$DISP"
  exit 0
fi

# 1. Xvfb — inside proot so the rootfs /usr/bin/xkbcomp and XKB data are visible,
#    with -b /tmp so the X socket lands on the host where the game can reach it.
if [ ! -S "/tmp/.X11-unix/X${N}" ]; then
  "$PROOT" -0 -r "$ROOTFS" -b /proc -b /dev -b /sys -b /tmp -w /root \
    /usr/bin/env PATH=/usr/bin:/bin "$XFB" "$DISP" -screen 0 640x480x24 -nolisten tcp \
    > "$LOGDIR/xvfb_${N}.log" 2>&1 &
  echo "started Xvfb ${DISP}"
fi
for _ in $(seq 1 50); do
  [ -S "/tmp/.X11-unix/X${N}" ] && break
  sleep 0.1
done
[ -S "/tmp/.X11-unix/X${N}" ] || { echo "FAIL: Xvfb ${DISP} socket did not appear"; exit 1; }
echo "ok: Xvfb ${DISP} ready"

# 2. game under Proton — new session so it survives, log captured so a silent death is visible.
#    DISPLAY-scoped: only treat an instance on THIS display as already up. The old check matched
#    ANY Nidhogg.exe, so with farm instances on :99/:100 a launch for :99 would silently skip (or
#    wrongly claim success) because some OTHER display had a game. That collision cost real probes.
GAME_PID=""
for d in /proc/[0-9]*; do
  [ "$(cat "$d/comm" 2>/dev/null)" = "Nidhogg.exe" ] || continue
  if tr '\0' '\n' < "$d/environ" 2>/dev/null | grep -qx "DISPLAY=$DISP"; then
    GAME_PID="${d#/proc/}"
    break
  fi
done
if [ -z "$GAME_PID" ]; then
  env DISPLAY="$DISP" \
      STEAM_COMPAT_CLIENT_INSTALL_PATH="$HOME/fake_steam" \
      STEAM_COMPAT_DATA_PATH="$PREFIX" \
      SteamAppId=94400 SteamGameId=94400 WINEDEBUG=-all \
      LD_PRELOAD="$SPY" \
      setsid "$PROTON" waitforexitandrun "$GAME" ${NID_GAME_ARGS:-} > "$LOG" 2>&1 < /dev/null &
  echo "started proton (log $LOG)"
fi

# 3. wait for the real game process AND a rendered frame, then run the gate
echo "waiting for boot and render..."
for _ in $(seq 1 60); do
  "$HERE/artemis_up.sh" "$DISP" >/dev/null 2>&1 && break
  sleep 2
done

# 4. the gate: prove it, and let this output be the record
"$HERE/artemis_up.sh" "$DISP"
