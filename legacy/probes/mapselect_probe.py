#!/usr/bin/env python3
"""mapselect_probe.py — probe the -lttraining map-select stall the moment it happens.

The -lttraining ("training teams") localtest script reaches rLevelSelect (map select)
after 'difficulty window' and then stalls (its cmd 6 press does not advance). The game,
left alone, drifts to the title attract demo within ~a minute, so the map select must be
probed AT the stall, not after.

    python3 tools/mapselect_probe.py

Steps: stop instance 0, relaunch -localtest -lttraining with the spy, tight-poll the
localtest.log for the stall marker ('beat cmd 6'), then IMMEDIATELY grab the screen
structure and probe candidate keys (Return / s / w), reporting the screen state + log
delta after each. One JSON line per observation -> state/probes/mapselect.jsonl.
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

IID = 0
DISP = ":99"
PREFIX = Path.home() / "nidfarm" / "prefixes" / "1"
GAME = Path.home() / "nidfarm" / "game" / "Nidhogg.exe"
PROTON = Path.home() / ".local/opt/GE-Proton11-12-x86_64/proton"
SPY = Path.home() / "nidhogg-pau" / "spy" / "nidspy.so"
STEAM_ROOT = Path.home() / "fake_steam"
LOGDIR = Path.home() / "nidlogs"
LOG = PREFIX / "pfx" / "drive_c" / "users" / "steamuser" / "AppData" / "Roaming" / "Nidhogg" / "localtest.log"
OUT = Path.home() / "nidhogg-pau" / "state" / "probes" / "mapselect.jsonl"

STALL_MARKER = "beat cmd 6"


def record(obj):
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "a") as f:
        f.write(json.dumps(obj) + "\n")
    print(json.dumps(obj))


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
    time.sleep(2)


def launch():
    stop_lane()
    log = (LOGDIR / "mapselect_probe.log").open("ab")
    env = dict(os.environ)
    env.pop("WAYLAND_DISPLAY", None)
    env.update(DISPLAY=DISP,
               STEAM_COMPAT_CLIENT_INSTALL_PATH=str(STEAM_ROOT),
               STEAM_COMPAT_DATA_PATH=str(PREFIX),
               SteamAppId="94400", SteamGameId="94400",
               WINEDEBUG="-all", LD_PRELOAD=str(SPY))
    args = [str(PROTON), "waitforexitandrun", str(GAME), "-localtest", "-lttraining"]
    subprocess.Popen(args, env=env, stdout=log, stderr=log, start_new_session=True,
                     cwd=str(Path.home() / "nidhogg-pau"))


def log_tail(n=3):
    try:
        return LOG.read_text(errors="replace").strip().splitlines()[-n:]
    except OSError:
        return []


def screen_class():
    """Cheap screen classification via the existing screen_state module."""
    try:
        out = subprocess.run([sys.executable, "tools/screen_state.py"],
                             capture_output=True, text=True, timeout=40).stdout
        first = out.strip().splitlines()[0] if out.strip() else "?"
        return first
    except Exception as e:
        return f"err {e}"


def highlight_band():
    """Return (y0, y1) of the grey highlight bar, or None. Inline copy of menu_map logic."""
    import numpy as np
    from PIL import Image
    n.grab(IID, "/tmp/nid_rugg/msprobe.png")
    a = np.array(Image.open("/tmp/nid_rugg/msprobe.png")).astype(int)[40:440]
    r, g, b = a[:, :, 0], a[:, :, 1], a[:, :, 2]
    hbar = ((r > 100) & (r < 205) & (g > 100) & (g < 205) & (b > 100) & (b < 205)
            & (np.abs(r - g) < 18) & (np.abs(g - b) < 18))
    by_row = hbar.sum(axis=1)
    mask = by_row > 300
    ys = np.nonzero(mask)[0]
    if len(ys) == 0:
        return None
    return (int(ys.min()), int(ys.max()))


def main():
    print("[probe] stop + relaunch -localtest -lttraining", flush=True)
    launch()
    # wait for boot + spy
    pid = None
    t0 = time.time()
    while time.time() - t0 < 120:
        pid = n._game_pid(IID)
        if pid and n.ping(pid) == f"pong {pid}":
            break
        time.sleep(2)
    print(f"[probe] booted pid={pid} at t+{int(time.time()-t0)}s", flush=True)

    # tight poll for the stall marker
    stall_at = None
    while time.time() - t0 < 200:
        tail = log_tail()
        if any(STALL_MARKER in line for line in tail):
            stall_at = time.time()
            break
        time.sleep(1)
    if not stall_at:
        print("[probe] never reached the stall marker", flush=True)
        record({"reached_stall": False, "log_tail": log_tail(6)})
        return
    print(f"[probe] stall marker seen at t+{int(stall_at-t0)}s; probing NOW", flush=True)

    record({"reached_stall": True, "t_since_launch": int(stall_at - t0),
            "log_tail": log_tail(4)})

    # immediate screen structure
    hb = highlight_band()
    sc = screen_class()
    print(f"[probe] at stall: highlight_band={hb} screen={sc}", flush=True)
    record({"stage": "stall", "highlight_band": hb, "screen": sc})

    # probe keys: press, wait, observe log delta + screen change
    for keysym in ("Return", "s", "w", "a", "d", "space"):
        before = log_tail()
        hb0 = highlight_band()
        n.key(IID, keysym, hold=0.15)
        time.sleep(2.5)
        after = log_tail()
        new_lines = [l for l in after if l not in before]
        sc2 = screen_class()
        record({"stage": "key", "key": keysym, "highlight_before": hb0,
                "highlight_after": highlight_band(), "screen": sc2,
                "new_log_lines": new_lines})
        print(f"[probe] key={keysym} new_log={new_lines} screen={sc2}", flush=True)
        # if the harness advanced (checkpoint fired), stop
        if any("four fighters" in l or "Brain" in l or "faceoff" in l for l in new_lines):
            print("[probe] HARNESS ADVANCED", flush=True)
            break

    print("[probe] done", flush=True)


if __name__ == "__main__":
    main()
