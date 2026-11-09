# -*- coding: utf-8 -*-
"""test_walk_review - "walk it like a trainee" (2.116.0): prepare / sign / verify on a fixture deck, and the gates.

    python test_walk_review.py

Pinned:
  * prepare makes one contact sheet per walked slide and review_brief.md (batches of at most 4 slides, each slide's stop texts,
    its figure's why / why_text from the build sheet, the six-point rubric); --slides limits it;
  * sign writes MNN_walk_review.json with the deck's hash, the reviewer and the date; slides not returned keep their old result;
  * verify: missing -> exit 1; signed -> exit 0; the deck changed -> stale (a build timestamp or comment change is NOT a change);
    a slide the walk has and the review lacks -> incomplete; an open fail -> failing;
  * the gates: build_module.py has --no-walk and prints "NOT DONE: walk review ..."; fix.py check --kind walk; course_portal upload.
No browser needed: the walk's stops are fixture PNGs.
"""
from __future__ import annotations

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


DECK = "<!-- built 2026-11-09T10:11:12 -->\n<html><body><section id=\"s01\">One</section><section id=\"s02\">Two</section></body></html>"


def fixture(tmp, n_slides=5):
    from PIL import Image
    course = os.path.join(tmp, "course")
    mdir = os.path.join(course, "modules", "module01")
    os.makedirs(os.path.join(mdir, "presentation"))
    Path(mdir, "presentation", "index.html").write_text(DECK, encoding="utf-8")
    wdir = os.path.join(course, "working_claude", "_build", "walk", "M01")
    os.makedirs(wdir)
    stops = []
    for i in range(1, n_slides + 1):
        for k in (1, 2, 3):
            name = "s%02d_k%d.png" % (i, k)
            Image.new("RGB", (480, 300), (30 * i, 60 * k, 120)).save(os.path.join(wdir, name))
            stops.append({"slide": "s%02d" % i, "k": k, "file": name, "title": "Slide %d" % i, "lit": ["Line %d" % k],
                          "ask": [], "reveal": ["The answer"] if k == 3 else [], "fig": ":1:2"})
    Path(wdir, "walk.json").write_text(json.dumps({"viewport": "1280x800", "stops": stops}), encoding="utf-8")
    sdir = os.path.join(course, "working_claude", "script")
    os.makedirs(sdir)
    Path(sdir, "M01.build.json").write_text(json.dumps({"screens": {
        "s02": {"figure": "s02.kit2d.json", "why": "sequence", "why_text": "The trainee sees the valve close."}}}), encoding="utf-8")
    return course, mdir


