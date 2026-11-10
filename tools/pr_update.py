#!/usr/bin/env python3
"""pr_update.py — post verified progress to the pull request, automatically.

Only *verified* facts are posted. That is the whole point: this project has retracted five phantom
results (teleports counted as rounds, wall-pinned gates, attract demos, day-old generations, a
forfeit labelled corroborated with `corroborated: false` in the same record). A bot that pastes raw
claims into a colleague's PR would spread exactly that noise, so the digest below recomputes
everything from the artefacts and refuses anything that fails the corroboration rules.

What counts as verified here:
  * a round with kind='round' AND (both_fighters_reset OR winner_screen OR ready_wall OR corroborated)
  * a win: one of those rounds with result in (win, won, p1)
  * the control gate: an entry in state/lane_a_gate.jsonl with max_delta >= 200
  * a score field: only if a claim says the HUD moved after a write AND a second worker replayed it
  * the entry point: enter_match_v2 returning True (recorded in claims)

Posting rules:
  * never more than one comment per MIN_GAP minutes
  * never a comment unless the digest changed
  * if --dry-run, print what would be posted and say nothing to GitHub

    python3 tools/pr_update.py --dry-run
    python3 tools/pr_update.py            # posts if there is something new and verified
"""
import json
import os
import subprocess
import sys
import time

REPO = "PauSolerValades/nidhogg-rl-linux"
PR = 1
STATE = "state"
DIGEST = os.path.join(STATE, "pr_last_digest.json")
MIN_GAP = 45 * 60          # seconds between comments, at most


def ssh(cmd, timeout=60):
    try:
        r = subprocess.run(["ssh", "-o", "ConnectTimeout=15", "-o", "ControlMaster=no",
                            "artemis", cmd], capture_output=True, text=True, timeout=timeout)
        return r.stdout
    except (subprocess.TimeoutExpired, OSError):
        return ""


def load_jsonl_remote(path):
    out = ssh(f"cat ~/nidhogg-pau/{path} 2>/dev/null")
    rows = []
    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except ValueError:
            continue
    return rows


def verified_digest():
    rounds = load_jsonl_remote("state/rounds.jsonl")

    def is_round(r):
        if str(r.get("kind", "")).lower() != "round":
            return False
        return (r.get("corroborated") is True or r.get("both_fighters_reset") is True
                or r.get("ready_wall") is True or r.get("winner_screen") is True)

    good = [r for r in rounds if is_round(r)]
    wins = [r for r in good if str(r.get("result", "")).lower() in ("win", "won", "p1")]

    gate = load_jsonl_remote("state/lane_a_gate.jsonl")
    gate_ok = [g for g in gate if isinstance(g, dict) and float(g.get("max_delta") or 0) >= 200]

    claims = load_jsonl_remote("state/claims.jsonl")
    entry_ok = [c for c in claims if "enter_match_v2" in (c.get("text") or "").lower()
                and ("live match" in (c.get("text") or "").lower()
                     or "verified live" in (c.get("text") or "").lower())]
    # A score field counts as verified ONLY if a claim says the HUD actually changed after a write AND a
    # second worker replayed it. The loose version of this test posted "a score field is now verified"
    # while the truth was the opposite (Pau's address was refuted and ours is still unknown) - caught by
    # running the digest in --dry-run before letting it near the PR.
    NEG = ("does not", "did not", "not verified", "refut", "varies", "unchanged", "failed", "no change")
    score_ok = []
    for c in claims:
        t = (c.get("text") or "").lower()
        if "score" not in t or "hud" not in t:
            continue
        if any(neg in t for neg in NEG):
            continue
        if not any(pos in t for pos in ("changed", "moved", "incremented")):
            continue
        if "replay" not in t and "second worker" not in t:
            continue
        score_ok.append(c)

    return {
        "rounds": len(good),
        "wins": len(wins),
        "gate_passes": len(gate_ok),
        "gate_max_delta": int(max([float(g.get("max_delta") or 0) for g in gate_ok], default=0)),
        "entry_proven": len(entry_ok) > 0,
        "score_verified": len(score_ok) > 0,
        "claims": len(claims),
    }


def body_for(d, prev):
    changed = []
    if prev.get("rounds") != d["rounds"]:
        changed.append(f"corroborated round boundaries: {prev.get('rounds', 0)} -> **{d['rounds']}**")
    if prev.get("wins") != d["wins"]:
        changed.append(f"verified round wins: {prev.get('wins', 0)} -> **{d['wins']}**")
    if prev.get("gate_passes") != d["gate_passes"]:
        changed.append(f"write-survival gate passes: {d['gate_passes']} (max x delta {d['gate_max_delta']} px)")
    if prev.get("entry_proven") != d["entry_proven"] and d["entry_proven"]:
        changed.append("`enter_match_v2` reaches a verified live match on our host")
    if prev.get("score_verified") != d["score_verified"] and d["score_verified"]:
        changed.append("a score field is now verified against the HUD")
    if not changed:
        return None
    lines = ["**Verified update** (auto-posted, only facts that pass the corroboration rules)", ""]
    lines += [f"* {c}" for c in changed]
    lines += ["", f"Totals: {d['rounds']} corroborated rounds, {d['wins']} wins, "
                  f"{d['claims']} claims recorded. " +
                  ("Win rate: " + f"{100.0*d['wins']/d['rounds']:.0f}% over {d['rounds']} rounds."
                   if d["rounds"] >= 10 else "No win rate claimed until 10+ rounds.")]
    return "\n".join(lines)


def main():
    dry = "--dry-run" in sys.argv
    os.makedirs(STATE, exist_ok=True)
    try:
        prev = json.load(open(DIGEST))
    except (OSError, ValueError):
        prev = {"digest": {}, "ts": 0}
    d = verified_digest()
    prev_d = prev.get("digest", {})
    body = body_for(d, prev_d)
    if not body:
        print("pr_update: nothing new and verified - no comment")
        return 0
    since = time.time() - prev.get("ts", 0)
    if since < MIN_GAP and not dry:
        print(f"pr_update: new verified facts but last comment was {int(since/60)} min ago (< {MIN_GAP//60}) - deferring")
        return 0
    if dry:
        print("--- would post ---")
        print(body)
        return 0
    r = subprocess.run(["gh", "pr", "comment", str(PR), "--repo", REPO, "--body", body],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print("pr_update: gh failed:", (r.stderr or r.stdout).strip()[:200])
        return 1
    json.dump({"digest": d, "ts": time.time()}, open(DIGEST, "w"), indent=1)
    print("pr_update: posted", (r.stdout or "").strip()[:120])
    return 0


if __name__ == "__main__":
    sys.exit(main())
