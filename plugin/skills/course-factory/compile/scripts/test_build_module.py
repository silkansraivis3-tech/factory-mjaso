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
    mine = OUT.replace("  - module02/tasks/sc1_a.html has no <title>", "  - module01/presentation/index.html has no data-title")
    check("a module's own finding beside the course-page ones fails it",
          b.own_package_findings(1, mine, "module01")[0] == 1)
    check("a passing package and a stop (exit 2) are passed through untouched",
          b.own_package_findings(0, "Ready", "module01") == (0, "Ready", 0)
          and b.own_package_findings(2, "Stopped", "module01") == (2, "Stopped", 0))
    print("\n%s" % ("ALL PASS" if not FAILS else "%d FAILED" % len(FAILS)))
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
