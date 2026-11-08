"""agents.py — session management so an agent can run, watch and collect its own subagents.

Gap this closes: the harness could START an agent (`bin/restart-agent.sh`) but had no way for a running
agent to see its own sessions, spawn a helper, message it, or read what it produced. That is why this
project's one attempt at parallelism went wrong: a `pi -p` subagent was spawned with `nohup` while the
parent was driving the same game, both wrote /tmp/nid_keys_0.txt, and an hour of measurements were
corrupted before anyone noticed.

Affordances provided:

  list                       every agent session with model, age, context and status
  spawn <name> <task-file>   start a subagent in its own tmux session; optionally lease the game slot
                             add --persona <file> to APPEND a project-local persona (e.g.
                             .pi/agents/goldfish.md). Personas live in this repo, never in the pi
                             install: the project must not modify the user's global agent set.
  send <name> <text>         give a running agent an instruction
  tail <name> [n]            last n lines of its pane, i.e. what it is actually doing
  wait <name> [secs]         block until it finishes (or the timeout expires)
  stop <name>                kill a stuck agent
  cost                       per-session token/context line if the pane shows one

Design points that matter, learned the hard way here:
  * a subagent that touches the GAME must lease the slot first (`spawn --game`), otherwise it collides
    with the parent's keypresses;
  * results must go to a FILE, not to prose in a pane, so the parent can consume them mechanically:
    every spawn gets a results path and the task file is told to write there;
  * `tail` exists so a supervisor reads what the child is DOING rather than waiting for a summary.

    python3 tools/agents.py list
    python3 tools/agents.py spawn audit1 /tmp/task_audit.md --game
    python3 tools/agents.py tail audit1
    python3 tools/agents.py wait audit1 600
    python3 tools/agents.py stop audit1
"""
import json
import os
import subprocess
import sys
import time

PREFIX = "nid-agent-"
REGISTRY = os.path.join("state", "agents.json")
MODEL = os.environ.get("NID_AGENT_MODEL", "deepseek-v4-pro")
PROVIDER = os.environ.get("NID_AGENT_PROVIDER", "deepseek")


def sh(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True).stdout


def sessions():
    """All agent sessions: any tmux session whose name starts with 'nid'.

    Deliberately loose. The main session is 'nidhogg-agent' while subagents are spawned as
    'nid-agent-<name>'; an earlier version only recognised the latter and reported "no agent
    sessions running" while the main agent was sitting right there.
    """
    out = {}
    for line in sh("tmux ls 2>/dev/null").splitlines():
        name = line.split(":")[0]
        if not name.startswith("nid"):
            continue
        short = name[len(PREFIX):] if name.startswith(PREFIX) else name
        out[short] = line
    return out


def tname(short):
    """Actual tmux session name for a short name reported by sessions()."""
    live = sessions()
    return live and (PREFIX + short if (PREFIX + short) in [l.split(":")[0] for l in live.values()] else short) or short


def reg_load():
    try:
        with open(REGISTRY) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def reg_save(r):
    os.makedirs("state", exist_ok=True)
    with open(REGISTRY, "w") as f:
        json.dump(r, f, indent=1)


def pane(name):
    if name in ("nidhogg-agent", "main"):
        return sh("tmux capture-pane -p -t nidhogg-agent 2>/dev/null")
    return sh(f"tmux capture-pane -p -t {PREFIX}{name} 2>/dev/null")


def status_of(name):
    p = pane(name)
    if not p:
        return "dead"
    tail = [l for l in p.splitlines() if l.strip()][-3:]
    joined = " ".join(tail)
    if "Working" in joined or "⠏" in joined or "⠋" in joined or "⠙" in joined:
        return "working"
    if ">" in p.splitlines()[-3:][0] if len(p.splitlines()) > 3 else False:
        return "idle"
    return "unknown"


def cost_line(name):
    for line in reversed(pane(name).splitlines()):
        if "DeepSeek" in line or "k/" in line or "◫" in line:
            return line.strip()
    return ""


def cmd_list():
    live = sessions()
    reg = reg_load()
    if not live:
        print("no agent sessions running")
        return 0
    print(f"{'name':12s} {'status':8s} {'age':8s} task")
    for name in live:
        r = reg.get(name, {})
        age = int(time.time() - r.get("ts", time.time()))
        print(f"{name:12s} {status_of(name):8s} {age:6d}s  {r.get('purpose', '?')}")
        c = cost_line(name)
        if c:
            print(f"{'':12s} {c}")
    return 0


