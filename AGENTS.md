# AGENTS.md — nidhogg-pau (project-local, deliberately short)

You are the **operator** for this project. Read `state/plan.json` (via `python3 tools/plan.py show`) and
work the next open step. The engineer session builds the harness; it does not drive the game.

## The one thing that matters

Train an agent that beats the CPU in the **real, locally installed** macOS Nidhogg. No simulator, no
computer vision for state (memory reads only). Keep the game off the user's screen, muted via the game's
own prefs, one instance.

## Own the game before touching it

    python3 tools/gameslot.py acquire operator --ttl 7200     # before launch/keys
    python3 tools/gameslot.py release                          # when you stop

If it says BUSY, someone else owns the game. Do not fight it.

## Tools that already exist — use them, do not rewrite them

| command | purpose |
|---|---|
| `python3 tools/plan.py show / next / done / block` | the plan; `done` requires evidence |
| `python3 tools/doctor.py --gate` | environment health; refuses on WARN/FAIL |
| `python3 tools/attest.py` | proves the path is real: room -> bind by response -> control gate -> opponent |
| `python3 game.py status/enter/state/do/rounds/shot` | one choke point for driving the game |
| `python3 tools/claim.py record/verify/fixtures` | every number you report needs `--cmd` and `--falsifier` |
| `python3 tools/mailbox.py check --as operator` | messages from the engineer; reply with `post --to engineer` |

## Facts already established (do NOT re-derive)

`state/facts.json` holds them with provenance: room table (`2 rMainMenu`, `3 rMultiMenu`, `17 rLevelSelect`,
`26-77` arenas), the menu scrolling under a fixed highlight bar (so selection is identified by the text
under the bar, not a coordinate), `_Current_Room` being an int32 global, the player object index varying
by room (bind by response, never by name), and the launch env requirements.

## Rules that cost hours to learn

1. Never trust a motion-only liveness test: the title screen runs a **live attract demo inside an arena
   room**. Only "D moves us right AND A moves us left" distinguishes control.
2. Never press D/A outside an arena room: in menus they are slider input and inside OPTIONS they cycle
   the language.
3. Never press Enter on an unknown cursor: it selects whatever is highlighted.
4. Never write `/tmp/nid_room_<id>.txt` — it is a `room_goto` command (renamed to `nid_roomgoto`).
5. One game process. `nice 19` / background QoS measured 4x slower (30 fps vs 120).
6. Never report a win rate you have not measured. As of now `rounds_won` is 0 and **no round transition
   has ever been observed** — that is the measurement the project is for.

## Reporting

Results, not activity. Numbers with their command. Half a sentence for anything uncertain. The user
checks whether numbers survive scrutiny, not whether you were busy.
