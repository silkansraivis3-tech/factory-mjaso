# -*- coding: utf-8 -*-
"""test_check_numbers - the course-wide number report (2.63.2).

    python -I test_check_numbers.py

A fixture course: approved scripts that state one limit as 20 ppm on a slide and 25 ppm in a question, fresh air as
20.9 % and 21 %, a flashpoint as 11 and 12 degrees; things that must NOT be listed (far-apart values sharing a word,
two limits stated together and repeated together, a draft script, an instructor page, the final test read twice).
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
SCRIPT = os.path.join(HERE, "check_numbers.py")
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


def block(out, name):
    """the lines of one DIFFERS group"""
    m = re.search(r"DIFFERS  [^\n]*\b%s\b[^\n]*\n((?:   .*\n)+)" % re.escape(name), out)
    return m.group(1) if m else ""


def main():
    tmp = tempfile.mkdtemp(prefix="check_numbers_")
    try:
        c = os.path.join(tmp, "course")
        sc = os.path.join(c, "working_claude", "script")
        put(os.path.join(sc, "M01.json"), {
            "module": 1, "status": "approved", "sources": ["IGF Code: the H2S limit is 40 ppm"],
            "screens": [{"id": "s01", "title": "Limits", "text": "The H2S exposure limit is 20 ppm over eight hours.\nFresh air holds 20.9 % oxygen.",
                         "visual": "a gauge reading 99 ppm"},
                        {"id": "s02", "text": "Methanol flashpoint 11 °C. Oxygen below 8 % and above 35 % is unsafe.\nFuel at 5 % oxygen cannot burn.",
                         "task": {"id": "t01", "question": "Which flashpoint is right?"}}]})
        put(os.path.join(sc, "M02.json"), {
            "module": 2, "status": "approved",
            "screens": [{"id": "s01", "text": "Oxygen below 8 % and above 35 % is unsafe."},
                        {"id": "s02", "text": "Fresh air: oxygen 21 %.",
                         "questions": [{"id": "q4", "question": "You must leave at an H2S level of 25 ppm or more. True?"}]},
                        {"id": "s03", "text": "Methanol flashpoint 12 °C. The pump runs 5 min, then 8 min."}]})
        put(os.path.join(sc, "M03.json"), {"module": 3, "status": "draft",
                                           "screens": [{"id": "s01", "text": "The H2S exposure limit is 22 ppm."}]})
        put(os.path.join(sc, "FINAL.json"), {"module": "final", "status": "approved",
                                             "screens": [{"id": "a01", "text": "The oxygen in air is 21 %."}]})
        mods = os.path.join(c, "modules")
        put(os.path.join(mods, "module04", "presentation", "index.html"),
            '<section id="s01"><p>The H2S exposure limit is 50 ppm for LNG staff.</p></section>'
            '<section id="s02"><p>Nitrogen 78 %.</p><script>var x="oxygen 30 %"</script></section>')
        put(os.path.join(mods, "module04", "instructor", "M04_PLAN.html"), '<section id="s01">The H2S exposure limit is 21 ppm.</section>')
        put(os.path.join(mods, "module05", "presentation", "index.html"),
            '<section id="s01"><p>The H2S exposure limit is 18 ppm.</p></section>')
        put(os.path.join(mods, "module05", "assessment", "final_a.html"), '<section id="a01">The oxygen in air is 21 %.</section>')

        code, out = run(c)
        check("exit 0 and a report: a difference is not a build block", code == 0 and "DIFFERS" in out, out)
        h2s = block(out, "h2s")
        check("20 ppm on a slide and 25 ppm in a question: the same quantity, both places named",
              re.search(r"20\s+1 place\(s\): M01 s01", h2s) and re.search(r"25\s+1 place\(s\): M02 q4", h2s), out)
        check("a built page with no script is read too (the module5 18 ppm), 50 ppm is too far to be the same limit",
              "18" in h2s and "module05/presentation" in h2s and not re.search(r"\b50\b", h2s), h2s)
        ox = block(out, "oxygen")
        check("fresh air 20.9 % against 21 %: both listed, with the slides", re.search(r"20\.9\s+1 place\(s\): M01 s01", ox) and "21" in ox and "M02 s02" in ox, out)
        check("... 5 % oxygen (far from 20.9, a different thing) and 8 / 35 (two limits, stated together twice) are not listed",
              not re.search(r"\s5\s+\d place", ox) and not re.search(r"\s(8|35)\s+\d place", ox), ox)
        fl = block(out, "flashpoint")
        check("a flashpoint of 11 and 12 degrees is listed, the temperature closeness is absolute (5 degrees)",
              re.search(r"11\s+1 place\(s\): M01 s02", fl) and re.search(r"12\s+1 place\(s\): M02 s03", fl), out)
        check("the final test is read once: its script, not also its page (the 21 % in FINAL a01, never module05 final_a)",
              "FINAL a01" in ox and "final_a.html" not in out, out)
        check("a draft script is never read (22 ppm), nor an instructor page (21 ppm), nor a source quote (40 ppm), picture brief (99 ppm), script tag (30 %)",
              "22" not in h2s and "M04_PLAN" not in out and not re.search(r"\b(40|99)\b", out) and "30" not in ox, out)
        check("5 min against 8 min in one place is no difference between two places", "min" not in out, out)

        code, strict = run(c, "--strict")
        check("--strict exits 1 when a quantity differs", code == 1, strict)
        code, js = run(c, "--json")
        try:
            rep = json.loads(js)["report"]
            ok = any("oxygen" in e["quantity"] and set(e["values"]) == {"20.9", "21"} for e in rep)
        except ValueError:
            ok = False
        check("--json gives the same report as data", ok, js)
        code, sp = run(c, "--from", "scripts")
        check("--from scripts leaves the built pages alone", "M05 s01" not in sp and "module05" not in sp, sp)

        # a consistent course: one value everywhere says nothing
        c2 = os.path.join(tmp, "course2")
        put(os.path.join(c2, "working_claude", "script", "M01.json"), {
            "module": 1, "status": "approved", "screens": [{"id": "s01", "text": "Oxygen 20.9 %."}, {"id": "s02", "text": "Oxygen 20,9 % again."}]})
        code, ok_out = run(c2)
        check("20.9 and 20,9 are one value: nothing is listed", code == 0 and "No quantity is stated with different values." in ok_out, ok_out)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("\n%s" % ("ALL PASS" if not FAILS else "%d FAILED" % len(FAILS)))
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
