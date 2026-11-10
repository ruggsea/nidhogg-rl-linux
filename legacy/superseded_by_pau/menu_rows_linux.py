#!/usr/bin/env python3
"""menu_rows_linux.py — read Nidhogg's menu state from the window, no OCR.

Finds the text rows and which one is selected (the row drawn on a grey highlight bar),
ported from Pau's macOS nav.py menu_rows(). On artemis the window is 640x480 with the
game content letterboxed at 640x400 (2x scale of the 320x200 room space, y offset 40),
so coordinates are read in the content crop and reported in GAME space (y/2).

Prints one line per text row: index, game-space y, background brightness, and whether
it is the selected row. Selection is the row with the brightest grey background.

    python3 tools/menu_rows_linux.py
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import nid_linux as n
from PIL import Image

# content crop: the 640x400 game area inside the 640x480 Xvfb frame (measured).
Y0, Y1 = 40, 440
X0, X1 = 0, 640
X_BAND = (0.10, 0.90)      # x fraction of the content crop to scan for text rows


def frame():
    n.grab(0, "/tmp/nid_rugg/menu.png")
    a = np.array(Image.open("/tmp/nid_rugg/menu.png")).astype(int)
    return a[Y0:Y1, X0:X1]


def menu_rows():
    c = frame()
    H, W = c.shape[:2]
    r, g, b = c[:, :, 0], c[:, :, 1], c[:, :, 2]
    # Pure-white text only. Measured false positive (prober 14:55): the r>175 test also
    # matches the arena floor (light grey ~RGB 192), so on the attract demo it reports a
    # fake "selected row". The attract-demo frame has 77198 light-grey px vs 162 pure-white
    # px; a >235 threshold keeps the 162 and drops the floor.
    white = (r > 235) & (g > 235) & (b > 235)
    x0, x1 = int(W * X_BAND[0]), int(W * X_BAND[1])
    band = white[:, x0:x1]
    text = band.sum(axis=1)
    bg = c[:, x0:x1].mean(axis=2)

    rows, cur = [], None
    for y in range(H):
        if text[y] > 8:
            if cur is None:
                cur = [y, y]
            elif y - cur[1] <= 10:
                cur[1] = y
            else:
                if cur[1] - cur[0] >= 6:
                    rows.append(tuple(cur))
                cur = [y, y]
        else:
            if cur is not None and cur[1] - cur[0] >= 6:
                rows.append(tuple(cur))
            cur = None
    if cur is not None and cur[1] - cur[0] >= 6:
        rows.append(tuple(cur))

    scored = [float(bg[max(0, a - 4):min(H - 1, b + 4)].mean()) for (a, b) in rows]
    mx = max(scored) if scored else 0.0
    sel = scored.index(mx) if mx > 30 else -1
    return rows, scored, sel


if __name__ == "__main__":
    rows, scored, sel = menu_rows()
    if not rows:
        print("no menu rows (title/attract, or a non-menu screen)")
        sys.exit(0)
    for i, (a, b) in enumerate(rows):
        mark = " <== SELECTED" if i == sel else ""
        print(f"row {i}: game_y {a//2}-{b//2}  bg={scored[i]:.1f}{mark}")
    print(f"selected row index: {sel}")
