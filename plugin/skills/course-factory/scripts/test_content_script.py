# -*- coding: utf-8 -*-
"""test_content_script - Stage 3: the words are approved before the HTML, and nothing changes unasked.

    python test_content_script.py

The example module is invented. The operator's Word edits are simulated by editing the file's XML
the way Word writes it (a real Word round trip is run separately when Word is installed - see
MANIFEST 4h). Pinned:
  * the review page and the Word file hold every screen in trainee order, one task per screen, the
    course text in the course language and the rest in the operator's; operator-stated facts listed once;
  * an untouched Word file reads back as "nothing changed";
  * typed text, tracked changes (read as if accepted), comments, a deleted box and text typed outside the
    boxes are all found - and NONE of it is applied: it is a pending list;
  * apply refuses without --confirmed; with it, only the edits are applied, each is logged in
    FEEDBACK_LOG.md, the old Word file is kept and a fresh one written; comments are not applied;
  * approval is refused while changes wait or the script has problems; any change after approval
    makes it a draft again;
  * check_script_match passes a module that says exactly the approved words, and fails a changed
    word, an extra sentence, a missing screen, a wrong correct answer and an unapproved script.
"""
from __future__ import annotations

import copy
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "content_script.py")
MATCH = os.path.join(HERE, "check_script_match.py")
sys.path.insert(0, HERE)
import content_script as cs  # noqa: E402
PASS, FAIL = [], []

SCRIPT = {
    "module": 1, "title": "Gas tankers", "course_language": "English", "operator_language": "lv", "status": "draft",
    "operator_facts": [{"fact": "On our simulator the ESD button is on the left console.", "where": "s03"}],
    "screens": [
        {"id": "s01", "kind": "slide", "title": "Why gas tankers are different",
         "text": "Liquefied gas is carried cold or under pressure.\nA leak turns into a vapour cloud.",
         "visual": "Photograph of a membrane LNG carrier", "notes": "Ask who has sailed on one.", "minutes": 3},
        {"id": "q01", "kind": "self-check", "question": "How is LNG carried?",
         "options": ["At about -163 °C", "At room temperature, under pressure", "As a solid"], "correct": "A",
         "feedback": "LNG is fully refrigerated.", "mechanic": "tap to choose"},
        {"id": "s02", "kind": "slide", "title": "Types of containment",
         "text": "Independent tanks: type A, B and C.\nMembrane tanks rely on the hull for strength.",
         "visual": "Cutaway of membrane and type B tanks", "notes": "", "minutes": 5},
        {"id": "m01", "kind": "module-check", "question": "Which tank relies on the hull?",
         "options": ["Type C", "Membrane", "Type A"], "correct": "B", "feedback": "Membrane tanks are supported by the hull.",
         "mechanic": "tap to choose", "graded": False}]}

W = cs.W


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print(("  ok    " if ok else "  FAIL  ") + name + (("  -> " + str(detail)[:400]) if detail and not ok else ""))


def run(*a):
    p = subprocess.run([sys.executable] + list(a), capture_output=True, text=True, encoding="utf-8", errors="replace")
    return p.returncode, p.stdout + p.stderr


def cs_run(*a):
    return run(TOOL, *a)


def new_course(tmp, name, script=SCRIPT):
    c = os.path.join(tmp, name)
    os.makedirs(os.path.join(c, "_factory", "script"))
    io.open(os.path.join(c, "_factory", "script", "M01.json"), "w", encoding="utf-8").write(json.dumps(script, ensure_ascii=False))
    io.open(os.path.join(c, "FEEDBACK_LOG.md"), "w", encoding="utf-8").write(
        "# log\n\n| # | Date | Stage · module · where | What the operator said | What changed | Operator-stated fact? |\n|---|---|---|---|---|---|\n"
        "| 1 | 2026-10-01 | 3 · M01 · s02 | type C tanks here are tested to 7 bar | used it | yes |\n")
    return c


