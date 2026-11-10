"""verified.py — ONE definition of "verified round", shared by every reporter.

Why this file exists: `milestones.py`, `pr_update.py` and my ad-hoc queries each grew their own
filter, and they disagreed. At the time of writing the artefact held **21 corroborated round entries
(13 wins, 1 loss)**, `milestones.py` reported **4 rounds, 0 wins**, and a third query reported 19/12.
Any number built on a private definition is a number nobody can check — which is exactly how this
project produced six phantom results.

Rule (and it is deliberately stricter than any label a writer can choose):
    kind == "round"  AND  (corroborated is True
                           or both_fighters_reset is True
                           or winner_screen is True
                           or ready_wall is True)

A `kind` label alone is never enough. A HUD pixel-count change is never enough. Prose is never enough.
"""
import json
import os
from collections import Counter

STATE = os.environ.get("NID_STATE", "state")


def load_jsonl(path):
    rows = []
    try:
        for line in open(path, errors="ignore"):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except ValueError:
                continue
    except OSError:
        pass
    return rows


def is_round(r):
    if str(r.get("kind", "")).lower() not in ("round", "round_end", "roundend"):
        return False
    return (r.get("corroborated") is True
            or r.get("both_fighters_reset") is True
            or r.get("winner_screen") is True
            or r.get("ready_wall") is True)


def rounds(path=None):
    path = path or os.path.join(STATE, "rounds.jsonl")
    return [r for r in load_jsonl(path) if is_round(r)]


def counts(path=None):
    rs = rounds(path)
    wins = [r for r in rs if str(r.get("result", "")).lower() in ("win", "won", "p1")]
    losses = [r for r in rs if str(r.get("result", "")).lower() in ("loss", "lost", "p2")]
    return {"rounds": len(rs), "wins": len(wins), "losses": len(losses),
            "decided": len(wins) + len(losses)}


def win_rate(path=None):
    """None until 10 decided rounds exist - a rate over 3 rounds is noise dressed as a statistic."""
    c = counts(path)
    if c["decided"] < 10:
        return None
    return 100.0 * c["wins"] / c["decided"]


def kind_breakdown(path=None):
    return Counter(str(r.get("kind")) for r in load_jsonl(path or os.path.join(STATE, "rounds.jsonl")))


if __name__ == "__main__":
    c = counts()
    print(json.dumps({**c, "win_rate": win_rate(), "kinds": dict(kind_breakdown())}, indent=1))
