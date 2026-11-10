#!/usr/bin/env python3
"""find_cursor.py — find the menu selection cursor in memory by RESPONSE.

On a menu, pressing S moves the selection one step. The cursor is a small int (index)
or a float (highlight y). We dump the biggest rw region, press S, dump again, and find
slots that changed by exactly +1 (int index) or a small fixed step (float y).

    python3 tools/find_cursor.py [steps]

Prints candidate (address, before, after) slots. The menu cursor is the one that
advances by a constant amount on each S and retreats on W.
"""
import struct
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import nid_linux as n
import linux_state as ls


def dump(a, b):
    pid = n._game_pid(0)
    raw = n.memory(pid, a, b - a, "/tmp/nid_rugg/cur.bin")
    if raw is None or len(raw) != b - a:
        return None
    return raw


def main():
    steps = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    pid = n._game_pid(0)
    if not pid:
        sys.exit("game not running")
    a, b = ls._regions()[0]
    print(f"region {hex(a)}-{hex(b)} {(b-a)>>20}MB")

    before = dump(a, b)
    n.key(0, "s", hold=0.12)
    time.sleep(2.0)
    after = dump(a, b)
    if before is None or after is None:
        sys.exit("dump failed")

    m = min(len(before), len(after))
    bi = np.frombuffer(before[:m], "<i4")
    ai = np.frombuffer(after[:m], "<i4")
    bf = np.frombuffer(before[:m], "<f4")
    af = np.frombuffer(after[:m], "<f4")

    # int candidates: value in 0..40, changed by +1 or -1
    d = ai - bi
    mask = (np.abs(d) <= 1) & (bi >= 0) & (bi < 40) & (d != 0)
    hits = np.nonzero(mask)[0]
    print(f"int slots (0..40) changed by +/-1 on S: {len(hits)}")
    for k in hits[:40]:
        print(f"  {hex(a + k*4)}  {int(bi[k])} -> {int(ai[k])}")

    # float candidates: changed by a small step 5..30 px, absolute value plausible
    df = af - bf
    fmask = (np.abs(df) > 4) & (np.abs(df) < 40) & (bf > 0) & (bf < 400) & (af > 0) & (af < 400)
    fhits = np.nonzero(fmask)[0]
    print(f"float slots (0..400) changed by 4..40 on S: {len(fhits)}")
    for k in fhits[:40]:
        print(f"  {hex(a + k*4)}  {float(bf[k]):.1f} -> {float(af[k]):.1f}  d={float(df[k]):.1f}")


if __name__ == "__main__":
    main()
