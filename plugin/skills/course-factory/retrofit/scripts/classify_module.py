#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""How much delivery redesign does this existing module need? A, B or C.

    classify_module.py <module.html | course_dir> [--json]

WHY THIS EXISTS
The colleague pilot asked for an existing module to be brought up to GAS BASIC
quality. What came back was a technically correct retrofit that still felt
weaker than GAS BASIC, because every individual decision to keep the existing
implementation was defensible and the sum of them was a module that passed
every check and did not look like the product.

So the decision is taken up front, from the delivery, and it is taken here
rather than by feel.

THE RULE THAT MATTERS
Classify on DELIVERY QUALITY, never on whether the HTML works. Valid markup,
resolving links and green checks are not signals. A module can be all three and
be educationally and visually weak; that module is a B or a C.

    A  preserve mostly as-is       already on the system and composed
    B  moderate delivery redesign  system present, delivery thin
    C  substantial redesign        the implementation is not evidence of anything

Signals and thresholds live in ../knowledge/classify.json and this script
implements exactly that file. Change the file, not the numbers here.

Exit code is 0 whichever level comes out - this reports, it does not gate.
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = json.loads((HERE.parent / "knowledge" / "classify.json").read_text(encoding="utf-8"))

SLIDE = re.compile(r'<section[^>]*\bclass=["\'][^"\']*\bslide\b[^"\']*["\'][^>]*>', re.I)
SLIDE_FULL = re.compile(
    r'<section[^>]*\bclass=["\'][^"\']*\bslide\b[^"\']*["\'][^>]*>(.*?)</section>', re.I | re.S)
BODY_CLS = re.compile(r'<div[^>]*\bclass=["\']slide-body([^"\']*)["\']', re.I)
LINK = re.compile(r"<link[^>]*\bhref=[\"']([^\"']+)[\"']", re.I)
ANCHOR = re.compile(r"<a\b[^>]*\bhref=", re.I)
TAG = re.compile(r"<[^>]+>")

NAMED = ["opener", "two-col", "stage", "activity", "checkbody", "sum", "trio", "photo"]
FIGURE = re.compile(r"<svg\b|<img\b|<canvas\b|<video\b|data-figure|data-motion", re.I)


def read(p):
    return Path(p).read_text(encoding="utf-8", errors="replace")


def find_module(target):
    p = Path(target)
    if p.is_file():
        return p
    for pat in ("module.html", "*/module.html", "presentation/index.html", "*/presentation/index.html"):
        hits = sorted(p.glob(pat))
        if hits:
            return hits[0]
    hits = sorted(p.rglob("module.html"))
    return hits[0] if hits else None


# The shell is a SET OF LANDMARKS, not a set of filenames.
#
# GAS BASIC Module_01 loads presentation.css and declares its tokens inside it -
# gb_shell.css and gb_tokens.css were extracted FROM that file. Scoring on the
# filename classified the reference product as "needs moderate redesign", which
# would have sent someone to rebuild the thing the rest of the system copies.
SHELL_LANDMARKS = [
    ("full-screen stage", r'id=["\']stage["\']|class=["\'][^"\']*\bstage\b'),
    ("one-page slides", r'class=["\'][^"\']*\bslide\b'),
    ("forward control", r'id=["\']btnNext["\']|class=["\'][^"\']*deck-next|data-audit-next'),
    ("header band", r'class=["\'][^"\']*slide-kind'),
    ("footer strip", r"data-foot="),
    ("branded landing", r'id=["\']landing["\']|id=["\']startBtn["\']'),
    ("overview grid", r'id=["\']overview["\']|class=["\'][^"\']*ov-grid'),
    ("instructor cue", r'id=["\']cue["\']|data-cue='),
]


def sig_canonical_shell(html, sheets):
    hits = [n for n, pat in SHELL_LANDMARKS if re.search(pat, html, re.I)]
    score = len(hits) / float(len(SHELL_LANDMARKS))
    # using the extracted files is a bonus, never the test
    names = " ".join(sheets).lower()
    if "gb_shell" in names:
        score = min(1.0, score + 0.08)
    if "gb_compose" in names:
        score = min(1.0, score + 0.07)
    return round(score, 3), {"landmarks": hits,
                             "missing": [n for n, _ in SHELL_LANDMARKS if n not in hits]}


