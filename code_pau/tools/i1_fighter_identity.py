#!/usr/bin/env python3
"""I1 v5q: dose-fix — prove bind A-response; face-D longer then repark; tap-D confirm (T125707Z dme=0)."""
import json, os, sys, time, threading
sys.path.insert(0, os.environ.get("CODE_PAU", "/home/ruggsea/nf-p/code_pau"))
import train_state as ts
import nidlinux as n
import nidstate as ns

FARM = os.environ.get("NIDFARM", "/home/ruggsea/nf-p/pau86")
IID = int(os.environ.get("NID_IID", "0"))
OUT = os.path.join(FARM, "results/runs/i1_probe.json")
STEP = float(os.environ.get("I1_STEP_S", "0.08"))
PARK_X = float(os.environ.get("I1_PARK_X", "400"))
TELEPORT_PX = 900.0
_p2_stop = threading.Event()

def valid_x(x):
    """Reject None, ±1e38 garbage, sentinel me≈-1, and dead me_x≈0 (Critic 11:22)."""
    try:
        if x is None:
            return False
        v = float(x)
        if abs(v) >= 3000.0:
            return False
        if abs(v + 1.0) < 0.51:  # me≈-1 invalid
            return False
        if abs(v) < 5.0:  # me≈0 dead/unbound read — T104147Z drive_ok x0=0
            return False
        return True
    except (TypeError, ValueError):
        return False

_KEYMAP = {65: "a", 68: "d", 83: "s", 87: "w", 37: "Left", 38: "Up", 39: "Right", 40: "Down"}

def hold(mgr, code, seconds):
    """Continuous keydown for `seconds` (v5j). Pulsed mgr.press left dme=0 at me≲500 on T230430Z."""
    keysym = _KEYMAP.get(int(code))
    if keysym is None:
        t0 = time.time()
        while time.time() - t0 < seconds:
            mgr.press(code)
            time.sleep(0.03)
        time.sleep(0.12)
        return
    try:
        n.keydown(IID, keysym)
        time.sleep(max(0.05, float(seconds)))
    finally:
        try:
            n.keyup(IID, keysym)
        except Exception:
            pass
    time.sleep(0.12)

def drive_ok(mgr, code=68, min_px=6.0, hold_s=0.85, max_abs=420.0):
    """Bound must move the expected sign. tele = |dme|>max_abs (death/respawn); wrong_sign separate.
    Critic 10:33: N20 +dme≈386 was no_drive because max_abs=280 on 0.28s D — allow real walk."""
    b0 = read_me(mgr)
    if not b0 or not valid_x(b0.get("me_x")):
        print("drive_ok no_me", b0, flush=True)
        return False, None
    x0 = b0["me_x"]
    sign = +1.0 if int(code) == 68 else -1.0
    hold(mgr, code, hold_s)
    b1 = read_me(mgr)
    if not b1 or not valid_x(b1.get("me_x")):
        print("drive_ok bad_me_post", b1, flush=True)
        return False, None
    dme = b1["me_x"] - x0
    # hard tele: jump bigger than TELEPORT_PX or off-arena; soft cap rejects only beyond max_abs
    hard_tele = abs(dme) > TELEPORT_PX or abs(b1["me_x"]) > 3000
    soft_tele = (not hard_tele) and (abs(dme) > float(max_abs))
    wrong = (dme * sign) < 0 and abs(dme) >= min_px
    ok = (not hard_tele) and (not soft_tele) and ((dme * sign) >= min_px)
    print("drive_ok", {"code": code, "x0": x0, "x1": b1["me_x"], "dme": dme,
                       "hard_tele": hard_tele, "soft_tele": soft_tele, "wrong_sign": wrong, "ok": ok}, flush=True)
    return ok, dme

def _ensure_p2():
    _p2_stop.clear()
    if not any(getattr(t, "name", "") == "p2_nudge" and t.is_alive() for t in threading.enumerate()):
        threading.Thread(target=p2_nudge_loop, daemon=True, name="p2_nudge").start()

