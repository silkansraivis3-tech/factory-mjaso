# -*- coding: utf-8 -*-
"""exercises.py - every module with a practical exercise gets at least one deck slide about it (2.63.2).

    python exercises.py <course> --module 8            what the module's exercise documents are, and whether a slide has each
    python exercises.py <course> --module 8 --propose  write the proposed slide(s) as a changes file for content_script.py propose

WHY (owner rule, 2026-10-21; the 2.63.0 full-course cross-check: "the 16 practical exercises have no slide or time slot")
  The novikontas-practical-exercises skill writes each exercise as two Word forms - the TRAINEE form and the INSTRUCTOR
  form (course\\to_review\\exercises\\M08\\IGF_Exercise_8.1_Trainee_v01.docx, ..._Instructor_v01.docx). Nothing in the
  factory read them, so a module could be built with its exercise never shown or timed.

WHAT IT DOES
  Finds each module's exercise forms (course\\to_review\\exercises\\MNN\\ and working_claude\\exercises\\MNN\\). Reads the
  TRAINEE form only for what goes on screen - its number, title, duration, objective and what the trainees need; the
  INSTRUCTOR form is named in the slide's cue as the copy to run it from, and none of its words reach a screen.
  A module's exercise has its slide when an "activity" screen says "exercise": "<no>" (or its title names "Exercise <no>").
  --propose writes working_claude\\script\\MNN.exercise_slides.json: one "add_screen" per missing slide - an activity
  (room task) screen before the module check, its minutes the form's duration (practice minutes, counted in the module's
  hours), to be proposed and approved like any other change: content_script.py propose ... --changes <that file>.
  The compiler says a module with an exercise and no slide for it as a build problem (compile_module.py).
"""
from __future__ import annotations

import argparse
import glob
import io
import json
import os
import re
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import workspace  # noqa: E402

TRAINEE = re.compile(r"trainee", re.I)
INSTRUCTOR = re.compile(r"instructor", re.I)
NUMBER = re.compile(r"exercise[ _-]*(\d+(?:[._]\d+)?)", re.I)


def mid(module):
    return "M%02d" % int(module) if str(module).isdigit() else str(module).upper()


