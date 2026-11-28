# Verified state, and what is not verified

## Path to training (Ruggero 2026-11-27g — keep this list true)
1. Critic rules on the PR-B diff; then the engineer commits the staged work.
2. Player-2 keys plus the round and outcome fields (kills and deaths are still always 0, so no reward can be computed).
3. One short end-to-end training smoke test: about 20 self-play episodes entered through `enter_match_v2`, with outcomes recorded. This is the check that says the setup is finished.
4. Open PR B to Pau (new branch from Pau `origin/main`; helper + test + short docs only).
5. Reward designs.
No new pre-checks or probes outside these five. A step that fails 3 times is cut down or done another way. "Nidhogg is working" means (a) a multiplayer-route training run is writing real outcomes, or (b) there is exactly one named blocker on this path, with an owner and a next action, less than 60 minutes old.

Every line here was measured on the real game. The second half lists the checks that are
**not** done, because knowing which claims are load-bearing matters more than the claims.

> **2026-11-27 farm integrity (read first):** I1 **SUPPORTED**. I2 **REFUSED** (pulse/continuous/block-hold; next = Critic plan balanced two-key). Fork goal: finish Pau's training setup → then reward designs. See state/mail/engineer.md.

> **Path blocker (2026-11-28T03:09Z, owner: nid-engineer): path step 2** — P2 action keys and the event-tied round/outcome fields are still missing. The 02:12Z `smoke20` run (20 episodes, `results/runs/smoke20_20261128T021210Z.jsonl`) entered multiplayer in 19/20 (`entry=True entered=True`; ep15 `entered=False`: READY park incomplete, fighters bound but spy published no sample), but read no outcome: `who=None` 20/20, `kills=0`, `deaths=0`, `round_counter=0`. Next action: (a) wire P2 attack/jump/crouch through `train_state.press` and prove they move `p2_y` (Critic plan 21:12Z step 1); (b) read kills/deaths and the round counter event-tied in `nid_state_bridge.py` (step 2). Each needs a claim+falsifier. Path step 3 (this smoke test) cannot pass until they do.

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
