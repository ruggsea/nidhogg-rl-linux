# PROVEN.md — Pau's proven memory map & state machine (extracted)

Reference extracted from Pau's tree at `~/pau-tree/`. Every claim cites **file:line** so the
other worker can audit against the source. Pau's own summary of what is sure vs guessed lives in
`docs/LAYOUT.md`; the raw lab provenance is `docs/workers/overnight.json` and `docs/MEMORY.md`.

Source files (all under `~/pau-tree/`):

| path | role |
|---|---|
| `docs/TMP_CURRENT_STATE.md` | snapshot: what we have / where / what's missing |
| `docs/LAYOUT.md` | memory map (proven vs inferred) |
| `docs/workers/overnight.json` | raw worker report — the score + forfeit proof |
| `nidstate.py` | code — `enter_match_v2()` |

---

## GIVENS — quick reference (consume, never re-derive)

Terse form of the proven facts below, for a compacted worker that must recover everything
without rediscovery. Corrections against `docs/PLAN_SWARM.md` are marked ⚠️.

| fact | value |
|---|---|
| live-match entry | `nidstate.enter_match_v2(i)` — MULTIPLAYER/local-2P, ~58 s, proven (§1) |
| P1 keys (yellow) | `a/d` walk, `w/s` sword, `f` attack, `g` jump (§1) |
| P2 keys (orange) | `Left/Right` arrows — ⚠️ **NOT `i/j/k/l`** (measured: "i/j/k/l do nothing") |
| fighter record | stride `0x200`; `x@+0xEC`, `y@+0xF0`, `facing f32@+0xD8`, `anim u32@+0xBC`, `type u32@+0x88` |
| ground / pad y | `192` (arena ground) / `128` (READY pads) |
| ORANGE (P2) score | `0xd5f57c8` u32 in Pau's env — ⚠️ **CONFIRMED REFUTED on artemis** (2-worker replay: write 0/1/2 → P2 rect orange px [4,4,4] and [92,92,92], no HUD change; build byte-identical). Lane C is re-mining the region (§2) |
| score copies (not displayed) | `0xf3c6368`, `0xf3c63e8`, `0xf3c6468` (stride `0x80`, region `0xece0000`) — ⚠️ read 2,2,2 at boot on artemis, so they are not tracking score=0 there |
| YELLOW (P1) score | **unknown** — NOT `0xd5f57c8 ± 4/8`; separate field (Lane C) |
| HUD score rects | P1 `[56,14,80,30]`, P2 `[214,14,238,30]`, drawn only on READY |
| round boundary on demand | `Escape` → `Down, Down` → `Enter` → FORFEIT → YES (§3) |
| writes persist | `x += 300` does not snap back, does not crash (→ episode reset is viable) |
| per-tick state file | `/tmp/nid_state_<pid>`, 128 B, 61.4 samples/s (§2b) |
| launch | `proton run`, **not** `waitforexitandrun` (blocks on `wineserver -w`) (§5) |
| roles | P1/P2 **SWAP** between rounds — re-prove by input, never cache (§4) |
| crash traps | non-integer score write kills the process; score write before the wins cell is allocated kills it (§2) |

---

## 1. Entry sequence + `enter_match_v2` signature

**Exact entry sequence** (`docs/TMP_CURRENT_STATE.md:58`):

> menu → `Enter×3` → READY → walk both onto pads (wall ± 0.333·W) → stage select → `Enter`

Full automated path is `nidstate.enter_match_v2()` (~58 s) — `docs/TMP_CURRENT_STATE.md:59`.

**Signature** (`nidstate.py:1171`):

```python
def enter_match_v2(i, verbose=True, stand=1.6, tries=2):
    """The measured recipe. Returns True only for a verified live match.

    READY -> park both at wall ∓ 0.333 W -> hold ~1.5 s -> stage select -> Return -> match.
    """
```

Body logic (from `nidstate.py:1171-1212`): `enter_ready(i)` → if `in_match(i)` return True →
`_wall_x(i)` → park **yellow** at `wall - 0.333·W` and **orange** at `wall + 0.333·W`
(`PAD_OFFSET_FRAC`) → poll up to `stand+1.8 s` for `on_stage_select(i)` → `n.key(i, "Return",
hold=0.12)` → `time.sleep(3.0)` (spawn + fall) → `in_match(i)` decides True/False. Returns False
on any failed attempt, retries `tries=2` times.

