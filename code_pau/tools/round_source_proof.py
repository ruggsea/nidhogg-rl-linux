#!/usr/bin/env python3
"""Prove the bridge reads the game round event-tied, and the outcome counters.

Two measurements, one run:

  1. ROUND SOURCE. Track the fighters with ``score = image_base + ROOM_OFF``. The spy
     then publishes the room index in its ``score_orange`` slot (nidspy.zig). At the
     same pid we read ROOM_OFF directly; the two must agree, so the bridge's room
     value really is the game's room and not a stale file or a wrong address.

  2. OUTCOME COUNTERS. Feed the live ``(room, FLAG_P1, FLAG_P2)`` stream to
     ``outcome_events.OutcomeTracker`` while P1 walks right into P2. Print every event
     (room change, death) with its time. A death here is an existence flag held low for
     `--debounce` samples, not an x-jump.

Writes results/runs/round_source_proof_<stamp>.json and prints SUMMARY. No reward, no
training, no TRAINING entry.

  cd ~/nf-p/pau86 && source env.sh && ~/nf-p/venv/bin/python code_pau/tools/round_source_proof.py
"""
import argparse
import json
import os
import struct
import sys
import time

CODE = os.environ.get("CODE_PAU", "/home/ruggsea/nf-p/code_pau")
sys.path.insert(0, CODE)
os.environ.setdefault("NIDFARM", os.path.expanduser("~/nf-p/pau86"))
os.environ.setdefault("NID_DISPLAY_BASE", "88")

import nidlinux as n                      # noqa: E402
import nidstate as s                      # noqa: E402
from nidmem import ROOM_OFF, exe_base    # noqa: E402
from tools import entry_health as eh     # noqa: E402
from tools.outcome_events import OutcomeTracker  # noqa: E402

IID = int(os.environ.get("NID_IID", "0"))
RUN = os.environ.get("NIDRUN", os.path.expanduser("~/nf-p/pau86/results/runs"))


def room_mem(pid):
    raw = n.memory(pid, exe_base(pid) + ROOM_OFF, 4, "/tmp/round_proof_room.bin")
    return struct.unpack("<i", raw)[0] if raw else None


def bind(pid):
    """P1 is required for the round-source check; P2 is used when identified."""
    fp = None
    for _ in range(3):
        fp = s.find_players_by_input(IID, hold=0.45)
        if fp and fp.get("P1"):
            break
        time.sleep(1.0)
    if not (fp and fp.get("P1")):
        return None
    tick = s.find_tick(pid) or 0
    try:
        n.untrack(pid)
    except Exception:
        pass
    n.track(pid, p1=fp["P1"], p2=fp.get("P2") or 0,
            score=exe_base(pid) + ROOM_OFF, tick=tick)
    time.sleep(0.4)
    return fp


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=float, default=40.0)
    ap.add_argument("--debounce", type=int, default=3)
    a = ap.parse_args()
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    out = {"stamp": stamp, "entered": False, "bound": False, "pid": None,
           "mem_room": None, "spy_room": None, "match": False,
           "flags": None, "events": [], "summary": None, "debounce": a.debounce}

    entered = bool(eh.ensure_entry(IID))
    pid = n._game_pid(IID)
    fp = bind(pid) if pid else None
    out.update(entered=entered, pid=pid, bound=bool(fp))
    if not entered or not pid or not fp:
        write(out, stamp); return 2

    # 1. round source: spy score slot vs a direct ROOM_OFF read at the same pid.
    mem_room = room_mem(pid)
    st = None
    for _ in range(20):
        st = n.state(pid)
        if st and (st.flags & n.FLAG_SCORE):
            break
        time.sleep(0.1)
    spy_room = st.score_orange if (st and (st.flags & n.FLAG_SCORE)) else None
    out.update(mem_room=mem_room, spy_room=spy_room, match=(mem_room == spy_room))
    if not out["match"]:
        write(out, stamp); return 3

    # 2. outcome counters on the live stream, driving P1 right into P2.
    tr = OutcomeTracker(debounce=a.debounce)
    have_p2 = bool(fp.get("P2"))
    t0 = time.time()
    n.keydown(IID, "d")
    last_flags = None
    try:
        while time.time() - t0 < a.seconds:
            st = n.state(pid)
            if st is not None:
                room = st.score_orange if (st.flags & n.FLAG_SCORE) else None
                p1 = bool(st.flags & n.FLAG_P1)
                p2 = bool(st.flags & n.FLAG_P2) if have_p2 else True
                flags = (int(p1), int(p2))
                if flags != last_flags:
                    out["flags"] = flags
                    last_flags = flags
                for ev in tr.update(room, p1, p2, ts=round(time.time() - t0, 2)):
                    out["events"].append(ev)
                    print("EVENT", json.dumps(ev), flush=True)
            time.sleep(0.02)
    finally:
        n.keyup(IID, "d")

    out["summary"] = tr.summary()
    write(out, stamp)
    return 0


def write(out, stamp):
    os.makedirs(RUN, exist_ok=True)
    path = os.path.join(RUN, f"round_source_proof_{stamp}.json")
    json.dump(out, open(path, "w"), indent=1)
    print("SUMMARY", json.dumps({k: out[k] for k in
          ("entered", "bound", "mem_room", "spy_room", "match", "flags", "summary")}))
    print("wrote", path)


if __name__ == "__main__":
    sys.exit(main())