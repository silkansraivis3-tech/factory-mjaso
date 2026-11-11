# -*- coding: utf-8 -*-
"""test_walk_review - "walk it like a trainee": prepare / sign / verify / accept / reopen on a fixture deck, and the gates.

    python test_walk_review.py

Every check RUNS the behaviour on a fixture course (a deck with a stylesheet, a script and a photograph beside it). Pinned:
  * prepare makes one contact sheet per walked slide, their manifest (each sheet's slide fingerprint) and review_brief.md
    (batches of at most 4 slides, each slide's stop texts, its figure's why / why_text, the rubric); --slides limits it;
    --stale shows only the slides with no verdict for what they show now, with what failed last time;
  * one slide, one fingerprint - the audits' own (check_cache.py): a fix to one slide makes that slide stale and no other; a
    changed stylesheet, script or new file of assets\\ makes them all stale; a replaced photograph the slides that show it;
  * sign records the fingerprint of the sheet the reviewer SAW: a slide with no sheet, or one that changed (or was walked
    again) after its sheet was made, is refused; "ok" must be true or false; a verdict that stands is not replaced;
    the builder's and the fixer's own signature and a missing --built-by are refused;
  * verify wants every slide of the deck reviewed - also one the walk never reached;
  * two rounds at most: a third sign is refused (exit 3), also after the failing slide was renamed; accept (the operator,
    with a reason, recorded with how it was run) lets the module pass and is void once the slide changes; reopen starts the
    rounds again and lets the open slides be reviewed as they are;
  * the final assessment is FINAL whether asked for by name or by its folder's number;
  * a review signed before the fingerprints stands for its deck and no other; a walk with no fingerprints is refused;
  * the gates: fix.py check --kind walk, course_portal upload (what stops it, and the accepted fails it shows);
  * the trainee's task pages (tasks\\, assessment\\, never an answer key) are reviewed like the slides: one verdict per
    question and per last screen, one fingerprint per page (the page and what it loads) - a changed page makes its own
    questions stale and nothing else; a module whose deck is reviewed and whose task pages are not is incomplete and
    refused at the upload; the two rounds, the accept (on the upload's list) and fix.py check --slides <page> hold for them.
No browser needed: the walk's stops are fixture PNGs (walk() stands in for the build's fit walk, walk_pages() for
review_sheets.mjs --walk-dir).
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import walk_review as wr  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
PASS, FAIL = [], []


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print(("  ok    " if ok else "  FAIL  ") + name + (("  -> " + str(detail)[:700]) if detail and not ok else ""))


WORDS = ["One", "Two", "Three", "Four", "Five"]
DECK = ("<html><head><link rel=\"stylesheet\" href=\"../assets/deck.css\"></head><body><main>"
        + "".join("<section class=\"slide\" id=\"s%02d\">%s%s</section>" % (i, w, "<img src=\"../assets/img/p3.jpg\">" if i == 3 else "")
                  for i, w in enumerate(WORDS, 1))
        + "</main><script src=\"../assets/gb_deck.js\"></script></body></html>")
FINAL_DECK = DECK.replace("id=\"s01\">", "id=\"s01\" data-block=\"FINAL-A\">")
BUILDER, FIXER, REVIEWER, OPERATOR = "build:1 (workflow builder)", "fix:1 (workflow fixer)", "Sonnet subagent", "Aleksis Vejs"
ALL = {"s%02d" % i: True for i in range(1, 6)}
ONE_FAIL = dict(ALL, s04="stop 3: the chart is still an empty axis")


def add_module(course, n, text=DECK):
    mdir = os.path.join(course, "modules", "module%02d" % n)
    os.makedirs(os.path.join(mdir, "presentation"))
    os.makedirs(os.path.join(mdir, "assets", "img"))
    Path(mdir, "assets", "deck.css").write_text(".slide{color:navy}", encoding="utf-8")
    Path(mdir, "assets", "gb_deck.js").write_text("var deck = 1", encoding="utf-8")
    Path(mdir, "assets", "img", "p3.jpg").write_bytes(b"a photograph")
    deck = Path(mdir, "presentation", "index.html")
    deck.write_text(text, encoding="utf-8")
    return deck


def walk(course, module=1, skip=()):
    """what the build's fit walk leaves (fit_gate.py --walk-dir): three stops a slide, and walk.json with each slide's
    fingerprint as the walk began"""
    from PIL import Image
    wdir = wr.walk_dir(course, module)
    os.makedirs(wdir, exist_ok=True)
    stamp = wr.walk_stamp(wr.deck_file(course, module))
    stops = []
    for i, sid in enumerate(stamp["fingerprints"], 1):
        for k in (1, 2, 3):
            if sid in skip:
                continue
            fname = "%s_k%d.png" % (sid, k)
            Image.new("RGB", (480, 300), (30 * i, 60 * k, 120)).save(os.path.join(wdir, fname))
            stops.append({"slide": sid, "k": k, "file": fname, "title": "Slide %d" % i, "lit": ["Line %d" % k],
                          "ask": [], "reveal": ["The answer"] if k == 3 else [], "fig": ":1:2"})
    Path(wdir, "walk.json").write_text(json.dumps(dict({"viewport": "1280x800", "stops": stops}, **stamp)), encoding="utf-8")


def fixture(tmp, name="course", skip=()):
    course = os.path.join(tmp, name)
    deck = add_module(course, 1)
    walk(course, 1, skip)
    sdir = os.path.join(course, "working_claude", "script")
    os.makedirs(sdir)
    Path(sdir, "M01.build.json").write_text(json.dumps({"screens": {
        "s02": {"figure": "s02.kit2d.json", "why": "sequence", "why_text": "The trainee sees the valve close."}}}), encoding="utf-8")
    return course, deck


def rebuilt(course, deck, text, module=1):
    """a fix and its build: the deck changes, it is walked again, and the reviewer gets the sheets of what changed"""
    deck.write_text(text, encoding="utf-8")
    walk(course, module)
    return wr.prepare(course, module, stale_only=True)


def reviewer(tmp, slides, by=REVIEWER):
    """a reviewer JSON file: {"s04": "stop 3: ..."} is a fail, {"s01": True} a pass, a dict is written as it is"""
    p = os.path.join(tmp, "reviewer.json")
    Path(p).write_text(json.dumps({"reviewed_by": by, "slides": {
        s: v if isinstance(v, dict) else {"ok": v is True, "fails": [] if v is True else [v]} for s, v in slides.items()}}),
        encoding="utf-8")
    return p


def signed(course, module=1):
    return json.loads(Path(wr.review_file(course, module)).read_text(encoding="utf-8"))


def raw(course, module=1):
    p = wr.review_file(course, module)
    return Path(p).read_text(encoding="utf-8") if os.path.isfile(p) else None


def brief_of(course, module=1):
    return Path(wr.walk_dir(course, module), "review_brief.md").read_text(encoding="utf-8")


def quiet(*argv):
    buf, stdin = io.StringIO(), sys.stdin
    sys.stdin = io.StringIO()          # as a session or a script runs it: no terminal
    try:
        with contextlib.redirect_stdout(buf):
            rc = wr.main(list(argv))
    finally:
        sys.stdin = stdin
    return rc, buf.getvalue()


def first_part(tmp):
    """prepare, sign, verify - one review, signed in batches; what a verdict is signed for"""
    course, deck = fixture(tmp)
    rc, lines = wr.prepare(course, 1)
    wdir = wr.walk_dir(course, 1)
    sheets = sorted(x for x in os.listdir(os.path.join(wdir, "sheets")) if x.endswith(".png"))
    brief = brief_of(course)
    check("prepare: one contact sheet per slide", rc == 0 and sheets == ["s%02d.png" % i for i in range(1, 6)], (rc, lines, sheets))
    from PIL import Image
    im = Image.open(os.path.join(wdir, "sheets", "s01.png"))
    check("... all its stops in a numbered grid (3 stops, 480 px each, side by side)", im.width >= 3 * 480 and im.height >= 300, im.size)
    check("... the brief lists the sheets in batches of at most 4 slides", "## Batch 1 - s01, s02, s03, s04" in brief and "## Batch 2 - s05" in brief
          and "2 batch(es) of up to 4 slides" in lines[1], lines)
    check("... each slide's stop texts, the answer on screen and the figure's why / why_text",
          "stop 3: lit: Line 3; answer on screen: The answer" in brief and "Figure why: sequence - The trainee sees the valve close." in brief)
    check("... and the rubric (changes on Next, shows what the line says, nothing empty / hidden / cut / duplicated / contradictory, "
          "what to do, the drawing's reason, answer visible and not over the figure)",
          all(x in brief for x in ("1. Something visibly changes on each Next", "2. The picture shows what the lit line says",
                                   "Nothing is empty, hidden, cut, duplicated or contradictory",
                                   "4. A trainee would know", "5. The drawing has a reason", "6. The answer / reveal")), brief[:600])
    check("... with the two points the sheet review used to carry for the deck: nothing of the factory's on screen, and the "
          "picture is the thing the words name", "7. Nothing on screen is the factory's" in brief and "8. The picture is the thing the words name" in brief
          and "a seafarer would not call it wrong" in brief and len(wr.RUBRIC) == 8)
    check("... and it tells the reviewer a builder never signs its own walk", "a builder never signs its own walk" in brief)
    seen = json.loads(Path(wr.manifest_file(course, 1)).read_text(encoding="utf-8"))["slides"]
    now = wr.fingerprints(str(deck))[1]
    check("... and the manifest says what each sheet is a picture of: the slide's fingerprint as it was walked",
          seen == now and len(set(seen.values())) == 5 and all(len(v) == 64 for v in seen.values()), seen)
    rc, _ = wr.prepare(course, 1, ["s02", "s03"])
    check("prepare --slides: only those slides' sheets are in the brief", rc == 0 and "## Batch 1 - s02, s03" in brief_of(course)
          and "s01" not in brief_of(course).split("## Batch")[1], rc)
    wr.prepare(course, 1)

    ok, kind, msg = wr.verify(course, 1)
    check("verify: no review yet -> missing, exit 1", not ok and kind == "missing" and quiet("verify", course, "--module", "1")[0] == 1, msg)
    four = {k: v for k, v in ONE_FAIL.items() if k != "s05"}
    rc, lines = wr.sign(course, 1, reviewer(tmp, four))
    check("sign: refused until it is told who built the module", rc == 2 and "--built-by" in lines[0] and raw(course) is None, (rc, lines))
    for own in (BUILDER, "BUILD:1 - workflow builder", "build 1 workflow-builder agent"):
        rc, lines = wr.sign(course, 1, reviewer(tmp, {"s01": True}, by=own), BUILDER)
        check("sign: the builder's own signature is refused, however it words its name (%s)" % own,
              rc == 2 and "never signs its own walk review" in lines[0] and raw(course) is None, (rc, lines))
    for bad in ({"ok": "false"}, {"ok": "true"}, {"ok": 1}, {"fails": []}, {"ok": True, "fails": "none"}):
        rc, lines = wr.sign(course, 1, reviewer(tmp, {"s01": bad, "s02": True}), BUILDER)
        check("sign: a verdict that is not a real true or false is refused, nothing written (%s)" % json.dumps(bad),
              rc == 2 and "s01" in lines[0] and raw(course) is None, (rc, lines))
    check("sign refuses a file that is no reviewer JSON, and one with no reviewer", wr.sign(course, 1, os.path.join(tmp, "nope.json"), BUILDER)[0] == 2
          and wr.sign(course, 1, reviewer(tmp, {"s01": True}, by=""), BUILDER)[0] == 2)
    rc, lines = wr.sign(course, 1, reviewer(tmp, four), BUILDER)
    got = signed(course)
    check("sign: writes MNN_walk_review.json with the deck's fingerprint, reviewer, date and slides",
          got["reviewed_by"] == "Sonnet subagent" and got["deck"] == wr.fingerprints(str(deck))[0] and got["date"] and got["slides"]["s04"]["ok"] is False
          and rc == 1 and "OPEN FAILS on s04" in lines[0], (rc, lines, got))
    check("... who built it, the round, and on every slide the fingerprint of the sheet the reviewer saw, the reviewer and the round",
          got["built_by"] == BUILDER and got["builders"] == [BUILDER] and got["rounds"] == 1 and "round 1 of 2" in lines[0]
          and all(v["fingerprint"] == seen[s] and v["reviewed_by"] == REVIEWER and v["round"] == 1 for s, v in got["slides"].items())
          and len(got["slides"]) == 4, (lines, got))
    check("... and lists every open fail with its slide and stop", "  s04 - stop 3: the chart is still an empty axis" in lines, lines)
    ok, kind, msg = wr.verify(course, 1)
    check("verify: s05 not reviewed -> incomplete", not ok and kind == "incomplete" and "s05" in msg, msg)
    rc, _ = wr.sign(course, 1, reviewer(tmp, {"s05": True}))
    ok, kind, msg = wr.verify(course, 1)
    check("... a second sign keeps the slides the reviewer did not return (and the builder's name); s04 still fails -> failing",
          not ok and kind == "failing" and "s04" in msg and "round 1 of 2" in msg and signed(course)["built_by"] == BUILDER, msg)
    check("... another batch of the same review is the same round", signed(course)["rounds"] == 1 and rc == 1)
    rc, out = quiet("verify", course, "--module", "1")
    check("verify prints the open fails with slide and stop", rc == 1 and "NOT DONE: walk review failing" in out and "  s04 - stop 3: the chart" in out, out)
    before = raw(course)
    rc, lines = wr.sign(course, 1, reviewer(tmp, {"s04": True, "s05": True}, by="another reviewer"))
    check("a fail is not signed away on the slide as it is: the verdict stands until the slide changes",
          rc == 2 and "already has a verdict" in lines[0] and raw(course) == before and wr.verify(course, 1)[1] == "failing", (rc, lines))
    fixed = DECK.replace("Four", "Four, fixed")
    rc0, lines0 = rebuilt(course, deck, fixed)
    rc, lines = wr.sign(course, 1, reviewer(tmp, {"s04": True, "s05": True}))
    ok, kind, msg = wr.verify(course, 1)
    check("the fail fixed, built and re-reviewed -> verify passes, exit 0 (the unchanged slide keeps its verdict)",
          rc0 == 0 and "## Batch 1 - s04\n" in brief_of(course) and ok and rc == 0 and signed(course)["rounds"] == 2
          and "s05 kept the verdict it has" in lines[0] and signed(course)["slides"]["s05"]["round"] == 1
          and quiet("verify", course, "--module", "1")[0] == 0, (lines0, lines, msg))
    rc, lines = wr.prepare(course, 1, stale_only=True)
    check("prepare --stale: nothing to review once every slide has a verdict for what it shows now", rc == 0 and "nothing to review" in lines[0], lines)

    assets = deck.parent.parent / "assets"
    for name, what, new in (("deck.css", "the stylesheet", ".slide{display:none}"), ("gb_deck.js", "a deck script", "var deck = 2")):
        was = (assets / name).read_text(encoding="utf-8")
        (assets / name).write_text(new, encoding="utf-8")
        ok, kind, msg = wr.verify(course, 1)
        check("%s changes -> every slide is stale" % what, not ok and kind == "stale" and "5 of 5 slide(s)" in msg, msg)
        (assets / name).write_text(was, encoding="utf-8")
        check("... and current again once it is as it was", wr.verify(course, 1)[0], wr.verify(course, 1))
    (assets / "kit_parts.js").write_text("var parts = []", encoding="utf-8")
    ok, kind, msg = wr.verify(course, 1)
    check("a new file of assets\\ (kit_parts.js) -> every slide is stale", not ok and kind == "stale" and "5 of 5 slide(s)" in msg, msg)
    os.remove(assets / "kit_parts.js")
    (assets / "img" / "p3.jpg").write_bytes(b"another photograph")
    ok, kind, msg = wr.verify(course, 1)
    check("a photograph is replaced -> the slide that shows it is stale and no other", not ok and kind == "stale" and "1 of 5 slide(s)" in msg
          and wr.to_review(course, 1) == ["s03"], msg)
    (assets / "img" / "p3.jpg").write_bytes(b"a photograph")

    deck.write_text(fixed.replace("Two", "Two, changed"), encoding="utf-8")
    ok, kind, msg = wr.verify(course, 1)
    check("the deck changed after the review -> stale, exit 1", not ok and kind == "stale" and quiet("verify", course, "--module", "1")[0] == 1, msg)
    check("... ONE slide changed -> that slide is stale and no other", "1 of 5 slide(s)" in msg and "s02" in msg and "s01" not in msg and "s03" not in msg
          and wr.to_review(course, 1) == ["s02"], msg)
    rc, lines = wr.prepare(course, 1, stale_only=True)
    check("prepare: the pictures are of an older slide -> refused, build again", rc == 2 and "walked before the deck changed" in lines[0]
          and "s02" in lines[0] and "build again" in lines[0], (rc, lines))
    rc, lines = wr.sign(course, 1, reviewer(tmp, {"s02": True}))
    check("sign: a verdict on the sheet of an older slide is refused", rc == 2 and "changed after its contact sheet was made" in lines[0], (rc, lines))
    walk(course)
    rc, lines = wr.prepare(course, 1, stale_only=True)
    check("... walked again, prepare --stale gives the reviewer that slide alone", rc == 0 and "## Batch 1 - s02\n" in brief_of(course)
          and "### s01" not in brief_of(course) and "s02" in lines[0], lines)
    # the reviewer is looking at the sheets while another step builds the module again
    deck.write_text(fixed.replace("Two", "Two, changed again by another step"), encoding="utf-8")
    walk(course)
    before = raw(course)
    rc, lines = wr.sign(course, 1, reviewer(tmp, {"s02": True}))
    check("the module is built again while the reviewer looks: its verdict on the older sheet is refused, nothing written",
          rc == 2 and "changed after its contact sheet was made" in lines[0] and "s02" in lines[0] and raw(course) == before, (rc, lines))
    wr.prepare(course, 1, stale_only=True)
    rc, lines = wr.sign(course, 1, reviewer(tmp, {"s02": True}))
    check("... the sheets made again and looked at, the verdict is signed for what the reviewer saw", rc == 0 and wr.verify(course, 1)[0]
          and signed(course)["slides"]["s02"]["fingerprint"] == wr.fingerprints(str(deck))[1]["s02"], (rc, lines))

    course, deck = fixture(tmp, "nosheet")
    rc, lines = wr.sign(course, 1, reviewer(tmp, ALL), BUILDER)
    check("sign: a slide no contact sheet was made for is refused - a reviewer signs only what prepare showed it",
          rc == 2 and "no contact sheet was made for" in lines[0] and raw(course) is None, (rc, lines))


def every_slide_part(tmp):
    """verify wants every slide of the deck, walked or not"""
    course, deck = fixture(tmp, "unreached", skip=("s05",))
    rc, lines = wr.prepare(course, 1)
    check("prepare: a slide the walk did not reach is named, the others get their sheets", rc == 0 and "4 contact sheet(s)" in lines[0]
          and any("no picture of s05" in x for x in lines), (rc, lines))
    rc, _ = wr.sign(course, 1, reviewer(tmp, {k: True for k in ALL if k != "s05"}), BUILDER)
    ok, kind, msg = wr.verify(course, 1)
    check("verify: every walked slide passed, but a slide of the deck was never walked -> not done",
          rc == 0 and not ok and kind == "incomplete" and "s05" in msg and "no picture" in msg, msg)
    rc, lines = wr.sign(course, 1, reviewer(tmp, {"s05": True}))
    check("... and nobody can sign the slide it was not shown", rc == 2 and "no contact sheet" in lines[0], (rc, lines))

    course, deck = fixture(tmp, "inserted")
    wr.prepare(course, 1)
    wr.sign(course, 1, reviewer(tmp, ALL), BUILDER)
    more = DECK.replace("<section class=\"slide\" id=\"s03\">", "<section class=\"slide\" id=\"s06\">New</section><section class=\"slide\" id=\"s03\">")
    deck.write_text(more, encoding="utf-8")
    check("a slide added to a signed deck and never walked -> not done", wr.verify(course, 1)[0] is False, wr.verify(course, 1))
    walk(course)
    rc, lines = wr.prepare(course, 1, stale_only=True)
    wr.sign(course, 1, reviewer(tmp, ALL))
    ok, kind, msg = wr.verify(course, 1)
    check("... walked, and the old slides signed again: still not done until the new slide is reviewed",
          rc == 0 and "6 contact sheet(s)" in lines[0] and not ok and kind == "incomplete" and "s06" in msg, (lines, msg))
    shutil.rmtree(wr.walk_dir(course, 1))
    check("... and losing the walk's pictures does not pass it", wr.verify(course, 1)[1] == "incomplete", wr.verify(course, 1))


def rounds_part(tmp):
    """two rounds at most, the operator's accept, reopen"""
    course, deck = fixture(tmp, "rounds")
    wr.prepare(course, 1)
    rc, _ = wr.sign(course, 1, reviewer(tmp, ONE_FAIL), BUILDER)
    rc0, lines0 = rebuilt(course, deck, DECK.replace("Four", "Four, fixed once"))
    brief = brief_of(course)
    check("round 2 starts with the fixed slide alone, and the brief says what failed last time",
          rc == 1 and rc0 == 0 and "## Batch 1 - s04\n" in brief and "Failed in the last review" in brief
          and "stop 3: the chart is still an empty axis" in brief.split("### s04")[1], (lines0, brief[-600:]))
    rc, lines = wr.sign(course, 1, reviewer(tmp, {"s04": True}, by=FIXER), [BUILDER, FIXER])
    check("sign: the one who fixed the slide cannot sign it either", rc == 2 and "never signs its own walk review" in lines[0]
          and signed(course)["rounds"] == 1, (rc, lines))
    rc, lines = wr.sign(course, 1, reviewer(tmp, {"s04": "stop 3: the axis has no bars yet"}), [BUILDER, FIXER])
    got = signed(course)
    check("round 2: still failing -> signed, the last round, the operator's choices printed",
          rc == 1 and got["rounds"] == 2 and got["slides"]["s04"]["round"] == 2 and got["slides"]["s01"]["round"] == 1
          and "round 2 of 2" in lines[0] and "that was the last round" in lines[0]
          and any("walk_review.py accept" in x and "walk_review.py reopen" in x for x in lines)
          and "  s04 - stop 3: the axis has no bars yet" in lines, (rc, lines))
    check("... and the review names everyone who built or fixed the module", got["builders"] == [BUILDER, FIXER] and got["built_by"] == BUILDER
          and "built by %s, %s" % (BUILDER, FIXER) in lines[0], got)
    ok, kind, msg = wr.verify(course, 1)
    check("... verify: failing, round 2 of 2, no third", not ok and kind == "failing" and "round 2 of 2, no third" in msg and "accept" in msg, msg)
    check("... open_fails lists what is left with slide and stop", wr.open_fails(course, 1) == ["s04 - stop 3: the axis has no bars yet"], wr.open_fails(course, 1))
    before = raw(course)
    rc, lines = wr.sign(course, 1, reviewer(tmp, {"s04": True}, by="another reviewer"))
    check("the last round's fail cannot be signed away by a new reviewer on the same deck", rc == 2 and "already has a verdict" in lines[0]
          and raw(course) == before and wr.verify(course, 1)[1] == "failing", (rc, lines))
    round2 = deck.read_text(encoding="utf-8")
    rebuilt(course, deck, DECK.replace("Four", "Four, fixed twice"))
    rc, lines = wr.sign(course, 1, reviewer(tmp, {"s04": True}))
    check("a third round is refused (exit 3) and nothing is written", rc == 3 and "no third" in lines[0] and "s04" in lines[0]
          and raw(course) == before, (rc, lines))
    ok, kind, msg = wr.verify(course, 1)
    rc, lines = wr.accept(course, 1, OPERATOR, "the axis is drawn in the next slide")
    check("accept: refused for a slide that changed after the review", rc == 2 and "changed after the review" in lines[0], (rc, lines))
    check("... and both it and verify name the way out of a module changed after its last round: reopen",
          "walk_review.py reopen" in lines[0] and kind == "stale" and "walk_review.py reopen" in msg, (lines, msg))
    deck.write_text(round2, encoding="utf-8")
    for name, why in ((BUILDER, "ok"), (FIXER, "ok"), (REVIEWER, "ok"), ("sonnet  SUBAGENT", "ok"), ("the Sonnet subagent (reviewer)", "ok"),
                      ("", "ok"), (OPERATOR, " ")):
        rc, lines = wr.accept(course, 1, name, why)
        check("accept: refused for %r / why %r (the operator's own act, with a reason)" % (name, why), rc == 2, (rc, lines))
    rc, lines = wr.accept(course, 1, OPERATOR, "the axis is drawn in the next slide", ["s02"])
    check("accept --slides: nothing open there -> refused", rc == 2 and "no open fail" in lines[0], (rc, lines))
    check("nothing accepted yet -> nothing to show at the upload", wr.accepted(course, 1) == [], wr.accepted(course, 1))
    rc, out = quiet("accept", course, "--module", "1", "--by", OPERATOR, "--why", "the axis is drawn in the next slide")
    a = signed(course)["slides"]["s04"].get("accepted") or {}
    check("accept: the operator lets the fail stand - recorded on the slide with who, when, why and what",
          rc == 0 and a.get("by") == OPERATOR and a.get("date") and a.get("why") == "the axis is drawn in the next slide"
          and a.get("fails") == ["stop 3: the axis has no bars yet"] and "s04 - stop 3: the axis has no bars yet" in out, (rc, out, a))
    check("... and how the command was run (here: not typed in a terminal)", a.get("how") == "run by a session or a script", a)
    check("... an agent's shell has a terminal for its input and is still not the operator typing: its environment says so",
          wr.how_run({"AI_AGENT": "an agent"}, tty=True) == "run by a session or a script"
          and wr.how_run({"CLAUDECODE": "1"}, tty=True) == "run by a session or a script"
          and wr.how_run({}, tty=True) == "typed in a terminal" and wr.how_run({}, tty=False) == "run by a session or a script")
    ok, kind, msg = wr.verify(course, 1)
    check("... and the module passes, saying whose accept it is", ok and "accepted by Aleksis Vejs" in msg and wr.open_fails(course, 1) == [], msg)
    let = wr.accepted(course, 1)
    check("... accepted() lists the fail with who, when, how and why - what an upload shows",
          len(let) == 1 and let[0].startswith("s04 - stop 3: the axis has no bars yet - accepted by Aleksis Vejs, ")
          and let[0].endswith("(run by a session or a script): the axis is drawn in the next slide"), let)
    rc0, _ = rebuilt(course, deck, DECK.replace("Four", "Four, changed after the accept"))
    ok, kind, msg = wr.verify(course, 1)
    check("... the accept was for what the reviewer saw: the slide changes -> stale again, and no longer listed as accepted",
          not ok and kind == "stale" and "s04" in msg and wr.accepted(course, 1) == [], msg)
    rc, lines = wr.sign(course, 1, reviewer(tmp, {"s04": True}))
    got = signed(course)
    check("... and its review is a new first round (nothing was open)", rc == 0 and got["rounds"] == 1 and "accepted" not in got["slides"]["s04"]
          and wr.verify(course, 1)[0], (rc, lines))

    course, deck = fixture(tmp, "renamed")
    wr.prepare(course, 1)
    wr.sign(course, 1, reviewer(tmp, ONE_FAIL), BUILDER)
    rebuilt(course, deck, DECK.replace("Four", "Four, fixed once"))
    wr.sign(course, 1, reviewer(tmp, {"s04": "stop 3: the axis has no bars yet"}))
    rebuilt(course, deck, DECK.replace("Four", "Four, fixed twice").replace("id=\"s04\"", "id=\"s09\""))
    before = raw(course)
    rc, lines = wr.sign(course, 1, reviewer(tmp, {"s09": True}))
    check("a failing slide renamed after the last round is still a third round: refused, the old fail named",
          rc == 3 and "s04 (no longer in the deck)" in lines[0] and raw(course) == before, (rc, lines))

    course, deck = fixture(tmp, "removed")
    wr.prepare(course, 1)
    wr.sign(course, 1, reviewer(tmp, ONE_FAIL), BUILDER)
    rc0, lines0 = rebuilt(course, deck, DECK.replace("<section class=\"slide\" id=\"s04\">Four</section>", ""))
    rc, lines = wr.sign(course, 1, reviewer(tmp, {k: True for k in ALL if k != "s04"}))
    got = signed(course)
    check("a failing slide removed as the fix: the others are reviewed in round 2, its verdict leaves the slides for the history",
          rc0 == 0 and "4 contact sheet(s)" in lines0[0] and rc == 0 and got["rounds"] == 2 and "s04" not in got["slides"]
          and [h["slide"] for h in got["history"]] == ["s04"] and wr.verify(course, 1)[0], (rc, lines, got.get("history")))

    course, deck = fixture(tmp, "reopen")
    wr.prepare(course, 1)
    wr.sign(course, 1, reviewer(tmp, ONE_FAIL), BUILDER)
    rebuilt(course, deck, DECK.replace("Four", "Four, fixed once"))
    wr.sign(course, 1, reviewer(tmp, {"s04": "stop 3: the axis has no bars yet"}))
    check("reopen: refused for the builder", wr.reopen(course, 1, BUILDER)[0] == 2)
    rc, out = quiet("reopen", course, "--module", "1", "--by", OPERATOR)
    got = signed(course)
    check("reopen: the operator starts the rounds again - recorded with who, how and which slides",
          rc == 0 and got["rounds"] == 0 and got["reopened"][0]["by"] == OPERATOR and got["reopened"][0]["slides"] == ["s04"]
          and got["reopened"][0]["how"] == "run by a session or a script", (rc, out, got.get("reopened")))
    rc0, lines0 = wr.prepare(course, 1, stale_only=True)
    rc, lines = wr.sign(course, 1, reviewer(tmp, {"s04": "stop 3: still no bars", "s05": True}, by="second reviewer"))
    got = signed(course)
    check("... the open slide may be reviewed again as it is (and only it): round 1",
          wr.to_review(course, 1) == [] and rc0 == 0 and "## Batch 1 - s04\n" in brief_of(course) and rc == 1 and got["rounds"] == 1
          and got["slides"]["s04"]["reviewed_by"] == "second reviewer" and got["slides"]["s05"]["reviewed_by"] == REVIEWER, (lines0, lines))
    rebuilt(course, deck, DECK.replace("Four", "Four, fixed twice"))
    rc, lines = wr.sign(course, 1, reviewer(tmp, {"s04": True}))
    got = signed(course)
    check("... the fix after it is round 2, and the reopening stays on record", rc == 0 and got["rounds"] == 2 and len(got["reopened"]) == 1
          and wr.verify(course, 1)[0], (rc, lines))


