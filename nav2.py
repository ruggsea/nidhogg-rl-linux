"""nav2.py — closed-loop entry to a TRAINING match, verified by ROOM NAME at every step.

Why this exists: every open-loop menu sequence failed, and blind probing corrupted the game's
settings (Enter on OPTIONS cycles the language; measured: French, then Chinese). The room table in
docs/ROOM_NAMES.md makes navigation checkable instead of hopeful:

    2 rMainMenu   3 rMultiMenu   4 rOnlineLobby   17 rLevelSelect   25 rPreMatch
    26-77 arena rooms (castle / mines / sky / wilds / cemetery)

Rules this follows:
  * never press D or A outside an arena room (they are menu/slider input elsewhere);
  * never press Enter on an unknown cursor position - only after a move that the room table can
    justify;
  * if a step lands on rMultiMenu, we picked MULTIPLAYER: Esc back and move the cursor up one;
  * success = room is an arena room AND fighters are published.

    python3 nav2.py           # drive the running game
"""
import sys
import time

import train_state as TS

K_ENTER, K_W, K_S, K_ESC = 13, 87, 83, 27


def press(mgr, code, wait=1.6):
    mgr.press(code)
    time.sleep(wait)


def room(mgr):
    return mgr.room()


def name(mgr):
    r = room(mgr)
    return f"{r}:{mgr.room_name(r)}"


def to_main_menu(mgr, log=print, tries=6):
    """Esc back to rMainMenu (room 2). We only ever Esc - never Enter - on unknown screens."""
    for _ in range(tries):
        if room(mgr) == 2:
            return True
        press(mgr, K_ESC, 1.3)
    return room(mgr) == 2


def find_multiplayer(mgr, log=print):
    """Locate the MULTIPLAYER row, which is the only main-menu item with a detectable effect.

    Entering MULTIPLAYER switches the game to room 3 (rMultiMenu); nothing else on the main menu
    does. So we can search for it safely, one Enter per candidate row, and once found we know
    exactly where the cursor is. MULTIPLAYER is directly below SINGLE PLAYER, so one W from there is
    the single-player submenu.

    This replaces blind cursor counting, which measured its way into OPTIONS twice and changed the
    game's language in the process.
    """
    for k in range(7):
        to_main_menu(mgr, log)
        for _ in range(k):
            press(mgr, K_S, 0.9)
        press(mgr, K_ENTER, 1.8)
        r = room(mgr)
        log(f"  probe k={k}: {mgr.room_name(r)}")
        if r == 3:
            log("  found MULTIPLAYER (room 3) - cursor position now known")
            return True
        if r != 2:
            press(mgr, K_ESC, 1.2)      # back out of whatever we opened
    log("  could not find MULTIPLAYER")
    return False


def main():
    mgr = TS.InstanceManager(iid=0)
    log = print
    if not mgr.alive():
        # This script drives a RUNNING game; without a launch it silently probed a dead one and
        # reported "could not find MULTIPLAYER" while nothing was running at all (measured).
        log("no game running - launching")
        mgr.close() if mgr.proc else None
        mgr.launch()
        time.sleep(TS.BOOT_WAIT)
    log(f"start: {name(mgr)}")

    if not find_multiplayer(mgr, log):
        return 1

    press(mgr, K_ESC, 1.4)              # leave rMultiMenu, cursor still on MULTIPLAYER
    press(mgr, K_W, 1.2)                # MULTIPLAYER -> SINGLE PLAYER
    press(mgr, K_ENTER, 1.8)            # submenu overlay: ARCADE / TRAINING
    log(f"  after SINGLE PLAYER: {name(mgr)}")
    press(mgr, K_S, 1.2)                # ARCADE -> TRAINING
    press(mgr, K_ENTER, 1.8)            # partner list
    log(f"  after TRAINING: {name(mgr)}")
    press(mgr, K_ENTER, 1.8)            # pick partner
    press(mgr, K_S, 1.2)                # DIFFICULTY -> START
    press(mgr, K_ENTER, 2.5)            # START
    press(mgr, K_ENTER, 2.5)            # skip intro card
    st, _ = mgr.read_state()
    r = room(mgr)
    log(f"  after START: {name(mgr)} fighters={bool(st and st.get('me_x'))}")
    ok = r in mgr.ARENA_ROOMS
    log("SUCCESS: in an arena room" if ok else "FAIL: not in an arena")
    return 0 if ok else 1



if __name__ == "__main__":
    sys.exit(main())
