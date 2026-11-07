"""keysweep.py — Phase 2 of Pau's plan (docs/NEXT_STEPS.md):

    "Player state machine. Full key sweep against the animation field.
     Acceptance: a table key -> animation values that names attack, crouch, roll, throw,
     jump, dive; rows 4/5/7/9 of the contract move to proven."

Method, following his provenance rule (a field is `proven` only if the row names the
STIMULUS that reveals it and the ORACLE that confirms it):

  stimulus: hold exactly one key for N frames
  oracle:   the offset must move under that key and must NOT move under a control hold
            (no key) or under a different key, on the same instance, in the same match

Reporting an offset as "animation" because it changed once is the mistake that cost them
four rounds. So every candidate here is compared against a no-key control and against at
least two other keys, and offsets that move in the control (idle drift, timers, camera) are
discarded before anything is claimed.

    python3 keysweep.py 0            # sweep on instance 0, write results/keysweep_0.json
"""
import json
import os
import sys
import time

import train_state as TS

DUMP = "/tmp/nid_dump_{}.txt"
KEYS = {"A": 65, "D": 68, "W": 87, "S": 83, "F": 70, "G": 71, "SPACE": 32, "SHIFT": 16}
HOLD = 0.55          # seconds held - long enough for an animation to change and stay
SETTLE = 0.35


def read_dump(iid):
    try:
        with open(DUMP.format(iid)) as f:
            out = {}
            for line in f:
                parts = line.split()
                if len(parts) == 2:
                    out[int(parts[0], 16)] = float(parts[1])
            return out or None
    except (OSError, ValueError):
        return None


def snapshot(mgr, iid, hold_key=None, hold=HOLD):
    """Sample the struct while holding (or not holding) a key."""
    if hold_key is None:
        time.sleep(hold)
        return read_dump(iid)
    t0 = time.time()
    last = None
    while time.time() - t0 < hold:
        mgr.press(hold_key)
        d = read_dump(iid)
        if d:
            last = d
        time.sleep(0.04)
    time.sleep(SETTLE)
    return last or read_dump(iid)


def diff(a, b):
    if not a or not b:
        return {}
    return {off: (a[off], b[off]) for off in a if off in b and abs(a[off] - b[off]) > 1e-4}


def main():
    iid = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    mgr = TS.InstanceManager(iid=iid)

    st, _ = mgr.read_state()
    if not TS.InstanceManager.has_players(st):
        print(json.dumps({"ok": False, "why": "no live match - enter one first",
                          "state": st}, indent=1))
        return

    results = {"iid": iid, "ts": time.time(), "keys": {}, "control": None}

    # control: the struct changes on its own (timers, camera, idle animation). Anything
    # that moves here is not attributable to a key and must be discarded.
    c1 = snapshot(mgr, iid, None)
    c2 = snapshot(mgr, iid, None)
    control = diff(c1, c2)
    results["control"] = sorted(control)

    for name, code in KEYS.items():
        before = read_dump(iid)
        during = snapshot(mgr, iid, code)
        after = read_dump(iid)
        moved = diff(before, during)
        # attribute only offsets that are NOT explained by the idle control
        attrib = {o: v for o, v in moved.items() if o not in control}
        results["keys"][name] = {
            "code": code,
            "candidate_offsets": sorted(attrib),
            "values": {f"0x{o:x}": [round(v[0], 3), round(v[1], 3)]
                       for o, v in sorted(attrib.items())[:12]},
            "reverted_after": sorted(o for o in attrib
                                     if after and abs(after.get(o, 0) - during.get(o, 0)) < 1e-4),
        }
        print(f"{name} ({code}): {len(attrib)} candidate offsets "
              f"{[hex(o) for o in sorted(attrib)[:8]]}", flush=True)
        time.sleep(0.6)

    # a field named by ONE key and by no other is the interesting kind
    owners = {}
    for name, r in results["keys"].items():
        for off in r["candidate_offsets"]:
            owners.setdefault(off, []).append(name)
    unique = {hex(o): names for o, names in sorted(owners.items()) if len(names) == 1}
    results["unique_to_one_key"] = unique

    os.makedirs("results", exist_ok=True)
    path = f"results/keysweep_{iid}.json"
    with open(path, "w") as f:
        json.dump(results, f, indent=1)
    print(f"\n{len(unique)} offsets are moved by exactly one key -> {path}")
    for off, names in list(unique.items())[:15]:
        print(f"  {off}: {names[0]}")


if __name__ == "__main__":
    main()
