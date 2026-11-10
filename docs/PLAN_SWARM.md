# SWARM PLAN — complete Pau's plan for the Nidhogg training interface

Source of truth for the facts below: `~/pau-tree/docs/TMP_CURRENT_STATE.md` (§2, §4, §7),
`docs/LAYOUT.md`, and `~/pau-tree/{nidlinux.py,nidstate.py}`. Everything in "GIVENS" is his
measurement, not ours. Do not re-derive a GIVEN; consume it.

## GIVENS (consume, never rediscover)

| fact | value |
|---|---|
| entry to a live match | `nidstate.enter_match_v2(i)` — MULTIPLAYER/local-2P, ~58 s, proven |
| P1 / P2 keys | `WASD` / `IJKL` — one harness drives both (self-play is free) |
| fighter record layout | stride `0x200`; `x@+0xEC`, `y@+0xF0`, `facing f32@+0xD8`, `anim u32@+0xBC`, `type u32@+0x88` |
| ground / pad y | `192` / `128` |
| **ORANGE (P2) score** | **`0xd5f57c8`** u32 — write 0/1/2 changes HUD bars |
| score copies (not displayed) | `0xf3c6368`, `0xf3c63e8`, `0xf3c6468` (stride `0x80`, region `0xece0000`) |
| HUD score rects | P1 `[56,14,80,30]`, P2 `[214,14,238,30]`, drawn only on READY |
| round boundary on demand | `Escape` → `Down, Down` → `Enter` → FORFEIT → YES (real Winner screen) |
| writes persist | `x += 300` does not snap back, does not crash |
| per-tick state file | `/tmp/nid_state_<pid>` 128 B, 61.4 samples/s, `n.track(pid,…)` + `n.state(pid)` |
| launch | `proton run`, **not** `waitforexitandrun` (blocks on `wineserver -w`) |
| roles | P1/P2 **SWAP** between rounds — never infer role from an address, re-prove by input |
| crash traps | non-integer score write kills the process; score write before wins cell allocated kills it |
| safe dirs | `/home/psoler/...` is readable (facts only — never write there) |

## HARD RULES for every lane

1. Use `~/pau-tree` modules. Do not write your own menu walker, spy, or launcher.
2. One worker = one instance = one display: `NIDFARM=~/.nidfarm-<lane>` with `NID_GAME_DIR=~/nidfarm/game`.
3. Every claim: `python3 tools/claim.py record "<text>" --cmd "<reproducible>" --falsifier "<what refutes it>"`.
4. A lane is DONE only when its acceptance test passes twice in a row on a fresh instance.
5. Never report a win rate. `rounds_won` is 0 until a verified round is won.

---

## WAVE 1 — four independent lanes (run simultaneously, one instance each)

### Lane A — the control gate (write-survival) — **blocks everything else**
*Pau's definition of "drivable": a write must survive into the simulation.*
1. `enter_match_v2(i)` → live match.
2. Read P1 `x`; `add(x, +200)` for ~300 ms; read back.
3. **PASS iff** read-back moved ≈200 **and** the sprite moved on the next frames. Attract demos cannot pass.
**Accept:** pass twice, on two fresh instances; record both deltas.
**Falsifier:** read-back drifts back to the original value, or sprite does not move.

### Lane B — round phase field
1. Use the forfeit trick to generate a boundary whenever you need one.
2. Poke the 2283 candidate slots **watching for BEHAVIOUR** (round ends, GO screen, HUD), not for a value change.
3. Narrow to a field whose value flips exactly at the boundary and whose poke can end/restart a round.
**Accept:** poking the field flips READY↔live visibly, twice.
**Falsifier:** a poke that changes only the number and never the behaviour.

### Lane C — YELLOW (P1) score
1. Mine only regions `0xd412000`/`0xece0000`, oracle = HUD rect `[56,14,80,30]` (P1 digit).
2. Integer writes only — a float kills the process.
**Accept:** write 0→1→2 and P1's HUD bars change correspondingly, twice, two processes.
**Falsifier:** HUD unchanged, or the write changes ORANGE's bars instead.

### Lane D — episode reset by writing x/y
1. In a live match, write both fighters' `x`/`y` to chosen values; verify the game continues sanely
   (no crash, no freeze, round still live, both fighters controllable after).
2. Time it: the goal is dropping the 58 s entry per episode.
**Accept:** 20 consecutive resets, 0 crashes, round still live after each.
**Falsifier:** any crash, freeze, or a round that silently ends on reset.

---

## WAVE 2 — depends on Wave 1 (starts when a lane closes)

### Lane E — round phase into the per-tick state file *(needs B)*
Extend `n.track(...)` to publish `phase` in `/tmp/nid_state_<pid>`; verify it flips at a forfeit boundary.
**Accept:** 10/10 boundaries visible in the state file with no screenshot.

### Lane F — reward signal *(needs A + C)*
Reward = Δ(ORANGE score) − Δ(YELLOW score) per round, plus shaped terms from `x`/`y` progress.
**Accept:** a scripted episode yields a non-zero reward trace with correct sign when we forfeit.

### Lane G — self-play driver *(needs A + D)*
One policy drives `WASD`, opponent policy drives `IJKL`; episodes reset via lane D.
**Accept:** 100 consecutive rounds with both policies acting, no crash, round outcomes recorded.
**Falsifier:** any round where neither fighter moves.

---

## WAVE 3 — training

### Lane H — trainer + throughput
Pick GA or PPO (Pau leaves the choice; the old repo has a GA), train against the scripted opponent first,
then self-play. Report **rounds won per hour** and nothing else until it beats the scripted opponent.

---

## Lane assignment (elastic — `tools/workers.py scale N`)

| worker | lane | needs game? |
|---|---|---|
| w-prober-1 | A (control gate) | yes |
| w-prober-2 | B (round phase) | yes |
| w-prober-3 | C (YELLOW score) | yes |
| w-prober-4 | D (episode reset) | yes |
| w-engineer | F/E wiring, docs | no |

Wave 1 wants **4 game lanes**, so `scale 5` (4 probers + 1 engineer) while the farm carries 4 instances
(Pau measured 15 instances = 43 cores, 33–48 fps each on his box; artemis has 384 cores). Drop to
`scale 1` the moment training starts.

## Definition of done for the whole plan

1. Lanes A–D closed with two-of-two acceptance.
2. `state/rounds.jsonl` has entries with `kind:"round"` produced by the driver, not by teleport counting.
3. A scripted episode produces reward traces with the correct sign.
4. Rounds won per hour is measured and recorded with a claim + falsifier.
5. Only then: any statement about beating anything.
