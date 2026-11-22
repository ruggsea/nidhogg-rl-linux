"""Self-play adapter: live Nidhogg (nidenv.Env), BOTH fighters driven by the trainer.

    env = SelfPlayEnv(seed); (o1, o2) = env.reset()
    (o1, o2), (r1, r2), done, info = env.step(a1, a2)      # a1, a2 in 0..6, each from its own side

Each fighter sees the game from its own side. P1 (yellow) gets nidenv's observation. P2 (orange)
gets the same vector built from the x-mirrored world (x' = MIRROR_X - x, facing' = -facing), so
"right" means "toward the opponent's side of the map" for both. P2's left/right actions are
swapped back before they reach the game (1 <-> 2). MIRROR_X = 2200 is the bound nidmem.scan uses
for fighter x, not a measured arena centre: P2's own-x feature is offset, not exactly mirrored.

Reward per fighter, at episode end only:
  +1 killed the opponent, -1 died (a draw = both: 0 + 0), and -STILL_PEN if the fighter did not
  walk (< WALK_STEPS steps that moved it along its held walk key, nidenv's motion count).
Episode ends at a kill or after MAX_TICKS game ticks (default 600, NID_SP_MAX_TICKS).
validity.py (rule from NID_RULE, v3 for reported numbers) is attached to every row but does not
enter the reward. Rows: $NIDFARM/episodes.jsonl (nidenv) and $NIDFARM/selfplay_eps.jsonl (here).
Restart and stall watchdog are nidtrain_env.TrainEnv's.
"""
import json, os, subprocess, time

import numpy as np

import nidtrain_env as te

from env_iface import N_OBS

MIRROR_X = 2200.0
SWAP = {1: 2, 2: 1}
WHO = ("P1", "P2")


def obs_pair(st, feat):
    """(o1, o2), each (N_OBS = 34,): the 8 base numbers, then OWN 13 fields, then OPPONENT's 13
    (nidobs.FEATS order). o1 = P1 in the world frame. o2 = P2 in the x-mirrored frame: base as
    before; fields through nidobs.mirror (fly_dx, ground_dx negated; ledge and view left/right
    swapped and negated). feat = nidenv.Env.feat (world frame, read at state st)."""
    import nidobs            # lazily, like nidenv in nidtrain_env (needs ~/nidhogg-main on the path)
    h1, h2 = (192 - st.p1_y) / 100, (192 - st.p2_y) / 100
    o1 = [st.p1_x / 1000, h1, st.p1_facing, (st.p2_x - st.p1_x) / 300,
          h2, st.p2_facing, st.p1_anim / 500, st.p2_anim / 500]
    # mirrored: own x' = M - p2_x, opponent x' = M - p1_x, dx' = p2_x - p1_x
    o2 = [(MIRROR_X - st.p2_x) / 1000, h2, -st.p2_facing, (st.p2_x - st.p1_x) / 300,
          h1, -st.p1_facing, st.p2_anim / 500, st.p1_anim / 500]
    e1 = [feat["P1"], feat["P2"]]
    e2 = [nidobs.mirror(feat["P2"]), nidobs.mirror(feat["P1"])]
    return tuple(np.clip(np.concatenate([np.array(v, np.float32)] + e), -2, 2)
                 for v, e in ((o1, e1), (o2, e2)))


def rewards(outcome, motion, still_pen, walk_steps):
    kills = {"P1": outcome in ("P1", "draw"), "P2": outcome in ("P2", "draw")}
    out = {}
    for w, o in (("P1", "P2"), ("P2", "P1")):
        moved = ((motion or {}).get(w) or {}).get("moved_steps", 0)
        walked = moved >= walk_steps
        r = float(kills[w]) - float(kills[o]) - (0.0 if walked else still_pen)
        out[w] = {"reward": round(r, 4), "kill": int(kills[w]), "death": int(kills[o]),
                  "moved_steps": moved, "walked": walked}
    return out


