#!/usr/bin/env python3
"""PLAN 02 memory watcher: poll live room index through forfeit (game.rounds-style room_change)."""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, os.environ.get("CODE_PAU", str(ROOT)))
sys.path.insert(0, str(ROOT / "tools"))

import nidlinux as n  # noqa: E402
import nidstate as s  # noqa: E402
import nidmem_room as mr  # noqa: E402

OUT = Path(os.environ.get("NID_PLAN02_OUT", ROOT / "state"))
OUT.mkdir(parents=True, exist_ok=True)
LOG = Path(os.environ.get("NID_PLAN02_LOG", OUT / "plan02_room_change.jsonl"))
ROUNDS = Path(os.environ.get("NID_ROUNDS_LOG", OUT / "rounds.jsonl"))


def jlog(path: Path, obj: dict) -> None:
    with path.open("a") as f:
        f.write(json.dumps(obj) + "\n")


def wait_game(i: int, timeout: float = 180.0) -> int:
    t0 = time.time()
    while time.time() - t0 < timeout:
        pid = n._game_pid(i)
        if pid and n.ping(pid):
            return pid
        time.sleep(3.0)
    raise RuntimeError("no game pid/spy within timeout")


def pad_status(i: int) -> dict:
    y = bool(s.pad_and_fighter(i, "yellow", "p02y"))
    o = bool(s.pad_and_fighter(i, "orange", "p02o"))
    o2 = bool(s.pad_and_fighter(i, "orange", "p02o2"))
    wx = s._wall_x(i, "p02w")
    return {"yellow": y, "orange": o, "orange2": o2, "wx": wx}


def in_arena(i: int) -> bool:
    try:
        return mr.read_room(i) in mr.ARENA_ROOMS
    except Exception:
        return False


def enter_live(i: int, verbose: bool = True) -> tuple[bool, str]:
    if in_arena(i):
        return True, "already_arena"
    if s.in_match(i) and in_arena(i):
        return True, "already_live"
    if s.enter_match_v2(i, verbose=verbose):
        return True, "enter_match_v2"
    if s.enter_match(i, verbose=verbose):
        return True, "enter_match"
    return False, "enter_failed"


def forfeit(i: int) -> None:
    n.key(i, "Escape", hold=0.15)
    time.sleep(0.8)
    n.key(i, "Down", hold=0.12)
    time.sleep(0.35)
    n.key(i, "Down", hold=0.12)
    time.sleep(0.35)
    n.key(i, "Return", hold=0.12)
    time.sleep(0.8)
    n.key(i, "Return", hold=0.12)


def wait_room_change(i: int, t0: float, expect_from: set[int] | None = None, timeout: float = 35.0):
    prev = mr.read_room(i)
    t_start = time.time()
    while time.time() - t_start < timeout:
        time.sleep(0.12)
        cur = mr.read_room(i)
        if cur != prev and (expect_from is None or prev in expect_from):
            return {
                "kind": "room_change",
                "from": prev,
                "to": cur,
                "t": round(time.time() - t0, 2),
                "from_name": mr.room_name(prev),
                "to_name": mr.room_name(cur),
            }
        prev = cur
    return None