**Input keys** (`docs/LAYOUT.md:39-41`):
- P1: `a/d` walk, `w/s` sword position (low → mid → up → pre-throw), `f` attack, `g` jump.
- P1: `f` while in "pre-throw" throws the sword (player-supplied; NOT confirmed in memory).
- P2: arrow keys (`Right/Left` measured; `i/j/k/l` do nothing).

**Pad geometry** (`docs/LAYOUT.md:64`): READY pads at `y = 128`, positioned at wall ± 0.333·W,
firing band 0.28..0.42·W. Arena ground `y = 192`. Room widths seen: 320 (READY), 960, 1943 (castle).

---

## 2. Score address `0xd5f57c8` — and how it was proven

> ⚠️ **ADDRESS NOT REPRODUCING ON ARTEMIS (2026-11-10)**: `0xd5f57c8` is Pau's proven
> address, but on our artemis instance it does NOT drive the HUD. Lane C's clean on-READY
> test (claim 71474245): wrote u32 0→1→2, readback=2 confirms the write lands, but the P2
> rect orange px stayed [4,4,4] — no crash, no HUD change. **The build is byte-identical**
> (data.win 42969eea1ed383fb, Nidhogg.exe 5b87efafdd9f99e1), so this is NOT a build
> difference: the score global has moved in our launch env, or `0xd5f57c8` is a stale/copy
> address here. The forfeit DIRECTION is unchanged (yellow forfeit → ORANGE +1 bar).
> **CONFIRMED REFUTED on artemis by a 2-worker replay** (claim 71474245 + Lane R's own
> instance: orange px [4,4,4] and [92,92,92] across 0/1/2 writes, HUD unchanged, readback=2).
> Lane C is re-mining `0xd412000-0xdd10000` with the HUD rect as oracle; **treat
> `0xd5f57c8` as refuted-on-artemis, not merely unproven.** The proof below is Pau's, kept
> for the method (interval mining + poke + HUD oracle), which is what re-mining uses.

**Address / type** (`docs/TMP_CURRENT_STATE.md:51`):

