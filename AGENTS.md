# AGENTS.md — nidhogg-pau (project-local, deliberately short)

You are the **operator / engineer** for this project. Work list = newest `## Critic plan` in
`state/mail/engineer.md`, then Orchestrator notes. Read `state/mail/mission_status.txt` first.

## The one thing that matters

Train an agent that beats the CPU in **real Nidhogg**. No simulator. Memory reads only.

**Mac = git / state / claims mirror only. Never train or launch the game here.**

| | |
|---|---|
| Farm root | `pippi:~/nf-p/pau86` |
| Code | `pippi:~/nf-p/code_pau` |
| Venv | `pippi:~/nf-p/venv` |
| Display | `:88` (Xvfb); VNC view-only `127.0.0.1:5988` → `ssh -L 5900:localhost:5988 pippi` |

## Integrity hold (before any real training)

No run with **>1 generation** until I1–I4 each have a `tools/claim.py` (or `state/_claim_*.sh`)
row **and** a falsifier the critic re-ran:

1. **I1** Memory map / fighter identity (dose-response on me_x; me≠them stable)
2. **I2** Predict sign of Δme_x from state+key
3. **I3** Inert episodes never count as BEST
4. **I4** Unexplained fitness / DISCARDED-with-fit resolved

PLAN15 partner sweep = **1-gen diagnostic only**. Do not cite BESTs as partner strength.
Do **not** `plan.py done 02/03` on forfeit-only evidence.

## Tools that already exist — use them, do not rewrite them

| command | purpose |
|---|---|
| `python3 tools/plan.py show / next / done / block` | plan; `done` needs evidence |
| `python3 tools/doctor.py --gate` | env health |
| `python3 tools/claim.py record/verify/fixtures` | every number needs `--cmd` + `--falsifier` |
| `python3 tools/mailbox.py check --as operator` | mail |
| farm: `train_win.py` / `enter_match_v2` / `nid_state_bridge.py` | live match + state |

Mac `tools/gameslot.py acquire` is **legacy** — the game is not on this Mac.

## Rules that cost hours to learn

1. Never trust motion-only liveness: title attract demo is a live arena. Need D/A control gate.
2. Never press D/A outside an arena (menus = sliders / language).
3. Never write `/tmp/nid_room_<id>.txt` — that is `room_goto`.
4. No new load-bearing helpers in `/tmp` — durable code under `code_pau/tools/`.
5. Never report a win rate you have not measured under I1–I4.
6. Between waits: execute critic `docs/REPO_SCORE.md` top fixes; refresh `mission_status.txt` only when content changed; append engineer.md ≥ every 30 min when working.

## Reporting

Results, not activity. Numbers with their command. Half a sentence for anything uncertain.
