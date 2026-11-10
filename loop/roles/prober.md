# Role: prober

You run game experiments; you do not edit the plan.

- Your job is measurement: run the probe, report numbers, write results to `state/probes/<topic>.jsonl`.
- Post findings to `state/mail/engineer.md` (append) so the engineer can close steps.
- The game is shared: check `python3 tools/gameslot.py status` before driving it. Never launch a second
  instance if one is attested and running.
- Entry is the current blocker. Keys: BOTH W/S and Up/Down move the menu cursor (the "arrows ignored"
  claim was retracted at 11:52). Selection is a GREY HIGHLIGHT BAR behind one text row (NOT a yellow dot).
  Live-match checkpoint = opponent_moves(>=8px/3s) AND drivable (find_fighter binds by response): the
  READY screen passes drivable only, the title attract-demo passes opponent_moves only; only a real
  TRAINING match passes BOTH. Preferred sequence (Pau's enter_live_match): Return->menu, Up->SINGLE
  PLAYER, Return, Return->TRAINING ladder, 4x Down->BEGIN, Return. NEVER press Return again once a match
  starts (Enter pauses/ends it). Fallback: Return, W, Return, S, Return, Return, Return (7 keys). Report
  per key: selected row (menu_rows_linux.py) + drivable + opponent_moves.
- ROOM TABLE (decompiled from game.ios, data.win byte-identical): 1=rLogos, 2=rMainMenu, 3=rMultiMenu,
  17=rLevelSelect (arena/level picker), 25=rPreMatch, 26-77=arenas. The 11-row list you hit after
  SINGLE PLAYER -> TRAINING is most likely rLevelSelect(17): macOS measured "Enter at 17 = match being
  set up". So: on that list press Enter ONCE on a selection, then verify find_fighter AND opponent_moves
  (a live arena), and STOP pressing keys. The trailing Returns in the 10-key SEQ are what land you in a
  list instead of a match.
- Record every probe with `claim.py record` including its falsifier.

# LATEST ENGINEER GUIDANCE (2026-11-09 16:30) — test these FIRST, they may skip the whole menu

1. MENU-BYPASS FLAGS. The build ships a developer net_test harness. Try relaunching the game with a
   command-line flag instead of walking menus:
       NID_GAME_ARGS="-netarcade" ./tools/launch_linux.sh :99     # logs "starting a local arcade match from the title screen" = auto player-vs-CPU
   Also available: -netpersonality N, -netdiff N, -netai, -netlevel training|arcade|tourney|tourneysim,
   -netmainmenu, -netsolo, -lttraining. launch_linux.sh now passes NID_GAME_ARGS through to the exe.
   After launch, check ls.opponent_moves_sustained(opp) as usual. This may beat the whole menu walk.

2. CONFIRMED TRAINING FLOW (if the flags are dead). From the game's own localtest strings the TRAINING
   menu order is: personality list -> AI difficulty window -> map select -> faceoff, and the CPU brain
   ("fighter 1 has a Brain") is created ONLY after walking all of it. Your clean S+Return skips
   personality + difficulty + map, which is exactly why the opponent stays frozen. So after entering
   TRAINING: pick a personality (W/S + Return), then move the AI DIFFICULTY SLIDER with A/D (it is a
   slider, NOT an S-navigated row), then confirm through map select, then START.

# ENGINEER ADDENDUM (16:47) — TrainingMenu has NO Step handler + the game can tell you its keys

1. data.win STRG has gml_Object_TrainingMenu_Create_0 (8 item structs 294-301) but NO
   TrainingMenu_Step_0/2 — the menu's input is NOT in a Step event (MainMenu DOES have Step_0). So stop
   expecting a single "confirm" key; the items themselves (or a parent) handle input. Your A/D =
   difficulty-slider observation fits: W/S = vertical row focus, A/D = adjust the focused slider.
2. The START/BEGIN row is at the BOTTOM of the menu (earlier note: "4x Down -> BEGIN"). Keep pressing S
   until the highlight reaches the bottom rows (difficulty -> map -> start) and note what each row's
   A/D and Return do per row.
3. BEST LEAD — make the game reveal its own keys: run the built-in localtest and read localtest.log.
   The harness has lt_press/lt_wait helpers and checkpoints 'training list' -> 'difficulty window' ->
   'training_window' -> 'training_faceoff' -> 'fighter 1 has a Brain'. Launch with -lttraining (training
   teams, 2v2) or -localtest and read ~/nidlogs/.../localtest.log (it logs every key it presses). Even
   if 2v2, the logged key sequence is the exact TRAINING menu walk for 1v1 too. Also try -netlevel
   training (values training|arcade|tourney|tourneysim).

# ENGINEER ADDENDUM (16:58) — localtest.log LOCATION corrected + what a probe found

1. 'localtest.log' is a RELATIVE filename (string 4029 in the STRG table, tool: tools/strg_dump.py),
   so it lands in the GAME'S CWD under proton, NOT ~/nidlogs. Search THESE paths (bounded, never
   `find /`): ~/nidfarm/game/, ~/nidhogg-pau/ (launch cwd), ~/nidpfx/drive_c/users/steamuser/.
   The lt_ inventory is confirmed: lt_press / lt_nav / lt_pressUntil / lt_wait / lt_log / lt_capture /
   localTestInit (all gml_Script_*@net_test).
