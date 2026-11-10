"""Neural policy + GA (evolution strategies style), pure numpy.

State (all read from memory by the injected harness):
    [dx, me_x, them_x, me_y, them_y, |dx|, alive_me, alive_them]
  normalised; dx = them_x - me_x in screen/room pixels.

Policy: 8 -> tanh(32) -> tanh(16) -> 5 actions (left, right, attack,
jump, idle). Weights evolve by tournament selection + crossover + gaussian
mutation, same loop shape as the parametric version.
"""
import numpy as np

# Action space cut to what Phase 2 PROVED reachable on this build
# (docs/INTERFACE.md, results/keysweep_0.json): A and D move x with correct opposite
# signs, G moves y (jump), F produces motion. W (87) and S (83) changed NOTHING in the
# instance window 0x80..0x2FF under a 0.55 s hold, and the in-game tutorial says
# "PRESS G TO JUMP" - so W/S were dead keys and one third of the action space (plus the
# selection pressure spent discovering they do nothing) was wasted.
# MEASURED arena extent in x (see obs_vector). Used to normalise the goal-distance input.
ARENA_X = 470.0

ACTIONS = [65, 68, 70, 71, 0]          # A, D, F(attack), G(jump), nothing

LAYERS = [8, 32, 16, 5]
SIZES = [LAYERS[i] * LAYERS[i + 1] for i in range(len(LAYERS) - 1)]
N_WEIGHTS = sum(SIZES) + sum(LAYERS[1:])


def unpack(w):
    mats = []
    off = 0
    for i in range(len(LAYERS) - 1):
        r, c = LAYERS[i], LAYERS[i + 1]
        size = r * c
        mats.append(w[off:off + size].reshape(r, c))
        off += size
        b = w[off:off + c]
        off += c
        mats.append(b)
    return mats


def forward(w, obs):
    h = np.asarray(obs, dtype=np.float64)
    mats = unpack(w)
    for i in range(0, len(mats), 2):
        h = np.tanh(h @ mats[i] + mats[i + 1])
    return h


def obs_vector(st):
    """The 8 inputs the policy sees. ROOM-AGNOSTIC by construction.

    MEASURED BUG in the previous version: slot 3 was `(ARENA_X - me_x)/ARENA_X` with ARENA_X = 470, a
    width measured in ONE arena. In a wider room (observed me_x = 606) that input went NEGATIVE
    (-0.289) and carried no meaning. Slots 2/4/5 normalised absolute coordinates by arbitrary
    constants (2000, 250) whose plausible ranges differ per room anyway.

    Everything here is now a RELATIVE quantity or a physical unit, so it means the same thing in every
    arena:
       0 signed horizontal gap to the opponent, 400 px = 1.0
       1 |gap|, capped at 1.0                 (distance, always positive, room-independent)
       2 height difference (me - them), 60 px = 1.0
       3 my height in the world, 600 px = 1.0  (ground vs platform is physically meaningful)
       4 their height, 600 px = 1.0
       5 closing/opening speed of the gap, 400 px/s = 1.0
       6 IN REACH flag (22 px strike range) - the timing signal for an attack
       7 opponent above/below me within reach (separate from 2, which fires at any distance)

    NOTE what is deliberately absent: any absolute "distance to the goal" input. The goal position per
    room is not known (the room table gives names, not geometry), and a wrong normalisation is worse
    than no input. The DIRECTION toward the goal is carried by the reward's territory terms instead.
    """
    if not st:
        return np.zeros(8)
    dx = st["them_x"] - st["me_x"]
    dy = st["them_y"] - st["me_y"]
    in_reach = abs(dx) <= 22.0
    v = np.array([
        dx / 400.0,
        min(abs(dx) / 400.0, 1.0),
        dy / 60.0,
        st["me_y"] / 600.0,
        st["them_y"] / 600.0,
        float(np.clip(st.get("dx_vel", 0.0) / 400.0, -1.0, 1.0)),
        1.0 if in_reach else 0.0,
        (dy / 60.0) if in_reach else 0.0,
    ], dtype=np.float64)
    return np.clip(v, -3.0, 3.0)


