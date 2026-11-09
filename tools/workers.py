#!/usr/bin/env python3
"""workers.py — elastic, parallel, self-looping workers on artemis.

One worker is one pi TUI in its own tmux session, armed with pi's `loop` tool. This manager reconciles
"how many workers should exist" with "how many exist", so scaling is a number you set, not a thing you
type carefully. It is pure scaling of the current system: same driver prompt, same tick message, same
plan/claims, same rules — just N of them, each with its own session and role.

WHY ELASTIC
    Exploration (menu entry, round detection, attestation variants) parallelises: several workers probe
    different hypotheses at once and the answer arrives in one round-trip instead of N ticks.
    Training does not parallelise this way: it wants ONE stable policy runner. So the target is a dial:
    `workers.py scale 3` while searching, `workers.py scale 1` once training starts.

COMPACTION
    pi has no CLI compact flag, and a slash command sent over tmux is treated as a chat message (measured).
    So a worker is compacted by RESTARTING it: fresh context, same files. State lives in
    loop/PI_TICKLOG.md, state/plan.json, state/claims.jsonl and the workers' own role files, so nothing
    is lost but the transcript. `reap` does this automatically when a pane reports a large context.

WRITE SAFETY
    Two workers editing state/plan.json at once would clobber each other. Claims are append-only (safe),
    ticklogs are per-worker, and plan edits go through `state/plan.lock` — only one worker closes a step
    at a time.

    python3 tools/workers.py scale 3          # grow to 3 (roles assigned round-robin)
    python3 tools/workers.py scale 1          # shrink to 1, keeps w1
    python3 tools/workers.py status           # who exists, context size, busy or idle
    python3 tools/workers.py reap             # restart dead/over-context workers
    python3 tools/workers.py assign 2 entry   # give worker 2 a focus
    python3 tools/workers.py tick             # send one manual tick to every idle worker
    python3 tools/workers.py down             # stop everything
"""
import json
import os
import re
import subprocess
import sys
import time

REPO = os.path.expanduser("~/nidhogg-pau")
STATE = os.path.join(REPO, "state")
WFILE = os.path.join(STATE, "workers.json")
SESS_PREFIX = "nid-w"
MAX_WORKERS = 5
CTX_COMPACT = 150_000          # restart a worker above this many context tokens
ROLES = ["engineer", "prober", "auditor", "engineer", "prober"]
# Thinking is per role, not global: judgement work (closing steps, auditing claims) is worth the
# wall-clock of high; routine probing is not. Measured complaint that motivated the dial: think:off made
# the agent ramble, think:high on everything made each turn slow.
THINKING = {"engineer": "high", "prober": "medium", "auditor": "high"}
PROVIDER = "deepseek"
MODEL = "deepseek-v4-pro"


def sh(cmd, timeout=60):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout + r.stderr
    except subprocess.TimeoutExpired:
        return 124, "timeout"


def load():
    try:
        return json.load(open(WFILE))
    except (OSError, ValueError):
        return {"workers": {}, "target": 1, "created": time.time()}


def save(d):
    os.makedirs(STATE, exist_ok=True)
    json.dump(d, open(WFILE, "w"), indent=1)


def exists(sess):
    rc, _ = sh(f"tmux has-session -t {sess} 2>/dev/null")
    return rc == 0


def pane(sess, scroll=0):
    rc, out = sh(f"tmux capture-pane -p -S -{scroll} -t {sess} 2>/dev/null")
    return re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", out) if rc == 0 else ""


def context_tokens(sess):
    """Read the context counter out of the worker's status line, e.g. '◫ 144k/1.0M'."""
    m = None
    for m2 in re.finditer(r"(\d+(?:\.\d+)?)k/(\d+(?:\.\d+)?)M", pane(sess, 40)):
        m = m2
    if not m:
        return 0
    return int(float(m.group(1)) * 1000)


def busy(sess):
    """A worker is busy if its status line shows the spinner word rather than the idle prompt."""
    tail = pane(sess, 6)
    return bool(re.search(r"[⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏]\s*(Working|Thinking)", tail))


