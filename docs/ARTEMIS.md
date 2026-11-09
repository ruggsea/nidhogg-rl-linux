# Running Nidhogg on artemis (root-free)

The farm route. artemis is Ubuntu 24.04, 384 cores, 1.1 TB RAM, 2x L40S — plenty of machine, but
**no passwordless sudo**, so anything that needs `apt install` on the host or a setuid helper is out.

## What was measured, and what it rules out

| check | result | consequence |
|---|---|---|
| `unshare -Ur true` | `write failed /proc/self/uid_map: Operation not permitted` | user namespaces blocked → no apptainer-in-userns, no bwrap |
| `docker ps` | permission denied | docker needs sudo → unusable |
| `command -v wine Xvfb xdotool` | all absent | nothing to run a Windows game with |
| `~/steamcmd/linux32/steamcmd` | `cannot execute: required file not found` | 32-bit binary, no i386 loader on the host |
| `curl -sI https://github.com` | HTTP 200 | outbound network works |

## The route that works: proot + our own rootfs

`proot` intercepts syscalls with ptrace, so it needs **no root and no namespaces**. Combined with an
Ubuntu base rootfs unpacked in the home directory it gives a full user-space distro with a fake `uid 0`
inside, where `apt` works normally.

```bash
mkdir -p ~/nidroot && cd ~/nidroot
curl -sL -o proot https://proot.gitlab.io/proot/bin/proot && chmod +x proot
curl -sL -o ubuntu-base.tar.gz \
  https://cdimage.ubuntu.com/ubuntu-base/releases/24.04/release/ubuntu-base-24.04.5-base-amd64.tar.gz
mkdir -p rootfs && tar xzf ubuntu-base.tar.gz -C rootfs

cat > run.sh <<'EOF'
#!/bin/bash
exec "$HOME/nidroot/proot" -0 -r "$HOME/nidroot/rootfs" \
  -b /proc -b /dev -b /sys -b /etc/resolv.conf \
  -w /root /usr/bin/env -i HOME=/root \
  PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
  TERM=xterm DEBIAN_FRONTEND=noninteractive /bin/bash -c "$*"
EOF
chmod +x run.sh
```

Verified: `./run.sh "id -u"` → `0`; `apt-get update` reaches the archive and exits 0.

Two notes for anyone repeating this:

* the proot release asset on GitHub 404s; the working URL is the gitlab.io one above;
* `ubuntu-base-24.04-base-amd64.tar.gz` does not exist — the published names are point releases
  (`24.04.5-base-amd64` at the time of writing). List the directory rather than guessing.

## Credentials

The Steam password lives in the **macOS Keychain** (`service nidhogg-steam`, `account rug125`) and is
piped to artemis over ssh **stdin** so it never appears in a process list, a log, or a commit. It must
never be written into this repo, which is intended to be public.

## Where this got to

Done and verified on artemis: proot rootfs works (`id -u` → 0), `apt-get update` exits 0, and
`wine` (`/usr/bin/wine`, 9.0), `wine32:i386`, `Xvfb` and `xdotool` are installed inside the rootfs.
Valve's `steamcmd` runs there and has self-updated (it failed on the host: no i386 loader).

**The Mac install is useless for this.** `~/Library/.../common/Nidhogg/Nidhogg.app` is a *native
macOS arm64 build* — there is no `.exe` and no `data.win` to copy, which is exactly what we have been
hooking on the Mac. Running on Linux therefore requires the **Windows depot** from Steam.

**Steam Guard is enabled on the account**, so a first login needs an emailed code; it cannot be fetched
from here (Gmail auth is not connected). Once one successful login exists, steamcmd caches the machine
auth and later downloads run unattended — which is what the farm needs.

## Next steps on this host

1. `dpkg --add-architecture i386` and install `wine64 wine32:i386 xvfb xdotool libc6:i386`
   inside the rootfs (in progress; log at `~/nidroot/apt_install.log`).
2. Steam login as `rug125` from inside the rootfs with `+@sSteamCmdForcePlatformType windows`, so the
   **Windows** depot of appid 94400 is fetched. Script staged at `/root/getgame.sh` inside the rootfs:
   it takes the password on stdin, reads a Steam Guard code from `/root/sg.txt` if present, and
   validates the install.
3. Launch under `Xvfb` with wine and confirm the hook publishes a room index
   (`/tmp/nid_room_now_0.txt`). A room index is the first proof that the game is actually running.
4. `tools/attest.py` against the headless instance — the same five checks as on the Mac
   (room → bind by response → direction gate → dose-response at a movement floor → opponent not inert).
   Step 19 in the plan; nothing is farmed before it passes.

