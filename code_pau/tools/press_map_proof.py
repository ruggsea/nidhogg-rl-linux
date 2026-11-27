#!/usr/bin/env python3
"""Proof that train_state.press routes F (70, attack) and G (71, jump) into the game.

Reads live NidState before/after a discrete press of each code through the real
InstanceManager.press path. A press reaches the game only if the state moves:
  jump (71)  -> p1_y sweeps (the fighter leaves the ground)
  attack(70) -> p1_anim shows a value not present in the idle baseline
No state change for either = the press did not reach the game (the old bug wrote a
/tmp/nid_keys_*.txt file that Linux never consumes). Writes one json under results/runs.
"""
import os, sys, time, json
sys.path.insert(0, "/home/ruggsea/nf-p/code_pau")
os.environ.setdefault("NIDFARM", "/home/ruggsea/nf-p/pau86")
os.environ.setdefault("NID_DISPLAY_BASE", "88")
import nidlinux as n, nidstate as s, train_state as t
from tools import entry_health as eh

IID = 0

def sample(pid, secs):
    out, t0 = [], time.time()
    while time.time() - t0 < secs:
        st = n.state(pid)
        if st and (st.flags & n.FLAG_P1):
            out.append((st.p1_y, st.p1_anim))
        time.sleep(0.02)
    return out

def main():
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    ent = bool(eh.ensure_entry(IID))
    pid = n._game_pid(IID)
    mgr = t.InstanceManager(IID)
    base = sample(pid, 1.0)
    base_anims = sorted({int(a) for _y, a in base})
    mgr.press(71); jump = sample(pid, 1.3)
    time.sleep(0.4)
    mgr.press(70); atk = sample(pid, 1.3)
    keysfile = os.path.exists(t.KEYS.format(IID))
    res = {
        "stamp": stamp, "pid": pid, "entered": ent, "instance": IID,
        "base_y": [min(y for y, _a in base), max(y for y, _a in base)],
        "base_anims": base_anims,
        "jump_y": [min(y for y, _a in jump), max(y for y, _a in jump)],
        "jump_anims_new": sorted({int(a) for _y, a in jump} - set(base_anims)),
        "atk_anims_new": sorted({int(a) for _y, a in atk} - set(base_anims)),
        "keys_file_written": keysfile,
        "jump_y_moved": (max(y for y, _a in jump) - min(y for y, _a in jump)) >= 10.0,
        "jump_anim_new": bool({int(a) for _y, a in jump} - set(base_anims)),
        "atk_anim_new": bool({int(a) for _y, a in atk} - set(base_anims)),
    }
    p = "/home/ruggsea/nf-p/pau86/results/runs/press_map_proof_%s.json" % stamp
    json.dump(res, open(p, "w"), indent=1)
    print(json.dumps(res))
    print("wrote", p)

if __name__ == "__main__":
    main()
