# -*- coding: utf-8 -*-
"""test_module_folder - L43: every module in its own folder, complete, opening on its own.

    python test_module_folder.py

A course\\modules\\ folder with one good module is invented, then broken one way at a time. Pinned:
  * a complete module folder passes: START_HERE.html opens the presentation straight away, START_HERE_EXTENDED.html
    has a button for the presentation, every task, the module plan and the instructor notes, every file used is inside
    the folder, nothing comes from the internet;
  * each of these is caught: no extended start, a START HERE that does not open the presentation, a task with no
    button, the module plan with no button, a picture from the internet, a style reaching outside the module, a
    missing picture;
  * the check finds the module folders from the master folder, the course folder or the modules folder;
  * START_HERE_EXTENDED.html is instructor-only for the tablet publisher, like START_HERE.html.
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
TOOL = os.path.join(HERE, "check_module_folder.py")
PASS, FAIL = [], []


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print(("  ok    " if ok else "  FAIL  ") + name + (("  -> " + str(detail)[:400]) if detail and not ok else ""))


def run(folder):
    p = subprocess.run([sys.executable, TOOL, folder], capture_output=True, text=True, encoding="utf-8", errors="replace")
    return p.returncode, p.stdout + p.stderr


def w(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    io.open(path, "w", encoding="utf-8").write(text)


def good_module(m):
    w(os.path.join(m, "START_HERE.html"),
      '<!DOCTYPE html><html><head><meta http-equiv="refresh" content="0; url=presentation/module.html"></head>'
      '<body><a href="presentation/module.html">Open the presentation</a></body></html>')
    w(os.path.join(m, "START_HERE_EXTENDED.html"),
      '<!DOCTYPE html><html><head><link rel="stylesheet" href="assets/css/gb_page.css"></head><body>'
      '<a href="presentation/module.html">Presentation</a><a href="tasks/sc1.html">Self-check 1</a>'
      '<a href="tasks/mc.html">Module check</a><a href="instructor/M01_MODULE_PLAN.html">Module plan</a>'
      '<a href="instructor/M01_INSTRUCTOR_NOTES.md">Instructor notes</a></body></html>')
    w(os.path.join(m, "presentation", "module.html"),
      '<html><head><link rel="stylesheet" href="../assets/css/gb_page.css"><script src="../assets/js/run.js"></script></head>'
      '<body><img src="../assets/img/lng%20carrier.jpg"><div style="background:url(../assets/img/hull.png)"></div></body></html>')
    w(os.path.join(m, "tasks", "sc1.html"), '<html><body><img src="../assets/img/hull.png"></body></html>')
    w(os.path.join(m, "tasks", "mc.html"), '<html><body><script src="../assets/js/run.js"></script></body></html>')
    w(os.path.join(m, "instructor", "M01_MODULE_PLAN.html"), "<html><body>plan</body></html>")
    w(os.path.join(m, "instructor", "M01_INSTRUCTOR_NOTES.md"), "# notes\n")
    for f in ("css/gb_page.css", "js/run.js", "img/lng carrier.jpg", "img/hull.png"):
        w(os.path.join(m, "assets", f), "x")


def main():
    tmp = tempfile.mkdtemp(prefix="mf_")
    try:
        master = os.path.join(tmp, "GAS Basic")
        os.makedirs(os.path.join(master, "source_files"))
        mods = os.path.join(master, "course", "modules")
        m = os.path.join(mods, "M01_Gas_tankers")
        good_module(m)

        print("-- a complete module folder")
        code, out = run(master)
        check("a complete, self-contained module folder passes - found from the master folder", code == 0 and "M01_Gas_tankers - complete" in out, out)
        check("... and from the modules folder and the module folder itself", run(mods)[0] == 0 and run(m)[0] == 0)

        def broken(name, fn, needle):
            b = os.path.join(tmp, "b_" + name, "M01_Gas_tankers")
            shutil.copytree(m, b)
            fn(b)
            code, out = run(b)
            check("caught: " + name, code == 1 and needle in out, out)

        print("\n-- what it must catch")
        broken("no extended start", lambda b: os.remove(os.path.join(b, "START_HERE_EXTENDED.html")), "START_HERE_EXTENDED.html - the page with a button")
        broken("a START HERE that does not open the presentation",
               lambda b: w(os.path.join(b, "START_HERE.html"), "<html><body>Welcome</body></html>"), "does not open the presentation straight away")
        broken("a task with no button on the extended start",
               lambda b: w(os.path.join(b, "tasks", "sc2.html"), "<html></html>"), "has no button for tasks/sc2.html")
        broken("the module plan with no button",
               lambda b: w(os.path.join(b, "START_HERE_EXTENDED.html"),
                           '<a href="presentation/module.html">P</a><a href="tasks/sc1.html">1</a><a href="tasks/mc.html">M</a>'
                           '<a href="instructor/M01_INSTRUCTOR_NOTES.md">N</a>'), "no button for instructor/M01_MODULE_PLAN.html")
        broken("a picture fetched from the internet",
               lambda b: w(os.path.join(b, "tasks", "sc1.html"), '<img src="https://example.com/x.png">'), "fetches from the internet")
        broken("a style reaching outside the module folder",
               lambda b: w(os.path.join(b, "tasks", "mc.html"), '<link rel="stylesheet" href="../../shared/gb.css">'), "reaches outside the module folder")
        broken("a missing picture",
               lambda b: os.remove(os.path.join(b, "assets", "img", "hull.png")), "uses ../assets/img/hull.png, which is not there")

        print("\n-- the start pages are the instructor's")
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "course-tablet-publisher", "scripts"))
        import re
        import gates
        pats = gates.load_platform()["role_rules"]["instructor_only_filename_patterns"]
        for n in ("START_HERE.html", "START_HERE_EXTENDED.html"):
            check("the tablet publisher treats %s as instructor-only" % n, any(re.search(p, n, re.I) for p, _ in pats))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("\n" + "=" * 72)
    print("%d passed, %d failed" % (len(PASS), len(FAIL)))
    if FAIL:
        return 1
    print("\nEvery module sits in its own folder, starts with a double-click, and needs nothing outside it.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
