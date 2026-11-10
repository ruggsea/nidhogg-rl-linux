"""observe_rounds.py — independent observer of the SAME state the trainer reads.

Purpose: a positive control for round-end detection. The trainer reports `roundsW 0
roundsL 0` over 100 s windows, which is either "nobody scored" or "the detector never
fires". Guessing is not acceptable here - this project has already shipped a phantom
"345 kills, 0 deaths" from a flicker, so the observer records every transition with timing
and lets the evidence decide.

Read-only: it never presses a key and never writes a control file, so it can run beside a
live training session without touching it.

  python3 observe_rounds.py 0 180        # watch instance 0 for 180 s
"""
import sys
import time

RAW = "/tmp/nid_state_{}.txt"


def read_raw(iid):
    """(them_x, them_y, me_x, me_y, have154, have242) or None."""
    try:
        with open(RAW.format(iid)) as f:
            v = f.read().split()
        if len(v) < 6:
            return None
        return tuple(float(x) for x in v[:6])
    except (OSError, ValueError):
        return None


def main():
    iid = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    secs = float(sys.argv[2]) if len(sys.argv) > 2 else 120.0

    print(f"observing instance {iid} for {secs:.0f}s (read-only)", flush=True)
    t0 = time.time()
    prev = None
    events = []
    samples = 0
    last_print = t0

    while time.time() - t0 < secs:
        raw = read_raw(iid)
        now = time.time() - t0
        if raw is None:
            time.sleep(0.05)
            continue
        samples += 1
        if prev is not None:
            # TRANSITIONS: a flag falling or rising, and any large teleport of either fighter.
            for idx, name in ((4, "them_flag"), (5, "me_flag")):
                if prev[idx] != raw[idx]:
                    ev = {"t": round(now, 2), "what": f"{name} {int(prev[idx])}->{int(raw[idx])}"}
                    events.append(ev)
                    print(f"  {ev['t']:7.2f}s  {ev['what']}", flush=True)
            for idx, name in ((0, "them_x"), (2, "me_x")):
                if abs(raw[idx] - prev[idx]) > 300:
                    ev = {"t": round(now, 2), "what": f"{name} jump {prev[idx]:.0f}->{raw[idx]:.0f}"}
                    events.append(ev)
                    print(f"  {ev['t']:7.2f}s  {ev['what']}", flush=True)
        prev = raw
        # periodic heartbeat so a long quiet stretch is distinguishable from a hang
        if now - (last_print - t0) > 20:
            print(f"  {now:7.2f}s  alive samples={samples} raw="
                  f"({raw[0]:.0f},{raw[1]:.0f},{raw[2]:.0f},{raw[3]:.0f},"
                  f"{int(raw[4])},{int(raw[5])})", flush=True)
            last_print = time.time()
        time.sleep(0.03)

    flags_down = [e for e in events if "->0" in e["what"]]
    print(f"\nsamples={samples} events={len(events)} flag_drops={len(flags_down)}", flush=True)
    print(f"duration={time.time()-t0:.1f}s", flush=True)
    print("VERDICT: rounds DO end in this window" if len(flags_down) >= 2
          else "VERDICT: no round boundary observed - cannot say anything about detection",
          flush=True)


if __name__ == "__main__":
    main()
