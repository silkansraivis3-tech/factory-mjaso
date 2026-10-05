# -*- coding: utf-8 -*-
"""test_course_package - L45: a course folder the classroom takes as it is, with every task opening from its slide.

    python test_course_package.py

A two-module course is built exactly to knowledge/classroom-system.json (the classroom's own rules) - module01 with a
self-check and a module check, module02 the final assessment - and must pass the factory's checks AND the classroom's
importer (course-tablet-publisher/vendor/package-core.mjs, run with Node). Then it is broken one way at a time - each
of the classroom's "before handing over" points, and the factory's own (L35, L43) - and every break must be caught.
Also pinned: the vendored importer is byte-identical to the classroom system's, when that repository is on this computer.
"""
from __future__ import annotations

import io
import os
import shutil
import subprocess
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "check_course_package.py")
SKILLS = os.path.dirname(os.path.dirname(HERE))
VENDOR = os.path.join(SKILLS, "course-tablet-publisher", "vendor", "package-core.mjs")
ORIGINAL = r"C:\Users\raiviss\Desktop\tablet-system-win\admin\package-core.mjs"
PASS, FAIL = [], []
D = "\u2014"


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print(("  ok    " if ok else "  FAIL  ") + name + (("  -> " + str(detail)[:600]) if detail and not ok else ""))


def run(folder, *extra):
    p = subprocess.run([sys.executable, TOOL, folder] + list(extra), capture_output=True, text=True, encoding="utf-8", errors="replace")
    return p.returncode, p.stdout + p.stderr


