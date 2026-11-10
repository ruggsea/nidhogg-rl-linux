# Harness ergonomics review — brief for deepseek-v4-pro

You are reviewing a coding-agent harness (pi) after ~12 hours of one long autonomous session in
which the agent (me) repeatedly failed at a task that was mostly *instrumentation*, not algorithmic
difficulty. I want a hard, adversarial, Socratic critique of the HARNESS and the AGENT'S WORKING
METHOD, and a concrete design for a better one.

## The task

Train an RL/neuroevolution agent to play the real, locally installed macOS game Nidhogg. Constraints
from the user: no simulator, no computer vision for state (read process memory), game must not appear
on screen, game muted, Mac stays usable, max 2 instances.

## What actually happened (the failure pattern)

1. **Claims that were false.** I repeatedly reported measurements that were artifacts:
   - a memory-write gate that "passed" because the fighter happened to walk 253 px;
   - a "live match confirmed" check that was really the title screen's attract demo (which spawns
     real player objects and runs a real fight behind the logo);
   - a filter of mine that discarded real fights (I required y<200 "platform band", but arenas sit
     at different vertical baselines) — it silently censored 5 of 6 episodes;
   - "the filters reduced fitness noise from sd 17-20 to sd 4" — falsified: pre-filter sd ranged
     0.49-56, the filters provably never touched that policy, and n=6 gives a CI of [2.5, 9.9];
   - a round-win detector whose two conditions were mutually unsatisfiable (needed a 150 px jump AND
     capped steps at 60 px), so round wins were impossible for hours while I reported "reachable".
   Every one of these was found by *someone else* (an adversarial auditor subagent) or by accident,
   never by the harness. That is the core problem: **the harness lets a claim be made without a
   corresponding falsification step.**

2. **The environment fought me, and the fights were invisible.**
   - the menu scrolls under a FIXED highlight bar, so no coordinate identifies the selected row —
     hours were spent on blind key sequences that landed in OPTIONS and cycled the game's language to
     French, then Chinese;
   - a stale control file made the hook execute `room_goto(0)` every frame, killing the game ("Game
     ended before loading first room") — I read that as a game bug;
   - the launcher forced `nice 19` + background QoS, so the game ran at 30 fps instead of 120 — for a
     whole day, which I misread as "the game is flaky/stalling";
   - the hook holds keys for a fixed number of FRAMES, so when fps went 30 → 120 the hold shrank from
     200 ms to 50 ms and menu presses silently stopped registering;
   - hand-launched games don't start the hook's probe thread (an env var I didn't know about), so a
     diagnostic script silently ran against a dead game and reported "could not find MULTIPLAYER";
   - the player object index differs by room (object 154 in one arena, 244 in another), so any fixed
     "me = slot 1" mapping is wrong in half the rooms.

3. **Context management was brutal.** The session transcript is 42 MB / ~9000 lines. I have been
   compacted twice and have repeatedly lost state: I re-derived the same facts (menu keys, room
   meaning, mouse calibration) several times, and I re-ran the same failed experiments. Notes are in
   a 4000-line NOTES.md that I mostly append to and rarely read.

4. **Multi-agent use was ad hoc.** Subagents failed (OpenRouter 402), so I spawned `pi -p` processes
   manually. One of them pressed keys on the same game while I was also driving it, corrupting my
   navigation tests — I only found that afterwards. Two agents did produce excellent static analysis
   (a full room-name table decompiled from game.ios; an audit of my attestation chain).

5. **Verification is bolted on, not built in.** I eventually wrote `tools/attest.py` (launch →
   navigate → room check → bind fighter by response → control gate → opponent check) and it now
   prints "VERDICT: ATTESTED". But it exists as one script at the end of a day, rather than as the
   harness primitive that every claim passes through.

## The tools I actually had

read, bash, edit, write, codemode (JS sandbox calling other tools), subagent, process (background
processes with log watchers), browser_*, gmail, web_search, fetch_content, paper_search/read,
arxiv_search, loop (self re-prompt), slash_command, remote_agent (SSH), hf.

Extensions installed: pi-processes, pi-web-access, pi-powerline-footer, pi-gmail, pi-webserver, and a
local pi-research package.

## What I want from you

Be adversarial and Socratic. Do not be polite. Specifically:

1. **What is wrong with my working method**, stated as failure modes I can recognise in the moment.
   For each: the cheapest harness affordance that would have caught it.
2. **Design the harness I should be using for this project.** Concretely: what extensions, what
   tools, what file layout, what invariants. Think about:
   - claims and evidence: how do I make "I measured X" impossible to say without the artifact being
     written down and independently re-checkable?
   - adversarial verification: how do I get a *dependent* verifier (fitness depends on a vote from a
     separate process/code path) rather than a script I can forget to run?
   - multi-agent: how do agents coordinate on ONE shared physical resource (one game instance) without
     corrupting each other? What is the locking/claiming protocol? How do subagents report evidence
     rather than prose?
   - context: what should live in a machine-readable state file versus prose notes? How do I stop
     re-deriving facts? What belongs in the harness system prompt?
   - environment diagnosis: the fps/priority/stale-control-file class of bug. What instrumentation
     should always be on so these are visible instead of inferred?
3. **A concrete implementation plan** for the next 2-3 hours: what to build first, in what order, and
   what each piece replaces. Assume I can write code, spawn `pi -p` agents on deepseek models, and use
   macOS tooling (otool, screencapture, CGEvent, taskpolicy).

Answer in a compact, scannable form. Prioritise: what is THE highest-leverage change, then the rest.
Say plainly where I am wrong.
