"""probe_restart.py — which key dismisses the round-over screen, and how fast?

Measured problem this session: a round lasts ~9 s, then the state file loses the fighters and
re-entry costs 2-3 minutes. `_accept_restart()` presses Enter and waits 4 s, twice, and the
trainer log shows it failing. Before adding more retries, find out what the screen actually
wants:

  1. get into a drivable match (gate-confirmed),
  2. let it run until the round ends (fighters disappear from the state file),
  3. try candidate keys one at a time, each with its own window, and record which one makes
     the fighters come back and how long it took.

Nothing here is assumed: a key only counts if players reappear AND the gate passes again.
"""
import json
import os
import sys
import time

import train_state as TS

CANDIDATES = [("Enter", 13), ("Space", 32), ("Esc", 27), ("F", 70), ("G", 71)]


def players(mgr):
    st, stale = mgr.read_state()
    return mgr.has_players(st) and not stale


def main():
    iid = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    mgr = TS.InstanceManager(iid=iid)
    out = {"iid": iid, "results": []}

    if not players(mgr):
        print("no live match to start from - run an episode first", flush=True)
        return

    # wait for the round to end, so we are looking at a real round-over screen
    print("waiting for the round to end...", flush=True)
    t0 = time.time()
    while time.time() - t0 < 120 and players(mgr):
        time.sleep(0.5)
    ended = not players(mgr)
    print(f"round over: {ended} (after {time.time()-t0:.1f}s)", flush=True)
    out["round_over"] = ended
    out["round_seconds"] = round(time.time() - t0, 1)
    if not ended:
        json.dump(out, open(f"results/restart_{iid}.json", "w"), indent=1)
        return

    for name, code in CANDIDATES:
        mgr.press(code)
        t0 = time.time()
        back = False
        while time.time() - t0 < 8.0:
            if players(mgr):
                back = True
                break
            time.sleep(0.25)
        elapsed = round(time.time() - t0, 2)
        drivable = False
        if back:
            mgr.prime_controls(1.0)
            drivable = mgr.prove_control(1.2)
        rec = {"key": name, "code": code, "players_back": back,
               "seconds": elapsed, "drivable": bool(drivable),
               "gate_px": round(mgr.gate_px, 1)}
        out["results"].append(rec)
        print(json.dumps(rec), flush=True)
        if back:
            break          # first key that works is the answer; no need to poke further

    os.makedirs("results", exist_ok=True)
    json.dump(out, open(f"results/restart_{iid}.json", "w"), indent=1)
    print("wrote results/restart_%d.json" % iid, flush=True)


if __name__ == "__main__":
    main()
