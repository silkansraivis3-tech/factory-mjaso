# -*- coding: utf-8 -*-
"""test_layout_fit - the picture's box beside the words: grown when the picture needs it, the words in parts when they do
not fit beside it, the picture alone on the stage, or another kind of picture when no box can show it.

    python test_layout_fit.py
"""
from __future__ import annotations

import json
import sys

import layout_fit as lf

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
FAILS = []


def check(name, ok, detail=""):
    print("  %s  %s%s" % ("ok  " if ok else "FAIL", name, "" if ok else "  -> %s" % (detail,)))
    if not ok:
        FAILS.append(name)


def kit(n, size=(800, 500)):
    spec = {"size": list(size), "label": "x", "parts": [{"id": "p%d" % i, "type": "valve", "label": "Part %d" % i} for i in range(n)]
            + [{"id": "frame", "type": "line"}]}
    return '<div class="fill fig"><script type="application/json" id="k">%s</script></div>' % json.dumps(spec)


def svg(words, vb="0 0 600 400"):
    return '<svg viewBox="%s">%s</svg>' % (vb, "".join("<text>%s</text>" % w for w in words))


def main():
    check("a kit drawing's names are its labelled parts (a frame with no label is not one)", lf.names_shown(kit(9)) == 9,
          lf.names_shown(kit(9)))
    check("an SVG's names are its words, each once", lf.names_shown(svg(["Valve", "Pump", "Valve", " "])) == 2)
    scene = {"label": "x", "parts": [{"id": "t", "type": "tank_c"}], "labels": [{"part": "t", "text": "Tank"}, {"part": "t", "text": "Dome"}]}
    check("a 3D scene's names are its labels", lf.names_shown(json.dumps(scene)) == 2, lf.names_shown(json.dumps(scene)))
    gauge = {"size": [200, 600], "parts": [{"id": "s", "type": "scale", "markers": [{"label": "LEL"}, {"label": "UEL"}],
                                             "limits": [{"at": 1, "label": "alarm"}]}]}
    check("a scale's markers and limits are names", lf.names_shown(json.dumps(gauge)) == 3, lf.names_shown(json.dumps(gauge)))
    check("a spec's shape is its size", abs(lf.aspect(kit(3, (900, 300))) - 3.0) < 1e-6)

    few, mid, busy, crowded, packed = (lf.demand(kit(n)) for n in (4, 8, 12, 18, 25))
    check("a picture of a few names keeps the even box beside 60 words", lf.choose(60, few) ==
          dict(lf.choose(60, few), action="box", box="even"), lf.choose(60, few))
    got = lf.choose(90, few)
    check("90 words beside a simple picture: the words' column grows, not the parts", (got["action"], got["box"]) == ("box", "text-wide"), got)
    got = lf.choose(60, busy)
    check("12 names: the picture grows to picture-wide, 60 words still beside it", (got["action"], got["box"]) == ("box", "picture-wide"), got)
    got = lf.choose(80, busy)
    check("12 names and 80 words: picture-wide, the words in 2 parts (one more than beside the even box)",
          (got["action"], got["box"], got["parts"]) == ("parts", "picture-wide", 2), got)
    got = lf.choose(200, crowded)
    check("18 names and 200 words: growing the picture would take the words from 3 parts to 5 - another kind of picture",
          got["action"] == "swap" and "picture-large" in got["why"], got)
    got = lf.choose(40, packed)
    check("25 names and 40 words: the picture alone on the stage", got["action"] == "stage" and got["box"] is None, got)
    got = lf.choose(80, packed)
    check("25 names and 80 words: no box shows it - another kind of picture", got["action"] == "swap", got)
    got = lf.choose(50, lf.demand(kit(2), three_d=True))
    check("a 3D model gets picture-wide at least (2.69.0)", got["box"] == "picture-wide" and abs(got["text"] - 0.42) < 1e-9, got)
    got = lf.choose(30, lf.demand(kit(3, (1200, 400))))
    check("a picture three times wider than high, 30 words: across the slide", got["action"] == "stage", got)
    got = lf.choose(30, busy, "even")
    check("the build sheet's box wins", got["box"] == "even" and got["action"] == "box", got)
    for b in lf.ORDER:
        check("the %s box holds fewer words than a box with a narrower picture" % b,
              all(lf.BOX[b]["words"] <= lf.BOX[c]["words"] for c in lf.ORDER[:lf.ORDER.index(b)]))
    check("every need step is a share a box (or the whole slide) can give",
          all(any(lf.picture_share(b) >= sh for b in lf.ORDER) or sh == 1.0 for _, sh in lf.BOX["need"]))
    print("\n%s" % ("ALL PASS" if not FAILS else "%d FAILED" % len(FAILS)))
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
