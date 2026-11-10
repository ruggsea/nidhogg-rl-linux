# VERDICT — nidhogg-pau step 01 is blocked by a game bug (route exhausted)

**Date:** 2026-11-09 23:40 UTC
**Author:** worker 1 (engineer), with worker 2 (prober)
**Conclusion:** No route in the installed Nidhogg build (game_version 108, built 10/30/2026) reaches a
**live CPU match**. Step 01 (attestation against a live CPU) is blocked by a genuine **game bug**, not by
our harness, our navigation, or our measurement code. This stops the loop until a human decides between
the options below.

## What step 01 needs

`tools/attest.py` must print `VERDICT: ATTESTED` three times in a row, each with the dose-response check.
The current Linux attestation additionally requires `running` + `opponent` — i.e. a **drivable P1 and a
CPU opponent that plays on its own**. That is the exact thing build 108 cannot produce.

## The measured evidence (each with a claim)

| route | result | claim |
|---|---|---|
| TRAINING (`SINGLE PLAYER → TRAINING`) | crashes/exits at the difficulty→map transition | 641721dc, 61d315b2, 1efd1c92 |
| TRAINING map select (manual walk) | reachable (3-row → 11-row list via Right), but the pick crashes the game | 5f2dac2f, 085771a5, caa2c4ab |
| ARCADE (`SINGLE PLAYER → ARCADE`) | crashes on entry (black screen, game exits) | 5a8c8d76 |
| `-netai / -netbot / -netbotaggr / -netlevel cpu` | all land in rOnlineLobby ready-up; frozen "no Brain" opponent | 96741734, 39a6b779 |
| `-ltcontrols / -ltshow5 / -ltteams / -lttraining` | controls menu / non-CPU / training stall | d08d0bb9, bb5ae838 |
| 4-key short walk (w,Return,s,Return) | reaches an arena with a drivable P1 (D=73–88 / A=73–79) but a frozen opponent | fb99568e, 4d6e531a, 5f2dac2f |

The CPU's AI is a "Brain" assigned only by the `createBrainForPlayer`/`createBrainForFighter` path
(STRG 7997–8000, personalities `aiChar*`) — the training map-select pick. That path crashes. Every route
that skips it (short walk, -net*) reaches a match-shaped state with a **frozen opponent** (no Brain).

## What this is NOT

- Not the 320×200 window patch (unpatched 960×600 crashes identically — 1efd1c92).
- Not the LD_PRELOAD spy (no-spy launch crashes identically — 641721dc).
- Not drifted prefs (reset to pristine still crashes — 61d315b2).
- Not a navigation problem we can fix with more key-mapping (ARCADE crashes on entry, and the map-select
  pick itself crashes).

## Options for the operator / manager (outside this loop's scope)

1. **Game update** — check Steam (appid 94400) for a build newer than 10/30/2026 that fixes the
   training/arcade entry crash. This is the cheapest fix if one exists. Needs steamcmd credentials.
2. **Binary patch** — reverse the crash site and patch `createBrainForPlayer` / the TrainingMenu
   destroy-timing bug. Feasible only as a dedicated RE effort (YYC, no symbols) — not tick work.
3. **Re-scope step 01** — e.g. attest the drivable P1 + dose-response against the reachable frozen-
   opponent arena (or self-play), and treat "live CPU" as a separate milestone gated on the game fix.
   This changes the project's foundation and should be a deliberate decision.

## Where the project stands (unchanged, per the hard rules)

- `rounds_won` = 0. **No round transition has ever been observed.** No win rate exists or is reported.
- 0 generations trained. Nothing is trained yet.
- Steps 22, 23, 24 are closed (headless launcher, Linux interface, attestation on artemis). Step 01
  onward is blocked by the bug above.

## State artifacts to keep

- `state/attest_runs.log` — full attestation history (the early `0x1908eec` ATTESTED streak predates the
  `running`/`opponent` checks and was on the READY screen, not a live match).
- `state/probes/` — walk2.jsonl, walk_train_menu.jsonl, flag_test.jsonl, unpatched_lt.jsonl,
  arcade_walk.jsonl, and the localtest logs.
- Claims: `641721dc 61d315b2 1efd1c92 5a8c8d76 96741734 39a6b779 fb99568e 4d6e531a 5f2dac2f
  085771a5 caa2c4ab d08d0bb9 bb5ae838 da7c3d1a e3ceec91 63d51d58 23c6c331 20d838fe`.
