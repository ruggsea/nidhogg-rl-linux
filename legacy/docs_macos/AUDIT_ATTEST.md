# Audit: attestation chain (launch -> navigate -> room -> bind -> gate -> opponent)

Read: `tools/attest.py`, `train_state.py` (prove_control, bind_by_response, read_pair, read_state,
_try_entry, execute entry path), `train_win.py` (state_of, episode loop). No files modified.

Verdict in one line: the chain proves that *some* instance in the game moved right while D was
held and left while A was held, once, for 1.8 s each. It does not prove that instance is a
fighter, that it is ours, that the keys caused the motion, or that the episode the GA scores is
the same one. All four false positives named in the brief are still reachable: the write gate
still passes on an attract demo walking under the keys (A1-A4), the attract demo is still a
legal room (A5), real fights are still discarded (B1-B12), and the selection leak narrowed but
did not close (C1-C2).

---

## A. Ways it reports success without the agent controlling a fighter

**A1. Bind can bind to the CPU / attract-demo AI.** `train_state.py:899-952`. Three
single-frame snapshots (`before`/`mid`/`after`, `:935-943`), 1.5 s holds, `min_px=6.0`. Any
instance that happens to walk right during window 1 and left during window 2 wins, which is the
normal behaviour of an AI-driven fighter, and the AI is the most mobile actor on screen. There is
no baseline, no key-up control window, no latency requirement, no repeat trial.
Fix: require the contrast. No-key windows must stay under measured drift, the response must begin
within 3 published frames of key-down (`_frame_now`, `train_state.py:738`) and stop within 3
frames of key-up; 6 randomised alternating holds, pass only if >=5/6 correct.

**A2. Bind's sort prefers the biggest mover, not a player body.** `train_state.py:952`:
`winners.sort(key=lambda w: (0 if w[0] and abs(w[1]) >= 20 else 1, ...))`. The comment above it
says "prefer a candidate whose object index looks like a player body (244/154)" but the code
tests `abs(w[1])` (dx magnitude). The stated guard against UI elements is not implemented, and
the implemented key actively selects for the AI.
Fix: carry the object index into the winner tuple from `before[inst][0]` and key on it
(`obj in (154, 244, 242)`), then on |dx|. The information is already in `snapshot()`.

**A3. The gate's motion is cheap: max-over-window, 6 px, 1.8 s.** `train_state.py:508-523`.
`best = max(best, (x - x0)*sign)` over 90 samples, `min_px=6.0`. Drift, walk-cycle slack or one
knockback gives D=+6 and (in the next window) A=+6. Nothing measures no-input drift, so the
threshold is uncalibrated.
Fix: compute drift over a keyless 1.8 s window first, set `min_px = drift_max + 3*sd`, and score
each direction from the position at the start of that hold (see B2).

**A4. `prove_control` runs on the named path when nothing is bound.** `train_state.py:500-507`:
if `bound_inst is None` it reads object 242 and can pass. The project's own measurement says 242
is not the fighter we command. So the gate can pass with zero binding, and `_drivable_now`'s
`break_ready` branch (`:1118-1128`) returns True without ever calling `bind_by_response`.
Fix: `prove_control` returns False when `bound_inst is None`; re-run gate + bind after
`break_ready` (the instance layout changed).

**A5. Room check cannot see the attract demo: the demo runs in room 29.** `tools/attest.py:28`
`TITLE_ROOMS = {2}`, and `train_state.py:446` `ARENA_ROOMS = set(range(26,78)) - {69,78}` includes
29. Repo history (a6d1320) records exactly this: the attract demo runs in an arena room. So
"left title room" `attest.py:101-103` and `in_arena()` both accept the title screen. Room is
never consulted again after step 3, and `ensure_match` (`:1240-1279`) does not consult it at all.
Fix: exclude the attract room explicitly, and require the pre-match progression (rMultiMenu 3 ->
rPreMatch 25) to have been observed, i.e. the room check is "we walked the path", not "not room 2".

**A6. `navigate()` result is discarded; navigation is open-loop.** `tools/attest.py:97` calls
`navigate(mgr)` and ignores its return; the only room assertion is `:101`. `navigate` uses fixed
`time.sleep(2.5)` per key (`:74-76`) and logs the room after each step but never branches on
it, unlike `_press_verified`/`_step` (`train_state.py:589-632, 714-724`). A run that lands in
OPTIONS, rLevelSelect or rTrophyRoom passes step 3 (any room except 2).
Fix: `ok["nav"] = navigate(mgr)`; make each step assert the expected room index from
`ROOM_NAMES.md` and abort otherwise.