def p2_nudge_loop():
    alt = False
    while not _p2_stop.is_set():
        try:
            n.key(IID, "Right" if alt else "Left", hold=0.15)
        except Exception as e:
            print("p2_nudge_err", type(e).__name__, e, flush=True)
        alt = not alt
        _p2_stop.wait(0.7)

def read_me(mgr, tries=20):
    for _ in range(tries):
        if mgr.bound_inst is None:
            return None
        b = mgr.read_bound()
        if b and valid_x(b.get("me_x")):
            return b
        time.sleep(0.05)
    return None

def read_pair_valid(mgr, tries=20):
    for _ in range(tries):
        if mgr.bound_inst is None:
            return None
        p = mgr.read_pair()
        if p and valid_x(p.get("me_x")) and valid_x(p.get("them_x")):
            return p
        time.sleep(0.05)
    return None

def park(mgr, target=PARK_X, tol=45.0, tries=50):
    for _ in range(tries):
        b = read_me(mgr)
        if not b:
            return False, None
        err = b["me_x"] - target
        if abs(err) <= tol:
            hold(mgr, 68, 0.08)
            b2 = read_me(mgr)
            return True, (b2 or b)["me_x"]
        hold(mgr, 65 if err > 0 else 68, min(0.35, 0.04 + abs(err) / 500.0))
    b = read_me(mgr)
    return False, (b or {}).get("me_x")

def corridor_ok(mgr, need_ahead=500.0):
    p = read_pair_valid(mgr)
    if not p:
        return False, None
    me, them = p["me_x"], p["them_x"]
    blocked = (them >= me - 10) and (them <= me + need_ahead)
    return (not blocked), p

def ensure_corridor(mgr, tries=8):
    for _ in range(tries):
        ok, p = corridor_ok(mgr)
        if ok:
            return True
        if p and p["them_x"] >= p["me_x"]:
            hold(mgr, 65, 0.55)
        else:
            time.sleep(0.4)
        park(mgr)
    ok, _ = corridor_ok(mgr)
    return ok

def sync_room_file(iid=IID, path="/tmp/nid_room_now_%s.txt"):
    """Critic 00:48: in_arena() reads this file; bridge can lag/die → stale menu room → bind_failed."""
    room = None
    try:
        import nidmem_room as mr
        room = mr.read_room(iid)
    except Exception as e:
        print("sync_room nidmem_err", repr(e), flush=True)
    if room is None:
        try:
            room = ns.read_room(iid) if hasattr(ns, "read_room") else None
        except Exception:
            room = None
    if room is None:
        return None
    try:
        open(path % iid, "w").write(str(int(room)) + "\n")
        open("/tmp/nid_room_%s.txt" % iid, "w").write(str(int(room)) + "\n")
    except Exception as e:
        print("sync_room write_err", repr(e), flush=True)
    print("sync_room", room, flush=True)
    return int(room)

def wait_arena(mgr, timeout=12.0):
    """Refresh room file until InstanceManager.in_arena() or timeout."""
    t0 = time.time()
    last = None
    while time.time() - t0 < timeout:
        last = sync_room_file()
        if mgr.in_arena():
            print("wait_arena ok", last, "t", round(time.time() - t0, 2), flush=True)
            return True, last
        time.sleep(0.4)
    print("wait_arena FAIL", last, "in_arena", mgr.in_arena(), flush=True)
    return False, last

def rebind(mgr, hold_s=1.0, attempts=4):

    b = mgr.bind_by_response(hold=hold_s, min_px=6.0, attempts=attempts)
    print("rebind", b, flush=True)
    return b

