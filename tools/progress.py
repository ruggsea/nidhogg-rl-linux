"""progress.py — is there NEW EVIDENCE that this project is actually working?

Built because "we got progress" has been said too often without evidence, and because the reverse is
also a failure: real progress can sit unnoticed in files nobody reads.

What counts as evidence here — nothing else does:

  attest       a line in state/attest_runs.log whose verdict starts with ATTESTED
  plan         a step in state/plan.json with status=done AND an evidence field
  claims       rows in state/claims.jsonl (each recorded with cmd + falsifier)
  generations  a completed generation (a '== gen N best' line) in a run log under /tmp
  rounds       a recorded round transition in state/rounds.jsonl (written by game.rounds)

Output: a compact snapshot, plus the DELTA since the previous snapshot (state/progress_last.json).
Exit code 0 always, so a loop can call it every tick; the delta is what a human should be told about.

    python3 tools/progress.py            # snapshot + delta
    python3 tools/progress.py --json
    python3 tools/progress.py --reset    # forget the previous snapshot
"""
import glob
import json
import os
import re
import sys
import time

SNAPSHOT = "state/progress_last.json"


def count_attested():
    ok = total = 0
    consecutive = 0
    best_consecutive = 0
    try:
        for line in open("state/attest_runs.log"):
            line = line.strip()
            if not line.startswith("{"):
                continue
            try:
                d = json.loads(line)
            except ValueError:
                continue
            total += 1
            if str(d.get("verdict", "")).startswith("ATTESTED"):
                ok += 1
                consecutive += 1
                best_consecutive = max(best_consecutive, consecutive)
            else:
                consecutive = 0
    except OSError:
        pass
    return ok, total, best_consecutive


def count_plan():
    try:
        p = json.load(open("state/plan.json"))
    except (OSError, ValueError):
        return 0, 0, []
    done = [s for s in p["steps"] if s.get("status") == "done" and s.get("evidence")]
    return len(done), len(p["steps"]), [s["id"] + " " + s["title"] for s in done]


def count_claims():
    n = 0
    try:
        for line in open("state/claims.jsonl"):
            if line.strip().startswith("{"):
                n += 1
    except OSError:
        pass
    return n


def count_generations():
    gens = 0
    for path in glob.glob("/tmp/pau_train*.log") + glob.glob("logs/*.log"):
        try:
            with open(path, errors="ignore") as f:
                gens = max(gens, len(re.findall(r"== gen \d+ best", f.read())))
        except OSError:
            continue
    return gens


def count_rounds():
    n = 0
    try:
        for line in open("state/rounds.jsonl"):
            if line.strip():
                n += 1
    except OSError:
        pass
    return n


def snapshot():
    att_ok, att_total, att_run = count_attested()
    plan_done, plan_total, plan_rows = count_plan()
    return {
        "ts": time.time(),
        "attest_passing": att_ok,
        "attest_total": att_total,
        "attest_best_streak": att_run,
        "plan_done": plan_done,
        "plan_total": plan_total,
        "plan_done_rows": plan_rows,
        "claims": count_claims(),
        "generations": count_generations(),
        "rounds_observed": count_rounds(),
    }


def main():
    if "--reset" in sys.argv:
        if os.path.exists(SNAPSHOT):
            os.remove(SNAPSHOT)
        print("previous snapshot removed")
        return 0

    now = snapshot()
    try:
        prev = json.load(open(SNAPSHOT))
    except (OSError, ValueError):
        prev = None

    delta = {}
    if prev:
        for k in ("attest_passing", "attest_best_streak", "plan_done", "claims",
                  "generations", "rounds_observed"):
            d = now[k] - prev.get(k, 0)
            if d:
                delta[k] = d

    if "--json" in sys.argv:
        print(json.dumps({"now": now, "delta": delta, "is_new": bool(delta)}, indent=1))
    else:
        print(f"evidence snapshot  ({time.strftime('%H:%M:%S')})")
        print(f"  attestation : {now['attest_passing']}/{now['attest_total']} runs passed, "
              f"best streak {now['attest_best_streak']} (step 01 needs 3 consecutive)")
        print(f"  plan        : {now['plan_done']}/{now['plan_total']} steps closed with evidence")
        for row in now["plan_done_rows"]:
            print(f"                - {row}")
        print(f"  claims      : {now['claims']} recorded (cmd + falsifier)")
        print(f"  generations : {now['generations']} completed")
        print(f"  rounds      : {now['rounds_observed']} transitions observed")
        if not prev:
            print("\n  (first snapshot - nothing to compare yet)")
        elif delta:
            print("\n  NEW EVIDENCE since last check:")
            for k, v in delta.items():
                print(f"    +{v} {k}")
        else:
            print("\n  no new evidence since the last check")

    os.makedirs("state", exist_ok=True)
    with open(SNAPSHOT, "w") as f:
        json.dump(now, f, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
