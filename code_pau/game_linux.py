#!/usr/bin/env python3
"""Linux port of legacy/macos_era/game.py::rounds() — memory room index + spy me_x.

PLAN 02 accept names game.rounds(); logs use source/api game.rounds (not plan02_memory).
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, os.environ.get("CODE_PAU", str(_REPO)))

import nidlinux as n  # noqa: E402
import nidmem_room as mr  # noqa: E402

IID = int(os.environ.get("NID_IID", "0"))
ROUNDS_LOG = Path(os.environ.get("NID_ROUNDS_LOG", _REPO / "state" / "rounds.jsonl"))
POLL_S = float(os.environ.get("NID_ROUNDS_POLL", "0.1"))


def _pid(inst: int | None = None) -> int | None:
    raw = os.environ.get("NID_GAME_PID")
    if raw:
        return int(raw)
    inst = IID if inst is None else inst
    return n._game_pid(inst)


def room(inst: int | None = None) -> int | None:
    try:
        return mr.read_room(inst if inst is not None else IID)
    except Exception:
        return None


def state_sample(inst: int | None = None) -> dict | None:
    pid = _pid(inst)
    if not pid:
        return None
    st = n.state(pid)
    if st is None:
        return None
    return {
        "me_x": st.p1_x,
        "me_y": st.p1_y,
        "them_x": st.p2_x,
        "them_y": st.p2_y,
        "room": room(inst),
        "seq": st.seq,
    }


def jlog(ev: dict) -> None:
    ROUNDS_LOG.parent.mkdir(parents=True, exist_ok=True)
    with ROUNDS_LOG.open("a") as f:
        f.write(json.dumps(ev) + "\n")


def rounds(seconds: float = 60.0, verbose: bool = True, log: bool = True, inst: int | None = None) -> list:
    """Watch for ROUND TRANSITIONS (room change / large me_x jump). Pau-faithful to Mac game.rounds()."""
    inst = IID if inst is None else inst
    t0 = time.time()
    prev_room = room(inst)
    prev = state_sample(inst)
    events: list[dict] = []
    while time.time() - t0 < seconds:
        time.sleep(POLL_S)
        cur = state_sample(inst)
        r = room(inst)
        if r != prev_room:
            ev = {
                "ts": time.time(),
                "t": round(time.time() - t0, 2),
                "kind": "room_change",
                "from": prev_room,
                "to": r,
                "to_name": mr.room_name(r) if r is not None else "?",
                "from_name": mr.room_name(prev_room) if prev_room is not None else "?",
                "source": "game.rounds",
                "api": "game.rounds",
            }
            events.append(ev)
            if verbose:
                fn = ev["from_name"]
                tn = ev["to_name"]
                print(f"  ROOM CHANGE {prev_room}({fn}) -> {r}({tn})")
            if log:
                jlog(ev)
            prev_room = r
        elif (
            prev
            and cur
            and prev.get("me_x") is not None
            and cur.get("me_x") is not None
            and abs(cur["me_x"] - prev["me_x"]) > 150
        ):
            ev = {
                "ts": time.time(),
                "t": round(time.time() - t0, 2),
                "kind": "teleport",
                "from": round(prev["me_x"]),
                "to": round(cur["me_x"]),
                "room": r,
                "source": "game.rounds",
                "api": "game.rounds",
            }
            events.append(ev)
            if verbose:
                print(f"  TELEPORT me_x {prev['me_x']:.0f} -> {cur['me_x']:.0f} in room {r}")
            if log:
                jlog(ev)
        prev = cur
    if verbose:
        print(f"  {len(events)} transitions in {seconds:.0f}s")
    return events


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser(description="game.rounds() — Linux memory watcher")
    ap.add_argument("cmd", nargs="?", default="rounds", choices=("rounds", "status"))
    ap.add_argument("seconds", nargs="?", type=float, default=60.0)
    ap.add_argument("--inst", type=int, default=IID)
    ap.add_argument("--no-log", action="store_true")
    args = ap.parse_args()
    if args.cmd == "status":
        print(
            json.dumps(
                {
                    "pid": _pid(args.inst),
                    "room": room(args.inst),
                    "room_name": mr.room_name(room(args.inst) or -1),
                    "state": state_sample(args.inst),
                },
                indent=1,
            )
        )
        return 0
    pid = _pid(args.inst)
    if not pid or not n.ping(pid):
        print("no live game/spy", file=sys.stderr)
        return 2
    print(f"game.rounds({args.seconds}) pid={pid} room={room(args.inst)}", flush=True)
    evs = rounds(args.seconds, log=not args.no_log, inst=args.inst)
    print(json.dumps({"n": len(evs), "kinds": {e["kind"] for e in evs}}, indent=1))
    return 0 if evs else 1


if __name__ == "__main__":
    raise SystemExit(main())