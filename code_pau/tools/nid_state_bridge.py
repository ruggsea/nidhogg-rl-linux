import os, sys, time, struct
sys.path.insert(0, '/home/ruggsea/nf-p/code_pau')
os.environ.setdefault('NIDFARM', '/home/ruggsea/nf-p/pau86')
os.environ.setdefault('NID_DISPLAY_BASE', '88')
import nidlinux as n, nidstate as s
from nidmem import ROOM_OFF, exe_base

LOG = '/home/ruggsea/nf-p/pau86/logs/state_bridge.log'
open('/home/ruggsea/nf-p/pau86/logs/state_bridge.pid', 'w').write(str(os.getpid()))

def log(m):
    open(LOG, 'a').write(time.strftime('%H:%M:%S') + ' ' + m + '\n')

log('bridge restart (pid-only retrack)')
last_pid = None
tracked = False

def write_outputs(st):
    open('/tmp/nid_state_0.txt', 'w').write(
        '%s %s %s %s 1 1\n' % (st.p2_x, st.p2_y, st.p1_x, st.p1_y))
    open('/tmp/nid_insts_0.txt', 'w').write(
        '1 242 %s %s\n2 154 %s %s\n' % (st.p1_x, st.p1_y, st.p2_x, st.p2_y))

def usable(st):
    if not st or not (st.flags & n.FLAG_P1 and st.flags & n.FLAG_P2):
        return False
    if min(abs(st.p1_x), abs(st.p2_x)) > 1400:
        return False
    if not (-50 <= st.p1_y <= 700 and -50 <= st.p2_y <= 700):
        return False
    if abs(st.p1_x) > 5000 or abs(st.p2_x) > 5000:
        return False
    return True

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
            try:
                n.untrack(pid)
            except Exception:
                pass
            n.track(pid, p1=p1, p2=p2, tick=tick)
            last_pid = pid
            tracked = True
            log('track p1=%#x p2=%#x' % (p1, p2))
            time.sleep(0.2)

        st = n.state(pid)
        if usable(st):
            write_outputs(st)
        try:
            raw = n.memory(pid, exe_base(pid) + ROOM_OFF, 4, '/tmp/tw_room.bin')
            if raw:
                room = struct.unpack('<i', raw)[0]
                open('/tmp/nid_room_now_0.txt', 'w').write(str(room) + '\n')
                open('/tmp/nid_room_0.txt', 'w').write(str(room) + '\n')
        except Exception:
            pass
        time.sleep(0.03)
    except Exception as e:
        log('err %s: %s' % (type(e).__name__, e))
        last_pid = None
        tracked = False
        time.sleep(1.0)
