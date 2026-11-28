"""Observation bridge: track both fighters and publish their state plus event-tied outcomes.

Runs on the farm as ``~/nf-p/venv/bin/python tools/nid_state_bridge.py``.

The spy tracks ``p1``/``p2`` and the game's room address (``score``), so every sample
carries the room index at that same tick (no separate memory read). Files written:

    /tmp/nid_state_0.txt     p2_x p2_y p1_x p1_y p2_alive p1_alive   (6 fields)
    /tmp/nid_insts_0.txt     1 242 <p1>  /  2 154 <p2>               (legacy insts)
    /tmp/nid_outcome_0.txt   json: OutcomeTracker.summary()
    /tmp/nid_events_0.jsonl  one line per room change / death event

Kills, deaths and the round counter come from the game's own room value and fighter
existence flags (see tools/outcome_events.py), never from an x-jump heuristic.
"""
import json
import os
import struct
import sys
import time

sys.path.insert(0, '/home/ruggsea/nf-p/code_pau')
os.environ.setdefault('NIDFARM', '/home/ruggsea/nf-p/pau86')
os.environ.setdefault('NID_DISPLAY_BASE', '88')
import nidlinux as n, nidstate as s
from nidmem import ROOM_OFF, exe_base
from tools.outcome_events import OutcomeTracker

LOG = '/home/ruggsea/nf-p/pau86/logs/state_bridge.log'
open('/home/ruggsea/nf-p/pau86/logs/state_bridge.pid', 'w').write(str(os.getpid()))


def log(m):
    open(LOG, 'a').write(time.strftime('%H:%M:%S') + ' ' + m + '\n')


log('bridge restart (event-tied outcomes)')
last_pid = None
tracked = False
tracker = OutcomeTracker(debounce=3)


def sane(st):
    return bool(st) and abs(st.p1_x) <= 5000 and abs(st.p2_x) <= 5000 \
        and -50 <= st.p1_y <= 700 and -50 <= st.p2_y <= 700


def write_outputs(st):
    p1f = 1 if st.flags & n.FLAG_P1 else 0
    p2f = 1 if st.flags & n.FLAG_P2 else 0
    room = st.score_orange if st.flags & n.FLAG_SCORE else None
    open('/tmp/nid_state_0.txt', 'w').write(
        '%s %s %s %s %d %d\n' % (st.p2_x, st.p2_y, st.p1_x, st.p1_y, p2f, p1f))
    open('/tmp/nid_insts_0.txt', 'w').write(
        '1 242 %s %s\n2 154 %s %s\n' % (st.p1_x, st.p1_y, st.p2_x, st.p2_y))
    events = tracker.update(room, p1f, p2f, ts=time.time())
    if events:
        with open('/tmp/nid_events_0.jsonl', 'a') as f:
            for ev in events:
                f.write(json.dumps(ev) + '\n')
    open('/tmp/nid_outcome_0.txt', 'w').write(json.dumps(tracker.summary()) + '\n')


while True:
    try:
        try:
            pid = n._game_pid(0)
        except Exception:
            pid = None
        if not pid:
            last_pid = None
            tracked = False
            time.sleep(0.5)
            continue
        try:
            if not n.ping(pid):
                last_pid = None
                tracked = False
                time.sleep(0.5)
                continue
        except Exception:
            last_pid = None
            tracked = False
            time.sleep(0.5)
            continue

        need_track = (not tracked) or (pid != last_pid)
        if need_track:
            log('track attempt pid=%s' % pid)
            p1 = p2 = None
            try:
                fp = s.find_players_by_input(0, hold=0.45)
                if fp and fp.get('P1') and fp.get('P2'):
                    p1, p2 = fp['P1'], fp['P2']
                    log('input fighters')
            except Exception as e:
                log('find_players_err %s:%s' % (type(e).__name__, e))
            if not p1 or not p2:
                log('waiting fighters')
                tracked = False
                time.sleep(2.0)
                continue
            tick = s.find_tick(pid) or 0
            room_addr = exe_base(pid) + ROOM_OFF
            try:
                n.untrack(pid)
            except Exception:
                pass
            n.track(pid, p1=p1, p2=p2, score=room_addr, tick=tick)
            last_pid = pid
            tracked = True
            log('track p1=%#x p2=%#x room=%#x' % (p1, p2, room_addr))
            time.sleep(0.2)

        st = n.state(pid)
        if sane(st):
            write_outputs(st)
        time.sleep(0.03)
    except Exception as e:
        log('err %s: %s' % (type(e).__name__, e))
        last_pid = None
        tracked = False
        time.sleep(1.0)