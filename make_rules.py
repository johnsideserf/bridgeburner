#!/usr/bin/env python3
"""Bridgeburner - illustrated two-page rules sheet."""
import math
from reportlab.lib.pagesizes import letter
from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas

W, H = letter  # 612 x 792

# Palette
PARCH   = HexColor("#F6EFDF")
PARCH2  = HexColor("#EFE5CE")
INK     = HexColor("#2B2620")
INK_SOFT= HexColor("#5A5245")
EMBER   = HexColor("#D35400")
EMBER_D = HexColor("#A73E00")
FLAME_Y = HexColor("#F5B041")
RIVER   = HexColor("#2E86AB")
RIVER_D = HexColor("#1B5E7D")
RED     = HexColor("#C0392B")
BLACK   = HexColor("#232323")
CARD_BG = HexColor("#FFFDF6")
CARD_ED = HexColor("#B8AD97")
GOLD    = HexColor("#C9A227")
SHADOW  = HexColor("#D8CDB6")

c = canvas.Canvas("/home/claude/bridgeburner/Bridgeburner_Rules.pdf", pagesize=letter)
c.setTitle("Bridgeburner - Rules")
c.setAuthor("A two-player card game")

# ---------------------------------------------------------------- suit glyphs
def heart(x, y, s, col):
    c.saveState(); c.setFillColor(col); c.setStrokeColor(col)
    r = s * 0.28
    c.circle(x - r*0.85, y + s*0.12, r, stroke=0, fill=1)
    c.circle(x + r*0.85, y + s*0.12, r, stroke=0, fill=1)
    p = c.beginPath()
    p.moveTo(x - s*0.5, y + s*0.10)
    p.lineTo(x + s*0.5, y + s*0.10)
    p.lineTo(x, y - s*0.52)
    p.close()
    c.drawPath(p, stroke=0, fill=1)
    c.restoreState()

def diamond(x, y, s, col):
    c.saveState(); c.setFillColor(col)
    p = c.beginPath()
    p.moveTo(x, y + s*0.55); p.lineTo(x + s*0.40, y)
    p.lineTo(x, y - s*0.55); p.lineTo(x - s*0.40, y)
    p.close(); c.drawPath(p, stroke=0, fill=1)
    c.restoreState()

def spade(x, y, s, col):
    c.saveState(); c.setFillColor(col); c.setStrokeColor(col)
    r = s * 0.26
    c.circle(x - r*0.85, y - s*0.10, r, stroke=0, fill=1)
    c.circle(x + r*0.85, y - s*0.10, r, stroke=0, fill=1)
    p = c.beginPath()
    p.moveTo(x - s*0.48, y - s*0.12)
    p.lineTo(x + s*0.48, y - s*0.12)
    p.lineTo(x, y + s*0.55)
    p.close(); c.drawPath(p, stroke=0, fill=1)
    c.setLineWidth(max(1.2, s*0.10))
    c.line(x, y - s*0.12, x, y - s*0.52)
    p2 = c.beginPath()
    p2.moveTo(x - s*0.20, y - s*0.52); p2.lineTo(x + s*0.20, y - s*0.52)
    p2.lineTo(x, y - s*0.36); p2.close()
    c.drawPath(p2, stroke=0, fill=1)
    c.restoreState()

def club(x, y, s, col):
    c.saveState(); c.setFillColor(col); c.setStrokeColor(col)
    r = s * 0.24
    c.circle(x, y + s*0.26, r, stroke=0, fill=1)
    c.circle(x - r*1.05, y - s*0.02, r, stroke=0, fill=1)
    c.circle(x + r*1.05, y - s*0.02, r, stroke=0, fill=1)
    c.setLineWidth(max(1.2, s*0.10))
    c.line(x, y + s*0.05, x, y - s*0.50)
    p2 = c.beginPath()
    p2.moveTo(x - s*0.20, y - s*0.52); p2.lineTo(x + s*0.20, y - s*0.52)
    p2.lineTo(x, y - s*0.34); p2.close()
    c.drawPath(p2, stroke=0, fill=1)
    c.restoreState()

