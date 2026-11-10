#!/usr/bin/env python3
"""room_oracle_linux.py — find and read _Current_Room (int32) on artemis.

GameMaker keeps the live room index in an int32 global. On Linux there is no symbol
hook, so we scan anonymous rw regions for int32 values that match the known room set
and are stable across reads. The room set and the "attract demo runs in an arena" trap
are in state/facts.json.

    python3 tools/room_oracle_linux.py [instance]

Prints candidate (address, value) pairs for the live room index.
"""
import struct
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import nid_linux as n

IID = int(sys.argv[1]) if len(sys.argv) > 1 else 0

ROOMS = {2: "rMainMenu", 3: "rMultiMenu", 4: "rOnlineLobby", 17: "rLevelSelect",
         19: "rControlsRoom", 20: "rMatchStats", 21: "rTutorial", 25: "rPreMatch",
         26: "arena", 27: "arena", 28: "arena", 29: "rCastleCenter", 30: "arena",
         31: "arena", 32: "arena", 33: "arena"}
ARENA = set(range(26, 78))
KNOWN = set(ROOMS) | ARENA


def _regions():
    pid = n._game_pid(IID)
    out = []
    for line in open(f"/proc/{pid}/maps"):
        p = line.split()
        if p[1][:2] != "rw" or (len(p) > 5 and p[-1].startswith("/")):
            continue
        a, b = (int(x, 16) for x in p[0].split("-"))
        if a >= 0x100000000:
            continue
        if (4 << 20) <= b - a <= (200 << 20):
            out.append((a, b))
    out.sort(key=lambda r: -(r[1] - r[0]))
    return out


def main():
    pid = n._game_pid(IID)
    if not pid:
        sys.exit("game not running")
    cands = {}
    for a, b in _regions():
        raw = n.memory(pid, a, b - a, "/tmp/nid_rugg/room.bin")
        if raw is None or len(raw) < b - a:
            continue
        # int32 view (little-endian)
        arr = np.frombuffer(raw, "<i4")
        # only plausible small room ids, in an aligned-ish way is too strict; scan all
        hits = np.nonzero(np.isin(arr, list(KNOWN)))[0]
        for k in hits:
            addr = a + int(k) * 4
            val = int(arr[k])
            cands[addr] = val
    print(f"candidates: {len(cands)} (value -> addr)")
    # group by value
    byval = {}
    for addr, val in cands.items():
        byval.setdefault(val, []).append(addr)
    for val in sorted(byval):
        addrs = byval[val]
        label = ROOMS.get(val, "arena" if val in ARENA else "?")
        print(f"  room={val} ({label}): {len(addrs)} addr(s) {[hex(x) for x in addrs[:6]]}")


if __name__ == "__main__":
    main()
