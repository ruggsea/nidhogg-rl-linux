#!/usr/bin/env python3
"""test_flags.py — launch the game with given NID_GAME_ARGS and check for a live CPU
match (find_fighter + opponent_moves_sustained). Relaunches cleanly each time.

    python3 tools/test_flags.py "-netlevel training"
    python3 tools/test_flags.py "-netarcade -netpersonality brawler -netdiff 2"
"""
import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import nid_linux as n
import linux_state as ls

HOME = Path.home()
PROCS = HOME / "nidfarm/procs.json"


def launch(args, boot_wait=50):
    # stop current
    subprocess.run([sys.executable, "tools/nid_linux.py", "stop"],
                   capture_output=True)
    time.sleep(2)
    subprocess.run(["pkill", "-x", "Nidhogg.exe"], capture_output=True)
    time.sleep(1)
    env = dict(__import__("os").environ, NID_GAME_ARGS=args)
    r = subprocess.run(["./tools/launch_linux.sh", ":99"], capture_output=True,
                       text=True, env=env)
    # register procs.json
    for _ in range(30):
        pids = subprocess.run(["pgrep", "-x", "Nidhogg.exe"],
                              capture_output=True, text=True).stdout.split()
        if pids:
            break
        time.sleep(1)
    if pids:
        PROCS.write_text(json.dumps({"0": {"wrapper": int(pids[0]), "display": ":99"}}))
    time.sleep(boot_wait)


def main():
    args = sys.argv[1] if len(sys.argv) > 1 else "-netarcade"
    print(f"launching with NID_GAME_ARGS={args!r}")
    launch(args)
    print("checking...")
    addr = ls.find_fighter()
    print(f"bound = {hex(addr) if addr else None}")
    if addr:
        opp = ls.find_opponent(addr)
        print(f"opp = {hex(opp) if opp else None}")
        if opp:
            mv1 = ls.opponent_moves(opp, seconds=8.0, min_px=8.0)
            time.sleep(4)
            mv2 = ls.opponent_moves(opp, seconds=8.0, min_px=8.0)
            print(f"opponent_moves window1={mv1} window2={mv2} sustained={mv1 and mv2}")
        else:
            print("no opponent found")
    else:
        print("no drivable fighter")


if __name__ == "__main__":
    main()
