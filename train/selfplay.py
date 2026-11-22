"""Self-play evolution strategy: ONE network (train.py's MLP 8 -> 16 tanh -> 7) drives both fighters.

  python3 train/selfplay.py --gens 20 --max_episodes 60 --pairs 3 --seed 0
  python3 train/selfplay.py --eval random  --eval_eps 20     # both fighters random weights
  python3 train/selfplay.py --eval trained --eval_eps 20     # both fighters the checkpoint

Each generation: K antithetic noise pairs. In an episode the perturbed candidate theta+-sigma*eps
drives one fighter and the current theta drives the other (both from their own side, see
selfplay_env.py); the candidate's fitness is its own fighter's reward. Pair k plays side P1 if k
is even, else P2; both members of a pair play the same side from the same episode seed. Fitness
of both fighters with identical weights would sum to ~0 (one's kill is the other's death), so
theta is scored against itself, not with itself. One line per generation; non-zero exit on crash.
"""
import argparse, json, os, pickle, sys, time
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from train import SIZES, act  # noqa: E402

WHO = ("P1", "P2")


def act_sample(theta, obs, rng):
    """Sample an action from softmax(logits). Greedy argmax from the one fixed reset spot froze
    whole episodes: a non-walking action (e.g. 6, stance down) leaves the state unchanged, so the
    same action was picked for all 150 steps (run4 eps 61-65: 0 moved steps for both)."""
    i, parts = 0, []
    for n in SIZES:
        parts.append(theta[i:i + n]); i += n
    w1, b1, w2, b2 = parts
    z = np.tanh(obs @ w1.reshape(len(obs), -1) + b1) @ w2.reshape(len(b1), -1) + b2
    p = np.exp(z - z.max()); p /= p.sum()
    return int(rng.choice(len(p), p=p))


def episode(env, th1, th2, rng=None):
    """rng given: sampled actions (training; the pair's two members share the seed). None: greedy."""
    o1, o2 = env.reset()
    done, acts = False, {w: [0] * 7 for w in WHO}
    while not done:
        a1, a2 = ((act_sample(th1, o1, rng), act_sample(th2, o2, rng)) if rng is not None
                  else (act(th1, o1), act(th2, o2)))
        acts["P1"][a1] += 1; acts["P2"][a2] += 1
        (o1, o2), _r, done, info = env.step(a1, a2)
    info["actions"] = acts          # per fighter, counts of actions 0..6 (P2 in its own frame)
    return info


def tally(infos):
    t = {"n": len(infos), "valid": sum(bool(i.get("valid")) for i in infos),
         "aborted": sum(i["outcome"] == "aborted" for i in infos),
         "draw": sum(i["outcome"] == "draw" for i in infos),
         "undecided": sum(i["outcome"] == "undecided" for i in infos)}
    for w in WHO:
        rs = [i["per"][w]["reward"] for i in infos]
        t[f"{w}_fit"] = round(float(np.mean(rs)), 3) if rs else None
        t[f"{w}_kills"] = sum(i["per"][w]["kill"] for i in infos)
        t[f"{w}_walked"] = sum(bool(i["per"][w]["walked"]) for i in infos)
        t[f"{w}_valid_wins"] = sum(bool(i.get("valid")) and i["outcome"] == w for i in infos)
    return t


