# Bridgeburner roadmap

## Done (2026-08-27)

- Engine + PSRO-lite solver with held-out best-response evaluation, first-player
  and comeback metrics, cross-ruleset summary.
- Ruleset locked: **the pile is the clock, torches within 2 ranks, equal turns**
  (tiebreak: top card, then next card down). Confirmed over 3 seeds.
- Live solver dashboard (`dashboard.py`), bot-game viewer and human-vs-bot table
  (`/play`), turn-by-turn trace tool.

## Next

- **Decide on `cheap_spans 2`** (spans 1–2 cost 1 action): 17-turn rounds,
  first build on turn ~2, best comeback rates, ~30% fewer burns. Adopt or not,
  then sync `RULES.md` / PDF.
- **Richer bot vocabulary** so "one dominant strategy" isn't an artifact of the
  gene space: bait builds, River denial (fording away the card the rival
  needs), torch conservation, colour-aware burn timing.
- **Interaction metrics** in the solver summary: turns to first build, share of
  turns where a burn was available, builds burned within one turn.
- **Human playtesting** with the locked rules; feed observed human plans back
  into the bot vocabulary.
- **Miniature CFR/MCCFR** (smaller deck, 3-card bridge) for a provably optimal
  baseline to sanity-check the PSRO results.

## Later: online playable version

Goal: play Bridgeburner in a browser against a friend or a bot, with a link.

- **Server:** the engine is already pure Python with a JSON action API
  (`game_session.py`, `/api/new`, `/api/act`). Move sessions from in-memory
  to a small store (SQLite/Redis), add a second human seat and turn
  notifications (WebSocket or long-poll), and per-game invite links.
- **Client:** `play.html` is the seed of the UI — split into a standalone app
  (hand/bridge/River components already exist), add animations for burns and
  the clock, mobile layout, and a match (best-of-three) wrapper.
- **Bots as opponents:** expose the solver's equilibrium strategies at several
  strengths (Builder → Sniper → Equilibrium) and a "watch the bots" replay
  feed for onboarding.
- **Hosting:** stateless HTTP + one websocket process is enough for early
  traffic; deploy behind TLS, no accounts needed for invite-link play.
- **Balance loop:** log finished online games (anonymised) and replay them
  through the solver's metrics so the ruleset keeps being validated against
  real human play, not just bots.
