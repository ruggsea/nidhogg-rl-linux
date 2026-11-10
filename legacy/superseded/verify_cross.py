"""verify_cross.py — does crossing x>=440 actually end a round in the game?

The round counter in train_win.py is a PROXY: it fires when our fighter walks past the
measured arena end. Nothing so far proves the game agrees. This observes the same state file the
trainer reads (read-only, safe beside a live run) and, each time our fighter crosses the line,
records what the game does in the following seconds.

If a crossing is a real round win, the game should show a round transition: both fighters
reposition (a jump far larger than any walking step). If the fighter simply keeps walking, the
proxy is fiction and must not be reported as a win.

    python3 verify_cross.py 300          # watch for 300 s
"""
import sys
import time

STATE = "/tmp/nid_state_0.txt"
GOAL_X = 440.0
MAX_STEP = 60.0


def read():
    try:
        v = open(STATE).read().split()
        if len(v) < 6:
            return None
        tx, ty, mx, my, h1, h2 = (float(x) for x in v[:6])
        if not (0.5 < abs(mx) < 3000 and 0.5 < abs(tx) < 3000):
            return None
        return {"me": mx, "them": tx}
    except (OSError, ValueError):
        return None


def main():
    secs = float(sys.argv[1]) if len(sys.argv) > 1 else 180.0
    print(f"watching for crossings of x >= {GOAL_X:.0f} for {secs:.0f}s", flush=True)
    t0 = time.time()
    prev = read()
    events = []
    while time.time() - t0 < secs:
        cur = read()
        if cur and prev:
            crossed = (prev["me"] < GOAL_X <= cur["me"]
                       and abs(cur["me"] - prev["me"]) < MAX_STEP)
            if crossed:
                t_cross = time.time() - t0
                print(f"  CROSS at t={t_cross:6.2f}  me {prev['me']:.0f} -> {cur['me']:.0f}",
                      flush=True)
                # watch the next 3 s: a real round transition moves BOTH fighters a long way
                snap = []
                tv = time.time()
                while time.time() - tv < 3.0:
                    s = read()
                    if s:
                        snap.append(s)
                    time.sleep(0.05)
                if not snap:
                    print("    (state disappeared right after the crossing)", flush=True)
                    events.append({"t": t_cross, "transition": None})
                else:
                    me_span = max(s["me"] for s in snap) - min(s["me"] for s in snap)
                    th_span = max(s["them"] for s in snap) - min(s["them"] for s in snap)
                    reset = me_span > 200 or th_span > 200
                    print(f"    3 s after: me span {me_span:6.1f}  them span {th_span:6.1f}  "
                          f"-> {'ROUND TRANSITION' if reset else 'kept walking'}", flush=True)
                    events.append({"t": t_cross, "me_span": me_span,
                                   "them_span": th_span, "transition": reset})
        prev = cur or prev
        time.sleep(0.04)

    print(f"\ncrossings observed: {len(events)}", flush=True)
    trans = [e for e in events if e.get("transition")]
    print(f"followed by a round transition: {len(trans)}", flush=True)
    if not events:
        print("VERDICT: no crossing happened - the proxy is untested, not disproven", flush=True)
    elif len(trans) == len(events):
        print("VERDICT: every crossing preceded a round transition - proxy looks real", flush=True)
    else:
        print("VERDICT: crossings happened WITHOUT a round transition - proxy is NOT a win",
              flush=True)


if __name__ == "__main__":
    main()
