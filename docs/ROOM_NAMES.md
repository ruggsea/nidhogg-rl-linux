# docs/ROOM_NAMES.md — room index → room name, this build

Read-only static analysis (otool / nm / llvm-objdump / xxd / grep). The game was **not** launched;
nothing was written to `/tmp`.

Build analysed:

```
/Users/ruggsea/Library/Application Support/Steam/steamapps/common/Nidhogg/Nidhogg.app/Contents/MacOS/Nidhogg
  58873104 bytes, 2025-10-30 22:28, Mach-O universal (x86_64 + arm64)
  data file: .../Contents/Resources/game.ios  104973218 bytes, 2025-10-30 22:28
```

`hook/inject.m` hardcodes **arm64** addresses (`F_RoomGetName` = `0x100cff04c` is the arm64
symbol), so every runtime address below is the arm64 one; x86_64 equivalents are given where I
had them, for the record.

---

## 1. TL;DR

* The build has **82 rooms, indices 0…81**. The index is the position in the **ROOM chunk of
  `game.ios`** (the GMS2 data file), which is also the order `Room_Load()` copies names in.
* **The room names are not strings in the Mach-O.** Searching the executable for `rLogos`,
  `rMainMenu`, `rCurves`, `rTrophyRoom`, `rShowLadder`, `rMods`, `rMacTest`, `rOperatorMenu`
  returns **0 hits**; `rPreMatch` / `rOnlineLobby` / `rCastleCenter` / `rDodgeSwords` occur only
  inside `gml_Room_<name>_Create` symbol names (§4). So the "compare the pointer returned by
  `F_RoomGetName(i)` against known name addresses in the binary" plan cannot work as stated.
* The names come from `game.ios`, are pointed into at runtime by
  `g_pWADBaseAddress + <file offset of the name>`, and are reachable three cheap ways (§6).
* Recommended instrument: `idx = *(uint32_t *)_Current_Room`, then `Room_Name(idx)`
  (one direct call, no RValue plumbing) → publish `idx` + name.

---

## 2. The table

`offset` = byte offset of the NUL-terminated name inside `Contents/Resources/game.ios`. Per the
loader's arithmetic (§3.2) the runtime pointer should be `g_pWADBaseAddress + offset`, so the
column doubles as a pointer check (§6.3) — that equality is read off the disassembly, not measured
in a running process (§8.2).