SUITS = {"S": (spade, BLACK), "H": (heart, RED), "D": (diamond, RED), "C": (club, BLACK)}

# ---------------------------------------------------------------- card drawing
def card(x, y, w, rank, suit, face_down=False, tilt=0):
    """Draw a playing card with bottom-left at (x, y). Height = 1.4 * w."""
    h = w * 1.4
    c.saveState()
    c.translate(x + w/2, y + h/2)
    if tilt: c.rotate(tilt)
    c.translate(-w/2, -h/2)
    # shadow
    c.setFillColor(SHADOW)
    c.roundRect(2.5, -2.5, w, h, w*0.10, stroke=0, fill=1)
    if face_down:
        c.setFillColor(HexColor("#8E3B2F"))
        c.setStrokeColor(HexColor("#6E2B22")); c.setLineWidth(1)
        c.roundRect(0, 0, w, h, w*0.10, stroke=1, fill=1)
        c.setStrokeColor(HexColor("#C9A227")); c.setLineWidth(0.8)
        c.roundRect(w*0.12, h*0.09, w*0.76, h*0.82, w*0.06, stroke=1, fill=0)
        c.setLineWidth(0.6)
        step = w * 0.18
        c.saveState()
        p = c.beginPath(); p.roundRect = None
        c.rect(w*0.12, h*0.09, w*0.76, h*0.82, stroke=0, fill=0)
        c.restoreState()
        n = 6
        for i in range(1, n):
            t = i / n
            c.line(w*0.12, h*0.09 + h*0.82*t, w*0.88, h*0.09 + h*0.82*t)
    else:
        fn, col = SUITS[suit]
        c.setFillColor(CARD_BG)
        c.setStrokeColor(CARD_ED); c.setLineWidth(1)
        c.roundRect(0, 0, w, h, w*0.10, stroke=1, fill=1)
        c.setFillColor(col)
        c.setFont("Helvetica-Bold", w*0.30)
        c.drawString(w*0.10, h - w*0.34, rank)
        fn(w*0.22, h*0.16, w*0.20, col)          # small suit under rank corner
        fn(w*0.62, h*0.52, w*0.52, col)          # big center suit
    c.restoreState()

# ---------------------------------------------------------------- icons
def flame(x, y, s, outline=False):
    c.saveState()
    def lick(cx, cy, sw, sh, col):
        c.setFillColor(col)
        p = c.beginPath()
        p.moveTo(cx, cy + sh)
        p.curveTo(cx + sw*0.9, cy + sh*0.55, cx + sw*0.75, cy - sh*0.25, cx, cy - sh*0.5)
        p.curveTo(cx - sw*0.75, cy - sh*0.25, cx - sw*0.9, cy + sh*0.55, cx, cy + sh)
        p.close(); c.drawPath(p, stroke=0, fill=1)
    lick(x, y, s*0.62, s*0.62, EMBER_D)
    lick(x + s*0.04, y - s*0.04, s*0.44, s*0.46, EMBER)
    lick(x + s*0.02, y - s*0.10, s*0.26, s*0.30, FLAME_Y)
    c.restoreState()

def waves(x, y, w, s, col=RIVER):
    c.saveState(); c.setStrokeColor(col); c.setLineWidth(s*0.14); c.setLineCap(1)
    n = max(2, int(w / (s*1.2)))
    seg = w / n
    for row in range(2):
        yy = y - row * s * 0.55
        p = c.beginPath()
        p.moveTo(x, yy)
        for i in range(n):
            x0 = x + i*seg
            p.curveTo(x0 + seg*0.33, yy + s*0.45, x0 + seg*0.66, yy + s*0.45, x0 + seg, yy)
        c.drawPath(p, stroke=1, fill=0)
    c.restoreState()

