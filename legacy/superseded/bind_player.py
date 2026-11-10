"""bind_player.py — find the instance WE control, by stimulus and response.

Why this exists: on this build all the cheap identifications are wrong.

  * "fighters are present"          -> true on the title screen, which runs a live attract match
  * "our input moves our fighter"   -> true on the attract demo too (D drifts right, A does nothing)
  * "the instance is named YellowPlayer" -> false on screens that plainly contain two fighters

The one test that has survived is stimulus-response: press D and the instance we control must move
RIGHT; press A and it must move LEFT. A demo AI moves on its own schedule and cannot satisfy both
signs on demand.

This tool takes `publish_instances` output (/tmp/nid_insts_<id>.txt: id, object_index, x, y),
runs that test over the candidate set, and reports which id answers - or that none does.

    python3 bind_player.py 0
"""
import sys
import time

INSTS = "/tmp/nid_insts_{}.txt"
KEYS = "/tmp/nid_keys_{}.txt"


def snap(iid):
    """{instance_id: (obj, x, y)} from the hook's dump, or None."""
    out = {}
    try:
        with open(INSTS.format(iid)) as f:
            for line in f:
                p = line.split()
                if len(p) == 4:
                    out[int(p[0])] = (int(p[1]), float(p[2]), float(p[3]))
    except (OSError, ValueError):
        return None
    return out or None


def press(iid, code, secs=0.9):
    t0 = time.time()
    while time.time() - t0 < secs:
        with open(KEYS.format(iid), "w") as f:
            f.write(f"{code}\n")
        time.sleep(0.05)


def measure(iid, code, secs=0.9):
    """Hold `code`, return {id: dx} for instances present before and after."""
    before = snap(iid)
    if not before:
        return None, None
    press(iid, code, secs)
    time.sleep(0.25)
    after = snap(iid)
    if not after:
        return None, None
    common = set(before) & set(after)
    return before, {i: after[i][1] - before[i][1] for i in common}


def main():
    iid = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    print("binding: candidates from the hook's instance dump")

    s = snap(iid)
    if not s:
        print("no instance dump - is the hook running and the game in a match?")
        return
    print(f"candidates: {len(s)} instances with plausible coordinates")

    before_d, dx_d = measure(iid, 68)      # D = right
    before_a, dx_a = measure(iid, 65)      # A = left
    if dx_d is None or dx_a is None:
        print("instance dump vanished during the test - cannot bind")
        return

    rows = []
    for inst in sorted(set(dx_d) & set(dx_a)):
        obj, x, y = before_d[inst]
        rows.append((inst, obj, x, y, dx_d[inst], dx_a[inst]))

    # The response we require: moved RIGHT under D, LEFT under A, both by a real margin.
    MIN = 8.0
    winners = [r for r in rows if r[4] >= MIN and r[5] <= -MIN]

    print(f"\n{'instance':>10s} {'obj':>4s} {'x':>8s} {'y':>7s} {'dx(D)':>7s} {'dx(A)':>7s}")
    for inst, obj, x, y, dd, da in sorted(rows, key=lambda r: -(r[4] - r[5]))[:12]:
        flag = "  <== RESPONDS CORRECTLY" if (dd >= MIN and da <= -MIN) else ""
        print(f"{inst:10d} {obj:4d} {x:8.1f} {y:7.1f} {dd:+7.1f} {da:+7.1f}{flag}")

    if winners:
        print(f"\nBOUND: instance id {winners[0][0]} (obj {winners[0][1]}) "
              f"dx(D)={winners[0][4]:+.1f} dx(A)={winners[0][5]:+.1f}")
    else:
        print(f"\nNO instance satisfied both directions (need dx(D) >= {MIN:.0f} and "
              f"dx(A) <= -{MIN:.0f}). Either this is not a controllable match, or the "
              f"fighter's coordinates are not in the dump.")


if __name__ == "__main__":
    main()
