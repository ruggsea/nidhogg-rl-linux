#!/usr/bin/env python3
"""manual_walk_probe.py — correctly-timed MANUAL training walk + arrow blind-pick.

The -lttraining localtest crashes at the difficulty->map transition (game bug). The
manual walk does NOT crash but must be timed right: the attract demo on the title screen
eats Return for ~10 presses, so we wait for the MAIN MENU signature (mean>55, yellow>8000)
before walking. Then, at the black map-select, sweep the untested ARROW keys + Return.

    python3 tools/manual_walk_probe.py
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image

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
OUT = REPO / "state" / "probes" / "manual_walk_probe.jsonl"

# accept=Return(13). Blind map-select sweep: arrows (never tried) + Return.
SWEEP = ["Return", "Return", "Return",
         "Right", "Return", "Left", "Return", "Down", "Return", "Up", "Return"]


def log(obj):
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "a") as f:
        f.write(json.dumps(obj) + "\n")
    print(json.dumps(obj), flush=True)


def frame_stats():
    p = "/tmp/nid_rugg/mw.png"
    if n.grab(IID, p) is None:
        return None
    im = np.array(Image.open(p).convert("RGB")).astype(int)
    r, g, b = im[:, :, 0], im[:, :, 1], im[:, :, 2]
    lum = 0.299 * r + 0.587 * g + 0.114 * b
    yellow = int(((r > 180) & (g > 160) & (b < 120)).sum())
    dark = int((lum < 30).sum())
    white = int(((r > 235) & (g > 235) & (b > 235)).sum())
    mean = round(float(lum.mean()), 1)
    cls = ("black" if mean < 12 else
           "arena" if mean > 85 else
           "menu" if (mean > 55 and yellow > 8000) else
           "darkrows" if white > 500 else
           "dark_other")
    return {"mean": mean, "yellow": yellow, "dark": dark, "white": white, "class": cls}


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
    # clear stale prefix locks
    for p in list(PREFIX.glob("pfx.lock")) + list((PREFIX / "pfx").glob("*.lock")):
        try:
            p.unlink()
        except OSError:
            pass
    fh = (LOGDIR / "manual_walk.log").open("ab")
    env = dict(os.environ)
    env.pop("WAYLAND_DISPLAY", None)
    env.update(DISPLAY=DISP,
               STEAM_COMPAT_CLIENT_INSTALL_PATH=str(STEAM_ROOT),
               STEAM_COMPAT_DATA_PATH=str(PREFIX),
               SteamAppId="94400", SteamGameId="94400",
               WINEDEBUG="-all", LD_PRELOAD=str(SPY))
    args = [str(PROTON), "waitforexitandrun", str(GAME)]
    subprocess.Popen(args, env=env, stdout=fh, stderr=fh,
                     start_new_session=True, cwd=str(REPO))
    for _ in range(120):
        cp = subprocess.run(["pgrep", "-x", "Nidhogg.exe"], capture_output=True, text=True)
        if cp.stdout.split():
            (Path.home() / "nidfarm" / "procs.json").write_text(
                json.dumps({"0": {"wrapper": int(cp.stdout.split()[0]), "display": DISP}}))
            break
        time.sleep(1)


def wait_menu(timeout=180):
    """Wait for the main menu (bright, yellow). Press Return to leave the title."""
    t0 = time.time()
    pressed = False
    while time.time() - t0 < timeout:
        st = frame_stats()
        if st and st["class"] == "menu":
            return True, st
        if st and st["class"] in ("black", "dark_other", "darkrows") and not pressed:
            # off the title (attract demo over or already past it); try to advance
            n.key(IID, "Return", hold=0.12)
            pressed = True
        time.sleep(2.0)
    return False, frame_stats()


def main():
    launch()
    ok, st = wait_menu()
    log({"event": "menu", "ok": ok, "frame": st})
    if not ok:
        log({"event": "fail", "why": "no main menu"})
        return 1

    # the training walk (from enter_training_linux.py, hand-mapped, 7 keys after the menu)
    for tag, key, wait in [
        ("w-single", "w", 2.0),
        ("ret-submenu", "Return", 2.5),
        ("s-training", "s", 2.0),
        ("ret-partner", "Return", 2.5),
        ("ret-pick", "Return", 2.5),
        ("s-start", "s", 2.0),
        ("ret-start", "Return", 3.0),
    ]:
        n.key(IID, key, hold=0.12)
        time.sleep(wait)
        log({"event": "walk", "tag": tag, "key": key, "frame": frame_stats()})

    # blind map-select sweep
    for i, k in enumerate(SWEEP):
        n.key(IID, k, hold=0.25)
        time.sleep(2.5)
        h = hit_check()
        obs = {"event": "key", "i": i, "key": k, "frame": frame_stats(), "hit": h}
        log(obs)
        if h["bound"] and h["opp_moves"]:
            log({"event": "HIT", "key": k, "hit": h})
            break
    log({"event": "done", "ts": time.time()})
    return 0


if __name__ == "__main__":
    sys.exit(main())
