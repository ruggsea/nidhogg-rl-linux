"""doctor.py — always-on environment diagnostics, so failures are SEEN, not inferred.

Every serious time sink today was an invisible environmental condition:

  * the launcher forced `nice 19` + background QoS -> 30 fps instead of 120, which read as "the game
    is flaky and stalls";
  * a stale `/tmp/nid_room_<id>.txt` was consumed as a `room_goto` COMMAND, killing the game with
    "Game ended before loading first room";
  * hand launches did not start the hook's probe thread (missing NID_THREAD), so a diagnostic ran
    against a dead game and reported "could not find MULTIPLAYER";
  * the hook's key hold is measured in FRAMES, so a 30->120 fps change shrank holds from 200 ms to
    50 ms and menu presses silently stopped registering;
  * several game processes accumulated and competed.

This prints one block per check with PASS/WARN/FAIL and writes JSON to state/health.json so a trainer
or an agent can depend on it. It never modifies anything except its own output file.

A report that nothing consumes is decoration. `--gate` makes it refuse: exit non-zero on WARN or
FAIL, so a launcher or trainer can refuse to start. This is the difference between documenting a
landmine and defusing it.

    python3 tools/doctor.py            # human table
    python3 tools/doctor.py --json     # machine
    python3 tools/doctor.py --gate     # refuse: exit 1 unless overall=PASS
"""
import json
import os
import re
import subprocess
import sys
import time

HOOK_LOG = "/tmp/nid_inject_{}.log"
STATE = "/tmp/nid_state_{}.txt"
ROOM = "/tmp/nid_room_now_{}.txt"
INSTS = "/tmp/nid_insts_{}.txt"
KEYS = "/tmp/nid_keys_{}.txt"
ROOM_CMD = "/tmp/nid_room_{}.txt"          # DANGER: this is a command file
OUT = os.path.join("state", "health.json")


def sh(cmd):
    try:
        return subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10).stdout
    except Exception as e:
        return f"__error__{e}"


def game_pids():
    out = sh("ps ax -o pid,pri,nice,%cpu,command | grep '[N]idhogg.app/Contents/MacOS/Nidhogg'")
    rows = []
    for line in out.splitlines():
        parts = line.split(None, 4)
        if len(parts) == 5:
            rows.append({"pid": int(parts[0]), "pri": int(parts[1]), "nice": int(parts[2]),
                         "cpu": float(parts[3])})
    return rows


def fps(iid=0):
    """Frame rate from the hook's own counter."""
    path = HOOK_LOG.format(iid)
    try:
        with open(path, "rb") as f:
            f.seek(0, 2)
            f.seek(max(0, f.tell() - 8000))
            tail = f.read().decode("utf-8", "ignore")
    except OSError:
        return None
    fs = [int(m) for m in re.findall(r"f=(\d+)", tail)]
    if len(fs) < 2:
        return None
    # sample the counter twice, 1.5 s apart, for a real rate
    f0 = fs[-1]
    time.sleep(1.5)
    try:
        with open(path, "rb") as f:
            f.seek(0, 2)
            f.seek(max(0, f.tell() - 8000))
            tail2 = f.read().decode("utf-8", "ignore")
        fs2 = [int(m) for m in re.findall(r"f=(\d+)", tail2)]
    except OSError:
        return None
    if not fs2:
        return None
    return round((fs2[-1] - f0) / 1.5, 1)


def read_int(path):
    try:
        return int(open(path).read().strip())
    except (OSError, ValueError):
        return None


def file_age(path):
    try:
        return round(time.time() - os.path.getmtime(path), 1)
    except OSError:
        return None


def main():
    iid = 0
    checks = []
    pids = game_pids()

    def add(name, status, detail):
        checks.append({"check": name, "status": status, "detail": detail})

    add("game processes", "PASS" if len(pids) == 1 else ("WARN" if pids else "FAIL"),
        f"{len(pids)} running" + (f" pids={[p['pid'] for p in pids]}" if pids else ""))

    if pids:
        p = pids[0]
        bad_prio = p["nice"] >= 10 or p["pri"] < 20
        add("priority", "FAIL" if bad_prio else "PASS",
            f"nice={p['nice']} pri={p['pri']} cpu={p['cpu']}%" +
            (" - low priority throttles the engine (NID_NICE makes this optional)" if bad_prio else ""))

    f = fps(iid)
    add("frame rate", "FAIL" if (f is not None and f < 40) else ("PASS" if f else "WARN"),
        f"{f} fps" if f else "no frame counter in the hook log")

    room = read_int(ROOM.format(iid))
    try:
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        import train_state as TS
        rname = TS.InstanceManager.room_name(room) if room is not None else "?"
    except Exception:
        rname = "?"
    add("room", "PASS", f"{room} ({rname})")

    def fresh(path, limit):
        a = file_age(path)
        return a is not None and a < limit, a

    ok_s, a_s = fresh(STATE.format(iid), 2)
    add("state file", "PASS" if ok_s else "FAIL", f"age {a_s}s")
    ok_i, a_i = fresh(INSTS.format(iid), 3)
    add("instance dump", "PASS" if ok_i else "WARN", f"age {a_i}s")
    ok_h, a_h = fresh(HOOK_LOG.format(iid), 5)
    add("hook log", "PASS" if ok_h else "FAIL",
        f"age {a_h}s (a stale log means the probe thread is not running)")

    # LEGACY landmine. The hook now reads /tmp/nid_roomgoto_<id>.txt, so this old path is no longer
    # consumed as a command. It is still reported if present so an old build cannot be ignored, but
    # only a NON-EMPTY file matters (an empty file has nothing to execute).
    legacy = ROOM_CMD.format(iid)
    if os.path.exists(legacy) and os.path.getsize(legacy) > 0:
        add("legacy room command", "WARN",
            f"{legacy} is non-empty - an OLD hook build would execute this as room_goto")
    else:
        add("legacy room command", "PASS", "absent or empty (hook now uses nid_roomgoto)")

    stale_keys = file_age(KEYS.format(iid))
    add("keys file", "PASS", f"age {stale_keys}s" if stale_keys is not None else "absent")

    worst = "PASS"
    for c in checks:
        if c["status"] == "FAIL":
            worst = "FAIL"
            break
        if c["status"] == "WARN":
            worst = "WARN"

    if "--json" in sys.argv:
        print(json.dumps({"overall": worst, "checks": checks}, indent=1))
    else:
        icons = {"PASS": "ok  ", "WARN": "WARN", "FAIL": "FAIL"}
        print(f"doctor  overall={worst}")
        for c in checks:
            print(f"  [{icons[c['status']]}] {c['check']:20s} {c['detail']}")

    os.makedirs("state", exist_ok=True)
    with open(OUT, "w") as fh:
        json.dump({"ts": time.time(), "overall": worst, "checks": checks}, fh, indent=1)
    if "--gate" in sys.argv:
        return 0 if worst == "PASS" else 1
    return 0 if worst != "FAIL" else 1


if __name__ == "__main__":
    sys.exit(main())
