// Bridgeburner — browser game vs bot. The engine is engine.js (a parity-tested
// port of the Python engine); bot decisions run in worker.js.
import { Game, mulberry32, legalActions, doAction, afterAction, endTurn, turnActions, snapshot, CURRENT_RULES, RED } from './engine.js';
import { BOTS, makeBot } from './bots.js';

const $ = id => document.getElementById(id);
const RANK = { 1: 'A', 11: 'J', 12: 'Q', 13: 'K' };
const rk = r => RANK[r] || String(r);
const key = c => c[0] + ':' + c[1];
const same = (a, b) => a && b && a[0] === b[0] && a[1] === b[1];
const cs = c => `${rk(c[0])}${c[1] === RED ? '♥' : '♠'}`;
const sleep = ms => new Promise(r => setTimeout(r, ms));
const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
const esc = s => String(s).replace(/[&<>]/g, ch => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[ch]));

// ---------------------------------------------------------------- bot worker
let worker = null, pending = new Map(), reqId = 0, inlineDecide = null;
function botInit(bot, seed) {
  if (window.Worker && location.protocol !== 'file:') {
    if (!worker) {
      worker = new Worker('worker.js', { type: 'module' });
      worker.onmessage = e => { const p = pending.get(e.data.id); if (p) { pending.delete(e.data.id); p(e.data.action); } };
    }
    worker.postMessage({ type: 'new', bot, seed });
  } else {
    inlineDecide = makeBot(bot, { rollouts: 96, rng: mulberry32(seed) });
  }
}
function botDecide(g, me, left, seed) {
  if (inlineDecide) return Promise.resolve(inlineDecide(g, me, left));
  return new Promise(res => { const id = ++reqId; pending.set(id, res); worker.postMessage({ type: 'decide', id, rules: g.rules, snapshot: snapshot(g), me, left, seed }); });
}

// ---------------------------------------------------------------- match state
const M = { round: 0, score: [0, 0], bot: 'Equilibrium', rules: { ...CURRENT_RULES }, seed: 1, humanFirst: true };
const S = { g: null, h: 0, b: 1, left: 0, over: false, winner: null, busy: false, sel: null, pending: null, log: [] };

function readControls() {
  M.bot = $('botSel').value;
  M.rules = { ...CURRENT_RULES };
  if ($('optTorch').checked) M.rules.burn_span = 2;
  if ($('optCheap').checked) M.rules.cheap_spans = 2;
  M.seed = Math.max(1, Math.min(999999, parseInt($('seedIn').value, 10) || 1));
  M.startFirst = $('optFirst').checked;
}
function writeUrl() {
  const q = new URLSearchParams({ seed: M.seed, bot: M.bot });
  if (M.rules.burn_span) q.set('torch', '1'); if (M.rules.cheap_spans) q.set('cheap', '1');
  if (!M.startFirst) q.set('first', 'bot');
  history.replaceState(null, '', '?' + q);
}

function newMatch() {
  readControls(); writeUrl();
  M.round = 0; M.score = [0, 0]; M.humanFirst = M.startFirst;
  $('chipBotName').textContent = BOTS[M.bot].label; $('botName').textContent = BOTS[M.bot].label;
  S.log = [];
  nextRound();
}
function nextRound() {
  M.round += 1;
  const seed = (M.seed * 7919 + M.round * 104729) >>> 0;
  S.g = new Game(M.rules, mulberry32(seed));
  S.h = M.humanFirst ? 0 : 1; S.b = 1 - S.h;
  S.over = false; S.winner = null; S.sel = null; S.pending = null; S.busy = false;
  S.left = turnActions(S.g);
  botInit(M.bot, seed ^ 0x9e3779b9);
  log('sys', `Round ${M.round}. ${M.humanFirst ? 'You go first.' : `${BOTS[M.bot].label} goes first.`}`);
  $('banner').className = 'banner';
  render(true);
  if (S.g.turn === S.b) botTurn();
}

