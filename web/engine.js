// Bridgeburner engine — a line-for-line port of engine.py.
// Cards are [rank 1..13, color] with RED = 0, BLK = 1. Parity with the Python
// engine is enforced by test/parity.test.js against Python-exported fixtures.

export const RED = 0, BLK = 1;

// --- rules ------------------------------------------------------------------
// rules keys (all optional): slack, salvage, burn_cost2, hand_limit, clock,
// p2_extra, first_turn_actions, equal_turns, burn_span, cheap_spans, clock_reply
export const CURRENT_RULES = { clock: true, equal_turns: true };

// --- RNG -----------------------------------------------------------------------
export function mulberry32(seed) {
  let a = seed >>> 0;
  const rng = () => {
    a = (a + 0x6D2B79F5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
  rng.shuffle = arr => { for (let i = arr.length - 1; i > 0; i--) { const j = Math.floor(rng() * (i + 1)); [arr[i], arr[j]] = [arr[j], arr[i]]; } return arr; };
  return rng;
}

export function freshDeck() {
  const d = [];
  for (let r = 1; r <= 13; r++) for (const c of [RED, RED, BLK, BLK]) d.push([r, c]);
  return d;
}

// --- helpers -------------------------------------------------------------------
const same = (a, b) => a[0] === b[0] && a[1] === b[1];
const indexOf = (list, card) => list.findIndex(c => same(c, card));
const has = (list, card) => indexOf(list, card) >= 0;
function removeCard(list, card) { const i = indexOf(list, card); if (i >= 0) list.splice(i, 1); }
// Python's min()/max() return the FIRST extreme element; keep that.
function minBy(list, key) { let best = null, bk = null; for (const x of list) { const k = key(x); if (best === null || k < bk) { best = x; bk = k; } } return best; }
function maxByTuple(list, key) {
  let best = null, bk = null;
  for (const x of list) { const k = key(x); if (best === null || k[0] > bk[0] || (k[0] === bk[0] && k[1] > bk[1])) { best = x; bk = k; } }
  return best;
}
function dedupe(cards) { const out = []; for (const c of cards) if (!has(out, c)) out.push(c); return out; }
export const chainLen = (cards, floor) => new Set(cards.filter(c => c[0] > floor).map(c => c[0])).size;

// --- game state ------------------------------------------------------------------
export class Game {
  constructor(rules, rng) {
    this.rules = rules || {}; this.rng = rng;
    const d = freshDeck(); if (rng) rng.shuffle(d);
    const n2 = 7 + (this.rules.p2_extra || 0);
    this.hands = [d.slice(0, 7), d.slice(7, 7 + n2)];
    this.river = d.slice(7 + n2, 10 + n2);
    this.draw = d.slice(10 + n2);
    this.discard = [];
    this.bridges = [[], []];
    this.turn = 0; this.turn_count = 0;
    this.first_to3 = null; this.first_to4 = null;
    this.burns = [0, 0];
  }
  static fromSnapshot(rules, s) {
    const g = new Game(rules, null);
    g.hands = s.hands.map(h => h.map(c => [...c]));
    g.river = s.river.map(c => [...c]); g.draw = s.draw.map(c => [...c]);
    g.discard = s.discard.map(c => [...c]); g.bridges = s.bridges.map(b => b.map(c => [...c]));
    g.turn = s.turn; g.turn_count = s.turn_count; g.burns = [...s.burns];
    return g;
  }
  clone() { return Game.fromSnapshot(this.rules, snapshot(this)); }
  canDraw() { return this.draw.length > 0 || (this.discard.length > 0 && !this.rules.clock); }
  drawCard() {
    if (!this.draw.length && this.discard.length && !this.rules.clock) {
      this.draw = this.discard; this.discard = [];
      if (this.rng) this.rng.shuffle(this.draw);
    }
    return this.draw.length ? this.draw.pop() : null;
  }
  burnCost(targetRank) { if (this.rules.burn_cost2) return 2; return targetRank >= 11 ? 2 : 1; }
  buildCost(me) { return this.bridges[me].length < (this.rules.cheap_spans || 0) ? 1 : 2; }
  paceOk(me) { const s = this.rules.slack; if (s == null) return true; return this.bridges[me].length >= this.bridges[1 - me].length - s; }
}

export function snapshot(g) {
  return { hands: g.hands.map(h => h.map(c => [...c])), river: g.river.map(c => [...c]), draw: g.draw.map(c => [...c]),
           discard: g.discard.map(c => [...c]), bridges: g.bridges.map(b => b.map(c => [...c])),
           turn: g.turn, turn_count: g.turn_count, burns: [...g.burns] };
}

export function compareBridges(a, b) {
  for (let i = 0; i < Math.min(a.length, b.length); i++) {
    const x = a[a.length - 1 - i][0], y = b[b.length - 1 - i][0];
    if (x !== y) return x > y ? 0 : 1;
  }
  return null;
}
export function clockWinner(g) {
  const [a, b] = g.bridges;
  if (a.length !== b.length) return a.length > b.length ? 0 : 1;
  return compareBridges(a, b);
}
export function equalTurnsWinner(g) {
  const done = g.bridges.map(b => b.length >= 5);
  if (done[0] && done[1]) return compareBridges(g.bridges[0], g.bridges[1]);
  return done[0] ? 0 : 1;
}
export function turnActions(g) { return g.turn_count === 0 ? (g.rules.first_turn_actions ?? 2) : 2; }

export function legalBurnCards(g, me) {
  const opp = 1 - me;
  if (!g.bridges[opp].length || !g.paceOk(me)) return [];
  const [tr, tc] = g.bridges[opp][g.bridges[opp].length - 1];
  const hi = tr + (g.rules.burn_span ?? 99);
  return g.hands[me].filter(c => c[1] === tc && tr < c[0] && c[0] <= hi);
}
export function buildable(g, me) {
  const b = g.bridges[me]; const floor = b.length ? b[b.length - 1][0] : 0;
  return g.hands[me].filter(c => c[0] > floor);
}

// All legal [action, cost] pairs for `me` with `left` actions remaining.
export function legalActions(g, me, left) {
  const out = [];
  if (g.canDraw()) out.push([[0], 1]);
  const bc = g.buildCost(me);
  if (left >= bc) for (const c of dedupe(buildable(g, me))) out.push([[1, c], bc]);
  if (g.bridges[1 - me].length) {
    const tr = g.bridges[1 - me][g.bridges[1 - me].length - 1][0]; const cost = g.burnCost(tr);
    if (cost <= left) for (const c of dedupe(legalBurnCards(g, me))) out.push([[2, c], cost]);
  }
  for (const c of dedupe(g.hands[me])) for (let i = 0; i < g.river.length; i++) out.push([[3, c, i], 1]);
  if (g.river.length) out.push([[4], 1]);
  if (g.bridges[me].length) out.push([[5], 1]);
  out.push([[9], 99]);
  return out;
}

// Apply an action. Returns its cost, null if illegal, 99 = pass (ends turn).
export function doAction(g, me, act) {
  const hand = g.hands[me]; const k = act[0];
  if (k === 0) { const c = g.drawCard(); if (c === null) return null; hand.push(c); return 1; }
  if (k === 1) {
    const card = act[1]; const b = g.bridges[me]; const floor = b.length ? b[b.length - 1][0] : 0;
    if (!has(hand, card) || card[0] <= floor) return null;
    const cost = g.buildCost(me);
    removeCard(hand, card); b.push([...card]);
    if (b.length === 3 && g.first_to3 === null) g.first_to3 = me;
    if (b.length === 4 && g.first_to4 === null) g.first_to4 = me;
    return cost;
  }
  if (k === 2) {
    const card = act[1]; const opp = 1 - me;
    if (!g.bridges[opp].length || !g.paceOk(me)) return null;
    const [tr, tc] = g.bridges[opp][g.bridges[opp].length - 1];
    if (!has(hand, card) || card[1] !== tc || card[0] <= tr) return null;
    if (card[0] > tr + (g.rules.burn_span ?? 99)) return null;
    const cost = g.burnCost(tr);
    removeCard(hand, card); g.discard.push([...card]);
    g.bridges[opp].pop();
    if (g.river.length) g.discard.push(g.river.shift());
    g.river.push([tr, tc]);
    if (g.rules.salvage) { const c2 = g.drawCard(); if (c2 !== null) g.hands[opp].push(c2); }
    return cost;
  }
  if (k === 3) {
    const [, hcard, ridx] = act;
    if (!has(hand, hcard) || ridx >= g.river.length) return null;
    removeCard(hand, hcard); g.discard.push([...hcard]);
    hand.push(g.river.splice(ridx, 1)[0]);
    const c2 = g.drawCard(); if (c2 !== null) g.river.push(c2);
    return 1;
  }
  if (k === 4) {
    if (!g.river.length) return null;
    g.discard.push(...g.river); g.river = [];
    for (let i = 0; i < 3; i++) { const c2 = g.drawCard(); if (c2 === null) break; g.river.push(c2); }
    return 1;
  }
  if (k === 5) { if (!g.bridges[me].length) return null; g.discard.push(g.bridges[me].pop()); return 1; }
  return 99;
}

// --- policy (gene-driven rule bot) ------------------------------------------------
export const GENE_KEYS = ["burn_min", "spend_cap", "build_trig", "keep_chain", "mortar", "ford_gain", "race_at", "demolish", "armor", "endgame"];

export function visibleCounts(g, me) {
  const vis = [new Array(14).fill(0), new Array(14).fill(0)];
  for (const c of g.hands[me]) vis[c[1]][c[0]]++;
  for (const c of g.river) vis[c[1]][c[0]]++;
  for (const br of g.bridges) for (const c of br) vis[c[1]][c[0]]++;
  return vis;
}
export function unseenHigher(g, me, card, vis) {
  const [r, col] = card; vis = vis || visibleCounts(g, me);
  let seen = 0; for (let i = r + 1; i <= 13; i++) seen += vis[col][i];
  return 2 * (13 - r) - seen;
}

export function policy(genes, g, me, left) {
  const [burn_min, spend_cap, build_trig, keep_chain, mortar, ford_gain, race_at, demolish, armor, endgame] = genes;
  const hand = g.hands[me]; const opp = 1 - me;
  const mylen = g.bridges[me].length, olen = g.bridges[opp].length;
  const floor = mylen ? g.bridges[me][mylen - 1][0] : 0;
  const b = buildable(g, me).filter(c => c[0] !== 13 || mylen === 4);   // King guard
  const bcost = g.buildCost(me);
  const rank = c => c[0];

  const pickBuild = () => {
    let cand = b;
    if (mortar && mylen >= 3) { const faces = cand.filter(c => c[0] >= 11); if (faces.length) cand = faces; }
    if (armor) {
      const vis = visibleCounts(g, me); const u = cand.map(c => unseenHigher(g, me, c, vis));
      const m = Math.min(...u); cand = cand.filter((c, i) => u[i] === m);
    }
    if (keep_chain) return maxByTuple(cand, c => [chainLen(hand, c[0]), -c[0]]);
    return minBy(cand, rank);
  };

  // 0. win now
  const ob = g.bridges[opp];
  if (mylen === 4 && g.rules.equal_turns && me === 1 && ob.length >= 5) {
    const fin = left >= bcost ? b : [];
    const outcome = new Map(fin.map(c => [c, compareBridges(ob, [...g.bridges[me], c])]));
    const wins = fin.filter(c => outcome.get(c) === 1);
    if (wins.length) return [1, minBy(wins, rank)];
    const q = legalBurnCards(g, me);
    if (q.length && g.burnCost(ob[ob.length - 1][0]) <= left) return [2, minBy(q, rank)];
    const draws = fin.filter(c => outcome.get(c) === null);
    if (draws.length) return [1, minBy(draws, rank)];
  } else if (mylen === 4 && b.length && left >= bcost) {
    return [1, minBy(b, rank)];
  }
  // 1. burn
  if (olen >= burn_min) {
    const q = legalBurnCards(g, me);
    if (q.length) {
      const tr = ob[ob.length - 1][0]; const card = minBy(q, rank);
      if (card[0] <= tr + spend_cap && g.burnCost(tr) <= left) return [2, card];
    }
  }
  // 2. build
  if (b.length && left >= bcost) {
    const need = 5 - mylen;
    const ok = build_trig === 0 || (build_trig === 1 && chainLen(hand, floor) >= need) || (build_trig === 2 && chainLen(hand, floor) >= need - 1);
    if (ok || olen >= race_at || g.draw.length <= endgame) return [1, pickBuild()];
  }
  // 3. demolish if stuck
  if (demolish && mylen && !b.length) {
    const newfloor = mylen >= 2 ? g.bridges[me][mylen - 2][0] : 0;
    if (chainLen(hand, newfloor) > chainLen(hand, floor)) return [5];
  }
  // 4. ford
  if (g.river.length && hand.length) {
    let bi = 0; for (let i = 1; i < g.river.length; i++) if (g.river[i][0] > g.river[bi][0]) bi = i;
    const low = minBy(hand, rank);
    if (g.river[bi][0] - low[0] >= ford_gain) return [3, low, bi];
  }
  // 5. draw
  if (g.canDraw()) return [0];
  if (g.river.length) return [4];
  return [9];
}

// --- turn loop ---------------------------------------------------------------------
export function afterAction(g, rules, me) {
  if (g.bridges[me].length >= 5) {
    if (!rules.equal_turns) return { over: true, winner: me, turnOver: true };
    if (me === 0) return { over: false, winner: null, turnOver: true };
    return { over: true, winner: equalTurnsWinner(g), turnOver: true };
  }
  return { over: false, winner: null, turnOver: false };
}
export function endTurn(g, rules, me) {
  const lim = rules.hand_limit;
  if (lim) { const h = g.hands[me]; while (h.length > lim) { const low = minBy(h, c => c[0]); removeCard(h, low); g.discard.push(low); } }
  g.turn = 1 - me; g.turn_count += 1;
  if (rules.equal_turns && me === 1 && g.bridges.some(b => b.length >= 5)) return { over: true, winner: equalTurnsWinner(g) };
  if (rules.clock && !g.draw.length) {
    if (rules.clock_reply && me === 0) return { over: false, winner: null };
    return { over: true, winner: clockWinner(g) };
  }
  return { over: false, winner: null };
}
// Play out `me`'s whole turn with a decision function decide(g, me, left) -> action.
export function botTurn(decide, g, rules, me, onAction) {
  let left = turnActions(g);
  while (left > 0) {
    const act = decide(g, me, left);
    let cost = doAction(g, me, act);
    if (cost === null) cost = 99;
    if (onAction) onAction(g, me, act, cost, left);
    if (act[0] === 2 && cost !== 99) g.burns[me] += 1;
    left -= cost;
    const r = afterAction(g, rules, me);
    if (r.over) return { over: true, winner: r.winner };
    if (r.turnOver) break;
  }
  return endTurn(g, rules, me);
}
export function play(genesA, genesB, rules, g, onAction, maxTurns = 200) {
  const genes = [genesA, genesB];
  while (g.turn_count < maxTurns) {
    const me = g.turn;
    const r = botTurn((gg, m, left) => policy(genes[m], gg, m, left), g, rules, me, onAction);
    if (r.over) return { winner: r.winner, game: g };
  }
  return { winner: null, game: g };
}
