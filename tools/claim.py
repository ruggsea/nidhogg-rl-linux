"""claim.py — a ledger that makes "I measured X" re-checkable, not remembered.

The failure this exists for: throughout this project I stated measurements that turned out to be
artifacts (a gate that passed because the fighter walked; a "live match" that was the title screen's
attract demo; "sd dropped to 4" from a cherry-picked subset; a round detector whose conditions were
mutually unsatisfiable). In every case the claim was written in prose and the evidence was never
attached, so it could not be falsified later without redoing the work.

A claim here is a triple:

    text     what is asserted
    cmd      the exact shell command that produces the evidence
    sha      sha256 of that command's output at the time of recording

`verify` re-runs every command and reports OK / DRIFT / ERROR. DRIFT means the world changed or the
claim was never true. Either way it is visible, which is the point.

    python3 tools/claim.py record "room 29 is an arena" --cmd "cat /tmp/nid_room_now_0.txt"
    python3 tools/claim.py verify
    python3 tools/claim.py list
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
import time

LEDGER = os.path.join("state", "claims.jsonl")


def run(cmd, timeout=30):
    try:
        p = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return (p.stdout + p.stderr).strip(), p.returncode
    except subprocess.TimeoutExpired:
        return "__timeout__", 124


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def record(text, cmd):
    out, rc = run(cmd)
    entry = {"ts": time.time(), "text": text, "cmd": cmd, "rc": rc,
             "sha": sha(out), "head": out[:300]}
    os.makedirs("state", exist_ok=True)
    with open(LEDGER, "a") as f:
        f.write(json.dumps(entry) + "\n")
    print(f"recorded: {text}")
    print(f"  cmd: {cmd}")
    print(f"  rc={rc} sha={entry['sha']}  {entry['head'][:120]!r}")
    return 0


def load():
    if not os.path.exists(LEDGER):
        return []
    out = []
    with open(LEDGER) as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def verify():
    claims = load()
    if not claims:
        print("no claims recorded")
        return 0
    bad = 0
    for c in claims:
        out, rc = run(c["cmd"])
        now = sha(out)
        if now == c["sha"] and rc == c["rc"]:
            status = "OK"
        elif rc != c["rc"]:
            status = "ERROR"
            bad += 1
        else:
            status = "DRIFT"
            bad += 1
        print(f"[{status:5s}] {c['text']}")
        print(f"          {c['cmd']}")
        if status != "OK":
            print(f"          was {c['sha']} ({c['head'][:90]!r})")
            print(f"          now {now} ({out[:90]!r})")
    print(f"\n{len(claims) - bad}/{len(claims)} claims still hold")
    return 0 if bad == 0 else 1


def listing():
    for c in load():
        age = round((time.time() - c["ts"]) / 60, 1)
        print(f"  {age:7.1f} min ago  {c['text']}")
        print(f"                cmd: {c['cmd']}")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=["record", "verify", "list"])
    ap.add_argument("text", nargs="?")
    ap.add_argument("--cmd")
    a = ap.parse_args()
    if a.action == "record":
        if not a.text or not a.cmd:
            print("record needs TEXT and --cmd")
            return 2
        return record(a.text, a.cmd)
    return verify() if a.action == "verify" else listing()


if __name__ == "__main__":
    sys.exit(main())
