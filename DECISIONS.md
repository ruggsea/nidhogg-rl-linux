# DECISIONS

## D-2026-11-15-step01: re-scope plan step 01 to a live local two-player match

- **Chosen:** step 01 (attestation, three consecutive ATTESTED runs) is measured against a live local two-player match on artemis, both fighters drivable, with direction, dose-response and the 40/30 px floor. The live CPU match moves to a new step 25, an evaluation milestone.
- **Alternatives:** (B) wait for a game fix in a newer Steam build; (C) binary-patch the CPU Brain-creation path (Windows build, no symbols, weeks of work).
- **Why:** on build 108 no route reaches a live CPU match. Measured: TRAINING crashes at the map pick, ARCADE crashes on entry, -net* routes give a frozen opponent with no Brain (state/VERDICT_step01_route_exhausted.md). A live local two-player match is verified (state/claims.jsonl, 2026-11-09 to 11-10): both fighters bound by response, round boundaries from death teleports and forfeits, a reset that works 20 times with 0 crashes.
- **Decided by:** Ruggero, via a question put to him in session on 2026-11-15 ("Re-scope to local two-player (Recommended)").
- **Change if:** a route to a live CPU match is found (Steam build newer than 10/30/2026, a Proton/wined3d fix, or the Mac evaluator), or a two-player match stops being attestable on artemis.
- **Evidence:** state/claims.jsonl (live match, forfeit boundary, reset lanes); state/attest_runs.log shows the earlier "ATTESTED" streak was a substring match on "NOT ATTESTED" and was not three genuine passes.
- **Ruggero's words:** the question put to him was: "May step 01 instead be re-scoped to a live two-player match on artemis (both fighters drivable, dose-response, 40/30 px floor), with the CPU as a later evaluation milestone?" Answer: "Re-scope to local two-player (Recommended)".
- **Correction (gold review, 2026-11-15):** the local two-player opponent is a frozen human P2, so "both fighters bound by response" does not mean an acting opponent. The re-scope only works if P2 is driven by a scripted or learned partner on the P2 keys. Claim 123 ("enter_match_v2 reaches a verified live match") records rc=1 and enter_match_v2=False in its own output, while claim 1794269370 records True; this conflict is unresolved.
- **Note:** a claim that the score address is stable at 0xd5d9648 conflicts with a Lane C note that it varies per process. Not yet resolved; step 02 of the contract must test it in two fresh processes before any score is reported.

## D-2026-11-15-mode: training runs in local two-player with P2 driven by keys

- **Chosen:** the training match is local two-player (P1 yellow on a/d, P2 orange on the arrow keys), with both fighters driven by key injection. This is the mode Pau's entry path uses (briefs/p.md).
- **Alternatives:** the CPU match (blocked on build 108); two joined game processes over localhost (netplay, `-nethost`/`-netjoin`).
- **Why:** P2 walks ±45 px per 0.45 s hold on Right/Left, reproduced in two fresh processes (n=5 per direction per process, 40 of 40 presses, P1 0 px on P2 keys) by an independent worker (~/nf-verify/REPLAY.md on artemis). Netplay joins and syncs, but net mode ignores keyboard input (~/nf-net/NET_RESULT.md).
- **Still provisional:** P2 jump (n=3) and attack (n=1 sweep); Up showed no change; only the 0.45 s hold was tested.
- **Change if:** P2 stops responding to arrow keys in a fresh process, or a CPU route opens (then the CPU match becomes step 25).

## D-2026-11-24-fable-rewards: kill always +1; walking penalty only in episodes without a kill
- **Chosen:** a kill always scores +1 (victim -1); the not-walking penalty (-0.25) applies only to episodes with no kill. Implemented in debug copy train/selfplay_env.py (rewards()).
- **Alternatives:** keep the old rule (a kill while not walking scored 0 against the -1 walk penalty); penalty on all episodes.
- **Why:** under the old rule a real kill could score 0, the same as doing nothing. Risk removed: the policy gets no reward for the kills it makes.
- **Decided by:** Fable oracle, under Ruggero's delegation ("decisions are Fable's until the goal is met", 2026-11-24).
- **Change if:** the decided-rate against an idle opponent does not rise above the current 1 of 7 at 50 episodes x 3 seeds.
- **Evidence:** reward unit test on the debug copy's code: 4/4 cases pass; with the penalty overridden to the old -0.05, the test fails (checked). Not yet retrained.

