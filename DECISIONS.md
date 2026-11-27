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

## 2026-11-27T09:56:17Z — I1 dose prep: A-first park me≤500; short D; too_right=500 (v5l)

- **Chosen:** Prep parks with **A-first** (face left) when me>500; face-right **only after** park. Refuse dose on `prep_fail`. `drive_ok` rejects teleport-sized |dme| (`max_abs`). Dose path: short D drive_ok (~0.28s) → **re-park me≤500** → hold-right. `too_right_after_drive` gate **500** (was 700). Probe tag **v5l**.
- **Alternatives:** Keep face-D-then-A; keep long 0.9s D probe before dose; keep too_right gate 700.
- **Why:** T013029Z: face-D-then-A → A_no_drive/still_too_right (me≳500); drive_ok(D,0.9s) overshot 127→655 then dose me0=655→183 dme=−472.
- **Decided by:** Critic ACK v5l 2026-11-27T09:56:17Z (plan 02:00 / eng 09:54).
- **Change if:** measured dose_ok with a different park/facing order under claim+falsifier.
- **Evidence:** `i1_probe_20261127T013029Z.log` / `i1_probe.json` (v5k dose_ok=false); `i1_dosefix_v5l.diff` (7620 B, md5 4c357823…); engineer.md 02:00–09:56.

## 2026-11-27T10:37:44Z — I1 dose prep: A-probe advisory; park ≪500; D max_abs=700 (v5m)

- **Chosen:** A-probe fail does **not** abort prep — always run pull+corridor. Park target ≪500 (`max_x−180`). `drive_ok` separates hard_tele / soft_tele / wrong_sign. Pre-dose D uses max_abs **700** (was 280). Probe tag **v5m**.
- **Alternatives:** Keep A-probe hard-refuse; keep max_abs=280 on short D.
- **Why:** T100338Z: A_no_drive returned False before pull → prep_fail me≳780; N20 +dme≈386 soft-tele → no_drive.
- **Decided by:** Critic ACK v5m 2026-11-27T10:37:44Z (plan 10:33 / eng 10:35).
- **Change if:** measured dose_ok with a stricter tele cap that still accepts real short-D walks.
- **Evidence:** `i1_probe_20261127T100338Z.log` / `i1_probe.json` (v5l dose_ok=false); `i1_dosefix_v5m.diff` (6951 B); engineer.md 10:33–10:35.

## 2026-11-27T11:27:50Z — I1 dose prep: refuse me≈0; re-face D + verify drive (v5n)

- **Chosen:** `valid_x` rejects `|x|<5` (dead/unbound). After park: re-face D, verify D→+dme (one retry), re-park ≤500 before dose. Dead me mid-prep → prep_fail. Probe tag **v5n**.
- **Alternatives:** Trust face after A-park; treat me_x≈0 as valid.
- **Why:** T104147Z: park≈322/15 but drive_ok(D) dme=0; x0=0 reads; N20 prep_fail null.
- **Decided by:** Critic ACK v5n 2026-11-27T11:27:50Z (plan 11:22 / eng 11:24).
- **Change if:** measured dose_ok without post-park D verify under claim+falsifier.
- **Evidence:** `i1_probe_20261127T104147Z.log` / `i1_probe.json` (v5m dose_ok=false); `i1_dosefix_v5n.diff` (3396 B); engineer.md 11:22–11:24.

## 2026-11-27T12:08:04Z — I1 dose prep: rebind after A-park; long face-D verify (v5o)

- **Chosen:** After A-park, **rebind** then face-D **0.45s** + D→+dme verify hold **0.55s**. On dme=0: rebind+repark+longer face-D (not A/D face-flip). Probe tag **v5o**.
- **Alternatives:** Keep short 0.20s face + A/D flip retry (v5n).
- **Why:** T113232Z: park≈301–322 then drive_ok(D) dme=0 (`D_no_drive_after_park`); face-flip jumped 301→1216 (bind dead/flipped).
- **Decided by:** Critic ACK v5o 2026-11-27T12:08:04Z (plan 12:04 / eng 12:06).
- **Change if:** measured dose_ok without post-park rebind under claim+falsifier.
- **Evidence:** `i1_probe_20261127T113232Z.log` / `i1_probe.json` (v5n dose_ok=false); `i1_dosefix_v5o.diff` (4714 B); engineer.md 12:04–12:06.

## 2026-11-27T12:17:39Z — enter_match_v2: poll in_match after Return; accept live if not READY (entryfix_v5o)