| idx | name | game.ios offset | idx | name | game.ios offset |
|----:|---|---|---:|---|---|
| 0 | `__Setup` | 0x347074 | 41 | `rCastleStairsRightEnd` | 0x347aec |
| 1 | `rLogos` | 0x3470a0 | 42 | `rCastleStairsSuddenDeath` | 0x347b08 |
| 2 | `rMainMenu` | 0x3470d0 | 43 | `rMinesLeftEnd` | 0x347b28 |
| 3 | `rMultiMenu` | 0x3471d4 | 44 | `rMinesLeftC` | 0x347c00 |
| 4 | `rOnlineLobby` | 0x347250 | 45 | `rMinesLeftB` | 0x347c38 |
| 5 | `rForceStartLevel` | 0x3472cc | 46 | `rMinesLeftA` | 0x347c48 |
| 6 | `rCastleBCenter` | 0x3472e4 | 47 | `rMinesCenter` | 0x347c7c |
| 7 | `rCaslteBRightA` | 0x347360 | 48 | `rMinesRightA` | 0x347d04 |
| 8 | `rCustomColors` | 0x34739c | 49 | `rMinesRightB` | 0x347d18 |
| 9 | `rMacTest` | 0x3473b0 | 50 | `rMinesRightC` | 0x347d2c |
| 10 | `rChallengeMode` | 0x347414 | 51 | `rMinesRightEnd` | 0x347d40 |
| 11 | `rCurves` | 0x3474f0 | 52 | `rMinesSuddenDeath` | 0x347d54 |
| 12 | `rTrophyRoom` | 0x3474fc | 53 | `rSkyLeftEnd` | 0x347d6c |
| 13 | `rArcadeProgress` | 0x34755c | 54 | `rSkyLeftB` | 0x347da4 |
| 14 | `rOperatorMenu` | 0x347570 | 55 | `rSkyLeftA` | 0x347ddc |
| 15 | `rNewChallenger` | 0x347584 | 56 | `rSkyCenter` | 0x347dec |
| 16 | `rBeatGameStats` | 0x347598 | 57 | `rSkyRightA` | 0x347dfc |
| 17 | `rLevelSelect` | 0x3475d4 | 58 | `rSkyRightB` | 0x347e64 |
| 18 | `rCredits` | 0x347614 | 59 | `rSkyRightEnd` | 0x347e74 |
| 19 | `rControlsRoom` | 0x347624 | 60 | `rSkySuddenDeath` | 0x347e88 |
| 20 | `rMatchStats` | 0x347688 | 61 | `rWildsLeftEnd` | 0x347e9c |
| 21 | `rTutorial` | 0x347698 | 62 | `rWildsLeftB` | 0x347eb0 |
| 22 | `rTournamentIntro` | 0x3476d0 | 63 | `rWildsLeftA` | 0x347fcc |
| 23 | `rShowLadder` | 0x347708 | 64 | `rWildsCenter` | 0x348028 |
| 24 | `rShowChampion` | 0x347768 | 65 | `rWildsRightA` | 0x3480e4 |
| 25 | `rPreMatch` | 0x34783c | 66 | `rWildsRightB` | 0x3480f8 |
| 26 | `rCastleLeftEnd` | 0x34784c | 67 | `rWildsRightEnd` | 0x348154 |
| 27 | `rCastleLeftB` | 0x3478a8 | 68 | `rWildsSuddenDeath` | 0x348168 |
| 28 | `rCastleLeftA` | 0x347908 | 69 | `rCaslteWithYardSketch` | 0x348180 |
| 29 | `rCastleCenter` | 0x347964 | 70 | `rCemeteryLeftEnd` | 0x3482cc |
| 30 | `rCastleRightA` | 0x3479f0 | 71 | `rCemeteryLeftB` | 0x34833c |
| 31 | `rCastleRightB` | 0x347a04 | 72 | `rCemeteryLeftA` | 0x348378 |
| 32 | `rCastleRightEnd` | 0x347a18 | 73 | `rCemeteryCenter` | 0x3483b8 |
| 33 | `rCastleSuddenDeath` | 0x347a2c | 74 | `rCemeteryRightA` | 0x3483cc |
| 34 | `rCastleStairsLeftEnd` | 0x347a44 | 75 | `rCemeteryRightB` | 0x3483e0 |
| 35 | `rCastleStairsLeftB` | 0x347a60 | 76 | `rCemeteryRightEnd` | 0x3483f4 |
| 36 | `rCastleStairsLeftA` | 0x347a78 | 77 | `rCemeterySuddenDeath` | 0x34840c |
| 37 | `rCastleStairsCenter` | 0x347a90 | 78 | `rMods` | 0x348428 |
| 38 | `rCastleStairs` | 0x347aa8 | 79 | `rCustomA` | 0x348434 |
| 39 | `rCastleStairsRightA` | 0x347abc | 80 | `rCustomB` | 0x348444 |
| 40 | `rCastleStairsRightB` | 0x347ad4 | 81 | `rDodgeSwords` | 0x348454 |

Names are verbatim, including the game's own typos: `rCaslteBRightA`, `rCaslteWithYardSketch`,
`rCastleBCenter`.

Screens the trainer cares about most: `2 rMainMenu`, `3 rMultiMenu`, `4 rOnlineLobby`,
`17 rLevelSelect`, `21 rTutorial`, `25 rPreMatch`, `29 rCastleCenter` (the castle arena),
`10 rChallengeMode`, `81 rDodgeSwords`, `0 __Setup`, `1 rLogos`.

---

## 3. How the mapping is derived (evidence)

### 3.1 The data file

`game.ios` is a normal GMS2 data file:

```
00000000: 46 4f 52 4d 9a c3 41 06 47 45 4e 38   FORM <size> GEN8
```

Chunk tags found by scanning: `SPRT` @0x4280, `BGND` @0x2fe60, `PATH` @0x31c70, `SCPT` @0x31e80,
`FONT` @0x3fbe0, `TMLN` @0x4d3d0, `OBJT` @0x4d400, **`ROOM` @0x667c0**, `TPAG` @0x2b5f10,
**`STRG` @0x2cc440**, `TXTR` @0x348700, `AUDO` @0x3bbac0.

