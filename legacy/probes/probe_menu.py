#!/usr/bin/env python3
"""probe_menu.py — instrument menu navigation on artemis: after each keypress,
report the menu state (text rows + selected row) so entry can be mapped step by step.

    python3 tools/probe_menu.py                 # just read the current screen
    python3 tools/probe_menu.py Return w Return  # press keys in order, report after each

Prints, for each step: the keysym, and the menu_rows() reading (text rows in game
space, background brightness, selected row). No OCR, no keys are pressed unless named.
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import nid_linux as n
import menu_rows_linux as mr


def show(tag):
    rows, scored, sel = mr.menu_rows()
    if not rows:
        print(f"[{tag}] no menu rows (title/attract or non-menu)")
        return
    parts = []
    for i, (a, b) in enumerate(rows):
        mark = "*" if i == sel else " "
        parts.append(f"{i}:y{a//2}-{b//2}(bg{scored[i]:.0f}){mark}")
    print(f"[{tag}] " + "  ".join(parts))


def main():
    keys = sys.argv[1:]
    show("start")
    for k in keys:
        n.key(0, k, hold=0.12)
        time.sleep(2.5)
        show(k)


if __name__ == "__main__":
    main()
