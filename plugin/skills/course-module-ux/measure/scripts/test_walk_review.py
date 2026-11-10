# -*- coding: utf-8 -*-
"""test_walk_review - "walk it like a trainee": prepare / sign / verify / accept / reopen on a fixture deck, and the gates.

    python test_walk_review.py

Pinned:
  * prepare makes one contact sheet per walked slide and review_brief.md (batches of at most 4 slides, each slide's stop texts,
    its figure's why / why_text from the build sheet, the rubric); --slides limits it; --stale shows only the slides with no
    verdict for what they show now, with what failed last time;
  * sign writes MNN_walk_review.json: who built, who reviewed, the round, and per slide the verdict with the slide's hash;
    slides not returned keep their old result; the builder's own signature and a missing --built-by are refused;
  * one slide, one hash: a fix to one slide makes that slide stale and no other; a change outside the slides makes all stale;
    a build timestamp or comment change is NOT a change; a review signed before the per-slide hashes still stands for its deck;
  * two rounds at most: a third sign is refused (exit 3); accept (the operator, never the builder or the reviewer, with a
    reason) lets the module pass and is void once the slide changes; reopen starts the rounds again;
  * pictures older than the deck are refused (fit_gate.py writes the slide hashes beside the walk);
  * the gates: build_module.py (also in a --no-course-pages build), fix.py check --kind walk, course_portal upload.
No browser needed: the walk's stops are fixture PNGs.
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
DECK = ("<!-- built 2026-11-09T10:11:12 -->\n<html><head><style>.slide{color:navy}</style></head><body>"
        + "".join("<section class=\"slide\" id=\"s%02d\">%s</section>" % (i, w) for i, w in enumerate(WORDS, 1))
        + "<script>var deck = 1</script></body></html>")
BUILDER, REVIEWER, OPERATOR = "build:1 (workflow builder)", "Sonnet subagent", "Aleksis Vejs"


def fixture(tmp, name="course", hashes=False):
    from PIL import Image
    course = os.path.join(tmp, name)
    mdir = os.path.join(course, "modules", "module01")
    os.makedirs(os.path.join(mdir, "presentation"))
    deck = Path(mdir, "presentation", "index.html")
    deck.write_text(DECK, encoding="utf-8")
    wdir = os.path.join(course, "working_claude", "_build", "walk", "M01")
    os.makedirs(wdir)
    stops = []
    for i in range(1, 6):
        for k in (1, 2, 3):
            fname = "s%02d_k%d.png" % (i, k)
            Image.new("RGB", (480, 300), (30 * i, 60 * k, 120)).save(os.path.join(wdir, fname))
            stops.append({"slide": "s%02d" % i, "k": k, "file": fname, "title": "Slide %d" % i, "lit": ["Line %d" % k],
                          "ask": [], "reveal": ["The answer"] if k == 3 else [], "fig": ":1:2"})
    walk = {"viewport": "1280x800", "stops": stops}
    if hashes:
        walk.update(slides=wr.slide_hashes(str(deck)), deck_sha256=wr.deck_sha256(str(deck)))
    Path(wdir, "walk.json").write_text(json.dumps(walk), encoding="utf-8")
    sdir = os.path.join(course, "working_claude", "script")
    os.makedirs(sdir)
    Path(sdir, "M01.build.json").write_text(json.dumps({"screens": {
        "s02": {"figure": "s02.kit2d.json", "why": "sequence", "why_text": "The trainee sees the valve close."}}}), encoding="utf-8")
    return course, deck


def reviewer(tmp, slides, by=REVIEWER):
    """a reviewer JSON file: {"s04": "stop 3: ..."} is a fail, {"s01": True} a pass"""
    p = os.path.join(tmp, "reviewer.json")
    Path(p).write_text(json.dumps({"reviewed_by": by, "slides": {
        s: {"ok": v is True, "fails": [] if v is True else [v]} for s, v in slides.items()}}), encoding="utf-8")
    return p


def signed(course):
    return json.loads(Path(wr.review_file(course, 1)).read_text(encoding="utf-8"))


def quiet(*argv):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = wr.main(list(argv))
    return rc, buf.getvalue()


def first_part(tmp):
    """prepare, sign, verify - one review, signed in batches"""
    course, deck = fixture(tmp)
    rc, lines = wr.prepare(course, 1)
    wdir = wr.walk_dir(course, 1)
    sheets = sorted(os.listdir(os.path.join(wdir, "sheets")))
    brief = Path(wdir, "review_brief.md").read_text(encoding="utf-8")
    check("prepare: one contact sheet per slide", rc == 0 and sheets == ["s%02d.png" % i for i in range(1, 6)], (rc, lines, sheets))
    from PIL import Image
    im = Image.open(os.path.join(wdir, "sheets", "s01.png"))
    check("... all its stops in a numbered grid (3 stops, 480 px each, side by side)", im.width >= 3 * 480 and im.height >= 300, im.size)
    check("... the brief lists the sheets in batches of at most 4 slides", "## Batch 1 - s01, s02, s03, s04" in brief and "## Batch 2 - s05" in brief)
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
    rc, _ = wr.prepare(course, 1, ["s02", "s03"])
    check("prepare --slides: only those slides' sheets are in the brief", rc == 0 and "## Batch 1 - s02, s03" in Path(wdir, "review_brief.md").read_text(encoding="utf-8")
          and "s01" not in Path(wdir, "review_brief.md").read_text(encoding="utf-8").split("## Batch")[1], rc)
    wr.prepare(course, 1)

    ok, kind, msg = wr.verify(course, 1)
    check("verify: no review yet -> missing, exit 1", not ok and kind == "missing" and quiet("verify", course, "--module", "1")[0] == 1, msg)
    rv = reviewer(tmp, {"s01": True, "s02": True, "s03": True, "s04": "stop 3: the chart is still an empty axis"})
    rc, lines = wr.sign(course, 1, rv)
    check("sign: refused until it is told who built the module", rc == 2 and "--built-by" in lines[0] and not os.path.isfile(wr.review_file(course, 1)), (rc, lines))
    for own in (BUILDER, "BUILD:1 - workflow builder"):
        rc, lines = wr.sign(course, 1, reviewer(tmp, {"s01": True}, by=own), BUILDER)
        check("sign: the builder's own signature is refused (%s)" % own, rc == 2 and "never signs its own walk review" in lines[0]
              and not os.path.isfile(wr.review_file(course, 1)), (rc, lines))
    rv = reviewer(tmp, {"s01": True, "s02": True, "s03": True, "s04": "stop 3: the chart is still an empty axis"})
    rc, lines = wr.sign(course, 1, rv, BUILDER)
    got = signed(course)
    check("sign: writes MNN_walk_review.json with the deck hash, reviewer, date and slides",
          got["reviewed_by"] == "Sonnet subagent" and len(got["deck_sha256"]) == 64 and got["date"] and got["slides"]["s04"]["ok"] is False
          and rc == 1 and "OPEN FAILS on s04" in lines[0], (rc, lines, got))
    check("... who built it, the round, and on every slide its own hash, reviewer and round",
          got["built_by"] == BUILDER and got["rounds"] == 1 and "round 1 of 2" in lines[0]
          and all(len(v["sha256"]) == 64 and v["reviewed_by"] == REVIEWER and v["round"] == 1 for v in got["slides"].values())
          and len({v["sha256"] for v in got["slides"].values()}) == 4, (lines, got))
    check("... and lists every open fail with its slide and stop", "  s04 - stop 3: the chart is still an empty axis" in lines, lines)
    ok, kind, msg = wr.verify(course, 1)
    check("verify: s05 not reviewed -> incomplete; an open fail on s04 is reported once reviewed", not ok and kind == "incomplete" and "s05" in msg, msg)
    rc, _ = wr.sign(course, 1, reviewer(tmp, {"s05": True}))
    ok, kind, msg = wr.verify(course, 1)
    check("... a second sign keeps the slides the reviewer did not return (and the builder's name); s04 still fails -> failing",
          not ok and kind == "failing" and "s04" in msg and "round 1 of 2" in msg and signed(course)["built_by"] == BUILDER, msg)
    check("... another batch of the same review is the same round", signed(course)["rounds"] == 1 and rc == 1)
    rc, out = quiet("verify", course, "--module", "1")
    check("verify prints the open fails with slide and stop", rc == 1 and "NOT DONE: walk review failing" in out and "  s04 - stop 3: the chart" in out, out)
    rc, _ = wr.sign(course, 1, reviewer(tmp, {"s04": True}))
    ok, kind, msg = wr.verify(course, 1)
    check("every fail fixed and re-reviewed -> verify passes, exit 0", ok and rc == 0 and quiet("verify", course, "--module", "1")[0] == 0, msg)
    rc, lines = wr.prepare(course, 1, stale_only=True)
    check("prepare --stale: nothing to review once every slide has a verdict for what it shows now", rc == 0 and "nothing to review" in lines[0], lines)

    deck.write_text(DECK.replace("2026-11-09T10:11:12", "2026-11-10T08:00:00").replace("<!-- built", "<!-- rebuilt"), encoding="utf-8")
    check("a rebuild that changes only the build timestamp / comments is the same deck - still verified", wr.verify(course, 1)[0])
    deck.write_text(DECK.replace("Two", "Two, changed"), encoding="utf-8")
    ok, kind, msg = wr.verify(course, 1)
    check("the deck changed after the review -> stale, exit 1", not ok and kind == "stale" and quiet("verify", course, "--module", "1")[0] == 1, msg)
    check("... ONE slide changed -> that slide is stale and no other", "1 of 5 slide(s)" in msg and "s02" in msg and "s01" not in msg and "s03" not in msg
          and wr.to_review(course, 1) == ["s02"], msg)
    rc, lines = wr.prepare(course, 1, stale_only=True)
    brief = Path(wr.walk_dir(course, 1), "review_brief.md").read_text(encoding="utf-8")
    check("... and prepare --stale gives the reviewer that slide alone", rc == 0 and "## Batch 1 - s02\n" in brief and "### s01" not in brief
          and "s02" in lines[0], (lines, brief[-500:]))
    deck.write_text(DECK.replace("color:navy", "color:red"), encoding="utf-8")
    ok, kind, msg = wr.verify(course, 1)
    check("a change outside the slides (a style, a script) makes every slide stale", not ok and kind == "stale" and "5 of 5 slide(s)" in msg, msg)
    check("sign refuses a reviewer JSON with no \"ok\" or no reviewer", wr.sign(course, 1, os.path.join(tmp, "nope.json"), BUILDER)[0] == 2
          and wr.sign(course, 1, reviewer(tmp, {"s01": True}, by=""), BUILDER)[0] == 2)
    h1, h2 = wr.slide_hashes(str(deck)), None
    deck.write_text(DECK.replace("color:navy", "color:red").replace("Four", "Four, fixed"), encoding="utf-8")
    h2 = wr.slide_hashes(str(deck))
    check("slide_hashes: one hash per <section id>, and only the changed slide's hash moves",
          sorted(h1) == ["s%02d" % i for i in range(1, 6)] and [s for s in h1 if h1[s] != h2[s]] == ["s04"], (h1, h2))
    return course, deck


def rounds_part(tmp):
    """two rounds at most, the operator's accept, reopen"""
    course, deck = fixture(tmp, "rounds")
    everything = {"s01": True, "s02": True, "s03": True, "s04": "stop 3: the chart is still an empty axis", "s05": True}
    rc, _ = wr.sign(course, 1, reviewer(tmp, everything), BUILDER)
    deck.write_text(DECK.replace("Four", "Four, fixed once"), encoding="utf-8")
    rc0, lines0 = wr.prepare(course, 1, stale_only=True)
    brief = Path(wr.walk_dir(course, 1), "review_brief.md").read_text(encoding="utf-8")
    check("round 2 starts with the fixed slide alone, and the brief says what failed last time",
          rc == 1 and rc0 == 0 and "## Batch 1 - s04\n" in brief and "Failed in the last review" in brief
          and "stop 3: the chart is still an empty axis" in brief.split("### s04")[1], (lines0, brief[-600:]))
    rc, lines = wr.sign(course, 1, reviewer(tmp, {"s04": "stop 3: the axis has no bars yet"}))
    got = signed(course)
    check("round 2: still failing -> signed, the last round, the operator's choices printed",
          rc == 1 and got["rounds"] == 2 and got["slides"]["s04"]["round"] == 2 and got["slides"]["s01"]["round"] == 1
          and "round 2 of 2" in lines[0] and "that was the last round" in lines[0]
          and any("walk_review.py accept" in x and "walk_review.py reopen" in x for x in lines)
          and "  s04 - stop 3: the axis has no bars yet" in lines, (rc, lines))
    ok, kind, msg = wr.verify(course, 1)
    check("... verify: failing, round 2 of 2, no third", not ok and kind == "failing" and "round 2 of 2, no third" in msg and "accept" in msg, msg)
    check("... open_fails lists what is left with slide and stop", wr.open_fails(course, 1) == ["s04 - stop 3: the axis has no bars yet"], wr.open_fails(course, 1))
    round2 = deck.read_text(encoding="utf-8")
    deck.write_text(DECK.replace("Four", "Four, fixed twice"), encoding="utf-8")
    before = Path(wr.review_file(course, 1)).read_text(encoding="utf-8")
    rc, lines = wr.sign(course, 1, reviewer(tmp, {"s04": True}))
    check("a third round is refused (exit 3) and nothing is written", rc == 3 and "no third" in lines[0] and "s04" in lines[0]
          and Path(wr.review_file(course, 1)).read_text(encoding="utf-8") == before, (rc, lines))
    rc, lines = wr.accept(course, 1, OPERATOR, "the axis is drawn in the next slide")
    check("accept: refused for a slide that changed after the review", rc == 2 and "changed after the review" in lines[0], (rc, lines))
    deck.write_text(round2, encoding="utf-8")
    for name, why in ((BUILDER, "ok"), (REVIEWER, "ok"), ("sonnet  SUBAGENT", "ok"), ("", "ok"), (OPERATOR, " ")):
        rc, lines = wr.accept(course, 1, name, why)
        check("accept: refused for %r / why %r (the operator's own act, with a reason)" % (name, why), rc == 2, (rc, lines))
    rc, lines = wr.accept(course, 1, OPERATOR, "the axis is drawn in the next slide", ["s02"])
    check("accept --slides: nothing open there -> refused", rc == 2 and "no open fail" in lines[0], (rc, lines))
    rc, out = quiet("accept", course, "--module", "1", "--by", OPERATOR, "--why", "the axis is drawn in the next slide")
    a = signed(course)["slides"]["s04"].get("accepted") or {}
    check("accept: the operator lets the fail stand - recorded on the slide with who, when, why and what",
          rc == 0 and a.get("by") == OPERATOR and a.get("date") and a.get("why") == "the axis is drawn in the next slide"
          and a.get("fails") == ["stop 3: the axis has no bars yet"] and "s04 - stop 3: the axis has no bars yet" in out, (rc, out, a))
    ok, kind, msg = wr.verify(course, 1)
    check("... and the module passes, saying whose accept it is", ok and "accepted by Aleksis Vejs" in msg and wr.open_fails(course, 1) == [], msg)
    deck.write_text(DECK.replace("Four", "Four, changed after the accept"), encoding="utf-8")
    ok, kind, msg = wr.verify(course, 1)
    check("... the accept was for what the reviewer saw: the slide changes -> stale again", not ok and kind == "stale" and "s04" in msg, msg)
    rc, lines = wr.sign(course, 1, reviewer(tmp, {"s04": True}))
    got = signed(course)
    check("... and its review is a new first round (nothing was open)", rc == 0 and got["rounds"] == 1 and "accepted" not in got["slides"]["s04"]
          and wr.verify(course, 1)[0], (rc, lines))

    course, deck = fixture(tmp, "reopen")
    wr.sign(course, 1, reviewer(tmp, everything), BUILDER)
    deck.write_text(DECK.replace("Four", "Four, fixed once"), encoding="utf-8")
    wr.sign(course, 1, reviewer(tmp, {"s04": "stop 3: the axis has no bars yet"}))
    check("reopen: refused for the builder", wr.reopen(course, 1, BUILDER)[0] == 2)
    rc, out = quiet("reopen", course, "--module", "1", "--by", OPERATOR)
    got = signed(course)
    check("reopen: the operator starts the rounds again - recorded", rc == 0 and got["rounds"] == 0 and got["reopened"][0]["by"] == OPERATOR, (rc, out))
    deck.write_text(DECK.replace("Four", "Four, fixed twice"), encoding="utf-8")
    rc, lines = wr.sign(course, 1, reviewer(tmp, {"s04": True}))
    got = signed(course)
    check("... the next review is round 1, and the reopening stays on record", rc == 0 and got["rounds"] == 1 and len(got["reopened"]) == 1 and wr.verify(course, 1)[0], (rc, lines))


