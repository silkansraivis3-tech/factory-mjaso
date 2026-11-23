# -*- coding: utf-8 -*-
"""course_overview - the course's whole picture for LND: the programme outline with hours, the main ILOs and the files
a lecturer or reviewer wants at hand (2.138.0).

    course_overview.py <course folder>

Written into the course's modules folder on every compile (compile_course.py calls build() after the additional
materials, whose files it copies):

    _course_shell\\overview.json                   kind "course-overview", version 1 - outline, hours, ILOs, materials
    _course_shell\\materials\\<group-folder>\\<file>  the downloadable files it lists

Everything is read off files the factory already has, nothing is typed here: working_claude\\programme.json (topics with
hours, main ILOs, which topic teaches which), architecture.json (title, language, which source_files hold the
programme), project_work.json (card titles) and the paper in additional-materials\\ (project cards, course plan, day
sheets). The programme document itself - the Word or PDF file the course was built from - is found by the names
architecture.json course.programme_file and programme.json source give under source_files\\.

It sits under _course_shell\\, which the classroom's importer keeps under instructor\\ and never copies to the trainees
(package-core.mjs copies only a path with tasks, handout, documents, assets or assessment in it - so the group folders
here are programme, project-work, course-plan and day-sheets, and package_problems() refuses any other name). LND reads
the file and shows it on the course page and in the review editor; the detailed ILO map stays in ilo_coverage.json.

A course with no programme.json, or one with no topics, gets no overview: build() says why in plain words and the
package check fails with the same reason - an old course is rebuilt from its programme, not papered over.
Exit 0 written or already as it should be; 1 nothing could be written; 2 usage.
"""
from __future__ import annotations

import datetime
import hashlib
import html
import io
import json
import os
import re
import shutil
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import workspace  # noqa: E402

OUT_REL = "_course_shell/overview.json"
MATERIALS = "_course_shell/materials"
RECORD = "compiled_course.json"                      # the hash record compile_course.py keeps; the copies are noted there
KIND = "course-overview"
VERSION = 1
# materials group -> the folder it sits in. The folder names must not be tasks, handout, documents, assets or assessment:
# the importer copies a path with one of them in it to the trainees (TRAINEE_PATH below, package-core.mjs line 177)
FOLDERS = {"programme": "programme", "project": "project-work", "plan": "course-plan", "day-sheets": "day-sheets"}
TRAINEE_PATH = re.compile(r"(^|/)(tasks|handout|documents|assets|assessment)/", re.I)
SOURCE_DOC = re.compile(r"source_files[/\\]([^/\\()\[\]\n;,]+?\.(?:docx?|pdf))", re.I)
HOURS = ("theory", "practical", "total")


# ------------------------------------------------------------------ reading
def load(path, default=None):
    try:
        with io.open(path, encoding="utf-8-sig") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def num(v):
    """a number of hours as the programme gives it: 12 stays 12, 2.5 stays 2.5, anything else is 0"""
    try:
        x = float(v)
    except (TypeError, ValueError):
        return 0
    return int(x) if x == int(x) else round(x, 2)


def safe_name(name):
    """the classroom takes no space in a file name (check_course_package): letters, digits, . _ - only"""
    stem, ext = os.path.splitext(name)
    return (re.sub(r"[^A-Za-z0-9._-]+", "_", stem).strip("_") or "file") + ext.lower()


def nice(stem):
    """a file name as a title: Day_1_computers -> Day 1 computers"""
    s = re.sub(r"[_\s]+", " ", stem).strip()
    return s[:1].upper() + s[1:]


def programme_documents(course, arch, prog):
    """[path] of the programme files that exist: every source_files\\<name>.docx|doc|pdf that architecture.json
    course.programme_file or programme.json source names (free text - revision 2 and revision 3 may both be in it)"""
    text = " ".join(str(x) for x in ((arch.get("course") or {}).get("programme_file"), prog.get("source")) if x)
    folders = []
    for base in (workspace.master_of(course), course, os.path.dirname(course)):
        d = os.path.join(base, "source_files")
        if os.path.isdir(d) and d not in folders:
            folders.append(d)
    found = []
    for m in SOURCE_DOC.finditer(text):
        for d in folders:
            p = os.path.join(d, m.group(1).strip())
            if os.path.isfile(p) and p not in found:
                found.append(p)
                break
    # the first named is the programme in force; Word before PDF is not guessed - the author's own order stands
    return found


