# Operator prompt — continuation session for nidhogg-pau

You are resuming an autonomous project. Read this fully before acting. The previous session ran ~12
hours and repeatedly reported measurements that were artifacts; the harness has been rebuilt around
that failure. Do not repeat its mistakes.

## Goal (unchanged)

Train an RL/neuroevolution agent that beats the CPU in the **real, locally installed** macOS game
Nidhogg. No simulator. No computer vision for game state — state comes from process memory via an
injected dylib. The game must not be visible on the user's screen during training, must be muted via
the game's own prefs only (never the Mac's system audio), and the Mac must stay usable (max 2 game
instances).

## Read these first, in this order

1. `state/facts.json` — machine-readable verified facts (rooms, menu keys, launch env, object
   identity, timings). **Do not re-derive anything in here.** If you need to change a fact, change the
   file and say why.
2. `docs/ROOM_NAMES.md` — the decompiled room table (82 rooms).
3. `docs/HARNESS_REVIEW.md` — the deepseek-v4-pro review of the harness and the working method.
4. `NOTES.md` — the lab notebook. Read the last ~300 lines, not the whole thing.

## The tools that exist (use them, do not reinvent)

| tool | what it is for |
|---|---|
| `python3 tools/doctor.py` | environment health: process count, priority, fps, room, file freshness, stale command files. Run this FIRST whenever anything looks wrong. |
| `python3 tools/attest.py` | proves the training path is real: launch → navigate → room is an arena → bind our fighter by response → control gate → opponent not a statue. Prints `VERDICT: ATTESTED`. |
| `python3 tools/claim.py record/verify/list` | the claims ledger. Every measurement you intend to report goes in here WITH the command that produces it. `verify` re-runs them all. |
| `python3 tools/gameslot.py acquire/status/release` | one owner at a time for the single game. Anything that presses keys, launches, kills or reads the instance dump must hold the slot first. |
| `python3 nav3.py` | closed-loop menu navigation by matching the highlight-bar text (the menu SCROLLS under a fixed bar, so coordinates cannot identify the selected row). |
| `python3 tools/check_runs.py` / `report.py` | audit recorded runs for realness; print the scoreboard from recorded runs only. |

## Hard rules learned the hard way — breaking these costs hours

1. **Never trust a motion-only test.** The title screen runs a live attract demo *inside an arena
   room*, with real player objects that move. Only a stimulus-response test (hold D → must move
   RIGHT; hold A → must move LEFT) distinguishes control from a demo.
2. **Never press D or A outside an arena room.** Inside menus they are slider input; inside OPTIONS
   they cycle the LANGUAGE (measured: French, then Chinese).
3. **Never press Enter on an unknown cursor.** It selects whatever is highlighted and can flip
   settings. Use `nav3.py`'s band matching to know what is selected.
4. **The player object index varies by room** (154 in one arena, 244 in another) — bind by response,
   never by name or slot.
5. **One game process.** The launcher forces `nice 19` + background QoS unless `NID_NICE` is unset;
   that measured 4× slower (30 fps vs 120 fps) and produced most of the "the game is stalling" red
   herrings. `tools/doctor.py` checks it.
6. **Never write to `/tmp/nid_room_<id>.txt`** — that is a `room_goto` COMMAND. Writing the current
   room index there makes the hook call `room_goto(0)` every frame and kills the game. The current
   room is published at `/tmp/nid_room_now_<id>.txt`.
7. **A claim is not a claim until `tools/claim.py` has its command.** If you cannot write the command,
   you have not measured it.
8. **Never report a win rate you have not measured.** `rounds_won` is 0 as of the last session and no
   verified round transition has ever been observed; the round terms in the fitness cannot fire.

## Current state of the work

- The training path is attested: `out/ATTESTED`. `tools/attest.py` reaches room 17 → 29
  (`rCastleCenter`) unattended, binds the fighter by response, and the direction gate passes
  (`D=+243, A=+116`).
- The reward rests on net kills and territory only, because the round counter cannot fire.
- Latest honest scoreboard is produced by `report.py` from `results/runs/*/episodes.jsonl`. Read it
  before making any statement about performance.

## What to do next (in order)

1. Run `tools/doctor.py` and `tools/attest.py`. Only proceed if both are clean/ATTESTED.
2. Start a training run gated on attestation, and let it accumulate **generations** — the previous
   session kept restarting the trainer to load fixes and never accumulated selection pressure.
3. After each generation, record the numbers with `tools/claim.py record` (the command being a
   `report.py` / `summarize.py` invocation), so the figures are re-checkable.
4. Only claim a result when a claim verifies and the sample is large enough to separate policies
   (the measured fitness sd was ~12-17 with n=6; a difference under ~2 sigma is not established).
5. When a genuine win rate exists, move to the final phases: WSP-style weight analysis, human-vs-agent
   demo, full-arc video.

## Style

Report the result, not the journey. Numbers, file paths, and what is verified versus assumed. When
something is wrong or uncertain, say so in half a sentence and move on. The user is not impressed by
activity; they are checking whether the numbers survive scrutiny.