def older_part(tmp):
    """pictures older than the deck; a review signed before the per-slide hashes"""
    course, deck = fixture(tmp, "older", hashes=True)
    check("a walk with slide hashes that match the deck: prepare and sign as usual",
          wr.prepare(course, 1)[0] == 0 and wr.sign(course, 1, reviewer(tmp, {"s%02d" % i: True for i in range(1, 6)}), BUILDER)[0] == 0)
    deck.write_text(DECK.replace("Three", "Three, changed"), encoding="utf-8")
    rc, lines = wr.prepare(course, 1, stale_only=True)
    check("prepare: the pictures are of an older slide -> refused, build again", rc == 2 and "walked before the deck changed" in lines[0] and "s03" in lines[0], (rc, lines))
    rc, lines = wr.sign(course, 1, reviewer(tmp, {"s03": True}))
    check("sign: a verdict on pictures of an older slide is refused", rc == 2 and "walked before the deck changed" in lines[0], (rc, lines))
    rc, lines = wr.sign(course, 1, reviewer(tmp, {"s01": True}))
    check("... a slide that did not change can still be signed", rc == 0, (rc, lines))

    course, deck = fixture(tmp, "legacy")
    old = {"deck_sha256": wr.deck_sha256(str(deck)), "reviewed_by": "Sonnet subagent", "date": "2026-11-09",
           "slides": {"s%02d" % i: {"ok": True, "fails": []} for i in range(1, 6)}}
    Path(wr.review_file(course, 1)).write_text(json.dumps(old), encoding="utf-8")
    check("a review signed before the per-slide hashes still stands for its deck", wr.verify(course, 1)[0], wr.verify(course, 1))
    rc, lines = wr.sign(course, 1, reviewer(tmp, {"s01": True}), BUILDER)
    got = signed(course)
    check("... and a later sign gives its kept slides their own hash", rc == 0 and all(len(v.get("sha256", "")) == 64 for v in got["slides"].values()) and wr.verify(course, 1)[0], got)
    Path(wr.review_file(course, 1)).write_text(json.dumps(old), encoding="utf-8")
    deck.write_text(DECK.replace("Two", "Two, changed"), encoding="utf-8")
    ok, kind, msg = wr.verify(course, 1)
    check("... once its deck changes, every slide of it is stale (it has no hash to tell them apart)", not ok and kind == "stale" and "5 of 5" in msg, msg)
    rc, lines = wr.sign(course, 1, reviewer(tmp, {"s02": True}), BUILDER)
    ok, kind, msg = wr.verify(course, 1)
    check("... and signing one slide does not make the others current", not ok and kind == "stale" and "4 of 5" in msg and "s02" not in msg, msg)