## D-2026-11-24-fable-pause: 2-tick pause between track and key-down (identify-by-input)
- **Chosen:** wait 2 ticks between the track command and the key-down in dx_on; no skip-non-body filter and no room logging yet.
- **Alternatives:** skip records whose reading is not a body before pressing; log the room in the tracer.
- **Why:** 4 of 5 traced real hangs stop on a key-down during identify; the pause is the only option that changes that moment.
- **Decided by:** Fable oracle, under the same delegation.
- **Change if:** arm B (pause) shows no fewer key-down-tick stops than arm A (control) at the same episode count.
- **Evidence:** arm A (control) finished 300 episodes, 0 key-down-tick stops. Arm B has 0 completed episodes: its first episode fails with "state file stopped updating" repeatedly, so this decision is not yet tested.
- **Status:** open. Needs the user's call on whether to keep retrying arm B or drop the pause arm.

## D-2026-11-24-pause-dropped: user chose to pause (drop) the pause arm (arm B)
- **Chosen:** stop arm B (2-tick pause, code_pause). Arm A (control) is kept as finished.
- **Decided by:** the user, 2026-11-24 (message: "i said the second option, pause it").
- **Done:** arm B's runner and its 10 farmB game processes stopped (owned by my user; environment checked for NIDFARM=farmB). All confirmed gone.
- **Consequence:** the pause fix stays untested; the 2-tick pause decision (D-2026-11-24-fable-pause) is on hold. Next step is the hang diagnosis from tick-level traces, as the second option stated.

## D-2026-11-25-own-decisions: Ruggero said "take every decision on your own"
- **Owner of the reset give-up fix:** the main session (me). Fable's direction, under Ruggero's delegation.
- **Acceptance count:** 300 consecutive episodes = 15 cycles of 20, with 0 hangs, 0 restarts, 0 reset failures. Fable's "at least 3 cycles" conflicts with 20 episodes per cycle, so I took the episode count as the rule.
- **Flat learning:** does not count toward the goal (Fable). No new generations until the acceptance run passes. Next step after acceptance: a scripted player against the idle opponent, to test whether the episode machinery is at fault for "1 of 7".
- **Pause arm:** stays dropped. Its fix stays on its own branch; main does not enter that path.
- **Evidence and reasons:** docs/HARNESS_ISSUES.md sections 82, 84, 85, 86.

