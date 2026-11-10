#!/usr/bin/env python3
"""reach_match.py — walk the LOCAL multiplayer flow to a real match, then observe.

Flow from the game's own localtest log (state/probes/localtest_full_run.log):
  title -> 5x Return -> ready-up room (room 4, P1 at integer x=8 y=128)
  -> hold d ~2.5s to WALK onto a plate -> level select (room 17)
  -> "the pick timer starts the match" (~10s, NO pick key needed) -> arena (26-77).

Logs state/probes/reach_match.jsonl. Uses frame_stats (fast) for continuous monitoring
and find_fighter (slow) only at key decision points.

    python3 tools/reach_match.py
"""
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import nid_linux as n
import linux_state as ls
from PIL import Image

OUT = Path.home() / "nidhogg-pau" / "state" / "probes" / "reach_match.jsonl"
KNOWN = np.array([2, 3, 4, 17, 19, 20, 25] + list(range(26, 78)), dtype=np.int32)


def logline(obj):
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "a") as f:
        f.write(json.dumps(obj) + "\n")
    print(json.dumps(obj), flush=True)


def frame_stats(tag):
    path = f"/tmp/nid_rugg/rm_{tag}.png"
    n.grab(0, path)
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
    """Most-common known-room int32 across the biggest 3 rw regions (vectorized)."""
    from collections import Counter
    pid = n._game_pid(0)
    if not pid:
        return None
    counts = Counter()
    for a, b in ls._regions()[:3]:
        raw = n.memory(pid, a, b - a, "/tmp/nid_rugg/rm_room.bin")
        if raw is None:
            continue
        arr = np.frombuffer(raw, "<i4")
        vals, cnts = np.unique(arr[np.isin(arr, KNOWN)], return_counts=True)
        for v, c in zip(vals.tolist(), cnts.tolist()):
            counts[int(v)] += c
    return counts.most_common(3)


def wait_title(timeout=150):
    t0 = time.time()
    while time.time() - t0 < timeout:
        if not n._game_pid(0):
            time.sleep(2)
            continue
        fs = frame_stats("title")
        if fs["dark"] > 150000 and fs["pure"] > 3000:
            return fs
        time.sleep(3)
    return frame_stats("title")


def main():
    pid = n._game_pid(0)
    if not pid:
        logline({"event": "no_game"})
        sys.exit("no game")
    logline({"event": "start", "pid": pid, "ts": time.time()})

    logline({"event": "title", "frame": wait_title()})

    for i in range(5):
        n.key(0, "Return", hold=0.12)
        time.sleep(2.2)
        logline({"event": "key", "key": "Return", "step": i, "ts": time.time()})

    p1 = ls.find_fighter(0)
    logline({"event": "ready_check", "ts": time.time(),
             "p1": hex(p1) if p1 else None,
             "p1_x": ls.read_f(p1) if p1 else None,
             "p1_y": ls.read_f(p1 + 4) if p1 else None,
             "room": room_top(), "frame": frame_stats("ready")})

    # walk onto the plate: hold d ~2.5s (localtest "walked onto the plates" ~80-120 steps)
    x0 = ls.read_f(p1) if p1 else None
    n.key(0, "d", hold=2.5)
    time.sleep(0.5)
    logline({"event": "walk", "ts": time.time(), "x_before": x0,
             "room": room_top(), "frame": frame_stats("after_walk")})

    # observe 24s: level select -> pick timer (~10s) -> match. frame every 3s, find_fighter once at end.
    for i in range(8):
        time.sleep(3.0)
        logline({"event": "obs", "i": i, "ts": time.time(),
                 "room": room_top(), "frame": frame_stats(f"obs{i}")})

    p1 = ls.find_fighter(0)
    logline({"event": "final_bind", "ts": time.time(),
             "p1": hex(p1) if p1 else None,
             "p1_x": ls.read_f(p1) if p1 else None,
             "p1_y": ls.read_f(p1 + 4) if p1 else None,
             "room": room_top()})

    logline({"event": "done", "ts": time.time()})
    print("DONE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
