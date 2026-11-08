"""analyze_vars.py — read the Match/MatchStats named-variable captures.

The hook's `pump_vars` asks the Match objects for a list of plausible round/score variable
names and logs what it finds (`[vars] obj=<n> <name> -> u0=.. f4=.. d1=..`). This tool turns
those lines into a table and, when more than one capture exists, shows which values CHANGED
between captures - a round counter must increment while a timer ticks, so both are expected to
move but only one is a count.

A name that is simply absent is also information: `pFindOrAlloc` creating the slot means the
variable exists, and no line means it does not.

Usage:
    python3 analyze_vars.py /tmp/nid_vars_out_0.txt [more_captures...]
"""
import re
import sys

LINE = re.compile(r"\[vars\] obj=(\d+) (\S+) -> u0=(\d+) f4=(-?[\d.]+) d1=(-?[\d.]+)")


def load(paths):
    caps = []
    for p in paths:
        rows = {}
        try:
            for line in open(p, errors="ignore"):
                m = LINE.search(line)
                if m:
                    obj, name = int(m.group(1)), m.group(2)
                    rows[(obj, name)] = (int(m.group(3)), float(m.group(4)), float(m.group(5)))
        except OSError as e:
            print(f"cannot read {p}: {e}")
        caps.append((p, rows))
    return caps


def main():
    paths = sys.argv[1:] or ["/tmp/nid_vars_out_0.txt"]
    caps = load(paths)
    if not any(r for _, r in caps):
        print("no [vars] captures found - the query did not reach an instance")
        return

    for path, rows in caps:
        print(f"\n== {path}  ({len(rows)} variables found)")
        for (obj, name), (u0, f4, d1) in sorted(rows.items()):
            print(f"   obj={obj:3d} {name:12s} int={u0:<12d} float={f4:<10.3f} dbl={d1:.3f}")

    if len(caps) > 1 and all(r for _, r in caps):
        print("\n== changes between the first and last capture")
        first, last = caps[0][1], caps[-1][1]
        for key in sorted(set(first) & set(last)):
            if first[key] != last[key]:
                obj, name = key
                print(f"   obj={obj:3d} {name:12s} {first[key]} -> {last[key]}")
        missing = set(first) ^ set(last)
        if missing:
            print(f"   (variables present in only one capture: {sorted(missing)})")


if __name__ == "__main__":
    main()
