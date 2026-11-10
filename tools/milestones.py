#!/usr/bin/env python3
"""milestones.py — email ONLY for milestones that matter, never for routine activity.

Why this replaces the old rule: check_progress.sh emailed whenever ANY counter moved, so every routine
claim (a threshold tweak, a detector fix) produced an email. That is noise: the inbox filled with
"claims: 16 -> 17" while nothing changed about whether the agent can play the game.

What counts as a milestone — i.e. what a person would want to be woken for:
  step_closed:<id>    a plan step closed WITH evidence (each new step id once)
  attest_streak3      the first honest 3-consecutive attestation (step 01's bar)
  first_generation    the first completed generation of evolution
  first_round         the first observed round transition
  first_win           the first verified round win
  pool_down           no workers alive (hard failure: nothing is progressing)
  stall               no plan step closed for STALL_HOURS while workers exist

Everything else is silent and merely appended to state/progress_history.jsonl for audit.

    python3 tools/milestones.py            # human output
    python3 tools/milestones.py --json     # {"new": [...], "body": "..."} for the mailer
"""
import json
import os
import sys
import time

STATE = "state"
FIRED = os.path.join(STATE, "milestones_fired.json")
HISTORY = os.path.join(STATE, "progress_history.jsonl")
STALL_HOURS = 6.0


def load_json(path, default):
    try:
        return json.load(open(path))
    except (OSError, ValueError):
        return default


def load_jsonl(path):
    out = []
    try:
        for line in open(path, errors="ignore"):
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except ValueError:
                continue
    except OSError:
        pass
    return out


def snapshot():
    plan = load_json(os.path.join(STATE, "plan.json"), {"steps": []})
    done = [(s.get("id"), s.get("title", "")) for s in plan.get("steps", []) if s.get("status") == "done"]
    from verified import counts as _vcounts
    _vc = _vcounts(os.path.join(STATE, "rounds.jsonl"))
    rounds = [None] * _vc["rounds"]  # only the count is used below
    wins = [None] * _vc["wins"]
    decided = _vc["decided"]
    runs = load_jsonl(os.path.join(STATE, "attest_runs.log"))
    streak = best = 0
    for r in runs:
        ok = r.get("ok") or {}
        good = (str(r.get("verdict", "")).startswith("ATTESTED")
                and ok.get("dose_response") and ok.get("running") and ok.get("opponent"))
        streak = streak + 1 if good else 0
        best = max(best, streak)
    # MEASURED false milestone (2026-11-09): "3 completed generations" fired from
    # /tmp/pau_train*.log last written Nov 8 18:29 - a day old, from the pre-fix harness. Only logs
    # newer than the curriculum epoch count.
    try:
        epoch = float(open(os.path.join(STATE, "curriculum_epoch")).read().strip())
    except (OSError, ValueError):
        epoch = 0.0
    gens = 0
    if os.path.isdir("/tmp"):
        for name in os.listdir("/tmp"):
            if not (name.startswith("pau_train") and name.endswith(".log")):
                continue
            path = os.path.join("/tmp", name)
            try:
                if os.path.getmtime(path) < epoch:
                    continue
                gens = max(gens, open(path, errors="ignore").read().count("== gen "))
            except OSError:
                pass
    # worker liveness, read from the elastic pool's own state
    workers = load_json(os.path.join(STATE, "workers.json"), {"workers": {}})
    import subprocess
    alive = 0
    if not workers.get("workers"):
        alive = -1                              # no pool configured / state not readable here
    else:
        for i in workers.get("workers", {}):
            r = subprocess.run(["tmux", "has-session", "-t", f"nid-w{i}"], capture_output=True)
            if r.returncode == 0:
                alive += 1
    return {"done": done, "best_streak": best, "generations": gens,
            "rounds": len(rounds), "wins": len(wins), "decided": decided, "workers_alive": alive}


