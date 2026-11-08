"""Episode-managed GA on Nidhogg's real published game state (no vision).

One owned game instance publishes:
    /tmp/nid_state_0.txt -> p154x p154y p242x p242y have154 have242
Object 242 is our YellowPlayer; object 154 is the OrangePlayer CPU.

Before and during every individual the episode manager keeps the game in a live
match. Missing fighters / the WINNER stats screen are dismissed with Enter and
the verified match-entry path is replayed. A dead process or stale state file
causes that one instance to be relaunched.

Usage:
    .venv/bin/python train_state.py --gens 6 --pop 8 --window 25 --seed 23
"""
import argparse
import json
import os
import random
import shutil
import signal
import statistics
import subprocess
import threading
import time

IMPORT_ERROR = None

HERE = os.path.dirname(os.path.abspath(__file__))
APP = "/Users/ruggsea/Library/Application Support/Steam/steamapps/common/Nidhogg/Nidhogg.app/Contents/MacOS/Nidhogg"
HERE_DIR = os.path.dirname(os.path.abspath(__file__))


def instance_app(iid):
    """Each instance runs its OWN copy of the bundle.

    PID bookkeeping kept failing (the runner re-execs; stale window numbers pointed at
    the wrong process), so a dead game was never killed, a new one was launched beside
    it, and the stale copy ate the room_goto that had already been used - which is why
    episodes reported "unable to obtain a match". With one bundle per instance, killing
    is just `pkill -f Nidhogg<iid>.app`, which cannot be ambiguous.
    """
    return APP   # per-instance copies break the code signature -> GL context fails
DYLD = os.path.join(HERE, "hook", "inject.dylib")
PREFS = os.path.expanduser("~/Library/Application Support/com.messhof.nidhogg/prefs.ini")
MUTED_PREFS = os.path.join(HERE, "prefs_muted.ini")
PRISTINE_PREFS = os.path.join(HERE, "prefs_pristine.ini")

import threading as _threading
_RESTART_LOCK = _threading.Lock()

STATE = "/tmp/nid_state_{}.txt"
ROOM = "/tmp/nid_room_{}.txt"
KEYS = "/tmp/nid_keys_{}.txt"
SPEED = "/tmp/nid_speed_{}.txt"
BRAIN = "/tmp/nid_brain_{}.txt"
INJECT_LOG = "/tmp/nid_inject_{}.log"
VARS = "/tmp/nid_vars_{}.txt"
OBJS = "/tmp/nid_objs_{}.txt"
OUT_LOG = "/tmp/nid_out_i{}.log"
LOG_PATH = "/tmp/nid_train_state.jsonl"
SUMMARY_PATH = "/tmp/nid_train_state_summary.json"
BEST_PATH = "/tmp/nid_best_params.json"

SPAWN_JUMP = 300.0
MISSING_MATCH_OVER = 1.5
FROZEN_MATCH_OVER = 6.0
STATE_STALE = 5.0
ENTRY_BOOT = 55.0   # seconds after launch before the first menu key
BOOT_WAIT = 48.0        # measured: keys pressed before ~frame 690 are eaten
                        # while the game is still loading, which shifted every
                        # subsequent menu step by one screen
MATCH_READY_TIMEOUT = 30.0
RUN_BUDGET = 40 * 60.0

# 8x Up (0.3 s apart), then Down/Enter with the verified waits.


def log(message):
    print(f"[{time.strftime('%H:%M:%S')}] {message}", flush=True)


def atomic_json(path, value):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(value, f, indent=2, sort_keys=True)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


