# -*- coding: utf-8 -*-
"""build_module.py - a module built and every check run, in ONE command; only what fails is printed (2.50.0).

    python compile/scripts/build_module.py <course> --module 1 [--viewport 1920x1080] [--no-course-pages]
                                           [--no-fix] [--no-review] [--draft] [--force]

WHY (IGF M01 benchmark, 2026-10-19): one module took 6 compiles and about 20 separate check runs, each one a turn of the
model re-reading a context of ~200k tokens. Every check still runs - nothing here is skipped or loosened - but in one
process, the independent ones at once, and the answer is short:

  1  figures      every kit figure on its real slide at once (course-visuals/kit/scripts/figure_fit.py): the spec checks,
                  every drawing audit at every step, grouped per figure; the fixes with one right answer made and proven
  2  compile      compile_module.py (deck, task pages, answer key, plan; its own drawing check, L54, on every page)
  3  the checks   at the same time: check_script_match.py --part instructor and --part trainee, check_navigation.py,
                  run_audits.py (1280 x 800, 1024 x 768 and any --viewport), then compile_course.py and
                  check_course_package.py (the course's own pages and the classroom's importer)
  4  the review   when everything passes: review_sheets.mjs photographs every slide, every figure step and every question
                  (asked, answered wrong, answered right) onto a few sheets - only the screens changed since the last
                  review - and checks that every question grades right and wrong answers as such (compile GUIDE 2f)

Printed: each failure with its file, slide or question, and what to do; a figure's problems once per part, not once per
step; then one line - PASS, or how many problems. Everything else is in the full log (its path is the last line).
--no-course-pages: a module agent in a parallel build (orchestration Rule 3 - one process writes COURSE.html).
Exit 0 PASS, 1 problems to fix, 2 stopped (the compiler refused: not approved, changed by hand, design files edited).
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import io
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
SKILLS = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
FACTORY = os.path.join(SKILLS, "course-factory", "scripts")
MEASURE = os.path.join(SKILLS, "course-module-ux", "measure", "scripts")
KIT = os.path.join(SKILLS, "course-visuals", "kit", "scripts")
sys.path.insert(0, HERE)
sys.path.insert(0, FACTORY)
sys.path.insert(0, KIT)

PY = sys.executable
L54_TAIL = re.compile(r" \(L54: fix the drawing.*?\)$| \(try the figure in the studio:.*?\)$| \(see every step at once:.*?\)$")


def run(cmd, timeout=900):
    """(exit code, output) of one tool, run as its own process (as the person would run it)"""
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout, env=env)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except subprocess.TimeoutExpired:
        return 2, "timed out after %d s: %s" % (timeout, " ".join(cmd))
    except OSError as err:
        return 2, "could not run %s: %s" % (cmd[0], err)


def compile_problems(out):
    """the compiler's 'To fix before it is shown' list, and its L60 recommendation"""
    probs, rec = [], ""
    if "To fix before it is shown:" in out:
        tail = out.split("To fix before it is shown:", 1)[1]
        probs = [L54_TAIL.sub("", x[4:].rstrip()) for x in tail.splitlines() if x.startswith("  - ")]
    m = re.search(r"RECOMMENDED \(L60\) - (.*?)\n=+", out, re.S)
    if m:
        rec = " ".join(m.group(1).split())
    return probs, rec


def lines_of(out, n=12):
    keep = [x.rstrip() for x in out.splitlines() if x.strip() and not x.startswith("  note:") and not set(x.strip()) <= set("=-")]
    return keep[-n:]


