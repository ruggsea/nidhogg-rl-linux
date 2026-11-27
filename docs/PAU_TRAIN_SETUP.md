# What Pau's training setup still needs — multiplayer (versus) survey

Written 2026-11-27 by engineer, on Critic plan 15:26:27Z (rule 7 fork goal (a)).
One inventory, no probe. Paths are on the farm (`pippi:~/nf-p/code_pau`), read this round.
Canonical entry is `nidstate.enter_match_v2` (STATE.md §Multiplayer entry), NOT `train_state._try_entry`.

For each line: **exists (file:line)** or **missing**.

## a. Entry / instance health

| item | state |
|---|---|
| Multiplayer entry recipe | **exists** `nidstate.enter_match_v2` `nidstate.py:1191` (READY → park wall∓0.333·W → hold ~1.5 s → stage select → `Return` → poll `in_match` ≤7.5 s). |
| READY detector | **exists** `enter_ready` `nidstate.py:824` (park both pads, eyes on pixels). |
| Wall detector | **exists** `_wall_x` (used at `nidstate.py:1209`); gate used by I-runs `tools/i1_fighter_identity.py:468`. |
| Instance restart on stuck screen | **missing.** `enter_match_v2` has no restart path: if `enter_ready` fails and `in_match` is false it returns `False` (`nidstate.py:1203`). |
| Reliability of ready/wall gate | **missing.** Latest failure: NAV `i1_nav_ready_20261127T150552Z.json` (`nav_ok:false wall:null fv:false ora:2980`, `enter_ready False` ×14, game_pid 3553939) and `i2_sign_dx_20261127T150912Z.log` **FAIL wall_gate**. Same pid as the 14:59 run: instance never restarted, stuck on an orange-flood screen. |
| What a fix needs | a pre-entry health gate (wall/`fv`/`central`) plus a relaunch of the instance when the gate fails, before `enter_match_v2` is called. `enter_match_v2` itself should stay the recipe, not carry restart logic. |

## b. P1 / P2 control map

| item | state |
|---|---|
| P1 walk keys | **exists** `P1_KEYS = ("a", "d")` `nidstate.py:764`. STATE.md: `a/d` walk, `w/s` sword, `f` attack, `g` jump. |
| P2 walk keys | **exists** `P2_KEYS = ("Left", "Right")` `nidstate.py:765` (comment: `i/j/k/l` do nothing). |
| P2 attack / jump / crouch keys | **missing** — never measured. Only Left/Right drive P2. |
| Key API | **exists** `nidlinux.key(i, keysym, hold=0.0)` `nidlinux.py:217` (`xdotool keydown`/`keyup`), `keydown`/`keyup` `:248`/`:253`; inside-game variant `:230`. |
| P2 injection point | **exists** `find_players_by_input` `nidstate.py:1116`: identifies P1 by `d`, P2 by `Right`, causal move-and-stop (not the attract demo). `tools/nid_state_bridge.py:64` binds both into `n.track`. |
| Self-play readiness | **partial** — P1 and P2 both drivable left/right; P2 has no attack/jump, so P2 cannot yet play a full policy. |

## c. Per-tick state for both fighters

| item | state |
|---|---|
| Reader | **exists** `tools/nid_state_bridge.py` (101 lines): tracks `fp['P1']`/`fp['P2']`, writes `/tmp/nid_state_0.txt` = `p2_x p2_y p1_x p1_y 1 1` and `/tmp/nid_insts_0.txt`; room via `ROOM_OFF`. |
| Consumer | **exists** `train_win.read_state` `train_win.py:186` (returns `them_x/y`, `me_x/y`, flags `have154/have242`); `read_raw` `:240`. |
| Fields read per tick | **exists** x, y for both (and flags), room. |
| Facing / sword / alive / round fields | **missing** from the published sample. Sword state exists in memory (arm `body+0x200`, sword `body+0x400`, noted `nidstate.py:544`) but is not read each tick; alive = flag flicker, no dedicated field; round is inferred from room only. |
| Does anything read P2 each tick? | **exists** — the bridge publishes P2 every tick; `train_state`/`train_win` currently use only `them_x/y` (P1 view) in `act`/`play`. |

## d. Round span (end → next without full re-entry)

| item | state |
|---|---|
| One round per match | **exists** (measured; STATE.md "A Training match is one round"). |
| Next round by `Enter` | **exists** `_accept_restart` `train_state.py:641` (Enter restarts ~0.4 s); `ensure_live_round` `train_state.py:1129` presses `13` until movement; `start_from_round_boundary` `train_state.py:1320`. |
| `ensure_match` orchestration | **exists** `train_state.py:1573` (cheap `_accept_restart` → `recover_match` → `run_entry`). |
| Versus equivalent of `train_win.room_change_round` | **partial** `train_win.py:119`: works from `ARENA_ROOMS` (26..77) and room-index direction; the T121159Z note (`nidstate.py:1195`) shows stage-select/Return returning while already live. Needs the same treatment wired to `enter_match_v2`, not `run_entry`. |
| Round counter / score read | **missing** — no confirmed round-score field in memory. |

## e. Round-outcome ground truth for reward

| item | state |
|---|---|
| Kills / deaths | **missing reliable.** Always 0 (STATE.md; `_at_edge` heuristic `train_win.py` ~:220, SPAWN_JUMP `:70`). Edge-teleport signature produced 485 false kills and was disabled. |
| Round win/loss | **partial heuristic** `room_change_round` `train_win.py:119` — only when room leaves/enters `ARENA_ROOMS`; a phantom 10-win generation was caught once, then tightened. |
| Event-tied reward (I4) | **missing** — no second source (round counter/score) is readable yet. |

## f. Train-loop swap (what the forbidden path owns today)

| item | state |
|---|---|
| Trainer imports | `train_win.py:22` `import train_state as TS`; `train_win.py:108` `import nidlinux as n` (local). **No `nidstate` import** in `train_win`/`train_state`. |
| Forbidden entry | **exists** `train_state._try_entry` `train_state.py:927` (SINGLE PLAYER → TRAINING → partner); `train_state.run_entry` `:1471`; `ensure_match` calls it `:1604`. |
| Trainer entry call sites to swap | `train_win.py:65` (global reset), `train_win.py:319` (`play` inert branch), `train_win.py:925` (main startup) — all `mgr.run_entry()`; plus `train_state.ensure_match` `:1573`→`:1604`. |
| What `enter_match_v2` must replace | every `run_entry()`/`_try_entry` call in `train_state`/`train_win` becomes a call into `nidstate.enter_match_v2` (needs `import nidstate` in `train_state`, and the bridge's P1/P2 tracking reused). |
| READY prime / drive gate in trainer | **exists** `prime_controls` `train_state.py:660`, `_drivable_now` `:1393` — these are entry-independent and can stay. |

## One paragraph, what is missing before >1 generation on versus

The multiplayer entry recipe exists and both fighters are memory-mapped, but three things are
missing: (1) a pre-entry instance health + relaunch gate, because the last two runs died on a
stale, orange-flood instance and `enter_match_v2` does not restart; (2) P2's attack/jump keys and
per-tick facing/sword/round fields, without which P2 cannot play a real policy and the reward has
no event source; (3) the train loop still enters through `run_entry`/`_try_entry` (TRAINING), so
`train_win`/`train_state` must call `enter_match_v2` instead. Items (1) and (3) are the blocking
ones for the fork goal; (2) is what self-play and I4 need after entry is reliable.