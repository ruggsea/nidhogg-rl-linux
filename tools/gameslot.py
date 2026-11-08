"""gameslot.py — one owner at a time for the single physical game instance.

Measured problem: I spawned a `pi -p` subagent to study the menu cursor while I was also driving the
same game with my own key presses. Both wrote /tmp/nid_keys_0.txt, so every measurement either of us
made was corrupted - and I only discovered it after an hour of contradictory results.

There is exactly ONE game. Anything that presses keys, launches, kills, or reads the instance dump
must hold the slot. This is a file lock with a liveness check, so a crashed holder does not deadlock
the project.

    python3 tools/gameslot.py acquire "menu survey"      # or: --ttl 1800
    python3 tools/gameslot.py status
    python3 tools/gameslot.py release

Exit code 0 = you hold it, 1 = someone else does.
"""
import json
import os
import sys
import time

SLOT = os.path.join("state", "gameslot.json")


def _alive(pid):
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def read():
    try:
        with open(SLOT) as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def acquire(purpose, ttl=3600, holder=None):
    cur = read()
    now = time.time()
    if cur:
        stale = (not _alive(cur.get("pid", 0))) or (now - cur.get("ts", 0) > cur.get("ttl", 0))
        if not stale:
            print(f"BUSY: {cur.get('purpose')!r} held by pid {cur.get('pid')} "
                  f"for {int(now - cur.get('ts', now))}s")
            return 1
        print(f"taking over a stale slot from pid {cur.get('pid')} ({cur.get('purpose')!r})")
    os.makedirs("state", exist_ok=True)
    with open(SLOT, "w") as f:
        json.dump({"pid": os.getpid(), "purpose": purpose, "ts": now, "ttl": ttl,
                   "holder": holder or os.uname().nodename}, f)
    print(f"ACQUIRED: {purpose!r} (pid {os.getpid()}, ttl {ttl}s)")
    return 0


def release():
    cur = read()
    if not cur:
        print("no slot held")
        return 0
    if cur.get("pid") != os.getpid():
        print(f"slot held by pid {cur.get('pid')} ({cur.get('purpose')!r}); "
              f"not yours to release (use `force` if it is stale)")
        return 1
    os.remove(SLOT)
    print("released")
    return 0


def status():
    cur = read()
    if not cur:
        print("FREE")
        return 0
    age = int(time.time() - cur.get("ts", 0))
    live = _alive(cur.get("pid", 0))
    print(f"{'HELD' if live else 'STALE'} by pid {cur.get('pid')} for {age}s: {cur.get('purpose')!r}")
    return 0


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    a = sys.argv[1]
    if a == "acquire":
        purpose = sys.argv[2] if len(sys.argv) > 2 else "unspecified"
        ttl = 3600
        if "--ttl" in sys.argv:
            ttl = int(sys.argv[sys.argv.index("--ttl") + 1])
        return acquire(purpose, ttl)
    if a == "release":
        return release()
    if a == "status":
        return status()
    if a == "force":
        path = SLOT
        if os.path.exists(path):
            os.remove(path)
        print("slot force-cleared")
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
