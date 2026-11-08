"""One clean diagnostic: kill, fresh launch, navigate, then test whether ANY fighter responds to D/A.
Prints the fighters before/after each direction so we can see exactly who (if anyone) we control."""
import sys
import time
import subprocess

sys.path.insert(0, ".")
import train_state as TS

mgr = TS.InstanceManager(iid=0)


def snap():
    d = {}
    try:
        for line in open("/tmp/nid_insts_0.txt"):
            p = line.split()
            if len(p) == 4:
                d[int(p[0])] = (int(p[1]), float(p[2]), float(p[3]))
    except OSError:
        pass
    return d


def fighters(s):
    return {i: v for i, v in s.items() if v[0] in (154, 242, 244, 245)}


def room():
    try:
        return int(open("/tmp/nid_room_now_0.txt").read().strip())
    except (OSError, ValueError):
        return None


print("0. kill + fresh launch", flush=True)
subprocess.run(["pkill", "-9", "-f", "MacOS/Nidhogg"], capture_output=True)
time.sleep(3)
mgr.launch()
time.sleep(TS.BOOT_WAIT)
print(f"   booted, room={room()}", flush=True)

print("1. navigate (highlight-bar path)", flush=True)
from tools.attest import navigate
ok = navigate(mgr)
print(f"   navigate -> {ok}, room={room()}", flush=True)

print("2. settle", flush=True)
for _ in range(10):
    st, _ = mgr.read_state()
    if st and st.get("me_x"):
        break
    time.sleep(0.5)
time.sleep(4.0)
st, _ = mgr.read_state()
print(f"   state: {st}", flush=True)

print("3. control test: D then A, watch fighters", flush=True)
before = fighters(snap())
print(f"   before D: {before}", flush=True)
mgr.press(68); time.sleep(1.0)
mid = fighters(snap())
print(f"   after  D: {mid}", flush=True)
mgr.press(65); time.sleep(1.0)
after = fighters(snap())
print(f"   after  A: {after}", flush=True)

# summarize movement
for iid in set(before) | set(mid) | set(after):
    b = before.get(iid); m = mid.get(iid); a = after.get(iid)
    dxD = (m[1] - b[1]) if (b and m) else None
    dxA = (a[1] - m[1]) if (m and a) else None
    print(f"   inst {iid} obj={ (b or m or a)[0] }: D_dx={dxD if dxD is not None else 'gone'}, A_dx={dxA if dxA is not None else 'gone'}", flush=True)
