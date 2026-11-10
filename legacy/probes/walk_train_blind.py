#!/usr/bin/env python3
"""walk_train_blind.py — robust walk title->TRAINING->map-select with blind START attempt.

Goal: reach the black training map select (rLevelSelect 17) and try to pick a map +
START blind, watching for the arena signature (mean > 85).

Each key is pressed only after the previous screen's signature is confirmed, so a slow
fade cannot eat a keystroke. Appends to state/probes/walk_train_blind.jsonl.
"""
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import nid_linux as n

IID = 0
OUT = Path.home() / "nidhogg-pau" / "state" / "probes" / "walk_train_blind.jsonl"


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def log(r):
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("a") as f:
        f.write(json.dumps(r) + "\n")


def frame():
    n.grab(IID, "/tmp/nid_rugg/wtb.png")
    return np.array(Image.open("/tmp/nid_rugg/wtb.png")).astype(int)


def analyze():
    c = frame()
    r, g, b = c[:, :, 0], c[:, :, 1], c[:, :, 2]
    dark = int(((r < 30) & (g < 30) & (b < 30)).sum())
    yellow = int(((r > 180) & (g > 160) & (b < 120)).sum())
    white_mask = (r > 235) & (g > 235) & (b > 235)
    white = int(white_mask.sum())
    orange = int(((r > 200) & (g > 90) & (g < 170) & (b < 90)).sum())
    mean = round(float(c.mean()), 1)
    # text rows (pure white) in the content band
    x0, x1 = int(c.shape[1] * 0.10), int(c.shape[1] * 0.90)
    wt = (white_mask[:, x0:x1]).sum(axis=1)
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


def press(key, hold=0.12):
    n.key(IID, key, hold=hold)


def wait_class(classes, timeout, tag):
    t0 = time.time()
    last = None
    while time.time() - t0 < timeout:
        st = analyze()
        last = st
        if st["class"] in classes:
            return st
        time.sleep(1.0)
    return last


def step(tag, key, wait, want):
    st = analyze()
    rec = {"ts": now(), "event": "step", "tag": tag, "key": key,
           "frame": st, "want": list(want)}
    log(rec)
    print(f"{tag:24s} key={key or '-':7s} class={st['class']:10s} "
          f"mean={st['mean']:5.1f} yel={st['yellow']:6d} rows={st['rows']}", flush=True)
    if key:
        press(key)
    t0 = time.time()
    while time.time() - t0 < wait:
        st = analyze()
        if st["class"] in want:
            break
        time.sleep(1.0)
    return st


def main():
    pid = n._game_pid(IID)
    print(f"pid {pid} on {n._disp(IID)}", flush=True)
    if not pid:
        print("no game; launch first", flush=True)
        return 1

    # 0. wait for title
    st = wait_class(("title", "menu"), 120, "waiting for title")
    print(f"initial: {st['class']} mean={st['mean']} yel={st['yellow']}", flush=True)
    if st["class"] == "menu":
        print("already on a menu", flush=True)

    # 1. Return -> main menu (retry up to 6)
    for attempt in range(6):
        st = step(f"Return->menu#{attempt+1}", "Return", 6, ("menu",))
        if st["class"] == "menu":
            break
        print(f"  menu not reached (got {st['class']}), retrying", flush=True)

    # 2. w -> SINGLE PLAYER, Return -> submenu
    step("w->single", "w", 3, ("menu", "bright_other", "darkrows", "dark_other"))
    step("Return->submenu", "Return", 4, ("menu", "darkrows", "dark_other"))

    # 3. s -> TRAINING, Return -> partner list
    step("s->training", "s", 3, ("darkrows", "dark_other", "black", "menu"))
    step("Return->partner", "Return", 5, ("darkrows", "dark_other", "black"))

    # 4. Return -> pick partner -> difficulty window
    step("Return->pick", "Return", 4, ("darkrows", "dark_other", "black"))

    # 5. Return -> difficulty window -> map select (black)
    st = step("Return->mapselect", "Return", 5, ("black", "darkrows", "dark_other"))
    print(f"after difficulty Return: {st['class']} mean={st['mean']}", flush=True)

    # 6. blind map select: pick default + START
    for tag, key in [("blind:pick", "Return"), ("blind:down", "s"),
                     ("blind:start", "Return"), ("blind:skip", "Return"),
                     ("blind:skip2", "Return")]:
        st = step(tag, key, 4, ("arena",))
        if st["class"] == "arena":
            print(f"ARENA REACHED after {tag}", flush=True)
            break

    st = analyze()
    print(f"FINAL: class={st['class']} mean={st['mean']} yel={st['yellow']} "
          f"rows={st['rows']}", flush=True)
    log({"ts": now(), "event": "final", "frame": st})
    return 0


if __name__ == "__main__":
    sys.exit(main())