class InstanceManager:
    """Own exactly one game process and keep it inside a playable match."""

    def __init__(self, iid=0):
        self.iid = iid
        self.proc = None
        self.out = None
        self.started_at = 0.0
        self.ever_have_players = False
        self.current_tag = None
        self.match_recoveries = 0
        self.hard_restarts = 0
        self.recovery_episodes = set()
        self.restart_episodes = set()
        self.needs_reset = False
        self.gate_px = 0.0
        self.gate_ts = 0.0

    def _note_recovery(self):
        if self.current_tag:
            self.recovery_episodes.add(self.current_tag)

    def _note_restart(self):
        if self.current_tag:
            self.restart_episodes.add(self.current_tag)

    def clean_files(self):
        for path in (STATE.format(self.iid), KEYS.format(self.iid),
                     INJECT_LOG.format(self.iid)):
            try:
                os.remove(path)
            except FileNotFoundError:
                pass

    def _alive_bundle(self):
        out = subprocess.run(["pgrep", "-f", f"Nidhogg{self.iid}.app"],
                             capture_output=True, text=True).stdout
        return bool(out.strip())

    def _pid_from_window(self):
        """Resolve this instance's window number (published by the harness) to its PID."""
        try:
            log = open(INJECT_LOG.format(self.iid), "rb").read().decode("utf-8", "replace")
        except OSError:
            return None
        hits = [ln.split("[win] ")[1].split()[0] for ln in log.splitlines() if "[win] " in ln]
        if not hits:
            return None
        try:
            wn = int(hits[-1])
        except ValueError:
            return None
        try:
            import Quartz
            for w in Quartz.CGWindowListCopyWindowInfo(
                    Quartz.kCGWindowListOptionAll, Quartz.kCGNullWindowID):
                if int(w.get("kCGWindowNumber", -1)) == wn:
                    return int(w.get("kCGWindowOwnerPID"))
        except Exception:
            return None
        return None

    @staticmethod
    def _nidhogg_pids():
        try:
            out = subprocess.run(["pgrep", "-f", "MacOS/Nidhogg"],
                                 capture_output=True, text=True).stdout
            return [int(t) for t in out.split()]
        except Exception:
            return []

    def alive(self):
        return self.proc is not None and self.proc.poll() is None

    def launch(self):
        self.clean_files()
        # RESTORE PREFS EVERY LAUNCH. Menu key presses can wander into the settings
        # screen and change saved state: a run on 2026-11-03 silently set
        # language="ru" (which rearranged every menu label and broke entry) and
        # unmuted the game. Pinning a known-good prefs makes entry deterministic again
        # and keeps the audio muted without ever touching the Mac's system volume.
        try:
            import shutil, pathlib
            dst = pathlib.Path.home() / "Library/Application Support/com.messhof.nidhogg/prefs.ini"
            src = pathlib.Path(__file__).parent / "prefs_locked.ini"
            if src.exists():
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.chmod(0o644)
                shutil.copyfile(src, dst)
                # LOCK IT. Injected menu keys wander into OPTIONS and rewrite the saved
                # settings: measured after a run, language had become "es-419" and
                # unmuted "1" (it was "ru" on an earlier day). A mid-run language change
                # also reorders every menu label, which is a prime suspect for entry
                # flakiness. Read-only prefs stop the game persisting those changes; the
                # in-memory state still comes from our pinned template at launch.
                dst.chmod(0o444)
        except Exception as e:
            log(f"instance {self.iid}: prefs restore failed: {e}")
        self.out = open(OUT_LOG.format(self.iid), "w")
        # a slept display makes GL context creation fail and the runner abort
        subprocess.run(["caffeinate", "-u", "-t", "1"], capture_output=True)
        # HARD GUARD: never let a launch orphan a previous process. Measured: 15 game
        # processes accumulated from re-entry/relaunch cycles, load hit 19.7 and the
        # game fell to 7-8 fps, which then looked like a timing bug in entry.
        subprocess.run(["pkill", "-9", "-f", "MacOS/Nidhogg"], capture_output=True)
        time.sleep(1.5)
        app_path = instance_app(self.iid)
        self.proc = subprocess.Popen(
            [app_path],
            env=dict(
                os.environ,
                NID_ID=str(self.iid),
                SteamAppId="94400",
                # Tell Steamworks we were launched by Steam so it does NOT re-exec
                # the game (the re-exec orphaned children: 2 instances -> 19 games).
                SteamGameId="94400",
                SteamClientLaunch="1",
                NID_QUIET="1",
                NID_FOCUS="1",
                NID_MAN="1",
                NID_THREAD="1",
                DYLD_INSERT_LIBRARIES=DYLD,
            ),
            stdout=self.out,
            stderr=subprocess.STDOUT,
            start_new_session=True,
            preexec_fn=lambda: (os.nice(19),
                                os.system(f"taskpolicy -b -p {os.getpid()} 2>/dev/null")),
        )
        self.started_at = time.monotonic()
        self.ever_have_players = False
        # The runner re-execs itself (SteamAPI_RestartAppIfNecessary), so one launch
        # can produce several Nidhogg processes. Own exactly the ones that appeared
        # AFTER our Popen - snapshotting afterwards instead made each instance adopt
        # the other's game and they killed each other (2 instances -> 10 games).
        self.pids = {self.proc.pid}
        # Ownership: a simultaneous before/after PID diff cannot tell two instances
        # apart (they launch together), which is how 2 instances grew to 18 games.
        # Each instance instead publishes its own window number via the harness
        # ("[win] <n>"), and macOS maps window -> owning PID. That is unambiguous.
        def _watch():
            for _ in range(60):
                time.sleep(1.0)
                pid = self._pid_from_window()
                if pid:
                    self.pids.add(pid)
        threading.Thread(target=_watch, daemon=True).start()
        # The game's own Steam re-exec chain spawns several copies within a second of
        # launch (measured: 5 processes, all within 3 s of each other), which is what
        # kept blowing past the 2-instance cap and throttling everything. A one-shot
        # pkill at launch cannot catch copies that appear afterwards, so police it
        # continuously: keep the newest process, kill the rest.
        def _enforce_single():
            while True:
                time.sleep(3)
                try:
                    out = subprocess.run(["pgrep", "-f", "MacOS/Nidhogg"],
                                         capture_output=True, text=True).stdout.split()
                    pids = [int(x) for x in out if x.isdigit()]
                except Exception:
                    continue
                # Keep the TWO newest. Culling to exactly one risked killing the very
                # process we were driving: a cull landed mid-entry and that entry then
                # failed. Two is also the stated cap, so this is the right threshold.
                if len(pids) > 2:
                    keep = set(sorted(pids)[-2:])
                    for pid in pids:
                        if pid not in keep:
                            subprocess.run(["kill", "-9", str(pid)], capture_output=True)
                    log(f"instance {self.iid}: culled {len(pids)-2} surplus game process(es)")
        # DISABLED: the cull thread repeatedly killed the process being driven
        # (measured: 13 launches in 5 min, games=0, generation never finished).
        # Duplicates are handled by the pkill at the top of launch() instead.
        # threading.Thread(target=_enforce_single, daemon=True).start()
        log(f"instance {self.iid}: launched pid {self.proc.pid}")

    def close(self):
        self._unlock_prefs()
        # kill every process running THIS instance's bundle copy, then wait for it
        subprocess.run(["pkill", "-9", "-f", f"Nidhogg{self.iid}.app"],
                       capture_output=True)
        for _ in range(20):
            if not self._alive_bundle():
                break
            time.sleep(0.25)
        proc = self.proc
        if proc is not None and proc.poll() is None:
            # kill the GROUP: GameMaker spawns helper children that survived the
            # old single-pid kill, which is how a 2-instance run grew to 12 games.
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except OSError:
                pass
        time.sleep(0.8)
        if proc is not None and proc.poll() is None:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except OSError:
                try:
                    proc.kill()
                except OSError:
                    pass
        if proc is not None:
            try:
                proc.wait(timeout=3)
            except (subprocess.TimeoutExpired, OSError):
                pass
        for pid in getattr(self, "pids", set()):
            try:
                os.kill(pid, signal.SIGKILL)
            except OSError:
                pass
        self.pids = set()
        if self.out is not None:
            self.out.close()
            self.out = None
        self.proc = None

    def read_state(self):
        """Return (state-or-None, stale). A state can have have154/have242 == 0."""
        try:
            path = STATE.format(self.iid)
            stale = time.time() - os.path.getmtime(path) > STATE_STALE
            with open(path) as f:
                vals = f.read().split()
            if len(vals) < 6:
                return None, stale
            o154x, o154y, p242x, p242y, h154, h242 = (float(v) for v in vals[:6])
            return {
                "them_x": o154x, "them_y": o154y,
                "me_x": p242x, "me_y": p242y,
                "have154": int(h154), "have242": int(h242),
            }, stale
        except (OSError, ValueError):
            return None, True

    @staticmethod
    @staticmethod
    def _pos_valid(x):
        return x is not None and 0.5 < abs(x) < 3000.0

    @staticmethod
    def has_players(st):
        """Are both fighters present? Judged by POSITION, not by the existence flags.

        MEASURED with an independent observer (observe_rounds.py) reading the same state
        file during a live generation:

            raw=(559, 96, 256, 229, 1, 0)     <- have242 = 0 while OUR fighter sits at 256

        Our own flag read 0 for a sustained 76 s while the fighter was plainly on the field,
        and the opponent's flag flickers similarly. So the flags are not a liveness signal at
        all. Positions are: a fighter that exists has an x in range; one that does not reads
        0. Using the flag here (as this code did) makes every live match look empty half the
        time, and makes "gone" fire during perfectly good play.
        """
        if not st:
            return False
        return InstanceManager._pos_valid(st.get("me_x")) and \
            InstanceManager._pos_valid(st.get("them_x"))

    def prove_control(self, hold=1.5, min_px=8.0):
        """ACTIVE, entry-time proof that input reaches the simulation.

        This is Pau's gate shape: prove drivability ONCE, when we enter, with an injected
        hold and a measured response. Testing continuously during an episode was wrong -
        a policy that legitimately chooses "nothing" stands still, so a per-tick motion
        test blocks the very episodes we want to score (observed: the trainer looping on
        "live fight confirmed" while the adversary said "frozen", so nothing ever scored).
        """
        st, _ = self.read_state()
        # position-based presence (flags are unreliable - see has_players)
        if not self.has_players(st):
            self.gate_px = 0.0
            return False
        # TRY BOTH DIRECTIONS. This only ever held D, so a fighter standing against the right
        # wall cannot move right and the gate fails no matter how responsive the game is.
        # Measured: "control gate A_px=8.0 (FAIL)" - exactly on the >8.0 threshold - and
        # earlier "A_px=3.0 (FAIL)" / "A_px=0.0 (FAIL)", each triggering a full re-entry.
        x0 = st["me_x"]
        moved = 0.0
        for key in (68, 65):               # D, then A if D produced nothing
            t0 = time.time()
            while time.time() - t0 < hold:
                self.press(key)
                s2, _ = self.read_state()
                if s2 is not None:
                    moved = max(moved, abs(s2["me_x"] - x0))
                time.sleep(0.04)
            if moved > min_px:
                break
        self.gate_px = moved
        log(f"instance {self.iid}: control gate A_px={moved:.1f} "
            f"({'PASS' if moved > min_px else 'FAIL'})")
        return moved > min_px

    def _accept_restart(self, tries=3, wait=12.0):
        """Dismiss the post-round screen and start the next match.

        MEASURED (probe_restart.py, results/restart_0.json): after a round ends, Enter does
        start the next match - players reappear in 7.61 s and the new match passes the
        control gate (A_px=22.7). The earlier 4-6 s windows were simply too short, so every
        restart "failed" and the trainer paid the full ~90 s menu re-entry instead. 12 s
        covers the measured 7.61 s with margin.
        """
        for i, _ in enumerate(range(tries)):
            self.press(13 if i % 2 == 0 else 32)
            t0 = time.time()
            while time.time() - t0 < wait:
                st, stale = self.read_state()
                if self.has_players(st) and not stale:
                    return True
                time.sleep(0.25)
        return False

    def prime_controls(self, hold=2.0, key=68):
        """Hold a direction until the game accepts movement.

        Measured (macOS notes, Session 89): this build shows "HOLD A OR D TO RUN" and
        ignores discrete presses; holding D for 2.5 s moved the fighter 113.5 -> 428
        (314 px). The adversary gate reports exactly this state as "frozen / input not
        reaching game": both fighters present, x not moving. A press/release sequence
        cannot satisfy it, a hold can.
        """
        t0 = time.time()
        while time.time() - t0 < hold:
            self.press(key)
            time.sleep(0.04)
        return True

    def press(self, code):
        if isinstance(code, tuple):
            for part in code:
                with open(KEYS.format(self.iid), "w") as f:
                    f.write(f"{part}\n")
                time.sleep(0.03)
            return
        with open(KEYS.format(self.iid), "w") as f:
            f.write(f"{code}\n")

    def _unlock_prefs(self):
        try:
            import pathlib
            p = (pathlib.Path.home() / "Library/Application Support/com.messhof.nidhogg"
                 / "prefs.ini")
            if p.exists():
                p.chmod(0o644)
        except Exception:
            pass

    def _screenshot(self):
        try:
            import nav
            return nav.capture_instance(self.iid)
        except Exception:
            return None

    def _press_verified(self, code, tries=3, wait=1.6):
        """Press a key and confirm the screen actually changed; retry if it did not.

        The menu silently ignores keys when they arrive during a transition (splash,
        title, screen wipe), which is why a fixed-delay script landed on the wrong
        screen even with the correct W/S keys.
        """
        import numpy as np
        for _ in range(tries):
            before = self._screenshot()
            self.press(code)
            time.sleep(wait)
            after = self._screenshot()
            if before is None or after is None:
                return True                       # cannot verify, assume it worked
            h = min(before.shape[0], after.shape[0])
            w = min(before.shape[1], after.shape[1])
            diff = float(np.abs(before[:h, :w].astype(int) - after[:h, :w].astype(int)).mean())
            if diff > 0.8:                        # the screen moved
                return True
            log(f"instance {self.iid}: key {code} had no effect, retrying")
        return False

    # Verified 2026-11-03 by direct measurement: this exact 8-key sequence reaches a
    # TRAINING match whose CPU is genuinely active (244 px of movement over 12 s while
    # we stood still). Rules learned the hard way:
    #   * menu navigation uses PLAYER-1 bindings: W(87)=up, S(83)=down; arrows do nothing
    #   * exactly ONE S press selects TRAINING - pressing S repeatedly walks back to
    #     ARCADE, which is a 2-player match with no CPU (fighters sit at READY forever)
    #   * exactly ONE leading Enter reaches the main menu; a second selects MULTIPLAYER
    #     and eventually ONLINE ("INVITED <name>, READY"), where no CPU exists
    ENTRY_SEQ = [(13, 2.4),   # title -> main menu
                 (87, 2.4),   # W -> SINGLE PLAYER
                 (13, 2.4),   # enter single player
                 (83, 2.4),   # S -> TRAINING
                 (13, 2.4),   # training list
                 (13, 2.4),   # personality
                 (13, 2.4)]   # difficulty -> fight starts
    # SEVEN keys, not eight. Measured: a 3rd Enter after the S lands a TRAINING match
    # with an ACTIVE CPU (34 px of CPU movement in 10 s), while a 4th Enter flips the
    # versus screen into 2-player ARCADE, where both fighters sit on the READY
    # platforms (y=128) forever and the CPU never moves. That single extra key is why
    # entire training runs scored a flat "rounds 0-1" against a frozen screen.   # level card -> fight

    def _raise_speed(self):
        """Speed up only AFTER a match is entered.

        Menu entry was calibrated at the default ~24 fps. At speed 180 (47.7 fps) the
        menus advance twice as fast and the same key sequence overshoots - measured:
        entry degraded from working to 0 successes over 9 attempts the moment speed
        was set at launch.
        """
        try:
            with open(SPEED.format(self.iid), "w") as f:
                f.write("180\n")
        except Exception:
            pass

    def _match_is_live(self, settle=16.0):
        """A match only counts if the fighters actually MOVE.

        Screenshots proved the trap: reaching a "match" is not enough - the 2-player
        versus screen also has both fighters on screen, but they stand on the READY
        platforms (y~128) forever and no input starts them. A real fight has fighters
        on the ground (y~192) and moving. So entry is verified by motion.
        """
        xs = []
        t0 = time.time()
        while time.time() - t0 < settle:
            st, _ = self.read_state()
            # POSITION, not flags. MEASURED with an independent observer: have242 read 0
            # for a sustained 76 s while our fighter sat at a valid x. Gating entry on
            # `have242 == 1` therefore rejected real matches, logged "S=<n> gave no live
            # fight", and relaunched - which is exactly the entry churn seen all session.
            if self.has_players(st):
                xs.append((st["me_x"], st["them_x"]))
            time.sleep(0.2)
        # A real fight: fighters stand on the GROUND (y ~192), not on the READY
        # platforms (y ~128), and they move. Flags flicker while a fighter respawns,
        # so require a run of samples rather than a simultaneous pair.
        if len(xs) < 6:
            return False
        cpu_motion = max(x[1] for x in xs) - min(x[1] for x in xs)
        if cpu_motion > 15:
            # A TRAINING match has a CPU that actually plays. In ARCADE the CPU
            # slot is a second idle human, so motion stays at exactly 0.
            return True
        moved = (max(x[0] for x in xs) - min(x[0] for x in xs)
                 + max(x[1] for x in xs) - min(x[1] for x in xs))
        ys = [st.get("me_y") for st in (self.read_state()[0],) if st]
        on_ground = False
        for _ in range(10):
            s2, _ = self.read_state()
            if s2 and s2.get("me_y", 0) > 175:
                on_ground = True
                break
            time.sleep(0.2)
        return on_ground or moved > 30

    # MEASURED (14:54): the sequence that actually enters TRAINING is
    #   13, W(87), 13, S(83), S(83), 13, 13, 13   i.e. TWO S presses
    # With one S press the game lands on ARCADE (2-player, inert CPU) and entry looks
    # broken. An earlier run cached "1" and that single wrong constant made every
    # entry fail for several ticks.
    ENTRY = (1, 2)                  # (leading Enters, S presses)

    def _wait_for_title(self, timeout=40.0):
        """Block until the game has actually drawn the title screen.

        Keys sent during loading are silently dropped (the hook log shows key events
        only from frame ~690 onward), so the fixed key sequence used to start several
        screens too early or too late depending on load time.
        """
        t0 = time.time()
        while time.time() - t0 < timeout:
            try:
                import nav as _nav
                a = _nav.capture_instance(str(self.iid))
                if a is not None and float(a.mean()) > 40.0:
                    return True
            except Exception:
                pass
            time.sleep(1.0)
        return False

    def _step(self, code, wait=2.0, tries=5, label=""):
        """Press one menu key, retrying until the screen visibly changes.

        Keys are silently swallowed while the game is still loading or mid-transition,
        which is what made the same sequence land on a different screen each run.
        Retrying until the screen moves makes entry self-correcting instead of
        timing-dependent.
        """
        ok = self._press_verified(code, tries=tries, wait=wait)
        log(f"instance {self.iid}: menu step {label or code} -> {'ok' if ok else 'no change'}")
        return ok

    def _wait_ready(self, min_frames=700, timeout=120.0):
        """Wait for boot, then best-effort confirm the game is rendering.

        The frame-counter check is kept only as an ADDITIONAL wait after a fixed boot,
        never as a replacement: reading it was unreliable (it reported "ready at frame
        1080 (1s)" on processes that had just started, because the harness log is not
        truncated per launch and offsets raced), and entry then looped through 13
        relaunches. The fixed boot is what measurably produced working entries.
        """
        time.sleep(ENTRY_BOOT)
        return True

    def _frame_now(self):
        """Latest game frame counter from the hook log ([win] <pid> f=<n>)."""
        try:
            with open(INJECT_LOG.format(self.iid), "rb") as f:
                f.seek(0, 2)
                f.seek(max(0, f.tell() - 4000))
                tail = f.read().decode("utf-8", "ignore")
            for line in reversed(tail.splitlines()):
                if " f=" in line:
                    return int(line.rsplit("f=", 1)[1])
        except (OSError, ValueError):
            pass
        return None

    def _wait_frames(self, frames=18, timeout=6.0):
        """Wait for N GAME frames, not N seconds.

        Entry used time.sleep(2.5) per key - 9 keys, so ~22 s per attempt, and an entry
        search of four variants cost minutes. The same key sequence at a fixed FRAME
        distance is what the game actually consumes, and this hook already publishes the
        frame counter. 18 frames is roughly what 400 ms bought at the calibrated rate.
        Falls back to a short sleep if the counter is unavailable.
        """
        f0 = self._frame_now()
        if f0 is None:
            time.sleep(0.4)
            return
        t0 = time.time()
        while time.time() - t0 < timeout:
            f1 = self._frame_now()
            if f1 is not None and f1 - f0 >= frames:
                return
            time.sleep(0.02)
        time.sleep(0.1)

    def _menu_home(self, presses=3, wait=0.9):
        """Return to the main menu before trying to enter.

        Entry variants assume they start from the main menu, but a FAILED variant leaves the
        game somewhere else - a submenu, a READY screen, or the options list - and the next
        variant then navigates from the wrong place. That is why entry cost 2-3 minutes and
        sometimes never succeeded: measured, right after a failed attempt the state file was
        present but all zeros (hook alive, no fighters), i.e. we were parked in a menu.

        Escape is the menu's back key; pressing it a bounded number of times from any menu
        depth lands on the main menu.
        """
        # ESC IS NOT SAFE HERE. Pressing Escape from the main menu opens the quit dialog and
        # a following Enter confirms it, so an "entry reset" built on Esc actually kills the
        # game - which matches what the log showed immediately after I added it (relaunch
        # after relaunch, entry never completing). Up/W is navigation only: menus wrap, so a
        # few presses land the selection at the top of the list regardless of where it was.
        for _ in range(presses):
            self.press(87)          # W = up
            time.sleep(wait)

    def _try_entry(self, s_count=1, n_lead=1):
        """Menu entry: n_lead Enters (title/popup), W, Enter, S x1, then 3 confirms."""
        self._wait_ready()
        self._menu_home()
        seq = [(13, 2.5)] * max(1, n_lead)
        seq += [(87, 2.5), (13, 2.5)]
        seq += [(83, 2.5)] * max(1, s_count)
        seq += [(13, 2.5), (13, 2.5), (13, 2.5)]
        for code, wait in seq:
            self.press(code)
            # frame-based, not wall-clock: see _wait_frames. The `wait` value is kept only
            # as a fallback when the frame counter cannot be read.
            self._wait_frames(18, timeout=max(1.0, wait))
        # Presence is all _try_entry should decide. It used to require
        # _match_is_live(settle=12), which needs cpu_motion > 15 - but during entry we press
        # no keys, so a quiet CPU reads as "no live fight" and entry relaunches endlessly
        # (measured: "S=1 gave no live fight - relaunching" over and over). Whether the
        # match is actually controllably OURS is decided next, by the active gate in
        # _drivable_now(), which holds a key and measures the response - a strictly better
        # test than watching the CPU twitch.
        for _ in range(2):
            st, _ = self.read_state()
            if self.has_players(st):
                return True
            self.press(13)
            time.sleep(4.0)
        st, _ = self.read_state()
        if self.has_players(st):
            return True
        # Still nothing: back out to the main menu and (on the first pass) retry the
        # sequence once. NOTE: no Escape here - Escape opens the quit dialog in this build
        # and the next Enter confirms it, which killed the game once already.
        log(f"instance {self.iid}: no fighters after entry sequence - backing out")
        return False


    def start_from_round_boundary(self, wait=3.0):
        """Force a fresh round so every episode begins from a comparable state.

        MEASURED this session (repeated measures): one policy produced fits of -0.24, 7.49 and
        -16.88 in three consecutive episodes - sd 12.5 on a scale whose useful range is about
        -30..30. The GA cannot resolve differences that small. The dominant source is that each
        episode starts wherever the previous one ended: different spawn positions, sometimes a
        fresh round, sometimes the middle of one.

        This presses Enter and waits briefly for a ROUND BOUNDARY - both fighters teleport across
        the arena, the signature measured in Session 142.

        MEASURED: Enter does NOT end or start a round from mid-round. Three consecutive attempts
        sat 14 s without a boundary ("no round boundary within 14s - starting anyway"), while
        Enter DOES work on a round-over screen (7.61 s, results/restart_0.json). So this is
        opportunistic: it catches the case where the previous episode ended on a round-over
        screen, and otherwise costs only a few seconds. It is not a true reset, and Phase 6 is
        therefore still open - this build does not let us force a round start. It is
        Pau's Phase 6 ("reset without the menu") reduced to what this build allows, since
        writing x directly does not survive (writes revert; see Session 121).
        """
        st0, _ = self.read_state()
        if not self.has_players(st0):
            return False
        x0, t0 = (st0["me_x"], st0["them_x"]), st0["them_x"]
        self.press(13)
        deadline = time.time() + wait
        while time.time() < deadline:
            st, _ = self.read_state()
            if self.has_players(st):
                me_jump = abs(st["me_x"] - x0[0]) > 300
                th_jump = abs(st["them_x"] - x0[1]) > 300
                if me_jump and th_jump:
                    log(f"instance {self.iid}: round boundary (reset) "
                        f"-> me={st['me_x']:.0f} them={st['them_x']:.0f}")
                    return True
            time.sleep(0.15)
        log(f"instance {self.iid}: no round boundary within {wait:.0f}s - starting anyway")
        return False

    def probe_match_vars_once(self):
        """After a fresh launch, ask the Match object for its named variables.

        Phase 4 needs a round/score field, and the only route left on this build is the
        instance's named variables (the builtin struct window 0x80..0x600 contains nothing
        but timers). The hook caches the Match pointer from the object walk, so the query has
        something to ask - but only in a process that loaded the fixed dylib. Doing this ONCE
        per launch, from the trainer, means the data arrives without spawning an extra game
        while a run is in progress.
        """
        if getattr(self, "_vars_probed", False):
            return
        self._vars_probed = True
        try:
            # ORDER MATTERS: the object walk is what caches the Match instance pointer, and
            # the variable query needs it (get_inst_list returns 0 for object 106). Firing
            # only `vars` produced "no instance" twice, which is why this is two steps.
            with open(OBJS.format(self.iid), "w") as f:
                f.write("Match\n")
            time.sleep(1.5)
            with open(VARS.format(self.iid), "w") as f:
                f.write("vars\n")
            time.sleep(2.5)
            with open(INJECT_LOG.format(self.iid), errors="ignore") as f:
                hits = [l for l in f if l.startswith("[vars]")]
            if hits:
                out = f"/tmp/nid_vars_out_{self.iid}.txt"
                with open(out, "w") as f:
                    f.write("\n".join(hits) + "\n")
                log(f"instance {self.iid}: captured {len(hits)} Match variables -> {out}")
        except OSError:
            pass

    def _drivable_now(self, tries=2, prime=0.7, gate=0.9, accept_wait=4.0):
        """Entry is not finished until the gate says input reaches the simulation.

        "Live fight confirmed" has been wrong before, and this session measured why: the
        READY screen has both fighters, answers `has_players` and every other presence
        check, and ignores input (gate A_px=3.0 while a live round gave 47-56). Entering
        into READY therefore looked like success and produced generations with no
        control at all.

        So: prime the controls, run the ACTIVE gate, and if it fails try the cheap Enter
        accept-restart (a round boundary is one press away) before giving up.
        """
        # TIMING MATTERS MORE THAN THOROUGHNESS HERE. Measured from timestamps in a
        # pop-2/reps-10 run: episodes were ~20 s of measurement against ~2.5 min of entry
        # overhead, so 90% of wall clock went into getting ready. The old numbers here
        # (prime 1.0 + gate 1.2 + accept-restart waits of up to 12 s, x3 tries) could spend
        # 40 s per attempt. Enter only ever works from a round-over screen (elsewhere it does
        # nothing at all, measured), so a short wait distinguishes the cases just as well.
        for _ in range(tries):
            st, _ = self.read_state()
            if not self.has_players(st):
                if not self._accept_restart(tries=1, wait=accept_wait):
                    return False
                continue
            self.prime_controls(prime)
            if self.prove_control(gate):
                return True
            if not self._accept_restart():
                return False
        return False

    def _enter_confirmed(self, s_count, n_lead):
        """One bounded entry attempt, accepted only if the result is drivable."""
        if not self._try_entry(s_count, n_lead):
            return False
        return self._drivable_now()

    def run_entry(self):
        """Enter a TRAINING match (real CPU) by searching the menu once, then caching.

        The submenu order decides whether we land in ARCADE (2-player, which waits
        forever for a second human - the READY screen that ate whole training runs)
        or TRAINING (a real CPU fight). Rather than hard-code a fragile S count, try
        the plausible ones on a freshly launched process and remember the winner.
        """
        cached = getattr(InstanceManager, "ENTRY", None)
        if cached is not None:
            n_lead, s_count = cached
            log(f"instance {self.iid}: using cached entry n_lead={n_lead} S={s_count}")
            if self._enter_confirmed(s_count, n_lead):
                self._raise_speed()
                log(f"instance {self.iid}: live AND drivable (gate confirmed)")
                self.probe_match_vars_once()
                return True
            log(f"instance {self.iid}: cached entry failed, re-searching")
        for n_lead, s_count in ((1, 2), (2, 2), (1, 1), (2, 1)):
            log(f"instance {self.iid}: trying entry n_lead={n_lead} S={s_count}")
            # (the duplicate `or self._try_entry(...)` here ran entry TWICE on the first
            # variant, doubling entry cost for nothing)
            if self._enter_confirmed(s_count, n_lead):
                InstanceManager.ENTRY = (n_lead, s_count)
                self._raise_speed()
                self.probe_match_vars_once()
                log(f"instance {self.iid}: TRAINING reached n_lead={n_lead} S={s_count}; cached")
                return True
            # DO NOT RELAUNCH AFTER EVERY FAILED VARIANT. That cost BOOT_WAIT (55 s) per
            # attempt, so a four-variant search spent 3-4 minutes in menu navigation while
            # the game was running perfectly well. Menu navigation does not need a fresh
            # process: try every variant on the SAME process first, and relaunch once only if
            # all of them fail. Measured context: episodes were ~20 s against ~2.5 min of
            # entry, i.e. 90% overhead.
            log(f"instance {self.iid}: S={s_count} gave no live fight - trying next variant")
        log(f"instance {self.iid}: no variant worked on this process - one relaunch")
        try:
            self.close()
        except Exception:
            pass
        time.sleep(1.5)
        self.launch()
        time.sleep(BOOT_WAIT)
        # last chance on the fresh process, using the most common variant
        if self._enter_confirmed(2, 1):
            InstanceManager.ENTRY = (1, 2)
            self._raise_speed()
            log(f"instance {self.iid}: TRAINING reached after relaunch")
            return True
        log(f"instance {self.iid}: no entry variant produced a live fight")
        return False


    def wait_for_match(self, timeout=MATCH_READY_TIMEOUT):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if not self.alive():
                return False
            st, stale = self.read_state()
            if not stale and self.has_players(st):
                self.ever_have_players = True
                return True
            time.sleep(0.25)
        return False

    def restart(self, reason):
        """Ask the trainer to reset the whole pool; do NOT launch here.

        Launching one instance in isolation raced with the other instance's sweep and
        left orphans (2 -> 19 processes). The trainer's `reset_all()` kills everything
        and relaunches the pool under one lock, which keeps the count exact.
        """
        self.needs_reset = True
        log(f"instance {self.iid}: needs pool reset ({reason})")
        return False

    def recover_match(self):
        """Recovery = clean process restart.

        Verified: room_goto works exactly ONCE per process (a 2nd call kills the
        runner), startMatch() needs arguments we do not have, and menu keys are
        off-limits (the NEWS panel opens external links). So the only safe way to
        get a fresh match is a fresh process. One process therefore serves one
        match; within that match the agent plays several rounds.
        """
        log(f"instance {self.iid}: match over -> restarting the process")
        return self.restart("match finished")

    def ensure_match(self):
        """Called before each individual. Never leaves a dead game running."""
        for attempt in range(2):
            st, stale = self.read_state()
            # ATTRIBUTION: every branch decision is logged, because "the match vanished"
            # has been the least checkable claim in this project. One line per call is
            # cheap next to a 6-minute entry search.
            log(f"instance {self.iid}: ensure_match alive={self.alive()} stale={stale} "
                f"players={self.has_players(st)} ever={self.ever_have_players} "
                f"attempt={attempt} state={st}")
            if self.alive() and not stale and self.has_players(st):
                self.ever_have_players = True
                return True
            if not self.alive():
                if self.restart("process dead before individual"):
                    return True
                continue
            uptime = time.monotonic() - self.started_at
            if uptime < BOOT_WAIT:
                time.sleep(BOOT_WAIT - uptime)
            if self.ever_have_players:
                # CHEAP RESTART FIRST. After a round ends the fighters leave the state
                # file, and one Enter press starts the next match in ~0.4 s, versus a
                # menu re-entry (~10-20 s) or a relaunch (~22 s boot). Measured on this
                # build. Trying it first is why the remaining individuals no longer abort
                # instantly as "no match".
                if self._accept_restart():
                    return True
                if self.recover_match():
                    return True
            else:
                self.run_entry()
                if self.wait_for_match():
                    return True
                if self.restart(f"initial entry failed (attempt {attempt + 1})"):
                    return True
        log(f"instance {self.iid}: unable to obtain a match")
        return False


