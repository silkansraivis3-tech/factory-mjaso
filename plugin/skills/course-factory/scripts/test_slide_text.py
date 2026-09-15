# -*- coding: utf-8 -*-
"""test_slide_text - the four rules a maritime reviewer returned, and the two
false-alarm traps that nearly shipped with them.

    python test_slide_text.py

Each assertion below is a sentence from the review, turned into something a build can
check. The awkward half is the NEGATIVE cases: a rule that also flags a legitimate book
citation, or an instructor's own planning note, gets switched off by the first person it
annoys, and then it protects nothing.
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
CHECK = os.path.join(HERE, "check_slide_text.py")

PASS: list[str] = []
FAIL: list[str] = []


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append(name + (("  -> " + detail) if detail and not ok else ""))
    print(("  ok    " if ok else "  FAIL  ") + name + (("  -> " + detail) if detail and not ok else ""))


def run(target):
    p = subprocess.run([sys.executable, CHECK, target, "--json"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    try:
        return json.loads(p.stdout)
    except ValueError:
        return {"findings": [], "_raw": p.stdout + p.stderr}


def write(root, rel, body):
    p = os.path.join(root, rel.replace("/", os.sep))
    os.makedirs(os.path.dirname(p), exist_ok=True)
    io.open(p, "w", encoding="utf-8", newline="\n").write(body)
    return p


def rules_of(d, rule, level=None):
    return [f for f in d["findings"]
            if f["rule"] == rule and (level is None or f["level"] == level)]


DECK = """<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><title>D</title></head>
<body>
<section class="slide" data-title="Opening"%s>
  <h1>%s</h1>
  <p class="sub">%s</p>
</section>
<section class="slide" data-title="Body">
  <h2>Tank types</h2>
  <figcaption>%s</figcaption>
  <p class="src">%s</p>
  <p class="srcline">Avots: ICS <em>Tanker Safety Guide (Liquefied Gas)</em>, 3rd Edition 2018.</p>
