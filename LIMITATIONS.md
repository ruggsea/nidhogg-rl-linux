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