> `0xd5f57c8`, region `0xd412000–0xdd10000`, **u32**. write 0 → tally blank, 1 → one bar,
> 2 → two bars; reproduced in two processes; same absolute address across processes
> (region base is not ASLR'd).

**Value encoding** (`docs/workers/overnight.json:50`): u32 integer (0,1,2); the HUD tally is drawn
directly from this value.

**How it was proven — the poke evidence** (`docs/workers/overnight.json:44-55`):
- Region base fixed across processes; found at the same absolute address in **two independent
  recordings** (`overnight.json:44-45`, processes `1885744` + `1979883` at `:72-74`).
- Recorded process 1885744 (score 2): write 0 → P2 digit rect 46 bar px → 2 px (blank);
  write 1 → 24 px / 1 bar; write 2 → 46 px / 2 bars; read-back confirmed every write, `ping ok`,
  restored 2 (`:52`).
- Second process 1979883 (score 1): baseline 24 px/1 bar; write 0 → 2 px (blank); write 1 → 24 px;
  ping ok, restored 1 (`:53`).
- Mined independently: the interval scan required `u32 == 0` in all 14 pre dumps, `== 1` in all 8
  score-1 dumps, `== 2` in the score-2 dump; 4 survivors, this one is the displayed value
  (`overnight.json:28-34`).

**Two hard caveats** (`docs/workers/overnight.json:76,161-162`):
1. **Not a static global**: `0xd5f57c8` is the wins cell only *once a round/match has been played*.
   At a brand-new READY with no round played, that offset belongs to another allocation — writing
   `u32 2` there **killed one process** (`:162`).
2. **Integers only**: writing `float 1.0f` (`0x3F800000`) killed the process within 0.5 s — the
   renderer indexes a glyph sprite/frame by the raw int; int writes 0/1/2/7/100 were all safe (`:161`).

**Cap** (`docs/TMP_CURRENT_STATE.md:89`, `overnight.json:54,71`): writing 7 or 100 draws the same
bars as 2 — the READY tally is "one bar per win, capped by rounds already played"; no distinct >2
glyph exists by design.

**Copies that are NOT the score** (`docs/TMP_CURRENT_STATE.md:52`, `overnight.json:166`):
`0xf3c6368 / 0xf3c63e8 / 0xf3c6468` (0x80 stride, region `0xece0000`) track 0→1→2 but poking them
never changes the HUD.

**YELLOW (P1) score is NOT at `+4`/`+8`** (`overnight.json:167`): adjacent candidates
`0xd5f57cc`(+4) and `0xd5f57d0`(+8) do not drive the YELLOW rect; the P1 counter stayed 0 through
the session so the 0→1 interval signature could not see it. The two scores are *separate* fields,
not an adjacent pair (`docs/TMP_CURRENT_STATE.md:85-86`).

---

## 2b. Per-tick state file (the Wave-2 substrate)

Pau's spy pushes one 128-byte struct per game tick to `/tmp/nid_state_<pid>`
(`n.track(pid, p1, p2, score, tick)` starts it, `n.state(pid)` reads it). Measured
61.4 samples/s, 128 B, temp+rename. **The binary layout is fixed** — it is mirrored in
`nidlinux.STATE_FMT` and the spy's `Snapshot` (`~/pau-tree/spy/nidspy.zig`); change both
or neither.

```
STATE_FMT = "<IIQQIIfffIfffIII56s"     # 128 bytes, little-endian, no padding
magic u32 | version u32 | seq u64 | t_ns u64 | tick u32 | flags u32
p1_x f32, p1_y f32, p1_facing f32, p1_anim u32
p2_x f32, p2_y f32, p2_facing f32, p2_anim u32
score_orange u32, score_yellow u32, 56-byte reserved
flags: FLAG_P1=1, FLAG_P2=2, FLAG_SCORE=4, FLAG_TICK=8
```

`score_orange` is published **today** from `0xd5f57c8`. `score_yellow` has a reserved
slot in the struct but is **not populated** until Lane C finds the address and `track()`
is called with it — that is why Lane F's reward can be wired the moment Lane C closes.
The 56-byte reserved tail is where Lane E's `phase` field goes (see `wave2/phase.py`).

---

## 3. Forfeit round-boundary sequence

**The sequence** (`docs/TMP_CURRENT_STATE.md:60-61`):

> pause (`Escape`) → `Down, Down` → `Enter` → **FORFEIT → YES**. The round ends with a real
> *Winner* screen and the wins tally increments. **This is how we generate boundaries on demand
> now — no fencing required.**

**Precise provenance** (`docs/workers/overnight.json:16`):

> LOCAL match → live round → pause (Escape) → FORFEIT (2x Down+Return) → YES: the pause dialog
> says 'YELLOW FORFEITS?', the round ends immediately with an ORANGE 'Winner' screen
> (KILLS 1 / SUICIDES 0), ENTER CONTINUE returns to READY and the ORANGE WINS tally gains one bar.
> Repeated twice in one recording: 0 → 1 → 2.

Boundary times recorded at 100.9 s and 172.8 s in that session (`overnight.json:17-18`).

**Why forfeit, not a teleport write** (`overnight.json:168`): writing `x` into a live fighter body
(`+0xEC` / `+0xFC`) is overwritten within one tick — the game recomputes body position, so
teleporting a fighter to the goal with a plain write is impossible.

---

## 4. Role-swap warning

**The warning** (`docs/TMP_CURRENT_STATE.md:66`):

> **Roles (P1/P2) SWAP** — never infer role from an address; re-prove by input after every transition.

Same rule in the memory map (`docs/LAYOUT.md:56`):

> role stability | **roles swap**: never infer P1/P2 from address order; re-prove by input after transitions

**Related reallocation warning** (`docs/LAYOUT.md:24-25`): the `+0x200` (arm) / `+0x400` (sword)
offsets are **NOT stable** — the chain reallocates during play (arm slot disappeared and the sword
slid from +0x400 to +0x200 inside one session). Identify arm/sword by *type pointer* and
*behaviour*, never by offset arithmetic.

**Object layout to re-verify per bind** (`docs/LAYOUT.md:8-21`):

```
stride 0x200   x@+0xEC   y@+0xF0   facing f32@+0xD8   anim u32@+0xBC   type u32@+0x88
+0x200 arm   +0x400 sword   (both by type+behaviour, not offset)
```

---

## 5. `proton run` vs `waitforexitandrun`

**Pau's rule** (`docs/TMP_CURRENT_STATE.md:25`):

> GE-Proton 11-12; **`proton run`, not `waitforexitandrun`** (the latter blocks on `wineserver -w`);
> **Valve's original `steam_api64.dll`** — the Goldberg/gbe stubs hang `SteamAPI_Init`.

So: use `proton run` for launching the game, and the genuine Valve `steam_api64.dll` (not a
Goldberg/gbe emulator stub, which hangs `SteamAPI_Init`).

> ⚠️ **Discrepancy with our launcher**: our current artemis launcher
> (`loop/CONTINUE_ARTEMIS.md`) uses `proton waitforexitandrun`. Per Pau this is exactly the call
> that blocks on `wineserver -w`. The other worker should check whether our detached-launch
> flakiness ("no process, no log") traces to this.

---

## 6. What Pau lists as still missing

From `docs/TMP_CURRENT_STATE.md:94-102` (§4 "What is MISSING before training"), with the done-item
correction at `:164`:

1. **Round phase in memory** — needed to know *when* a round is live/over without screenshots
   (`:96`). Inferred only: 2283 u32 slots flip `0` (READY) → `1` (live) → `0` (READY), but poking
   the 15 clean candidates (8 at READY, 15 mid-round) produced **no behavioural change** —
   unproven (`docs/TMP_CURRENT_STATE.md:83-84`, `overnight.json:78-110`).
2. **YELLOW score** — needed for a symmetric reward/observation (`:97`). Not found: `+4`/`+8` from
   orange ruled out by poking (`docs/TMP_CURRENT_STATE.md:85-86`).
3. **Room/substage id** — needed to know when cached addresses are invalid (`:98`); human advanced
   two substages without ending the round, no field located (`:87`).
4. ~~Per-tick state file~~ — **done**, see §2.2 (`:99-100`, struck through at `:164`). Remaining:
   add sword position once the sword set is mapped, and round phase once found.
5. **Reset semantics in practice** — writes are kept (`x += 300` sticks, no crash), but nobody has
   yet built "reset an episode by writing x/y" and verified the game continues sanely; needed to
   drop the 58 s menu entry per episode (`:101-102`).

Also listed as **inferred, not proven** (`docs/TMP_CURRENT_STATE.md:81-92`): round phase, YELLOW
wins counter, room/substage id, and the score-cap rule.

**Immediate next steps, in order** (`docs/TMP_CURRENT_STATE.md:159-168`): (1) round phase via the
forfeit trick + behavioural poke; (2) YELLOW score by the same mining restricted to
`0xd412000`/`0xece0000` with HUD P1 rect `[56,14,80,30]` as oracle; (3) [done]; (4) episode reset
by writing both fighters' x/y; (5) only then pick a trainer and measure rounds won per hour.

---

## Cross-cutting traps (each cost a session) — `docs/TMP_CURRENT_STATE.md:136-153`

1. Never `pkill -f` — matches your own command line; use `pkill -x` or match `/proc/<pid>/environ`.
2. Never press keys while a human plays — identification presses `d/a/arrows` break "stops when
   released"; identify once in a controlled pause.
3. Identify early in a match — the 0x200 chain reallocates as the session runs.
4. A dump offset is meaningless without `regions.json`; low regions keep bases across processes,
   high ones are ASLR'd.
5. A flipping bit passes any single ±1 test — hunt needs several intervals, both directions.
6. Measure the measurement (a per-screenshot fps loop reports 1 fps on a 60 fps game).
7. `biggest_heap()` may be a zero-filled reservation (42 dumps of zeros).
8. Roles swap; offsets reallocate — re-prove rather than cache.