* `ROOM` chunk data starts at **0x667c8**; first u32 = **82** (room count), then 82 absolute
  file offsets to the room entries (first one = 0x66914).
* Each room entry begins with a u32 = **absolute file offset of the room name**; those land at
  0x347074…0x348454, i.e. in the tail of the STRG string blob (STRG data starts at 0x2cc448,
  `TXTR` starts at 0x348700 — GMS2 writes the STRG string bytes at the end of the file).
* Reading the 82 name offsets in chunk order produces the table in §2, all 82 strings clean.

### 3.2 Runtime: who fills the name array (`arm64`)

```
0x100e105fc  Room_Load(char* roomList, int roomCount, unsigned char* data)
  0x100e10624   x20 = *(int*)roomList            ; count
  0x100e106d8   str x20, [g_roomCount]           ; 0x1014cce78, 8-byte store
  0x100e106a4   g_roomDataArray = ReAlloc(..., count*8)   ; 0x1014cce80, CRoom* per index
  0x100e106e8   cARRAY_MEMORY<const char*>::setLength(&0x1014cce50, count)
  0x100e10734   loop i = 0..count-1:
  0x100e10738     base = *g_pWADBaseAddress                       ; 0x1015350c8
  0x100e1073c     entry = base + roomList->offsets[i]             ; per-room entry in game.ios
  0x100e1078c     name  = base + *(int*)entry                     ; the STRG name offset
  0x100e10720     g_roomNameArray[i] = name                       ; array ptr at 0x1014cce58
```

So: **the name string a room resolves to is `g_pWADBaseAddress + <the offset in §2>`** — it is
not a heap copy, it points straight into the memory image of `game.ios`. The index is simply the
position in the ROOM-chunk pointer list, copied in order.

### 3.3 Reading a name back (`arm64`, this is exactly what `F_RoomGetName` calls)

```
0x100e10ae0  const char* Room_Name(int i):
    if (i < 0)                       return "<undefined>";      ; 0x101481dde
    if (i >= g_roomCount)            return "<undefined>";      ; g_roomCount = 0x1014cce78
    if (g_roomDataArray[i] == NULL)  return "<undefined>";      ; 0x1014cce80
    return g_roomNameArray[i];                                  ; array ptr 0x1014cce58

0x100e10a78  bool Room_Exists(int i)   ; same bounds test, non-NULL room data
0x100e10b24  int  Room_Find(const char* name)   ; strcmp over g_roomNameArray, -1 if absent
0x100cff04c  F_RoomGetName(RValue& ret, CInst*, CInst*, int argc, RValue** args):
    idx = YYGetRef(args, 0, 0x01000003, Room_Number(), 0, 1, 0)
    YYCreateString(&ret, Room_Name(idx))
```

`Room_Number()` (`0x100e10a6c`) is `ldr w0, [0x1014cce78]` — the **same 8-byte slot
`Room_Load` writes the room count into**. I could not establish that it returns the current room
index, so do not build on it; use `_Current_Room` (§6.1).

`_Current_Room` (int32, arm64 `0x101530d98`, x86_64 `0x10176acd8`) is the live index: it is what
the GML `room` command reads (`Command_CurrentRoom`, `0x100e15964` → `0x100e159c8`,
`0x101530d98`) and what `room_goto` writes. This matches the project's own earlier decompile in
`NOTES.md` (session 210).

---

## 4. What `strings` actually finds for room names

Room names appear in the Mach-O **only** as part of YYC code-generation symbol names:

| string found | x86_64 file / vmaddr | arm64 file / vmaddr |
|---|---|---|
| `gml_Room___Setup_Create` | 0x014cb699 / 0x1014c7699 | 0x02fe6089 / 0x10128e089 |
| `gml_Room_rOnlineLobby_Create` | 0x014cb6d0 / 0x1014c76d0 | 0x02fe60c0 / 0x10128e0c0 |
| `gml_Room_rPreMatch_Create` | 0x014cb808 / 0x1014c7808 | 0x02fe61f8 / 0x10128e1f8 |
| `gml_Room_rCastleCenter_Create` | 0x014cb888 / 0x1014c7888 | 0x02fe6278 / 0x10128e278 |
| `gml_Room_rDodgeSwords_Create` | 0x014cc2d8 / 0x1014c82d8 | 0x02fe6cc8 / 0x10128ecc8 |