**A7. Presence is accepted as a match, and menu coordinates count as valid.** `_pos_valid`
(`train_state.py:397-398`) accepts `0.5 < |x| < 3000`, so the title/menu characters at x~1288
count as two live fighters; `has_players` (`:417-434`) therefore returns True on the title
screen, and `_try_entry` accepts it at `:861-870` ("if we have players, entry succeeded") before
any gate runs. `screen_kind`'s `>1200` test is never used in that path.
Fix: valid arena x is ~0..600; anything outside is "menu", not "player present".

**A8. `state_of` silently downgrades from the bound instance to the named path.**
`train_win.py:95-105`: `read_pair()` returns None -> `read_state(iid)` (objects 242/154) with no
log, no invalidation, no episode flag. This happens on every round reset, because the fighter
instance is destroyed and recreated: `read_bound` (`train_state.py:331-348`) matches instance id
only, so the id is gone. From then on the episode scores a different entity, and
`screen_kind(st0)` (`train_win.py:653`) uses that same entity, so the one check that catches a
menu (`>1200`) is bypassed whenever binding is active: `read_bound` coordinates come from a dump
that filters `fx < 1200` (`hook/inject.m:1168`), so the check can never fire while bound.
Fix: `bound_inst is not None and read_pair() is None` -> unbind, mark segment invalid, log;
compute the screen test from the named state and the room, independent of binding.

**A9. Instance ids are trusted without their object index, and are never re-verified.**
`train_state.py:344` matches `int(p[0]) == self.bound_inst` only; the bind result stores the id
alone (`:955-957`). If the id is recycled by another object (effects, the other fighter, a
duplicate Man instance) the gate and `read_pair` read the wrong entity with no error.
Fix: store `(id, object_index)` at bind and require both to match on every read; invalidate on
mismatch.

**A10. `read_pair` invents its presence flags and picks "them" by x only.**
`train_state.py:370-375`: candidates are any instance whose object index is in `(154,244,242)`,
chosen as nearest in x to us, excluding only our instance id; `have154`/`have242` are hardcoded
to 1. Consequences: if our fighter is object 244 and a second 244 instance exists (duplicate,
spawn ghost), "them" becomes us; if bind landed on the CPU (A1), "them" becomes our real
fighter, so kills/advance/conceded are inverted and the "opponent is not a statue" check is
satisfied by our own fighter. Downstream `has_players` is trivially true.
Fix: require a distinct instance id *and* a distinct object index, require |y_me - y_them| < 40 and
opposite halves of the arena at least once, and pass the real flags through.

**A11. The opponent check reads the named path, so it can be the bound instance.**
`tools/attest.py:116` -> `train_state.py:962-985` (`read_state`, object 154). Nothing asserts the
opponent instance is not `bound_inst`. If bind landed on 154 (possible via A1), step 6 measures
the fighter we already accepted as ours.
Fix: opponent = `read_pair()[them instance id]`, assert `id != bound_inst` and `obj != bound_obj`.

**A12. `in_arena`, `read_bound`, `read_pair` do no staleness check, and stale files survive
launch.** `train_state.py:452-458` and `:331-375` read `/tmp/nid_room_now_<iid>.txt` and
`/tmp/nid_insts_<iid>.txt` with no mtime test, while `read_state` (`:377-395`) does check mtime.
`clean_files` (`:122-127`) removes only STATE, KEYS, INJECT_LOG — not INSTS, ROOM, the room_now
channel, SPEED, VARS or OBJS. After a relaunch that fails to inject, the pre-flight chain reads
the previous process's files: room says arena, instances say fighters.
Fix: delete all `/tmp/nid_*_<iid>.*` in `launch()`, and reject any read older than 1.0 s.

**A13. `publish_instances` reads the instance hash table from a second thread.**
`hook/inject.m:1141-1180` runs at ~60 ms cadence on the probe thread while the game mutates the
table. A torn read pairs an id with another instance's coordinates. `bind_by_response` takes
single snapshots, so one torn frame can nominate a phantom responder or break a real one.
Fix: publish two consecutive ticks and only emit an id whose position advanced plausibly
(|dx| < 60 px) in both; have the reader take the median of 3 snapshots.

