#!/usr/bin/env python3
"""probe_submenu.py — interactively map the 3-row TRAINING submenu we land on.

The game is already on the submenu (mean ~25, 3 white rows).  Press S/W one at a
time, read the highlight position + rows after each, then Return on the chosen row
and report frame + room + find_fighter + opponent_moves_sustained.

    python3 tools/probe_submenu.py [--keys "s s Return"]
"""
import json
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import nid_linux as n           # noqa: E402
import linux_state as ls        # noqa: E402

IID = 0
KNOWN = np.array([2, 3, 4, 17, 19, 20, 25] + list(range(26, 78)), dtype=np.int32)
ROOM_NAMES = {2: "rMainMenu", 3: "rMultiMenu", 4: "rOnlineLobby", 17: "rLevelSelect",
              19: "rControlsRoom", 20: "rMatchStats", 21: "rTutorial", 25: "rPreMatch",
              29: "rCastleCenter"}
OUT = Path.home() / "nidhogg-pau" / "state" / "probes" / "submenu_probe.jsonl"


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def log(r):
    with OUT.open("a") as f:
        f.write(json.dumps(r) + "\n")


def frame():
    p = n.grab(IID, "/tmp/nid_rugg/sm.png")
    return np.array(Image.open(p)).astype(int)[40:440]


def analyze():
    c = frame()
    r, g, b = c[:, :, 0], c[:, :, 1], c[:, :, 2]
    white = (r > 235) & (g > 235) & (b > 235)
    grey = (abs(r - g) < 12) & (abs(g - b) < 12) & (r > 50) & (r < 210)
    yellow = (r > 180) & (g > 160) & (b < 120)
    x0, x1 = int(c.shape[1] * 0.10), int(c.shape[1] * 0.90)
    white_t = white[:, x0:x1].sum(axis=1)
    bg = c[:, x0:x1].mean(axis=2)
    # white text rows
    rows, cur = [], None
    for y in range(c.shape[0]):
        if white_t[y] > 8:
            if cur is None:
                cur = [y, y]
            elif y - cur[1] <= 10:
                cur[1] = y
            else:
                if cur[1] - cur[0] >= 6:
                    rows.append(tuple(cur))
                cur = [y, y]
        else:
            if cur is not None and cur[1] - cur[0] >= 6:
                rows.append(tuple(cur))
            cur = None
    if cur is not None and cur[1] - cur[0] >= 6:
        rows.append(tuple(cur))
    scored = [float(bg[max(0, a - 4):min(c.shape[0] - 1, b + 4)].mean()) for (a, b) in rows]
    mx = max(scored) if scored else 0.0
    sel = scored.index(mx) if mx > 30 else -1
    # highlight bar: the grey row whose y overlaps the selected row
    grey_bg = c[:, x0:x1].mean(axis=2)
    grey_mask = grey[:, x0:x1].sum(axis=1) > 30
    hb = None
    for (a, b) in rows:
        band = grey_bg[a:b + 1].mean()
        if band > 40:
            hb = (a, b, round(float(band), 1))
    return {"mean": round(float(c.mean()), 1),
            "rows": [(a // 2, b // 2, round(s, 1)) for (a, b), s in zip(rows, scored)],
            "sel": sel,
            "grey_band_rows": [(a // 2, b // 2) for (a, b) in rows if
                               grey_bg[a:b + 1].mean() > 40],
            "yellow": int(yellow.sum())}


def room_top():
    pid = n._game_pid(IID)
    if not pid:
        return None
    counts = Counter()
    for a, b in ls._regions()[:3]:
        raw = n.memory(pid, a, b - a, "/tmp/nid_rugg/sm_room.bin")
        if raw is None:
            continue
        arr = np.frombuffer(raw, "<i4")
        vals, cnts = np.unique(arr[np.isin(arr, KNOWN)], return_counts=True)
        for v, c in zip(vals.tolist(), cnts.tolist()):
            counts[int(v)] += c
    return [(ROOM_NAMES.get(v, f"r{v}"), v, c) for v, c in counts.most_common(3)]


def match_check():
    pid = n._game_pid(IID)
    addr = ls.find_fighter(IID) if pid else None
    if addr is None:
        return {"bind": None, "sustained": None, "round": None}
    opp = ls.find_opponent(addr)
    if opp is None:
        return {"bind": hex(addr), "sustained": None, "round": None}
    return {"bind": hex(addr), "opp": hex(opp),
            "sustained": ls.opponent_moves_sustained(opp),
            "round": ls.round_running(addr, opp, settle=2.0, min_px=5.0)}


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--keys", type=str, default="s s Return")
    a = ap.parse_args()
    keys = a.keys.split()

    log({"ts": now(), "event": "start", "pid": n._game_pid(IID),
         "state": analyze(), "room": room_top()})
    print("START:", analyze(), "room:", room_top())

    for i, k in enumerate(keys):
        n.key(IID, k, hold=0.12)
        time.sleep(2.5)
        st = analyze()
        rec = {"ts": now(), "event": "key", "key": k, "idx": i, "state": st,
               "room": room_top()}
        log(rec)
        print(f"  key#{i} {k}: mean={st['mean']} rows={st['rows']} sel={st['sel']} "
              f"grey={st['grey_band_rows']} room={room_top()}")

    mc = match_check()
    log({"ts": now(), "event": "match_check", "result": mc})
    print("MATCH CHECK:", mc)
    print("DONE")


if __name__ == "__main__":
    main()
