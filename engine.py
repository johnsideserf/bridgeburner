#!/usr/bin/env python3
"""
Bridgeburner engine + parameterized policy space.

Rules dict keys:
  slack      : None = burning unrestricted
               int n = may burn only if len(my bridge) >= len(opp bridge) - n
  salvage    : True = when your bridge card is burned, draw 1 card as compensation
  burn_cost2 : True = burning always costs 2 actions
  hand_limit : int  = discard down to this at end of turn
  clock      : True = no reshuffle; round ends when the draw pile runs out
               (longer bridge wins, tiebreak higher top card, else draw)
  p2_extra   : int  = extra cards dealt to the second player
  first_turn_actions : int = actions on the very first turn of the game (P1)
  equal_turns: True = a finished bridge by the first player doesn't end the
               round until the second player has had their turn too; both
               finished -> higher top card, then next card down, ... ; identical -> draw
  burn_span  : int  = torch card must be at most this many ranks above target
  cheap_spans: int  = building costs 1 action while your bridge has fewer
                      than this many cards (2 actions after)
"""
import random

RED, BLK = 0, 1

# The locked ruleset (2026-08-27): pile is the clock, torches within 2 ranks,
# second player always gets a reply turn. See RULES.md.
CURRENT_RULES = {"clock": True, "burn_span": 2, "equal_turns": True}

def fresh_deck():
    # (rank 1..13, color) x2 copies per color = 52
    return [(r, c) for r in range(1, 14) for c in (RED, RED, BLK, BLK)]

class G:
    __slots__ = ("rules","rng","hands","river","draw","discard","bridges",
                 "turn","turn_count","first_to3","first_to4","burns")
    def __init__(self, rules, rng):
        self.rules = rules; self.rng = rng
        d = fresh_deck(); rng.shuffle(d)
        n2 = 7 + rules.get("p2_extra", 0)
        self.hands   = [d[:7], d[7:7+n2]]
        self.river   = d[7+n2:10+n2]
        self.draw    = d[10+n2:]
        self.discard = []
        self.bridges = [[], []]
        self.turn = 0; self.turn_count = 0
        self.first_to3 = None   # who first reached bridge length 3 / 4
        self.first_to4 = None
        self.burns = [0, 0]     # burns performed by each player

    def can_draw(self):
        return bool(self.draw) or (bool(self.discard) and not self.rules.get("clock"))

    def draw_card(self):
        if not self.draw and self.discard and not self.rules.get("clock"):
            self.draw, self.discard = self.discard, []
            self.rng.shuffle(self.draw)
        return self.draw.pop() if self.draw else None

    def burn_cost(self, target_rank):
        if self.rules.get("burn_cost2"): return 2
        return 2 if target_rank >= 11 else 1

    def build_cost(self, me):
        return 1 if len(self.bridges[me]) < self.rules.get("cheap_spans", 0) else 2

    def pace_ok(self, me):
        s = self.rules.get("slack")
        if s is None: return True
        return len(self.bridges[me]) >= len(self.bridges[1-me]) - s

def compare_bridges(a, b):
    """Tiebreak between two bridges of equal length: compare the top card,
    then the next card down, and so on. Returns 0/1 or None if identical."""
    for x, y in zip(reversed(a), reversed(b)):
        if x[0] != y[0]: return 0 if x[0] > y[0] else 1
    return None

def clock_winner(g):
    """Round ended on the clock: longer bridge wins, then compare_bridges."""
    a, b = g.bridges
    if len(a) != len(b): return 0 if len(a) > len(b) else 1
    return compare_bridges(a, b)

def equal_turns_winner(g):
    """End of the second player's turn with at least one finished bridge:
    the finished side wins; both finished -> higher top card, equal -> None."""
    done = [len(b) >= 5 for b in g.bridges]
    if all(done): return compare_bridges(*g.bridges)
    return 0 if done[0] else 1

def turn_actions(g):
    if g.turn_count == 0: return g.rules.get("first_turn_actions", 2)
    return 2

def legal_burn_cards(g, me):
    opp = 1 - me
    if not g.bridges[opp] or not g.pace_ok(me): return []
    tr, tc = g.bridges[opp][-1]
    hi = tr + g.rules.get("burn_span", 99)
    return [c for c in g.hands[me] if c[1] == tc and tr < c[0] <= hi]

def buildable(g, me):
    b = g.bridges[me]
    floor = b[-1][0] if b else 0
    return [c for c in g.hands[me] if c[0] > floor]

def legal_actions(g, me, left):
    """All legal (action, cost) pairs for `me` with `left` actions remaining."""
    out = []
    if g.can_draw(): out.append(((0,), 1))
    bc = g.build_cost(me)
    if left >= bc:
        for c in dict.fromkeys(buildable(g, me)): out.append(((1, c), bc))
    if g.bridges[1-me]:
        tr = g.bridges[1-me][-1][0]; cost = g.burn_cost(tr)
        if cost <= left:
            for c in dict.fromkeys(legal_burn_cards(g, me)): out.append(((2, c), cost))
    for c in dict.fromkeys(g.hands[me]):
        for i in range(len(g.river)): out.append(((3, c, i), 1))
    if g.river: out.append(((4,), 1))
    if g.bridges[me]: out.append(((5,), 1))
    out.append(((9,), 99))
    return out