def spawn(i, role):
    sess = f"{SESS_PREFIX}{i}"
    if exists(sess):
        sh(f"tmux kill-session -t {sess}")
        time.sleep(1)
    thinking = THINKING.get(role, "medium")
    cmd = (f'pi --provider {PROVIDER} --model {MODEL} --thinking {thinking} '
           f'--append-system-prompt loop/driver_prompt.md')
    rc, out = sh(f'cd {REPO} && tmux new -d -s {sess} -c {REPO} "{cmd}"')
    if rc != 0:
        return False, f"tmux new failed: {out.strip()}"
    # wait for the TUI to be ready before typing, or the arming message is swallowed (measured: a
    # worker restarted with 0/1.0M context and never received it)
    for _ in range(40):
        time.sleep(1)
        if re.search(r"deepseek-v4-pro|Working|>", pane(sess, 10)):
            break
    arm(sess, i, role)
    return True, "started"


def arm(sess, i, role):
    msg = (f"You are worker {i} (role: {role}) of the nidhogg loop on artemis. "
           f"Arm pi's self-loop: call the loop tool with action=start, minutes=5, "
           f"untilFile={REPO}/loop/VERDICT.md, message = exact contents of loop/self_tick.md. "
           f"Then read loop/roles/{role}.md for your focus, python3 tools/plan.py next, and start working.")
    sh(f"tmux send-keys -t {sess} {json.dumps(msg)} Enter")


def stop(i):
    sess = f"{SESS_PREFIX}{i}"
    sh(f"tmux kill-session -t {sess}")
    return True


def status():
    d = load()
    rows = []
    for i in sorted(d.get("workers", {}), key=int):
        w = d["workers"][i]
        sess = f"{SESS_PREFIX}{i}"
        alive = exists(sess)
        rows.append({
            "id": int(i), "role": w.get("role"), "session": sess, "alive": alive,
            "context_k": round(context_tokens(sess) / 1000, 1) if alive else None,
            "busy": busy(sess) if alive else None,
            "started": w.get("started"),
        })
    return {"target": d.get("target"), "workers": rows}


def scale(n):
    n = max(0, min(int(n), MAX_WORKERS))
    d = load()
    d["workers"] = d.get("workers") or {}
    have = {int(k) for k, v in d["workers"].items() if exists(f"{SESS_PREFIX}{k}")}
    # grow
    for i in range(1, n + 1):
        if i not in have:
            role = ROLES[(i - 1) % len(ROLES)]
            ok, msg = spawn(i, role)
            if ok:
                d["workers"][str(i)] = {"role": role, "started": time.time()}
            else:
                print(f"w{i}: FAILED {msg}")
    # shrink (highest ids first, never the last one if n>0)
    for i in sorted(have, reverse=True):
        if i > n:
            stop(i)
            d["workers"].pop(str(i), None)
    d["target"] = n
    save(d)
    return status()


def reap():
    """Restart workers that died or whose context is too large (compaction)."""
    d = load()
    actions = []
    for i in list(d.get("workers", {})):
        sess = f"{SESS_PREFIX}{i}"
        if not exists(sess):
            role = d["workers"][i].get("role", "engineer")
            ok, msg = spawn(int(i), role)
            actions.append(f"w{i}: dead -> {msg}")
            continue
        ctx = context_tokens(sess)
        if ctx >= CTX_COMPACT and not busy(sess):
            role = d["workers"][i].get("role", "engineer")
            sh(f"tmux kill-session -t {sess}")
            ok, msg = spawn(int(i), role)
            actions.append(f"w{i}: compacted at {ctx // 1000}k -> restarted")
    save(d)
    return actions or ["nothing to reap"]


def tick_all():
    d = load()
    sent = []
    for i in d.get("workers", {}):
        sess = f"{SESS_PREFIX}{i}"
        if exists(sess) and not busy(sess):
            sh(f'tmux send-keys -t {sess} "{" ".join(sys.argv[2:]) or "Continue: one step, then end your turn."}" Enter')
            sent.append(f"w{i}")
    return sent or ["no idle workers"]


def main():
    a = sys.argv[1] if len(sys.argv) > 1 else "status"
    if a == "status":
        print(json.dumps(status(), indent=1))
    elif a == "scale":
        print(json.dumps(scale(sys.argv[2] if len(sys.argv) > 2 else 1), indent=1))
    elif a == "down":
        print(json.dumps(scale(0), indent=1))
    elif a == "reap":
        print("\n".join(reap()))
    elif a == "tick":
        print("ticked: " + ", ".join(tick_all()))
    elif a == "assign":
        i, role = sys.argv[2], sys.argv[3]
        d = load()
        d.setdefault("workers", {}).setdefault(i, {})["role"] = role
        save(d)
        sh(f'tmux send-keys -t {SESS_PREFIX}{i} "Your role is now {role}. Read loop/roles/{role}.md and switch focus." Enter')
        print(f"w{i} -> {role}")
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