# ------------------------------------------------------------------ the overview
def outline_of(prog):
    """[row] one per programme topic, in order - topic n is module n (M%02d); None when the programme has no topics"""
    topics = prog.get("topics") or {}
    if not isinstance(topics, dict) or not topics:
        return None
    by_topic = {}
    for i, t in (prog.get("ilo_topic") or {}).items():
        by_topic.setdefault(str(t), []).append(str(i))
    rows = []
    for n in sorted(topics, key=lambda k: (int(k) if str(k).isdigit() else 10 ** 6, str(k))):
        t = topics[n] if isinstance(topics[n], dict) else {}
        theory, practical = num(t.get("theory")), num(t.get("practical"))
        k = int(n) if str(n).isdigit() else len(rows) + 1
        rows.append({"n": k, "module": "M%02d" % k, "title": str(t.get("title") or "").strip(),
                     "theory": theory, "practical": practical, "total": num(theory + practical),
                     "assessment": bool(t.get("assessment")),
                     "ilos": sorted(by_topic.get(str(n), []), key=lambda x: (int(x) if x.isdigit() else 10 ** 6, x)),
                     "topics": [{"ref": str(s.get("ref") or ""), "title": str(s.get("title") or "").strip()}
                                for s in t.get("subtopics") or [] if isinstance(s, dict)]})
    return rows


def ilos_of(prog, outline):
    rows = []
    for i, text in sorted((prog.get("main_ilos") or {}).items(), key=lambda kv: (int(kv[0]) if str(kv[0]).isdigit() else 10 ** 6, str(kv[0]))):
        rows.append({"id": str(i), "text": str(text or "").strip(), "modules": [r["module"] for r in outline if str(i) in r["ilos"]]})
    return rows


def hours_of(prog, outline):
    """the programme's own total row when it has one, else the sum of the topics; the check compares the two"""
    tr = prog.get("total_row") or {}
    h = {k: num(sum(r[k] for r in outline)) for k in HOURS}
    for k in HOURS:                                   # a total row may give only some of the three: those it gives stand
        if tr.get(k) not in (None, ""):
            h[k] = num(tr.get(k))
    h["note"] = str(tr.get("note") or "")
    return h


def material_rows(course):
    """[(group, title, source path)] of the paper beside the course that LND shows for download"""
    root = os.path.join(course, workspace.ADDITIONAL)
    names = lambda *p: sorted(f for f in (os.listdir(os.path.join(root, *p)) if os.path.isdir(os.path.join(root, *p)) else [])
                              if os.path.isfile(os.path.join(root, *p, f)))
    out = []
    pw = load(workspace.claude_path(course, "project_work.json"), {}) or {}
    cards = {}
    for p in pw.get("projects") or []:
        if isinstance(p, dict) and p.get("code"):
            cards[str(p["code"]).upper()] = p
    # a project card as PDF; a course that has only the Word files gives those
    kind = "pdf" if names("project-cards", "pdf") else "docx"
    for f in names("project-cards", kind):
        code = f.split("_", 1)[0].upper()
        p = cards.get(code)
        title = ("%s - %s%s" % (code, p.get("title"), " (%s)" % p["department"] if p.get("department") else "")) if p else nice(os.path.splitext(f)[0])
        out.append(("project", "Project work card " + title, os.path.join(root, "project-cards", kind, f)))
    for f in names("acp"):
        if f.lower().endswith(".docx"):
            out.append(("plan", "Course plan (ACP)", os.path.join(root, "acp", f)))
    for f in names("day-sheets"):
        if f.lower().endswith(".pdf"):
            # the file name is cut short; the page it was printed from has the full title
            page = os.path.join(root, "day-sheets", os.path.splitext(f)[0] + ".html")
            m = re.search(r"<title>([^<]+)", open(page, encoding="utf-8", errors="replace").read(4000)) if os.path.isfile(page) else None
            out.append(("day-sheets", html.unescape(m.group(1)).strip()[:140] if m else nice(os.path.splitext(f)[0]),
                        os.path.join(root, "day-sheets", f)))
    return out


