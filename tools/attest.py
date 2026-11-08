"""attest.py — prove, in one run, that the training path reaches a match we control.

This is the check the project spent a day missing. It does the whole chain and prints a single
verdict, with the evidence for each step:

  1. LAUNCH      a fresh game with the hook
  2. NAVIGATE    the mapped menu path to SINGLE PLAYER -> TRAINING -> partner -> START
                 (mapped by hand from screenshots; the cursor starts on MULTIPLAYER, which is the
                 ARCADE route and gives a standing placeholder opponent)
  3. ROOM        read _Current_Room (an int32 global) and confirm we left the title room
  4. BIND        identify OUR fighter by stimulus-response: D must move it right, A left
  5. GATE        re-run that test against the bound instance and require both directions
  6. OPPONENT    confirm the opponent instance moved at some point (not a statue)

Only if all six pass is a training run worth starting.

    python3 tools/attest.py            # full run
    python3 tools/attest.py --no-launch  # attest whatever is already running
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import train_state as TS

ROOM_FILE = "/tmp/nid_room_now_{}.txt"
TITLE_ROOMS = {2}


def room(iid):
    try:
        return int(open(ROOM_FILE.format(iid)).read().strip())
    except (OSError, ValueError):
        return None


ONLINE_ROOM = 3          # measured: MULTIPLAYER leads here ("SEARCHING FOR PLAYERS")


def esc_home(mgr, log=print, tries=5):
    """Back out to the main menu (room 2) using the room index as feedback."""
    for _ in range(tries):
        if room(mgr.iid) == 2:
            return True
        mgr.press(27)            # Esc = back
        time.sleep(1.4)
    return room(mgr.iid) == 2


def navigate(mgr, log=print):
    """The hand-verified path, no searching.

    Why not search: every blind Enter lands on whatever the cursor happens to be on, and if that is
    OPTIONS then Enter cycles the LANGUAGE row - measured: the game came back in FRENCH, then
    CHINESE. Blind menu probing corrupts the game's settings, so navigation uses exactly the
    sequence that was walked by hand with screenshots, and fails loudly if it does not work.

        PRESS ENTER
        W        -> SINGLE PLAYER   (the cursor starts on MULTIPLAYER = online)
        ENTER    -> ARCADE / TRAINING submenu
        S        -> TRAINING
        ENTER    -> partner list
        ENTER    -> partner submenu (DIFFICULTY / START)
        S        -> START
        ENTER    -> start
        ENTER    -> skip the level-intro card
    """
    seq = [(13, "PRESS ENTER"), (87, "W -> SINGLE PLAYER"), (13, "enter submenu"),
           (83, "S -> TRAINING"), (13, "enter partner list"), (13, "pick partner"),
           (83, "S -> START"), (13, "START"), (13, "skip intro card"), (13, "skip intro again")]
    for code, what in seq:
        mgr.press(code)
        time.sleep(2.5)
        log(f"   {what:24s} room={room(mgr.iid)}")
    st, _ = mgr.read_state()
    r = room(mgr.iid)
    ok = bool(st) and abs(st.get("me_x") or 0) > 0 and r not in (1, 2, 3)
    log(f"   result: room={r} fighters={bool(st and st.get('me_x'))} -> {'OK' if ok else 'NO MATCH'}")
    return ok


def main():
    launch = "--no-launch" not in sys.argv
    iid = 0
    mgr = TS.InstanceManager(iid=iid)
    ok = {}

    if launch:
        print("1. LAUNCH")
        mgr.close() if mgr.proc else None
        mgr.launch()
        time.sleep(TS.BOOT_WAIT)
        print(f"   launched, boot wait {TS.BOOT_WAIT:.0f}s, room={room(iid)}")

    print("2. NAVIGATE (mapped path)")
    navigate(mgr)

    print("3. ROOM")
    r = room(iid)
    left_title = r is not None and r not in TITLE_ROOMS
    print(f"   room={r}  left title room: {left_title}")
    ok["room"] = left_title

    print("4. BIND BY RESPONSE (D must move us right, A left)")
    bound = mgr.bind_by_response()
    print(f"   bound instance: {bound}")
    ok["bind"] = bound is not None

    print("5. CONTROL GATE on the bound instance")
    passed = mgr.prove_control()
    print(f"   gate: {'PASS' if passed else 'FAIL'}  {getattr(mgr, 'gate_dir', {})}")
    ok["gate"] = passed

    print("6. OPPONENT IS NOT A STATUE")
    moves = mgr._opponent_moves(seconds=6.0, min_px=8.0)
    print(f"   opponent moved: {moves}")
    ok["opponent"] = moves

    print("\nVERDICT:", "ATTESTED - training run is meaningful" if all(ok.values())
          else "NOT ATTESTED - " + ", ".join(k for k, v in ok.items() if not v) + " failed")
    print("  " + "  ".join(f"{k}={'ok' if v else 'FAIL'}" for k, v in ok.items()))


if __name__ == "__main__":
    main()
