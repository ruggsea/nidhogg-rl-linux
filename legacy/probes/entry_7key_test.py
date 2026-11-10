#!/usr/bin/env python3
"""entry_7key_test.py — Pau's exact 7-key training entry, tested on the Linux build.

Pau's measured recipe (his NOTES.md, Session 41/46): the ONE sequence that reaches a
live TRAINING match against an ACTIVE CPU is SEVEN keys —

    Enter(13), W(87), Enter(13), S(83), Enter(13), Enter(13), Enter(13)

verified by CPU motion (>15 px idle) and both fighters at y~192 (the ground). An 8th
Enter, or an extra S press, flips it into ARCADE (2-player READY, CPU inert) or into the
level-select grid. Our 10-key port (enter_training_linux.py) had an extra S + trailing
Returns and landed on the level-select grid (which the -lttraining harness also crashes
on) — so this test uses Pau's exact 7 keys, no trailing presses.

    python3 tools/entry_7key_test.py [--tries 3] [--verbose]

Success = memory-verified live match: find_fighter binds a drivable P1 AND the opponent
moves >=8px/3s (an active CPU, not the READY statue and not the attract demo).
"""
import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import nid_linux as n
import linux_state as ls

# Pau's exact 7-key sequence (GML codes -> xdotool keysyms).
SEQ = [
    ("Return", 2.2),   # title -> MAIN MENU
    ("w", 1.8),        # MULTIPLAYER -> SINGLE PLAYER (cursor starts on MULTIPLAYER)
    ("Return", 2.2),   # -> SINGLE PLAYER submenu (ARCADE / TRAINING)
    ("s", 1.8),        # ARCADE -> TRAINING
    ("Return", 2.2),   # -> TRAINING partner list
    ("Return", 2.2),   # pick partner
    ("Return", 2.5),   # START -> match
]
# No 8th press, no trailing Return: that is what flips it into ARCADE / level select.


def in_match(verbose=False):
    """(ok, addr, why) — a live match = drivable P1 AND a moving CPU opponent."""
    addr = ls.find_fighter()
    if not addr:
        return False, None, "no drivable fighter"
    if not ls.prove_control(addr):
        return False, addr, "fighter not drivable (D/A)"
    opp = ls.find_opponent(addr)
    if opp is None:
        return False, addr, "no opponent record"
    moves = ls.opponent_moves(opp, seconds=3.0, min_px=8.0)
    if not moves:
        return False, addr, "opponent inert (READY/ARCADE statue)"
    return True, addr, "live match (drivable + active CPU)"


def run_one(verbose):
    for i, (keysym, wait) in enumerate(SEQ):
        n.key(0, keysym, hold=0.12)
        time.sleep(wait)
        if verbose:
            print(f"  key {i}: {keysym} (wait {wait}s)")
    ok, addr, why = in_match(verbose)
    if verbose:
        print(f"  after 7 keys: ok={ok} addr={hex(addr) if addr else None} why={why}")
    return ok, addr, why


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tries", type=int, default=2)
    ap.add_argument("--verbose", action="store_true")
    a = ap.parse_args()
    for t in range(a.tries):
        print(f"attempt {t + 1}/{a.tries}", flush=True)
        ok, addr, why = run_one(a.verbose)
        if ok:
            print(f"REACHED LIVE MATCH addr={hex(addr)}", flush=True)
            return 0
        print(f"  not live: {why}", flush=True)
        time.sleep(1.0)
    print("did not reach a live match", flush=True)
    return 1


if __name__ == "__main__":
    sys.exit(main())
