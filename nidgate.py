"""nidgate.py — "are we actually controlling a real match?" as a falsifiable test.

Ported concept from Pau's `nidstate.control_gate` (docs/INTERFACE.md, docs/gate/*.json),
adapted to the macOS harness in this repo. The Linux version proves the same thing with
three checks; two of them carry over unchanged and one is replaced by something stronger
that only this platform has.

    A. DRIVABLE. Hold a direction; a record's x must move. The title screen's attract demo
       moves, but not because of our keys: measured 0.0 px of direction control on attract,
       100.8 px on READY (docs/gate/attract.json, docs/gate/ready.json).

    B. IDENTITY. On Linux this is "the record tracks the sprite 1:1" (median 0.87 px error,
       next-best record 51 px). On macOS the hook finds fighters by EXACT strcmp on
       "YellowPlayer"/"OrangePlayer", so identity is semantic, not a motion coincidence.
       It is strictly stronger than pixel tracking, and it is why attract cannot pass.

    C. NO OTHER CANDIDATE. The address must be stable across samples, otherwise a stale or
       re-used pointer could look drivable by luck.

Nothing here writes to the game. Pau abandoned the write-based gate after it killed the
game twice (docs/INTERFACE.md: writes are "unsafe"), and on this build the x field we can
reach is a derived copy anyway (60 writes -> 0 drift, measured in the mac tree).

Usage:
    python3 nidgate.py 0            # run once, print verdict as JSON
    python3 nidgate.py 0 --loop 10  # keep verifying, append to /tmp/nid_gate_0.jsonl
"""
import json
import os
import sys
import time

import train_state as TS

VOTE_FILE = "/tmp/nid_gate_{}.jsonl"


def _named(state):
    """Both fighters must be present by name. Attract creates no such instance."""
    return bool(state and state.get("have154") and state.get("have242"))


def check_identity(mgr, hold_ms=500):
    """A + C: hold a direction, require the record to move and to be a stable address."""
    st0, _ = mgr.read_state()
    if not _named(st0):
        return {"pass": False, "why": "no named fighters (menu/attract)", "A_px": 0.0}

    x0 = st0["me_x"]
    t0 = time.time()
    moved = 0.0
    while time.time() - t0 < hold_ms / 1000.0:
        mgr.press(68)                      # hold D
        s, _ = mgr.read_state()
        if s:
            moved = max(moved, abs(s["me_x"] - x0))
        time.sleep(0.03)
    time.sleep(0.15)

    st1, _ = mgr.read_state()
    if not _named(st1):
        return {"pass": False, "why": "fighters vanished during hold", "A_px": moved}

    # C: address stability. The hook reports a fresh read each call; if the instance
    # pointer changed under us the "movement" may be a different object.
    stable = st1.get("have154") == st0.get("have154")

    ok = moved > 8.0 and stable
    return {
        "pass": bool(ok),
        "A_px": round(moved, 2),
        "C_stable": bool(stable),
        "P1_x": [round(x0, 2), round(st1["me_x"], 2)],
        "why": "drivable" if ok else ("input dead" if moved <= 8.0 else "unstable address"),
    }


def check_passive(mgr, span=1.0):
    """Non-intrusive gate for use WHILE the trainer is driving the game.

    check_identity() injects its own keys to prove drivability. That is right when we are
    the only actor, but during an episode the trainer is already sending keys, and a second
    writer would corrupt the action stream - so the verifier must be able to confirm a real
    match without touching the input.

    Fails closed on any doubt:
      * both fighters must be present BY NAME (attract creates none),
      * the state file must be FRESH (a stale file was a real bug: a credits screen
        reported fighters from a previous match),
      * our fighter's x must MOVE over the window (frozen state = not a live simulation).
    """
    st0, stale0 = mgr.read_state()
    if not _named(st0):
        return {"pass": False, "why": "no named fighters (menu/attract)"}
    if stale0:
        return {"pass": False, "why": "stale state file"}
    x0 = st0["me_x"]
    moved = 0.0
    t0 = time.time()
    while time.time() - t0 < span:
        s2, st2 = mgr.read_state()
        if s2 is not None and not st2:
            moved = max(moved, abs(s2["me_x"] - x0))
        time.sleep(0.06)
    ok = moved > 4.0
    return {"pass": bool(ok), "A_px": round(moved, 2),
            "why": "live and moving" if ok else "frozen / input not reaching game"}


def gate(iid=0, mgr=None, passive=False):
    own = mgr is None
    if own:
        mgr = TS.InstanceManager(iid=iid)
    try:
        res = check_passive(mgr) if passive else check_identity(mgr)
    except Exception as e:                       # a gate that crashes must fail closed
        res = {"pass": False, "why": f"exception: {e}"}
    finally:
        if own:
            pass                     # read-only: never touch a game we did not start
    res["ts"] = time.time()
    res["iid"] = iid
    return res


def main():
    iid = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    loop = None
    if "--loop" in sys.argv:
        loop = float(sys.argv[sys.argv.index("--loop") + 1])
    if loop is None:
        print(json.dumps(gate(iid), indent=1))
        return
    path = VOTE_FILE.format(iid)
    while True:
        r = gate(iid)
        with open(path, "a") as f:
            f.write(json.dumps(r) + "\n")
        print(json.dumps(r), flush=True)
        time.sleep(loop)


if __name__ == "__main__":
    main()
