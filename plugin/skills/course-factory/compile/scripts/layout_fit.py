#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""layout_fit - the picture's box on a slide with words beside a picture (layout-templates.json "boxes").

A picture asks for room by what it shows at once: the names on it (a kit drawing's labelled parts, a 3D scene's labels,
an SVG's words, a photograph's spots), a 3D model, a shape much wider than high. The slide's words ask for room by how
many they are. choose() settles both:

  box     the smallest box that shows the picture readably and holds the words beside it
  parts   the picture in the box it needs, the words beside it in parts (content-in-parts)
  stage   the picture needs the whole slide and the words are few: the picture alone on the stage (figure-stage)
  swap    the picture needs more than any box beside these words - growing it would cut the words into too many parts,
          or it needs the whole slide and the words are too many for that: the factory makes it another kind of picture

    python layout_fit.py "<figure html or spec file>" --words 70 [--3d] [--box picture-wide]
    python test_layout_fit.py
"""
from __future__ import annotations

import argparse
import io
import json
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILLS = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
LT = json.load(io.open(os.path.join(SKILLS, "course-module-ui", "knowledge", "layout-templates.json"), encoding="utf-8"))
BOX = LT["boxes"]
ORDER = BOX["order"]
STAGE_WORDS = LT["variety"]["stage_max_words"]
PART_WORDS = LT["parts"]["part_words"]
JSON_DATA = re.compile(r'<script type="application/json"[^>]*>(.*?)</script>', re.S)
SVG_TEXT = re.compile(r"<text\b[^>]*>(.*?)</text>", re.S | re.I)
VIEWBOX = re.compile(r'viewBox="\s*[-\d.]+[ ,]+[-\d.]+[ ,]+([\d.]+)[ ,]+([\d.]+)"')


def specs(fig):
    """the JSON specs in a figure's markup (a kit drawing, a 3D scene) - or the figure itself when it is a spec"""
    out = []
    for m in JSON_DATA.finditer(fig or ""):
        try:
            out.append(json.loads(m.group(1).replace("<\\/", "</")))
        except ValueError:
            continue
    if not out and (fig or "").lstrip().startswith("{"):
        try:
            out.append(json.loads(fig))
        except ValueError:
            pass
    return [d for d in out if isinstance(d, dict)]


def names_shown(fig):
    """how many names the picture shows at once: a spec's labelled parts and its spots, else an SVG's words"""
    n = 0
    for d in specs(fig):
        parts = d.get("parts") or []
        parts = parts.values() if isinstance(parts, dict) else parts
        for p in parts:
            if isinstance(p, dict):
                n += 1 if str(p.get("label") or p.get("tag") or "").strip() else 0
                n += sum(1 for x in (p.get("markers") or []) + (p.get("limits") or []) if isinstance(x, dict) and x.get("label"))
        labels = d.get("labels")                        # a 3D scene's names: [{"part", "text"}]
        n += len([x for x in labels if isinstance(x, dict)]) if isinstance(labels, list) else 0
        n += len(d.get("spots") or [])
    if n:
        return n
    return len({re.sub(r"<[^>]+>|\s+", " ", t).strip() for t in SVG_TEXT.findall(fig or "")} - {""})


def aspect(fig):
    """width / height of the picture's own shape (a spec's "size", an SVG's viewBox), or None"""
    for d in specs(fig):
        try:
            w, h = [float(x) for x in d.get("size")][:2]
            if w > 0 and h > 0:
                return w / h
        except (TypeError, ValueError):
            continue
    m = VIEWBOX.search(fig or "")
    return float(m.group(1)) / float(m.group(2)) if m and float(m.group(2)) > 0 else None


def demand(fig, three_d=False, spots=0):
    """what the picture asks for: {"names", "share" (of the slide's width), "wide", "three_d"}"""
    n = names_shown(fig) + (spots or 0)
    share = max(sh for lo, sh in BOX["need"] if n >= lo)
    if three_d:
        share = max(share, BOX["three_d"])
    a = aspect(fig)
    return {"names": n, "share": share, "wide": bool(a and a >= BOX["wide_aspect"]), "three_d": bool(three_d)}