</section>
</body></html>
"""


def deck(title="Basic Training", sub="Six days", cap="", src="", cue=""):
    return DECK % ((' data-cue="%s"' % cue) if cue else "", title, sub, cap, src)


def main() -> int:
    tmp = tempfile.mkdtemp(prefix="slidetext_")
    print("=" * 72)
    print("test_slide_text - what a course-facing page may say")
    print("=" * 72)
    try:
        # ---- 1 · internal shorthand ------------------------------------
        print("\n-- an internal abbreviation must not reach a trainee")
        r = os.path.join(tmp, "a"); write(r, "module.html", deck(title="OCFAM - Basic Training"))
        d = run(r)
        f = rules_of(d, "abbrev", "FAIL")
        check("an internal abbreviation on the deck FAILS", len(f) == 1, str(d)[:160])
        check("and the report gives the full course title to use instead",
              f and "Oil and Chemical Tanker Cargo Operations" in f[0]["fix"])

        r = os.path.join(tmp, "b"); write(r, "tasks/T1.html",
                                          "<html><body><p>In OCFAM you must know.</p></body></html>")
        check("on a trainee TASK page too", len(rules_of(run(r), "abbrev", "FAIL")) == 1)

        r = os.path.join(tmp, "c")
        write(r, "module.html", deck(cue="Tell the room this is the OCFAM course."))
        check("and in an instructor CUE, which is read aloud",
              len(rules_of(run(r), "abbrev", "FAIL")) == 1)

        # ---- 2 · the title slide ---------------------------------------
        print("\n-- the title slide is not a version-control record")
        r = os.path.join(tmp, "d")
        write(r, "module.html", deck(sub="Approved LJA programme, revision 3, topic 1"))
        d = run(r)
        v = rules_of(d, "version", "FAIL")
        check("revision number, approval and authority all FAIL on the opening slide",
              len(v) >= 3, "got %d" % len(v))

        # ---- 3 · what may be cited -------------------------------------
        print("\n-- an IMO model course is not a source of fact")
        r = os.path.join(tmp, "e")
        write(r, "module.html",
              deck(src="Source: IMO Model Course 1.01, 1.1 (Fig. 1.1 C and D)."))
        d = run(r)
        check("a model course cited as a SOURCE fails",
              len(rules_of(d, "source", "FAIL")) >= 1)

        r = os.path.join(tmp, "f")
        write(r, "module.html", deck(cap="Figure: IMO Model Course 1.01, 1.2."))
        check("a model course credited for a FIGURE fails",
              len(rules_of(run(r), "source", "FAIL")) >= 1)

        # ---- 4 · the factory's own markers -----------------------------
        print("\n-- the factory's markers belong in factory-notes.md")
        r = os.path.join(tmp, "g")
        write(r, "module.html",
              deck(sub="PLACEHOLDER - WAITING FOR DECISION on the pump list. TBD."))
        d = run(r)
        m = rules_of(d, "markers", "FAIL")
        check("PLACEHOLDER / WAITING FOR DECISION / TBD all fail", len(m) >= 3,
              "got %d" % len(m))

        # ---- 5 · THE FALSE-ALARM TRAPS ---------------------------------
        # A rule that also flags legitimate work gets switched off, and then it
        # protects nothing. These are the cases that must stay silent.
        print("\n-- what must NOT be flagged")
        r = os.path.join(tmp, "h")
        write(r, "module.html",
              deck(src="Avots: IMO <em>IGC Code</em>, 2016 edition, &sect;13.4."))
        d = run(r)
        check("a real publication cited as a source is left alone",
              not d["findings"], str(d["findings"])[:180])

        r = os.path.join(tmp, "i")
        write(r, "plan/MODULE_01_PLAN.html",
              "<html><body><p>IMO Model Course 1.04 allows 4.5 hours here. "
              "The programme is approved, revision 3.</p></body></html>")
        d = run(r)
        check("an instructor PLAN citing a model course is a note, not a failure",
              not [f for f in d["findings"] if f["level"] == "FAIL"]
              and len(rules_of(d, "source", "NOTE")) >= 1, str(d["findings"])[:180])

        r = os.path.join(tmp, "j")
        write(r, "handout/index.html",
              "<html><body><p>The approved programme allows a maximum of 24 trainees "
              "for theory.</p></body></html>")
        d = run(r)
        check("'the approved programme allows...' in body prose is NOT flagged",
              not d["findings"], str(d["findings"])[:180])

        r = os.path.join(tmp, "k")
        write(r, "module.html",
              deck(sub="If the cargo is unknown, treat it as the worst case."))
        check("the ordinary word 'unknown' is not mistaken for a marker",
              not run(r)["findings"])

        r = os.path.join(tmp, "l")
        write(r, "factory-notes.md", "PROVISIONAL: Track B at 69%.\n")
        write(r, "module.html", deck())
        check("factory-notes.md is not course-facing and is never scanned",
              not run(r)["findings"])

        # ---- 6 · the line number must be the FILE's line number --------
        print("\n-- a reported line is the line in the file")
        r = os.path.join(tmp, "m")
        body = ("<!DOCTYPE html>\n<html><head>\n<!-- a comment\n   spanning\n   lines -->\n"
                "<style>\n.x{color:red}\n</style>\n</head>\n<body>\n"
                "<section class=\"slide\"><h2>T</h2>\n"
                "<p class=\"src\">Source: IMO Model Course 1.04.</p>\n"
                "</section></body></html>\n")
        p = write(r, "module.html", body)
        d = run(r)
        want = body.split("\n").index('<p class="src">Source: IMO Model Course 1.04.</p>') + 1
        got = [f["line"] for f in rules_of(d, "source", "FAIL")]
        check("the line survives comments and <style> being stripped",
              got and got[0] == want, "reported %s, actually line %d" % (got, want))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("\n" + "=" * 72)
    print("%d passed, %d failed" % (len(PASS), len(FAIL)))
    if FAIL:
        for f in FAIL:
            print("  FAIL  " + f)
        return 1
    print("\nThe four rules bite where a trainee reads, stay quiet on an instructor's own\n"
          "notes, and never flag a real publication.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
