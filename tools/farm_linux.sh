#!/bin/bash
# farm_linux.sh — several independent Nidhogg instances on one host, following Pau's Linux recipe.
#
# WHY: one physical game serialises all game work. Three workers existed but only the prober could touch
# the game, and it got 12% of the ticks because everyone else queued behind the same instance. Instances
# are the only thing that makes parallelism mean anything for experiments.
#
# Pau's measured recipe (his docs/LINUX.md, reproduced here with our paths):
#   * one Xvfb per instance         -> nothing on screen
#   * one wine prefix per instance  -> no prefix-lock fights between instances
#   * window patched 960x600->320x200 in a COPY of data.win -> 25 fps becomes 60 fps, CPU 112%->41%
#   * audio off in the prefix       -> no audio threads, silent
#   * Proton `waitforexitandrun` + SteamAppId=94400 -> no Steam client needed
#
# Filesystem is btrfs, so `cp --reflink=always` makes a prefix copy nearly free (measured: supported).
#
#   ./tools/farm_linux.sh init            # template prefix + patched game copy (once)
#   ./tools/farm_linux.sh start 3         # instances 1..3 on displays :81 :82 :83
#   ./tools/farm_linux.sh status
#   ./tools/farm_linux.sh stop [i]        # all, or one
#
# Each instance records itself in state/farm.json with its display and pids, so a worker can claim one
# instead of assuming :99.

set -uo pipefail
REPO="${FARM_REPO:-$HOME/nidhogg-pau}"
ROOT="${FARM_ROOT:-$HOME/nidfarm}"
TPL="$ROOT/prefix-template"
GAME_SRC="$HOME/nidhogg_win"
GAME="$ROOT/game"                      # patched copy, shared read-only by all instances
PROTON="$HOME/.local/opt/GE-Proton11-12-x86_64/proton"
# Instance numbering is aligned with tools/nid_linux.py, which addresses instance i as display
# DISPLAY_BASE+i with DISPLAY_BASE=99. So farm instance 1 runs on :99 == nid_linux instance 0, farm
# instance 2 on :100 == nid_linux instance 1. Without this the farm would be capacity no tool could see.
BASE_DISPLAY=${FARM_BASE_DISPLAY:-98}  # instance i -> display $((BASE_DISPLAY + i))
PROOT="$HOME/nidroot/rootfs"
WINEPREFIX_XVFB="$PROOT/usr/bin/Xvfb"
STATE="$REPO/state/farm.json"

log() { echo "[farm] $*"; }
game_pid() { pgrep -x Nidhogg.exe 2>/dev/null | head -1; }

state_read() { python3 - "$STATE" <<'PY'
import json,sys
try: print(json.dumps(json.load(open(sys.argv[1]))))
except Exception: print("{}")
PY
}
state_write() { python3 - "$STATE" "$@" <<'PY'
import json,sys
path=sys.argv[1]
try: d=json.load(open(path))
except Exception: d={}
key=sys.argv[2]
if key=="del":
    d.pop(sys.argv[3], None)
else:
    d[key]=json.loads(sys.argv[3])
json.dump(d, open(path,"w"), indent=1)
PY
}

ensure_xvfb() {   # $1 = display number
  local d=$1
  pgrep -f "Xvfb :$d " >/dev/null && return 0
  "$HOME/nidroot/proot" -0 -r "$PROOT" -b /proc -b /dev -b /sys -b /tmp \
      /usr/bin/env PATH=/usr/bin:/bin /usr/bin/Xvfb ":$d" -screen 0 640x480x24 -nolisten tcp \
      >"$ROOT/logs/xvfb_$d.log" 2>&1 &
  sleep 2
  pgrep -f "Xvfb :$d " >/dev/null
}

