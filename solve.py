#!/usr/bin/env python3
"""
Approximate Nash / exploitability analysis for Bridgeburner (PSRO-lite).

For each ruleset:
  1. Start with a pool of seed strategies (builder / hoarder / sniper / etc).
  2. Repeat PSRO iterations:
       a. Round-robin the pool -> empirical payoff matrix.
       b. Solve the matrix game (regret matching) -> Nash mixture over pool.
       c. Search the full gene space (coordinate ascent + restarts) for the
          best response to that mixture.
       d. Exploitability ~= best-response winrate - 50%.  Add exploiter to pool.
  3. Report final mixture (the approx. perfect strategy), exploitability
     trajectory, comeback rate and stall rate under mixture self-play.

Run bigger on a laptop:   python solve.py --games 400 --iters 8 --restarts 4
"""
import argparse, random, sys
from engine import (GENE_SPACE, GENE_KEYS, rand_genes, gname, winrate, play)

SEEDS = {
    #                 burn spend build keep mort ford race demo
    "Builder":        (99,  13,   0,    1,   0,   2,   99,  1),
    "Hoarder":        (0,   13,   1,    1,   0,   1,   99,  0),
    "Sniper":         (3,   13,   1,    1,   0,   1,   4,   0),
    "Balanced":       (2,   5,    0,    1,   1,   2,   3,   1),
}

RULESETS = {
    "NoLimit  (burn always allowed)":        {},
    "KeepPace (burn iff your len >= theirs)": {"slack": 0},
    "Slack1   (burn iff len >= theirs - 1)":  {"slack": 1},
    "Salvage  (burned player draws 1)":       {"salvage": True},
    "Slack1 + Salvage":                       {"slack": 1, "salvage": True},
}

def solve_matrix(M, iters=3000):
    """Nash mix for zero-sum matrix (row payoff = winrate) via regret matching."""
    n = len(M)
    reg = [0.0]*n; strat_sum = [0.0]*n
    cur = [1.0/n]*n
    for _ in range(iters):
        # payoff of each pure row vs current col strategy (symmetric game)
        u = [sum(M[i][j]*cur[j] for j in range(n)) for i in range(n)]
        avg = sum(u[i]*cur[i] for i in range(n))
        for i in range(n):
            reg[i] += u[i] - avg
        pos = [max(r, 0.0) for r in reg]
        s = sum(pos)
        cur = [p/s for p in pos] if s > 0 else [1.0/n]*n
        for i in range(n):
            strat_sum[i] += cur[i]
    t = sum(strat_sum)
    return [s/t for s in strat_sum]

def wr_vs_mix(genes, pool, mix, rules, n, rng):
    """Win rate of genes against pool sampled from mix."""
    w = 0.0
    for i in range(n):
        j = rng.choices(range(len(pool)), weights=mix)[0]
        opp = pool[j]
        if i % 2 == 0:
            r, _ = play(genes, opp, rules, random.Random(rng.random()))
            w += 1.0 if r == 0 else 0.5 if r is None else 0.0
        else:
            r, _ = play(opp, genes, rules, random.Random(rng.random()))
            w += 1.0 if r == 1 else 0.5 if r is None else 0.0
    return w / n

def best_response(pool, mix, rules, rng, games, restarts, passes=2):
    """Coordinate-ascent search over the full gene space vs the mixture."""
    best_g, best_w = None, -1.0
    starts = [rand_genes(rng) for _ in range(restarts)]
    # also start from the current best pool member
    starts.append(pool[max(range(len(pool)), key=lambda i: mix[i])])
    for g0 in starts:
        g = list(g0)
        w = wr_vs_mix(tuple(g), pool, mix, rules, games, rng)
        for _ in range(passes):
            keys = list(range(len(GENE_KEYS)))
            rng.shuffle(keys)
            for ki in keys:
                key = GENE_KEYS[ki]
                for val in GENE_SPACE[key]:
                    if val == g[ki]: continue
                    trial = g[:]; trial[ki] = val
                    tw = wr_vs_mix(tuple(trial), pool, mix, rules, games, rng)
                    if tw > w + 0.01:
                        g, w = trial, tw
        if w > best_w:
            best_g, best_w = tuple(g), w
    return best_g, best_w

