The review is written to `docs/HARNESS_REVIEW.md` (where `loop/CONTINUE.md` already expects it). Here it is.

---

# Harness ergonomics review — nidhogg-pau

Your premise is one sentence too late. You asked what harness you *should* build. You already built it: `claim.py`, `gameslot.py`, `doctor.py`, `check_env.py`, `facts.json`, `.pi/agents/goldfish.md`, `loop/CONTINUE.md`. Each one documents, in its own docstring, the exact failure that motivated it. The problem is not missing tools. It's that they are all optional, and options get skipped.

Proof from the repo right now:

- `state/claims.jsonl` has **2 entries, recorded the same second, both trivial** ("the game binary exists", "29 is an arena"). A demo, not a ledger. None of the claims that cost you the day entered it.
- `state/gameslot.json` holds `"purpose": "holder test"`. A test entry. The tool was never used against a real conflict, because it was written after the conflict.
- `doctor.py` reports nice=0, 160 fps, room 20. It works, it's right, and it was written at hour ~11.
- `grep` shows `gameslot.py` and `claim.py` are called from nowhere except docs and `CONTINUE.md`. `doctor.py` is called by one script. **None of the three is in the training loop or the input path.**

So the highest-leverage change is not a new tool. It is one sentence: **a number cannot be reported, and the loop cannot advance, unless it is a claim that passed the claim primitive, and the primitive itself contains a falsification step.**

## The one field that was missing

`claim.py` records (text, cmd, sha) and `verify` re-runs the cmd. That detects DRIFT: the world changed or the claim was never true at record time. It does **not** detect a false measurement of the wrong thing. The 253px gate, the "sd 4" from n=6, the mutually-unsatisfiable round detector: all would `verify` OK forever, because the cmd that produces each one measures the wrong proxy.

A claim needs a **null experiment** ("what would I observe if this were false, and did I observe it instead") and, for numeric claims, **n and a CI**. `record` refuses a numeric claim without `--null` and `--n`. `verify` then re-runs the cmd (drift) *and* evaluates the null (falsification). This single addition is the only thing in this review that would have caught the false-positive claims on its own.

## Failure modes, cheapest affordance, current status

| Failure mode | Cheapest affordance | Status |
|---|---|---|
| Proxy reported as target (253px, demo, sd-4) | `--null` + n/CI in claim; record refuses without them | claim.py exists, lacks the field. **This is the gap.** |
| Censoring filter, no reject ledger (y<200) | filter writes rejects + counts to disk; sample eyeballed | no mechanism, a prose rule. Add `--rejects`. |
| Mutually-unsatisfiable detector | golden fixtures; detector must pass gold before scoring | no `gold/` dir. check_env.py tests the seed policy only. |
| n=6 as sd 4 (CI [2.5,9.9]) | claim carries n+CI; report refuses without them | same as row 1. |
| Invisible environment (nice19, stale cmd, NID_THREAD, frame-hold) | doctor run first; loop blocked while health != PASS | doctor.py is correct but not gated on. |
| Re-deriving facts (2 compactions) | facts.json + `fact` command that errors on duplicates | facts.json is good; no guard, no mechanical read-first. |
| Two drivers, one car | gameslot enforced at the input path | gameslot.py not wired into the hook/key-writers. |
| Verification bolted on | attest emits a claim, not a stdout line | attest prints VERDICT, writes out/ATTESTED; no ledger entry. |

## Where you are wrong

1. **Wrong that the harness "lets a claim be made without a falsification step."** You built the step. You built it as an *option*. The free path — a sentence in chat or NOTES.md — still costs nothing, so you kept taking it. Stop building tools; make the free path unavailable.

2. **Wrong that "the environment fought me and the fights were invisible."** The priority was in `ps -o nice,pri` all day. The frame rate was in the hook counter. The room was published every frame. The stale command file was a file in /tmp. None of it was hidden. You inferred behavior from outcomes instead of reading state, repeatedly, for a day.

3. **Wrong that the answer to context is more context.** 42 MB of transcript and 5000 lines of NOTES is the disease. You re-derived facts because you kept a narrative, not a store. facts.json only works if reading it is the first mechanical act of every tick, not a suggestion in CONTINUE.md.

4. **Wrong to trust your summary of a subagent.** The corrupting agent was invisible until after the damage. A subagent reports a claim id + sha and the orchestrator verifies; it does not report prose you believe.

5. **Wrong that "ATTESTED" closes the loop.** It's a stdout line and a file, stale in ten minutes. A verdict not in the ledger with a re-runnable command is the fifth false claim waiting to happen.

## Implementation plan, next 2–3 hours (ordered by leverage)

