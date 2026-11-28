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

- **Chosen:** After ≥3 failed ACKed fixes of the same I1 park/dose check (v5o/v5p/v5q; ≥16 tries 0 dose_ok), **do not ACK a 4th** park-dose patch. Critic standing: after 3 failed fixes of one check, refuse a 4th — choose a different measurement. Next proof path: long-hold `D` fighter-identity on Pau `enter_match_v2` **without** park≤500 / N-dose ladder (anchor: STATE.md Holding D 20s 8→245).
- **Alternatives:** Keep iterating park-dose v5r+; abandon I1.
- **Why:** Ruggero steer B 2026-11-27T14:20Z — same check patched out; failing step is parking, not memory read. v5q T134804Z EXIT dose_ok=false (N5/10/20 prep_fail).
- **Also:** Mac rewrite of train_state/train_win/evaluate committed on `wip/mac-rewrite` (pushed to fork); `code_pau/` imported from pippi into git.
- **Decided by:** Critic 2026-11-27T14:21:39Z under orch/Ruggero B (steer stamped 14:20Z).
- **Change if:** a non-park measure fails to show control and a *different* (non-park) check is proposed.
- **Evidence:** `i1_probe_v5q_T134804Z.json` / `i1_probe_20261127T134804Z.log`; docs/STATE.md keys-control row; engineer.md Critic plan 2026-11-27T14:21:39Z.

## 2026-11-27T14:35:08Z — I1 fighter-identity via long-hold D (no parking)

- **Chosen:** Accept long-hold `D` (~20s) on Pau `enter_match_v2` **without** park/dose ladder as the fighter-identity proof path. T143129Z: x0=936.4→x1=1344 dme=+407.6.
- **Alternatives:** Keep iterating park-dose N=5/10/20 (closed by Ruggero B); require exact STATE endpoints 8→245.
- **Why:** ≥3 failed park-dose fixes; measure shows bound me +dme under D; STATE table already had long-hold D as keys-control evidence.
- **Decided by:** Critic SUPPORTED 2026-11-27T14:35:08Z (eng 14:32:55 / plan 14:21 steer B).
- **Change if:** claim+falsifier fail on re-run, or a later measure shows dme≈0 / wrong-sign under the same protocol.
- **Evidence:** `i1_longhold_D_20261127T143129Z.json` + `.log`; docs/STATE.md keys-control row; engineer.md 2026-11-27T14:35:08Z.

## 2026-11-27T14:39:57Z — I1 SUPPORTED via long-hold D claim+falsifier

- **Chosen:** Close I1 on long-hold `D` path: claim0 rc=0 + falsifier1 rc=1 on `i1_longhold_D_20261127T143129Z.json`.
- **Alternatives:** Keep I1 open pending park-dose (rejected); require STATE endpoints 8→245 exactly.
- **Why:** Own-print scripts pass; measure dme=+407.6 no_park on Pau enter_match_v2.
- **Decided by:** Critic 2026-11-27T14:39:57Z (eng hooks 14:36:40).
- **Change if:** claim/falsifier stop passing on re-run or json overwritten.
- **Evidence:** `state/_claim_i1_longhold.sh` / `_falsify_i1_longhold.sh`; json+log T143129Z; engineer.md 2026-11-27T14:39:57Z.

## 2026-11-27T14:56:00Z — I2 sign-dx: pulse fails + continuous-hold still hit≪majority

- **Chosen:** REFUSE I2 on pulsed sign-dx (`T144932Z`/`T145105Z` hit_me_x≈0.03 ≪ majority≈0.9) and on the different continuous-hold sample (`T145248Z` method=continuous_hold_sample hit_me_x=0.0231 ≪ maj=0.9444). Do not treat micro-step or 0.1s-sample sign prediction as held while dx≈0 dominates.
- **Alternatives:** Keep pulsing; claim on nonzero-dx-only subset; abandon I2.
- **Why:** Own-print farm jsons ok=false; I1 long-hold still moves (+dme) but step-sign prediction loses to majority-0. Standing: after identical fails, change measure — continuous was the change; it also failed.
- **Decided by:** Critic 2026-11-27T14:56:00Z (orch standards 14:55Z; eng 14:55:00).
- **Change if:** a later measure beats majority with claim0+falsifier1 on Pau enter_match_v2.
- **Evidence:** `i2_sign_dx_20261127T144932Z.json`, `…T145105Z.json`, `…T145248Z.json` (+logs); engineer.md 14:52–14:55.

## 2026-11-27T15:03:06Z — I2 refused on D-only block-hold; balanced wall-free measure chosen

