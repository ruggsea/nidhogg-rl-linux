"""Extra observation fields read from GameMaker instance records (found in ~/nf-obs/FIELDS.md).

Instance records: stride 0x200, vtable u64 at +0x00 > 2^40, f32 270.0 at +0x110; +0xB4 id,
+0xB8 object index, +0xE8 blend colour, +0xEC/+0xF0 x/y, +0x120 bbox. Instances are recreated on
respawn and on room change, so nothing is trusted by address: every read() finds the records by
object index again. A full heap scan costs ~0.85 s, so read() scans a window around the instance
pool (WIN bytes either side of the records the last full scan found, one spy round trip together
with the RValues) and falls back to a full scan when a body or the camera is missing from it.
An instance variable's RValue address is fixed while the instance lives, so it is cached per
instance id; a new id (respawn, new held sword) resolves its variable map again (`resolves`).

Per fighter, world frame (N_FEAT = 13 numbers, FEATS order), each clipped to [-2, 2]:
   0 has_sword      body (obj 74) var 0x192E7, 1/0
   1 stance         held-sword var 0x19AD2: 1 high -> +1, 3 mid -> 0, 2 low -> -1; 0 without one
   2 held_sword     1 if an obj 244/155 instance has var 0x1920B == this body's instance id
   3 floor          (top of the floor under x - feet y)/100: 0 standing, >0 floor below; 2 if none
   4 ledge_left     (nearest x to the left where that floor changes - x)/300, <0; -2 if none
   5 ledge_right    (nearest x to the right where it changes - x)/300, >0; +2 if none
   6 ceiling        (head y - bottom of the lowest solid above the head)/100, head = y-26; 2 if none
   7 view_left      (camera x - 160 - x)/300 (camera = obj 66), <=0 while on screen
   8 view_right     (camera x + 160 - x)/300, >=0 while on screen
   9 fly_present    1 if a flying sword (obj 153) exists
  10 fly_dx         (x of the nearest flying sword - x)/300; 0 if none
  11 ground_present 1 if a sword lies on the ground (obj 167)
  12 ground_dx      (x of the nearest ground sword - x)/300; 0 if none
Position x, y = the fighter's body record (obj 74 of its colour nearest the tracked record), read
in the same snapshot as the swords and camera. A fighter with no body record (dead, not yet
respawned) gets 0 for fields 0-2 and the rest from the tracked x, y.
Solids = obj 12 bboxes (l, t, r, b). Mirror (P2's own view, x' = M - x): fly_dx and ground_dx
change sign; ledge_left/right and view_left/right swap and change sign; the rest stays.
Not observed (not found in memory): a sword stuck in scenery, the room width.
"""
import struct

import numpy as np

from nidmem import n, s

ID, X, BB = 0xB4, 0xEC, 0x120
BODY, CAM, SOLID, FLY, GROUND, HELD = 74, 66, 12, 153, 167, (244, 155)
WANT = (BODY, CAM, SOLID, FLY, GROUND) + HELD
COLOUR = {0x0000FFFF: "P1", 0x0040A0FF: "P2"}
K_HAS, K_OWNER, K_STANCE = 0x192E7, 0x1920B, 0x19AD2
STANCE = {1: 1.0, 3: 0.0, 2: -1.0}
VIEW_HALF, HEAD, WIN = 160.0, 26.0, 0x40000
FEATS = ["has_sword", "stance", "held_sword", "floor", "ledge_left", "ledge_right", "ceiling",
         "view_left", "view_right", "fly_present", "fly_dx", "ground_present", "ground_dx"]
N_FEAT = len(FEATS)
SWAP, NEG = [(4, 5), (7, 8)], [10, 12]


def mirror(f):
    f = np.asarray(f, np.float32)
    g = f.copy()
    for a, b in SWAP:
        g[a], g[b] = -f[b], -f[a]
    g[NEG] = -f[NEG]
    return g


def floor_under(S, x, y):
    tops = [t for l, t, r, b in S if l <= x <= r + 1 and t >= y - 2]
    return min(tops) if tops else None


def ceiling_over(S, x, y):
    bots = [b for l, t, r, b in S if l <= x <= r + 1 and b < y - HEAD + 2]
    return max(bots) if bots else None


