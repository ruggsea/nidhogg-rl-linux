# Operator kickoff — artemis

You are running **on artemis** now, next to the game. Same project, same rules, different host.
Everything below is measured from this machine; where a number is Pau's rather than ours it says so.

## What already works here

* **GE-Proton11-12** at `~/.local/opt/GE-Proton11-12-x86_64` (copied from Pau's home, which is readable).
* **The Windows depot of Nidhogg** at `~/nidhogg_win` — `Nidhogg.exe` 25 MB, `data.win` 105,057,698 bytes,
  sha256 `444dcf0a…`. Verified byte-identical to the Mac copy. `steam_api64.dll` included.
* **A patched copy** at `~/nidfarm/game` with Pau's GEN8 window patch applied:
  `data.win` offset `0x10 + 60` = 320×200 (was 960×600). His measurement: **25 → 60 fps, 112% → 41% CPU**.
* **The game runs.** Under `Xvfb :99` + Proton it reached the title screen, rendering correctly
  (measured: process at 610% CPU, a real frame grabbed with `ffmpeg -f x11grab`).
* **pi on artemis**: `~/.local/bin/pi`, model `deepseek-v4-pro` verified (`DEEPSEEK_OK`). Node is
  user-space at `~/nodejs`; `npm config set prefix ~/.local` was required or pi's extension install fails.

The launch line that works (env var `STEAM_COMPAT_CLIENT_INSTALL_PATH` is **mandatory** — without it Proton
dies with `KeyError`):

```bash
export DISPLAY=:99
export STEAM_COMPAT_CLIENT_INSTALL_PATH=$HOME/fake_steam
export STEAM_COMPAT_DATA_PATH=$HOME/nidpfx
export SteamAppId=94400 SteamGameId=94400 WINEDEBUG=-all
pgrep -f "Xvfb :99 " >/dev/null || (Xvfb :99 -screen 0 640x480x24 -nolisten tcp >~/nidlogs/xvfb.log 2>&1 &)
~/.local/opt/GE-Proton11-12-x86_64/proton waitforexitandrun ~/nidfarm/game/Nidhogg.exe
```

Audio is already silenced in the prefix (`[Software\\Wine\\Drivers] "Audio"=""` in `~/nidpfx/pfx/user.reg`).

## Your first job: make the launch reliable

Open problem, honestly stated: the last few detached launches (`nohup setsid ~/launch_farm.sh … &` over ssh)
sometimes leave **no process and no log**. A foreground launch works. So the launcher needs to be made
robust before anything else: verify the process is alive, the log exists, and a frame can be grabbed —
and fail loudly when not. `~/nidlogs/` holds the logs so far.

## Then, port the interface — this is the real work

**The macOS hook does not exist here.** `inject.dylib` is arm64 Mach-O; there is no injection on Linux.
Do it Pau's way (`/home/psoler/nidhogg-rl-install/`, readable):

* **state**: `/proc/<pid>/mem`, scanning anonymous rw regions for **float32** slots that move right when
  `d` is held and left when `a` is held. Positions are float32 in this build — a float64 sweep finds only
  counters. His `findstate.py` + `nidlinux.py` already do this, and his `docs/LINUX.md`/`INTERFACE.md`
  describe it. Bind by response, exactly as the Mac harness does, just by scanning instead of by symbol.
* **input**: `xdotool windowfocus $win` + `xdotool key/keydown/keyup`, no window manager needed.
  `xdotool` is **not** on the host — it is inside the proot rootfs at `~/nidroot` (see `docs/ARTEMIS.md`),
  so either drive it through `~/nidroot/run.sh` with `-b /tmp` so it reaches `:99`, or find another route.
* **throughput**: one reflinked wine prefix per instance, one `Xvfb` per instance, `STEAM_COMPAT_DATA_PATH`
  per instance. Pau measured 8 cores ≈ 14 instances ≈ 840 steps/s at ~455 MB RSS each. This machine has
  384 cores, so the ceiling here is far higher — but the game's own cap is **60 steps/s per instance**,
  so scale means instances, not frame rate.

## Rules that still apply, unchanged

1. **Nothing counts as evidence except measurement.** An attested run in `state/attest_runs.log`
   (3 consecutive, with dose-response and ≥40/30 px displacement), a plan step closed with evidence,
   a claim with `--cmd` and `--falsifier`, a completed generation, an observed round transition.
2. **Never report a win rate.** `rounds_won` is 0 and no round transition has ever been observed.
3. **Every number goes through `tools/claim.py record --cmd … --falsifier …`.**
4. Wall-pinned fighters and attract demos have both fooled this project before. A control gate must show
   **movement**, not just the right sign — that is why the 40/30 px floor exists.
5. `tools/doctor.py`, `game.py` and much of `train_state.py` are **macOS-specific** (`/tmp/nid_*` files,
   the dylib). Porting them is part of your work, not an afterthought: a ported `doctor.py --gate` must
   pass before any training run here counts.

## Plan

`state/plan.json` is the plan. Steps 01–10 are unchanged in intent; they now execute **here** instead of
on the Mac. Steps 18–21 are the artemis bring-up, 22–24 the interface port. Read it before starting:
`python3 tools/plan.py next`.
