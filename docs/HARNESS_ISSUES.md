# Harness issues and fixes (Linux line)

Kept current with the PR. Each entry: symptom, cause, fix, and the evidence. Numbers come from the runs named in the entry.

## 1. Match entry returns False although a match starts
- **Symptom:** enter_match_v2 returns False; in_match turns True 4-20 s later.
- **Cause:** the check read in_match 3 s after Return, before the match appeared.
- **Fix:** restart path polls in_match for up to 30 s (wait_live). Cold launches on pippi: 4/10 live before, 10/10 after.

## 2. Drive check misses slow fighter moves
- **Symptom:** a live match is reported as not live; one fighter moved 9 px in a 0.4 s walk press.
- **Cause:** the 0.4 s press was too short on the slower machine.
- **Fix:** walk press lengthened to 0.8 s; the 15 px threshold is unchanged.

## 3. Stand-still policy (the main learning failure)
- **Symptom:** after generation 5, the trained policy stops walking; win rate against the frozen checkpoint rises to 0.85-0.93 with no real improvement.
- **Cause:** the reward gave a very small cost for not moving (-0.05), and the opponent walks onto a still sword, so standing still wins.
- **Fix:** not-walking penalty raised to -1.0 per episode; half the training pairs play the frozen checkpoint; evaluation counts an episode only if the trained policy walked (5+ steps).

## 4. Action sampling collapse
- **Symptom:** all fighters pick the same action for a whole episode; nothing moves.
- **Cause:** training used argmax over the network's outputs, and every episode starts from the same spot.
- **Fix:** training samples actions from the softmax of the outputs (seeded per episode); evaluation stays greedy.

## 5. Timeouts produced by the death check (44% of episodes)
- **Symptom:** episodes end undecided after about 600 ticks although a kill happened.
- **Cause:** the death check fired on idle fighters, then released keys and waited 6 s per episode.
- **Fix:** the death confirmation runs only when the frozen fighter is in a death animation (297, 245, 311, 323-327). Undecided after a false freeze: 17% to 4% over 100 episodes.
- **Open:** death-animation kills went 69 to 66 per 100 on the same seeds; within noise, not yet settled by a 400-episode test.

## 6. Reset writes into freed memory and the game crashes (status-5 exits)
- **Symptom:** the game process exits by itself with launcher status 5, mostly right after a draw (both fighters killed); a fault address in the Wine log reads through an empty pointer.
- **Cause (leading, two cases):** the reset writes x/y to a master record that points at a sword instance destroyed by the double death.
- **Fix:** before each reset write, check the master's id is non-zero and its object is 155 or 244; otherwise look it up again (up to 3 times) and skip the write if none is live.
- **Evidence:** status-5 exits per run went from 2 (before the guard) to 0 in 400 guarded episodes. Weak evidence (two cases against zero) until repeated.

## 7. Reset failures under load
- **Symptom:** resets fail "reset failed 5 times", "no record answers to P1's keys", and "no live master" (1-2 per 50 episodes per instance).
- **Causes and fixes:**
  - Unarmed fighter (animation 366) rejected: 366 added to the idle set. Before: 2/3 resets; after: 3/3.
  - Fighters on different floors: y written with x. Effect not fully proven.
  - Ledge hang (animation 580/659): drop key tapped and both placed again; a failed preferred spot is not reused. Single-instance failed resets: 4/50 to 0/50.
  - Short state read in place(): reads again up to 6 times, then a counted error instead of a crash.
- **Open:** a rare fighter with no living record (about 1 in 100 episodes): logged, not fixed.

## 8. Game exits that are not ours
- **Symptom:** a game exits on its own (status 5) about 1 in 100-150 instance-episodes.
- **Cause:** not yet known; most exits follow double kills (see 6).
- **Fix:** the runner survives the exit (aborted episode and one restart); launcher exit records keep the code, signal, last memory writes and the Wine fault line.