def do(g, me, act):
    """Apply action, return cost or None if illegal. 99 = pass (ends turn)."""
    hand = g.hands[me]; k = act[0]
    if k == 0:                                   # draw
        c = g.draw_card()
        if c is None: return None
        hand.append(c); return 1
    if k == 1:                                   # build card
        card = act[1]; b = g.bridges[me]
        floor = b[-1][0] if b else 0
        if card not in hand or card[0] <= floor: return None
        cost = g.build_cost(me)
        hand.remove(card); b.append(card)
        if len(b) == 3 and g.first_to3 is None: g.first_to3 = me
        if len(b) == 4 and g.first_to4 is None: g.first_to4 = me
        return cost
    if k == 2:                                   # burn card
        card = act[1]; opp = 1 - me
        if not g.bridges[opp] or not g.pace_ok(me): return None
        tr, tc = g.bridges[opp][-1]
        if card not in hand or card[1] != tc or card[0] <= tr: return None
        if card[0] > tr + g.rules.get("burn_span", 99): return None
        cost = g.burn_cost(tr)
        hand.remove(card); g.discard.append(card)
        g.bridges[opp].pop()
        if g.river: g.discard.append(g.river.pop(0))
        g.river.append((tr, tc))
        if g.rules.get("salvage"):
            c2 = g.draw_card()
            if c2 is not None: g.hands[opp].append(c2)
        return cost
    if k == 3:                                   # ford hand_card river_idx
        _, hcard, ridx = act
        if hcard not in hand or ridx >= len(g.river): return None
        hand.remove(hcard); g.discard.append(hcard)
        hand.append(g.river.pop(ridx))
        c2 = g.draw_card()
        if c2 is not None: g.river.append(c2)
        return 1
    if k == 4:                                   # flush
        if not g.river: return None
        g.discard.extend(g.river); g.river = []
        for _ in range(3):
            c2 = g.draw_card()
            if c2 is None: break
            g.river.append(c2)
        return 1
    if k == 5:                                   # demolish
        if not g.bridges[me]: return None
        g.discard.append(g.bridges[me].pop()); return 1
    return 99                                    # pass

# ------------------------------------------------------------------ policy
# Genes (all small discrete spaces):
GENE_SPACE = {
    "burn_min":   [0, 1, 2, 3, 4, 99],   # burn only if opp bridge >= this (99 never)
    "spend_cap":  [2, 5, 13],            # burn only with card <= target rank + cap
    "build_trig": [0, 1, 2],             # 0 build asap; 1 need full chain; 2 chain-1
    "keep_chain": [0, 1],                # choose build card preserving longest chain
    "mortar":     [0, 1],                # prefer J/Q/K for bridge slots 4-5
    "ford_gain":  [1, 2, 3],             # ford if best river - worst hand >= gain
    "race_at":    [3, 4, 99],            # if opp bridge >= this, build asap
    "demolish":   [0, 1],                # tear down own bridge when stuck
    "armor":      [0, 1],                # prefer build card with fewest unseen higher same-color cards
    "endgame":    [0, 6, 12],            # build asap once draw pile <= this many cards
}
GENE_KEYS = list(GENE_SPACE)

def rand_genes(rng):
    return tuple(rng.choice(GENE_SPACE[k]) for k in GENE_KEYS)

def gname(genes):
    return ",".join(f"{k}={v}" for k, v in zip(GENE_KEYS, genes))

def chain_len(cards, floor):
    return len({c[0] for c in cards if c[0] > floor})

def unseen_higher(g, me, card):
    """Copies of higher, same-color cards NOT visible to `me` (own hand, river,
    both bridges). A card with 0 unseen higher cards cannot be burned."""
    r, col = card
    total = 2 * (13 - r)                     # 2 copies per rank per color
    seen = 0
    for c in g.hands[me]:
        if c[1] == col and c[0] > r: seen += 1
    for c in g.river:
        if c[1] == col and c[0] > r: seen += 1
    for br in g.bridges:
        for c in br:
            if c[1] == col and c[0] > r: seen += 1
    return total - seen

