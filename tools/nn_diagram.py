"""nn_diagram.py — draw the policy network that is actually being trained.

Reads LAYERS and ACTIONS from neuro.py so the picture cannot drift from the code, labels every input
with what it physically means (and its normalisation), and every output with the game action it maps to.

    python3 tools/nn_diagram.py                # writes docs/nn_diagram.png and docs/nn_diagram.svg
    python3 tools/nn_diagram.py --text         # plain ASCII version, for notes and terminals
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import neuro

INPUTS = [
    ("dx / 400", "signed horizontal gap to opponent"),
    ("|dx| / 400", "distance to opponent (always +)"),
    ("dy / 60", "height difference (me - them)"),
    ("me_y / 600", "my height in the world"),
    ("them_y / 600", "opponent height"),
    ("dx_vel / 400", "gap closing/opening speed"),
    ("IN REACH", "1 if |dx| <= 22 px strike range"),
    ("dy in reach", "height gap, only when in reach"),
]

ACTION_NAMES = {
    65: ("LEFT", "hold A - retreat"),
    68: ("RIGHT", "hold D - approach"),
    70: ("ATTACK", "F - swing sword"),
    71: ("JUMP", "G - jump"),
    0: ("NOTHING", "no key held"),
}


def text_diagram():
    L = neuro.LAYERS
    print(f"policy: {L[0]} inputs -> tanh({L[1]}) -> tanh({L[2]}) -> {L[3]} actions (argmax)")
    print(f"weights: {neuro.N_WEIGHTS}   actions: {neuro.ACTIONS}\n")
    print("INPUTS")
    for i, (expr, meaning) in enumerate(INPUTS):
        print(f"  in{i + 1}  {expr:12s}  {meaning}")
    print("\nHIDDEN")
    print(f"  layer 1: {L[1]} units, tanh")
    print(f"  layer 2: {L[2]} units, tanh")
    print("\nOUTPUTS (argmax picks one per decision)")
    for i, code in enumerate(neuro.ACTIONS):
        name, meaning = ACTION_NAMES.get(code, (str(code), ""))
        print(f"  out{i + 1}  {name:8s} {meaning}")
    print("\nPER-SAMPLE VALUES (each arrow is w*x + b, then tanh)")


def draw():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

    L = neuro.LAYERS
    fig_w = 15.0
    fig_h = 8.6
    fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=160)
    ax.axis("off")
    ax.set_xlim(0, fig_w)
    ax.set_ylim(0, fig_h)

    # column x positions
    xs = [2.2, 7.0, 9.6, 12.6]

    def node(x, y, r, colour, lw=1.0):
        ax.add_patch(plt.Circle((x, y), r, facecolor=colour, edgecolor="#333", lw=lw, zorder=3))

    def spread(n, y0, y1):
        if n == 1:
            return [(y0 + y1) / 2]
        step = (y1 - y0) / (n - 1)
        return [y1 - i * step for i in range(n)]

    # input nodes, evenly across the height, labelled on the left
    y_in = spread(L[0], 1.0, fig_h - 1.0)
    for (expr, meaning), y in zip(INPUTS, y_in):
        node(xs[0], y, 0.17, "#bfe3ff")
        ax.text(xs[0] - 0.32, y + 0.10, expr, ha="right", va="center", fontsize=9.5,
                family="monospace", fontweight="bold")
        ax.text(xs[0] - 0.32, y - 0.18, meaning, ha="right", va="center", fontsize=7.4,
                color="#555")

    # hidden layers
    y_h1 = spread(L[1], 0.55, fig_h - 0.55)
    y_h2 = spread(L[2], 1.5, fig_h - 1.5)
    for y in y_h1:
        node(xs[1], y, 0.11, "#d8f0d0")
    for y in y_h2:
        node(xs[2], y, 0.15, "#fff3c4")

    # outputs
    y_out = spread(L[3], 1.4, fig_h - 1.4)
    for code, y in zip(neuro.ACTIONS, y_out):
        name, meaning = ACTION_NAMES.get(code, (str(code), ""))
        node(xs[3], y, 0.20, "#ffd6d6")
        ax.text(xs[3] + 0.30, y + 0.09, name, ha="left", va="center", fontsize=10,
                fontweight="bold")
        ax.text(xs[3] + 0.30, y - 0.19, meaning, ha="left", va="center", fontsize=7.4,
                color="#555")

    # connections (thin, translucent: 8*32 + 32*16 + 16*5 = 838 weights)
    for y0 in y_in:
        for y1 in y_h1:
            ax.add_patch(FancyArrowPatch((xs[0] + 0.17, y0), (xs[1] - 0.11, y1),
                                         arrowstyle="-", lw=0.25, color="#7aa6c2",
                                         alpha=0.35, zorder=1))
    for y0 in y_h1:
        for y1 in y_h2:
            ax.add_patch(FancyArrowPatch((xs[1] + 0.11, y0), (xs[2] - 0.15, y1),
                                         arrowstyle="-", lw=0.25, color="#8fae7a",
                                         alpha=0.35, zorder=1))
    for y0 in y_h2:
        for y1 in y_out:
            ax.add_patch(FancyArrowPatch((xs[2] + 0.15, y0), (xs[3] - 0.20, y1),
                                         arrowstyle="-", lw=0.35, color="#c98a8a",
                                         alpha=0.45, zorder=1))

    # layer headers
    ax.text(xs[0], fig_h - 0.42, f"INPUT  ({L[0]})", ha="center", fontsize=11, fontweight="bold")
    ax.text(xs[1], fig_h - 0.42, f"tanh ({L[1]})", ha="center", fontsize=11, fontweight="bold")
    ax.text(xs[2], fig_h - 0.42, f"tanh ({L[2]})", ha="center", fontsize=11, fontweight="bold")
    ax.text(xs[3], fig_h - 0.42, f"ACTIONS ({L[3]})", ha="center", fontsize=11, fontweight="bold")

    ax.text(fig_w / 2, 0.30,
            f"8 -> 32 -> 16 -> 5 tanh network, {neuro.N_WEIGHTS} weights, evolved by a genetic algorithm.\n"
            f"Per decision: forward pass, then argmax -> one of {len(neuro.ACTIONS)} game actions.\n"
            f"Observation is room-agnostic: relative geometry + physical units, no absolute coordinates.",
            ha="center", va="center", fontsize=8.6, color="#222")

    os.makedirs("docs", exist_ok=True)
    for ext, fmt in (("png", "png"), ("svg", "svg")):
        out = f"docs/nn_diagram.{ext}"
        fig.savefig(out, format=fmt, bbox_inches="tight", facecolor="white")
        print("wrote", out)
    plt.close(fig)


if __name__ == "__main__":
    print(f"LAYERS={neuro.LAYERS}  ACTIONS={neuro.ACTIONS}  N_WEIGHTS={neuro.N_WEIGHTS}\n")
    text_diagram()
    if "--text" not in sys.argv:
        draw()
