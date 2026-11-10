#!/usr/bin/env python3
"""mapselect_nav.py — detailed navigation of the training map select (netLevelPicker).

Last tick (walk_train_menu.py, claim caa2c4ab) found: the correctly-timed walk
(w,Return,s,Return,Return,Return from the main menu) reaches a DARK map select (3 white
rows [90,146,159]), and LEFT reveals a 10-12-row list (the map list). But the blind sweep
never reached an arena (mean>85). This probes the map pick MORE carefully: press keys one
at a time and record the frame + find_fighter/opponent after EACH key, so we see exactly
where the pick+START transition is.

Evidence: state/probes/mapselect_nav.jsonl.
"""
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image

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
OUT = Path.home() / "nidhogg-pau" / "state" / "probes" / "mapselect_nav.jsonl"

ls.IID = IID


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def log(r):
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("a") as f:
        f.write(json.dumps(r) + "\n")


def frame():
    n.grab(IID, "/tmp/nid_rugg/msn.png")
    return np.array(Image.open("/tmp/nid_rugg/msn.png").convert("RGB")).astype(int)


def analyze():
    c = frame()
    r, g, b = c[:, :, 0], c[:, :, 1], c[:, :, 2]
    dark = int(((r < 30) & (g < 30) & (b < 30)).sum())
    yellow = int(((r > 180) & (g > 160) & (b < 120)).sum())
    white_mask = (r > 235) & (g > 235) & (b > 235)
    white = int(white_mask.sum())
    orange = int(((r > 200) & (g > 90) & (g < 170) & (b < 90)).sum())
    mean = round(float(c.mean()), 1)
    x0, x1 = int(c.shape[1] * 0.10), int(c.shape[1] * 0.90)
    wt = white_mask[:, x0:x1].sum(axis=1)
    rows, cur = [], None
    for y in range(c.shape[0]):
        if wt[y] > 8:
            cur = [y, y] if cur is None else [cur[0], y]
        else:
            if cur is not None and cur[1] - cur[0] >= 6:
                rows.append(cur[0] // 2)
            cur = None
    if cur is not None and cur[1] - cur[0] >= 6:
        rows.append(cur[0] // 2)
    cls = ("black" if mean < 12 else
           "title" if (mean < 60 and yellow > 2000 and dark > 150000) else
           "arena" if mean > 85 else
           "menu" if (mean > 55 and yellow > 8000) else
           "darkrows" if rows else
           "dark_other")
    return {"mean": mean, "dark": dark, "yellow": yellow, "white": white,
            "orange": orange, "rows": rows, "class": cls}


def hit_check():
    out = {"bound": None, "opp": None, "running": None, "opp_moves": None}
    try:
        a = ls.find_fighter()
    except Exception as e:  # noqa: BLE001
        out["err"] = f"find_fighter {type(e).__name__}: {e}"
        return out
    if not a:
        return out
    out["bound"] = hex(a)
    try:
        opp = ls.find_opponent(a)
    except Exception as e:  # noqa: BLE001
        out["err"] = f"find_opponent {type(e).__name__}: {e}"
        return out
    if opp is None:
        return out
    out["opp"] = hex(opp)
    out["running"] = bool(ls.round_running(a, opp, settle=2.0, min_px=5.0))
    out["opp_moves"] = bool(ls.opponent_moves_sustained(opp))
    return out


def press(key, hold=0.12):
    n.key(IID, key, hold=hold)


def launch():
    for d in Path("/proc").iterdir():
        if not d.name.isdigit():
            continue
        try:
            comm = (d / "comm").read_text().strip()
            env = (d / "environ").read_bytes()
        except OSError:
            continue
        if comm == "Nidhogg.exe" and b"DISPLAY=:99" in env.split(b"\0"):
            os.kill(int(d.name), 9)
        if comm in ("wine", "wineserver") and b"STEAM_COMPAT_DATA_PATH=" + str(PREFIX).encode() in env:
            os.kill(int(d.name), 9)
        if comm == "python3" and b"waitforexitandrun" in (d / "cmdline").read_bytes():
            os.kill(int(d.name), 9)
    time.sleep(2)
    fh = (LOGDIR / "mapselect_nav.log").open("ab")
    env = dict(os.environ)
    env.pop("WAYLAND_DISPLAY", None)
    env.update(DISPLAY=DISP,
               STEAM_COMPAT_CLIENT_INSTALL_PATH=str(STEAM_ROOT),
               STEAM_COMPAT_DATA_PATH=str(PREFIX),
               SteamAppId="94400", SteamGameId="94400",
               WINEDEBUG="-all", LD_PRELOAD=str(SPY))
    args = [str(PROTON), "waitforexitandrun", str(GAME)]
    subprocess.Popen(args, env=env, stdout=fh, stderr=fh,
                     start_new_session=True, cwd=str(Path.home() / "nidhogg-pau"))
    print("[launch] patched game on :99", flush=True)


def wait_menu(timeout=180):
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            st = analyze()
        except Exception as e:  # noqa: BLE001
            st = {"class": "err", "mean": -1, "err": str(e)}
        if st["class"] == "menu":
            return st
        time.sleep(2)
    return st


def observe(tag):
    """Grab frame + hit check, log and print."""
    st = analyze()
    h = hit_check() if st["class"] in ("arena", "darkrows", "dark_other", "black") else None
    r = {"ts": now(), "tag": tag, "frame": st, "hit": h}
    log(r)
    print(f"{tag:30s} class={st['class']:10s} mean={st['mean']:5.1f} "
          f"rows={st['rows']} bound={h.get('bound') if h else None} "
          f"opp_moves={h.get('opp_moves') if h else None}", flush=True)
    return st


def key_step(tag, key, wait=3.0):
    press(key, hold=0.15)
    time.sleep(wait)
    return observe(tag)


def main():
    launch()
    st = wait_menu()
    if st.get("class") != "menu":
        print("FAIL: no menu", flush=True)
        return 1
    print(f"menu reached mean={st['mean']}", flush=True)

    # walk to map select
    key_step("w", "w", 2.0)
    key_step("Return(single)", "Return", 2.0)
    key_step("s", "s", 2.0)
    key_step("Return(training)", "Return", 2.0)
    key_step("Return(personality)", "Return", 2.0)
    key_step("Return(difficulty)", "Return", 2.0)
    observe("at-mapselect")

    # careful pick: Left opens the list, then select + confirm
    key_step("Left", "Left", 2.0)
    observe("list-open")
    # try selecting a map: Down then Return, then Return (START)
    for nav in ("Down", "Down", "Up", "Down", "Up"):
        key_step(f"nav-{nav}", nav, 1.5)
        key_step(f"pick-{nav}", "Return", 2.5)
        st = observe(f"after-pick-{nav}")
        if st["class"] == "arena":
            print(f"ARENA after {nav}+Return", flush=True)
            break
        # a second Return might be START
        key_step(f"start-{nav}", "Return", 2.5)
        st = observe(f"after-start-{nav}")
        if st["class"] == "arena":
            print(f"ARENA after {nav}+Return+Return", flush=True)
            break

    observe("final")
    return 0


if __name__ == "__main__":
    sys.exit(main())
