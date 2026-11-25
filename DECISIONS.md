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
