"""Win-reward trainer: fitness = rounds won / lost / matches won.

Round logic, all from published state (no vision):
  * a single player's x teleporting => that player died this round
  * BOTH teleporting at once        => the round ended and reset
  * the round goes to whoever did NOT die
  * first to 3 round wins takes the match (Nidhogg is best-of-5)

Fitness = 10*rounds_won - 6*rounds_lost + 30*match_won + small shaping so early
random policies still get a gradient (advance toward the enemy goal).
"""
import argparse
import json
import os
import threading
import time

import numpy as np

import neuro
import train_state as TS

LOG = "/tmp/nid_win_train.jsonl"
RESET_LOCK = threading.Lock()


def reset_all(mgrs, log=print):
    """Kill every game process and relaunch the whole pool, serialized.

    Per-instance restarts orphaned processes (the runner re-execs itself via
    SteamAPI_RestartAppIfNecessary), which is how 2 instances became 10-19 games.
    A global sweep under a lock keeps the count exactly equal to len(mgrs).
    """
    # MUST use the same lock as InstanceManager.restart(), otherwise a global sweep
    # can kill a game another instance has just launched, which then reports
    # "process dead", restarts, and triggers another sweep (the restart cascade).
    with TS._RESTART_LOCK:
        log("  [reset] sweeping all game processes and relaunching the pool")
        os.system('pkill -f "MacOS/Nidhogg"')
        # WAIT for them to actually die before relaunching: relaunching while the
        # old ones were still exiting is what made the pool oscillate 2 -> 8.
        for _ in range(30):
            if not TS.InstanceManager._nidhogg_pids():
                break
            time.sleep(0.5)
        stragglers = TS.InstanceManager._nidhogg_pids()
        if stragglers:
            log(f"  [reset] {len(stragglers)} stragglers, SIGKILL")
            os.system('pkill -9 -f "MacOS/Nidhogg"')
            time.sleep(2)
        for m in mgrs:
            m.close()
        for m in mgrs:
            m.launch()
        time.sleep(TS.BOOT_WAIT)
        for m in mgrs:
            m.run_entry()
        for m in mgrs:
            m.wait_for_match()
            m.needs_reset = False
        time.sleep(2)
SPAWN_JUMP = 90.0   # px between consecutive ~70 Hz samples. Normal motion is <20 px
                   # per sample, so 90 catches a respawn teleport (300 missed the
                   # respawns that land close to the death spot)
ROUNDS_TO_WIN = 3
HOLD_TICKS = 8   # MEASURED: 8 -> advance 123-134 px per episode; 20 -> only 14-24 px.
                 # A longer hold makes the agent commit into the CPU and get stuck, so
                 # the intuitive 'be more decisive' change was wrong. Keep 8.   # 8 ticks (~0.16 s) made the agent change direction so often it
                 # travelled almost nowhere: advance varied only 11 px across a whole
                 # 70 s episode. 20 gives a sustained commitment.          # ~150 ms of held action per decision
# MEASURED arena (300 s trajectory, 6224 samples): x spans about 0..462 and kill/respawn
# teleports land at the ends. The old values (1650 / 250) made `me_armed` require me_x > 950,
# which no sample ever reached - so a round win was structurally impossible regardless of the
# policy. These are set from the measurement instead.
# 440 was too early: verified crossings there produced NO round transition (me_span 6-19 px,
# our fighter never teleported), so the proxy was firing mid-field on an arbitrary x and
# paying the 60-point round term for nothing. Measured arena extremes reach ~512, so the line
# is now at the actual end.
GOAL_X = 500.0         # our goal line is at the right end of the measured arena
GOAL_X_OPP = 20.0      # the CPU goal line is at the left end
# A crossing must be WALKED, not teleported: respawns jump the whole arena in one sample and
# would otherwise be scored as goals. Any single-sample move larger than this invalidates a
# crossing for that sample.
CROSS_MAX_STEP = 60.0


def read_state(iid):
    try:
        v = open(TS.STATE.format(iid)).read().split()
        if len(v) < 6:
            return None
        o154x, o154y, y242x, y242y, h1, h2 = (float(x) for x in v[:6])
        # DO NOT discard the sample when a flag reads 0. MEASURED (raw trace, t=0.25 s):
        # the CPU's existence flag flickers to 0 for a frame or two while the fighter is
        # plainly alive at (262, 560) - a reader flicker, the same artefact that once
        # produced "345 kills, 0 deaths". Returning None here turned every flicker into
        # "the match ended", which aborted episodes one second in. The flags travel with
        # the sample now and the CALLER decides what a 0 means, with a sustained timer.
        # GATE: a (0,0) pair is a not-yet-initialised / frozen instance, not a
        # fighter standing at the goal. Without this the goal-crossing detector
        # counted every blank sample as a round loss (157/episode once).
        if y242x <= 1.0 and o154x <= 1.0:
            return None
        if not (0.0 <= y242x <= 3000.0 and 0.0 <= o154x <= 3000.0):
            return None
        # The flags MUST be included. This function and InstanceManager.read_state()
        # returned different shapes: this one omitted have154/have242, so any caller that
        # then asked has_players() raised KeyError: 'have154'. Measured cost: an episode
        # that had run its whole window (samples=1200) was marked inert by the exception
        # and discarded - the gate error was the only trace, and it hid behind
        # "no match" reporting for hours.
        return {"them_x": o154x, "them_y": o154y, "me_x": y242x, "me_y": y242y,
                "have154": int(h1), "have242": int(h2)}
    except (OSError, ValueError):
        return None