def reason_none(course, prog):
    if not prog:
        return "working_claude\\programme.json is missing, so there is no programme outline to show"
    return "working_claude\\programme.json has no topics, so there is no programme outline to show"


def build(course, title, record=None, quiet=False):
    """write the overview and copy the materials into the course's modules folder; (written paths, problems).
    `record` is compile_course's hash record: every file written is noted in it (key = path in the modules folder)."""
    modules = os.path.join(course, workspace.MODULES)
    if not os.path.isdir(modules):
        return [], ["there is no modules folder yet - nothing to write the overview into"]
    arch = load(workspace.claude_path(course, "architecture.json"), {}) or {}
    prog = load(workspace.claude_path(course, "programme.json"), {}) or {}
    outline = outline_of(prog)
    if outline is None:
        return [], ["No course overview was written: %s. Add the programme's topics (Stage 1 intake) and compile again - "
                    "the package check stops the course until it has one" % reason_none(course, prog)]
    probs, written = [], []
    rec = record if record is not None else {}
    shell = os.path.join(modules, "_course_shell")
    mats, used = [], set()

    def copy(group, mtitle, src):
        rel = "%s/%s/%s" % (MATERIALS[len("_course_shell/"):], FOLDERS[group], safe_name(os.path.basename(src)))
        if rel in used:                                   # two sources with one clean name: the second gets a number
            stem, ext = os.path.splitext(rel)
            rel = "%s_%d%s" % (stem, len(used), ext)
        used.add(rel)
        dst = os.path.join(shell, *rel.split("/"))
        data = open(src, "rb").read()
        if not (os.path.isfile(dst) and open(dst, "rb").read() == data):
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with open(dst, "wb") as f:
                f.write(data)
            written.append(dst)
        rec["_course_shell/" + rel] = hashlib.sha256(data).hexdigest()
        mats.append({"group": group, "title": mtitle, "file": rel, "size": len(data)})

    docs = programme_documents(course, arch, prog)
    for i, p in enumerate(docs):
        copy("programme", "Study course programme" if i == 0 else "Study course programme - " + nice(os.path.splitext(os.path.basename(p))[0]), p)
    if not docs:
        probs.append("the programme document was not found: name it in architecture.json course.programme_file as "
                     "source_files/<file>.docx (or .pdf) and put the file there - the overview needs it")
    for group, mtitle, src in material_rows(course):
        copy(group, mtitle, src)
    # a copy this tool made before and no longer makes is moved aside, never deleted (L8)
    mdir = os.path.join(shell, *MATERIALS[len("_course_shell/"):].split("/"))
    old = os.path.join(workspace.claude_path(course, "additional_materials"), "old", time.strftime("%Y-%m-%d"))
    keep = set(os.path.normpath(os.path.join(shell, *m["file"].split("/"))) for m in mats)
    for dp, _, fs in os.walk(mdir):
        for f in fs:
            p = os.path.normpath(os.path.join(dp, f))
            if p not in keep:
                dst = os.path.join(old, os.path.relpath(p, course))
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.move(p, dst)
                rec.pop(os.path.relpath(p, modules).replace("\\", "/"), None)
                if not quiet:
                    print("Moved aside (no longer made): %s" % os.path.relpath(p, course))
    hours = hours_of(prog, outline)
    got = {k: num(sum(r[k] for r in outline)) for k in HOURS}
    if any(got[k] != hours[k] for k in HOURS):
        probs.append("the programme's topic hours add up to %s theory + %s practical = %s, but its total row says %s + %s = %s - "
                     "correct working_claude\\programme.json (topics or total_row), then compile again"
                     % (got["theory"], got["practical"], got["total"], hours["theory"], hours["practical"], hours["total"]))
    doc = {"kind": KIND, "version": VERSION, "built": datetime.date.today().isoformat(),
           "course": {"title": title, "language": str((arch.get("course") or {}).get("course_language") or prog.get("language") or "English")},
           "programme": {"source": str(prog.get("source") or ""), "academic_hour_min": num(prog.get("academic_hour_min")) or 45},
           "hours": hours, "outline": outline, "ilos": ilos_of(prog, outline), "materials": mats}
    out = os.path.join(shell, "overview.json")
    before = load(out, None)
    if isinstance(before, dict) and {k: v for k, v in before.items() if k != "built"} == {k: v for k, v in doc.items() if k != "built"}:
        doc["built"] = before.get("built") or doc["built"]            # nothing changed: the same file, the same day
    text = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    if not (os.path.isfile(out) and io.open(out, encoding="utf-8").read() == text):
        os.makedirs(shell, exist_ok=True)
        with io.open(out, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        written.append(out)
    rec[OUT_REL] = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return written, probs


# ------------------------------------------------------------------ the package check
def package_problems(folder):
    """[problem] of the package's _course_shell\\overview.json - it is required: every compiled course carries it"""
    p = os.path.join(folder, *OUT_REL.split("/"))
    fix = "run the course compile again (compile_course.py) - it writes the overview from the programme"
    if not os.path.isfile(p):
        return ["%s is missing - LND shows the course's whole picture from it; %s (a course with no programme.json topics "
                "cannot have one: the compile says so)" % (OUT_REL, fix)]
    try:
        doc = json.load(io.open(p, encoding="utf-8-sig"))
    except ValueError:
        return ["%s is not valid JSON - %s" % (OUT_REL, fix)]
    if not isinstance(doc, dict) or doc.get("kind") != KIND:
        return ["%s must be an object with \"kind\": \"%s\" - %s" % (OUT_REL, KIND, fix)]
    probs = []
    outline = doc.get("outline")
    if not isinstance(outline, list) or not outline or not all(isinstance(r, dict) for r in outline):
        return ["%s has an empty outline - the programme has no topics to show; %s" % (OUT_REL, fix)]
    hours = doc.get("hours") if isinstance(doc.get("hours"), dict) else {}
    for k in HOURS:
        s = num(sum(num(r.get(k)) for r in outline))
        if s != num(hours.get(k)):
            probs.append("%s: the outline's %s hours add up to %s but the overview says %s - correct programme.json, then %s"
                         % (OUT_REL, k, s, num(hours.get(k)), fix))
    mats = doc.get("materials")
    mats = mats if isinstance(mats, list) else []
    if not any(isinstance(m, dict) and m.get("group") == "programme" for m in mats):
        probs.append("%s lists no programme document - put the programme file in source_files, name it in architecture.json "
                     "course.programme_file, then %s" % (OUT_REL, fix))
    shell = os.path.join(folder, "_course_shell")
    for m in mats:
        f = str(m.get("file") or "") if isinstance(m, dict) else ""
        if not f or not os.path.isfile(os.path.join(shell, *f.split("/"))):
            probs.append("%s lists %s, which is not in _course_shell - %s" % (OUT_REL, f or "a material with no file", fix))
        elif TRAINEE_PATH.search("_course_shell/" + f):
            probs.append("%s: %s would be copied to the trainee tablets - the materials are the lecturer's; rename the folder "
                         "(never tasks, handout, documents, assets or assessment)" % (OUT_REL, f))
    return probs


# ------------------------------------------------------------------ the command
def title_of(course):
    arch = load(workspace.claude_path(course, "architecture.json"), {}) or {}
    intake = load(workspace.claude_path(course, "intake.json"), {}) or {}
    return str(intake.get("course_name") or "").strip() or str((arch.get("course") or {}).get("title") or "").strip()


def main(argv=None):
    a = list(sys.argv[1:] if argv is None else argv)
    if len(a) != 1:
        print(__doc__.split("\n")[0] + "\n    course_overview.py <course folder>")
        return 2
    course = workspace.work_folder(a[0], create=False)
    rec_p = workspace.claude_path(course, RECORD)
    rec = load(rec_p, {}) or {}
    written, probs = build(course, title_of(course) or "Course", rec)
    if os.path.isdir(os.path.join(course, workspace.MODULES)):
        import content_script as cs                       # here, not at the top: only the command needs it
        cs.save(rec_p, rec)                               # writes only when a hash changed
    print("Built %d file(s): %s" % (len(written), OUT_REL) if written else "Nothing changed - the overview is as the last build wrote it.")
    for x in probs:
        print("  - " + x)
    return 1 if probs else 0


if __name__ == "__main__":
    sys.exit(main())
