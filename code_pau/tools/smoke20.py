#!/usr/bin/env python3
"""20-episode self-play smoke test through enter_match_v2.

Purpose: the end-to-end check that says whether Pau's training setup is finished.
Each episode enters a live multiplayer match (entry_health.ensure_entry -> enter_match_v2),
binds the two fighters with the existing input test, drives P1 with the keys that work today
(a/d/w/s/f/g) and P2 with the documented arrows (Left/Right), samples the spy state, and
records the outcome: who won, kills, deaths, round counter. Those four fields come from
tools/outcome_events.OutcomeTracker, an event-tied source (game room + fighter alive
flags with a 3-sample death debounce), never an x-jump. Every field that could not be
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
from nidmem import ROOM_OFF, exe_base     # noqa: E402
from tools import entry_health as eh     # noqa: E402
from tools.outcome_events import ARENA_ROOMS, OutcomeTracker, round_boundary  # noqa: E402

IID = int(os.environ.get("NID_IID", "0"))
RUN = Path(os.environ.get("NIDRUN", os.path.expanduser("~/nf-p/pau86/results/runs")))
TELEPORT = 300.0                          # train_state.SPAWN_JUMP: walk is <3 px/sample
DECIDE = 0.15                             # key hold + sample interval
EDGE = 60.0                               # respawn/round boundary at the arena ends

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
            # Track the game room in the spy's score slot too, so the tracker reads
            # the room at the same tick as the alive flags (same as the bridge).
            n.track(pid, p1=fp["P1"], p2=fp["P2"],
                    score=exe_base(pid) + ROOM_OFF, tick=tick)
            time.sleep(0.3)
            return pid
        time.sleep(1.5)
    return None


def forfeit_round(pid, prev_room, rec, t0):
    """Round boundary on demand: the game's own forfeit (PROVEN.md §3).

    pause (Escape) -> Down, Down -> Return -> Return ends the round/match with an
    arena -> rMatchStats room transition. Used only when scripted play produced no
    in-play round; the event is tagged ``via: forfeit`` so it is never counted as a
    kill or a self-play win.
    """
    for k in ("Escape", "Down", "Down", "Return", "Return"):
        n.key(IID, k, hold=0.12)
        time.sleep(0.7)
        room = room_now(pid)
        b = round_boundary(prev_room, room)
        if b:
            b.update(t=round(time.time() - t0, 1), via="forfeit")
            rec["_room_bounds"].append(b)
            rec["room_rounds"] += 1
            return room
        prev_room = room
    settle_end = time.time() + 12.0           # poll for rMatchStats to appear
    while time.time() < settle_end:
        room = room_now(pid)
        b = round_boundary(prev_room, room)
        if b:
            b.update(t=round(time.time() - t0, 1), via="forfeit")
            rec["_room_bounds"].append(b)
            rec["room_rounds"] += 1
            return room
        prev_room = room
        time.sleep(0.2)
    return prev_room


def room_now(pid):
    st = n.state(pid)
    if st is not None and (st.flags & n.FLAG_SCORE):
        return st.score_orange
    return None


def one_episode(ep, seconds, rng, p2_policy="mirror", p1_policy="mirror",
                finish="none"):
    entry_returned = bool(eh.ensure_entry(IID))
    rec = {"episode": ep, "entry_returned": entry_returned, "entered": False, "samples": 0,
           "who_won": None, "kills": 0, "deaths": 0, "round_counter": 0,
           "rounds_won": 0, "rounds_lost": 0,
           "p1_moved_px": 0.0, "p2_moved_px": 0.0,
           "teleport_p1": 0, "teleport_p2": 0, "flag_drop_p1": 0, "flag_drop_p2": 0,
           "play_seconds": 0.0, "round_events": [], "missing": [],
           # step-2 cut: round boundaries from the verified room index (ROOM_OFF),
           # never the FLAG_P1/P2 death debounce (commit 38c5d0e, LIMITATION 28).
           "room_rounds": 0, "_room_bounds": [],
           # raw spy-flag diagnostics: prove whether FLAG_P1/P2 ever drop at all.
           # nidspy.zig:225 inRange() is a mapping-bounds check, so these are expected
           # to stay 1 for the whole match; that is the point of measuring them.
           "flag_low_p1": 0, "flag_low_p2": 0,
           "flag_low_streak_max_p1": 0, "flag_low_streak_max_p2": 0,
           "p1x_min": None, "p1x_max": None, "p2x_min": None, "p2x_max": None,
           "rooms_seen": []}
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

    tracker = OutcomeTracker(debounce=3)     # event-tied kills/deaths/round counter
    prev_room = None
    t0 = time.time()
    last_decide = 0.0
    blank_since = None
    sweep_i = 0
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
                if p1_policy == "engage":
                    # Keep the measured striking band (dx ~22 lands, dx ~59 misses) and
                    # vary the sword height so a mid-block cannot clash forever.
                    adx = abs(dx)
                    if adx > 45:
                        n.key(IID, P1_FWD if dx > 0 else P1_BACK, hold=0.10)
                    elif adx < 18:
                        n.key(IID, P1_BACK if dx > 0 else P1_FWD, hold=0.10)
                    else:
                        n.key(IID, "w" if sweep_i % 2 == 0 else "s", hold=0.08)
                        n.key(IID, P1_ATK, hold=0.10)
                        sweep_i += 1
                elif p1_policy == "run":
                    # Simplest in-play attempt: always push toward the opponent's goal
                    # (right) and spam attack, so a kill becomes an advance. P2 idle.
                    n.key(IID, P1_FWD, hold=0.10)
                    n.key(IID, P1_ATK, hold=0.10)
                    if rng.random() < 0.12:
                        n.key(IID, P1_JUMP, hold=0.10)
                else:
                    n.key(IID, P1_FWD if dx > 0 else P1_BACK, hold=0.10)
                    if abs(dx) < 60:
                        n.key(IID, P1_ATK, hold=0.10)
                    elif rng.random() < 0.15:
                        n.key(IID, P1_JUMP, hold=0.10)
                # P2 policy: mirror on the arrows, or idle so P1 can win a round.
                # No P2 attack/jump key exists yet.
                if p2_policy == "mirror":
                    n.key(IID, P2_BACK if dx > 0 else P2_FWD, hold=0.10)
        st = n.state(pid)
        if st is None:
            blank_since = blank_since or now
            time.sleep(0.03)
            continue
        # Feed the event-tied tracker on every sample, including samples where one
        # flag is down: a fighter's flag held low for 3 samples IS the death event.
        # Skipping those samples is what made kills/deaths read 0 in 02:12Z smoke20.
        p1_alive = bool(st.flags & n.FLAG_P1)
        p2_alive = bool(st.flags & n.FLAG_P2)
        room = st.score_orange if st.flags & n.FLAG_SCORE else None
        # Room-index round boundary (the step-2 outcome source). Navigation through
        # menu/lobby rooms returns None, so re-entry is never counted as a round.
        b = round_boundary(prev_room, room)
        if b:
            b["t"] = round(now - t0, 1)
            rec["room_rounds"] += 1
            rec["_room_bounds"].append(b)
        prev_room = room
        tracker.update(room, p1_alive, p2_alive, ts=round(now - t0, 1))
        for _who, _alive in (("p1", p1_alive), ("p2", p2_alive)):
            if _alive:
                rec["_streak_" + _who] = 0
            else:
                rec["flag_low_" + _who] += 1
                rec["_streak_" + _who] = rec.get("_streak_" + _who, 0) + 1
                if rec["_streak_" + _who] > rec["flag_low_streak_max_" + _who]:
                    rec["flag_low_streak_max_" + _who] = rec["_streak_" + _who]
        if not (p1_alive and p2_alive):
            blank_since = blank_since or now
            time.sleep(0.03)
            continue
        blank_since = None
        p2x, p2y, p1x, p1y = st.p2_x, st.p2_y, st.p1_x, st.p1_y
        rec["p1x_min"] = p1x if rec["p1x_min"] is None else min(rec["p1x_min"], p1x)
        rec["p1x_max"] = p1x if rec["p1x_max"] is None else max(rec["p1x_max"], p1x)
        rec["p2x_min"] = p2x if rec["p2x_min"] is None else min(rec["p2x_min"], p2x)
        rec["p2x_max"] = p2x if rec["p2x_max"] is None else max(rec["p2x_max"], p2x)
        if room is not None and room not in rec["rooms_seen"]:
            rec["rooms_seen"].append(room)
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
        time.sleep(0.03)
    rec["play_seconds"] = round(time.time() - t0, 1)
    rec.pop("_streak_p1", None)
    rec.pop("_streak_p2", None)

    # Scripted play never ended a round in play (idle P2, mirror, and the strike-band
    # engage policy all produced 0 room boundaries). If asked, end the episode with the
    # game's own forfeit so a real room-index outcome is recorded, tagged via=forfeit.
    if finish == "forfeit" and rec["room_rounds"] == 0 and prev_room in ARENA_ROOMS:
        rec["via"] = "forfeit"
        prev_room = forfeit_round(pid, prev_room, rec, t0)

    # Event-tied outcome: deaths from the (dead) alive flags plus round boundaries
    # from the verified room index. With neither, the winner stays None and is
    # never guessed from a jump.
    rec["round_counter"] = tracker.rounds + rec["room_rounds"]
    rec["kills"] = tracker.kills
    rec["deaths"] = tracker.deaths
    rec["rounds_won"] = tracker.kills
    rec["rounds_lost"] = tracker.deaths
    rec["round_events"] = ([e for e in tracker.events if e["kind"] in ("death", "room")]
                           + rec.pop("_room_bounds"))

    end = read_pair(pid)
    if end:
        rec["p1_moved_px"] = round(abs(end[2] - start[2]), 1)
        rec["p2_moved_px"] = round(abs(end[0] - start[0]), 1)
    if rec["round_counter"] > 0:
        adv = [e for e in rec["round_events"] if e.get("kind") == "round_advance"]
        ends = [e for e in rec["round_events"] if e.get("kind") == "round_match_end"]
        if adv:
            rec["who_won"] = "P1" if adv[-1].get("advanced_right") else "P2"
        elif ends and ends[-1].get("via") == "forfeit":
            rec["who_won"] = "P2"          # yellow (P1) forfeited the match
        # any other match end does not name a winner
    # no observed round -> who_won stays None; the teleport counts are a weaker
    # second source and must not be promoted to a result.
    return rec


def missing_for(recs):
    m = []
    if recs and all(r["kills"] == 0 and r["deaths"] == 0 for r in recs):
        m.append("kills/deaths: 0 in every episode (event-tied alive-flag source fired 0 times)")
    if any(r["entered"] and r["p2_moved_px"] <= 10.0 for r in recs):
        m.append("P2 control: P2 did not move even when arrows were pressed in some episodes")
    m.append("P2 action keys: no proven P2 attack/jump (only arrows Left/Right pressed)")
    if any(r["round_counter"] == 0 for r in recs):
        m.append("round counter/outcome: no event-tied round observed (room+alive tracker)")
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
    ap.add_argument("--p2", choices=("mirror", "idle"), default="mirror",
                    help="P2 policy: mirror P1 with the arrows, or stay idle")
    ap.add_argument("--p1", choices=("mirror", "engage", "run"), default="mirror",
                    help="P1 policy: mirror approach, strike-band engage with height sweep, "
                         "or run-right-and-attack")
    ap.add_argument("--finish", choices=("none", "forfeit"), default="none",
                    help="if play ends no round, end the episode with the game's own forfeit")
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
            rec = one_episode(ep, args.seconds, rng, p2_policy=args.p2, p1_policy=args.p1,
                              finish=args.finish)
            recs.append(rec)
            f.write(json.dumps(rec) + "\n")
            f.flush()
            print(f"ep {ep}/{args.episodes} entry={rec['entry_returned']} "
                  f"entered={rec['entered']} who={rec['who_won']} "
                  f"W-L={rec['rounds_won']}-{rec['rounds_lost']} kills={rec['kills']} "
                  f"deaths={rec['deaths']} rounds={rec['round_counter']} "
                  f"room_rounds={rec['room_rounds']} "
                  f"p1_px={rec['p1_moved_px']} p2_px={rec['p2_moved_px']} "
                  f"samples={rec['samples']} flaglow_p1={rec['flag_low_p1']} "
                  f"flaglow_p2={rec['flag_low_p2']}", flush=True)
    summary = {
        "stamp": stamp, "episodes": args.episodes, "file": str(out),
        "entered": sum(1 for r in recs if r["entered"]),
        "entry_returned": sum(1 for r in recs if r["entry_returned"]),
        "entry_false_positive": sum(1 for r in recs
                                    if r["entry_returned"] and not r["entered"]),
        "with_round": sum(1 for r in recs if r["round_counter"] > 0),
        "room_rounds_total": sum(r.get("room_rounds", 0) for r in recs),
        "p1_wins": sum(1 for r in recs if r["who_won"] == "P1"),
        "p2_wins": sum(1 for r in recs if r["who_won"] == "P2"),
        "undecided": sum(1 for r in recs if r["who_won"] is None),
        "kills_total": sum(r["kills"] for r in recs),
        "deaths_total": sum(r["deaths"] for r in recs),
        "p2_moved_in": sum(1 for r in recs if r["entered"] and r["p2_moved_px"] > 10.0),
        "flag_low_p1_total": sum(r["flag_low_p1"] for r in recs),
        "flag_low_p2_total": sum(r["flag_low_p2"] for r in recs),
        "flag_low_streak_max": max([r["flag_low_streak_max_p1"] for r in recs]
                                   + [r["flag_low_streak_max_p2"] for r in recs] + [0]),
        "missing": missing_for(recs),
    }
    (RUN / f"smoke20_{stamp}_summary.json").write_text(json.dumps(summary, indent=1))
    print("SUMMARY " + json.dumps(summary), flush=True)


if __name__ == "__main__":
    main()