def run_trial(i: int, trial: int) -> dict | None:
    t0 = time.time()
    ready = s.on_ready_screen(i) if hasattr(s, "on_ready_screen") else s.match_state(i) == "ready"
    live_match = s.in_match(i)
    arena = in_arena(i)
    try:
        room = mr.read_room(i)
    except Exception:
        room = -1
    jlog(
        LOG,
        {
            "phase": "trial_start",
            "trial": trial,
            "ready": ready,
            "live": arena,
            "live_match": live_match,
            "room": room,
        },
    )

    if not arena:
        if s.match_state(i) != "ready" and not in_arena(i):
            jlog(LOG, {"phase": "ensure_match", "state": s.match_state(i), "room": room})
            em = False
            try:
                wait_game(i, timeout=60)
                em = s.ensure_match(i, attempts=2, verbose=True)
            except Exception as e:
                jlog(LOG, {"phase": "ensure_match", "ok": False, "error": type(e).__name__, "msg": str(e)})
            else:
                jlog(
                    LOG,
                    {
                        "phase": "ensure_match",
                        "ok": em,
                        "state": s.match_state(i),
                        "room": mr.read_room(i),
                    },
                )
            arena = in_arena(i)
        if not arena and (ready or room in (2, 3, 4, 17, 25)):
            s.enter_ready(i)
        jlog(LOG, {"phase": "park", **pad_status(i)})
        t_stage = time.time()
        ok, how = enter_live(i)
        jlog(LOG, {"phase": "stage", "after": round(time.time() - t_stage, 2), "how": how, "ok": ok})
        if not ok and how == "enter_failed":
            s.enter_ready(i)
            jlog(LOG, {"phase": "park", **pad_status(i)})
            ok2 = s.enter_match_v2(i, verbose=True)
            jlog(LOG, {"phase": "fallback_enter", "ok": ok2, "live": in_arena(i)})
            if not ok2 and not in_arena(i):
                jlog(LOG, {"phase": "trial_end", "trial": trial, "n": 0, "error": "no_live_match"})
                return None
        elif not ok:
            jlog(LOG, {"phase": "trial_end", "trial": trial, "n": 0, "error": how})
            return None

    try:
        arena_room = mr.read_room(i)
    except Exception as e:
        jlog(LOG, {"phase": "trial_end", "trial": trial, "n": 0, "error": str(e)})
        return None
    jlog(LOG, {"phase": "live", "trial": trial, "room": arena_room})

    forfeit(i)
    ev = wait_room_change(i, t0, expect_from=set(mr.ARENA_ROOMS) | {29})
    if not ev:
        jlog(LOG, {"phase": "trial_end", "trial": trial, "n": 0, "error": "no_room_change"})
        return None

    rec = {
        "ts": time.time(),
        "kind": "room_change",
        "from": ev["from"],
        "to": ev["to"],
        "trial": trial,
        "source": "plan02_memory",
        "t": ev["t"],
        "ready": s.match_state(i) == "ready" if hasattr(s, "match_state") else ready,
        "live": in_arena(i),
    }
    jlog(LOG, {**ev, "trial": trial, "phase": "room_change"})
    jlog(LOG, {"phase": "trial_end", "trial": trial, "n": 1, "room": ev["to"], "ready": rec["ready"]})
    jlog(ROUNDS, rec)
    return rec


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--inst", type=int, default=0)
    ap.add_argument("--trials", type=int, default=1)
    ap.add_argument("--first-trial", type=int, default=3, help="trial number for first run (default 3)")
    args = ap.parse_args()

    pid = wait_game(args.inst)
    print("game pid", pid, flush=True)

    events = []
    for k in range(args.trials):
        trial = args.first_trial + k
        print(f"=== trial {trial} ===", flush=True)
        ev = run_trial(args.inst, trial)
        if ev:
            events.append(ev)
            print("LOGGED", ev, flush=True)
        else:
            print("trial", trial, "FAILED", flush=True)
        time.sleep(1.5)

    kinds: dict[str, int] = {}
    for e in events:
        kinds[e["kind"]] = kinds.get(e["kind"], 0) + 1
    summary = {
        "phase": "summary",
        "n": len(events),
        "kinds": kinds,
        "same_kind_twice": len(events) >= 2 and max(kinds.values()) >= 2,
        "events": [
            {"from": e["from"], "to": e["to"], "trial": e["trial"], "t": e["t"]} for e in events
        ],
    }
    jlog(LOG, summary)
    print("SUMMARY", summary, flush=True)
    return 0 if events else 1


if __name__ == "__main__":
    raise SystemExit(main())