def policy(genes, g, me, left, burns_done):
    (burn_min, spend_cap, build_trig, keep_chain,
     mortar, ford_gain, race_at, demolish, armor, endgame) = genes
    hand = g.hands[me]; opp = 1 - me
    mylen = len(g.bridges[me]); olen = len(g.bridges[opp])
    floor = g.bridges[me][-1][0] if g.bridges[me] else 0
    # King guard: a King below slot 5 is a dead end, never build it there.
    b = [c for c in buildable(g, me) if c[0] != 13 or mylen == 4]

    def pick_build():
        cand = b
        if mortar and mylen >= 3:
            faces = [c for c in cand if c[0] >= 11]
            if faces: cand = faces
        if armor:
            u = {c: unseen_higher(g, me, c) for c in cand}
            m = min(u.values())
            cand = [c for c in cand if u[c] == m]
        if keep_chain:
            return max(cand, key=lambda c: (chain_len(hand, c[0]), -c[0]))
        return min(cand, key=lambda c: c[0])

    bcost = g.build_cost(me)
    # 0. win now
    if mylen == 4 and b and left >= bcost:
        return (1, min(b, key=lambda c: c[0]))
    # 1. burn
    if olen >= burn_min:
        q = legal_burn_cards(g, me)
        if q:
            tr = g.bridges[opp][-1][0]
            card = min(q, key=lambda c: c[0])
            if card[0] <= tr + spend_cap and g.burn_cost(tr) <= left:
                return (2, card)
    # 2. build
    if b and left >= bcost:
        need = 5 - mylen
        ok = (build_trig == 0 or
              (build_trig == 1 and chain_len(hand, floor) >= need) or
              (build_trig == 2 and chain_len(hand, floor) >= need - 1))
        if ok or olen >= race_at or len(g.draw) <= endgame:
            return (1, pick_build())
    # 3. demolish if stuck: nothing buildable and tearing down the top card
    #    would give a longer chain (always true when the bridge ends in a K)
    if demolish and g.bridges[me] and not b:
        newfloor = g.bridges[me][-2][0] if mylen >= 2 else 0
        if chain_len(hand, newfloor) > chain_len(hand, floor):
            return (5,)
    # 4. ford
    if g.river and hand:
        bi = max(range(len(g.river)), key=lambda i: g.river[i][0])
        low = min(hand, key=lambda c: c[0])
        if g.river[bi][0] - low[0] >= ford_gain:
            return (3, low, bi)
    # 5. draw
    if g.can_draw():
        return (0,)
    if g.river:
        return (4,)
    return (9,)  # pass

def after_action(g, rules, me):
    """Called after `me` acts. Returns (over, winner, turn_over)."""
    if len(g.bridges[me]) >= 5:
        if not rules.get("equal_turns"): return True, me, True
        if me == 0: return False, None, True     # P1 finished: P2 still gets a turn
        return True, equal_turns_winner(g), True
    return False, None, False

def end_turn(g, rules, me):
    """Hand limit, pass the turn, equal-turns / clock resolution.
    Returns (over, winner)."""
    lim = rules.get("hand_limit")
    if lim:
        h = g.hands[me]
        while len(h) > lim:
            low = min(h, key=lambda c: c[0])
            h.remove(low); g.discard.append(low)
    g.turn = 1 - me; g.turn_count += 1
    if rules.get("equal_turns") and me == 1 and any(len(b) >= 5 for b in g.bridges):
        return True, equal_turns_winner(g)
    if rules.get("clock") and not g.draw:
        return True, clock_winner(g)
    return False, None

def bot_turn(genes, g, rules, me, on_action=None):
    """Play out `me`'s whole turn with `genes`. Returns (over, winner)."""
    left = turn_actions(g); burns = 0
    while left > 0:
        act = policy(genes, g, me, left, burns)
        cost = do(g, me, act)
        if cost is None:
            cost = 99
        if on_action: on_action(g, me, act, cost)
        if act[0] == 2 and cost != 99:
            burns += 1; g.burns[me] += 1
        left -= cost
        over, winner, turn_over = after_action(g, rules, me)
        if over: return True, winner
        if turn_over: break
    return end_turn(g, rules, me)

def play(genesA, genesB, rules, rng, max_turns=200, g=None, on_action=None):
    """Return (winner 0/1/None, game) with A moving first.
    on_action(g, me, act, cost) is called after every applied action."""
    if g is None: g = G(rules, rng)
    genes = (genesA, genesB)
    while g.turn_count < max_turns:
        me = g.turn
        over, winner = bot_turn(genes[me], g, rules, me, on_action)
        if over: return winner, g
    return None, g

def winrate(genesA, genesB, rules, n, rng):
    """A's win rate over n games, alternating first player. Stalls = 0.5."""
    w = 0.0
    for i in range(n):
        if i % 2 == 0:
            r, _ = play(genesA, genesB, rules, random.Random(rng.random()))
            w += 1.0 if r == 0 else 0.5 if r is None else 0.0
        else:
            r, _ = play(genesB, genesA, rules, random.Random(rng.random()))
            w += 1.0 if r == 1 else 0.5 if r is None else 0.0
    return w / n

def match_stats(genesA, genesB, rules, n, rng):
    """A vs B over n games, alternating first player. Returns dict:
    winrate (A's, stalls=0.5), first_player (first mover's win rate),
    stalls, avg_turns, burns_per_game."""
    w = fp = stalls = turns = burns = 0.0
    for i in range(n):
        first, second, a_idx = (genesA, genesB, 0) if i % 2 == 0 else (genesB, genesA, 1)
        r, g = play(first, second, rules, random.Random(rng.random()))
        if r is None:
            stalls += 1; w += 0.5; fp += 0.5
        else:
            w += 1.0 if r == a_idx else 0.0
            fp += 1.0 if r == 0 else 0.0
        turns += g.turn_count; burns += sum(g.burns)
    return {"winrate": w/n, "first_player": fp/n, "stalls": stalls/n,
            "avg_turns": turns/n, "burns_per_game": burns/n}
