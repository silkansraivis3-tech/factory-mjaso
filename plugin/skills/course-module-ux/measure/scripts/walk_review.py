#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""walk_review - "walk it like a trainee": the deck's stops looked at together, by an AI reviewer, before a module is done.

    python walk_review.py prepare <course> --module N [--slides s03,s07]
    python walk_review.py sign    <course> --module N --review reviewer.json
    python walk_review.py verify  <course> --module N

WHY (operator Aleksis Vejs, 2026-11-09, after the Project Management review): the checks measure fit and overflow; they never
look at the slides the way a trainee does - a drawing that never moves, an empty chart, a picture that says the opposite of
the lit line all passed. fit_gate.py walks the deck (Start, every Next) and, at 1280x800 only, saves each stop as a ~480 px
picture with walk.json (the lit line's text, the room's question / its answer, the figure's signature) into
working_claude/_build/walk/MNN/. This script turns them into something a reviewer can judge several slides at once:

  prepare  one CONTACT SHEET per slide (all its stops in a numbered grid) -> walk/MNN/sheets/sNN.png, and
           walk/MNN/review_brief.md: the sheets in batches of 3-4 slides, each slide's stop texts and its figure's why /
           why_text, and the RUBRIC. Needs Pillow (python -m pip install pillow).
  sign     the reviewer's answer {"reviewed_by": "...", "slides": {"s03": {"ok": true, "fails": []}}} ->
           working_claude/_build/MNN_walk_review.json {deck_sha256, reviewed_by, date, slides}. With --slides on prepare a fix
           reviews only its touched slides: sign keeps the earlier result of every slide the reviewer did not return.
  verify   exit 0 only when the review exists, was made for THIS deck (hash of the deck ignoring build timestamps and comments),
           covers every walked slide, and no fail is open. Exit 1 otherwise (missing / stale / failing / incomplete).

The reviewer is an AI agent run by the lead session - the factory cannot call one. compile/GUIDE.md and fix/GUIDE.md say how:
one Sonnet subagent per batch of 3-4 contact sheets (several images in one look), returning the reviewer JSON.
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import re
import sys
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
FACTORY_SCRIPTS = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(HERE))), "course-factory", "scripts")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BATCH = 4
RUBRIC = [
    "Something visibly changes on each Next (the lit line, the figure, the question or its answer) - a stop that looks like the one before it is a fail.",
    "The picture shows what the lit line says (a bar rises when the line says it rises; the highlighted part is the part named).",
    "Nothing is empty, hidden, cut, duplicated or contradictory - an empty chart or axis, a label off the edge, the same thing drawn twice, a figure that says one thing while the words say another.",
    "A trainee would know what to do / what the slide teaches - the slide has one point and it is readable from the sheet.",
    "The drawing has a reason and serves it - its why / why_text (below) is what the trainee sees change or see; a drawing that is decoration, or a 3D model of a flat idea, fails.",
    "The answer / reveal is visible when it should be and does not cover the figure.",
]


def mid(module):
    return "FINAL" if str(module).lower() == "final" else "M%02d" % int(module)


def _work(course):
    return os.path.abspath(course)


def build_dir(course):
    p = os.path.join(_work(course), "working_claude", "_build")
    if os.path.isdir(p):
        return p
    for old in (os.path.join(_work(course), "_build"), os.path.join(_work(course), "_factory", "_build")):
        if os.path.isdir(old):
            return old
    return p


def walk_dir(course, module):
    return os.path.join(build_dir(course), "walk", mid(module))


def review_file(course, module):
    return os.path.join(build_dir(course), "%s_walk_review.json" % mid(module))


