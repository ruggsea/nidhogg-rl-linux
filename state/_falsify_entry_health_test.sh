#!/bin/bash
# Falsifier: non-zero when the entry_health test claim HOLDS (the tests pass).
cd "$(dirname "$0")/.."
if python3 -m unittest code_pau.tools.entry_health_test >/dev/null 2>&1; then
    exit 1
fi
exit 0