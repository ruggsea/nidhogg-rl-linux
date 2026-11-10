#!/usr/bin/env python3
"""walk2.py — deterministic-ish manual walk + map pick (engineer's improved version).

Improvements over walk_train_menu.py:
  1. scroll-to-top recipe: after entering SINGLE PLAYER, press w x3 to reset the cursor
     to ARCADE (top), then s x1 -> TRAINING (fixes the 3-item submenu non-determinism).
  2. map pick: expand the list (Right) FIRST, then confirm a map INSIDE the expanded list
     (the earlier sweep only pressed Return at the collapsed state = no-op).

    python3 tools/walk2.py
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
import nid_linux as n
import linux_state as ls

IID = 0
DISP = ":99"
PREFIX = Path.home() / "nidfarm" / "prefixes" / "1"
GAME = Path.home() / "nidfarm" / "game" / "Nidhogg.exe"
PROTON = Path.home() / ".local/opt/GE-Proton11-12-x86_64/proton"
SPY = Path.home() / "nidhogg-pau" / "spy" / "nidspy.so"
STEAM_ROOT = Path.home() / "fake_steam"
LOGDIR = Path.home() / "nidlogs"
REPO = Path.home() / "nidhogg-pau"
OUT = REPO / "state" / "probes" / "walk2.jsonl"


def log(obj):
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "a") as f:
        f.write(json.dumps(obj) + "\n")
    print(json.dumps(obj), flush=True)


def frame_stats():
    n.grab(IID, "/tmp/nid_rugg/w2.png")
    im = np.array(Image.open("/tmp/nid_rugg/w2.png").convert("RGB")).astype(int)
    r, g, b = im[:, :, 0], im[:, :, 1], im[:, :, 2]
    lum = 0.299 * r + 0.587 * g + 0.114 * b
    yellow = int(((r > 180) & (g > 160) & (b < 120)).sum())
    white_mask = (r > 235) & (g > 235) & (b > 235)
    white = int(white_mask.sum())
    mean = round(float(lum.mean()), 1)
    # text rows in the content band
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
    for p in list(PREFIX.glob("pfx.lock")) + list((PREFIX / "pfx").glob("*.lock")):
        try:
            p.unlink()
        except OSError:
            pass
    fh = (LOGDIR / "walk2.log").open("ab")
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
    for _ in range(120):
        cp = subprocess.run(["pgrep", "-x", "Nidhogg.exe"], capture_output=True, text=True)
        if cp.stdout.split():
            (Path.home() / "nidfarm" / "procs.json").write_text(
                json.dumps({"0": {"wrapper": int(cp.stdout.split()[0]), "display": DISP}}))
            break
        time.sleep(1)


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

    # walk to SINGLE PLAYER -> TRAINING with scroll-to-top reset
    for tag, key, wait in [
        ("w-single", "w", 2.0),       # MULTIPLAYER -> SINGLE PLAYER
        ("ret-sub", "Return", 2.5),   # enter SINGLE PLAYER
        ("w-top1", "w", 1.5),         # reset scroll to top (ARCADE)
        ("w-top2", "w", 1.5),
        ("w-top3", "w", 1.5),
        ("s-training", "s", 2.0),     # ARCADE -> TRAINING
        ("ret-train", "Return", 2.5), # enter TRAINING (partner list)
        ("ret-partner", "Return", 2.5),  # pick partner -> difficulty
        ("s-start", "s", 2.0),        # DIFFICULTY -> START
        ("ret-start", "Return", 3.0), # START -> map select
    ]:
        press(key)
        time.sleep(wait)
        log({"event": "walk", "tag": tag, "key": key, "frame": frame_stats()})

    # map pick: expand FIRST (Right), then confirm INSIDE the expanded list (Return),
    # then START (Return). NO Down (it collapses the list back to the difficulty window
    # and the subsequent Return re-triggers the difficulty->map crash).
    for i, k in enumerate(["Right", "Return", "Return", "space", "z", "Return"]):
        press(k, hold=0.25)
        time.sleep(2.5)
        h = hit_check()
        fs = frame_stats()
        obs = {"event": "pick", "i": i, "key": k, "frame": fs, "hit": h}
        log(obs)
        if fs["class"] == "arena" or (h["bound"] and h["opp_moves"]):
            log({"event": "HIT", "key": k, "hit": h})
            break
        if h["bound"] is None and i >= 1:
            # lost the bind (game advanced or crashed); stop pressing blindly
            break
    log({"event": "done", "ts": time.time()})
    return 0


if __name__ == "__main__":
    sys.exit(main())
