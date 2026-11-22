"""Failure snapshots for hangs and 'no record' resets: what was running when it happened.

diag.snapshot(env, kind, why) appends one row to $NIDFARM/diag.jsonl:
  pids    every process whose environ holds this farm's NIDFARM: pid, state (R/S/D/Z/T from
          /proc/<pid>/stat), wchan, cpu seconds, cmdline (cut)
  game    the farm's Nidhogg.exe pid, spy ping answer, age of the spy state file (s), last state
          sample (tick, seq, both fighters' x/y/anim), room index
  window  xdotool search --name Nidhogg on the farm's display, and the display geometry
  recs    (kind 'no_record') fighter-type records from a heap scan with x/y, m.rec, m.dead
  frame   path of a screenshot of the display, when one can be taken
Every probe is wrapped on its own: a dead game must still give a row (the failing field says why).
"""
import json, os, subprocess, time
from pathlib import Path

FARM = Path(os.environ.get("NIDFARM") or (Path.home() / ".nidfarm"))
DISP = f":{int(os.environ.get('NID_DISPLAY_BASE', '0'))}"


def _try(f):
    try:
        return f()
    except Exception as e:                      # a snapshot field that cannot be read says why
        return f"unreadable: {type(e).__name__}: {str(e)[:200]}"


def _procs():
    out = []
    for p in os.listdir("/proc"):
        if not p.isdigit():
            continue
        try:
            if f"NIDFARM={FARM}\0".encode() not in Path(f"/proc/{p}/environ").read_bytes():
                continue
            st = Path(f"/proc/{p}/stat").read_text().rsplit(")", 1)[1].split()
            out.append({"pid": int(p), "state": st[0], "cpu_s": round((int(st[11]) + int(st[12])) / 100, 1),
                        "wchan": Path(f"/proc/{p}/wchan").read_text()[:40],
                        "cmd": Path(f"/proc/{p}/cmdline").read_bytes().replace(b"\0", b" ").decode()[:90]})
        except OSError:
            continue
    return out


def snapshot(env, kind, why):
    from nidmem import n, s
    row = {"t": time.strftime("%Y-%m-%dT%H:%M:%S"), "kind": kind, "why": str(why)[:2000],
           "i": getattr(env, "count", None), "pids": _try(_procs)}
    pid = _try(lambda: n._game_pid(0))
    row["game_pid"] = pid
    if isinstance(pid, int):
        row["spy_ping"] = _try(lambda: n.ping(pid))
        row["state_file_age_s"] = _try(lambda: round(time.time() - os.path.getmtime(f"/tmp/nid_state_{pid}"), 2))
        st = _try(lambda: n.state(pid))
        row["last_state"] = st if isinstance(st, str) else (st and {k: getattr(st, k) for k in (
            "tick", "seq", "p1_x", "p1_y", "p1_anim", "p2_x", "p2_y", "p2_anim")})
    row["window"] = _try(lambda: subprocess.run(["xdotool", "search", "--name", "Nidhogg"],
                                                env=dict(os.environ, DISPLAY=DISP), capture_output=True,
                                                text=True, timeout=10).stdout.split())
    row["display"] = _try(lambda: subprocess.run(["xdotool", "getdisplaygeometry"], env=dict(os.environ, DISPLAY=DISP),
                                                 capture_output=True, text=True, timeout=10).stdout.strip())
    inner = getattr(env, "env", None)
    m = getattr(inner, "m", None)
    if m is not None:
        row["room"] = _try(lambda: m.room_log[-1][1] if m.room_log else None)
        row["m_rec"] = _try(lambda: {w: r and hex(r) for w, r in m.rec.items()})
        row["m_dead"] = _try(lambda: [hex(a) for a in m.dead])
        if kind == "no_record":
            row["type_records"] = _try(lambda: {hex(a): [round(x, 1), round(y, 1)] for a, (x, y) in m.type_records().items()})
    name = f"diag_{kind}_{int(time.time())}"
    row["frame"] = _try(lambda: (s.frame(0, name), name + ".png")[1])
    with open(FARM / "diag.jsonl", "a") as f:
        f.write(json.dumps(row, default=str) + "\n")
    return row