def edit_docx(path, fn):
    with zipfile.ZipFile(path) as z:
        parts = {n: z.read(n) for n in z.namelist()}
    doc = parts["word/document.xml"].decode("utf-8")
    doc, extra = fn(doc)
    parts["word/document.xml"] = doc.encode("utf-8")
    parts.update(extra)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for n, b in parts.items():
            z.writestr(n, b)


def box(doc, tag):
    m = re.search(r'<w:sdt><w:sdtPr><w:alias[^>]*/><w:tag w:val="%s"/>.*?</w:sdt>' % re.escape(tag), doc, re.S)
    return m


def main():
    tmp = tempfile.mkdtemp(prefix="cs_")
    try:
        print("-- render: the operator's review page and Word file")
        c = new_course(tmp, "c1")
        code, out = cs_run("render", c, "--module", "1")
        p = cs.paths(c, 1)
        page = io.open(p["review"], encoding="utf-8").read()
        check("render writes the review page and the Word file", code == 0 and os.path.isfile(p["docx"]), out)
        check("the page is in the operator's language, the course text marked English",
              '<html lang="lv">' in page and "satura scenārijs" in page and '<span class="verb" lang="en">Types of containment</span>' in page)
        order = [page.find('<span class="sid">%s</span>' % x) for x in ("s01", "q01", "s02", "m01")]
        check("screens appear in the trainee's order", order == sorted(order) and -1 not in order, order)
        check("each task is its own screen, shown as on the tablet, with the correct answer marked",
              page.count('<div class="tablet">') == 2 and page.count('class="opt right"') == 2)
        check("self-check and module check are labelled not graded", "Paškontrole — bez vērtējuma" in page and "Moduļa pārbaude — bez vērtējuma" in page)
        check("operator-stated facts listed once - from the script and from FEEDBACK_LOG.md",
              "left console" in page and "tested to 7 bar" in page and page.count("Jūsu norādītie fakti") == 1)
        doc = zipfile.ZipFile(p["docx"]).read("word/document.xml").decode("utf-8")
        n_boxes = doc.count("<w:sdt>")
        check("every editable text is its own locked Word box", n_boxes == 5 + 7 + 5 + 7 and doc.count('w:lock w:val="sdtLocked"') == n_boxes, n_boxes)
        check("the boxes carry the course language", 'w:lang w:val="en"' in doc)
        code, out = cs_run("read", c, "--module", "1")
        check("an untouched Word file reads back as nothing changed", code == 0 and "nothing" in out and not os.path.exists(p["pending"]), out)

        print("\n-- the operator edits the Word file - read, and do NOT apply")
        def edits(doc):
            m = box(doc, "s02.text")
            new = m.group(0).replace("Membrane tanks rely on the hull for strength.", "Membrane tanks are supported by the hull.")
            doc = doc.replace(m.group(0), new)
            m = box(doc, "q01.opt.B")     # a tracked change: 'room' deleted, 'ambient' inserted
            new = m.group(0).replace('<w:t xml:space="preserve">At room temperature, under pressure</w:t></w:r>',
                                     '<w:t xml:space="preserve">At </w:t></w:r><w:del w:id="91" w:author="Anna"><w:r><w:delText>room</w:delText></w:r></w:del>'
                                     '<w:ins w:id="92" w:author="Anna"><w:r><w:t>ambient</w:t></w:r></w:ins><w:r><w:t xml:space="preserve"> temperature, under pressure</w:t></w:r>')
            doc = doc.replace(m.group(0), new)
            m = box(doc, "s01.title")     # a comment on the title
            new = m.group(0).replace("<w:sdtContent><w:p>", '<w:sdtContent><w:p><w:commentRangeStart w:id="5"/>', 1)
            doc = doc.replace(m.group(0), new)
            m = box(doc, "s02.notes")     # a box deleted outright
            doc = doc.replace(m.group(0), "")
            doc = doc.replace("</w:body>", '<w:p><w:r><w:t>Please add a slide on BOG.</w:t></w:r></w:p></w:body>')   # typed outside the boxes
            comments = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:comments xmlns:w="%s">'
                        '<w:comment w:id="5" w:author="Anna"><w:p><w:r><w:t>Say LNG and LPG carriers.</w:t></w:r></w:p></w:comment></w:comments>' % W)
            return doc, {"word/comments.xml": comments.encode("utf-8")}
        edit_docx(p["docx"], edits)
        before = io.open(p["script"], encoding="utf-8").read()
        code, out = cs_run("read", c, "--module", "1")
        check("typed text is found - and only the changed words are named",
              '"rely on" becomes "are supported by"' in out and '"hull for strength." becomes "hull."' in out, out)
        check("a tracked change is read as if accepted, and said to be tracked, by whom",
              'answer B becomes "At ambient temperature, under pressure"' in out and "tracked changes in q01.opt.B" in out and "Anna" in out, out)
        check("a comment is placed on its screen and field", "comment on s01.title from Anna" in out, out)
        check("a deleted box is reported, not guessed", "box for s02.notes was deleted" in out, out)
        check("text typed outside the boxes is reported, not guessed", "Please add a slide on BOG." in out and "will not guess" in out, out)
        check("NOTHING was applied - the script is unchanged, a pending list waits",
              io.open(p["script"], encoding="utf-8").read() == before and os.path.isfile(p["pending"]))
        code, out = cs_run("approve", c, "--module", "1", "--by", "Anna")
        check("approval is refused while understood changes wait", code == 1 and "waiting" in out, out)
        code, out = cs_run("apply", c, "--module", "1")
        check("apply refuses without --confirmed", code == 2 and "--confirmed" in out, out)

        print("\n-- the operator confirmed: apply")
        code, out = cs_run("apply", c, "--module", "1", "--confirmed")
        s = cs.load(p["script"])
        s02 = [x for x in s["screens"] if x["id"] == "s02"][0]
        q01 = [x for x in s["screens"] if x["id"] == "q01"][0]
        check("the edits are applied", code == 0 and "supported by the hull." in s02["text"] and q01["options"][1] == "At ambient temperature, under pressure", out)
        check("comments and notes are NOT applied - they come back as proposals", "were NOT applied" in out and "Why gas tankers are different" == s["screens"][0]["title"], out)
        fb = io.open(os.path.join(c, "FEEDBACK_LOG.md"), encoding="utf-8").read()
        check("each applied change is logged in FEEDBACK_LOG.md", fb.count("| 3 · M01 ·") == 1 + 2 and fb.count("(Word file)") == 2, fb[-400:])
        check("the old Word file is kept, and a fresh one written",
              any(f.endswith(".docx") for f in os.listdir(p["old"])) and os.path.isfile(p["docx"]))

        print("\n-- a chat correction, then 'no'")
        ch = os.path.join(tmp, "changes.json")
        io.open(ch, "w", encoding="utf-8").write(json.dumps([{"field": "m01.correct", "new": "C"}]))
        code, out = cs_run("propose", c, "--module", "1", "--changes", ch)
        check("a chat correction is shown as understood, not applied", "the correct answer becomes C (was B)" in out and os.path.isfile(p["pending"]), out)
        code, out = cs_run("discard", c, "--module", "1")
        check("'no' discards it and the script is unchanged",
              not os.path.isfile(p["pending"]) and [x for x in cs.load(p["script"])["screens"] if x["id"] == "m01"][0]["correct"] == "B", out)

        print("\n-- approval, and what undoes it")
        code, out = cs_run("approve", c, "--module", "1", "--by", "Anna")
        check("the operator's 'next' approves it", code == 0 and cs_run("status", c, "--module", "1")[0] == 0, out)
        io.open(ch, "w", encoding="utf-8").write(json.dumps([{"field": "s01.minutes", "new": "4"}]))
        cs_run("propose", c, "--module", "1", "--changes", ch)
        cs_run("apply", c, "--module", "1", "--confirmed")
        check("any change after approval makes it a draft again", cs_run("status", c, "--module", "1")[0] == 1)
        for v in ("6", "3"):          # two corrections in the same second: the archive names must not collide
            io.open(ch, "w", encoding="utf-8").write(json.dumps([{"field": "s01.minutes", "new": v}]))
            cs_run("propose", c, "--module", "1", "--changes", ch)
            code, out = cs_run("apply", c, "--module", "1", "--confirmed")
        check("two corrections applied in the same second both succeed, and nothing is left waiting",
              code == 0 and not os.path.isfile(p["pending"]) and cs.load(p["script"])["screens"][0]["minutes"] == 3, out)
        cs_run("approve", c, "--module", "1", "--by", "Anna")

        print("\n-- problems in a script are caught before it is shown")
        bad = copy.deepcopy(SCRIPT)
        bad["screens"][3]["graded"] = True
        bad["screens"][1]["correct"] = "D"
        bad["screens"].append({"id": "s09", "kind": "slide", "title": "After the check", "text": "x"})
        cb = new_course(tmp, "bad", bad)
        code, out = cs_run("render", cb, "--module", "1")
        check("a graded module check is caught", "module check is not graded" in out, out)
        check("a correct answer that is not an option is caught", "the correct answer 'D'" in out, out)
        check("a slide after the module check is caught", "slide comes after the module check" in out, out)
        check("... and approval is refused", cs_run("approve", cb, "--module", "1", "--by", "x")[0] == 1)

        print("\n-- 2.16.1: the slide-text check runs on the script, before any HTML")
        dirty = copy.deepcopy(SCRIPT)
        dirty["screens"][0]["title"] = "Why gas tankers are different - Revision 3"
        dirty["screens"][0]["text"] = "Liquefied gas is carried cold or under pressure.\nSource: IMO Model Course 1.04"
        dirty["screens"][0]["notes"] = "The IMO Model Course 1.04 covers this in section 2."
        dirty["screens"][1]["question"] = "What does OCFAM require here?"
        dirty["screens"][1]["feedback"] = "LNG is fully refrigerated. [VERIFY: the exact temperature]"
        cd = new_course(tmp, "dirty", dirty)
        code, out = cs_run("render", cd, "--module", "1")
        pd = cs.paths(cd, 1)
        dpage = io.open(pd["review"], encoding="utf-8").read()
        for what, needle in (("a model course cited as a source on a slide", "s01 · text"),
                             ("version control on the opening slide", "s01 · title"),
                             ("an internal abbreviation in a question", "q01 · question"),
                             ("a factory marker in the feedback", "q01 · feedback")):
            check("found and shown on the review page: " + what, needle in dpage and "teksta pārbaude atrada" in dpage, needle)
        check("each must-fix finding is marked as such", dpage.count("jāizlabo, pirms to redz apmācāmais") >= 4)
        notes_li = re.search(r"<li><b>[^<]*s01 · notes</b>.*?</li>", dpage)
        check("a model course in the INSTRUCTOR notes is only a note, never a must-fix",
              notes_li is not None and "informācijai" in notes_li.group(0) and "jāizlabo" not in notes_li.group(0),
              notes_li and notes_li.group(0))
        check("render reports the findings", "The text check found" in out and "[must fix] screen 1 (s01), text" in out, out)
        ddoc = zipfile.ZipFile(pd["docx"]).read("word/document.xml").decode("utf-8")
        check("the findings are in the Word file too", "teksta pārbaude atrada" in ddoc and "q01 · feedback" in ddoc)
        code, out = cs_run("read", cd, "--module", "1")
        check("the findings in the Word file are not mistaken for the operator's own text", "outside the boxes" not in out and code == 0, out)
        code, out = cs_run("approve", cd, "--module", "1", "--by", "Anna")
        check("approval is refused while a must-fix finding stands", code == 1 and "text check found" in out, out)
        code, out = cs_run("approve", cd, "--module", "1", "--by", "Anna", "--despite-findings")
        rec = cs.load(pd["script"])
        check("the operator may approve despite them (L26) - and that is recorded",
              code == 0 and len(rec.get("approved_despite_findings", [])) >= 4, out)
        code, out = cs_run("render", c, "--module", "1")
        check("a clean script says the text check found nothing",
              "Teksta pārbaude neko neatrada" in io.open(p["review"], encoding="utf-8").read())

        print("\n-- the built module says exactly the approved words")
        s = cs.load(p["script"])
        mdir = os.path.join(c, "modules", "m1")
        os.makedirs(os.path.join(mdir, "tasks"))
        def slide(x, extra=""):
            lines = "".join('<p data-script-field="text">%s</p>' % l for l in x["text"].split("\n"))
            return ('<section class="slide" data-script="%s" data-cue="instructor only"><div class="slide-kind">Theory · A1</div>'
                    '<h2 data-script-field="title">%s</h2>%s<svg><text>label</text></svg><p class="src">Source: SIGTTO</p>%s</section>'
                    % (x["id"], x["title"], lines, extra))
        def task(x, correct=None):
            opts = "".join('<button data-script-field="opt.%s"%s>%s</button>' % (L, ' data-correct="true"' if L == (correct or x["correct"]) else "", o)
                           for L, o in zip(cs.letters(len(x["options"])), x["options"]))
            return ('<div data-script="%s"><p data-script-field="question">%s</p>%s<p data-script-field="feedback">%s</p></div>'
                    % (x["id"], x["question"], opts, x["feedback"]))
        def build(slides_extra="", drop=None, correct=None, word=None):
            sl = [x for x in s["screens"] if x["kind"] == "slide" and x["id"] != drop]
            deck = "<html><body>%s</body></html>" % "".join(slide(x, slides_extra if x["id"] == "s01" else "") for x in sl)
            if word:
                deck = deck.replace(word[0], word[1], 1)
            io.open(os.path.join(mdir, "module.html"), "w", encoding="utf-8").write(deck)
            tk = [x for x in s["screens"] if x["kind"] in cs.TASKS]
            io.open(os.path.join(mdir, "tasks", "t1.html"), "w", encoding="utf-8").write(
                "<html><body>%s</body></html>" % "".join(task(x, correct if x["id"] == "m01" else None) for x in tk))
            return run(MATCH, c, "--module", "1")
        code, out = build()
        check("a module that says exactly the approved words passes", code == 0, out)
        code, out = build(word=("supported by the hull.", "supported by the ship's hull."))
        check("one changed word fails", code == 1 and "s02" in out, out)
        code, out = build(slides_extra="<p>An extra sentence nobody approved.</p>")
        check("an extra sentence on a slide fails", code == 1 and "not in the approved script" in out, out)
        code, out = build(drop="s02")
        check("a screen that was not built fails", code == 1 and "s02) is not built" in out, out)
        code, out = build(correct="A")
        check("a wrong correct answer fails", code == 1 and "marked correct is A - approved: B" in out, out)
        code, out = build(slides_extra='<p data-script-ignore="decor">Deck furniture</p>')
        check("data-script-ignore is allowed but counted for QA", code == 0 and "data-script-ignore" in out, out)
        cs_run("propose", c, "--module", "1", "--changes", ch)
        io.open(ch, "w", encoding="utf-8").write(json.dumps([{"field": "s01.minutes", "new": "5"}]))
        cs_run("propose", c, "--module", "1", "--changes", ch)
        cs_run("apply", c, "--module", "1", "--confirmed")
        code, out = build()
        check("a script changed after approval fails the match", code == 1 and "not approved" in out, out)

        print("\n-- the review files never ship to a tablet")
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "course-tablet-publisher", "scripts"))
        import gates
        plat = gates.load_platform()
        repo = os.path.join(tmp, "repo")
        base = os.path.join(repo, plat["asset_roots"]["trainee"], "courses", "x", "review", "")
        for n in ("M01_SCRIPT_REVIEW.html", "M01_SCRIPT.docx"):
            check("the publisher sorts %s as INTERNAL" % n, gates.classify(repo, plat, base + n) == "INTERNAL", gates.classify(repo, plat, base + n))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("\n" + "=" * 72)
    print("%d passed, %d failed" % (len(PASS), len(FAIL)))
    if FAIL:
        return 1
    print("\nThe words are approved before the HTML, every correction is shown before it is applied, and the\n"
          "built module is checked word for word against what the operator approved.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
