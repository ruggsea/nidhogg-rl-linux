"""adversary.py — an independent verifier the trainer is forced to depend on.

The failure this exists for, stated plainly: every phantom result in this project came from
a component grading its own work. The trainer decided "this episode was a real match" using
the same readings it then scored, so when those readings were wrong (title screen attract
demo, stale state file, a READY screen that ignores input) the trainer happily paid fitness
for it.

So the verdict comes from somewhere else:

  * separate PROCESS (dies then restart the trainer does not silently keep training),
  * separate CODE PATH (nidgate.py, not train_win.py's inline checks),
  * its own clock (votes every few seconds whether or not an episode is running),
  * and it FAILS CLOSED: no fresh PASS means the episode cannot be scored.

train_win.py reads the vote log and marks an episode no_match unless a PASS landed within
`max_age` seconds of the episode. A stale vote is not a pass.

    python3 adversary.py 0            # verify every 8s for instance 0, append votes
    python3 adversary.py 0 --read     # print the current verdict the trainer would see
"""
import json
import os
import sys
import time

import nidgate

LOG = "/tmp/nid_gate_{}.jsonl"


def latest(iid, max_age=25.0):
    """The newest vote for this instance, and whether it is fresh and passing.

    Returns (ok, info). ok is True ONLY for a fresh PASS. Everything else - missing file,
    old verdict, failing verdict - is False, so a broken adversary stops training rather
    than waving it through.
    """
    path = LOG.format(iid)
    try:
        with open(path) as f:
            lines = [l for l in f if l.strip()]
    except OSError:
        return False, {"why": "adversary never ran"}
    if not lines:
        return False, {"why": "adversary has no votes"}
    try:
        vote = json.loads(lines[-1])
    except ValueError:
        return False, {"why": "unreadable vote"}
    age = time.time() - vote.get("ts", 0)
    fresh = age <= max_age
    ok = bool(vote.get("pass")) and fresh
    return ok, {"age_s": round(age, 1), "fresh": fresh,
                "pass": bool(vote.get("pass")),
                "why": vote.get("why"), "A_px": vote.get("A_px")}


def main():
    iid = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    if "--read" in sys.argv:
        ok, info = latest(iid)
        print(json.dumps({"trust_match": ok, **info}, indent=1))
        return
    period = 8.0
    if "--period" in sys.argv:
        period = float(sys.argv[sys.argv.index("--period") + 1])
    path = LOG.format(iid)
    while True:
        try:
            vote = nidgate.gate(iid)
        except Exception as e:
            vote = {"ts": time.time(), "pass": False, "why": f"gate crashed: {e}"}
        with open(path, "a") as f:
            f.write(json.dumps(vote) + "\n")
        print(("PASS " if vote.get("pass") else "FAIL ")
              + str(vote.get("why")) + f"  A_px={vote.get('A_px')}", flush=True)
        time.sleep(period)


if __name__ == "__main__":
    main()
