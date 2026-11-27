#!/usr/bin/env python3
"""READY-nav aligned with wall_gate predicates (Critic 00:16/00:23).

nav_ok ≡ ns._fighters_visible AND central _wall_x AND on_ready_screen.
yel/ora/blu crumb counts are DIAG ONLY — must NOT pass nav_ok.
If P1 is blue (prefs p1_color≠1), write muted prefs (yellow/orange) + restart,
then Escape/Return → enter_ready until nav_ok.
No TRAINING.
"""
import os, sys, json, time
sys.path.insert(0, os.environ.get("CODE_PAU", "/home/ruggsea/nf-p/code_pau"))
import nidlinux as n, nidstate as ns
try:
    import nidmem_room as mr
except Exception:
    mr = None

IID = int(os.environ.get("NID_IID", "0"))
ART = os.environ.get("NIDART", "/home/ruggsea/nf-p/pau86/art")
RUN = os.environ.get("NIDRUN", "/home/ruggsea/nf-p/pau86/results/runs")
PREFS = os.environ.get(
    "NID_PREFS",
    "/home/ruggsea/nf-p/pau86/inst/0/pfx/drive_c/users/steamuser/AppData/Roaming/Nidhogg/prefs.ini",
)
MUTED = os.environ.get("NID_MUTED", "/home/ruggsea/nf-p/code_pau/prefs_muted.ini")
FW = 320.0
stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())


def room():
    try:
        return mr.read_room(IID) if mr else None
    except Exception as e:
        return str(e)


def wall_central(wall, frame_w=FW, lo=0.35, hi=0.65):
    if wall is None:
        return False
    return (lo * frame_w) <= float(wall) <= (hi * frame_w)


def crumb_counts(a):
    """DIAG-only colour crumbs (must not gate)."""
    r, g, b = (a[:, :, k].astype(int) for k in range(3))
    h = a.shape[0]

    def band(m):
        m = m.copy()
        m[int(h * 0.62):, :] = False
        return int(m.sum())

    return {
        "yel": band((r > 240) & (g > 240) & (b < 80)),
        "ora": band((r > 200) & (g > 120) & (g < 205) & (b < 110)),
        "blu": band((b > 160) & (r < 140) & (g > 60) & (g < 220)),
    }


def snapshot(tag):
    try:
        pid = n._game_pid(IID)
    except Exception as e:
        pid = None
        print("snapshot no_pid", tag, repr(e), flush=True)
    if not pid:
        row = {"tag": tag, "fv": False, "ready": False, "wall": None, "central": False,
               "nav_ok": False, "wall_gate_ok": False, "err": "no_game_pid"}
        print("SNAP", json.dumps(row, default=str), flush=True)
        return row
    a = ns.frame(IID, f"nav_{tag}")
    wall = ns._wall_x(IID, f"nav_w_{tag}")
    fr = ns.frame(IID, f"nav_fw_{tag}")
    fw = float(fr.shape[1]) if fr is not None else FW
    fv = bool(ns._fighters_visible(IID, f"nav_fv_{tag}"))
    ready = bool(ns.on_ready_screen(IID))
    crumbs = crumb_counts(a) if a is not None else {"yel": None, "ora": None, "blu": None}
    central = wall_central(wall, fw)
    nav_ok = bool(fv and central and ready)
    wall_gate_ok = bool(fv and central)
    try:
        mstate = ns.match_state(IID)
    except Exception as e:
        mstate = f"err:{type(e).__name__}"
    try:
        geo = ns.menu_geometry(IID, f"nav_g_{tag}")
    except Exception:
        geo = None
    row = {
        "tag": tag,
        "fv": fv,
        "ready": ready,
        "wall": wall,
        "central": central,
        "fw": fw,
        "yel": crumbs.get("yel"),
        "ora": crumbs.get("ora"),
        "blu": crumbs.get("blu"),
        "match_state": mstate,
        "room": room(),
        "geo": geo,
        "wall_gate_ok": wall_gate_ok,
        "nav_ok": nav_ok,
        "game_pid": pid,
    }
    print("SNAP", json.dumps(row, default=str), flush=True)
    return row


def set_yel_ora_from_color_menu():
    print("set pL yellow", flush=True)
    for _ in range(12):
        n.key(IID, "Left", hold=0.08)
        time.sleep(0.12)
    n.key(IID, "Down", hold=0.1)
    time.sleep(0.35)
    print("set pR orange", flush=True)
    for _ in range(12):
        n.key(IID, "Left", hold=0.08)
        time.sleep(0.12)
    n.key(IID, "Right", hold=0.1)
    time.sleep(0.25)
    print("BACK via Return", flush=True)
    n.key(IID, "Return", hold=0.12)
    time.sleep(1.0)