def paragraphs(path):
    """a .docx's paragraphs in order (a table's cells are paragraphs too), as plain text - no library needed"""
    try:
        with zipfile.ZipFile(path) as z:
            xml = z.read("word/document.xml").decode("utf-8", "replace")
    except (OSError, KeyError, zipfile.BadZipFile):
        return []
    out = []
    for p in re.findall(r"<w:p[ >].*?</w:p>", xml, re.S):
        t = re.sub(r"<w:tab/>", " ", p)
        t = re.sub(r"<[^>]+>", "", t)
        t = (t.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"').replace("&apos;", "'"))
        t = re.sub(r"\s+", " ", t).strip()
        if t:
            out.append(t)
    return out


def after(paras, label):
    """the paragraph after a label cell ("Title" -> "SDS hunt")"""
    for i, p in enumerate(paras[:-1]):
        if p.rstrip(":. ").lower() == label.lower():
            return paras[i + 1]
    return ""


def starting(paras, prefix):
    for p in paras:
        if p.lower().startswith(prefix.lower()):
            return p[len(prefix):].strip()
    return ""


def read(path):
    """the trainee form's own words: number, title, minutes, objective, what the trainees need"""
    ps = paragraphs(path)
    dur = re.search(r"(\d+)\s*min", after(ps, "Duration"), re.I)
    return {"no": after(ps, "Exercise No.") or after(ps, "Exercise No"), "title": after(ps, "Title"),
            "minutes": int(dur.group(1)) if dur else 0, "objective": after(ps, "Objective of Exercise"),
            "need": starting(ps, "What you need:")}


def folders(course, module):
    m = mid(module)
    return [os.path.join(course, "to_review", "exercises", m), workspace.claude_path(course, "exercises", m)]


def found(course, module):
    """[{no, title, minutes, objective, need, trainee, instructor}] - each exercise of the module whose TRAINEE form is there"""
    out = {}
    for d in folders(course, module):
        for f in sorted(glob.glob(os.path.join(d, "*.docx"))):
            name = os.path.basename(f)
            if name.startswith("~$"):
                continue
            n = NUMBER.search(name)
            key = n.group(1).replace("_", ".") if n else os.path.splitext(name)[0]
            e = out.setdefault(key, {"trainee": None, "instructor": None})
            if TRAINEE.search(name):
                e["trainee"] = f
            elif INSTRUCTOR.search(name):
                e["instructor"] = f
    exs = []
    for key, e in sorted(out.items(), key=lambda kv: [int(x) if x.isdigit() else x for x in re.split(r"[.]", kv[0])]):
        if not e["trainee"]:
            continue
        r = read(e["trainee"])
        r["no"] = r["no"] or key
        r.update(trainee=e["trainee"], instructor=e["instructor"])
        exs.append(r)
    return exs


def names(title, no):
    """the title names exercise <no>: "Exercise 9.2", "Practical 9.2", or a range that holds it, "Practicals 9.1-9.3" """
    if re.search(r"\b(?:exercises?|practicals?)\s+%s\b" % re.escape(no), title, re.I):
        return True
    m = re.match(r"(\d+)\.(\d+)$", no)
    for r in re.finditer(r"\b(?:exercises?|practicals?)\s+(\d+)\.(\d+)\s*[-–]\s*(?:(\d+)\.)?(\d+)\b", title, re.I):
        if m and r.group(1) == m.group(1) and (r.group(3) or r.group(1)) == m.group(1) \
                and int(r.group(2)) <= int(m.group(2)) <= int(r.group(4)):
            return True
    return False


def slide_of(script, ex):
    """the activity screen that is this exercise's slide, else None. 2.63.3 - or a slide of the practical track that names
    it (the IGF instructors' reviewed scripts: "kind": "slide", "track": "practical", "Practicals 9.1-9.3 - in the gas
    lab"; the 2.63.2 full-course build failed M08-M15 on a slide that was there)"""
    for s in script.get("screens", []):
        if s.get("kind") != "activity" and s.get("track") != "practical" and not s.get("practical_minutes"):
            continue
        if str(s.get("exercise") or "").strip() == ex["no"]:
            return s
        if names(s.get("title") or "", ex["no"]):
            return s
    return None


def missing(course, script):
    """the module's exercises with no slide"""
    if not course or not script.get("module"):
        return []
    return [ex for ex in found(course, script["module"]) if not slide_of(script, ex)]


def first_sentence(t):
    """the first sentence, its first clause when it goes on ("..., and to show you ...") - a proposal the operator edits"""
    t = re.split(r"(?<=[.!?])\s", t.strip(), 1)[0]
    t = re.split(r",\s+and to\s", t, 1)[0].rstrip(",;. ")
    return t + "."


def screen(ex, sid):
    """the proposed slide: the TRAINEE form's words only (what the trainees do, what they need, the time); the instructor
    form is named in the cue, never quoted"""
    do = re.sub(r"^to let (you|the trainees?)\s+", "", ex["objective"].strip(), flags=re.I)
    do = do[:1].upper() + do[1:]
    lines = [first_sentence(do)]
    if ex["need"]:
        lines.append("You need: " + first_sentence(ex["need"].split(";")[0]))
    if ex["minutes"]:
        lines.append("Time: %d min" % ex["minutes"])
    notes = "- Run it from the instructor copy%s." % (": " + os.path.basename(ex["instructor"]) if ex["instructor"] else "")
    return {"id": sid, "kind": "activity", "exercise": ex["no"], "title": "Exercise %s - %s" % (ex["no"], ex["title"]),
            "text": "\n".join(x for x in lines if x), "notes": notes, "minutes": ex["minutes"] or 1}


def proposal(script, exs):
    """changes for content_script.py propose: each missing exercise's slide, before the module check's task slide.
    Its minutes: the form's time when the script's allocation has room for it; a script whose minutes already fill its
    allocation gives the deck the programme's theory part only (IGF Basic: topic 8 theory 0.5 h + practical 0.5 h, the
    script 21 minutes) - the exercise is the practical part, so the slide takes 0 deck minutes and says its own time in
    "practice_minutes" (the IGF original course: data-mins 0, data-practical-mins the form's time)"""
    ids = {s.get("id") for s in script.get("screens", [])}
    sc = script.get("screens", [])
    mc = next((i for i, s in enumerate(sc) if s.get("kind") == "task-slide" and (s.get("opens") or "") == "MC"), None)
    if mc is not None:          # before the recap that leads into the module check (L51), not between them (IGF M08 rebuild)
        while mc > 0 and sc[mc - 1].get("recap"):
            mc -= 1
        mc = sc[mc]["id"]
    alloc = float(script.get("minutes_allocated") or 0)
    used = sum(float(s.get("minutes") or 0) for s in script.get("screens", []) if s.get("kind") in ("slide", "task-slide", "activity"))
    out = []
    for ex in exs:
        sid = "x" + re.sub(r"\W", "", ex["no"])
        while sid in ids:
            sid += "b"
        ids.add(sid)
        s = screen(ex, sid)
        if alloc and used + s["minutes"] > alloc + 0.5:
            s["practice_minutes"], s["minutes"] = s["minutes"], 0
            s["notes"] += "\n- Its %d min are the module's practical hours, not the deck's minutes." % s["practice_minutes"]
        else:
            used += s["minutes"]
        ch = {"add_screen": s}
        if mc:
            ch["before"] = mc
        out.append(ch)
    return out


def main(argv=None):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("course")
    ap.add_argument("--module", required=True)
    ap.add_argument("--propose", action="store_true")
    o = ap.parse_args(argv)
    sp = workspace.claude_path(o.course, "script", mid(o.module) + ".json")
    script = json.load(io.open(sp, encoding="utf-8")) if os.path.isfile(sp) else {"module": o.module, "screens": []}
    exs = found(o.course, o.module)
    if not exs:
        print("%s has no exercise forms (looked in %s)" % (mid(o.module), " and ".join(folders(o.course, o.module))))
        return 0
    miss = [ex for ex in exs if not slide_of(script, ex)]
    for ex in exs:
        s = slide_of(script, ex)
        print("  Exercise %s - %s (%d min): %s" % (ex["no"], ex["title"], ex["minutes"], ("slide " + s["id"]) if s else "NO SLIDE"))
    if o.propose and miss:
        out = workspace.claude_path(o.course, "script", mid(o.module) + ".exercise_slides.json")
        with io.open(out, "w", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(proposal(script, miss), ensure_ascii=False, indent=1))
        print("Proposed %d slide(s): %s\n    then: content_script.py propose \"%s\" --module %s --changes \"%s\""
              % (len(miss), out, o.course, o.module, out))
    return 1 if miss and not o.propose else 0


if __name__ == "__main__":
    sys.exit(main())
