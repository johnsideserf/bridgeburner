# bridge-burner-proofs

Balance analysis for **Bridgeburner**, a two-player card game played with a
standard 52-card deck. Contains the game engine, a PSRO-style equilibrium
solver, earlier heuristic-bot tournaments, and the illustrated rules PDF.

## The game (current ruleset)

Race to build a 5-card ascending bridge (aces low, suits ignored). 2 actions
per turn:

| Action   | Cost | Effect |
|----------|------|--------|
| Draw     | 1    | Take top card of the draw pile |
| Build    | 2    | Play a hand card higher than your rightmost bridge card |
| Burn     | 1*   | Discard a same-color, higher hand card to destroy opponent's rightmost bridge card (it washes into the River). **Salvage:** the burned player draws 1 card. *Burning a J/Q costs 2 actions; Kings are unburnable (nothing beats them) |
| Ford     | 1    | Discard any hand card, take any of the 3 face-up River cards, refill River |
| Flush    | 1    | Replace all 3 River cards |
| Demolish | 1    | Remove your own rightmost bridge card |

Setup: deal 7 each, 3 face-up River cards. Empty draw pile → reshuffle
discards. First 5-card bridge wins; best of three.

## Files

- `engine.py` — fast game engine + parameterized policy space (~4k strategies).
  Rule variants via a `rules` dict: `slack` (keep-pace), `salvage`,
  `burn_cost2`, `hand_limit`.
- `solve.py` — PSRO-lite: round-robin payoff matrix → Nash mixture (regret
  matching) → coordinate-ascent best-response search → exploitability
  trajectory, comeback and stall rates.
- `sim.py`, `sim2.py` — earlier heuristic-bot tournaments (rounds 1 & 2).
- `make_rules.py` — regenerates `Bridgeburner_Rules.pdf` (reportlab).
- `RULES.md` — plain-text rulebook (same content as the PDF; keep in sync).

## Key findings so far

- Original unrestricted rules: equilibrium = hoard high cards + burn
  everything; 23% of games stall. Broken.
- Keep-pace rule (burn only if your bridge >= theirs): unexploitable but
  kills comebacks (4% after opponent reaches 4) and most interaction.
- Slack-1 keep-pace: re-enables the burn lock. Rejected.
- **Salvage (shipped):** burns always legal, burned player draws 1.
  Exploitability ~55% and falling, 0% stalls, ~12-turn games, best comeback
  rate (10% after opponent hits 4). Equilibrium burns concentrate on
  spans 4–5.

## Run it

```
python solve.py                                  # quick pass (~5 min)
python solve.py --games 500 --iters 8 --restarts 5   # thorough (~30–60 min)
python make_rules.py                             # rebuild the PDF
```

## Open questions

- Push exploitability from ~55% toward 50%: more eval games, richer gene
  space (e.g. color-aware burn timing, river denial).
- CFR/MCCFR solver for a miniature Bridgeburner (smaller deck, 3-card
  bridge) to get provably optimal play for the abstraction.
- Human playtesting of the salvage meta: do burns really cluster late?
