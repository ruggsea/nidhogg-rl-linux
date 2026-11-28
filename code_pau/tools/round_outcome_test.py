#!/usr/bin/env python3
"""Fixture test for ``outcome_events.round_boundary`` (no game needed).

Feeds fixed room-index pairs and prints the result as one JSON line, so a claim and
its falsifier read the same deterministic behaviour. This is the step-2 cut: round
boundaries from the verified room index, not the FLAG_P1/P2 death debounce.

  python3 code_pau/tools/round_outcome_test.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from outcome_events import round_boundary  # noqa: E402

CASES = [
    (29, 29, False),    # same room: no boundary
    (29, 4, False),     # arena -> lobby: re-entry navigation
    (4, 29, False),     # lobby -> arena: entry navigation
    (20, 29, False),    # match stats -> arena: re-entry
    (29, 20, True),     # arena -> rMatchStats: match ended
    (29, 35, True),     # arena -> arena, higher index: advanced right
    (35, 29, True),     # arena -> arena, lower index: advanced left
    (None, 29, False),  # no previous room
]


def main():
    rows = []
    for prev, cur, expect in CASES:
        got = round_boundary(prev, cur)
        fired = got is not None
        rows.append({"prev": prev, "cur": cur, "expect_boundary": expect,
                     "got": fired, "event": got})
    n_advance = sum(1 for r in rows if r["event"]
                    and r["event"]["kind"] == "round_advance")
    n_end = sum(1 for r in rows if r["event"]
                and r["event"]["kind"] == "round_match_end")
    n_nav = sum(1 for r in rows if not r["event"])
    print(json.dumps({"cases": rows, "n_boundaries": n_advance + n_end,
                      "n_advance": n_advance, "n_match_end": n_end,
                      "n_navigation": n_nav,
                      "all_expectations_match": all(r["got"] == r["expect_boundary"]
                                                    for r in rows)}))


if __name__ == "__main__":
    main()