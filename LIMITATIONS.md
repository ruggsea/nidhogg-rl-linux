# LIMITATIONS

Accepted limits. Do not “fix” these by quietly ignoring them.

1. **Farm-only train/game.** This Mac does not run Nidhogg or `train_win.py`. Farm = pippi `~/nf-p/{pau86,code_pau,venv}`, display `:88`.
2. **No Mac rewrite commit** of `train_state.py` / `train_win.py` until stash-or-keep is decided. Farm diffs live on pippi; record them as unified diffs in engineer.md.
3. **PLAN15 = 1-generation diagnostic.** Partner BEST lines are not partner-strength evidence. Critic may REFUSE them (inert BEST, me/them swap, DISCARDED-with-fit).
4. **I1–I4 hold on Pau versus path.** No real training (>1 gen) and no “learns/beats” until those claims hold **after** `enter_match_v2` (local versus). TRAINING-menu I1 does not count.
5. **plan.json 02/03 stay open.** Do not `plan.py done` on B5/forfeit-only. Steps 05–07/11/12 are `pending I1–I4`.
6. **`/tmp` helpers are not durable.** Load-bearing code belongs in `code_pau/tools/` (or Mac `tools/`). Obsolete one-shots must be cleared or dated obsolete.
7. **AppleDouble / clutter.** `._*` must stay out of the tree (gitignore + delete). Checkpoints and bulk run logs are not source of truth — claims + figures are.
8. **Do not build a second stack.** Ignore Mac TRAINING/`run_entry`/partner_downs as the training path; ignore `.claude/worktrees/step01-rescope` docs as current. Pau `nidstate`/`nidlinux`/`PROVEN.md` win.
9. **READY-nav ≡ wall_gate.** `nav_ok` requires `_fighters_visible` + central `_wall_x` + `on_ready_screen`; yel/ora crumbs are diag-only (old cols_ok false-positive on BLUE+ORANGE). Probe wall-gate fail `no_fighters` ≠ `wall_null` when wall present (Critic ACK 2026-11-27T00:23:31Z).
10. **I1 bind needs live room-file.** `InstanceManager.in_arena` reads `/tmp/nid_room_now_%s.txt` — must sync from nidmem after entry (`wait_arena`) or bind refuses on stale menu room. Both colour parks required; walk tol scales with fw (v5k Critic ACK 2026-11-27T00:52:02Z).
11. **No probe without fresh NAV-DONE.** After kill/abort, require a new `i1_nav_ready_*.json` with `nav_ok=true` stamp newer than the Critic HARD line (2026-11-27T00:56:36Z). Do not relaunch from in_match on a stale READY stamp; wall=None launches get killed.
12. **Orange park / stage-select.** At fw=640, pad hitbox can fire stage-select before centroid±tol; treat that as park success. Do not re-READY after orange=False if still READY — retry in-place. Hold must not divide by fw scale (Critic ACK 2026-11-27T01:24:37Z).

13. **I1 dose prep (v5l).** A-first hard park me≤500 before face-right; refuse dose on prep_fail. Short D drive_ok then re-park ≤500 before hold; too_right gate 500 (not 700). Reject teleport-sized drive_ok jumps. Critic ACK 2026-11-27T09:56:17Z — still REFUSE I1 until dose_ok+claim0+falsifier1.

14. **I1 dose prep (v5m).** A-probe is advisory — pull loop must still run. Park target ≪500. Pre-dose D max_abs=700 so real +dme≈400 is not soft-tele. Critic ACK 2026-11-27T10:37:44Z — still REFUSE I1 until dose_ok+claim0+falsifier1.

15. **I1 dose prep (v5n).** Refuse me_x≈0 as valid. After park must re-face D and verify D→+dme before dose; dead_me→prep_fail. Critic ACK 2026-11-27T11:27:50Z — still REFUSE I1 until dose_ok+claim0+falsifier1.

16. **I1 dose prep (v5o).** After A-park must rebind before face-D verify (0.45s face + 0.55s D hold). On D dme=0: rebind+repark+longer face — do not A/D face-flip. Critic ACK 2026-11-27T12:08:04Z — still REFUSE I1 until dose_ok+claim0+falsifier1.

17. **enter_match_v2 spawn poll (entryfix_v5o).** After Return, poll `in_match` ≤~7.5s (not one 3s sleep). If not on READY but already `in_match`, accept live. Critic ACK 2026-11-27T12:17:39Z — still REFUSE I1 until dose_ok+claim0+falsifier1.

18. **I1 dose prep (v5p).** D-verify must be short (~0.18s, max_abs≈160) to avoid soft/hard tele. Hard repark me≤500 after verify. Rebind-before-verify or abort clean. Critic ACK 2026-11-27T12:54:06Z — still REFUSE I1 until dose_ok+claim0+falsifier1.

19. **I1 dose prep (v5q).** Prove bind A-response before dose; face-D ≥0.55s then repark if >500; tap-D confirm (~0.22s, max_abs≈180). Retry must reuse full face+tap path. Critic ACK 2026-11-27T13:42:28Z — still REFUSE I1 until dose_ok+claim0+falsifier1.

20. **No 4th fix of the same check.** After 3 failed fixes of one check, Critic must not ACK a 4th — choose a different way (Ruggero 2026-11-27T14:20Z). I1 park-dose is closed for further patches; next path is non-park long-hold `D` measure. Still REFUSE I1 / TRAINING until a real path holds (claim0+falsifier1).