def prep_after_rebind(mgr, max_x=500.0):
    """Critic 13:37 v5q: D dme=0 at park≤500 = facing/bind dead. Prove A-response; face-D longer+repark; tap-D confirm."""
    target = min(PARK_X, max_x - 180.0)  # ≪500 (was max_x-80 → ~420)
    _p2_stop.set()  # pause p2 so orange cannot shove us right during park
    time.sleep(0.1)
    b_chk = read_me(mgr)
    if b_chk and valid_x(b_chk.get("me_x")) and b_chk["me_x"] > max_x:
        # face LEFT (A) then probe — but NEVER refuse here; pull loop is the hard park
        hold(mgr, 65, 0.22)
        ok_a, d_a = drive_ok(mgr, code=65, min_px=6.0, hold_s=0.45, max_abs=500.0)
        if not ok_a:
            print("prep_after_rebind A_probe_fail_continue", d_a, flush=True)
            hold(mgr, 68, 0.10)
            hold(mgr, 65, 0.25)
            # face-flip retry advisory only
            drive_ok(mgr, code=65, min_px=6.0, hold_s=0.55, max_abs=500.0)
    ensure_corridor(mgr, tries=6)
    for pull in range(40):
        b = read_me(mgr)
        if not b or not valid_x(b.get("me_x")):
            _ensure_p2()
            return False, None
        if b["me_x"] <= max_x:
            break
        try:
            p = read_pair_valid(mgr, tries=3)
            if p and valid_x(p.get("them_x")) and abs(p["them_x"] - b["me_x"]) < 260:
                # them blocking: keep A + short wait for p2 (paused — nudge them with arrows ourselves)
                hold(mgr, 37, 0.20)  # Left arrow on p2 slot via keymap? 37=Left in _KEYMAP for hold
                hold(mgr, 65, 0.45)
        except Exception:
            pass
        hold(mgr, 65, min(1.20, 0.22 + (b["me_x"] - max_x) / 180.0))
        if pull % 3 == 2:
            park(mgr, target=target, tol=35.0, tries=30)
    ok_park, park_x = park(mgr, target=target, tol=28.0, tries=120)
    b = read_me(mgr)
    if not b or not valid_x(b.get("me_x")):
        _ensure_p2()
        return False, park_x
    if b["me_x"] > max_x:
        ensure_corridor(mgr, tries=4)
        hold(mgr, 65, 1.8)
        park(mgr, target=target, tol=28.0, tries=60)
        b = read_me(mgr)
        if not b or not valid_x(b.get("me_x")) or b["me_x"] > max_x:
            print("prep_after_rebind still_too_right", None if not b else b.get("me_x"), flush=True)
            _ensure_p2()
            return False, None if not b else b.get("me_x")

    def _hard_repark(why=""):
        """Pull left until me≤max_x (T122037Z verify overshoot left park at 800–1300)."""
        for _ in range(25):
            bb = read_me(mgr)
            if not bb or not valid_x(bb.get("me_x")):
                return False, None
            if bb["me_x"] <= max_x:
                park(mgr, target=target, tol=28.0, tries=20)
                bb2 = read_me(mgr)
                return True, None if not bb2 else bb2.get("me_x")
            hold(mgr, 65, min(1.0, 0.25 + (bb["me_x"] - max_x) / 200.0))
        bb = read_me(mgr)
        ok = bool(bb and valid_x(bb.get("me_x")) and bb["me_x"] <= max_x)
        if not ok:
            print("prep_after_rebind still_too_right", None if not bb else bb.get("me_x"), why, flush=True)
        return ok, None if not bb else bb.get("me_x")

    def _face_d_verify():
        """Critic 13:37: short D left dme=0 at park≤500 (facing/bind dead, not tele).
        Prove bound responds (A -dme); face-D longer then repark; tap-D confirm +dme."""
        # 1) ensure bound inst responds before dose (A should pull left after park)
        ok_a, d_a = drive_ok(mgr, code=65, min_px=3.0, hold_s=0.20, max_abs=140.0)
        if not ok_a:
            print("prep_after_rebind bind_no_A_response", d_a, flush=True)
            bb0 = read_me(mgr)
            return False, d_a, None if not bb0 else bb0.get("me_x")
        ok_rp, _ = _hard_repark("post_A_prove")
        if not ok_rp:
            bb0 = read_me(mgr)
            return False, None, None if not bb0 else bb0.get("me_x")
        # 2) face RIGHT longer (0.55s) without committing verify walk; repark if shove >max_x
        hold(mgr, 68, 0.55)
        bb = read_me(mgr)
        if not bb or not valid_x(bb.get("me_x")):
            print("prep_after_rebind dead_me_after_park", None if not bb else bb.get("me_x"), flush=True)
            return False, None, None if not bb else bb.get("me_x")
        if bb["me_x"] > max_x:
            ok_rp, park_x = _hard_repark("post_face")
            if not ok_rp:
                return False, None, park_x
            hold(mgr, 68, 0.18)  # re-face after repark (short)
            bb = read_me(mgr)
            if not bb or not valid_x(bb.get("me_x")):
                print("prep_after_rebind dead_me_after_park", None if not bb else bb.get("me_x"), flush=True)
                return False, None, None if not bb else bb.get("me_x")
            if bb["me_x"] > max_x:
                print("prep_after_rebind still_too_right", bb["me_x"], flush=True)
                return False, None, bb["me_x"]
        # 3) tap-D confirm +dme (short; tight max_abs — not the old 0.55–0.70 tele hold)
        ok, dme = drive_ok(mgr, code=68, min_px=4.0, hold_s=0.22, max_abs=180.0)
        return ok, dme, bb.get("me_x")

    # Critic 12:50: rebind before verify must succeed or abort clean
    rb = rebind(mgr, hold_s=0.7, attempts=4)
    if rb is None:
        print("prep_after_rebind rebind_after_park_failed", flush=True)
        _ensure_p2()
        return False, b.get("me_x")
    ok_rp, park_at = _hard_repark("post_rebind")
    if not ok_rp:
        _ensure_p2()
        return False, park_at
    ok_d, d_d, park_at = _face_d_verify()
    if not ok_d:
        # one clean retry: rebind must succeed; short verify again (not long 0.70 hold)
        print("prep_after_rebind D_verify_retry", d_d, "park", park_at, flush=True)
        mgr.bound_inst = None
        time.sleep(0.2)
        rb2 = rebind(mgr, hold_s=0.9, attempts=4)
        if rb2 is None:
            print("prep_after_rebind rebind_after_park_failed", flush=True)
            _ensure_p2()
            return False, park_at
        ok_rp, park_at = _hard_repark("retry")
        if not ok_rp:
            _ensure_p2()
            return False, park_at
        # retry uses same face-longer + tap-D (not bare short hold)
        ok_d, d_d, park_at = _face_d_verify()
    if not ok_d:
        print("prep_after_rebind D_no_drive_after_park", d_d, flush=True)
        _ensure_p2()
        return False, park_at
    # Critic 12:50: hard repark ≤500 after verify shove
    ok_rp, park_at = _hard_repark("post_verify")
    if not ok_rp:
        _ensure_p2()
        return False, park_at
    hold(mgr, 68, 0.10)  # leave facing right without walking
    b = read_me(mgr)
    _ensure_p2()
    if not b or not valid_x(b.get("me_x")):
        print("prep_after_rebind dead_me_final", None if not b else b.get("me_x"), flush=True)
        return False, None if not b else b.get("me_x")
    if b["me_x"] > max_x:
        print("prep_after_rebind still_too_right", b["me_x"], flush=True)
        return False, b["me_x"]
    return True, b["me_x"]

