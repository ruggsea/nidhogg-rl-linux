
## Reset by writing x/y (2026-11-25)
- Pau's own reset test (scripts/reset_test.py, his main, unmodified) FAILS 8 of 8: every write snaps back within 0.35 s. Our place() runs are labelled "not Pau's reset". Paper sentence: "We could not reset episodes by writing fighter positions; the game restores them within 0.35 s, so episodes are bounded by the round instead."
