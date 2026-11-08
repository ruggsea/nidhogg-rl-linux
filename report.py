"""report.py — the project scoreboard, computed from recorded runs only.

Rule this exists to enforce: no number may be quoted unless it can be recomputed from a recorded
run. Anything living only in a /tmp log that has since been overwritten is not evidence.

It reports, across every run under results/runs/:

  * how many episodes were REAL (opponent actually played) and how many were not;
  * per-episode kills vs deaths - BOTH the aggregate and the per-episode count, because those
    two told different stories earlier tonight and the aggregate was the misleading one;
  * rounds: claimed vs verified, kept strictly separate. An unverified claim is an artifact;
  * whether any of the task's success conditions have ever been met.

Usage:
    python3 report.py
"""
import glob
import json
import os
import statistics as st


def load_all():
    eps = []
    for run in sorted(glob.glob("results/runs/*")):
        path = os.path.join(run, "episodes.jsonl")
        try:
            with open(path) as f:
                for line in f:
                    line = line.strip()
                    if line:
                        e = json.loads(line)
                        e["_run"] = os.path.basename(run)
                        eps.append(e)
        except OSError:
            continue
    return eps


def is_real(e):
    if e.get("no_match"):
        return False
    span = e.get("opp_span")
    if span is None or span < 15.0:
        return False
    return (e.get("samples") or 0) >= 20


def main():
    eps = load_all()
    if not eps:
        print("no recorded episodes under results/runs/")
        return
    real = [e for e in eps if is_real(e)]
    print(f"episodes recorded: {len(eps)}   REAL: {len(real)}   "
          f"(not real or discarded: {len(eps) - len(real)})")
    if not real:
        print("\nNo REAL episodes recorded yet - nothing below can be claimed.")
        return

    k = sum(e.get("kills", 0) for e in real)
    d = sum(e.get("deaths", 0) for e in real)
    per_ep = [(e.get("kills", 0), e.get("deaths", 0)) for e in real]
    better = sum(1 for a, b in per_ep if a > b)
    even = sum(1 for a, b in per_ep if a == b)
    print(f"\nkills {k}   deaths {d}   (aggregate net {k - d:+d})")
    print(f"per episode: kills>deaths in {better}/{len(real)}, equal in {even}/{len(real)}")
    diffs = [e.get("fitness") for e in real if e.get("fitness") is not None]
    if len(diffs) > 1:
        print(f"fitness: mean {st.mean(diffs):.2f}  sd {st.stdev(diffs):.2f}  n {len(diffs)}")

    cw = sum(e.get("rounds_won", 0) for e in real)
    cl = sum(e.get("rounds_lost", 0) for e in real)
    vw = sum(sum(1 for v in (e.get("cross_verified") or []) if v) for e in real)
    uw = sum(sum(1 for v in (e.get("cross_verified") or []) if not v) for e in real)
    vl = sum(sum(1 for v in (e.get("loss_verified") or []) if v) for e in real)
    ul = sum(sum(1 for v in (e.get("loss_verified") or []) if not v) for e in real)
    print(f"\nrounds counted {cw}W/{cl}L   verified {vw}W/{vl}L   "
          f"refused-as-artifact {uw}W/{ul}L")

    print("\nsuccess conditions:")
    print(f"  a verified round win      : {'YES' if vw else 'never'}")
    print(f"  kills > deaths in aggregate: {'YES' if k > d else 'no'}")
    print(f"  a measured win rate       : {'YES' if vw + vl >= 10 else 'no - not enough verified rounds'}")


if __name__ == "__main__":
    main()
