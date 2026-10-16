# -*- coding: utf-8 -*-
"""Where a "label the drawing" task's empty boxes go, and how wide they are - so no build sheet places one by hand.

WHY (IGF M01-M03, 2026-10-16): the boxes were a fixed 17 % wide, packed to the right of the places. "Tank connection
space" was cut off in its box, five boxes in one row ran off the right edge, and three build sheets (M01 m01, M02 m01,
M03 q06) placed every box by hand ("labels": {"...": {"box": [left, top, width]}}).

WHAT IT DOES - in the two bands task_pages.py leaves above and below the drawing (no box covers what is drawn):
  WIDTH  every box of a question is as wide as its longest label needs on at most two lines (the chip's 16 px words,
         its padding, the tick it gets when checked) - one width for all, so the size never tells which box is which
  ROWS   a place in the upper half of the drawing gets a box in the band above, the rest below; a band that cannot hold
         its boxes hands the ones nearest the middle to the other band
  ORDER  in each band the boxes keep the order across of the places they point at, each as close above (or below) its
         place as the others allow (least squares, PAV), 1 % from the edges and between boxes - so no two leader lines
         cross and none runs under a box
A label that still does not fit (more boxes than two bands can hold) is reported in places[i]["crowded"].
"""
from __future__ import annotations

import re

FONT_PX = 16.0          # .lbox .chip font-size (gb_answer.css)
PAD_PX = 2 * 8 + 4      # its padding both sides, the dashed border
TICK_PX = 26            # the ✓ or ↻ a checked chip shows after its words (.chip.right::after)
MIN_PX = 120.0
GAP = 1.0               # % between boxes and from the drawing's edges

# Raleway at 16 px, by character class (measured in Chrome on the deck's font; a little generous on purpose)
_NARROW = set("iljtf.,;:'!|()[]-/ ")
_WIDE = set("mwMW@")


def char_px(c):
    if c in _NARROW:
        return 5.0
    if c in _WIDE:
        return 13.5
    if c.isupper():
        return 11.0
    if c.isdigit():
        return 9.4
    return 8.8


def words_px(s):
    return sum(char_px(c) for c in s) * 1.06


def two_lines_px(text):
    """the width the words need on at most two lines, broken at the best space"""
    t = re.sub(r"\s+", " ", (text or "").strip())
    best = words_px(t)
    for m in re.finditer(" ", t):
        a, b = t[:m.start()], t[m.end():]
        best = min(best, max(words_px(a), words_px(b)))
    return best


def box_px(text):
    return max(MIN_PX, two_lines_px(text) + PAD_PX + TICK_PX)


def pav(target, lo, hi):
    """the nondecreasing sequence nearest the targets (least squares), each kept within [lo, hi] (pool adjacent violators)"""
    blocks = []                                # [sum, count]
    for t in target:
        blocks.append([t, 1])
        while len(blocks) > 1 and blocks[-2][0] / blocks[-2][1] > blocks[-1][0] / blocks[-1][1]:
            s, n = blocks.pop()
            blocks[-1][0] += s
            blocks[-1][1] += n
    out = []
    for s, n in blocks:
        out += [s / n] * n
    out = [min(max(v, a), b) for v, a, b in zip(out, lo, hi)]
    for i in range(1, len(out)):              # clamping can break the order: restore it, then the upper bounds
        out[i] = max(out[i], out[i - 1])
    for i in range(len(out) - 2, -1, -1):
        out[i] = min(out[i], out[i + 1])
    return out


def spread(row, w):
    """lefts for boxes of width w (%) in one band, in the order of their places across, as near each place as can be"""
    n = len(row)
    step = w + GAP
    want = [p["box"][0] + p["box"][2] / 2.0 - w / 2.0 for p in row]
    # y_i = left_i - i * step must be nondecreasing; the first box from GAP and the last to 100 - GAP make every y lie in
    # one interval [GAP, 100 - GAP - w - (n - 1) step] - clamping the free answer to it keeps it ordered and nearest
    lo, hi = GAP, 100.0 - GAP - w - (n - 1) * step
    ys = pav([want[i] - i * step for i in range(n)], [lo] * n, [max(lo, hi)] * n)
    return [round(ys[i] + i * step, 2) for i in range(n)]


def capacity(w):
    return max(1, int((100.0 - GAP) // (w + GAP)))


def label_boxes(places, vb, ppu, band_px=64.0, box_px_h=56.0, width_px=1240.0):
    """places: [{"t": words, "box": [left, top, width, height] % of the drawing (the place)}] - sets each "at" to
    [left, top, width] % of the drawing for its empty box. vb is the drawing's view box with its bands (task_pages
    band_vb); ppu its px per unit at 1280 x 800."""
    if not places:
        return places
    wpx, hpx = vb[2] * ppu, vb[3] * ppu
    w = min(48.0, max(box_px(p["t"]) for p in places) * 100.0 / wpx)
    cap = capacity(w)
    mid = lambda p: p["box"][1] + p["box"][3] / 2.0
    top = [p for p in places if mid(p) < 50]
    bot = [p for p in places if p not in top]
    # a band that cannot hold its boxes hands those nearest the middle to the other one
    while len(top) > cap and len(bot) < cap:
        q = max(top, key=mid)
        top.remove(q)
        bot.append(q)
    while len(bot) > cap and len(top) < cap:
        q = min(bot, key=mid)
        bot.remove(q)
        top.append(q)
    gap = (band_px - box_px_h) / 2.0
    for row, y in ((top, round(100.0 * gap / hpx, 2)), (bot, round(100.0 * (hpx - gap - box_px_h) / hpx, 2))):
        row.sort(key=lambda p: p["box"][0] + p["box"][2] / 2.0)
        if not row:
            continue
        ww = w
        if len(row) > cap:                     # more than a band holds even after handing over: each box its own width
            ww = 100.0 / len(row) - GAP - 0.01
            for p in row:
                p["crowded"] = True
        for p, left in zip(row, spread(row, ww)):
            p["at"] = [left, y, round(ww, 2)]
    return places
