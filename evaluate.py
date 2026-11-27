"""Evaluate a policy against the CPU: play N rounds, report round/match wins.

Round outcomes use the plan03 MET signal (room_change_round), not GOAL_X walks.

Writes results/runs/plan07_eval.json (and /tmp/nid_eval.json). Touches out/BEATS_CPU
when win_rate >= 0.6 over a sample with rounds_won >= 6.
"""
import argparse
import json
import os
import sys
import time

import numpy as np

import neuro
import train_state as TS
import train_win as W

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out", "BEATS_CPU")
DURABLE = os.path.join(HERE, "results", "runs", "plan07_eval.json")


def evaluate(mgr, weights, rounds=12, seed=999, seconds=600.0):
    w = np.array(weights, dtype=float)
    rng = np.random.default_rng(seed)
    if not mgr.ensure_match():
        # try full entry once
        if not mgr.run_entry() or not mgr.wait_for_match():
            return None
    try:
        mgr._raise_speed()
    except Exception:
        pass
    try:
        if getattr(mgr, "bound_inst", None) is None and hasattr(mgr, "bind_by_response"):
            mgr.bind_by_response()
    except Exception:
        pass

    won = lost = 0
    events = []
    prev_room = W.read_room_now(mgr.iid)
    last_pay = 0.0
    t0 = time.time()
    while won + lost < rounds and time.time() - t0 < seconds:
        room = W.read_room_now(mgr.iid)
        rc = W.room_change_round(prev_room, room, me_yellow=True)
        if rc is not None and time.time() - last_pay > 1.0:
            if rc == "won":
                won += 1
                print(f"  ROUND WON room {prev_room}->{room} ({won}-{lost})", flush=True)
            else:
                lost += 1
                print(f"  round lost room {prev_room}->{room} ({won}-{lost})", flush=True)
            events.append({"t": round(time.time() - t0, 2), "from": prev_room,
                           "to": room, "outcome": rc})
            last_pay = time.time()
            # accept next round
            mgr.press(13)
            time.sleep(0.5)
        if room is not None:
            prev_room = room

        st = W.state_of(mgr) if hasattr(W, "state_of") else W.read_state(mgr.iid)
        if st is None:
            # maybe match over / stats
            if time.time() - last_pay > 8.0:
                try:
                    mgr._accept_restart(tries=1, wait=4.0)
                except Exception:
                    mgr.press(13)
                time.sleep(0.3)
            time.sleep(0.05)
            continue
        code = neuro.decide(w, st, rng)
        if code:
            mgr.press(code)
        time.sleep(0.02)

    n = won + lost
    return {
        "rounds_won": won,
        "rounds_lost": lost,
        "rounds_total": n,
        "win_rate": (won / n) if n else 0.0,
        "events": events,
        "seconds": round(time.time() - t0, 1),
        "source": "train_win.room_change_round",
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("policy", nargs="?", default="/tmp/nid_best_win.json")
    ap.add_argument("--rounds", type=int, default=12)
    ap.add_argument("--seconds", type=float, default=600.0)
    ap.add_argument("--seed", type=int, default=999)
    args = ap.parse_args()
    if not os.path.exists(args.policy):
        print("no policy to evaluate:", args.policy)
        return
    d = json.load(open(args.policy))
    os.environ["NID_ORDERS"] = "1"
    os.system('pkill -f "MacOS/Nidhogg" 2>/dev/null')
    time.sleep(1.5)
    try:
        os.chmod(TS.PREFS, 0o644)
    except OSError:
        pass
    with open(TS.PREFS, "w") as f:
        f.write(open(TS.MUTED_PREFS).read())
    mgr = TS.InstanceManager(iid=0)
    mgr.launch()
    time.sleep(TS.BOOT_WAIT)
    mgr.run_entry()
    mgr.wait_for_match()
    res = evaluate(mgr, d["weights"], rounds=args.rounds,
                   seed=args.seed, seconds=args.seconds)
    try:
        mgr.close()
    except Exception:
        pass
    time.sleep(1)
    try:
        os.chmod(TS.PREFS, 0o644)
        with open(TS.PREFS, "w") as f:
            f.write(open(TS.PRISTINE_PREFS).read())
    except OSError:
        pass
    payload = res or {}
    os.makedirs(os.path.dirname(DURABLE), exist_ok=True)
    json.dump(payload, open(DURABLE, "w"), indent=1)
    json.dump(payload, open("/tmp/nid_eval.json", "w"), indent=1)
    print("eval:", payload, flush=True)
    if res and res.get("rounds_total", 0) >= 10:
        print(f"PLAN07_OK rounds_total={res['rounds_total']} "
              f"W={res['rounds_won']} L={res['rounds_lost']} "
              f"win_rate={res['win_rate']:.3f}", flush=True)
    if res and res.get("win_rate", 0) >= 0.6 and res.get("rounds_won", 0) >= 6:
        os.makedirs(os.path.dirname(OUT), exist_ok=True)
        open(OUT, "w").write(json.dumps(res))
        print("BEATS_CPU flag written", flush=True)


if __name__ == "__main__":
    main()
