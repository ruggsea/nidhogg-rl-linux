#!/bin/bash
# Claim: the entry_health gate unit test passes via `python3 -m unittest` (no game, no display).
set -e
cd "$(dirname "$0")/.."
python3 -m unittest -v code_pau.tools.entry_health_test