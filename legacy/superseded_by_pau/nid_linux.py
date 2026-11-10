#!/usr/bin/env python3
"""Headless Nidhogg on artemis: the hands and eyes, Pau's way, artemis paths.

State is read by an in-process spy (spy/nidspy.so, LD_PRELOAD'd into the game) that
reads its own address space on command — no ptrace, no /proc, so wine's habit of
reparenting its processes to systemd does not matter. Input is xdotool, which lives in
our proot rootfs and is driven against the host X display with -b /tmp.

    python3 tools/nid_linux.py start 1            # one instance on :99
    python3 tools/nid_linux.py status
    python3 tools/nid_linux.py key 0 Return       # one key (held 0.12s)
    python3 tools/nid_linux.py keydown 0 d        # hold a key down
    python3 tools/nid_linux.py keyup 0 d
    python3 tools/nid_linux.py peek 0 /tmp/f.png  # one screenshot (host ffmpeg)
    python3 tools/nid_linux.py stop

This file never touches game memory itself; the spy does, and it is loaded with the game.
"""
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

HOME = Path.home()
FARM = Path(os.environ.get("NIDFARM") or (HOME / "nidfarm"))
PROTON = Path(os.environ.get("NID_PROTON")
              or HOME / ".local/opt/GE-Proton11-12-x86_64/proton")
GAME = (Path(os.environ.get("NID_GAME_DIR") or (FARM / "game"))) / "Nidhogg.exe"
STEAM_ROOT = Path(os.environ.get("NID_STEAM_ROOT") or (HOME / "fake_steam"))
PREFIX = Path(os.environ.get("NID_PREFIX") or (HOME / "nidpfx"))
PROCS = FARM / "procs.json"
LOGDIR = HOME / "nidlogs"
SPY = Path(__file__).resolve().parent.parent / "spy/nidspy.so"
PROOT = HOME / "nidroot/proot"
ROOTFS = HOME / "nidroot/rootfs"
DISPLAY_BASE = int(os.environ.get("NID_DISPLAY_BASE", "99"))
XVFB_RES = os.environ.get("NID_XVFB_RES", "640x480x24")

# ---------------------------------------------------------------- launch


def _pids():
    return json.loads(PROCS.read_text()) if PROCS.exists() else {}


def _save(d):
    FARM.mkdir(exist_ok=True)
    PROCS.write_text(json.dumps(d, indent=1))


