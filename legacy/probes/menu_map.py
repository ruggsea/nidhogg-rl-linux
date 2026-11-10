#!/usr/bin/env python3
"""menu_map.py — full read of Nidhogg's menu state on artemis: text rows (pure
white), the grey highlight bar (selected item), and the vertical order.

    python3 tools/menu_map.py

Prints, in game space (content crop is 2x scaled, y offset 40):
  - each pure-white text row [y0, y1] and its mean brightness (white ~255)
  - the highlight bar [y0, y1] (grey neutral band, the selected item)
  - the selected text row (the one the bar is behind)
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import nid_linux as n

Y0, Y1 = 40, 440
X0, X1 = 0, 640


def _rows(mask):
    """cluster True rows (1-D) into [a,b] bands with >=4px runs."""
    ys = np.nonzero(mask)[0]
    rows, cur = [], None
    for y in ys:
        cur = [y, y] if cur is None else [cur[0], y]
        if y - cur[0] > 3 and (y - cur[0]) % 1 == 0:
            pass
    # simpler: walk pixel rows
    rows, cur = [], None
    n = mask.shape[0]
    for y in range(n):
        if mask[y]:
            cur = [y, y] if cur is None else [cur[0], y]
        else:
            if cur is not None and cur[1] - cur[0] >= 3:
                rows.append((cur[0], cur[1]))
            cur = None
    if cur is not None and cur[1] - cur[0] >= 3:
        rows.append((cur[0], cur[1]))
    return rows


def main():
    n.grab(0, "/tmp/nid_rugg/map.png")
    a = np.array(Image.open("/tmp/nid_rugg/map.png")).astype(int)[Y0:Y1, X0:X1]
    r, g, b = a[:, :, 0], a[:, :, 1], a[:, :, 2]
    pure = (r > 235) & (g > 235) & (b > 235)
    # highlight bar: neutral grey, mid brightness, spans width
    hbar = ((r > 100) & (r < 205) & (g > 100) & (g < 205) & (b > 100) & (b < 205)
            & (np.abs(r - g) < 18) & (np.abs(g - b) < 18))
    text_by_row = pure.sum(axis=1)
    bar_by_row = hbar.sum(axis=1)
    # a highlight bar row must be mostly grey across the width
    bar_mask = bar_by_row > 300          # >= ~half width grey

    text_rows = _rows(text_by_row > 4)
    bar_rows = _rows(bar_mask)
    print("text rows (game y):")
    for (a0, a1) in text_rows:
        print(f"  {a0//2:3d}-{a1//2:3d}  white={text_by_row[a0:a1+1].max()}")
    print("highlight bars (game y):")
    for (a0, a1) in bar_rows:
        print(f"  {a0//2:3d}-{a1//2:3d}")
    # selected = text row overlapping a highlight bar
    sel = None
    for (ta, tb) in text_rows:
        for (ba, bb) in bar_rows:
            if ba <= (ta + tb) / 2 <= bb:
                sel = (ta, tb)
    print("selected text row:", f"{sel[0]//2}-{sel[1]//2}" if sel else None)


if __name__ == "__main__":
    main()
