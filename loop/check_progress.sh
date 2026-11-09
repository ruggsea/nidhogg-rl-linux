#!/usr/bin/env bash
# check_progress.sh — thin wrapper: the check runs on artemis, where the state lives.
# Emails only on a milestone (see tools/milestones.py); silent otherwise.
set -uo pipefail
ssh -o BatchMode=yes -o ConnectTimeout=20 -o ControlMaster=no artemis \
  'cd ~/nidhogg-pau && bash loop/check_progress_remote.sh' 2>&1 | tail -20
