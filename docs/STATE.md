# Verified state, and what is not verified

## Path to training (Ruggero 2026-11-27g — keep this list true)
1. **DONE** (2026-11-28): critic ruled the PR-B diff (6bb5bcd) and the engineer committed the staged work (c36795e).
2. **CURRENT BLOCKER** (owner: nid-engineer): **outcome source = verified room index; scripted play still ends no round.** The alive-flag death source is invalid (`FLAG_P1/P2` = `nidspy.zig:225` `inRange()`, a bounds check that never drops, L28). Round boundaries now come from the verified room index (`ROOM_OFF`; `state/round_source_proof_20261128T062640Z.json`, `mem_room == spy_room == 29`) via `outcome_events.round_boundary`: arena→different arena = advance, arena→`rMatchStats`(20) = match end, anything through a menu/lobby room = re-entry navigation, not a round. A **real match end was produced and recorded**: `state/round_outcome_proof_20261128T114017Z.json` — `room_start 29`, `room_end 20`, via the game's own forfeit sequence (claim `state/_claim_room_rounds.sh` rc=0 / `state/_falsify_room_rounds.sh` rc=1). `smoke20` is wired to this source (`room_rounds`), but a rerun (`results/runs/smoke20_20261128T114701Z.jsonl`, 2/4 entered) recorded 0 in-play round ends: the mirror policy never ends a round, and holding right for 150 s ended none either (L31). The winner/kill field stays dropped until a reproducible kill. **Next: a policy or opponent that ends a round in play (kill, then advance to the goal), not another outcome-variable patch.** P2 action keys remain **cut**.
3. One short end-to-end training smoke test: about 20 self-play episodes entered through `enter_match_v2`, with outcomes recorded. Blocked by step 2: `smoke20` records `room_rounds` from the room index now, but scripted self-play episodes end no round, so a run still records 0 played outcomes.
4. Open PR B to Pau (new branch from Pau `origin/main`; helper + test + short docs only).
5. Reward designs.
No new pre-checks or probes outside these five. A step that fails 3 times is cut down or done another way. "Nidhogg is working" means (a) a multiplayer-route training run is writing real outcomes, or (b) there is exactly one named blocker on this path, with an owner and a next action, less than 60 minutes old.

Every line here was measured on the real game. The second half lists the checks that are
**not** done, because knowing which claims are load-bearing matters more than the claims.

> **2026-11-27 farm integrity (read first):** I1 **SUPPORTED**. I2 **REFUSED** (pulse/continuous/block-hold; next = Critic plan balanced two-key). Fork goal: finish Pau's training setup → then reward designs. See state/mail/engineer.md.

> **Path blocker (2026-11-28T10:20Z, owner: nid-engineer): path step 2 CUT to the round counter.** `smoke20` is wired to `OutcomeTracker`; the 08:35Z rerun entered 19/20 but read 0 outcomes. Root cause: `FLAG_P1/P2` is `nidspy.zig:225` `inRange()`, a mapping-bounds check (`:353,355`), 1 for the whole match, so the debounced death (`outcome_events.py:60-70`) cannot fire. Confirmed live: `score_hunt_20261128T095632Z.json` watched 251 addresses for 150 s, `flags_seen [[1,1]]` every sample, no round ended. Cut (Orchestrator): step 2 = round counter only (room index); winner/kill dropped until a reproducible kill. Claim rc=0 / falsifier rc=1: `state/_claim_flags_constant.sh` / `state/_falsify_flags_constant.sh`. Path step 3 cannot pass until the round counter gives ≥1 event on a real round end.

## Multiplayer entry (Ruggero 2026-11-27d — write once)

**Canonical train entry** = game **MULTIPLAYER** local versus (policy vs policy / self-play), not TRAINING-vs-CPU.

| | |
|---|---|
| Function | `code_pau/nidstate.enter_match_v2(i)` (~58 s; PROVEN.md §1) |
| Menu path | title → Enter×3 → READY (both on pads) → stage select → Enter → live match |
| Body | `enter_ready` → park yellow/orange at wall∓0.333·W → stage select → Return → sleep 3s → `in_match` |
| P1 keys | a/d walk, w/s sword, f attack, g jump |
| P2 keys | arrow Left/Right (needed for self-play) |
| Not this | `train_state._try_entry` / SINGLE PLAYER → TRAINING / `run_entry` / partner_downs |

