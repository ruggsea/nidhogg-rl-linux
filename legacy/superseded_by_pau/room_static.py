#!/usr/bin/env python3
"""room_static.py — narrow the _Current_Room candidate slots WITHOUT pressing keys.

The prober's room_find.py presses Escape and looks for int32 slots that change
room-to-room. That finds many lookalike counters. This tool is the read-only
complement: dump the game heap twice a few seconds apart with NO input, and report
the int32 slots whose value sits in the known-room set AND stays constant. The room
global is constant while the screen is idle; animation/frame counters are not.

Safe to run while another worker drives: it only reads memory via the spy.

    python3 tools/room_static.py
"""
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import nid_linux as n
import linux_state as ls

ROOMS = set(list(range(1, 5)) + [17, 19, 20, 21, 25] + list(range(26, 78)))
NAMES = {1: "rLogos", 2: "rMainMenu", 3: "rMultiMenu", 4: "rOnlineLobby",
         17: "rLevelSelect", 25: "rPreMatch", 29: "rCastleCenter"}


def dump(pid, a, b):
    raw = n.memory(pid, a, b - a, "/tmp/nid_rugg/roomstatic.bin")
    if raw is None or len(raw) != b - a:
        return None
    return np.frombuffer(raw, "<i4")


def main():
    pid = n._game_pid(0)
    if not pid:
        sys.exit("game not running")
    regions = ls._regions()[:5]     # biggest 5 rw regions, biggest first
    before = {}
    for a, b in regions:
        arr = dump(pid, a, b)
        if arr is not None:
            before[(a, b)] = arr
        print(f"region {hex(a)}-{hex(b)} ({(b-a)>>20} MB) dumped")
    time.sleep(3.0)
    stable = []
    for (a, b), arr0 in before.items():
        arr1 = dump(pid, a, b)
        if arr1 is None:
            continue
        m = min(len(arr0), len(arr1))
        arr0, arr1 = arr0[:m], arr1[:m]
        inroom = np.isin(arr0, list(ROOMS))
        unchanged = arr0 == arr1
        hits = np.nonzero(inroom & unchanged)[0]
        for k in hits:
            stable.append((a + k * 4, int(arr0[k])))
    print(f"\nstable room-valued int32 slots (no input, 3s apart): {len(stable)}")
    for addr, v in sorted(stable, key=lambda t: t[1]):
        print(f"  {hex(addr)}  room {v}  ({NAMES.get(v, 'arena?' if 26 <= v <= 77 else '?')})")


if __name__ == "__main__":
    main()
