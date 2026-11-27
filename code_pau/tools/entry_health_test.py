#!/usr/bin/env python3
"""Unit test for the entry-health gate (tools/entry_health.py). No game, no display.

nidlinux / nidstate are stubbed before entry_health is imported, so this runs anywhere:
    python3 -m unittest code_pau.tools.entry_health_test
    python3 tools/entry_health_test.py
Exit 0 = all pass. The live end-to-end check is tools/entry_swap_check.py (farm + game).
"""
import os
import sys
import types
import unittest

# Make `import entry_health` work no matter which directory unittest is started from.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def _stub(name, **attrs):
    m = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(m, k, v)
    sys.modules[name] = m
    return m


_stub("nidlinux", _game_pid=lambda i: 1, stop_id=lambda i: None,
      start_ids=lambda ids, fresh=False: None, key=lambda i, k, hold=0.0: None)
_stub("nidstate", enter_match_v2=lambda i, verbose=True: True,
      _fighters_visible=lambda i, name="": True, _wall_x=lambda i, name="": None,
      frame=lambda i, name="": None, _mask=lambda a, which: a,
      on_ready_screen=lambda i: True, enter_ready=lambda i, tries=8, wait=1.0: True)

import entry_health as eh  # noqa: E402


class FakeTime:
    """time() advances 1 s per call and sleep() is free, so the 20 s poll is instant."""

    def __init__(self):
        self.t = 0.0

    def time(self):
        self.t += 1.0
        return self.t

    def sleep(self, _s):
        pass


class StuckSig(unittest.TestCase):
    def test_stuck(self):
        self.assertTrue(eh.stuck_sig({"fv": False, "wall": None, "yel": 0}))

    def test_live(self):
        self.assertFalse(eh.stuck_sig({"fv": True, "wall": None, "yel": 2980}))

    def test_ready_wall(self):
        self.assertFalse(eh.stuck_sig({"fv": True, "wall": 319.5, "yel": 984}))

    def test_yellow_only_is_not_stuck(self):
        self.assertFalse(eh.stuck_sig({"fv": False, "wall": None, "yel": 5}))


class EnsureEntry(unittest.TestCase):
    def setUp(self):
        eh.time = FakeTime()
        self.calls = []
        eh.relaunch = lambda iid=0: self.calls.append("relaunch")
        eh.settle_ready = lambda iid=0, max_loops=12: {}

    def test_stuck_relaunches_then_enters(self):
        seq = [{"fv": False, "wall": None, "yel": 0}, {"fv": True}]
        eh.snapshot = lambda tag, iid=0: seq.pop(0)
        eh.ns.enter_match_v2 = lambda i, verbose=True: self.calls.append("enter") or True
        self.assertTrue(eh.ensure_entry(0))
        self.assertEqual(self.calls, ["relaunch", "enter"])

    def test_live_skips_relaunch(self):
        eh.snapshot = lambda tag, iid=0: {"fv": True, "wall": None, "yel": 2980}
        eh.ns.enter_match_v2 = lambda i, verbose=True: self.calls.append("enter") or True
        self.assertTrue(eh.ensure_entry(0))
        self.assertEqual(self.calls, ["enter"])

    def test_poll_accepts_late_spawn(self):
        snaps = [{"fv": True, "wall": None, "yel": 2980}, {"fv": False},
                 {"fv": True}, {"fv": True}]
        eh.snapshot = lambda tag, iid=0: snaps.pop(0)
        eh.ns.enter_match_v2 = lambda i, verbose=True: self.calls.append("enter") or False
        self.assertTrue(eh.ensure_entry(0))
        self.assertEqual(self.calls, ["enter"])

    def test_gives_up_after_one_retry(self):
        eh.snapshot = lambda tag, iid=0: {"fv": False, "wall": None, "yel": 0}
        eh.ns.enter_match_v2 = lambda i, verbose=True: self.calls.append("enter") or False
        self.assertFalse(eh.ensure_entry(0))
        self.assertEqual(self.calls, ["relaunch", "enter", "relaunch", "enter"])

    def test_entered_but_no_fighters_is_false(self):
        eh.snapshot = lambda tag, iid=0: {"fv": False, "wall": None, "yel": 0}
        eh.ns.enter_match_v2 = lambda i, verbose=True: self.calls.append("enter") or True
        self.assertFalse(eh.ensure_entry(0))
        self.assertEqual(self.calls, ["relaunch", "enter"])


if __name__ == "__main__":
    unittest.main(verbosity=2)