def older_part(tmp):
    """a walk and a review made by an older factory"""
    course, deck = fixture(tmp, "older")
    wj = Path(wr.walk_dir(course, 1), "walk.json")
    old_walk = {k: v for k, v in json.loads(wj.read_text(encoding="utf-8")).items() if k in ("viewport", "stops")}
    wj.write_text(json.dumps(dict(old_walk, slides={"s01": "x"}, deck_sha256="y")), encoding="utf-8")
    rc, lines = wr.prepare(course, 1)
    check("a walk that does not say which deck it was made of (an older factory's) -> prepare refused, build again",
          rc == 2 and "does not say which deck" in lines[0] and "build again" in lines[0], (rc, lines))

    course, deck = fixture(tmp, "legacy")
    wr.prepare(course, 1)
    old = {"deck_sha256": wr.deck_sha256(str(deck)), "reviewed_by": "Sonnet subagent", "date": "2026-11-09", "built_by": BUILDER,
           "slides": {"s%02d" % i: {"ok": True, "fails": [], "sha256": "0" * 64} for i in range(1, 5)}}
    Path(wr.review_file(course, 1)).write_text(json.dumps(old), encoding="utf-8")
    ok, kind, msg = wr.verify(course, 1)
    check("a review signed before the fingerprints still stands for its deck (s05 was not in it -> incomplete, not stale)",
          not ok and kind == "incomplete" and "s05" in msg, msg)
    rc, lines = wr.sign(course, 1, reviewer(tmp, {"s05": True}))
    got = signed(course)
    check("... and a later sign gives its kept slides their fingerprint", rc == 0 and wr.verify(course, 1)[0]
          and all(v.get("fingerprint") == wr.fingerprints(str(deck))[1][s] for s, v in got["slides"].items()), got)
    old["slides"]["s05"] = {"ok": True, "fails": []}
    Path(wr.review_file(course, 1)).write_text(json.dumps(old), encoding="utf-8")
    rebuilt(course, deck, DECK.replace("Two", "Two, changed"))
    ok, kind, msg = wr.verify(course, 1)
    check("... once its deck changes, every slide of it is stale (it recorded nothing to tell them apart)", not ok and kind == "stale" and "5 of 5" in msg, msg)
    rc, lines = wr.sign(course, 1, reviewer(tmp, {"s02": True}))
    ok, kind, msg = wr.verify(course, 1)
    check("... and signing one slide does not make the others current", rc == 0 and not ok and kind == "stale" and "4 of 5" in msg and "s02" not in msg, msg)