cmd_init() {
  mkdir -p "$ROOT"/{logs,prefixes}
  # patched game copy (window 320x200)
  if [ ! -f "$GAME/data.win" ]; then
    log "copying game and patching window 960x600 -> 320x200"
    mkdir -p "$GAME"
    cp -a "$GAME_SRC/." "$GAME/"
    python3 - "$GAME/data.win" <<'PY'
import struct,sys
p=sys.argv[1]; d=bytearray(open(p,"rb").read())
before=struct.unpack_from("<II", d, 0x10+60)
struct.pack_into("<II", d, 0x10+60, 320, 200)
open(p,"wb").write(d)
print(f"window {before} -> (320, 200)")
PY
  else
    log "patched game copy already present"
  fi
  # template prefix: copy our working prefix, audio off
  if [ ! -d "$TPL/pfx" ]; then
    log "building prefix template (reflink copy of ~/nidpfx)"
    mkdir -p "$TPL"
    cp -a --reflink=always "$HOME/nidpfx/." "$TPL/" 2>/dev/null || cp -a "$HOME/nidpfx/." "$TPL/"
    local reg="$TPL/pfx/user.reg"
    grep -q "Wine..Drivers" "$reg" 2>/dev/null || \
      printf '\n[Software\\\\Wine\\\\Drivers] 1790000000\n"Audio"=""\n' >> "$reg"
    rm -f "$TPL/pfx.lock"
  else
    log "prefix template already present"
  fi
  log "init done: game=$GAME template=$TPL"
}

cmd_start() {
  local n="${1:-1}" i
  mkdir -p "$ROOT"/{logs,prefixes}
  command -v >/dev/null
  for i in $(seq 1 "$n"); do
    local d=$((BASE_DISPLAY + i)) pre="$ROOT/prefixes/$i"
    ensure_xvfb "$d" || { log "instance $i: Xvfb :$d failed"; continue; }
    if [ -d "$pre/pfx" ]; then
      rm -f "$pre/pfx.lock" "$pre/pfx/dosdevices/z:" 2>/dev/null
    else
      mkdir -p "$pre"
      cp -a --reflink=always "$TPL/." "$pre/" 2>/dev/null || cp -a "$TPL/." "$pre/"
    fi
    log "starting instance $i on :$d"
    env -u WAYLAND_DISPLAY DISPLAY=":$d" \
        STEAM_COMPAT_CLIENT_INSTALL_PATH="$HOME/fake_steam" \
        STEAM_COMPAT_DATA_PATH="$pre" \
        SteamAppId=94400 SteamGameId=94400 WINEDEBUG=-all \
        setsid "$PROTON" waitforexitandrun "$GAME/Nidhogg.exe" \
        >>"$ROOT/logs/game_$i.log" 2>&1 &
    state_write "i$i" "{\"display\": $d, \"prefix\": \"$pre\", \"started\": $(date +%s)}"
  done
  sleep 45
  cmd_status
}

cmd_status() {
  local n=0
  for i in 1 2 3 4 5 6 7 8; do
    local pre="$ROOT/prefixes/$i" d=$((BASE_DISPLAY + i))
    [ -d "$pre" ] || continue
    local pid
    pid=$(pgrep -f "STEAM_COMPAT_DATA_PATH=$pre" 2>/dev/null | head -1)
    local xs; xs=$(pgrep -f "Xvfb :$d " | head -1)
    printf "instance %s  display :%s  proton=%s  xvfb=%s\n" "$i" "$d" "${pid:--}" "${xs:--}"
    n=$((n+1))
  done
  [ "$n" -eq 0 ] && echo "no instances configured (run: farm_linux.sh init && start N)"
  printf "Nidhogg.exe processes: %s\n" "$(pgrep -c -x Nidhogg.exe)"
}

cmd_stop() {
  local i="${1:-all}"
  if [ "$i" = "all" ]; then
    pkill -x "Nidhogg.exe" 2>/dev/null
    pkill -f "proton waitforexitandrun" 2>/dev/null
    log "stopped all instances"
    return
  fi
  local pre="$ROOT/prefixes/$i"
  pkill -f "STEAM_COMPAT_DATA_PATH=$pre" 2>/dev/null
  log "stopped instance $i"
}

case "${1:-status}" in
  init)   cmd_init ;;
  start)  cmd_start "${2:-1}" ;;
  status) cmd_status ;;
  stop)   cmd_stop "${2:-all}" ;;
  *) echo "usage: $0 {init|start N|status|stop [i]}" ;;
esac
