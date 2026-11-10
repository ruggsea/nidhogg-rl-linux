Tick of the nidhogg loop (workers on artemis, next to the game).

1. `python3 tools/plan.py next` — the step you are on. Read `loop/roles/<your role>.md` for your focus.
2. Work the step HARD: run as many experiments as it takes inside this turn. Do not stop after one probe
   just to report — that is what made progress slow. Stop when the step is CLOSED with evidence, or when
   you are genuinely blocked by something you cannot fix.
3. Close with `python3 tools/plan.py done <id> --evidence <path|cmd>`; every number via
   `python3 tools/claim.py record "<text>" --cmd "<reproducible cmd>" --falsifier "<what would refute it>"`.
4. Append 4 lines to loop/PI_TICKLOG.md: step / result / measured / next.
5. End your turn when the step is closed or blocked, so the loop can re-prompt you.

Hard rules: never report a win rate (rounds_won is 0, no round transition has ever been observed); control
gates need 40/30 px of movement, not just the right sign; never `find /` or `grep -r` on artemis (14 TB,
load 100-200); check the game with `pgrep -x Nidhogg.exe`, not `pgrep -f`; state comes from the LD_PRELOAD
spy, /proc/<pid>/mem is blocked here. If you are a second worker, coordinate through state/mail/ and the
plan lock — do not close the same step as another worker.
