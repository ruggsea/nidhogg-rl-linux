#!/usr/bin/env bash
# check_progress.sh — one tick: has anything real happened, and tell the user if so.
#
# Called by the self-loop every few minutes. Emails ONLY when the evidence snapshot gains something
# (an attestation passing, a plan step closed with evidence, a claim recorded, a generation completed,
# or a round transition observed). Silent otherwise, so the inbox stays useful.
#
# Email goes through artemis because this Mac has no RESEND_API_KEY (see rules/cloud.md); Gmail's token
# is revoked.
set -uo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO"
PY="${NID_PYTHON:-$HOME/Projects/nidhogg-rl/.venv/bin/python}"

OUT="$("$PY" tools/progress.py --json 2>&1)" || { echo "progress check failed: $OUT"; exit 0; }
NEW="$(PROG_JSON="$OUT" "$PY" -c 'import json,os;print(json.loads(os.environ["PROG_JSON"])["is_new"])')"
BODY="$(PROG_JSON="$OUT" "$PY" - <<'PY'
import json, os
d = json.loads(os.environ["PROG_JSON"])
n, delta = d["now"], d["delta"]
lines = []
lines.append("EVIDENCE SNAPSHOT")
for k, v in delta.items():
    lines.append(f"  +{v} {k}")
lines.append("")
lines.append("state now:")
lines.append(f"  attestation : {n['attest_passing']}/{n['attest_total']} runs passed, best streak {n['attest_best_streak']} (step 01 needs 3 consecutive)")
lines.append(f"  plan        : {n['plan_done']}/{n['plan_total']} steps closed with evidence")
for r in n["plan_done_rows"]:
    lines.append(f"                - {r}")
lines.append(f"  claims      : {n['claims']}")
lines.append(f"  generations : {n['generations']}")
lines.append(f"  rounds      : {n['rounds_observed']}")
lines.append("")
lines.append("Still unclaimed: no win rate exists until 10+ verified rounds (plan step 07).")
print("\n".join(lines))
PY
)"

if [ "$NEW" = "True" ]; then
  echo "NEW EVIDENCE"
  printf '%s\n' "$BODY"
  ssh -o BatchMode=yes -o ConnectTimeout=10 artemis 'cat > /tmp/mail_body.txt' <<< "$BODY" \
    && ssh -o BatchMode=yes -o ConnectTimeout=10 artemis \
       '~/claude-code-config/bin/notify.sh mail "$(cat /tmp/mail_body.txt)" "Nidhogg progress: new evidence"' \
    && echo "(emailed)" || echo "(email failed - evidence is in state/progress_last.json)"
else
  echo "no new evidence"
  printf '%s\n' "$BODY" | head -6
fi
