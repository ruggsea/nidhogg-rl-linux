#!/usr/bin/env python3
"""mapselect_sweep.py — the engineer's EXACT map-pick sweep (23:11).

Engineer RE (claim 085771a5): the training map select is a 12-map LIST. Collapsed = 3 rows
[90,146,159]; LEFT/RIGHT expands to 12 rows [29..195]; DOWN collapses; UP holds. Confirm =
accept(Return=13) / accept_alt(space=32) / z (hardcoded 'attack').

Sweep (from the collapsed 3-row state), logging frame rows + find_fighter after EACH key:
  A) Right          (expand 12 rows)
  B) Down           (move highlight to row 1)
  C) Return         (confirm map -> watch if it changes/collapses)
  D) Down, Down, Return  (navigate to a possible START row at the bottom)
  E) if C unchanged: Right, Down, Space
  F) also: Right, Down, z

Watch for mean>85 (arena) at every step. Evidence: state/probes/mapselect_sweep.jsonl.
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
OUT = Path.home() / "nidhogg-pau" / "state" / "probes" / "mapselect_sweep.jsonl"

ls.IID = IID


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def log(r):
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("a") as f:
        f.write(json.dumps(r) + "\n")


def frame():
    n.grab(IID, "/tmp/nid_rugg/mss.png")
    return np.array(Image.open("/tmp/nid_rugg/mss.png").convert("RGB")).astype(int)


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
    fh = (LOGDIR / "mapselect_sweep.log").open("ab")
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
    st = analyze()
    h = hit_check() if st["class"] == "arena" else None
    r = {"ts": now(), "tag": tag, "frame": st, "hit": h}
    log(r)
    print(f"{tag:28s} class={st['class']:10s} mean={st['mean']:5.1f} "
          f"rows={st['rows']} bound={h.get('bound') if h else None} "
          f"opp_moves={h.get('opp_moves') if h else None}", flush=True)
    return st


def key_observe(tag, key, wait=2.5):
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

    def is_mapselect(st):
        r = st.get("rows") or []
        return (st["class"] in ("darkrows", "black")
                and len(r) == 3
                and abs(r[0] - 90) <= 12 and abs(r[2] - 159) <= 12)

    # walk to map select, with Esc+retry (navigation is non-deterministic)
    st = observe("pre-walk")
    for attempt in range(4):
        key_observe(f"w#{attempt}", "w", 2.0)
        key_observe(f"Return-single#{attempt}", "Return", 2.0)
        key_observe(f"s#{attempt}", "s", 2.0)
        key_observe(f"Return-train#{attempt}", "Return", 2.0)
        key_observe(f"Return-pers#{attempt}", "Return", 2.0)
        st = key_observe(f"Return-diff#{attempt}", "Return", 2.0)
        if is_mapselect(st):
            print(f"MAP SELECT reached (attempt {attempt})", flush=True)
            break
        # back out to the main menu and retry
        for _ in range(3):
            key_observe("Esc", "Escape", 1.2)
        time.sleep(1.5)
    st = observe("at-mapselect")

    # A) Right (expand 12 rows)
    st = key_observe("A-Right", "Right", 2.0)
    # B) Down (highlight row 1)
    st = key_observe("B-Down", "Down", 2.0)
    # C) Return (confirm map)
    st = key_observe("C-Return", "Return", 3.0)
    if st["class"] == "arena":
        print("ARENA after C", flush=True)
        return 0

    # D) Down x2 + Return (START row)
    key_observe("D-Down1", "Down", 1.5)
    key_observe("D-Down2", "Down", 1.5)
    st = key_observe("D-Return", "Return", 3.0)
    if st["class"] == "arena":
        print("ARENA after D", flush=True)
        return 0

    # E) Right, Down, Space (space = accept_alt)
    key_observe("E-Right", "Right", 1.5)
    key_observe("E-Down", "Down", 1.5)
    st = key_observe("E-Space", "space", 3.0)
    if st["class"] == "arena":
        print("ARENA after E", flush=True)
        return 0

    # F) Right, Down, z (z = hardcoded attack)
    key_observe("F-Right", "Right", 1.5)
    key_observe("F-Down", "Down", 1.5)
    st = key_observe("F-z", "z", 3.0)
    if st["class"] == "arena":
        print("ARENA after F", flush=True)
        return 0

    observe("final")
    print("no arena reached", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
