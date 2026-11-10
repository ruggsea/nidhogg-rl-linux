#!/usr/bin/env python3
"""attest_linux.py — prove, on artemis, that the training path reaches a match we control.

The macOS hook is gone; on Linux the same five facts are established by memory scan and
xdotool instead of by symbol:

  1. LIVE        a game process is up, Xvfb is up, and a real frame renders
  2. BIND        a float32 slot responds: hold d -> moves right, hold a -> moves left
  3. GATE        the bound fighter clears the displacement floor (>=40/30 px)
  4. DOSE        holding the key 3x longer moves it ~3x further (ratio >= 1.6)
  5. FLOOR       both directions must clear the wall-pinned floor

Only if all pass is a training run worth starting. Every verdict is appended to
state/attest_runs.log.

    python3 tools/attest_linux.py            # full run against the live game
"""
import importlib.util
import json
import os
import sys
import time
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "ls", Path(__file__).resolve().parent / "linux_state.py")
ls = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ls)

spec = importlib.util.spec_from_file_location(
    "n", Path(__file__).resolve().parent / "nid_linux.py")
n = importlib.util.module_from_spec(spec)
spec.loader.exec_module(n)

MIN_GATE_MAJOR = 40.0
MIN_GATE_MINOR = 30.0
# Auto-select the instance that actually has a running game, unless one is named explicitly. Measured:
# the live game moved between displays within minutes and stale indices produced "bind failed" rows that
# looked like dead games.
if len(sys.argv) > 1:
    INST = int(sys.argv[1])
elif os.environ.get("NID_INSTANCE"):
    INST = int(os.environ["NID_INSTANCE"])
else:
    INST = n.live_instance(prefer_flags=["-netai", "-netarcade"])
    if INST is None:
        print("no running Nidhogg.exe found - start an instance first (tools/farm_linux.sh start 2)")
        raise SystemExit(2)
    print(f"auto-selected instance {INST} (display :{n.DISPLAY_BASE + INST})")



def live():
    """1. LIVE: game process, Xvfb socket, non-blank frame, spy answers ping."""
    pid = n._game_pid(INST)
    if not pid:
        return False, "no Nidhogg.exe process"
    disp = n._disp(INST) or ":99"
    if not Path(f"/tmp/.X11-unix/X{disp[1:]}").is_socket():
        return False, f"no Xvfb socket on {disp}"
    if n.ping(pid) is None:
        return False, "spy does not answer ping"
    if n.frame(INST, "/tmp/nid_rugg/att_frame.png") is None:
        return False, "cannot grab a frame"
    return True, f"pid {pid}"


def main():
    try:
        return _run()
    except Exception as e:  # noqa: BLE001 - a crashed run must still record a verdict row
        print(f"\nCRASH during attestation: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        verdict({"live": False, "crash": True}, note=f"{type(e).__name__}: {e}")
        return 1


def _run():
    ok = {}

    print("1. LIVE")
    is_live, detail = live()
    print(f"   {detail} -> {'ok' if is_live else 'FAIL'}")
    ok["live"] = is_live

    print("2. BIND (by response)")
    addr = ls.find_fighter(INST)
    print(f"   bound: {hex(addr) if addr else None}")
    ok["bind"] = addr is not None
    if addr is None:
        verdict(ok)
        return 1

    print("3. GATE (direction + floor)")
    gate = ls.prove_control(addr)
    d, a = gate.get("D", 0.0), gate.get("A", 0.0)
    floor = (max(abs(d), abs(a)) >= MIN_GATE_MAJOR
             and min(abs(d), abs(a)) >= MIN_GATE_MINOR)
    print(f"   D={d:+.1f} A={a:+.1f}  floor(>=40/30): {'ok' if floor else 'FAIL'}")
    ok["gate"] = d > 0 and a > 0
    ok["floor"] = floor

    print("4. DOSE-RESPONSE (proportionality)")
    dr_ok, d_short, d_long, ratio = ls.dose_response(addr)
    print(f"   short={d_short:.1f}px long={d_long:.1f}px ratio={ratio:.2f} "
          f"-> {'PASS' if dr_ok else 'FAIL'}")
    ok["dose_response"] = dr_ok

    # 5. The two checks the Linux attestation used to skip, and that let it pass on the
    #    READY (local-2P) screen: a round must actually be running, and the opponent must
    #    be a CPU that plays, not a statue waiting for a second human.
    print("5. ROUND RUNNING + OPPONENT (CPU plays, not READY)")
    opp = ls.find_opponent(addr)
    if opp is None:
        print("   no opponent record found")
        ok["running"] = False
        ok["opponent"] = False
    else:
        print(f"   opponent x @ {hex(opp)}")
        ok["running"] = ls.round_running(addr, opp, settle=2.0, min_px=5.0)
        ok["opponent"] = ls.opponent_moves_sustained(opp)
        print(f"   round running: {ok['running']}   opponent moved >=8px in two 6s windows: {ok['opponent']}")

    verdict(ok, addr=addr, gate=gate, dose=(d_short, d_long, ratio))
    return 0 if all(ok.values()) else 1


def verdict(ok, addr=None, gate=None, dose=None, note=None):
    passed = all(ok.values())
    v = ("ATTESTED - training run is meaningful" if passed
         else "NOT ATTESTED - " + ", ".join(k for k, x in ok.items() if not x) + " failed")
    print("\nVERDICT:", v)
    os.makedirs("state", exist_ok=True)
    with open("state/attest_runs.log", "a") as f:
        f.write(json.dumps({
            "ts": time.time(), "verdict": v, "ok": ok,
            "host": "artemis", "addr": hex(addr) if addr else None,
            "gate": gate, "dose": {"short": dose[0], "long": dose[1], "ratio": dose[2]}
            if dose else None, "note": note}) + "\n")


if __name__ == "__main__":
    sys.exit(main())