def sign_all(tmp, course, module):
    wr.prepare(course, module)
    return wr.sign(course, module, reviewer(tmp, ALL), BUILDER)[0]


def gates_part(tmp):
    """the final assessment's one name; fix.py check --kind walk; course_portal upload"""
    course, deck = fixture(tmp, "gates")
    final = add_module(course, 2, FINAL_DECK)
    add_module(course, 3)
    walk(course, 2)
    walk(course, 3)
    check("the final assessment is FINAL by name and by its folder's number: one review file, one walk folder, one deck",
          wr.canon(course, 2) == "final" and wr.canon(course, "final") == "final" and wr.canon(course, 3) == 3
          and os.path.basename(wr.review_file(course, 2)) == "FINAL_walk_review.json" and wr.review_file(course, 2) == wr.review_file(course, "final")
          and wr.walk_dir(course, 2) == wr.walk_dir(course, "final") and os.path.basename(wr.walk_dir(course, 2)) == "FINAL"
          and os.path.samefile(wr.deck_file(course, "final"), final) and os.path.samefile(wr.deck_file(course, 2), final),
          (wr.review_file(course, 2), wr.deck_file(course, "final")))
    sys.path.insert(0, str(HERE.parents[2] / "course-factory" / "scripts"))
    import course_portal
    os.environ["CF_FIX_NO_WALK_RUN"] = "1"
    problems = course_portal.walk_problems(course)
    check("course_portal upload: every built module with no walk review is a blocker - the final too, once",
          len(problems) == 3 and all("missing" in x for x in problems) and [x.split(" for ")[1].split(" ")[0] for x in problems] == ["M01", "FINAL", "M03"], problems)
    rc = sign_all(tmp, course, "final")
    ok, kind, msg = wr.verify(course, 2)
    check("the final signed under its name (the build, the workflow) is found by its folder's number (the portal, fix.py)",
          rc == 0 and ok and "FINAL" in msg, msg)
    sign_all(tmp, course, 1)
    sign_all(tmp, course, 3)
    check("... and nothing stops the upload once every module and the final are signed", course_portal.walk_problems(course) == [], course_portal.walk_problems(course))
    check("... with nothing accepted to show", course_portal.walk_accepted(course) == [], course_portal.walk_accepted(course))
    import fix
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = fix.cmd_check(course, "walk", "1", "s02")
    check("fix.py check --kind walk: passes on a signed module", code == 0 and "walk review passed" in buf.getvalue(), buf.getvalue())
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = fix.cmd_check(course, "walk", "2", None)
    check("... and on the final assessment, asked for by its folder's number", code == 0 and "walk review passed for FINAL" in buf.getvalue(), buf.getvalue())
    deck.write_text(DECK.replace("Two", "Two, fixed"), encoding="utf-8")
    walk(course)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = fix.cmd_check(course, "walk", "1", "s02")
    check("... and fails (with the brief for the reviewer) once a fix changed the deck", code == 1 and "walk review stale" in buf.getvalue()
          and "review_brief.md" in buf.getvalue(), buf.getvalue())
    check("... telling the fixer to name who built and fixed it, that the reviewer is someone else, and that there are two rounds",
          "--built-by" in buf.getvalue() and "never the session that made the fix" in buf.getvalue() and "Two rounds at most" in buf.getvalue()
          and "batch of up to 4 contact sheets" in buf.getvalue(), buf.getvalue())
    rc, lines = wr.sign(course, 1, reviewer(tmp, {"s02": "stop 1: the new line is cut"}), FIXER)
    problems = course_portal.walk_problems(course)
    check("course_portal upload: an open fail stops it, one line a module", rc == 1 and len(problems) == 1 and "\n" not in problems[0]
          and "open fails on s02" in problems[0], (lines, problems))
    wr.accept(course, 1, OPERATOR, "the line is read out by the instructor")
    check("... and the operator's accept lets it through", course_portal.walk_problems(course) == [], course_portal.walk_problems(course))
    let = course_portal.walk_accepted(course)
    check("... listed for the upload with its module: what goes up with a fail nobody fixed",
          len(let) == 1 and let[0].startswith("M01 s02 - stop 1: the new line is cut - accepted by Aleksis Vejs")
          and let[0].endswith("the line is read out by the instructor"), let)


