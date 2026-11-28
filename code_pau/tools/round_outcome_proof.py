#!/usr/bin/env python3
"""Prove a REAL round outcome is read from the verified room index (step 2).

The FLAG_P1/P2 death source cannot fire (nidspy.zig:225 inRange, commit 38c5d0e), so
the outcome is read from the room index at ``exe_base(pid) + ROOM_OFF`` — verified as
the game's room variable in ``state/round_source_proof_20261128T062640Z.json``
(``mem_room == spy_room == 29``). ``outcome_events.round_boundary`` maps a room
transition to a round:

    arena -> a different arena : round advance (screen moved)
    arena -> rMatchStats (20)  : match ended (a forfeit from an arena is a loss)
    arena -> menu/lobby        : re-entry navigation, NOT a round

One measurement: enter a live multiplayer match (``enter_match_v2``), bind the
fighters, play a short scripted P1/P2 policy, and watch the room for a boundary. If
play produces none, drive the game's own forced-loss sequence (Escape menu forfeit,
the recipe in ``game_rounds_forfeit.py``) and read the resulting arena -> rMatchStats
boundary. So the run yields a real, room-index outcome either way when a round ends.

Writes ``state/round_outcome_proof_<stamp>.json`` and prints SUMMARY. No reward, no
training, no TRAINING entry.

  cd ~/nf-p/pau86 && source env.sh
  ~/nf-p/venv/bin/python ~/nf-p/code_pau/tools/round_outcome_proof.py --seconds 25
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

CODE = os.environ.get("CODE_PAU", os.path.expanduser("~/nf-p/code_pau"))
sys.path.insert(0, CODE)
os.environ.setdefault("NIDFARM", os.path.expanduser("~/nf-p/pau86"))
os.environ.setdefault("NID_DISPLAY_BASE", "88")

import nidlinux as n                        # noqa: E402
import nidstate as s                        # noqa: E402
from nidmem import ROOM_OFF, exe_base        # noqa: E402
from tools import entry_health as eh         # noqa: E402
from tools.outcome_events import ARENA_ROOMS, round_boundary, room_name  # noqa: E402

IID = int(os.environ.get("NID_IID", "0"))
STATE = os.environ.get("NIDSTATE", os.path.expanduser("~/nf-p/pau86/state"))

P1_FWD, P1_BACK, P1_ATK = "d", "a", "f"
P2_FWD, P2_BACK = "Right", "Left"
DECIDE = 0.15


def room_now(pid):
    st = n.state(pid)
    if st is not None and (st.flags & n.FLAG_SCORE):
        return st.score_orange
    return None


def bind():
    """Find the two fighters by input response and TRACK them (score slot = room).

    Tracking is required: without ``n.track`` the spy publishes no flags and
    ``room_now`` returns None. Mirrors smoke20.bind.
    """
    pid = n._game_pid(IID)
    if not (pid and n.ping(pid)):
        return None
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
            return pid
        time.sleep(1.0)
    return None


def drive(seconds, prev_room):
    """Play a short P1/P2 policy; return (prev_room, boundary_events)."""
    import random
    rng = random.Random(20261128)
    t0 = time.time()
    last = 0.0
    events = []
    while time.time() - t0 < seconds:
        now = time.time()
        if now - last >= DECIDE:
            last = now
            st = n.state(n._game_pid(IID))
            if st is not None and (st.flags & n.FLAG_P1) and (st.flags & n.FLAG_P2):
                dx = st.p2_x - st.p1_x
                n.key(IID, P1_FWD if dx > 0 else P1_BACK, hold=0.10)
                if abs(dx) < 60:
                    n.key(IID, P1_ATK, hold=0.10)
                n.key(IID, P2_BACK if dx > 0 else P2_FWD, hold=0.10)
        r = room_now(n._game_pid(IID))
        if r != prev_room:
            b = round_boundary(prev_room, r)
            if b:
                b["t"] = round(time.time() - t0, 2)
                events.append(b)
            prev_room = r
        time.sleep(0.03)
    return prev_room, events


def forfeit(prev_room):
    """The game's own forced-loss sequence; returns (prev_room, events)."""
    pid = n._game_pid(IID)
    events = []
    t0 = time.time()
    for k in ("Escape", "Down", "Down", "Return", "Return"):
        n.key(IID, k, hold=0.12)
        time.sleep(0.7)
        r = room_now(pid)
        if r != prev_room:
            b = round_boundary(prev_room, r)
            if b:
                b["via"] = "forfeit"
                b["t"] = round(time.time() - t0, 2)
                events.append(b)
            prev_room = r
    # settle: poll a few seconds for the match-stats room to appear
    while time.time() - t0 < 12:
        r = room_now(pid)
        if r != prev_room:
            b = round_boundary(prev_room, r)
            if b:
                b["via"] = "forfeit"
                b["t"] = round(time.time() - t0, 2)
                events.append(b)
            prev_room = r
        time.sleep(0.2)
    return prev_room, events


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=float, default=25.0, help="scripted-play watch")
    ap.add_argument("--no-forfeit", action="store_true", help="do not force a loss")
    a = ap.parse_args()
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    out = {"stamp": stamp, "entered": False, "bound": False, "pid": None,
           "room_start": None, "room_end": None, "events": [],
           "via": None, "tracker": None}

    entered = bool(eh.ensure_entry(IID))
    pid = bind() if n._game_pid(IID) else None
    out.update(entered=entered, bound=bool(pid), pid=n._game_pid(IID))
    # `entered` from ensure_entry is a screen-snapshot AND (entry_health.py); it can read
    # False while the match is live (T113244Z: in_match after Return +7.6s, fighters bound).
    # The bound fighters are the real evidence, so do not gate on `entered`.
    if not pid:
        write(out, stamp)
        return 2
    time.sleep(1.5)
    prev = room_now(pid)
    out["room_start"] = prev
    if prev is None:
        write(out, stamp)
        return 3

    prev, events = drive(a.seconds, prev)
    if events:
        out["via"] = "play"
    elif not a.no_forfeit and prev in ARENA_ROOMS:
        prev, events = forfeit(prev)
        out["via"] = "forfeit"
    out["events"] = events
    out["room_end"] = prev
    out["tracker"] = {"rounds_by_room": len(events),
                      "room_end_name": room_name(prev)}
    write(out, stamp)
    return 0


def write(out, stamp):
    os.makedirs(STATE, exist_ok=True)
    path = os.path.join(STATE, f"round_outcome_proof_{stamp}.json")
    json.dump(out, open(path, "w"), indent=1)
    print("SUMMARY", json.dumps({k: out[k] for k in
          ("entered", "bound", "room_start", "room_end", "via",
           "tracker")}))
    print("wrote", path)


if __name__ == "__main__":
    sys.exit(main())