# Audit: "the direction gate proves we control the fighter, because D moves it right and A moves left"

## Verdict: FALSIFIED

The premise ("D moves it right and A moves left") does not establish the conclusion ("we control
the fighter"). The repository's own records contain a direct counterexample to the inference, and
the gate named in the claim applies no fighter-identity or round-state check.

## Evidence

1. **A non-fighter object satisfied exactly the D-right/A-left signature.** NOTES.md:4862-4864
   (Session 217): `bind_by_response` reported `BOUND to instance 100404 (dx_D=+35, dx_A=-75)` while
   "that instance sits at **y=55**, not on the ground (fighters read y~160)". The note's own words:
   "the binder accepted a false responder: an object that moves when we press keys without being the
   fighter (camera, effect, UI)." So "D right +35, A left -75" was true of an object that is NOT the
   fighter. This is the exact mechanism the claim cites, shown insufficient.

2. **The gate itself applies no fighter-shape filter.** `prove_control()` (train_state.py:473-535)
   passes when `results.get("D") > min_px and results.get("A") > min_px` (train_state.py:531),
   measuring `me_x` from `read_state()` (fixed slot p242x, train_state.py:397) or `read_bound()`
   (the bound instance). It never checks y-band, x-range, or object index. The fighter-shape filter
   (`fighter_shaped`, y 100-320 / x 0-1600 / PLAYER_OBJS, two cycles) exists only in
   `bind_by_response()` (train_state.py:948-957), NOT in the gate. The gate therefore cannot tell
   "our fighter moved" from "some camera/parallax object moved".

3. **The fixed slot the gate measures is not the controlled object in all rooms.**
   facts.json `player_identity.finding`: "the object index of the player DIFFERS BY ROOM: object 154
   answered in one arena (D +64, A -25), object 244 in another". `read_state()` hard-maps `me_x` to
   p242x (train_state.py:397). In `_try_entry` the gate PASS is computed *before* binding
   (train_state.py:1114 `if self.prove_control(gate):` runs ahead of `bind_by_response()` at
   train_state.py:1127), so the first PASS measures the unverified fixed slot.

4. **No round-state check.** `prove_control` guards only on `in_arena()` (room index) and
   `has_players()` (positions valid) — train_state.py:477-491. Nothing consults round/victory state,
   so the gate can in principle run and pass after a round has ended. The repo's only measurement of
   post-round responsiveness (Session 54, NOTES.md:1644) says "the fighters stay on screen but inert
   after a round ends", which would make the gate FAIL (not pass) on a round-over screen — so this is
   an unguarded assumption, not a demonstrated false positive. Unmeasured: Nidhogg's post-kill
   "run to the Wurm" phase, where the winner remains controllable while the round is already decided;
   the gate would PASS there.

5. **The attract demo lives inside an arena room, so the room guard does not exclude it.**
   facts.json `rooms.note`: "the title screen's attract demo runs INSIDE an arena room (29
   rCastleCenter), so room index alone cannot distinguish demo from match". `ARENA_ROOMS =
   range(26,78)-{69,78}` (train_state.py:454) includes 29, so `in_arena()` returns True on the demo.
   The directional test is the gate's *only* remaining defense against the demo, and (1) shows it is
   not sufficient. Session 203 (NOTES.md:4415-4432) measured the demo as "D produces movement, A
   produces none" — A=0 fails the gate in most cases — but its 9-screen table also contains one
   `D=+16.0 A=15.0 PASS` whose screen identity is not established, so the demo-vs-match pass rate is
   not cleanly zero.

## Alternatives not excluded

- The gate PASS could reflect a camera/parallax/UI object moving right under D and left under A
  (demonstrated once, Session 217), not a fighter.
- The gate could PASS on a real but already-decided round (post-kill winner still controllable),
  because no round state is read.
- The gate could PASS while measuring the opponent or a wrong fixed slot (facts.json, Session 211),
  since object index varies by room.

## Cheapest measurement that would settle it

Run `tools/attest.py` to a gate PASS, then read the bound instance's `object_index` and `y` from
`/tmp/nid_insts_<id>.txt` and confirm it is a player object on the ground band (y≈120-300), then
read the round/score field (none exists yet) to confirm the round is live. Add to `prove_control()`
the same `fighter_shaped()` filter already in `bind_by_response()` (train_state.py:950) and a
round-active check; until then the gate's PASS is "some object moved right then left", not "we
control the fighter".
