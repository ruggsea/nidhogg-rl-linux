#!/usr/bin/env python3
"""menu_rows2.py — full text-row read at a LOW brightness threshold (>120), plus the
grey highlight bar, so menu items rendered dimly are not undercounted.

The earlier reader used pure-white (>235) and missed items rendered at ~120-180.
Prints every text row in game space and marks the selected row (grey highlight band).

    python3 tools/menu_rows2.py
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import nid_linux as n

Y0, Y1 = 40, 440
X0, X1 = 0, 640


def rows_of(mask, min_run=3):
    ys = np.nonzero(mask)[0]
    rows, cur = [], None
    for y in ys:
        cur = [y, y] if cur is None else [cur[0], y]
        if y - cur[0] > 3:
            if cur[1] - cur[0] >= min_run:
                rows.append((cur[0], cur[1]))
            cur = [y, y]
    if cur is not None and cur[1] - cur[0] >= min_run:
        rows.append((cur[0], cur[1]))
    return rows


def main():
    n.grab(0, "/tmp/nid_rugg/mr2.png")
    a = np.array(Image.open("/tmp/nid_rugg/mr2.png")).astype(int)[Y0:Y1, X0:X1]
    r, g, b = a[:, :, 0], a[:, :, 1], a[:, :, 2]
    # text: near-neutral bright
    text = (r > 120) & (g > 120) & (b > 120) & (np.abs(r - g) < 60) & (np.abs(g - b) < 60)
    # highlight bar: grey neutral band behind a row (the selected item)
    hbar = ((r > 100) & (r < 200) & (g > 100) & (g < 200) & (b > 100) & (b < 200)
            & (np.abs(r - g) < 20) & (np.abs(g - b) < 20))
    text_by_row = text.sum(axis=1)
    hbar_by_row = hbar.sum(axis=1)
    text_rows = rows_of(text_by_row > 4, min_run=2)
    bar_rows = rows_of(hbar_by_row > 250, min_run=4)
    print("text rows (game y):", [(a0 // 2, a1 // 2) for a0, a1 in text_rows])
    print("highlight bars (game y):", [(a0 // 2, a1 // 2) for a0, a1 in bar_rows])
    sel = []
    for (ta, tb) in text_rows:
        for (ba, bb) in bar_rows:
            if ba <= (ta + tb) / 2 <= bb:
                sel.append((ta // 2, tb // 2))
    print("selected:", sel if sel else None)


if __name__ == "__main__":
    main()
