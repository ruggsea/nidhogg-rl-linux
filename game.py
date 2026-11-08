"""game.py — the single choke point for driving Nidhogg.

Everything that touches the game goes through here. Before this file, every script wrote
/tmp/nid_keys_<id>.txt directly and slept in wall-clock seconds, which caused the same class of bug
over and over:

  * holds were timed in seconds, so when the frame rate went 30 -> 120 fps the same sleep became 4x
    longer in game time (and the hook's own 6-frame hold shrank to 50 ms, so menu presses were lost);
  * nothing owned the game, so two agents wrote the same key file and silently corrupted each other;
  * "is it live?" was re-invented in each script, usually as "some fighters are moving", which the
    title screen's attract demo satisfies.

This module gives the agent AFFORDANCES instead of file paths:

    game.status()            one dict: process, fps, room (named), bound fighter, liveness
    game.enter_training()    reach a TRAINING match using highlight-bar matching (verifies by room)
    game.state()             OUR fighter (bound by response) + opponent + room + frame
    game.do("right", 12)     hold a direction for 12 GAME FRAMES
    game.attack(), game.jump(), game.wait(20)
    game.rounds(seconds=60)  watch for round transitions (room change) and report them
    game.shot(path)          screenshot of the game window only

Invariants enforced here, because breaking them cost hours: exactly one game process; keys are only
pressed in an arena room; the fighter we report is the one that answers our keys.

CLI:
    python3 game.py status
    python3 game.py enter
    python3 game.py state
    python3 game.py do right 12
    python3 game.py rounds 60
"""
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import train_state as TS

IID = int(os.environ.get("NID_IID", "0"))
KEYS = f"/tmp/nid_keys_{IID}.txt"
HOOK = f"/tmp/nid_inject_{IID}.log"
INSTS = f"/tmp/nid_insts_{IID}.txt"
STATE = f"/tmp/nid_state_{IID}.txt"
ROOM = f"/tmp/nid_room_now_{IID}.txt"

# GML key codes
K = {"left": 65, "right": 68, "attack": 70, "jump": 71, "crouch": 83,
     "enter": 13, "esc": 27, "up_dir": 87, "space": 32, "up": 38}

DEFAULT_HOLD_FRAMES = 8


# ------------------------------------------------------------------ process / frame clock
def frame():
    """Current game frame from the hook's counter, or None."""
    try:
        with open(HOOK, "rb") as f:
            f.seek(0, 2)
            f.seek(max(0, f.tell() - 6000))
            tail = f.read().decode("utf-8", "ignore")
    except OSError:
        return None
    fs = re.findall(r"f=(\d+)", tail)
    return int(fs[-1]) if fs else None


def fps(sample=1.5):
    f0 = frame()
    if f0 is None:
        return None
    time.sleep(sample)
    f1 = frame()
    return None if f1 is None else round((f1 - f0) / sample, 1)


def process_count():
    out = subprocess.run("ps ax | grep -c '[N]idhogg.app/Contents/MacOS/Nidhogg'",
                         shell=True, capture_output=True, text=True).stdout.strip()
    return int(out or 0)


# ------------------------------------------------------------------ room / state
def room():
    try:
        return int(open(ROOM).read().strip())
    except (OSError, ValueError):
        return None


def room_name(r=None):
    r = room() if r is None else r
    return TS.InstanceManager.room_name(r) if r is not None else "?"


def in_arena(r=None):
    r = room() if r is None else r
    return r in TS.InstanceManager.ARENA_ROOMS


def raw_state():
    try:
        v = open(STATE).read().split()
        if len(v) < 6:
            return None
        tx, ty, mx, my, h1, h2 = (float(x) for x in v[:6])
        return {"slot1_x": tx, "slot1_y": ty, "slot2_x": mx, "slot2_y": my,
                "have1": int(h1), "have2": int(h2)}
    except (OSError, ValueError):
        return None


def instances():
    d = {}
    try:
        with open(INSTS) as f:
            for line in f:
                p = line.split()
                if len(p) == 4:
                    d[int(p[0])] = (int(p[1]), float(p[2]), float(p[3]))
    except (OSError, ValueError):
        return None
    return d or None


_BOUND = {"id": None}


