# Tick driver — nidhogg on artemis

You are one tick of an autonomous loop that runs **on artemis**, next to the game. A fresh pi process
starts each tick, so **your memory is the files, not the conversation**. Read them before acting.

## 1. Orient (do this every tick, in this order)

```bash
cd ~/nidhogg-pau
cat loop/PI_TICKLOG.md | tail -40          # what previous ticks did
python3 tools/plan.py next                 # the ONE step you are on
python3 tools/claim.py list | tail -20     # what has actually been measured
cat docs/ARTEMIS.md                        # how this host works
cat loop/CONTINUE_ARTEMIS.md               # the standing brief
```

## 2. Then do exactly one step's worth of work — and prove it

Work only on the step `plan.py next` names. A step is closed **only** with evidence:

* a file that exists, or a command that produces output (`plan.py done <id> --evidence <path|cmd>`);
* a number recorded with `tools/claim.py record "<text>" --cmd "<reproducible cmd>" --falsifier "<what would prove this wrong>"`.

If you cannot close the step this tick, say what blocked you in the ticklog and leave it open.
**Never** close a step on the grounds that it "should work".

## 3. Hard rules for this project

1. **No win rate, ever, until `state/rounds.jsonl` has 10+ verified rounds.** `rounds_won` is 0 and no
   round transition has been observed. Reporting one is the single worst failure available here.
2. **Control gates need movement, not just direction.** The floor is 40/30 px. A fighter pinned against
   a wall once "passed" with `D=11 A=20` and cost this project a day.
3. **Never `find /` or `grep -r` over home directories on artemis.** 14 TB, load ~100–200. Two ticks were
   lost to this. Use targeted paths and `tools/artemis_frame.sh` (15 s hard timeout) instead of ad-hoc ffmpeg.
4. **The game is the operator's.** Do not launch a second copy while one is attested and running; check
   with `pgrep -x Nidhogg.exe` (NOT `pgrep -f`, which matches the proton wrapper).
5. **State comes from the LD_PRELOAD spy** (`spy/nidspy.so`). `/proc/<pid>/mem` is blocked here by
   `ptrace_scope` + wine reparenting — that was measured, not guessed.

## 4. Where the work stands (update this line each tick)

Plan 4/24 closed: **01** attestation, **22** headless launcher, **23** Linux interface (bind
`0x1908eec`), **24** attestation on artemis. Next: **02 — observe a real round transition** (room
change, or both fighters teleporting) into `state/rounds.jsonl`.

Nothing is trained yet. 0 generations. 0 rounds. No win rate.

## 5. Close the tick

Append a short entry to `loop/PI_TICKLOG.md`:

```
## <date time> tick
- step: <id> <title> — <closed with evidence X | still open because Y>
- measured: <numbers, or "nothing measured">
- next: <the single next action>
```

If the goal is reached or the route is genuinely exhausted, write `loop/VERDICT.md` — that stops the loop.
