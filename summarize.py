"""summarize.py — read a training log and report per-policy statistics.

The fitness is noisy (measured sd 8.6 for one policy), so a raw "best 10.63" line in the
training log is not evidence that one policy beats another. This reports, for every policy that
has repeated draws:

    mean, sd, standard error, and the difference from the best policy with ITS standard error,
    so a gap can be judged against the noise instead of against intuition.

Usage:
    python3 summarize.py /path/to/train.log
"""
import re
import statistics as st
import sys

BLOCK = re.compile(r"(g\d+i\d+):\s*reps=(\d+)\s*fits=\[([^\]]*)\]")


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "/tmp/pau_train44.log"
    try:
        text = open(path, errors="ignore").read()
    except OSError as e:
        print(f"cannot read {path}: {e}")
        return

    blocks = []
    for m in BLOCK.finditer(text):
        tag, reps, fits = m.group(1), int(m.group(2)), [float(x) for x in m.group(3).split(",")]
        if len(fits) < 2:
            continue
        blocks.append({
            "tag": tag, "n": len(fits), "mean": st.mean(fits),
            "sd": st.stdev(fits), "se": st.stdev(fits) / len(fits) ** 0.5,
        })

    if not blocks:
        print("no policy with repeated draws yet")
        return

    blocks.sort(key=lambda b: -b["mean"])
    print(f"{'policy':10s} {'n':>3s} {'mean':>8s} {'sd':>7s} {'se':>6s}   vs best")
    best = blocks[0]
    for b in blocks:
        diff = b["mean"] - best["mean"]
        diff_se = (b["se"] ** 2 + best["se"] ** 2) ** 0.5
        sigma = abs(diff) / diff_se if diff_se else 0.0
        verdict = "" if b is best else f"{diff:+7.2f} +-{diff_se:5.2f} ({sigma:.1f} sigma)"
        print(f"{b['tag']:10s} {b['n']:3d} {b['mean']:8.2f} {b['sd']:7.2f} {b['se']:6.2f}   {verdict}")

    print("\nRule of thumb: below ~2 sigma the ordering is not established.")


if __name__ == "__main__":
    main()
