#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""walk_review - "walk it like a trainee": the deck's stops looked at together, by an AI reviewer, before a module is done.

    python walk_review.py prepare <course> --module N [--slides s03,s07] [--stale]
    python walk_review.py sign    <course> --module N --review reviewer.json --built-by "<who built the module>"
    python walk_review.py verify  <course> --module N
    python walk_review.py accept  <course> --module N --by "<operator>" --why "<why it can ship>" [--slides s04]
    python walk_review.py reopen  <course> --module N --by "<operator>"

WHY (operator Aleksis Vejs, 2026-11-09, after the Project Management review): the checks measure fit and overflow; they never
look at the slides the way a trainee does - a drawing that never moves, an empty chart, a picture that says the opposite of
the lit line all passed. fit_gate.py walks the deck (Start, every Next) and, at 1280x800 only, saves each stop as a ~480 px
picture with walk.json (the lit line's text, the room's question / its answer, the figure's signature) into
working_claude/_build/walk/MNN/. This script turns them into something a reviewer can judge several slides at once:

  prepare  one CONTACT SHEET per slide (all its stops in a numbered grid) -> walk/MNN/sheets/sNN.png, and
           walk/MNN/review_brief.md: the sheets in batches of 3-4 slides, each slide's stop texts and its figure's why /
           why_text, and the RUBRIC. --stale: only the slides with no verdict for what they show now (never reviewed, or
           changed since) - after a fix that is the changed slides alone. Needs Pillow (python -m pip install pillow).
  sign     the reviewer's answer {"reviewed_by": "...", "slides": {"s03": {"ok": true, "fails": []}}} ->
           working_claude/_build/MNN_walk_review.json: who built the module, who reviewed it, the round, and for every slide
           its verdict with the hash of what the reviewer saw. A slide the reviewer did not return keeps its earlier result.
           The reviewer is never the builder: sign refuses a "reviewed_by" equal to --built-by.
  verify   exit 0 only when every walked slide has a verdict for what it shows NOW and no fail is open. Exit 1 otherwise:
           missing / stale (names the changed slides only) / incomplete / failing.
  accept   the operator lets fails stand: recorded on each slide with who, when and why. A slide that changes afterwards
           needs its review again - the accept was for what the reviewer saw.
  reopen   the operator has the leftovers fixed after all: the two rounds start again.

ONE SLIDE, ONE HASH. A slide's hash is its own <section> plus everything outside the slides (styles, scripts, navigation),
ignoring build timestamps and comments: a fix to one slide leaves every other slide's verdict standing, a change to the
shell makes them all stale.

TWO ROUNDS AT MOST. The first review, one fix, the review of what the fix changed - then no third: what still fails is the
operator's, listed with its slide and stop (accept, or reopen). sign refuses a third round.

The reviewer is an AI agent that did not build the module - the factory cannot call one. In the whole-course workflow it is
the walk judge (orchestration/workflows/build_course.js); in a single session compile/GUIDE.md 2i and fix/GUIDE.md say how:
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
MAX_ROUNDS = 2
RUBRIC = [
    "Something visibly changes on each Next (the lit line, the figure, the question or its answer) - a stop that looks like the one before it is a fail.",
    "The picture shows what the lit line says (a bar rises when the line says it rises; the highlighted part is the part named).",
    "Nothing is empty, hidden, cut, duplicated or contradictory - an empty chart or axis, a label off the edge, the same thing drawn twice, a figure that says one thing while the words say another.",
    "A trainee would know what to do / what the slide teaches - the slide has one point and it is readable from the sheet.",
    "The drawing has a reason and serves it - its why / why_text (below) is what the trainee sees change or see; a drawing that is decoration, or a 3D model of a flat idea, fails.",
    "The answer / reveal is visible when it should be and does not cover the figure.",
    "Nothing on screen is the factory's instead of the trainee's - a file path, a drive letter, a placeholder, a credit line that is cut or lies over the picture.",
    "The picture is the thing the words name, and a seafarer would not call it wrong - another instrument, part or place than the slide names, a part drawn where it cannot be, a pipe or label ending on nothing.",
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
SECTION = re.compile(r"<section\b[^>]*\bid=\"([^\"]+)\"[^>]*>", re.I)


def _sha(text):
    return hashlib.sha256(re.sub(r"\s+", " ", text).encode("utf-8")).hexdigest()


def _content(path):
    with open(path, encoding="utf-8") as f:
        return STAMP.sub("", COMMENT.sub("", f.read()))


def deck_sha256(path):
    """the deck's content, ignoring HTML comments and build timestamps - two builds of the same deck hash the same"""
    return _sha(_content(path))


def slide_hashes(path):
    """{slide id: hash} - a slide's own <section> with everything outside the slides (the shell), so a change to one slide
    leaves the others' hashes alone and a change to the shell changes them all. A slide runs to the next slide's start."""
    t = _content(path)
    starts = [(m.start(), m.group(1)) for m in SECTION.finditer(t)]
    if not starts:
        return {}
    end = t.rfind("</section>")
    end = end + len("</section>") if end > starts[-1][0] else len(t)
    shell = _sha(t[:starts[0][0]] + t[end:])
    out = {}
    for i, (a, sid) in enumerate(starts):
        b = starts[i + 1][0] if i + 1 < len(starts) else end
        out.setdefault(sid, _sha(shell + "|" + t[a:b]))
    return out


def deck_now(path):
    """-> (the whole deck's hash, hash of a slide id). A walked slide with no <section> of its own gets the whole deck's"""
    whole, each = deck_sha256(path), slide_hashes(path)
    return whole, lambda sid: each.get(sid, whole)


def load_json(p, default=None):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def save_review(course, module, rv):
    p = review_file(course, module)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        json.dump(rv, f, indent=1, ensure_ascii=False, sort_keys=True)


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


def walked_before_change(course, module, now):
    """the slides whose pictures are older than the deck: fit_gate.py wrote each slide's hash beside the walk, and the deck
    has changed since. A walk with no hashes (an older fit_gate.py) is not judged"""
    data = load_json(os.path.join(walk_dir(course, module), "walk.json"), {}) or {}
    seen, whole = data.get("slides"), data.get("deck_sha256")
    if not isinstance(seen, dict) and not whole:
        return []
    seen = seen if isinstance(seen, dict) else {}
    return [s for s in stops_by_slide(course, module) if seen.get(s, whole) != now(s)]


def is_open(v):
    """a slide's verdict still has a fail nobody accepted"""
    return bool(not v.get("ok") or v.get("fails")) and not v.get("accepted")


def is_stale(v, sid, rv, whole, now):
    """the slide changed after its verdict. A verdict from before the per-slide hashes stands only for the deck it was
    signed for"""
    if v.get("sha256"):
        return v["sha256"] != now(sid)
    return rv.get("deck_sha256") != whole


def who(name):
    return re.sub(r"[^a-z0-9]+", " ", str(name or "").lower()).strip()


def to_review(course, module):
    """the walked slides with no verdict for what they show now: never reviewed, or changed since"""
    deck = deck_file(course, module)
    rv = load_json(review_file(course, module), {}) or {}
    got = rv.get("slides") or {}
    walked = list(stops_by_slide(course, module))
    if not deck:
        return walked
    whole, now = deck_now(deck)
    return [s for s in walked if s not in got or is_stale(got[s], s, rv, whole, now)]


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


def prepare(course, module, slides=None, stale_only=False):
    """-> (exit code, [lines]). Makes the sheets and the brief for every walked slide, only `slides`, or (stale_only) only
    the slides with no verdict for what they show now"""
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
    deck = deck_file(course, module)
    old = walked_before_change(course, module, deck_now(deck)[1]) if deck else []
    if stale_only:
        due = to_review(course, module)
        ids = [s for s in ids if s in due]
        if not ids:
            return 0, ["walk_review: nothing to review for %s - every walked slide has a verdict for what it shows now" % mid(module)]
    if any(s in old for s in ids):
        return 2, ["walk_review: %s walked before the deck changed (%s) - the pictures are of an older slide; build again "
                   "(build_module.py, or fit_gate.py --walk-dir), then prepare" % (mid(module), ", ".join(s for s in ids if s in old))]
    why = figure_why(course, module)
    last = (load_json(review_file(course, module), {}) or {}).get("slides") or {}
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
              "",
              "You did not build this module: a builder never signs its own walk (walk_review.py sign --built-by refuses it)."]
    order = [s for s in by if s in sheets]
    for b in range(0, len(order), BATCH):
        batch = order[b:b + BATCH]
        lines += ["", "## Batch %d - %s" % (b // BATCH + 1, ", ".join(batch)), ""]
        for sid in batch:
            lines += ["### %s - %s" % (sid, by[sid][0].get("title", "")), "", "Sheet: `%s`" % sheets[sid]]
            w = why.get(sid)
            lines += ["Figure why: %s - %s" % w if w else "Figure why: (none declared - a slide with no drawing, or the build sheet has no why)"]
            was = (last.get(sid) or {}).get("fails") or []
            if was:
                lines += ["Failed in the last review - say for each whether it is fixed now: %s" % " | ".join(was)]
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
    return 0, ["walk_review: %d contact sheet(s) in %s%s" % (len(sheets), os.path.join(wdir, "sheets"),
                                                            " - only the slides not reviewed as they are now: %s" % ", ".join(order)
                                                            if stale_only else ""),
               "walk_review: the brief for the reviewer: %s (%d batch(es) of up to %d slides)" % (
                   path, (len(order) + BATCH - 1) // BATCH, BATCH)]


def choices(module):
    """what the operator can do with fails left after the last round"""
    return ("accept them: walk_review.py accept <course> --module %s --by \"<operator>\" --why \"<why it can ship>\"; or have "
            "them fixed and start again: walk_review.py reopen <course> --module %s --by \"<operator>\"" % (module, module))


def open_fails(course, module, slides=None):
    """["s04 - stop 3: the chart is still an empty axis", ...] - every fail nobody accepted, with its slide and stop"""
    got = (load_json(review_file(course, module), {}) or {}).get("slides") or {}
    walked = list(stops_by_slide(course, module))
    return ["%s - %s" % (s, f) for s in (walked or sorted(got)) if s in got and is_open(got[s]) and (not slides or s in slides)
            for f in (got[s].get("fails") or ["not ok"])]


def sign(course, module, review_path, built_by=None):
    """-> (exit code, [lines]). Writes MNN_walk_review.json from the reviewer's JSON: 0 signed and clean, 1 signed with open
    fails, 2 refused (bad input, the builder's own signature, pictures older than the deck), 3 refused (a third round)"""
    deck = deck_file(course, module)
    if not deck:
        return 2, ["walk_review: no deck for %s" % mid(module)]
    rv = load_json(review_path)
    if not isinstance(rv, dict) or not isinstance(rv.get("slides"), dict) or not rv["slides"]:
        return 2, ["walk_review: %s is not reviewer JSON ({\"reviewed_by\", \"slides\": {...}})" % review_path]
    by = str(rv.get("reviewed_by") or "").strip()
    if not by:
        return 2, ["walk_review: the reviewer JSON has no \"reviewed_by\""]
    prior = load_json(review_file(course, module), {}) or {}
    builder = str(built_by or rv.get("built_by") or prior.get("built_by") or "").strip()
    if not builder:
        return 2, ["walk_review: say who built %s - sign ... --built-by \"<who built the module>\" (the reviewer is someone else)" % mid(module)]
    if who(by) == who(builder):
        return 2, ["walk_review: \"%s\" built %s - a builder never signs its own walk review; a reviewer that did not build "
                   "it looks at the sheets and signs" % (builder, mid(module))]
    whole, now = deck_now(deck)
    today = date.today().isoformat()
    old = [s for s in walked_before_change(course, module, now) if s in rv["slides"]]
    if old:
        return 2, ["walk_review: %s walked before the deck changed (%s) - the reviewer saw an older slide; build again, "
                   "prepare --stale, and review those" % (mid(module), ", ".join(old))]
    walked = list(stops_by_slide(course, module))
    was = prior.get("slides") or {}
    was_open = [s for s, v in was.items() if is_open(v) and (not walked or s in walked)]
    if not was:
        rnd = 1
    elif prior.get("deck_sha256") == whole:                  # more batches of the same review
        rnd = max(1, int(prior.get("rounds", 1)))
    elif not was_open:                                       # the last review ended clean: a new change, a new first round
        rnd = 1
    else:
        rnd = int(prior.get("rounds", 1)) + 1
    if rnd > MAX_ROUNDS:
        return 3, ["walk_review: %s has had its %d walk rounds - no third. Still failing: %s" % (mid(module), MAX_ROUNDS, ", ".join(sorted(was_open))),
                   "  The operator's choice - %s" % choices(module)]
    slides = {}
    for sid, r in rv["slides"].items():
        if not isinstance(r, dict) or "ok" not in r:
            return 2, ["walk_review: slide %s has no \"ok\" in the reviewer JSON" % sid]
        fails = [str(x) for x in (r.get("fails") or []) if str(x).strip()]
        slides[sid] = {"ok": bool(r["ok"]) and not fails, "fails": fails, "sha256": now(sid), "reviewed_by": by, "date": today, "round": rnd}
        if not r["ok"] and not fails:
            slides[sid]["fails"] = ["(the reviewer failed this slide without saying why)"]
    kept = {}
    for k, v in was.items():
        if k not in slides:
            # a verdict from before the per-slide hashes: it stands for the deck it was signed for, and for no other
            kept[k] = v if v.get("sha256") else dict(v, sha256=now(k) if prior.get("deck_sha256") == whole else "signed-for-an-older-deck")
    out = dict({k: v for k, v in prior.items() if k == "reopened"},
               deck_sha256=whole, reviewed_by=by, built_by=builder, date=today, rounds=rnd, slides=dict(kept, **slides))
    save_review(course, module, out)
    bad = sorted(k for k, v in out["slides"].items() if is_open(v) and (not walked or k in walked))
    head = "walk_review: signed %s by %s (round %d of %d; built by %s) - %d slide(s) reviewed now" % (
        mid(module), by, rnd, MAX_ROUNDS, builder, len(slides))
    if not bad:
        return 0, [head]
    if rnd < MAX_ROUNDS:
        head += "; OPEN FAILS on %s - fix them, build, then prepare --stale and ONE more review of what changed" % ", ".join(bad)
        return 1, [head] + ["  " + x for x in open_fails(course, module)]
    head += "; OPEN FAILS on %s - that was the last round" % ", ".join(bad)
    return 1, [head] + ["  " + x for x in open_fails(course, module)] + ["  The operator's choice - %s" % choices(module)]


def verify(course, module, slides=None):
    """-> (ok, "missing" | "stale" | "failing" | "incomplete" | "", message). `slides`: only these slides must be covered"""
    p = review_file(course, module)
    rv = load_json(p)
    if not rv:
        return False, "missing", "walk review missing for %s - walk the module, then run the reviewer (walk_review.py prepare / sign)" % mid(module)
    deck = deck_file(course, module)
    if not deck:
        return False, "missing", "no deck for %s" % mid(module)
    whole, now = deck_now(deck)
    got = rv.get("slides") or {}
    walked = [s for s in stops_by_slide(course, module) if not slides or s in slides]
    judged = [s for s in (walked or sorted(got)) if s in got and (not slides or s in slides)]
    stale = [s for s in judged if is_stale(got[s], s, rv, whole, now)]
    if stale:
        return False, "stale", ("walk review stale for %s - %d of %d slide(s) changed after the review: %s; build, then "
                                "walk_review.py prepare --stale shows the reviewer only those" % (
                                    mid(module), len(stale), len(judged), ", ".join(stale)))
    gaps = [s for s in walked if s not in got]
    if gaps:
        return False, "incomplete", "walk review incomplete for %s - not reviewed: %s" % (mid(module), ", ".join(gaps))
    bad = [s for s in judged if is_open(got[s])]
    if bad:
        last = int(rv.get("rounds", 1)) >= MAX_ROUNDS
        return False, "failing", "walk review failing for %s - open fails on %s (%s) - round %s of %d%s" % (
            mid(module), ", ".join(bad), "; ".join(got[bad[0]].get("fails") or ["not ok"])[:160], max(1, int(rv.get("rounds", 1))), MAX_ROUNDS,
            ", no third: the operator accepts what is left or reopens it (walk_review.py accept / reopen)" if last
            else ": fix them, build, and one more review of what changed")
    let = sorted({(got[s].get("accepted") or {}).get("by", "?") for s in judged if got[s].get("accepted")})
    n = sum(1 for s in judged if got[s].get("accepted"))
    return True, "", "walk review passed for %s (%s, %s%s)" % (
        mid(module), rv.get("reviewed_by", "?"), rv.get("date", "?"),
        "; fails on %d slide(s) accepted by %s" % (n, ", ".join(let)) if n else "")


def _operator(rv, by):
    """-> why this name cannot act as the operator, or '' """
    if not who(by):
        return "say who decides - --by \"<operator>\""
    names = {who(rv.get("built_by")), who(rv.get("reviewed_by"))} | {who(v.get("reviewed_by")) for v in (rv.get("slides") or {}).values()}
    if who(by) in names - {""}:
        return "\"%s\" built or reviewed this module - the accept is the operator's, never the builder's or the reviewer's" % by
    return ""


def accept(course, module, by, why, slides=None):
    """-> (exit code, [lines]). The operator lets the open fails (of `slides`, or all) stand - recorded on each slide"""
    rv = load_json(review_file(course, module))
    deck = deck_file(course, module)
    if not rv or not deck:
        return 2, ["walk_review: no walk review to accept for %s" % mid(module)]
    no = _operator(rv, by)
    if no:
        return 2, ["walk_review: " + no]
    if not str(why or "").strip():
        return 2, ["walk_review: say why it can ship - --why \"...\" (it is recorded beside the fail)"]
    whole, now = deck_now(deck)
    got = rv.get("slides") or {}
    walked = list(stops_by_slide(course, module))
    todo = [s for s in (walked or sorted(got)) if s in got and is_open(got[s]) and (not slides or s in slides)]
    if not todo:
        return 2, ["walk_review: no open fail to accept for %s%s" % (mid(module), " on %s" % ", ".join(slides) if slides else "")]
    changed = [s for s in todo if is_stale(got[s], s, rv, whole, now)]
    if changed:
        return 2, ["walk_review: %s changed after the review (%s) - an accept is for what the reviewer saw; review it first "
                   "(prepare --stale)" % (mid(module), ", ".join(changed))]
    lines = []
    for s in todo:
        got[s]["accepted"] = {"by": str(by).strip(), "date": date.today().isoformat(), "why": str(why).strip(), "fails": list(got[s].get("fails") or [])}
        lines += ["  %s - %s" % (s, f) for f in got[s]["accepted"]["fails"] or ["not ok"]]
    save_review(course, module, rv)
    return 0, ["walk_review: %s - %s accepted %d slide(s) as they are (%s): %s" % (mid(module), str(by).strip(), len(todo), str(why).strip(), ", ".join(todo))] + lines


def reopen(course, module, by):
    """-> (exit code, [lines]). The operator has the leftovers fixed after all: the rounds start again"""
    rv = load_json(review_file(course, module))
    if not rv:
        return 2, ["walk_review: no walk review to reopen for %s" % mid(module)]
    no = _operator(rv, by)
    if no:
        return 2, ["walk_review: " + no]
    rv["rounds"] = 0
    rv.setdefault("reopened", []).append({"by": str(by).strip(), "date": date.today().isoformat()})
    save_review(course, module, rv)
    return 0, ["walk_review: %s reopened by %s - fix what is open, build, prepare --stale, and the rounds start again (%d at most)" % (
        mid(module), str(by).strip(), MAX_ROUNDS)]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("cmd", choices=("prepare", "sign", "verify", "accept", "reopen"))
    ap.add_argument("course")
    ap.add_argument("--module", required=True)
    ap.add_argument("--slides")
    ap.add_argument("--stale", action="store_true", help="prepare: only the slides with no verdict for what they show now")
    ap.add_argument("--review")
    ap.add_argument("--built-by", help="sign: who built the module - the reviewer must be someone else")
    ap.add_argument("--by", help="accept / reopen: the operator")
    ap.add_argument("--why", help="accept: why the fails can ship")
    o = ap.parse_args(argv)
    slides = [x for x in (o.slides or "").split(",") if x.strip()] or None
    if o.cmd == "prepare":
        rc, lines = prepare(o.course, o.module, slides, o.stale)
    elif o.cmd == "sign":
        if not o.review:
            print("walk_review: sign needs --review <reviewer.json>")
            return 2
        rc, lines = sign(o.course, o.module, o.review, o.built_by)
    elif o.cmd == "accept":
        rc, lines = accept(o.course, o.module, o.by, o.why, slides)
    elif o.cmd == "reopen":
        rc, lines = reopen(o.course, o.module, o.by)
    else:
        ok, kind, msg = verify(o.course, o.module, slides)
        print(("OK: " if ok else "NOT DONE: ") + msg)
        if kind == "failing":
            print("\n".join("  " + x for x in open_fails(o.course, o.module, slides)))
        return 0 if ok else 1
    print("\n".join(lines))
    return rc


if __name__ == "__main__":
    sys.exit(main())