def sig_composition(bodies):
    """Did the author DECLARE a composition, and how many different ones?

    Any modifier class on `.slide-body` counts. A fixed vocabulary list was
    tried and it marked the golden deck down for using its own names -
    `exp-stage`, `sil-row`, `handover`, `block-open` - which are the names our
    vocabulary was extracted from. What is being measured is whether the author
    chose a composition per screen, not whether they chose ours."""
    if not bodies:
        return 0.0, {"named": 0, "distinct": 0, "screens": 0}
    named, kinds = 0, set()
    for cls in bodies:
        toks = [t for t in cls.split() if t and t != "slide-body"]
        if toks:
            named += 1
            kinds.add(toks[0])
    share = named / len(bodies)
    # Uniformity is the defect this signal exists for: a module where every
    # screen is the same shape scores badly even when each screen is tidy.
    variety = min(1.0, len(kinds) / 4.0)
    return round(0.6 * share + 0.4 * variety, 3), {
        "named": named, "distinct": len(kinds), "screens": len(bodies),
        "compositions": sorted(kinds)[:10]}


def sig_teaching_visuals(sections):
    substantial = [s for s in sections if len(TAG.sub(" ", s).split()) >= 25]
    if not substantial:
        substantial = sections
    if not substantial:
        return 0.0, {"with_visual": 0, "substantial": 0}
    withvis = sum(1 for s in substantial if FIGURE.search(s))
    return round(withvis / len(substantial), 3), {
        "with_visual": withvis, "substantial": len(substantial)}


def sig_activity(html, sections):
    launches = [s for s in sections if re.search(r'data-activity=|class=["\'][^"\']*\bact\b', s, re.I)]
    if not launches:
        return 1.0, {"launches": 0, "note": "module announces no activities"}
    good = 0
    for s in launches:
        whole = bool(re.search(r"act-code", s, re.I)) and bool(re.search(r"act-title|act-inst", s, re.I))
        carded = bool(re.search(r'class=["\'][^"\']*\bact\b["\']', s))
        if whole and not carded:
            good += 1
    return round(good / len(launches), 3), {"launches": len(launches), "canonical": good}


def sig_tablet(html, sections):
    have = 0.0
    if re.search(r'id=["\']btnNext["\']', html) and re.search(r'id=["\']btnPrev["\']', html):
        have += 0.4
    if re.search(r'class=["\'][^"\']*gbt-topback', html) or re.search(r'id=["\']gb-home["\']', html):
        have += 0.2
    inside = sum(len(ANCHOR.findall(s)) for s in sections)
    if inside == 0:
        have += 0.3
    if re.search(r"min-height:\s*(4[4-9]|[5-9]\d)px", html) or "gb_shell" in html:
        have += 0.1
    return min(1.0, have), {"links_inside_slides": inside}


# The canonical token NAMES, from course-module-ui. A module that declares these
# scores here wherever it declares them - in gb_tokens.css, in its own
# presentation.css, or in a <style> block. What is measured is whether the deck
# paints from a named set, not which file the set lives in.
CANON_TOKENS = ["--navy", "--deep", "--blue", "--amber", "--white", "--ink", "--grey",
                "--line-l", "--line-d", "--txt-d", "--dim-l", "--dim-d",
                "--good", "--warn", "--r-m", "--font"]


def sig_tokens(html, sheets, base):
    css = ""
    for h in sheets:
        if "://" in h:
            continue
        f = (base / h.split("?")[0]).resolve()
        if f.exists():
            css += f.read_text(encoding="utf-8", errors="replace")
    css += "".join(re.findall(r"<style[^>]*>(.*?)</style>", html, re.S | re.I))
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    if not css.strip():
        return 0.0, {"tokens": "no stylesheet found"}

    declared = set(re.findall(r"(--[a-z][\w-]*)\s*:", css))
    present = [t for t in CANON_TOKENS if t in declared]
    coverage = len(present) / float(len(CANON_TOKENS))

    body = re.sub(r":root\s*\{.*?\}", "", css, flags=re.S)
    raw = len(re.findall(r"(?:color|background|border[a-z-]*)\s*:[^;{}]*#[0-9a-fA-F]{3,8}", body))
    total = len(re.findall(r"(?:color|background|border[a-z-]*)\s*:", body)) or 1
    cleanliness = max(0.0, 1.0 - (raw / total) * 2.5)

    return round(0.65 * coverage + 0.35 * cleanliness, 3), {
        "canonical_tokens_declared": "%d/%d" % (len(present), len(CANON_TOKENS)),
        "raw_chrome_colours_outside_root": raw}


