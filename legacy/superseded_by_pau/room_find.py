#!/usr/bin/env python3
"""room_find.py — locate _Current_Room on the Windows build by RESPONSE, not by
guessing an address.

GameMaker keeps the live room index in an int32 global. We dump the biggest rw heap
region, press Escape (back one menu), dump again, and find int32 slots whose value
changed from one known-room index to another known-room index. The room global is the
slot that does that; nothing else moves room-to-room.

    python3 tools/room_find.py
"""
import struct
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
    raw = n.memory(pid, a, b - a, "/tmp/nid_rugg/roomfind.bin")
    return np.frombuffer(raw, "<i4") if raw is not None and len(raw) == b - a else None


def main():
    pid = n._game_pid(0)
    if not pid:
        sys.exit("game not running")
    a, b = ls._regions()[0]          # biggest rw region
    print(f"region {hex(a)}-{hex(b)}  {(b-a)>>20} MB")

    before = dump(pid, a, b)
    if before is None:
        sys.exit("dump failed")
    # candidate slots: currently a known room index
    cand = np.nonzero(np.isin(before, list(ROOMS)))[0]

    print(f"known-room candidate slots: {len(cand)}; pressing Escape (back)")
    n.key(0, "Escape", hold=0.12)
    time.sleep(2.5)

    after = dump(pid, a, b)
    if after is None:
        sys.exit("second dump failed")
    m = min(len(before), len(after))
    before, after = before[:m], after[:m]

    hits = []
    for k in cand:
        if k >= m:
            continue
        old, new = int(before[k]), int(after[k])
        if old != new and new in ROOMS and old in ROOMS:
            hits.append((a + k * 4, old, new))
    print(f"slots that changed room-to-room: {len(hits)}")
    for addr, old, new in hits:
        print(f"  {hex(addr)}  room {old} -> {new}  "
              f"({NAMES.get(old,'?')} -> {NAMES.get(new,'?')})")


if __name__ == "__main__":
    main()
