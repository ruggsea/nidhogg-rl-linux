# Docs index

Five documents, in the order you should read them. Everything else is archived under
`legacy/` — kept for provenance, not for reading.

| doc | answers |
|---|---|
| **PLAN_SWARM.md** | what we are building, in lanes, with falsifiable acceptance per lane |
| **PROVEN.md** | what is actually measured, with provenance, and what is still unknown |
| **ARTEMIS.md** | how the host works: Proton, Xvfb, farm, per-lane prefixes |
| **INTERFACE.md** | the state/action contract (Pau's, adapted) |
| **ROOM_NAMES.md** | room index → name, from the decompiled room table |

## Source of truth

* **Code**: `~/pau-tree` is Pau's stack and we use it directly — do not fork it. Our own code is
  `tools/` (workers, claims, milestones, plan) and the three root files (`neuro.py`, `train_win.py`,
  `evaluate.py`) that will hold the trainer.
* **Facts**: `PROVEN.md`. A fact is only there if it survived the double-check protocol in
  PLAN_SWARM.md (two processes, two directions, falsifier, cross-worker replay).
* **Journal**: `state/claims.jsonl` — every claim with its command and falsifier. `state/plan.json`
  is the machine-readable plan.

## House rules

1. Measured beats argued. No number without `claim.py record --cmd … --falsifier …`.
2. No win rate until 10+ verified rounds. `rounds_won` is 0.
3. Archive, don't delete: `git mv` into `legacy/` with a MANIFEST note.
4. Prefer Pau's function to writing ours. Two implementations of one thing is how 2026-11-09 was lost.
