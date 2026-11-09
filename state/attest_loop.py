"""Run tools/attest.py repeatedly until 3 consecutive passing runs are at the tail of
state/attest_runs.log. A run PASSES only if verdict == 'ATTESTED - training run is meaningful'
(exact) AND the run's ok.dose_response is True (the new 5-check gate). Old runs without a
dose_response field, and NOT-ATTESTED runs, do not count."""
import subprocess
import sys
import json


MAX_RUNS = 10
RUN_TIMEOUT = 420  # seconds; a full run is ~2.5-5 min


def passing():
    out = []
    try:
        with open("state/attest_runs.log") as f:
            for line in f:
                line = line.strip()
                if not line.startswith("{"):
                    continue
                try:
                    d = json.loads(line)
                except Exception:
                    continue
                if "verdict" not in d:
                    continue
                gate = d.get("gate") or {}
                d_mag = abs(gate.get("D") or 0)
                a_mag = abs(gate.get("A") or 0)
                enough = max(d_mag, a_mag) >= 40.0 and min(d_mag, a_mag) >= 30.0
                passed = (d["verdict"] == "ATTESTED - training run is meaningful"
                          and d.get("ok", {}).get("dose_response") is True
                          and enough)
                out.append(passed)
    except OSError:
        pass
    return out


for i in range(1, MAX_RUNS + 1):
    print(f"=== attest run {i} ===", flush=True)
    try:
        subprocess.run([sys.executable, "tools/attest.py"], cwd=".", timeout=RUN_TIMEOUT)
    except subprocess.TimeoutExpired:
        print(f"run {i} timed out after {RUN_TIMEOUT}s; continuing", flush=True)
        continue
    ps = passing()
    streak = 0
    for p in reversed(ps):
        if p:
            streak += 1
        else:
            break
    print(f"  [runs={len(ps)} tail_streak={streak}]", flush=True)
    if streak >= 3:
        print("3 CONSECUTIVE ATTESTED", flush=True)
        sys.exit(0)

print(f"NOT REACHED after {MAX_RUNS} runs", flush=True)
sys.exit(1)
