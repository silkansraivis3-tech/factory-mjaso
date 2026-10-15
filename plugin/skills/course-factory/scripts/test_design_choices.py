# -*- coding: utf-8 -*-
"""test_design_choices - L26 (2.30.0): the person's design choice, made after hearing the risk, is kept and obeyed.

    python test_design_choices.py

A choice is written once into the course's STANDARDS.md, found from any folder a check is given (the master folder,
course\\, course\\modules\\, one module), names only a design rule, and lives beside the ordinary standards
fix.py writes. The checks that obey it are tested with their own tools (test_course_package, test_content_script,
course-module-ui test_design_system).
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
sys.path.insert(0, HERE)
import design_choices as dc  # noqa: E402

PASS, FAIL = [], []


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print(("  ok    " if ok else "  FAIL  ") + name + (("  -> " + str(detail)[:500]) if detail and not ok else ""))


def run(*a):
    p = subprocess.run([sys.executable] + list(a), capture_output=True, text=True, encoding="utf-8", errors="replace")
    return p.returncode, p.stdout + p.stderr


def main():
    tmp = tempfile.mkdtemp(prefix="dc_")
    try:
        master = os.path.join(tmp, "GAS_Basic")
        work = os.path.join(master, "course")
        for d in ("source_files", os.path.join("course", "working_claude"), os.path.join("course", "modules", "module01", "presentation")):
            os.makedirs(os.path.join(master, d))

        print("-- the rules a choice can depart from are design only")
        code, out = run(os.path.join(HERE, "design_choices.py"), "rules")
        check("the list names the recap, the picture viewer and the brand, each with the risk to say",
              code == 0 and all(k in out for k in ("recap", "picture-viewer", "brand", "risk to say")), out)
        material = ("programme", "ilo", "hours", "source", "words", "script")
        check("... and nothing of the course material", not any(m in k for k in dc.RULES for m in material), sorted(dc.RULES))
        try:
            dc.add(work, "main-ilo", "reword the Main ILO", "I want it shorter")
            check("a choice against a rule that is not design is refused", False)
        except ValueError as e:
            check("a choice against a rule that is not design is refused", "not a design rule" in str(e), e)

        print("\n-- written once, found from anywhere")
        n = dc.add(work, "recap", "No recap slide", 'the instructor "sums up" himself', "the modules end differently")
        text = io.open(os.path.join(work, "working_claude", "STANDARDS.md"), encoding="utf-8").read()
        check("it is standard S1 in STANDARDS.md, tagged with the rule and the risk told",
              n == 1 and "S1 No recap slide (" in text and "[departs from: recap; risk told: the modules end differently]" in text, text)
        for where, f in (("the master folder", master), ("course\\", work), ("course\\modules\\", os.path.join(work, "modules")),
                         ("one module", os.path.join(work, "modules", "module01"))):
            got = dc.load(f).get("recap")
            check("found from %s" % where, got and got["n"] == 1 and got["said"] == "the instructor 'sums up' himself", got)
        check("the label names the choice, the date and the words", dc.label(dc.load(work)["recap"]).startswith("the operator's choice S1 ("))
        keep, notes = dc.split(["a", "b"], dc.load(work), "recap", lambda p: p == "a")
        check("split moves only what the choice covers into notes", keep == ["b"] and notes and notes[0].startswith("a - the operator's choice S1"), (keep, notes))
        keep, notes = dc.split(["a"], dc.load(work), "brand", lambda p: True)
        check("... and nothing for a rule nobody chose against", keep == ["a"] and not notes)

        print("\n-- beside the ordinary standards")
        code, out = run(os.path.join(HERE, "fix.py"), "standard", work, "--add", "Text bigger everywhere", "--said", "text bigger")
        code2, out2 = run(os.path.join(HERE, "fix.py"), "standard", work, "--add", "Our own blue on the end slide", "--said", "I like this blue",
                          "--departs", "brand", "--risk", "it is not the brand blue")
        st = dc.standards(work)
        check("fix.py standard writes an ordinary standard S2 and, with --departs, a design choice S3",
              code == 0 and code2 == 0 and [(s["n"], s["rule"]) for s in st] == [(1, "recap"), (2, ""), (3, "brand")], (out, out2, st))
        check("an ordinary standard is not a choice", set(dc.load(work)) == {"recap", "brand"})
        p = os.path.join(work, "working_claude", "STANDARDS.md")
        text = io.open(p, encoding="utf-8").read()
        io.open(p, "w", encoding="utf-8").write("\n".join(l for l in text.splitlines() if not l.startswith("S3 ")) + "\n")
        check("the person removes a choice by deleting its line - and it is gone", "brand" not in dc.load(work))
        check("... and its number is never given again", dc.add(work, "motion", "Keep the logo spinning", "I like it") == 3)
        code, out = run(os.path.join(HERE, "design_choices.py"), "list", master)
        check("list shows each choice with the rule, the words and the risk", code == 0 and "S1" in out and "against: recap" in out
              and "risk told: the modules end differently" in out and "S3" in out, out)

        print("\n-- every skill says it near the top, so a skill loaded alone still listens")
        skills = os.path.dirname(os.path.dirname(HERE))
        for d in sorted(os.listdir(skills)):
            p = os.path.join(skills, d, "SKILL.md")
            if not os.path.isfile(p):
                continue
            head = "\n".join(io.open(p, encoding="utf-8").read().splitlines()[:110])      # near the top, before the lanes
            check("%s: the person decides the design, a choice is recorded and never changed back" % d,
                  "design_choices.py add" in head and "back" in head and "risk" in head, head[-400:])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("\n" + "=" * 72)
    print("%d passed, %d failed" % (len(PASS), len(FAIL)))
    print("\nThe person's design choice, made after hearing the risk, is written once and obeyed by every check.")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