def deck_icon(x, y, s):
    for i, off in enumerate([(4, -4), (2, -2), (0, 0)]):
        c.setFillColor(CARD_BG if i == 2 else PARCH2)
        c.setStrokeColor(INK_SOFT); c.setLineWidth(1)
        c.roundRect(x + off[0], y + off[1], s*0.75, s, s*0.08, stroke=1, fill=1)
    spade(x + s*0.375, y + s*0.5, s*0.42, BLACK)

def brick_icon(x, y, s):
    c.saveState()
    c.setStrokeColor(INK_SOFT); c.setLineWidth(1)
    rows = [(0, [0, 0.5]), (0.34, [-0.25, 0.25, 0.75]), (0.68, [0, 0.5])]
    bw, bh = s*0.5, s*0.30
    c.setFillColor(HexColor("#B26A4C"))
    for ry, xs in rows:
        for rx in xs:
            bx, by = x + rx*bw*2*0.5, y + ry*s
            c.rect(bx, by, bw, bh, stroke=1, fill=1)
    # up arrow
    c.setFillColor(INK)
    p = c.beginPath()
    ax = x + s*1.28
    p.moveTo(ax, y + s*0.95); p.lineTo(ax - s*0.22, y + s*0.55); p.lineTo(ax + s*0.22, y + s*0.55)
    p.close(); c.drawPath(p, stroke=0, fill=1)
    c.setLineWidth(s*0.14); c.setStrokeColor(INK); c.setLineCap(1)
    c.line(ax, y + s*0.58, ax, y + s*0.05)
    c.restoreState()

def ford_icon(x, y, s):
    waves(x, y + s*0.25, s*1.5, s*0.5)
    c.saveState()
    c.setStrokeColor(INK); c.setLineWidth(s*0.13); c.setLineCap(1)
    # swap arrows
    c.line(x + s*0.15, y + s*0.85, x + s*1.15, y + s*0.85)
    c.setFillColor(INK)
    p = c.beginPath()
    p.moveTo(x + s*1.35, y + s*0.85); p.lineTo(x + s*1.10, y + s*0.97); p.lineTo(x + s*1.10, y + s*0.73)
    p.close(); c.drawPath(p, stroke=0, fill=1)
    c.line(x + s*0.35, y + s*1.15, x + s*1.35, y + s*1.15)
    p = c.beginPath()
    p.moveTo(x + s*0.15, y + s*1.15); p.lineTo(x + s*0.40, y + s*1.27); p.lineTo(x + s*0.40, y + s*1.03)
    p.close(); c.drawPath(p, stroke=0, fill=1)
    c.restoreState()

def flush_icon(x, y, s):
    c.saveState()
    c.setStrokeColor(RIVER); c.setLineWidth(s*0.16); c.setLineCap(1)
    # swirl
    cx, cy = x + s*0.7, y + s*0.7
    for r, a0, a1 in [(s*0.62, 30, 300), (s*0.36, 90, 360)]:
        c.arc(cx - r, cy - r, cx + r, cy + r, a0, a1 - a0)
    c.setFillColor(RIVER)
    p = c.beginPath()
    ang = math.radians(300)
    tx, ty = cx + s*0.62*math.cos(ang), cy + s*0.62*math.sin(ang)
    p.moveTo(tx + s*0.14, ty + s*0.22); p.lineTo(tx - s*0.16, ty + s*0.10); p.lineTo(tx + s*0.10, ty - s*0.14)
    p.close(); c.drawPath(p, stroke=0, fill=1)
    c.restoreState()

def hammer_icon(x, y, s):
    c.saveState()
    c.translate(x + s*0.7, y + s*0.6); c.rotate(-35)
    c.setFillColor(HexColor("#8A6B3F")); c.setStrokeColor(INK_SOFT); c.setLineWidth(1)
    c.rect(-s*0.08, -s*0.75, s*0.16, s*0.95, stroke=1, fill=1)   # handle
    c.setFillColor(HexColor("#4F4A42"))
    c.roundRect(-s*0.42, s*0.16, s*0.84, s*0.34, s*0.06, stroke=1, fill=1)  # head
    c.restoreState()
    # debris
    c.setFillColor(INK_SOFT)
    for dx, dy, r in [(0.10, 0.10, 0.05), (0.28, 0.02, 0.04), (0.02, 0.26, 0.035)]:
        c.circle(x + s*dx, y + s*dy, s*r, stroke=0, fill=1)

