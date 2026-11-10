#!/usr/bin/env python3
"""blindpick_probe.py — at the training map-select stall, sweep keys and watch for a match.

Reaches the deterministic -lttraining stall (black rLevelSelect), then sweeps a battery of
blind-pick keys ONE AT A TIME, recording after each press the frame signature, the room
(via room_oracle), and the attestation HIT signal (find_fighter + round_running +
opponent_moves_sustained). A HIT = a drivable P1 AND a CPU opponent that plays.

    python3 tools/blindpick_probe.py [--quick]   # quick = fewer sweeps

Logs every observation to state/probes/blindpick.jsonl. Relaunches cleanly each attempt.
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
OUT = REPO / "state" / "probes" / "blindpick.jsonl"

STALL = "beat cmd 6"
# accept=13 (Return), accept_alt=32 (space) from prefs.ini [controls]. Prior probes used
# w/s/a/d/Return/space at the stall but NEVER arrow keys; the picker (netLevelPicker) is
# most likely arrow-moved + Return-confirmed. Lead with the pick+start+skip Returns, then
# each arrow + Return.
SWEEP = ["Return", "Return", "Return",
         "Right", "Return", "Left", "Return", "Down", "Return", "Up", "Return",
         "space"]
QUICK_SWEEP = ["Return", "Return", "Return", "Right", "Return", "Down", "Return"]


def log(obj):
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "a") as f:
        f.write(json.dumps(obj) + "\n")
    print(json.dumps(obj), flush=True)


def stop_lane():
    """Kill EVERYTHING holding this lane: the game AND any wine/wineserver that a
    failed launch left holding the prefix lock. Prober measured: a stuck launch leaves
    comm=wine + comm=wineserver that stop_lane() never killed, so the next launch's
    game never spawns -> reach_stall() retries forever."""
    killed = []
    for d in Path("/proc").iterdir():
        if not d.name.isdigit():
            continue
        try:
            comm = (d / "comm").read_text().strip()
            env = (d / "environ").read_bytes().split(b"\0")
        except OSError:
            continue
        is_ours = (b"DISPLAY=" + DISP.encode() in env
                   or any(e.startswith(b"STEAM_COMPAT_DATA_PATH=" + str(PREFIX).encode())
                          for e in env))
        if comm in ("Nidhogg.exe", "wine", "wineserver", "wineboot.exe",
                    "winedevice.exe", "steam.exe", "explorer.exe") and is_ours:
            try:
                os.kill(int(d.name), signal.SIGKILL)
                killed.append(comm)
            except OSError:
                pass
    time.sleep(2)
    return killed


def launch():
    stop_lane()
    # remove the previous run's localtest.log so stall detection only sees THIS run
    try:
        LOG.unlink()
    except OSError:
        pass
    # clear stale prefix locks from SIGKILLed games (farm_linux.sh does the same)
    for p in list(PREFIX.glob("pfx.lock")) + list((PREFIX / "pfx").glob("*.lock")):
        try:
            p.unlink()
        except OSError:
            pass
    fh = (LOGDIR / "blindpick.log").open("ab")
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
    # register the real game pid in procs.json once it shows up (memory reads key off it)
    for _ in range(30):
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


def frame_stats():
    p = "/tmp/nid_rugg/bp_frame.png"
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


def room_now():
    try:
        cp = subprocess.run([sys.executable, "tools/room_oracle_linux.py", "0"],
                            capture_output=True, text=True, timeout=40, cwd=str(REPO))
        txt = (cp.stdout or "") + (cp.stderr or "")
        # print the last few candidate lines compactly
        lines = [l for l in txt.splitlines() if l.strip()]
        return lines[-8:]
    except Exception as e:  # noqa: BLE001
        return [f"room err: {e}"]


def hit_check():
    """Return dict with the attestation HIT signal."""
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


def game_alive():
    """The lane is alive if the game OR its wine/proton wrapper is up. During a slow
    wineboot --init (dirty prefix) Nidhogg.exe is not up for 60-90s, so checking only
    Nidhogg.exe made reach_stall() kill a healthy-but-booting game."""
    cp = subprocess.run(["pgrep", "-x", "Nidhogg.exe"], capture_output=True, text=True)
    if cp.returncode == 0:
        return True
    cp = subprocess.run(["pgrep", "-f", "proton waitforexitandrun"],
                        capture_output=True, text=True)
    return cp.returncode == 0


def reach_stall(retries=3):
    for attempt in range(retries):
        launch()
        t0 = time.time()
        while time.time() - t0 < 200:
            if has_stall():
                time.sleep(3)
                return True, attempt
            # death detection: lane must be alive OR still booting (<100s)
            if not game_alive() and time.time() - t0 > 100:
                break
            time.sleep(2)
        log({"event": "retry", "ts": time.time(), "attempt": attempt})
    return False, retries


def main():
    quick = "--quick" in sys.argv
    sweep = QUICK_SWEEP if quick else SWEEP
    ok, attempt = reach_stall()
    if not ok:
        log({"event": "fail", "ts": time.time(), "why": "no stall in retries"})
        return 1
    pid = n._game_pid(IID)
    log({"event": "stall", "ts": time.time(), "pid": pid, "attempt": attempt,
         "frame": frame_stats(), "room": room_now()})

    for i, k in enumerate(sweep):
        n.key(IID, k, hold=0.25)
        time.sleep(2.5)
        h = hit_check()
        obs = {"event": "key", "ts": time.time(), "i": i, "key": k,
               "frame": frame_stats(), "room": room_now(), "hit": h}
        log(obs)
        if h["bound"] and h["opp_moves"]:
            log({"event": "HIT", "ts": time.time(), "key": k, "hit": h})
            print("HIT: drivable P1 + CPU opponent plays", flush=True)
            break

    log({"event": "done", "ts": time.time()})
    return 0


if __name__ == "__main__":
    sys.exit(main())
