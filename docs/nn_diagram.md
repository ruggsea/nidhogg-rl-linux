# Policy network

```mermaid
flowchart LR
  %% generated from neuro.py by tools/nn_mermaid.py - do not edit by hand

  subgraph IN["INPUT (8) - room-agnostic: relative geometry + physical units"]
    direction TB
    i1["<b>dx / 400</b><br/><i>signed gap to opponent</i>"]
    i2["<b>|dx| / 400</b><br/><i>distance to opponent</i>"]
    i3["<b>dy / 60</b><br/><i>height difference</i>"]
    i4["<b>me_y / 600</b><br/><i>my height</i>"]
    i5["<b>them_y / 600</b><br/><i>opponent height</i>"]
    i6["<b>dx_vel / 400</b><br/><i>gap closing speed</i>"]
    i7["<b>IN REACH</b><br/><i>|dx| <= 22 px</i>"]
    i8["<b>dy in reach</b><br/><i>height gap when close</i>"]
  end

  H1["tanh<br/><b>32 units</b>"]
  H2["tanh<br/><b>16 units</b>"]

  subgraph OUT["ACTIONS (5) - one per decision, argmax"]
    direction TB
    o0["<b>LEFT</b><br/><i>hold A - retreat</i>"]
    o1["<b>RIGHT</b><br/><i>hold D - approach</i>"]
    o2["<b>ATTACK</b><br/><i>F - swing</i>"]
    o3["<b>JUMP</b><br/><i>G - jump</i>"]
    o4["<b>NOTHING</b><br/><i>no key</i>"]
  end

  i1 --> H1
  i2 --> H1
  i3 --> H1
  i4 --> H1
  i5 --> H1
  i6 --> H1
  i7 --> H1
  i8 --> H1
  H1 --> H2
  H2 --> o0
  H2 --> o1
  H2 --> o2
  H2 --> o3
  H2 --> o4

  W[/"901 weights, evolved by a GA"/]
  W -.-> H1
  W -.-> H2
  W -.-> OUT
```

Layers: `[8, 32, 16, 5]` - 901 weights, 5 actions `[65, 68, 70, 71, 0]`.

Generated from `neuro.py` by `tools/nn_mermaid.py`.

## Why each input looks the way it does

* every input is a **relative quantity** or a **physical unit** (pixels / 600 for a
  height), never an absolute coordinate divided by an arbitrary constant - the previous
  version carried `(470 - me_x)/470` where 470 was one arena's width, and it went
  **negative** in wider rooms;
* there is deliberately **no 'distance to my goal' input**: the goal position per room is
  unknown (the decompiled table gives room names, not geometry), and a wrong
  normalisation is worse than none. Direction toward the goal is carried by the reward's
  territory terms instead.
* only five outputs because a keysweep proved `W` and `S` change nothing on this build
  (jump is `G`), so the original seven-action space had two dead keys.
