#!/usr/bin/env python3
"""PLAN03 prep: live room poll → train_win round-term fitness delta (no win-rate fiction).

Polls read_room_now() until room_change_round fires, applies fitness_delta_on_room_change,
appends one row to state/plan03_train_win_fit.jsonl with live=true. Optional forfeit via
nidstate keys (farm only). Does not touch plan.json.

  NIDFARM=~/nf-p/pau86 CODE_PAU=~/nf-p/code_pau python3 tools/plan03_live_fit.py --poll-only
  python3 tools/plan03_live_fit.py --forfeit   # enter match + forfeit then poll
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, os.environ.get("CODE_PAU", str(ROOT)))

import train_win as tw  # noqa: E402

OUT = Path(os.environ.get("NID_PLAN03_FIT_LOG", ROOT / "state" / "plan03_train_win_fit.jsonl"))


def jlog(obj: dict) -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("a") as f:
        f.write(json.dumps(obj) + "\n")


def poll_until_pay(iid: int, timeout: float = 45.0, rounds_won: int = 0, rounds_lost: int = 0):
    t0 = time.time()
    prev = tw.read_room_now(iid)
    if prev is None:
        raise RuntimeError(f"read_room_now({iid}) returned None — no live room index")
    while time.time() - t0 < timeout:
        time.sleep(0.12)
        cur = tw.read_room_now(iid)
        if cur is None:
            continue
        pay = tw.fitness_delta_on_room_change(prev, cur, rounds_won, rounds_lost)
        if pay is not None:
            pay["t"] = round(time.time() - t0, 2)
            pay["iid"] = iid
            return pay
        prev = cur
    return None


def forfeit_keys(iid: int) -> None:
    import nidlinux as n  # noqa: E402

    for key, hold in (("Escape", 0.15), ("Down", 0.12), ("Down", 0.12), ("Return", 0.12), ("Return", 0.12)):
        n.key(iid, key, hold=hold)
        time.sleep(0.35 if key != "Escape" else 0.8)


def enter_if_needed(iid: int) -> str:
    try:
        import nidstate as s  # noqa: E402
        import nidmem_room as mr  # noqa: E402

        if mr.read_room(iid) in mr.ARENA_ROOMS:
            return "already_arena"
        if s.enter_match_v2(iid, verbose=True):
            return "enter_match_v2"
        if s.enter_match(iid, verbose=True):
            return "enter_match"
        return "enter_failed"
    except ImportError:
        return "no_nidstate"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--inst", type=int, default=0)
    ap.add_argument("--timeout", type=float, default=45.0)
    ap.add_argument("--forfeit", action="store_true", help="enter match then forfeit before poll")
    ap.add_argument("--poll-only", action="store_true", help="poll only (transition must happen externally)")
    args = ap.parse_args()

    entry = None
    if args.forfeit:
        entry = enter_if_needed(args.inst)
        if entry == "enter_failed":
            print("enter_failed", flush=True)
            sys.exit(2)
        time.sleep(1.0)
        forfeit_keys(args.inst)
    elif not args.poll_only:
        print("specify --forfeit or --poll-only", flush=True)
        sys.exit(2)

    pay = poll_until_pay(args.inst, timeout=args.timeout)
    if pay is None:
        jlog({"phase": "live_miss", "iid": args.inst, "entry": entry, "ts": time.time()})
        print("no room_change within timeout", flush=True)
        sys.exit(1)

    summary = {
        "phase": "summary",
        "live": True,
        "source": "train_win_live_probe",
        "module": "train_win.py",
        "probe": "tools/plan03_live_fit.py",
        "funcs": ["read_room_now", "room_change_round", "fitness_delta_on_room_change"],
        "coeffs": pay.get("coeffs"),
        "fitness_before": pay["fitness_before"],
        "fitness_after": pay["fitness_after"],
        "fitness_delta": pay["fitness_delta"],
        "rounds_won": pay["rounds_won"],
        "rounds_lost": pay["rounds_lost"],
        "transitions": [pay],
        "entry": entry,
        "ts": time.time(),
        "note": "live poll; round term from train_win helpers only",
    }
    jlog(summary)
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == "__main__":
    main()