def module_dir(course, module):
    """modules\\module01, else modules\\M01_<title>, else modules\\m1 - the folder fix.py also finds"""
    n = int(module) if str(module).isdigit() else None
    mods = os.path.join(_work(course), "modules")
    if str(module).lower() == "final":       # 2.116.1 (PM): the final assessment is the last module's folder (L34)
        found = [d for pat in ("module[0-9][0-9]", "M[0-9][0-9]_*") for d in glob.glob(os.path.join(mods, pat)) if os.path.isdir(d)]
        nums = [(int(re.search(r"(\d+)", os.path.basename(d)).group(1)), d) for d in found]
        return max(nums)[1] if nums else None
    for pat, rx in (("module[0-9][0-9]", r"module(\d+)$"), ("M[0-9][0-9]_*", r"M(\d+)_"), ("m[0-9]*", r"m(\d+)$")):
        for d in sorted(glob.glob(os.path.join(mods, pat))):
            m = re.match(rx, os.path.basename(d))
            if m and os.path.isdir(d) and int(m.group(1)) == n:
                return d
    return None


def deck_file(course, module):
    d = module_dir(course, module)
    if not d:
        return None
    for n in (os.path.join("presentation", "index.html"), "module.html", "index.html"):
        if os.path.isfile(os.path.join(d, n)):
            return os.path.join(d, n)
    return None


STAMP = re.compile(r"\b20\d\d-\d\d-\d\d[T ]\d\d:\d\d(?::\d\d)?(?:\.\d+)?(?:Z|[+-]\d\d:?\d\d)?")
COMMENT = re.compile(r"<!--.*?-->", re.S)


def deck_sha256(path):
    """the deck's content, ignoring HTML comments and build timestamps - two builds of the same deck hash the same"""
    with open(path, encoding="utf-8") as f:
        t = f.read()
    t = STAMP.sub("", COMMENT.sub("", t))
    return hashlib.sha256(re.sub(r"\s+", " ", t).encode("utf-8")).hexdigest()


def load_json(p, default=None):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def figure_why(course, module):
    """{slide id: (why, why_text)} from the module's build sheet (kit figure, kit3d model or custom figure)"""
    out = {}
    for d in (os.path.join(_work(course), "working_claude", "script"), os.path.join(_work(course), "script")):
        b = load_json(os.path.join(d, mid(module) + ".build.json"))
        if b:
            for sid, e in (b.get("screens") or {}).items():
                if isinstance(e, dict) and (e.get("why") or e.get("why_text")):
                    out[sid] = (e.get("why", ""), e.get("why_text", ""))
            break
    # 2.116.1 - the reason may live in the figure's own spec (figures/MNN/sNN.kit.json, .kit2d.json, .kit3d.json)
    for spec in sorted(glob.glob(os.path.join(_work(course), "working_claude", "figures", mid(module), "*.kit*.json"))):
        sid = os.path.basename(spec).split(".")[0]
        s = load_json(spec) or {}
        if sid not in out and isinstance(s, dict) and (s.get("why") or s.get("why_text")):
            out[sid] = (s.get("why", ""), s.get("why_text", ""))
    return out


def stops_by_slide(course, module):
    data = load_json(os.path.join(walk_dir(course, module), "walk.json"), {}) or {}
    out = {}
    for s in data.get("stops", []):
        out.setdefault(s["slide"], []).append(s)
    return out