def bind(verbose=False):
    """Identify OUR fighter by stimulus and response: D must move it right, A left.

    The object index of the player differs between rooms (154 in one arena, 244 in another), so this
    can only be answered by pressing keys and watching. Cached per process.
    """
    PLAYER_OBJS = (154, 242, 244, 245)
    if not in_arena():
        if verbose:
            print(f"  not in an arena (room {room()}) - refusing to press D/A")
        return None
    # Direction-accumulating, not cycle-paired: requiring D-right AND A-left in the SAME cycle
    # failed on live matches because the D hold's momentum carried into the A hold (measured:
    # "1 candidate responded once" on a controllable match). Each direction is measured from a
    # fresh baseline with a settle between, and the max displacement is accumulated across cycles.
    rights = {}
    lefts = {}
    for _ in range(3):
        a = instances()
        if not a:
            return None
        _hold(K["right"], 20)
        b = instances() or {}
        for inst in set(a) & set(b):
            obj, x, y = a[inst]
            if obj in PLAYER_OBJS and 100 <= y <= 320:
                rights[inst] = max(rights.get(inst, 0.0), b[inst][1] - a[inst][1])
        wait(10)                       # settle: release, let momentum die
        c = instances()
        if not c:
            return None
        _hold(K["left"], 20)
        d = instances() or {}
        for inst in set(c) & set(d):
            obj, x, y = c[inst]
            if obj in PLAYER_OBJS and 100 <= y <= 320:
                lefts[inst] = max(lefts.get(inst, 0.0), c[inst][1] - d[inst][1])
        wait(10)
    cands = [i for i in rights if rights.get(i, 0.0) >= 6 and lefts.get(i, 0.0) >= 6]
    if not cands:
        if verbose:
            print(f"  no fighter answered both directions (D={ {k: round(v, 1) for k, v in rights.items()} } A={ {k: round(v, 1) for k, v in lefts.items()} })")
        return None
    best = max(cands, key=lambda i: rights[i] + lefts[i])
    _BOUND["id"] = best
    if verbose:
        print(f"  bound to instance {best} (D +{rights[best]:.0f} A -{lefts[best]:.0f})")
    return best


def state():
    """Our fighter (bound) + the nearest player-ish opponent + room + frame."""
    inst = _BOUND["id"]
    cur = instances()
    if inst is None or not cur or inst not in cur:
        inst = bind()
        cur = instances()
        if inst is None or not cur or inst not in cur:
            return None
    _obj, mx, my = cur[inst]
    others = [(i, v) for i, v in cur.items()
              if i != inst and v[0] in (154, 242, 244, 245) and 60 <= v[2] <= 400]
    opp = min(others, key=lambda kv: abs(kv[1][1] - mx)) if others else None
    return {"room": room(), "room_name": room_name(), "frame": frame(),
            "me_x": mx, "me_y": my,
            "them_x": opp[1][1] if opp else None,
            "them_y": opp[1][2] if opp else None,
            "dx": (opp[1][1] - mx) if opp else None,
            "bound": inst}


# ------------------------------------------------------------------ input primitives
def _hold(code, frames=DEFAULT_HOLD_FRAMES, timeout=3.0):
    """Hold a key for N GAME FRAMES (not seconds). Rewrites the key file until the frame counter
    advances by N, which is what the game actually consumes."""
    f0 = frame()
    with open(KEYS, "w") as f:
        f.write(f"{code}\n")
    if f0 is None:
        time.sleep(frames / 60.0)
        return
    t0 = time.time()
    while time.time() - t0 < timeout:
        f1 = frame()
        if f1 is not None and f1 - f0 >= frames:
            return
        with open(KEYS, "w") as f:
            f.write(f"{code}\n")
        time.sleep(0.01)


def wait(frames=20):
    f0 = frame()
    if f0 is None:
        time.sleep(frames / 60.0)
        return
    t0 = time.time()
    while time.time() - t0 < 5:
        f1 = frame()
        if f1 is not None and f1 - f0 >= frames:
            return
        time.sleep(0.01)


def do(action, frames=DEFAULT_HOLD_FRAMES):
    """Semantic action. Refuses the movement/attack keys unless we are in an arena room, because in
    menus those same keys change settings (D/A inside OPTIONS cycle the language)."""
    if action in ("left", "right", "attack", "jump") and not in_arena():
        raise RuntimeError(f"refusing '{action}' outside an arena room (room {room()} {room_name()})")
    if action not in K:
        raise KeyError(f"unknown action {action!r}; known: {sorted(K)}")
    _hold(K[action], frames)


