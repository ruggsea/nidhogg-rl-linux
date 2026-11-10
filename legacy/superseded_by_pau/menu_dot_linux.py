#!/usr/bin/env python3
"""menu_dot_linux.py — Nidhogg's menu selection marker, Pau's way, on artemis.

The selected menu item is marked by a YELLOW DOT (●) whose pixels reach further right
(x~197-218 in 320x200 game space) than the labels (which stop at x~185). So the selected
row is simply the row whose yellow pixels reach furthest right. Nothing is hardcoded
about item order: enumerate_rows() learns it by pressing Down and watching where the dot
lands.

This is more robust than white-text detection: the dot is the game's own selection marker,
unambiguous and unaffected by labels, floor texture, or the attract demo.

On artemis the window is 640x480 with the game content letterboxed at 640x400 (2x scale,
y offset 40), so Pau's 320x200 coordinates are doubled inside the content crop and the
result is reported back in GAME space (y/2), matching menu_rows_linux.py.

    python3 tools/menu_dot_linux.py             # print the selected row (game y), or None
    python3 tools/menu_dot_linux.py --enumerate # learn the row list by pressing Down
    python3 tools/menu_dot_linux.py --goto 2    # press Down until the dot sits on row 2
"""
import argparse
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import nid_linux as n
from PIL import Image

# content crop inside the 640x480 Xvfb frame (measured).
Y0, Y1 = 40, 440
X0, X1 = 0, 640
SCALE = 2               # content is 2x the 320x200 game space

# Pau's selected_y mask, in 320x200 game space -> doubled for the content crop.
M_Y_LO, M_Y_HI = 108 * SCALE, 182 * SCALE      # y scan band (below the logo tail)
M_X_LO, M_X_HI = 95 * SCALE, 260 * SCALE       # x scan band
DOT_X_LO, DOT_X_HI = 197 * SCALE, 218 * SCALE  # the dot reaches further right than labels


def frame():
    n.grab(0, "/tmp/nid_rugg/menu_dot.png")
    a = np.array(Image.open("/tmp/nid_rugg/menu_dot.png")).astype(int)
    return a[Y0:Y1, X0:X1]


def selected_y():
    """game-space y of the selected row (the yellow dot), or None."""
    c = frame()
    r, g, b = c[:, :, 0], c[:, :, 1], c[:, :, 2]
    m = (r > 190) & (g > 170) & (b < 130)
    m[:M_Y_LO, :] = False
    m[M_Y_HI:, :] = False
    m[:, :M_X_LO] = False
    m[:, M_X_HI:] = False
    xmax = np.zeros(m.shape[0], dtype=int)
    ys = np.nonzero(m)[0]
    for y in np.unique(ys):
        row = np.nonzero(m[y])[0]
        if len(row):
            xmax[y] = row.max()
    hits = np.nonzero((xmax > DOT_X_LO) & (xmax < DOT_X_HI))[0]
    return int(hits.mean()) // SCALE if len(hits) else None


def enumerate_rows(presses=8, wait=0.7):
    """Row y-positions in menu order, learned by pressing Down (the list wraps)."""
    seen = []
    y = selected_y()
    if y is None:
        return seen
    seen.append(y)
    for _ in range(presses):
        n.key(0, "Down", hold=0.12)
        time.sleep(wait)
        y = selected_y()
        if y is None or y in seen:
            break
        seen.append(y)
    return seen


def goto_row(rows, index, tries=12, wait=0.7):
    """Press Down until the dot sits on rows[index]."""
    target = rows[index]
    for _ in range(tries):
        y = selected_y()
        if y is None:
            return False
        if abs(y - target) <= 2:
            return True
        n.key(0, "Down", hold=0.12)
        time.sleep(wait)
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--enumerate", action="store_true")
    ap.add_argument("--goto", type=int, default=None)
    a = ap.parse_args()
    if a.enumerate:
        rows = enumerate_rows()
        if not rows:
            print("no menu dot on screen (title/attract/non-menu)")
            sys.exit(1)
        for i, y in enumerate(rows):
            print(f"row {i}: game_y {y}")
        return 0
    if a.goto is not None:
        rows = enumerate_rows()
        if not rows:
            print("no menu dot")
            sys.exit(1)
        print("rows:", rows)
        print("goto", a.goto, "->", "ok" if goto_row(rows, a.goto) else "FAILED")
        return 0
    y = selected_y()
    print(f"selected row game_y: {y}" if y is not None else "no menu dot on screen")
    return 0 if y is not None else 1


if __name__ == "__main__":
    sys.exit(main())