def candidates(snap, last_progress_ts):
    out = {}
    for sid, title in snap["done"]:
        out[f"step_closed:{sid}"] = f"plan step {sid} closed with evidence: {title[:80]}"
    if snap["best_streak"] >= 3:
        out["attest_streak3"] = f"{snap['best_streak']} consecutive full-criterion attestations"
    if snap["generations"] >= 1:
        out["first_generation"] = f"{snap['generations']} completed generation(s)"
    if snap["rounds"] >= 1:
        out["first_round"] = f"{snap['rounds']} round transition(s) observed"
    if snap["wins"] >= 1:
        out["first_win"] = f"{snap['wins']} verified round win(s)"
    # A win RATE only exists above 10 rounds, and it is the number a person actually cares about. Fires
    # once, when it first becomes measurable - not on every increment (that would be counter noise).
    decided = snap.get("decided", 0)
    if decided >= 10:
        rate = 100.0 * snap["wins"] / decided
        out["winrate_measured"] = (f"first measured win rate: {snap['wins']}/{decided} = {rate:.0f}% "
                                   f"(opponent inert unless stated otherwise)")
    if snap["workers_alive"] < 0:
        pass                                    # could not determine - never fire on ignorance
    elif snap["workers_alive"] == 0:
        out["pool_down"] = "no workers alive - nothing is progressing"
    elif last_progress_ts and (time.time() - last_progress_ts) > STALL_HOURS * 3600:
        hrs = (time.time() - last_progress_ts) / 3600
        out["stall"] = f"no plan step closed in {hrs:.1f}h with {snap['workers_alive']} worker(s) alive"
    return out


def main():
    os.makedirs(STATE, exist_ok=True)
    fired = load_json(FIRED, {})
    snap = snapshot()

    # when was the last step closed (for the stall rule)?
    closed_ts = max([fired.get(f"step_closed:{sid}", {}).get("ts", 0) for sid, _ in snap["done"]] or [0])
    last_progress = closed_ts or load_json(os.path.join(STATE, "milestone_epoch.json"), {}).get("ts", time.time())

    cands = candidates(snap, last_progress)
    new = {k: v for k, v in cands.items() if k not in fired}

    # record what happened for audit even when nothing is emailed
    with open(HISTORY, "a") as f:
        f.write(json.dumps({"ts": time.time(), "snapshot": snap, "new": list(new)}) + "\n")

    if new:
        now = time.time()
        for k in new:
            fired[k] = {"ts": now, "text": new[k]}
        json.dump(fired, open(FIRED, "w"), indent=1)

    if "--seed" in sys.argv:
        now = time.time()
        for k, v in cands.items():
            fired.setdefault(k, {"ts": now, "text": v, "seeded": True})
        json.dump(fired, open(FIRED, "w"), indent=1)
        print(f"seeded {len(cands)} existing milestone(s); future ones will email")
        return 0

    body = []
    if new:
        body.append("MILESTONE(S) REACHED")
        for k, v in new.items():
            body.append(f"  * {v}")
        body.append("")
    body.append("state now:")
    body.append(f"  plan        : {len(snap['done'])} step(s) closed with evidence")
    body.append(f"  attestation : best full-criterion streak {snap['best_streak']}")
    body.append(f"  generations : {snap['generations']}")
    body.append(f"  rounds      : {snap['rounds']} observed, {snap['wins']} won")
    body.append(f"  workers     : {snap['workers_alive']} alive")
    body.append("")
    from verified import win_rate as _wrate
    _wr = _wrate(os.path.join(STATE, "rounds.jsonl"))
    if _wr is None:
        body.append("No win rate is claimed until 10+ decided rounds exist.")
    else:
        body.append(f"Win rate: {_wr:.0f}% over {snap['decided']} decided rounds "
                    f"(opponent inert unless a lane says otherwise).")
    text = "\n".join(body)

    if "--json" in sys.argv:
        print(json.dumps({"new": list(new), "body": text}, indent=1))
    else:
        print(text if new else "no milestone")
        if new:
            print("\n" + text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
