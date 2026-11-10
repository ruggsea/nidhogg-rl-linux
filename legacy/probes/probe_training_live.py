#!/usr/bin/env python3
"""probe_training_live.py — the DECISIVE experiment (engineer 18:27):

Run `-localtest -lttraining` on a CLEAN single instance (lane 0, :99, prefixes/1) and,
the moment the localtest.log reaches a live-match checkpoint ('fighter 1 has a Brain' /
'four fighters at the faceoff' / 'training_faceoff'), probe find_fighter +
opponent_moves_sustained and (optionally) run the attest gates.

Clean = kill any :99 game first, clear the prefix lock, and drop stale wine procs on the
prefix so the last run's "died at rLevelSelect (prefix collision)" cannot recur.

    python3 tools/probe_training_live.py [--attest]
"""
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

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
LTLOG = PREFIX / "pfx" / "drive_c" / "users" / "steamuser" / "AppData" / "Roaming" / "Nidhogg" / "localtest.log"
OUT = REPO / "state" / "probes" / "lttraining_full_run.log"
PROBE_OUT = REPO / "state" / "probes" / "training_live_probe.jsonl"

TRIGGERS = ["has a Brain", "four fighters at the faceoff", "training_faceoff",
            "training_window", "player drivable"]
ATTEST = "--attest" in sys.argv


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
    # clear the prefix lock + stale wine processes on THIS prefix
    for lock in [PREFIX / "pfx.lock", PREFIX / "pfx" / "pfx.lock"]:
        try:
            lock.unlink()
        except OSError:
            pass


def launch():
    stop_lane()
    log = (LOGDIR / "training_live.log").open("ab")
    env = dict(os.environ)
    env.pop("WAYLAND_DISPLAY", None)
    env.update(DISPLAY=DISP,
               STEAM_COMPAT_CLIENT_INSTALL_PATH=str(STEAM_ROOT),
               STEAM_COMPAT_DATA_PATH=str(PREFIX),
               SteamAppId="94400", SteamGameId="94400",
               WINEDEBUG="-all", LD_PRELOAD=str(SPY))
    args = [str(PROTON), "waitforexitandrun", str(GAME), "-localtest", "-lttraining"]
    subprocess.Popen(args, env=env, stdout=log, stderr=log, start_new_session=True,
                     cwd=str(REPO))
    print(f"[launch] -localtest -lttraining on {DISP}")


def read_lt():
    if not LTLOG.exists():
        return ""
    try:
        return LTLOG.read_text(errors="replace")
    except OSError:
        return ""


def probe(ts):
    pid = n._game_pid(IID)
    rec = {"ts": ts, "pid": pid, "game_up": bool(pid)}
    if not pid:
        return rec
    addr = ls.find_fighter(IID)
    rec["bind_addr"] = hex(addr) if addr else None
    if addr is None:
        return rec
    opp = ls.find_opponent(addr)
    rec["opp_addr"] = hex(opp) if opp else None
    if opp is not None:
        rec["opponent_moves_sustained"] = ls.opponent_moves_sustained(opp)
        rec["round_running"] = ls.round_running(addr, opp, settle=2.0, min_px=5.0)
    return rec


def run_attest():
    r = subprocess.run([sys.executable, str(REPO / "tools" / "attest_linux.py"), str(IID)],
                       capture_output=True, text=True, timeout=300)
    print(r.stdout[-3000:])
    if r.stderr:
        print("STDERR:", r.stderr[-1000:])


def main():
    launch()
    print(f"[probe] waiting for boot + harness (watching {LTLOG})")
    seen_triggers = set()
    probed = False
    t0 = time.time()
    last_len = -1
    while time.time() - t0 < 420:          # up to 7 min
        txt = read_lt()
        if len(txt) != last_len:
            last_len = len(txt)
            for line in txt.splitlines()[-6:]:
                print("  " + line, flush=True)
            for tr in TRIGGERS:
                if tr in txt and tr not in seen_triggers:
                    seen_triggers.add(tr)
                    print(f"[TRIGGER] '{tr}' seen -> probing", flush=True)
                    rec = probe(time.time())
                    rec["trigger"] = tr
                    with open(PROBE_OUT, "a") as f:
                        f.write(json.dumps(rec) + "\n")
                    print(f"[probe] {json.dumps(rec)}", flush=True)
                    if tr in ("has a Brain", "four fighters at the faceoff") and ATTEST and not probed:
                        probed = True
                        run_attest()
        if "has a Brain" in txt and not probed:
            # one final probe+attest when the brain checkpoint is reached
            rec = probe(time.time())
            rec["trigger"] = "has a Brain (final)"
            with open(PROBE_OUT, "a") as f:
                f.write(json.dumps(rec) + "\n")
            print(f"[probe-final] {json.dumps(rec)}", flush=True)
            if ATTEST:
                run_attest()
            probed = True
        time.sleep(10)
    txt = read_lt()
    OUT.write_text(txt)
    print(f"[done] full log saved to {OUT} ({len(txt)} bytes); triggers seen: {sorted(seen_triggers)}")


if __name__ == "__main__":
    main()