def cmd_spawn(name, taskfile, game=False, ttl=3600, persona=None):
    if name in sessions():
        print(f"session {name} already exists")
        return 1
    task = open(taskfile).read()
    results = os.path.abspath(os.path.join("state", f"agent_{name}_result.md"))
    note = f"\n\n---\nWrite your FINAL ANSWER as a file at: {results}\n" \
           f"That file is the deliverable; the supervisor reads it mechanically and will not read " \
           f"this conversation. Be terse and factual in it.\n"
    prompt_path = f"/tmp/task_{name}.md"
    with open(prompt_path, "w") as f:
        f.write(task + note)

    pre = ""
    if game:
        slot = subprocess.run([sys.executable, "tools/gameslot.py", "acquire",
                               f"subagent:{name}", "--ttl", str(ttl)],
                              capture_output=True, text=True)
        print(slot.stdout.strip())
        if slot.returncode != 0:
            print("refusing to spawn a game-touching agent while the slot is held by someone else")
            return 1
        pre = f"echo 'GAME SLOT LEASED TO YOU. Release it when done: python3 tools/gameslot.py release'; "

    persona_arg = ""
    if persona:
        ppath = os.path.abspath(persona)
        if not os.path.exists(ppath):
            print(f"no persona file {ppath}")
            return 1
        # project-local persona, appended to the system prompt; nothing installed globally
        persona_arg = f"--append-system-prompt '{ppath}' "

    inner = (f"cd '{os.getcwd()}' && {pre}pi --provider {PROVIDER} --model {MODEL} "
             f"{persona_arg}-p < {prompt_path}")
    sh(f"tmux new -d -s {PREFIX}{name} \"{inner}\"")
    reg = reg_load()
    reg[name] = {"purpose": task.strip().splitlines()[0][:120], "ts": time.time(),
                 "task": prompt_path, "results": results, "game": game}
    reg_save(reg)
    print(f"spawned {name} (model {PROVIDER}/{MODEL})")
    print(f"  task:    {prompt_path}")
    print(f"  results: {results}")
    return 0


def cmd_send(name, text):
    if name not in sessions():
        print(f"no session {name}")
        return 1
    sh(f"tmux send-keys -t {PREFIX}{name} {json.dumps(text)} Enter")
    print(f"sent to {name}")
    return 0


def cmd_tail(name, n=25):
    p = pane(name)
    if not p:
        print(f"no session {name}")
        return 1
    lines = [l for l in p.splitlines()]
    print("\n".join(lines[-n:]))
    return 0


def cmd_wait(name, secs=600):
    t0 = time.time()
    while time.time() - t0 < secs:
        if name not in sessions():
            r = reg_load().get(name, {})
            print(f"{name} finished after {int(time.time() - t0)}s")
            res = r.get("results")
            if res and os.path.exists(res):
                print(f"--- {res} ---")
                print(open(res).read()[:4000])
            return 0
        time.sleep(3)
    print(f"{name} still running after {secs}s (use `tail {name}`)")
    return 1


def cmd_stop(name):
    if name not in sessions():
        print(f"no session {name}")
        return 1
    sh(f"tmux kill-session -t {PREFIX}{name}")
    r = reg_load().get(name, {})
    if r.get("game"):
        subprocess.run([sys.executable, "tools/gameslot.py", "force"], capture_output=True)
        print("game slot cleared")
    print(f"stopped {name}")
    return 0


def cmd_cost():
    for name in sessions():
        print(f"{name}: {cost_line(name) or 'no cost line visible'}")
    return 0


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    a = sys.argv[1]
    if a == "list":
        return cmd_list()
    if a == "spawn":
        name, task = sys.argv[2], sys.argv[3]
        return cmd_spawn(name, task, game="--game" in sys.argv,
                         ttl=int(sys.argv[sys.argv.index("--ttl") + 1]) if "--ttl" in sys.argv else 3600,
                         persona=sys.argv[sys.argv.index("--persona") + 1] if "--persona" in sys.argv else None)
    if a == "send":
        return cmd_send(sys.argv[2], sys.argv[3])
    if a == "tail":
        return cmd_tail(sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 25)
    if a == "wait":
        return cmd_wait(sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 600)
    if a == "stop":
        return cmd_stop(sys.argv[2])
    if a == "cost":
        return cmd_cost()
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
