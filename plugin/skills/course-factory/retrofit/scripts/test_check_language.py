# -*- coding: utf-8 -*-
"""test_check_language - COURSE_LANGUAGE drift, declared by name or by code.

    python -I test_check_language.py

A fixture course of English slides and one Latvian task page: --declare English, EN, en and English+LV all read the
slides as the declared language, and the Latvian page drifts unless Latvian is declared too.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "check_language.py")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
FAILS = []

EN = ("<p>The cargo tank is filled before the ship leaves the berth, and the officer checks the pressure of each tank "
      "with the gauge that is on the deck. If the pressure is too high, the crew must stop the pump and report it to "
      "the master, who will decide what is done next.</p>")
LV = ("<p>Kravas tvertne ir jāpiepilda pirms kuģis atstāj piestātni, un virsnieks pārbauda spiedienu katrā tvertnē. Ja "
      "spiediens ir par augstu, apkalpei jāaptur sūknis un tas jāziņo kapteinim, kas arī izlemj, kas ir jādara tālāk, "
      "un tikai pēc tam var turpināt darbu ar kravu vai bez tās.</p>")


def check(name, ok, detail=""):
    if not ok:
        FAILS.append(name)
    print(("  ok    " if ok else "  FAIL  ") + name + (("  -> " + str(detail)[-700:]) if detail and not ok else ""))


def put(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def run(course, *args):
    p = subprocess.run([sys.executable, "-I", SCRIPT, course, "--json", *args], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    try:
        return p.returncode, json.loads(p.stdout)
    except ValueError:
        return p.returncode, {"error": p.stdout + p.stderr}


def main():
    tmp = tempfile.mkdtemp(prefix="check_language_")
    try:
        c = os.path.join(tmp, "course")
        put(os.path.join(c, "module01", "presentation", "index.html"), "<html><body>%s</body></html>" % EN)
        put(os.path.join(c, "module02", "presentation", "index.html"), "<html><body>%s</body></html>" % EN)
        for name in ("English", "EN", "en", "english"):
            code, rep = run(c, "--declare", name, "--strict")
            check("--declare %s: the English slides are in the course language" % name,
                  code == 0 and rep.get("files") and not rep.get("drift"), rep)
        put(os.path.join(c, "module02", "tasks", "q01.html"), "<html><body>%s</body></html>" % LV)
        code, rep = run(c, "--declare", "EN", "--strict")
        check("--declare EN: the Latvian task page drifts, the English slides do not",
              code == 1 and [d["file"].replace("\\", "/") for d in rep.get("drift", [])] == ["module02/tasks/q01.html"], rep)
        code, rep = run(c, "--declare", "EN+LV", "--strict")
        check("--declare EN+LV: both languages are the course's", code == 0 and not rep.get("drift"), rep)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("\n%s" % ("ALL PASS" if not FAILS else "%d FAILED" % len(FAILS)))
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