def task_html(pid, words="Which gauge shows the tank pressure?"):
    """a self-check built as by default (the build sheet's feedback off: data-reveal="debrief"), the check with feedback on"""
    return ("<html><head><link rel=\"stylesheet\" href=\"../assets/deck.css\"></head><body%s><h1>%s</h1><p>%s</p>%s</body></html>"
            % (' data-reveal="debrief"' if pid == "self_check_1" else "", pid, words,
               "<img src=\"../assets/img/gauge.jpg\">" if pid == "self_check_1" else ""))


def add_tasks(course, module=1, pages=("self_check_1", "check"), sub="tasks"):
    """the module's task pages (and an answer key, which is no trainee's page) -> the module folder"""
    mdir = wr.module_dir(course, module)
    os.makedirs(os.path.join(mdir, sub), exist_ok=True)
    for pid in pages:
        Path(mdir, sub, pid + ".html").write_text(task_html(pid), encoding="utf-8")
    Path(mdir, sub, "check_answer_key.html").write_text("<html>the answers</html>", encoding="utf-8")
    Path(mdir, "assets", "img", "gauge.jpg").write_bytes(b"a gauge")
    return mdir


def walk_pages(course, module=1):
    """what the build's task walk leaves (review_sheets.mjs --walk-dir): per question a picture as asked at both sizes,
    answered wrong and answered right, the page's last screen after each run, and tasks.json with each page's fingerprint
    as its walk began. A page unchanged since it was walked keeps its pictures"""
    from PIL import Image
    wdir = wr.stamp_tasks(course, module)
    stamp = json.loads(Path(wdir, "tasks_stamp.json").read_text(encoding="utf-8"))["pages"]
    old = (wr.load_json(os.path.join(wdir, "tasks.json"), {}) or {}).get("pages") or {}
    pages = {}
    for n, (pid, e) in enumerate(stamp.items(), 1):
        if (old.get(pid) or {}).get("fingerprint") == e["fingerprint"]:
            pages[pid] = old[pid]
            continue
        os.makedirs(os.path.join(wdir, "tasks", pid), exist_ok=True)

        def shot(name, k):
            rel = "tasks/%s/%s.png" % (pid, name)
            Image.new("RGB", (480, 300), (60 * n, 50 * k, 90)).save(os.path.join(wdir, rel))
            return rel
        said = {"wrong": "Not quite - the tank gauge is the one on the dome.", "right": "Correct."}
        pages[pid] = dict(e, questions=[
            {"id": q, "ask": "%sWhich gauge shows the tank pressure?" % q[1:], "mech": "choice", "states": [
                {"state": s, "file": shot("%s_%d_%s" % (q, k, s.replace(" ", "_")), k), "said": said.get(s, "")}
                for k, s in enumerate(("asked", "asked 1024x768", "wrong", "right"), 1)]} for q in ("q1", "q2")],
            result=[{"state": s, "file": shot("result_" + s.replace(" ", "_"), k)}
                    for k, s in enumerate(("all wrong", "all right"), 1)])
    Path(wdir, "tasks.json").write_text(json.dumps({"viewport": "1280x800", "pages": pages}), encoding="utf-8")


