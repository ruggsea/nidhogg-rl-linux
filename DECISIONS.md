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

## 2026-11-27T00:52:02Z — I1 bind: sync room-file + both parks + walk scale (v5k)

- **Chosen:** Before `InstanceManager.bind`, `sync_room_file` from nidmem + `wait_arena` so `/tmp/nid_room_now_%s.txt` matches live arena room. `enter_match_v2` must park **both** yellow and orange; `_walk_to_x` tol/steps/hold scale with frame width (320→640). Probe tag **v5k**.
- **Alternatives:** Trust stale room file; allow orange park=False; keep fixed 320-pixel walk params.
- **Why:** T004558Z: live room 29 (arena) but room file stale=2 → `in_arena=False` → refuse bind; orange park failed at fw=640 with unscaled tol.
- **Decided by:** Critic ACK v5k 2026-11-27T00:52:02Z (plan 00:48).
- **Change if:** `InstanceManager.in_arena` reads nidmem directly (no file) or a measured READY path never uses fw≠320.
- **Evidence:** `i1_bind_diag_20261127T005042Z.json`; `i1_bindfix_probe.diff` + `i1_bindfix_nidstate.diff`; Critic/engineer.md 00:48–00:52.

## 2026-11-27T00:56:36Z — No I1 probe without fresh NAV-DONE stamp

- **Chosen:** After a probe kill/abort, launch **no** I1 probe until a **new** `i1_nav_ready_*.json` exists with `nav_ok=true` (fv∧central∧on_ready + wall) and stamp **after** the Critic HARD line. Kill wall=None / in_match relaunches that skip NAV-DONE.
- **Alternatives:** Reuse prior READY stamp; rely on wall_gate alone from mid-match; relaunch immediately after SIGNAL 15.
- **Why:** T005307Z/T005521Z launched from in_match room29 with stale T004530Z nav → wall_gate fighters=True wall=None forever; wasted COUNT and false progress.
- **Decided by:** Critic HARD 2026-11-27T00:56:36Z (Orch STEER).
- **Change if:** measured proof wall_gate recovers central wall+on_ready from in_match without fresh READY-nav.
- **Evidence:** `i1_probe_20261127T005307Z.log`, `i1_probe_20261127T005521Z.log`; Critic/engineer.md 00:54–00:56.

## 2026-11-27T01:24:37Z — Orange park: stage-select = success; hold no /scale

- **Chosen:** `_walk_to_x` treats `on_stage_select` as success; hold = px/600 (no /scale), cap 0.50. `enter_match_v2` parks orange-first then yellow; accept stage-select during park; retry in-place while still READY (do not abandon for re-READY).
- **Alternatives:** Keep yellow-first + re-READY on orange=False; keep hold/=scale.
- **Why:** Diag fw=640: ora_x≈447 target≈533; hold scaled 0.071 halved steps; orange walk fires stage-select before centroid±tol → mask_lt20 False → re-READY lost screen (T010238Z enter_or_in_match_false).
- **Decided by:** Critic ACK 2026-11-27T01:24:37Z (plan 01:03 / eng 01:23).
- **Change if:** measured fw=640 park reaches centroid±tol without stage-select and dose path prefers that.
- **Evidence:** `i1_orange_park_diag_20261127T012259Z.json`; `i1_orange_park_fix.diff` (5716 B); engineer.md 01:23.
