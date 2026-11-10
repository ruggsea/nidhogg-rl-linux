# docs/INTERFACE.md — the contract (skeleton, to be filled)

**Provenance admits only `proven` / `inferred` / `unknown`.**
A field is `proven` only if the row names the *stimulus* that reveals it and the *oracle* that
confirmed it. Everything else stays `unknown`, however plausible it looks.

| # | field | source | stimulus | oracle | provenance |
|---|---|---|---|---|---|
| 1 | sword held / not held | `body+0x400` record | — | — | unknown |
| 2 | sword x, y (both players) | sibling `+0xEC`/`+0xF0` | — | — | inferred (layout only) |
| 3 | alive / dead | type group size < 2 | — | — | unknown |
| 4 | attack key | animation field `+0x58`/`+0x64` | — | — | unknown |
| 5 | crouch / roll | animation field | — | — | unknown |
| 6 | thrown sword (projectile) | new object type | — | — | unknown |
| 7 | facing | ±1 float / sprite flip | — | — | unknown |
| 8 | velocity | derived (Δx per tick) | none | — | unknown |
| 9 | stun / hit | animation field | — | — | unknown |
| 10 | round score | HUD pips / int that increments | — | — | unknown |
| 11 | round phase | READY / live / ended | — | — | unknown |
| 12 | round timer | counting int | — | — | unknown |
| 13 | which instance is us (P1/P2) | type group + start position | — | — | **proven** (READY, 8/8 d/a, ≤1.78 px) |
| 14 | tick / frame counter | monotone int | — | — | unknown |
| 15 | room / stage id | invalidates cached addresses | — | — | unknown |

## Phase 2 results (key sweep, macOS harness) — `results/keysweep_0.json`

Stimulus: hold one key 0.55 s. Oracle: the offset must move under that key and must NOT
move under a no-key control (control moved only `0xd0`, `0x2cc` — camera/timer bookkeeping,
discarded before attribution). One run, one live match (`have154=have242=1`).

| offset | stimulus | observed | sign check | provenance |
|---|---|---|---|---|
| `+0xEC` (mirror `+0xFC`) | `A` (65) | 113.5 -> 108.5 | decreases (left) | **proven**, mutual with `D` |
| `+0xEC` (mirror `+0xFC`) | `D` (68) | 108.5 -> 113.5 | increases (right) | **proven**, mutual with `A` |
| `+0xF0` (mirror `+0x100`) | `G` (71) | 560.0 -> 529.0 | y decreases = upward | **proven** (jump) |
| `+0xF0` (mirror `+0x100`) | `SPACE` (32) | 527.0 -> 545.0 | y increases = falling | **proven** (landing edge of same arc) |
| `+0x120`, `+0x128` | `A`/`D`/`F` | tracks x, offset -1.5/+1.5 | moves with x only | inferred: collision-box edges, not position |
| `+0x124`, `+0x12C` | `G`/`SPACE` | tracks y, offset -26/+0 | moves with y only | inferred: same box, vertical edges |

Rows 4/5/7/9 of the contract are **not** yet proven: `F` (attack), `W` and `S` produced no
attributable offset, and `SHIFT` did nothing. `F` moved x by +3.0 with no animation field
identified, which is consistent with an attack lunge but is not evidence of one — a single
sample with no discriminating oracle. Naming attack needs the animation field, which is the
next stimulus to hunt.

**Negative results, recorded because they are deliverables (Pau's rule 6):** `W` (87),
`S` (83) and `SHIFT` (16) change **no** offset in `0x80..0x2FF`. On this build jump is `G`,
not `W` — the tutorial says "PRESS G TO JUMP" — so `W`/`S` are not reachable actions here
and must not be in the action space.

## Proven facts this table rests on

```
record stride 0x200   x @ +0xEC   y @ +0xF0   type @ +0x88
duplicates            x @ +0xFC   y @ +0x100
siblings              sword = body + 0x400   arm = body + 0x200
```

Known instance (one run, one room — the type pointer changes per run):

```
type 0x174f900 → 0x191c400  x=8.0   y=128   P1 (yellow sprite 8.7 px)
                 0x191bc00  x=202.0 y=128   P2
```

## Control-side contract

| item | requirement | status |
|---|---|---|
| control gate | **read-only**: input direction control (A) + record tracks sprite 1:1 (B) + no other record does (C) | **proven** — `nidstate.control_gate`; attracts fail A (0.0 px), READY passes 12/12 with median 0.87 px error; evidence in `docs/gate/` |
| action→observation latency | ticks from held key to visible state | unknown |
| reset semantics | writing `x`/`y`: does physics snap back? | unknown |
| address stability | stable within a room; re-bind by type after a room change | inferred |
| writes | `poke`/`hold`/`add` work on some fields but have **killed the game twice**; not used by any gate | unsafe |
| death reallocation | do records move/allocate on death? | unknown |
| determinism | identical inputs from one reset → identical trajectory? | unknown |
