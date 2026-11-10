#!/usr/bin/env python3
"""probe_training_matrix.py — the engineer's 21:09 definitive training-flow probe.

Flow (from the game's own -lttraining localtest):
  main menu -> TRAINING -> training list (personality) -> difficulty window
  (SEPARATE screen) -> ONE press -> rLevelSelect(17) -> START.

Probe matrix at the difficulty window (log room_top + frame mean at EVERY step —
the map grid renders BLACK, so frame mean + room are the advance signals):
  (a) Return ONCE (accept default) -> room 17 (black map select)?
  (b) if not: Left, Return; then Right, Return (difficulty as a cycle value)
  (c) map select: Return (pick default map) -> s down + Return (START)
  -> watch for arena (frame mean > 85 or room 26-77).

    python3 tools/probe_training_matrix.py
"""
import json
import os
import signal
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import nid_linux as n           # noqa: E402
import linux_state as ls        # noqa: E402

IID = 0
DISP = ":99"
PREFIX = Path.home() / "nidfarm" / "prefixes" / "1"
GAME = Path.home() / "nidfarm" / "game" / "Nidhogg.exe"
PROTON = Path.home() / ".local/opt/GE-Proton11-12-x86_64/proton"
SPY = Path.home() / "nidhogg-pau" / "spy" / "nidspy.so"
STEAM_ROOT = Path.home() / "fake_steam"
LOGDIR = Path.home() / "nidlogs"
REPO = Path.home() / "nidhogg-pau"
OUT = REPO / "state" / "probes" / "training_matrix.jsonl"
FRAMEDIR = REPO / "state" / "probes" / "frames"
FRAMEDIR.mkdir(exist_ok=True)

KNOWN = np.array([2, 3, 4, 17, 19, 20, 25] + list(range(26, 78)), dtype=np.int32)
ROOM_NAMES = {2: "rMainMenu", 3: "rMultiMenu", 4: "rOnlineLobby", 17: "rLevelSelect",
              19: "rControlsRoom", 20: "rMatchStats", 21: "rTutorial", 25: "rPreMatch",
              29: "rCastleCenter"}


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def log(r):
    with OUT.open("a") as f:
        f.write(json.dumps(r) + "\n")


def stop_lane():
    for d in Path("/proc").iterdir():
        if not d.name.isdigit():
            continue
        try:
            comm = (d / "comm").read_text().strip()
            env = (d / "environ").read_bytes()
        except OSError:
            continue
        if comm == "Nidhogg.exe" and b"DISPLAY=" + DISP.encode() in env.split(b"\0"):
            try:
                os.kill(int(d.name), signal.SIGKILL)
            except OSError:
                pass
    time.sleep(2)
    for lock in [PREFIX / "pfx.lock", PREFIX / "pfx" / "pfx.lock"]:
        try:
            lock.unlink()
        except OSError:
            pass


def launch():
    stop_lane()
    logf = (LOGDIR / "training_matrix.log").open("ab")
    env = dict(os.environ)
    env.pop("WAYLAND_DISPLAY", None)
    env.update(DISPLAY=DISP,
               STEAM_COMPAT_CLIENT_INSTALL_PATH=str(STEAM_ROOT),
               STEAM_COMPAT_DATA_PATH=str(PREFIX),
               SteamAppId="94400", SteamGameId="94400",
               WINEDEBUG="-all", LD_PRELOAD=str(SPY))
    subprocess.Popen([str(PROTON), "waitforexitandrun", str(GAME)],
                     env=env, stdout=logf, stderr=logf, start_new_session=True,
                     cwd=str(REPO))
    print("[launch]")


def frame_stats(tag):
    path = str(FRAMEDIR / f"{tag}.png")
    if not n.grab(IID, path):
        return None
    a = np.array(Image.open(path)).astype(int)[40:440, 0:640]
    r, g, b = a[:, :, 0], a[:, :, 1], a[:, :, 2]
    pure = (r > 235) & (g > 235) & (b > 235)
    dark = (r < 60) & (g < 60) & (b < 60)
    yellow = (r > 180) & (g > 160) & (b < 120)
    orange = (r > 180) & (g > 70) & (g < 160) & (b < 100)
    return {"mean": round(float(a.mean()), 1), "pure": int(pure.sum()),
            "dark": int(dark.sum()), "yellow": int(yellow.sum()),
            "orange": int(orange.sum())}