# ---------------------------------------------------------------- page chrome
def page_frame():
    c.setFillColor(PARCH)
    c.rect(0, 0, W, H, stroke=0, fill=1)
    c.setStrokeColor(GOLD); c.setLineWidth(1.4)
    c.rect(18, 18, W-36, H-36, stroke=1, fill=0)
    c.setLineWidth(0.5)
    c.rect(23, 23, W-46, H-46, stroke=1, fill=0)

def section_title(x, y, text, col=EMBER_D):
    c.setFillColor(col)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(x, y, text.upper())
    tw = c.stringWidth(text.upper(), "Helvetica-Bold", 14)
    c.setStrokeColor(GOLD); c.setLineWidth(1)
    c.line(x + tw + 8, y + 4, W - 46, y + 4)

def body(x, y, lines, size=10.2, leading=13.6, col=INK, font="Helvetica"):
    c.setFont(font, size); c.setFillColor(col)
    for ln in lines:
        c.drawString(x, y, ln)
        y -= leading
    return y

def rich_line(x, y, parts, size=10.2):
    """parts = [(text, font, color), ...] drawn on one baseline."""
    for text, font, col in parts:
        c.setFont(font, size); c.setFillColor(col)
        c.drawString(x, y, text)
        x += c.stringWidth(text, font, size)
    return x

# ================================================================ PAGE 1
page_frame()

# Header band
c.setFillColor(INK)
c.rect(23, H-118, W-46, 95, stroke=0, fill=1)
flame(70, H-72, 30)
flame(W-70, H-72, 30)
c.setFillColor(PARCH)
c.setFont("Helvetica-Bold", 40)
c.drawCentredString(W/2, H-72, "BRIDGEBURNER")
c.setFillColor(FLAME_Y)
c.setFont("Helvetica-Oblique", 12.5)
c.drawCentredString(W/2, H-95, "A two-player card game of building & sabotage")
c.setFillColor(PARCH2)
c.setFont("Helvetica", 8.5)
c.drawCentredString(W/2, H-110, "2 players  ·  standard 52-card deck  ·  ~15 minutes per round")

y = H - 148

# --- Setup
section_title(46, y, "Setup")
y -= 20
y = body(46, y, [
    "Shuffle the deck.  Deal 7 cards to each player.  Flip 3 cards face-up in the middle:",
])
x_end = rich_line(46, y, [
    ("this shared pool is the ", "Helvetica", INK),
    ("River", "Helvetica-Bold", RIVER_D),
    (".  The rest becomes a face-down draw pile.  If the draw pile ever", "Helvetica", INK),
])
y -= 13.6
y = body(46, y, ["runs out, shuffle the discards to refill it."])
y -= 6

# Setup illustration: draw pile + river cards
il_y = y - 84
card(60, il_y, 52, "", "S", face_down=True)
c.setFillColor(INK_SOFT); c.setFont("Helvetica-Bold", 8.5)
c.drawCentredString(86, il_y - 13, "DRAW PILE")
waves(150, il_y + 6, 300, 12)
card(175, il_y + 6, 48, "8", "D")
card(245, il_y + 6, 48, "K", "C")
card(315, il_y + 6, 48, "4", "H")
c.setFillColor(RIVER_D); c.setFont("Helvetica-Bold", 8.5)
c.drawCentredString(270, il_y - 13, "THE RIVER  (always 3 face-up cards)")
# hand fan
for i, (r, s_, t) in enumerate([("2","S",-16),("6","H",-8),("9","C",0),("J","D",8),("A","S",16)]):
    card(430 + i*18, il_y + 4 + abs(2-i)*-3 + 6, 44, r, s_, tilt=t)
c.setFillColor(INK_SOFT); c.setFont("Helvetica-Bold", 8.5)
c.drawCentredString(492, il_y - 13, "YOUR HAND  (7 cards)")
y = il_y - 34

