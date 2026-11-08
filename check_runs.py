"""check_runs.py — audit recorded training runs for REALNESS, not performance.

Every run writes `results/runs/<id>/episodes.jsonl`. This tool answers the only question that
mattered tonight: was each episode a real match, and are the numbers attached to it honest?

It deliberately does NOT print a "best" or a win rate. Those have been wrong before, and always
for the same reason: an aggregate reported as if it were a fact about individual episodes. So it
prints per-episode verdicts and then the counts of each verdict.

Per-episode REALNESS checks (each one has caught a real bug in this project):

  entry gate       gate_px must clear the threshold the run actually used
  opponent played  opp_span >= 15 px - a statue produces reproducible, meaningless results
  enough samples   the window was actually observed, not truncated
  round claims     a claimed round must be backed by a verification flag; an unverified claim is
                   reported as an ARTIFACT, not a win

Usage:
    python3 check_runs.py                 # audit every recorded run
    python3 check_runs.py results/runs/<id>
"""
import glob
import json
import os
import sys

MIN_OPP_SPAN = 15.0
MIN_SAMPLES = 20


def load(run_dir):
    path = os.path.join(run_dir, "episodes.jsonl")
    rows = []
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
    except OSError:
        return []
    return rows


def classify(ep):
    """Return (verdict, reasons) for one episode.

    REALNESS IS DECIDED BY WHAT HAPPENED DURING THE EPISODE, not by the entry-time gate.
    A goldfish audit of this very project found the two disagree: one episode had
    `inert_entry=True` but the opponent moved 462 px, another had `inert_entry=False` and the
    opponent never moved. The during-episode span is the stronger evidence, so only that (and
    having actually observed the window) can make an episode not-real. An entry-gate failure is
    reported as a WARNING, because it usually just means the 10 s probe was unlucky.
    """
    reasons = []
    if ep.get("no_match"):
        return "DISCARDED", ["already discarded by the trainer"]
    span = ep.get("opp_span")
    if span is None:
        reasons.append("opponent span not recorded (run predates the field)")
    elif span < MIN_OPP_SPAN:
        reasons.append(f"opponent span {span:.0f} px - statue")
    if (ep.get("samples") or 0) < MIN_SAMPLES:
        reasons.append(f"only {ep.get('samples')} samples")
    # OUR FIGHTER MUST MOVE TOO. Measured: the "always left" seed pinned itself against the
    # left wall and every episode read me=[114..114], [16..16], [95..95] - zero movement, zero
    # kills, zero deaths. The opponent played (opp_span 112-207), so the episode passed the
    # realness test while containing NO policy signal at all: the fitness described the CPU's
    # behaviour, not ours. A fighter that never moves cannot demonstrate anything.
    _mr = ep.get("me_span_range") or [None, None]
    if _mr[0] is not None and _mr[1] is not None and abs(_mr[1] - _mr[0]) < 15.0:
        reasons.append(f"our fighter moved {(abs(_mr[1] - _mr[0])):.0f} px - no policy signal")
    if reasons:
        return "NOT REAL", reasons
    if ep.get("inert_entry"):
        return "REAL", ["warning: entry gate failed but the opponent played anyway"]
    return "REAL", []


def round_honesty(eps):
    """Separate claimed rounds into verified and unverified."""
    claimed_w = sum(e.get("rounds_won", 0) for e in eps)
    claimed_l = sum(e.get("rounds_lost", 0) for e in eps)
    ver_w = sum(sum(1 for v in (e.get("cross_verified") or []) if v) for e in eps)
    unver_w = sum(sum(1 for v in (e.get("cross_verified") or []) if not v) for e in eps)
    ver_l = sum(sum(1 for v in (e.get("loss_verified") or []) if v) for e in eps)
    unver_l = sum(sum(1 for v in (e.get("loss_verified") or []) if not v) for e in eps)
    return {
        "claimed_wins": claimed_w, "claimed_losses": claimed_l,
        "verified_wins": ver_w, "unverified_wins": unver_w,
        "verified_losses": ver_l, "unverified_losses": unver_l,
    }


def main():
    targets = sys.argv[1:] or sorted(glob.glob("results/runs/*"))
    if not targets:
        print("no recorded runs under results/runs/")
        return
    for run in targets:
        eps = load(run)
        print(f"\n=== {run}   ({len(eps)} episodes)")
        if not eps:
            print("   no episodes recorded")
            continue
        counts = {}
        for ep in eps:
            verdict, reasons = classify(ep)
            counts[verdict] = counts.get(verdict, 0) + 1
            if verdict != "REAL":
                print(f"   {ep.get('tag','?'):10s} {verdict:9s} {'; '.join(reasons)}")
        print(f"   verdicts: {counts}")
        real = [e for e in eps if classify(e)[0] == "REAL"]
        if real:
            k = sum(e.get("kills", 0) for e in real)
            d = sum(e.get("deaths", 0) for e in real)
            better = [e["tag"] for e in real if e.get("kills", 0) > e.get("deaths", 0) and False]
            print(f"   REAL episodes: {len(real)}   kills {k}  deaths {d}")
            # per-episode, not aggregate: the aggregate has misled before
            ep_level = [(e.get("tag"), e.get("kills", 0), e.get("deaths", 0)) for e in real]
            kills_ge = [t for t, kk, dd in ep_level if kk >= dd]
            print(f"   episodes with kills >= deaths: {len(kills_ge)} of {len(real)} "
                  f"-> {kills_ge[:6]}")
        rh = round_honesty(eps)
        print(f"   rounds claimed {rh['claimed_wins']}W/{rh['claimed_losses']}L   "
              f"verified {rh['verified_wins']}W/{rh['verified_losses']}L   "
              f"UNVERIFIED {rh['unverified_wins']}W/{rh['unverified_losses']}L")
        if rh["unverified_wins"] or rh["unverified_losses"]:
            print("   ^ unverified round claims are ARTIFACTS until a round transition is seen")


if __name__ == "__main__":
    main()