(file offset = slice-relative address + slice base: x86_64 base `0x4000`, arm64 base `0x1d58000`.)

They sit in a plain pool of 8-byte-aligned, NUL-terminated `gml_*` names in `__DATA`
(`…/gml_Room___Setup_Create`, `…/gml_RoomCC_rMultiMenu_0_Create`, `…/gml_Room_rOnlineLobby_Create`,
`…/gml_Room_rForceStartLevel_Create`, …), i.e. the C++ symbol names of the creation-code functions,
**emitted in room order**. Walking that pool recovers the room order for the 66 rooms that have
creation code, which independently corroborates §3.1's ordering. The same names occur three more
times per slice: as mangled symbols (`__Z25gml_Room_rPreMatch_CreateP9CInstanceS0_`), in a
`_g_Script_…` table, and next to `…/GM_MAC/Nidhogg/…/Game/*.gml.cpp` source paths.

Only **66 of the 82** rooms have such a symbol. **Absent from the binary entirely** (no name
string anywhere, no creation-code function): `1 rLogos`, `2 rMainMenu`, `8 rCustomColors`,
`9 rMacTest`, `11 rCurves`, `12 rTrophyRoom`, `13 rArcadeProgress`, `14 rOperatorMenu`,
`15 rNewChallenger`, `16 rBeatGameStats`, `17 rLevelSelect`, `18 rCredits`, `20 rMatchStats`,
`23 rShowLadder`, `24 rShowChampion`, `78 rMods` — exactly the menu rooms, i.e. the ones a
trainer needs to recognise. They cannot be recovered from the executable at all.

Function entry points, for hooking creation code per room (arm64):
`gml_Room___Setup_Create` `0x10070e908`, `gml_Room_rOnlineLobby_Create` `0x10070ec04`,
`gml_Room_rPreMatch_Create` `0x10070fabc`, `gml_Room_rCastleCenter_Create` `0x10070ff08`,
`gml_Room_rDodgeSwords_Create` `0x100714d80`.

### 4.1 Menu words that do exist in the Mach-O

The words a trainer might use to recognise a screen are present as C++ string literals (they are
code literals, not the drawn text: the drawn text is in the `game.ios` string table). First
occurrence of each:

| literal | x86_64 vmaddr | arm64 vmaddr |
|---|---|---|
| `SINGLE PLAYER` | 0x101330e8c | 0x100ff5edf |
| `MULTIPLAYER` | 0x101326a69 | 0x100fece51 |
| `TRAINING` | 0x1013285b5 | 0x100fee577 |
| `ARCADE` | 0x1013310e8 | 0x100ff60e9 |
| `ONLINE` | 0x101330d10 | 0x100ff5d7c |
| `CPU BATTLE` | 0x10132bb25 | 0x100ff139c |
| `TOURNAMENT` | 0x10131b9fd | 0x100fe3055 |
| `PRESS ENTER` | — not found — | — not found — |

No room name appears next to these literals; they do not identify a room.

---

## 5. Reproduce the table (no game launch)

```sh
B=".../Contents/MacOS/Nidhogg"; D=".../Contents/Resources/game.ios"
nm -arch arm64 "$B" | grep -E "Room_Name|Room_Load|F_RoomGetName|Current_Room|g_pWADBaseAddress"
otool -tvV -arch arm64 -p "__Z9Room_Namei" "$B"
python3 - "$D" <<'EOF'
import struct,sys
d=open(sys.argv[1],'rb').read(); u=lambda o: struct.unpack('<I',d[o:o+4])[0]
ROOM=419784            # 'ROOM' tag at 419776, +8
for i in range(u(ROOM)):                       # 82
    ent=u(ROOM+4+4*i); off=u(ent)              # absolute name offset
    print(i, hex(off), d[off:d.index(b'\0',off)].decode())
EOF
```

---

## 6. How the hook should verify the current room

### 6.1 Cheap, no strings: current index

