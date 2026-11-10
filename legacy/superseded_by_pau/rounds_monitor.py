#!/usr/bin/env python3
"""rounds_monitor.py — watch the bound fighter's position for a round transition.

A round transition in Nidhogg is a teleport: both fighters jump from their end-of-round
positions back to their spawn platforms in a single frame. Normal movement tops out at
~100 px/s, so a teleport shows as a jump of tens of px in BOTH x and y between two
consecutive samples. A jump key only moves y (not x), and walking only moves x, so the
x+y-together jump is the round signature.

Every detected transition is appended to state/rounds.jsonl (ts, kind, positions).

    python3 tools/rounds_monitor.py [seconds]     # default: run until interrupted
"""
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

X = 0x1908eec      # bound fighter x (record +0xEC); re-bind if the room changes
Y = X + 4          # y at +0xF0

TELE_DX = 30.0
TELE_DY = 30.0
INTERVAL = 0.1


def read_xy():
    pid = n._game_pid(0)
    if not pid:
        return None
    raw = n.memory(pid, X, 8, "/tmp/nid_rugg/xy.bin")
    if not raw or len(raw) < 8:
        return None
    x, y = struct.unpack("<ff", raw)
    return x, y


def main():
    seconds = float(sys.argv[1]) if len(sys.argv) > 1 else None
    log_path = Path("state/rounds.jsonl")
    log_path.parent.mkdir(exist_ok=True)

    prev = None
    t0 = time.time()
    transitions = 0
    print(f"monitoring x@0x1908eec (teleport: dx>{TELE_DX} and dy>{TELE_DY} in one sample)")
    while seconds is None or time.time() - t0 < seconds:
        cur = read_xy()
        if cur is None:
            time.sleep(INTERVAL)
            continue
        if prev is not None:
            dx = cur[0] - prev[0]
            dy = cur[1] - prev[1]
            if abs(dx) > TELE_DX and abs(dy) > TELE_DY:
                transitions += 1
                rec = {"ts": time.time(), "kind": "teleport",
                       "x_before": prev[0], "y_before": prev[1],
                       "x_after": cur[0], "y_after": cur[1],
                       "dx": round(dx, 1), "dy": round(dy, 1)}
                with open(log_path, "a") as f:
                    f.write(json.dumps(rec) + "\n")
                print(f"ROUND TRANSITION #{transitions}: "
                      f"x {prev[0]:.1f}->{cur[0]:.1f} (dx {dx:+.1f}), "
                      f"y {prev[1]:.1f}->{cur[1]:.1f} (dy {dy:+.1f})")
        prev = cur
        time.sleep(INTERVAL)
    print(f"done: {transitions} transition(s) observed")


if __name__ == "__main__":
    main()