def picture_share(box):
    return round(1 - BOX[box]["text"], 3)


def parts_needed(words, box):
    """1 when the words fit beside the box, else the parts of about a part's words in that column"""
    if words <= BOX[box]["words"]:
        return 1
    per = PART_WORDS * BOX[box]["words"] / float(BOX[BOX["default"]]["words"])
    return int(math.ceil(words / per))


def choose(words, need, asked=None):
    """{"action": box | parts | stage | swap, "box", "text" (the words' share), "parts", "why"} for a slide of `words`
    words beside a picture that asks for `need` (demand()). asked: the build sheet's "box", which wins"""
    def out(action, box, why):
        return {"action": action, "box": box, "text": BOX[box]["text"] if box else None,
                "parts": parts_needed(words, box) if box else 1, "why": why}
    if asked in ORDER:
        return out("box" if parts_needed(words, asked) == 1 else "parts", asked, "the build sheet asks for it")
    holds = [b for b in ORDER if picture_share(b) >= need["share"] - 1e-9]
    if need["wide"] and words <= STAGE_WORDS:
        return out("stage", None, "a picture %s wider than high, and %d words: across the slide" % (BOX["wide_aspect"], words))
    if not holds:
        if words <= STAGE_WORDS:
            return out("stage", None, "%d names on the picture need the whole slide; %d words go under it"
                       % (need["names"], words))
        return out("swap", ORDER[-1], "%d names on the picture need the whole slide, and %d words are too many to go with it "
                   "(%d at most)" % (need["names"], words, STAGE_WORDS))
    d = BOX["default"]
    bigger = [b for b in holds if picture_share(b) >= picture_share(d)]             # the default, then larger pictures
    smaller = [b for b in reversed(holds) if picture_share(b) < picture_share(d)]   # a wider words' column
    for b in bigger[:1] + smaller + bigger[1:]:
        if parts_needed(words, b) == 1:
            return out("box", b, "%d names%s, %d words" % (need["names"], ", a 3D model" if need["three_d"] else "", words))
    b = bigger[0]
    base, grown = parts_needed(words, d), parts_needed(words, b)
    if grown - base <= BOX["extra_parts"]:
        return out("parts", b, "%d words in %d parts beside the %s box" % (words, grown, b))
    return out("swap", b, "the picture needs the %s box (%d %% of the width) for its %d names, and beside it %d words go from "
               "%d to %d parts" % (b, round(100 * picture_share(b)), need["names"], words, base, grown))


SWAP_ADVICE = ("make it another kind of picture: in steps (a few names a step), a 3D model whose names show on tap, the picture "
               "on a slide of its own (\"composition\": \"stage\") with the words on the slide before, or fewer names on this one")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("figure", help="a figure's markup file, or a kit / kit3d spec")
    ap.add_argument("--words", type=int, required=True)
    ap.add_argument("--3d", dest="three_d", action="store_true")
    ap.add_argument("--box", choices=ORDER)
    o = ap.parse_args()
    fig = io.open(o.figure, encoding="utf-8").read()
    need = demand(fig, o.three_d)
    got = choose(o.words, need, o.box)
    print("picture: %d names, needs %d %% of the width%s%s" % (need["names"], round(100 * need["share"]),
                                                          ", a 3D model" if need["three_d"] else "", ", wide" if need["wide"] else ""))
    print("%s%s - %s" % (got["action"], " (%s, words %d %%, %d part(s))" % (got["box"], round(100 * got["text"]), got["parts"])
                          if got["box"] else "", got["why"]))
    if got["action"] == "swap":
        print(SWAP_ADVICE)
    return 0


if __name__ == "__main__":
    sys.exit(main())