UNITS = ["%s.%s" % (p, u) for p in ("check", "self_check_1") for u in ("q1", "q2", "result")]
TAP = "picture 3: the tap area for the vent mast covers only its cap"


def fix_check(course, module, slides):
    import fix
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = fix.cmd_check(course, "walk", module, slides)
    return code, buf.getvalue()


def tasks_part(tmp):
    """the trainee's task pages: walked, reviewed and gated like the deck's slides"""
    course, deck = fixture(tmp, "tasks")
    mdir = add_tasks(course)
    page = Path(mdir, "tasks", "check.html")
    pages = wr.task_pages(mdir)
    check("task pages: every page of tasks\\ is one, never an answer key - each with its own fingerprint",
          list(pages) == ["check", "self_check_1"] and pages["check"]["file"] == "tasks/check.html"
          and pages["check"]["fingerprint"] and pages["check"]["fingerprint"] != pages["self_check_1"]["fingerprint"], pages)
    check("... named by its id, its file or the file's name; a slide is no task page",
          wr.page_named(pages, "check") == "check" and wr.page_named(pages, "tasks/check.html") == "check"
          and wr.page_named(pages, "tasks\\self_check_1.html") == "self_check_1" and wr.page_named(pages, "check.html") == "check"
          and wr.page_named(pages, "s02") is None)
    check("... a fix reaches the task pages when it names none of its slides, a page or one of its questions",
          wr.touches_tasks(pages, None) and wr.touches_tasks(pages, ["s02", "check.q2"]) and wr.touches_tasks(pages, ["self_check_1.html"])
          and not wr.touches_tasks(pages, ["s02", "s03"]) and not wr.touches_tasks({}, None))
    sys.path.insert(0, str(HERE.parents[2] / "course-factory" / "scripts"))
    import course_portal
    os.environ["CF_FIX_NO_WALK_RUN"] = "1"

    # the deck walked and reviewed, the task pages never walked
    rc, lines = wr.prepare(course, 1)
    check("prepare: a task page the walk has no picture of is named - no reviewer can pass it",
          rc == 0 and any("has no picture of task page check, task page self_check_1" in x for x in lines), lines)
    rc, lines = wr.sign(course, 1, reviewer(tmp, ALL), BUILDER)
    ok, kind, msg = wr.verify(course, 1)
    check("verify: a deck reviewed whole is not a module reviewed - its task pages were never walked",
          rc == 0 and not ok and kind == "incomplete" and "not reviewed: task page check, task page self_check_1" in msg
          and "no picture" in msg, (lines, msg))
    problems = course_portal.walk_problems(course)
    check("... and the upload is refused for it", len(problems) == 1 and "incomplete for M01" in problems[0]
          and "task page check" in problems[0], problems)
    rc, lines = wr.sign(course, 1, reviewer(tmp, {"check": True}))
    check("... a page with no picture cannot be signed", rc == 2 and "no contact sheet was made for task page check" in lines[0], lines)

    # a build that failed walked the deck only: the walk judge's prepare walks the task pages itself, so round 1 judges them
    called, real = [], wr.walk_tasks
    wr.walk_tasks = lambda c, m: (called.append(m), walk_pages(c), (0, ""))[2]
    os.environ.pop("CF_FIX_NO_WALK_RUN")
    try:
        rc, lines = wr.prepare(course, 1, stale_only=True)
        rc_s, lines_s = wr.prepare(course, 1, ["s02"])
    finally:
        wr.walk_tasks = real
        os.environ["CF_FIX_NO_WALK_RUN"] = "1"
    check("prepare: task pages with no picture are walked first - the brief holds their questions, none is left without one",
          called == [1] and rc == 0 and "6 task-page question(s) and last screen(s)" in lines[0]
          and not any("no picture" in x for x in lines), (called, lines))
    check("... once: walked as they are now, they are not walked again; a prepare of slides alone walks no task page",
          called == [1] and rc_s == 0 and "task-page" not in lines_s[0], (called, lines_s))

    # walked: one unit per question and per last screen
    walk_pages(course)
    ok, kind, msg = wr.verify(course, 1)
    check("... walked and not reviewed is not done either", not ok and kind == "incomplete"
          and "not reviewed: task page check, task page self_check_1" in msg and "no picture" not in msg, msg)
    check("... nor is the upload", len(course_portal.walk_problems(course)) == 1, course_portal.walk_problems(course))
    rc, lines = wr.prepare(course, 1)
    wdir = wr.walk_dir(course, 1)
    brief = brief_of(course)
    check("prepare: one contact sheet per slide, per question and per last screen",
          rc == 0 and "(5 slide(s), 6 task-page question(s) and last screen(s))" in lines[0] and "4 batch(es)" in lines[1]
          and all(os.path.isfile(os.path.join(wdir, "sheets", u + ".png")) for u in UNITS + list(ALL)), lines)
    from PIL import Image
    wide = Image.open(os.path.join(wdir, "sheets", "check.q1.png")).size
    last = Image.open(os.path.join(wdir, "sheets", "check.result.png")).size
    check("... a question's sheet holds its four pictures, a last screen's its two", wide[1] > last[1] * 1.5, (wide, last))
    sheet = Image.open(os.path.join(wdir, "sheets", "check.q1.png")).convert("RGB")
    first = Image.open(os.path.join(wdir, "tasks", "check", "q1_1_asked.png")).convert("RGB")
    check("... a picture's number stands in a band above it, not on it: the screen's own first words stay readable",
          sheet.getpixel((10, 10)) == (10, 36, 99) and sheet.getpixel((9, 39)) == first.getpixel((1, 1))
          and sheet.getpixel((30, 50)) == first.getpixel((22, 12)),
          (sheet.getpixel((10, 10)), sheet.getpixel((9, 39)), first.getpixel((1, 1))))
    check("the brief: the task rubric beside the deck's, each of its points",
          "Judge by this RUBRIC" in brief and "Judge by this TASK RUBRIC" in brief and all(r in brief for r in wr.TASK_RUBRIC)
          and all(r in brief for r in wr.RUBRIC), brief[:1500])
    check("... each page's questions in order, once", brief.count("## The task pages of this review") == 1
          and "- `tasks/check.html` (check, feedback on): q1 1. Which gauge shows the tank pressure?; q2 2. Which gauge" in brief, brief)
    check("... the rubric follows each page's build sheet: with feedback off a right answer left unmarked after a wrong one is "
          "no fail (one attempt, explained in the debrief); with feedback on it is still judged",
          wr.DEBRIEF in brief and "- `tasks/self_check_1.html` (self_check_1, feedback off): " in brief
          and "Task page: tasks/self_check_1.html, feedback off - its last screen" in brief
          and "Task page: tasks/check.html, feedback on - question q2" in brief and "on a page with feedback ON only" in wr.TASK_RUBRIC[2]
          and "never a fail" in wr.DEBRIEF and "judged on point 3 in full" in wr.DEBRIEF, brief)
    check("... each question with its page, its kind and what the screen said in each picture",
          "### check.q2 - 2. Which gauge shows the tank pressure?" in brief and "Task page: tasks/check.html, feedback on - question q2 (choice)" in brief
          and "- picture 3: wrong - the screen says: \"Not quite - the tank gauge" in brief and "- picture 4: right" in brief
          and "### self_check_1.result - the last screen" in brief and "Task page: tasks/self_check_1.html, feedback off - its last screen" in brief, brief)
    check("... and the name a verdict goes under", "exactly as its heading has it (\"check.q1\")" in brief
          and "## Batch 3 - check.q1, check.q2, check.result, self_check_1.q1" in brief, brief)
    rc, lines = wr.sign(course, 1, reviewer(tmp, dict({u: True for u in UNITS}, **{"check.q2": TAP})))
    ok, kind, msg = wr.verify(course, 1)
    got = signed(course)
    check("sign: one failing question fails the module - in the round of the deck's review, signed for its page's fingerprint",
          rc == 1 and got["rounds"] == 1 and not ok and kind == "failing" and "open fails on check.q2" in msg
          and got["slides"]["check.q2"]["fingerprint"] == pages["check"]["fingerprint"] and got["tasks"]
          and got["slides"]["self_check_1.result"]["ok"] is True, (lines, msg))
    check("... and says what was reviewed in its own words", "- 6 task-page question(s) and last screen(s) reviewed now" in lines[0], lines[0])
    check("... and stops the upload", len(course_portal.walk_problems(course)) == 1 and "open fails on check.q2" in course_portal.walk_problems(course)[0])
    code, out = fix_check(course, "1", "self_check_1")
    check("fix.py check --kind walk --slides <a task page>: only that page must be covered", code == 0 and "walk review passed" in out, out)
    code, out = fix_check(course, "1", "s02,tasks/check.html")
    check("... a page named by its file: its open fail stops the check, with the fail", code == 1 and "open fails on check.q2" in out
          and "check.q2 - " + TAP in out, out)

    # a fix to one task page
    page.write_text(task_html("check", "Which gauge shows the vent mast's pressure?"), encoding="utf-8")
    ok, kind, msg = wr.verify(course, 1)
    check("a task page changed: its questions and its last screen are stale - no other page, no slide",
          not ok and kind == "stale" and "3 of 11" in msg and "changed after the review: task page check;" in msg
          and "self_check_1" not in msg, msg)
    rc, lines = wr.prepare(course, 1, stale_only=True)
    check("... and pictures of the page as it was are not shown to a reviewer", rc == 2 and "task page check" in lines[0]
          and "older" in lines[0], lines)
    walk_pages(course)
    rc, lines = wr.prepare(course, 1, stale_only=True)
    brief = brief_of(course)
    check("prepare --stale: only the changed page's questions and last screen, with what failed last time",
          rc == 0 and "(0 slide(s), 3 task-page question(s) and last screen(s))" in lines[0] and "task page check" in lines[0]
          and "### check.q1" in brief and "### check.result" in brief and "### self_check_1" not in brief and "### s0" not in brief
          and "Judge by this RUBRIC" not in brief and "Failed in the last review - say for each whether it is fixed now: " + TAP in brief, (lines, brief))
    rc, lines = wr.sign(course, 1, reviewer(tmp, {"self_check_1.q1": True}))
    check("... a question of the page that did not change keeps the verdict it has", rc == 2 and "already has a verdict" in lines[0], lines)
    rc, lines = wr.sign(course, 1, reviewer(tmp, {"check.q1": True, "check.q2": TAP, "check.result": True}), FIXER)
    check("round 2 after the fix: a question still failing is the last round - the operator's choice",
          rc == 1 and signed(course)["rounds"] == 2 and "that was the last round" in lines[0] and "accept" in lines[-1], lines)
    second = page.read_text(encoding="utf-8")
    page.write_text(task_html("check", "A third try"), encoding="utf-8")
    walk_pages(course)
    wr.prepare(course, 1, stale_only=True)
    rc, lines = wr.sign(course, 1, reviewer(tmp, {"check.q1": True, "check.q2": True, "check.result": True}))
    check("... and a third review of a task page is refused like a slide's", rc == 3 and "Still failing: check.q2" in lines[0], lines)
    page.write_text(second, encoding="utf-8")
    walk_pages(course)
    rc, lines = wr.accept(course, 1, OPERATOR, "the mast's cap is what a trainee taps", ["tasks/check.html"])
    ok, kind, msg = wr.verify(course, 1)
    let = course_portal.walk_accepted(course)
    check("accept: the operator lets a task page's fail stand - the module passes and the upload goes",
          rc == 0 and ok and "accepted by Aleksis Vejs" in msg and course_portal.walk_problems(course) == [], (lines, msg))
    check("... on the operator's list at the upload, with its page and question",
          len(let) == 1 and let[0].startswith("M01 check.q2 - " + TAP + " - accepted by Aleksis Vejs")
          and let[0].endswith("the mast's cap is what a trainee taps") and wr.accepted(course, 1)[0].startswith("check.q2 - "), let)

    # what a page loads is part of it; the deck and the pages do not make each other stale
    Path(mdir, "assets", "img", "gauge.jpg").write_bytes(b"another gauge")
    ok, kind, msg = wr.verify(course, 1)
    check("a picture one task page shows replaced: that page is stale, no other page and no slide",
          not ok and kind == "stale" and "3 of 11" in msg and "changed after the review: task page self_check_1;" in msg, msg)
    Path(mdir, "assets", "img", "gauge.jpg").write_bytes(b"a gauge")
    deck.write_text(DECK.replace("Two", "Two, changed"), encoding="utf-8")
    ok, kind, msg = wr.verify(course, 1)
    check("a slide changed: the slide is stale, no task page", not ok and kind == "stale" and "1 of 11" in msg and "s02" in msg
          and "task page" not in msg and len(course_portal.walk_accepted(course)) == 1, msg)

    # the final assessment's variants are task pages of the final
    add_module(course, 2, FINAL_DECK)
    add_tasks(course, 2, ("final",), "assessment")
    walk(course, 2)
    rc = sign_all(tmp, course, "final")
    ok, kind, msg = wr.verify(course, "final")
    check("the final assessment: its page in assessment\\ is reviewed too - the final's deck alone is not the final",
          rc == 0 and list(wr.task_pages(wr.module_dir(course, "final"))) == ["final"] and not ok and kind == "incomplete"
          and "FINAL" in msg and "task page final" in msg, msg)
    walk_pages(course, "final")

    # 2.125.0 - a walk that broke off: tasks.json names the questions it did not show whole, and they have no picture
    tj = Path(wr.walk_dir(course, "final"), "tasks.json")
    whole = json.loads(tj.read_text(encoding="utf-8"))
    cut = json.loads(json.dumps(whole))
    cut["pages"]["final"]["questions"] = cut["pages"]["final"]["questions"][:1]
    cut["pages"]["final"]["ids"] = ["q1", "q2", "q3"]
    cut["pages"]["final"]["missed"] = [{"id": "q2", "why": "never shown"}]
    tj.write_text(json.dumps(cut), encoding="utf-8")
    rc, lines = wr.prepare(course, "final", stale_only=True)
    check("a walk that broke off: the questions it never showed are named (its own list, and the page's ids) - no "
          "reviewer can pass them", any("has no picture of final.q2, final.q3" in x for x in lines), lines)
    rc, lines = wr.sign(course, "final", reviewer(tmp, {"final.q1": True, "final.result": True}))
    ok, kind, msg = wr.verify(course, "final")
    check("... and the questions it did show, signed, are not the page reviewed",
          rc == 0 and not ok and kind == "incomplete" and "final.q2, final.q3" in msg and "no picture" in msg, (lines, msg))
    rc, lines = wr.sign(course, "final", reviewer(tmp, {"final.q2": True}))
    check("... a verdict on a question with no picture is refused", rc == 2 and "final.q2" in " ".join(lines), lines)
    tj.write_text(json.dumps(whole), encoding="utf-8")
    wr.prepare(course, "final", stale_only=True)
    rc, lines = wr.sign(course, "final", reviewer(tmp, {"final.q2": True}))
    check("... and passes once its questions and last screen are signed", rc == 0 and wr.verify(course, 2)[0], (lines, wr.verify(course, 2)))

    # 2.125.0 - a stop the fit walk could not take a picture of: its slide has no picture
    wj = Path(wr.walk_dir(course, "final"), "walk.json")
    kept = wj.read_text(encoding="utf-8")
    shot = json.loads(kept)
    sid = shot["stops"][0]["slide"]
    shot["stops"].append({"slide": sid, "k": 9, "file": "", "lost": "the browser gave no picture"})
    wj.write_text(json.dumps(shot), encoding="utf-8")
    d = wr.Deck(course, "final")
    rc, lines = wr.prepare(course, "final")
    check("a stop with no picture: its slide is not walked - prepare names it, and a new verdict on it has no sheet",
          d.unshot == [sid] and sid not in d.stops and sid in d.slides()
          and any("has no picture of" in x and sid in x for x in lines), (d.unshot, lines))
    wj.write_text(kept, encoding="utf-8")


def main():
    try:
        import PIL  # noqa: F401
    except ImportError:
        print("SKIP - Pillow is not installed")
        return 0
    tmp = tempfile.mkdtemp(prefix="walk_review_")
    try:
        first_part(tmp)
        every_slide_part(tmp)
        rounds_part(tmp)
        older_part(tmp)
        gates_part(tmp)
        tasks_part(tmp)
    finally:
        os.environ.pop("CF_FIX_NO_WALK_RUN", None)
        shutil.rmtree(tmp, ignore_errors=True)
    print("\n%d passed, %d failed" % (len(PASS), len(FAIL)))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
