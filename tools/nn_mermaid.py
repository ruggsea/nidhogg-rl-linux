"""nn_mermaid.py — the policy network as a Mermaid diagram (renders on GitHub).

Emits docs/nn_diagram.md. Layers come from neuro.py so the diagram cannot drift from the code.

The hidden layers are drawn as single nodes labelled with their width rather than 32 and 16 individual
circles: a full fan-out of 901 edges is unreadable at any zoom and adds nothing - what matters is the
width, the activation, and which physical quantity each input carries.

    python3 tools/nn_mermaid.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import neuro

INPUTS = [
    ("i1", "dx / 400", "signed gap to opponent"),
    ("i2", "|dx| / 400", "distance to opponent"),
    ("i3", "dy / 60", "height difference"),
    ("i4", "me_y / 600", "my height"),
    ("i5", "them_y / 600", "opponent height"),
    ("i6", "dx_vel / 400", "gap closing speed"),
    ("i7", "IN REACH", "|dx| <= 22 px"),
    ("i8", "dy in reach", "height gap when close"),
]

ACTIONS = {
    65: ("LEFT", "hold A - retreat"),
    68: ("RIGHT", "hold D - approach"),
    70: ("ATTACK", "F - swing"),
    71: ("JUMP", "G - jump"),
    0: ("NOTHING", "no key"),
}


def build():
    L = neuro.LAYERS
    out = []
    out.append("```mermaid")
    out.append("flowchart LR")
    out.append("  %% generated from neuro.py by tools/nn_mermaid.py - do not edit by hand")
    out.append("")
    out.append("  subgraph IN[\"INPUT (8) - room-agnostic: relative geometry + physical units\"]")
    out.append("    direction TB")
    for nid, expr, meaning in INPUTS:
        out.append(f'    {nid}["<b>{expr}</b><br/><i>{meaning}</i>"]')
    out.append("  end")
    out.append("")
    out.append(f'  H1["tanh<br/><b>{L[1]} units</b>"]')
    out.append(f'  H2["tanh<br/><b>{L[2]} units</b>"]')
    out.append("")
    out.append(f'  subgraph OUT["ACTIONS ({L[3]}) - one per decision, argmax"]')
    out.append("    direction TB")
    for idx, code in enumerate(neuro.ACTIONS):
        name, meaning = ACTIONS.get(code, (str(code), ""))
        out.append(f'    o{idx}["<b>{name}</b><br/><i>{meaning}</i>"]')
    out.append("  end")
    out.append("")
    for nid, _expr, _m in INPUTS:
        out.append(f"  {nid} --> H1")
    out.append("  H1 --> H2")
    for idx in range(len(neuro.ACTIONS)):
        out.append(f"  H2 --> o{idx}")
    out.append("")
    out.append(f"  W[/\"{neuro.N_WEIGHTS} weights, evolved by a GA\"/]")
    out.append("  W -.-> H1")
    out.append("  W -.-> H2")
    out.append("  W -.-> OUT")
    out.append("```")
    return "\n".join(out)


def main():
    body = build()
    path = "docs/nn_diagram.md"
    os.makedirs("docs", exist_ok=True)
    with open(path, "w") as f:
        f.write("# Policy network\n\n")
        f.write(body + "\n\n")
        f.write(f"Layers: `{neuro.LAYERS}` - {neuro.N_WEIGHTS} weights, "
                f"{len(neuro.ACTIONS)} actions `{neuro.ACTIONS}`.\n\n")
        f.write("Generated from `neuro.py` by `tools/nn_mermaid.py`.\n\n")
        f.write("## Why each input looks the way it does\n\n")
        f.write("* every input is a **relative quantity** or a **physical unit** (pixels / 600 for a\n"
                "  height), never an absolute coordinate divided by an arbitrary constant - the previous\n"
                "  version carried `(470 - me_x)/470` where 470 was one arena's width, and it went\n"
                "  **negative** in wider rooms;\n")
        f.write("* there is deliberately **no 'distance to my goal' input**: the goal position per room is\n"
                "  unknown (the decompiled table gives room names, not geometry), and a wrong\n"
                "  normalisation is worse than none. Direction toward the goal is carried by the reward's\n"
                "  territory terms instead.\n")
        f.write("* only five outputs because a keysweep proved `W` and `S` change nothing on this build\n"
                "  (jump is `G`), so the original seven-action space had two dead keys.\n")
    print("wrote", path)
    print(body)


if __name__ == "__main__":
    main()