```c
// arm64, resolved once at install time (symaddr logs every call)
static uint32_t *pCurRoom = NULL;                 // symaddr(0x101530d98ULL, "_Current_Room")
static int (*pRoomExists)(int) = NULL;            // symaddr(0x100e10a78ULL, "Room_Exists")

uint32_t cur = *pCurRoom;                         // 0..81 expected
int      ok  = pRoomExists((int)cur);             // 1 = the game agrees a room is there
```

`_Current_Room` is a plain int32 global (NOT a pointer — that mistake is recorded in
`NOTES.md` session 210). Publish it to its own file (`nid_room_now_<id>.txt`), never to a file
the hook also reads as a command.

### 6.2 Name for an index: one direct call, not `F_RoomGetName`

```c
typedef const char *(*NameFn)(int);
static NameFn pRoomName = NULL;   // (NameFn)symaddr(0x100e10ae0ULL, "Room_Name")

const char *nm = pRoomName(i);    // i in 0..81; returns "<undefined>" (0x101481dde) if invalid
```

`Room_Name` takes a plain `int` and returns a plain `const char*`; it skips the four calls of the
`F_RoomGetName` path (`YYGetRef` → `Room_Number` → `Room_Name` → `YYCreateString`). It is valid
for any `i` in `0..81`, and returns the literal `"<undefined>"` outside that range, so it cannot
walk off the table — but `probe_rooms()` looping `0..90` still logs 9 bogus rows; use `0..81`.

If you keep using `F_RoomGetName`, the existing extraction is correct: `YYCreateString`
(arm64 `0x100c66b58`) builds a 16-byte CString `{char* data @+0x0, u32 refcount @+0x8,
u32 length @+0xc}` and stores the CString pointer in `RValue+0x0` with the type tag at `+0x8`,
so `nm = *(char **)out.v.p` is right.

### 6.3 Pointer comparison: what works and what cannot

* **Cannot work:** comparing to an address in the Mach-O. The names are not in the binary (§4),
  and at runtime the pointer is `mmap`/`malloc`'d `game.ios` + offset, so it moves with ASLR and
  with where the WAD is loaded. Any hardcoded "known name address" is meaningless.
* **Works, exact, per launch** (if the loader arithmetic in §3.2 is right): read the WAD base and
  compare the *offset*, not the address:

  ```c
  uint64_t base = *(volatile uint64_t *)symaddr(0x1015350c8ULL, "g_pWADBaseAddress");
  uint64_t off  = (uint64_t)pRoomName(i) - base;      // must equal the §2 offset
  ```

  e.g. `Room_Name(29) - g_pWADBaseAddress == 0x347964` → `rCastleCenter`. This checks the whole
  table mechanically: 82 offsets, one comparison each, and it fails loudly if `game.ios` is
  replaced by an update (offsets shift, the table in §2 goes stale).
* **Works, weakest:** `strcmp(pRoomName(i), "rCastleCenter") == 0`. Fine for a trainer,
  breaks silently on a name change (a build edit could rename rooms).
* **Works, identity only:** capture `pRoomName(i)` for `i = 0..81` once per process into a table
  of pointers and compare the current pointer against it. Pointer equality is stable inside one
  process (they all point into the same WAD image), but says nothing across launches, so it can
  only tell "same room as pointer k", never "this is rCastleCenter".
* **Best combined check** (what I would put in the trainer): index from `_Current_Room`, name
  from `Room_Name(idx)`, offset check against `g_pWADBaseAddress`, and `Room_Exists(idx)` as a
  guard before either; log all four once per second. Three independent facts have to agree before
  the trainer believes the screen.

### 6.4 Ready-to-use probe (replacing `probe_rooms()`)

```c
static const char *(*pRoomName)(int) = NULL;                   // symaddr(0x100e10ae0, "Room_Name")
static int (*pRoomExists)(int)       = NULL;                   // symaddr(0x100e10a78, "Room_Exists")
static uint32_t *pCurRoom           = NULL;                    // symaddr(0x101530d98, "_Current_Room")
static uint64_t *pWadBase           = NULL;                    // symaddr(0x1015350c8, "g_pWADBaseAddress")

static void probe_rooms(void) {
    if (!pRoomName || !pRoomExists || !pCurRoom || !pWadBase) return;
    uint32_t cur = *pCurRoom;
    LOG("[room] now=%u name=%s\n", cur, pRoomName((int)cur));
    for (int i = 0; i < 82; i++) {                 // 82, not 90
        if (!pRoomExists(i)) continue;
        const char *nm = pRoomName(i);
        LOG("[room] %d = %s  off=0x%06llx\n", i, nm,
            (unsigned long long)((uint64_t)nm - *pWadBase));
    }
}
```

