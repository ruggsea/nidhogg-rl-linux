#!/usr/bin/env python3
"""walk_train_arrows.py — manual walk to the training map select, then ARROW-KEY sweep.

The -lttraining route CRASHES at the difficulty window; the MANUAL walk reaches the map
select ALIVE (black -> darkrows). Arrow keys (Left/Right/Up/Down) have NEVER been tried
there (every probe used w/s/a/d/Return/space). This walks title -> SINGLE PLAYER ->
TRAINING -> partner -> difficulty -> map select, then sweeps arrow keys (each followed by
Return) and measures frame class + find_fighter + opponent_moves after each, watching for
an arena (mean>85) or a live-match HIT (bound AND opponent_moves_sustained).

Evidence: state/probes/walk_train_arrows.jsonl (one JSON line per step/observation).
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
OUT = Path.home() / "nidhogg-pau" / "state" / "probes" / "walk_train_arrows.jsonl"

ls.IID = IID


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def log(r):
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("a") as f:
        f.write(json.dumps(r) + "\n")


def frame():
    n.grab(IID, "/tmp/nid_rugg/wta.png")
    return np.array(Image.open("/tmp/nid_rugg/wta.png")).astype(int)


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
        out["err"] = f"find_fighter: {type(e).__name__}: {e}"
        return out
    if not a:
        return out
    out["bound"] = hex(a)
    try:
        opp = ls.find_opponent(a)
    except Exception as e:  # noqa: BLE001
        out["err"] = f"find_opponent: {type(e).__name__}: {e}"
        return out
    if opp is None:
        return out
    out["opp"] = hex(opp)
    out["running"] = bool(ls.round_running(a, opp, settle=2.0, min_px=5.0))
    out["opp_moves"] = bool(ls.opponent_moves_sustained(opp))
    return out


def press(key, hold=0.12):
    n.key(IID, key, hold=hold)


def step(tag, key, wait, want):
    st = analyze()
    log({"ts": now(), "event": "step", "tag": tag, "key": key,
         "frame": st, "want": list(want)})
    print(f"{tag:26s} key={key or '-':7s} class={st['class']:10s} "
          f"mean={st['mean']:5.1f} rows={st['rows']}", flush=True)
    if key:
        press(key)
    t0 = time.time()
    while time.time() - t0 < wait:
        st = analyze()
        if st["class"] in want:
            break
        time.sleep(1.0)
    return st


def launch():
    # kill any Nidhogg.exe on :99 and any stuck wine/wineserver for prefixes/1
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
    time.sleep(2)
    fh = (LOGDIR / "walk_train_arrows.log").open("ab")
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
    print("[launch] patched game on :99 (no args, manual walk)", flush=True)


def wait_title(timeout=150):
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            st = analyze()
        except Exception as e:  # noqa: BLE001
            st = {"class": "err", "mean": -1, "err": str(e)}
        if st["class"] in ("title", "menu"):
            return st
        time.sleep(2)
    return st


def main():
    launch()
    st = wait_title()
    print(f"initial: {st.get('class')} mean={st.get('mean')}", flush=True)

    # 1. Return -> main menu (retry up to 6)
    for attempt in range(6):
        st = step(f"Return->menu#{attempt+1}", "Return", 6, ("menu",))
        if st["class"] == "menu":
            break
    # 2. w -> SINGLE PLAYER, Return -> submenu
    step("w->single", "w", 3, ("menu", "darkrows", "dark_other"))
    step("Return->submenu", "Return", 4, ("menu", "darkrows", "dark_other"))
    # 3. s -> TRAINING, Return -> partner list
    step("s->training", "s", 3, ("darkrows", "dark_other", "black", "menu"))
    step("Return->partner", "Return", 5, ("darkrows", "dark_other", "black"))
    # 4. Return -> pick partner -> difficulty window
    step("Return->pick", "Return", 4, ("darkrows", "dark_other", "black"))
    # 5. Return -> difficulty -> map select (black)
    st = step("Return->mapselect", "Return", 5, ("black", "darkrows", "dark_other"))
    print(f"at map select: {st['class']} mean={st['mean']} rows={st['rows']}", flush=True)

    # 6. ARROW-KEY sweep at the map select. Each arrow, then Return, then measure.
    sweep = ["Left", "Right", "Up", "Down",
             "Left", "Right", "Up", "Down",
             "Left", "Right", "Up", "Down"]
    for i, k in enumerate(sweep):
        st = step(f"arrow:{k}#{i+1}", k, 2, ("darkrows", "dark_other", "black", "arena"))
        if st["class"] == "arena":
            log({"ts": now(), "event": "arena", "i": i, "key": k, "frame": st})
            print(f"ARENA after {k}", flush=True)
            break
        # Return to confirm/advance, then measure live-match signal
        time.sleep(0.5)
        press("Return", hold=0.12)
        time.sleep(2.0)
        h = hit_check()
        st2 = analyze()
        obs = {"ts": now(), "event": "arrow", "i": i, "key": k,
               "frame": st2, "hit": h}
        log(obs)
        print(f"  after {k}+Return: class={st2['class']} mean={st2['mean']} "
              f"bound={h['bound']} opp_moves={h['opp_moves']}", flush=True)
        if st2["class"] == "arena" or (h["bound"] and h["opp_moves"]):
            log({"ts": now(), "event": "HIT", "key": k, "hit": h, "frame": st2})
            print("HIT: live match", flush=True)
            break

    st = analyze()
    print(f"FINAL: class={st['class']} mean={st['mean']} rows={st['rows']}", flush=True)
    log({"ts": now(), "event": "final", "frame": st})
    return 0


if __name__ == "__main__":
    sys.exit(main())