**2026-11-26 13:29Z** `train_win` "no fighters after entry sequence" was the **TRAINING** menu path (`_try_entry` n_lead/S cache), not multiplayer/`enter_match_v2`. Fixing train entry means wiring Pau's multiplayer route into the trainer, not more TRAINING variants.

## Verified by measurement

| Claim | Evidence |
|---|---|
| Keys control the fighter | Holding `A`: me_x 142 → 8. Holding `D` 20 s: 8 → 245 (+237 px, ~12 px/s) |
| Strikes land only at close range | At dx=22: CPU 246 → 297 (+51 px). At dx=59: 0 px in 15 s |
| Running alone cannot win | 120 s of holding right: start 114, peak 480, end 71 — pushed back |
| Entry lands in TRAINING (active CPU) | CPU moves 29–244 px while the agent does nothing; ARCADE shows 0 px |
| A Training match is one round | Accept presses never restart a round; re-entry per episode is required |
| State reads at ~40 Hz | 2,400+ samples per 60 s episode |
| The game runs at 47.7 fps at speed 180 | vs a throttled 23.8 fps before the latency-critical activity assertion |
| Console keys/values are exact | player positions correlate with visible gameplay; `A` moves left, `D` right |

## Current performance (honest)

* **Rounds won: 0.** In every run, to date.
* Rounds lost: 0 in most runs; 10 in the run where the agent was rewarded for closing
  distance (it rushed in and died).
* Best policy behaviour measured so far: `min_dx` 15–26 px (it does reach striking range)
  and `pushed` up to 3.00 (300 px of CPU displacement) — i.e. it can win exchanges
  occasionally, but not convert them into rounds.
* Fitness numbers (`best 12.13`, etc.) are a *designed reward*, not a win rate. They are not
  comparable across reward changes.

## Checks that have NOT been done (be appropriately paranoid here)

1. **Is the opponent really the CPU?** Entry goes through the Training menu, and the
   opponent moves on its own (29–244 px measured while we stand still), which a waiting
   room does not do. But we have never read the CPU's personality/difficulty setting back
   out of the game, so "it is the CPU" is inference, not proof.
2. **Are kills and deaths counted correctly?** No. `kills`/`deaths` are always 0 because
   death detection was never made reliable (see `docs/EXPERIMENTS.md`). Round outcomes are
   counted from goal-line crossings between consecutive samples, which caught a phantom
   10-win generation once and was then tightened — but it is still a heuristic.
3. **Is the agent improving?** Mixed. Behavioural metrics improve and then regress when the
   reward changes (min_dx 90 → 15–26 px is a real behavioural change). Win rate — the only
   metric that matters — has been 0 throughout, so "improving" cannot be claimed yet.
4. **Are the weights meaningful?** The population is diverse (12 nets, 5 distinct actions on
   a fixed observation, mean pairwise weight distance 30.3), but no analysis of what the
   trained weights encode has been done. That was planned as a later phase.
5. **Is the game fully decompiled?** No. We have the symbol table (142,869 symbols, 28,289
   `gml_*`), so scripts can be named and called, and `startMatch`'s one-int signature was
   recovered from its call site. We cannot yet read GML variables by name, and the room list
   is not recoverable from strings.

## Environment pitfalls that produced false conclusions

* The off-screen window is occluded and throttled to ~24 fps; screenshots can take minutes
  when the machine is loaded, which once made entry "hang for 18 minutes".
* The game's own `online.log` revealed that a recovery heuristic had walked into the online
  lobby — a failure that looked exactly like a broken key sequence.
* Stale game processes from Steam's re-exec chain inflated load to 19 and made timing
  assumptions fail intermittently.
* Files in `/tmp` persist across launches (`nid_state_*.txt`, `nid_inject_*.log`), which
  caused a readiness check to read previous runs' frame counters.
