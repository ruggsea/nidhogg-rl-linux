#!/usr/bin/env python3
"""Fixture test for event-tied outcome fields (no game needed).

Feeds ``outcome_events.OutcomeTracker`` a fixed sample stream and prints the result as
one JSON line, so a claim and its falsifier read the same deterministic behaviour.

Stream (room, p1_alive, p2_alive):
  arena 29 both alive            -> no event
  1 sample with P1=0             -> a flicker, must NOT become a death
  P2=0 for 4 samples             -> a death: P2 died, P1 wins the round
  room -> 20 (rMatchStats)       -> a room event that leaves the arena

  python3 code_pau/tools/outcome_events_test.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from outcome_events import OutcomeTracker, summarize_fixture  # noqa: E402

SAMPLES = ([(29, 1, 1)] * 3 + [(29, 0, 1)] + [(29, 1, 1)] * 2
           + [(29, 1, 0)] * 4 + [(29, 1, 1)] * 2 + [(20, 1, 1)] * 3)


def main():
    summary, events = summarize_fixture(SAMPLES)
    deaths = [e for e in events if e["kind"] == "death"]
    rooms = [e for e in events if e["kind"] == "room"]
    print(json.dumps({
        "summary": summary,
        "deaths": deaths,
        "rooms": rooms,
        "deaths_n": len(deaths),
        "rounds_left_arena": sum(1 for e in rooms if e["left_arena"]),
    }))


if __name__ == "__main__":
    main()