def classify(path):
    html = read(path)
    base = Path(path).parent
    sheets = [h for h in LINK.findall(html) if h.lower().endswith(".css") or "css" in h.lower()]
    sections = SLIDE_FULL.findall(html)
    bodies = BODY_CLS.findall(html)

    s = {}
    d = {}
    s["canonical_shell"], d["shell"] = sig_canonical_shell(html, sheets)
    s["composition_vocabulary"], d["composition"] = sig_composition(bodies)
    s["teaching_visuals"], d["visuals"] = sig_teaching_visuals(sections)
    s["activity_screens"], d["activity"] = sig_activity(html, sections)
    s["tablet_behaviour"], d["tablet"] = sig_tablet(html, sections)
    s["token_adherence"], d["tokens"] = sig_tokens(html, sheets, base)

    # the spec carries prose keys beside the signals; skip them
    w = {k: v["weight"] for k, v in SPEC["signals"].items()
         if not k.startswith("_")}
    score = sum(s[k] * w[k] for k in w)

    level = "A" if score >= 0.80 else ("B" if score >= 0.45 else "C")
    applied = []

    # "no shell" is now a landmark count, not a filename check: under a quarter
    # of the shell's structural landmarks means there is nothing to preserve at
    # the delivery layer, whatever the stylesheet is called.
    if s["canonical_shell"] < 0.25:
        level = "C"
        applied.append("almost none of the shell's structural landmarks are present (%s) - "
                       "there is nothing to preserve at the delivery layer"
                       % ", ".join(d["shell"]["landmarks"]) or "none")
    if d["composition"]["named"] == 0 and s["teaching_visuals"] < 0.25 and level == "A":
        level = "B"
        applied.append("every screen is default flow and under a quarter carry a visual - "
                       "a uniform text module is exactly what this law exists for")
    if d["tablet"]["links_inside_slides"] > 0 and level == "A":
        level = "B"
        applied.append("links inside slides - the one-page architecture is broken, which is a "
                       "delivery rebuild however good the rest looks")

    return {
        "module": str(path),
        "screens": len(sections),
        "signals": s,
        "detail": d,
        "score": round(score, 3),
        "level": level,
        "level_name": SPEC["levels"][level]["name"],
        "overrides_applied": applied,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("target", help="a module.html, or a folder containing one")
    ap.add_argument("--json", action="store_true", help="machine-readable")
    a = ap.parse_args()

    p = find_module(a.target)
    if not p:
        print("No module.html under %s" % a.target)
        return 1

    r = classify(p)
    if a.json:
        print(json.dumps(r, ensure_ascii=False, indent=1))
        return 0

    print("=" * 72)
    print("classify_module - how much delivery redesign does this need?")
    print("=" * 72)
    print("\n%s\n%d screens\n" % (r["module"], r["screens"]))
    for k, v in sorted(r["signals"].items(),
                       key=lambda x: -SPEC["signals"][x[0]]["weight"]):
        bar = "#" * int(round(v * 24))
        print("  %-24s %5.2f  %-24s (w %.2f)" % (k, v, bar, SPEC["signals"][k]["weight"]))
    print("\n  %-24s %5.2f" % ("weighted", r["score"]))
    print("\n  LEVEL %s - %s" % (r["level"], r["level_name"]))
    for o in r["overrides_applied"]:
        print("        override: %s" % o)
    print("\n%s" % SPEC["levels"][r["level"]]["means"])
    print("\nReminder: this is a DELIVERY judgement. Valid markup, resolving links and green")
    print("checks are not signals here and never raise the level.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