- **Chosen:** After stage-select Return, poll `in_match` up to **~7.5s** (not single 3.0s sleep). If `enter_ready` fails but `in_match` → return True. Final `in_match` check after attempts exhausted.
- **Alternatives:** Keep fixed 3.0s sleep; return False on any enter_ready fail.
- **Why:** T121159Z: stage-select-during-park → Return → 3s miss → “not on READY” while already live/transitioning → enter_or_in_match_false (entry False in_match True).
- **Decided by:** Critic ACK entryfix_v5o 2026-11-27T12:17:39Z (plan 12:15 / eng 12:16).
- **Change if:** measured enter_match_v2 always sees in_match within 3s under claim+falsifier.
- **Evidence:** `i1_probe_20261127T121159Z.log` / `i1_probe.json` (fail=enter_or_in_match_false); `i1_entryfix_v5o.diff` (1963 B); engineer.md 12:15–12:16.

## 2026-11-27T12:54:06Z — I1 dose prep: short D-verify; hard repark ≤500 (v5p)

- **Chosen:** D-verify hold **~0.18s** with max_abs **160** (prove +dme without tele). `_hard_repark` to me≤500 after rebind and after verify. Rebind-before-verify must succeed or abort clean (no long retry hold). Probe tag **v5p**.
- **Alternatives:** Keep 0.55–0.70s D verify with max_abs 700 (v5o).
- **Why:** T122037Z: long D-verify → soft_tele +718 / hard_tele +1012 as D_no_drive; post-verify park left me≳800; rebind_after_park_failed.
- **Decided by:** Critic ACK v5p 2026-11-27T12:54:06Z (plan 12:50 / eng 12:51).
- **Change if:** measured dose_ok with a longer verify that still avoids tele under claim+falsifier.
- **Evidence:** `i1_probe_20261127T122037Z.log` / `i1_probe.json` (v5o dose_ok=false); `i1_dosefix_v5p.diff` (5877 B); engineer.md 12:50–12:51.

## 2026-11-27T13:42:28Z — I1 dose prep: prove A-response; face-D longer then repark; tap-D confirm (v5q)

- **Chosen:** Before D-verify, prove bound responds via A (-dme). Face-D **0.55s** (no walk commit) then `_hard_repark` if me>500; tap-D confirm hold **0.22s** max_abs **180**. Retry reuses full `_face_d_verify`. Probe tag **v5q**.
- **Alternatives:** Keep v5p short face 0.22 + D-verify 0.18 only (left dme=0 at park≤500).
- **Why:** T125707Z: after park me≲500, short D-verify → dme=0 (facing/bind dead, not tele); N5 park≈792 / N10 592 / N20 320 prep_fail.
- **Decided by:** Critic ACK v5q 2026-11-27T13:42:28Z (plan 13:37 / eng 13:38).
- **Change if:** measured dose_ok without pre-dose A-prove under claim+falsifier.
- **Evidence:** `i1_probe_20261127T125707Z.log` / `i1_probe.json` (v5p dose_ok=false); `i1_dosefix_v5q.diff` (4582 B md5 5132c92d); engineer.md 13:37–13:38.

## 2026-11-27T14:21:39Z — I1: stop park-dose patches; try long-hold D without parking (Ruggero B)

- **Chosen:** After ≥3 failed ACKed fixes of the same I1 park/dose check (v5o/v5p/v5q; ≥16 tries 0 pass), **do not ACK a 4th** park-dose patch. Next proof path: measure long-hold `D` fighter-identity on Pau `enter_match_v2` **without** park≤500 / N-dose ladder (anchor: STATE.md Holding D 20s 8→245).
- **Alternatives:** Keep iterating park-dose v5r+; abandon I1.
- **Why:** Ruggero steer B 2026-11-27T14:20Z — same check patched out; different way required. v5q T134804Z EXIT dose_ok=false (N5/10/20 prep_fail).
- **Decided by:** Critic 2026-11-27T14:21:39Z under orch/Ruggero B.
- **Change if:** a non-park measure fails to show control and a *different* (non-park) check is proposed.
- **Evidence:** `i1_probe_v5q_T134804Z.json` / `i1_probe_20261127T134804Z.log`; docs/STATE.md keys-control row; engineer.md Critic plan 2026-11-27T14:21:39Z.

## 2026-11-27T14:20Z — Stop park/dose patching after v5q; long-hold path next (Ruggero steer B)

- **Chosen:** After live v5q EXIT, no further ACK of park/dose prep patches for I1. Critic rule: after 3 failed fixes of the same check, refuse a 4th; require a different measurement. First alternative: docs/STATE.md long-hold D (x 8→245 in 20 s) as fighter-identity without parking.
- **Why:** ≥16 park/dose tries, 0 dose_ok; failing step is parking, not memory read.
- **Also:** Mac rewrite of train_state/train_win/evaluate committed on `wip/mac-rewrite` (pushed to fork); `code_pau/` imported from pippi into git.
- **Decided by:** Ruggero steer B 2026-11-27 via orchestrator.
