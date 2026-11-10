#!/usr/bin/env python3
"""supervise.py — keep the worker pool honest without a human in the loop.

Runs every pass and fixes the four things that actually kill throughput, in order of how often they bit:

 1. **Idle workers.** Measured repeatedly: seven workers sitting at a prompt with 400–600k of context
    while nothing progressed. Idle > IDLE_MIN gets a concrete kick, not a vague one.
 2. **Context bloat.** pi has no CLI compact, so compaction is a restart. Over CTX_MAX and idle ->
    restart (files carry the state; see loop/driver_prompt.md).
 3. **No game running.** A lane that needs a game and finds none burns its tick on process checks.
 4. **Sloppy records.** Under a weaker model the corroboration fields start disappearing from round
    entries. A round entry without them is noise, and noise is what produced six retracted results.

Every pass appends one line to loop/supervise.log so the trend is auditable afterwards.

    python3 tools/supervise.py --once      # one pass, print what it did
    python3 tools/supervise.py             # daemon: one pass every INTERVAL seconds
"""
import json
import os
import re
import subprocess
import sys
import time

REPO = os.path.expanduser("~/nidhogg-pau")
STATE = os.path.join(REPO, "state")
LOG = os.path.join(REPO, "loop", "supervise.log")
INTERVAL = 300
IDLE_MIN = 6            # minutes idle before a kick
CTX_MAX = 120_000       # tokens before a restart when idle
KICK = ("Continue your assigned lane from docs/PLAN_SWARM.md. One concrete experiment, write the "
        "full structural record (all corroboration fields), claim.py with cmd+falsifier, then end "
        "your turn so the loop can re-prompt you.")


def sh(cmd, timeout=30):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout + r.stderr
    except subprocess.TimeoutExpired:
        return 124, "timeout"


def pane(sess, scroll=0):
    rc, out = sh(f"tmux capture-pane -p -S -{scroll} -t {sess} 2>/dev/null")
    return re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", out) if rc == 0 else ""


def workers():
    try:
        d = json.load(open(os.path.join(STATE, "workers.json")))
    except (OSError, ValueError):
        return {}
    return d.get("workers", {})


def ctx_tokens(txt):
    m = re.findall(r"(\d+(?:\.\d+)?)k/(\d+(?:\.\d+)?)M", txt)
    return int(float(m[-1][0]) * 1000) if m else 0


def is_busy(txt):
    return bool(re.search(r"[⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏]\s*(Working|Thinking)", txt))


def claim_quality(minutes=45):
    """Fraction of recent round entries that carry corroboration. This is the leading indicator of a
    weak model producing plausible nonsense."""
    cutoff = time.time() - minutes * 60
    good = bad = 0
    try:
        for line in open(os.path.join(STATE, "rounds.jsonl"), errors="ignore"):
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if float(r.get("ts") or 0) < cutoff:
                continue
            if r.get("kind") != "round":
                continue
            if (r.get("corroborated") is True or r.get("both_fighters_reset") is True
                    or r.get("winner_screen") is True or r.get("ready_wall") is True):
                good += 1
            else:
                bad += 1
    except OSError:
        pass
    return good, bad


def games():
    rc, out = sh("pgrep -c -x Nidhogg.exe 2>/dev/null || true")
    try:
        return int((out or "0").strip().splitlines()[0])
    except (ValueError, IndexError):
        return 0


def ensure_games(n=3):
    """Start instances if the farm is empty. Uses Pau's launcher, one per lane farm."""
    started = []
    for suffix in ("a", "b", "c")[:max(0, n - games())]:
        farm = os.path.expanduser(f"~/.nidfarm-{suffix}")
        if os.path.isdir(farm):
            continue
        cmd = (f"cd ~/pau-tree && NIDFARM={farm} NID_GAME_DIR=$HOME/nidfarm/game "
               f"NID_PROTON=$HOME/.local/opt/GE-Proton11-12-x86_64/proton "
               f"nohup python3 -c 'import nidlinux as n; n.start_ids([0])' "
               f"> {farm}.log 2>&1 &")
        sh(cmd)
        started.append(suffix)
    return started


def one_pass(verbose=True):
    acts = []
    w = workers()
    for i in sorted(w, key=int):
        sess = f"nid-w{i}"
        rc, _ = sh(f"tmux has-session -t {sess} 2>/dev/null")
        if rc != 0:
            acts.append(f"w{i}: dead")
            continue
        txt = pane(sess, 30)
        ctx = ctx_tokens(pane(sess, 6))
        busy = is_busy(txt)
        if busy:
            continue
        # idle: how long? use the log's last kick as a proxy to avoid kicking every pass
        marker = os.path.join(STATE, f".kick_w{i}")
        last = os.path.getmtime(marker) if os.path.exists(marker) else 0
        if ctx >= CTX_MAX:
            sh(f"tmux kill-session -t {sess}")           # keeper/reap will respawn fresh
            acts.append(f"w{i}: compacts {ctx//1000}k -> restarted")
            open(marker, "w").close()
        elif time.time() - last > IDLE_MIN * 60:
            sh(f'tmux send-keys -t {sess} "{KICK}" Enter')
            open(marker, "w").close()
            acts.append(f"w{i}: idle {ctx//1000}k -> kicked")

    g = games()
    if g == 0:
        started = ensure_games(3)
        acts.append(f"games=0 -> started {started or 'nothing (farms exist, check logs)'}")

    good, bad = claim_quality()
    line = (f"{time.strftime('%H:%M:%S')} games={g} workers={len(w)} "
            f"round-records good={good} bad={bad} acts={len(acts)} "
            f"{'; '.join(acts) if acts else 'steady'}")
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    with open(LOG, "a") as f:
        f.write(line + "\n")
    if verbose:
        print(line)
    return acts


def main():
    if "--once" in sys.argv:
        one_pass()
        return 0
    while True:
        try:
            one_pass()
        except Exception as e:                     # never let the supervisor die
            with open(LOG, "a") as f:
                f.write(f"{time.strftime('%H:%M:%S')} supervisor error: {e}\n")
        time.sleep(INTERVAL)


if __name__ == "__main__":
    sys.exit(main())