def contact_sheet(stops, wdir, out_path, cols=3):
    """all of a slide's stops in a numbered grid -> out_path (needs Pillow)"""
    from PIL import Image, ImageDraw, ImageFont
    ims = []
    for s in stops:
        p = os.path.join(wdir, s["file"])
        if os.path.isfile(p):
            ims.append((s["k"], Image.open(p).convert("RGB")))
    if not ims:
        return False
    w, h = max(i.width for _, i in ims), max(i.height for _, i in ims)
    cols = min(cols, len(ims))
    rows = (len(ims) + cols - 1) // cols
    pad = 8
    sheet = Image.new("RGB", (cols * (w + pad) + pad, rows * (h + pad) + pad), (255, 255, 255))
    try:
        font = ImageFont.load_default(size=22)
    except TypeError:
        font = ImageFont.load_default()
    d = ImageDraw.Draw(sheet)
    for n, (k, im) in enumerate(ims):
        x, y = pad + (n % cols) * (w + pad), pad + (n // cols) * (h + pad)
        sheet.paste(im, (x, y))
        d.rectangle([x, y, x + 34, y + 30], fill=(10, 36, 99))
        d.text((x + 8, y + 3), str(k), fill=(255, 255, 255), font=font)
        d.rectangle([x, y, x + im.width - 1, y + im.height - 1], outline=(180, 180, 180))
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    sheet.save(out_path)
    return True


def prepare(course, module, slides=None):
    """-> (exit code, [lines]). Makes the sheets and the brief for every walked slide (or only `slides`)"""
    wdir = walk_dir(course, module)
    by = stops_by_slide(course, module)
    if not by:
        return 2, ["walk_review: no walk for %s in %s - run the build (or fit_gate.py --walk-dir) first" % (mid(module), wdir)]
    try:
        import PIL  # noqa: F401
    except ImportError:
        return 2, ["walk_review: Pillow is not installed - python -m pip install pillow"]
    want = [x.strip() for x in slides if x.strip()] if slides else None
    ids = [s for s in by if not want or s in want]
    missing = [s for s in (want or []) if s not in by]
    if not ids:
        return 2, ["walk_review: none of %s was walked" % ", ".join(want or [])]
    why = figure_why(course, module)
    sheets = {}
    for sid in ids:
        out = os.path.join(wdir, "sheets", sid + ".png")
        if contact_sheet(by[sid], wdir, out):
            sheets[sid] = out
    lines = ["# Walk review - %s" % mid(module), "",
             "Look at each contact sheet below: every stop of the slide, numbered, as the trainee sees it at 1280x800 "
             "(Start, then each Next). Judge the whole set of a batch in one look. Judge by this RUBRIC - one slide, each point:", ""]
    lines += ["%d. %s" % (i, r) for i, r in enumerate(RUBRIC, 1)]
    lines += ["", "Return ONLY this JSON (every slide of the batch; \"fails\" are short, concrete sentences naming the stop number):", "",
              "    {\"reviewed_by\": \"<your name / model>\", \"slides\": {\"s03\": {\"ok\": true, \"fails\": []},",
              "                                                     \"s07\": {\"ok\": false, \"fails\": [\"stop 3: the chart is still an empty axis\"]}}}",
              ""]
    order = [s for s in by if s in sheets]
    for b in range(0, len(order), BATCH):
        batch = order[b:b + BATCH]
        lines += ["", "## Batch %d - %s" % (b // BATCH + 1, ", ".join(batch)), ""]
        for sid in batch:
            lines += ["### %s - %s" % (sid, by[sid][0].get("title", "")), "", "Sheet: `%s`" % sheets[sid]]
            w = why.get(sid)
            lines += ["Figure why: %s - %s" % w if w else "Figure why: (none declared - a slide with no drawing, or the build sheet has no why)"]
            for s in by[sid]:
                bits = ["lit: " + " / ".join(s.get("lit") or []) if s.get("lit") else "lit: -"]
                if s.get("ask"):
                    bits.append("question on screen: " + " / ".join(s["ask"])[:120])
                if s.get("reveal"):
                    bits.append("answer on screen: " + " / ".join(s["reveal"])[:120])
                lines.append("- stop %d: %s" % (s["k"], "; ".join(bits)))
            lines.append("")
    if missing:
        lines += ["", "(not walked: %s)" % ", ".join(missing)]
    path = os.path.join(wdir, "review_brief.md")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    return 0, ["walk_review: %d contact sheet(s) in %s" % (len(sheets), os.path.join(wdir, "sheets")),
               "walk_review: the brief for the reviewer: %s (%d batch(es) of up to %d slides)" % (
                   path, (len(order) + BATCH - 1) // BATCH, BATCH)]


def sign(course, module, review_path):
    """-> (exit code, [lines]). Writes MNN_walk_review.json from the reviewer's JSON"""
    deck = deck_file(course, module)
    if not deck:
        return 2, ["walk_review: no deck for %s" % mid(module)]
    rv = load_json(review_path)
    if not isinstance(rv, dict) or not isinstance(rv.get("slides"), dict) or not rv["slides"]:
        return 2, ["walk_review: %s is not reviewer JSON ({\"reviewed_by\", \"slides\": {...}})" % review_path]
    if not str(rv.get("reviewed_by") or "").strip():
        return 2, ["walk_review: the reviewer JSON has no \"reviewed_by\""]
    slides = {}
    for sid, r in rv["slides"].items():
        if not isinstance(r, dict) or "ok" not in r:
            return 2, ["walk_review: slide %s has no \"ok\" in the reviewer JSON" % sid]
        fails = [str(x) for x in (r.get("fails") or []) if str(x).strip()]
        slides[sid] = {"ok": bool(r["ok"]) and not fails, "fails": fails}
        if not r["ok"] and not fails:
            slides[sid]["fails"] = ["(the reviewer failed this slide without saying why)"]
    prior = load_json(review_file(course, module), {}) or {}
    kept = {k: v for k, v in (prior.get("slides") or {}).items() if k not in slides}
    out = {"deck_sha256": deck_sha256(deck), "reviewed_by": str(rv["reviewed_by"]).strip(), "date": date.today().isoformat(),
           "slides": dict(kept, **slides)}
    p = review_file(course, module)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, indent=1, ensure_ascii=False, sort_keys=True)
    bad = sorted(k for k, v in out["slides"].items() if not v["ok"])
    return (1 if bad else 0), ["walk_review: signed %s by %s - %d slide(s) reviewed now%s" % (
        mid(module), out["reviewed_by"], len(slides), "; OPEN FAILS on %s - fix them and walk the module again" % ", ".join(bad) if bad else "")]


def verify(course, module, slides=None):
    """-> (ok, "missing" | "stale" | "failing" | "incomplete" | "", message). `slides`: only these slides must be covered"""
    p = review_file(course, module)
    rv = load_json(p)
    if not rv:
        return False, "missing", "walk review missing for %s - walk the module, then run the reviewer (walk_review.py prepare / sign)" % mid(module)
    deck = deck_file(course, module)
    if not deck:
        return False, "missing", "no deck for %s" % mid(module)
    if rv.get("deck_sha256") != deck_sha256(deck):
        return False, "stale", "walk review stale for %s - the deck changed after it was signed; walk and review it again" % mid(module)
    got = rv.get("slides") or {}
    walked = [s for s in stops_by_slide(course, module) if not slides or s in slides]
    gaps = [s for s in walked if s not in got]
    if gaps:
        return False, "incomplete", "walk review incomplete for %s - not reviewed: %s" % (mid(module), ", ".join(gaps))
    bad = sorted(s for s, v in got.items() if (not slides or s in slides) and (not v.get("ok") or v.get("fails")))
    if bad:
        return False, "failing", "walk review failing for %s - open fails on %s (%s)" % (
            mid(module), ", ".join(bad), "; ".join(got[bad[0]].get("fails") or ["not ok"])[:160])
    return True, "", "walk review passed for %s (%s, %s)" % (mid(module), rv.get("reviewed_by", "?"), rv.get("date", "?"))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("cmd", choices=("prepare", "sign", "verify"))
    ap.add_argument("course")
    ap.add_argument("--module", required=True)
    ap.add_argument("--slides")
    ap.add_argument("--review")
    o = ap.parse_args(argv)
    slides = [x for x in (o.slides or "").split(",") if x.strip()] or None
    if o.cmd == "prepare":
        rc, lines = prepare(o.course, o.module, slides)
        print("\n".join(lines))
        return rc
    if o.cmd == "sign":
        if not o.review:
            print("walk_review: sign needs --review <reviewer.json>")
            return 2
        rc, lines = sign(o.course, o.module, o.review)
        print("\n".join(lines))
        return rc
    ok, kind, msg = verify(o.course, o.module, slides)
    print(("OK: " if ok else "NOT DONE: ") + msg)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