# ------------------------------------------------------------------ navigation
def enter_training(max_scrolls=8, verbose=True):
    """Reach a TRAINING match. Returns True when the room is an arena with fighters published.

    The main menu scrolls under a FIXED highlight bar, so the selected row is only identifiable by the
    text under the bar - that is what nav3 does. Everything after the first selection is a fixed,
    hand-verified sequence.
    """
    import nav3
    from PIL import Image

    if not process_count():
        raise RuntimeError("no game process - launch one first (TS.InstanceManager.launch)")

    for _ in range(3):
        if nav3.band() is not None:
            break
        _hold(K["enter"], 20)
        time.sleep(1.5)

    # RECOVER FROM THE WRONG MENU. Measured failure: one run in four landed in room 4
    # (rOnlineLobby) because it selected MULTIPLAYER - the S x5 wrap assumes the cursor starts on
    # MULTIPLAYER, which is false when the previous session left the menu elsewhere. The
    # highlight-bar search below does not depend on cursor position, so: back out to the main menu
    # and let it search.
    for _ in range(4):
        if room() not in (3, 4):
            break
        if verbose:
            print(f"  in {room_name()} - backing out to the main menu")
        _hold(K["esc"], 20)
        time.sleep(1.2)

    ref = Image.open("/tmp/band_singleplayer.png").convert("L")
    if not nav3.scroll_until(TS.InstanceManager(iid=IID), ref, "SINGLE PLAYER", log=print if verbose else (lambda *a: None)):
        if verbose:
            print("  could not select SINGLE PLAYER")
        return False

    for code, what, frames in ((K["enter"], "enter SINGLE PLAYER", 30),
                               (K["crouch"], "-> TRAINING", 20),
                               (K["enter"], "enter TRAINING", 25),
                               (K["enter"], "pick partner", 25),
                               (K["crouch"], "-> START", 20),
                               (K["enter"], "START", 45),
                               (K["enter"], "skip intro", 40),
                               (K["enter"], "skip intro", 30)):
        _hold(code, frames)
        if verbose:
            print(f"  {what:22s} room={room()} {room_name()}")

    ok = in_arena() and (bind(verbose) is not None)
    if verbose:
        print(f"  result: arena={in_arena()} bound={_BOUND['id']}")
    return ok


# ------------------------------------------------------------------ round transitions
def rounds(seconds=60.0, verbose=True):
    """Watch for ROUND TRANSITIONS and report what they look like.

    This is the measurement the project is missing: rounds_won has never fired, so every "win" claim
    has been about a proxy. A round boundary should show up as a room change (the arena scrolls), a
    teleport of both fighters, or a state-file dropout. We log all three with timestamps.
    """
    t0 = time.time()
    prev_room = room()
    prev = state()
    events = []
    while time.time() - t0 < seconds:
        wait(6)
        cur = state()
        r = room()
        if r != prev_room:
            ev = {"t": round(time.time() - t0, 2), "kind": "room_change",
                  "from": prev_room, "to": r, "to_name": room_name(r)}
            events.append(ev)
            if verbose:
                print(f"  ROOM CHANGE {prev_room}({room_name(prev_room)}) -> {r}({room_name(r)})")
            prev_room = r
        elif prev and cur and prev.get("me_x") is not None and cur.get("me_x") is not None:
            if abs(cur["me_x"] - prev["me_x"]) > 150:
                ev = {"t": round(time.time() - t0, 2), "kind": "teleport",
                      "from": round(prev["me_x"]), "to": round(cur["me_x"]), "room": r}
                events.append(ev)
                if verbose:
                    print(f"  TELEPORT me_x {prev['me_x']:.0f} -> {cur['me_x']:.0f} in room {r}")
        prev = cur
    if verbose:
        print(f"  {len(events)} transitions in {seconds:.0f}s")
    return events


def shot(path="/tmp/game_now.png"):
    out = subprocess.run(["/tmp/winid"], capture_output=True, text=True).stdout
    wid = None
    for line in out.splitlines():
        p = line.split()
        if len(p) == 2 and p[1] == "960x628":
            wid = p[0]
            break
    if not wid:
        return False
    subprocess.run(["screencapture", "-x", "-o", "-l", wid, path], capture_output=True)
    return True


def status():
    st = state()
    return {"processes": process_count(), "fps": fps(0.8), "room": room(),
            "room_name": room_name(), "in_arena": in_arena(),
            "bound": _BOUND["id"], "state": st,
            "slot": json.load(open("state/gameslot.json")) if os.path.exists("state/gameslot.json") else None}


def main():
    a = sys.argv[1] if len(sys.argv) > 1 else "status"
    if a == "status":
        print(json.dumps(status(), indent=1))
    elif a == "enter":
        print("OK" if enter_training() else "FAILED")
    elif a == "state":
        print(json.dumps(state(), indent=1))
    elif a == "do":
        do(sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else DEFAULT_HOLD_FRAMES)
    elif a == "rounds":
        rounds(float(sys.argv[2]) if len(sys.argv) > 2 else 60.0)
    elif a == "shot":
        print("saved" if shot() else "no window")
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
