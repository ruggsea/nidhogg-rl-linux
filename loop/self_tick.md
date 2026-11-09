Tick of the nidhogg loop (you are on artemis, next to the game).

1. `python3 tools/plan.py next` — the ONE step you work on.
2. Do one step's worth of work. Close it ONLY with evidence: `python3 tools/plan.py done <id> --evidence <path|cmd>`, and record any number with `python3 tools/claim.py record "<text>" --cmd "<reproducible cmd>" --falsifier "<what would prove it wrong>"`.
3. Append 4 lines to loop/PI_TICKLOG.md: step / result / measured / next.
4. Check `loop status`; if the goal is reached or the route is genuinely exhausted, `loop stop` and write loop/VERDICT.md.

Hard rules: never report a win rate (rounds_won is 0, no round transition has ever been observed); control gates need 40/30 px of movement, not just the right sign; never `find /` or `grep -r` on artemis (14 TB, load 100-200); check the game with `pgrep -x Nidhogg.exe`, not `pgrep -f`; state comes from the LD_PRELOAD spy, /proc/<pid>/mem is blocked here.
