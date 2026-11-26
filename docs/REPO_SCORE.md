# Repo score — 2026-11-26T19:04Z

Evidence refresh (Orchestrator 19:03Z). Scores unchanged pending I1 v3 exit + claim/falsifier.
Criteria: `docs/REPO_QUALITY.md`. Prior polish batch eng 17:25Z still holds for Q01–Q08/Q10–Q11/Q13–Q18.

| id | score | evidence |
|---|---|---|
| Q01 | 2 | Root README: Mac=mirror, farm=pippi `~/nf-p/{pau86,code_pau,venv}`, mission_status + Critic plan, I1–I4 hold. |
| Q02 | 2 | `AGENTS.md`: farm ops, no Mac train, I1–I4, Critic plan, VNC tunnel. |
| Q03 | 1 | `mission_status.txt` needs refresh after I1 v3 exit (was 19:00Z; v3 still running). |
| Q04 | 2 | plan.json 02+03 `done=false`; 05–07/11/12 pending I1–I4. |
| Q05 | 2 | `NOTES.md` Linux/integrity + me/them; `docs/STATE.md` I1-red banner (engineer to update after v3). |
| Q06 | 2 | Root `DECISIONS.md`: farm-only, I1–I4 hold, step-01 rescope. |
| Q07 | 2 | Root `LIMITATIONS.md`: farm-only, PLAN15 diagnostic, I1–I4, 02/03 open. |
| Q08 | 2 | `find . -name '._*'` → 0; gitignore has `._*`. |
| Q09 | 1 | Still 176 `claims.jsonl` rows; **no** I1 claim/falsifier. PLAN15 BESTs not accepted. I1 probes exist as evidence only (`i1_probe.json` retry2 `dose_ok=False`). |
| Q10 | 2 | `results/figures/plan15_partner_fitness.png` diagnostic only. |
| Q11 | 2 | SUPERSEDED banners; entry = README+AGENTS+mission_status. |
| Q12 | 0 | **No I1–I4 claim/falsifier scripts.** Farm free (p7 **84245/4031373 dead**, PLAN15 closed `plan15_partners.json`). I1 in progress: retry2 REFUSED (N10 teleport −1e38, N20 dme=0); v3 `i1_fighter_identity.py` still running — **not** a pass. |
| Q13 | 2 | PLAN.md render of plan.json; 02/03 open. |
| Q14 | 2 | `.gitignore` has `._*`, `*.pt`/`*.pth`/`ckpt*`. |
| Q15 | 2 | Cold open of README answers goal / farm / blocked / next. |
| Q16 | 2 | `/tmp` one-shots → `*.OBSOLETE_20261126`. |
| Q17 | 2 | Worktree docs SUPERSEDED. |
| Q18 | 2 | NOTES + EXPERIMENTS + claims greppable; I1 probe logs under `results/runs/i1_probe_*`. |

**Weighted sum:** **62 / 72** (Q03 2→1). Weighted mean ≈ **1.72**. Pass bar: **FAIL** (Q12=0, Q09=1).

## Remaining top fixes

1. **Q12 / Q09** — After I1 v3 exits: if `dose_ok` land claim+falsifier; critic re-runs; then re-score. Until then keep Q12=0 / REFUSE I1.
2. Engineer: paste v3 json+log; refresh `mission_status.txt` + `docs/STATE.md` I1 banner (red until dose_ok+claim/falsifier).
3. One probe pid only; leave VNC/bridge/:88.
