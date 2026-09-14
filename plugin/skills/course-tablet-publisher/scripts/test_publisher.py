# -*- coding: utf-8 -*-
"""test_publisher - the approval gate, the runtime gate, and the preview surface.

Every assertion here exists because the alternative is a course reaching the production
Android repository without a person having said so, or reaching a tablet in a state where
it cannot run. Both are silent failures: an unapproved publish looks exactly like an
approved one, and a `target="_blank"` on a WebView with no tabs looks exactly like a frozen
tablet.

The fixtures are synthetic and live in a temporary folder. Nothing here reads or writes the
real Android project - which is itself the first thing tested.

    python test_publisher.py
"""
from __future__ import annotations

import io
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable

PASS: list[str] = []
FAIL: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    (PASS if ok else FAIL).append(name + (("  -> " + detail) if detail and not ok else ""))


def run(args: list[str]) -> tuple[int, str]:
    p = subprocess.run([PY] + args, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return p.returncode, (p.stdout or "") + (p.stderr or "")


# --------------------------------------------------------------------------- fixtures
PAGE_OK = """<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><title>%s</title></head>
<body><a class="gbt-topback" href="../index.html">Back</a><p>ok</p></body></html>
"""

PAGE_BAD = """<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><title>bad</title></head>
<body>
<a class="gbt-topback" href="../index.html">Back</a>
<a href="x.html" target="_blank">no tabs on a tablet</a>
<button onclick="window.open('y.html')">no window manager</button>
<script>fetch('d.json');</script>
</body></html>
"""


def make_repo(root: str, with_bad: bool = False) -> str:
    tt = os.path.join(root, "app", "src", "main", "assets", "training_terminal",
                      "courses", "t-course")
    it = os.path.join(root, "app", "src", "instructor", "assets", "instructor_terminal",
                      "courses", "t-course")
    os.makedirs(os.path.join(tt, "tasks"), exist_ok=True)
    os.makedirs(it, exist_ok=True)
    io.open(os.path.join(tt, "course.json"), "w", encoding="utf-8").write(json.dumps({
        "id": "t-course", "title": "Test Course", "version": "1.0.0",
        "status": "draft", "modules": 1}))
    io.open(os.path.join(tt, "index.html"), "w", encoding="utf-8").write(PAGE_OK % "Test")
    io.open(os.path.join(tt, "tasks", "T1.html"), "w", encoding="utf-8").write(PAGE_OK % "T1")
    if with_bad:
        io.open(os.path.join(tt, "tasks", "bad.html"), "w",
                encoding="utf-8").write(PAGE_BAD)
    return root


def main() -> int:
    tmp = tempfile.mkdtemp(prefix="ntp_test_")
    try:
        # ---- 1 · the approval gate ---------------------------------------
        # --publish without --approved-by must refuse BEFORE anything is opened, so
        # point it at a repo path that does not exist: if it gets far enough to look,
        # the refusal came too late.
        rc, out = run([os.path.join(HERE, "publish.py"),
                       "--repo", os.path.join(tmp, "no-such-repo"),
                       "--course-id", "t-course", "--publish"])
        check("publish without approval is refused", rc != 0, "rc=%d" % rc)
        check("the refusal says the app is READ ONLY without approval",
              "not been approved" in out and "PUBLISH TARGET" in out)
        check("the refusal shows the colleague what approval sounds like",
              "Approved. Publish this course" in out)
        check("the refusal points at preview, not at git",
              "preview.py" in out and "git" not in out.split("preview.py")[0][-200:])
        check("nothing was touched before refusing",
              "platform repository" not in out and "gate" not in out.lower())

        # the same command WITH approval must get past the gate and fail later, on its
        # own merits - proving the approval check is the thing that stopped it before.
        rc2, out2 = run([os.path.join(HERE, "publish.py"),
                         "--repo", os.path.join(tmp, "no-such-repo"),
                         "--course-id", "t-course", "--publish",
                         "--approved-by", "Test Person"])
        check("with approval it proceeds past the gate",
              "not been approved" not in out2)

        # ---- 2 · the runtime gate ----------------------------------------
        good = make_repo(os.path.join(tmp, "good"))
        rc3, out3 = run([os.path.join(HERE, "gates.py"), "--repo", good,
                         "--course-id", "t-course"])
        check("a clean course passes the runtime gate",
              "[FAIL] runtime" not in out3, out3[-300:])

        bad = make_repo(os.path.join(tmp, "bad"), with_bad=True)
        rc4, out4 = run([os.path.join(HERE, "gates.py"), "--repo", bad,
                         "--course-id", "t-course"])
        for needle, what in (
            ('target="_blank"', "target=_blank"),
            ("window.open", "window.open"),
            ("fetch()", "fetch"),
        ):
            check("runtime gate catches " + what, needle in out4)
        check("a runtime failure stops publication", "VERDICT: FAIL" in out4)

        # the platform shell may reach the backend; a course may not
        shell = os.path.join(bad, "app", "src", "instructor", "assets",
                             "instructor_terminal", "live")
        os.makedirs(shell, exist_ok=True)
        io.open(os.path.join(shell, "live.js"), "w", encoding="utf-8").write(
            "var x = new XMLHttpRequest();")
        rc5, out5 = run([os.path.join(HERE, "gates.py"), "--repo", bad,
                         "--course-id", "t-course"])
        check("the live-class shell is exempt from the runtime gate",
              "live/live.js" not in out5 and "live\\live.js" not in out5)

        # ---- 3 · the preview surface -------------------------------------
        course = os.path.join(tmp, "course")
        os.makedirs(os.path.join(course, "tasks"), exist_ok=True)
        io.open(os.path.join(course, "module.html"), "w",
                encoding="utf-8").write(PAGE_OK % "The deck")
        io.open(os.path.join(course, "START_HERE.html"), "w",
                encoding="utf-8").write(PAGE_OK % "Start here")
        io.open(os.path.join(course, "tasks", "T1.html"), "w",
                encoding="utf-8").write(PAGE_OK % "Task one")
        io.open(os.path.join(course, "fragment.html"), "w",
                encoding="utf-8").write('<div class="f1">a fragment, not a page</div>')

        rc6, out6 = run([os.path.join(HERE, "preview.py"), "--course", course])
        review = os.path.join(course, "REVIEW.html")
        check("preview writes REVIEW.html", os.path.isfile(review))
        html = io.open(review, encoding="utf-8").read() if os.path.isfile(review) else ""
        check("the review page links the deck", "module.html" in html)
        check("the review page links the task", "tasks/T1.html" in html)
        check("a figure fragment is not offered as a page", "fragment.html" not in html)
        check("the review page states the approval sentence",
              "Approved. Publish this course" in html)
        check("the review page carries no course CSS",
              'href="assets/' not in html and "<link" not in html)
        check("preview reports file:// as safe for clean output",
              "file:// safe" in out6, out6[-200:])

        # and it must SAY SO when the course would not survive file://
        io.open(os.path.join(course, "tasks", "T2.html"), "w", encoding="utf-8").write(
            PAGE_OK % "T2" + "<script>fetch('x.json');</script>")
        rc7, out7 = run([os.path.join(HERE, "preview.py"), "--course", course])
        check("preview warns when a page would not work as a file",
              "will NOT work" in out7, out7[-200:])

        # ---- 4 · the review surface can never be published ----------------
        plat = json.load(io.open(os.path.join(HERE, "..", "knowledge", "platform.json"),
                                 encoding="utf-8"))
        globs = plat["role_rules"]["internal_globs"]
        check("REVIEW.html is internal by pattern",
              any("REVIEW" in g for g in globs))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("=" * 72)
    print("test_publisher - PREVIEW, APPROVAL, PUBLISH")
    print("=" * 72)
    for p in PASS:
        print("  ok    " + p)
    for f in FAIL:
        print("  FAIL  " + f)
    print()
    print("%d passed, %d failed" % (len(PASS), len(FAIL)))
    if not FAIL:
        print("\nThe gate refuses an unapproved publish before it opens anything, the "
              "runtime\nchecks catch what fails silently on a tablet, and the review "
              "surface cannot ship.")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
