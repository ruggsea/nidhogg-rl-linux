#!/usr/bin/env python3
"""One run proving the TRAIN entry path is the multiplayer helper (Critic 17:18Z item 2).

Drives InstanceManager.launch() -> run_entry() exactly as train_win does, and writes one
json/log: helper fires (pid change when needed), then a round starts under the new route.
No TRAINING, no generations. Run on the farm with pau86/env.sh sourced.
"""
import json
import os
import sys
import time

CODE = os.environ.get("CODE_PAU", "/home/ruggsea/nf-p/code_pau")
sys.path.insert(0, CODE)
sys.path.insert(0, os.path.join(CODE, "tools"))
import nidlinux as n            # noqa: E402
import train_state as TS        # noqa: E402
import i1_ready_nav as nav      # noqa: E402
from tools import entry_health as eh   # noqa: E402

ARENA_ROOMS = range(26, 78)

IID = int(os.environ.get("NID_IID", "0"))
RUN = os.environ.get("NIDRUN", "/home/ruggsea/nf-p/pau86/results/runs")
STAMP = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())


def pid():
    try:
        return n._game_pid(IID)
    except Exception:
        return None


def main():
    os.makedirs(RUN, exist_ok=True)
    m = TS.InstanceManager(iid=IID)
    print("entry_health", eh.__file__, "retry", "no verified match" in open(eh.__file__).read(), flush=True)
    pid0 = pid()
    print("BEFORE pid", pid0, flush=True)
    if pid0 is None:
        m.launch()
    pid_launch = pid()
    print("LAUNCHED pid", pid_launch, flush=True)

    ok = bool(m.run_entry())
    pid1 = pid()
    print("RUN_ENTRY", ok, "pid_after", pid1, flush=True)

    round_started = False
    room_seen = None
    st = None
    t0 = time.time()
    while time.time() - t0 < 45:
        st, _stale = m.read_state()
        if m.has_players(st):
            room_seen = nav.room()
            if room_seen is not None and int(room_seen) in ARENA_ROOMS:
                round_started = True
                break
        time.sleep(1.0)

    out = {
        "probe": "entry_swap_v1", "stamp": STAMP, "iid": IID,
        "pid_before": pid0, "pid_after_launch": pid_launch, "pid_after_entry": pid1,
        "pid_changed": bool((pid0 != pid1) or (pid_launch and pid_launch != pid0)),
        "run_entry_ok": ok, "has_players": bool(st is not None and m.has_players(st)),
        "room_at_round": room_seen, "round_started": round_started,
        "entry": "train_state.run_entry -> tools/entry_health.ensure_entry -> nidstate.enter_match_v2",
    }
    path = os.path.join(RUN, "entry_swap_%s.json" % STAMP)
    open(path, "w").write(json.dumps(out, indent=2) + "\n")
    print("WROTE", path, flush=True)
    print("ENTRY_SWAP", json.dumps(out), flush=True)
    raise SystemExit(0 if (ok and round_started) else 2)


if __name__ == "__main__":
    main()