def w(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    io.open(path, "w", encoding="utf-8", newline="\n").write(text)


TASK = ("<!DOCTYPE html><html><head><meta charset=\"utf-8\"><title>%s</title><link rel=\"stylesheet\" href=\"../assets/css/task.css\"></head>"
        "<body><img src=\"../assets/img/hull.jpg\"><script src=\"../assets/js/task.js\"></script><script>"
        "addEventListener('message', e => { if (e.data && e.data.type === 'gb-timer') {} });"
        "function done(ok, total, items, head) { window.parent.postMessage({type: 'gb-task-done', code: '%s', title: 'x', ok: ok, total: total,"
        " head: head, items: items, answered: total, of: total, timeout: false}, '*'); }%s</script></body></html>")


def good_course(c):
    w(os.path.join(c, "COURSE.html"), "<!DOCTYPE html><html><head><title>GAS Basic</title>"
      "<meta name=\"description\" content=\"Basic training for liquefied gas tanker cargo operations.\"></head><body>"
      "<a href=\"module01/START_HERE.html\">Module 1</a><a href=\"module02/START_HERE.html\">Final assessment</a></body></html>")
    w(os.path.join(c, "_course_shell", "course_map.js"), 'window.COURSE_MAP = [{"code":"module01","title":"Gas tankers","entry":"presentation/index.html"},'
      '{"code":"module02","title":"Final assessment","entry":"presentation/index.html"}];')
    m = os.path.join(c, "module01")
    w(os.path.join(m, "presentation", "index.html"),
      "<!DOCTYPE html><html><head><title>GAS Basic · Module 1 " + D + " Gas tankers · Instructor presentation</title>"
      "<link rel=\"stylesheet\" href=\"../assets/css/deck.css\"></head><body>"
      "<section class=\"slide active\" id=\"s01\" data-title=\"Why gas tankers are different\" data-kind=\"Theory\" data-cue=\"- Ask who has sailed on one.\">"
      "<h2>Why gas tankers are different</h2><img src=\"../assets/img/hull.jpg\"></section>"
      "<section class=\"slide\" id=\"t01\" data-kind=\"Task\" data-activity=\"SC1\" data-task-href=\"../tasks/sc1_keeping_the_cargo_liquid.html\""
      " data-title=\"SC1 " + D + " Keeping the cargo liquid\"><p class=\"act-code\">SC1</p><h2 class=\"act-title\">Keeping the cargo liquid</h2></section>"
      "<section class=\"slide\" id=\"p01\" data-kind=\"Task\" data-activity=\"P1\" data-link-hint=\"At the gas-measurement bench\" data-title=\"P1 " + D + " Take a reading\"></section>"
      "<section class=\"slide\" id=\"t02\" data-kind=\"Check\" data-activity=\"MC\" data-task-href=\"../assessment/check.html\" data-title=\"MC " + D + " Module check\"></section>"
      "<script src=\"../assets/js/deck.js\"></script></body></html>")
    w(os.path.join(m, "START_HERE.html"), "<meta http-equiv=\"refresh\" content=\"0; url=presentation/index.html\"><a href=\"presentation/index.html\">Open</a>")
    w(os.path.join(m, "START_HERE_EXTENDED.html"), "<a href=\"presentation/index.html\">Presentation</a><a href=\"tasks/sc1_keeping_the_cargo_liquid.html\">SC1</a>"
      "<a href=\"assessment/check.html\">Module check</a><a href=\"instructor/module_plan.html\">Plan</a>")
    w(os.path.join(m, "tasks", "sc1_keeping_the_cargo_liquid.html"), TASK % ("SC1 " + D + " Keeping the cargo liquid", "SC1", "done(3, 4, [{t: '1.', ok: true}], '');"))
    w(os.path.join(m, "assessment", "check.html"), TASK % ("MC " + D + " Module check", "MC", "var pass = 4; done(5, 6, [{t: '1.', ok: true}], 5 >= pass ? 'PASSED' : 'NOT PASSED');"))
    w(os.path.join(m, "assessment", "check_answer_key.html"), "<p>1 A, 2 C</p>")
    w(os.path.join(m, "instructor", "module_plan.html"), "<p>plan</p>")
    for f in ("css/task.css", "css/deck.css", "js/task.js", "js/deck.js", "img/hull.jpg"):
        w(os.path.join(m, "assets", f), "x")
    f2 = os.path.join(c, "module02")
    w(os.path.join(f2, "presentation", "index.html"),
      "<title>GAS Basic · Module 2 " + D + " Final assessment</title><section class=\"slide active\" data-title=\"Final assessment\" data-kind=\"Check\""
      " data-activity=\"FA\" data-task-href=\"../assessment/final.html\"></section>")
    w(os.path.join(f2, "START_HERE.html"), "<a href=\"presentation/index.html\">Open</a>")
    w(os.path.join(f2, "START_HERE_EXTENDED.html"), "<a href=\"presentation/index.html\">P</a><a href=\"assessment/final.html\">Final</a>")
    w(os.path.join(f2, "assessment", "final.html"), TASK.replace("../assets/css/task.css", "../assets/final.css").replace("<img src=\"../assets/img/hull.jpg\">", "")
      .replace("<script src=\"../assets/js/task.js\"></script>", "") % ("FA " + D + " Final assessment", "FA", "done(30, 36, [{t: '1.', ok: true}], 30 >= 26 ? 'PASSED' : 'NOT PASSED');"))
    w(os.path.join(f2, "assets", "final.css"), "x")


def main():
    tmp = tempfile.mkdtemp(prefix="cp_")
    try:
        master = os.path.join(tmp, "GAS_Basic")
        os.makedirs(os.path.join(master, "source_files"))
        os.makedirs(os.path.join(master, "course", "to_review"))
        os.makedirs(os.path.join(master, "course", "working_claude"))
        c = os.path.join(master, "course", "modules")
        good_course(c)

        print("-- a course folder built to the classroom's rules")
        code, out = run(master)
        node = shutil.which("node")
        check("it passes - found from the master folder", code == 0 and "Ready: the classroom takes this folder as it is" in out, out)
        if node:
            check("the classroom's own importer ran on it and would add it as GAS Basic, two modules",
                  'would add it as "GAS Basic" (id gas-basic, version 1.0.0)' in out and "2 module(s)" in out, out)
        else:
            check("without Node the factory says plainly that the importer did not run", "Node is not installed" in out, out)
        check("... from the course folder and the modules folder too", run(os.path.join(master, "course"))[0] == 0 and run(c)[0] == 0)

        def broken(name, fn, needle, importer=False):
            b = os.path.join(tmp, "b_" + str(len(PASS) + len(FAIL)), "modules")
            shutil.copytree(c, b)
            fn(b)
            code, out = run(b) if importer else run(b, "--no-importer")
            check("caught: " + name, code == 1 and needle in out, out)

        print("\n-- the classroom's own before-handover list")
        broken("a module without presentation/index.html", lambda b: os.remove(os.path.join(b, "module01", "presentation", "index.html")),
               "module01/presentation/index.html is missing")
        broken("a slide without data-title", lambda b: w(os.path.join(b, "module01", "presentation", "index.html"),
               io.open(os.path.join(c, "module01", "presentation", "index.html"), encoding="utf-8").read().replace(' data-title="Why gas tankers are different"', "")),
               "module01 slide 1 (s01) has no data-title")
        broken("a task slide pointing at a page that is not there", lambda b: os.remove(os.path.join(b, "module01", "tasks", "sc1_keeping_the_cargo_liquid.html")),
               "opens ../tasks/sc1_keeping_the_cargo_liquid.html, which is not there")
        broken("a task slide with neither a page nor a hint", lambda b: w(os.path.join(b, "module01", "presentation", "index.html"),
               io.open(os.path.join(c, "module01", "presentation", "index.html"), encoding="utf-8").read().replace(' data-link-hint="At the gas-measurement bench"', "")),
               "says neither where (data-task-href) nor how (data-link-hint)")
        broken("a task page that never reports its result", lambda b: w(os.path.join(b, "module01", "tasks", "sc1_keeping_the_cargo_liquid.html"),
               "<title>SC1 " + D + " Keeping the cargo liquid</title><p>no report</p>"), "never reports its result (gb-task-done)")
        broken("a module check without PASSED / NOT PASSED", lambda b: w(os.path.join(b, "module01", "assessment", "check.html"),
               (TASK % ("MC " + D + " Module check", "MC", "done(5, 6, [], '');"))), "must report head 'PASSED' or 'NOT PASSED'")
        broken("a script from the internet", lambda b: w(os.path.join(b, "module01", "tasks", "sc1_keeping_the_cargo_liquid.html"),
               (TASK % ("SC1 " + D + " Keeping the cargo liquid", "SC1", "done(1,1,[],'');")).replace("../assets/js/task.js", "https://cdn.example.com/x.js")),
               "loads a script from the internet")
        broken("a file over 6 MB", lambda b: open(os.path.join(b, "module01", "assets", "img", "big.jpg"), "wb").write(b"\0" * (6 * 1024 * 1024 + 1)),
               "the classroom takes at most 6 MB per file")
        broken("a working folder inside the course", lambda b: w(os.path.join(b, "notes", "draft.html"), "x"), "notes\\ is not a module")
        broken("a trainee page linking back to START_HERE.html", lambda b: w(os.path.join(b, "module01", "tasks", "sc1_keeping_the_cargo_liquid.html"),
               (TASK % ("SC1 " + D + " Keeping the cargo liquid", "SC1", "done(1,1,[],'');")).replace("<body>", "<body><a href=\"../START_HERE.html\">Back</a>")),
               "(a trainee page) links to module01/START_HERE.html, which is instructor-only")
        broken("a space in a file name", lambda b: shutil.copy(os.path.join(b, "module01", "assets", "img", "hull.jpg"), os.path.join(b, "module01", "assets", "img", "lng carrier.jpg")),
               "a space in the name: module01/assets/img/lng carrier.jpg")

        print("\n-- the factory's own rules for it")
        broken("a task page whose title does not start with its code", lambda b: w(os.path.join(b, "module01", "tasks", "sc1_keeping_the_cargo_liquid.html"),
               TASK % ("Keeping the cargo liquid", "SC1", "done(1,1,[],'');")), 'its <title> must be "SC1 ' + D + ' <title>"')
        broken("a task page no slide opens", lambda b: w(os.path.join(b, "module01", "tasks", "sc2_orphan.html"), TASK % ("SC2 " + D + " Orphan", "SC2", "done(1,1,[],'');")),
               "module01/tasks/sc2_orphan.html is opened by no slide")
        broken("two slides opening one page", lambda b: w(os.path.join(b, "module01", "presentation", "index.html"),
               io.open(os.path.join(c, "module01", "presentation", "index.html"), encoding="utf-8").read().replace(
                   'data-activity="P1" data-link-hint="At the gas-measurement bench"', 'data-activity="SC9" data-task-href="../tasks/sc1_keeping_the_cargo_liquid.html"')),
               "one slide, one task page")
        broken("a task list page for the trainee (L35)", lambda b: w(os.path.join(b, "module01", "tasks", "index.html"), "<a href=\"sc1_keeping_the_cargo_liquid.html\">1</a>"),
               "tasks/index.html is a task list")
        broken("a style reaching outside the module (L43)", lambda b: w(os.path.join(b, "module01", "tasks", "sc1_keeping_the_cargo_liquid.html"),
               (TASK % ("SC1 " + D + " Keeping the cargo liquid", "SC1", "done(1,1,[],'');")).replace("../assets/css/task.css", "../../module02/assets/final.css")),
               "reaches outside its module")
        broken("the course map not matching the modules", lambda b: w(os.path.join(b, "_course_shell", "course_map.js"),
               'window.COURSE_MAP = [{"code":"module01","title":"Gas tankers","entry":"presentation/index.html"}];'), "_course_shell/course_map.js lists module01, the folder has module01, module02")
        broken("no START_HERE_EXTENDED.html (L43)", lambda b: os.remove(os.path.join(b, "module02", "START_HERE_EXTENDED.html")), "module02/START_HERE_EXTENDED.html is missing")
        if node:
            print("\n-- the classroom's importer itself")
            broken("a missing style the importer refuses", lambda b: os.remove(os.path.join(b, "module01", "assets", "css", "task.css")),
                   "the classroom's importer: Link outside the package", importer=True)

        print("\n-- the importer copy is the classroom's own")
        if os.path.isfile(ORIGINAL):
            a = io.open(ORIGINAL, encoding="utf-8").read().replace("\r\n", "\n").strip()
            b = io.open(VENDOR, encoding="utf-8").read().replace("\r\n", "\n").strip()
            check("vendor/package-core.mjs is byte-identical to the classroom system's admin/package-core.mjs", a == b,
                  "the classroom's importer changed - copy it again: %s -> %s" % (ORIGINAL, VENDOR))
        else:
            check("(the classroom system is not on this computer - the copy cannot be compared here)", os.path.isfile(VENDOR))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("\n" + "=" * 72)
    print("%d passed, %d failed" % (len(PASS), len(FAIL)))
    if FAIL:
        return 1
    print("\nA course folder built to the classroom's rules passes the factory and the classroom's own importer;\n"
          "every point of the classroom's before-handover list is caught when it is broken.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
