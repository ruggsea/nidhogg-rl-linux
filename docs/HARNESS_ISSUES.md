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

## 16. Viewer outage from a trace patch (2026-11-23, our mistake)
- **What broke:** a per-tick trace patch applied about 19:52 UTC left part of Env.__init__ inside a new method. Every Env then lacked home_y, so the viewer's reset crashed.
- **Effect:** the viewer's restart loop relaunched its game 81 times between 19:51 and 23:34 UTC and played 0 episodes. The VNC showed launches and black screens for about 3 h 40 min.
- **Not affected:** es4 uses ~/nf-p/code, not the debug copy.
- **Fix:** 23:34 UTC, the init lines restored into __init__ (checked with the AST). The viewer recovered by its own restart; episodes resumed at 23:36 UTC.
- **Process change:** each status report now first checks the viewer's last episode row time, not only the hourly counts.

## 17. Full per-tick traces (debug copy)
- **Debug launches:** 23:22 UTC (boot retry worked; the game was lost between match entry and the first episode, then hit the same home_y bug); 23:34 UTC (match at 23:37, first try). The 23:34 launch broke the one-launch-per-hour rule on purpose, after the fix.
- **First trace:** ~/nf-p/viz85/trace/20261123T233713-3494928_ep0000.jsonl.gz, 5.6 KB, episode 0: current policy as P1, P2 won.
- **Pending:** 20-episode trace cycle with trace_check results by episode number; controls (40 trained vs idle, 40 frozen vs frozen), each with n and side split; total trace size.
- **Status:** the Fable decisions (random reset sides, kill always +1, walking penalty -0.25 only without a kill, 40 px test on cap episodes only) are applied in the debug copy only. Nothing from them is validated yet.

## 18. Trace cycle 1 and control matches (debug farm, es4 generation 20, Fable rules)
Raw file: ~/nf-p/dbg86/ctrl.jsonl on pippi, 100 rows; totals checked against the agent's table (P1 16, P2 28, undecided 56).

Trace cycle 1 (20 episodes): 3 with unexplained events (episodes 1 and 11: a tracked body record freed mid-play, fix in debug copy for cycle 2; episode 12: game exit with code 1 during a reset, cause not found). Best clean run 9; current 7 at cycle end.
Checker rules were relaxed during the run (writes counted as pokes, 6-tick settle, reset phases excluded from jump checks). Re-checked on all 20 files: 0 play-tick jumps over 30 px without a write within 6 ticks, out of 25,982 ticks.