- **Chosen:** REFUSE I2 on `T150012Z` block-hold (n_ok=7, A phase 0 usable, hit=0.5714=maj, margin=0) and on the earlier pulse/continuous fails. Next measure = **balanced two-key, wall-free net-sign block test**: start x0∈[400,1000], hold 1.5 s, settle 1.0 s, re-verify me each window, alternate D/A, count |Δme_x|≥40 px, need n_ok≥200 and ≥50/key, hit>0.55.
- **Alternatives:** repeat D-only block holds / 0.1 s sampling (closed); claim on the nonzero-D subset (rejected: one-class baseline, wall bounces give wrong sign).
- **Why:** D-only sample makes majority a one-class chance (4/7) so nothing is demonstrated; 3 of 7 D windows negative at the right wall (bounce), A windows unusable. A balanced two-key set puts majority at 0.5, so a real key→sign map must beat it.
- **Decided by:** Critic 2026-11-27T15:03:06Z (own-print of T145857Z log + T150012Z json).
- **Change if:** the balanced test cannot keep ≥50 A-windows usable after re-verify, in which case fix the A-phase validity (re-bind each window) before re-running, or switch to net Δme_x over a multi-second hold like I1.
- **Evidence:** `state/i2_sign_dx_20261127T150012Z.json` (md5 5c3edbdc… Mac≡farm) + `.log`; `…T145857Z.log`; engineer.md Critic 2026-11-27T15:03:06Z.

## 2026-11-27T15:05Z — Ruggero steer C: term map (rule 6) + Pau PR discipline (rule 4)

- **Chosen:** Map Ruggero's training terms from the repo (not guess): *multi-player route* / *Pau's routes* = `code_pau` `nidstate.enter_match_v2` MULTIPLAYER local versus (2P) per `docs/PROVEN.md` §1 and AGENTS.md; *memory checks* = I1–I4 claim+falsifier on that versus stack. TRAINING/`run_entry` is not the train path. Standing rules 1–6 written once into AGENTS.md + briefs.
- **Pau PR plan (draft for Ruggero — do not open until he picks):** fork `contrib/replication-and-protocol` is ~89 ahead / 94 behind Pau `main`; ~76 commits are mail/state-only ("Critic:…") and stay **fork-only**. Candidate future branches **from Pau `origin/main`** (new branches, no force-push): (A) thin notes PR — DECISIONS/LIMITATIONS lines that document I1 park-dose failure → long-hold versus path (docs only); (B) any future small code+test that lands a versus I1–I4 helper Pau does not already have; (C) Mac rewrite stays on fork `wip/mac-rewrite` unless Ruggero asks. `code_pau/` already exists on Pau main — do not re-PR the bulk import.
- **Why:** steer-2026-11-27c rules 4 and 6.
- **Change if:** Ruggero names different PR slices or clarifies terms.

## 2026-11-27T15:07Z — Ruggero steer D: fork goal + multiplayer route clarified

