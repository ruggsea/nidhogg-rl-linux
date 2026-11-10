#!/usr/bin/env python3
"""flag_matrix.py — prober lane 2: the FLAG MATRIX on instance 1 (:100, prefixes/2).

For each flag, launch a FRESH instance on :100 with the LD_PRELOAD spy, wait for boot
+ title + flag trigger, then measure the live-match checkpoint the prober role defines:

    - find_fighter binds by RESPONSE   (hold a -> left, hold d -> right)
    - opponent_moves >= 8px in 3s      (a real CPU, not the READY/statue screen)

Only when BOTH are true do we have a drivable match with a live CPU. Results append to
state/probes/flag_matrix.jsonl, one line per (flag, timepoint) measurement.

    python3 tools/flag_matrix.py                  # run the whole matrix
    python3 tools/flag_matrix.py -netai           # one flag

Never touches instance 0 (:99) — that is worker 2's lane.
"""
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import nid_linux as n          # noqa: E402
import linux_state as ls       # noqa: E402

IID = 1
DISP = ":100"
PREFIX = Path.home() / "nidfarm" / "prefixes" / "2"
GAME = Path.home() / "nidfarm" / "game" / "Nidhogg.exe"
PROTON = Path.home() / ".local/opt/GE-Proton11-12-x86_64/proton"
SPY = Path.home() / "nidhogg-pau" / "spy" / "nidspy.so"
STEAM_ROOT = Path.home() / "fake_steam"
LOGDIR = Path.home() / "nidlogs"
OUT = Path.home() / "nidhogg-pau" / "state" / "probes" / "flag_matrix.jsonl"

# redirect every linux_state primitive to instance 1 (its IID is a module global)
ls.IID = IID

FLAGS = ["-netai", "-netfw", "-networkdebug", "-netarcade -netpersonality brawler"]


def stop_lane():
    """Kill the Nidhogg.exe on :100 and its proton wrapper (prefixes/2). Leaves :99 alone."""
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


def register():
    """Merge instance 1 into procs.json so nid_linux key input finds its display."""
    procs = Path.home() / "nidfarm" / "procs.json"
    d = {}
    if procs.exists():
        try:
            d = json.loads(procs.read_text())
        except Exception:
            d = {}
    d["1"] = {"wrapper": 0, "display": DISP}
    procs.write_text(json.dumps(d))


def launch(flag):
    stop_lane()
    tag = flag.replace(" ", "_").lstrip("-")
    log = (LOGDIR / f"flagmatrix_{tag}.log").open("ab")
    env = dict(os.environ)
    env.pop("WAYLAND_DISPLAY", None)
    env.update(DISPLAY=DISP,
               STEAM_COMPAT_CLIENT_INSTALL_PATH=str(STEAM_ROOT),
               STEAM_COMPAT_DATA_PATH=str(PREFIX),
               SteamAppId="94400", SteamGameId="94400",
               WINEDEBUG="-all", LD_PRELOAD=str(SPY))
    args = [str(PROTON), "waitforexitandrun", str(GAME)] + flag.split()
    p = subprocess.Popen(args, env=env, stdout=log, stderr=log, start_new_session=True)
    register()
    return p.pid


def wait_ready(timeout=120):
    t0 = time.time()
    while time.time() - t0 < timeout:
        pid = n._game_pid(IID)
        if pid and n.ping(pid) == f"pong {pid}":
            return pid
        time.sleep(2)
    return None


def measure(flag):
    pid = n._game_pid(IID)
    res = {"flag": flag, "ts": time.time(), "game_up": bool(pid)}
    if not pid:
        res["note"] = "no game process on :100"
        return res
    bound = ls.find_fighter()
    res["bound_by_response"] = bound is not None
    res["bound_addr"] = hex(bound) if bound else None
    if bound is not None:
        opp = ls.find_opponent(bound)
        res["opponent_addr"] = hex(opp) if opp else None
        res["opponent_moves_8px_3s"] = bool(opp) and ls.opponent_moves(opp, seconds=3.0, min_px=8.0)
    else:
        res["opponent_addr"] = None
        res["opponent_moves_8px_3s"] = False
    return res


def record(res):
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "a") as f:
        f.write(json.dumps(res) + "\n")
    live = res.get("bound_by_response") and res.get("opponent_moves_8px_3s")
    print(f"[flag] {res['flag']:34s} up={res.get('game_up')} "
          f"bind={res.get('bound_by_response')} "
          f"opp_moves={res.get('opponent_moves_8px_3s')} "
          f"-> {'LIVE MATCH' if live else '-'}", flush=True)


def run_flag(flag):
    launch(flag)
    pid = wait_ready()
    if not pid:
        print(f"[flag] {flag}: game never came up on :100", flush=True)
        record({"flag": flag, "ts": time.time(), "game_up": False, "note": "no boot"})
        return
    print(f"[flag] {flag}: game up pid {pid}, waiting for title + flag trigger", flush=True)
    # boot -> title takes ~35-45s; flags trigger AT the title screen, so sample twice.
    for wait in (45, 30):
        time.sleep(wait)
        res = measure(flag)
        record(res)
        if res.get("bound_by_response") and res.get("opponent_moves_8px_3s"):
            return


def main():
    flags = sys.argv[1:] or FLAGS
    for f in flags:
        run_flag(f)


if __name__ == "__main__":
    main()