1. **(30 min) claim.py v2**: `--null`, `--n/--ci`; refuse numeric claims without them; `attest.py --claim` writes the verdict into the ledger. Replaces the "gate passed / sd 4 / reachable" prose. **Highest leverage.**
2. **(30 min) `loop/TICK.sh`**: per tick run doctor (block if not PASS), check gameslot, require reported numbers to be claims. Turns CONTINUE.md from a document into a gate.
3. **(30 min) `gold/`**: freeze 3 hand-labeled traces (real match, real round win, title demo); detectors must pass gold before scoring.
4. **(30 min) goldfish scheduling**: loop invokes the goldfish on each new claim, stores the verdict, report.py reads claims not prose.
5. **(30 min) gameslot enforcement** in the input writers + `fact` duplicate-guard + doctor `--diff`.
6. **(30 min) migrate prose facts into facts.json**, trim NOTES.md to decisions, wire the loop driver to consume it.

## Questions to ask in the moment

- What would I observe if this claim were false? Have I run that, and what did it show?
- Am I measuring the thing, or a proxy of it? What's the null?
- Did what I just did change the environment invisibly? What does `doctor.py --diff` say?
- Is this fact already in facts.json? Then why am I re-deriving it?
- Who holds the gameslot? Do I?
- Would this survive a fresh-context agent whose only job is to refute it?
cmd (drift), evaluate null
(falsification), re-run golden fixtures (detector sanity). Every number that feeds fitness or a user
report is a claim; report.py and the README fitness curve read only from state/claims.jsonl.

**Adversarial verification.** The goldfish subagent exists (`.pi/agents/goldfish.md`,
deepseek-v4-pro). What is missing is scheduling: the loop driver invokes it on each new claim with
only (claim + artifact path), stores the verdict on the claim, and the fitness loop only advances a
claim that a separate path did not falsify. The dependent property: the verifier did not produce the
measurement, has no stake in it passing, and may not accept files the claim itself wrote
(goldfish.md already forbids this).

**Multi-agent.** One game, one writer. gameslot.py is correct; the missing piece is enforcement at
the point of writing: the launcher, nav3.py, attest.py, and any key/click writer acquire the slot
before touching /tmp/nid_keys_* or /tmp/nid_click_*, and refuse otherwise. Subagents default
read-only (goldfish already is). A subagent that must drive gets a second game instance (second
slot) or explicitly leases the first. A subagent final message is a claim id + sha, not narrative.

**Context.** Machine-readable: facts.json (exists), a `fact` command that errors on a duplicate key,
and the loop's tick-0 mechanical action of reading facts.json. Prose: NOTES.md becomes a
decisions-only log (decision + one-line reason). The re-derivation guard is the `fact` command
erroring, not a reminder.

**Environment diagnosis.** doctor.py is the right instrument and already writes state/health.json
with an `overall`. Two upgrades: run it at the top of every tick and block training while overall !=
PASS; add `--diff` against the previous snapshot so a change (fps halved, nice flipped, room_cmd
reappearing) surfaces as a delta instead of an inference three hours later.

**Harness system prompt.** loop/CONTINUE.md is already 90% of it. Promote it to the actual loop
driver script, so its rules are executed, not read.

## Implementation plan, next 2-3 hours

Ordered by leverage. Each line names what it replaces.

1. (30 min) claim.py v2: add `--null`, `--n/--ci`; refuse numeric claims without them;
   `attest.py --claim` writes the verdict into the ledger. Replaces: the "gate passed / sd dropped
   to 4 / reachable" prose claims. Highest leverage.
2. (30 min) `loop/TICK.sh`: per tick, run doctor.py (block if not PASS), check gameslot (do not act
   while held by a live pid), and require any reported number to be a claim. Turns CONTINUE.md from
   a document into a gate. Replaces: the "run doctor when something looks wrong" convention.
3. (30 min) `gold/`: freeze 3 hand-labeled traces (real match, real round win, title demo); a
   detector must pass gold before scoring. Replaces: the mutually-unsatisfiable round detector and
   the censoring filter being trusted unread.
4. (30 min) goldfish scheduling: the loop invokes the goldfish on each new claim; verdict stored on
   the claim; report.py reads claims not prose. Replaces: "I trusted my own summary of the run."
5. (30 min) gameslot enforcement in the input writers + `fact` duplicate-guard + doctor `--diff`.
   Replaces: the two-drivers-one-car hazard and re-derivation.
6. (30 min) migrate remaining prose facts into facts.json, trim NOTES.md to decisions, write the
   loop driver to consume it. Replaces: the 5000-line notebook as memory.

## The questions to ask in the moment

- What would I observe if this claim were false? Have I run that, and what did it show?
- Am I measuring the thing, or a proxy of the thing? What is the null?
- Did what I just did change the environment invisibly? What does doctor.py --diff say?
- Is this fact already in facts.json? Then why am I re-deriving it?
- Who holds the gameslot? Do I?
- Would this claim survive a fresh-context agent whose only job is to refute it?
