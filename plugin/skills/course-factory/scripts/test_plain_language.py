# -*- coding: utf-8 -*-
"""test_plain_language - L25, and the false alarms that would get it switched off.

    python test_plain_language.py

The rule is easy to state and easy to make useless. Flag every occurrence of the word
"open" and it is noise; flag nothing inside a code block and a report can smuggle a
wall of tool output past it. Both edges are pinned below.
"""
from __future__ import annotations

import io
import json
import os
import shutil
import subprocess
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
CHECK = os.path.join(HERE, "check_plain_language.py")

PASS: list[str] = []
FAIL: list[str] = []


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print(("  ok    " if ok else "  FAIL  ") + name +
          (("  -> " + str(detail)[:220]) if detail and not ok else ""))


def run(body, name="factory-notes.md"):
    d = tempfile.mkdtemp(prefix="plain_")
    try:
        p = os.path.join(d, name)
        io.open(p, "w", encoding="utf-8", newline="\n").write(body)
        r = subprocess.run([sys.executable, CHECK, p, "--json"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        try:
            return json.loads(r.stdout)
        except ValueError:
            return {"findings": [], "_raw": r.stdout + r.stderr}
    finally:
        shutil.rmtree(d, ignore_errors=True)


def of(d, level):
    return [f for f in d["findings"] if f["level"] == level]


GOOD = """# What I changed in Module 4

Slide 12 explains the cargo pump but has no picture of one.

Where it is: C:\\Users\\raiviss\\Desktop\\gas basic\\course\\Module 04\\module.html - it is
the slide headed "The cargo pump", the twelfth one.

To see it, double-click that file. It opens in your web browser and you can press the
right arrow key to move through the slides.

What to do: tell me to add the pump drawing and I will put it at the top of the slide.
You will then see the drawing first and the text underneath it.
"""


def main() -> int:
    print("=" * 72)
    print("test_plain_language - can the person this was written for act on it?")
    print("=" * 72)

    print("\n-- a report written properly is left alone")
    d = run(GOOD)
    check("a full, plain, actionable report passes", not d["findings"], d["findings"])

    print("\n-- jargon with nothing beside it")
    d = run("The stylesheet was rebuilt. Open C:\\courses\\M4 and look at it.\n")
    check('bare "stylesheet" is reported', len(of(d, "FAIL")) == 1, d["findings"])
    check("and the report gives the plain wording to use instead",
          d["findings"] and "controls how the slides look" in d["findings"][0]["fix"])

    d = run("The file that controls how the slides look (the stylesheet) was rebuilt.\n"
            "Open C:\\courses\\M4 to see it.\n")
    check("the same word explained beside it is left alone",
          not of(d, "FAIL"), d["findings"])

    d = run("I made a new commit. You can open it later.\n")
    check('"commit" with no explanation is reported', len(of(d, "FAIL")) == 1, d["findings"])

    print("\n-- a path nobody can find")
    d = run("Add the drawing to module.html and then open it.\n")
    check("a bare file name is reported as hard to find",
          len(of(d, "WARN")) == 1, d["findings"])
    check("and the fix shows the shape of a findable path",
          d["findings"] and "C:\\Users" in d["findings"][0]["fix"])

    d = run("Add the drawing to C:\\Users\\raiviss\\Desktop\\M4\\module.html, then open "
            "that file by double-clicking it.\n")
    check("a full path beside the file name is left alone",
          not of(d, "WARN"), d["findings"])

    print("\n-- a problem with no way out")
    d = run("The check failed on eleven slides because the pictures are missing.\n")
    check("naming a failure and stopping is reported", len(of(d, "FAIL")) == 1, d["findings"])

    d = run("The check failed on eleven slides because the pictures are missing. "
            "Tell me to find them and I will search your source files first.\n")
    check("the same failure with a next step is left alone",
          not of(d, "FAIL"), d["findings"])

    print("\n-- the edges that would get this switched off")
    d = run("Everything passed. The course is ready for the tablets.\n")
    check("a clean report is not forced to invent a remedy", not d["findings"], d["findings"])

    d = run("Run this in the black window where commands are typed:\n\n"
            "```\npython check_hours.py Module_04\n```\n\n"
            "If it says the minutes match, you are done. If it says anything else, copy "
            "the whole message and send it to me.\n")
    check("a command inside a code block is not judged as prose",
          not d["findings"], d["findings"])

    # The first version of this check had a next-step vocabulary of about twenty words
    # and complained about the factory's own handoff page, which says "find a real
    # photograph". A checker that flags text already doing the right thing gets switched
    # off by the first person it annoys.
    for phrase in ("Find a real photograph instead.",
                   "This page is everything somebody needs to finish them.",
                   "Tell me and I will fix it.",
                   "Save the picture in the module folder.",
                   "Look for it in your source files first."):
        d = run("Eleven pictures are missing. " + phrase + "\n")
        check("a next step phrased as %r is accepted" % phrase.split()[0].lower(),
              not of(d, "FAIL"), d["findings"])

    d = run("| Slide | Problem |\n|---|---|\n| 12 | picture missing |\n")
    check("a table row is not judged as a paragraph", not of(d, "FAIL"), d["findings"])

    d = run("The word failed appears in the course text about a failed cargo pump seal, "
            "and the fix is to replace the seal before the next transfer.\n")
    check("maritime content that happens to use the word 'failed' is not flagged",
          not of(d, "FAIL"), d["findings"])

    print("\n" + "=" * 72)
    print("%d passed, %d failed" % (len(PASS), len(FAIL)))
    if FAIL:
        return 1
    print("\nThe rule bites on prose a person has to act on, and stays out of the commands,\n"
          "tables and maritime text where technical words belong.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
