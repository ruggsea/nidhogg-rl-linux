"""Record how the game launcher ends: exit code or signal of every proton process this Python starts,
with the game's last published state and the Wine log tail.

install() replaces subprocess.Popen with a subclass that, for a command containing 'proton', starts
a thread waiting on it and appends one row to $NIDFARM/launcher_exits.jsonl when it ends:
  t, pid, returncode, signal (returncode < 0), alive_s, cmd,
  game_pid (last Nidhogg.exe of this farm seen by a 5 s poller), state_age_s and last_state (the
  spy's state file of that pid: tick, fighters, room), wine_tail (last 25 lines of logs/py_0.log).
Other commands are untouched. nidlinux.start_ids discards its Popen object; this keeps a reference,
so the exit status is not lost to subprocess's background reaping.
"""
import json, os, signal, struct, subprocess, threading, time
from pathlib import Path

FARM = Path(os.environ.get("NIDFARM") or (Path.home() / ".nidfarm"))
_Popen = subprocess.Popen
_last_game = {"pid": None}


def _farm_game_pid():
    tag = f"NIDFARM={FARM}\0".encode()
    for d in Path("/proc").iterdir():
        if not d.name.isdigit():
            continue
        try:
            if (d / "comm").read_text().strip() == "Nidhogg.exe" and tag in (d / "environ").read_bytes():
                return int(d.name)
        except OSError:
            continue
    return None


def _poll():
    while True:
        pid = _farm_game_pid()
        if pid:
            _last_game["pid"] = pid
        time.sleep(5)


def _last_state(pid):
    p = Path(f"/tmp/nid_state_{pid}")
    if not pid or not p.exists():
        return None, None
    import nidlinux  # same STATE_FMT as the spy
    raw = p.read_bytes()
    age = round(time.time() - p.stat().st_mtime, 2)
    if len(raw) != nidlinux.STATE_SIZE:
        return age, f"bad size {len(raw)}"
    f = struct.unpack(nidlinux.STATE_FMT, raw)
    return age, {"seq": f[2], "tick": f[4], "flags": f[5], "p1": [round(f[6], 1), round(f[7], 1), f[9]],
                 "p2": [round(f[10], 1), round(f[11], 1), f[13]], "room": f[14]}


class _Tracked(_Popen):
    def __init__(self, args, *a, **k):
        super().__init__(args, *a, **k)
        if "proton" in " ".join(map(str, args if isinstance(args, (list, tuple)) else [args])):
            threading.Thread(target=self._watch, args=(time.time(), args), daemon=True).start()

    def _watch(self, t0, args):
        rc = self.wait()
        gpid = _last_game["pid"]
        row = {"t": time.strftime("%Y-%m-%dT%H:%M:%S"), "pid": self.pid, "returncode": rc,
               "signal": signal.Signals(-rc).name if rc < 0 else None, "alive_s": round(time.time() - t0),
               "cmd": " ".join(map(str, args))[-80:], "game_pid": gpid}
        try:
            row["state_age_s"], row["last_state"] = _last_state(gpid)
        except Exception as e:                 # the exit row must be written even if this fails
            row["last_state"] = f"unreadable: {e}"
        log = FARM / "logs" / "py_0.log"
        row["wine_tail"] = log.read_text(errors="replace").splitlines()[-25:] if log.exists() else None
        with open(FARM / "launcher_exits.jsonl", "a") as f:
            f.write(json.dumps(row) + "\n")


def install():
    if subprocess.Popen is not _Tracked:
        subprocess.Popen = _Tracked
        threading.Thread(target=_poll, daemon=True).start()