def prefs_restart_yellow():
    print("prefs_restart → muted yellow/orange", flush=True)
    try:
        os.chmod(PREFS, 0o644)
    except Exception as e:
        print("chmod", e, flush=True)
    open(PREFS, "w").write(open(MUTED).read())
    print("prefs", [l.strip() for l in open(PREFS) if "color" in l], flush=True)
    n.stop_id(IID)
    time.sleep(2)
    n.start_ids([IID])
    t0 = time.time()
    pid = None
    while time.time() - t0 < 120:
        pid = n._game_pid(IID)
        if pid:
            break
        time.sleep(2)
    print("game_pid_after", pid, "wait_s", round(time.time() - t0), flush=True)
    time.sleep(12)
    return pid


def settle_ready(max_loops=10):
    c = snapshot("settle0")
    for i in range(max_loops):
        if c.get("nav_ok"):
            return c
        # color overlay path
        if c.get("geo") is not None and not c.get("central"):
            print("overlay: try color/Back", flush=True)
            n.key(IID, "z", hold=0.0)
            time.sleep(0.8)
            if ns.menu_geometry(IID, f"ov{i}") is not None:
                set_yel_ora_from_color_menu()
            n.key(IID, "x", hold=0.0)
            time.sleep(0.7)
            n.key(IID, "Return", hold=0.12)
            time.sleep(0.8)
            c = snapshot(f"ov{i}")
            continue
        n.key(IID, "Escape", hold=0.12)
        time.sleep(0.8)
        n.key(IID, "Escape", hold=0.12)
        time.sleep(0.8)
        for _ in range(3):
            n.key(IID, "Return", hold=0.12)
            time.sleep(0.9)
        er = ns.enter_ready(IID, tries=3, wait=0.8)
        print("enter_ready", er, flush=True)
        c = snapshot(f"settle{i+1}")
    return c


def main():
    os.makedirs(ART, exist_ok=True)
    os.makedirs(RUN, exist_ok=True)
    print("game_pid", n._game_pid(IID), "win", n.window(IID), flush=True)
    n._focus(IID)
    time.sleep(0.2)

    c = snapshot("pre")
    n.grab(IID, f"{ART}/i1_nav_pre_{stamp}.png")

    # Wrong P1 colour (blue) → prefs restart to yellow/orange. Do NOT restart merely for missing ora/wall.
    p1_blue = (c.get("blu") or 0) > 40 and (c.get("yel") or 0) < 20
    if p1_blue:
        if c.get("geo") is not None:
            set_yel_ora_from_color_menu()
            c = snapshot("after_color")
        if (c.get("blu") or 0) > 40 and (c.get("yel") or 0) < 20:
            prefs_restart_yellow()
            c = snapshot("post_restart")

    c = settle_ready(max_loops=12)
    # last chance color fix if wall held but still no yellow fighters
    if c.get("central") and not c.get("fv"):
        print("wall held, force color menu", flush=True)
        n.key(IID, "Escape", hold=0.12)
        time.sleep(0.9)
        n.key(IID, "z", hold=0.0)
        time.sleep(0.7)
        set_yel_ora_from_color_menu()
        n.key(IID, "x", hold=0.0)
        time.sleep(0.7)
        c = settle_ready(max_loops=6)

    final = snapshot("final")
    shot = n.grab(IID, f"{ART}/i1_nav_ready_{stamp}.png")
    out = {
        "nav_ok": bool(final.get("nav_ok")),
        "wall_gate_ok": bool(final.get("wall_gate_ok")),
        "state": {
            "ready": final.get("ready"),
            "fv": final.get("fv"),
            "wall": final.get("wall"),
            "central": final.get("central"),
            "yel": final.get("yel"),
            "ora": final.get("ora"),
            "blu": final.get("blu"),
            "match_state": final.get("match_state"),
            "room": final.get("room"),
        },
        "screenshot": shot,
        "game_pid": n._game_pid(IID),
        "stamp": stamp,
        "note": "aligned nav_ok≡fv+central+on_ready; prefs yellow if blue; Critic 00:23",
    }
    path = f"{RUN}/i1_nav_ready_{stamp}.json"
    open(path, "w").write(json.dumps(out, indent=2) + "\n")
    open(f"{RUN}/i1_nav_ready_latest.json", "w").write(json.dumps(out, indent=2) + "\n")
    print("WROTE", path, flush=True)
    print(
        "NAV_RESULT",
        json.dumps(
            {"nav_ok": out["nav_ok"], "wall_gate_ok": out["wall_gate_ok"], **out["state"]},
            default=str,
        ),
        flush=True,
    )
    raise SystemExit(0 if out["nav_ok"] else 2)


if __name__ == "__main__":
    main()
