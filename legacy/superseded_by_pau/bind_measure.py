#!/usr/bin/env python3
"""Bind the fighter position on Linux by response, and measure the displacement.

No screen parsing. A controllable fighter is defined by response: hold 'd' -> a
float32 slot moves right at fighter speed; hold 'a' -> the SAME slot moves left.
This is the macOS bind-by-response, done by scanning memory instead of by symbol.

wine maps the game's data across several anonymous rw regions (not one big heap), so
the scan runs over every rw region above a floor. Candidates are float32 slots whose
parked value is a plausible room x (0..400) and which move 5..150 px right under 'd'
and back left under 'a' — a band the camera/timer/texture noise cannot sit in.

Prints the bound address and measured displacement so it can be recorded as a claim.

    python3 tools/bind_measure.py [instance]
"""
import importlib.util
import struct
import sys
import time
from pathlib import Path

import numpy as np

spec = importlib.util.spec_from_file_location(
    "n", Path(__file__).resolve().parent / "nid_linux.py")
n = importlib.util.module_from_spec(spec)
spec.loader.exec_module(n)

MIN_REGION = 4 << 20
MAX_REGION = 200 << 20
HOLD = 0.5
MIN_MOVE = 5.0
MAX_MOVE = 150.0
XMAX = 400.0
REC = 0x200
X_OFF = 0xEC


def regions(pid):
    out = []
    for line in open(f"/proc/{pid}/maps"):
        p = line.split()
        if p[1][:2] != "rw" or (len(p) > 5 and p[-1].startswith("/")):
            continue
        a, b = (int(x, 16) for x in p[0].split("-"))
        # the fighter lives in wine's Windows process heap, mapped at low addresses
        # (< 4 GiB); the high-address regions are GL/D3D texture and vertex buffers
        if a >= 0x100000000:
            continue
        if MIN_REGION <= b - a <= MAX_REGION:
            out.append((a, b))
    out.sort(key=lambda r: -(r[1] - r[0]))
    return out


def dump(pid, a, b):
    raw = n.memory(pid, a, b - a, "/tmp/nid_rugg/bind.bin")
    return np.frombuffer(raw, "<f4") if raw else None


def read_f(pid, addr):
    raw = n.memory(pid, addr, 4, "/tmp/nid_rugg/read.bin")
    return struct.unpack("<f", raw)[0] if raw else None


def scan_region(pid, a, b):
    """float32 slots in this region that move right under d and left under a."""
    n.key(0, "a", hold=1.4)
    time.sleep(0.3)
    A = dump(pid, a, b)
    n.key(0, "d", hold=HOLD)
    time.sleep(0.2)
    B = dump(pid, a, b)
    n.key(0, "a", hold=HOLD)
    time.sleep(0.2)
    C = dump(pid, a, b)
    if A is None or B is None or C is None:
        return []
    m = min(len(A), len(B), len(C))
    A, B, C = A[:m], B[:m], C[:m]
    with np.errstate(invalid="ignore"):
        good = ((B - A > MIN_MOVE) & (B - A < MAX_MOVE)
                & (B - C > MIN_MOVE) & (B - C < MAX_MOVE)
                & (A > 0) & (A < XMAX) & (B > 0) & (B < XMAX)
                & np.isfinite(A) & np.isfinite(B) & np.isfinite(C))
    return [(a + k * 4, float(A[k]), float(B[k]), float(C[k]))
            for k in np.nonzero(good)[0]]


def main():
    i = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    pid = n._game_pid(i)
    if not pid:
        sys.exit("game not running")

    found = []
    for a, b in regions(pid):
        got = scan_region(pid, a, b)
        if got:
            print(f"region {hex(a)}: {len(got)} candidates")
            found.extend(got)
    if not found:
        print("no controllable fighter found (is a match running?)")
        return 1

    # prefer the record-aligned x field (+0xEC within a 0x200 record) — the body x
    aligned = [c for c in found if (c[0] - X_OFF) % REC == 0]
    pool = aligned or found
    pool.sort(key=lambda c: c[1])          # P1 parks against the left wall: smallest x
    addr, parked, after_d, after_a = pool[0]
    print(f"\nbound: x@ {hex(addr)}  (parked {parked:.1f} -> hold d {after_d:.1f} "
          f"-> hold a {after_a:.1f})")

    d_deltas, a_deltas = [], []
    for _ in range(3):
        before = read_f(pid, addr)
        n.key(0, "d", hold=HOLD)
        time.sleep(0.15)
        vd = read_f(pid, addr)
        n.key(0, "a", hold=HOLD)
        time.sleep(0.15)
        va = read_f(pid, addr)
        if None in (before, vd, va):
            continue
        d_deltas.append(vd - before)
        a_deltas.append(va - vd)
    if not d_deltas:
        print("measurement failed")
        return 1
    d_mean, a_mean = float(np.mean(d_deltas)), float(np.mean(a_deltas))
    print(f"displacement: hold d ({HOLD}s) -> +{d_mean:.1f} px   "
          f"hold a ({HOLD}s) -> {a_mean:.1f} px")
    print(f"ADDR={addr:#x} D_DELTA={d_mean:.1f} A_DELTA={a_mean:.1f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
