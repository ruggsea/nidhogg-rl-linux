# Superseded scripts (kept for provenance, not used)

Each of these was replaced by something narrower and tested. They are here rather than deleted so the
history stays auditable, but nothing in the live harness imports them.

| file | replaced by | why |
|---|---|---|
| `nav.py` | `nav3.py` + `game.py enter_training()` | blind key sequences; landed in OPTIONS and cycled the game language |
| `nav2.py` | `nav3.py` | tried to search the menu by room index; every main-menu item shares room 2, so it could not tell rows apart |
| `bind_player.py` | `game.bind()` | same response test, now inside the single choke point |
| `probe_restart.py` | `NOTES.md` session 132 | one-off measurement (Enter restores a round in 7.61 s) |
| `verify_cross.py` | `game.rounds()` | one-off watcher that never caught a crossing |
| `observe_rounds.py` | `game.rounds()` | same, plus it could not be run inside the loop |
| `pokehunt.py`, `hunt_live.py`, `hunt_paused.py`, `findstate.py` | `state/facts.json` + `game.py` | pre-gate memory hunting; every offset it found was later shown to be a view/draw artefact |
| `agent.py`, `agent_play.py` | `game.py` + `train_win.py` | early harness entry points |
| `plot_progress.py` | `report.py` | reported aggregates without recording evidence |

The live surface is: `game.py`, `train_state.py`, `train_win.py`, `neuro.py`, `nav3.py`, `adversary.py`,
`nidgate.py`, `report.py`, `check_runs.py`, `summarize.py`, `evaluate.py`, `analyze_vars.py`,
`keysweep.py`, `video_*.py`, plus `tools/` and `.pi/`.
