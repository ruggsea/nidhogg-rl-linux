#!/usr/bin/env python3
"""flag_test.py — test one -net* flag combo for a drivable fighter + live CPU opponent.

Launches a FRESH instance on :100 (prefixes/2) with the given flag string, then
monitors frame brightness every ~8s and runs the bind + opponent-sustained check at the
match window (~45-75s post-boot, per the earlier -netai measurement). Logs to
state/probes/flag_test.jsonl. Robust to procs.json flapping via the _disp fallback.

Measurement bar (engineer): find_fighter binds a REAL fighter AND
opponent_moves_sustained (two 6s windows, both >=8px).

    python3 tools/flag_test.py "-netlevel training -netai -netpersonality brawler -netdiff 3"
"""
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import nid_linux as n
import linux_state as ls

IID = 1
DISP = ":100"
PREFIX = Path.home() / "nidfarm" / "prefixes" / "2"
GAME = Path.home() / "nidfarm" / "game" / "Nidhogg.exe"
PROTON = Path.home() / ".local/opt/GE-Proton11-12-x86_64/proton"
SPY = Path.home() / "nidhogg-pau" / "spy" / "nidspy.so"
STEAM_ROOT = Path.home() / "fake_steam"
LOGDIR = Path.home() / "nidlogs"
OUT = Path.home() / "nidhogg-pau" / "state" / "probes" / "flag_test.jsonl"
ONLINE = PREFIX / "pfx" / "drive_c" / "users" / "steamuser" / "AppData" / "Roaming" / "Nidhogg" / "online.log"

ls.IID = IID


def log(obj):
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "a") as f:
        f.write(json.dumps(obj) + "\n")
    print(json.dumps(obj), flush=True)


def stop_lane():
    for d in Path("/proc").iterdir():
        if not d.name.isdigit():
            continue
        try:
            comm = (d / "comm").read_text().strip()
            env = (d / "environ").read_bytes()
        except OSError:
            continue
        if comm == "Nidhogg.exe" and b"DISPLAY=:100" in env.split(b"\0"):
            try:
                os.kill(int(d.name), signal.SIGKILL)
            except OSError:
                pass
        if b"STEAM_COMPAT_DATA_PATH=" + str(PREFIX).encode() in env:
            try:
                os.kill(int(d.name), signal.SIGKILL)
            except OSError:
                pass
    time.sleep(2)


def launch(flag):
    stop_lane()
    logfile = (LOGDIR / f"flagtest_{flag.replace(' ', '_').lstrip('-')}.log").open("ab")
    env = dict(os.environ)
    env.pop("WAYLAND_DISPLAY", None)
    env.update(DISPLAY=DISP,
               STEAM_COMPAT_CLIENT_INSTALL_PATH=str(STEAM_ROOT),
               STEAM_COMPAT_DATA_PATH=str(PREFIX),
               SteamAppId="94400", SteamGameId="94400",
               WINEDEBUG="-all", LD_PRELOAD=str(SPY))
    args = [str(PROTON), "waitforexitandrun", str(GAME)] + flag.split()
    subprocess.Popen(args, env=env, stdout=logfile, stderr=logfile, start_new_session=True)
    # ensure the display mapping survives procs.json flapping (fallback now in _disp)


def wait_boot(timeout=150):
    t0 = time.time()
    while time.time() - t0 < timeout:
        pid = n._game_pid(IID)
        if pid and n.ping(pid) == f"pong {pid}":
            return pid
        time.sleep(2)
    return None


def frame_bright():
    f = n.frame(IID, "/tmp/nid_rugg/ft.png")
    if f is None:
        return None
    a = f.astype(int)
    r, g, b = a[:, :, 0], a[:, :, 1], a[:, :, 2]
    return {"mean": round(float(a.mean()), 1),
            "white": int(((r > 235) & (g > 235) & (b > 235)).sum()),
            "dark": int(((r < 60) & (g < 60) & (b < 60)).sum()),
            "yellow": int(((r > 180) & (g > 160) & (b < 120)).sum()),
            "orange": int(((r > 180) & (g > 70) & (g < 160) & (b < 100)).sum())}


def measure(tag):
    res = {"tag": tag, "ts": time.time(), "frame": frame_bright()}
    bound = ls.find_fighter()
    res["bound"] = bound is not None
    res["bound_addr"] = hex(bound) if bound else None
    if bound is not None:
        opp = ls.find_opponent(bound)
        res["opp"] = hex(opp) if opp else None
        res["opp_sustained"] = bool(opp) and ls.opponent_moves_sustained(opp)
        res["round_running"] = bool(opp) and ls.round_running(bound, opp)
    else:
        res["opp"] = None
        res["opp_sustained"] = False
        res["round_running"] = False
    return res


def online_log_tail():
    try:
        return ONLINE.read_text().strip()[-500:]
    except OSError:
        return None


def main():
    flag = " ".join(sys.argv[1:]) or "-netlevel training -netai -netpersonality brawler -netdiff 3"
    log({"event": "launch", "flag": flag, "ts": time.time()})
    launch(flag)
    pid = wait_boot()
    if not pid:
        log({"event": "no_boot", "flag": flag})
        sys.exit("no boot")
    log({"event": "booted", "flag": flag, "pid": pid, "ts": time.time()})

    # frame monitor every 6s; bind+opponent once the frame looks like an arena
    # (mean > 85) or at ~45s post-boot as a fallback.
    boot = time.time()
    measured = False
    while time.time() - boot < 100:
        age = time.time() - boot
        fb = frame_bright()
        log({"event": "frame", "age": round(age, 1), "frame": fb})
        arena_like = fb is not None and fb["mean"] > 85
        if not measured and (arena_like or age >= 45):
            measured = True
            tag = f"measure@{round(age)}s"
            log({"event": "measure", "tag": tag, **measure(tag)})
        time.sleep(6)

    log({"event": "online_log", "flag": flag, "log": online_log_tail()})
    log({"event": "done", "flag": flag, "ts": time.time()})
    print("DONE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
