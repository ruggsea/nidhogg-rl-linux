#!/usr/bin/env python3
"""probe_training_walk.py — manual TRAINING menu walk, frame+room captured at every key.

Corrected version: waits PROPERLY for the title (dark>150000 AND pure>3000, the
signature reach_match.py uses) before walking, so keys are never pressed into a
booting game.  Walks the engineer's mapped path one key at a time and, at the 3-row
submenu (difficulty / map / START), tests whether START (skip MAP) starts a match.

Success = find_fighter binds AND opponent_moves_sustained (two 6s windows >=8px).
All measurements -> state/probes/training_walk.jsonl.

    python3 tools/probe_training_walk.py
"""
import json
import os
import signal
import subprocess
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
DISP = ":99"
PREFIX = Path.home() / "nidfarm" / "prefixes" / "1"
GAME = Path.home() / "nidfarm" / "game" / "Nidhogg.exe"
PROTON = Path.home() / ".local/opt/GE-Proton11-12-x86_64/proton"
SPY = Path.home() / "nidhogg-pau" / "spy" / "nidspy.so"
STEAM_ROOT = Path.home() / "fake_steam"
LOGDIR = Path.home() / "nidlogs"
REPO = Path.home() / "nidhogg-pau"
OUT = REPO / "state" / "probes" / "training_walk.jsonl"
FRAMEDIR = REPO / "state" / "probes" / "frames"
FRAMEDIR.mkdir(exist_ok=True)

KNOWN = np.array([2, 3, 4, 17, 19, 20, 25] + list(range(26, 78)), dtype=np.int32)
ROOM_NAMES = {2: "rMainMenu", 3: "rMultiMenu", 4: "rOnlineLobby", 17: "rLevelSelect",
              19: "rControlsRoom", 20: "rMatchStats", 21: "rTutorial", 25: "rPreMatch",
              29: "rCastleCenter"}


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def log(rec):
    with OUT.open("a") as f:
        f.write(json.dumps(rec) + "\n")


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
    for lock in [PREFIX / "pfx.lock", PREFIX / "pfx" / "pfx.lock"]:
        try:
            lock.unlink()
        except OSError:
            pass


def launch():
    stop_lane()
    logf = (LOGDIR / "training_walk.log").open("ab")
    env = dict(os.environ)
    env.pop("WAYLAND_DISPLAY", None)
    env.update(DISPLAY=DISP,
               STEAM_COMPAT_CLIENT_INSTALL_PATH=str(STEAM_ROOT),
               STEAM_COMPAT_DATA_PATH=str(PREFIX),
               SteamAppId="94400", SteamGameId="94400",
               WINEDEBUG="-all", LD_PRELOAD=str(SPY))
    subprocess.Popen([str(PROTON), "waitforexitandrun", str(GAME)],
                     env=env, stdout=logf, stderr=logf, start_new_session=True,
                     cwd=str(REPO))
    print(f"[launch] clean boot on {DISP}")


def frame_stats(tag):
    path = str(FRAMEDIR / f"{tag}.png")
    if not n.grab(IID, path):
        return None
    a = np.array(Image.open(path)).astype(int)[40:440, 0:640]
    r, g, b = a[:, :, 0], a[:, :, 1], a[:, :, 2]
    pure = (r > 235) & (g > 235) & (b > 235)
    dark = (r < 60) & (g < 60) & (b < 60)
    yellow = (r > 180) & (g > 160) & (b < 120)
    orange = (r > 180) & (g > 70) & (g < 160) & (b < 100)
    return {"mean": round(float(a.mean()), 1), "pure": int(pure.sum()),
            "dark": int(dark.sum()), "yellow": int(yellow.sum()),
            "orange": int(orange.sum())}


