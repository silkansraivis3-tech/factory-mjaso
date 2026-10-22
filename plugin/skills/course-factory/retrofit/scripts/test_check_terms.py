# -*- coding: utf-8 -*-
"""test_check_terms - the course-wide terminology report (2.63.2).

    python -I test_check_terms.py

A fixture course: M01 and M02 approved scripts that name one quantity two ways, a draft script (never read), a
module with no script (read from its built page), an instructor page (never read).
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "check_terms.py")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
FAILS = []


def check(name, ok, detail=""):
    if not ok:
        FAILS.append(name)
    print(("  ok    " if ok else "  FAIL  ") + name + (("  -> " + str(detail)[-700:]) if detail and not ok else ""))


def put(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text if isinstance(text, str) else json.dumps(text))


def run(course, *args):
    p = subprocess.run([sys.executable, "-I", SCRIPT, course, *args], capture_output=True, text=True, encoding="utf-8", errors="replace")
    return p.returncode, p.stdout + p.stderr


def main():
    tmp = tempfile.mkdtemp(prefix="check_terms_")
    try:
        c = os.path.join(tmp, "course")
        sc = os.path.join(c, "working_claude", "script")
        put(os.path.join(sc, "M01.json"), {
            "module": 1, "status": "approved", "sources": ["IGF Code: the LFL is the lower flammable limit"],
            "screens": [{"id": "s01", "title": "Limits", "text": "Gas below the LEL cannot burn.", "visual": "a LFL chart"},
                        {"id": "s02", "title": "Rooms", "text": "Two LELs are set.\nThe hazardous area is marked.",
                         "task": {"id": "t01", "question": "Where is the bunkering station?"}}]})
        put(os.path.join(sc, "M02.json"), {
            "module": 2, "status": "approved",
            "screens": [{"id": "s01", "text": "The LFL is read on the detector."},
                        {"id": "s02", "notes": "Walk to the bunker station.", "text": "The hazardous area ends at the door."}]})
        put(os.path.join(sc, "M03.json"), {"module": 3, "status": "draft",
                                           "screens": [{"id": "s01", "text": "A hazardous zone, a hazardous space."}]})
        mods = os.path.join(c, "modules")
        put(os.path.join(mods, "module04", "presentation", "index.html"),
            '<html><body><section class="slide" id="s01"><p>A fuel preparation room.</p></section>'
            '<section class="slide" id="s02"><p>A fuel preparation space.</p><script>var x="fuel preparation space"</script></section></body></html>')
        put(os.path.join(mods, "module04", "instructor", "M04_PLAN.html"),
            '<section id="s01">The hazardous zone and the dry powder.</section>')

        code, out = run(c)
        check("exit 0 and a report: a mixed group is not a build block", code == 0 and "MIXED  LEL" in out, out)
        check("the five default pairs are loaded", "5 synonym group(s)" in out, out)
        lel = out.split("MIXED  LEL")[1].split("MIXED")[0]
        check("LEL / LFL: both forms counted, plural LELs too; the source quote and the picture brief are not (LEL 2, LFL 1)",
              re.search(r"LEL\s+2 x", lel) and re.search(r"LFL\s+1 x", lel), lel)
        check("... each variant with the module and slide it is used in",
              "M01 s01" in lel and "M01 s02" in lel and "M02 s01" in lel and re.search(r"LFL\s+1 x  in M02: M02 s01", lel), lel)
        check("a task's words are found by the slide that holds it (bunkering station), the instructor cue too (bunker station)",
              "MIXED  bunkering station" in out and "bunker station" in out and "M02 s02" in out, out)
        check("a group used under one name only is consistent and not listed (hazardous area in M01 / M02, no variant)",
              "MIXED  hazardous area" not in out, out)
        check("a draft script is never read (its hazardous zone / space do not show)", "hazardous zone" not in out and "M03" not in out, out)
        check("a module with no script is read from its built page, by section id, script and style tags ignored",
              "MIXED  fuel preparation room" in out and "module04/presentation/index.html s02" in out
              and re.search(r"fuel preparation space\s+1 x", out) and re.search(r"fuel preparation room\s+1 x", out), out)
        check("an instructor page is never read (its dry powder / hazardous zone do not show)",
              "dry powder" not in out and "M04_PLAN" not in out, out)
        code, out_s = run(c, "--strict")
        check("--strict exits 1 when a group is mixed", code == 1, out_s)
        code, out_s = run(c, "--from", "scripts")
        check("--from scripts leaves the built page alone", "fuel preparation" not in out_s, out_s)

        # the course's own list: adds a pair, replaces a default, an empty list drops one
        put(os.path.join(c, "working_claude", "terms.json"), {
            "_note": "a comment", "hazardous area": ["hazardous space", "hazardous zone"],
            "LEL": [], "detector": ["detection head"]})
        put(os.path.join(sc, "M02.json"), {
            "module": 2, "status": "approved",
            "screens": [{"id": "s01", "text": "The detector and the detection head."},
                        {"id": "s02", "text": "The hazardous space is marked."}]})
        code, out2 = run(c)
        check("working_claude/terms.json: a new pair is judged, an empty list drops a default (LEL no longer listed)",
              "MIXED  detector" in out2 and "detection head" in out2 and "MIXED  LEL" not in out2 and "5 synonym group(s)" in out2, out2)
        check("... the same preferred term replaces the default entry (hazardous area now has its own variants)",
              "MIXED  hazardous area" in out2 and "hazardous space" in out2, out2)
        code, js = run(c, "--json")
        try:
            rep = json.loads(js)["report"]
            ok = any(r["preferred"] == "detector" and r["mixed"] for r in rep)
        except ValueError:
            ok = False
        check("--json gives the same report as data", ok, js)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("\n%s" % ("ALL PASS" if not FAILS else "%d FAILED" % len(FAILS)))
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