// ---------------------------------------------------------------- turn flow
function describe(g, me, act, cost) {
  const k = act[0];
  if (k === 0) return 'draws a card';
  if (k === 1) return `builds ${cs(act[1])}`;
  if (k === 2) return `burns with ${cs(act[1])}${cost === 2 ? ' (2 actions)' : ''}`;
  if (k === 3) return `fords: ${cs(act[1])} out, ${cs(g.hands[me][g.hands[me].length - 1])} in`;
  if (k === 4) return 'flushes the River';
  if (k === 5) return 'demolishes their own top card';
  return 'ends the turn';
}
function log(who, text) { S.log.push({ who, text }); if (S.log.length > 60) S.log.shift(); renderLog(); }

async function applyAction(me, act) {
  const g = S.g;
  const opp = 1 - me;
  const burnTarget = act[0] === 2 ? g.bridges[opp][g.bridges[opp].length - 1] : null;
  if (burnTarget && !reduced) await animateBurn(opp === S.h ? 'myBridge' : 'botBridge');
  const cost = doAction(g, me, act);
  if (cost === null) return null;
  if (act[0] === 2) g.burns[me] += 1;
  log(me === S.h ? 'you' : 'bot', (me === S.h ? 'You ' : `${BOTS[M.bot].label} `) + describe(g, me, act, cost) + '.');
  return cost;
}
function finishTurn(me) {
  const r = endTurn(S.g, M.rules, me);
  if (r.over) return endRound(r.winner);
  S.left = turnActions(S.g);
  return false;
}
function endRound(winner) {
  S.over = true; S.winner = winner;
  if (winner === S.h) M.score[0] += 1; else if (winner === S.b) M.score[1] += 1;
  const done = M.score[0] === 2 || M.score[1] === 2;
  const b = $('banner');
  const how = S.g.bridges.some(x => x.length >= 5) ? 'finished bridge' : 'the clock ran out';
  b.className = 'banner show ' + (winner === S.h ? 'win' : winner === S.b ? 'lose' : 'draw');
  b.innerHTML = (winner === S.h ? 'You win the round' : winner === S.b ? `${esc(BOTS[M.bot].label)} wins the round` : 'Drawn round')
    + `<small>${how} · match ${M.score[0]}–${M.score[1]}</small>`
    + (done ? `<small><b>${M.score[0] > M.score[1] ? 'You take the match.' : 'The bot takes the match.'}</b></small>` : '');
  log('sys', winner === null ? 'Drawn round.' : winner === S.h ? 'You win the round.' : `${BOTS[M.bot].label} wins the round.`);
  M.humanFirst = !M.humanFirst;
  return true;
}

async function botTurn() {
  S.busy = true; render();
  const me = S.b; const g = S.g;
  let left = turnActions(g);
  $('botStatus').innerHTML = '<span class="think">thinking…</span>';
  while (left > 0 && !S.over) {
    const act = await botDecide(g, me, left, M.seed);
    await sleep(reduced ? 60 : 420);
    let cost = await applyAction(me, act);
    if (cost === null) cost = 99;
    left -= cost;
    render();
    const r = afterAction(g, M.rules, me);
    if (r.over) { endRound(r.winner); break; }
    if (r.turnOver) break;
  }
  if (!S.over) finishTurn(me);
  S.busy = false;
  render();
}

async function humanAct(act) {
  if (S.busy || S.over || S.g.turn !== S.h) return;
  const legal = legalActions(S.g, S.h, S.left).some(([a]) => JSON.stringify(a) === JSON.stringify(act));
  if (!legal) return;
  S.busy = true; S.sel = null; S.pending = null;
  const cost = await applyAction(S.h, act);
  if (cost === null) { S.busy = false; render(); return; }
  S.left -= (cost === 99 ? S.left : cost);
  const r = afterAction(S.g, M.rules, S.h);
  render();
  if (r.over) { endRound(r.winner); S.busy = false; render(); return; }
  if (r.turnOver || S.left <= 0 || cost === 99) {
    if (finishTurn(S.h)) { S.busy = false; render(); return; }
    S.busy = false;
    await sleep(reduced ? 0 : 250);
    return botTurn();
  }
  S.busy = false; render();
}

