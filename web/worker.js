// Bot decisions off the main thread so the table never stutters.
import { Game, mulberry32 } from './engine.js';
import { makeBot } from './bots.js';

let decide = null;
const ROLLOUTS = { Rollout: 160 };

self.onmessage = e => {
  const m = e.data;
  if (m.type === 'new') {
    decide = makeBot(m.bot, { rollouts: ROLLOUTS[m.bot] || 96, rng: mulberry32(m.seed >>> 0) });
    return;
  }
  if (m.type === 'decide') {
    const g = Game.fromSnapshot(m.rules, m.snapshot);
    g.rng = mulberry32((m.seed + g.turn_count) >>> 0);   // for non-clock reshuffles only
    const action = decide(g, m.me, m.left);
    self.postMessage({ type: 'action', id: m.id, action });
  }
};
