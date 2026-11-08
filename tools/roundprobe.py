"""roundprobe.py — find what a ROUND TRANSITION actually looks like in memory.

Why: after a full day, `rounds_won` is still 0 and no round transition has ever been observed. The
fitness therefore rests on kills and territory only, and the 60/150-point round terms cannot fire. Until
we know what the game does at a round boundary, every claim about "winning" is about a proxy we
invented.

Method (stimulus + oracle, the shape this project keeps needing):
  * bind our fighter by response (so we know which instance we control);
  * drive it toward the opponent and attack repeatedly (a scripted policy - we are not testing a
    learner here, we are looking for a state change);
  * sample at ~20 Hz: room index, both fighters' positions, and the whole instance dump;
  * report every ROOM CHANGE and every large teleport, with the samples either side.

A round boundary should be one of: room index changes (the arena scrolls), both fighters teleport, or
some field flips. Whatever it turns out to be, this prints it instead of me guessing.

    python3 tools/roundprobe.py --seconds 90
"""
import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import train_state as TS

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HERE, "state", "roundprobe.jsonl")


def snap(iid):
    d = {}
    try:
        with open(f"/tmp/nid_insts_{iid}.txt") as f:
            for line in f:
                p = line.split()
                if len(p) == 4:
                    d[int(p[0])] = (int(p[1]), float(p[2]), float(p[3]))
    except (OSError, ValueError):
        return None
    return d or None


def room(iid):
    try:
        return int(open(f"/tmp/nid_room_now_{iid}.txt").read().strip())
    except (OSError, ValueError):
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=float, default=90.0)
    ap.add_argument("--iid", type=int, default=0)
    a = ap.parse_args()

    mgr = TS.InstanceManager(iid=a.iid)
    if not mgr.in_arena():
        print(f"not in an arena (room={room(a.iid)}) - run tools/attest.py first")
        return 1

    bound = mgr.bind_by_response()
    if bound is None:
        print("could not bind our fighter - nothing to drive")
        return 1
    print(f"bound to instance {bound}; driving with attack+advance for {a.seconds:.0f}s")

    t0 = time.time()
    prev = snap(a.iid)
    prev_room = room(a.iid)
    events = []
    n = 0
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    fh = open(OUT, "w")

    while time.time() - t0 < a.seconds:
        # scripted drive: advance toward the opponent, swing often
        cur = snap(a.iid)
        if cur and bound in cur and cur.get(bound):
            me = cur[bound][1]
            others = [v for k, v in cur.items() if k != bound and v[0] in (242, 244, 245, 154)]
            opp = min(others, key=lambda v: abs(v[1] - me)) if others else None
            if opp:
                gap = opp[1] - me
                key = 68 if gap > 25 else (65 if gap < -25 else 70)   # approach, or swing
            else:
                key = 68
        else:
            key = 70
        mgr.press(key)
        time.sleep(0.04)

        n += 1
        if n % 3:
            continue
        cur = snap(a.iid)
        r = room(a.iid)
        if not cur:
            continue
        rec = {"t": round(time.time() - t0, 2), "room": r, "bound": bound,
               "me": cur.get(bound), "n_inst": len(cur)}
        fh.write(json.dumps(rec) + "\n")

        if prev is not None and prev_room is not None:
            if r != prev_room:
                ev = {"t": rec["t"], "kind": "ROOM_CHANGE", "from": prev_room, "to": r,
                      "me_before": prev.get(bound), "me_after": cur.get(bound)}
                events.append(ev)
                print(f"  ROOM CHANGE {prev_room} -> {r}  me {prev.get(bound)} -> {cur.get(bound)}")
            elif bound in prev and bound in cur:
                dx = abs(cur[bound][1] - prev[bound][1])
                if dx > 150:
                    ev = {"t": rec["t"], "kind": "TELEPORT", "dx": round(dx, 1),
                          "from": prev[bound], "to": cur[bound], "room": r}
                    events.append(ev)
                    print(f"  TELEPORT of our fighter dx={dx:.0f} in room {r}: "
                          f"{prev[bound]} -> {cur[bound]}")
        prev, prev_room = cur, r

    fh.close()
    print(f"\n{n} samples, {len(events)} events -> {OUT}")
    if not events:
        print("no room change and no teleport observed: either nothing happened, or the round "
              "boundary is not a position change at all")
    return 0


if __name__ == "__main__":
    sys.exit(main())
