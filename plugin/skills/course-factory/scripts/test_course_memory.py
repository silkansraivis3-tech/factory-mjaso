# -*- coding: utf-8 -*-
"""test_course_memory - L32: the course remembers, and a pattern is only ever what the operator approved.

    python test_course_memory.py

Pinned below:
  * start writes COURSE_STATE.md and FEEDBACK_LOG.md, and never overwrites either;
  * check refuses a state file a new session could not resume from, and accepts a complete one;
  * a pattern is drafted from the operator's corrections, and a DRAFT is never offered to a later course;
  * approval refuses while the course, course type or "made by" is empty, and records who approved it;
  * only approved patterns are listed, with course, type, subject and author - so fit can be judged;
  * the memory files never ship: the publisher sorts them as INTERNAL.
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
TOOL = os.path.join(HERE, "course_memory.py")
SKILLS = os.path.dirname(os.path.dirname(HERE))
PASS, FAIL = [], []


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print(("  ok    " if ok else "  FAIL  ") + name + (("  -> " + str(detail)) if detail and not ok else ""))


def run(*a):
    p = subprocess.run([sys.executable, TOOL] + list(a), capture_output=True, text=True, encoding="utf-8", errors="replace")
    return p.returncode, p.stdout + p.stderr


def rd(p):
    return io.open(p, encoding="utf-8").read()


def wr(p, s):
    io.open(p, "w", encoding="utf-8", newline="\n").write(s)


def main():
    tmp = tempfile.mkdtemp(prefix="mem_")
    try:
        c = os.path.join(tmp, "Gas Basic")
        os.makedirs(c)
        print("-- start, and never overwrite")
        code, out = run("start", c, "--title", "Basic Training for Liquefied Gas Tanker Cargo Operations")
        st, fb = os.path.join(c, "working_claude", "COURSE_STATE.md"), os.path.join(c, "working_claude", "FEEDBACK_LOG.md")   # L44
        check("start writes both files", code == 0 and os.path.isfile(st) and os.path.isfile(fb), out)
        wr(fb, rd(fb) + "| 2 | 2026-10-01 | 3 · M1 · slide 4 | too much text, split it | split into two screens | no |\n")
        run("start", c, "--title", "x")
        check("a second start leaves the files exactly as they were", "split into two screens" in rd(fb))

        print("\n-- check: can a new session resume from it?")
        code, out = run("check", c)
        check("a fresh template is NOT enough to resume from", code == 1 and "stage is not named" in out, out)
        s = rd(st)
        s = s.replace("**Stage:** <1 Intake | 2 Architecture | 3 Content script | 4 Pilot Module 1 | 5 Remaining modules | 6 Final assessment and handover>",
                      "**Stage:** 3 Content script")
        s = s.replace("**Next step:** <one sentence: what happens next, and what the operator will be shown>",
                      "**Next step:** the Module 1 content script is shown for approval.")
        s = s.replace("| Course | <title> |", "| Course | Basic Training for Liquefied Gas Tanker Cargo Operations |")
        s = s.replace("| Course type | <NEW_ENTRANT / EXPERIENCED> |", "| Course type | NEW_ENTRANT |")
        wr(st, s)
        code, out = run("check", c)
        check("a filled state file passes, and names the stage", code == 0 and "3 Content script" in out, out)
        os.remove(fb)
        code, out = run("check", c)
        check("a missing FEEDBACK_LOG.md is reported", code == 1 and "FEEDBACK_LOG.md is missing" in out, out)
        run("start", c, "--title", "x")

        print("\n-- a pattern is drafted, shown, and only then approved")
        wr(fb, rd(fb) + "| 1 | 2026-10-01 | 3 · M1 · slide 4 | keep the old pump drawing, it shows the relief valve | kept it | no |\n"
                      "| 2 | 2026-10-02 | 3 · M1 · slide 9 | the relief valve on these ships lifts at 0.25 bar | used it | yes |\n")
        code, out = run("draft-pattern", c)
        rv = os.path.join(c, "to_review")
        drafts = [f for f in os.listdir(rv) if f.endswith(".draft.md")]
        check("draft-pattern writes a DRAFT, not a pattern - into to_review, for the operator to read", code == 0 and len(drafts) == 1, out)
        d = os.path.join(rv, drafts[0])
        t = rd(d)
        check("the draft carries the course and course type from the state file",
              "| **Course** | Basic Training for Liquefied Gas Tanker Cargo Operations |" in t and "| **Course type** | NEW_ENTRANT |" in t, t[:600])
        check("the draft carries the operator's corrections in their words", "keep the old pump drawing" in t, t)

        code, out = run("patterns", "--also", c)
        check("a draft is never offered to a later course", "No approved course patterns" in out and "a draft" in out, out)

        code, out = run("approve-pattern", c, "--by", "Raivis Silkans")
        check("approval refuses while 'Made by' is empty", code == 1 and "Made by" in out and os.path.isfile(d), out)
        wr(d, rd(d).replace("| **Made by** | <the operator who worked on the course> |", "| **Made by** | A. Colleague |")
                   .replace("| **Subject area** | <e.g. liquefied gas tankers, electrical, fire fighting> |", "| **Subject area** | liquefied gas tankers |"))
        code, out = run("approve-pattern", c, "--by", "Raivis Silkans")
        wc = os.path.join(c, "working_claude")
        final = [f for f in os.listdir(wc) if f.startswith("COURSE_PATTERN_") and not f.endswith(".draft.md")]
        check("approval saves it into working_claude and removes the draft", code == 0 and len(final) == 1 and not os.path.exists(d), out)
        check("the approver and the date are written into it", "| **Approved by** | Raivis Silkans on 20" in rd(os.path.join(wc, final[0])))

        code, out = run("patterns", "--also", c, "--course-type", "NEW_ENTRANT")
        check("an approved pattern is listed with course, type, subject and author",
              "Basic Training for Liquefied Gas Tanker Cargo Operations · NEW_ENTRANT · liquefied gas tankers · made by A. Colleague" in out
              and "same course type" in out, out)
        check("... and the listing says it is guidance, never a rule", "never rules" in out, out)
        code, out = run("patterns", "--also", c, "--course-type", "EXPERIENCED")
        check("a different course type is shown as such", "a different course type" in out, out)

        print("\n-- the rule is where a session reads it")
        cf = os.path.join(SKILLS, "course-factory")
        skill = rd(os.path.join(cf, "SKILL.md"))
        full = rd(os.path.join(cf, "references", "laws-in-full.md"))
        check("SKILL.md carries 'The course remembers — L32'", "## The course remembers — L32" in skill)
        check("SKILL.md says to read COURSE_STATE.md first and show the pattern before saving",
              "starts by reading `COURSE_STATE.md`" in skill and "show it to the operator in plain language" in skill)
        check("the full L32 text carries the owner's three pattern conditions",
              "shown to the operator in plain language before it is saved" in full
              and "names the course, the course type and who made it" in full
              and "guidance for future courses, never rules" in full)

        print("\n-- the memory never ships to a tablet")
        sys.path.insert(0, os.path.join(SKILLS, "course-tablet-publisher", "scripts"))
        import gates
        plat = gates.load_platform()
        repo = os.path.join(tmp, "repo")
        base = os.path.join(repo, plat["asset_roots"]["trainee"], "courses", "gas", "")
        for name in ("COURSE_STATE.md", "FEEDBACK_LOG.md", "COURSE_PATTERN_Gas.md", "COURSE_PATTERN_Gas.draft.md", "factory-notes.md"):
            check("the publisher sorts %s as INTERNAL" % name, gates.classify(repo, plat, base + name) == "INTERNAL",
                  gates.classify(repo, plat, base + name))
        check("... while a trainee page still ships", gates.classify(repo, plat, base + "index.html") != "INTERNAL")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("\n" + "=" * 72)
    print("%d passed, %d failed" % (len(PASS), len(FAIL)))
    if FAIL:
        return 1
    print("\nThe course remembers where it stands and what the operator corrected, a pattern is only ever\n"
          "what the operator read and approved, and none of it reaches a tablet.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
