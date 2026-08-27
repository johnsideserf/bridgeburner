#!/usr/bin/env python3
"""
Approximate Nash / exploitability analysis for Bridgeburner (PSRO-lite).

For each ruleset:
  1. Start with a pool of seed strategies (builder / hoarder / sniper / etc).
  2. Repeat PSRO iterations:
       a. Round-robin the pool -> empirical payoff matrix (incremental).
       b. Solve the matrix game (regret matching) -> Nash mixture over pool.
       c. Search the full gene space (coordinate ascent + restarts) for the
          best response to that mixture.
       d. Re-evaluate that best response on a FRESH, larger batch of games
          (held-out) so the reported exploitability isn't winner's-curse noise.
       e. Add exploiter to pool; stop when held-out BR winrate <= --stop.
  3. Report final mixture, exploitability trajectory, first-player advantage,
     comeback rate, stall rate, burns/game under mixture self-play.

Usage:
  python solve.py                              # all rulesets, quick
  python solve.py --rules NoLimit,BurnCost2    # prefix match on names
  python solve.py --games 500 --iters 8 --restarts 5 --heldout 6
"""
import argparse, random, sys
from engine import (GENE_SPACE, GENE_KEYS, rand_genes, gname, winrate, play,
                    match_stats)

SEEDS = {
    #                 burn spend build keep mort ford race demo armor end
    "Builder":        (99,  13,   0,    1,   0,   2,   99,  1,   0,   0),
    "Hoarder":        (0,   13,   1,    1,   0,   1,   99,  0,   0,   0),
    "Sniper":         (3,   13,   1,    1,   0,   1,   4,   0,   0,   0),
    "Balanced":       (2,   5,    0,    1,   1,   2,   3,   1,   0,   0),
    "Armored":        (2,   5,    0,    1,   0,   2,   3,   1,   1,   0),
    "Clockwatcher":   (2,   5,    1,    1,   0,   2,   3,   1,   0,   12),
}

# Name -> rules dict. Add candidate rulesets here; select with --rules.
RULESETS = {
    "NoLimit":          {},
    "KeepPace":         {"slack": 0},
    "Slack1":           {"slack": 1},
    "Salvage":          {"salvage": True},
    "BurnCost2":        {"burn_cost2": True},
    "HandLimit8":       {"hand_limit": 8},
    "BurnCost2+Hand8":  {"burn_cost2": True, "hand_limit": 8},
    "P2x1":             {"p2_extra": 1},
    "P1a1":             {"first_turn_actions": 1},
    "Clock":            {"clock": True},
    "Clock+P2x1":       {"clock": True, "p2_extra": 1},
    "Clock+P2x2":       {"clock": True, "p2_extra": 2},
    "Clock+P1a1":       {"clock": True, "first_turn_actions": 1},
    "Clock+BurnCost2":  {"clock": True, "burn_cost2": True},
    "Clock+BurnCost2+P2x1": {"clock": True, "burn_cost2": True, "p2_extra": 1},
}

def select_rulesets(spec):
    """'all' or comma-separated prefixes of RULESETS names."""
    if spec == "all": return list(RULESETS)
    out = []
    for p in spec.split(","):
        p = p.strip()
        hits = [n for n in RULESETS if n.lower() == p.lower()] or \
               [n for n in RULESETS if n.lower().startswith(p.lower())]
        if not hits:
            sys.exit(f"unknown ruleset '{p}'. Known: {', '.join(RULESETS)}")
        out.extend(h for h in hits if h not in out)
    return out

def solve_matrix(M, iters=3000):
    """Nash mix for symmetric zero-sum matrix (row payoff = winrate) via
    regret matching."""
    n = len(M)
    reg = [0.0]*n; strat_sum = [0.0]*n
    cur = [1.0/n]*n
    for _ in range(iters):
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

def payoff_matrix(pool, rules, games, rng, prev=None):
    """Round-robin winrate matrix. If prev (k x k) is given, only the new
    rows/cols for pool[k:] are simulated."""
    n = len(pool); k = len(prev) if prev else 0
    M = [[0.5]*n for _ in range(n)]
    for i in range(k):
        for j in range(k):
            M[i][j] = prev[i][j]
    for i in range(n):
        for j in range(max(i+1, k), n):
            w = winrate(pool[i], pool[j], rules, games, rng)
            M[i][j] = w; M[j][i] = 1.0 - w
    return M

def wr_vs_mix(genes, pool, mix, rules, n, rng):
    """Win rate of genes against pool sampled from mix."""
    w = 0.0
    for i in range(n):
        opp = pool[rng.choices(range(len(pool)), weights=mix)[0]]
        if i % 2 == 0:
            r, _ = play(genes, opp, rules, random.Random(rng.random()))
            w += 1.0 if r == 0 else 0.5 if r is None else 0.0
        else:
            r, _ = play(opp, genes, rules, random.Random(rng.random()))
            w += 1.0 if r == 1 else 0.5 if r is None else 0.0
    return w / n

def evaluate_heldout(genes, pool, mix, rules, games, rng, mult=4):
    """Unbiased re-evaluation of a candidate on games*mult fresh games."""
    return wr_vs_mix(genes, pool, mix, rules, games*mult, rng)

