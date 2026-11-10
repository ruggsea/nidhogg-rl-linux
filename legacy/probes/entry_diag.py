#!/usr/bin/env python3
"""entry_diag.py — run the 10-key TRAINING entry sequence, reporting the menu state
after EVERY key (text rows + highlight bar), so a wrong landing is seen at the step
that caused it, not at the end.

    python3 tools/entry_diag.py [--start-at N]

Keys (index -> meaning), from train_state._try_entry on the Windows build:
    0 Return  title -> MAIN MENU
    1 w       MULTIPLAYER -> SINGLE PLAYER
    2 Return  -> SINGLE PLAYER submenu (ARCADE / TRAINING)
    3 s       ARCADE -> TRAINING
    4 Return  -> TRAINING partner list
    5 Return  pick partner -> DIFFICULTY + START submenu
    6 s       DIFFICULTY -> START
    7 Return  START -> match
    8 Return  skip level-intro card
    9 Return  round start (some intros need a second press)
"""
import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import nid_linux as n
import linux_state as ls
from screen_state import classify

SEQ = [
    ("Return", 2.5), ("w", 2.0), ("Return", 2.5), ("s", 2.0), ("Return", 2.5),
    ("Return", 2.5), ("s", 2.0), ("Return", 2.5), ("Return", 2.0), ("Return", 1.5),
]


def read_menu():
    return classify()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start-at", type=int, default=0)
    a = ap.parse_args()

    print(f"start-at={a.start_at}")
    for i in range(a.start_at, len(SEQ)):
        keysym, wait = SEQ[i]
        n.key(0, keysym, hold=0.12)
        time.sleep(wait)
        d = read_menu()
        rows = d["text_rows_game_y"]
        print(f"  key {i:2d} {keysym:7s} -> state={d['state']} rows={rows}")

    # final: is there a live match? (bind by response + opponent moves)
    print("  checking live match (find_fighter + opponent_moves)...")
    addr = ls.find_fighter()
    if addr:
        opp = ls.find_opponent(addr)
        if opp is not None:
            moves = ls.opponent_moves(opp, seconds=4.0, min_px=8.0)
            print(f"  bound={hex(addr)} opp={hex(opp)} opponent_moves(4s)={moves}")
        else:
            print(f"  bound={hex(addr)} but no opponent record")
    else:
        print("  find_fighter: no drivable fighter (not in an arena, or no control)")


if __name__ == "__main__":
    main()
