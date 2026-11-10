#!/usr/bin/env python3
"""drive_blind.py — reach the training map-grid and navigate it blind to a CPU match.

The training route (only way to give the CPU a Brain) has a broken step: after the AI
difficulty window, the map select (rLevelSelect/room 17, VsLevelSelect grid) renders a
FULLY BLACK frame and the -lttraining harness either stalls there ('beat cmd 6') or the
game exits at the difficulty->map transition. The menu screens around it RENDER; only
the grid is black, and the grid still answers keys (Up exits it back to a 3-item menu).

This re-launches with retries, reaches the stall, then tries, watching frame brightness
(black grid ~0.0, menu ~60-75, arena ~90+) and running a real bind (D_DELTA/A_DELTA)
the moment the frame stops being black:
  phase A: blind grid navigation (arrows + Return)
  phase B: Esc back to the 3-item menu, then walk its rows to START

    python3 tools/drive_blind.py
"""
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import nid_linux as n  # noqa: E402

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
OUT = REPO / "state" / "probes" / "drive_blind.jsonl"

STALL = "beat cmd 6"
MAX_RETRIES = 4
BATTERY = [
    ("phaseA-confirm", ("Return",)),
    ("phaseA-confirm2", ("space",)),
    ("phaseA-right", ("Right", "Return")),
    ("phaseA-left", ("Left", "Return")),
    ("phaseA-down", ("Down", "Return")),
    ("phaseA-up", ("Up", "Return")),
    ("phaseB-esc-start", ("Escape", "Down", "Return")),
    ("phaseB-esc-start2", ("Escape", "Down", "Down", "Return")),
    ("phaseB-esc-upstart", ("Escape", "Up", "Return")),
    ("phaseB-esc-sstart", ("Escape", "s", "Return")),
    ("phaseB-esc-start3", ("Escape", "Down", "Down", "Down", "Return")),
    ("phaseB-start-direct", ("Return", "Return")),
]


def logline(obj):
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "a") as f:
        f.write(json.dumps(obj) + "\n")


def stop_lane():
    for d in Path("/proc").iterdir():
        if not d.name.isdigit():
            continue
        try:
            comm = (d / "comm").read_text().strip()
            env = (d / "environ").read_bytes()
        except OSError:
            continue
        if comm == "Nidhogg.exe" and b"DISPLAY=" + DISP.encode() in env.split(b"\0"):
            try:
                os.kill(int(d.name), signal.SIGKILL)
            except OSError:
                pass
    time.sleep(4)


def launch():
    stop_lane()
    log = (LOGDIR / "drive_blind.log").open("ab")
    env = dict(os.environ)
    env.pop("WAYLAND_DISPLAY", None)
    env.update(DISPLAY=DISP,
               STEAM_COMPAT_CLIENT_INSTALL_PATH=str(STEAM_ROOT),
               STEAM_COMPAT_DATA_PATH=str(PREFIX),
               SteamAppId="94400", SteamGameId="94400",
               WINEDEBUG="-all", LD_PRELOAD=str(SPY))
    args = [str(PROTON), "waitforexitandrun", str(GAME), "-localtest", "-lttraining"]
    subprocess.Popen(args, env=env, stdout=log, stderr=log,
                     start_new_session=True, cwd=str(REPO))
    print("[launch] -localtest -lttraining", flush=True)


def log_has_stall():
    try:
        return STALL in LOG.read_text(errors="replace")
    except OSError:
        return False


def frame_mean():
    p = "/tmp/nid_rugg/db_frame.png"
    if n.grab(IID, p) is None:
        return None
    im = np.array(Image.open(p).convert("RGB")).astype(int)
    lum = 0.299 * im[:, :, 0] + 0.587 * im[:, :, 1] + 0.114 * im[:, :, 2]
    return round(float(lum.mean()), 1)


def run_bind():
    try:
        cp = subprocess.run(
            [sys.executable, str(REPO / "tools" / "bind_measure.py"), "0"],
            capture_output=True, text=True, timeout=180, cwd=str(REPO))
        return (cp.stdout or "") + (cp.stderr or "")
    except Exception as e:  # noqa: BLE001
        return f"bind error: {type(e).__name__}: {e}"


def reach_stall():
    for attempt in range(MAX_RETRIES):
        launch()
        t0 = time.time()
        stalled = False
        while time.time() - t0 < 150:
            if log_has_stall():
                stalled = True
                break
            if not n._game_pid(IID) and time.time() - t0 > 40:
                break  # game died before stall -> retry
            time.sleep(2)
        if stalled:
            time.sleep(3)
            return True, attempt
        print(f"[retry {attempt}] no stall (game exited or timed out)", flush=True)
        logline({"event": "retry", "ts": time.time(), "attempt": attempt})
    return False, MAX_RETRIES


def main():
    ok, attempts = reach_stall()
    if not ok:
        print("[fail] could not reach stall in retries", flush=True)
        return 1
    pid = n._game_pid(IID)
    base = frame_mean()
    print(f"[stall] pid={pid} base_mean={base}", flush=True)
    logline({"event": "stall", "ts": time.time(), "pid": pid, "base_mean": base})

    for tag, seq in BATTERY:
        for k in seq:
            n.key(IID, k, hold=0.25)
            time.sleep(0.5)
        time.sleep(2.5)
        m = frame_mean()
        obj = {"event": "try", "ts": time.time(), "tag": tag, "seq": list(seq), "mean": m}
        if m is not None and m > 85:
            b = run_bind()
            obj["bind"] = b[-600:]
            print(json.dumps(obj), flush=True)
            logline(obj)
            # a real drivable fighter -> stop
            if "D_DELTA=" in b and "A_DELTA=" in b:
                import re
                mm = re.search(r"D_DELTA=([-\d.]+) A_DELTA=([-\d.]+)", b)
                if mm and float(mm.group(1)) > 10 and float(mm.group(2)) < -10:
                    print(f"[HIT] real fighter after {tag} {list(seq)}", flush=True)
                    break
        else:
            print(json.dumps(obj), flush=True)
            logline(obj)
    print("[done]", flush=True)
    logline({"event": "done", "ts": time.time()})
    return 0


if __name__ == "__main__":
    sys.exit(main())