def read_rows():
    path = "/tmp/nid_rugg/tw_rows.png"
    if not n.grab(IID, path):
        return None
    c = np.array(Image.open(path)).astype(int)[40:440]
    H, W = c.shape[:2]
    r, g, b = c[:, :, 0], c[:, :, 1], c[:, :, 2]
    white = (r > 235) & (g > 235) & (b > 235)
    x0, x1 = int(W * 0.10), int(W * 0.90)
    band = white[:, x0:x1]
    text = band.sum(axis=1)
    bg = c[:, x0:x1].mean(axis=2)
    rows, cur = [], None
    for y in range(H):
        if text[y] > 8:
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
    scored = [float(bg[max(0, a - 4):min(H - 1, b + 4)].mean()) for (a, b) in rows]
    mx = max(scored) if scored else 0.0
    sel = scored.index(mx) if mx > 30 else -1
    return [(a // 2, b // 2, round(s, 1)) for (a, b), s in zip(rows, scored)], sel


def room_top():
    pid = n._game_pid(IID)
    if not pid:
        return None
    counts = Counter()
    for a, b in ls._regions()[:3]:
        raw = n.memory(pid, a, b - a, "/tmp/nid_rugg/tw_room.bin")
        if raw is None:
            continue
        arr = np.frombuffer(raw, "<i4")
        vals, cnts = np.unique(arr[np.isin(arr, KNOWN)], return_counts=True)
        for v, c in zip(vals.tolist(), cnts.tolist()):
            counts[int(v)] += c
    top = counts.most_common(3)
    return [(ROOM_NAMES.get(v, f"r{v}"), v, c) for v, c in top]


def wait_title(timeout=150):
    t0 = time.time()
    while time.time() - t0 < timeout:
        if not n._game_pid(IID):
            time.sleep(2)
            continue
        fs = frame_stats("boot_poll")
        if fs and fs["dark"] > 150000 and fs["pure"] > 3000:
            return fs
        time.sleep(3)
    return frame_stats("boot_poll")


def step(tag, keysym, note):
    fs = frame_stats(tag)
    rows = read_rows()
    rt = room_top()
    rec = {"ts": now(), "event": "step", "tag": tag, "key": keysym, "note": note,
           "frame": fs, "rows": rows, "room_top": rt}
    print(f"  {tag}: frame={fs} rows={rows} room={rt}")
    log(rec)
    return rec


def check_match(tag):
    pid = n._game_pid(IID)
    rec = {"ts": now(), "event": "match_check", "tag": tag, "pid": pid,
           "game_up": bool(pid)}
    if not pid:
        log(rec)
        return rec
    addr = ls.find_fighter(IID)
    rec["bind_addr"] = hex(addr) if addr else None
    if addr is None:
        print(f"  {tag}: find_fighter -> None")
        log(rec)
        return rec
    opp = ls.find_opponent(addr)
    rec["opp_addr"] = hex(opp) if opp else None
    if opp is not None:
        rec["opponent_moves_sustained"] = ls.opponent_moves_sustained(opp)
        rec["round_running"] = ls.round_running(addr, opp, settle=2.0, min_px=5.0)
        print(f"  {tag}: bind={hex(addr)} opp={hex(opp)} "
              f"sustained={rec['opponent_moves_sustained']} "
              f"round_running={rec['round_running']}")
    log(rec)
    return rec


def main():
    launch()
    print("[walk] waiting for title (dark>150000 AND pure>3000)...")
    fs = wait_title()
    print(f"[walk] title reached: {fs}")
    time.sleep(2)

    log({"ts": now(), "event": "launch", "disp": DISP, "pid": n._game_pid(IID),
         "title_frame": fs})

    for keysym, wait, note in [
        ("Return", 2.5, "title -> main menu"),
        ("w", 2.0, "-> single player"),
        ("Return", 2.5, "enter single player"),
        ("s", 2.0, "-> training"),
        ("Return", 2.5, "enter training (partner list)"),
        ("Return", 2.5, "pick partner -> 3-row submenu"),
    ]:
        n.key(IID, keysym, hold=0.12)
        time.sleep(wait)
        step(f"after_{keysym}".replace(" ", ""), keysym, note)

    step("submenu_top", None, "3-row submenu (after partner pick)")
    n.key(IID, "s", hold=0.12); time.sleep(2.0)
    step("submenu_s1", "s", "one S")
    n.key(IID, "s", hold=0.12); time.sleep(2.0)
    step("submenu_s2", "s", "two S")

    n.key(IID, "Return", hold=0.12)
    time.sleep(3.0)
    step("after_start_return", "Return", "Return on START row")
    time.sleep(2.0)
    check_match("after_start_return")

    print("[walk] done")


if __name__ == "__main__":
    main()
