# -*- coding: utf-8 -*-
"""test_check_task_pages - the dead-markup sweep judges the page's own markup, not what it carries for others.

    python test_check_task_pages.py

Pinned (2.38.0, found on the compiled IGF pilot pages):
  * an id named by a selector in another element's data attribute - <svg data-kit="#kit-q10-1"> and its
    <script type="application/json" id="kit-q10-1">, the figure kit's documented way - is read, not dead;
  * the ids inside a drawing the compiler placed in the page (svg.taskfig - the course's shared figure file, the same
    the deck shows) are the drawing's own names and are not judged here;
  * an id outside both that nothing reads is still a finding.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
CHECK = os.path.join(HERE, "check_task_pages.py")
PASS, FAIL = [], []

PAGE = """<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><title>SC1 — Test</title><style>.wrap{margin:0}</style></head>
<body><main class="wrap">
<svg class="taskfig" data-fig="ga" viewBox="0 0 10 10"><g id="sp-tank" data-name="Fuel tank"><rect id="hull-line" width="5" height="5"/></g></svg>
<svg data-kit="#kit-q10-1"></svg><script type="application/json" id="kit-q10-1">{"size":[10,10],"parts":[]}</script>
%s
</main></body></html>
"""


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print(("  ok    " if ok else "  FAIL  ") + name + (("  -> " + str(detail)[:600]) if detail and not ok else ""))


def sweep(extra):
    tmp = tempfile.mkdtemp(prefix="ctp_")
    try:
        p = os.path.join(tmp, "page.html")
        with open(p, "w", encoding="utf-8") as f:
            f.write(PAGE % extra)
        r = subprocess.run([sys.executable, CHECK, p, "--only", "deadmarkup"], capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        return r.returncode, r.stdout + r.stderr
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    code, out = sweep("")
    check("a figure-kit spec named by data-kit=\"#id\" is read", "kit-q10-1" not in out, out)
    check("the ids of a drawing placed by the compiler (svg.taskfig) are not judged on the task page",
          "sp-tank" not in out and "hull-line" not in out, out)
    check("... so the page passes", code == 0, out)
    code, out = sweep('<p id="orphan">x</p>')
    check("an id of the page's own that nothing reads is still a finding", code == 1 and 'id="orphan"' in out, out)
    print("\n%d passed, %d failed" % (len(PASS), len(FAIL)))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
