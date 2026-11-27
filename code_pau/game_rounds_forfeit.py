#!/usr/bin/env python3
"""Run game.rounds() while driving a forfeit — same transition plan02 sees, tagged game.rounds."""
from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import time
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, os.environ.get("CODE_PAU", str(_REPO)))
sys.path.insert(0, str(_REPO / "tools"))

import nidlinux as n  # noqa: E402
import nidstate as s  # noqa: E402
import nidmem_room as mr  # noqa: E402
import game_linux as game  # noqa: E402

LOG = Path(os.environ.get("NID_PLAN02_LOG", _REPO / "state" / "game_rounds_runs.jsonl"))


def jlog(obj: dict) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a") as f:
        f.write(json.dumps(obj) + "\n")


def _press(inst: int, keysym: str, ms: int = 120) -> None:
    pid = game._pid(inst)
    if pid:
        try:
            n.spy_key(pid, keysym, ms=ms)
            return
        except Exception:
            pass
    n.key(inst, keysym, hold=ms / 1000.0)


def forfeit(i: int) -> None:
    _press(i, "Escape", ms=150)
    time.sleep(0.8)
    _press(i, "Down", ms=120)
    time.sleep(0.35)
    _press(i, "Down", ms=120)
    time.sleep(0.35)
    _press(i, "Return", ms=120)
    time.sleep(0.8)
    _press(i, "Return", ms=120)


def in_arena(i: int) -> bool:
    try:
        return mr.read_room(i) in mr.ARENA_ROOMS
    except Exception:
        return False


def ensure_arena(i: int) -> bool:
    if in_arena(i):
        return True
    if s.enter_match_v2(i, verbose=True):
        return in_arena(i)
    if s.enter_match(i, verbose=True):
        return in_arena(i)
    s.enter_ready(i)
    return in_arena(i)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--inst", type=int, default=0)
    ap.add_argument("--watch", type=float, default=50.0, help="game.rounds() seconds")
    ap.add_argument("--delay", type=float, default=2.0, help="seconds after watch starts before forfeit")
    args = ap.parse_args()

    pid = game._pid(args.inst)
    if not pid or not n.ping(pid):
        print("no game", flush=True)
        return 2
    jlog({"phase": "start", "pid": pid, "room": game.room(args.inst)})

    if not ensure_arena(args.inst):
        jlog({"phase": "abort", "reason": "no_arena", "room": game.room(args.inst)})
        print("not in arena", flush=True)
        return 1

    jlog({"phase": "arena", "room": game.room(args.inst)})
    events: list = []

    def watch():
        nonlocal events
        events = game.rounds(args.watch, inst=args.inst)

    th = threading.Thread(target=watch, daemon=True)
    th.start()
    time.sleep(args.delay)
    forfeit(args.inst)
    th.join(timeout=args.watch + 5)

    kinds = {}
    for e in events:
        kinds[e["kind"]] = kinds.get(e["kind"], 0) + 1
    summary = {
        "phase": "summary",
        "n": len(events),
        "kinds": kinds,
        "same_kind_twice": len(events) >= 2 and max(kinds.values(), default=0) >= 2,
        "source": "game.rounds",
        "events": events,
    }
    jlog(summary)
    print("SUMMARY", json.dumps(summary), flush=True)
    rc = 0 if events else 1
    rc = 0 if any(e.get("source") == "game.rounds" for e in events) else rc
    return rc


if __name__ == "__main__":
    raise SystemExit(main())