# --- Goal
section_title(46, y, "How to win")
y -= 20
x_end = rich_line(46, y, [
    ("Build a ", "Helvetica", INK),
    ("bridge", "Helvetica-Bold", EMBER_D),
    (": a face-up row of ", "Helvetica", INK),
    ("5 cards in ascending value", "Helvetica-Bold", INK),
    (" in front of you.  Suits don't", "Helvetica", INK),
])
y -= 13.6
y = body(46, y, [
    "matter and gaps are fine — each card just has to beat the one before it.  Aces are low.",
    "First finished bridge wins the round; play best of three.",
])
y -= 8

# Bridge illustration
bx, bw, gap = 130, 58, 14
b_y = y - 92
ex = [("3","C"), ("5","D"), ("6","S"), ("9","H"), ("Q","S")]
for i, (r, s_) in enumerate(ex):
    card(bx + i*(bw+gap), b_y, bw, r, s_)
# arrows between
c.setFillColor(EMBER)
for i in range(4):
    ax = bx + (i+1)*(bw+gap) - gap/2 - 2
    ay = b_y + bw*0.7
    p = c.beginPath()
    p.moveTo(ax + 5, ay); p.lineTo(ax - 3, ay + 4); p.lineTo(ax - 3, ay - 4)
    p.close(); c.drawPath(p, stroke=0, fill=1)
c.setFillColor(EMBER_D); c.setFont("Helvetica-Bold", 9)
c.drawCentredString(bx + 2.5*(bw+gap) - gap/2, b_y - 14, "A WINNING BRIDGE  —  EACH CARD HIGHER THAN THE LAST")
y = b_y - 36

# --- Mortar callout
c.setFillColor(PARCH2)
c.setStrokeColor(GOLD); c.setLineWidth(1)
c.roundRect(40, y - 74, W - 80, 66, 8, stroke=1, fill=1)
card(52, y - 66, 36, "K", "S")
tx = 104
c.setFillColor(EMBER_D); c.setFont("Helvetica-Bold", 11)
c.drawString(tx, y - 24, "FACE CARDS ARE MORTAR")
c.setFillColor(INK); c.setFont("Helvetica", 9.6)
c.drawString(tx, y - 38, "A Jack, Queen, or King at the end of your bridge is tough: Burning it costs your rival")
c.drawString(tx, y - 50, "their entire turn (2 actions) instead of 1. But nothing builds past a King — overreach")
c.drawString(tx, y - 62, "with mortar too early and you'll have to Demolish your own work to keep climbing.")

c.setFillColor(INK_SOFT); c.setFont("Helvetica-Oblique", 8.5)
c.drawCentredString(W/2, 34, "Page 1 of 2  —  turn over for actions")
c.showPage()

# ================================================================ PAGE 2
page_frame()

c.setFillColor(INK)
c.rect(23, H-88, W-46, 65, stroke=0, fill=1)
c.setFillColor(PARCH)
c.setFont("Helvetica-Bold", 24)
c.drawCentredString(W/2, H-58, "ON YOUR TURN:  SPEND 2 ACTIONS")
c.setFillColor(FLAME_Y)
c.setFont("Helvetica-Oblique", 10.5)
c.drawCentredString(W/2, H-78, "Mix and match, or repeat the same action twice — whatever the cost allows.")