// ---------------------------------------------------------------- rendering
function cardEl(c, cls = '', animate = false) {
  if (!c) return `<div class="card back ${cls}"></div>`;
  const face = c[0] >= 11 ? ' face' : '';
  return `<div class="card ${c[1] === RED ? 'red' : 'black'}${face} ${cls}${animate ? ' deal' : ''}" data-card="${key(c)}"><span class="pip">${c[1] === RED ? '♥' : '♠'}</span>${rk(c[0])}<span class="pip b">${c[1] === RED ? '♥' : '♠'}</span></div>`;
}
function bridgeHtml(cards, animate) {
  let s = '';
  for (let i = 0; i < 5; i++) {
    if (i) s += '<span class="link">›</span>';
    s += cards[i] ? cardEl(cards[i], '', animate && i === cards.length - 1) : `<div class="slot">${i + 1}</div>`;
  }
  return s;
}
function animateBurn(bridgeId) {
  const el = $(bridgeId).querySelector('.card:last-of-type');
  if (!el) return Promise.resolve();
  el.classList.add('burning');
  return sleep(900);
}
function legalFor(kind, card) { return legalActions(S.g, S.h, S.left).filter(([a]) => a[0] === kind && (!card || same(a[1], card))); }

function render(deal = false) {
  const g = S.g; if (!g) return;
  const myTurn = g.turn === S.h && !S.over && !S.busy;
  $('turnLabel').textContent = S.over ? 'Round over' : g.turn === S.h ? 'Your turn' : `${BOTS[M.bot].label}'s turn`;
  const al = $('actionsLeft'); al.textContent = S.over ? '–' : g.turn === S.h ? S.left : '·';
  al.className = 'big num' + (g.turn === S.h && !S.over ? ' sky' : '');
  $('turnNo').textContent = `turn ${g.turn_count + 1}`;
  $('roundNo').textContent = `${M.round} / 3`;
  $('burnsKv').textContent = `${g.burns[S.h]} / ${g.burns[S.b]}`;
  $('chipYou').innerHTML = `<small>You</small>${M.score[0]}`; $('chipYou').className = 'chip' + (M.score[0] === 2 ? ' won' : '');
  $('chipBot').innerHTML = `<small>${esc(BOTS[M.bot].label)}</small>${M.score[1]}`; $('chipBot').className = 'chip' + (M.score[1] === 2 ? ' lost' : '');
  $('botStatus').textContent = S.busy && g.turn === S.b ? '' : `${g.hands[S.b].length} cards`;
  if (S.busy && g.turn === S.b) $('botStatus').innerHTML = '<span class="think">thinking…</span>';
  $('youStatus').textContent = myTurn ? (S.pending === 'ford' ? 'pick a River card' : S.sel ? `${cs(S.sel)} selected` : 'click a card') : 'your hand';

  $('botHand').innerHTML = g.hands[S.b].map(() => cardEl(null)).join('');
  $('botBridge').innerHTML = bridgeHtml(g.bridges[S.b], deal);
  $('myBridge').innerHTML = bridgeHtml(g.bridges[S.h], deal);
  const torches = new Set(myTurn ? legalFor(2).map(([a]) => key(a[1])) : []);
  $('myHand').innerHTML = [...g.hands[S.h]].sort((a, b) => a[0] - b[0] || a[1] - b[1]).map(c => {
    let cls = myTurn ? 'can' : '';
    if (S.sel && same(S.sel, c)) cls += ' sel';
    if (torches.has(key(c))) cls += ' torch';
    if (S.pending === 'ford' && !(S.sel && same(S.sel, c))) cls += ' dim';
    return cardEl(c, cls, deal);
  }).join('');
  $('river').innerHTML = g.river.map(c => cardEl(c, S.pending === 'ford' ? 'target' : '')).join('');
  $('pileN').textContent = g.draw.length; $('pileN').className = g.draw.length <= 6 ? 'ember' : '';
  $('discardN').textContent = g.discard.length;
  $('deck').innerHTML = Array.from({ length: Math.max(1, Math.min(4, Math.ceil(g.draw.length / 9))) }, () => cardEl(null)).join('');
  $('rowMyHand').classList.toggle('active', g.turn === S.h && !S.over);
  $('rowBotHand').classList.toggle('active', g.turn === S.b && !S.over);
  renderActions(myTurn);
}
function renderActions(myTurn) {
  const box = $('actions');
  if (S.over) {
    const done = M.score[0] === 2 || M.score[1] === 2;
    box.innerHTML = done ? `<button class="btn gold wide" data-cmd="new">Deal a new match</button>`
                         : `<button class="btn leaf wide" data-cmd="next">Next round <span class="cost">${M.humanFirst ? 'you go first' : 'bot goes first'}</span></button>`;
    return;
  }
  if (!myTurn) { box.innerHTML = `<span class="hint">${S.busy ? `${esc(BOTS[M.bot].label)} is playing…` : ''}</span>`; return; }
  const btn = (label, action, cls = '', dis = false, cost = null) =>
    `<button class="btn ${cls}" ${dis ? 'disabled' : ''} data-act='${action === null ? '' : JSON.stringify(action)}'>${label}${cost != null ? `<span class="cost">${cost}</span>` : ''}</button>`;
  let html = '', hint = 'Click a card in your hand, or draw.';
  if (S.pending === 'ford') { html += btn('Cancel', 'cancel'); hint = `<b>Ford:</b> pick the River card to take for ${cs(S.sel)}.`; }
  else if (S.sel) {
    const b = legalFor(1, S.sel)[0], u = legalFor(2, S.sel)[0], f = legalFor(3, S.sel);
    const bcost = S.g.buildCost(S.h);
    html += btn('Build', b ? b[0] : null, 'sky', !b, bcost);
    html += btn('Burn', u ? u[0] : null, 'ember', !u, u ? u[1] : '');
    html += btn('Ford', f.length ? 'ford' : null, 'gold', !f.length, 1);
    hint = b ? `Build ${cs(S.sel)} on your bridge.` : u ? `${cs(S.sel)} can burn their top card.` : `${cs(S.sel)} can't be built here — ford it, or burn with it later.`;
  }
  const draw = legalFor(0)[0], flush = legalFor(4)[0], dem = legalFor(5)[0];
  html += btn('Draw', draw ? draw[0] : null, '', !draw, 1) + btn('Flush', flush ? flush[0] : null, '', !flush, 1) + btn('Demolish', dem ? dem[0] : null, '', !dem, 1) + btn('End turn', [9]);
  box.innerHTML = html + `<span class="hint">${hint}</span>`;
}
function renderLog() { $('log').innerHTML = [...S.log].reverse().map(e => `<div class="${e.who}">${e.who === 'sys' ? '' : ''}${esc(e.text)}</div>`).join(''); }

