"""curriculum.py — raise the difficulty when the policy masters the current one.

The user's suggestion, and it is the right shape: do not run a fixed sweep of difficulties (most of that
budget lands on settings already mastered or far out of reach), and do not jump to a hard setting. Raise
difficulty ONE STEP when the policy has mastered the current one, and hold it otherwise.

Two signals are needed and they are different:

  MASTERED   the policy wins at the current difficulty. That needs a verified round/win measurement,
             which does not exist yet (rounds_won is 0), so today this signal is unavailable.
  PLATEAU    fitness has stopped improving over the last K generations. This IS computable from the run
             logs now, and it is the fallback trigger: if there is nothing left to learn at this level,
             raising difficulty is the only way to create new gradient.

So the rule is deliberately conservative: raise only when a definite signal says the current level is
exhausted; otherwise hold. Raising on noise would destroy the measurement the project spent a day
building.

    python3 tools/curriculum.py status      # current step, plateau evidence, decision
    python3 tools/curriculum.py advance     # force the next step (records why)
    python3 tools/curriculum.py reset

State lives in state/curriculum.json so the choice is visible and reproducible, not remembered.
"""
import glob
import json
import os
import re
import sys
import time

STATE = os.path.join("state", "curriculum.json")
LEVELS = ["lowest", "low", "medium", "high", "highest"]   # the TRAINING slider, left to right
PLATEAU_GENS = 3          # generations without improvement before we consider it mastered
MIN_IMPROVEMENT = 2.0     # fitness points; below the measured noise floor (~2 sigma) it is not progress


def load():
    try:
        return json.load(open(STATE))
    except (OSError, ValueError):
        return {"level": 0, "history": [], "created": time.time()}


def save(d):
    os.makedirs("state", exist_ok=True)
    json.dump(d, open(STATE, "w"), indent=1)


def generations():
    """Best fitness per generation, from any run log that recorded a summary line."""
    out = []
    for path in sorted(glob.glob("/tmp/pau_train*.log")):
        try:
            txt = open(path, errors="ignore").read()
        except OSError:
            continue
        for m in re.finditer(r"== gen (\d+) best (-?\d+\.\d+)", txt):
            out.append((int(m.group(1)), float(m.group(2)), path))
    return out[-20:]


def decide():
    gens = generations()
    d = load()
    level = d.get("level", 0)
    if len(gens) < PLATEAU_GENS + 1:
        return {"action": "hold", "why": f"only {len(gens)} generations recorded; need "
                                        f"{PLATEAU_GENS + 1} to judge a plateau",
                "level": level, "level_name": LEVELS[min(level, len(LEVELS) - 1)]}
    best_recent = max(g[1] for g in gens[-PLATEAU_GENS:])
    best_before = max(g[1] for g in gens[:-PLATEAU_GENS])
    improvement = best_recent - best_before
    plateaued = improvement < MIN_IMPROVEMENT
    if plateaued and level < len(LEVELS) - 1:
        return {"action": "advance", "why": f"best fitness improved only {improvement:+.2f} over the last "
                                            f"{PLATEAU_GENS} generations (below the {MIN_IMPROVEMENT} noise "
                                            f"floor) - the current level is exhausted",
                "level": level, "level_name": LEVELS[level], "next": LEVELS[level + 1]}
    return {"action": "hold", "why": f"improvement {improvement:+.2f} over the last {PLATEAU_GENS} "
                                     f"generations; still learning at {LEVELS[min(level, len(LEVELS) - 1)]}",
            "level": level, "level_name": LEVELS[min(level, len(LEVELS) - 1)]}


def advance(reason="manual"):
    d = load()
    if d.get("level", 0) >= len(LEVELS) - 1:
        print("already at the highest level")
        return 1
    d["history"].append({"ts": time.time(), "from": d.get("level", 0), "why": reason})
    d["level"] = d.get("level", 0) + 1
    save(d)
    print(f"difficulty -> {LEVELS[d['level']]} ({reason})")
    return 0


def main():
    a = sys.argv[1] if len(sys.argv) > 1 else "status"
    if a == "status":
        print(json.dumps(decide(), indent=1))
        return 0
    if a == "advance":
        return advance(sys.argv[2] if len(sys.argv) > 2 else "manual")
    if a == "reset":
        save({"level": 0, "history": [], "created": time.time()})
        print("curriculum reset to", LEVELS[0])
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