def recover_bind(mgr):
    mgr.bound_inst = None
    time.sleep(0.4)
    for round_i in range(3):
        print("recover_bind round", round_i, flush=True)
        b = rebind(mgr, hold_s=1.2, attempts=4)
        if b:
            return b
        try:
            n.key(IID, "d", hold=0.2); time.sleep(0.2)
            n.key(IID, "a", hold=0.2)
            n.key(IID, "Right", hold=0.15)
        except Exception:
            pass
        time.sleep(0.5)
    return None

def dose_one(mgr, N):
    last = {"N": N, "fail": "retries_exhausted"}
    for attempt in range(4):
        if mgr.bound_inst is None:
            if not recover_bind(mgr):
                print("dose", N, "attempt", attempt, "no_bind_recover", flush=True)
                last = {"N": N, "attempt": attempt, "fail": "no_bind"}
                continue
        ok_park, park_x = park(mgr)
        if not ok_park or park_x is None or park_x > 700:
            hold(mgr, 65, 1.0)
            ok_park, park_x = park(mgr)
        clear = ensure_corridor(mgr)
        ok_park, park_x = park(mgr)
        if not rebind(mgr):
            print("dose", N, "attempt", attempt, "rebind_before_hold_failed", flush=True)
            if not recover_bind(mgr):
                last = {"N": N, "attempt": attempt, "fail": "no_bind"}
                continue
        # dose-fix: face-right + hard park me_x≲500 before b0
        ok_prep, park_x = prep_after_rebind(mgr, max_x=500.0)
        if not ok_prep:
            print("dose", N, "attempt", attempt, "prep_fail", park_x, flush=True)
            mgr.bound_inst = None
            last = {"N": N, "attempt": attempt, "fail": "prep_fail", "park_x": park_x}
            continue
        ok_park = True
        b0 = read_me(mgr)
        p0 = read_pair_valid(mgr)
        if not b0 or not p0 or not valid_x(b0.get("me_x")) or not valid_x(p0.get("them_x")):
            print("dose", N, "attempt", attempt, "no_state_pre_or_bad_me", b0, flush=True)
            mgr.bound_inst = None
            last = {"N": N, "attempt": attempt, "fail": "bad_me_pre"}
            continue
        if b0["me_x"] > 500:
            print("dose", N, "attempt", attempt, "start_too_right", b0["me_x"], flush=True)
            hold(mgr, 65, 1.2)
            mgr.bound_inst = None
            continue
        # Critic 02:00: short D→+dme check, then re-park me≲500 before dose (0.9s overshot 127→655 → dme_le_0)
        _p2_stop.set()  # pause arrow nudge so it cannot cancel D
        time.sleep(0.15)
        # Critic 10:33: max_abs=280 rejected real D +386 as tele/no_drive — allow up to ~700 on short probe
        ok_drv, d_drv = drive_ok(mgr, code=68, min_px=4.0, hold_s=0.28, max_abs=700.0)
        if not ok_drv:
            print("dose", N, "attempt", attempt, "no_drive_pre", d_drv, flush=True)
            mgr.bound_inst = None
            _ensure_p2()
            last = {"N": N, "attempt": attempt, "fail": "no_drive", "dme_probe": d_drv, "park_x": park_x}
            continue
        # re-park left after drive probe so dose baseline is me≲500 facing right
        ok_re, park_x = prep_after_rebind(mgr, max_x=500.0)
        if not ok_re:
            print("dose", N, "attempt", attempt, "repark_fail", park_x, flush=True)
            mgr.bound_inst = None
            _ensure_p2()
            last = {"N": N, "attempt": attempt, "fail": "prep_fail", "park_x": park_x}
            continue
        b0 = read_me(mgr)
        p0 = read_pair_valid(mgr)
        if not b0 or not p0 or not valid_x(b0.get("me_x")):
            print("dose", N, "attempt", attempt, "bad_me_after_drive", b0, flush=True)
            mgr.bound_inst = None
            _ensure_p2()
            last = {"N": N, "attempt": attempt, "fail": "bad_me_pre"}
            continue
        if b0["me_x"] > 500:
            print("dose", N, "attempt", attempt, "too_right_after_drive", b0["me_x"], flush=True)
            hold(mgr, 65, 1.0)
            mgr.bound_inst = None
            _ensure_p2()
            last = {"N": N, "attempt": attempt, "fail": "prep_fail", "park_x": b0["me_x"]}
            continue
        hold(mgr, 68, max(N * STEP, 0.55))  # continuous RIGHT (v5j floor 0.55s)
        b1 = read_me(mgr)
        p1 = read_pair_valid(mgr)
        if not b1 or not valid_x(b1.get("me_x")):
            print("dose", N, "attempt", attempt, "garbage_after_or_me_-1", b1, flush=True)
            mgr.bound_inst = None
            last = {"N": N, "attempt": attempt, "fail": "bad_me_post"}
            continue
        dme = b1["me_x"] - b0["me_x"]
        dthem = (p1["them_x"] - p0["them_x"]) if p1 else None
        teleport = abs(dme) > TELEPORT_PX or abs(b1["me_x"]) > 3000
        row = {"N": N, "attempt": attempt, "park": ok_park, "park_x": park_x, "clear": clear,
               "me0": b0["me_x"], "me1": b1["me_x"], "dme": dme,
               "them0": p0["them_x"], "them1": (p1 or {}).get("them_x"), "dthem": dthem,
               "teleport": teleport, "hold_s": max(N * STEP, 0.55), "bound": mgr.bound_inst}
        print("dose", row, flush=True)
        _ensure_p2()  # resume p2 nudge after dose hold
        # hard-fail wrong-way / tiny / garbage (dose-fix)
        if teleport or dme <= 0:
            print("dose", N, "attempt", attempt, "hard_fail_dme", dme, flush=True)
            mgr.bound_inst = None
            last = row
            last["fail"] = "dme_le_0" if dme <= 0 else "teleport"
            continue
        if dme <= 5:
            mgr.bound_inst = None
            last = row
            continue
        return row
    return last