## 9. Machine load and cap
- **Symptom:** artemis load reached 3,500-4,000 on 384 cores (other users' processes); games could not enter a match at that load.
- **Fix:** load gate (wait while 1-minute load is above 150) on artemis; the runs moved to pippi, capped at 32 cores and 64 GB per the cap agreed with Ruggero.

## 10. Process hygiene
- **Symptom:** orphaned games and wine processes left by earlier attempts.
- **Fix:** every kill is by verified pid (owner uid and farm path in the process environment); no pkill or name-based kills. Stopped 492 orphans on artemis in one scoped pass.

## Open items
- Learning: no trend against the frozen checkpoint yet across four runs (win rate stays near 0.5 with overlapping intervals). Current run is the first with the death-check fix and the new learning settings.
- Reward design: the walking penalty may still need tuning if the new run stops moving again.
- Acceptance: 400-episode test for death-animation kills is still pending.
- Maintenance: the working code is spread over several server folders; it needs one clean branch and reviewable commits.

## 11. Reset bugs found by reviewing recorded episodes (2026-11-23, debug copy)
Method: each viewer episode is recorded with video and a reset phase trace (wall time, tick, object index, x, y, animation for both fighters). Every event is then explained from video and logs before the next episode is run.

- **Reset visible as a teleport:** the reset always writes P1 left and P2 right, so when fighters finish on swapped sides, the next reset moves them back across each other. The reset works as coded. Open decision: keep the sides as they ended, or always restore fixed sides.
- **Bug A, fighter record in hang animation 580/659 during the reset:** 18 of 65 resets (1 in 4), in the first hour with fixes 1-3. Mostly not a fighter hanging on a ledge: the game frees a record and reuses its address for another object while the reset still reads it. Of 73 trace points with animation 580/659, 5 were a real body (object 74); the rest were objects 154 (18), 243 (18), 244 (4), or no record (28).
- **Bug B, fighter dies during the reset:** 11 of 65. Nine of these were deaths during probe writes, i.e. a test spot put a fighter within the other's blade reach.
- **Bug C, stale death:** 1 of 65. Same cause as A: a respawn record at an address seen in an earlier episode.
- **Fix 1 (accept a respawn only if object 74):** 0 rejections in 65 episodes. It never fired.
- **Fix 2 (a death during a probe ends the probe):** fired 9 times. It moves the reset on after the death but does not prevent it.
- **Fix 3 (confirm a death that started before the time limit):** fired once; it turned an undecided episode into a P1 win.
- **Earlier 0-of-5 result was luck:** rows 71-75 had no bug events, but none of the fixes fired in them, so they don't show the fixes work.

Status: the debug-copy code is not yet committed to this branch. Next round in the debug copy: re-check each tracked record's object index after every write, keep probe spots out of blade reach, and compare records by instance id instead of address. Not yet validated.

## 12. Training worker crash on a failed memory read (es4, 2026-11-23)
- **Symptom:** the farm2 worker exited at 16:12:45Z in generation 6.
- **Cause:** a game-memory read returned nothing. The observation code (nidobs.py line 126) unpacks it without a check, which raises a TypeError. The episode error handler catches only assertion, runtime, value and OS errors, so the TypeError ended the worker process.
- **Handling:** the worker was relaunched within the cap; the coordinator re-queued the episode it was playing. No training data lost.
- **Open:** adding TypeError to the episode-level handler is a one-line fix. Not applied to the running training, to keep generations comparable.

## Training progress (es4, fixed reference, decided episodes only)
- Generation 0: 15 of 40 (0.375, Wilson 0.24-0.53).
- Generation 5: 21 of 40 (0.525, Wilson 0.375-0.671). As P1 12/20, as P2 9/20.
- Intervals still overlap; no clear improvement yet. About 25-29 minutes per generation.

## 13. Reset debugging, hours 3-4 (debug copy; es4 unchanged)
Counts per reset, from reset traces logged by the viewer game (rows 214-409, 195 resets, 2026-11-23 17:15-19:16Z).

| Bug | Hour 3 (99 resets) | Hour 4 (96 resets) |
|---|---|---|
| A: tracked record changes object during reset (caught before write) | 33 | 40 |
| B: body dies during reset | 3 | 3 |
| C: stale death | 3 | 0 |

- **Fix A2** (drop and re-identify a record whose object changed before writing): caught 27 rows in hour 3 and 34 in hour 4. Works as coded. Cause not fixed: the game reuses a fighter's record address for another object while the reset reads it.
- **Read-back threshold after place():** 3 px was too strict (stopped 13 probes, mostly standing bodies 4-8 px off). 10 px (hour 4): 14 rows, 18 stops, all real off-spot bodies (one 396.7 px).
- **Stale-death address rule:** the "respawn present at an earlier start" reason voided two real kills in hour 4 (rows 374, 408). Dropped. Now 0.
- **Room check** (refuse probe spots outside the start room): untested, no reset left the room in hour 4.
- **Death during a probe** (fix 2): 0 in hours 3-4.
- **Failed resets** ("reset failed 5 times", "no record answers to P1's keys") still restart the game: 2 in hour 4, 11 in hour 3.

## 14. Early stop and episode length (debug copy findings)
- **Early-stop bug (episode 13, 2026-11-23 16:21Z):** P2 died to a real kill (death animation 327) while P1 stood idle. Both then froze, and the freeze check needs exactly one frozen fighter, so the death check never ran. The "both frozen 90 ticks" early stop ended the episode as undecided, scoring 0/0 for a real kill. The same rule is in es4's code. Proposed fix (debug copy first): when both are frozen and one is in a death animation, run the death check on that one. Not yet tested.
- **Episode length** (265 viewer episodes with per-step traces, from 13:52Z; see review/episode_length.md on pippi):
  - Play itself never exceeds 605 ticks. The 600-tick cap applies to play; end-of-episode checks add the rest.
  - 41 episodes ran long through the kill path: corpse frozen 30 ticks, then the death check waits up to 360 ticks for respawn, then the 1.5 s double-kill check.
  - 10 episodes had a false freeze whose death check waited about 430 ticks inside the cap, cutting play to 174-554 ticks.
  - After a kill, play continues: median 15 steps (6.7 s) before the episode ends. The respawned fighter never plays in that episode. The next reset therefore starts about 7 s after the kill.
  - No reset started before the previous episode row was written.
  - 11 resets produced no episode row (failed reset, then game restart, then a fresh reset). On screen this looks like a double reset with a black screen of about 2 minutes.

## Training (es4, fixed reference, decided episodes only)
- Generation 10 (2026-11-23 17:49Z): P1 10/20 (0.50, Wilson 0.30-0.70), walked 28 vs 28 frozen; P2 10/20 (0.50), walked 30 vs 26 frozen.
- Generations 0, 5, 10: 0.375, 0.525, 0.50 pooled. Intervals overlap; no clear improvement yet.
- Generation 10 took 2,698 s against about 1,300-1,900 s before. Training stalled with 0 games for a period on 2026-11-23 around 19:23Z (load 89), then resumed at 12 games by 19:35Z.
- Farm2 worker crashed at 16:12:45Z on an unchecked memory read (TypeError in nidobs.py line 126; the episode handler does not catch TypeError). Worker relaunched; one-line fix proposed, not applied to es4.

## Open
- Decision needed from Ruggero: reset sides (keep as ended, or always restore fixed P1-left/P2-right). This is the visible "teleport".
- Decision needed: a kill that also gets the walking penalty scores 0 (for example, row 53: kill +1, walk -1). Affects training signal.
- Debug-copy fix code is not on this branch. It will be committed only after a round validates it.

## 15. Decisions taken by the Fable oracle (2026-11-23, applied in the debug copy first)
Per the user's instruction, Fable makes the decisions until the goal (controllable, reliable, robust training episodes) is met.
1. Reset sides: randomised per episode, with mirrored start spots; the side is logged; evaluation is balanced 50/50 by side. Reason: a side advantage must not be learned as skill.
2. Reward: a kill always scores +1; the walking penalty applies only to episodes without a kill, at -0.25. Reason: the current rule scores a real kill as 0 when the killer also gets the penalty.
3. Validity: a decided kill is never discarded because the victim moved under 40 px. The 5-step and 40 px test applies per fighter, to cap episodes only; v3 is kept as a reported statistic. Reason: the current rule throws away the killer's learning signal.
Status: not yet tested. Pending: trace checker run and two control matches (trained vs idle; same policy vs itself), each reported with n.
