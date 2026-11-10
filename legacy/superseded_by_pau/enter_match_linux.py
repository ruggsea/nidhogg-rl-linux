#!/usr/bin/env python3
"""enter_match_linux.py — reach a real TRAINING match on artemis, verified by MEMORY.

The menu navigation is the one thing the project could not automate (OVERVIEW limit #5),
and the two ways it went wrong were both measured:

  * the main-menu rows are reached through a scrolling list under a fixed highlight bar, so
    the selected row is identified by the yellow dot under the bar (selected_y), never a
    coordinate;
  * the camera FOLLOWS P1 in a match, so the sprite stays put while the world scrolls — the
    sprite centroid is the wrong liveness oracle. The right one is memory: the bound fighter's
    x (tools/linux_state.find_fighter) and the opponent's x (find_opponent + opponent_moves).

This script walks title -> MENU -> SINGLE PLAYER -> TRAINING -> ladder -> BEGIN and returns
True only when the memory checks show a drivable P1 AND a moving CPU opponent.

    python3 tools/enter_match_linux.py [--tries 3] [--verbose]
"""
import argparse
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import nid_linux as n
import linux_state as ls

from PIL import Image  # noqa: E402


def window_box():
    """(x, y, w, h) of the game window inside the Xvfb frame, or None.

    The Xvfb display is 640x480 but the patched game window is 320x200 and sits at an
    offset (measured 160,149), so every pixel coordinate must be read in the CROPPED
    window, not the full grab.
    """
    w = n.window(0)
    if not w:
        return None
    r = n._xdo(n._pids()[str(0)]["display"], "getwindowgeometry", "--shell", w)
    d = {}
    for line in r.stdout.splitlines():
        k, _, v = line.partition("=")
        if k in ("X", "Y", "WIDTH", "HEIGHT"):
            d[k] = int(v)
    if "WIDTH" not in d:
        return None
    return d.get("X", 0), d.get("Y", 0), d["WIDTH"], d["HEIGHT"]


def frame():
    """The game window as a cropped HxWx3 array (320x200 on artemis)."""
    n.grab(0, "/tmp/nid_rugg/nav.png")
    a = np.array(Image.open("/tmp/nid_rugg/nav.png"))
    box = window_box()
    if box is None:
        return a
    x, y, w, h = box
    return a[y:y + h, x:x + w]


def selected_y():
    """y of the menu's selection dot (small yellow/orange dot at x~197-218), or None."""
    a = frame()
    if a is None or a.size == 0:
        return None
    r, g, b = a[:, :, 0].astype(int), a[:, :, 1].astype(int), a[:, :, 2].astype(int)
    m = (r > 190) & (g > 170) & (b < 130)
    m[:108, :] = False          # logo tail
    m[182:, :] = False
    m[:, :95] = False
    m[:, 260:] = False
    xmax = np.zeros(m.shape[0], dtype=int)
    for y in range(95, 182):
        row = np.nonzero(m[y])[0]
        if len(row):
            xmax[y] = row.max()
    ys = np.nonzero((xmax > 197) & (xmax < 218))[0]
    return int(ys.mean()) if len(ys) else None


def held(keysym, wait):
    n.key(0, keysym, hold=0.12)
    time.sleep(wait)


def ensure_menu(tries=10):
    for _ in range(tries):
        if selected_y() is not None:
            return True
        held("Return", 1.5)
    return selected_y() is not None


def in_match():
    """(True, addr) iff P1 is drivable AND the opponent moved >=8px/3s."""
    addr = ls.find_fighter()
    if not addr:
        return False, None
    opp = ls.find_opponent(addr)
    if opp is None:
        return False, addr
    return ls.opponent_moves(opp, seconds=3.0, min_px=8.0), addr


def navigate(verbose=True):
    """One navigation attempt. Returns True iff the memory checks see a live match."""
    # 0. a menu must be open; the title/READY screens have no selection dot.
    if not ensure_menu():
        if verbose:
            print("  no menu dot after Returns")
        return False

    # 1. MULTIPLAYER (default) -> SINGLE PLAYER. Up is the measured direction here.
    held("Up", 1.0)
    held("Return", 1.6)          # -> SINGLE PLAYER screen (HOW TO PLAY / TRAINING)
    held("Return", 1.6)          # TRAINING -> opponent ladder
    # 2. BEGIN sits at the bottom of the ladder; walk it then confirm.
    for _ in range(4):
        held("Down", 0.7)
    held("Return", 2.0)          # BEGIN -> match
    time.sleep(2.0)

    ok, addr = in_match()
    if verbose:
        print(f"  after sequence: in_match={ok} bound={hex(addr) if addr else None}")
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tries", type=int, default=3)
    ap.add_argument("--verbose", action="store_true")
    a = ap.parse_args()
    for t in range(a.tries):
        if a.verbose or True:
            print(f"attempt {t + 1}/{a.tries}")
        if navigate(verbose=True):
            print("REACHED LIVE MATCH")
            return 0
        time.sleep(1.0)
    print("did not reach a live match")
    return 1


if __name__ == "__main__":
    sys.exit(main())
