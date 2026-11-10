#!/usr/bin/env python3
"""doctor.py — always-on environment diagnostics for Nidhogg on artemis (Linux/Proton).

The macOS hook is gone, so this replaces the /tmp/nid_* file checks with the Linux
equivalents: the game process, the Xvfb socket, a rendered frame, and the in-process
spy. One block per check with PASS/WARN/FAIL, JSON to state/health.json, and `--gate`
refuses (exit non-zero) unless every check passes.

    python3 tools/doctor.py            # human table
    python3 tools/doctor.py --json     # machine
    python3 tools/doctor.py --gate     # refuse: exit 1 unless overall=PASS
"""
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
OUT = Path("state/health.json")
DISP = ":99"


def _game_pid():
    for d in Path("/proc").iterdir():
        if not d.name.isdigit():
            continue
        try:
            if (d / "comm").read_text().strip() == "Nidhogg.exe":
                return int(d.name)
        except OSError:
            continue
    return None


def _xvfb():
    return Path("/tmp/.X11-unix/X99").is_socket()


def _frame_mean():
    r = subprocess.run(
        ["ffmpeg", "-nostdin", "-loglevel", "error", "-f", "x11grab",
         "-video_size", "640x480", "-i", DISP, "-frames:v", "1",
         "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
        capture_output=True, timeout=20)
    if r.returncode != 0 or len(r.stdout) < 640 * 480 * 3:
        return None
    px = r.stdout[: 640 * 480 * 3]
    return sum(px) / (640 * 480 * 3)


def _spy_ping(pid):
    res = Path(f"/tmp/nid_res_{pid}")
    res.unlink(missing_ok=True)
    Path(f"/tmp/nid_cmd_{pid}").write_text("ping\n")
    for _ in range(40):
        time.sleep(0.05)
        if res.exists():
            return res.read_text().strip()
    return None


def _mute():
    """Headless Linux has no audio path at all: no sound server, no sound card, and
    the game's ALSA attempts fail silently (seen in the proton log). Muted by construction."""
    servers = subprocess.run(
        ["pgrep", "-f", "pulseaudio|pipewire|wireplumber"],
        capture_output=True).stdout.strip()
    cards = list(Path("/dev/snd").glob("pcm*"))
    if not servers and not cards:
        return "PASS", "no audio server and no sound card - game is muted by construction"
    return "WARN", (f"audio server running ({servers.decode()!r}) or cards present "
                    f"({cards})")


def main():
    checks = []

    def add(name, status, detail):
        checks.append({"check": name, "status": status, "detail": detail})

    pid = _game_pid()
    add("game process", "PASS" if pid else "FAIL",
        f"Nidhogg.exe pid {pid}" if pid else "no Nidhogg.exe under wine")

    add("display", "PASS" if _xvfb() else "FAIL",
        "Xvfb :99 socket present" if _xvfb() else "no Xvfb socket /tmp/.X11-unix/X99")

    mean = _frame_mean()
    add("frame", "PASS" if (mean is not None and mean > 5.0) else "FAIL",
        f"mean brightness {mean:.1f}" if mean is not None else "cannot grab a frame")

    if pid:
        pong = _spy_ping(pid)
        add("spy", "PASS" if pong else "FAIL",
            pong if pong else "spy does not answer ping")
    else:
        add("spy", "FAIL", "no game process to ping")

    m_status, m_detail = _mute()
    add("mute", m_status, m_detail)

    worst = "PASS"
    for c in checks:
        if c["status"] == "FAIL":
            worst = "FAIL"
            break
        if c["status"] == "WARN":
            worst = "WARN"

    if "--json" in sys.argv:
        print(json.dumps({"overall": worst, "checks": checks}, indent=1))
    else:
        icons = {"PASS": "ok  ", "WARN": "WARN", "FAIL": "FAIL"}
        print(f"doctor  overall={worst}")
        for c in checks:
            print(f"  [{icons[c['status']]}] {c['check']:14s} {c['detail']}")

    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps({"ts": time.time(), "overall": worst, "checks": checks},
                              indent=1))
    if "--gate" in sys.argv:
        return 0 if worst == "PASS" else 1
    return 0 if worst != "FAIL" else 1


if __name__ == "__main__":
    sys.exit(main())
