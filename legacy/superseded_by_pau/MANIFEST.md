# Superseded by Pau's stack (`~/pau-tree`)

These were our own Linux-side reimplementations. Pau had already proven the same things, better, and
every "bind failed / gate failed" report during 2026-11-09 came from debugging our copies of his work.
Kept here for reference, not used by any live path.

| our file | replaced by (pau-tree) |
|---|---|
| `nid_linux.py` | `nidlinux.py` — env-configurable (`NID_GAME_DIR`, `NID_PROTON`, `NIDFARM`), Zig spy, `proton run`, per-tick state file |
| `linux_state.py` | `nidstate.py` + `nidlinux.track()/state()` |
| `attest_linux.py` | his write-survival gate: `add(x,+200)` must persist into the simulation |
| `menu_rows_linux.py`, `menu_dot_linux.py` | `nidstate.ensure_menu()` / `enter_match_v2()` |
| `enter_match_linux.py`, `enter_training_linux.py` | `nidstate.enter_match_v2()` — 58 s, proven, local 2P |
| `drive_round_linux.py`, `rounds_monitor.py` | forfeit boundary: `Escape` → `Down, Down` → `Enter` → FORFEIT → YES |
| `bind_measure.py` | `nidlinux` track + read-back, and the write-survival gate |

## Still open in his list (§7), so not superseded — revisit with his tooling

* room / substage id (no field located yet)
* round phase in memory
* YELLOW score address
* sword position in the per-tick state file

## Kept from our side, because Pau has no equivalent

* `tools/workers.py` — elastic parallel worker pool (scale N, per-role, compaction)
* `tools/milestones.py` — milestone-only email (no routine noise)
* `tools/claim.py` — claims with a required falsifier
* `tools/plan.py`, `keeper_artemis.sh`, `loop_artemis.sh`, `start_agent.sh`