def ledges(S, x, y):
    """Nearest x left/right of x where floor_under(., y) differs from floor_under(x, y). The floor
    is piecewise constant and changes only at a box's l or r+2, so only those x are tested."""
    f = floor_under(S, x, y)
    edges = sorted({e for l, t, r, b in S for e in (l, r + 2)})
    left = next((e - 1 for e in reversed(edges) if e <= x and floor_under(S, e - 1, y) != f), None)
    right = next((e for e in edges if e > x and floor_under(S, e, y) != f), None)
    return left, right


def parse(raw, base):
    """Instance records of the WANT objects in a byte range starting at base (0x200-aligned)."""
    q = np.frombuffer(raw[: len(raw) // 8 * 8], "<u8")
    f = np.frombuffer(raw[: len(raw) // 4 * 4], "<f4")
    slots = np.arange(0, len(q) - 0x40, 0x40)
    out = []
    for j in np.nonzero((q[slots] > (1 << 40)) & (f[slots * 2 + 0x110 // 4] == 270.0))[0]:
        off = int(slots[j]) * 8
        if off + 0x200 > len(raw):
            continue
        iid, obj = struct.unpack_from("<II", raw, off + ID)
        if obj in WANT:
            x, y = struct.unpack_from("<ff", raw, off + X)
            out.append(dict(a=base + off, id=iid, obj=obj, x=x, y=y,
                            col=struct.unpack_from("<I", raw, off + 0xE8)[0],
                            bb=struct.unpack_from("<4f", raw, off + BB)))
    return out


class Reader:
    def __init__(self, pid):
        self.pid, self.win, self.vars = pid, None, {}
        self.full_cols, self.since_full = set(), 0
        self.full_scans = self.resolves = self.unread = 0
        self.last = None

    def full_scan(self):
        heaps = s._cached_heaps(self.pid) or [r for r in s.regions(self.pid) if r[1] - r[0] >= 1 << 20]
        reqs = [(a, b - a, f"/tmp/nobs_{k}.bin") for k, (a, b) in enumerate(heaps)]
        L = []
        for (a, _b), raw in zip(heaps, n.memory_many(self.pid, reqs)):
            if raw is None:          # some regions are refused by the spy (as in scanall.py)
                self.unread += 1
                continue
            L += parse(raw, a)
        self.full_scans += 1
        live = [d["a"] for d in L if d["obj"] in (BODY, CAM)]
        assert live, "full scan: no body or camera record"
        self.win = (min(live) - WIN) & ~0x1FF, max(live) + 0x200 + WIN
        return L

    def _resolve(self, d, keys):
        """{key: RValue address} from the instance variable hash map at rec+0x08."""
        rd = lambda a, z: n.memory(self.pid, a, z, "/tmp/nobs_v.bin")
        mp, = struct.unpack("<Q", rd(d["a"] + 8, 8))
        cur, = struct.unpack("<I", rd(mp, 4))
        el, = struct.unpack("<Q", rd(mp + 0x10, 8))
        raw = rd(el, cur * 16)
        got = {}
        for k in range(cur):
            p, key, _h = struct.unpack_from("<QII", raw, k * 16)
            if p and key in keys:
                got[key] = p
        assert set(got) == set(keys), f"instance {d['id']} obj {d['obj']}: no var {set(keys) - set(got)}"
        self.vars[d["id"]] = got
        self.resolves += 1
        return got

    def _scan(self):
        """(records, {RValue address: 16 bytes}) in one round trip: the window plus the RValues
        of every instance id seen before. A body or the camera missing -> full scan."""
        cached = [p for v in self.vars.values() for p in v.values()]
        if self.win:
            lo, hi = self.win
            reqs = [(lo, hi - lo, "/tmp/nobs_win.bin")] + [(p, 16, f"/tmp/nobs_r{k}.bin")
                                                           for k, p in enumerate(cached)]
            raw = n.memory_many(self.pid, reqs)
            if raw[0] is not None:
                L = parse(raw[0], lo)
                cols = {d["col"] for d in L if d["obj"] == BODY}
                # a body missing from the window: full scan, but while a fighter has no body at
                # all (dead, not respawned) only every 30th read
                self.since_full += 1
                lost = [c for c in COLOUR if c not in cols and (c in self.full_cols or self.since_full >= 30)]
                if not lost and any(d["obj"] == CAM for d in L):
                    return L, {p: b for p, b in zip(cached, raw[1:]) if b is not None}
        L = self.full_scan()
        self.full_cols, self.since_full = {d["col"] for d in L if d["obj"] == BODY}, 0
        return L, {}

    def read(self, pos):
        """pos = {"P1": (x, y), "P2": (x, y)}, the tracked fighters. Returns {who: features in
        the world frame, "ids": instance ids used, "cam_x", "n_fly", "n_ground", "full"}."""
        full0 = self.full_scans
        L, rv = self._scan()
        by = lambda *o: [d for d in L if d["obj"] in o]
        solids = sorted(tuple(d["bb"]) for d in by(SOLID))
        cams = by(CAM)
        assert len(cams) == 1, f"{len(cams)} camera instances"
        cam_x = cams[0]["x"]
        bodies, gap = {}, {}
        for who, (x, y) in pos.items():
            mine = [d for d in by(BODY) if COLOUR.get(d["col"]) == who]
            if not mine:     # dead, no respawn yet: no body record of this colour
                bodies[who] = dict(id=None, x=x, y=y)
                gap[who] = None
                continue
            # the body nearest the tracked record. The tracked sample is a few ticks older than
            # this read (3 px x, 6 px y seen mid-jump); a large gap = the tracked record died and
            # this is the respawned body (seen: the corpse record stays obj 74 for a while, then
            # goes, before nidenv notices the death); the gap is reported
            bodies[who] = b = min(mine, key=lambda d: abs(d["x"] - x) + abs(d["y"] - y))
            gap[who] = round(abs(b["x"] - x) + abs(b["y"] - y), 1)
        held = by(*HELD)
        need = [(b, (K_HAS,)) for b in bodies.values() if b["id"] is not None]
        need += [(d, (K_OWNER, K_STANCE)) for d in held]
        for d, keys in need:
            if d["id"] not in self.vars:
                self._resolve(d, keys)
        missing = [p for d, _k in need for p in self.vars[d["id"]].values() if p not in rv]
        if missing:
            rv.update(zip(missing, n.memory_many(self.pid, [(p, 16, f"/tmp/nobs_m{k}.bin")
                                                            for k, p in enumerate(missing)])))
        live = {d["id"] for d, _k in need}
        self.vars = {i: v for i, v in self.vars.items() if i in live}   # dead ids: stop reading
        num = lambda i, k: struct.unpack_from("<d", rv[self.vars[i][k]], 0)[0]
        ref = lambda i, k: struct.unpack_from("<I", rv[self.vars[i][k]], 0)[0]
        fly, ground = by(FLY), by(GROUND)
        out = {"ids": {}, "cam_x": cam_x, "n_fly": len(fly), "n_ground": len(ground),
               "full": self.full_scans > full0, "track_gap": gap}
        for who in pos:
            b = bodies[who]
            x, y = b["x"], b["y"]          # same snapshot as the swords and the camera
            sw = [d for d in held if b["id"] is not None and ref(d["id"], K_OWNER) == b["id"]]
            st = STANCE.get(int(num(sw[0]["id"], K_STANCE)), 0.0) if sw else 0.0
            fl, ce = floor_under(solids, x, y), ceiling_over(solids, x, y)
            ll, lr = ledges(solids, x, y)
            nf = min(fly, key=lambda d: abs(d["x"] - x)) if fly else None
            ng = min(ground, key=lambda d: abs(d["x"] - x)) if ground else None
            has = num(b["id"], K_HAS) if b["id"] is not None else 0.0
            f = [has, st, float(bool(sw)),
                 2.0 if fl is None else (fl - y) / 100,
                 -2.0 if ll is None else (ll - x) / 300, 2.0 if lr is None else (lr - x) / 300,
                 2.0 if ce is None else (y - HEAD - ce) / 100,
                 (cam_x - VIEW_HALF - x) / 300, (cam_x + VIEW_HALF - x) / 300,
                 float(bool(fly)), 0.0 if nf is None else (nf["x"] - x) / 300,
                 float(bool(ground)), 0.0 if ng is None else (ng["x"] - x) / 300]
            out[who] = np.clip(np.array(f, np.float32), -2, 2)
            out["ids"][who] = {"body": b["id"], "sword": sw[0]["id"] if sw else None}
            out[who + "_xy"] = (x, y)
        self.last = out
        return out
