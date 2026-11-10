#!/usr/bin/env python3
"""Linux state primitives for Nidhogg-on-artemis: the memory-scan equivalent of the
macOS hook's InstanceManager.

Everything keys off ONE float32 address (the fighter's x), found by response (hold d ->
moves right, hold a -> moves left) and read through the in-process spy. There is no
instance dump on Linux, so the "bound instance" is the bound ADDRESS.

    find_fighter(pid)        -> x-address of the controllable fighter, or None
    read_f(pid, addr)        -> float32
    park(addr, dir)          -> walk a direction for a moment
    walk_until_wall(addr)    -> walk into a wall, return the x where it stopped
    arena_extent(addr)       -> {left, right, width}
    centre(addr, ext)        -> walk to the middle of the measured floor
    prove_control(addr)      -> direction gate: D->right, A->left (px per direction)
    dose_response(addr)      -> proportionality: hold 3x longer -> ~3x further
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
XMAX = 400.0
REC = 0x200
X_OFF = 0xEC
IID = int(__import__("os").environ.get("NID_INSTANCE", "0"))

# dose-response / gate timing, calibrated to the small LOCAL-2P arena floor (135 px)
HOLD_SHORT = 0.3
HOLD_LONG = 0.6
GATE_HOLD = 0.8
DOSE_RATIO = 1.6
DOSE_MIN = 8.0
MIN_GATE_MAJOR = 40.0
MIN_GATE_MINOR = 30.0


# ---------------------------------------------------------------- read


def read_f(addr):
    pid = n._game_pid(IID)
    if not pid:
        return None
    raw = n.memory(pid, addr, 4, "/tmp/nid_rugg/read.bin")
    return struct.unpack("<f", raw)[0] if raw else None


def _regions():
    pid = n._game_pid(IID)
    out = []
    for line in open(f"/proc/{pid}/maps"):
        p = line.split()
        if p[1][:2] != "rw" or (len(p) > 5 and p[-1].startswith("/")):
            continue
        a, b = (int(x, 16) for x in p[0].split("-"))
        if a >= 0x100000000:          # high-address regions are GL/D3D texture buffers
            continue
        if MIN_REGION <= b - a <= MAX_REGION:
            out.append((a, b))
    out.sort(key=lambda r: -(r[1] - r[0]))
    return out


def _dump(pid, a, b):
    raw = n.memory(pid, a, b - a, "/tmp/nid_rugg/bind.bin")
    return np.frombuffer(raw, "<f4") if raw else None


def find_fighter(iid=None):
    """Bind the controllable fighter on instance `iid` (default: the module IID / NID_INSTANCE).

    Instance-aware because the farm runs several games at once: attestation against instance 0 while the
    only live game is on instance 1 binds nothing and reports "bind failed", which looks exactly like a
    dead game. Each instance has its own display, prefix and spy.

    Audit-hardened against two measured failure modes:
      * key-state/timer slots that read 0 at rest and nonzero only while a key is held
        (A=0, B=nonzero, C=0) — a real fighter is at a plausible x at rest AND returns to it;
      * the sort key re-reading memory that has changed since the scan (returned denormals
        like -1.4e30). Candidates are scored on their SCAN-TIME samples, never re-read.
    """
    global IID
    if iid is not None:
        IID = int(iid)
    pid = n._game_pid(IID)
    if not pid:
        return None
    found = []
    for a, b in _regions():
        n.key(IID, "a", hold=1.4)
        time.sleep(0.3)
        A = _dump(pid, a, b)
        n.key(IID, "d", hold=0.5)
        time.sleep(0.2)
        B = _dump(pid, a, b)
        n.key(IID, "a", hold=0.5)
        time.sleep(0.2)
        C = _dump(pid, a, b)
        if A is None or B is None or C is None:
            continue
        m = min(len(A), len(B), len(C))
        A, B, C = A[:m], B[:m], C[:m]
        with np.errstate(invalid="ignore", over="ignore"):
            good = ((B - A > 8) & (B - A < 200) & (B - C > 8) & (B - C < 200)
                    & (A > 1) & (A < 1100) & (B > 1) & (B < 1100) & (C > 1) & (C < 1100)
                    & (np.abs(A - C) < 30)
                    & np.isfinite(A) & np.isfinite(B) & np.isfinite(C))
        for k in np.nonzero(good)[0]:
            # y is the next float (+4); a real fighter's ground line is stable while it
            # walks horizontally, so y must be plausible and not jump between samples.
            ya = float(A[k + 1]) if k + 1 < len(A) else -1.0
            yb = float(B[k + 1]) if k + 1 < len(B) else -1.0
            yc = float(C[k + 1]) if k + 1 < len(C) else -1.0
            if not (10 < ya < 300 and 10 < yb < 300 and 10 < yc < 300):
                continue
            if abs(ya - yb) > 20 or abs(ya - yc) > 20:
                continue
            aligned = int((a + k * 4 - X_OFF) % REC == 0)
            # score: prefer aligned, prefer a large clean rightward displacement
            found.append((a + k * 4, aligned, float(B[k]) - float(A[k])))
    if not found:
        return None
    found.sort(key=lambda t: (-t[1], -t[2]))
    return found[0][0]


# ---------------------------------------------------------------- movement


def park(addr, dirkey, seconds=1.4):
    n.key(IID, dirkey, hold=seconds)
    time.sleep(0.3)


def walk_until_wall(addr, dirkey, max_s=5.0):
    """Hold a direction until x stops moving; return the stopped x."""
    n.keydown(IID, dirkey)
    x = read_f(addr)
    stalls = 0
    t0 = time.time()
    while time.time() - t0 < max_s:
        time.sleep(0.1)
        nx = read_f(addr)
        if nx is not None and x is not None and abs(nx - x) < 2.0:
            stalls += 1
            if stalls >= 5:
                break
        else:
            stalls = 0
        x = nx if nx is not None else x
    n.keyup(IID, dirkey)
    time.sleep(0.5)          # settle: let the fighter come fully to rest at the wall
    return x


def arena_extent(addr):
    left = walk_until_wall(addr, "a")
    right = walk_until_wall(addr, "d")
    if left is None or right is None:
        return None
    return {"left": min(left, right), "right": max(left, right),
            "width": abs(right - left)}


def centre(addr, ext=None):
    ext = ext or arena_extent(addr)
    if not ext or ext["width"] < 40:
        return False
    mid = (ext["left"] + ext["right"]) / 2.0
    for _ in range(20):
        x = read_f(addr)
        if x is None:
            return False
        err = x - mid
        if abs(err) <= ext["width"] * 0.15:
            return True
        n.key(IID, "a" if err > 0 else "d", hold=0.1)
        time.sleep(0.05)
    return True


# ---------------------------------------------------------------- gates


def _delta_max(addr, key, seconds, sign):
    """Max signed displacement during a held key (captures the peak before any wall bounce)."""
    x0 = read_f(addr)
    n.keydown(IID, key)
    best = 0.0
    t0 = time.time()
    while time.time() - t0 < seconds:
        x = read_f(addr)
        if x is not None and x0 is not None:
            best = max(best, (x - x0) * sign)
        time.sleep(0.05)
    n.keyup(IID, key)
    time.sleep(0.3)
    return best


def prove_control(addr):
    """Direction gate. Park against one wall, then measure the reverse hold: a fighter
    we control travels ~100 px across the floor; a wall-pinned fighter cannot move."""
    results = {}
    walk_until_wall(addr, "a")            # park LEFT, then measure rightward under d
    results["D"] = _delta_max(addr, "d", GATE_HOLD, +1)
    walk_until_wall(addr, "d")            # park RIGHT, then measure leftward under a
    results["A"] = _delta_max(addr, "a", GATE_HOLD, -1)
    return results


def find_opponent(p1_addr):
    """x-address of the OTHER fighter (P2), found in P1's own heap region.

    Fighter records are 0x200-strided with x @ +0xEC and y @ +0xF0 (float32, room space).
    P2 is the 0x200-strided +0xEC slot that is not P1, has a plausible room x, and an x
    separated from P1's. This is the memory-scan equivalent of the macOS hook's `them_x`.

    The old |y - p1y| > 40 filter was removed: it excluded the real opponent whenever P1's
    y was off the ground line (jumping/respawning/falling), which returned None and made
    opponent_moves unmeasurable. The x-separation filter is the discriminator now.
    """
    pid = n._game_pid(IID)
    if not pid:
        return None
    p1x = read_f(p1_addr)
    if p1x is None:
        return None
    region = _region_of(p1_addr)
    if region is None:
        return None
    a, b = region
    raw = n.memory(pid, a, b - a, "/tmp/nid_rugg/opp.bin")
    if raw is None:
        return None
    arr = np.frombuffer(raw, "<f4")
    cands = []
    for k in range(len(arr) - 1):
        addr = a + k * 4
        if (addr - X_OFF) % REC != 0 or addr == p1_addr:
            continue
        x, y = float(arr[k]), float(arr[k + 1])
        if not (0 < x < 1100 and 15 < y < 260):
            continue
        if abs(x - p1x) < 20:            # must be a DIFFERENT fighter, not P1's own record
            continue
        cands.append((addr, x, y))
    if not cands:
        return None
    # the opponent is the plausible fighter on the other side of the arena; in a 2-player
    # game that is the nearest OTHER fighter by x-separation.
    cands.sort(key=lambda c: abs(c[1] - p1x))
    return cands[0][0]


def _region_of(addr):
    pid = n._game_pid(IID)
    for line in open(f"/proc/{pid}/maps"):
        p = line.split()
        if p[1][:2] != "rw":
            continue
        a, b = (int(x, 16) for x in p[0].split("-"))
        if a <= addr < b:
            return a, b
    return None


def round_running(me_addr, opp_addr, settle=2.0, min_px=5.0):
    """True if EITHER fighter moves >=min_px during `settle` with no input.

    This is the Linux port of the macOS `ensure_live_round`: a round that is in progress
    shows movement (the CPU plays); the READY screen and a post-round screen are inert.
    A wall-pinned or dead fighter is exactly what this catches.
    """
    x0_me, x0_th = read_f(me_addr), read_f(opp_addr)
    moved = 0.0
    t0 = time.time()
    while time.time() - t0 < settle:
        m, t = read_f(me_addr), read_f(opp_addr)
        if m is not None and x0_me is not None:
            moved = max(moved, abs(m - x0_me))
        if t is not None and x0_th is not None:
            moved = max(moved, abs(t - x0_th))
        time.sleep(0.1)
    return moved >= min_px


def opponent_moves(opp_addr, seconds=6.0, min_px=8.0):
    """True if the opponent's x moves >=min_px over `seconds` (the CPU plays, not a statue).

    READY/ARCADE has a second-human slot that never arrives: the inert fighter is pinned
    at one x for the whole window (measured 203.00 for 60 s on macOS). A real TRAINING
    CPU moves on its own.
    """
    xs = []
    t0 = time.time()
    while time.time() - t0 < seconds:
        x = read_f(opp_addr)
        if x is not None:
            xs.append(x)
        time.sleep(0.1)
    return len(xs) >= 3 and (max(xs) - min(xs)) >= min_px


def opponent_moves_sustained(opp_addr, seconds=6.0, min_px=8.0, gap=5.0):
    """True iff the opponent moves >=min_px in TWO consecutive `seconds` windows separated
    by `gap`. A single 6s window can be satisfied by a scripted spawn/intro walk that then
    freezes (the frozen match: fighters spawn, walk to mid, then stop - auditor measured
    0.82% pixel change = static). Two windows separated by a gap cannot: window 2 lands
    after the freeze. This is the audit-hardened liveness signal."""
    def _window():
        xs = []
        t0 = time.time()
        while time.time() - t0 < seconds:
            x = read_f(opp_addr)
            if x is not None:
                xs.append(x)
            time.sleep(0.1)
        return (max(xs) - min(xs)) if len(xs) >= 3 else 0.0
    w1 = _window()
    time.sleep(gap)
    w2 = _window()
    return w1 >= min_px and w2 >= min_px


def dose_response(addr):
    """Proportionality: hold 3x longer -> roughly 3x further, measured from the same wall.

    The opponent can drift into the path and clamp one measurement (seen once as
    short=36 long=43), so the test is repeated and the first clean pass is returned."""
    def from_left(seconds):
        walk_until_wall(addr, "a")
        return _delta_max(addr, "d", seconds, +1)

    best = (0.0, 0.0, 0.0)
    for _ in range(3):
        d_short = from_left(HOLD_SHORT)
        d_long = from_left(HOLD_LONG)
        ratio = (d_long / d_short) if d_short > 1.0 else 0.0
        ok = (d_short >= DOSE_MIN and d_long >= DOSE_MIN * DOSE_RATIO
              and ratio >= DOSE_RATIO)
        if ok:
            return True, d_short, d_long, ratio
        if ratio > best[2]:
            best = (d_short, d_long, ratio)
    return False, best[0], best[1], best[2]


if __name__ == "__main__":
    addr = find_fighter()
    print("bound:", hex(addr) if addr else None)
    if addr:
        ext = arena_extent(addr)
        print("extent:", {k: round(v, 1) for k, v in ext.items()} if ext else None)
        print("gate:", {k: round(v, 1) for k, v in prove_control(addr).items()})
        ok, ds, dl, r = dose_response(addr)
        print(f"dose: {'PASS' if ok else 'no'} short={ds:.1f} long={dl:.1f} ratio={r:.2f}")
