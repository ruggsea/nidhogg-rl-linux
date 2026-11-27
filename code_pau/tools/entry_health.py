#!/usr/bin/env python3
"""Entry health gate for the multiplayer training entry (Critic 2026-11-27T18:54:54Z).

Before `nidstate.enter_match_v2`: read the stuck signature from the screen (no fighters, no
READY wall, no yellow), relaunch the instance if unhealthy, settle to READY, then enter.
One json under results/runs with snapshot before -> pid after -> entered.

Self-contained: stdlib + `nidlinux` + `nidstate` only.

What it does NOT do: no train loop, no reward, no state bridge, no caller. No TRAINING, no
park-dose. (The caller lives in the fork's `train_state.py`.)

Measured T165855Z: `nidstate.in_match()` is a FALSE POSITIVE on the stuck screen (returned
True with fv=false wall=null yel=0 ora=2980), so the gate does NOT trust `in_match`; it uses
the screen signature. In a live match after entry, wall is None / central False (the wall is
a READY-screen detector).
"""
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for _p in (ROOT, os.environ.get("CODE_PAU", "")):
    if _p and _p not in sys.path:
        sys.path.insert(0, _p)

import nidlinux as n     # noqa: E402
import nidstate as ns    # noqa: E402

IID = int(os.environ.get("NID_IID", "0"))
RUN = os.environ.get("NIDRUN", "/home/ruggsea/nf-p/pau86/results/runs")
STAMP = os.environ.get("NID_STAMP") or time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
FIELDS = ("ready", "fv", "wall", "yel")


def pid(iid=IID):
    try:
        return n._game_pid(iid)
    except Exception:
        return None


def snapshot(tag, iid=IID):
    """Minimal screen state: fighters visible, READY wall, ready screen, yellow crumb count."""
    if not pid(iid):
        return {"tag": tag, "fv": False, "wall": None, "ready": False, "yel": 0}
    fv = bool(ns._fighters_visible(iid, f"eh_fv_{tag}"))
    wall = ns._wall_x(iid, f"eh_w_{tag}")
    yel = 0
    if not fv:
        try:
            a = ns.frame(iid, f"eh_y_{tag}")
            if a is not None:
                m = ns._mask(a, "yellow")
                m[int(m.shape[0] * 0.62):, :] = False
                yel = int(m.sum())
        except Exception:
            yel = 0
    try:
        ready = bool(ns.on_ready_screen(iid))
    except Exception:
        ready = False
    return {"tag": tag, "fv": fv, "wall": wall, "ready": ready, "yel": yel}


def stuck_sig(c):
    """The critic's stuck signature: no fighters, no READY wall, no yellow."""
    return (not c.get("fv")) and (c.get("wall") is None) and ((c.get("yel") or 0) == 0)


def settle_ready(iid=IID, max_loops=12):
    """Escape/Return until `enter_ready` sees fighters+wall. Returns the last snapshot."""
    c = snapshot("settle0", iid)
    for k in range(max_loops):
        if ns.enter_ready(iid):
            return snapshot(f"settle{k + 1}", iid)
        n.key(iid, "Escape", hold=0.12)
        time.sleep(0.8)
        n.key(iid, "Escape", hold=0.12)
        time.sleep(0.8)
        for _ in range(3):
            n.key(iid, "Return", hold=0.12)
            time.sleep(0.9)
        c = snapshot(f"settle{k + 1}", iid)
    return c


def relaunch(iid=IID):
    print("RELAUNCH stuck instance", iid, flush=True)
    try:
        n.stop_id(iid)
    except Exception as e:
        print("stop_id err", repr(e), flush=True)
    time.sleep(2)
    n.start_ids([iid], fresh=False)
    t0 = time.time()
    while time.time() - t0 < 120:
        if pid(iid):
            break
        time.sleep(2)
    print("game_pid_after", pid(iid), "wait_s", round(time.time() - t0), flush=True)
    time.sleep(8)


def ensure_entry(iid=IID):
    """Health gate, then enter Match_v2. True only for a verified live match.

    Called by the train loop instead of the old menu walk: if the stuck signature is present
    the instance is relaunched and settled to READY, then `nidstate.enter_match_v2`. An
    already-live match is accepted by enter_match_v2.
    """
    before = snapshot("ee_before", iid)
    if stuck_sig(before):
        relaunch(iid)
        settle_ready(iid)
    entered = bool(ns.enter_match_v2(iid, verbose=True))
    if not entered:
        # enter_match_v2 polls in_match for 7.5s after Return; spawn can take longer
        # (measured: fighters visible at room=29 after it gave up). Poll fighters 20s.
        t0 = time.time()
        while time.time() - t0 < 20:
            time.sleep(1.0)
            if snapshot("ee_poll", iid).get("fv"):
                entered = True
                print("ensure_entry: fighters appeared after enter_match_v2 gave up", flush=True)
                break
    if not entered:
        # Still nothing: one fresh process, then retry.
        print("ensure_entry: no verified match -> relaunch and retry", flush=True)
        relaunch(iid)
        settle_ready(iid)
        entered = bool(ns.enter_match_v2(iid, verbose=True))
    time.sleep(2)
    after = snapshot("ee_after", iid)
    return bool(entered and after.get("fv"))


def main():
    os.makedirs(RUN, exist_ok=True)
    pid0 = pid()
    before = snapshot("eh_before")
    stuck_before = stuck_sig(before)
    print("HEALTH_BEFORE", json.dumps({"pid": pid0, "wall": before.get("wall"),
          "fv": before.get("fv"), "yel": before.get("yel"), "ready": before.get("ready"),
          "stuck": stuck_before}, default=str), flush=True)
    relaunched = False
    after_relaunch = None
    if stuck_before:
        relaunch()
        relaunched = True
        after_relaunch = settle_ready()
    entered = bool(ns.enter_match_v2(IID, verbose=True))
    time.sleep(2)
    after = snapshot("eh_after")
    pid1 = pid()
    pid_changed = bool(pid1 and pid0 and pid1 != pid0)
    out = {
        "probe": "entry_health_v1", "stamp": STAMP, "iid": IID,
        "ok": bool(entered and after.get("fv")),
        "stuck_before": stuck_before, "relaunched": relaunched,
        "game_pid_before": pid0, "game_pid_after": pid1, "pid_changed": pid_changed,
        "entry": "enter_match_v2", "entered": entered,
        "before": {k: before.get(k) for k in FIELDS},
        "after": {k: after.get(k) for k in FIELDS},
        "after_relaunch": ({k: after_relaunch.get(k) for k in FIELDS} if after_relaunch else None),
        "note": "stuck = fv false and wall null and yel 0 (in_match not trusted)",
    }
    path = "%s/entry_health_%s.json" % (RUN, STAMP)
    open(path, "w").write(json.dumps(out, indent=2) + "\n")
    print("WROTE", path, flush=True)
    print("ENTRY_HEALTH", json.dumps({k: out[k] for k in
          ("ok", "stuck_before", "relaunched", "game_pid_before", "game_pid_after",
           "entered")}), flush=True)
    raise SystemExit(0 if out["ok"] else 2)


if __name__ == "__main__":
    main()