def _act_name(code):
    return {65: "A_left", 68: "D_right", 70: "F_attack", 71: "G_jump", 0: "IDLE",
            None: "IDLE"}.get(code, f"key{code}")


def _at_edge(x):
    """True if x sits at an arena end.

    MEASURED (300 s trajectory, 6224 samples): the arena spans x ~0..462 and kill/respawn
    teleports land at the ends - observed jumps 2->462, 346->0, 246->-32, 256->6. A teleport
    is therefore only a death if it lands at an edge. Requiring that fixed the previous
    failure mode, where a bare "jump > SPAWN_JUMP" test counted 485 deaths in one episode and
    the reward was switched off entirely.
    """
    return x is not None and (x < 60.0 or x > 400.0)


def read_raw(iid):
    """Raw published state, flags included: (o_x, o_y, y_x, y_y, have_o, have_y)."""
    try:
        v = open(TS.STATE.format(iid)).read().split()
        if len(v) < 6:
            return None
        return (float(v[0]), float(v[1]), float(v[2]), float(v[3]),
                float(v[4]), float(v[5]))
    except (OSError, ValueError):
        return None


def play(mgr, w, seconds, seed, tag, log=print):
    if not mgr.ensure_match():
        # Do NOT restart here: the generation loop does one global reset instead.
        return {"fitness": -100.0, "rounds_won": 0, "rounds_lost": 0,
                "match_won": 0, "trace": [], "tag": tag, "no_match": True}

    rng = np.random.default_rng(seed)
    _episode_start = time.time()   # window the adversary judges this episode over
    # A match is ONE round. After it ends the fighters stay on screen but inert, so
    # ensure_match() sees "live" and every later individual reuses the same dead match -
    # measured: 54 episodes ran on a single entry, and all 12 individuals in a generation
    # scored an identical -19.11 because they saw identical, action-independent state.
    # Re-enter whenever the match is not actually moving.
    # SPEED. The game sat at 9.5 fps during play because the speed control file was never
    # written (the only caller was the entry path, which the cached-entry route skips).
    # At that rate a 120 s episode yielded 116-143 state samples instead of ~2400, so with
    # HOLD_TICKS=8 each decision lasted ~8 real seconds and the agent had no control.
    # Setting it per episode makes it independent of which entry branch ran.
    try:
        mgr._raise_speed()
    except Exception:
        pass
    # PHASE 6 (Pau's plan): start every episode from a round boundary, so two policies are
    # compared on the same initial conditions. Without this, one policy produced fits of
    # -0.24 / 7.49 / -16.88 in three consecutive episodes (sd 12.5) and selection was noise.
    try:
        _reset_ok = mgr.start_from_round_boundary()
    except Exception:
        _reset_ok = False
    st0 = read_state(mgr.iid)
    inert = st0 is None
    _adv = {"trust_match": False, "why": "not checked"}
    if not inert and hasattr(mgr, "prime_controls"):
        # The READY state has both fighters on screen and ignores discrete presses. The
        # adversary reports it as "frozen / input not reaching game". Hold a direction
        # first - measured to unlock movement (113.5 -> 428 px under a 2.5 s hold).
        mgr.prime_controls(1.6)
    if not inert:
        xs = []
        tt = time.time()
        while time.time() - tt < 1.5:
            s2 = read_state(mgr.iid)
            if s2:
                xs.append(s2["them_x"])
            time.sleep(0.1)
        # The adversary is the authority on whether this is a real, drivable match. It runs
        # in its own process on its own clock; a stale or failing vote makes the episode
        # unscorable. Motion alone is NOT evidence: the title screen's attract demo moves.
        # ENTRY-TIME GATE (Pau's shape): prove once that input reaches the simulation,
        # then judge the episode on that proof plus fresh state. A per-tick motion test
        # cannot work because a policy may legitimately stand still.
        try:
            # Use the RETRYING path, not a single shot. Measured: a one-shot gate at
            # episode start returned A_px=7.0 against the 8 px threshold and the episode
            # was thrown away, even though entry seconds earlier had passed with 15.0.
            # _drivable_now() primes, re-gates, and uses the cheap Enter accept between
            # attempts, which is exactly what this situation needs.
            gok = mgr._drivable_now()
            mgr.gate_ts = time.time()
            st1 = read_state(mgr.iid)
            fresh = st1 is not None and mgr.has_players(st1)
            _adv = {"entry_gate": gok, "A_px": round(mgr.gate_px, 1),
                    "fresh_state": fresh}
            inert = not (gok and fresh)
        except Exception as e:
            _adv = {"why": f"gate error: {e}"}
            inert = True
        except Exception as e:
            _adv = {"why": f"adversary unavailable: {e}"}
            inert = True
    if inert:
        mgr.press(27); time.sleep(1.5)
        mgr.press(27); time.sleep(1.5)
        mgr.run_entry()

    t0 = time.time()
    trace = []
    prev = None
    held_code = None
    hold_left = 0
    died_me = died_them = False          # deaths since the current round began
    me_deaths = them_deaths = 0          # TOTAL deaths this episode (for shaping)
    prev_flags = None
    rounds_won = rounds_lost = 0
    me_crossed = them_crossed = False
    me_armed = them_armed = False
    last_round_t = 0.0
    matches_won = matches_lost = 0
    match_rounds_won = match_rounds_lost = 0
    best_me = start_me = best_them = worst_them = None
    start_them = None
    next_accept_t = 0.0                  # when to press Enter to start the next round

    def end_round(log=log):
        nonlocal died_me, died_them, rounds_won, rounds_lost
        nonlocal match_rounds_won, match_rounds_lost, matches_won, matches_lost
        # ROUNDS ARE NO LONGER AWARDED HERE. This path attributed round wins to the
        # teleport-based death detector, and that detector is broken: one 120 s episode
        # recorded kills=485 deaths=402 (every position jump counts as a death). That
        # produced "roundsW 7 / roundsL 9" in a generation whose fighter never got past
        # x=604 on a 1650 goal line - phantom wins, exactly like the earlier 10-0.
        # Rounds are now counted ONLY from genuine goal-line crossings below.
        died_me = died_them = False
        if match_rounds_won >= ROUNDS_TO_WIN:
            matches_won += 1
            match_rounds_won = match_rounds_lost = 0
        elif match_rounds_lost >= ROUNDS_TO_WIN:
            matches_lost += 1
            match_rounds_won = match_rounds_lost = 0

    saw_player = False
    gone_since = None
    accept_tries = [0]
    death_actions = []
    cross_verdicts = []
    real_samples = 0
    exit_reason = "window-complete"
    sum_me = 0.0
    min_abs_dx = None
    while time.time() - t0 < seconds:
        # DEATH = the fighter's existence flag drops. read_state() deliberately
        # returns None when a flag is 0, so this check MUST run before that gate -
        # otherwise the death is never observed (measured: 0 deaths in 10 episodes).
        raw = read_raw(mgr.iid)
        # TRACE THE FIRST SECONDS. Episodes are dying ~1 s after a passing gate with
        # "accept-failed", and a round cannot end in one second - so the loop is almost
        # certainly misreading a brief gap in the state file as a round boundary. Print the
        # raw flags for the early part of each episode so the next run shows which it is.
        if real_samples < 25 and (time.time() - t0) < 6.0:
            print(f"    {tag} t={time.time()-t0:5.2f} raw={raw}", flush=True)
        if raw is not None and prev_flags is not None:
            if prev_flags[0] > 0.5 and raw[4] < 0.5:
                them_deaths += 1
            if prev_flags[1] > 0.5 and raw[5] < 0.5:
                me_deaths += 1
        if raw is not None:
            prev_flags = (raw[4], raw[5])
        st = read_state(mgr.iid)
        # "gone" now means OUR fighter is absent AND the state is unreadable. A flicker in
        # the OPPONENT's flag is not an absence: measured at t=0.25 s the CPU flag dropped
        # while its position read (262, 560). Treating that as gone aborted the episode.
        # OUR fighter absent, judged by POSITION: the have242 flag read 0 for a sustained
        # 76 s during live play (independent observer), so it cannot be the liveness test.
        gone = st is None or not (0.5 < abs(st.get("me_x") or 0.0) < 3000.0)
        if gone:
            # once we have seen a live fighter, a sustained absence means the match
            # ended: stop the window and let the manager start a fresh process.
            if saw_player:
                gone_since = gone_since or time.time()
                # 8 s, not 2.5: a ROUND transition also hides both fighters for a
                # moment, and 2.5 s cut every episode off after a single round, so
                # a best-of-5 match only ever yielded one round of signal.
                if time.time() - gone_since > 4.0:
                    # A round just ended. Press accept to start the NEXT round instead
                    # of closing the episode: with one round per episode every episode
                    # was exactly "rounds 0-1", which gives the GA almost no signal.
                    accept_tries[0] += 1
                    if accept_tries[0] <= 2:
                        # 1.2 s was far too short. MEASURED (results/restart_0.json):
                        # after a round ends, Enter brings the fighters back in 7.61 s.
                        # Pressing and then looking again 1.2 s later always saw "still
                        # gone", so every round looked like the end of the match.
                        print(f"  {tag}: round over, accepting next "
                              f"(try {accept_tries[0]})", flush=True)
                        # Enter alone was not enough: with the policy pressing keys, the
                        # post-round screen sometimes ignored it and the episode ended at
                        # samples=51. Fall back to the alternating Enter/Space path and
                        # record which one worked, so the next run can stop guessing.
                        got = mgr._accept_restart(tries=3, wait=8.0)
                        print(f"  {tag}: accept via alternate keys -> {got}", flush=True)
                        if not got:
                            exit_reason = "accept-failed-alternate"
                            break
                        gone_since = None
                        continue
                    exit_reason = "accept-failed-after-2-tries"
                    print(f"  {tag}: match over, ending window (accept failed)", flush=True)
                    break
            time.sleep(0.05)
            continue
        saw_player = True
        real_samples += 1
        sum_me += st["me_x"]
        adx = abs(st["them_x"] - st["me_x"])
        min_abs_dx = adx if min_abs_dx is None else min(min_abs_dx, adx)
        gone_since = None
        if start_me is None:
            start_me, best_them = st["me_x"], st["them_x"]
            start_them = st["them_x"]
            best_me, worst_them = st["me_x"], st["them_x"]
        best_me = max(best_me, st["me_x"])
        worst_them = min(worst_them, st["them_x"])
        best_them = max(best_them, st["them_x"]) if best_them is not None else st["them_x"]
        max_them = best_them
        if prev is not None:
            me_jump = abs(st["me_x"] - prev["me_x"]) > SPAWN_JUMP
            them_jump = abs(st["them_x"] - prev["them_x"]) > SPAWN_JUMP
            if me_jump and them_jump:
                end_round()                       # full reset: attribute it
                start_me, best_them = st["me_x"], st["them_x"]
                start_them = st["them_x"]
                best_me, worst_them = st["me_x"], st["them_x"]
            elif me_jump and _at_edge(st["me_x"]):
                died_me = True                    # we respawned at an arena end => we died
                me_deaths += 1
                # HOW did we die? Record the action we were holding. Measured need: the agent
                # loses every exchange and we had no evidence about whether that is
                # overcommitment (dying while attacking) or passivity (dying while idle). The
                # action space is small enough that this histogram names the cause.
                death_actions.append(_act_name(held_code))
            elif them_jump and _at_edge(st["them_x"]):
                died_them = True
                them_deaths += 1

        # WINNING THE ROUND IS CROSSING TO THE FAR END, not a kill. In Nidhogg
        # you win a round by reaching your opponent's goal. Rooms span ~0..1920,
        # so crossing beyond GOAL_X is a round win for whoever crossed.
        # A round is won/lost only on a genuine TRANSITION toward that goal line.
        # A respawning fighter sits at x ~ 0 (the CPU's spawn side), which used to
        # be read as "crossed our goal" and produced 1110 phantom losses in 10
        # episodes. Track approach from deep in the field, then require the cross.
        # armed once we have been back in our own half this episode (the old
        # `me_x > GOAL_X - 700` was true from the first sample in a 470 px arena)
        if st["me_x"] < GOAL_X * 0.55:
            me_armed = True
        now_t = time.time()
        # A round win must be a GENUINE crossing between consecutive samples, not a
        # respawn that happens to land past the goal line. Measured: a fresh population
        # reported 10 wins in 10 rounds while its fighter never left x=808..897, which
        # is exactly this bug. Requiring prev sample < GOAL_X-150 kills the phantom.
        # walked, not teleported: the step into the goal must be small. Measured teleports
        # cover a whole arena (2 -> 462) in one sample, so this rejects respawns cleanly.
        # SELF-CONTRADICTION FIXED. The old guard required prev < GOAL_X - 150 AND now >=
        # GOAL_X in the same sample - a 150+ px jump - while CROSS_MAX_STEP = 60 forbids any
        # step over 60 px. Both could never be true at once, so `genuine_cross` was UNREACHABLE
        # and no policy could ever score a round. (Session 145 "round wins are reachable" was
        # therefore wrong: I changed GOAL_X 1650 -> 440 and added the step limit, but left the
        # 150 px arming margin, which in a 470 px arena is a third of the field.)
        # Correct form: cross the line in one ordinary step, having previously been back in our
        # own half.
        genuine_cross = (prev is not None
                         and prev["me_x"] < GOAL_X
                         and st["me_x"] >= GOAL_X
                         and abs(st["me_x"] - prev["me_x"]) < CROSS_MAX_STEP
                         and me_armed and now_t - t0 > 3.0)
        if genuine_cross and me_armed and not me_crossed and now_t - last_round_t > 6.0:
            # VERIFY THE PROXY IN PASSING. Our round counter fires when our fighter walks past
            # x>=GOAL_X, but nothing yet proves the GAME agrees. A real round transition moves
            # both fighters far (the arena resets); if our fighter simply keeps walking, the
            # proxy is fiction. Watched once, quietly, right after each crossing.
            try:
                _watch = []
                _tw = time.time()
                while time.time() - _tw < 1.5:
                    _s = read_state(mgr.iid)
                    if _s:
                        _watch.append(_s)
                    time.sleep(0.05)
                if _watch:
                    _me_span = max(w["me_x"] for w in _watch) - min(w["me_x"] for w in _watch)
                    _th_span = max(w["them_x"] for w in _watch) - min(w["them_x"] for w in _watch)
                    # BOTH fighters must reposition. Measured: four crossings gave
                    # me_span 6-19 px - our fighter never teleported - so no round was
                    # ending. The old `or` accepted a CPU merely running 220 px as a
                    # transition, which is not a round end.
                    _transition = _me_span > 200 and _th_span > 200
                    cross_verdicts.append(bool(_transition))
                    print(f"  {tag}: CROSSING VERIFY me_span={_me_span:.0f} "
                          f"them_span={_th_span:.0f} transition={_transition}", flush=True)
            except Exception:
                pass
            rounds_won += 1; match_rounds_won += 1
            me_crossed = True; me_armed = False
            last_round_t = now_t
            next_accept_t = now_t + 2.5
            if match_rounds_won >= ROUNDS_TO_WIN:
                matches_won += 1
                match_rounds_won = match_rounds_lost = 0
        if st["me_x"] < GOAL_X - 400:
            me_crossed = False
        if st["them_x"] > GOAL_X * 0.45:
            them_armed = True
        genuine_cross_them = (prev is not None
                              and prev["them_x"] > GOAL_X_OPP
                              and st["them_x"] <= GOAL_X_OPP
                              and abs(st["them_x"] - prev["them_x"]) < CROSS_MAX_STEP
                              and them_armed and now_t - t0 > 3.0)
        if genuine_cross_them and them_armed and not them_crossed and now_t - last_round_t > 6.0:
            rounds_lost += 1; match_rounds_lost += 1
            them_crossed = True; them_armed = False
            last_round_t = now_t
            next_accept_t = now_t + 2.5
            if match_rounds_lost >= ROUNDS_TO_WIN:
                matches_lost += 1
                match_rounds_won = match_rounds_lost = 0
        if st["them_x"] > GOAL_X_OPP + 400:
            them_crossed = False
        # After a round ends the game waits on a READY screen. Pressing accept starts
        # the next round, which is the only way to get more than ONE round of signal
        # into a 45 s window (measured: every episode was exactly 1 round, 42/42).
        if next_accept_t and time.time() >= next_accept_t:
            mgr.press(13)
            next_accept_t = 0.0
        # relative approach speed, for strike timing (see neuro.obs_vector input 5)
        if prev is not None:
            gap_now = st["them_x"] - st["me_x"]
            gap_prev = prev["them_x"] - prev["me_x"]
            dt = max(1e-3, time.time() - prev.get("_t", time.time()))
            vel = (gap_now - gap_prev) / dt
            st["dx_vel"] = 0.7 * st.get("dx_vel", 0.0) + 0.3 * vel
        st["_t"] = time.time()
        prev = st
        trace.append([round(time.time() - t0, 2), round(st["me_x"]), round(st["them_x"])])
        # ACTION REPEAT: hold each decision for HOLD_TICKS samples. Deciding at
        # 50 Hz meant the aim changed between pressing attack and the swing
        # landing, so no attack ever resolved coherently.
        if hold_left <= 0 or held_code is None:
            held_code = neuro.decide(w, st, rng)
            hold_left = HOLD_TICKS
        hold_left -= 1
        if held_code:
            mgr.press(held_code)
        time.sleep(0.02)

    progress = 0.0
    if start_me is not None:
        progress = ((best_me - start_me) - (best_them - worst_them)) / 100.0
    # NOTE: a kill/death shaping term was tried here and REMOVED. Measured: 0 deaths
    # were detected across 20 episodes even though 10 rounds were lost, because a
    # respawn often lands within SPAWN_JUMP(300 px) of where the fighter died, so the
    # teleport test misses it. A permanently-zero term is noise, not signal. Death
    # detection needs the visibility-gap signal instead (fighter vanishes, then
    # reappears) - that is the next thing to build.
    # DIAGNOSTIC ONLY - never in fitness. Measured: 485 "kills" in one episode from the
    # teleport detector, which would contribute +249 and swamp every real term.
    # Kills and deaths, now measured by the edge-teleport signature rather than a bare
    # jump threshold (which produced 485 false kills and had to be disabled). Weighted well
    # below a round win (60) but enough to shape a fight: taking a stock is progress toward
    # crossing, and dying hands the CPU ground.
    # PRIMARY SIGNAL: net kills. An integer count per episode, so its variance is far lower
    # than the continuous territory terms (measured sd ~12 across reps of one policy, vs a
    # spread of ~5 for the kill counts themselves). Taking a stock is the mechanical
    # precondition for crossing the goal, so this points at the objective as well as being
    # measurable.
    # SMALL NET TERM. The kill-dominant version (20 per net stock) was measured as NOISIER
    # than territory (sd 23.3 vs 11.8) and produced spreads from -97.6 to +22.7 within one
    # policy. Kept here only as a nudge, because kills are a genuine precondition for
    # crossing while territory is the measured lower-variance signal.
    # NET stocks, not separate rewards. Measured immediately after the first version:
    # g0i0r2 with kills=3, deaths=3 scored fit=28.9 and g0i0r3 with the same 3/3 scored 32.3 -
    # i.e. an EVEN trade was being paid +30, because 25 per kill against 15 per death is a
    # 5:3 ratio. A one-for-one exchange should be worth nothing. Now it is.
    kills_reward = 6.0 * (them_deaths - me_deaths)
    # TERRITORY IS THE LEARNING SIGNAL. Measured: every individual scored an identical
    # -8.3 because a Training match is ONE round, so the win/loss term is a single bit
    # and the GA has nothing to differentiate on. These continuous terms give a gradient
    # inside that round: ground gained, ground conceded, and how far we got at best.
    advance = 0.0
    conceded = 0.0
    if start_me is not None and best_me is not None:
        # SUSTAINED advance, not peak: using best_me rewarded one lucky frame, and the
        # measured advance sat at 170-182 px over a whole 70 s episode (~2.5 px/s) while
        # holding a direction reaches ~17 px/s. Mean position rewards actually holding
        # ground toward the goal instead of twitching.
        mean_me = sum_me / max(1, real_samples)
        advance = (mean_me - start_me) / 100.0          # px converted to "metres"
        # must use the CPU's START x: best_them is now a running MAX (see pushed below)
        conceded = (start_them - worst_them) / 100.0 if start_them is not None else 0.0
    # GOAL PROXIMITY: with the current window no round resolves (30/30 episodes ended
    # 0-0), so nothing rewarded actually approaching the goal line. This term does, and
    # it is the only path by which a crossing - and therefore a round win - can appear.
    proximity = 0.0
    # REMOVED: proximity used to pay 4.0 * (best_me / GOAL_X) - a flat reward for existing
    # at a position on the field. Measured here: all six individuals in a generation scored
    # an IDENTICAL 10.9, which is the signature of a term that cannot depend on the policy.
    # Standing next to the CPU outscored taking ground, so the GA had no gradient toward
    # the goal line. A position is not an achievement.
    # PUSH THEM BACK. Measured: running alone gains ~366 px and then gets shoved back to
    # the start, so the only way to hold ground is to win exchanges. Nothing rewarded
    # that: `conceded` only punishes being pushed. This term pays for driving the CPU
    # toward its own goal, which is what attacking is for.
    pushed = 0.0
    if start_them is not None and best_them is not None:
        pushed = (best_them - start_them) / 100.0
    # CLOSE TO STRIKING DISTANCE. Measured: a strike only lands at |dx| <= 22 px
    # (+51 px of push at 22, 0 px at 59), and `pushed` was 0.00 in every episode - the
    # agent never closes. This pays for getting near the opponent, which is the
    # precondition for ever winning an exchange.
    closeness = 0.0
    if min_abs_dx is not None:
        # Weight cut 5.0 -> 1.0. Measured with 5.0: the agent engaged and LOST every
        # round (roundsL 10/10, CPU crossing our line each time) - closing distance was
        # worth more than surviving the contact, so it learned to rush in and die.
        # Closing is a precondition, not the objective; the outcome has to pay more.
        closeness = 1.0 * max(0.0, 1.0 - min_abs_dx / 200.0)
    territory = (2.0 * advance - 4.0 * conceded + proximity
                 + 12.0 * pushed + closeness)
    # THE NOISY TERMS ARE DEMOTED, NOT REMOVED. Measured (Session 151): four reps of ONE
    # policy gave sd 11.76 on a score dominated by the territory terms, which is larger than
    # any plausible difference between two policies. Kills (integer) now carry the objective;
    # territory and progress are kept at a quarter weight as directional shaping only.
    SHAPING = 1.0
    fitness = (60.0 * rounds_won - 30.0 * rounds_lost
               + 150.0 * matches_won - 80.0 * matches_lost
               + kills_reward
               + SHAPING * float(np.clip(progress, -5, 5))
               + SHAPING * float(np.clip(territory, -12, 12)))
    # AN EPISODE AGAINST A STATUE IS NOT AN EPISODE. Measured (Session 166): five of six
    # episodes had the CPU pinned at x=203 for the full 60 s - kills=0, deaths=0, rounds 0-0 -
    # while the entry gate reported PASS because only OUR fighter was tested. A training match
    # must have an opponent that plays, so an episode where the opponent never moved 15 px is
    # discarded no matter how good the rest of the numbers look.
    _th_span = None
    try:
        _th_span = abs(best_them - worst_them) if (best_them is not None and worst_them is not None) else None
    except Exception:
        pass
    inert_opponent = (_th_span is not None and _th_span < 15.0 and real_samples > 20)
    if inert_opponent:
        log(f"  {tag}: DISCARDED - opponent moved only {_th_span:.1f} px in {real_samples} "
            f"samples (inert opponent, not a training match)")
    # unscorable if we never reached a live, drivable match, or could not see enough of it
    no_match = (real_samples < 20) or bool(inert) or inert_opponent
    # attribute every abandonment instead of inferring it later
    # COORDINATE CALIBRATION. The round win/loss detector compares against GOAL_X=1650 and
    # GOAL_X_OPP=250, and `me_armed` needs me_x > GOAL_X-700 = 950. Every position observed
    # today was well below that, which would make a round win structurally impossible. The
    # exact arena range in THIS build is unknown, so record it per episode instead of
    # assuming it.
    _me_rng = ""
    if start_me is not None and best_me is not None:
        _me_rng = f" me=[{start_me:.0f}..{best_me:.0f}]"
    _th_rng = ""
    if start_them is not None and worst_them is not None:
        _th_rng = f" them=[{worst_them:.0f}..{best_them:.0f}]"
    log(f"  {tag}: exit={exit_reason} samples={real_samples} inert={bool(inert)} "
        f"adv={_adv}{_me_rng}{_th_rng} kills={them_deaths} deaths={me_deaths} "
        f"opp_span={(_th_span if _th_span is not None else -1):.0f} "
        f"death_acts={death_actions} cross_verified={cross_verdicts} "
        f"reset={_reset_ok}")
    rec = {"no_match": bool(no_match), "adversary": _adv,
           "real_samples": real_samples,
           "advance": round(advance, 2), "conceded": round(conceded, 2),
           "territory": round(territory, 2), "fitness": round(fitness, 2),
           "pushed": round(pushed, 2), "closeness": round(closeness, 2),
           "min_dx": (round(min_abs_dx, 0) if min_abs_dx is not None else None),
           "kills": them_deaths, "deaths": me_deaths, "rounds_won": rounds_won,
           "rounds_lost": rounds_lost, "matches_won": matches_won,
           "matches_lost": matches_lost, "progress": round(progress, 2),
           "trace": trace, "tag": tag, "weights": w.tolist()}
    log(f"  {tag} (inst {mgr.iid}): fit={fitness:.1f} rounds {rounds_won}-{rounds_lost} "
        f"matches {matches_won}-{matches_lost}")
    # END-OF-EPISODE RESTART. A round ends when the episode ends, and the state file then
    # drops to "no fighters". Discovering that at the START of the next individual forced a
    # full menu re-entry (measured this session: 2-3 minutes per individual, so a generation
    # of six rarely completed). Pressing Enter here, while we still know a round boundary
    # just happened, starts the next match in well under a second.
    try:
        # Settle first: right at the end of an episode the round-over screen may still be
        # showing both fighters, so an immediate check sees "players present" and skips the
        # restart - and by the time the next individual asks, they are gone and it pays the
        # full menu re-entry. Wait for the state to settle, then act.
        time.sleep(2.0)
        if not mgr.has_players(mgr.read_state()[0]):
            mgr._accept_restart()
    except Exception:
        pass
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--instances", type=int, default=4)
    ap.add_argument("--gens", type=int, default=10)
    ap.add_argument("--pop", type=int, default=16)
    ap.add_argument("--window", type=float, default=45.0)
    ap.add_argument("--seed", type=int, default=5)
    ap.add_argument("--init", action="store_true")
    ap.add_argument("--reps", type=int, default=2)
    args = ap.parse_args()

    os.environ["NID_ORDERS"] = "1"
    os.system('pkill -f "MacOS/Nidhogg" 2>/dev/null')
    # (removed) this used to run `pkill -f train_win.py`, whose pattern matches the very
    # process running it - starting a training run killed itself a moment later.
    time.sleep(2)
    # the prefs file is chmod 444 while a run is active (so injected menu keys cannot
    # rewrite the user's settings); unlock before writing, launch() re-locks it.
    try:
        os.chmod(TS.PREFS, 0o644)
    except OSError:
        pass
    with open(TS.PREFS, "w") as f:
        f.write(open(TS.MUTED_PREFS).read())

    pop = neuro.Population(size=args.pop, seed=args.seed)
    # warm start: if a previous run left a best policy, seed the population with it
    import os as _os
    seed_path = "/tmp/nid_best_win.json"
    if args.init and _os.path.exists(seed_path):
        try:
            prev = json.load(open(seed_path))["weights"]
            w0 = np.array(prev, dtype=float)
            if w0.shape[0] == neuro.N_WEIGHTS:
                pop.W[0] = w0
                for i in range(1, 4):
                    pop.W[i] = w0 + np.random.default_rng(args.seed + i).normal(0, 0.06, w0.shape)
                print(f"warm start from previous best (fitness {json.load(open(seed_path)).get('fitness')})", flush=True)
        except Exception as exc:
            print("warm start skipped:", exc, flush=True)
    mgrs = [TS.InstanceManager(iid=i) for i in range(args.instances)]
    for m in mgrs:
        m.launch()
    time.sleep(TS.BOOT_WAIT)
    for m in mgrs:
        m.run_entry()
    for m in mgrs:
        m.wait_for_match()
    # 600 is the measured sweet spot: 226 fps in game, vs 124 at 1200 and 154 at 2000
    for m in mgrs:
        try:
            with open(TS.SPEED.format(m.iid), "w") as f:
                f.write("600\n")
        except OSError:
            pass
    time.sleep(3)

    best_overall = None
    for gen in range(args.gens):
        # process hygiene: the runner re-execs itself, and any missed child would
        # accumulate across restarts. At each generation boundary, if the count has
        # drifted above 2x our instances, sweep everything and let ensure_match
        # relaunch cleanly (it is designed to).
        if any(m.needs_reset for m in mgrs):
            reset_all(mgrs)
            for m in mgrs:
                m.needs_reset = False
        pids = TS.InstanceManager._nidhogg_pids()
        # Careful: the runner re-execs itself via SteamAPI_RestartAppIfNecessary, so 2
        # processes are normal for a moment during a launch. Tightening this to `> len(mgrs)`
        # made the sweep kill a healthy instance 8 s after a passing gate - measured, with
        # the log showing "control gate A_px=15.0 (PASS) / live AND drivable" then instantly
        # "== sweep: 2 game processes, resetting". Only sweep on real accumulation.
        if len(pids) > 2 * len(mgrs) + 2:
            print(f"== sweep: {len(pids)} game processes, resetting", flush=True)
            os.system('pkill -f "MacOS/Nidhogg"')
            time.sleep(3)
        results = [None] * len(pop.W)
        # ONE EPISODE AT A TIME PER INSTANCE. This used to spawn a thread per individual
        # with `mgrs[i % len(mgrs)]`, so with --instances 1 six threads drove the SAME
        # game concurrently: six interleaved key streams, six concurrent ensure_match /
        # restart calls (which is where four `launched pid` lines inside one second came
        # from), and episodes whose state was mangled by the others. It also made every
        # individual's fitness depend on the neighbours rather than on its own weights.
        # Now individuals are grouped by instance: parallel ACROSS instances, serial
        # WITHIN one.
        buckets = [[] for _ in mgrs]
        for i in range(len(pop.W)):
            buckets[i % len(mgrs)].append(i)

        def run_bucket(slot):
            for i in buckets[slot]:
                # An exception inside play() used to kill this thread silently: results[i]
                # stayed None, the "missing" filter skipped None rows, and the episode
                # vanished with no log line at all. That is why runs showed entry working
                # and then no episodes, with nothing to read.
                try:
                    # REPEATED MEASURES. Measured this session: the same seed scored 19.4 in
                    # one episode and -1.6 in another, and the ranking REVERSED between runs
                    # (always-attack 25.6 -> 2.2, always-right -1.6 -> 19.4). One episode
                    # cannot rank two policies; per-episode noise swamps the difference. Each
                    # individual is played `reps` times and the fitness averaged.
                    runs = [play(mgrs[slot], pop.W[i], args.window,
                                 gen * 997 + i * 7 + rep, f"g{gen}i{i}r{rep}")
                            for rep in range(getattr(args, "reps", 2))]
                    valid = [r for r in runs if r and not r.get("no_match")]
                    if not valid:
                        results[i] = runs[0] if runs else None
                    else:
                        avg = dict(valid[0])
                        avg["fitness"] = float(np.mean([r["fitness"] for r in valid]))
                        avg["fitness_all"] = [round(r["fitness"], 2) for r in valid]
                        for k in ("rounds_won", "rounds_lost", "matches_won",
                                  "matches_lost", "kills", "deaths"):
                            avg[k] = int(np.mean([r.get(k, 0) for r in valid]))
                        avg["tag"] = f"g{gen}i{i}"
                        avg["no_match"] = False
                        results[i] = avg
                        print(f"  g{gen}i{i}: reps={len(valid)} "
                              f"fits={avg['fitness_all']} mean={avg['fitness']:.2f}",
                              flush=True)
                except Exception:
                    import traceback
                    print(f"  g{gen}i{i}: play() RAISED:", flush=True)
                    traceback.print_exc()
                    results[i] = {"fitness": -100.0, "rounds_won": 0, "rounds_lost": 0,
                                  "no_match": True, "tag": f"g{gen}i{i}",
                                  "trace": [], "error": "see traceback"}

        threads = [threading.Thread(target=run_bucket, args=(slot,))
                   for slot in range(len(mgrs)) if buckets[slot]]
        for th in threads:
            th.start()
        for th in threads:
            th.join()
        good = [r for r in results if r and not r.get("no_match")]
        if len(good) < len(results):
            # one global reset, then re-run only the individuals that had no match
            missing = [i for i, r in enumerate(results) if r and r.get("no_match")]
            print(f"== gen {gen}: {len(missing)} individuals had no match, resetting",
                  flush=True)
            reset_all(mgrs)
            for i in missing:
                w = pop.W[i]
                tag = f"g{gen}i{i}"
                results[i] = play(mgrs[i % len(mgrs)], w, args.window,
                                  gen * 997 + i, tag)
            good = [r for r in results if r and not r.get("no_match")]
        if not good:
            print(f"== gen {gen}: all failed", flush=True)
            continue
        pop.next_gen([r["fitness"] for r in results])
        best = max(good, key=lambda r: r["fitness"])
        mean = float(np.mean([r["fitness"] for r in good]))
        print(f"== gen {gen} best {best['fitness']:.2f} mean {mean:.2f} "
              f"roundsW {sum(r['rounds_won'] for r in good)} "
              f"roundsL {sum(r['rounds_lost'] for r in good)} "
              f"matchW {sum(r['matches_won'] for r in good)}", flush=True)
        if best_overall is None or best["fitness"] > best_overall["fitness"]:
            best_overall = best
        with open("/tmp/nid_win_history.json", "w") as f:
            json.dump({"gen": gen, "best": best["fitness"], "mean": mean}, f)
        for r in results:
            with open(LOG, "a") as f:
                f.write(json.dumps(r) + "\n")
        if best_overall:
            with open("/tmp/nid_best_win.json", "w") as f:
                json.dump({"fitness": best_overall["fitness"],
                           "weights": best_overall["weights"],
                           "rounds_won": best_overall["rounds_won"],
                           "rounds_lost": best_overall["rounds_lost"]}, f)

    print("best:", best_overall["fitness"] if best_overall else None, flush=True)
    for m in mgrs:
        m.close()
    with open(TS.PREFS, "w") as f:
        f.write(open(TS.PRISTINE_PREFS).read())
    print("done; prefs restored", flush=True)


if __name__ == "__main__":
    main()