2. Engineer probe (16:54): NID_GAME_ARGS=-lttraining launched and rendered (UP AND RENDERING,
   brightness 55), but NO localtest.log appeared within ~50s. So the harness does NOT auto-run at boot;
   like -netarcade it likely triggers AT THE TITLE SCREEN ('starting a local arcade match from the
   title screen'), and my instance got killed before it got there. When you run it: wait for the title
   (room 2), give it ~30s more, then search the paths above for localtest.log.
3. Coordination note: I (engineer) accidentally launched the game at 16:54 while you were mid-cycle and
   we collided — your relaunch (16:57, no args) killed my -lttraining instance. Slot is now FREE.
   I will not drive the game; that is yours. If you need the slot, `gameslot.py acquire prober`.

# ENGINEER ADDENDUM (18:1x) — TOOLING FIXED + -netai confirmed dead, retry with fixed tools

1. TOOLING FIXED (in tools/linux_state.py, claim recorded):
   - find_opponent NO LONGER filters on `abs(y - p1y) > 40` (that filter returned None whenever P1's y
     was off the ground line, making opponent_moves unmeasurable). Now it picks the nearest OTHER
     0x200-strided +0xEC fighter by x-separation (min 20px apart).
   - find_fighter now scores candidates on SCAN-TIME samples (no re-reading memory, which used to return
     denormals like -1.4e30 / 0xff33950) and requires a real position: A>1, |A-C|<30 (returns to the
     same spot), and a STABLE y (10<y<300, |dy|<20 across samples). This rejects the key-state/timer
     slots (A=0, B=nonzero, C=0) that were being bound as "fighters".
   Re-run your verify_live.py / sustained checks against the fixed tools before trusting any
   opponent_moves result.

2. CONFIRMED on the live -netai instance (:100, pid 7348): fixed find_fighter returns **None** — there
   is NO drivable fighter right now. -netai is a dead end (the frozen no-brain match). DROP it.

3. The real route to a live CPU is unchanged: TRAINING with the FULL walk (personality -> AI DIFFICULTY
   slider via A/D -> map -> START), which is the only thing that calls createBrainForPlayer. Or the
   -netarcade + -netpersonality/-netdiff menu-bypass flags. Or -lttraining (wait for title, then ~30s
   for localtest.log in the game cwd). My earlier bind test nudged a/d on :100; treat that instance as
   dirty and relaunch fresh for your next probe.

# ENGINEER ADDENDUM (18:3x) — THE HARNESS REACHES REAL MATCHES; run -lttraining to completion

1. BREAKTHROUGH (claim recorded): the game's OWN localtest harness drives the full menu on artemis.
   - NID_GAME_ARGS=-localtest runs a 478-step script, 53 PASS / 0 FAIL, reaching real arenas
     (rWildsCenter, rMinesCenter) and a full double-elim tournament. Saved: state/probes/localtest_full_run.log.
   - NID_GAME_ARGS=-lttraining is the TRAINING flow: 'start: training teams' -> 'do TRAINING' ->
     'training list' -> 'difficulty window' -> rLevelSelect (map). Its NEXT checkpoints (from data.win
     STRG, strings 4305-4312) are: training_window -> "four fighters at the faceoff" -> "training 2v2:
     teams on, the player alone without a Brain" -> "fighter 1 has a Brain" -> training_faceoff.
     So: 2v2 training = the PLAYER is drivable and 3 CPU fighters carry brains. That is the live-CPU
     match we need to attest.

2. DECISIVE EXPERIMENT (your lane): run `NID_GAME_ARGS="-localtest -lttraining"` (or just `-lttraining`)
   on a CLEAN instance — the last try died at rLevelSelect after 5.7s, almost certainly a PREFIX
   COLLISION (two instances on prefixes/1), NOT a real stall, because the -localtest default navigates
   rLevelSelect fine. Before launching: pgrep -x Nidhogg.exe must show you have exactly one instance
   (kill the stale -netai :100 pid if it is yours to kill). Then:
   a. let it run to completion (>=3 min), SAVE the full log to state/probes/lttraining_full_run.log;
   b. while it runs, every ~15s probe find_fighter() + find_opponent() + opponent_moves_sustained() and
      record which checkpoint (the log line) corresponds to a drivable fighter AND a moving opponent;
   c. the moment you see "four fighters at the faceoff" / "fighter 1 has a Brain", run attest_linux.py
      against that instance (fixed tools from my last tick: find_fighter no longer garbage-binds).
   Report the room + whether opponent_moves_sustained ever goes True.

3. If -lttraining also stalls at map select, capture the EXACT last log line and tell me — then I
   reverse the map-select key from the exe (net_cmd.txt / lt_press arg) rather than guessing.
