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
