#!/usr/bin/env python3
"""drive_round_linux.py — force a real round transition and log it.

The game is a LOCAL 2P match: P1 (bound fighter, responds to a/d) and P2 (inert, no
CPU) stand on the same flat floor. We walk P1 into P2 and attack until P2 dies; the
round then resets and both fighters teleport back to their spawn platforms. That reset
is the round transition this project has never observed.

Signature we record (not guess): a single-sample jump of P1's position far larger than
any walk/lunge can produce. Normal movement at 60 fps over a 0.05 s sample is a few px;
a round reset moves P1 the whole floor width in one frame.

Logs every candidate to state/rounds.jsonl with the samples either side, and prints the
same. Exits 0 iff at least one transition was observed.

    python3 tools/drive_round_linux.py [--seconds 60] [--addr 0x1908eec]
"""
import argparse
import importlib.util
import json
import struct
import sys
import time
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "n", Path(__file__).resolve().parent / "nid_linux.py")
n = importlib.util.module_from_spec(spec)
spec.loader.exec_module(n)

REC = 0x200
X_OFF = 0xEC
Y_OFF = 0xF0
JUMP = 40.0          # px in one 0.05 s sample that no walk/lunge can reach


def read_f(pid, addr):
    raw = n.memory(pid, addr, 4, "/tmp/nid_rugg/read.bin")
    return struct.unpack("<f", raw)[0] if raw else None


def read_xy(pid, addr):
    raw = n.memory(pid, addr, 8, "/tmp/nid_rugg/xy.bin")
    if not raw or len(raw) < 8:
        return None
    return struct.unpack("<ff", raw)


def find_opponent(pid, p1_x):
    """The other fighter record: a 0x200-strided +0xEC float32 with a plausible x, a y
    near P1's, that is NOT the address P1 responds at, and whose x differs from P1's."""
    cands = []
    for line in open(f"/proc/{pid}/maps"):
        p = line.split()
        if p[1][:2] != "rw" or (len(p) > 5 and p[-1].startswith("/")):
            continue
        a, b = (int(x, 16) for x in p[0].split("-"))
        if a >= 0x100000000 or b - a < (REC * 4) or b - a > (200 << 20):
            continue
        raw = n.memory(pid, a, b - a, "/tmp/nid_rugg/scan.bin")
        if raw is None:
            continue
        import numpy as np
        arr = np.frombuffer(raw, "<f4")
        for k in range(len(arr)):
            addr = a + k * 4
            if (addr - X_OFF) % REC != 0 or addr == p1_x:
                continue
            x = float(arr[k])
            if not (0 < x < 400):
                continue
            yidx = k + 1
            if yidx >= len(arr):
                continue
            y = float(arr[yidx])
            if abs(y - 128.0) < 40 and abs(x - p1_x) > 20:
                cands.append((addr, x, y))
    cands.sort(key=lambda c: abs(c[1] - p1_x))
    return cands[0] if cands else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=float, default=90.0)
    ap.add_argument("--addr", default="0x1908eec")
    ap.add_argument("--opp", default=None, help="opponent x address, if known")
    a = ap.parse_args()

    pid = n._game_pid(0)
    if not pid:
        sys.exit("game not running")
    p1_x = int(a.addr, 16)
    p1_xy = read_xy(pid, p1_x)
    if p1_xy is None:
        sys.exit("cannot read P1 position")

    opp_addr = int(a.opp, 16) if a.opp else None
    if opp_addr is None:
        opp = find_opponent(pid, p1_xy[0])
        if opp is None:
            sys.exit("could not find P2 record")
        opp_addr, ox, oy = opp
    print(f"P1 x@{p1_x:#x} at ({p1_xy[0]:.1f},{p1_xy[1]:.1f}); "
          f"P2 x@{opp_addr:#x}")

    log_path = Path("state/rounds.jsonl")
    log_path.parent.mkdir(exist_ok=True)

    t0 = time.time()
    prev1 = p1_xy
    transitions = 0
    samples = 0
    fh = open(log_path, "a")

    # drive: walk toward P2 and swing
    while time.time() - t0 < a.seconds:
        cur1 = read_xy(pid, p1_x)
        cur2 = read_xy(pid, opp_addr)
        if cur1 is None:
            time.sleep(0.05)
            continue
        me = cur1[0]
        # steer: approach P2 until within sword range, then keep attacking
        if cur2 is not None:
            gap = cur2[0] - me
            if gap > 18:
                n.keydown(0, "d")
            elif gap < -18:
                n.keydown(0, "a")
            else:
                n.keyup(0, "d")
                n.keyup(0, "a")
                n.key(0, "f", hold=0.06)
        else:
            # P2 record vanished (death/realloc) — keep attacking where we stand
            n.keyup(0, "d")
            n.keyup(0, "a")
            n.key(0, "f", hold=0.06)

        samples += 1
        # transition detection: single-sample jump far beyond walk/lunge speed
        if prev1 is not None:
            dx = cur1[0] - prev1[0]
            dy = cur1[1] - prev1[1]
            if abs(dx) > JUMP or abs(dy) > JUMP:
                transitions += 1
                rec = {"ts": time.time(), "kind": "teleport",
                       "x_before": round(prev1[0], 1), "y_before": round(prev1[1], 1),
                       "x_after": round(cur1[0], 1), "y_after": round(cur1[1], 1),
                       "dx": round(dx, 1), "dy": round(dy, 1),
                       "p2_before": (round(cur2[0], 1), round(cur2[1], 1)) if cur2 else None}
                fh.write(json.dumps(rec) + "\n")
                fh.flush()
                print(f"ROUND TRANSITION #{transitions}: P1 "
                      f"({prev1[0]:.1f},{prev1[1]:.1f}) -> "
                      f"({cur1[0]:.1f},{cur1[1]:.1f})  dx={dx:+.1f} dy={dy:+.1f}")
        prev1 = cur1
        time.sleep(0.05)

    n.keyup(0, "d")
    n.keyup(0, "a")
    fh.close()
    print(f"done: {samples} samples, {transitions} transition(s)")
    return 0 if transitions > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
