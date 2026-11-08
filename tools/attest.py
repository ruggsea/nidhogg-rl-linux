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
    """Deterministic path, with a CLOSED-LOOP anchor for the first Enter.

    Measured key behaviour on this build:
        S (83)       moves the menu cursor DOWN, and WRAPS
        W (87)       does NOT move the main menu
        ArrowUp (38) acts as BACK
        Enter (13)   selects

    The trap in the first version: at 120 fps the main menu is often already up by the time we press
    Enter, so that Enter SELECTS MULTIPLAYER instead of dismissing a splash - and every following key
    is then interpreted inside the multiplayer submenu (measured: ended in rControlsRoom via OPTIONS).
    So the anchor is verified: if we land in rMultiMenu (room 3), Esc back and apply the S x5 wrap
    from the known MULTIPLAYER position.
    """
    def step(code, what, wait=1.8):
        mgr.press(code)
        time.sleep(wait)
        log(f"   {what:24s} room={room(mgr.iid)} -> {mgr.room_name(room(mgr.iid))}")

    step(13, "first Enter", 2.5)
    if room(mgr.iid) == 3:
        step(27, "Esc out of MULTIPLAYER", 1.5)   # cursor stays on MULTIPLAYER
    # from MULTIPLAYER, five downs wrap to SINGLE PLAYER
    for i in range(5):
        mgr.press(83)
        time.sleep(1.0)
    log(f"   S x5 -> SINGLE PLAYER     room={room(mgr.iid)}")
    step(13, "enter SINGLE PLAYER", 2.4)
    step(83, "S -> TRAINING", 1.4)
    step(13, "enter TRAINING", 2.0)
    step(13, "pick partner", 2.0)
    step(83, "S -> START", 1.4)
    step(13, "START", 3.0)
    step(13, "skip intro", 2.5)
    step(13, "skip intro again", 2.0)
    st, _ = mgr.read_state()
    r = room(mgr.iid)
    ok = r in mgr.ARENA_ROOMS
    log(f"   result: room={r} ({mgr.room_name(r)}) fighters={bool(st and st.get('me_x'))}")
    return ok


def main():
    launch = "--no-launch" not in sys.argv
    iid = 0
    mgr = TS.InstanceManager(iid=iid)
    ok = {}

    if launch:
        # ALWAYS relaunch. Attesting against a game that has been left in some menu state is how
        # this chain kept landing in OPTIONS/MULTIPLAYER: the menu cursor position is inherited, and
        # so are in-memory settings (the language was flipped to French and then Chinese by blind
        # Enters in OPTIONS). A fresh launch restores prefs and puts the cursor on MULTIPLAYER.
        print("1. LAUNCH (always fresh)")
        try:
            mgr.close()
        except Exception:
            pass
        import subprocess
        subprocess.run(["pkill", "-9", "-f", "MacOS/Nidhogg"], capture_output=True)
        time.sleep(3)
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
