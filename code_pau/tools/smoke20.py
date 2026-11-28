#!/usr/bin/env python3
"""20-episode self-play smoke test through enter_match_v2.

Purpose: the end-to-end check that says whether Pau's training setup is finished.
Each episode enters a live multiplayer match (entry_health.ensure_entry -> enter_match_v2),
binds the two fighters with the existing input test, drives P1 with the keys that work today
(a/d/w/s/f/g) and P2 with the documented arrows (Left/Right), samples the spy state, and
records the outcome: who won, kills, deaths, round counter. Every field that could not be
read is listed in `missing`.

Writes one JSONL row per episode under results/runs/smoke20_<stamp>.jsonl and prints a
running line, so the run survives a timeout. No reward, no training, no TRAINING entry.

  cd ~/nf-p/pau86 && source env.sh
  ~/nf-p/venv/bin/python ~/nf-p/code_pau/tools/smoke20.py --episodes 20 --seconds 18
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
from pathlib import Path

CODE = os.environ.get("CODE_PAU", "/home/ruggsea/nf-p/code_pau")
sys.path.insert(0, CODE)
os.environ.setdefault("NIDFARM", os.path.expanduser("~/nf-p/pau86"))
os.environ.setdefault("NID_DISPLAY_BASE", "88")

import nidlinux as n                     # noqa: E402
import nidstate as s                     # noqa: E402
import train_win as tw                   # noqa: E402
from tools import entry_health as eh     # noqa: E402

IID = int(os.environ.get("NID_IID", "0"))
RUN = Path(os.environ.get("NIDRUN", os.path.expanduser("~/nf-p/pau86/results/runs")))
TELEPORT = 300.0                          # train_state.SPAWN_JUMP: walk is <3 px/sample
DECIDE = 0.15                             # key hold + sample interval
EDGE = 60.0                               # train_win kill/respawn lands at arena ends

# Keys that work today. P1 measured (a/d/w/s/f/g). P2: arrows move; attack/jump unproven.
P1_FWD, P1_BACK, P1_ATK, P1_JUMP = "d", "a", "f", "g"
P2_FWD, P2_BACK = "Right", "Left"


def pid_now():
    try:
        pid = n._game_pid(IID)
    except Exception:
        return None
    return pid if pid and n.ping(pid) else None


def read_pair(pid):
    """(p2_x, p2_y, p1_x, p1_y) from the spy, None until both fighters are published."""
    st = n.state(pid)
    if st is None or not (st.flags & n.FLAG_P1 and st.flags & n.FLAG_P2):
        return None
    if max(abs(st.p1_x), abs(st.p2_x)) > 5000.0:
        return None
    if not (-50.0 <= st.p1_y <= 700.0 and -50.0 <= st.p2_y <= 700.0):
        return None
    return st.p2_x, st.p2_y, st.p1_x, st.p1_y


def bind(iid):
    """Track p1/p2 for this pid by the measured input response. None if not drivable."""
    pid = pid_now()
    if not pid:
        return None
    for _ in range(4):
        fp = s.find_players_by_input(iid, hold=0.45)
        if fp and fp.get("P1") and fp.get("P2"):
            tick = s.find_tick(pid) or 0
            try:
                n.untrack(pid)
            except Exception:
                pass
            n.track(pid, p1=fp["P1"], p2=fp["P2"], tick=tick)
            time.sleep(0.3)
            return pid
        time.sleep(1.5)
    return None


def one_episode(ep, seconds, rng):
    entry_returned = bool(eh.ensure_entry(IID))
    rec = {"episode": ep, "entry_returned": entry_returned, "entered": False, "samples": 0,
           "who_won": None, "kills": 0, "deaths": 0, "round_counter": 0,
           "rounds_won": 0, "rounds_lost": 0,
           "p1_moved_px": 0.0, "p2_moved_px": 0.0,
           "teleport_p1": 0, "teleport_p2": 0, "flag_drop_p1": 0, "flag_drop_p2": 0,
           "play_seconds": 0.0, "round_events": [], "missing": []}
    if not entry_returned:
        rec["missing"].append("entry: enter_match_v2/ensure_entry returned False")
        return rec

    # entry_returned is NOT entered: nidstate.in_match() has a false positive on a
    # stuck/READY screen (fv=false). Bind the fighters before believing the match.
    pid = bind(IID)
    if pid is None:
        rec["missing"].append("entry: ensure_entry True but could not bind fighters "
                              "(nidstate.in_match false positive on stuck screen)")
        return rec
    prev = read_pair(pid)
    rec["entered"] = prev is not None
    if not rec["entered"]:
        rec["missing"].append("entry: fighters bound but spy published no sample")
        return rec
    start = prev

    prev_flags = None
    prev_room = tw.read_room_now(IID)
    t0 = time.time()
    last_decide = 0.0
    blank_since = None
    while time.time() - t0 < seconds:
        now = time.time()
        # Never press keys when the arena is gone: a post-round screen treats a/d as a
        # menu slider (AGENTS rule 2). Stop the policy and end the episode.
        if blank_since is not None and now - blank_since > 2.0:
            break
        if now - last_decide >= DECIDE and blank_since is None:
            last_decide = now
            st = read_pair(pid)
            if st:
                p2x, _p2y, p1x, _p1y = st
                dx = p2x - p1x
                n.key(IID, P1_FWD if dx > 0 else P1_BACK, hold=0.10)
                if abs(dx) < 60:
                    n.key(IID, P1_ATK, hold=0.10)
                elif rng.random() < 0.15:
                    n.key(IID, P1_JUMP, hold=0.10)
                # P2 policy: the same shape on the arrows. No P2 attack/jump key exists yet.
                n.key(IID, P2_BACK if dx > 0 else P2_FWD, hold=0.10)
        st = n.state(pid)
        if st is None or not (st.flags & n.FLAG_P1 and st.flags & n.FLAG_P2):
            blank_since = blank_since or now
            time.sleep(0.03)
            continue
        blank_since = None
        p2x, p2y, p1x, p1y = st.p2_x, st.p2_y, st.p1_x, st.p1_y
        rec["samples"] += 1
        if abs(p1x - prev[2]) > TELEPORT:
            rec["teleport_p1"] += 1
            if p1x < EDGE or p1x > 400.0:
                rec["flag_drop_p1"] += 1
        if abs(p2x - prev[0]) > TELEPORT:
            rec["teleport_p2"] += 1
            if p2x < EDGE or p2x > 400.0:
                rec["flag_drop_p2"] += 1
        prev = (p2x, p2y, p1x, p1y)
        flags = (int(bool(st.flags & n.FLAG_P1)), int(bool(st.flags & n.FLAG_P2)))
        if prev_flags:
            if prev_flags[1] > 0.5 and flags[1] < 0.5:
                rec["deaths"] += 1
            if prev_flags[0] > 0.5 and flags[0] < 0.5:
                rec["kills"] += 1
        prev_flags = flags
        room = tw.read_room_now(IID)
        if room is not None and prev_room is not None:
            out = tw.room_change_round(prev_room, room, me_yellow=True)
            if out is not None:
                rec["round_events"].append({"t": round(now - t0, 1), "from": prev_room,
                                            "to": room, "outcome": out})
                rec["round_counter"] += 1
                if out == "won":
                    rec["rounds_won"] += 1
                else:
                    rec["rounds_lost"] += 1
        if room is not None:
            prev_room = room
        time.sleep(0.03)
    rec["play_seconds"] = round(time.time() - t0, 1)

    end = read_pair(pid)
    if end:
        rec["p1_moved_px"] = round(abs(end[2] - start[2]), 1)
        rec["p2_moved_px"] = round(abs(end[0] - start[0]), 1)
    if rec["round_counter"] > 0:
        rec["who_won"] = "P1" if rec["rounds_won"] > rec["rounds_lost"] else "P2"
    # no observed round -> who_won stays None; the teleport counts are a weaker
    # second source and must not be promoted to a result.
    return rec


def missing_for(recs):
    m = []
    if recs and all(r["kills"] == 0 and r["deaths"] == 0 for r in recs):
        m.append("kills/deaths: 0 in every episode (existence-flag source fires 0 times)")
    if any(r["entered"] and r["p2_moved_px"] <= 10.0 for r in recs):
        m.append("P2 control: P2 did not move even when arrows were pressed in some episodes")
    m.append("P2 action keys: no proven P2 attack/jump (only arrows Left/Right pressed)")
    if any(r["round_counter"] == 0 for r in recs):
        m.append("round counter/outcome: no room_change round observed (score field unmapped)")
    if any(r["who_won"] is None for r in recs):
        m.append("who won: undecidable without a verified round/score source")
    if any(not r["entry_returned"] for r in recs):
        m.append("entry: enter_match_v2/ensure_entry returned False at least once")
    if any(r["entry_returned"] and not r["entered"] for r in recs):
        m.append("entry false positive: ensure_entry True but no bindable match")
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--episodes", type=int, default=20)
    ap.add_argument("--seconds", type=float, default=18.0)
    ap.add_argument("--seed", type=int, default=20261128)
    args = ap.parse_args()

    RUN.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    out = RUN / f"smoke20_{stamp}.jsonl"
    rng = random.Random(args.seed)
    print(f"smoke20 start {stamp} episodes={args.episodes} seconds={args.seconds} -> {out}",
          flush=True)
    recs = []
    with out.open("w") as f:
        for ep in range(1, args.episodes + 1):
            rec = one_episode(ep, args.seconds, rng)
            recs.append(rec)
            f.write(json.dumps(rec) + "\n")
            f.flush()
            print(f"ep {ep}/{args.episodes} entry={rec['entry_returned']} "
                  f"entered={rec['entered']} who={rec['who_won']} "
                  f"W-L={rec['rounds_won']}-{rec['rounds_lost']} kills={rec['kills']} "
                  f"deaths={rec['deaths']} rounds={rec['round_counter']} "
                  f"p1_px={rec['p1_moved_px']} p2_px={rec['p2_moved_px']} "
                  f"samples={rec['samples']}", flush=True)
    summary = {
        "stamp": stamp, "episodes": args.episodes, "file": str(out),
        "entered": sum(1 for r in recs if r["entered"]),
        "entry_returned": sum(1 for r in recs if r["entry_returned"]),
        "entry_false_positive": sum(1 for r in recs
                                    if r["entry_returned"] and not r["entered"]),
        "with_round": sum(1 for r in recs if r["round_counter"] > 0),
        "p1_wins": sum(1 for r in recs if r["who_won"] == "P1"),
        "p2_wins": sum(1 for r in recs if r["who_won"] == "P2"),
        "undecided": sum(1 for r in recs if r["who_won"] is None),
        "kills_total": sum(r["kills"] for r in recs),
        "deaths_total": sum(r["deaths"] for r in recs),
        "p2_moved_in": sum(1 for r in recs if r["entered"] and r["p2_moved_px"] > 10.0),
        "missing": missing_for(recs),
    }
    (RUN / f"smoke20_{stamp}_summary.json").write_text(json.dumps(summary, indent=1))
    print("SUMMARY " + json.dumps(summary), flush=True)


if __name__ == "__main__":
    main()