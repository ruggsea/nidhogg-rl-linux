#!/usr/bin/env python3
"""probe_arcade.py — try the ARCADE route (player-vs-CPU) instead of TRAINING.

Main menu cursor starts on MULTIPLAYER; w -> SINGLE PLAYER; Return -> submenu
(ARCADE / TRAINING) with ARCADE first; Return picks ARCADE.  Arcade may skip the
personality/difficulty/map walk that TRAINING needs.

    python3 tools/probe_arcade.py
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
OUT = REPO / "state" / "probes" / "arcade_probe.jsonl"


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def log(r):
    with OUT.open("a") as f:
        f.write(json.dumps(r) + "\n")
    print(json.dumps(r), flush=True)


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
    logf = (LOGDIR / "arcade_probe.log").open("ab")
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


def frame_stats():
    path = "/tmp/nid_rugg/arc.png"
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


def wait_title(timeout=150):
    t0 = time.time()
    while time.time() - t0 < timeout:
        if not n._game_pid(IID):
            time.sleep(2)
            continue
        fs = frame_stats()
        if fs and fs["dark"] > 150000 and fs["yellow"] > 2000:
            return fs
        time.sleep(3)
    return frame_stats()


def main():
    launch()
    print("[arcade] waiting for title")
    fs = wait_title()
    print(f"[arcade] title: {fs}")
    time.sleep(2)

    for keysym, wait, note in [
        ("Return", 2.5, "title -> main menu"),
        ("w", 2.0, "-> single player"),
        ("Return", 2.5, "enter single player (ARCADE first)"),
        ("Return", 3.0, "pick ARCADE"),
    ]:
        n.key(IID, keysym, hold=0.12)
        time.sleep(wait)
        log({"ts": now(), "event": "key", "key": keysym, "note": note,
             "frame": frame_stats()})

    # observe: arcade should go to a match (arena) or an arcade ladder menu
    for i in range(6):
        time.sleep(3.0)
        fs = frame_stats()
        pid = n._game_pid(IID)
        addr = ls.find_fighter(IID) if pid else None
        rec = {"ts": now(), "event": "obs", "i": i, "frame": fs, "bind": hex(addr) if addr else None}
        if addr:
            opp = ls.find_opponent(addr)
            rec["opp"] = hex(opp) if opp else None
            if opp:
                rec["opponent_moves_sustained"] = ls.opponent_moves_sustained(opp)
        log(rec)

    print("[arcade] done")


if __name__ == "__main__":
    main()