**A14. The gate is proven once per episode, never after a mid-episode state change.**
`train_win.py:226` gates at entry; the loop then presses Enter to start the next round
(`:352`, `:524`) and `start_from_round_boundary` (`train_state.py:986-1025`)
presses Enter before the gate. READY, arcade and round-over screens are all reachable after the
last proof, and nothing re-checks.
Fix: after every accept/restart, re-run `prove_control` + `read_pair`; if it fails, close the
segment and mark those samples invalid instead of folding them into the total.

**A15. A failed gate does not disqualify the episode.** `train_win.py:239-243`: if `inert`, it
presses Esc twice, calls `run_entry()`, and then falls through into the scoring loop with no
`return`. Disqualification is only `real_samples < 20 or inert_opponent or frozen_agent or
main_screen` (`:688-689`), all motion-based, and the attract demo satisfies all of them.
Fix: `inert` -> no_match unless the re-entry is followed by a passing gate *and* a bind in the
same match.

**A16. `gate_px` collapses D and A into one number and is logged as "A_px".**
`train_state.py:521` `self.gate_px = max(results.values())`; `train_win.py:230` reports it as
`A_px`. Evidence written to `episodes.jsonl` and to the run logs does not say which direction
produced it, so a D-only response reads as a two-direction pass in every later analysis.
Fix: log `gate_dir` verbatim; store `gate_px` only as `min(D, A)`.

**A17. `_opponent_moves` proves motion, not an opponent playing.** `train_state.py:962-985`:
8-15 px of x-span over 5-10 s on the named object. A demo AI, a knockback or a camera-less walk
cycle passes it. It is used as an acceptance condition inside `_drivable_now` (`:1107, 1123`) and
in attest step 6.
Fix: require the opponent to change *sign of approach* (close then retreat) at least once, and to
be within stroke range of us at some point; require the same from the bound-pair reader.

---

## B. Ways it reports failure on a genuine match

**B1. `in_arena` refuses to gate outside rooms 26..77.** `train_state.py:466-470, 900-902`.
rTutorial (21), rForceStartLevel (5), rPreMatch (25) and any round transition that briefly reports
a menu room make both `prove_control` and `bind_by_response` return early without pressing a key.
Fix: gate on "not a menu room and a match object exists", not on an arena whitelist; the room file
should be advisory.

**B2. The A measurement is taken against the pre-D position, so a wall-pinned fighter fails.**
`train_state.py:508-519`: `x0` is read before the D hold; if D moved us 0 -> 40, the A window
reads 40 -> 5 and scores `(5-0)*-1 = -5`, below `min_px`, even though A worked. Same shape as the
documented "A_px=8.0 (FAIL)" episode.
Fix: score each direction from the position at the start of its own hold, or score the
peak-to-trough reversal.

**B3. Both directions are mandatory, so a fighter against a wall fails.** `train_state.py:523`.
Fix: accept `max(D, A) > min_px` plus a reversal (the fighter moved back when the key reversed).

**B4. Momentum kills the A window.** `train_state.py:924-930`: `hold_key` sleeps 0.2 s after
key-up and `mid` is one frame. Our fighter is still decelerating rightward, so `dx_a` is positive
for an instant and the candidate is discarded.
Fix: settle for a fixed frame count (published `f=` counter) and take `mid` as the last of 3
samples.

**B5. Instance identity must survive three snapshots.** `train_state.py:942`: set intersection of
`before/mid/after`. Ids churn at round start, the hook caps at 600 instances per dump, and the
window is 1.5 s wide. One missing id and the real fighter is not a candidate.
Fix: match by (id, object index) with a tolerance of one missing snapshot; allow up to 3 attempts
with a shorter hold (0.6 s).

**B6. `_drivable_now` requires the CPU to move 8 px in 10 s.** `train_state.py:1107`. On an
initial easy difficulty, a round-over screen or a paused frame counter this fails on a genuine
match, and the caller then discards the episode or re-enters.
Fix: use the round-state (room/rMatchStats) to tell "between rounds" from "CPU asleep", and only
apply the CPU term after a round has started.

**B7. Fixed 2.5 s menu waits against a stale speed file.** `attest.py:74-77` and
`train_state.py:122` (clean_files does not remove `SPEED`). On this build the game runs 24 fps at
`speed` default and ~226 fps at 600 — the repo already measured that entry "overshoots" when speed
was raised (`_raise_speed` docstring, `:633-646`). A left-over `nid_speed_0.txt` = 600 from a prior
training run makes attest's open-loop sequence land on the wrong screens.
Fix: delete the speed file on launch and write the calibrated value before navigating.

