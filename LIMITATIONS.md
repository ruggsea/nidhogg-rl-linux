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

20. **No 4th fix of the same check.** After 3 failed fixes of one check, Critic must not ACK a 4th — choose a different way (Ruggero 2026-11-27T14:20Z). I1 park-dose remains closed for further patches.

21. **I1 identity path = long-hold D (no park).** Park-dose ladder closed (LIMITATION 20). Measure SUPPORTED 2026-11-27T14:35:08Z; formal hold is LIMITATION 22 (claim0+falsifier1).

22. **I1 held via long-hold D** (Critic 2026-11-27T14:39:57Z): claim0+falsifier1 on `i1_longhold_D_20261127T143129Z.json`. Park-dose path remains closed. No TRAINING until I2/I3 (and standing integrity) hold.

23. **I2 needs a balanced, wall-free sample.** A D-only or wall-bounce sample makes the majority baseline a one-class chance (T150012Z: n_ok=7, hit=0.5714=maj, margin=0) — nothing is shown. Accept an I2 sign map only on ≥50 usable windows per key, start x0≥300 px from both walls, |Δme_x|≥40 px, hit>0.55 over the balanced set (Critic 2026-11-27T15:03:06Z).

24. **Entry/nav wall-gate can fail on a stale instance.** Measured 2026-11-27T15:09Z: `i1_nav_ready…T150552Z` `nav_ok:false` (`wall:null, fv:false, yel:0, ora:2980`), 14 settle snaps unchanged, `enter_ready False` each; `game_pid 3553939` was the same frozen instance from the 14:59 run. I2 cannot run until entry reaches a fresh live round. Recorded as a setup gap, not a check (Critic 2026-11-27T15:26:27Z).

## Pre-training code gaps (Critic adversarial read, 2026-11-27T19:27Z)

Found while waiting, in the code we would run experiments on. Fix before any >1-generation run; each fix needs a claim.

25. **Linux action map drops attack and jump.** `train_state.press` `_map` (`train_state.py:682-684`) maps 65/68/83/87 and arrows but not **70 (F, attack)** or **71 (G, jump)**; `act` returns both (`:1471`, `:1475`). Unmapped codes are written to `/tmp/nid_keys_*.txt`, which the code's own comment says Linux does not consume (`:679-680`). Therefore the policy's attack and jump never reach the game; the train loop only moves. This alone makes any kill/reward result untrustworthy.
26. **Reward shaping can outweigh kills, untested (I4 missing).** `fitness = 3*theirs - 2*mine + advance/100 + approach/40` (`train_state.py:1609`). `advance`/`approach` are pixel sums over a 25 s episode; a few hundred px equals a kill (3.0) and exceeds a death (2.0). No I4 claim tests the terms, so a policy that walks forward without killing can score. Do not read fitness as "wins" until each term has an I4 claim.
27. **Crashed episodes can enter the gene pool / become BEST (violates I3).** `failed_record` has fitness `-100` (`train_state.py:1622`); `main()` takes `elite = results[:max(2, pop//3)]` (`:1687`) and updates `best` from `generation_best` (`:1697`). With pop=8 and ≥2 failed episodes, the elite is two crash records, and an all-fail generation makes `best` a `-100` failed record. Inert/no-match must never be BEST (I3).
28. **Death detection is an unverified heuristic.** A single-fighter x-jump > `SPAWN_JUMP` counts as a death, both-jump as a round end (`train_state.py:1570-1582`). A fast dash or camera pan can fake a death; an asymmetric round respawn can count one. No event-tied I4 check yet.
29. **Two identity sources, not reconciled.** The bridge writes P1/P2 from memory flags into `/tmp/nid_state_0.txt` (`tools/nid_state_bridge.py:19`); the control path binds the responding instance by key (`train_state.py:952 bind_by_response`). `read_state` (`train_state.py:448`) uses the bridge file without checking the bound instance. If flag-P1 differs from the key-responding instance, me/them and the reward sign invert — the exact I2 premise. Reconcile or gate before trusting any me/them number.
