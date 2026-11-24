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