def comeback_stats(pool, mix, rules, rng, n):
    """Self-play under the mixture: comeback + stall rates."""
    lead3_loses = lead4_loses = lead3_n = lead4_n = stalls = 0
    tot_turns = 0
    for i in range(n):
        a = rng.choices(range(len(pool)), weights=mix)[0]
        b = rng.choices(range(len(pool)), weights=mix)[0]
        r, g = play(pool[a], pool[b], rules, random.Random(rng.random()))
        tot_turns += g.turn_count
        if r is None: stalls += 1; continue
        if g.first_to3 is not None:
            lead3_n += 1
            if r != g.first_to3: lead3_loses += 1
        if g.first_to4 is not None:
            lead4_n += 1
            if r != g.first_to4: lead4_loses += 1
    return (lead3_loses/max(1,lead3_n), lead4_loses/max(1,lead4_n),
            stalls/n, tot_turns/n)

def run(args):
    rng = random.Random(args.seed)
    for rname, rules in RULESETS.items():
        print(f"\n{'='*68}\n{rname}\n{'='*68}")
        pool = [tuple(v) for v in SEEDS.values()]
        names = list(SEEDS)
        exploit_traj = []
        for it in range(args.iters):
            # payoff matrix
            n = len(pool)
            M = [[0.5]*n for _ in range(n)]
            for i in range(n):
                for j in range(i+1, n):
                    w = winrate(pool[i], pool[j], rules, args.games, rng)
                    M[i][j] = w; M[j][i] = 1.0 - w
            mix = solve_matrix(M)
            br, brw = best_response(pool, mix, rules, rng,
                                    args.games, args.restarts)
            exploit_traj.append(brw)
            top = sorted(zip(names, mix), key=lambda kv: -kv[1])[:3]
            mixdesc = "  ".join(f"{nm}:{p:.0%}" for nm, p in top if p > 0.02)
            print(f" iter {it+1}: nash mix [{mixdesc}]  "
                  f"best-response wins {brw:.0%}")
            if brw <= 0.55:
                print("   -> mixture is near-unexploitable within this "
                      "policy space; stopping early")
                pool.append(br); names.append(f"BR{it+1}")
                break
            pool.append(br); names.append(f"BR{it+1}")
            print(f"   exploiter: {gname(br)}")
        # final mixture + health metrics
        n = len(pool)
        M = [[0.5]*n for _ in range(n)]
        for i in range(n):
            for j in range(i+1, n):
                w = winrate(pool[i], pool[j], rules, args.games, rng)
                M[i][j] = w; M[j][i] = 1.0 - w
        mix = solve_matrix(M)
        cb3, cb4, stall, avg_t = comeback_stats(pool, mix, rules, rng,
                                                args.games*4)
        print(" FINAL:")
        for nm, p, g in sorted(zip(names, mix, pool), key=lambda kv: -kv[1]):
            if p > 0.03:
                print(f"   {p:5.0%}  {nm:5s} {gname(g)}")
        print(f"   exploitability trajectory: "
              + " -> ".join(f"{w:.0%}" for w in exploit_traj))
        print(f"   comeback after opponent hits 3: {cb3:.0%}"
              f"   after 4: {cb4:.0%}")
        print(f"   stalls {stall:.0%}   avg game {avg_t:.0f} turns")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--games", type=int, default=120,
                    help="games per evaluation (raise on a fast machine)")
    ap.add_argument("--iters", type=int, default=4, help="PSRO iterations")
    ap.add_argument("--restarts", type=int, default=2,
                    help="random restarts in best-response search")
    ap.add_argument("--seed", type=int, default=3)
    run(ap.parse_args())