def figure_slides(text):
    """the slide ids the figure pre-check already reported (their compile drawing findings say the same thing again)"""
    return set(re.findall(r"^  (s\d+\w*) \(", text, re.M))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("course")
    ap.add_argument("--module", required=True)
    ap.add_argument("--viewport", action="append", default=[], help="another audit size, WxH (1280x800 and 1024x768 always run)")
    ap.add_argument("--no-course-pages", action="store_true", help="a module agent in a parallel build: no compile_course.py")
    ap.add_argument("--no-fix", action="store_true", help="the figure pre-check makes no fix of its own")
    ap.add_argument("--no-review", action="store_true", help="no review sheets after a pass")
    ap.add_argument("--draft", action="store_true")
    ap.add_argument("--force", action="store_true")
    o = ap.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    t0 = time.time()
    import workspace
    import content_script as cs
    course = workspace.work_folder(o.course, create=False)
    import compile_module as cm
    mdir, why = cm.module_folder(course, o.module)
    if not mdir:
        print("Stopped - " + why)
        return 2
    m = cs.mid(o.module) if str(o.module).isdigit() else str(o.module)
    logdir = workspace.claude_path(course, "_build")
    os.makedirs(logdir, exist_ok=True)
    log = io.open(os.path.join(logdir, "%s_build.log" % m), "w", encoding="utf-8")
    say, fails, notes = [], [], []

    def logged(title, out):
        log.write("\n===== %s\n%s\n" % (title, out))

    # 1 - every figure at once, before the compile
    fig_text = ""
    if str(o.module).isdigit():
        try:
            import figure_fit
            fcode, fig_text, _ = figure_fit.run_all(course, o.module, fix=not o.no_fix)
        except Exception as err:                     # noqa: BLE001 - the compile's own drawing check still runs
            fcode, fig_text = 1, "Figures: the pre-check could not run (%s) - the compile's drawing check still judges them" % err
        logged("figures (figure_fit.py)", fig_text)
        body = [x for x in fig_text.splitlines()[1:-1]]
        if body:
            say.append("FIGURES")
            say += body
        if fcode:
            fails.append("figures")
    # 2 - the compile (with its own drawing check)
    cmd = [PY, os.path.join(HERE, "compile_module.py"), course, "--module", str(o.module)]
    cmd += ["--draft"] if o.draft else []
    cmd += ["--force"] if o.force else []
    ccode, cout = run(cmd)
    logged("compile_module.py", cout)
    if ccode == 2:
        print("\n".join(say + ["", "COMPILE - stopped:"] + ["  " + x for x in lines_of(cout, 25)]))
        print("Full log: %s" % log.name)
        log.close()
        return 2
    probs, rec = compile_problems(cout)
    shown = figure_slides(fig_text)
    probs = [x for x in probs if not any(re.search(r"\(%s\)[ :]" % re.escape(s), x) and re.search(r"\b(empty|text zone|inside|"
                                                                                                    r"cut off|small text|label|contrast)\b", x)
                                         for s in shown)]
    if ccode != 0 or probs:
        fails.append("compile")
        say.append("COMPILE - %d problem(s) to fix%s:" % (len(probs), " (the figures above not repeated)" if shown else ""))
        say += ["  - " + x for x in probs]
        if any("L54" in x or "drawing" in x for x in probs):
            say.append("  (a drawing problem: fix the drawing, or mark a crossing that is meant data-may-cross / data-no-contain / "
                       "data-may-overlap; a kit figure: studio.py <figure>.kit.json --step all)")
    if "Not checked:" in cout:
        fails.append("drawing check not run")
        say.append("DRAWING CHECK did not run: " + cout.split("Not checked:", 1)[1].strip().splitlines()[0])
    if rec:
        notes.append("RECOMMENDED (L60): " + rec)
    mm = re.search(r"Real photographs still missing.*?listed in\s*\n\s*(\S.*?)\n((?:  - .*\n?)*)", cout)
    if mm:
        notes.append("Real photographs still to take: %d thing(s), listed in %s" % (len(mm.group(2).strip().splitlines()), mm.group(1).strip()))
    # 3 - the checks, at the same time
    deck = os.path.join(mdir, "presentation", "index.html")
    jobs = {
        "words (instructor)": [PY, os.path.join(FACTORY, "check_script_match.py"), course, "--module", str(o.module), "--part", "instructor"],
        "words (trainee)": [PY, os.path.join(FACTORY, "check_script_match.py"), course, "--module", str(o.module), "--part", "trainee"],
        "navigation": [PY, os.path.join(MEASURE, "check_navigation.py"), mdir],
    }
    sizes = ["1024x768"] + [v for v in o.viewport if v not in ("1280x800", "1024x768")]
    if os.path.isfile(deck):
        a = [PY, os.path.join(MEASURE, "run_audits.py"), deck, "--quiet"]
        for v in sizes:
            a += ["--viewport", v]
        jobs["audits 1280x800 %s" % " ".join(sizes)] = a

    if not o.no_course_pages:
        jobs["course pages (compile_course.py)"] = [PY, os.path.join(HERE, "compile_course.py"), course]
    # 4 - the review sheets are made at the same time (2.50.1: they were a third of a passing build), into a folder of
    # their own: they become the review only when everything passes, so a failed build never hides a changed screen
    out_dir = workspace.claude_path(course, "review", m)
    pending = out_dir + ".pending"
    want_review = not o.no_review and not fails
    if want_review:
        import shutil
        shutil.rmtree(pending, ignore_errors=True)
        jobs["review sheets"] = ["node", os.path.join(MEASURE, "review_sheets.mjs"), mdir, pending, "--base=" + out_dir]
    results = {}
    with cf.ThreadPoolExecutor(max_workers=7) as ex:
        futs = {ex.submit(run, c): k for k, c in jobs.items()}
        pkg = None
        for f in cf.as_completed(futs):
            results[futs[f]] = f.result()
            # the importer reads every file of the module folder: it waits for the audits, whose probe pages come and go
            # in presentation\, and for the course pages; it then runs beside the review sheets
            if pkg is None and all(k in results for k in jobs if k != "review sheets"):
                pkg = ex.submit(run, [PY, os.path.join(FACTORY, "check_course_package.py"), os.path.join(course, workspace.MODULES)])
        if pkg is None:
            pkg = ex.submit(run, [PY, os.path.join(FACTORY, "check_course_package.py"), os.path.join(course, workspace.MODULES)])
        results["course package"] = pkg.result()
    for k in [x for x in jobs if x != "review sheets"] + ["course package"]:
        code, out = results[k]
        logged(k, out)
        if code != 0:
            fails.append(k)
            say.append("%s - FAIL:" % k.upper())
            # the audits name every element and its words (run_audits.summarise), so they keep more lines - no --json run to find them
            say += ["  " + x for x in lines_of("\n".join(y for y in out.splitlines() if not y.startswith("Built ")),
                                               40 if k.startswith("audits") else 12)]
    passed = not fails
    review = ""
    if want_review and passed:
        rcode, rout = results["review sheets"]
        if rcode == 0:                          # the sheets are the review now: the last review's folder is replaced
            import shutil
            shutil.rmtree(out_dir, ignore_errors=True)
            os.replace(pending, out_dir)
            rout = rout.replace(pending, out_dir)
        logged("review_sheets.mjs", rout)
        if rcode == 1:                          # not promoted: the next review still compares with the last one shown
            passed = False
            fails.append("task pages")
            say.append("TASK PAGES - FAIL (review_sheets.mjs answered every question by its own keys and checked every leader "
                       "line as the engine placed it - fix the drawing or the build sheet's \"labels\"):")
            say += ["  " + x for x in rout.splitlines() if "FAIL" in x]
        elif rcode == 0:
            first = rout.strip().splitlines()[0] if rout.strip() else ""
            n = re.search(r"Review sheets: (\d+) of (\d+) screens.*?on (\d+) sheet", first)
            review = (("VISUAL REVIEW (required, GUIDE 2f): %s of %s screens changed since the last review, on %s sheet(s) in\n  %s\n"
                       "  Give the sheets to ONE review subagent (model haiku or sonnet) with %s - it returns a short verdict."
                       % (n.group(1), n.group(2), n.group(3), out_dir, os.path.join(SKILLS, "course-factory", "compile", "REVIEW_PROMPT.md")))
                      if n and n.group(1) != "0" else
                      "Visual review: no screen changed since the last review - nothing new to look at.")
        else:
            notes.append("Review sheets not made (%s) - do the visual review by hand (GUIDE 2f)" % (lines_of(rout, 1) or ["?"])[0])
    log.close()
    for x in say:
        print(x)
    for x in notes:
        print(x)
    secs = time.time() - t0
    if passed:
        print("PASS %s - figures, compile + drawing check, words (instructor, trainee), navigation, audits 1280x800 %s, course package"
              " (%.0f s)" % (m, " ".join(sizes), secs))
        if review:
            print(review)
    else:
        print("FAIL %s - %s (%.0f s)" % (m, ", ".join(fails), secs))
    print("Full log: %s" % log.name)
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
