#!/usr/bin/env python3
"""grid_explore.py — reach the rLevelSelect(17) grid and probe its selection keys.

The 10-key entry sequence ends on a 2-column grid (room 17). This tool navigates there
from the current state, then reports where the selection cursor is and how keys move
it, and finally whether any key enters an arena (find_fighter + opponent_moves).

    python3 tools/grid_explore.py [--start-at 0] [--moves "s s Return"]
"""
import argparse
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import nid_linux as n
import linux_state as ls

SEQ = [("Return", 2.5), ("w", 2.0), ("Return", 2.5), ("s", 2.0), ("Return", 2.5),
       ("Return", 2.5), ("s", 2.0), ("Return", 2.5), ("Return", 2.0)]


def grab(tag):
    n.grab(0, f"/tmp/nid_rugg/ge_{tag}.png")
    return np.array(Image.open(f"/tmp/nid_rugg/ge_{tag}.png")).astype(int)[40:440]


def changed_region(a1, a2):
    c = np.abs(a1 - a2)
    mask = c.max(axis=2) > 30
    ys, xs = np.nonzero(mask)
    if len(ys) == 0:
        return None
    return (int(ys.min()) + 40, int(ys.max()) + 40, int(xs.min()), int(xs.max()), int(len(ys)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start-at", type=int, default=0)
    ap.add_argument("--moves", type=str, default="")
    a = ap.parse_args()

    for i in range(a.start_at, len(SEQ)):
        keysym, wait = SEQ[i]
        n.key(0, keysym, hold=0.12)
        time.sleep(wait)
    print("on grid after 9 keys")

    # report cursor: press nothing, grab twice to see if animated
    b1 = grab("b1"); time.sleep(0.6); b2 = grab("b2")
    print("idle motion px:", int((np.abs(b1 - b2).max(axis=2) > 30).sum()))

    # apply moves, reporting the changed region each time
    for tok in a.moves.split():
        if tok in ("Return", "s", "w", "f", "space", "a", "d"):
            before = grab("pre")
            n.key(0, tok if tok != "space" else "space", hold=0.12)
            time.sleep(2.0)
            after = grab("post")
            r = changed_region(before, after)
            print(f"  {tok:8s} -> changed region y{x if False else ''} {r}")
        else:
            print(f"  skip unknown key {tok}")

    # final live-match check
    addr = ls.find_fighter()
    if addr:
        opp = ls.find_opponent(addr)
        print(f"LIVE? bound={hex(addr)} opp={hex(opp) if opp else None}")
        if opp:
            print("  opponent_moves(4s) =", ls.opponent_moves(opp, seconds=4.0, min_px=8.0))
    else:
        print("LIVE? no drivable fighter")


if __name__ == "__main__":
    main()