def _ensure_display(disp):
    n = disp.lstrip(":")
    if Path(f"/tmp/.X11-unix/X{n}").is_socket():
        return True
    subprocess.Popen(
        [str(PROOT), "-0", "-r", str(ROOTFS), "-b", "/proc", "-b", "/dev",
         "-b", "/sys", "-b", "/tmp", "-w", "/root",
         "/usr/bin/env", "PATH=/usr/bin:/bin", "/usr/bin/Xvfb", disp,
         "-screen", "0", XVFB_RES, "-nolisten", "tcp"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        start_new_session=True)
    for _ in range(50):
        if Path(f"/tmp/.X11-unix/X{n}").is_socket():
            return True
        time.sleep(0.1)
    return False


def start(n):
    start_ids(list(range(n)))


def start_ids(ids):
    LOGDIR.mkdir(exist_ok=True)
    procs = _pids()
    for i in ids:
        disp = f":{DISPLAY_BASE + i}"
        _ensure_display(disp)
        prefix = PREFIX  # single shared prefix for now; reflink-per-instance comes later
        env = dict(os.environ)
        env.pop("WAYLAND_DISPLAY", None)
        env.update(DISPLAY=disp,
                   STEAM_COMPAT_CLIENT_INSTALL_PATH=str(STEAM_ROOT),
                   STEAM_COMPAT_DATA_PATH=str(prefix),
                   SteamAppId="94400", SteamGameId="94400",
                   WINEDEBUG="-all", LD_PRELOAD=str(SPY))
        log = (LOGDIR / f"inst_{DISPLAY_BASE + i}.log").open("ab")
        p = subprocess.Popen([str(PROTON), "waitforexitandrun", str(GAME)],
                             env=env, stdout=log, stderr=log, start_new_session=True)
        procs[str(i)] = {"wrapper": p.pid, "display": disp}
        print(f"instance {i}: display {disp}, wrapper {p.pid}")
    _save(procs)
    for i in ids:
        pid = None
        for _ in range(180):
            pid = _game_pid(i)
            if pid:
                break
            time.sleep(0.5)
        print(f"instance {i}: game pid {pid}")


def stop():
    for i in list(_pids()):
        stop_id(i)
    PROCS.unlink(missing_ok=True)
    print("stopped")


def stop_id(i):
    procs = _pids()
    info = procs.pop(str(i), None)
    targets = [info["wrapper"]] if info else []
    game = _game_pid(i)
    if game:
        targets.append(game)
    for pid in targets:
        try:
            os.kill(pid, signal.SIGTERM)
        except (ProcessLookupError, PermissionError):
            pass
    _save(procs)
    time.sleep(1)


def _game_pid(i):
    """The Nidhogg.exe whose DISPLAY matches instance i's.

    Two sources, in order: the procs.json registry this module writes when IT launches an instance, and
    a /proc scan by DISPLAY. The fallback exists because farm_linux.sh launches instances itself, so they
    never enter that registry - measured: _game_pid(1) returned None while a healthy Nidhogg.exe with
    DISPLAY=:100 was running, which would have made the whole farm invisible to every tool routed here.
    """
    info = _pids().get(str(i))
    disp = info["display"] if info else f":{DISPLAY_BASE + i}"
    target = f"DISPLAY={disp}".encode()
    for d in Path("/proc").iterdir():
        if not d.name.isdigit():
            continue
        try:
            if (d / "comm").read_text().strip() != "Nidhogg.exe":
                continue
            env = (d / "environ").read_bytes()
        except OSError:
            continue
        if target in env.split(b"\0"):
            return int(d.name)
    return None


# ---------------------------------------------------------------- input (xdotool in proot)


def _xdo(disp, *args):
    return subprocess.run(
        [str(PROOT), "-0", "-r", str(ROOTFS), "-b", "/proc", "-b", "/dev",
         "-b", "/sys", "-b", "/tmp", "-w", "/root",
         "/usr/bin/env", f"DISPLAY={disp}", "PATH=/usr/bin:/bin",
         "/usr/bin/xdotool", *args], capture_output=True, text=True, timeout=15)


def _disp(i):
    """Display string for instance i, or None when it is not registered.

    procs.json (written by start/start_ids, deleted by stop) is the registry.  When
    the game dies or is stopped mid-run, _pids() loses the entry and every input
    primitive below used to raise KeyError — which crashed attest_linux.py in the
    middle of a run and left no verdict row.  No-op instead, so the caller observes
    a dead instance through read_f()/find_fighter() returning None.

    FALLBACK: when procs.json is missing/flapped (a concurrent worker rewrites or
    deletes it), derive the display from DISPLAY_BASE + i — exactly the convention
    _game_pid() already uses (:99 = i0, :100 = i1).  Without this, n.frame/n.key
    silently no-op whenever another worker's start()/stop() touches procs.json,
    which surfaces as 'no frame' on a healthy game."""
    info = _pids().get(str(i))
    return info["display"] if info else f":{DISPLAY_BASE + i}"


def _env(i):
    return dict(os.environ, DISPLAY=_disp(i))


def live_instance(prefer_flags=None):
    """Which instance index actually has a running game right now - measured, not assumed.

    MEASURED churn: the live game moved from :100 to :99 between two checks minutes apart, and workers
    kept attesting against the display that had been live a moment earlier, producing "bind failed" rows
    that look like dead games. Auto-selecting from /proc removes that whole class of failure.
    """
    best = None
    for d in Path("/proc").iterdir():
        if not d.name.isdigit():
            continue
        try:
            if (d / "comm").read_text().strip() != "Nidhogg.exe":
                continue
            env = (d / "environ").read_bytes().split(b"\0")
        except OSError:
            continue
        disp = None
        cmd = b""
        for e in env:
            if e.startswith(b"DISPLAY="):
                disp = e.decode().split("=", 1)[1]
        try:
            cmd = (d / "cmdline").read_bytes()
        except OSError:
            pass
        if not disp:
            continue
        try:
            idx = int(disp.split(":")[1]) - DISPLAY_BASE
        except (ValueError, IndexError):
            continue
        if idx < 0:
            continue
        has_flag = bool(prefer_flags and any(f.encode() in cmd for f in prefer_flags))
        score = (has_flag, idx)
        if best is None or score > best[0]:
            best = (score, idx)
    return best[1] if best else None


def window(i):
    """The game's X window on instance i.

    MEASURED failure this fixes: on a farm instance (display :100) the game window has NO name - xdotool
    reports empty names and "Default IME" - so the name search returned nothing, _focus() silently did
    nothing, and every keystroke went nowhere. That surfaces as "bind failed" or "gate/floor/dose failed"
    while the game is perfectly healthy, which reads exactly like a dead game.
    Fallback: take any window that is big enough to be the game (>=300x180) and is not the IME window.
    """
    disp = _disp(i)
    if not disp:
        return None
    w = _xdo(disp, "search", "--onlyvisible", "--name", "[Nn]idhogg").stdout.split()
    if w:
        return w[0]
    for cand in _xdo(disp, "search", "--onlyvisible", "").stdout.split():
        name = _xdo(disp, "getwindowname", cand).stdout.strip()
        if "IME" in name:
            continue
        geo = _xdo(disp, "getwindowgeometry", "--shell", cand).stdout
        try:
            dims = dict(l.split("=") for l in geo.split() if "=" in l)
            if int(dims.get("WIDTH", 0)) >= 300 and int(dims.get("HEIGHT", 0)) >= 180:
                return cand
        except (ValueError, TypeError):
            continue
    return None


def _focus(i):
    disp = _disp(i)
    if not disp:
        return None
    w = window(i)
    if w:
        _xdo(disp, "windowfocus", w)
    return w


def key(i, keysym, hold=0.0):
    disp = _disp(i)
    if not disp:
        return None
    _focus(i)
    if hold:
        _xdo(disp, "keydown", keysym)
        time.sleep(hold)
        _xdo(disp, "keyup", keysym)
    else:
        _xdo(disp, "key", "--clearmodifiers", keysym)


def keydown(i, keysym):
    disp = _disp(i)
    if not disp:
        return None
    _focus(i)
    _xdo(disp, "keydown", keysym)


def keyup(i, keysym):
    disp = _disp(i)
    if not disp:
        return None
    _xdo(disp, "keyup", keysym)


# ---------------------------------------------------------------- eyes


def grab(i, path="/tmp/nid_grab.png"):
    disp = _disp(i)
    if not disp:
        return None
    w, h = int(XVFB_RES.split("x")[0]), int(XVFB_RES.split("x")[1])
    r = subprocess.run(
        ["ffmpeg", "-nostdin", "-loglevel", "error", "-f", "x11grab",
         "-video_size", f"{w}x{h}", "-i", disp, "-frames:v", "1", "-y", path],
        capture_output=True, timeout=30)
    return path if r.returncode == 0 else None


def frame(i, path="/tmp/nid_f.png"):
    p = grab(i, path)
    if not p:
        return None
    w, h = int(XVFB_RES.split("x")[0]), int(XVFB_RES.split("x")[1])
    r = subprocess.run(
        ["ffmpeg", "-nostdin", "-loglevel", "error", "-i", p,
         "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, timeout=30)
    return np.frombuffer(r.stdout, np.uint8).reshape(h, w, 3)


def stable_change(base, after):
    if base is None or after is None:
        return 0
    b1, b2 = base
    still = np.abs(b1.astype(int) - b2.astype(int)).max(2) < 6
    moved = np.abs(after.astype(int) - b1.astype(int)).max(2) > 24
    return int((still & moved).sum())


def press(i, keysym, tries=6, wait=0.9, thresh=60):
    b1 = frame(i, "/tmp/nid_b1.png")
    time.sleep(0.35)
    b2 = frame(i, "/tmp/nid_b2.png")
    for _ in range(tries):
        key(i, keysym)
        time.sleep(wait)
        if stable_change((b1, b2), frame(i, "/tmp/nid_b3.png")) > thresh:
            return True
    return False


# ---------------------------------------------------------------- spy protocol


def memory(pid, addr, size, path="/tmp/nid_rugg/dump.bin"):
    """Ask the in-process spy for a byte range (it reads its own memory)."""
    out = Path(path)
    out.parent.mkdir(exist_ok=True)
    out.unlink(missing_ok=True)
    cmd = Path(f"/tmp/nid_cmd_{pid}")
    cmd.write_text(f"dump {addr:x} {size:x} {path}\n")
    t0 = time.time()
    while cmd.exists() and time.time() - t0 < 10:
        time.sleep(0.02)
    if cmd.exists():
        cmd.unlink(missing_ok=True)
        return None
    return out.read_bytes() if out.exists() else None


def ping(pid):
    res = Path(f"/tmp/nid_res_{pid}")
    res.unlink(missing_ok=True)
    Path(f"/tmp/nid_cmd_{pid}").write_text("ping\n")
    for _ in range(40):
        time.sleep(0.05)
        if res.exists():
            return res.read_text().strip()
    return None


# ---------------------------------------------------------------- CLI


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "start":
        start(int(sys.argv[2]))
    elif cmd == "stop":
        stop()
    elif cmd == "start-id":
        start_ids([int(sys.argv[2])])
    elif cmd == "stop-id":
        stop_id(int(sys.argv[2]))
    elif cmd == "status":
        for i in _pids():
            print(f"{i}: display {_pids()[i]['display']} pid {_game_pid(i)}")
    elif cmd == "key":
        key(int(sys.argv[2]), sys.argv[3])
    elif cmd == "keydown":
        keydown(int(sys.argv[2]), sys.argv[3])
    elif cmd == "keyup":
        keyup(int(sys.argv[2]), sys.argv[3])
    elif cmd == "peek":
        print(grab(int(sys.argv[2]), sys.argv[3] if len(sys.argv) > 3 else "/tmp/nid_grab.png"))
    elif cmd == "ping":
        print(ping(_game_pid(int(sys.argv[2]))))
    else:
        print(__doc__)