class Population:
    def __init__(self, size=24, seed=0, scripted=True):
        self.rng = np.random.default_rng(seed)
        self.W = self.rng.normal(0.0, 0.7, size=(size, N_WEIGHTS))
        if scripted:
            # CURRICULUM SEEDS. Measured: holding a direction moves the fighter at
            # ~12 px/s, but the evolved net managed ~0.1 px of net movement - it never
            # learned even to walk. Rather than wait for that to emerge, start the
            # population from hand-written policies so selection has something that
            # already moves and strikes to recombine from.
            for i, w in enumerate(scripted_seeds()[:size]):
                self.W[i] = w

    def next_gen(self, fitness):
        order = np.argsort(-np.asarray(fitness))
        elite = self.W[order[: max(2, self.W.shape[0] // 4)]]
        n = self.W.shape[0]
        kids = list(elite)
        while len(kids) < n:
            a, b = self.rng.choice(elite.shape[0], 2)
            w = np.where(self.rng.random(N_WEIGHTS) < 0.5, elite[a], elite[b]).copy()
            mut = self.rng.random(N_WEIGHTS) < 0.06
            w += mut * self.rng.normal(0.0, 0.22, N_WEIGHTS)
            kids.append(w)
        # ANCHOR THE SEEDS. The hand-written "walk in, strike when in reach" policy is
        # the only thing that ever lands a hit, but plain tournament selection drops it
        # long before a better variant appears (measured: min_dx 90 px, i.e. nothing ever
        # closes). Keeping two scripted anchors in every generation gives selection
        # something attack-capable to recombine from instead of rediscovering it.
        seeds = scripted_seeds()
        anchors = [seeds[4], seeds[5]] if len(seeds) > 5 else seeds[-2:]
        for k, w in enumerate(anchors):
            kids[-(k + 1)] = w
        self.W = np.array(kids)


def scripted_seeds():
    """Hand-written policies expressed as weights, for the initial population.

    Bias-only seeds force a constant action (hidden units are all tanh(0)=0, so the
    last-layer bias alone decides the argmax). The reach-conditional seed instead
    routes the "in reach" observation through one hidden unit, so it walks right and
    strikes exactly when the opponent is within sword range.
    """
    # Offsets derived from LAYERS. They used to be hardcoded for a 7-action output
    # (W1 0:256, B1 256:288, W2 288:800, B2 800:816, W3 816:928, B3 928:935) and silently
    # broke the moment the action space changed - the seeds crashed on an empty slice.
    off = 0
    _slices = []
    for i in range(len(LAYERS) - 1):
        r, c = LAYERS[i], LAYERS[i + 1]
        _slices.append((slice(off, off + r * c), slice(off + r * c, off + r * c + c)))
        off += r * c + c
    W1, B1 = _slices[0]
    W2, B2 = _slices[1]
    W3, B3 = _slices[2]
    OUT = LAYERS[-1]
    seeds = []

    def base():
        return np.zeros(N_WEIGHTS)

    # The "always jump" seed was dropped: it scored near zero every time it ran, and the slot
    # is better spent on a policy that attacks. Order matters - Population fills the first
    # `size` slots, so with pop 6 a seventh seed is NEVER evaluated (the reach-and-attack seed
    # spent all night in slot 7 and never ran once).
    for idx in (1, 0, 2):             # always right / left / attack
        w = base(); w[B3][idx] = 3.0; seeds.append(w.copy())

    # walk right, attack when in reach (obs[6] is the 1.0/0.0 reach flag)
    w = base()
    w[6 * 32 + 0] = 10.0              # input 'reach' -> hidden L1 unit 0
    w[288 + 0 * 16 + 0] = 10.0        # L1 unit 0 -> L2 unit 0 (pass-through; without
                                      # this the all-zero middle layer zeroes it out)
    w[W3][0 * OUT + 2] = 5.0          # unit 0 -> attack (ACTIONS[2])
    w[B3][1] = 1.5                    # otherwise: move right
    seeds.append(w)

    # same but strafe left when in reach (feint), attack otherwise
    w = base()
    w[6 * 32 + 0] = 10.0
    w[W3][0 * OUT + 0] = 5.0          # unit 0 -> left
    w[B3][1] = 1.5
    seeds.append(w)

    # MEASURED: in the first scored generation, the seed that ALWAYS attacks (i2) scored
    # 25.6 while every moving seed scored between -20 and 5.3. Swinging beats walking, but
    # always-attacking never closes the gap. This seed combines them: attack whenever the
    # gap is under 60 px (well inside the measured 22 px strike range plus approach), and
    # walk toward the opponent otherwise.
    w = base()
    w[0 * 32 + 0] = -10.0             # obs[0] = dx/400 -> unit 0, negative: close gap wins
    w[B1][0] = 1.75                   # threshold: attack once dx/400 < 0.175 (dx < 70 px).
                                      # 1.5 gave exactly dx<60, so a fighter at dx=60 did NOT
                                      # attack - the boundary case masked whether the seed works.
    w[W2][0 * 16 + 0] = 10.0          # pass unit 0 to L2 unit 0
    w[W3][0 * OUT + 2] = 5.0          # -> attack
    w[B3][1] = 1.5                    # otherwise -> move right
    seeds.append(w)
    return seeds


def rand_policy(rng):
    return rng.normal(0.0, 0.7, size=N_WEIGHTS)


IDLE_INDEX = 4          # ACTIONS[4] is "nothing"


def decide(w, st, rng):
    out = forward(w, obs_vector(st))
    a = int(np.argmax(out))
    if rng.random() < 0.03:           # small exploration floor
        a = int(rng.integers(0, len(ACTIONS)))
    # Standing still is never useful in Nidhogg: a whole generation converged on the
    # idle output and scored exactly 0.00 (no progress, no kills, no rounds). Replace
    # idle with "advance on the opponent" so every policy always does something.
    if a == IDLE_INDEX and st:
        return 68 if st["them_x"] > st["me_x"] else 65
    return ACTIONS[a]
