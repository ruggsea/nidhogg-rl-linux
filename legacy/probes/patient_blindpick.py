#!/usr/bin/env python3
"""patient_blindpick.py — ONE clean launch of -lttraining, patient stall wait, key sweep.

Unlike blindpick_probe.py (which retried and kept SIGKILLing a booting game, leaving the
prefix dirty), this does exactly one launch and waits up to 300s for the stall, polling the
localtest.log. No death detection, no relaunch. Once at the stall it sweeps keys one at a
time and measures frame + find_fighter + round_running + opponent_moves after each.
"""
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import nid_linux as n
import linux_state as ls

IID = 0
DISP = ":99"
PREFIX = Path.home() / "nidfarm" / "prefixes" / "1"
GAME = Path.home() / "nidfarm" / "game" / "Nidhogg.exe"
PROTON = Path.home() / ".local/opt/GE-Proton11-12-x86_64/proton"
SPY = Path.home() / "nidhogg-pau" / "spy" / "nidspy.so"
STEAM_ROOT = Path.home() / "fake_steam"
LOGDIR = Path.home() / "nidlogs"
REPO = Path.home() / "nidhogg-pau"
LOG = (PREFIX / "pfx" / "drive_c" / "users" / "steamuser" /
       "AppData" / "Roaming" / "Nidhogg" / "localtest.log")
OUT = REPO / "state" / "probes" / "patient_blindpick.jsonl"

STALL = "beat cmd 6"
SWEEP = ["Return", "Return", "Return",
         "Right", "Return", "Left", "Return", "Down", "Return", "Up", "Return",
         "space", "Return"]


def log(obj):
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "a") as f:
        f.write(json.dumps(obj) + "\n")
    print(json.dumps(obj), flush=True)


def frame_stats():
    p = "/tmp/nid_rugg/pp_frame.png"
    if n.grab(IID, p) is None:
        return None
    try:
        from PIL import Image
        import numpy as np
        im = np.array(Image.open(p).convert("RGB")).astype(int)
        lum = 0.299 * im[:, :, 0] + 0.587 * im[:, :, 1] + 0.114 * im[:, :, 2]
        return {"mean": round(float(lum.mean()), 1),
                "dark": int((lum < 30).sum()), "yellow": int((im[:, :, 0] > 150).sum())}
    except Exception as e:  # noqa: BLE001
        return {"error": str(e)}


def hit_check():
    out = {"bound": None, "opp": None, "running": None, "opp_moves": None}
    a = ls.find_fighter()
    if not a:
        return out
    out["bound"] = hex(a)
    opp = ls.find_opponent(a)
    if opp is None:
        return out
    out["opp"] = hex(opp)
    out["running"] = ls.round_running(a, opp, settle=2.0, min_px=5.0)
    out["opp_moves"] = ls.opponent_moves_sustained(opp)
    return out


def launch():
    # remove the previous localtest.log so stall detection sees only THIS run
    try:
        LOG.unlink()
    except OSError:
        pass
    fh = (LOGDIR / "patient_blindpick.log").open("ab")
    env = dict(os.environ)
    env.pop("WAYLAND_DISPLAY", None)
    env.update(DISPLAY=DISP,
               STEAM_COMPAT_CLIENT_INSTALL_PATH=str(STEAM_ROOT),
               STEAM_COMPAT_DATA_PATH=str(PREFIX),
               SteamAppId="94400", SteamGameId="94400",
               WINEDEBUG="-all", LD_PRELOAD=str(SPY))
    args = [str(PROTON), "waitforexitandrun", str(GAME), "-localtest", "-lttraining"]
    subprocess.Popen(args, env=env, stdout=fh, stderr=fh,
                     start_new_session=True, cwd=str(REPO))
    # register procs.json once Nidhogg.exe shows up
    for _ in range(120):
        cp = subprocess.run(["pgrep", "-x", "Nidhogg.exe"], capture_output=True, text=True)
        pids = cp.stdout.split()
        if pids:
            (Path.home() / "nidfarm" / "procs.json").write_text(
                json.dumps({"0": {"wrapper": int(pids[0]), "display": DISP}}))
            break
        time.sleep(1)


def has_stall():
    try:
        return STALL in LOG.read_text(errors="replace")
    except OSError:
        return False


def main():
    launch()
    t0 = time.time()
    log({"event": "launched", "ts": time.time()})
    while time.time() - t0 < 300:
        if has_stall():
            log({"event": "stall", "ts": time.time(), "t": round(time.time() - t0),
                 "frame": frame_stats()})
            break
        time.sleep(2)
    else:
        log({"event": "no_stall", "ts": time.time(),
             "log_tail": (LOG.read_text(errors="replace")[-300:]
                          if LOG.exists() else "NO LOG FILE")})
        return 1

    time.sleep(2)
    for i, k in enumerate(SWEEP):
        n.key(IID, k, hold=0.25)
        time.sleep(2.5)
        h = hit_check()
        obs = {"event": "key", "ts": time.time(), "i": i, "key": k,
               "frame": frame_stats(), "hit": h}
        log(obs)
        if h["bound"] and h["opp_moves"]:
            log({"event": "HIT", "ts": time.time(), "key": k, "hit": h})
            break
    log({"event": "done", "ts": time.time()})
    return 0


if __name__ == "__main__":
    sys.exit(main())
