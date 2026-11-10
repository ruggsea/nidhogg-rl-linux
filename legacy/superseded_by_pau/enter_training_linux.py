#!/usr/bin/env python3
"""enter_training_linux.py — reach a real TRAINING match on artemis, corrected keys.

The first port (enter_match_linux.py) navigated with xdotool arrow keys (Up/Down). That
was wrong: the Windows build navigates its menus with W (up) and S (down), and the cursor
in the main menu starts on MULTIPLAYER. The correct, hand-mapped sequence is in
train_state.py:_try_entry (13=Return, 87=w, 83=s):

    Return  title -> MAIN MENU            (NEWS / SINGLE PLAYER / MULTIPLAYER / OPTIONS / EXTRAS)
    w       MULTIPLAYER -> SINGLE PLAYER
    Return  -> SINGLE PLAYER submenu      (ARCADE / TRAINING)
    s       ARCADE -> TRAINING
    Return  -> TRAINING partner list      (NO DIVEKICKS / ... / RANDOM)
    Return  pick partner -> submenu       (DIFFICULTY slider + START)
    s       DIFFICULTY -> START
    Return  START -> match
    Return  skip the level-intro card
    Return  some intros need a second press

Success is judged by MEMORY, not pixels: P1 drivable (linux_state.find_fighter) AND the
opponent moving on its own (linux_state.opponent_moves). Escape is never used - from the
main menu it opens the quit dialog.

    python3 tools/enter_training_linux.py [--tries 3] [--verbose]
"""
import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import nid_linux as n
import linux_state as ls

SEQ = [
    ("Return", 2.5),   # title -> MAIN MENU (no-op if a menu is already open and cursor is set)
    ("w", 2.0),        # MULTIPLAYER -> SINGLE PLAYER
    ("Return", 2.5),   # -> SINGLE PLAYER submenu (ARCADE / TRAINING)
    ("s", 2.0),        # ARCADE -> TRAINING
    ("Return", 2.5),   # -> TRAINING partner list
    ("Return", 2.5),   # pick partner -> DIFFICULTY + START submenu
    ("s", 2.0),        # DIFFICULTY -> START
    ("Return", 2.5),   # START -> match
    ("Return", 2.0),   # skip level-intro card
    ("Return", 1.5),   # round start (some intros need a second press)
]


def frame_sum():
    a = n.frame(0, "/tmp/nid_rugg/entry_frame.png")
    return None if a is None else int(a.mean())


def in_match():
    """(True, addr) iff P1 is drivable AND the opponent moved >=8px/3s."""
    addr = ls.find_fighter()
    if not addr:
        return False, None
    opp = ls.find_opponent(addr)
    if opp is None:
        return False, addr
    return ls.opponent_moves(opp, seconds=3.0, min_px=8.0), addr


def press_verified(keysym, wait):
    """Send one key and wait; report whether the screen changed."""
    before = frame_sum()
    n.key(0, keysym, hold=0.12)
    time.sleep(wait)
    after = frame_sum()
    changed = (before is None or after is None
               or abs(after - before) > 2)
    return changed


def run_one(verbose):
    for i, (keysym, wait) in enumerate(SEQ):
        n.key(0, keysym, hold=0.12)
        time.sleep(wait)
        if verbose:
            print(f"  {i:2d} {keysym:8s} wait={wait:.1f}s")
    ok, addr = in_match()
    if verbose:
        print(f"  after sequence: in_match={ok} bound={hex(addr) if addr else None}")
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tries", type=int, default=3)
    ap.add_argument("--boot-wait", type=float, default=0.0,
                    help="seconds to wait for the game to finish booting before the sequence")
    ap.add_argument("--verbose", action="store_true")
    a = ap.parse_args()
    if a.boot_wait > 0:
        print(f"waiting {a.boot_wait:.0f}s for boot/title")
        time.sleep(a.boot_wait)
    for t in range(a.tries):
        print(f"attempt {t + 1}/{a.tries}")
        if run_one(verbose=True):
            print("REACHED LIVE MATCH")
            return 0
        time.sleep(1.0)
    print("did not reach a live match")
    return 1


if __name__ == "__main__":
    sys.exit(main())
