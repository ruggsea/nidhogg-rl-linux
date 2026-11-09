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