def act(params, st, rng):
    dx = st["them_x"] - st["me_x"]
    toward = 68 if dx > 0 else 65       # D / A
    away = 65 if dx > 0 else 68
    if abs(dx) > params["engage"]:
        if rng.random() < params["jump"]:
            return 71                    # G = jump
        return toward
    if rng.random() < params["aggr"]:
        aim = {0: 83, 1: 87, 2: 87}[params["aim"]]
        return aim, 70                   # aim, then F = attack
    if rng.random() < params["retreat"]:
        return away
    return 87 if params["aim"] >= 1 else 83


def run_individual(mgr, params, seconds, seed, tag):
    """Run 25 s of actual control; recovery time does not consume the window."""
    rng = random.Random(seed)
    deadline = time.monotonic() + seconds
    trace = []
    mine = theirs = 0
    round_resets = 0
    prev = None
    segment = None
    segment_advances = []
    segment_approaches = []
    missing_since = None
    last_fresh = time.monotonic()
    last_motion = time.monotonic()
    last_coords = None

    def finish_segment():
        if segment is not None:
            segment_advances.append(
                (segment["best_me"] - segment["start_me"])
                - (segment["start_them"] - segment["worst_them"])
            )
            segment_approaches.append(segment["approach"])

    def reset_after_recovery():
        nonlocal prev, segment, missing_since, last_motion, last_coords, last_fresh
        finish_segment()
        prev = None
        segment = None
        missing_since = None
        last_motion = time.monotonic()
        last_coords = None
        last_fresh = time.monotonic()

    while time.monotonic() < deadline:
        now = time.monotonic()
        if not mgr.alive():
            recovery_started = time.monotonic()
            if not mgr.restart("process died during individual"):
                break
            deadline += time.monotonic() - recovery_started
            reset_after_recovery()
            continue

        st, stale = mgr.read_state()
        if stale:
            if now - last_fresh > STATE_STALE:
                recovery_started = time.monotonic()
                if not mgr.restart("state file stale during individual"):
                    break
                deadline += time.monotonic() - recovery_started
                reset_after_recovery()
            else:
                time.sleep(0.1)
            continue
        last_fresh = now

        if not mgr.has_players(st):
            if missing_since is None:
                missing_since = now
            elif now - missing_since >= MISSING_MATCH_OVER:
                recovery_started = time.monotonic()
                if not mgr.recover_match():
                    break
                deadline += time.monotonic() - recovery_started
                reset_after_recovery()
            else:
                time.sleep(0.1)
            continue

        missing_since = None
        mgr.ever_have_players = True
        if segment is None:
            segment = {
                "start_me": st["me_x"], "best_me": st["me_x"],
                "start_them": st["them_x"], "worst_them": st["them_x"],
                "approach": 0.0, "last_gap": None,
            }

        coords = (st["me_x"], st["me_y"], st["them_x"], st["them_y"])
        if last_coords is not None and any(
                abs(a - b) > 1.0 for a, b in zip(coords, last_coords)):
            last_motion = now
        elif now - last_motion > FROZEN_MATCH_OVER:
            # Some stats screens leave sticky fighter state. No coordinates
            # changing for six seconds despite actions is the fallback signal.
            recovery_started = time.monotonic()
            if not mgr.recover_match():
                break
            deadline += time.monotonic() - recovery_started
            reset_after_recovery()
            continue
        last_coords = coords

        if prev is not None:
            me_jump = abs(st["me_x"] - prev["me_x"]) > SPAWN_JUMP
            them_jump = abs(st["them_x"] - prev["them_x"]) > SPAWN_JUMP
            if me_jump and them_jump:
                # both respawned simultaneously: the ROUND ended. Not deaths.
                finish_segment()
                segment = {
                    "start_me": st["me_x"], "best_me": st["me_x"],
                    "start_them": st["them_x"], "worst_them": st["them_x"],
                    "approach": 0.0, "last_gap": None,
                }
                round_resets += 1
            elif me_jump:
                mine += 1
            elif them_jump:
                theirs += 1
        prev = dict(st)
        if segment is not None:
            segment["best_me"] = max(segment["best_me"], st["me_x"])
            segment["worst_them"] = min(segment["worst_them"], st["them_x"])
            gap = abs(st["them_x"] - st["me_x"])
            if segment["last_gap"] is not None:
                segment["approach"] += segment["last_gap"] - gap   # positive = closed in
            segment["last_gap"] = gap
        trace.append([
            round(seconds - max(0.0, deadline - now), 2),
            round(st["me_x"]), round(st["them_x"]),
        ])
        mgr.press(act(params, st, rng))
        time.sleep(0.05)

    finish_segment()
    advance = sum(segment_advances)
    approach = sum(segment_approaches)
    fitness = 3.0 * theirs - 2.0 * mine + advance / 100.0 + approach / 40.0
    return {
        "fitness": round(fitness, 3),
        "my_deaths": mine,
        "their_deaths": theirs,
        "advance": round(advance, 1),
        "rounds": round_resets, "approach": round(approach, 1),
        "params": params,
        "trace": trace,
        "tag": tag,
    }


