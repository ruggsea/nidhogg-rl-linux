#!/usr/bin/env python3
"""score_finder.py — locate the score field AT GAME TIME, per process.

Why this exists: Pau's fixed address `0xd5f57c8` was refuted twice on our instances (write lands,
HUD digit does not move) and the field's address **varies per process** even though the region
`0xd412000` keeps a fixed base. A hardcoded address can therefore never be trusted across launches —
the only robust answer is to find it each time the game starts, prove it against the HUD, and cache
(address, pid) for the life of that process.

THE TEST (three stages, cheapest first)

1. **Differential narrowing.** Snapshot the region at score 0, play/forfeit exactly one round, snapshot
   again. Keep only u32 slots that incremented by exactly 1. This cuts ~290k slots to a handful without
   writing anything (writing blind crashes the process — measured).

2. **HUD write-probe.** For each surviving candidate: write 1, read the P1 (or P2) digit rect on a clean
   READY screen, restore the original value. The winner is the one whose write moves its own digit.
   Guard rails:
     * only probe once the wins cell is allocated (i.e. after at least one round has been played),
       because writing a score before that CRASHES the game;
     * integers only, never floats;
     * after each probe check the pid is still alive — if a candidate killed the game, record it as
       hazardous and continue on a fresh process.

3. **Cross-check.** Re-probe the winner from a *second* fresh process before caching it. A field that
   only works in one process is a coincidence, not a field.

    python3 tools/score_finder.py --dry-run        # show the plan, touch nothing
    python3 tools/score_finder.py                  # find + verify + cache

Output: state/score_addr.json  {"pid": …, "addr": "0x…", "who": "P1|P2", "verified": true, "ts": …}
and a claim with its falsifier.
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.expanduser("~/pau-tree"))
sys.path.insert(0, os.path.expanduser("~/nidhogg-pau/tools"))

REGION = (0xD412000, 0xDD10000)
CACHE = os.path.expanduser("~/nidhogg-pau/state/score_addr.json")
GRAB = os.path.expanduser("~/nidhogg-pau/state/score_grab")
P1_RECT = (56, 14, 80, 30)       # YELLOW digit, READY screen only (Pau §2.6)
P2_RECT = (214, 14, 238, 30)     # ORANGE digit
U32_UNINIT = 0x78787878

try:
    import nidlinux as n
except Exception as e:                                  # noqa: BLE001
    print(f"score_finder: cannot import nidlinux from ~/pau-tree ({e})")
    raise SystemExit(2)


# ---------------------------------------------------------------- compatibility shim
# Pau's module has changed shape between revisions; resolve by capability, not by name, so this keeps
# working when he renames things. The worker should print the resolved names once and confirm.
def _resolve(*names):
    for name in names:
        fn = getattr(n, name, None)
        if callable(fn):
            return fn
    return None


memory = _resolve("memory", "dump", "read_bytes")
key = _resolve("key", "press", "spy_key")
grab = _resolve("grab", "screenshot", "frame")
state_fn = _resolve("state", "get_state")
pid_fn = _resolve("_game_pid", "game_pid")


def game_pid():
    return pid_fn(0) if pid_fn else None


def u32_at(pid, addr):
    raw = memory(pid, addr, addr + 4) if memory else None
    if not raw:
        return None
    return int.from_bytes(raw[:4], "little")


def write_u32(pid, addr, value):
    """Only integers; a non-integer score write kills the process (Pau §2.6)."""
    w = _resolve("poke", "write", "spy_poke")
    if not w:
        raise RuntimeError("no write primitive found in nidlinux")
    return w(pid, addr, value, "u32") if "u32" in (w.__doc__ or "") else w(pid, addr, value)


def hud_cols(rect, path):
    """Count bright pixels inside a HUD digit rect — the oracle, cheap and screen-only."""
    if not grab:
        return None
    grab(0, path)
    try:
        from PIL import Image
    except ImportError:
        return None
    try:
        im = Image.open(path).convert("L").crop(rect)
    except OSError:
        return None
    return sum(1 for p in im.getdata() if p > 200)


def snapshot(pid, path):
    if not memory:
        return None
    data = memory(pid, REGION[0], REGION[1], path)
    return data


def differential(before_path, after_path):
    """u32 slots that incremented by exactly 1 - the score stepped once."""
    try:
        import numpy as np
    except ImportError:
        print("numpy required")
        return []
    try:
        a = np.frombuffer(open(before_path, "rb").read(), "<u4")
        b = np.frombuffer(open(after_path, "rb").read(), "<u4")
    except OSError:
        return []
    m = min(len(a), len(b))
    idx = np.nonzero((b[:m].astype("int64") - a[:m].astype("int64")) == 1)[0]
    return [REGION[0] + int(i) * 4 for i in idx
            if a[i] != U32_UNINIT and a[i] < 100 and b[i] < 100]


def probe(pid, addr, rect, path):
    """Write 1, read the digit, restore. Returns (moved_px, survived)."""
    orig = u32_at(pid, addr)
    if orig is None:
        return 0, False
    base = hud_cols(rect, path)
    try:
        write_u32(pid, addr, 1)
    except Exception:                                   # noqa: BLE001
        return 0, False
    time.sleep(0.25)
    after = hud_cols(rect, path)
    alive = game_pid() is not None
    try:
        if alive:
            write_u32(pid, addr, orig)                  # restore what we found
    except Exception:                                   # noqa: BLE001
        pass
    if base is None or after is None:
        return 0, alive
    return abs(after - base), alive


def main():
    dry = "--dry-run" in sys.argv
    os.makedirs(GRAB, exist_ok=True)
    pid = game_pid()
    if not pid:
        print("score_finder: no running Nidhogg.exe (tools/farm_linux.sh start, or nidlinux.start_ids)")
        return 2
    print(f"score_finder: pid {pid}, region {REGION[0]:#x}-{REGION[1]:#x}")
    if dry:
        print("plan: (1) snapshot at 0, (2) play/forfeit one round, (3) diff for +1, "
              "(4) write-probe survivors against the HUD rect, (5) re-verify in a second process, cache")
        return 0

    before = os.path.join(GRAB, "before.bin")
    after = os.path.join(GRAB, "after.bin")
    if not snapshot(pid, before):
        print("score_finder: snapshot failed (no read primitive?)")
        return 2
    print("snapshot 1 taken - now forfeit exactly one round, then press ENTER to continue")
    input()                                             # the worker drives the round; we only measure
    if not snapshot(pid, after):
        print("score_finder: second snapshot failed")
        return 2
    cands = differential(before, after)
    print(f"differential: {len(cands)} candidate(s) incremented by exactly 1")
    if not cands:
        print("score_finder: nothing incremented - the round boundary was not real, or the score "
              "lives outside the scanned region. Do NOT write blindly.")
        return 1

    for who, rect in (("P1", P1_RECT), ("P2", P2_RECT)):
        for addr in cands[:40]:
            moved, alive = probe(pid, addr, rect, os.path.join(GRAB, "probe.png"))
            tag = "CRASHED" if not alive else f"{moved} px"
            print(f"  {who} {addr:#x}: {tag}")
            if not alive:
                print("  -> candidate is hazardous; restart the game and resume with the rest")
                return 1
            if moved >= 8:
                out = {"pid": pid, "addr": hex(addr), "who": who, "verified": False, "ts": time.time()}
                json.dump(out, open(CACHE, "w"), indent=1)
                print(f"score_finder: {who} score candidate {addr:#x} moved the digit by {moved} px")
                print("  now re-verify from a SECOND fresh process before trusting it (protocol rule)")
                return 0
    print("score_finder: no candidate moved the HUD; treat the differential as inconclusive")
    return 1


if __name__ == "__main__":
    sys.exit(main())
