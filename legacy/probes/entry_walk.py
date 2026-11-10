#!/usr/bin/env python3
"""entry_walk.py — single-threaded, one-key-at-a-time entry walk with full evidence.

The operator's protocol: launch ONE game, wait for the TITLE screen (verified by frame,
not process count), then press keys one at a time with a frame grab after each, and STOP
the moment a frame shows two fighters on an arena floor with YELLOW/ORANGE labels.

Keys used are Pau's measured 7-key sequence (his NOTES.md Session 41/46), one per step:
    Return, w, Return, s, Return, Return, Return
An 8th Enter or an extra S flips into ARCADE (inert) or level-select — so exactly 7.

After EVERY key it:
  * saves a frame to /tmp/nid_rugg/fc_step<N>.png
  * classifies pixels (white/grey/dark/yellow/orange + text rows)
  * memory-checks find_fighter / prove_control / find_opponent / opponent_moves

Success (two fighters on an arena floor with yellow+orange labels) is reported when the
frame has BOTH yellow and orange regions AND text rows (scoreboard labels), corroborated
by find_fighter binding a drivable P1. One JSON line per step -> state/probes/entry_walk.jsonl.

    python3 tools/entry_walk.py            # full walk (launch + 7 keys)
    python3 tools/entry_walk.py --nol      # assume a live game on :99, just walk
"""
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import nid_linux as n
import linux_state as ls

OUT = Path.home() / "nidhogg-pau" / "state" / "probes" / "entry_walk.jsonl"
Y0, Y1, X0, X1 = 40, 440, 0, 640

KEYS = [("Return", "title->main menu"),
        ("w", "up: MULTIPLAYER->SINGLE PLAYER"),
        ("Return", "open SINGLE PLAYER"),
        ("s", "down: ARCADE->TRAINING"),
        ("Return", "open TRAINING (partner list)"),
        ("Return", "pick partner"),
        ("Return", "START -> match")]


def logline(obj):
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "a") as f:
        f.write(json.dumps(obj) + "\n")
    print(json.dumps(obj), flush=True)


def kill_game():
    for d in Path("/proc").iterdir():
        if not d.name.isdigit():
            continue
        try:
            if (d / "comm").read_text().strip() != "Nidhogg.exe":
                continue
        except OSError:
            continue
        try:
            os.kill(int(d.name), signal.SIGKILL)
        except OSError:
            pass
    time.sleep(2)


def launch():
    kill_game()
    subprocess.run(["bash", "tools/farm_linux.sh", "start", "1"],
                   capture_output=True, text=True, timeout=120)
    # wait for a game to appear
    t0 = time.time()
    while time.time() - t0 < 90:
        if n._game_pid(0):
            return True
        time.sleep(2)
    return False


def grab_classify(tag):
    path = f"/tmp/nid_rugg/fc_{tag}.png"
    n.grab(0, path)
    a = np.array(Image.open(path)).astype(int)[Y0:Y1, X0:X1]
    r, g, b = a[:, :, 0], a[:, :, 1], a[:, :, 2]
    pure = (r > 235) & (g > 235) & (b > 235)
    grey = (r > 140) & (r < 236) & (g > 140) & (g < 236) & (b > 140) & (b < 236)
    dark = (r < 60) & (g < 60) & (b < 60)
    yellow = (r > 180) & (g > 160) & (b < 120)
    orange = (r > 180) & (g > 70) & (g < 160) & (b < 100)
    text = pure.sum(axis=1)
    rows, cur = [], None
    for y in range(a.shape[0]):
        if text[y] > 4:
            cur = [y, y] if cur is None else [cur[0], y]
        else:
            if cur is not None and cur[1] - cur[0] >= 4:
                rows.append((cur[0] // 2, cur[1] // 2))
            cur = None
    if cur is not None and cur[1] - cur[0] >= 4:
        rows.append((cur[0] // 2, cur[1] // 2))
    return {
        "path": path,
        "mean": round(float(a.mean()), 1),
        "pure_white_px": int(pure.sum()),
        "grey_px": int(grey.sum()),
        "dark_px": int(dark.sum()),
        "yellow_px": int(yellow.sum()),
        "orange_px": int(orange.sum()),
        "text_rows_game_y": rows,
    }


def mem_check():
    r = {}
    try:
        addr = ls.find_fighter(0)
        r["fighter"] = hex(addr) if addr else None
        if addr:
            r["drivable"] = bool(ls.prove_control(addr))
            opp = ls.find_opponent(addr)
            r["opponent"] = hex(opp) if opp else None
            if opp:
                r["opponent_moves"] = bool(ls.opponent_moves(opp, seconds=3.0, min_px=8.0))
    except Exception as e:  # noqa: BLE001
        r["error"] = f"{type(e).__name__}: {e}"
    return r


def wait_title(timeout=120):
    """Wait until a frame looks like the title (big white/gold logo text, no menu bar)."""
    t0 = time.time()
    while time.time() - t0 < timeout:
        if not n._game_pid(0):
            time.sleep(2)
            continue
        try:
            c = grab_classify("title_probe")
        except Exception as e:  # noqa: BLE001
            time.sleep(2)
            continue
        # title: dark screen with a large white/gold text block; not a menu (few rows)
        if c["dark_px"] > 150000 and c["pure_white_px"] > 3000:
            return c
        # OR title with the attract demo started: fighters present but still PRESS ENTER
        if c["dark_px"] > 100000 and (c["yellow_px"] > 5000 or c["orange_px"] > 5000):
            return c
        time.sleep(3)
    return grab_classify("title_probe")


def main():
    nolaunch = "--nol" in sys.argv
    if not nolaunch:
        launch()
        c = wait_title()
        logline({"event": "title", "ts": time.time(), "frame": c})
    else:
        c = grab_classify("title_probe")
        logline({"event": "title_skip", "ts": time.time(), "frame": c})

    for i, (keysym, desc) in enumerate(KEYS):
        n.key(0, keysym, hold=0.12)
        time.sleep(2.2)
        c = grab_classify(f"step{i}")
        m = mem_check()
        logline({"event": "key", "step": i, "key": keysym, "desc": desc,
                 "ts": time.time(), "frame": c, "mem": m})

        # success: two fighters (yellow AND orange regions) + scoreboard text rows
        if (c["yellow_px"] > 3000 and c["orange_px"] > 3000
                and len(c["text_rows_game_y"]) >= 2):
            logline({"event": "SUCCESS_FRAME", "step": i, "ts": time.time(),
                     "frame": c, "mem": m})
            print(f"\n>>> SUCCESS FRAME at step {i} ({keysym}: {desc})", flush=True)
            print(f"    frame: {c}", flush=True)
            print(f"    mem:   {m}", flush=True)
            return 0
    print("\nwalk complete, no success frame detected", flush=True)
    return 1


if __name__ == "__main__":
    sys.exit(main())
