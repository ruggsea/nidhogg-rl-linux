# Repo score — 2026-11-26T17:22Z

Scored by critic against `docs/REPO_QUALITY.md`. Evidence from Mac tree + `ssh pippi` peek.
Re-score after the engineer lands a Critic-plan batch.

| id | score | evidence |
|---|---|---|
| Q01 | 0 | Root `README.md` still titled/framed as Mac train (`uv venv`, `python3 train_win.py`, Steam Mac path). **0** hits of `pippi` / `nf-p` / `mirror`. |
| Q02 | 0 | `AGENTS.md` (mtime 2026-11-08): “Train … locally installed **macOS** Nidhogg”, `gameslot.py acquire`, no I1–I4, no farm, no Critic plan. |
| Q03 | 2 | `state/mail/mission_status.txt` `updated=2026-11-26T17:16Z`: farm=pippi paths, I1–I4 hold, PLAN15 p7, VNC tunnel, stash-or-keep. |
| Q04 | 2 | `plan.json`: 02+03 `done=false`; 05–07/11/12 `done=false` + `reason: pending I1-I4 …`. PLAN.md render matches open 02/03. |
| Q05 | 1 | Engineer reports NOTES Linux/integrity section today; root `NOTES.md` still opens on 2026-10-25 Mac injection. `docs/STATE.md` is Mac-verified table, rounds_won=0, no me/them swap. Partial. |
| Q06 | 0 | No root `DECISIONS.md`. Step-01 rescope and I1–I4 hold live only in plan.json history / mail. |
| Q07 | 0 | No root `LIMITATIONS.md`. |
| Q08 | 0 | `find . -name '._*' \| wc -l` → **277** (root, docs/, spy/, legacy/, out/, …). |
| Q09 | 1 | 176 `claims.jsonl` rows; 18 `_claim_*.sh` + 19 `_falsify_*.sh`. Critic 16:44Z REFUSED citing PLAN15 BESTs / plan06 win without I1. Older claims exist; integrity gate not claimed. |
| Q10 | 0 | No `results/figures/`. No PNG+command pairs for PLAN15 or I-checks. |
| Q11 | 0 | README + AGENTS = Mac train; `mission_status` = farm-only. `docs/OVERVIEW.md` / `NEXT_STEPS.md` / `.claude/worktrees/...` add more entry stories. |
| Q12 | 0 | No `state/_claim_i1*` / I2–I4 claim or falsifier. Critic has not SUPPORTED any I1–I4 claim. |
| Q13 | 2 | `PLAN.md` header: rendered from `state/plan.json` by `tools/plan.py`; open/done flags align with json for 02–07/11/12. |
| Q14 | 1 | `.gitignore` present (needs spot-check for `._*` / checkpoints); AppleDouble still on disk. Not a full audit this round. |
| Q15 | 0 | Cold open of README alone → “run train_win on this Mac”. Must read `mission_status.txt` to learn farm. |
| Q16 | 1 | Durable `code_pau/tools/nid_state_bridge.py` exists. Engineer still lists obsolete `/tmp` one-shots (do_step02_poll5, patch_*, …) not cleared. |
| Q17 | 0 | `.claude/worktrees/step01-rescope/docs/*` duplicates LAYOUT/OVERVIEW/… without superseded banner at root docs index. |
| Q18 | 1 | `docs/EXPERIMENTS.md` + `NOTES.md` + claims cover older tries; today’s PLAN15 inert/me-them findings are in mail/logs more than the notebook. |

**Weighted sum:** 0·3 + 0·3 + 2·2 + 2·3 + 1·2 + 0·2 + 0·1 + 0·0·2 + 1·3 + 0·2 + 0·2 + 0·3 + 2·1 + 1·1 + 0·2 + 1·2 + 0·1 + 1·1 = **18 / 72** (max 2×weight). Weighted mean ≈ **0.50**. Pass bar (≥1.5 and Q01/Q02/Q04/Q09/Q12 ≥1): **FAIL**.

## Top fixes for a human opening cold (engineer order after I1–I4 / VNC)

1. **Q01** — Rewrite root README first screen: Mac = mirror; farm = pippi `~/nf-p/{pau86,code_pau,venv}`; point at `mission_status.txt` + Critic plan; mark Mac `train_win.py` runbook superseded.
2. **Q02** — Rewrite `AGENTS.md` to farm ops + I1–I4 hold + no Mac train/game + VNC tunnel.
3. **Q08** — Delete all `._*` in tree; add `._*` to `.gitignore`.
4. **Q15/Q11** — One entry path only; banner or move stale `docs/NEXT_STEPS.md` / worktree docs.
5. **Q06/Q07** — Add root `DECISIONS.md` + `LIMITATIONS.md` (I1–I4 hold, farm-only, stash-or-keep, PLAN15 diagnostic).
6. **Q10** — Create `results/figures/`; first figure = PLAN15 partner bars with inert-counted marked (command in engineer.md).
7. **Q12/Q09** — After fighter-identity fix: land I1 claim+falsifier; then I3/I2/I4. No “learns/beats” without them.
8. **Q16** — Clear or mark obsolete the listed `/tmp` helpers on pippi.
9. **Q05** — Fold me/them swap + inert-as-BEST into `NOTES.md` / `docs/STATE.md` with log paths.

I1–I4 and live VNC still outrank every polish item when the farm is free.
