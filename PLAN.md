# PLAN


0/10 steps done.

Rendered from `state/plan.json` by `tools/plan.py`. Do not edit by hand.

- [>] **01** Attestation passes consistently (3 consecutive runs)
      accept: tools/attest.py prints VERDICT: ATTESTED three times in a row - and each run must include the DOSE-RESPONSE check (holding D 3x longer must move the fighter ~3x further). The direction gate alone can be satisfied by the title screen's attract demo by coincidence; proportionality cannot. All runs appended to state/attest_runs.log.
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