(Keep it on the main-thread tick: `NOTES.md` session 34 shows GML calls from the probe thread
killing the process.)

---

## 7. Cross-checks against this project's own measurements (already in `NOTES.md`)

| measured | table says | where |
|---|---|---|
| launch, room = 1 | `1 rLogos` | session 213 `1. LAUNCH room=1` |
| "PRESS ENTER" title, room = 2 | `2 rMainMenu` | sessions 210/211/213 |
| nav fallthrough landed on room 3, not the arena | `3 rMultiMenu` | session 213 `3. ROOM room=3` |
| `Enter` at 17 = "match being set up" after SINGLE PLAYER → TRAINING | `17 rLevelSelect` | session 211 |
| arena with two fighters, room = 29 | `29 rCastleCenter` | sessions 210/211 |
| `online.log` recorded `rOnlineLobby` after Enter walked MULTIPLAYER → ONLINE | `4 rOnlineLobby`, next room after `3 rMultiMenu` | session 52 (no index in that log line) |
| `room_goto(25)` was already believed to be `rPreMatch` and it yields a live match | `25 rPreMatch` | session 15, line 605 |

No contradiction anywhere. Provenance per the `docs/INTERFACE.md` convention: **proven** for
indices 1, 2, 3, 17, 29 (index read from the live game and the screen described); **inferred**
for 4 and 25 (consistent with the game's own log and this project's earlier notes, index not
logged); **inferred** for the remaining 75 (single static source chain: ROOM-chunk order →
`Room_Load` copy order → `Room_Name` indexing, corroborated by the creation-code pool order in §4).

---

## 8. What I could NOT establish

1. **No room-name string exists in the Mach-O**, so "compare the pointer against known name
   addresses in the binary" is impossible for this build. The premise of the brief holds for
   `game.ios`, not for the executable. All names were read from `game.ios` (§3.1).
2. **Not measured in-process.** I was told not to launch the game, so I did not observe
   `Room_Name(i)` returning these strings at runtime. The chain
   `Room_Load → g_roomNameArray → Room_Name` and the chunk→index order are read off the
   disassembly, not watched. Only the six indices in §7 have live confirmation.
3. **`Room_Number()` semantics unresolved.** It reads the same 8-byte slot that `Room_Load`
   stores the room *count* into (`0x1014cce78`), while `Room_Name`/`Room_Exists` use that slot as
   the count bound. Either it returns the count (and is not the "current room" accessor) or the
   slot holds something I cannot see statically. Nothing should depend on it; use
   `_Current_Room`. Whether `F_RoomGetName()` **without** an argument returns garbage for this
   reason is untested.
4. **`probe_rooms()` as shipped has never been seen to work.** Its RValue→CString dereference
   matches the `YYCreateString` layout (§6.2), but `NID_ROOMS` output was not available to me, so
   I cannot say the logged rows were ever non-empty.
5. **Which rooms map to which physical fight arena** is not derivable from the names alone:
   `25 rPreMatch` was already described as producing a live match in `NOTES.md` session 15, while
   `29 rCastleCenter` did too in sessions 210/211. The names are the game's; what the screens do
   is not established here.
6. **Offsets are version-specific.** The §2 offset column belongs to `game.ios`
   (2025-10-30, 104973218 bytes). Any Steam update replaces the data file and shifts them; the
   index→name order would probably survive, the offsets would not.
7. **The x86_64 slice was only partially mapped** (I gave `Room_Name` = `0x10101da80`,
   `Room_Load` = `0x10101d560`, `_Current_Room` = `0x10176acd8`,
   `g_pWADBaseAddress` = `0x10176f028`, room arrays at `0x101706bb0/bb8/bc8`). The hook is
   arm64-only (`symaddr` hardcodes arm64 addresses + slide), so x86_64 was not chased further.