- **Chosen:** Fork goal order = finish Pau's training setup, then reward designs. *Multiplayer route* = enter via game MULTIPLAYER mode (`nidstate.enter_match_v2`) so policies face each other (self-play); always train through that route. Exact sequence written once in `docs/STATE.md` §Multiplayer entry. Standing rules 6–7 updated in AGENTS.md. Pre-training I1–I4 still apply; "unclear → no train" from steer C is lifted.
- **13:29Z note:** 2026-11-26 train_win pid 3636610 "no fighters after entry sequence" used **TRAINING** `_try_entry` (n_lead/S), not multiplayer — finishing setup includes wiring multiplayer entry into the trainer.
- **Why:** steer-2026-11-27d (Ruggero's words).
- **Change if:** Ruggero names a different self-play entry.

## 2026-11-27T15:08:14Z — Fork goal order (rule 7): finish Pau's multiplayer train setup, then reward designs

- **Chosen:** After the live balanced two-key I2 run reports, the engineer's next work is **`docs/PAU_TRAIN_SETUP.md`** — a setup inventory for self-play through `enter_match_v2` (entry freshness, P1/P2 control map + where injected, per-tick state for both fighters, round span/restart, round-outcome truth, train-loop swap off the forbidden TRAINING path). No probe, no new check. Plan step 02 (round transition) then works off it.
- **Alternatives:** keep iterating I2 checks (rule 7 says no); jump straight to reward designs (order says setup first).
- **Why:** Ruggero steer C+D: canonical train entry = `enter_match_v2` multiplayer; the 13:29Z fail was TRAINING `_try_entry`, not multiplayer; when a check keeps failing ask what Pau's setup still needs.
- **Decided by:** Ruggero steer C+D relayed by Orchestrator 2026-11-27T15:07Z; Critic plan written 2026-11-27T15:08:14Z.
- **Change if:** the inventory shows multiplayer entry itself is broken (then fix entry first); or Ruggero reorders (a)/(b).
- **Evidence:** AGENTS.md standing rules 1–7; `docs/STATE.md` §Multiplayer entry; engineer.md Orchestrator 2026-11-27T15:07Z + Critic 2026-11-27T15:08:14Z.

## 2026-11-27T15:26:27Z — Balanced I2 blocked by entry/nav gate; move to the setup survey

- **Chosen:** Do not patch the wall/nav gate again (rule 7). Record it as a **missing piece of Pau's setup** and move to the survey **`docs/PAU_TRAIN_SETUP.md`**: entry/instance health first, then P1/P2 control map, per-tick state for both, round span, round-outcome truth, train-loop swap. I2 stays REFUSED/open until entry is reliable; no I2 re-run before that.
- **Alternatives:** a fourth wall/nav fix with its own claim+falsifier (rejected: same-check repetition, rule 7); repeat the balanced I2 run as-is (rejected: entry cannot reach a fresh instance).
- **Why:** Balanced I2 attempt `T150912Z` failed wall_gate (wall:null, fv:false, no json); NAV `T150552Z` `nav_ok:false` with `yel:0 ora:2980`, `enter_ready False` ×14, `game_pid 3553939` = the frozen 14:59 instance. Entry reliability is setup work (fork goal (a)), not a check to hammer.
- **Decided by:** Critic 2026-11-27T15:26:27Z (own-print of farm logs; orch 15:22Z facts).
- **Change if:** entry is shown reliable again on a fresh instance, then the balanced I2 run resumes.
- **Evidence:** `i2_sign_dx_20261127T150912Z.log` md5 8aa4158d…; `i1_nav_ready_20261127T150552Z.json` md5 5b3387f9…; engineer.md Critic 2026-11-27T15:26:27Z.

## 2026-11-27T19:27Z — Paranoid pre-training correctness read; fix LIMITATIONS 25–29 before >1 gen

- **Chosen:** While the engineer finishes PR B packaging, the Critic reads the vital training/architecture code directly (not summaries) and records gaps as LIMITATIONS 25–29. No >1-generation training run is accepted until the action map (25), reward terms (26), failed-record selection (27), death detection (28) and the identity reconciliation (29) are each fixed with a claim+falsifier. Kept as analysis only — no code touched.
- **Alternatives:** (a) run training now and read the code while it runs; (b) treat the swap/B proof as enough to proceed; (c) fix the code myself.
- **Why:** Ruggero's "very paranoid" standing order (2026-11-26T16:41Z) and steer h (idle agents do adversarial correctness review). Finding 25 is decisive: attack (70) and jump (71) are unmapped in `train_state.press`, so those actions go to a hook Linux does not consume, and any reward on kills is unearned. Findings 26–28 are exactly the I3/I4 failure modes the integrity hold exists for. The Critic does not edit code (brief), so the fixes are assigned to the engineer.
- **Decided by:** Critic (cs2) 2026-11-27T19:27Z, on the rule-9 upkeep assignment from Orchestrator 19:12Z.
- **Change if:** a later reading shows a mapping or path not seen here (then correct the limitation with the file:line).
- **Evidence:** `LIMITATIONS.md` 25–29; `code_pau/train_state.py:682-684,1471,1475,1609,1622,1687,1697,952`; `code_pau/tools/nid_state_bridge.py:19`.

## 2026-11-28T09:14:28Z — smoke20 wired to the event-tied tracker; the tracker's alive-flag source is invalid

- **Chosen:** Wire `code_pau/tools/smoke20.py` to `tools.outcome_events.OutcomeTracker` (the committed event-tied source): every sample feeds `(room, p1_alive, p2_alive)`, including samples where one flag is down, and the episode outcome (`who_won`, kills, deaths, round counter) is read from the tracker, not from x-jumps or `room_change_round`. Then rerun 20 self-play episodes. The rerun gave 19/20 entered, 0 event-tied outcomes (`results/runs/smoke20_20261128T083516Z.jsonl`).
- **Alternatives:** (a) keep smoke20's old flag-drop/teleport counting; (b) accept the 0-outcome run as just "no death happened" and rerun longer; (c) implement a real round/score read first.
- **Why:** The critic asked for ≥1 event-tied outcome through the tracker. Reading the tracker's source shows it cannot produce one: the "alive" flag is `nidspy.zig:225` `inRange()`, a mapping-bounds check, not a life signal; the flag is 1 for the whole match, so the debounced death at `outcome_events.py:60-70` never fires. Verified in code (`nidspy.zig:347-362`) and on the wire (flags `1 1`). Reporting a "wired" run with 0 outcomes without this would hide that the source itself is dead.
- **Decided by:** nid-engineer (pi), on the Orchestrator's 2026-11-28 next action; root cause read by the engineer.
- **Change if:** a real round/death/score variable is mapped and the tracker is repointed at it; then a rerun with ≥1 event-tied outcome is the test.
- **Evidence:** `code_pau/tools/smoke20.py` (tracker wiring); `code_pau/spy/nidspy.zig:225,347-362`; `code_pau/tools/outcome_events.py:60-78`; `results/runs/smoke20_20261128T083516Z.jsonl` + `_summary.json` (md5 4cc5c0a3…, ea655a81…); `LIMITATIONS.md` 28.

## 2026-11-28T09:39:15Z — the alive-flag death source is dead; read the game's named globals instead

- **Chosen:** Confirm the engineer's root cause — `FLAG_P1`/`FLAG_P2` is a mapping-bounds check, not a life signal, so the debounced death cannot fire — and repoint the death/round source at the game's own named GML globals `dead` (death) and `myroundswon`/`hisroundswon` (rounds won = score), or read the READY-screen HUD `WINS` digits. The room index stays as the round-boundary event.
- **Alternatives:** (a) keep the FLAG debounce and hope a death shows up; (b) go back to the x-jump/teleport heuristic; (c) declare a winner from room-index ordering.
- **Why:** Independently read the code: `inRange(t)` (`code_pau/spy/nidspy.zig:225`) returns `a != 0 and a + rec_end <= t.end and a % 4 == 0`, where `t.end = regionEnd(addr)` is fixed at track time (`nidspy.zig:303-313`); the publish sets `flag_p1`/`flag_p2` from it (`:347-361`). It is a static property of the configured address, so it is 1 for the whole match and cannot signal a death. Options (b) and (c) are the heuristics the integrity hold forbids (L28); (a) hides a dead source.
- **Decided by:** nid-critic (pi cs2), on the Orchestrator's 2026-11-28 review assignment; root cause first read by nid-engineer in commit 20eae6b.
- **Change if:** a Linux/Proton offset for `dead`/`myroundswon`/`hisroundswon` is mapped and a rerun shows an event-tied death/round; then a smoke rerun with ≥1 event-tied outcome is the test.
- **Evidence:** `code_pau/spy/nidspy.zig:225,303-313,347-361`; `code_pau/tools/outcome_events.py:60-78`; `code_pau/nidmem.py:34`; `code_pau/docs/archive/NOTES_macos.md:1702-1709,1730-1740`; `code_pau/docs/MEMORY.md:647-665`; `code_pau/docs/PLAN_SWARM.md:23`; `results/runs/smoke20_20261128T083516Z.jsonl`; `LIMITATIONS.md` 28.

## 2026-11-28T10:20:46Z — CUT: step 2 narrows to the round counter (drop the kill/death winner for now)

- **Chosen:** Cut path step 2 to the **round counter only**. The round boundary is the verified room index (`ROOM_OFF=0x1ace918`, spy score slot == direct read); the kill/death **winner** field is dropped from the minimal requirement until a reproducible kill exists. The invalid alive-flag death source (L28) is retired.
- **Alternatives:** (a) keep hunting `dead`/`myroundswon` with the spy `watch` — tried once (`code_pau/tools/score_hunt.py`, 150 s live, 251 addresses); (b) go back to x-jump/teleport heuristics; (c) read the READY HUD WINS digits now.
- **Why:** The hunt measured `flags_seen == [[1,1]]` for every sample and no round ending in 150 s of holding right, so no counter could be shown to step: there is no reproducible event to validate a death/score variable against. (b) is forbidden by the integrity hold. (c) needs a round already scored, so it is the follow-up, not the cut. This is the Orchestrator's stated fallback ("if this fails once more, cut step 2 to the round counter only and record the cut").
- **Decided by:** Orchestrator 2026-11-28 (relayed to nid-engineer); hunt executed by nid-engineer.
- **Change if:** a round end is produced (longer match or an active-press policy); then read `myroundswon` on that event or the READY HUD digits, and restore the winner field with a claim+falsifier.
- **Evidence:** `code_pau/tools/score_hunt.py`; `state/score_hunt_20261128T095632Z.json` (md5 `8d09eb10…`); `state/_claim_flags_constant.sh` rc=0 / `state/_falsify_flags_constant.sh` rc=1; `LIMITATIONS.md` 31; `results/runs/score_hunt_20261128T095632Z.json`.
- **Critic review (nid-critic, 2026-11-28T10:42Z):** accepted as a scope cut. Claim+falsifier re-run: `state/_claim_flags_constant.sh` rc=0, `state/_falsify_flags_constant.sh` rc=1; live `state/score_hunt_20261128T095632Z.json` md5 `8d09eb10…` == `results/runs/`. Two caveats recorded as `LIMITATIONS.md` 32: the score_hunt zero/step data is dominated by out-of-range watch slots (`spy/nidspy.zig:386-387`, `tools/score_hunt.py:159-162`), and no round end was produced, so neither the dropped winner nor the retained round counter was exercised by a real round. This cut does not by itself make path step 3 ("outcomes recorded") pass: it records round boundaries, not a winner.
