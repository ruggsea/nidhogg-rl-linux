#!/usr/bin/env python3
"""Hunt the game's real round/score variable with the spy's `watch` command.

For step 2 (L28): the bridge's alive flag is a mapping-bounds check, so it never marks a
death. The spy can sample up to 16 arbitrary u32s at tick rate (`watch`, see
spy/nidspy.zig); this tool points it at a window around the tracked room address and at
the fighter records, cycles through the window in passes, and reports every address that
held one value for a long time and then *stepped* — the shape of a round/score counter.

Trigger: P1 holds right for the run, so the match is live and a round can actually end.
A step is correlated with room changes read at the same time. No reward, no training.

  cd ~/nf-p/pau86 && source env.sh
  ~/nf-p/venv/bin/python ~/nf-p/code_pau/tools/score_hunt.py --seconds 150
"""
from __future__ import annotations

import argparse
import json
import os
import struct
import sys
import time
from pathlib import Path

CODE = os.environ.get("CODE_PAU", "/home/ruggsea/nf-p/code_pau")
sys.path.insert(0, CODE)
os.environ.setdefault("NIDFARM", os.path.expanduser("~/nf-p/pau86"))
os.environ.setdefault("NID_DISPLAY_BASE", "88")

import nidlinux as n                          # noqa: E402
import nidstate as s                          # noqa: E402
from nidmem import ROOM_OFF, exe_base        # noqa: E402
from tools import entry_health as eh         # noqa: E402

IID = int(os.environ.get("NID_IID", "0"))
RUN = Path(os.environ.get("NIDRUN", os.path.expanduser("~/nf-p/pau86/results/runs")))
WATCH_FMT = "<IIQII16I8s"                     # mirrors Snapshot/Watch in nidspy.zig
WATCH_SIZE = 96
# record offsets that are known to move every tick (positions); skip, they are not counters
MOTION_OFFS = {0xEC, 0xF0, 0xFC, 0x100}
STEP4 = range(0, 0x101, 4)


def watch_file(pid):
    try:
        raw = Path(f"/tmp/nid_watch_{pid}").read_bytes()
    except OSError:
        return None
    if len(raw) != WATCH_SIZE:
        return None
    f = struct.unpack(WATCH_FMT, raw)
    if f[0] != 0x5744494E:                    # "NIDW"
        return None
    # layout: magic, version, seq, tick, count, v[16], pad -> values are f[5:5+count]
    return f[2], list(f[5:5 + f[4]])          # (seq, values)


def set_watch(pid, addrs):
    assert n._wait_idle(pid, 2.0), "spy busy"
    n._send(pid, "watch " + " ".join(f"{a:x}" for a in addrs))
    for _ in range(50):
        if n._wait_idle(pid, 2.0):
            w = watch_file(pid)
            if w and w[1]:
                return True
        time.sleep(0.02)
    return False


def bind(pid):
    for _ in range(4):
        fp = s.find_players_by_input(IID, hold=0.45)
        if fp and fp.get("P1") and fp.get("P2"):
            tick = s.find_tick(pid) or 0
            try:
                n.untrack(pid)
            except Exception:
                pass
            n.track(pid, p1=fp["P1"], p2=fp["P2"],
                    score=exe_base(pid) + ROOM_OFF, tick=tick)
            time.sleep(0.3)
            return fp
        time.sleep(1.5)
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=float, default=150.0)
    ap.add_argument("--hold", type=float, default=0.35, help="seconds per 16-address pass")
    ap.add_argument("--room-span", type=int, default=0x100)
    a = ap.parse_args()

    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    RUN.mkdir(parents=True, exist_ok=True)
    out = {"stamp": stamp, "entered": False, "bound": False, "pid": None,
           "room_addr": None, "candidates": [], "steps": [], "room_changes": [],
           "flags_seen": [], "seconds": a.seconds}
    path = RUN / f"score_hunt_{stamp}.json"
    print(f"score_hunt start {stamp} -> {path}", flush=True)

    entered = bool(eh.ensure_entry(IID))
    pid = n._game_pid(IID)
    out.update(entered=entered, pid=pid)
    if not entered or not pid:
        path.write_text(json.dumps(out, indent=1)); print("NO_ENTRY", out); return 2
    fp = bind(pid)
    out["bound"] = bool(fp)
    if not fp:
        path.write_text(json.dumps(out, indent=1)); print("NO_BIND", out); return 3

    room_addr = exe_base(pid) + ROOM_OFF
    out["room_addr"] = hex(room_addr)
    addrs = []
    for off in range(-a.room_span, a.room_span + 4, 4):
        addrs.append(("room%+#x" % off, room_addr + off))
    for who in ("P1", "P2"):
        base = fp[who]
        for off in STEP4:
            if off not in MOTION_OFFS:
                addrs.append((f"{who}%+#x" % off, base + off))
    out["candidates"] = [name for name, _ in addrs]

    first = {}
    changes = {name: [] for name, _ in addrs}
    room_changes = []
    flags_seen = []
    prev_room = None
    t0 = time.time()
    n.keydown(IID, "d")
    i = 0
    try:
        while time.time() - t0 < a.seconds:
            chunk = addrs[i:i + 16] if i + 16 <= len(addrs) else addrs[i:] + addrs[: (i + 16) - len(addrs)]
            i = (i + 16) % len(addrs)
            if not set_watch(pid, [ad for _, ad in chunk]):
                time.sleep(0.1)
                continue
            end = time.time() + a.hold
            while time.time() < end:
                st = n.state(pid)
                if st is not None:
                    r = st.score_orange if st.flags & n.FLAG_SCORE else None
                    fl = (int(bool(st.flags & n.FLAG_P1)), int(bool(st.flags & n.FLAG_P2)))
                    if fl not in flags_seen:
                        flags_seen.append(fl)
                    if r is not None and prev_room is not None and r != prev_room:
                        room_changes.append({"t": round(time.time() - t0, 2),
                                             "from": prev_room, "to": r})
                        print("ROOM", room_changes[-1], flush=True)
                    if r is not None:
                        prev_room = r
                time.sleep(0.02)
            w = watch_file(pid)
            if not w:
                continue
            now = round(time.time() - t0, 2)
            for (name, _addr), val in zip(chunk, w[1]):
                prev = changes[name][-1][1] if changes[name] else first.get(name)
                if name not in first:
                    first[name] = val
                elif val != prev:
                    changes[name].append((now, val))
                    print(f"CHANGE {name} {val} @{now}s", flush=True)
    finally:
        n.keyup(IID, "d")

    steps = []
    for name, _addr in addrs:
        hist = changes[name]
        if hist:
            steps.append({"name": name, "first": first[name],
                          "n_changes": len(hist), "changes": hist[:20]})
    out["steps"] = sorted(steps, key=lambda d: d["n_changes"])
    out["room_changes"] = room_changes
    out["flags_seen"] = flags_seen
    path.write_text(json.dumps(out, indent=1))
    print("SUMMARY " + json.dumps({"entered": entered, "bound": out["bound"],
                                   "room_changes": room_changes, "flags_seen": flags_seen,
                                   "n_step_addrs": len(steps),
                                   "low_change": [s["name"] + ":" + str(s["n_changes"])
                                                  for s in out["steps"][:12]]}))
    print("wrote", path)


if __name__ == "__main__":
    sys.exit(main())