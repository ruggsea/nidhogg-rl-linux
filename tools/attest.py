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
import json
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
    """Navigate to TRAINING using the HIGHLIGHT-BAR signal, then walk the submenus.

    The main menu scrolls under a fixed highlight bar, so the selected row can only be identified by
    the text under that bar. nav3.band() crops it and scroll_until() presses S until the wanted item
    is selected - which is what finally made this work unattended:

        try 7: diff vs SINGLE PLAYER = 8.3
        SINGLE PLAYER is under the highlight bar
    """
    import nav3
    from PIL import Image

    # make sure a menu is open (fresh launch sits on the title screen)
    for _ in range(3):
        if nav3.band() is not None:
            break
        mgr.press(13)
        time.sleep(2.0)

    # Measured failure mode: 1 run in 4 landed in room 4 (rOnlineLobby) because the S x5 wrap assumes
    # the cursor starts on MULTIPLAYER. Back out to the main menu first; the highlight-bar search does
    # not depend on cursor position.
    for _ in range(4):
        if room(mgr.iid) not in (3, 4):
            break
        log(f"   in {mgr.room_name(room(mgr.iid))} - backing out to the main menu")
        mgr.press(27)
        time.sleep(1.2)

    ref = Image.open("/tmp/band_singleplayer.png").convert("L")
    if not nav3.scroll_until(mgr, ref, "SINGLE PLAYER", log=log):
        log("   FAIL: never scrolled SINGLE PLAYER under the bar")
        return False

    for code, what, wait in ((13, "enter SINGLE PLAYER", 2.4),
                             (83, "S -> TRAINING", 1.4),
                             (13, "enter TRAINING", 2.0),
                             (13, "pick partner", 2.0),
                             (83, "S -> START", 1.4),
                             (13, "START", 3.0),
                             (13, "skip intro", 2.5),
                             (13, "skip intro again", 2.0)):
        mgr.press(code)
        time.sleep(wait)
        log(f"   {what:22s} room={room(mgr.iid)} {mgr.room_name(room(mgr.iid))}")

    st, _ = mgr.read_state()
    r = room(mgr.iid)
    log(f"   result: room={r} ({mgr.room_name(r)}) me_x={st and st.get('me_x')}")
    return r in mgr.ARENA_ROOMS


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

    # The round does not accept input immediately: after entering the arena the game shows a "GO"
    # moment. Measured: binding straight away finds no responder; a short settle fixes it.
    print("3b. SETTLE (wait for the round to accept input)")
    for _ in range(10):
        st, _ = mgr.read_state()
        if st and st.get("me_x"):
            break
        time.sleep(0.5)
    time.sleep(4.0)
    print("   settled")

    # The CPU in TRAINING is ACTIVE (measured: 29-244 px while we stand still), so it can kill
    # our bound fighter between bind and gate - the bound instance is then destroyed and re-created
    # with a new id, and the gate reads a dead id (FAIL {}). Bind and gate are therefore retried as
    # a PAIR: a gate failure that leaves no bound instance triggers a fresh bind, and prove_control
    # re-runs _make_space each call so a cornered fighter gets a new chance to move.
    print("4-5. BIND + CONTROL GATE (re-bind on failure; CPU is active)")
    bound = None
    passed = False
    for attempt in range(10):
        if mgr.read_bound() is None:
            bound = mgr.bind_by_response()
            if bound is None:
                # Fighter dead / round over. In TRAINING the CPU can kill us mid-bind, after
                # which the game shows a post-round screen (rMatchStats) and the next match only
                # starts on Enter/Space (measured 7.6 s). Try the cheap restart, then settle.
                print(f"   attempt {attempt + 1}: no responder; trying round restart")
                mgr._accept_restart(tries=1, wait=10.0)
                for _ in range(10):
                    st, _ = mgr.read_state()
                    if st and st.get("me_x"):
                        break
                    time.sleep(0.5)
                time.sleep(2.0)
                continue
            print(f"   attempt {attempt + 1}: bound instance {bound}")
        passed = mgr.prove_control()
        if passed:
            break
        print(f"   attempt {attempt + 1}: gate FAIL {getattr(mgr, 'gate_dir', {})}")
        time.sleep(2.0)
    print(f"   bound instance: {bound}")
    print(f"   gate: {'PASS' if passed else 'FAIL'}  {getattr(mgr, 'gate_dir', {})}")
    ok["bind"] = bound is not None
    ok["gate"] = passed

    print("5b. DOSE-RESPONSE (is the movement CAUSED by our key?)")
    # A self-driving attract demo can satisfy the direction gate by coincidence - it moves on its own
    # and over a 1.2 s hold can drift right, then left later. Proportionality cannot be faked: hold the
    # key 3x longer and a fighter we control travels ~3x further.
    dr_ok = False
    try:
        dr_ok, d_s, d_l, ratio = mgr.dose_response()
        print(f"   short hold -> {d_s:+.1f}px, long hold -> {d_l:+.1f}px, "
              f"ratio {ratio:.2f} -> {'PASS' if dr_ok else 'FAIL'}")
    except Exception as e:
        print(f"   dose-response error: {e}")
    ok["dose_response"] = dr_ok

    print("6. OPPONENT IS NOT A STATUE")
    # The CPU idles briefly between behaviours (and right after a round transition), so one
    # 6 s window can read 0 px. Retry a few windows: the point is that the CPU moves on its own
    # at all, not that it never stands still.
    moves = False
    for attempt in range(4):
        moves = mgr._opponent_moves(seconds=6.0, min_px=8.0)
        if moves:
            break
        print(f"   opponent still on attempt {attempt + 1}; retrying")
        time.sleep(2.0)
    print(f"   opponent moved: {moves}")
    ok["opponent"] = moves

    verdict = ("ATTESTED - training run is meaningful" if all(ok.values())
               else "NOT ATTESTED - " + ", ".join(k for k, v in ok.items() if not v) + " failed")
    print("\nVERDICT:", verdict)
    # append every verdict so progress can be counted rather than remembered
    os.makedirs("state", exist_ok=True)
    with open("state/attest_runs.log", "a") as f:
        f.write(json.dumps({"ts": time.time(), "verdict": verdict,
                            "ok": ok, "room": room(iid),
                            "gate": getattr(mgr, "gate_dir", {}),
                            "bound": bound}) + "\n")
    print("  " + "  ".join(f"{k}={'ok' if v else 'FAIL'}" for k, v in ok.items()))


if __name__ == "__main__":
    main()
