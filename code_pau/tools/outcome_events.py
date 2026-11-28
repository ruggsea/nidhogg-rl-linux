"""Event-tied kills / deaths / round counter from the spy's own samples (LIMITATION 28).

Both sources are the game's state read at the spy's sample seam, never a motion
heuristic:

  * room   — the current room index, published in the spy's tracked ``score`` slot
             (``nidspy.zig``: ``inRange(g_score) -> score_orange``). A room change is
             the game switching rooms, an event.
  * alive  — ``FLAG_P1`` / ``FLAG_P2``: set while the tracked fighter record is inside
             its mapped region (``nidspy.zig``: ``inRange(g_p1/g_p2)``).

A **death** fires when an alive flag is 0 for ``debounce`` consecutive samples. That
debounce rejects the one-frame flicker documented in ``train_state.py`` ("the CPU's
existence flag flickers to 0 for a frame or two while the fighter is plainly alive").
A death is the end of a round: the survivor wins it. With no death observed the winner
is ``None`` and is never guessed from a position jump. A room change is recorded as a
second source next to the death; it is never used alone to declare a winner.

Pure: feed samples, read counters. No game, no I/O.
"""
from __future__ import annotations

# Mirrors train_state.InstanceManager.ARENA_ROOMS. Room 69 and 78 are not arenas.
ARENA_ROOMS = frozenset(range(26, 78)) - {69, 78}
MATCH_STATS_ROOM = 20          # rMatchStats: the match is over (a forfeit from an arena is a loss)
MENU_NAMES = {0: "__Setup", 1: "rLogos", 2: "rMainMenu", 3: "rMultiMenu", 4: "rOnlineLobby",
              17: "rLevelSelect", 18: "rCredits", 20: "rMatchStats", 21: "rTutorial",
              25: "rPreMatch", 78: "rMods", 81: "rDodgeSwords"}


def room_name(room):
    if room in MENU_NAMES:
        return MENU_NAMES[room]
    return f"arena_{room}" if room in ARENA_ROOMS else f"room_{room}"


def round_boundary(prev, cur):
    """A ROUND boundary read from the verified room index alone (step 2 cut).

    The alive flags (FLAG_P1/P2) are ``nidspy.zig:225`` ``inRange()``, a mapping-bounds
    check that stays 1 for the whole match, so no death event can fire from them
    (commit 38c5d0e, LIMITATION 28). The room index at ``exe_base(pid) + ROOM_OFF`` is
    the verified game variable (``state/round_source_proof_20261128T062640Z.json``:
    ``mem_room == spy_room == 29``). Round boundaries are read from it:

      * arena -> a different arena : the screen advanced. ``advanced_right`` is
        ``cur > prev``; it is a hint, not a winner (train_win.room_change_round).
      * arena -> rMatchStats (20)  : the match ended. A forfeit from an arena is a loss.
      * anything touching a menu/lobby room : re-entry navigation, NOT a round.

    Winner is never asserted here: the room index does not say who won. Returns the
    boundary event, or None when the transition is not a round.
    """
    if prev is None or cur is None or prev == cur:
        return None
    if prev not in ARENA_ROOMS:
        return None
    if cur in ARENA_ROOMS:
        return {"kind": "round_advance", "from": prev, "to": cur,
                "from_name": room_name(prev), "to_name": room_name(cur),
                "advanced_right": cur > prev}
    if cur == MATCH_STATS_ROOM:
        return {"kind": "round_match_end", "from": prev, "to": cur,
                "from_name": room_name(prev), "to_name": room_name(cur)}
    return None


class OutcomeTracker:
    """Fold ``(room, p1_alive, p2_alive)`` samples into event-tied counters.

    P1 = yellow (us), P2 = orange (them), matching ``nid_state_bridge``.
    """

    def __init__(self, debounce=3):
        self.debounce = max(1, int(debounce))
        self.room = None
        self.last_room_change = None
        self._down = {"P1": 0, "P2": 0}
        self._fired = {"P1": False, "P2": False}
        self.rounds = 0
        self.kills = 0                 # P2 deaths (rounds we won)
        self.deaths = 0                # P1 deaths (rounds we lost)
        self.events = []

    def update(self, room, p1_alive, p2_alive, ts=None):
        out = []
        if room is not None and room != self.room:
            if self.room is not None:
                ev = {"kind": "room", "t": ts, "from": self.room, "to": room,
                      "from_name": room_name(self.room), "to_name": room_name(room),
                      "left_arena": self.room in ARENA_ROOMS}
                self.last_room_change = ev
                out.append(ev)
            self.room = room
        for who, alive in (("P1", bool(p1_alive)), ("P2", bool(p2_alive))):
            if alive:
                self._down[who] = 0
                self._fired[who] = False
                continue
            self._down[who] += 1
            if self._down[who] >= self.debounce and not self._fired[who]:
                self._fired[who] = True
                other = "P2" if who == "P1" else "P1"
                ev = {"kind": "death", "t": ts, "who": who, "winner": other,
                      "room": self.room, "room_name": room_name(self.room) if self.room is not None else None}
                self.rounds += 1
                if who == "P1":
                    self.deaths += 1
                else:
                    self.kills += 1
                out.append(ev)
        self.events.extend(out)
        return out

    def summary(self):
        return {"rounds": self.rounds, "kills": self.kills, "deaths": self.deaths,
                "room": self.room,
                "room_name": room_name(self.room) if self.room is not None else None}


def summarize_fixture(samples, debounce=3):
    """Run the tracker over a sample list; helper for the claim/falsifier and tests."""
    tr = OutcomeTracker(debounce=debounce)
    for i, (room, p1, p2) in enumerate(samples):
        tr.update(room, p1, p2, ts=i)
    return tr.summary(), tr.events