def main():
    try:
        import PIL  # noqa: F401
    except ImportError:
        print("SKIP - Pillow is not installed")
        return 0
    tmp = tempfile.mkdtemp(prefix="walk_review_")
    try:
        course, mdir = fixture(tmp)
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
        check("... and the six-point rubric (changes on Next, shows what the line says, nothing empty / hidden / cut / duplicated / contradictory, "
              "what to do, the drawing's reason, answer visible and not over the figure)",
              all(x in brief for x in ("1. Something visibly changes on each Next", "2. The picture shows what the lit line says",
                                       "nothing is empty, hidden, cut, duplicated or contradictory".capitalize()[:0] + "Nothing is empty, hidden, cut, duplicated or contradictory",
                                       "4. A trainee would know", "5. The drawing has a reason", "6. The answer / reveal")), brief[:600])
        rc, _ = wr.prepare(course, 1, ["s02", "s03"])
        check("prepare --slides: only those slides' sheets are in the brief", rc == 0 and "## Batch 1 - s02, s03" in Path(wdir, "review_brief.md").read_text(encoding="utf-8")
              and "s01" not in Path(wdir, "review_brief.md").read_text(encoding="utf-8").split("## Batch")[1], rc)
        wr.prepare(course, 1)

        ok, kind, msg = wr.verify(course, 1)
        check("verify: no review yet -> missing, exit 1", not ok and kind == "missing" and wr.main(["verify", course, "--module", "1"]) == 1, msg)
        rv = os.path.join(tmp, "reviewer.json")
        Path(rv).write_text(json.dumps({"reviewed_by": "Sonnet subagent", "slides": {
            "s01": {"ok": True, "fails": []}, "s02": {"ok": True, "fails": []}, "s03": {"ok": True, "fails": []},
            "s04": {"ok": False, "fails": ["stop 3: the chart is still an empty axis"]}}}), encoding="utf-8")
        rc, lines = wr.sign(course, 1, rv)
        signed = json.loads(Path(wr.review_file(course, 1)).read_text(encoding="utf-8"))
        check("sign: writes MNN_walk_review.json with the deck hash, reviewer, date and slides",
              signed["reviewed_by"] == "Sonnet subagent" and len(signed["deck_sha256"]) == 64 and signed["date"] and signed["slides"]["s04"]["ok"] is False
              and rc == 1 and "OPEN FAILS on s04" in lines[0], (rc, lines, signed))
        ok, kind, msg = wr.verify(course, 1)
        check("verify: s05 not reviewed -> incomplete; an open fail on s04 is reported once reviewed", not ok and kind == "incomplete" and "s05" in msg, msg)
        Path(rv).write_text(json.dumps({"reviewed_by": "Sonnet subagent", "slides": {"s05": {"ok": True, "fails": []}}}), encoding="utf-8")
        wr.sign(course, 1, rv)
        ok, kind, msg = wr.verify(course, 1)
        check("... a second sign keeps the slides the reviewer did not return; s04 still fails -> failing", not ok and kind == "failing" and "s04" in msg, msg)
        Path(rv).write_text(json.dumps({"reviewed_by": "Sonnet subagent", "slides": {"s04": {"ok": True, "fails": []}}}), encoding="utf-8")
        rc, _ = wr.sign(course, 1, rv)
        ok, kind, msg = wr.verify(course, 1)
        check("every fail fixed and re-reviewed -> verify passes, exit 0", ok and rc == 0 and wr.main(["verify", course, "--module", "1"]) == 0, msg)
        deck = Path(mdir, "presentation", "index.html")
        deck.write_text(DECK.replace("2026-11-09T10:11:12", "2026-11-10T08:00:00").replace("<!-- built", "<!-- rebuilt"), encoding="utf-8")
        check("a rebuild that changes only the build timestamp / comments is the same deck - still verified", wr.verify(course, 1)[0])
        deck.write_text(DECK.replace("Two", "Two, changed"), encoding="utf-8")
        ok, kind, msg = wr.verify(course, 1)
        check("the deck changed after the review -> stale, exit 1", not ok and kind == "stale" and wr.main(["verify", course, "--module", "1"]) == 1, msg)
        check("sign refuses a reviewer JSON with no \"ok\" or no reviewer", wr.sign(course, 1, os.path.join(tmp, "nope.json"))[0] == 2)

        # --- the gates
        src = Path(HERE.parents[2], "course-factory", "compile", "scripts", "build_module.py").read_text(encoding="utf-8")
        check("build_module.py: --no-walk for factory tests, the fit walk saves its stops, and a module with no review is NOT DONE",
              '"--no-walk"' in src and '"--walk-dir"' in src and 'print("NOT DONE: %s' in src and "walk_review.verify(course, o.module)" in src)
        sys.path.insert(0, str(HERE.parents[2] / "course-factory" / "scripts"))
        import course_portal
        os.environ["CF_FIX_NO_WALK_RUN"] = "1"
        problems = course_portal.walk_problems(course)
        check("course_portal upload: a built module whose walk review is stale / missing is a blocker", problems and "stale" in problems[0], problems)
        deck.write_text(DECK, encoding="utf-8")
        rv2 = Path(tmp, "r2.json")
        rv2.write_text(json.dumps({"reviewed_by": "x", "slides": {"s%02d" % i: {"ok": True, "fails": []} for i in range(1, 6)}}), encoding="utf-8")
        wr.sign(course, 1, str(rv2))
        check("... and none once it is signed for this deck", course_portal.walk_problems(course) == [], course_portal.walk_problems(course))
        import fix
        import io
        import contextlib
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
    finally:
        os.environ.pop("CF_FIX_NO_WALK_RUN", None)
        shutil.rmtree(tmp, ignore_errors=True)
    print("\n%d passed, %d failed" % (len(PASS), len(FAIL)))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