// ---------------------------------------------------------------- input
document.addEventListener('click', e => {
  const b = e.target.closest('button[data-cmd]');
  if (b) { if (b.dataset.cmd === 'new') newMatch(); else nextRound(); return; }
  const a = e.target.closest('button[data-act]');
  if (a) {
    if (!a.dataset.act) return;
    const v = JSON.parse(a.dataset.act);          // 'cancel' | 'ford' | an action array
    if (v === 'cancel') { S.sel = null; S.pending = null; render(); return; }
    if (v === 'ford') { S.pending = 'ford'; render(); return; }
    humanAct(v);
    return;
  }
  const c = e.target.closest('.card[data-card]');
  if (!c || S.busy || S.over || S.g.turn !== S.h) return;
  const card = c.dataset.card.split(':').map(Number);
  if (S.pending === 'ford' && c.parentElement.id === 'river') {
    const idx = [...c.parentElement.children].indexOf(c);
    return humanAct([3, S.sel, idx]);
  }
  if (c.parentElement.id === 'myHand') { S.sel = S.sel && same(S.sel, card) ? null : card; S.pending = null; render(); }
});
$('newMatch').addEventListener('click', newMatch);
$('botSel').addEventListener('change', () => { $('botBlurb').innerHTML = `<p>${esc(BOTS[$('botSel').value].blurb)}</p>`; });

// ---------------------------------------------------------------- boot
(function boot() {
  $('botSel').innerHTML = Object.entries(BOTS).map(([k, v]) => `<option value="${k}">${esc(v.label)}</option>`).join('');
  const q = new URLSearchParams(location.search);
  $('botSel').value = BOTS[q.get('bot')] ? q.get('bot') : 'Equilibrium';
  $('optTorch').checked = q.get('torch') === '1'; $('optCheap').checked = q.get('cheap') === '1';
  $('optFirst').checked = q.get('first') !== 'bot';
  $('seedIn').value = parseInt(q.get('seed'), 10) || Math.floor(Math.random() * 99999) + 1;
  $('botBlurb').innerHTML = `<p>${esc(BOTS[$('botSel').value].blurb)}</p>`;
  newMatch();
})();