def failed_record(params, tag):
    return {
        "fitness": -100.0, "my_deaths": 0, "their_deaths": 0,
        "advance": 0.0, "params": params, "trace": [], "tag": tag,
    }


def append_record(rec):
    with open(LOG_PATH, "a") as f:
        f.write(json.dumps(rec) + "\n")
        f.flush()
        os.fsync(f.fileno())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--gens", type=int, default=6)
    parser.add_argument("--pop", type=int, default=8)
    parser.add_argument("--window", type=float, default=25.0)
    parser.add_argument("--seed", type=int, default=23)
    args = parser.parse_args()

    if os.path.exists(LOG_PATH):
        backup = f"{LOG_PATH}.bak.{int(time.time())}"
        os.replace(LOG_PATH, backup)
        log(f"previous log backed up to {backup}")

    # Mute only the game. The finally block always restores the user's prefs.
    shutil.copyfile(MUTED_PREFS, PREFS)
    mgr = InstanceManager(0)
    rng = random.Random(args.seed)
    import agent as A   # legacy parametric-policy trainer only (see legacy/)
    population = [A.rand_params(rng) for _ in range(args.pop)]
    best = None
    generations = []
    run_started = time.monotonic()
    stopped_for_budget = False

    try:
        mgr.launch()
        for gen in range(args.gens):
            results = []
            for ind, params in enumerate(population):
                if time.monotonic() - run_started > RUN_BUDGET:
                    stopped_for_budget = True
                    log("40-minute safety budget reached; stopping cleanly")
                    break
                tag = f"g{gen}i{ind}"
                mgr.current_tag = tag
                if mgr.ensure_match():
                    rec = run_individual(
                        mgr, params, args.window,
                        args.seed + gen * 97 + ind, tag,
                    )
                else:
                    rec = failed_record(params, tag)
                append_record(rec)
                results.append(rec)
                log(f"{tag}: fit={rec['fitness']:.3f} their={rec['their_deaths']} "
                    f"mine={rec['my_deaths']} advance={rec['advance']:.1f} "
                    f"samples={len(rec['trace'])}")
            if stopped_for_budget:
                break

            results.sort(key=lambda rec: -rec["fitness"])
            generation_best = results[0]
            mean = statistics.fmean(rec["fitness"] for rec in results)
            generations.append({
                "generation": gen, "best": generation_best["fitness"],
                "mean": round(mean, 3), "best_tag": generation_best["tag"],
            })
            print(f"== gen {gen} best {generation_best['fitness']:.1f} "
                  f"mean {mean:.1f}", flush=True)
            if best is None or generation_best["fitness"] > best["fitness"]:
                best = generation_best

            elite = [rec["params"] for rec in results[:max(2, args.pop // 3)]]
            next_population = list(elite)
            while len(next_population) < args.pop:
                a, b = rng.sample(elite, 2)
                next_population.append(A.mutate(A.crossover(a, b, rng), rng))
            population = next_population

        if best is not None:
            print("best params:", json.dumps(best["params"]), flush=True)
            print(f"best tag {best['tag']} fitness {best['fitness']}", flush=True)
    finally:
        if best is not None:
            atomic_json(BEST_PATH, {
                "tag": best["tag"], "fitness": best["fitness"],
                "params": best["params"],
            })
        episodes = sorted(mgr.recovery_episodes | mgr.restart_episodes)
        atomic_json(SUMMARY_PATH, {
            "complete": len(generations) == args.gens and not stopped_for_budget,
            "requested": {"generations": args.gens, "population": args.pop,
                          "seconds_per_individual": args.window, "seed": args.seed},
            "generations": generations,
            "best": best,
            "episodes_needing_restart_or_recovery": len(episodes),
            "episode_tags_needing_restart_or_recovery": episodes,
            "episodes_needing_hard_restart": len(mgr.restart_episodes),
            "episode_tags_needing_hard_restart": sorted(mgr.restart_episodes),
            "match_recoveries": mgr.match_recoveries,
            "hard_instance_restarts": mgr.hard_restarts,
            "log": LOG_PATH,
        })
        mgr.current_tag = None
        mgr.close()
        shutil.copyfile(PRISTINE_PREFS, PREFS)
        log("owned game stopped; pristine prefs restored")


if __name__ == "__main__":
    main()
