# -*- coding: utf-8 -*-
"""Where a "label the drawing" task's empty boxes go - so no build sheet places one by hand (2.48.0).

WHY (IGF M01-M03, 2026-10-16): the boxes were packed to the right of their places. Five boxes in one row ran off the
right edge, and three build sheets (M01 m01, M02 m01, M03 q06) placed every box by hand.

HOW WIDE is task_pages.label_px (2.46.0): every box of a question is as wide as its longest label needs. This file only
PLACES them, in the two bands task_pages.py leaves above and below the drawing (no box covers what is drawn):
  ROWS   a place in the upper half of the drawing gets a box in the band above, the rest below; a band that cannot hold
         its boxes hands the ones nearest the middle to the other band
  ORDER  in each band the boxes keep the order across of the places they point at, each as close above (or below) its
         place as the others allow (least squares, PAV), 1 % from the edges and between boxes, the top band clear of
         the drawing's full-screen button - so no two leader lines cross and none runs under a box
What still does not fit (more boxes than two bands hold) is returned, for task_pages.py to report - never cut off.
"""
from __future__ import annotations

GAP = 1.0               # % between boxes and from the drawing's edges


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


def spread(row, w, right=100.0):
    """lefts for boxes of width w (%) in one band, in the order of their places across, as near each place as can be;
    `right` is where the band ends (100, or less where the full-screen button sits)"""
    n = len(row)
    step = w + GAP
    want = [p["box"][0] + p["box"][2] / 2.0 - w / 2.0 for p in row]
    # y_i = left_i - i * step must be nondecreasing; the first box from GAP and the last to right - GAP make every y lie
    # in one interval - clamping the free answer to it keeps it ordered and nearest
    lo, hi = GAP, right - GAP - w - (n - 1) * step
    ys = pav([want[i] - i * step for i in range(n)], [lo] * n, [max(lo, hi)] * n)
    return [round(ys[i] + i * step, 2) for i in range(n)]


def capacity(w, right=100.0):
    return max(1, int((right - 2 * GAP + GAP) // (w + GAP)))


def label_boxes(places, vb, ppu, w, band_px=64.0, box_px_h=56.0, corner=0.0):
    """places: [{"t": words, "box": [left, top, width, height] % of the drawing (the place)}] - sets each "at" to
    [left, top, width] % of the drawing for its empty box, w % wide (task_pages.label_px). vb is the drawing's view box
    with its bands (task_pages.band_vb), ppu its px per unit at 1280 x 800, corner the % the top band keeps free at its
    right end. Returns True when every box fits; False when a band holds more than it can (they are squeezed, and
    task_pages.py says so)."""
    if not places:
        return True
    hpx = vb[3] * ppu
    rights = {"top": 100.0 - corner, "bot": 100.0}
    mid = lambda p: p["box"][1] + p["box"][3] / 2.0
    top = [p for p in places if mid(p) < 50]
    bot = [p for p in places if p not in top]
    cap = {"top": capacity(w, rights["top"]), "bot": capacity(w, rights["bot"])}
    # a band that cannot hold its boxes hands those nearest the middle to the other one
    while len(top) > cap["top"] and len(bot) < cap["bot"]:
        q = max(top, key=mid)
        top.remove(q)
        bot.append(q)
    while len(bot) > cap["bot"] and len(top) < cap["top"]:
        q = min(bot, key=mid)
        bot.remove(q)
        top.append(q)
    fits = len(top) <= cap["top"] and len(bot) <= cap["bot"]
    gap = (band_px - box_px_h) / 2.0
    for name, row, y in (("top", top, round(100.0 * gap / hpx, 2)), ("bot", bot, round(100.0 * (hpx - gap - box_px_h) / hpx, 2))):
        row.sort(key=lambda p: p["box"][0] + p["box"][2] / 2.0)
        if not row:
            continue
        ww = w if len(row) <= cap[name] else max(1.0, (rights[name] - GAP) / len(row) - GAP)
        for p, left in zip(row, spread(row, ww, rights[name])):
            p["at"] = [left, y, round(ww, 2)]
            if ww != w:
                p["crowded"] = True
    return fits