def gates_part(tmp, course, deck):
    src = Path(HERE.parents[2], "course-factory", "compile", "scripts", "build_module.py").read_text(encoding="utf-8")
    check("build_module.py: --no-walk for factory tests, the fit walk saves its stops, and a module with no review is NOT DONE",
          '"--no-walk"' in src and '"--walk-dir"' in src and 'print("NOT DONE: %s' in src and "walk_review.verify(course, module)" in src
          and "walk_gate(course, o.module, alone=passed)" in src)
    check("fit_gate.py writes each slide's hash beside the walk", "walk_review.slide_hashes(" in Path(HERE, "fit_gate.py").read_text(encoding="utf-8"))
    sys.path.insert(0, str(HERE.parents[2] / "course-factory" / "scripts"))
    import course_portal
    os.environ["CF_FIX_NO_WALK_RUN"] = "1"
    problems = course_portal.walk_problems(course)
    check("course_portal upload: a built module whose walk review is stale / missing is a blocker", problems and "stale" in problems[0], problems)
    deck.write_text(DECK, encoding="utf-8")
    wr.sign(course, 1, reviewer(tmp, {"s%02d" % i: True for i in range(1, 6)}, by="x"))
    check("... and none once it is signed for this deck", course_portal.walk_problems(course) == [], course_portal.walk_problems(course))
    import fix
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = fix.cmd_check(course, "walk", "1", "s02")
    check("fix.py check --kind walk: passes on a signed module", code == 0 and "walk review passed" in buf.getvalue(), buf.getvalue())
    deck.write_text(DECK + "<!-- x -->\n<p>new</p>", encoding="utf-8")
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = fix.cmd_check(course, "walk", "1", "s02")
    check("... and fails (with the brief for the reviewer) once a fix changed the deck", code == 1 and "walk review stale" in buf.getvalue()
          and "review_brief.md" in buf.getvalue(), buf.getvalue())
    check("... telling the fixer to name the builder, that the reviewer is someone else, and that there are two rounds",
          "--built-by" in buf.getvalue() and "never the session that made the fix" in buf.getvalue() and "Two rounds at most" in buf.getvalue(), buf.getvalue())
    wr.sign(course, 1, reviewer(tmp, {"s%02d" % i: (True if i != 2 else "stop 1: the new line is cut") for i in range(1, 6)}, by="x"))
    problems = course_portal.walk_problems(course)
    check("course_portal upload: an open fail stops it, one line a module", len(problems) == 1 and "\n" not in problems[0] and "open fails on s02" in problems[0], problems)
    wr.accept(course, 1, OPERATOR, "the line is read out by the instructor")
    check("... and the operator's accept lets it through", course_portal.walk_problems(course) == [], course_portal.walk_problems(course))


def main():
    try:
        import PIL  # noqa: F401
    except ImportError:
        print("SKIP - Pillow is not installed")
        return 0
    tmp = tempfile.mkdtemp(prefix="walk_review_")
    try:
        course, deck = first_part(tmp)
        rounds_part(tmp)
        older_part(tmp)
        gates_part(tmp, course, deck)
    finally:
        os.environ.pop("CF_FIX_NO_WALK_RUN", None)
        shutil.rmtree(tmp, ignore_errors=True)
    print("\n%d passed, %d failed" % (len(PASS), len(FAIL)))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