def room_top():
    pid = n._game_pid(IID)
    if not pid:
        return None
    counts = Counter()
    for a, b in ls._regions()[:3]:
        raw = n.memory(pid, a, b - a, "/tmp/nid_rugg/tm_room.bin")
        if raw is None:
            continue
        arr = np.frombuffer(raw, "<i4")
        vals, cnts = np.unique(arr[np.isin(arr, KNOWN)], return_counts=True)
        for v, c in zip(vals.tolist(), cnts.tolist()):
            counts[int(v)] += c
    return [(ROOM_NAMES.get(v, f"r{v}"), v, c) for v, c in counts.most_common(4)]


def wait_title(timeout=150):
    t0 = time.time()
    last = None
    while time.time() - t0 < timeout:
        if not n._game_pid(IID):
            time.sleep(2)
            continue
        fs = frame_stats("boot_poll")
        last = fs
        if fs and fs["dark"] > 150000 and fs["pure"] > 3000:
            return fs
        time.sleep(3)
    return last


def press(keysym, wait=2.5):
    n.key(IID, keysym, hold=0.12)
    time.sleep(wait)
    fs = frame_stats(f"after_{keysym}")
    rt = room_top()
    rec = {"ts": now(), "event": "key", "key": keysym, "frame": fs, "room": rt}
    log(rec)
    print(f"  {keysym}: frame={fs} room={rt}")
    return rec


def match_signal(rec):
    """True if this looks like a live match (arena)."""
    fs = rec.get("frame") or {}
    mean = fs.get("mean", 0)
    return mean is not None and mean > 85


def main():
    launch()
    print("[matrix] waiting for title")
    fs = wait_title()
    print(f"[matrix] title/boot frame: {fs}")
    log({"ts": now(), "event": "launch", "pid": n._game_pid(IID), "boot_frame": fs})

    # walk to TRAINING (verify main menu is reached first)
    press("Return", 2.5)     # title -> main menu
    # verify main menu: mean should be bright (~60-75); if not, Return again
    r = press("Return", 3.0)
    press("w", 2.0)          # -> SINGLE PLAYER
    press("Return", 2.5)     # enter single player
    press("s", 2.0)          # -> TRAINING
    press("Return", 3.0)     # enter TRAINING (training list / difficulty)

    # let the training list/difficulty window load (black -> dark submenu)
    print("[matrix] waiting for training list to settle (up to 60s)")
    for i in range(20):
        time.sleep(3)
        fs = frame_stats(f"settle{i}")
        rt = room_top()
        print(f"  settle{i}: frame={fs} room={rt}")
        log({"ts": now(), "event": "settle", "i": i, "frame": fs, "room": rt})
        if fs and fs["mean"] is not None and 10 < fs["mean"] < 60:
            break   # dark submenu appeared

    # ---- PROBE MATRIX at the difficulty window ----
    # (a) Return ONCE (accept default difficulty) -> room 17?
    r = press("Return", 3.0)
    if r.get("frame") and r["frame"].get("mean", 99) < 10:
        print("[matrix] -> BLACK map select (room 17 candidate). Navigating blind.")
    # (b) if not advanced, cycle difficulty Left/Right + Return
    for dirkey in ("a", "d"):
        if match_signal(r):
            break
        r = press(dirkey, 2.0)
        r = press("Return", 3.0)
        if r.get("frame") and r["frame"].get("mean", 99) < 10:
            print(f"[matrix] after {dirkey}+Return -> BLACK map select")
            break
        if match_signal(r):
            print(f"[matrix] after {dirkey}+Return -> ARENA")
            break

    # (c) map select: pick default map + START
    press("Return", 3.0)   # pick default map
    press("s", 2.0)        # down to START
    r = press("Return", 3.0)  # START

    # observe for a match
    print("[matrix] observing for match (up to 30s)")
    for i in range(10):
        time.sleep(3)
        fs = frame_stats(f"match{i}")
        rt = room_top()
        print(f"  match{i}: frame={fs} room={rt}")
        log({"ts": now(), "event": "obs", "i": i, "frame": fs, "room": rt})
        if fs and fs["mean"] is not None and fs["mean"] > 85:
            print("[matrix] ARENA SIGNATURE (mean>85) — checking live match")
            pid = n._game_pid(IID)
            addr = ls.find_fighter(IID) if pid else None
            if addr:
                opp = ls.find_opponent(addr)
                if opp:
                    sus = ls.opponent_moves_sustained(opp)
                    print(f"[matrix] bind={hex(addr)} opp={hex(opp)} sustained={sus}")
                    log({"ts": now(), "event": "live_match", "bind": hex(addr),
                         "opp": hex(opp), "sustained": sus})
            break

    print("[matrix] done")


if __name__ == "__main__":
    main()
