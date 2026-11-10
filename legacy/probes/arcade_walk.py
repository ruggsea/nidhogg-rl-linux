#!/usr/bin/env python3
"""arcade_walk.py — deterministic ARCADE route (SINGLE PLAYER -> ARCADE), the fight-CPU mode.

The engineer's 23:20 menu order: main menu NEWS/SINGLE PLAYER/MULTIPLAYER/OPTIONS/EXTRAS
(cursor on MULTIPLAYER); SINGLE PLAYER submenu = ARCADE/TRAINING/CPU BATTLE. Deterministic
recipe: w -> SINGLE PLAYER, Return, w x3 (reset scroll to top = ARCADE), Return -> ARCADE.

Then press Return/space through the ARCADE character/colour select, watching for an arena
(mean>85) + find_fighter + a MOVING opponent (opponent_moves_sustained). The decisive
question (engineer 23:35): does ARCADE give the CPU a Brain (moving opponent), or is the
opponent frozen here too?

Evidence: state/probes/arcade_walk.jsonl.
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import nid_linux as n          # noqa: E402
import linux_state as ls       # noqa: E402

IID = 0
DISP = ":99"
PREFIX = Path.home() / "nidfarm" / "prefixes" / "1"
GAME = Path.home() / "nidfarm" / "game" / "Nidhogg.exe"
PROTON = Path.home() / ".local/opt/GE-Proton11-12-x86_64/proton"
SPY = Path.home() / "nidhogg-pau" / "spy" / "nidspy.so"
STEAM_ROOT = Path.home() / "fake_steam"
LOGDIR = Path.home() / "nidlogs"
REPO = Path.home() / "nidhogg-pau"
OUT = REPO / "state" / "probes" / "arcade_walk.jsonl"

ls.IID = IID


def log(obj):
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "a") as f:
        f.write(json.dumps(obj) + "\n")
    print(json.dumps(obj), flush=True)


def frame_stats():
    n.grab(IID, "/tmp/nid_rugg/aw.png")
    im = np.array(Image.open("/tmp/nid_rugg/aw.png").convert("RGB")).astype(int)
    r, g, b = im[:, :, 0], im[:, :, 1], im[:, :, 2]
    lum = 0.299 * r + 0.587 * g + 0.114 * b
    yellow = int(((r > 180) & (g > 160) & (b < 120)).sum())
    white_mask = (r > 235) & (g > 235) & (b > 235)
    white = int(white_mask.sum())
    mean = round(float(lum.mean()), 1)
    H = im.shape[0]
    x0, x1 = int(im.shape[1] * 0.10), int(im.shape[1] * 0.90)
    wt = white_mask[:, x0:x1].sum(axis=1)
    rows, cur = [], None
    for y in range(H):
        if wt[y] > 8:
            cur = [y, y] if cur is None else [cur[0], y]
        else:
            if cur is not None and cur[1] - cur[0] >= 6:
                rows.append(cur[0] // 2)
            cur = None
    if cur is not None and cur[1] - cur[0] >= 6:
        rows.append(cur[0] // 2)
    cls = ("black" if mean < 12 else
           "arena" if mean > 85 else
           "menu" if (mean > 55 and yellow > 8000) else
           "darkrows" if rows else
           "dark_other")
    return {"mean": mean, "yellow": yellow, "white": white, "rows": rows, "class": cls}


def hit_check():
    out = {"bound": None, "opp": None, "running": None, "opp_moves": None}
    a = ls.find_fighter()
    if not a:
        return out
    out["bound"] = hex(a)
    opp = ls.find_opponent(a)
    if opp is None:
        return out
    out["opp"] = hex(opp)
    out["running"] = bool(ls.round_running(a, opp, settle=2.0, min_px=5.0))
    out["opp_moves"] = bool(ls.opponent_moves_sustained(opp))
    return out


def press(key, hold=0.12):
    n.key(IID, key, hold=hold)


def launch():
    for d in Path("/proc").iterdir():
        if not d.name.isdigit():
            continue
        try:
            comm = (d / "comm").read_text().strip()
            env = (d / "environ").read_bytes()
        except OSError:
            continue
        if comm == "Nidhogg.exe" and b"DISPLAY=:99" in env.split(b"\0"):
            os.kill(int(d.name), 9)
        if comm in ("wine", "wineserver") and b"STEAM_COMPAT_DATA_PATH=" + str(PREFIX).encode() in env:
            os.kill(int(d.name), 9)
    time.sleep(2)
    fh = (LOGDIR / "arcade_walk.log").open("ab")
    env = dict(os.environ)
    env.pop("WAYLAND_DISPLAY", None)
    env.update(DISPLAY=DISP,
               STEAM_COMPAT_CLIENT_INSTALL_PATH=str(STEAM_ROOT),
               STEAM_COMPAT_DATA_PATH=str(PREFIX),
               SteamAppId="94400", SteamGameId="94400",
               WINEDEBUG="-all", LD_PRELOAD=str(SPY))
    args = [str(PROTON), "waitforexitandrun", str(GAME)]
    subprocess.Popen(args, env=env, stdout=fh, stderr=fh,
                     start_new_session=True, cwd=str(REPO))


def wait_menu(timeout=180):
    t0 = time.time()
    while time.time() - t0 < timeout:
        st = frame_stats()
        if st["class"] == "menu":
            return st
        if st["class"] == "title" and int(time.time() - t0) % 10 == 0:
            press("Return", hold=0.1)
        time.sleep(2)
    return st


def main():
    launch()
    st = wait_menu()
    log({"event": "menu", "frame": st})
    if st["class"] != "menu":
        log({"event": "no_menu", "frame": st})
        return 1

    # deterministic ARCADE walk
    for tag, key, wait in [
        ("w-single", "w", 2.0),       # MULTIPLAYER -> SINGLE PLAYER
        ("ret-sub", "Return", 2.5),   # enter SINGLE PLAYER
        ("w-top1", "w", 1.5),         # reset scroll to top (ARCADE)
        ("w-top2", "w", 1.5),
        ("w-top3", "w", 1.5),
        ("ret-arcade", "Return", 2.5),  # enter ARCADE
    ]:
        press(key)
        time.sleep(wait)
        log({"event": "walk", "tag": tag, "key": key, "frame": frame_stats()})

    # through ARCADE character/colour select
    for i, k in enumerate(["Return", "Return", "space", "Return", "space", "z",
                           "Return", "Return"]):
        press(k, hold=0.25)
        time.sleep(2.5)
        h = hit_check()
        fs = frame_stats()
        obs = {"event": "pick", "i": i, "key": k, "frame": fs, "hit": h}
        log(obs)
        if fs["class"] == "arena" and h["bound"]:
            log({"event": "arena", "i": i, "key": k, "hit": h})
            if h["opp_moves"]:
                log({"event": "HIT", "key": k, "hit": h})
                print("HIT: LIVE CPU", flush=True)
            else:
                log({"event": "frozen", "key": k, "hit": h})
                print("ARENA but FROZEN opponent", flush=True)
            break
    log({"event": "done", "ts": time.time()})
    return 0


if __name__ == "__main__":
    sys.exit(main())
