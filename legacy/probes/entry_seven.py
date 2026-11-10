#!/usr/bin/env python3
"""entry_seven.py — the macOS-verified 7-key TRAINING sequence, run on the Windows build.

EXPERIMENTS.md: the 8-key sequence had "one Enter too many, which flips the versus screen
into 2-player ARCADE. Correct sequence: 7 keys." The 10-key _try_entry sequence on Windows
lands on a frozen match-setup state (fighters at x=0,y=0, opponent never moves) - the same
"one Enter too many" failure. This runs the 7-key form and checks for a live CPU match.

    Return (title->main), W (->SINGLE PLAYER), Return (enter), S (->TRAINING),
    Return (training list), Return (personality), Return (difficulty -> fight)
"""
import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import nid_linux as n
import linux_state as ls
from screen_state import classify

SEQ = [("Return", 2.5), ("w", 2.0), ("Return", 2.5), ("s", 2.0),
       ("Return", 2.5), ("Return", 2.5), ("Return", 2.5)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start-at", type=int, default=0)
    a = ap.parse_args()
    for i in range(a.start_at, len(SEQ)):
        keysym, wait = SEQ[i]
        n.key(0, keysym, hold=0.12)
        time.sleep(wait)
        d = classify()
        print(f"  key {i:2d} {keysym:7s} -> state={d['state']} rows={d['text_rows_game_y']}")

    print("checking live match...")
    addr = ls.find_fighter()
    if addr:
        opp = ls.find_opponent(addr)
        print(f"  bound={hex(addr)} opp={hex(opp) if opp else None}")
        if opp:
            mv = ls.opponent_moves(opp, seconds=6.0, min_px=8.0)
            rr = ls.round_running(addr, opp, settle=3.0, min_px=5.0)
            print(f"  opponent_moves(6s)={mv}  round_running={rr}")
    else:
        print("  find_fighter: none")


if __name__ == "__main__":
    main()
