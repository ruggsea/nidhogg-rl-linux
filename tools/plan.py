"""plan.py — a plan the agent actually works, with evidence required to close a step.

Why: the previous session had a 4000-line NOTES.md and no plan. Work was chosen by whatever felt
urgent, steps were re-opened after every compaction, and "done" never meant anything - the one number the
project exists for (`rounds_won`) sat at 0 for a full day while other things were polished.

Design:
  * `state/plan.json` is the single source of truth: ordered steps, each with an id, a title, an
    acceptance criterion, a status, and (when closed) the evidence that closed it.
  * `PLAN.md` is rendered from it, so the plan is visible in the repo and in an editor.
  * a step can only be closed with EVIDENCE: `plan.py done <id> --evidence <path-or-command>`. The
    evidence must exist (a file) or produce output (a command); the ledger records who closed it and
    when. No evidence, no closing - that is the whole point.
  * `next` prints exactly one step: the first that is open. The loop calls it each tick.

    python3 tools/plan.py show
    python3 tools/plan.py next
    python3 tools/plan.py start <id>
    python3 tools/plan.py done <id> --evidence "python3 tools/doctor.py --gate"
    python3 tools/plan.py block <id> --reason "..."
    python3 tools/plan.py add "title" --accept "how we know it is done"
"""
import argparse
import json
import os
import subprocess
import sys
import time

PLAN = os.path.join("state", "plan.json")
RENDER = "PLAN.md"
STATUS_ICON = {"open": "[ ]", "active": "[>]", "done": "[x]", "blocked": "[!]"}


def load():
    try:
        with open(PLAN) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {"created": time.time(), "steps": []}


def save(p):
    os.makedirs("state", exist_ok=True)
    with open(PLAN, "w") as f:
        json.dump(p, f, indent=1)
    render(p)


def render(p):
    lines = ["# PLAN", "", "Rendered from `state/plan.json` by `tools/plan.py`. Do not edit by hand.", ""]
    for s in p["steps"]:
        icon = STATUS_ICON.get(s["status"], "[?]")
        lines.append(f"- {icon} **{s['id']}** {s['title']}")
        lines.append(f"      accept: {s['accept']}")
        if s.get("evidence"):
            lines.append(f"      evidence: `{s['evidence']}`")
        if s.get("reason"):
            lines.append(f"      reason: {s['reason']}")
    done = sum(1 for s in p["steps"] if s["status"] == "done")
    lines.insert(2, f"\n{done}/{len(p['steps'])} steps done.\n")
    with open(RENDER, "w") as f:
        f.write("\n".join(lines) + "\n")


def evidence_ok(ev):
    """Evidence must be REAL: an existing file, or a command that runs and produces output."""
    if not ev:
        return False, "no evidence given"
    if os.path.exists(ev):
        return True, f"file exists ({os.path.getsize(ev)} bytes)"
    try:
        r = subprocess.run(ev, shell=True, capture_output=True, text=True, timeout=120)
    except subprocess.TimeoutExpired:
        return False, "evidence command timed out"
    if r.returncode != 0:
        return False, f"evidence command exited {r.returncode}: {(r.stdout + r.stderr)[:200]}"
    if not (r.stdout or r.stderr).strip():
        return False, "evidence command produced no output"
    return True, (r.stdout + r.stderr).strip()[:200]


def cmd_show(p):
    render(p)
    print(open(RENDER).read())
    return 0


def cmd_next(p):
    for s in p["steps"]:
        if s["status"] in ("open", "active"):
            print(json.dumps({"id": s["id"], "title": s["title"], "accept": s["accept"],
                              "status": s["status"]}, indent=1))
            return 0
    print("no open steps")
    return 0


def cmd_start(p, sid):
    for s in p["steps"]:
        if s["id"] == sid:
            s["status"] = "active"
            s["started"] = time.time()
            save(p)
            print(f"started {sid}: {s['title']}")
            return 0
    print(f"no step {sid}")
    return 1


def cmd_done(p, sid, ev):
    for s in p["steps"]:
        if s["id"] == sid:
            ok, why = evidence_ok(ev)
            print(f"evidence check: {'OK' if ok else 'REJECTED'} - {why}")
            if not ok:
                print("step NOT closed. A step needs evidence that exists or produces output.")
                return 1
            s["status"] = "done"
            s["evidence"] = ev
            s["closed"] = time.time()
            save(p)
            print(f"closed {sid}: {s['title']}")
            return 0
    print(f"no step {sid}")
    return 1


def cmd_block(p, sid, reason):
    for s in p["steps"]:
        if s["id"] == sid:
            s["status"] = "blocked"
            s["reason"] = reason
            save(p)
            print(f"blocked {sid}: {reason}")
            return 0
    print(f"no step {sid}")
    return 1


def cmd_add(p, title, accept):
    sid = f"{len(p['steps']) + 1:02d}"
    p["steps"].append({"id": sid, "title": title, "accept": accept, "status": "open"})
    save(p)
    print(f"added {sid}: {title}")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=["show", "next", "start", "done", "block", "add"])
    ap.add_argument("id", nargs="?")
    ap.add_argument("--evidence")
    ap.add_argument("--reason")
    ap.add_argument("--accept")
    a = ap.parse_args()
    p = load()
    if a.action == "show":
        return cmd_show(p)
    if a.action == "next":
        return cmd_next(p)
    if a.action == "start":
        return cmd_start(p, a.id)
    if a.action == "done":
        return cmd_done(p, a.id, a.evidence)
    if a.action == "block":
        return cmd_block(p, a.id, a.reason or "unspecified")
    if a.action == "add":
        return cmd_add(p, a.id, a.accept or "unspecified")
    return 2


if __name__ == "__main__":
    sys.exit(main())
