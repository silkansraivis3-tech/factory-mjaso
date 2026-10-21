# -*- coding: utf-8 -*-
"""test_build_module - build_module.py's course-package verdict in a parallel build (2.51.0).

    python test_build_module.py

With --no-course-pages a module agent never writes COURSE.html or any START_HERE page - compile_course.py does, once
every module is in. Before 2.51.0 the package check still failed on those missing pages (and on the other modules'),
so no module of a parallel build could PASS and none reached its review sheets (benchmark 2026-10-20, workflow_before).
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import build_module as b  # noqa: E402

FAILS = []


def check(name, ok, detail=""):
    if not ok:
        FAILS.append(name)
    print(("  ok    " if ok else "  FAIL  ") + name + (("  -> " + str(detail)[:600]) if detail and not ok else ""))


# check_course_package.py's own words, from the benchmark course before assembly (shortened)
OUT = """Course folder: C:\\c\\modules
  16 module(s)

6 thing(s) to fix before it goes into the classroom:
  - module01/START_HERE.html is missing - opens the presentation (L43)
  - module01/presentation/index.html uses ../START_HERE_EXTENDED.html, which is not there
  - module02/START_HERE_EXTENDED.html is missing - the instructor's quick-access page (L43)
  - module02/tasks/sc1_a.html has no <title>
  - the classroom's importer: Link outside the package: instructor/COURSE.html → instructor/module01/START_HERE.html
  - _course_shell/course_map.js lists M01, the folder has module01, module02

Worth a look (does not stop it):
  - module01: 11 drawn subjects still need a real photograph