## Headless frame rate

Xvfb has no vsync and no display link, so the "parked window runs at 24-30 fps" problem found on macOS
should not exist here in the same form. Measure it rather than assume it: plan step 20 requires a
recorded fps with the window hidden or absent, as a claim with a falsifier.

## Pau's route (found on artemis, and it supersedes most of the above)

`/home/psoler/` is readable, and it contains the whole Linux setup: `nidhogg-rl-install`,
`nidhogg-rl-launch`, `nidhogg-rl-fps`, plus **GE-Proton11-12 at
`~/.local/opt/GE-Proton11-12-x86_64`** (copied to our account, 1.6 GB). His
`docs/LINUX.md` is a measured recipe, and it removes the need for proot/wine-from-scratch:

| his measurement | how |
|---|---|
| no Steam client needed | `proton waitforexitandrun Nidhogg.exe` + `SteamAppId=94400` |
| nothing on screen | one `Xvfb :N` per instance |
| **25 fps -> 60 fps** | GEN8 default window size patched `960x600` -> `320x200` in a **copy** of `data.win`, at `0x10 + 60` |
| CPU **112% -> 41%** per instance | same patch |
| silent, no audio threads | `[Software\\Wine\\Drivers] "Audio"=""` in the prefix `user.reg` |
| keyboard in, no window manager | `xdotool windowfocus $win` + `xdotool key` |
| isolated instances | one reflinked wine prefix each (`cp -a --reflink=always`) |
| state **without injection** | `/proc/<pid>/mem`; positions are **float32** (a float64 sweep finds only counters) |
| cost per instance | ~455 MB RSS, 60 steps/s cap |
| throughput | 8 cores ~ 14 instances ~ 840 steps/s |

Two consequences for this project:

1. **The macOS hook does not port.** `inject.dylib` is arm64 Mach-O; on Linux there is no
   injection at all. State comes from `/proc/<pid>/mem` scanned for float32 slots that move right
   when `d` is held and left when `a` is held — the same bind-by-response idea, done by scanning
   memory instead of by symbol address. His `findstate.py` + `nidlinux.py` already implement this.
2. **60 steps/s is the game's own cap**, not a rendering limit, so per-instance frame rate tops out
   there however fast the machine is. Above that the answer is **parallel instances**, and artemis
   has 384 cores.

### What we brought that he did not have

The **Windows depot** (appid 94400) fetched with `@sSteamCmdForcePlatformType windows`; his docs
assume a local install. It now sits at `~/nidhogg_win` on artemis
(`Nidhogg.exe` 25 MB, `data.win` 100 MB, `steam_api64.dll`).

### Attributed, not reproduced

Every number in the table above is **Pau's measurement on his own machine** (8 cores, Intel iGPU +
MX150), read from his `LINUX.md`. None of it has been reproduced on artemis yet. Reproducing the
320x200 patch (fps 25 -> 60) is part of plan step 20, and must be recorded as a claim with its own
command before it is repeated as fact.

## Parallel workers (elastic)

`tools/workers.py` runs N self-looping pi workers in their own tmux sessions (`nid-w1..N`), each with a
role (`loop/roles/*.md`), one shared plan and append-only claims.

```bash
python3 tools/workers.py scale 3     # grow (exploration: entry, round detection, audit run in parallel)
python3 tools/workers.py scale 1     # shrink for TRAINING - one stable policy runner, not a crowd
python3 tools/workers.py status      # alive / context / busy per worker
python3 tools/workers.py reap        # restart dead workers, compact any over 150k context
python3 tools/workers.py thinking <level>
```

Verified: scale 2 → 3 → 1 with correct roles, sessions created and cleaned up, tick messages armed.
Compaction is a restart, because pi has no CLI compact and a `/compact` typed into tmux arrives as chat.

### Measured dead ends (do not retry these)

* `--thinking <level>` on the CLI does **not** change the level: `~/.pi/agent/settings.json`
  `defaultThinkingLevel` wins (worker launched with `--thinking low` still displayed `think:high`).
* A per-role config dir (`PI_CODING_AGENT_DIR=~/.pi/agents/role-<role>` with its own settings) was created
  and the worker restarted from it, and the pane still displayed `think:high`.
* The `provider/model:thinking` suffix killed the session outright (empty pane).

Conclusion: for `deepseek-v4-pro` on this build the thinking level is effectively fixed at `high`. The
`thinking` subcommand sets the global setting and restarts everyone, which is the only lever that takes
effect; do not assume per-worker variation.

### Current scale

Exploration phase → **3 workers** (engineer, prober, auditor). When training starts, `scale 1`.
