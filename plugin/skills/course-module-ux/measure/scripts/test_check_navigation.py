#!/usr/bin/env python3
"""test_check_navigation - check_navigation.py sees the way out the shared engine provides (finding 6).

    python test_check_navigation.py

A compiled task page has no inline script: its Back link (a.gbt-topback, href="#") is wired by the shared
course-task-ux/assets/gb_answer.js. Judged on inline JS alone the page was "trapped". Pinned:
  * a task page that loads gb_answer.js is not trapped (the engine is read from the page's own assets folder);
  * the same page with the engine file missing from disk is still not trapped (a known shared engine, by name);
  * a page with no script and no link out is still trapped; so is one loading an unknown script with no way out.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
CHECK = os.path.join(HERE, "check_navigation.py")
ENGINE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(HERE))), "course-task-ux", "assets", "gb_answer.js")
PASS, FAIL = [], []

PAGE = """<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><title>T</title></head><body>
<header><a class="gbt-topback" href="#"><span class="gbt-ico">&#9664;</span> Back</a></header>
<main><section class="gb-task"><h1>Task</h1><button type="button">Check</button></section></main>
%s</body></html>"""


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print(("  ok    " if ok else "  FAIL  ") + name + (("  -> " + str(detail)[:600]) if detail and not ok else ""))


def run(path):
    p = subprocess.run([sys.executable, CHECK, path], capture_output=True, text=True, encoding="utf-8", errors="replace")
    return p.returncode, p.stdout


def main():
    tmp = tempfile.mkdtemp(prefix="nav_")
    try:
        os.makedirs(os.path.join(tmp, "assets"))
        os.makedirs(os.path.join(tmp, "tasks"))
        shutil.copy(ENGINE, os.path.join(tmp, "assets", "gb_answer.js"))
        with_engine = os.path.join(tmp, "tasks", "t1.html")
        open(with_engine, "w", encoding="utf-8").write(PAGE % '<script src="../assets/gb_answer.js"></script>\n')
        code, out = run(with_engine)
        check("a task page that loads the shared gb_answer.js is not trapped", code == 0 and "trapped" not in out, out)

        os.remove(os.path.join(tmp, "assets", "gb_answer.js"))
        code, out = run(with_engine)
        check("... nor when the engine file cannot be read from here (a known shared engine, by name)",
              code == 0 and "trapped" not in out, out)

        bare = os.path.join(tmp, "tasks", "t2.html")
        open(bare, "w", encoding="utf-8").write(PAGE % "")
        code, out = run(bare)
        check("a page with no script and no link out is still trapped", code == 1 and "trapped" in out, out)

        other = os.path.join(tmp, "tasks", "t3.html")
        open(os.path.join(tmp, "assets", "other.js"), "w", encoding="utf-8").write("var x = 1;")
        open(other, "w", encoding="utf-8").write(PAGE % '<script src="../assets/other.js"></script>')
        code, out = run(other)
        check("an unknown script that offers no way out does not rescue it", code == 1 and "trapped" in out, out)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("\n%d passed, %d failed" % (len(PASS), len(FAIL)))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
