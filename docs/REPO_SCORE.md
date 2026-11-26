# Repo score — 2026-11-26T18:22Z

Re-score after engineer REPO batch (eng 17:25Z). Criteria: `docs/REPO_QUALITY.md`.

| id | score | evidence |
|---|---|---|
| Q01 | 2 | Root README first screen: Mac=mirror, farm=pippi `~/nf-p/{pau86,code_pau,venv}`, mission_status + Critic plan, I1–I4 hold, Mac runbook marked superseded. |
| Q02 | 2 | `AGENTS.md` rewritten: farm ops, no Mac train/gameslot, I1–I4, Critic plan, VNC tunnel. |
| Q03 | 2 | `mission_status.txt` `updated=2026-11-26T17:57:35Z`: p7 hung note, VNC, REPO batch landed, I1–I4. |
| Q04 | 2 | plan.json 02+03 `done=false`; 05–07/11/12 pending I1–I4. |
| Q05 | 2 | `NOTES.md` §2026-11-26 Linux farm/integrity + me/them paths; `docs/STATE.md` farm integrity banner (I1 red). |
| Q06 | 2 | Root `DECISIONS.md`: farm-only, I1–I4 hold, step-01 rescope (Chosen/Alt/Why/By/Change if/Evidence). |
| Q07 | 2 | Root `LIMITATIONS.md`: farm-only, stash-or-keep, PLAN15 diagnostic, I1–I4, 02/03 open, /tmp, AppleDouble. |
| Q08 | 2 | `find . -name '._*' \| wc -l` → **0**. `.gitignore` has `._*` / `**/._*`. |
| Q09 | 1 | Still 176 claims; PLAN15 BESTs not accepted. No new integrity claim rows. |
| Q10 | 2 | `results/figures/plan15_partner_fitness.png` (+ twin bests.png), PNG 1200×540. Eng named command. Diagnostic only. |
| Q11 | 2 | SUPERSEDED banners on `docs/NEXT_STEPS.md`, `docs/OVERVIEW.md`; worktree `docs/SUPERSEDED.md`. Entry = README+AGENTS+mission_status. |
| Q12 | 0 | No I1–I4 claim/falsifier scripts yet. Farm still on hung p7 — I1 blocked. |
| Q13 | 2 | PLAN.md still render of plan.json; 02/03 open. |
| Q14 | 2 | `.gitignore` adds `._*`, `*.pt`/`*.pth`/`ckpt*`. |
| Q15 | 2 | Cold open of README answers goal / farm / blocked / next. |
| Q16 | 2 | pippi `/tmp/{do_step02_poll5,fc_all,fix_*,patch_*,stoplog}.py` → `*.OBSOLETE_20261126` (10 files); live `.py` gone. |
| Q17 | 2 | Worktree docs marked SUPERSEDED; root entry path clear. |
| Q18 | 2 | NOTES integrity section + EXPERIMENTS + claims cover tries; PLAN15 findings greppable. |

**Weighted sum:** 2·3+2·3+2·2+2·3+2·2+2·2+2·1+2·2+1·3+2·2+2·2+0·3+2·1+2·1+2·2+2·2+2·1+2·1 = **63 / 72**. Weighted mean ≈ **1.75**. Pass bar (≥1.5 and Q01/Q02/Q04/Q09/Q12 ≥1): **FAIL** only on **Q12=0** (and Q09 still 1). Polish batch landed; integrity claims still missing.

## Remaining top fixes (after I1 farm free)

1. **Q12** — I1 claim+falsifier (then I3/I2/I4). Blocks pass bar.
2. **Q09** — Land those as accepted numbers with critic re-run.
3. When p7 dies: partners JSON (no `.tmp`), then I1 on free farm.
4. Re-score once Q12 ≥1.
