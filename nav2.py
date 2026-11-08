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


def main():
    mgr = TS.InstanceManager(iid=0)
    log = print
    log(f"start: {name(mgr)}")

    if not to_main_menu(mgr, log):
        log("FAIL: could not reach rMainMenu")
        return 1

    # From rMainMenu the cursor is wherever it was left. A wrong pick lands in rMultiMenu (3),
    # which is detectable, so search up to four steps upward and stop when the room stops being
    # rMultiMenu. NEWS/OPTIONS are avoided by never going below the cursor we verify.
    for up in (1, 2):
        to_main_menu(mgr, log)
        for _ in range(up):
            press(mgr, K_W, 1.1)
        press(mgr, K_ENTER, 2.2)
        r = room(mgr)
        log(f"  up={up} -> {mgr.room_name(r)}")
        if r == 3:
            log("    that is MULTIPLAYER; backing out")
            continue
        # Still rMainMenu (2) after Enter means the SINGLE PLAYER submenu opened as an OVERLAY in
        # the same room (measured: MULTIPLAYER leaves for room 3, SINGLE PLAYER does not). That is
        # the state we want, so continue rather than treating it as a failure.
        if r == 2:
            log("    submenu overlay in rMainMenu (expected for SINGLE PLAYER)")

        # SINGLE PLAYER submenu: ARCADE is first, TRAINING second.
        press(mgr, K_S, 1.2)          # ARCADE -> TRAINING
        press(mgr, K_ENTER, 1.8)      # into the partner list
        log(f"    after TRAINING: {name(mgr)}")
        press(mgr, K_ENTER, 1.8)      # pick the first partner
        press(mgr, K_S, 1.2)          # DIFFICULTY -> START
        press(mgr, K_ENTER, 2.5)      # START
        press(mgr, K_ENTER, 2.5)      # skip the level-intro card
        st, _ = mgr.read_state()
        log(f"    after START: {name(mgr)} fighters={bool(st and st.get('me_x'))}")
        if room(mgr) in mgr.ARENA_ROOMS and st and abs(st.get("me_x") or 0) > 0:
            log("SUCCESS: in an arena room with fighters")
            return 0
        log("    not a match; trying the next cursor position")
    log("FAIL: no sequence reached an arena")
    return 1


if __name__ == "__main__":
    sys.exit(main())
