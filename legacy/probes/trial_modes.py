#!/usr/bin/env python3
"""trial_modes.py — enter each SINGLE PLAYER mode in turn and check for a live CPU.

Navigates title -> main menu -> SINGLE PLAYER, then for item i in 0..3: press S i
times, Return to enter, wait, and report find_fighter + opponent_moves (sustained).
The TRAINING mode is the one where P1 is drivable AND the opponent moves.

    python3 tools/trial_modes.py [--start-i 0]
"""
import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import nid_linux as n
import linux_state as ls


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start-i", type=int, default=0)
    a = ap.parse_args()

    # nav to SINGLE PLAYER submenu
    for keysym, wait in [("Return", 2.5), ("w", 2.0), ("Return", 2.5)]:
        n.key(0, keysym, hold=0.12)
        time.sleep(wait)
    print("in SINGLE PLAYER submenu; cursor at item 0")

    for i in range(a.start_i, 4):
        if i > 0:
            n.key(0, "s", hold=0.12)
            time.sleep(1.8)
        n.key(0, "Return", hold=0.12)
        time.sleep(3.0)
        addr = ls.find_fighter()
        opp = ls.find_opponent(addr) if addr else None
        mv = None
        if opp:
            mv = ls.opponent_moves(opp, seconds=8.0, min_px=8.0)
        print(f"item {i}: bound={hex(addr) if addr else None} opp={hex(opp) if opp else None} opponent_moves(8s)={mv}")
        # back out: Escape twice
        n.key(0, "Escape", hold=0.12); time.sleep(1.8)
        n.key(0, "Escape", hold=0.12); time.sleep(1.8)


if __name__ == "__main__":
    main()