def wall_central(wall, frame_w=320.0, lo=0.35, hi=0.65):
    """Reject edge false-walls (e.g. 8.5/18); READY centre wall is near mid (~180 on 320)."""
    if wall is None:
        return False
    return (lo * frame_w) <= float(wall) <= (hi * frame_w)

def wall_gate(max_loops=15):
    """Critic 19:26/19:31: fighters + CENTRAL wall before enter_match_v2. No TRAINING/Up."""
    trace = []
    for i in range(max_loops):
        fv = bool(ns._fighters_visible(IID, f"wg_fv{i}"))
        wall = ns._wall_x(IID, f"wg_w{i}")
        ready = bool(ns.on_ready_screen(IID)) if hasattr(ns, "on_ready_screen") else None
        # measure frame width when possible
        fr = ns.frame(IID, f"wg_fw{i}")
        fw = float(fr.shape[1]) if fr is not None else 320.0
        central = wall_central(wall, fw)
        row = {"i": i, "fighters": fv, "wall": wall, "central": central, "on_ready": ready, "fw": fw}
        print("wall_gate", row, flush=True)
        trace.append(row)
        if fv and central:
            return True, wall, trace
        # Escape toward menu, then Return x3 (MULTIPLAYER default — never Up)
        n.key(IID, "Escape", hold=0.12); time.sleep(0.9)
        n.key(IID, "Escape", hold=0.12); time.sleep(0.9)
        for _ in range(3):
            n.key(IID, "Return", hold=0.12); time.sleep(1.1)
        # also try enter_ready presses if still no wall
        if ns._wall_x(IID, f"wg_mid{i}") is None:
            ns.enter_ready(IID, tries=4, wait=0.9)
    last_wall = trace[-1].get("wall") if trace else None
    return False, last_wall, trace

