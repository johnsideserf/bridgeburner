#!/usr/bin/env python3
"""Human-vs-bot sessions and bot-vs-bot replays for the dashboard's /play page."""
import random
from engine import (G, do, policy, legal_actions, after_action, end_turn, bot_turn,
                    turn_actions, play, CURRENT_RULES)
from trace_game import STRATEGIES, cs

def card_label(c): return cs(c)

def action_label(g, me, act, cost, hide_draw=False):
    k = act[0]
    if k == 0: return "Draw" + ("" if hide_draw or not g.hands[me] else f" ({cs(g.hands[me][-1])})")
    if k == 1: return f"Build {cs(act[1])}"
    if k == 2: return f"Burn with {cs(act[1])}" + (" (2 actions)" if cost == 2 else "")
    if k == 3: return f"Ford: discard {cs(act[1])}, take River #{act[2]+1}"
    if k == 4: return "Flush the River"
    if k == 5: return "Demolish own top card"
    return "End turn"

def legal_menu(g, me, left):
    out = []
    for act, cost in legal_actions(g, me, left):
        k = act[0]
        if k == 0: label = "Draw a card"
        elif k == 1: label = f"Build {cs(act[1])}"
        elif k == 2: label = f"Burn with {cs(act[1])}"
        elif k == 3: label = f"Ford: discard {cs(act[1])} for {cs(g.river[act[2]])}"
        elif k == 4: label = "Flush the River"
        elif k == 5: label = "Demolish your top card"
        else: label = "End turn"
        out.append({"action": [k] + [list(x) if isinstance(x, tuple) else x for x in act[1:]],
                    "cost": cost, "label": label})
    return out

class Session:
    def __init__(self, rules=None, bot="Equilibrium", seed=0, human_first=True):
        self.rules = dict(CURRENT_RULES if rules is None else rules)
        self.bot_genes = STRATEGIES[bot]; self.bot_name = bot
        self.g = G(self.rules, random.Random(seed))
        self.human = 0 if human_first else 1
        self.bot = 1 - self.human
        self.left = turn_actions(self.g)
        self.burns = 0
        self.over = False; self.winner = None
        self.log = []
        if self.g.turn == self.bot: self._bot_turn()

    def _bot_turn(self):
        me = self.bot; turn = self.g.turn_count
        def hook(g, who, act, cost):
            self.log.append({"who": "bot", "turn": turn + 1,
                             "text": action_label(g, who, act, cost, hide_draw=True)})
        over, winner = bot_turn(self.bot_genes, self.g, self.rules, me, hook)
        if over: self.over, self.winner = True, winner
        else: self.left = turn_actions(self.g)

    def act(self, action):
        if self.over: raise ValueError("game is over")
        if self.g.turn != self.human: raise ValueError("not your turn")
        act = tuple(tuple(x) if isinstance(x, list) else x for x in action)
        legal = {a for a, c in legal_actions(self.g, self.human, self.left)}
        if act not in legal: raise ValueError(f"illegal action {action}")
        me = self.human
        cost = do(self.g, me, act)
        if cost is None: raise ValueError("engine rejected action")
        self.log.append({"who": "human", "turn": self.g.turn_count + 1,
                         "text": action_label(self.g, me, act, cost)})
        if act[0] == 2: self.g.burns[me] += 1
        self.left -= cost
        over, winner, turn_over = after_action(self.g, self.rules, me)
        if over:
            self.over, self.winner = True, winner
        elif turn_over or self.left <= 0:
            over, winner = end_turn(self.g, self.rules, me)
            if over: self.over, self.winner = True, winner
            else: self._bot_turn()
        return self.state()

    def state(self):
        g = self.g; h = self.human; b = self.bot
        winner = None
        if self.over:
            winner = "draw" if self.winner is None else ("human" if self.winner == h else "bot")
        return {
            "turn": 0 if g.turn == h else 1, "left": self.left if g.turn == h else 0,
            "turn_count": g.turn_count, "human_seat": h + 1,
            "hand": [list(c) for c in sorted(g.hands[h])],
            "bot_hand_size": len(g.hands[b]),
            "river": [list(c) for c in g.river], "pile": len(g.draw), "discard": len(g.discard),
            "bridges": {"human": [list(c) for c in g.bridges[h]], "bot": [list(c) for c in g.bridges[b]]},
            "legal": legal_menu(g, h, self.left) if (g.turn == h and not self.over) else [],
            "log": self.log[-40:], "winner": winner, "over": self.over,
            "rules": self.rules, "bot": self.bot_name, "burns": list(g.burns),
        }

def replay_frames(seed=0, a="Equilibrium", b="Equilibrium", rules=None):
    rules = CURRENT_RULES if rules is None else rules
    g = G(rules, random.Random(seed))
    frames = []
    def snap(who, text, turn_count):
        frames.append({"turn_count": turn_count, "who": who, "action": text,
                       "hands": [[list(c) for c in sorted(g.hands[0])], [list(c) for c in sorted(g.hands[1])]],
                       "bridges": [[list(c) for c in g.bridges[0]], [list(c) for c in g.bridges[1]]],
                       "river": [list(c) for c in g.river], "pile": len(g.draw),
                       "discard": len(g.discard), "burns": list(g.burns)})
    snap(None, "Deal", 0)
    def hook(gg, me, act, cost): snap(me, action_label(gg, me, act, cost), gg.turn_count)
    r, g2 = play(STRATEGIES[a], STRATEGIES[b], rules, random.Random(seed), g=g, on_action=hook)
    turns = frames[-1]["turn_count"] + 1 if frames[-1]["who"] is not None else g2.turn_count
    return {"frames": frames, "result": None if r is None else r, "turns": turns,
            "a": a, "b": b, "rules": rules}