**B8. Key delivery is a file write racing a frame loop that caps at 32 pending keys.**
`hook/inject.m:274-299`: each frame truncates the file and stops accepting after `pending_n == 32`,
silently dropping the rest; hold length is 12 frames (`hook/inject.m:301`), i.e. 53 ms at 226 fps.
`prove_control` writes every 40 ms (`:512`) and can lose samples or keys.
Fix: hold a key for a frame count obtained from the hook, and have the hook publish a key-accept
counter the reader can assert against.

**B9. `has_players` requires the named opponent too.** `train_state.py:431-434`: both `me_x` and
`them_x` must be valid, but the repo's own measurement says object 154's coordinates/flag vanish
and reappear. Used at `:481` (gate), `:1079` (`_drivable_now`), `:1211` (`wait_for_match`),
`:1250` (`ensure_match`), so a genuine match with a flickering opponent reads as "no match".
Fix: require only the bound fighter's validity inside a match, in the gate and in
`ensure_match`.

**B10. `_press_verified` returns True when it cannot take a screenshot.** `train_state.py:596-604`:
`if before is None or after is None: return True`. With screen recording permission lost or the
window parked, every menu step "succeeds" and the sequence runs blind and the failure surfaces
later as a gate failure, not as a capture failure.
Fix: return None/"unverified" and fail the entry loudly.

**B11. `launch()` pkills every Nidhogg process, so a pool kills itself.**
`train_state.py:200` inside `launch`, called per instance in `train_win.main` (`for m in mgrs:
m.launch()`) and in `reset_all` (`train_win.py:60-62`). Each launch kills the games started a
moment earlier, so with `--instances 4` at most the last instance has a game; the others report
dead process, restart, and trigger sweeps. Also `_alive_bundle`/`close` pgrep for
`Nidhogg<iid>.app` while `instance_app` returns the same `Nidhogg.app` for every iid
(`train_state.py:33-40`), so those patterns never match.
Fix: one `pkill` before the pool launch, never inside it; drop the iid suffix from the pgrep
patterns or restore per-instance bundles.

**B12. Generation-level retry re-scores only the missing individual, on an arbitrary instance.**
`train_win.py:909-914`: `reset_all` then `play(mgrs[i % len(mgrs)], ...)` with a different seed
(`gen*997+i`, no rep suffix) from the original reps (`gen*997+i*7+rep`). The retry is therefore a
different experiment from the other individuals' episodes, and it is what gets selected.
Fix: reuse the same seeds and the instance that was assigned to `i`.

---

## C. Selection leak that survives today

**C1. Mean over valid reps only.** `train_win.py:872-877`: `valid = [r for r in runs if not
no_match]`, `fitness = mean(valid)`. A policy that only produces a scorable episode when the fight
is easy keeps that episode's score; a policy that is scorable twice gets its average. The flaky
policy is systematically rewarded and its extra variance is invisible.
Fix: include every rep with `-100` for invalid, or require all reps valid for the mean and mark
the individual `no_match` otherwise.

**C2. Validity is motion-only and can be satisfied by the demo.** `train_win.py:653-689`:
`inert_opponent` (>15 px), `frozen_agent` (>15 px), `main_screen` (x>1200 on `st0`). With A8
(binding) `main_screen` cannot fire; the two motion terms are exactly what the historical
"attract demo passed the gate" false positive satisfied.
Fix: `no_match` must include `not episode_gate_passed and not episode_bind_ok`, recorded from a
gate run *inside* the episode, plus a room/attract-room assertion sampled during play.

---

## D. Minimum repair to make the chain mean something

1. Bind must require a control contrast (no-key window) and a signed reversal within one hold,
   repeated 6 times, on an instance with a player object index (A1, A2, A13).
2. Every state read comes from `(instance id, object index)` verified together, with a 1 s mtime
   limit, and the episode is invalid if the pair does not resolve (A8, A9, A12).
3. Room is checked before and during play, with the attract room excluded and the menu path
   required, never as "not room 2" (A5, A6).
4. The gate runs inside the episode and its failure disqualifies the episode (A14, A15).
5. `screen_kind` and the arena x-range test use the named state and the room, never the bound
   instance (A7, A8, C2).