def line(prefix, t, extra=""):
    return (f"{prefix} eps={t['n']} fit P1={t['P1_fit']:+.3f} P2={t['P2_fit']:+.3f} "
            f"kills P1={t['P1_kills']} P2={t['P2_kills']} draw={t['draw']} undecided={t['undecided']} "
            f"aborted={t['aborted']} walked(>=5 moved steps) P1={t['P1_walked']}/{t['n']} "
            f"P2={t['P2_walked']}/{t['n']} valid(v3)={t['valid']} valid_wins P1={t['P1_valid_wins']} "
            f"P2={t['P2_valid_wins']}{extra}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--gens", type=int, default=20)
    p.add_argument("--max_episodes", type=int, default=60)
    p.add_argument("--pairs", type=int, default=3)
    p.add_argument("--sigma", type=float, default=0.3)
    p.add_argument("--lr", type=float, default=0.3)
    p.add_argument("--max_ticks", type=int, default=600)
    p.add_argument("--still_pen", type=float, default=0.05)
    p.add_argument("--eval", choices=["random", "trained"])
    p.add_argument("--eval_eps", type=int, default=20)
    p.add_argument("--live", default="", help="dir for episodes.jsonl (one row per episode) and gens.log")
    p.add_argument("--eval_seed", type=int, default=12345, help="weights seed for --eval random")
    p.add_argument("--ckpt", default=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                  "ckpt", "selfplay_s0.pkl"))
    a = p.parse_args()

    import selfplay_env
    tag = f"eval_{a.eval}" if a.eval else f"train_s{a.seed}"
    env = selfplay_env.SelfPlayEnv(a.seed, max_ticks=a.max_ticks, still_pen=a.still_pen, tag=tag)

    if a.eval:
        th = (np.random.default_rng(a.eval_seed).normal(0, 0.5, sum(SIZES)) if a.eval == "random"
              else pickle.load(open(a.ckpt, "rb"))["theta"])
        infos = []
        for e in range(a.eval_eps):
            env.seed(a.eval_seed + e)
            infos.append(episode(env, th, th))
            i = infos[-1]
            print(f"eval {a.eval} ep {e}: outcome={i['outcome']} ticks={i.get('ticks')} "
                  f"valid={i.get('valid')} " + " ".join(
                      f"{w}:r={i['per'][w]['reward']:+.2f},moved={i['per'][w]['moved_steps']}"
                      for w in WHO), flush=True)
        print(line(f"EVAL {a.eval}", tally(infos)), flush=True)
        return

    os.makedirs(os.path.dirname(a.ckpt), exist_ok=True)
    rng = np.random.default_rng(a.seed)
    st = {"theta": rng.normal(0, 0.5, sum(SIZES)), "gens": [], "episodes": 0}
    if os.path.exists(a.ckpt):
        st = pickle.load(open(a.ckpt, "rb"))
        rng.bit_generator.state = st["rng"]
        print(f"resumed {a.ckpt}: {len(st['gens'])} gens, {st['episodes']} episodes", flush=True)
        env.count = st["episodes"]          # video names and episode_index continue
    while len(st["gens"]) < a.gens and st["episodes"] + 2 * a.pairs <= a.max_episodes:
        t0 = time.time()
        eps = rng.normal(size=(a.pairs, len(st["theta"])))
        fit, infos = np.zeros((a.pairs, 2)), []
        for k in range(a.pairs):
            side, ep_seed = WHO[k % 2], int(rng.integers(2**31))
            for j, sgn in enumerate((1, -1)):
                cand = st["theta"] + sgn * a.sigma * eps[k]
                env.seed(ep_seed)
                th1, th2 = (cand, st["theta"]) if side == "P1" else (st["theta"], cand)
                info = episode(env, th1, th2, np.random.default_rng(ep_seed))
                infos.append(info)
                fit[k, j] = info["per"][side]["reward"]
                if a.live:
                    live_row(a.live, len(st["gens"]), st["episodes"] + len(infos) - 1, side, info)
        adv = fit[:, 0] - fit[:, 1]
        if adv.std() > 0:
            st["theta"] = st["theta"] + a.lr / a.pairs * ((adv / adv.std())[:, None] * eps).sum(0)
        st["episodes"] += len(infos)
        t = tally(infos)
        t.update(gen=len(st["gens"]), cand_fit=round(float(fit.mean()), 3), secs=round(time.time() - t0))
        st["gens"].append(t)
        st["rng"] = rng.bit_generator.state
        pickle.dump(st, open(a.ckpt + ".tmp", "wb")); os.replace(a.ckpt + ".tmp", a.ckpt)
        msg = line(f"gen {t['gen']}", t, f" cand_fit={t['cand_fit']:+.3f} secs={t['secs']}")
        print(msg, flush=True)
        if a.live:
            with open(os.path.join(a.live, "gens.log"), "a") as f:
                f.write(time.strftime("%Y-%m-%dT%H:%M:%S ") + msg + "\n")
    with open(te_path(), "a") as f:
        f.write(json.dumps({"run": env.run_id, "gens": st["gens"]}) + "\n")


def live_row(d, gen, ep, cand_side, info):
    os.makedirs(d, exist_ok=True)
    row = {"generation": gen, "episode": ep, "outcome": info["outcome"], "candidate_side": cand_side,
           "kills": {w: info["per"][w]["kill"] for w in WHO},
           "moved_steps": {w: info["per"][w]["moved_steps"] for w in WHO},
           "fitness": {w: info["per"][w]["reward"] for w in WHO},
           "ticks": info.get("ticks"), "valid_v3": bool(info.get("valid")),
           "run": os.environ.get("NID_SP_RUN"), "episode_index": info.get("episode_index"),
           "start": info.get("start"), "video": info.get("video"),
           "round_state": info.get("round_state"), "stale_deaths": info.get("stale_deaths"),
           "raw_outcome": info.get("raw_outcome"), "actions": info.get("actions"),
           "t": time.strftime("%Y-%m-%dT%H:%M:%S")}
    with open(os.path.join(d, "episodes.jsonl"), "a") as f:
        f.write(json.dumps(row) + "\n")


def te_path():
    import nidtrain_env
    return nidtrain_env.FARM / "selfplay_gens.jsonl"


if __name__ == "__main__":
    main()
