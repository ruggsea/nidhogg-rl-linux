#!/usr/bin/env python3
"""map_submenu.py — reach a submenu and map its items by tracking the selection
cursor with frame-diff after each S press (the only thing that moves is the
highlight/selection, so the diff region = the selected item's location).

    python3 tools/map_submenu.py [--nav "Return w Return"] [--steps N]

Default nav: Return (demo/title -> main menu), w (-> SINGLE PLAYER), Return (enter).
Then N S-presses, each followed by a frame diff locating the moved selection.
"""
import argparse
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import nid_linux as n


def grab(tag):
    n.grab(0, f"/tmp/nid_rugg/ms_{tag}.png")
    return np.array(Image.open(f"/tmp/nid_rugg/ms_{tag}.png")).astype(int)[40:440]


def changed_region(a1, a2):
    c = np.abs(a1 - a2)
    mask = c.max(axis=2) > 30
    ys, xs = np.nonzero(mask)
    if len(ys) == 0:
        return None
    return (int(ys.min()) + 40, int(ys.max()) + 40, int(xs.min()), int(xs.max()), int(len(ys)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--nav", type=str, default="Return w Return")
    ap.add_argument("--steps", type=int, default=6)
    a = ap.parse_args()

    for tok in a.nav.split():
        n.key(0, tok, hold=0.12)
        time.sleep(2.2)
    print(f"nav '{a.nav}' done")

    prev = grab("p0")
    time.sleep(0.5)
    for i in range(a.steps):
        before = grab("b")
        n.key(0, "s", hold=0.12)
        time.sleep(1.8)
        after = grab("c")
        r = changed_region(before, after)
        print(f"  S#{i+1}: changed region {r}")
    # final: what does the screen look like (row structure)
    n.grab(0, "/tmp/nid_rugg/ms_final.png")
    a = np.array(Image.open("/tmp/nid_rugg/ms_final.png")).astype(int)[40:440]
    r, g, b = a[:, :, 0], a[:, :, 1], a[:, :, 2]
    for th in (120, 180):
        text = (r > th) & (g > th) & (b > th) & (np.abs(r - g) < 60) & (np.abs(g - b) < 60)
        ys = np.nonzero(text.sum(axis=1) > 4)[0]
        rows = []
        if len(ys):
            cur = [ys[0], ys[0]]
            for y in ys[1:]:
                if y - cur[1] <= 5:
                    cur[1] = y
                else:
                    if cur[1] - cur[0] >= 2:
                        rows.append((cur[0] // 2, cur[1] // 2))
                    cur = [y, y]
            if cur[1] - cur[0] >= 2:
                rows.append((cur[0] // 2, cur[1] // 2))
        print(f"  final text rows (>{th}, game y): {rows}")


if __name__ == "__main__":
    main()
