#!/usr/bin/env python3
"""walk_training.py — verified training walk + submenu probe (engineer, artemis).

Screen signatures (measured, facts.json linux_menu_walk + prober training_walk.jsonl):
  title    mean < 60, yellow > 4000 (big logo)
  menu     mean > 55, yellow > 8000 (bright main menu / single-player submenu)
  darkrows mean ~20..40 with 3 white text rows (partner list / difficulty window)
  black    mean < 12, no rows (map-select grid renders black)
  arena    mean > 85 (floor/walls)

Each nav key is only pressed once the PREVIOUS screen is confirmed, so a slow fade
cannot eat a keystroke (the failure mode that made the walk nondeterministic).
Appends to state/probes/walk_training.jsonl.

    python3 tools/walk_training.py [--fresh] [--probe "Return"] [--timeout 30]
"""
import argparse
import json
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import nid_linux as n
import linux_state as ls

IID = 0
KNOWN = np.array([2, 3, 4, 17, 19, 20, 25] + list(range(26, 78)), dtype=np.int32)
ROOM_NAMES = {2: "rMainMenu", 3: "rMultiMenu", 4: "rOnlineLobby", 17: "rLevelSelect",
              19: "rControlsRoom", 20: "rMatchStats", 21: "rTutorial", 25: "rPreMatch",
              29: "rCastleCenter"}
OUT = Path.home() / "nidhogg-pau" / "state" / "probes" / "walk_training.jsonl"


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def log(r):
    with OUT.open("a") as f:
        f.write(json.dumps(r) + "\n")


def frame():
    p = n.grab(IID, "/tmp/nid_rugg/wt.png")
    return np.array(Image.open(p)).astype(int)[40:440]


def analyze():
    c = frame()
    r, g, b = c[:, :, 0], c[:, :, 1], c[:, :, 2]
    white = (r > 235) & (g > 235) & (b > 235)
    yellow = (r > 180) & (g > 160) & (b < 120)
    orange = (r > 200) & (g > 90) & (g < 170) & (b < 90)
    # text rows (pure white)
    x0, x1 = int(c.shape[1] * 0.10), int(c.shape[1] * 0.90)
    wt = white[:, x0:x1].sum(axis=1)
    rows, cur = [], None
    for y in range(c.shape[0]):
        if wt[y] > 8:
            cur = [y, y] if cur is None else [cur[0], y]
        else:
            if cur is not None and cur[1] - cur[0] >= 6:
                rows.append((cur[0] // 2, cur[1] // 2))
            cur = None
    if cur is not None and cur[1] - cur[0] >= 6:
        rows.append((cur[0] // 2, cur[1] // 2))
    return {"mean": round(float(c.mean()), 1),
            "yellow": int(yellow.sum()), "orange": int(orange.sum()),
            "rows": rows}


def screen_class(st):
    if st["mean"] < 12:
        return "black"
    if st["mean"] < 55 and st["yellow"] > 4000:
        return "title"
    if st["mean"] > 85:
        return "arena"
    if st["mean"] > 55 and st["yellow"] > 8000:
        return "menu"
    if st["mean"] > 55:
        return "bright_other"
    if st["rows"]:
        return "darkrows"
    return "dark_other"


def room_top():
    pid = n._game_pid(IID)
    if not pid:
        return None
    counts = Counter()
    for a, b in ls._regions()[:3]:
        raw = n.memory(pid, a, b - a, "/tmp/nid_rugg/wt_room.bin")
        if raw is None:
            continue
        arr = np.frombuffer(raw, "<i4")
        vals, cnts = np.unique(arr[np.isin(arr, KNOWN)], return_counts=True)
        for v, c in zip(vals.tolist(), cnts.tolist()):
            counts[int(v)] += c
    return [(ROOM_NAMES.get(v, f"r{v}"), v, c) for v, c in counts.most_common(3)]


def wait_for(classes, timeout, tag):
    t0 = time.time()
    last = None
    while time.time() - t0 < timeout:
        st = analyze()
        last = st
        if screen_class(st) in classes:
            return st
        time.sleep(1.0)
    return last


def step(tag, key, wait):
    st = analyze()
    rt = room_top()
    rec = {"ts": now(), "event": "step", "tag": tag, "key": key,
           "frame": st, "class": screen_class(st), "room_top": rt}
    log(rec)
    print(f"{tag:22s} key={key or '-':7s} class={screen_class(st):11s} "
          f"mean={st['mean']:5.1f} yel={st['yellow']:6d} rows={st['rows']} "
          f"room={rt}", flush=True)
    if key:
        n.key(IID, key, hold=0.12)
        time.sleep(wait)
    return st, rt


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fresh", action="store_true", help="Esc several times to reset to title")
    ap.add_argument("--probe", type=str, default="Return")
    ap.add_argument("--timeout", type=float, default=30.0)
    a = ap.parse_args()

    pid = n._game_pid(IID)
    print(f"pid {pid} on {n._disp(IID)}", flush=True)
    if not pid:
        print("no game; launch first", flush=True)
        return 1

    # reset to title if asked
    if a.fresh:
        for _ in range(6):
            n.key(IID, "Escape", hold=0.1)
            time.sleep(1.0)

    # 1. title -> Return -> main menu (retry the Return until the menu is confirmed)
    st = wait_for(("title", "arena"), a.timeout, "waiting for title/attract")
    if st is None or screen_class(st) not in ("title", "arena"):
        print("no title/attract seen; current:", st, flush=True)
        return 1
    step("title_or_attract", None, 0.0)
    for attempt in range(5):
        n.key(IID, "Return", hold=0.12)
        st = wait_for(("menu", "bright_other"), 6.0, "after Return (menu?)")
        if st is not None and screen_class(st) in ("menu", "bright_other"):
            break
        print(f"  Return attempt {attempt+1}: still {screen_class(st) if st else None}", flush=True)
    step("main_menu", None, 0.0)

    # 2. w (SINGLE PLAYER) -> Return -> single-player submenu
    step("nav:w->single", "w", 2.5)
    step("nav:Return->submenu", "Return", 2.5)

    # 3. s (TRAINING) -> Return -> partner list (dark rows)
    step("nav:s->training", "s", 2.5)
    step("nav:Return->partner", "Return", 2.5)
    st = wait_for(("darkrows", "black"), 8.0, "after enter training")
    step("training_list_or_window", None, 0.0)

    # 4. pick partner -> difficulty window (Return once)
    step("nav:Return->pick", "Return", 2.5)
    step("submenu", None, 0.0)

    # 5. probe matrix
    print("--- probe ---", flush=True)
    for key in a.probe.split():
        step(f"probe:{key}", key, 2.5)

    # match check
    pid = n._game_pid(IID)
    addr = ls.find_fighter(IID) if pid else None
    if addr is None:
        mc = {"bind": None, "sustained": None, "round": None}
    else:
        opp = ls.find_opponent(addr)
        mc = {"bind": hex(addr), "opp": hex(opp) if opp else None,
              "sustained": ls.opponent_moves_sustained(opp) if opp else None,
              "round": ls.round_running(addr, opp, settle=2.0, min_px=5.0) if opp else None}
    log({"ts": now(), "event": "match_check", "result": mc})
    print("MATCH CHECK:", mc, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