rows = [
    ("DRAW", "1 ACTION", deck_icon, [
        [("Take the top card of the draw pile into your hand.", "Helvetica", INK)],
    ]),
    ("BUILD", "2 ACTIONS", brick_icon, [
        [("Play a card from your hand onto the right end of your bridge.  It must be", "Helvetica", INK)],
        [("higher", "Helvetica-Bold", INK), (" than your current rightmost card.  Slow, deliberate work — a full", "Helvetica", INK)],
        [("build takes your whole turn, so your rival always gets a chance to answer.", "Helvetica", INK)],
    ]),
    ("BURN", "1 ACTION*", flame, [
        [("Discard a hand card that matches the ", "Helvetica", INK), ("color", "Helvetica-Bold", INK), (" (red/black) of your opponent's", "Helvetica", INK)],
        [("rightmost bridge card ", "Helvetica", INK), ("and beats it", "Helvetica-Bold", INK), (".  Their card is destroyed — and washes into", "Helvetica", INK)],
        [("the River, replacing its oldest card.  ", "Helvetica", INK), ("Salvage:", "Helvetica-Bold", EMBER_D), (" the burned player immediately", "Helvetica", INK)],
        [("draws 1 card from the pile — every act of arson arms your rival.", "Helvetica", INK)],
        [("*Mortar resists the flames: burning a Jack, Queen, or King costs ", "Helvetica", INK), ("both", "Helvetica-Bold", EMBER_D), (" actions.", "Helvetica", INK)],
    ]),
    ("FORD", "1 ACTION", ford_icon, [
        [("Discard any card from your hand, take any one of the 3 River cards, then", "Helvetica", INK)],
        [("refill the River from the draw pile.  A known card beats a blind draw.", "Helvetica", INK)],
    ]),
    ("FLUSH", "1 ACTION", flush_icon, [
        [("Discard all 3 River cards and deal 3 fresh ones from the draw pile.", "Helvetica", INK)],
        [("Fish for what you need — but your rival sees the new cards too.", "Helvetica", INK)],
    ]),
    ("DEMOLISH", "1 ACTION", hammer_icon, [
        [("Remove the rightmost card of ", "Helvetica", INK), ("your own", "Helvetica-Bold", INK), (" bridge to the discard pile.", "Helvetica", INK)],
        [("Sometimes you tear down a low card to rebuild a taller ascent.", "Helvetica", INK)],
    ]),
]

ry = H - 112
icon_x = 52
for name, cost, icon, lines in rows:
    n = len(lines)
    row_h = 26 + n * 13
    # zebra card
    c.setFillColor(CARD_BG)
    c.setStrokeColor(CARD_ED); c.setLineWidth(0.8)
    c.roundRect(38, ry - row_h, W - 76, row_h - 4, 6, stroke=1, fill=1)
    icon(icon_x, ry - row_h + 12, 26 if icon is not flame else 20)
    tx = 118
    c.setFillColor(INK); c.setFont("Helvetica-Bold", 13)
    c.drawString(tx, ry - 20, name)
    nw = c.stringWidth(name, "Helvetica-Bold", 13)
    c.setFillColor(EMBER); c.setFont("Helvetica-Bold", 9)
    c.drawString(tx + nw + 10, ry - 20, cost)
    ly = ry - 34
    for parts in lines:
        rich_line(tx, ly, parts, size=9.6)
        ly -= 13
    ry -= row_h + 6

# Strategy footer
ry -= 2
c.setFillColor(INK)
c.roundRect(38, ry - 108, W - 76, 102, 8, stroke=0, fill=1)
flame(60, ry - 56, 18)
c.setFillColor(FLAME_Y); c.setFont("Helvetica-Bold", 12)
c.drawString(88, ry - 24, "ARSONIST'S ADVICE")
c.setFillColor(PARCH); c.setFont("Helvetica", 9.3)
tips = [
    "Every burn spent is a card not built — attack when it costs them more than it costs you.",
    "Early arson is charity — every burn hands your rival a fresh card. Save the torch for spans four and five.",
    "Watch the colors: ending your bridge on a card whose color you've bled from the deck is armor.",
    "The River remembers. Burned cards resurface there — don't hand your rival their card back.",
    "Mortar buys time, not immunity. A face-card cap costs your rival a full turn to burn — build while they swing.",
]
ty = ry - 42
for t in tips:
    c.drawString(88, ty, "\u2022  " + t)
    ty -= 13.5

c.setFillColor(INK_SOFT); c.setFont("Helvetica-Oblique", 8.5)
c.drawCentredString(W/2, 34, "Page 2 of 2  —  first bridge of five wins  ·  best of three rounds takes the match")

c.save()
print("done")
