# Repo quality bar (nidhogg-pau)

Critic-owned. Engineer executes fixes listed in the newest `## Critic plan` in
`state/mail/engineer.md`. Re-score in `docs/REPO_SCORE.md` after each landed batch.
Standards cited: `~/Projects/claude-code-config/CLAUDE.md` (Style / Records / Research
results), `rules/project-records.md`, sibling shape (persona-vector: short entry README
that names goal, where code lives, where numbers live).

Score each criterion 0 / 1 / 2. Weight is relative importance for a human opening cold
or for trusting a training claim. I1–I4 integrity always outranks polish.

| id | weight | pass-when | fail-when |
|---|---|---|---|
| Q01 | 3 | Root `README.md` says in the first screen: goal, Mac = git/state/claims mirror only, farm = pippi `~/nf-p/pau86` + `~/nf-p/code_pau` + `~/nf-p/venv`, and where to read status (`state/mail/mission_status.txt`). | README still reads as “train on this Mac” / copies nidhogg-rl Mac launch, or never names pippi. |
| Q02 | 3 | `AGENTS.md` matches today’s ops: no Mac train/game, I1–I4 before real training, Critic plan as work list, farm paths, VNC tunnel line. | AGENTS still tells an operator to acquire the Mac game slot and train locally. |
| Q03 | 2 | `state/mail/mission_status.txt` `updated=` is today’s UTC hour (or the last real change), names I1–I4 status, farm pid/display, VNC. | Missing, or last update predates the current Critic plan / farm state by hours with no reason. |
| Q04 | 3 | `state/plan.json` (and rendered `PLAN.md`) keep 02/03 open; any step whose number rests on untrusted memory is `done=false` with `pending I1-I4` (or equivalent) in `reason`. | Closing 02/03 on B5/forfeit-only, or citing 05–07/11/12 as wins while I1 is red. |
| Q05 | 2 | Root or `docs/` has a greppable current notebook: today’s Linux/integrity findings (me/them swap, inert-as-BEST, bridge, prefs) with evidence paths. | `NOTES.md` / `docs/STATE.md` stop at Mac-era Oct/Nov-8 and contradict the farm. |
| Q06 | 2 | Root `DECISIONS.md` exists with dated forks (Chosen / Alternatives / Why / Decided by / Change if / Evidence), including step-01 rescope and I1–I4 hold. | No DECISIONS file; forks live only in chat or engineer.md. |
| Q07 | 1 | Root `LIMITATIONS.md` lists accepted limits (e.g. farm-only train, no Mac rewrite until stash-or-keep, PLAN15 = 1-gen diagnostic). | Limits only implied in mail. |
| Q08 | 2 | `find . -name '._*' \| wc -l` is 0 in the working tree (or those paths are gitignored and absent from commits). | Dozens/hundreds of AppleDouble `._*` next to real files. |
| Q09 | 3 | Every number the project treats as accepted has a `tools/claim.py` (or `state/_claim_*.sh`) row **and** a falsifier that exits 1; critic re-ran both. | Accepted / “done” numbers with no falsifier, or claim scripts that pass on inert/frozen fighters. |
| Q10 | 2 | `results/figures/` holds PNGs for each reported result; engineer.md names the exact command that made each figure. | No figures dir, or results only as prose / raw logs. |
| Q11 | 2 | One entry story: root README + AGENTS point at the farm; obsolete “Mac train” runbooks are marked superseded or moved under `legacy/`. | Parallel entry points (`README`, `docs/OVERVIEW`, `docs/NEXT_STEPS`, AGENTS) disagree on where to train. |
| Q12 | 3 | I1–I4 each have a claim script + falsifier under `state/` (or `tools/claim.py` rows); critic has SUPPORTED them in engineer.md. | No I1–I4 claims; training or “learns/beats” language without them. |
| Q13 | 1 | `PLAN.md` is the render of `state/plan.json` (`tools/plan.py`); checked boxes match `done`. | Hand-edited PLAN.md drift, or show vs json disagree. |
| Q14 | 1 | `.gitignore` excludes venvs, checkpoints (`*.pt`/`*.pth`/`ckpt*`), run logs bulk, `__pycache__`, `._*`. | Accidental commit of weights/logs/AppleDouble. |
| Q15 | 2 | A cold human can answer in ≤2 minutes: what is the goal, where does the game run, what is blocked, what to read next — from README + mission_status alone. | Must dig engineer.md / worktrees / SESSION_LOG to learn Mac≠farm. |
| Q16 | 2 | Durable helpers live under `tools/` (Mac) or `code_pau/tools/` (pippi); `/tmp` one-shots are gone or listed obsolete with date. | Load-bearing patches only in `/tmp/*.py` on pippi. |
| Q17 | 1 | No duplicate swarm/worktree docs presented as current (`docs/` vs `.claude/worktrees/...`) without a “superseded” banner. | Two OVERVIEW/NEXT_STEPS trees with different facts and no pointer. |
| Q18 | 1 | Experiments tried (and failed) are greppable in `NOTES.md` / `docs/EXPERIMENTS.md` / claims with outcome + evidence path. | Silent retries of failed recipes. |

Weights sum = 36. Pass bar for “human-enjoyable”: weighted mean ≥ 1.5 and Q01,Q02,Q04,Q09,Q12 all ≥ 1.