def best_response(pool, mix, rules, rng, games, restarts, passes=2, accept=0.02):
    """Coordinate-ascent search over the full gene space vs the mixture.
    Returns (genes, search_winrate) -- the search winrate is optimistically
    biased; call evaluate_heldout on the result."""
    best_g, best_w = None, -1.0
    starts = [rand_genes(rng) for _ in range(restarts)]
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
                    if tw > w + accept:
                        g, w = trial, tw
        if w > best_w:
            best_g, best_w = tuple(g), w
    return best_g, best_w

def selfplay_stats(pool, mix, rules, rng, n):
    """Mixture self-play: first-player edge, comebacks, stalls, turns, burns."""
    lead3_loses = lead4_loses = lead3_n = lead4_n = stalls = 0
    fp = tot_turns = burns = 0.0
    for i in range(n):
        a = rng.choices(range(len(pool)), weights=mix)[0]
        b = rng.choices(range(len(pool)), weights=mix)[0]
        r, g = play(pool[a], pool[b], rules, random.Random(rng.random()))
        tot_turns += g.turn_count; burns += sum(g.burns)
        if r is None:
            stalls += 1; fp += 0.5; continue
        fp += 1.0 if r == 0 else 0.0
        if g.first_to3 is not None:
            lead3_n += 1
            if r != g.first_to3: lead3_loses += 1
        if g.first_to4 is not None:
            lead4_n += 1
            if r != g.first_to4: lead4_loses += 1
    return {"first_player": fp/n,
            "comeback3": lead3_loses/max(1, lead3_n),
            "comeback4": lead4_loses/max(1, lead4_n),
            "stalls": stalls/n, "avg_turns": tot_turns/n,
            "burns_per_game": burns/n}

def solve_ruleset(rname, rules, args, rng):
    print(f"\n{'='*68}\n{rname}  {rules}\n{'='*68}")
    pool = [tuple(v) for v in SEEDS.values()]
    names = list(SEEDS)
    exploit_traj = []
    M = None
    for it in range(args.iters):
        M = payoff_matrix(pool, rules, args.games, rng, prev=M)
        mix = solve_matrix(M)
        br, search_w = best_response(pool, mix, rules, rng,
                                     args.games, args.restarts)
        brw = evaluate_heldout(br, pool, mix, rules, args.games, rng,
                               mult=args.heldout)
        exploit_traj.append(brw)
        top = sorted(zip(names, mix), key=lambda kv: -kv[1])[:3]
        mixdesc = "  ".join(f"{nm}:{p:.0%}" for nm, p in top if p > 0.02)
        print(f" iter {it+1}: nash mix [{mixdesc}]  "
              f"best-response wins {brw:.1%} held-out (search saw {search_w:.0%})")
        pool.append(br); names.append(f"BR{it+1}")
        if brw <= args.stop:
            print(f"   -> mixture is near-unexploitable within this "
                  f"policy space (<= {args.stop:.0%}); stopping early")
            break
        print(f"   exploiter: {gname(br)}")
    M = payoff_matrix(pool, rules, args.games, rng, prev=M)
    mix = solve_matrix(M)
    st = selfplay_stats(pool, mix, rules, rng, args.games*args.heldout)
    support = sum(1 for p in mix if p > 0.03)
    print(" FINAL:")
    for nm, p, g in sorted(zip(names, mix, pool), key=lambda kv: -kv[1]):
        if p > 0.03:
            print(f"   {p:5.0%}  {nm:8s} {gname(g)}")
    print(f"   exploitability trajectory: "
          + " -> ".join(f"{w:.0%}" for w in exploit_traj))
    print(f"   first-player wins {st['first_player']:.0%}   "
          f"comeback after opp hits 3: {st['comeback3']:.0%}  after 4: {st['comeback4']:.0%}")
    print(f"   stalls {st['stalls']:.0%}   avg game {st['avg_turns']:.0f} turns   "
          f"burns/game {st['burns_per_game']:.1f}   mixture support {support}")
    return {"ruleset": rname, "exploit": exploit_traj[-1], "support": support, **st}

def run(args):
    rng = random.Random(args.seed)
    rows = [solve_ruleset(n, RULESETS[n], args, rng)
            for n in select_rulesets(args.rules)]
    print(f"\n{'='*68}\nSUMMARY (lower exploit, ~50% first-player, higher comeback, "
          f"support>1 = better)\n{'='*68}")
    print(f"{'ruleset':18s} {'exploit':>7s} {'P1 win':>7s} {'cb@3':>5s} {'cb@4':>5s} "
          f"{'stall':>5s} {'turns':>5s} {'burns':>5s} {'supp':>4s}")
    for r in rows:
        print(f"{r['ruleset']:18s} {r['exploit']:7.0%} {r['first_player']:7.0%} "
              f"{r['comeback3']:5.0%} {r['comeback4']:5.0%} {r['stalls']:5.0%} "
              f"{r['avg_turns']:5.0f} {r['burns_per_game']:5.1f} {r['support']:4d}")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--games", type=int, default=200,
                    help="games per evaluation during search")
    ap.add_argument("--iters", type=int, default=6, help="PSRO iterations")
    ap.add_argument("--restarts", type=int, default=3,
                    help="random restarts in best-response search")
    ap.add_argument("--heldout", type=int, default=5,
                    help="held-out evaluation uses games*heldout fresh games")
    ap.add_argument("--stop", type=float, default=0.53,
                    help="stop when held-out best-response winrate <= this")
    ap.add_argument("--rules", default="all",
                    help="'all' or comma-separated ruleset name prefixes")
    ap.add_argument("--seed", type=int, default=3)
    run(ap.parse_args())
