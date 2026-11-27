# DECISIONS

Dated forks. Format: **Chosen / Alternatives / Why / Decided by / Change if / Evidence**.

---

## 2026-11-26 — Farm-only train; Mac is mirror

- **Chosen:** All game launch and training on pippi (`~/nf-p/pau86` + `code_pau` + `venv`). Mac holds git, claims, mail, docs.
- **Alternatives:** Train on Mac Steam build; dual Mac+Linux trainers.
- **Why:** Mac rewrite of train_state/train_win blocked (stash-or-keep); Linux farm already enters Training and runs PLAN15 diagnostics; Mac train invents a second broken path.
- **Decided by:** Ruggero / Orchestrator (mission_status + briefs 2026-11-26).
- **Change if:** stash-or-keep resolves and a measured Mac path matches farm under I1–I4.
- **Evidence:** `state/mail/mission_status.txt`, `state/mail/brief_pi_engineer.md`.

## 2026-11-26 — I1–I4 integrity hold before real training

- **Chosen:** No run with >1 generation accepted until I1–I4 claims+falsifiers hold and critic re-ran them. PLAN15 = 1-gen diagnostic only.
- **Alternatives:** Keep citing PLAN15 BESTs / plan06 “verified win” as progress.
- **Why:** Critic REFUSED inert BESTs, me/them swap (p2 g0i0), and plan06 frozen me_x with room flicker — fitness on untrusted memory is not a result.
- **Decided by:** Ruggero 16:41Z / Critic plan 16:44Z.
- **Change if:** I1–I4 SUPPORTED in engineer.md with claim+falsifier exit codes.
- **Evidence:** `docs/REPO_QUALITY.md` Q09/Q12; Critic plan in `state/mail/engineer.md`; `results/runs/plan15_p2_DIVEKICKER.log`.

## 2026-11 — Step-01 rescope (server/farm gate before scale)

- **Chosen:** Move compute to farm/server only after a falsifiable control gate; keep Mac as records.
- **Alternatives:** Scale Mac workers; jump rooms with `room_goto` for throughput.
- **Why:** Parallel workers without a shared gate multiply inconsistent “discoveries”; `room_goto` yields inert CPU.
- **Decided by:** project notes / plan step-01 history.
- **Change if:** gate (live AND drivable + I1 identity) holds under claim verify.
- **Evidence:** `docs/NEXT_STEPS.md` (historical), current hold in `plan.json` 02/03 open.

## 2026-11-26T19:21:34Z — Build only on Pau versus stack; shed TRAINING path for I1/train

- **Chosen:** I1–I4 and future training use `nidstate.enter_match_v2` (MULTIPLAYER local versus). Drop TRAINING/`run_entry`/partner_downs as the integrity and training entry.
- **Alternatives:** Keep dual stacks (TRAINING CPU curriculum + versus); treat PLAN15 as the train path.
- **Why:** Ruggero 19:20 — farm is versus; Pau's proven path is enter_match_v2. TRAINING I1 produced no_bind/wrong-mode confusion.
- **Decided by:** Ruggero (verbal) + Critic plan 2026-11-26T19:21:34Z.
- **Change if:** measured proof that TRAINING is required for a load-bearing claim Pau's versus cannot supply.
- **Evidence:** `docs/PROVEN.md` §1; Critic/engineer.md 2026-11-26T19:21:34Z; VNC versus observation.

## 2026-11-27T00:23:31Z — Align READY-nav with wall_gate; honest fail labels

- **Chosen:** `nav_ok ≡ ns._fighters_visible ∧ central _wall_x ∧ on_ready_screen`. yel/ora crumb counts are DIAG ONLY (must not pass nav_ok). Wall-gate fail labels: `no_fighters` when wall present + fighters False (not `wall_null`); `wall_not_central` / `wall_null` / `wall_gate_fail` as appropriate.
- **Alternatives:** Keep old nav yel/ora cols_ok as READY; keep mislabeling fighters=False+central wall as `wall_null`.
- **Why:** T001135Z nav json yel=25/fv=True lied vs shot re-score yel=0; T001147Z wall_gate had wall=159.5×15 but fail=wall_null because fighters=False — nav≠gate blocked dose path.
- **Decided by:** Critic ACK align 2026-11-27T00:23:31Z (plan 00:16 → 00:23).
- **Change if:** measured proof that `_fighters_visible` rejects a true READY screen that yel/ora correctly accept under enter_match_v2.
- **Evidence:** `i1_diag_detectors_20261127T001934Z.json`; farm `tools/i1_ready_nav.py` + `i1_align_gates_v5j.diff` (2023 B); Critic/engineer.md 00:16–00:23.
