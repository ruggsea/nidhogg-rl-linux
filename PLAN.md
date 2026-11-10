# PLAN


3/24 steps done.

Rendered from `state/plan.json` by `tools/plan.py`. Do not edit by hand.

- [!] **01** Attestation passes consistently (3 consecutive runs)
      accept: tools/attest.py prints VERDICT: ATTESTED three times in a row - and each run must include the DOSE-RESPONSE check (holding D 3x longer must move the fighter ~3x further). The direction gate alone can be satisfied by the title screen's attract demo by coincidence; proportionality cannot. All runs appended to state/attest_runs.log.
      evidence: `state/attest_runs.log`
      reason: Game bug in build 108 (built 10/30/2026): no route reaches a live CPU match — TRAINING+ARCADE crash on entry, -net* frozen no-Brain, -lt* exhausted. Claims 641721dc 5a8c8d76 fb99568e. Manager decision pending (game update / binary patch / re-scope). Step 02 does NOT need a live CPU and stays open.
- [ ] **02** Observe a real round transition in memory
      accept: game.rounds() reports the same transition kind twice, with the room change or teleport logged in state/rounds.jsonl
- [ ] **03** Wire the verified round signal into the reward
      accept: train_win.py pays a round term only when the observed transition fires; a claim.py entry proves the term changed a fitness value
- [ ] **04** Run 3 full generations without restarting the trainer
      accept: three '== gen N best' lines in one run log, with per-generation claim rows
- [ ] **05** Establish whether any policy beats another at >=2 sigma
      accept: summarize.py output showing a >=2 sigma gap, recorded as a claim with its command
- [ ] **06** Win a round against the CPU, verified
      accept: a round transition with us as the winner, corroborated by two independent signals
- [ ] **07** Measure a win rate over >=10 verified rounds
      accept: evaluate.py over >=10 rounds, recorded as a claim
- [ ] **08** WSP-style weight analysis + hand-edited policy comparison
      accept: layer dump, reasoning, hand-edited variant scored head-to-head
- [ ] **09** Human-vs-agent demo
      accept: play_vs_agent.sh run with the trained policy, outcome recorded
- [ ] **10** Full-arc video
      accept: video built, covering failures→fixes→training→result
- [ ] **11** Verify the observation is physically meaningful in every arena
      accept: obs_vector recorded from three different rooms; every component inside [-1,1] except y/600 which must stay in [0,1]; no feature may depend on a per-room constant. Recorded via tools/claim.py.
- [ ] **12** Decide the reward question with numbers, not taste
      accept: the fitness has a measurable gradient: >=2 sigma separation between a scripted pusher and an idle policy at the current reps, recorded as a claim with its command.
- [ ] **13** Scale to N parallel game instances once 01-04 are green
      accept: N>=2 instances running via InstanceManager(iid=i), aggregate throughput measured and claimed; only start this after attestation, round signal and 3 generations have passed.
- [ ] **14** Generalize across ARENAS, not one room
      accept: matches recorded in >=3 distinct arena groups (castle 26-33, mines 43-52, sky 53-60, wilds 61-68, cemetery 70-77), with per-arena-group fitness reported. The room index is already published, so this is bookkeeping plus enough episodes.
- [ ] **15** Curriculum: vary the TRAINING partner type
      accept: the partner list is reachable by keys (NO DIVEKICKS / NO THROWS / DIVEKICKER / RUN N LUNGE / BRAWLER / NEVER LUNGES / PARRY MASTER / RANDOM); a policy is trained against a rotating partner and its fitness is reported per partner, so it cannot overfit one opponent.
- [ ] **16** Adaptive difficulty curriculum: raise the level when the current one is mastered
      accept: the level is raised by tools/curriculum.py on evidence, never on a schedule: either a VERIFIED win signal at the current level (needs the round signal, today unavailable), or a fitness plateau over 3 generations that is below the measured noise floor. The level, every change and its reason are recorded in state/curriculum.json, and per-level fitness is reported. A policy that only wins at the level it was raised to has not generalized.
- [ ] **17** Prove the SWORD state (in hand / thrown) and add it to the observation
      accept: sword state established by the distance oracle (sword-to-body small => held, large/absent => thrown), proven in both states with two independent routes where possible (sibling record at body+0x400 and a sword-sized instance near the body). Only then add one input slot and say which existing slot it replaces - the input width is 8 and changing it invalidates weights.
- [ ] **18** Research and execute the ARTEMIS route (Pau's Linux lead), credential-safe
      accept: read docs/DEPLOY.md + INTERFACE.md and Pau's NEXT_STEPS for the Linux assumptions, then on artemis: steamcmd installed and logged in as rug125 (password read from the macOS Keychain at run time, never committed or echoed), Nidhogg (appid 94400) downloaded, wine/proton + Xvfb + xdotool installed or extracted user-space, game launches headless and publishes a room index. Evidence: a transcript of the commands and the room file. NO password may appear in the repo, a commit, a log, or an agent message.
- [ ] **19** Attest a real match ON ARTEMIS
      accept: tools/attest.py runs there against the headless instance and prints VERDICT: ATTESTED with dose-response and >=40/30 px displacement. This is the gate for using the farm at all.
- [ ] **20** High frame rate with no visible window (headless/occluded)
      accept: measured fps >=100 with the window hidden or the screen asleep: identify the throttle (App Nap / occlusion / CVDisplayLink tied to display) and defeat it, either by disabling App Nap for the process and keeping a real display link, or by driving the game's step function from the hook at a fixed rate. Record fps before and after as a claim with its falsifier - the current parked figure is 24-30 fps vs 120-320 visible.
- [ ] **21** Farm: >=2 parallel attested instances on artemis
      accept: N>=2 instances (InstanceManager(iid=i)) attested simultaneously with aggregate throughput measured, and per-instance room/arena recorded so generalization data accumulates from the start.
- [x] **22** Robust headless launcher on artemis (verify, don't assume)
      accept: a launcher that starts Xvfb + the patched game under Proton and PROVES it: process alive, log written, a frame grabbed from the display, then returns non-zero if any check fails. The last detached launches left no process and no log, so this is the first blocker.
      evidence: `./tools/launch_linux.sh :99`
- [x] **23** Port the interface to Linux: /proc/<pid>/mem state + xdotool input
      accept: bind the fighter by response on Linux (hold d -> a float32 slot moves right, hold a -> it moves left), and drive keys with xdotool against the per-instance Xvfb display. Record the bound address and the measured displacement as a claim. This replaces the macOS dylib entirely.
      evidence: `python3 tools/bind_measure.py 0`
- [x] **24** Port doctor/game/attest to Linux and pass attestation ON artemis
      accept: tools/doctor.py --gate passes on Linux paths, and tools/attest.py reaches VERDICT: ATTESTED there with dose-response and >=40/30 px displacement. Nothing is trained on the farm before this.
      evidence: `python3 tools/attest.py`
