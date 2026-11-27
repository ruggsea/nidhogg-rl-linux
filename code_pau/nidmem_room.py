"""Linux/Proton live room index: Nidhogg.exe image base + ROOM_OFF int32 (Pau nidmem path)."""
from __future__ import annotations

import os
import struct
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, os.environ.get("CODE_PAU", str(_REPO)))

import nidlinux as n  # noqa: E402

# GameMaker room order in data.win ROOM chunk (.data @ base+ROOM_OFF; Windows PE, Proton maps same).
ROOM_OFF = 0x1ACE918
ARENA_ROOMS = range(26, 78)
MENU_ROOMS = {
    1: "rLogos",
    2: "rMainMenu",
    3: "rMultiMenu",
    4: "rOnlineLobby",
    17: "rLevelSelect",
    20: "rMatchStats",
    25: "rPreMatch",
}


def exe_base(pid: int) -> int:
    with open(f"/proc/{pid}/maps") as f:
        for line in f:
            if line.rstrip().endswith("/Nidhogg.exe"):
                return int(line.split("-")[0], 16)
    raise AssertionError(f"Nidhogg.exe not mapped in pid {pid}")


def room_addr(pid: int) -> int:
    return exe_base(pid) + ROOM_OFF


def read_room_pid(pid: int, art: str | None = None) -> int:
    path = art or os.path.join(os.environ.get("NIDART", "/tmp"), "nmem_room.bin")
    raw = n.memory(pid, room_addr(pid), 4, path)
    if not raw:
        raise RuntimeError("room read failed")
    v = struct.unpack("<i", raw)[0]
    if not (0 <= v < 82):
        raise RuntimeError(f"room index out of range: {v}")
    return v


def read_room(inst: int = 0) -> int:
    pid = n._game_pid(inst)
    if not pid or not n.ping(pid):
        raise RuntimeError("no live game/spy")
    return read_room_pid(pid)


def room_name(room: int) -> str:
    if room in MENU_ROOMS:
        return MENU_ROOMS[room]
    if room in ARENA_ROOMS:
        return f"arena_{room}"
    return f"room_{room}"