def write_out(out):
    open(OUT, "w").write(json.dumps(out, indent=2) + "\n")
    print("WROTE", OUT, flush=True)

def main():
    out = {"ok": False, "probe": "i1_fighter_identity_v5q", "step_s": STEP, "park_x": PARK_X,
           "entry_family": "enter_match_v2"}
    try:
        out["game_pid"] = n._game_pid(IID)
    except Exception as e:
        out["game_pid_err"] = repr(e)
    print("game_pid", out.get("game_pid"), flush=True)

    print("wall_gate then enter_match_v2 — not run_entry/TRAINING", flush=True)
    ok_gate, wall, trace = wall_gate()
    out["wall_gate"] = {"ok": ok_gate, "wall": wall, "trace": trace[-4:]}
    if not ok_gate:
        # Critic 00:16: do not mislabel fighters=False + central wall as wall_null
        last = (trace[-1] if trace else {}) or {}
        if last.get("wall") is not None and last.get("central") and not last.get("fighters"):
            fail = "no_fighters"
        elif last.get("wall") is not None and not last.get("central"):
            fail = "wall_not_central"
        elif last.get("wall") is None:
            fail = "wall_null"
        else:
            fail = "wall_gate_fail"
        out["fail"] = fail
        write_out(out)
        print(json.dumps(out, indent=2), flush=True)
        print(f"BLOCKER {fail} — refused enter_match_v2", flush=True)
        return 3

    try:
        entered = bool(ns.enter_match_v2(IID, verbose=True))
    except Exception as e:
        out["enter_err"] = f"{type(e).__name__}:{e}"
        entered = False
    out["entry"] = "enter_match_v2" if entered else None
    print("entry", entered, "in_match", ns.in_match(IID), flush=True)
    if not entered or not ns.in_match(IID):
        out["fail"] = "enter_or_in_match_false"
        write_out(out)
        print(json.dumps(out, indent=2), flush=True)
        return 2

    t = threading.Thread(target=p2_nudge_loop, daemon=True, name="p2_nudge")
    t.start()
    mgr = ts.InstanceManager(IID)
    mgr.started_at = time.monotonic()
    # Critic 00:48: room file was stale(=2) while nidmem room=29 → refuse bind
    ok_ar, room_now = wait_arena(mgr, timeout=15.0)
    out["room_after_entry"] = room_now
    out["in_arena"] = bool(ok_ar)
    if not ok_ar:
        out["fail"] = "not_arena_after_entry"
        _p2_stop.set()
        write_out(out)
        print(json.dumps(out, indent=2), flush=True)
        return 1
    bound = recover_bind(mgr) or rebind(mgr)
    out["bound_inst"] = bound
    if not bound:
        out["fail"] = "bind_failed"
        _p2_stop.set()
        write_out(out)
        print(json.dumps(out, indent=2), flush=True)
        return 1

    samples = []
    t0 = time.time()
    while time.time() - t0 < 8.0:
        p = read_pair_valid(mgr)
        if p:
            me = (round(p["me_x"], 1), round(p["me_y"], 1))
            them = (round(p["them_x"], 1), round(p["them_y"], 1))
            samples.append({"t": round(time.time() - t0, 2), "me": me, "them": them, "eq": me == them})
        time.sleep(0.2)
    eq_n = sum(1 for s in samples if s["eq"])
    out["stability"] = {"n": len(samples), "me_eq_them": eq_n, "head": samples[:2], "tail": samples[-2:]}
    out["stable_ok"] = len(samples) >= 20 and eq_n == 0
    print("stable_ok", out["stable_ok"], eq_n, len(samples), flush=True)

    doses = []
    for N in (5, 10, 20):
        row = dose_one(mgr, N)
        doses.append(row)
        out["doses"] = doses
        write_out(out)  # rewrite after each N so mid-death is not stale
    out["doses"] = doses
    valid = [d for d in doses if "dme" in d and not d.get("teleport") and not d.get("fail") and d["dme"] > 5]
    dmes = [d["dme"] for d in valid]
    dthems = [d["dthem"] for d in valid if d.get("dthem") is not None]
    Ns = [d["N"] for d in valid]
    mono = Ns == [5, 10, 20] and len(dmes) == 3 and dmes[0] > 5 and dmes[1] > dmes[0] and dmes[2] > dmes[1]
    them_uncorr = not (len(dthems) == 3 and dthems[0] > 5 and dthems[1] > dthems[0] and dthems[2] > dthems[1])
    out["mono"] = mono
    out["them_uncorr"] = them_uncorr
    out["dose_ok"] = bool(mono and them_uncorr)
    out["ok"] = bool(out["stable_ok"] and out["dose_ok"])
    _p2_stop.set()
    write_out(out)
    print(json.dumps(out, indent=2), flush=True)
    return 0 if out["ok"] else 1

if __name__ == "__main__":
    import signal
    def _die(sig, frame):
        print("SIGNAL", sig, flush=True)
        raise SystemExit(128+sig)
    signal.signal(signal.SIGTERM, _die)
    signal.signal(signal.SIGINT, _die)
    sys.exit(main())
