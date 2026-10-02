# -*- coding: utf-8 -*-
"""test_workspace - L40 and L41: the factory works in course\\ beside the operator's material, and reads the
old course whole before it plans anything.

    python test_workspace.py

A small master folder is invented: source_files\\, KNOWLEDGE_BASE\\ and an old course with a deck, an exercise,
an old .doc, a training film and a lock file. Pinned:
  * a master folder is recognised; its course\\ folder is made beside the material; the course folder itself,
    or an old-style folder, is used as it is;
  * the factory's tools - the course memory, the architecture page, the content script, the knowledge-base
    decisions - write into course\\ when they are given the master folder;
  * the material is never changed: a fingerprint of every file before and after is identical;
  * old_course.py reads every file: each slide's title, words and pictures, the speaker notes, each document's
    headings and words, the films; an old .doc is flagged as not read, never skipped in silence; lock files are
    left out and counted; the lists go into course\\_factory\\ only;
  * the architecture page asks every module what it takes from the old course once the old course is read.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import workspace  # noqa: E402
PASS, FAIL = [], []


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print(("  ok    " if ok else "  FAIL  ") + name + (("  -> " + str(detail)[:400]) if detail and not ok else ""))


def run(script, *a):
    p = subprocess.run([sys.executable, os.path.join(HERE, script)] + list(a), capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return p.returncode, p.stdout + p.stderr


def fingerprint(folder, skip="course"):
    h = hashlib.sha256()
    for dp, dn, fn in os.walk(folder):
        if os.path.abspath(dp) == os.path.abspath(folder):
            dn[:] = [d for d in dn if d != skip]
        for f in sorted(fn):
            full = os.path.join(dp, f)
            h.update(os.path.relpath(full, folder).encode("utf-8"))
            h.update(open(full, "rb").read())
    return h.hexdigest()


PA = "http://schemas.openxmlformats.org/drawingml/2006/main"
PP = "http://schemas.openxmlformats.org/presentationml/2006/main"
WN = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def slide_xml(title, body):
    return ('<p:sld xmlns:p="%s" xmlns:a="%s"><p:cSld><p:spTree>'
            '<p:sp><p:nvSpPr><p:nvPr><p:ph type="title"/></p:nvPr></p:nvSpPr><p:txBody><a:p><a:r><a:t>%s</a:t></a:r></a:p></p:txBody></p:sp>'
            '<p:sp><p:nvSpPr><p:nvPr/></p:nvSpPr><p:txBody><a:p><a:r><a:t>%s</a:t></a:r></a:p></p:txBody></p:sp>'
            '</p:spTree></p:cSld></p:sld>' % (PP, PA, title, body))


def make_pptx(path):
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("ppt/slides/slide1.xml", slide_xml("Gas tankers", "Why gas is carried cold or under pressure"))
        z.writestr("ppt/slides/slide2.xml", slide_xml("Type C tanks", "Pressure vessels, no secondary barrier, design pressure about 18 bar"))
        z.writestr("ppt/slides/slide10.xml", slide_xml("Membrane tanks", "Thin barrier carried by the hull"))
        z.writestr("ppt/slides/_rels/slide2.xml.rels",
                   '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   '<Relationship Id="r1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="../media/a.png"/>'
                   '<Relationship Id="r2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="../media/b.png"/>'
                   '</Relationships>')
        z.writestr("ppt/media/a.png", b"\x89PNG picture a")
        z.writestr("ppt/media/b.png", b"\x89PNG picture b")
        z.writestr("ppt/media/logo.png", b"\x89PNG the logo")
        for k in (1, 10):              # the same logo on two slides - kept once
            z.writestr("ppt/slides/_rels/slide%d.xml.rels" % k,
                       '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                       '<Relationship Id="r1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="../media/logo.png"/>'
                       '</Relationships>')
        z.writestr("ppt/notesSlides/notesSlide2.xml",
                   '<p:notes xmlns:p="%s" xmlns:a="%s"><a:t>Ask why a pressure vessel needs no barrier</a:t></p:notes>' % (PP, PA))


def make_docx(path):
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("word/document.xml",
                   '<w:document xmlns:w="%s"><w:body>'
                   '<w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>Gas tanker arrangement</w:t></w:r></w:p>'
                   '<w:p><w:r><w:t>Name the spaces on the general arrangement plan.</w:t></w:r></w:p>'
                   '</w:body></w:document>' % WN)


def main():
    tmp = tempfile.mkdtemp(prefix="ws_")
    try:
        master = os.path.join(tmp, "my course")
        old = os.path.join(master, "old_course")
        for d in ("source_files", os.path.join("KNOWLEDGE_BASE", "sources"), os.path.join("old_course", "1. Gas tankers", "1. Power Point Presentation"),
                  os.path.join("old_course", "1. Gas tankers", "2. Exercise for Trainee"), os.path.join("old_course", "1. Gas tankers", "4. Training Film"),
                  os.path.join("old_course", "0. Course header")):
            os.makedirs(os.path.join(master, d))
        io.open(os.path.join(master, "KNOWLEDGE_BASE", "SOURCE_MANIFEST.json"), "w").write('{"sources": []}')
        io.open(os.path.join(master, "source_files", "programme.pdf"), "wb").write(b"%PDF-1.4 fake")
        make_pptx(os.path.join(old, "1. Gas tankers", "1. Power Point Presentation", "1. Liquefied Gas tankers.pptx"))
        make_docx(os.path.join(old, "1. Gas tankers", "2. Exercise for Trainee", "Arrangement - Exercise for Trainee.docx"))
        io.open(os.path.join(old, "1. Gas tankers", "4. Training Film", "Loading.mp4"), "wb").write(b"\0" * 2048)
        io.open(os.path.join(old, "0. Course header", "Course Plan.doc"), "wb").write(b"\xd0\xcf\x11\xe0 old binary")
        io.open(os.path.join(old, "1. Gas tankers", "2. Exercise for Trainee", ".~lock.Arrangement.docx#"), "w").write("lock")
        before = fingerprint(master)

        print("-- the work folder sits beside the material")
        check("a folder holding source_files, a knowledge base and an old course is a master folder", workspace.is_master(master))
        w = workspace.work_folder(master)
        check("its work folder is course\\ beside the material, made on first use", w == os.path.join(master, "course") and os.path.isdir(w), w)
        check("the course folder itself is used as it is", workspace.work_folder(w) == w)
        plain = os.path.join(tmp, "plain")
        os.makedirs(plain)
        check("an old-style folder with no material in it is used as it is", workspace.work_folder(plain) == plain)
        check("the master folder is found back from the course folder", workspace.master_of(w) == master)
        code, out = run("workspace.py", master)
        check("workspace.py says where the factory writes and lists the material, read only",
              code == 0 and w in out and "read only" in out and "old_course\\" in out, out)

        print("\n-- the tools write into course\\ when given the master folder")
        code, out = run("course_memory.py", "start", master, "--title", "GAS Basic")
        check("the course memory starts in course\\, not in the master folder",
              code == 0 and os.path.isfile(os.path.join(w, "working_claude", "COURSE_STATE.md")) and not os.path.exists(os.path.join(master, "COURSE_STATE.md")), out)
        prog = {"academic_hour_min": 40, "topics": {"1": {"title": "Gas tankers", "theory": 1, "practical": 0},
                                                    "2": {"title": "Final assessment", "theory": 1, "practical": 0, "assessment": True}},
                "main_ilos": {"1": "Contribute to safe cargo operations"}}
        arch = {"course": {"title": "GAS Basic", "course_language": "English", "operator_language": "en", "course_type": "NEW_ENTRANT",
                           "old_course": old},
                "main_ilos": [{"id": "1", "text": "Contribute to safe cargo operations"}],
                "modules": [{"module": 1, "title": "Gas tankers", "main_ilos": ["1"], "media": [{"kind": "model_3d", "what": "tank types"}],
                             "module_check": {"questions": 5, "mechanics": ["hotspot", "order", "match"]}}],
                "final_assessment": {"topic": "2", "questions": 30, "pass_mark": "70 %", "graded": True}}
        for n, v in (("programme.json", prog), ("architecture.json", arch)):
            io.open(os.path.join(w, "working_claude", n), "w", encoding="utf-8").write(json.dumps(v))
        code, out = run("make_architecture_page.py", "--course", master, "--check")
        check("the architecture page asks what each module takes from the old course, once it is read",
              code == 1 and "the old course was read, but this module does not say" in out, out)
        arch["modules"][0]["from_old_course"] = {"had": "1. Gas tankers - 52 slides, one exercise, one film",
                                                 "keep": ["the tanker types and the containment systems"],
                                                 "modernise": ["the static tank photographs become a 3D model of the four tank types"],
                                                 "add": ["a tap-the-place task on the general arrangement"]}
        io.open(os.path.join(w, "working_claude", "architecture.json"), "w", encoding="utf-8").write(json.dumps(arch))
        code, out = run("make_architecture_page.py", "--course", master)
        ap = os.path.join(w, "to_review", "ARCHITECTURE_REVIEW.html")
        page = io.open(ap, encoding="utf-8").read() if os.path.isfile(ap) else ""
        check("... and shows it: kept, modernised and made digital, added",
              code == 0 and "From the old course - kept, modernised, added" in page and "a 3D model of the four tank types" in page
              and not os.path.exists(os.path.join(master, "ARCHITECTURE_REVIEW.html")), out)
        os.makedirs(os.path.join(w, "working_claude", "script"), exist_ok=True)
        io.open(os.path.join(w, "working_claude", "script", "M01.json"), "w", encoding="utf-8").write(json.dumps(
            {"module": 1, "title": "Gas tankers", "course_language": "English", "operator_language": "en", "screens": [
                {"id": "s01", "kind": "slide", "title": "Gas tankers", "text": "x", "notes": "- y", "minutes": 1,
                 "from_old": "1. Liquefied Gas tankers.pptx, slides 1-2 - the photographs become a 3D model"}]}))
        code, out = run("content_script.py", "render", master, "--module", "1")
        rp = os.path.join(w, "to_review", "M01_SCRIPT_REVIEW.html")
        check("the content script renders its page, Word file and instructor notes into course\\to_review",
              os.path.isfile(rp) and os.path.isfile(os.path.join(w, "to_review", "M01_INSTRUCTOR_NOTES.md"))
              and os.path.isfile(os.path.join(w, "to_review", "M01_SCRIPT.docx")) and not os.path.exists(os.path.join(master, "to_review")), out)
        check("to_review holds only what the operator checks - nothing of the factory's own",
              sorted(os.listdir(os.path.join(w, "to_review"))) == ["ARCHITECTURE_REVIEW.html", "M01_INSTRUCTOR_NOTES.md", "M01_SCRIPT.docx", "M01_SCRIPT_REVIEW.html"],
              os.listdir(os.path.join(w, "to_review")))
        check("the course folder itself holds only the three places",
              sorted(os.listdir(w)) == ["to_review", "working_claude"], os.listdir(w))
        check("... and a slide says where in the old course it comes from", "the photographs become a 3D model" in io.open(rp, encoding="utf-8").read())

        print("\n-- the old course, read whole")
        code, out = run("old_course.py", "inventory", old, "--course", master)
        inv = json.load(io.open(os.path.join(w, "working_claude", "old_course_inventory.json"), encoding="utf-8"))
        md = io.open(os.path.join(w, "working_claude", "OLD_COURSE_INVENTORY.md"), encoding="utf-8").read()
        deck = [f for s in inv["sections"] for f in s["files"] if f["type"] == "pptx"][0]
        check("every slide of a deck is read, in slide order: its title and words", [x["title"] for x in deck["slides"]] ==
              ["Gas tankers", "Type C tanks", "Membrane tanks"] and deck["slides"][1]["words"] >= 10, deck["slides"])
        check("... its pictures and its speaker notes", deck["slides"][1]["pictures"] == 2 and deck["slides"][1]["notes_words"] > 0, deck["slides"][1])
        doc = [f for s in inv["sections"] for f in s["files"] if f["type"] == "docx"][0]
        check("an exercise's headings and words are read, and it is known as the trainee's exercise",
              doc["headings"] == ["Gas tanker arrangement"] and doc["words"] > 5 and doc["role"] == "exercise_trainee", doc)
        check("a training film is listed as a possible real video", "training film" in md and "Loading.mp4" in md)
        check("an old .doc is flagged as not read - never skipped in silence", "NOT READ" in md and "Course Plan.doc" in md)
        check("lock files are left out, and counted", inv["lock_files_left_out"] == 1 and ".~lock" not in md)
        check("the summary counts it all", "4 files in 2 sections: 3 slides with 4 pictures, 1 training films; 1 could not be read" in out, out)
        code, out = run("old_course.py", "images", old, "--course", master)
        idx = json.load(io.open(os.path.join(w, "working_claude", "old_course_images", "_index.json"), encoding="utf-8"))
        got = sorted(os.listdir(os.path.join(w, "working_claude", "old_course_images", "1. Gas tankers", "1. Liquefied Gas tankers")))
        check("every picture in the old decks is copied out, named by its slide - a repeated logo kept once",
              got == ["slide01_logo.png", "slide02_a.png", "slide02_b.png"] and sum(1 for x in idx if x.get("repeat")) == 1, (got, idx))
        check("... marked usable as the owner decided (2026-10-01), with the deck and slide it came from",
              all(x.get("rights", "").startswith("OWNER_CLEARED") for x in idx if not x.get("repeat")) and idx[0]["deck"].endswith(".pptx"), idx)
        check("the lists are written into course\\working_claude only", not os.path.exists(os.path.join(old, "working_claude"))
              and not os.path.exists(os.path.join(master, "working_claude")) and not os.path.exists(os.path.join(w, "_factory")))

        print("\n-- an older course is tidied into the three places - moved, never deleted")
        legacy = os.path.join(tmp, "older", "course")
        for rel, txt in (("COURSE_STATE.md", "state"), ("FEEDBACK_LOG.md", "log"), ("factory-notes.md", "notes"), ("architecture.json", "{}"),
                         ("programme.json", "{}"), ("ARCHITECTURE_REVIEW.html", "<p>page</p>"), ("_factory/script/M01.json", "{}"),
                         ("_factory/intake.json", "{}"), ("review/M01_SCRIPT.docx", "docx"), ("review/M01_SCRIPT_REVIEW.html", "page"),
                         ("instructor_notes/M01_INSTRUCTOR_NOTES.md", "notes"), ("build/BUILD_BRIEF.md", "brief"),
                         ("COURSE_PATTERN_Gas.draft.md", "draft"), ("my own notes.txt", "mine")):
            os.makedirs(os.path.dirname(os.path.join(legacy, rel)), exist_ok=True)
            io.open(os.path.join(legacy, rel), "w", encoding="utf-8").write(txt)
        check("before tidying, the tools still find an older course's files where they are",
              workspace.claude_path(legacy, "COURSE_STATE.md") == os.path.join(legacy, "COURSE_STATE.md")
              and workspace.claude_path(legacy, "script", "M01.json") == os.path.join(legacy, "_factory", "script", "M01.json")
              and workspace.review_path(legacy, "M01_SCRIPT.docx", for_reading=True) == os.path.join(legacy, "review", "M01_SCRIPT.docx"))
        n_before = sum(len(f) for _, _, f in os.walk(legacy))
        code, out = run("workspace.py", "tidy", legacy)
        check("tidy moves every file the factory made into to_review and working_claude", code == 0
              and sorted(os.listdir(os.path.join(legacy, "to_review"))) == ["ARCHITECTURE_REVIEW.html", "COURSE_PATTERN_Gas.draft.md", "M01_INSTRUCTOR_NOTES.md", "M01_SCRIPT.docx", "M01_SCRIPT_REVIEW.html"]
              and os.path.isfile(os.path.join(legacy, "working_claude", "script", "M01.json"))
              and os.path.isfile(os.path.join(legacy, "working_claude", "COURSE_STATE.md"))
              and os.path.isfile(os.path.join(legacy, "working_claude", "build", "BUILD_BRIEF.md")), out)
        check("... deletes nothing - every file is still there, and what it does not know it leaves and names",
              sum(len(f) for _, _, f in os.walk(legacy)) == n_before and os.path.isfile(os.path.join(legacy, "my own notes.txt"))
              and "my own notes.txt" in out, out)
        check("... and afterwards the tools find everything in its new place",
              workspace.claude_path(legacy, "script", "M01.json") == os.path.join(legacy, "working_claude", "script", "M01.json"))

        print("\n-- the material is never changed")
        check("every file in source_files, the knowledge base and the old course is exactly as it was", fingerprint(master) == before)

        print("\n-- nothing the factory writes there ships to a tablet")
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "course-tablet-publisher", "scripts"))
        import gates
        plat = gates.load_platform()
        repo = os.path.join(tmp, "repo")
        base = os.path.join(repo, plat["asset_roots"]["trainee"], "courses", "x", "")
        for n in ("working_claude/old_course_inventory.json", "working_claude/OLD_COURSE_INVENTORY.md", "to_review/ARCHITECTURE_REVIEW.html"):
            check("the publisher sorts %s as INTERNAL" % n, gates.classify(repo, plat, base + n) == "INTERNAL", gates.classify(repo, plat, base + n))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("\n" + "=" * 72)
    print("%d passed, %d failed" % (len(PASS), len(FAIL)))
    if FAIL:
        return 1
    print("\nThe factory works in course\\ beside the material, never changes the material, and reads the old\n"
          "course whole before it plans what to keep, modernise and add.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
