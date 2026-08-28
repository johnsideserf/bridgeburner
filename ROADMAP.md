# Bridgeburner roadmap

## Done (2026-08-27)

- Engine + PSRO-lite solver with held-out best-response evaluation, first-player
  and comeback metrics, cross-ruleset summary.
- Ruleset locked: **the pile is the clock, torches within 2 ranks, equal turns**
  (tiebreak: top card, then next card down). Confirmed over 3 seeds.
- Live solver dashboard (`dashboard.py`), bot-game viewer and human-vs-bot table
  (`/play`), turn-by-turn trace tool.

## Next

- **`cheap_spans 2`** (spans 1–2 cost 1 action) shipped as the optional
  "Quick Foundations" house rule: 17-turn rounds, first build on turn ~2, best
  comeback rates, ~30% fewer burns. Promote to the standard rules if
  playtesting prefers it.
- **Richer bot vocabulary** so "one dominant strategy" isn't an artifact of the
  gene space: bait builds, River denial (fording away the card the rival
  needs), torch conservation, colour-aware burn timing.
- **Interaction metrics** in the solver summary: turns to first build, share of
  turns where a burn was available, builds burned within one turn.
- **Human playtesting** with the locked rules; feed observed human plans back
  into the bot vocabulary. Watch for the **clock drain**: a first player ahead
  on the tiebreak can empty the pile on their own turn and end the round
  before P2 replies (legal; no bot plays it; a hand-written drainer moved P1
  from 49% to 51%). The `clock_reply` rule flag (P2 always gets a reply turn
  when the pile runs out) is implemented as `Current+ClockReply`; in
  simulation it over-corrects for bots (P1 win 48–49% -> 45–46%, 2 seeds x
  400 games, nothing else changes), so it is **not** in the standard rules.
  Adopt it only if humans actually play the drain line.
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