"""


def main():
    code, out, left = b.own_package_findings(1, OUT, "module01")
    check("module 1 of a parallel build: the missing course pages and module 2's own problem do not fail it",
          code == 0 and left == 6 and "none (6 left to the check after assembly)" in out, (code, left, out))
    check("... and the notes the check printed are kept", "real photograph" in out, out)
    code, out, left = b.own_package_findings(1, OUT, "module02")
    check("module 2: its own problem (a task page with no <title>) still fails it",
          code == 1 and left == 5 and "sc1_a.html has no <title>" in out, (code, left))
    pre = OUT.replace("6 thing(s)", "9 thing(s)").replace(
        "  - _course_shell/course_map.js",
        "  - the classroom's importer: The course ID must be a unique name without spaces.\n"
        "  - the classroom's importer: Give the course title.\n"
        "  - .tmp.drivedownload\\ is not a module (module01 ...) - the factory's own material belongs in working_claude\n"
        "  - _course_shell/course_map.js")
    code, out, left = b.own_package_findings(1, pre, "module01")
    check("2.58.0 before assembly: the importer's missing course ID / title and a sync tool's folder are not module 1's "
          "(the IGF full build: no module ever saw PASS)", code == 0 and left == 9, (code, left, out))
    mine = OUT.replace("  - module02/tasks/sc1_a.html has no <title>", "  - module01/presentation/index.html has no data-title")
    check("a module's own finding beside the course-page ones fails it",
          b.own_package_findings(1, mine, "module01")[0] == 1)
    check("a passing package and a stop (exit 2) are passed through untouched",
          b.own_package_findings(0, "Ready", "module01") == (0, "Ready", 0)
          and b.own_package_findings(2, "Stopped", "module01") == (2, "Stopped", 0))
    last = {"inputs": "k1", "only_figures": True}
    check("2.56.0 a figures-only round: only figures fail, the last full build failed on figures alone, same inputs -> stop",
          b.figures_only_round(["figures"], False, last, "k1"))
    check("... never when the script or build sheet changed, the last build failed on more, --full, or nothing failed yet",
          not b.figures_only_round(["figures"], False, last, "k2")
          and not b.figures_only_round(["figures"], False, {"inputs": "k1", "only_figures": False}, "k1")
          and not b.figures_only_round(["figures"], True, last, "k1")
          and not b.figures_only_round([], False, last, "k1")
          and not b.figures_only_round(["figures"], False, {}, "k1"))
    blanks_part()
    stages_part()
    layout_part()
    retry_part()
    print("\n%s" % ("ALL PASS" if not FAILS else "%d FAILED" % len(FAILS)))
    return 1 if FAILS else 0


def blanks_part():
    """2.52.0 - a build sheet with --init-build's blanks still in it builds nothing; one line says what to fill (M01 workflow
    benchmark run 1: a 68 s build whose eight compile problems were all blanks)"""
    import io
    import json
    import shutil
    import subprocess
    import tempfile
    import test_compile_module as tcm
    import content_script as cs
    tmp = tempfile.mkdtemp(prefix="bm_blanks_")
    try:
        sc = tcm.script(screens=tcm.SCREENS + [
            {"id": "q02", "kind": "self-check", "set": "SC1", "mechanic": "hotspot", "question": "Tap the vent mast.",
             "visual": "the ship", "answer": "Vent mast*\nFuel tank", "feedback": "High above the deck."}])
        c, md = tcm.new_course(tmp, sc)
        check("a filled build sheet has no blanks", b.starter_blanks(c, 1) == [], b.starter_blanks(c, 1))
        tcm.build_of(c, lambda s: s["screens"].update(s01={"figure": "", "visual_kind": "photo"}, q02={"figure": "", "areas": {}},
                                                       s04={"figure": "m01_s04_3d.html", "visual_kind": "model_3d"}))
        got = b.starter_blanks(c, 1)
        check("the starter's blanks are found: a slide with no picture, a question on no picture, a planned 3D scene not written",
              [x[0] for x in got] == [["s01"], ["q02"], ["s04 (m01_s04_3d.html)"]], got)
        p = subprocess.run([sys.executable, os.path.join(HERE, "build_module.py"), c, "--module", "1"], capture_output=True,
                           text=True, encoding="utf-8", errors="replace", timeout=300)
        out = (p.stdout or "") + (p.stderr or "")
        check("build_module.py builds nothing on it (exit 1) and says in one line what to fill",
              p.returncode == 1 and out.strip().count("\n") == 0 and out.startswith("FAIL M01 - nothing built")
              and "s01" in out and "q02" in out and "declined_3d" in out
              and not os.path.isfile(os.path.join(md, "presentation", "index.html")), (p.returncode, out))
        tcm.build_of(c, lambda s: s["screens"]["s04"].update(declined_3d="the operator keeps the flat drawing"))
        check("a 3D scene declined with the operator's reason is no blank", [x[0] for x in b.starter_blanks(c, 1)] == [["s01"], ["q02"]],
              b.starter_blanks(c, 1))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def stages_part():
    import io
    import time
    buf = io.StringIO()
    b.write_stages(buf, [("figures (figure_fit.py)", 41.2), ("compile (compile_module.py, its drawing check)", 63.0),
                         ("  audits 1280x800 1024x768", 120.4)], time.time() - 230)
    text = buf.getvalue()
    check("2.52.0: the build log ends with each stage's seconds and the total",
          "===== stage seconds" in text and "figures (figure_fit.py)" in text and "41 s" in text and "120 s" in text
          and "total" in text and "230 s" in text, text)


def layout_part():
    """2.62.0 - a slide the compiler built another way for L62 that the audit failed is measured out (IGF M04 s05: 102
    words under a photograph across the slide spilled 66 px; no word count would have told)"""
    import io
    import json
    import tempfile
    deck = ('<section class="slide" data-script="s04" data-template="explain-figure.v1">\n'
            '<section class="slide" id="s05" data-script="s05" data-varied="picture-top|light|a1b2c3d4e5f6">\n'
            '<section class="slide dark" data-script="s06" data-varied="picture-left|dark|0123456789ab">')
    audit = ("  1024x768  deck     FAIL n=3   13 slides\n              slide 5 (s05): spills ul.support by 66 px\n"
             "              slide 4 (s04): spills div.copy by 7 px\n")
    got = b.moved_misfits(deck, audit)
    check("only a failing slide the compiler moved is a misfit - not one built its own way, not a moved one that passed",
          got == {"s05": ("picture-top", "light", "a1b2c3d4e5f6")}, got)
    path = os.path.join(tempfile.mkdtemp(prefix="bm_layout_"), "M01_layout_avoid.json")
    b.measure_out(path, got)
    b.measure_out(path, {"s05": ("picture-left", "light", "a1b2c3d4e5f6")})
    b.measure_out(path, got)
    av = json.load(io.open(path, encoding="utf-8"))
    check("each misfit's way joins its slide's list once", av == {"s05": {"words": "a1b2c3d4e5f6", "avoid": [
        ["picture-top", "light"], ["picture-left", "light"]]}}, av)
    b.measure_out(path, {"s05": ("picture-right", "dark", "ffffffffffff")})
    av = json.load(io.open(path, encoding="utf-8"))
    check("... and a slide whose approved words changed starts a new list",
          av["s05"] == {"words": "ffffffffffff", "avoid": [["picture-right", "dark"]]}, av)
    check("one build builds the misfits again at most %d times" % b.LAYOUT_ROUNDS, b.LAYOUT_ROUNDS == 2)


def retry_part():
    """2.63.0 - a round that will be built again does not wait for the review sheets or check the package: the moment the
    audits say a slide the compiler moved does not fit, every check still running is ended and the package is not
    started (IGF M01 / M02 v262: retried rounds waited 22-824 s, the sheets holding browser slots the next round needed)"""
    import tempfile
    import time
    tmp = tempfile.mkdtemp(prefix="bm_retry_")
    mark = os.path.join(tmp, "package_ran")
    py = sys.executable
    jobs = {"words (instructor)": [py, "-c", "print('ok')"],
            "audits 1280x800 1024x768": [py, "-c", "import time, sys; time.sleep(1); print('slide 5 (s05): spills'); sys.exit(1)"],
            "review sheets": [py, "-c", "import time; time.sleep(40)"]}
    pkg = [py, "-c", "open(%r, 'w').write('x')" % mark]
    asked = []

    def retry(k, res):
        asked.append(k)
        return {"s05": ("picture-top", "light", "abc")} if k.startswith("audits") and res[0] else None
    t = time.time()
    results, took, again = b.run_checks(jobs, pkg, retry)
    secs = time.time() - t
    check("a round that will retry ends as soon as the audits say so - not after the 40 s review sheets (%.1f s)" % secs,
          secs < 15 and again == {"s05": ("picture-top", "light", "abc")}, (secs, again))
    check("... the package is never checked in that round", "course package" not in results and not os.path.exists(mark), results.keys())
    check("... and the review sheets' answer is not one to read (it was ended)", results.get("review sheets", (0,))[0] != 0, results.get("review sheets"))
    jobs["review sheets"] = [py, "-c", "print('sheets')"]
    results, took, again = b.run_checks(jobs, pkg, lambda k, res: None)
    check("a round that will not retry runs everything and checks the package once the others are done",
          again is None and results["review sheets"][0] == 0 and results["course package"][0] == 0 and os.path.exists(mark), results)


if __name__ == "__main__":
    sys.exit(main())