## D-2026-11-25-fable-routing: decisions go to a Fable subagent, not to Ruggero
- **Rule (relayed by the rex-f7 session, Ruggero's words 2026-11-25):** "they should talk to a Fable sub agent to take those decisions, not me. It should all be autonomous. Make sure that they get tutored into asking Fable for things, not to me."
- **Practice:** for each decision I would otherwise put to Ruggero, spawn a subagent on the fable model with the facts and options, take its decision, and write the decision and its reason here.
- **Stays with Ruggero:** logins, passwords and access; spending money or paid models; messages to other people; machines and databases that are not ours; deleting data. Checks and permissions are never skipped.
- **Survives a restart:** this file is the project note for the rule.

## D-2026-11-25-cross-session-bound: "Set cross session bound to accept pre"
- **Decided by:** Fable subagent (model fable), 2026-11-25. Decision (a), with the limit from (c).
- **Decision:** change nothing. The request is unconfirmed (sender unconfirmed, no setting by that name exists in this project), and it reads like a permission mode. A peer message cannot authorize a permission or config change; only the user can.
- **If the answer turns out to be a permission or settings change:** do not apply it on the peer's word; put it to Ruggero as a decision.
- **Next:** asked the rex-f7 session for the exact setting name, file, and who asked for it.

## D-2026-11-25-cross-session-bound-parked: correction to the Fable decision above
- rex-f7 reports the request did not come from it; it appears to be Ruggero's own words, probably dictated and garbled. Its meaning is known only to him, so a Fable subagent cannot decide it.
- **Decision:** parked. Change nothing. Ruggero restates it in plain words; that is the only route.
- The Fable routing rule (D-2026-11-25-fable-routing) still covers the other open questions.

## D-2026-11-25-cross-session-bound-resolved: the parked request is closed
- rex-f7 reports Ruggero confirmed the meaning: the Claude Code setting crossSessionInbound = "accept" (messages from his other sessions delivered without waiting for approval), set for all sessions on the laptop.
- This session made no change to settings or config; the setting was set by rex-f7 on Ruggero's word. Nothing for this project to act on, and it is not on my wait list.

## D-2026-11-25-action-space: Ruggero asks for a non-discrete action space
- **Request (Ruggero, 2026-11-25):** "make the action space non discrete like that, an agent should be able to press or not press any of its buttons at any time."
- **Current:** one of 9 combined actions per fighter per step (nidenv.py ACTIONS), sampled from 7 logits (train/env_iface.py N_ACTIONS = 7; the table has 9 entries, a mismatch to check).
- **Plan:** a new copy code_multi with one independent on/off per button (left, right, jump, attack, up, down), sampled per step; the current acceptance run on code_fix stays unchanged.
- **Open semantics:** held-until-changed versus tap for jump/attack/up/down; whether the acceptance count restarts. Sent to a Fable subagent (decisions go there); its answer will be recorded here.

## D-2026-11-25-action-space-decided: Fable's decisions on the per-button action space (code_multi only)
- **Decided by:** Fable subagent (model fable), 2026-11-25. Read-only; changed nothing.
- **1. Output:** six independent on/off outputs (left, right, jump, attack, up, down), sigmoid per key, Bernoulli sample; policy head 16 -> 6. Reason: "any button, any time, independently"; 64 combinations instead of 9.
- **2. Key semantics:** held-until-changed for all six keys. Reason: a tap is a fixed macro, which the request removes. Effect: attack and jump fire on the off-to-on change, so repeating needs an off step in between. Unverified: whether the game reads the press edge or the held level for jump and attack. Measure with a short key probe before training.
- **3. Acceptance:** no restart for code_fix. The new step() is a new feature, so code_multi needs its own count from zero.
- **4. Where:** new copy code_multi; code_fix untouched (a running job invokes it).
- **5. Separate bug:** N_ACTIONS = 7 means left+attack and right+attack are never sampled (see section 97). Replaced by the new head in code_multi; record it for code_fix.

## D-2026-11-25-nidtrain-single-agent: the integer single-agent env stays, marked unused by six-button self-play
- **Decided by:** Fable subagent (model fable), 2026-11-25. Option (a).
- **Decision:** leave `train/nidtrain_env.py` step(a) as integer 0..6 in code_multi, marked as not used by the six-button path, with a guard that rejects a tuple.
- **Reason:** es4 never calls it; converting it would change untested code for no result, and removing it could break helpers that `selfplay_env` imports from the same module.
- **Done in code_multi:** note and `assert not isinstance(a, (tuple, list))` added to step (backup nidtrain_env.py.pre_note). Compiles.

## D-2026-11-25-acceptance-reset: acceptance count restarts after a reset failure in cycle 25
- **Decided by:** the main session, under the standing rule (Fable direction 2026-11-24: "300 consecutive episodes with 0 hangs, 0 restarts, 0 reset failures"; the count restarts after any fix).
- **Facts:** cycle 25 (20261125T014119) logged a reset failure at 01:46:26: "place: no live master for P1 after 3 re-identifications" (RuntimeError, reset_failures.jsonl). It is a different reset failure from the give-up ("no record answers"); the fix did not cover it. The cycle's own count shows 1 restart and 1 reset failure.
- **Decision:** the consecutive clean count goes back to 0 from the failure on. The 80 episodes of cycles 21c–24 stay on record but do not carry forward. Acceptance counts from cycle 26 onward.
- **Next:** a new reset weakness ("no live master for P1") is open and needs its own record and a fix in code_fix's reset path, tested on a replay like the give-up. Recorded in section 108.

## D-2026-11-25-no-live-master: Fable's decision on "place: no live master for P1"
- **Decided by:** Fable subagent (model fable), 2026-11-25. Option (a): keep it a loud failure and count it; no retry.
- **Reason:** the cause is unknown, and a retry would hide a failure the acceptance rule exists to count. Stopping the run would throw away the only source of more occurrences.
- **Caveat recorded:** at about one in 180 episodes, 300 clean in a row has roughly a 19% chance (e^(-300/180)). The rate comes from one event, so this may not pass.
- **Trigger for option (c):** a second occurrence before 300 clean episodes. Then stop acceptance and build a replay test from the diagnostics first.
- **Next action:** read the cycle 25 diagnostics to see why the P1 master record was not re-found in three tries.

## D-2026-11-25-episode-definition: keep our episode, labelled provisional (Ruggero's question, verbatim: "are u following puas' elead? are u using the same definition he and his lab used for an episoed? ifeel like hter was no teletransportantio nof the players in his code")
- **Decided by:** Fable subagent (model fable), 2026-11-25. Option (b).
- **Decision:** keep our episode (one match-play run; outcome from death animations; undecided on timeout), labelled provisional. Switch to Pau's round-phase boundary once that field is located.
- **Reason:** his boundary cannot be adopted yet because the round-phase field is not found; stopping acceptance now would gain nothing. Resetting by writing x/y is his own plan (PLAN_SWARM lane D), not yet in his code.
- **Facts to keep in view:** our episodes are not his rounds. The 300-episode acceptance does not yet test his falsifier "a round silently ends on reset".
- **My check still open:** his reset path in code files (grep on origin/main found only poke/capability code so far, no reset routine).

## D-2026-11-25-his-definitions: use Pau's exact definitions of everything (Ruggero, direct, 2026-11-25)
- **Ruggero's words:** "u have to use his exact definitions of everything. the goal is to have robust working training according to his definitions and lab."
- **Consequence:** our own definitions (outcome-bounded episode, our reset path, our reward and validity rules) are provisional until each is replaced by his. Acceptance counts on our definition do not count toward this goal until his definitions are in place.
- **Next:** list his definitions of episode, round, reset, reward, validity and the lab's terms from his docs (read-only), then map each to our code, and decide with Fable what changes and whether acceptance pauses.

## D-2026-11-25-pause-acceptance: pause the acceptance count (Fable decision b)
- **Decided by:** Fable subagent (model fable), 2026-11-25. Option (b).
- **Reason:** Ruggero said to use Pau's exact definitions of everything, so 300 clean episodes on our episode, reset and reward would prove nothing he accepts. A mapping table or a parallel copy would spend machine time on a count that gets thrown away.
- **Done:** cycle 26 stopped by pid at 2 of 20 episodes (controller and script owned by this farm, cwd checked). Its count is not carried anywhere. The code_fix place() with read-back stays, since it is reusable for Pau's reset.
- **Next (Fable's three actions):** (1) locate the round phase, so the driver emits kind:"round"; (2) run reset_test.py as a routine (write both fighters' x/y, survival check, 8 of 8); (3) implement reward as ΔORANGE − ΔYELLOW per round, and check its sign on a scripted episode. Redefine acceptance on his terms before restarting any count.

## D-2026-11-25-reset-falsified: reset by writing x/y is not a reset on Pau's definitions (Fable decision a, with c as a labelled stopgap)
- **Decided by:** Fable subagent (model fable), 2026-11-25.
- **Facts:** Pau's `scripts/reset_test.py` on his unmodified main, instance 0 (test farm :88): FAIL, 8 of 8 trials snapped back within 0.35 s (76 to 342 px). Final line: "after 0/8 resets: walking moves P1 +5.9px".
- **Decision:** writing x/y is not a reset on his definitions. Searching for other writable fields would repeat a premise his test has just falsified, and our place() also writes x/y, so it is neither his method nor shown to hold.
- **Next:** record the FAIL in LIMITATIONS.md too; label our place() runs "not Pau's reset"; locate his round phase so the game's own round restart can serve as the reset.