class SelfPlayEnv(te.TrainEnv):
    def __init__(self, seed=0, max_ticks=None, still_pen=0.05, walk_steps=5, tag="", **kw):
        super().__init__(seed, **kw)
        self.max_ticks = max_ticks or int(os.environ.get("NID_SP_MAX_TICKS", "600"))
        self.still_pen, self.walk_steps, self.tag = still_pen, walk_steps, tag
        self.sp_log = te.FARM / "selfplay_eps.jsonl"
        self.aborts_in_row = 0

    def reset(self):
        # nidenv refuses a reset unless both fighters stand in an idle stance anim (IDLE_ANIMS);
        # TrainEnv.reset restarts the game once on failure; a reset that still fails restarts
        # the game again (never carries a hanging fighter into an episode), then gives up
        for k in range(3):
            try:
                super().reset()
                break
            except (AssertionError, RuntimeError, ValueError, OSError) as e:
                self._reset_failed(e)
                if k == 2:
                    raise
                self._restart(f"reset failed after a restart: {e}"[:3000])
        st = self.env.last
        self.start = {w: {"anim": int(getattr(st, f"{p}_anim")), "y": round(getattr(st, f"{p}_y"), 1),
                          "height": round(192 - getattr(st, f"{p}_y"), 1),
                          "facing": getattr(st, f"{p}_facing")} for w, p in (("P1", "p1"), ("P2", "p2"))}
        obs = obs_pair(st, self.env.feat)
        self.start["obs"] = {w: [round(float(v), 4) for v in o] for w, o in zip(WHO, obs)}  # logged only
        self._video_start()
        return obs

    def _reset_failed(self, e):
        """Count a failed reset (separately from game deaths); the caller restarts the game."""
        self.reset_failures = getattr(self, "reset_failures", 0) + 1
        with open(te.FARM / "reset_failures.jsonl", "a") as f:
            f.write(json.dumps({"t": time.strftime("%Y-%m-%dT%H:%M:%S"), "i": self.count,
                                "type": type(e).__name__, "why": str(e)[:30000]}) + "\n")
        self._diag(str(e))

    def _diag(self, why):
        """Snapshot what was running for a hang or a 'no record' reset (train/diag.py)."""
        kind = ("hang" if any(k in why for k in ("state file stopped", "no game", "spy", "/proc/"))
                else "no_record" if "no record answers" in why else None)
        if kind:
            import diag
            diag.snapshot(self, kind, why)

    # ------------------------------------------------ one mp4 per episode (NID_SP_VIDEO_DIR)
    def _video_start(self):
        vdir = os.environ.get("NID_SP_VIDEO_DIR")
        self.video, self.video_proc = None, None
        if not vdir:
            return
        os.makedirs(vdir, exist_ok=True)
        disp = f":{int(os.environ.get('NID_DISPLAY_BASE', '0')) + self.inst}"
        geom = subprocess.run(["xdotool", "getdisplaygeometry"], env=dict(os.environ, DISPLAY=disp),
                              capture_output=True, text=True, check=True).stdout.split()
        w, h = int(geom[0]), int(geom[1])
        sh = 640 * h // w // 2 * 2                       # keep aspect, letterbox into 640x480
        self.video = f"{os.environ.get('NID_SP_RUN', 'run')}_ep{self.count}.mp4"
        self.video_proc = subprocess.Popen(
            ["ffmpeg", "-loglevel", "error", "-y", "-f", "x11grab", "-video_size", f"{w}x{h}",
             "-framerate", "20", "-i", disp, "-vf", f"scale=640:{sh},pad=640:480:0:{(480 - sh) // 2}",
             "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p",
             os.path.join(vdir, self.video)], stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
            stderr=open(os.path.join(vdir, "ffmpeg.log"), "a"),
            preexec_fn=lambda: __import__("ctypes").CDLL("libc.so.6").prctl(1, 15))  # die with us

    def _video_stop(self):
        p, self.video_proc = getattr(self, "video_proc", None), None
        if p is None:
            return
        try:
            p.communicate(b"q", timeout=15)
        except subprocess.TimeoutExpired:
            p.kill(); p.wait()                           # our own child, by its pid
        if p.returncode not in (0, 255):
            raise RuntimeError(f"ffmpeg exited {p.returncode} for {self.video}")

    def step(self, a1, a2):
        assert 0 <= int(a1) <= 6 and 0 <= int(a2) <= 6, (a1, a2)
        a2_game = SWAP.get(int(a2), int(a2))
        try:
            _, done, info = self.env.step(int(a1), a2_game)
            if not done and self.env.last.tick - self.env.tick0 >= self.max_ticks:
                _, done, info = self.env._end({"tick": self.env.last.tick, "outcome": "undecided"},
                                              {"timeout_ticks": self.max_ticks})
        except (AssertionError, RuntimeError, ValueError, OSError) as e:
            return self._sp_abort(f"{type(e).__name__}: {e}")
        self.steps += 1
        self.last_progress = time.time()
        if not done:
            return obs_pair(self.env.last, self.env.feat), (0.0, 0.0), False, info
        self._video_stop()
        self.aborts_in_row = 0
        row = info.pop("row", {})
        self.need_restart = any(x.startswith("a: non-arena") for x in row.get("invalid_reasons") or [])
        # a stale death does not count: drop it from the outcome, mark the episode invalid
        stale = row.get("stale_deaths") or {}
        if stale:
            dead = {"P1": ["P2"], "P2": ["P1"], "draw": ["P1", "P2"]}.get(info["outcome"], [])
            alive_dead = [w for w in dead if w not in stale]
            info["outcome"] = ("draw" if len(alive_dead) == 2 else
                               {"P2": "P1", "P1": "P2"}[alive_dead[0]] if alive_dead else "undecided")
            row["valid"] = False
            row["invalid_reasons"] = (row.get("invalid_reasons") or []) + [
                f"stale death {w}: {'; '.join(r)}" for w, r in stale.items()]
        per = rewards(info["outcome"], row.get("motion"), self.still_pen, self.walk_steps)
        rec = {"tag": self.tag, "run": self.run_id, "i": self.count, "seed": self.ep_seed,
               "outcome": info["outcome"], "steps": self.steps, "ticks": row.get("ticks"),
               "valid": bool(row.get("valid")), "invalid_reasons": row.get("invalid_reasons"),
               "rule": row.get("rule"), "per": per, "motion": row.get("motion"),
               "nid_episode": getattr(self.env, "ep", 0) - 1, "t": time.strftime("%Y-%m-%dT%H:%M:%S"),
               "start": self.start, "video": self.video, "episode_index": self.count,
               "round_state": row.get("round_state"), "stale_deaths": stale,
               "raw_outcome": row.get("outcome")}
        self._write(rec)
        info = dict(info, per=per, valid=rec["valid"], ticks=rec["ticks"], start=self.start, round_state=rec["round_state"],
                    stale_deaths=stale, raw_outcome=rec["raw_outcome"],
                    video=rec["video"], episode_index=rec["episode_index"])
        return obs_pair(self.env.last, self.env.feat), (per["P1"]["reward"], per["P2"]["reward"]), True, info

    def _sp_abort(self, err):
        """Game state lost mid-episode: no reward for either side, logged, restart before next."""
        self._video_stop()
        self._diag(err)
        self.aborts_in_row += 1
        if self.aborts_in_row > 5:
            raise SystemExit(f"5 aborted episodes in a row; last: {err[:500]}")
        rec = {"tag": self.tag, "run": self.run_id, "i": self.count, "seed": self.ep_seed,
               "outcome": "aborted", "steps": self.steps, "valid": False,
               "invalid_reasons": [f"aborted: {err[:300]}"], "t": time.strftime("%Y-%m-%dT%H:%M:%S"),
               "start": getattr(self, "start", None), "video": self.video, "episode_index": self.count}
        self._write(rec)
        self.need_restart = True
        z = np.zeros(N_OBS, np.float32)
        per = {w: {"reward": 0.0, "kill": 0, "death": 0, "moved_steps": 0, "walked": False} for w in WHO}
        return (z, z), (0.0, 0.0), True, {"outcome": "aborted", "per": per, "valid": False, "ticks": None,
                                          "start": rec["start"], "video": rec["video"],
                                          "episode_index": rec["episode_index"]}

    def _write(self, rec):
        with open(self.sp_log, "a") as f:
            f.write(json.dumps(rec) + "\n")
        self.count += 1


def make(seed=0):
    return SelfPlayEnv(seed)