Controls (first policy's wins among decided episodes, Wilson 95%):
- A, current vs frozen (n=20): 7/14 = 0.50 [0.27, 0.73]. Agrees with es4's evaluations: no measurable gain.
- B, current vs idle, always action 0 (n=40): 1/7 decided = 0.14 [0.03, 0.51]; 33 undecided. The policy does not learn to attack a standing opponent.
- C, frozen vs frozen (n=40): 10/23 = 0.43 [0.26, 0.63]; P1 won 7/23 = 0.30 [0.16, 0.51]. The 0.5 check holds; the seat split is too small to call bias.

Conclusion: no learning signal yet. The training design is the open question.

## 19. Trace cycle 2 (run 20261124T004755, 20 episodes, es4 generation 20-23)
Raw check, read from pippi trace files: episodes 4, 8 and 9 each contain one restart, exit or no-record line (game hung or exited in 4 and 8; no record answered P1's keys in 9). Episodes 10-19 contain none.
- Episode 5 (outcome P1, 1056 ticks, valid_v3 False): the end record shows P2 dead on the corpse branch (freeze tick 8360, no respawn). P1's tracked record changed from object 74 to 243 at tick 8119 while P2 was dying. Not yet explained: could be P1 dying, or a reused record. The video (dbg86_ep5.mp4) is needed to settle it.
- Streak: 10 episodes (10-19) with no unexplained events by the checker's rules. The checker rules were relaxed in cycle 1; treat the streak as provisional until the restarts in 4, 8 and 9 are explained.
- Open: game hang or exit in 4 and 8; missing key answer in 9; episode 5's object change. Cycle 3 adds an object-change check in play.

## 20. Cycle 2 restarts: raw trace lines (episodes 4, 8, 9)
- **Episodes 4 and 8:** the last play-phase rows show P2 at x 0, y 0, animation 0 (record zeroed) during the P1 end check (tick 3950 and 5098). The restart reason logged is "state file stopped updating (game hung or exited)". Cause: P2's record was freed, and the spy's state file stopped updating in the same window. Not yet proven which came first.
- **Episode 9:** restart reason "no record answers to P1's keys". P1's last record (object 445) was live at tick 3617; the re-identification found nothing. The respawn walk for P2 ran but P1's keys still went unanswered.
- These restarts are not yet linked to the object-reuse problem seen in episodes 4 and 5; treat that link as a hypothesis.

## 21. es4 fixed-reference evals, updated from the raw file (2026-11-24 01:23 UTC)
Read from ~/nf-p/es4/evals.jsonl on pippi (decided episodes only, Wilson 95%):
- Generation 0: 6/20 (0.30) P1; 9/20 (0.45) P2.
- Generation 5: P1 12/20 (0.60, 0.39-0.78), walked 30 vs 27 frozen; P2 9/20 (0.45).
- Generation 10: P1 10/20 (0.50, 0.30-0.70), walked 28 vs 28; P2 10/20 (0.50).
- Generation 15: P1 12/20 (0.60, 0.39-0.78), walked 38 vs 32; P2 12/20 (0.60, 0.39-0.78), walked 31 vs 32.
- Generation 20: P1 9/20 (0.45, 0.26-0.66), walked 39 vs 36; P2 9/20 (0.45), walked 34 vs 36.
- Latest generation at this read: 22. Run not ended. 18 games running, load 53.
Pattern: every eval sits near 0.5 and the intervals overlap. No measurable gain over the frozen checkpoint.

## 22. The four game hangs: raw comparison (2026-11-24)
Compared the last rows before each hang in the trace files (cycle 1 ep 12; cycle 2 ep 4 and ep 8; cycle 3 ep 8):
- In all four, P2's record reads (0, 0, 0, 0) on the last tick, during an end check (end_check_P1 in three, end_check_P2 in one).
- In all four, the other fighter (P1) is either in a death animation (297, 311) or a hang animation (580) at that moment.
- In all four, the episode records the outcome P2 or an abort, and the next line is the restart.
- Last key sends before the hang are key-up lines only ("ku ..."), no new key press.
Reading: the game frees P2's record during P1's death check, and the spy stops publishing state in the same window. Cause order is not yet proven. Cycle 4 logs the game's last state at each hang to test it.

## 23. Correction to section 22 (cycle 3, episode 8, tick by tick)
- P2's record first reads (0, 0) at tick 17182. The game then stops publishing state at tick 18182, a thousand ticks later. P1 stays frozen in death animation 297 at x 1127.2 for the whole window.
- So the hang does not start when P2's record is freed. Something earlier stalls the game, and P2's record going to zero is a symptom in the same window.
- Section 22's reading ("the game frees P2's record during P1's death check, and the state stops") is wrong for this episode. Cycle 4 must log from the start of the death check, not only the last rows.

## 24. Lead: the hang may start at a reset (cycle 3, episode 8)
- A reset_start phase and the first attempt_start both fire at tick 17161. P2's record reads (0, 0) from tick 17182 onward, and the game stops publishing state at tick 18182.
- P1 walks normally during that window (x 1092 to 1090), so the stall is on P2's side, from the reset.
- Lead only, from one episode. Cycle 4 must log the reset's first writes for both fighters to confirm or reject it.

## 25. Hang count and correction (agent report, review/hangs.md on pippi)
Corrects sections 22-24. Five game hangs or exits in 60 traced episodes, not four (cycle 2 episode 9 also exited).
- Cycle 1 ep 12: re-identifying P2 after the episode; P2 (0,0) vanished.
- Cycle 2 ep 4: stepped approach inside the reset; the only hang in a reset. P2 at 1219.6, not vanished.
- Cycle 2 ep 8: re-identifying after the episode; P2 (0,0) vanished.
- Cycle 2 ep 9: exit; P1's keys not answered first.
- Cycle 3 ep 8: death check on P2; P1 in death animation 297; P2 (0,0) vanished.
Across 13 exits with return code 1 since 23:34Z: P2's record read (0,0) in 7 of 8 exits with a recorded state. The reset lead in section 24 covers one of five, so it is not the cause. The relaunch after each exit died again within about 3 minutes (5 of 5); the second relaunch worked.
Open: why P2's record disappears before the exit. Hypothesis (unproven): a short gap between the master-record check and the write.
Cycle 4 started 01:28:46Z (debug farm). Logs per launch: launchwatch last state, room index per sample, per-episode videos at 2 fps.

## 26. Verified from the raw launcher log (2026-11-24 01:4x UTC)
Read from ~/nf-p/dbg86/launcher_exits.jsonl on pippi:
- Game exits with return code 1 since 23:34 UTC: 13.
- Of those, 8 have a recorded last state; in 7 of the 8, P2 reads (0, 0).
- Example last state (2026-11-23 ~23:43 exit): tick 26112, P1 (1888, 160, anim 174), P2 (0, 0, anim 0), room 29.
- Room index is 29 in every recorded last state: no room change registered before an exit.

## 27. Trace cycle 4 (run 20261124T013102, 2026-11-24 01:31-01:40 UTC)
- 20 of 20 episodes: no unexplained event, no game hang, no code-1 exit. Streak 20.
- The only game exit is the runner's own stop at 01:40:12 (return code -15).
- Outcomes: P2 11, P1 4, undecided 5; episodes 496-1116 ticks.
- Hangs per 20 episodes: cycle 1: 1; cycle 2: 3; cycle 3: 1; cycle 4: 0. Total 5 in 80.
- Not a fix. Cycle 4 changed only the room-index logging. At the earlier rate (5 in 60), a hang-free 20-episode run happens by chance about one time in five.
- Plan: 20-episode cycles on the debug farm until a hang recurs or three clean cycles in a row.

## 28. Cycle 4 outcome counts, corrected from the raw trace files
Recount of the 20 cycle 4 files (run 20261124T013102): P1 4, P2 10, undecided 6 (the agent's report said P2 11, undecided 5). Tick range 496-1116 confirmed.

## 29. Trace cycle 5 (run 20261124T014409, 01:44-01:52 UTC) and the death-list fix
- No game hang, no code-1 exit. One unexplained episode: episode 7. P2 was in death animations 327, 323 and then 243 (from tick 16920); the episode ended at the 600-tick cap at 16925 as undecided, with P2 penalised for walking.
- Cause: the death check only accepts animations in its death list, and 243 was not in it.
- Fix (debug copy): 243 and 247 added to the death animations. This also changes the in-play death check, so it affects training labels. Checked by the agent: in 20 episodes where 243 appears, every case falls within 60 ticks after a listed death animation (36 of 36 occurrences).
- Hang rate, 100 traced episodes: 4/100 by the trace rule (Wilson 95% 0.016-0.098); 5/100 counting code-1 exits (0.022-0.112).
- Streak: 12 (episodes 8-19 of cycle 5). Reset from 20.
- Next: cycle 6 with the widened death list.

## 30. Trace cycle 6 (run 20261124T015656, 01:56-02:07 UTC), death list widened
- 20 of 20 episodes clean: no unexplained event, no game hang, no code-1 exit. Streak 20 (first of three clean cycles in a row).
- Hangs over 120 traced episodes: trace rule 4/120 (Wilson 95% 0.013-0.083); code-1 exits 5/120 (0.018-0.094).
- No hangs in cycles 4-6 (60 episodes). The hang code has not changed, so this is not a fix; the interval still allows about 1 in 12 episodes.
- Next: cycle 7 (started 02:07 UTC).

## 31. es4 worker crash (second) and the decision on the episode catch
- 02:06:01 UTC: the farm2 worker crashed on the same TypeError as at 16:12 (memory read returned nothing; nidobs.py line 126). Episode eval_g25_P1_022 re-queued; no data lost. Relaunched 02:09:28 as nfp-es4-farm2b, same limits (cores 8-15, 16 GB).
- Two crashes from this bug in about 13 hours.
- Decision (Fable, under the user's delegation): apply the one-line episode-level catch of TypeError to es4 at the next generation boundary. Only the crashing episode aborts; nothing else changes.
- es4 fixed-reference evals (wins among decided, current vs frozen): gen 0 15/40 (0.375, 0.242-0.530); gen 5 21/40 (0.525, 0.375-0.671); gen 10 20/40 (0.50, 0.352-0.648); gen 15 24/40 (0.60, 0.446-0.737); gen 20 18/40 (0.45, 0.307-0.602). All intervals overlap: no trend yet.

## 32. The es4 TypeError handler, checked in the code (2026-11-24)
- The handler the change goes into (train/selfplay_env.py, step(), around line 153) is episode-level: its except branch calls _sp_abort, which ends the current episode as aborted. Adding TypeError there aborts only the crashing episode.
- Still required before it lands: the full traceback of every caught TypeError is written to the es4 log, and more than 3 TypeError aborts in one generation is reported before the next generation.
- Not yet applied to es4 at the time of this entry.

## 33. The es4 TypeError change, as specified (lands after the generation-25 line; applies from generation 26)
- Handler: train/selfplay_env.py step(), line 153 (episode-level). Line 153 adds TypeError to the except list; a new line 154 writes the UTC timestamp and full traceback to ~/nf-p/es4/typeerror_tracebacks.log for TypeError only; line 155 is unchanged.
- Effect: a TypeError aborts only the crashing episode (logged aborted, both rewards 0, valid False). More than 5 aborts in a row stops the worker.
- Diff: 1 line changed, 1 added (tested on a temporary copy; compiles). Original kept as selfplay_env.py.pre_typeerror.
- Landing: workers restarted one at a time under the cap (8 cores, 16 GB each). Nothing else in es4 changes.
- Watch: more than 3 TypeError aborts in one generation is reported before the next generation.

## 34. Trace cycle 7 (run 20261124T021118, 02:11-02:22 UTC)
- 20 of 20 episodes clean, no game hang, no code-1 exit. Streak 20 (second of three clean cycles in a row).
- Hangs over 140 traced episodes: trace rule 4/140 (Wilson 95% 0.011-0.071); code-1 exits 5/140 (0.015-0.081).
- No hangs in cycles 4-7 (80 episodes). Not a fix: the hang code has not changed.
- The es4 TypeError change is still armed for the generation-25 boundary.

## 35. Streak correction (2026-11-24)
- Rule (Ruggero's): any restart resets the streak, including a boot retry.
- Cycle 8 (run 20261124T023247) had a boot retry at 02:30:29 UTC before episode 0 (game did not come up within 400 s; retry booted; match live 02:32:43). Under the rule, cycle 8 is not clean.
- Clean cycles in a row: 2 (cycles 6 and 7). Current run from cycle 8: 0. Cycle 9 (started 02:44:01 UTC) is clean cycle 1 if no restart occurs.
- Boot failure logs found on pippi: ~/nf-p/dbg86/run.fail1.log, run.fail2.log, logs/py_0.fail2.log, logs/py_0.fail4.log. Not yet matched to the 02:30 timestamp.
- Hang rate over 160 traced episodes: trace rule 4/160 (Wilson 95% 0.010-0.063); code-1 exits 5/160 (0.013-0.071). Hang code unchanged; not a fix.

## 36. es4 TypeError change is live (generation 26)
- Applied 02:49:47 UTC, after generation 25 finished at 02:49:42. Diff checked on pippi: line 153 adds TypeError to the episode-level catch; line 154 writes each TypeError traceback to ~/nf-p/es4/typeerror_tracebacks.log. Compiles. Original kept as selfplay_env.py.pre_typeerror.
- Workers restarted one at a time (farm1 02:52, farm2 02:55, farm3 02:58, farm4 03:01 UTC), same 8 cores and 16 GB each; all ready by 03:01 UTC.
- TypeError aborts in generation 26 so far: 0 (no traceback log yet at 02:44 check on pippi, read before workers were restarted).
- Watch: more than 3 per generation is reported before the next generation.

## 37. Cycle 9 game exit (raw, 2026-11-24)
- Run 20261124T024622: 20 trace files written. Launcher log (~/nf-p/dbg86/launcher_exits.jsonl): game exit with return code 1 at 02:52:31 UTC; alive 503 s; game pid 400738.
- Last recorded state: tick 25096, P1 (1158, 192, anim 463), P2 (909, 173, anim 580), room 29.
- Under the restart rule this breaks cycle 9's clean streak. Episode and trace of the last ticks requested from the pippi agent; no debug-farm relaunch until it reports.
- Hang rate so far: 5 code-1 exits in 160+ traced episodes (see section 35); this is one more if it is counted at the agent's report.

## 38. Cycle 9 exit reclassified (pippi agent, raw checked)
- The 02:52:31 UTC code-1 exit (run 20261124T024622) is not a game hang. It came after a reset failed five times in episode 5 (seed 90005; reset_failures.jsonl). The training env then restarted the game, and its stop sent SIGTERM to the launcher and to Nidhogg.exe, so the launcher returned 1.
- Cause in the reset: attempts 1-4 re-identified P2 through the "unstuck" path, each time returning a non-body record (object 243, new instance each attempt); each search took about 49 s.
- Hang classification unchanged: 4 real hangs (cycle 1 ep 12; cycle 2 ep 4 and ep 8; cycle 3 ep 8). Cycle 2 ep 9 exit was also our restart after a reset failure, not a hang.
- New failure class: reset failures with restart (cycle 9 episode 5 is the first in this run; 1 in about 180 traced episodes).
- Debug-copy fix approved (no retry of the same unstuck path after a failed search; wait for respawn). Cycle 10 to start once the fix is in.

## 39. Cycle 9 result and the reset-retry fix (pippi agent; exit timing checked)
- The 02:52:31 UTC exit is the first game of run 20261124T024622 (pid 400738), stopped by our restart after the reset before episode 5 failed five times. Episode 16 was played in the second game; no exit there (the second game was stopped at 03:02:36 by the run's end, rc -15).
- Cycle 9: 20 episodes, 0 boot retries, 1 reset-failure restart (episode 5), 0 real hangs. Streak broken at episode 5; 14 clean after it.
- Hang rate over 180 traced episodes: 4/180 = 0.022 (Wilson 95% 0.009-0.056).
- Fix in the debug copy (nidmem.py): identify() and unstick() accept a record only if its live object index is 74. Non-body records are skipped and counted (guard "skip_not_body"). No address blacklist (the game reuses addresses). File parses and imports.
- Cycle 10 started 03:05:13 UTC. Reset-failure restarts per cycle now printed by the cycle report.

## 40. Cycle 10 (run 20261124T030736, 03:07-03:17 UTC), checked from raw files
- 20 trace files; no restart or abort text; the only launcher exit is the run's own stop at 03:17:05 (rc -15). Boot retries 0, reset-failure restarts 0, code-1 exits 0. Clean under the restart rule: 1 of 3.
- Hang rate over 200 traced episodes: 4/200 = 0.020 (Wilson 95% 0.008-0.050).
- Process miss: cycle 10 launched at a 1-minute load of 164.6, above the 150 gate. The debug launcher had no load check; the farm restart path does. Fixed in the debug launcher (waits while 1-minute load is above 150, logs each wait).
- Context: load spike coincided with the es4 worker relaunches (02:49-03:01 UTC) and six debug games. Other users not checked.

## 41. es4 generation 25 evaluation, read from the raw file (2026-11-24 03:19 UTC)
- Generation 25 (01:59:59 UTC): P1 14/20 = 0.70 (Wilson 95% 0.48-0.86), walked 42 vs 42 frozen; P2 15/20 = 0.75 (0.53-0.89), walked 42 vs 43 frozen.
- Previous: generation 20 at 0.45 (both seats); generations 0-15 between 0.375 and 0.60.
- Read carefully: the highest point so far, but each seat has 20 counted episodes and the intervals still overlap the earlier ones. This is one evaluation, not a trend. Needs the next evaluations (generation 30) and a control check before any claim.
- Walk counts equal to the frozen checkpoint, so the win is not from standing still.

## 42. Load gate for the debug cycles, verified from the file (2026-11-24 03:28 UTC)
- cycle.sh calls run_ctrl.sh; run_ctrl.sh waits while the 1-minute load (from /proc/loadavg) is above 150, logging each wait (dbg86/run_ctrl.sh, line 6). Read from pippi.
- Cycle 11 (run 20261124T032016) in progress: 11 episodes written at 03:27 UTC, no restart or abort text so far.
- Still open: the cycle 8 boot retry at 02:30 UTC has no matching log on pippi (checked against the four boot-failure logs, all from 23 Nov).

## 43. Cycle 11 (run 20261124T032016, 03:20-03:30 UTC), checked from raw files
- 20 trace files; no restart or abort text; the only launcher exit is the run's own stop at 03:30:47 (rc -15). Boot retries 0, reset-failure restarts 0, code-1 exits 0. Clean under the restart rule: 2 of 3 (cycles 10 and 11).
- Hang rate over 220 traced episodes: 4/220 = 0.018 (Wilson 95% 0.007-0.046). No real hangs since cycle 3 (160 episodes). Hang code unchanged; not a fix.

## 44. Cycle 8 boot failure, confirmed from raw output
- ~/nf-p/dbg86/cycle8.out on pippi: "attempt 0: boot failed: full farm cleanup" at 02:30:29 UTC. This is the boot retry counted in section 35; it is no longer an open question.

## 45. Cycle 12 (run 20261124T033435): not clean (raw check, 2026-11-24 03:47 UTC)
- Episode 11: restart with reason "spy did not run the batch" (trace file 20261124T033435-961469_ep0011).
- Code-1 game exit at 03:38:20 UTC (launcher log, pid 961562, game pid 968445, alive 357 s). Last recorded state: tick 16386, game still responding (state age 0.1 s). Not the known hang signature.
- Cause of "spy did not run the batch": not yet confirmed.
- Effect: cycle 12 is not clean; the three-in-a-row count restarts after it.

## 46. Late-batch fix in the debug copy (checked 2026-11-24 03:48 UTC)
- Cause of cycle 12's restart: the in-game spy had not finished a command batch within 2 s; the code then failed the reset, the training env restarted the game, and the stop gave the code-1 exit. The game was still running and updating (state age 0.1 s): a slow spy, not a hang.
- Fix in debug copy nidmem.py (lines 72-76): if a batch is not done after 2 s, wait up to 8 s more without resending keys; each late batch is counted as spy_late with its wait time. Read from pippi: the 8 s wait and the counter are present; the file parses.
- Not yet validated: cycle 13 with the fix is pending; the count of spy_late events per cycle is the measure.
- Real hangs over 240 traced episodes: 4 (Wilson 95% 0.006-0.042), none since cycle 3.

## 47. Cycle 13 (run 20261124T034926, 03:49-04:01 UTC), checked from raw files
- 20 trace files; no restart or abort text; the only launcher exit is the run's own stop at 04:01:26 (rc -15). Boot retries 0, reset-failure restarts 0, code-1 exits 0.
- spy_late 0 in the run: no batch needed the extra 8 s wait. Clean under the restart rule: 1 of 3 (cycle 12 reset the count).
- Hang rate over 260 traced episodes: 4/260 = 0.015 (Wilson 95% 0.006-0.039). No real hang since cycle 3.

## 48. Cycle 14 (run 20261124T040553): real hang, fifth (checked from raw logs, 04:10 UTC)
- Launcher: code-1 exit at 04:10:56 UTC, alive 435 s. Reset log: episode 13, RuntimeError "state file stopped updating (game hung or exited)".
- Before the stop: P2's record read (0, 0) (vanished); P1's tracked record at (656, 192), animation 164, facing 9.5 (not a valid facing; not a body). Last key line "kd d".
- Pattern across all 5 real hangs: P2's record vanished shortly before. In 3 of 5 the code was writing positions or pressing keys during re-identification or approach. Consistent with our writes during a respawn, not proven.
- Streak: best 13 in cycle 14 (eps 0-12); clean since episode 14 (6 episodes). Clean cycles in a row: 0.
- Hang rate over 280 traced episodes: 5/280 = 0.018 (Wilson 95% 0.008-0.041). The cycle script printed 4/280 because the trace rule matched only the "state file stopped" reason logged; treat 5 as the count.
- Fix 1 (debug copy, nidenv): refuse any position write while a tracked fighter reads (0, 0) or a record is not a body; skip put-back ("write_refused", "put_back_skipped" counted).
- Fix 2 (debug copy, selfplay_env.reset): episode seed kept across reset retries. Found: episode 13 after a restart ran with seed 13 instead of 90013.
- Cycle 15 pending behind the load gate. es4 at generation 29, no TypeError aborts.

## 49. Cycle 15 in progress (run 20261124T042517; checked from raw files, 04:30 UTC)
- 5 trace files so far: no restart or abort text; write_refused 0; put_back_skipped 0; no launcher exits since 04:25 UTC.
- Pending: the rest of the run, the hang count, two clean cycles after it, and the generation 30 eval.

## 50. Cycle 15 hang (sixth), es4 finished, next decision (2026-11-24 ~04:50 UTC)
- Cycle 15 (run 20261124T042517): one real hang at episode 8 (state file stopped 04:31:08 UTC). P2 read (0,0) before the stop; P1 alive; the reset was in the probe phase sending only key presses. No position write was in progress, so the write guard (fix 1) could not stop it. Fix 1 never triggered (write_refused 0).
- Seed check: passes on every episode including the restarted episode 8 (fix 2 works).
- Hang count over 300 traced episodes: 6/300 = 0.020 (Wilson 95% 0.009-0.043). All six came with P2 vanished. cycle.sh printed 4/300 because it reads an old table; the 6/300 is from cycle_extra.py.
- Decision (Fable, under the user's delegation): debug copy only. When a tracked fighter reads (0,0) in a reset, wait without input (cap 5 s) before probing; count each wait as vanish_wait. Then cycles 16 onward behind the load gate, reporting the hang count after each.
- es4 finished at 04:44:36 UTC (30 generations). Counted wins (decided, current walked): gen 25 29/40 = 0.725 (0.572-0.839); gen 30 23/40 = 0.575 (0.422-0.715); earlier 0.375, 0.525, 0.50, 0.60, 0.45. No trend; intervals overlap. TypeError aborts 0 in generations 26-30.
- es4 check cron (1c3344cb) cancelled. The four idle es4 worker scopes (nfp-es4-farm1..4-g26) are left alone pending a decision.

## 51. Hang-count check: the signature search misses some hangs (2026-11-24)
- Recount of all 300 traced episodes for the text "state file stopped": 4 files (cycle 1 ep 12 is not among them; cycle 2 ep 4 and ep 8; cycle 3 ep 8; cycle 1 ep 2 matches the signature but is a different event per the earlier review).
- Not counted by the signature search: cycle 14 ep 13 and cycle 15 ep 8, both logged under a different restart reason.
- Use 6/300 (the count including restarts from cycle_extra.py), not 4/300 from the old table in cycle.sh.

## 52. Correction: the (0,0) readings are our tracking, not vanished fighters (pippi agent, 2026-11-24)
- identify-by-input (Mem.dx_on) tracks one body as P1 and leaves the P2 slot at 0, so P2 reads (0,0) by construction. The earlier "P2 vanished" reading was partly our own tracking artefact.
- Of 8 traced restarts with a P2 (0,0) reading, 6 happened during the find/identify phase while dx_on key presses were being sent (includes cycle 15 ep 8 and cycle 1 ep 12). Cycle 14 ep 13 is labelled approach but shows the same keys. Cycle 2 ep 4 was in approach with no zero reading.
- Vanish-wait (5 s, debug copy) is implemented as specified; expect few or no vanish_wait events and no drop in hangs.
- Next (debug copy only): list the game state (animations, facings, room, last 10 key presses) before each dx_on press in the six hangs, to find what precedes each stop.

## 53. Hang pattern and identify-by-input (checked against raw traces, 2026-11-24)
- Last key sends before the five traced real hangs (cycle 1 ep 12; cycle 2 ep 8; cycle 14 ep 13; cycle 15 ep 8; cycle 2 ep 4): four of five stop on the same tick as a key-down during dx_on (identify-by-input). Cycle 2 ep 4 stopped 4 ticks after an approach poke, not a key press.
- Checked by reading the last sends myself: the restart files of cycle 2 ep 4, ep 8 and cycle 3 ep 8 end with "ku" lines in end checks; cycle 14 ep 13 and cycle 15 ep 8 end with dx_on key presses. Matches the agent's table.
- Denominator (300 traced episodes): 4 stops in 6,786 dx_on key-downs (0.06%); 2 in 1,340 presses on a non-body reading (0.15%, Wilson 95% 0.04-0.54%); 2 in 5,446 on a body reading (0.04%, 0.01-0.13%). Intervals overlap: not enough data to tell.
- Not applied, needs a decision: skip non-body records before a dx_on press; pause 1-2 ticks between track and key-down; log the room in the tracer (room is None in the traces now).
- Cycle 16 (launched 04:48 UTC): result pending in ~/nf-p/dbg86/cycle16.out.

## 54. Single hang count (supersedes the counts in sections 46-53)
- Real hangs: 6 in 300 traced episodes (Wilson 95% 0.009-0.043). This is the only count to use.
- Sections 48-51 quoting 5/280 or 4/300 or 4/260 are superseded: the 4/300 figure comes from the signature search in cycle.sh, which misses two hangs (cycle 14 ep 13, cycle 15 ep 8).
- Cause: unproven. Four of the six follow a key press during identify-by-input.
- Cycle 16: result not read (SSH to pippi timed out at 10:36 UTC). Clean-cycle streak: 0.

## 55. Fable decisions (2026-11-24), not yet applied or tested
- Identify-by-input: apply only a 2-tick pause between the track command and the key-down (debug copy). Check: two interleaved arms of 300 episodes each, pause and no pause, same seeds. Worked if the pause arm has no key-down-tick stops and the no-pause arm still shows some. Baseline: 4 stops in 6,786 presses. Skip-non-body filter and room logging wait.
- Reward: kill always +1 with no walk penalty; walk penalty -0.25 only in episodes without a kill; death -1. Check: unit test on the reward function first (show it failing on current code), then retrain and compare the idle-opponent decided rate (now 1 of 7) on at least 50 episodes x 3 seeds, against a rerun of the baseline at the same size.
- Validity: decided kills kept (earlier decision, not changed here).
- Wilson checks of the cited numbers: gen 30 23/40 = 0.575 (0.422-0.715); cycle B 1/7 = 0.143 (0.026-0.513); 6/300 = 0.020 (0.009-0.043).

## 56. Two-arm pause test, interim (2026-11-24 ~11:35 UTC)
- Design: arm A = debug copy (no pause), arm B = code_pause (2-tick wait in dx_on). Same 300 seeds (90000+e), current es4 policy vs frozen. Running on displays :87 and :88 under the load gate; started 11:10 UTC; expected about 2.5-3 h.
- Diff check: the arms differ by one line (self.ticks(2) in nidmem.dx_on); nidenv.py and selfplay_env.py identical.
- Interim, read from pippi with arm_report.py: arm A 26 episodes, 0 restarts, 0 hangs, 642 identify key-downs, 0 key-down-tick stops (0/26, Wilson 95% 0-0.129). Arm B: no traced episodes yet. No comparison possible yet.
- Earlier first-chunk boot on both displays showed "game pid None"; later chunks ran. Cause of the first failure not identified.
- Not yet a result. Stop counts per arm and intervals to be reported at run end.

## 57. Two-arm pause test: arm B failing on its first episodes (2026-11-24 ~12:12 UTC)
- Arm A: 87 episodes, 1 restart (reset failed 5 times), 0 key-down-tick stops (0/87, Wilson 95% 0-0.042).
- Arm B: 0 episodes. Chunk 0 failed on try 1 and try 2 with "state file stopped updating (game hung or exited)" (farmB logs). Chunk 20 and 80 still retrying.
- Read: the game stops publishing state during arm B's first episode, the hang signature. The pause fix has no working run yet, so it is untested.
- Not yet diagnosed. Needs the first-tick trace of arm B's episode 0 before any change.

## 58. Two-arm pause test status (2026-11-24 13:36 UTC)
- Arm B: still 0 completed episodes (no files under arm B's trace folder). Latest run line: chunk 80, try 1, leftover-pid cleanup at 13:25 UTC. Earlier chunks failed with "state file stopped updating".
- Arm A: last full read 12:40 UTC: 138 episodes, 2 restarts, 0 key-down stops. Not re-read since the SSH drop at 13:00 UTC.
- Pause fix: untested (no arm B episodes).

## 59. Arm A final (control, no pause), 2026-11-24 15:07 UTC
- Arm A: 300 episodes finished (14:20 UTC), 2 restarts, 0 hangs, 0 key-down-tick stops out of 300 (6,617 identify key-downs). Stop rate 0 (Wilson 95% 0-0.013).
- Arm B (2-tick pause): still 0 completed episodes; chunk 140 try 1 failed with "state file stopped updating", try 2 running. Pause effect cannot be measured yet.

## 60. Two-arm pause test: arm B still failing (2026-11-24 16:10 UTC)
- Arm B: 0 completed episodes. Chunk 180 try 1 failed with "state file stopped updating (game hung or exited)"; try 2 running with no error at 16:09 UTC. Earlier chunks 0, 40, 140, 160 failed the same way.
- Arm A (control): finished 300 episodes, 0 key-down-tick stops (section 59).
- Pause fix: untested. The 2-tick wait is only exercised once arm B produces episodes.

## 61. Record catch-up, 2026-11-24 16:50-17:07 UTC (verified from pippi logs at each check)
- Arm B (2-tick pause): still 0 completed episodes. Chunk 220 try 1 failed with "state file stopped updating (game hung or exited)"; chunk 220 try 2 running with no error at 17:06 UTC. Earlier chunks 0, 40, 140, 160, 180, 200 failed the same way.
- Arm A (control): finished 300 episodes at 14:20 UTC, 2 restarts, 0 hangs, 0 key-down-tick stops of 300 (section 59).
- Hang count: 6 in 300 traced episodes (Wilson 95% 0.013-0.043 as stated earlier); not re-verified after cycle 16.
- Clean-cycle streak: 1 of 3 (cycle 16 clean; cycle 15 hang broke the earlier run).
- Open decision for the user: keep retrying arm B, or drop the pause arm and move to the hang diagnosis from tick-level traces.
- VNC: tunnel to the pippi viewer restarted from the Mac at about 17:04 UTC; viewer answered on localhost:6085.
- Goal: not met. es4 generation 30 won 23/40 (0.575), no learning trend; trained policy 1/7 vs idle opponent.

## 62. Cycle 15 stop, launcher record (2026-11-24 04:31 UTC), not yet explained
- Launcher exit: returncode 1, alive 485 s, phase "reset", state age 0.12 s at exit, 2.5 s since last write. Last state: tick 24003, P1 (1195.2, 192, anim 465), P2 (0, 0, anim 0), room 29.
- The two follow-up relaunches (04:34 and 04:36 UTC) exited within minutes with no state.
- Traces of that episode and the next reset show normal play and a clean reset; the stop is only in the launcher record.
- Open: whether our reset writes or the game's own exit caused it. Next step: the game's own log for 04:31 UTC on pippi.

## 63. Cycle 15 stop: the game's own Wine tail (2026-11-24, checked)
- Launcher record at 04:31 UTC (dbg86/launcher_exits.jsonl): wine_tail and fault_lines show only ordinary Wine noise (openxr, ALSA, process fixme lines). No fault address, no crash line.
- Read: the game gave no crash signal of its own, which points to the stop being our restart after the failed reset (reset_failures: "no record answers to P2's keys", 04:31:05 UTC). Likely, not proven: a stop signal from our side would not necessarily leave a Wine error line.
- Still open: a confirmed cause needs the process's exit signal, which the launcher record does not capture.

## 64. Correction: most debug-farm "hangs" were our own setup error (2026-11-24 18:25 UTC)
- Mechanism: when a reset gives up, the env restarts its game and runs clean_farm, which SIGKILLs every Nidhogg/wine process whose environment contains the farm path as a substring. The debug farm's trace dir was set to the viewer's folder, so every viewer give-up also killed the debug farm's game.
- Evidence: each of the 12 debug-farm game exits while live falls within 0-3 s of a viewer give-up or an es4 restart. Arm A (control, trace dir outside viz85) finished 300/300 with 0 hangs, 0 key-down-tick stops, 2 deliberate restarts, 0 seed mismatches.
- Fix applied to the debug farm env only: trace dir now a symlink outside the viewer path. Not yet applied: clean_farm should match the exact NIDFARM= entry (approved for the debug copy).
- Consequence: the 6-hang count over 300-320 episodes and the key-down-tick explanation are both superseded. Use a fresh series from cycle 17 (18:25 UTC onward).
- Still open: the reset path that gives up ("no record answers to P2's keys"): about 5 on the viewer and about 10 across es4 farms in about 18 h. Each now costs one restart.

## 65. Verified state at 18:27 UTC (2026-11-24)
- Exact-match kill rule is in the debug copy: `~/nf-p/code_dbg/nidlinux.py` line 98 tests `NIDFARM=<farm>` as an exact env entry. Read on pippi; the staged test result is the pippi agent's (not re-run by me).
- Cycle 17 launched 18:25:35Z in scope nfp-dbg86-1825; cycle17.out has no result line yet. No launcher exits and no cycle-17 trace files have been recorded since 18:25.
- Reset give-up: 114 cases over about 36 h on viewer and es4 farms (pippi agent's count from each farm's diag.jsonl; not re-counted by me). Pattern split from its report: 54 with two fighter records, 20 with the missing fighter parked at x=1600, 34 with extra non-body records. Fix for the 54 case not applied; pippi agent proposed it for the debug copy only.
- Cleanup-fix claim and the superseded hang counts are in section 64.

## 66. The staged clean_farm test checks a copy of the rule, not the function
- I read `~/nf-p/viz85/review/test_cleanfarm.py` on pippi. It compares two string expressions on four made-up environments (viewer game, debug game old env, debug game new env, prefix-sharing farm). It never calls `clean_farm` and sends no signal.
- What it shows: the substring rule matches the prefix-sharing farm (`viz85x`) and the new exact rule does not. That is the right behaviour, but it is evidence about the expression, not about `clean_farm`.
- Still to prove: a call to `clean_farm` against a harmless stand-in process with a staged environment, showing the old rule would have killed it and the new rule does not. Not yet done.
- The code line is `code_dbg/nidlinux.py:98`; the test's last check only confirms that the same expression text appears there.

## 67. clean_farm run on stub processes (2026-11-24, pippi)
- Stubs: two copies of /bin/sleep named Nidhogg.exe, started by the test, owned by my uid. One with NIDFARM=/home/ruggsea/nf-p/teststub_cf (the farm), one with NIDFARM=/home/ruggsea/nf-p/teststub_cfx (prefix-sharing). FARM was pointed at the stub path, so the stop and lock steps had nothing of the real farm to touch.
- Result: clean_farm killed the exact-match stub (exited = True) and left the prefix-sharing stub alive (exited = False). That is the intended behaviour of the exact-match rule, shown by running the function, not a string copy.
- Real game processes: the two real Nidhogg.exe pids (1014336, 1095278) were present before and after. The script's "unchanged: False" is a bug in my check, not a kill: it counted the stub pids in the before list, and the surviving sibling stub was then killed by the script's own cleanup. Nothing else was signalled.
- Script kept at ~/nf-p/viz85/review/cf_stub_test.py on pippi.

## 68. Cycle 17 launcher exits, first two (2026-11-24, checked 18:49 UTC)
- 18:35:33, returncode 1, phase reset, alive 595 s. Wine tail: ordinary RPC/fixme lines, no fault.
- 18:40:45, returncode -15 (SIGTERM), phase episode, alive 309 s. Cycle log line 18:40:45 is an end-of-episode step and "done" at 18:40:47. Who sent the SIGTERM is not in the logs I read. Not explained yet.
- Cycle 17 still running at 18:49; 20 new trace files since 18:25 in dtrace.
- Counts for the fresh series are not yet computed; the 18:35 exit is in the fresh series and counts as a reset-phase exit.

## 69. Who sends SIGTERM to the game (candidates for the 18:40:45 exit, not proven)
- Read on pippi: the only code in the debug copy that sends SIGTERM to a game process is `stop_id()` in `code_dbg/nidlinux.py:168`. It kills the instance's wrapper and game pid, and is the restart-your-own-instance path.
- `dbg86/dbg86_ctrl.py:67` calls `rec.terminate()`, but that is the ffmpeg recorder, not the game.
- So the 18:40:45 SIGTERM came most likely from a `stop_id()` call in the debug farm's restart path during an episode. That call is what a give-up or an abort triggers. Which caller hit it at 18:40:45 is not in the logs I read.
- To prove it: have `stop_id()` log its caller (traceback) to a file before the kill, and let the next cycle run. Not applied; it is a debug-copy change that needs the pippi agent or an approval to make.

## 70. Cycle 17 result, fresh series (2026-11-24, from raw files via dbg86/fresh_series.py)
- Cycle 17 (20261124T182750): 20 episodes, 0 hangs, 1 restart, 1 reset failure, clean-cycle streak 0 (the cycle is not clean because of the restart and the reset failure).
- Series hangs: 0/20 = 0.000, Wilson 95% [0.000, 0.161]. Counted over one cycle only; the clean-cycle requirement is three in a row, so the goal is still not met.
- Read-only check: the script has no kill, unlink or write calls on its own (grep before running).
- The 18:35:33 reset exit (code 1) and the 18:40:45 SIGTERM are both inside this cycle; the 18:40:45 one is still unexplained (section 69).

## 71. Correction to section 69: the 18:40:45 SIGTERM was the end-of-cycle stop
- Verified on pippi: `dbg86/dbg86_ctrl.py` line 104 calls `n.stop()` and then logs "done"; ctrl.log shows the episode at 18:40:45 ("A_current_vs_frozen 19 ... undecided", the 20th and last episode) followed by "done" at 18:40:47. The launcher's -15 at 18:40:45 is that stop, which goes through `stop_id()`.
- So this was a normal end-of-cycle shutdown, not an unexplained kill. Section 69's "not proven" is now settled by this reading.
- Caller log: `stop_id()` in `code_dbg/nidlinux.py` now writes its stack to `$NIDFARM/stop_id_callers.log` (line 168). The debug farm's file is `dbg86/stop_id_callers.log`. It takes effect from cycle 18; cycle 17 had loaded the old module.
- Cycle 17's one restart was episode 11, the reset give-up at 18:35:32 (the 18:35:33 exit, code 1). Clean-cycle streak 0.

## 72. Cycle 15 stop (04:31 UTC): explained as the cross-kill, not a game crash
- Timestamps I read on pippi: viewer reset give-up "no record answers to P2's keys" at 04:31:05 (viz85 reset_failures.jsonl, diag.jsonl); debug-farm launcher exit at 04:31:08, returncode 1, phase reset, alive 485 s (dbg86 launcher_exits.jsonl); game Wine tail has no crash or fault line.
- The pippi agent's account: the give-up runs clean_farm, which killed every Nidhogg/wine process whose environment contained the farm path as a substring. The debug farm's trace dir sat inside the viewer's folder, so the viewer's give-up killed the debug game 3 s later.
- So the cycle 15 stop is the cross-kill (fixed by the exact NIDFARM= match and the moved trace dir), not an unexplained game exit. Section 69's and 63's "likely our restart" reading is superseded by this.
- The cycle 15 hang count (6 in 300) belongs to the contaminated runs and is not used.
- Still open: the reset give-up itself (the viewer's own resets), which costs a restart each time.

## 73. Reset give-up count, re-counted from the raw diag files (2026-11-24)
- Lines containing "no record answers" in each farm's diag.jsonl on pippi: farm1 29, viz85 25, farm4 25, farm3 20, farm2 15, dbg86 2, arms/farmB 0. Total 116.
- The pippi agent reported 114. My count is 116 on the same files; the 2-line gap is not explained (likely a different match on P1/P2 wording or a file it excluded). Use 116 from this count, and note it is a line count, not a count of distinct resets.
- Caveat: these lines span about 36 h and include the cross-kill period, so they are not all independent give-ups under the current code.

## 74. Cycle 18 started (2026-11-24 18:52:28 UTC)
- Nothing was running on pippi when I checked at 18:52 (no cycle process; the pippi agent is no longer in the session list). I started `dbg86/cycle.sh` myself with the existing script, unchanged. The 20-episode cycle runs in scope nfp-dbg86-1852; the load gate in run_ctrl applies. 6 game processes were up at the check.
- Load was 19.35 when cycle 18 launched, so the gate may hold it before its first episode.
- The cycle runs with the debug copy as it stood at 18:52 (exact-match kill rule, caller log in stop_id). The reset give-up fix is not in it.
- Not done: the reset give-up fix and the cycle 18 count. Counts come from `dbg86/fresh_series.py` once cycle18.out has its "hang rate" line.

## 75. Cycle 18 result (2026-11-24, checked 19:04 UTC from raw files via dbg86/fresh_series.py)
- Cycle 18 (20261124T185443): 20 episodes, 0 hangs, 0 restarts, 0 reset failures, clean-cycle streak 1 (this cycle is clean).
- Fresh series so far, cycles 17-18: 0 hangs in 40 episodes, Wilson 95% [0.000, 0.088]. Cycle 17 is not clean (1 restart, 1 reset failure), so the consecutive clean-cycle count is 1, not 2.
- Goal still needs three clean cycles in a row; cycle 19 is the next one needed. Cycle 19 is not started. The cycle script was run by hand; no loop is scheduled to start it.

## 76. Cycle 19 started (2026-11-24 19:05:05 UTC)
- Started by hand with the existing `dbg86/cycle.sh`, unchanged, in scope nfp-dbg86-1905. Load was 5.3 at launch, so the load gate was not holding it.
- Cycle 19 is the one needed for the streak: a clean cycle here makes the consecutive count 2 (cycle 18 clean, cycle 17 not). Three in a row needs cycle 20 as well.
- Counts: read from raw files via dbg86/fresh_series.py after cycle19.out shows its "hang rate" line.

## 77. The stop_id caller log confirms the end-of-cycle stop (2026-11-24)
- First entry in dbg86/stop_id_callers.log: 19:04:19Z, instance 0, pids [1175168, 1179004], caller `dbg86_ctrl.py` line 104 (`n.stop()`), which is the end of cycle 18. Matches section 71 (the end-of-cycle stop, not a crash).
- Cycle 19 has not yet reached its own end; no second entry yet. The log is the only stop record that proves the caller, so keep it for the next SIGTERM.

## 78. Cycle 19 result (2026-11-24, checked 19:17 UTC from raw files)
- Cycle 19 (20261124T190720): 20 episodes, 0 hangs, 0 restarts, 0 reset failures; clean. Controller ended with EXIT 0.
- Consecutive clean-cycle streak: 2 (cycles 18 and 19). Cycle 17 is not clean.
- Series, cycles 17-19: 0 hangs in 60 episodes, Wilson 95% [0.000, 0.060].
- Needed for the goal: cycle 20 clean.

## 79. Cycle 20 started (2026-11-24 19:17:28 UTC)
- Started by hand with the unchanged `dbg86/cycle.sh`, scope nfp-dbg86-1917; load 12.6 at launch. Cycle 20 is the last clean cycle needed for three in a row.
- Counts from raw files via dbg86/fresh_series.py once cycle20.out has its "hang rate" line.

## 80. Cycle 20 result: three clean cycles in a row (2026-11-24, checked 19:53 UTC from raw files)
- Cycle 20 (20261124T191957): 20 episodes, 0 hangs, 0 restarts, 0 reset failures; controller EXIT 0.
- Consecutive clean-cycle streak: 3 (cycles 18, 19, 20). This meets the three-in-a-row bar set in this log. Cycle 17 is not clean.
- Series, cycles 17-20: 0 hangs in 80 episodes, Wilson 95% [0.000, 0.046].
- What this does NOT establish: the es4 learning result is unchanged (generation 30 won 23 of 40, 0.575, no learning trend; the trained policy decided 1 of 7 against an idle opponent). The reset give-up fix has no owner. The pause fix is untested (arm dropped at the user's request). Cycles 18-20 ran with the unchanged debug copy, so the streak covers the reset path as it stands, not a fixed one.

## 81. Generation 30 number, verified from raw es4 eval records (2026-11-24, 19:5x UTC)
- `es4/evals.jsonl`, gen 30 (04:27:16 UTC): P1 current_wins 9, decided 20, attempted 37, undecided 13, win_rate 0.45 (Wilson 95% [0.258, 0.658]). P2 current_wins 14, decided 20, win_rate 0.70.
- Combined: 9 + 14 = 23 wins of 40 decided. The 23/40 = 0.575 figure is correct as the sum of both seats.
- Seat split is not in the 23/40 summary: the P1 seat won 9 of 20, the P2 seat won 14 of 20. Each seat alone has n = 20; the two intervals overlap, so the seat gap is not established either way.
- Gen 25 for comparison (01:59:59): P1 14 of 20, P2 15 of 20. The series does not show a rising trend across these two checkpoints.

## 82. Decisions waiting on Ruggero (written 2026-11-24, for the next reader)
Context: the debug farm has three clean cycles in a row (18-20, 0 hangs in 80 episodes) on the reset path as it stands. The learning result is flat: generation 30 won 23 of 40 (0.575), no trend across gen 25 and 30, the trained policy decided 1 of 7 against an idle opponent. The pause arm was dropped at Ruggero's request.

Decision 1: who fixes the reset give-up ("no record answers to P2's keys", 116 lines in the diag files; the 54-case pattern is two fighter records, one of them the missing fighter's dead record).
- Option A: re-engage the pippi agent (it has left the session list) to write the 54-case fix in the debug copy, test it on staged states, then run cycles.
- Option B: the main session takes it on, same debug-copy rule, staged test first.
- Recommendation: B, because it needs no agent to be revived and the fix is small enough to stage. Reason: the pippi agent's own proposal (walk the other fighter in the GO direction, re-check every second) is untested.

Decision 2: does the flat generation-30 learning result count toward "fully controllable, reliable and robust"?
- Option A: yes, the goal needs a learning gain before it can be called met; the next step is an ES run that moves the idle-opponent decided rate above 1 of 7.
- Option B: no, the goal is the environment's reliability; learning is a separate experiment that can run after.
- Recommendation: A, because the goal's wording is "training episodes", and training that does not learn is not yet robust training. This is a judgement; Ruggero decides.

## 83. Where the reset give-up is decided in the debug copy (read-only, 2026-11-24)
- `code_dbg/nidenv.py` `_find()` (about line 139): waits and walks the other fighter in the fixed sequence (wait 3 s; right 1.5 s; left 3 s), calling `identify` after each step. A walk that leaves the other fighter 1.5 s to the right of its start is the path the 54-case pattern takes; the pippi agent's reading is that this does not bring a dead fighter back.
- `code_dbg/nidenv.py` `reset()` (about line 317–336): five attempts; the assertion at line 336 (`no record answers to {who}'s keys`) fires when `_find` returns nothing for a fighter on every attempt.
- Candidate fix for the 54-case (not applied): change the walk so the other fighter walks in the on-screen GO direction for longer, re-checking every second for a record that answers, and treat a dead record that answers again as alive. The change is confined to `_find()`; a staged test would call `_find` on a recorded state with the other fighter's record present and no answer.
- Owner still open (section 82, decision 1).

## 84. Fable's direction (2026-11-25, relayed by the fable consultant session) and the plan I am taking
Advice only, from the Fable consultant under Ruggero's standing delegation. Not a grant of anything; permissions are unchanged.
1. Reset give-up: I own it now. Order: (a) a test that replays the failure from the diagnostic lines and fails on the current code; (b) the change in `_find()`; (c) the test passes; (d) an acceptance run fixed before it starts: 0 hangs, 0 restarts, 0 reset failures in 300 consecutive episodes over at least 3 cycles. The count restarts after the fix.
2. Flat learning does not count toward the goal; the goal is about the episodes. 23 of 40 against 29 of 40 is noise at n=40. "1 of 7 against an idle opponent" points at the episode machinery: run a simple scripted player against the idle opponent; if it cannot win nearly every game, the fault is in the episodes. No new generations until the acceptance run passes; earlier training is labelled as made before the fix.
3. Pause path stays dropped. Its untested fix stays on its own branch; main must not be able to enter that path by accident.

Plan, and what I have not yet done:
- Not yet started: the replay test. The engine's `identify` and `answers` need a fake memory with `scan`, `answers`, `_is_body`, `track`, `send`, `release_all`, `rec`, `dead`, `otypes`. Read so far: `identify` at nidmem.py:156, `_find` at nidenv.py ~139. The diag record for the give-up (farm1, 2026-11-22 23:45:14) shows both fighters alive, on screen, and both records present, yet no answer to P1's keys. A fake that only fails every answer would test the loop, not the condition, so the replay must reproduce the state.
- To keep the viewer untouched, the fix goes in a separate copy `~/nf-p/code_fix` (copied from `code_dbg`), and only the debug controller's `sys.path` (dbg86_ctrl.py lines 11-12) is pointed at it. The viewer loads `code_dbg` and is not changed.
- Decision that remains with Ruggero: none of the three above needs him under the standing delegation, but the acceptance numbers in 1(d) are Fable's proposal and he may want to set them.

## 85. Reset give-up fix: replay test, change, and acceptance start (2026-11-25)
- Fix copy: `~/nf-p/code_fix` (copy of code_dbg). The viewer and es4 still load code_dbg, unchanged.
- Replay test: `~/nf-p/code_fix/test_giveup_replay.py` (copy in tests/). A MECHANISM MODEL: the fake memory assumes the dead fighter's record answers its keys only after the other fighter has walked left at least 200 px. This is my hypothesis, not a game recording. It is not proof the fix works in the game.
  - On the code before the change: FAIL. The walk nets -150 px (right 1.5 s, left 3 s); `respawn_walk` = ['P2 right 1.5s', 'P2 left 3s']; no respawn. Reproduces the give-up shape.
- Change (fix copy only, backup nidenv.py.pre_giveup): the left walk is four 1-second steps, each followed by a re-identify, so the other fighter nets -250 px. After the change: PASS.
- Acceptance, per Fable: the debug controller and launcher now point at code_fix (dbg86_ctrl.py and run_ctrl.sh, backups *.pre_codefix). Cycle 21 is the first acceptance cycle.
- Count question for Fable/Ruggero (not decided by me): "300 consecutive episodes over at least 3 cycles" is inconsistent at 20 episodes per cycle (300 = 15 cycles). Until answered, the run goes on and the count is kept per episode.
- Pause arm: still dropped; not touched.
- Learning: not run; no new generations until acceptance passes.

## 86. Acceptance cycle 21 launched on code_fix (2026-11-24 23:32:11 UTC)
- Scope nfp-dbg86-2332, running the unchanged cycle script pointed at code_fix. First acceptance cycle; it counts only if it and the next 14 cycles (300 episodes) finish with 0 hangs, 0 restarts, 0 reset failures, pending the count question in section 85.
- 23:34 UTC check: cycle 21's controller log shows "game pid None" for instance 0 (wrapper 1749917, up 2 min). The game processes are up (Nidhogg.exe under Proton, plus a second launch at 1 min). Not yet confirmed in a match; no restarts, hangs or reset failures logged. Counts start when the first episode is logged.

## 87. Acceptance cycle 21: boot retry (2026-11-25 check, 23:47 UTC)
- Attempt 0 failed at 23:40:22 ("boot failed: full farm cleanup"); the cycle retried. A new game process for DISPLAY :86 (pid 1778947, comm Nidhogg.exe) is up, so the launcher's `game pid None` should clear on its next check. The other Nidhogg.exe on :85 is the viewer's game, untouched.
- No episode logged yet. Counts from raw files once the first episode is logged.

## 88. Acceptance cycle 21 stalled and was relaunched (2026-11-25, 23:47 UTC)
- The first cycle-21 controller (pid 1749841) stopped writing to ctrl.log at 23:40:46, seven minutes before the check, after "boot failed: full farm cleanup" at 23:40:22. It was waiting with `game pid None` while a game for :86 was up (pid 1778947). Its processes were owned by my user, with cwd in dbg86/code_fix. Stopped by pid; all four gone.
- The stalled output is kept as cycle21.stalled.out. Nothing from it counts toward acceptance (no episodes logged).
- Relaunched at 23:47:51 as cycle21b (same cycle script, same code_fix). Its first log line shows the same `game pid None` state, which is normal for the first seconds. Root cause of the earlier stall is not yet known: `_game_pid` matches on comm and DISPLAY, and the game for :86 was up, so the matching step is the place to look if this recurs.
- Acceptance counts restart from cycle21b.

## 89. Cycle21b boot failed again (2026-11-25, 23:56 UTC): not yet explained
- Attempt 0 failed at 23:56:04 ("boot failed: full farm cleanup"), the same message as 23:40:22. The controller boots for up to 400 s waiting for the game's spy to answer a ping; neither boot answered.
- Code check: the fix copy (code_fix) matches code_dbg in nidlinux.py, nidmem.py and nidobs.py. The only difference is nidenv.py (the `_find` walk), which the boot path does not call. train/ is identical.
- Load during these boots was 21–23 (cycles 19–20 booted at 5–12). Load is the leading candidate and is not proven.
- Next: the next boot's result decides it. If it fails again at similar load, read the spy's state for the game on :86 before changing anything.

## 90. Boot failures: load and code_fix both checked; neither explains them alone (2026-11-25)
- Counted from raw controller logs on pippi: 22 debug-controller logs; boot failures in 3 (ctrl.024401, ctrl.234747 = the stalled cycle 21, ctrl.log = cycle 21b). The other 19 booted without a failure.
- Load at cycle start: the failing cycles began at load 11.8 (cycle 21) and 21.4 (cycle 21b). Cycle 20 booted cleanly at 12.6, cycle 19 at 5.3. So load does not separate them. Load is no longer the leading candidate.
- Code: ctrl.024401 failed once and predates code_fix (it ran on code_dbg). So the boot failure is not specific to code_fix either.
- Current reading: an intermittent boot failure (about 1 in 7 cycles) that predates this session's changes; cause not found. Not yet a blocker for the acceptance count, since a failed boot still retries and logs nothing for episodes.

## 91. SSH to pippi timed out at the banner exchange (2026-11-25, 00:08 UTC); backing off
- The check at 00:08 UTC failed with "Connection timed out during banner exchange", the signature of a self-imposed rate-limit (see the SSH self-ban rule in CLAUDE.md memory). The earlier one-minute Monitor loop (15 SSH checks in a row, 23:50–23:56) is the likely cause.
- Decision (taken by me, no retry): no SSH to pippi until the 01:07 UTC check, then one check at a time. Retry loops would extend any ban.
- Acceptance state at the last good read (23:57 UTC): cycle21b still in its boot window (game pid None, wrapper 1811440). No episodes logged. Counts not yet started.
- Pending on the next good read: the controller's boot result, then the acceptance count per the rule in section 85 (300 consecutive episodes, 0 hangs, 0 restarts, 0 reset failures).

## 92. Cause of the boot failures on code_fix: my copy was missing the spy folder (2026-11-25, 00:29 UTC)
- The launcher loads the spy from `spy/nidspy.so` next to its own code (nidlinux.py line 42). `code_fix` was copied with only the `*.py` files and `train/`, so the folder `spy/` was absent. The game ran, but the spy never came up: "game/spy did not come up; game alive True", twice per attempt, then the controller exited with "two sessions lost before the first episode" (ctrl.233207b.log).
- This is why cycle 21 stalled and cycle 21b failed: my copy, not the game and not the load. The earlier "intermittent" reading in section 90 was wrong for these failures; the failures predating code_fix (ctrl.024401) are not explained by this and are still open.
- Fix: `spy/` copied from code_dbg into code_fix (cmp: identical). Relaunched as cycle21c. Acceptance count restarts from cycle21c's first episode.
- Lesson for this copy: copy the whole tree, not only *.py.

## 93. Acceptance cycle21c booted and is running episodes (2026-11-25, 00:34 UTC)
- Launch at 00:31:24 (pid 1878348, enter_match_v2 and in_match True). Episodes are being logged from 00:33 (ctrl.log, episodes 3–6 of this cycle at 00:34).
- Counts for acceptance come from raw files once the cycle completes. Acceptance needs 15 consecutive cycles of 20 with 0 hangs, 0 restarts and 0 reset failures (section 85).

## 94. Acceptance count so far (2026-11-25, 00:35 UTC, from raw files)
- Cycle 21c (20261125T003128): 9 of 20 episodes logged; 0 hangs, 0 restarts, 0 reset failures so far; controller log shows 0 restart, lost-game or boot-failure lines.
- Acceptance count toward 300: 9 episodes, all clean so far. The "clean-cycle streak 4" that fresh_series.py prints includes this unfinished cycle and is provisional; count it only when the cycle finishes.

## 95. Acceptance cycle 21c finished clean; cycle 22 started (2026-11-25, 00:55 UTC)
- Cycle 21c (20261125T003128): 20 of 20 episodes, 0 hangs, 0 restarts, 0 reset failures. Controller finished. Acceptance count toward 300: 20 clean episodes (1 cycle of 15).
- Cycle 22 started by hand with the unchanged cycle script, now on code_fix (cycle22.out). Counts from raw files once its controller finishes.
- The fresh_series.py "clean-cycle streak 4" still counts the pre-fix cycles 18–20 and is not the acceptance count; acceptance starts at cycle 21c.

## 96. Acceptance cycle 22 finished clean (2026-11-25, 01:10 UTC, from raw files)
- Cycle 22 (20261125T005729): 20 of 20 episodes, 0 hangs, 0 restarts, 0 reset failures; controller EXIT 0.
- Acceptance count toward 300 consecutive: 40 clean episodes (cycles 21c and 22), 2 of 15 cycles.
- Next cycle (23) needs starting by hand; the wake-up stays on the acceptance count.

## 97. Correction: the policy can never press two keys at once (found 2026-11-25, read-only)
- The action table `ACTIONS` in nidenv.py has 9 entries; the two combined ones are indices 7 (left+attack) and 8 (right+attack).
- The policy's output size is `N_ACTIONS = 7` (train/env_iface.py; used by train/train.py for the layer shapes), and actions are sampled from those 7 logits, so indices 0–6 only.
- Result: indices 7 and 8 are unreachable. The current policy never presses two keys together, and "left+attack" / "right+attack" never happen. My earlier answer ("only those two pairs press two keys") was wrong about reachability and is corrected here.
- This is one of the reasons for the per-button action change (D-2026-11-25-action-space). Written in code_multi only; code_fix (the acceptance run) is unchanged.

## 98. Per-button key transition written and tested in code_multi (2026-11-25)
- `key_transition(held, bits1, bits2)` in code_multi nidenv.py: six on/off values per fighter in the order left, right, jump, attack, up, down; held until changed; returns the ku/kd lines and the new held set. `step()` now uses it, and the separate tap path is gone.
- Staged test `code_multi/tests/test_keys.py`: PASS. Checks: one key on gives one kd; holding does not re-fire; a changed key gives a single kd; all off gives ku for each held key; two fighters with two keys each give the right kd set.
- Not yet done: the policy head (16 -> 6 sigmoid outputs, Bernoulli sampling) in train/, the callers that pass bit tuples instead of action ints, and a key probe in the real game to see whether jump and attack read the press edge or the held level (Fable's decision 2).
- The original file is nidenv.py.pre_multi. code_fix (acceptance) is untouched.

## 99. Work list for the six-output policy in code_multi (2026-11-25, read-only check)
Callers of the discrete action that must change, found by grep in code_multi (not yet edited):
- `train/env_iface.py`: N_ACTIONS = 7, and the `step(self, action: int)` signature. Becomes 6 outputs; the step takes a bit tuple per fighter.
- `train/train.py`: SHAPES use N_ACTIONS (layer 16 -> 6), and `act()` takes argmax; becomes `z > 0` per key.
- `train/selfplay.py`: `act_sample()` samples one categorical action (softmax + rng.choice). Becomes sigmoid per key with `rng.random(6) < p`. `episode()` counts `acts` over 7 indices; becomes counts per button.
- `train/selfplay_env.py`: `step(self, a1, a2)` forwards to nidenv `step`; the bit tuples pass straight through.
- `train/nidtrain_env.py`: single-agent `step(self, a)` maps `nidenv.ACTIONS[a]`; this is the trainer's own env and needs the same six-bit form or must stay on the old action table.
- `train/replay_stub.py`: a stub step; check whether it is used by any run.
Order: env_iface and nidtrain_env first (so the import shapes agree), then train.py, selfplay.py, selfplay_env.py. Each change gets a staged test before the next. The code_fix run is not touched.

## 100. Six-output policy module written and tested in code_multi (2026-11-25)
- New `code_multi/train/policy6.py`: MLP obs -> H tanh -> 6 logits, one per button; `sample_bits` draws each button independently (p = sigmoid, pressed when U < p); `greedy_bits` presses where logit > 0.
- Staged test `code_multi/tests/test_policy6.py`: PASS. Checks shapes of the unpacked weights, that the greedy output is six bits, that sampled frequencies match the sigmoid probabilities (tolerance 0.03 over 4000 draws), and that some samples press two or more buttons at once.
- Not yet wired in: train.py's SHAPES and act(), selfplay.py's act_sample and episode, selfplay_env.py's step, nidtrain_env.py. The list and order are in section 99. code_fix (acceptance) is untouched.

## 101. Self-play sampling switched to six outputs in code_multi; trainer shapes not yet (2026-11-25)
- `train/selfplay.py`: `act_sample` now calls `policy6.sample_bits` (six independent buttons); `episode()` counts presses per button (six counters per fighter). Backup: selfplay.py.pre_policy6. Compiles.
- Not yet consistent: `train/train.py` still builds the 7-output shapes (`SHAPES` from N_ACTIONS = 7), so a 6-output theta from self-play would not match the trainer's `act()` and the parameter vector. `train.py` and `env_iface.py` must change together; `nidtrain_env.py` also depends on the 7-entry table.
- So code_multi is not yet runnable end to end. Wiring the trainer shapes is the next step; then the selfplay_env step and the key probe.

## 102. Trainer shapes and greedy action wired to six buttons in code_multi (2026-11-25)
- `train/train.py`: SHAPES use N_BUTTONS = 6 (not N_ACTIONS = 7); `act()` returns the greedy six-button tuple from policy6.greedy_bits. Backup train.py.pre_policy6. Compiles.
- Staged test `code_multi/tests/test_train_shapes.py`: PASS. The parameter vector has the six-output size, and the greedy action is six 0/1 values.
- Still not runnable end to end: `train/nidtrain_env.py` (single-agent env, step takes an int) and `train/selfplay_env.py` (step(a1, a2) forwards to nidenv) still pass integer actions into nidenv. They must pass six-bit tuples to nidenv.step, which uses key_transition. That is the next edit, then a staged test of one episode with a fake game.
- `train/selfplay.py` imports SIZES and act from train.py, so it now uses the six-output shapes too.

## 103. Self-play environment takes six-button tuples in code_multi (2026-11-25)
- `train/selfplay_env.py`: `step(a1, a2)` now takes six-bit tuples and passes P1's to nidenv.step directly. P2's tuple goes through `mirror_bits`, which swaps its left and right buttons (indices 0 and 1) for its mirrored frame. The old integer `SWAP` table is no longer used on this path. Backup selfplay_env.py.pre_bits. Compiles.
- Staged test `code_multi/tests/test_mirror.py`: PASS (only left and right swap; other buttons unchanged).
- Still integer: `train/nidtrain_env.py` (single-agent env, step takes int and its partner returns an int). Left as is for now; the self-play path is the one es4 uses. Decide with Fable whether the single-agent path is kept or dropped in code_multi.
- Not yet run: one episode end to end with a fake game through nidenv.step and key_transition. That is the next test.

## 104. Acceptance cycle 23 finished clean (2026-11-25, 01:24 UTC, from raw files)
- Cycle 23 (20261125T011326): 20 of 20 episodes, 0 hangs, 0 restarts, 0 reset failures; the controller's log has no restart, lost-game or boot-failure line.
- Acceptance count toward 300 consecutive: 60 clean episodes, 3 of 15 cycles (21c, 22, 23).
- Next: start cycle 24 by hand on code_fix, with the same unchanged script, and keep recording counts from raw files.
