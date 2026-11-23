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
