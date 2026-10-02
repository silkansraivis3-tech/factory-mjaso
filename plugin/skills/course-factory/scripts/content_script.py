#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Stage 3 - the module content script, word for word, and the operator's corrections to it (L29).

    content_script.py render   <course> --module 1           review page + Word file for the operator
    content_script.py read     <course> --module 1 [--docx F] [--pdf F]   what the operator changed -> PENDING
    content_script.py propose  <course> --module 1 --changes changes.json  a chat correction -> PENDING
    content_script.py apply    <course> --module 1 --confirmed           apply PENDING - only after the operator said yes
    content_script.py approve  <course> --module 1 --by "<name>"         the operator's "next"
    content_script.py status   <course> --module 1

WHY THIS EXISTS
Until 2.16.0 the operator saw the real words of a module for the first time in finished HTML, and
every correction landed on built pages. Now the words are approved first. The script is a file -
working_claude/script/M01.json - holding the whole lesson in the order it is taught. What the operator checks -
the review page, the Word file, the instructor notes - goes into to_review/ (L44).

TWO TABLETS (owner, 2026-09-30 - L35)
The course runs on two tablets, and the script is shown the same way:
  * INSTRUCTOR TABLET - the slides, mirrored to the classroom screen: each slide's exact text, its
    planned picture, its minutes and the instructor notes (on the instructor's panel only). When it
    is time for a task, the slide is a TASK SLIDE (kind "task-slide", "opens": "SC1"): its words only
    say that a task starts now and what it is about, and the instructor's panel has one button,
    OPEN TASK. The task itself is never on a slide.
  * TRAINEE TABLET - only the tasks: self-checks, the module check, the final assessment. A task
    opens on every trainee tablet when the instructor presses OPEN TASK, and only then; no task list,
    no browsing, no "all tasks" or "back" button. One question per screen ("set": "SC1"), and at the
    end the trainee sees their own score - for them, not counted. Only the final assessment is graded.

ENOUGH THEORY BEFORE ANY TASK (owner, 2026-09-30 - L36)
knowledge/theory-rules.json sets the floors, and every finding is shown at the top of the review
page: a slide too thin to teach from, instructor notes too thin to explain from, a module whose words
do not fill its minutes, a self-check with too little theory before it, a question whose answer is
not in the slides already taught, a task written onto a slide, minutes that do not add up to the
programme's. For every question the page names the slide that teaches its answer.

PICTURES AND TASKS (owner, 2026-09-30 - L37, L38)
Every slide leaves room for its picture and says what it is: "visual_kind" (a photograph, a schematic, a
step animation, a 3D model, a video ... - knowledge/media-and-tasks.json), "visual" (what it shows) and
"layout". The review page draws that place on the slide, says who makes each picture - the factory, the
image generator, the sources, Novikontas (a photo, a film, a 3D scan) or outside help - and lists what
Novikontas has to capture. Every task says how the trainee answers ("mechanic"): choose one, choose all
that are right, choose-and-justify, order, match, sort into groups, complete the sentence, tap the place,
label the drawing, find the hazards, read the instrument, set the value, operate the panel, a scenario.
The answer of all but the choosing ones is one editable text box, one line per item, "*" marking what is
right. The floors - no module of plain "choose one", a hands-on question in every module, something that
moves where the theory is long - are checked like the theory.

THE OPERATOR'S COPY IS A WORD FILE (owner, 2026-09-30)
render writes review/M01_SCRIPT.docx beside a review page that prints to PDF. Every editable text is
its own Word box (a content control, tagged with the screen and field, locked against deletion but
not against typing). The operator may type in the boxes, or add Word comments; read takes both.
Tracked changes are read as they would stand if accepted; the list says which were tracked, and by
whom. What it cannot read reliably, it says plainly: a box deleted outright, text typed outside the
boxes, a comment it cannot place on a screen.

NOTHING IS APPLIED UNTIL THE OPERATOR SAYS YES (owner, 2026-09-30)
read and propose never change the script. They write working_claude/script/M01.pending.json and print the
plain list of what was understood - "slide 7: X becomes Y; self-check 1, question 3: the correct
answer becomes B". Only apply --confirmed changes the script, logs each change in FEEDBACK_LOG.md,
and re-renders both files. Any change after approval puts the module back to draft; approve records
who approved which version.

Standard library only - it runs on any colleague's computer. PDF comments need the pypdf package;
without it, read says so and asks for the comments in Word or in the chat instead.
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import html
import io
import json
import os
import re
import shutil
import sys
import zipfile
from datetime import date, datetime
from xml.etree import ElementTree as ET

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
SKILLS = os.path.dirname(SKILL)
LABELS = json.load(io.open(os.path.join(SKILL, "knowledge", "page-labels.json"), encoding="utf-8"))
RULES = json.load(io.open(os.path.join(SKILL, "knowledge", "theory-rules.json"), encoding="utf-8"))
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
Q = lambda t: "{%s}%s" % (W, t)

sys.path.insert(0, HERE)
import check_slide_text as slide_text  # noqa: E402  - the same four rules the built slides get (L22)
import workspace  # noqa: E402  - the factory works in course\ beside the operator's material (L40)

MEDIA = json.load(io.open(os.path.join(SKILL, "knowledge", "media-and-tasks.json"), encoding="utf-8"))
KINDS = ("slide", "task-slide", "activity", "self-check", "module-check", "final")
TASKS = ("self-check", "module-check", "final")          # trainee tablet - one question per screen
INSTRUCTOR = ("slide", "task-slide", "activity")          # instructor tablet - the classroom screen
SLIDE_FIELDS = ("title", "text", "visual_kind", "visual", "notes", "minutes")
TASK_SLIDE_FIELDS = ("title", "text", "notes", "minutes")
FAIL, NOTE = slide_text.FAIL, slide_text.NOTE

# how a trainee answers (L38) - which parts of a task each mechanic uses; knowledge/media-and-tasks.json names them
MECHANICS = [k for k in MEDIA["mechanics"] if not k.startswith("_")]
USES = {"single_choice": {"options"}, "multi_select": {"options"}, "choose_and_justify": {"options", "answer"},
        "order": {"answer"}, "match": {"answer"}, "categorise": {"answer"}, "cloze": {"answer"},
        "hotspot": {"answer", "visual"}, "label_diagram": {"answer", "visual"}, "spot_the_hazard": {"answer", "visual"},
        "read_instrument": {"options", "visual"}, "set_value": {"answer", "visual"}, "panel_operate": {"answer", "visual"},
        "scenario": {"answer"}}
OLD_MECHANIC = {"tap to choose": "single_choice", "": "single_choice", None: "single_choice"}
VISUAL_KINDS = [k for k in MEDIA["visual_kinds"] if not k.startswith("_")]


def mech(s):
    m = s.get("mechanic")
    return OLD_MECHANIC.get(m, m)


def uses(s, part):
    return part in USES.get(mech(s), {"options"})


# ------------------------------------------------------------------ files
def mid(module):
    return "FINAL" if str(module).lower() == "final" else "M%02d" % int(module)


def paths(course, module):
    m = mid(module)
    d = workspace.claude_path(course, "script")          # the factory's own copy (L44)
    r = workspace.review_dir(course)                     # what the operator checks (L44)
    return {"script": os.path.join(d, m + ".json"), "pending": os.path.join(d, m + ".pending.json"),
            "old": os.path.join(d, "old"), "review": os.path.join(r, m + "_SCRIPT_REVIEW.html"),
            "docx": os.path.join(r, m + "_SCRIPT.docx"), "dir": d, "rdir": r,
            "notes_md": os.path.join(r, m + "_INSTRUCTOR_NOTES.md")}


def load(p):
    with io.open(p, encoding="utf-8") as f:
        return json.load(f)


def save(p, obj):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with io.open(p, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.write("\n")


def content_hash(script):
    return hashlib.sha256(json.dumps(script.get("screens", []), ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()[:16]


def T(script, key, **kw):
    lang = script.get("operator_language", "en")
    s = LABELS.get(lang, {}).get(key) or LABELS["en"].get(key) or key
    return s.format(**kw) if kw else s


def course_lang(script):
    return LABELS["course_language_codes"].get(script.get("course_language", ""), "en")


# ------------------------------------------------------------------ where things are, in words
def plan_of(script):
    """Slide numbers on the instructor tablet, and the task sets on the trainee tablet, in order."""
    slide_no, sets, set_of = {}, [], {}
    n = 0
    for s in script.get("screens", []):
        if s.get("kind") in INSTRUCTOR:
            n += 1
            slide_no[s["id"]] = n
        elif s.get("kind") in TASKS:
            k = s.get("set") or {"self-check": "SC", "module-check": "MC", "final": "FA"}[s["kind"]]
            if k not in set_of:
                set_of[k] = {"id": k, "kind": s["kind"], "questions": [], "opened_by": None}
                sets.append(set_of[k])
            set_of[k]["questions"].append(s)
    for s in script.get("screens", []):
        if s.get("kind") == "task-slide" and s.get("opens") in set_of and not set_of[s["opens"]]["opened_by"]:
            set_of[s["opens"]]["opened_by"] = s["id"]
    k = 0
    for st in sets:
        if st["kind"] == "self-check":
            k += 1
            st["no"] = k
    return slide_no, sets, set_of


def set_name(script, st):
    if st["kind"] == "self-check":
        return T(script, "s_sc_name", k=st.get("no", "?"))
    return T(script, "s_mc_name" if st["kind"] == "module-check" else "s_fa_name")


def place(script, sid):
    """'slide 7' or 'self-check 1, question 3' - how the operator finds it on the page."""
    slide_no, sets, _ = plan_of(script)
    if sid in slide_no:
        return T(script, "s_slide_n", n=slide_no[sid])
    for st in sets:
        for q, s in enumerate(st["questions"], 1):
            if s["id"] == sid:
                return T(script, "s_question_in", set=set_name(script, st), q=q)
    return sid


# ------------------------------------------------------------------ fields
def letters(n):
    return [chr(ord("A") + i) for i in range(n)]


def kind_label(kind, lang="en"):
    """The operator's words for a kind of visual - 'none' and an unknown kind are shown as written."""
    k = MEDIA["visual_kinds"].get(kind)
    if kind == "none":
        return {"lv": "nav - kopsavilkuma slaids", "ru": "нет - итоговый слайд"}.get(lang, "none - a summary slide")
    return (k.get(lang) or k["en"]) if k else (kind or "")


def parse_kind(text):
    """A kind as the operator typed it - its id or its name in any language - back to its id."""
    t = (text or "").strip().lower()
    if t in MEDIA["visual_kinds"] or t == "none":
        return t
    for k in VISUAL_KINDS:
        for lang in ("en", "lv", "ru"):
            if MEDIA["visual_kinds"][k].get(lang, "").lower() == t:
                return k
    if t.startswith(("none", "nav", "нет")):
        return "none"
    return text


def mech_label(m, lang="en"):
    k = MEDIA["mechanics"].get(m) or {}
    return k.get(lang) or k.get("en") or m


def fields_of(screen, lang="en"):
    """Every editable field of one screen as (field id, value) - options become opt.A, opt.B ...; the kind of
    visual is shown in the operator's words. How the trainee answers is not a box: changing it changes what the
    answer is, so it goes through the chat."""
    out = []
    if screen["kind"] in TASKS:
        out.append(("question", screen.get("question", "")))
        if uses(screen, "visual"):
            out += [("visual_kind", kind_label(screen.get("visual_kind", ""), lang)), ("visual", screen.get("visual", ""))]
        if uses(screen, "options"):
            for L, o in zip(letters(len(screen.get("options", []))), screen.get("options", [])):
                out.append(("opt." + L, o))
            out.append(("correct", screen.get("correct", "")))
        if uses(screen, "answer"):
            out.append(("answer", screen.get("answer", "")))
        out.append(("feedback", screen.get("feedback", "")))
    else:
        names = TASK_SLIDE_FIELDS if screen["kind"] == "task-slide" else SLIDE_FIELDS
        for f in names:
            v = screen.get(f, "")
            out.append((f, kind_label(v, lang) if f == "visual_kind" else ("" if v is None else str(v))))
    return out


def get_field(screen, f, lang="en"):
    if f.startswith("opt."):
        i = ord(f[4]) - ord("A")
        opts = screen.get("options", [])
        return opts[i] if 0 <= i < len(opts) else None
    v = screen.get(f, "")
    if f == "visual_kind":
        return kind_label(v, lang)
    return "" if v is None else str(v)


def set_field(screen, f, value):
    if f.startswith("opt."):
        i = ord(f[4]) - ord("A")
        opts = screen.setdefault("options", [])
        while len(opts) <= i:
            opts.append("")
        opts[i] = value
    elif f == "visual_kind":
        screen[f] = parse_kind(value)
    elif f == "minutes":
        try:
            screen[f] = float(value) if "." in value else int(value)
        except ValueError:
            screen[f] = value
    else:
        screen[f] = value


def minutes(s):
    try:
        return float(s.get("minutes") or 0)
    except (TypeError, ValueError):
        return 0.0


SET_VALUE = re.compile(r"^\s*(-?\d+(?:[.,]\d+)?)\s*([^\s±+]*)\s*(?:±|\+/-)\s*(\d+(?:[.,]\d+)?)\s*,\s*range\s+"
                       r"(-?\d+(?:[.,]\d+)?)\s*(?:to|–|-)\s*(-?\d+(?:[.,]\d+)?)\s*$", re.I)


def lines_of(text):
    return [x.strip() for x in (text or "").split("\n") if x.strip()]


def starred(line):
    return line.rstrip().endswith("*") or line.lstrip().startswith("*")


def unstar(line):
    return line.strip().strip("*").strip()


def correct_letters(s):
    return [x.strip().upper() for x in re.split(r"[,\s;]+", str(s.get("correct", ""))) if x.strip()]


def read_answer(s):
    """A task's answer as the operator wrote it, taken apart: (problems, the right answer's words, the wrong
    answers' words). The right answer's words feed the 'was it taught?' check (L36); the wrong ones are left out
    of it, so a word every option shares does not count as taught."""
    m, sid, probs, right, wrong = mech(s), s.get("id"), [], [], []
    opts = s.get("options", [])
    if m not in USES:
        return ["%s: unknown way of answering %r - use one of: %s" % (sid, s.get("mechanic"), ", ".join(MECHANICS))], [], []
    if uses(s, "options"):
        L = correct_letters(s)
        if len(opts) < 2:
            probs.append("%s: a task needs at least two answers to choose from" % sid)
        if not L or any(x not in letters(len(opts)) for x in L):
            probs.append("%s: the correct answer %r is not one of %s" % (sid, s.get("correct"), "/".join(letters(len(opts)))))
        elif m != "multi_select" and len(L) != 1:
            probs.append("%s: '%s' has exactly one correct answer, not %s" % (sid, mech_label(m), ", ".join(L)))
        elif m == "multi_select" and len(L) == len(opts):
            probs.append("%s: in 'choose all that are right', not every answer may be right" % sid)
        right += [o for x, o in zip(letters(len(opts)), opts) if x in L]
        wrong += [o for x, o in zip(letters(len(opts)), opts) if x not in L]
    if uses(s, "visual") and not (s.get("visual") or "").strip():
        probs.append("%s: '%s' needs the picture, drawing or panel it is done on - say what it shows" % (sid, mech_label(m)))
    if not uses(s, "answer"):
        return probs, right, wrong
    ls = lines_of(s.get("answer"))
    if m in ("order", "label_diagram"):
        if len(ls) < 3:
            probs.append("%s: '%s' needs at least three items, one per line" % (sid, mech_label(m)))
        right += ls
    elif m == "match":
        bad = [x for x in ls if x.count("=") != 1]
        if len(ls) < 3 or bad:
            probs.append("%s: 'match the pairs' needs at least three lines written as: left = right" % sid)
        right += ls
    elif m == "categorise":
        groups = [x.split(":", 1) for x in ls]
        if len(groups) < 2 or any(len(g) != 2 or not [i for i in g[1].split(";") if i.strip()] for g in groups):
            probs.append("%s: 'sort into groups' needs at least two lines written as: Group: item; item" % sid)
        right += ls
    elif m in ("hotspot", "spot_the_hazard", "choose_and_justify"):
        good = [unstar(x) for x in ls if starred(x)]
        if len(ls) < 3 or not good:
            probs.append("%s: '%s' needs at least three lines, the right one(s) marked *" % (sid, mech_label(m)))
        if m == "choose_and_justify" and len(good) != 1:
            probs.append("%s: 'choose the action, then the reason' needs exactly one reason marked *" % sid)
        right += good
        wrong += [unstar(x) for x in ls if not starred(x)]
    elif m == "cloze":
        gaps = re.findall(r"\[([^\]]+)\]", s.get("answer", ""))
        if not gaps:
            probs.append("%s: 'complete the sentence' needs at least one gap written as [right* | wrong | wrong]" % sid)
        for g in gaps:
            parts = [p.strip() for p in g.split("|")]
            good = [unstar(p) for p in parts if starred(p)]
            if len(parts) < 2 or len(good) != 1:
                probs.append("%s: every gap needs two or more choices, exactly one marked * - [%s]" % (sid, g))
            right += good
            wrong += [unstar(p) for p in parts if not starred(p)]
    elif m == "set_value":
        mm = SET_VALUE.match(s.get("answer", "") or "")
        if not mm:
            probs.append("%s: 'set the value' is written as one line: value unit ± tolerance, range low to high "
                         "(e.g. -42 °C ± 2, range -60 to 20)" % sid)
        else:
            v, lo, hi = (float(mm.group(i).replace(",", ".")) for i in (1, 4, 5))
            if not lo <= v <= hi:
                probs.append("%s: the value %g is outside its own range %g to %g" % (sid, v, lo, hi))
            right.append("%s %s" % (mm.group(1), mm.group(2)))
    elif m == "panel_operate":
        if not ls or any(x.count("=") != 1 for x in ls):
            probs.append("%s: 'operate the panel' needs one line per control: control = the state it must end in" % sid)
        right += ls
    elif m == "scenario":
        if len(ls) < 2:
            probs.append("%s: a scenario needs at least two steps, one per line" % sid)
        for x in ls:
            if "=>" not in x:
                probs.append("%s: each scenario step is written as: situation => right action* | wrong | wrong" % sid)
                continue
            acts = [a.strip() for a in x.split("=>", 1)[1].split("|")]
            good = [unstar(a) for a in acts if starred(a)]
            if len(acts) < 2 or len(good) != 1:
                probs.append("%s: every scenario step needs two or more actions, exactly one marked *" % sid)
            right += good
            wrong += [unstar(a) for a in acts if not starred(a)]
    return probs, right, wrong


def answer_items(s):
    """The visible pieces of an answer-box task - what a built task page shows, one element each with
    data-script-field="answer" - and the ones marked right (data-correct="true"). check_script_match compares
    them as a set, since the tablet shuffles them."""
    m, ls, items, right = mech(s), lines_of(s.get("answer")), [], []
    if m in ("order", "label_diagram"):
        items = [unstar(x) for x in ls]
    elif m in ("hotspot", "spot_the_hazard", "choose_and_justify"):
        items = [unstar(x) for x in ls]
        right = [unstar(x) for x in ls if starred(x)]
    elif m in ("match", "panel_operate"):
        items = [p.strip() for x in ls for p in x.split("=", 1)]
    elif m == "categorise":
        for x in ls:
            g, _, rest = x.partition(":")
            items += [g.strip()] + [i.strip() for i in rest.split(";") if i.strip()]
    elif m == "cloze":
        text = s.get("answer", "")
        items = [t.strip() for t in re.split(r"\[[^\]]+\]", text) if t.strip()]
        for g in re.findall(r"\[([^\]]+)\]", text):
            parts = [p.strip() for p in g.split("|")]
            items += [unstar(p) for p in parts]
            right += [unstar(p) for p in parts if starred(p)]
    elif m == "scenario":
        for x in ls:
            sit, _, acts = x.partition("=>")
            items.append(sit.strip())
            for a in acts.split("|"):
                if a.strip():
                    items.append(unstar(a))
                    if starred(a):
                        right.append(unstar(a))
    return items, right


def validate(script):
    probs, seen = [], set()
    screens = script.get("screens", [])
    for i, s in enumerate(screens):
        sid = s.get("id")
        if not sid or sid in seen:
            probs.append("screen %d has no id, or an id used twice (%s)" % (i + 1, sid))
        seen.add(sid)
        if s.get("kind") not in KINDS:
            probs.append("screen %s: unknown kind %r" % (sid, s.get("kind")))
        if s.get("kind") == "slide" and s.get("visual_kind") and parse_kind(s["visual_kind"]) not in VISUAL_KINDS + ["none"]:
            probs.append("%s: unknown kind of visual %r - use one of: %s" % (sid, s["visual_kind"], ", ".join(VISUAL_KINDS)))
        if s.get("kind") in TASKS:
            probs += read_answer(s)[0]
            if not s.get("feedback"):
                probs.append("%s: no feedback for the trainee after answering" % sid)
            if s.get("kind") == "module-check" and s.get("graded"):
                probs.append("%s: a module check is not graded (L27)" % sid)
    slide_no, sets, set_of = plan_of(script)
    kinds = [s.get("kind") for s in screens]
    index = {s.get("id"): i for i, s in enumerate(screens)}
    for s in screens:
        if s.get("kind") == "task-slide" and s.get("opens") not in set_of:
            probs.append("%s: a task slide must say which task it opens (\"opens\": the task's set) - %r opens nothing" % (s["id"], s.get("opens")))
    for st in sets:
        name = set_name(script, st)
        if not st["opened_by"]:
            probs.append("%s: no task slide opens it - on the tablet a task opens only when the instructor presses "
                         "OPEN TASK on a task slide (L35)" % name)
            continue
        start = index[st["opened_by"]]
        qi = [index[q["id"]] for q in st["questions"]]
        if qi != list(range(start + 1, start + 1 + len(qi))):
            probs.append("%s: its questions must come straight after the task slide that opens it (%s), one after another"
                         % (name, st["opened_by"]))
    if script.get("module") != "final" and str(script.get("module")).lower() != "final":
        if "module-check" not in kinds:
            probs.append("the module has no module check - every teaching module ends with one (L27)")
        else:
            first = kinds.index("module-check")
            if any(k in ("slide", "activity") for k in kinds[first:]):
                probs.append("a slide comes after the module check starts - the module check is the end of the module")
    alloc = script.get("minutes_allocated")
    if alloc:
        got = sum(minutes(s) for s in screens if s.get("kind") in INSTRUCTOR)
        if abs(got - float(alloc)) > 0.5:
            probs.append("the minutes add up to %g, the programme gives this module %g - they must be equal (L1)" % (got, float(alloc)))
    return probs


# ------------------------------------------------------------------ enough theory (L36)
STOP = set("""about above after again against also among another around because been before being below between both
could does doing down during each either every from further have having here into itself just least less made make
many more most much must near never only other over same should since some such than that their them then there these
they this those through under until upon very were what when where which while will with within without would your
kas kad kur kurš kura kuri kuras kuru tiek tikt tiem tās tajā tiek būt būs bija arī tikai ļoti starp pirms pēc
vairāk mazāk visi visas viss katrs katra tāpēc tomēr nevis gan kādā kāda kādi
это этот эта эти если когда также только между может может быть более менее очень после перед который которая
которые которых""".split())
NUM = re.compile(r"[-−–]?\d+(?:[.,]\d+)?")


def words(text):
    return re.findall(r"\w+", text or "", re.UNICODE)


def wc(*texts):
    return sum(len(words(t)) for t in texts)


def terms(text):
    t = (text or "").lower()
    nums = {n.replace("−", "-").replace("–", "-").replace(",", ".") for n in NUM.findall(t)}
    ws = {w[:5] for w in re.findall(r"[^\W\d_]{4,}", t, re.UNICODE) if w not in STOP}
    return nums, ws


def taught_share(answer, taught, others=()):
    """How much of an answer's key words are in the taught text: numbers exactly, words by their first
    five letters (so 'membrane' finds 'membranes', and Latvian and Russian endings still match). Words
    the wrong answers share are left out when anything is left - 'semi-refrigerated' is taught by
    'semi', not by 'refrigerated', which every option about cold cargo has."""
    an, aw = terms(answer)
    on, ow = set(), set()
    for o in others:
        n, w = terms(o)
        on |= n
        ow |= w
    if (an - on) or (aw - ow):
        an, aw = an - on, aw - ow
    if not an and not aw:
        return None
    tn, tw = taught
    tn_abs = {x.lstrip("-") for x in tn}
    hit = sum(1 for n in an if n in tn or n.lstrip("-") in tn_abs) + sum(1 for w in aw if w in tw)
    return hit / float(len(an) + len(aw))


def slide_terms(s):
    return terms("%s\n%s\n%s" % (s.get("title", ""), s.get("text", ""), s.get("notes", "")))


def theory_findings(script):
    """Everything L36 asks, as findings shown at the top of the review page. Also returns, for every
    question, the slide(s) that teach its answer - the page shows them beside the question."""
    R = RULES
    screens = script.get("screens", [])
    slide_no, sets, set_of = plan_of(script)
    found, taught_on = [], {}
    final = str(script.get("module")).lower() == "final"

    def add(sid, field, level, key, **kw):
        found.append({"where": place(script, sid) if sid else T(script, "s_the_module"), "screen": sid or "", "field": field,
                      "level": level, "rule": key, "detail": T(script, key, **kw), "fix": ""})

    th_words = th_min = 0.0
    for s in screens:
        if s.get("kind") != "slide":
            continue
        w_slide = wc(s.get("title", ""), s.get("text", ""))
        w_notes = wc(s.get("notes", ""))
        th_words += w_slide + w_notes
        th_min += minutes(s)
        if w_slide < R["slide"]["min_words"]:
            add(s["id"], "text", FAIL, "t_thin_slide", w=w_slide, min=R["slide"]["min_words"])
        elif w_slide > R["slide"]["max_words"]:
            add(s["id"], "text", NOTE, "t_long_slide", w=w_slide, max=R["slide"]["max_words"])
        if w_notes < R["notes"]["min_words"]:
            add(s["id"], "notes", FAIL, "t_thin_notes", w=w_notes, min=R["notes"]["min_words"])
        elif w_notes > R["notes"]["max_words"]:
            add(s["id"], "notes", FAIL, "t_long_notes", w=w_notes, max=R["notes"]["max_words"])
    if th_min and not final:
        rate = th_words / th_min
        if rate < R["module"]["min_words_per_theory_minute"]:
            add(None, "", FAIL, "t_density", w=int(th_words), min="%g" % th_min, rate="%.0f" % rate,
                floor=R["module"]["min_words_per_theory_minute"])

    # a block of new theory before every self-check; every answer taught before its task opens
    since_min = since_words = 0.0
    seen_slides = []
    for s in screens:
        k = s.get("kind")
        if k == "slide":
            since_min += minutes(s)
            since_words += wc(s.get("title", ""), s.get("text", ""), s.get("notes", ""))
            seen_slides.append(s)
        elif k == "task-slide":
            st = set_of.get(s.get("opens"))
            if st and st["kind"] == "self-check":
                rb = R["before_self_check"]
                if since_min < rb["min_minutes"] or since_words < rb["min_words"]:
                    add(s["id"], "", FAIL, "t_before_sc", set=set_name(script, st), min="%g" % since_min, w=int(since_words),
                        fmin=rb["min_minutes"], fw=rb["min_words"])
                n = len(st["questions"])
                if n < R["self_check"]["min_questions"]:
                    add(s["id"], "", FAIL, "t_sc_small", set=set_name(script, st), q=n, lo=R["self_check"]["min_questions"])
                elif n > R["self_check"]["max_questions"]:
                    add(s["id"], "", NOTE, "t_sc_big", set=set_name(script, st), q=n, hi=R["self_check"]["max_questions"])
            if st and st["kind"] == "module-check" and len(st["questions"]) < R["module_check"]["min_questions"]:
                add(s["id"], "", FAIL, "t_mc_small", q=len(st["questions"]), lo=R["module_check"]["min_questions"])
            if st:
                slide_words = terms("%s %s" % (s.get("title", ""), s.get("text", "")))[1]
                for q in st["questions"]:
                    qw = terms(q.get("question", ""))[1]
                    if len(qw) >= 3 and len(qw & slide_words) >= 0.8 * len(qw):
                        add(s["id"], "text", FAIL, "t_task_on_slide", set=set_name(script, st))
                        break
                if not final:
                    for q in st["questions"]:
                        _, right, others = read_answer(q)
                        answer = "\n".join(right)
                        if not any(terms(answer)):
                            answer, others = q.get("feedback", ""), []
                        each = [(taught_share(answer, slide_terms(x), others) or 0, x) for x in seen_slides]
                        union = (set().union(*[slide_terms(x)[0] for x in seen_slides]) if seen_slides else set(),
                                 set().union(*[slide_terms(x)[1] for x in seen_slides]) if seen_slides else set())
                        share = taught_share(answer, union, others)
                        best = sorted([e for e in each if e[0] >= 0.3], key=lambda e: -e[0])[:2]
                        taught_on[q["id"]] = sorted(slide_no[x["id"]] for _, x in best)
                        if share is not None and share < R["answers_taught_first"]["min_share"]:
                            add(q["id"], "question", FAIL, "t_not_taught")
            since_min = since_words = 0.0
    return found, taught_on


# ------------------------------------------------------------------ the text check, before HTML (2.16.1)
def text_findings(script):
    """check_slide_text's four rules on every screen of the script - internal abbreviations, a model
    course cited as a source, version control on the opening slide, the factory's own markers.
    What the trainee sees is checked as a presentation page (a finding must be fixed); the
    instructor notes and the planned-picture note are instructor-only (reported, never failed)."""
    rules = slide_text.load_rules(slide_text.RULES)
    first_slide = next((s["id"] for s in script.get("screens", []) if s.get("kind") in INSTRUCTOR), None)
    found, seen = [], set()
    for s in script.get("screens", []):
        course_facing = ["title", "text"] if s["kind"] not in TASKS else \
            ["question"] + ["opt." + L for L in letters(len(s.get("options", [])))] + (["answer"] if uses(s, "answer") else []) + ["feedback"]
        opening = ("%s\n%s" % (s.get("title", ""), s.get("text", ""))) if s["id"] == first_slide else ""
        for f, kind in [(x, "presentation") for x in course_facing] + [("notes", "instructor"), ("visual", "instructor")]:
            text = get_field(s, f) or ""
            if not text.strip():
                continue
            out = []
            slide_text.scan_text(text, opening if f in ("title", "question") else "", "%s.%s" % (s["id"], f), kind, rules, out)
            for x in out:
                key = (s["id"], f, x.rule, x.detail)
                if key not in seen:
                    seen.add(key)
                    found.append({"where": place(script, s["id"]), "screen": s["id"], "field": f, "level": x.level,
                                  "rule": x.rule, "detail": x.detail, "fix": x.fix})
    return found


def media_findings(script):
    """L37, L38 - every slide leaves room for a named visual, a module moves where it can, and the tasks are
    varied and hands-on. Floors: knowledge/media-and-tasks.json."""
    F = MEDIA["floors"]
    found = []
    lang = script.get("operator_language", "en")

    def add(sid, field, level, key, **kw):
        found.append({"where": place(script, sid) if sid else T(script, "s_the_module"), "screen": sid or "", "field": field,
                      "level": level, "rule": key, "detail": T(script, key, **kw), "fix": ""})

    slides = [s for s in script.get("screens", []) if s.get("kind") == "slide"]
    kinds = []
    for s in slides:
        k = parse_kind(s.get("visual_kind", ""))
        if k == "none" or not (k or "").strip():
            # no quota (owner, 2.18.1): a slide with no picture is a suggestion - the summary slide not even that
            if s is not slides[-1]:
                add(s["id"], "visual_kind", NOTE, "v_none")
            continue
        if k not in VISUAL_KINDS:
            add(s["id"], "visual_kind", FAIL, "v_no_kind")
        elif not (s.get("visual") or "").strip():
            add(s["id"], "visual", FAIL, "v_no_what", kind=kind_label(k, lang))
        if k in VISUAL_KINDS:
            kinds.append(k)
            if MEDIA["visual_kinds"][k]["made_by"] == "nano_banana":
                add(s["id"], "visual_kind", NOTE, "v_generated", kind=kind_label(k, lang))
    final = str(script.get("module")).lower() == "final"
    th_min = sum(minutes(s) for s in slides)
    if not final and slides:
        moving = [k for k in kinds if MEDIA["visual_kinds"][k]["family"] in ("moving", "interactive", "3d", "video")]
        if th_min >= F["moving_or_3d_per_module_from_min"] and not moving:      # suggestions, not rules (2.18.1)
            add(None, "", NOTE, "v_no_motion", min="%g" % th_min)
        if len(slides) >= F["min_visual_kinds_from_slides"] and len(set(kinds)) < F["min_visual_kinds"]:
            add(None, "", NOTE, "v_few_kinds", n=len(set(kinds)), lo=F["min_visual_kinds"])

    slide_no, sets, set_of = plan_of(script)
    qs = [q for st in sets if st["kind"] != "final" for q in st["questions"]]
    for st in sets:
        if st["kind"] == "final":
            continue
        ms = {mech(q) for q in st["questions"]}
        lo = F["self_check_min_mechanics"] if st["kind"] == "self-check" else F["module_check_min_mechanics"]
        if len(st["questions"]) >= lo and len(ms) < lo:
            add(st["opened_by"], "", FAIL, "m_mix", set=set_name(script, st), n=len(ms), lo=lo)
    if qs and not final:
        share = sum(1 for q in qs if mech(q) == "single_choice") / float(len(qs))
        if share > F["single_choice_max_share"]:
            add(None, "", FAIL, "m_too_much_choice", pct="%.0f" % (100 * share), max="%.0f" % (100 * F["single_choice_max_share"]))
        if sum(1 for q in qs if MEDIA["mechanics"].get(mech(q), {}).get("hands_on")) < F["hands_on_min_per_module"]:
            add(None, "", FAIL, "m_no_hands_on")
        run = 1
        for a, b in zip(qs, qs[1:]):
            run = run + 1 if mech(a) == mech(b) else 1
            if run == F["max_same_in_a_row"] + 1:
                add(b["id"], "", NOTE, "m_same_in_a_row", n=run, how=mech_label(mech(b), lang))
    return found


def all_findings(script):
    th, _ = theory_findings(script)
    return th + media_findings(script) + text_findings(script)


def blocking(findings):
    return [f for f in findings if f["level"] == FAIL]


# ------------------------------------------------------------------ operator-stated facts
def operator_facts(course, script):
    facts = [dict(f) for f in script.get("operator_facts", [])]
    fb = workspace.claude_path(course, "FEEDBACK_LOG.md")
    if os.path.isfile(fb):
        for line in io.open(fb, encoding="utf-8").read().splitlines():
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) >= 6 and cells[0].isdigit() and cells[5].lower().startswith("yes"):
                if str(script.get("module")) in cells[2] or mid(script.get("module")) in cells[2] or "M%s" % script.get("module") in cells[2]:
                    facts.append({"fact": cells[3], "where": cells[2], "said": cells[1]})
    return facts


def summary(script):
    screens = script.get("screens", [])
    sl = [s for s in screens if s.get("kind") == "slide"]
    th_min = sum(minutes(s) for s in sl)
    return {"slides": len([s for s in screens if s.get("kind") in INSTRUCTOR]), "theory_min": th_min,
            "task_min": sum(minutes(s) for s in screens if s.get("kind") == "task-slide"),
            "practice_min": sum(minutes(s) for s in screens if s.get("kind") == "activity"),
            "slide_words": sum(wc(s.get("title", ""), s.get("text", "")) for s in sl),
            "note_words": sum(wc(s.get("notes", "")) for s in sl),
            "total_min": sum(minutes(s) for s in screens if s.get("kind") in INSTRUCTOR)}


# ------------------------------------------------------------------ the review page
FAMILY_MARK = {"still": "▣", "moving": "▶", "interactive": "☝", "3d": "⬢", "video": "●"}


def media_summary(script):
    """What the module shows and asks, counted - and every picture someone outside the factory has to make."""
    lang = script.get("operator_language", "en")
    slide_no, sets, _ = plan_of(script)
    kinds, who, mechs = {}, {}, {}
    for s in script.get("screens", []):
        if s.get("kind") in ("slide",) or (s.get("kind") in TASKS and uses(s, "visual")):
            k = parse_kind(s.get("visual_kind", ""))
            if k in VISUAL_KINDS:
                kinds[k] = kinds.get(k, 0) + 1
                who.setdefault(MEDIA["visual_kinds"][k]["made_by"], []).append(
                    (place(script, s["id"]), kind_label(k, lang), s.get("visual", "")))
        if s.get("kind") in TASKS and s.get("kind") != "final":
            mechs[mech(s)] = mechs.get(mech(s), 0) + 1
    return {"kinds": kinds, "who": who, "mechs": mechs}


def media_summary_html(e, V, script):
    lang = script.get("operator_language", "en")
    sm = media_summary(script)
    fam = lambda k: MEDIA["visual_kinds"][k]["family"]
    kinds = ", ".join("%s %s × %d" % (FAMILY_MARK[fam(k)], kind_label(k, lang), n) for k, n in sorted(sm["kinds"].items(), key=lambda x: -x[1]))
    mechs = ", ".join("%s × %d" % (mech_label(m, lang), n) for m, n in sorted(sm["mechs"].items(), key=lambda x: -x[1]))
    o = ['<div class="card"><h3>%s</h3><table class="nums"><tr><td>%s</td><td>%s</td></tr><tr><td>%s</td><td>%s</td></tr></table>' % (
        e(T(script, "s_msum_title")), e(T(script, "s_msum_kinds")), e(kinds) or "—", e(T(script, "s_msum_mechs")), e(mechs) or "—")]
    for key in ("novikontas", "outside", "nano_banana"):
        items = sm["who"].get(key)
        if not items:
            continue
        mb = MEDIA["made_by"][key]
        o.append('<h4>%s (%d)</h4><p class="note">%s</p><ul>%s</ul>' % (
            e(mb.get(lang) or mb["en"]), len(items), e(mb["how"]),
            "".join("<li><b>%s</b> · %s — %s</li>" % (e(w), e(k), V(d)) for w, k, d in items)))
    made_here = sum(len(sm["who"].get(k, [])) for k in ("factory", "sources"))
    o.append('<p class="note">%s</p></div>' % e(T(script, "s_msum_factory", n=made_here)))
    return "".join(o)


def visual_box(e, V, script, kind, desc, small=False):
    """The place the picture takes on the slide or the task, with what it is and who makes it (L37)."""
    lang = script.get("operator_language", "en")
    k = parse_kind(kind)
    info = MEDIA["visual_kinds"].get(k)
    if k == "none":
        return '<div class="vbox none"><span class="vk">%s</span></div>' % e(kind_label("none", lang))
    who = MEDIA["made_by"].get(info["made_by"], {}) if info else {}
    return ('<div class="vbox%s%s"><span class="vk">%s %s</span><span class="vd">%s</span><span class="vw">%s</span></div>' % (
        " small" if small else "", " f-" + info["family"] if info else " unknown",
        FAMILY_MARK.get(info["family"], "?") if info else "?", e(kind_label(k, lang) if info else kind or T(script, "v_no_kind_short")),
        V(desc) if desc else "<b>%s</b>" % e(T(script, "v_no_what_short")), e(who.get(lang) or who.get("en") or "")))


def task_body(e, V, script, s):
    """The task as the trainee's tablet shows it - one mock per way of answering (L38)."""
    m, L, lang = mech(s), correct_letters(s), script.get("operator_language", "en")
    ls = lines_of(s.get("answer"))
    out = []
    if uses(s, "visual"):
        out.append(visual_box(e, V, script, s.get("visual_kind", ""), s.get("visual"), small=True))
    if uses(s, "options"):
        box = "☐" if m == "multi_select" else ""
        out.append("".join('<div class="opt%s"><b>%s%s</b> %s</div>' % (" right" if x in L else "", box, x, V(o))
                           for x, o in zip(letters(len(s.get("options", []))), s.get("options", []))))
    if m == "choose_and_justify":
        out.append('<p class="mh">%s</p>%s' % (e(T(script, "mm_reason")), "".join(
            '<div class="opt%s">%s</div>' % (" right" if starred(x) else "", V(unstar(x))) for x in ls)))
    elif m == "order":
        out.append('<p class="mh">%s</p><ol class="steps">%s</ol>' % (e(T(script, "mm_order")), "".join("<li>%s</li>" % V(x) for x in ls)))
    elif m == "match":
        out.append('<p class="mh">%s</p><table class="pairs">%s</table>' % (e(T(script, "mm_match")), "".join(
            "<tr><td>%s</td><td>⟷</td><td>%s</td></tr>" % (V(x.split("=", 1)[0].strip()), V(x.split("=", 1)[-1].strip())) for x in ls)))
    elif m == "categorise":
        cols = []
        for x in ls:
            g, _, items = x.partition(":")
            cols.append('<div class="grp"><b>%s</b>%s</div>' % (V(g.strip()), "".join(
                '<span class="chip">%s</span>' % V(i.strip()) for i in items.split(";") if i.strip())))
        out.append('<p class="mh">%s</p><div class="grps">%s</div>' % (e(T(script, "mm_categorise")), "".join(cols)))
    elif m == "cloze":
        def gap(mo):
            parts = [p.strip() for p in mo.group(1).split("|")]
            return '<span class="gap">%s</span>' % " / ".join(
                ('<b class="ok">%s</b>' if starred(p) else "%s") % html.escape(unstar(p)) for p in parts)
        out.append('<p class="mh">%s</p><p class="cloze" lang="%s">%s</p>' % (
            e(T(script, "mm_cloze")), course_lang(script), re.sub(r"\[([^\]]+)\]", gap, html.escape(s.get("answer", "")))))
    elif m in ("hotspot", "spot_the_hazard", "label_diagram"):
        key = {"hotspot": "mm_hotspot", "spot_the_hazard": "mm_hazard", "label_diagram": "mm_label"}[m]
        out.append('<p class="mh">%s</p>%s' % (e(T(script, key)), "".join(
            '<span class="chip%s">%s</span>' % (" ok" if (starred(x) or m == "label_diagram") else "", V(unstar(x))) for x in ls)))
    elif m == "set_value":
        mm = SET_VALUE.match(s.get("answer", "") or "")
        if mm:
            v, lo, hi = (float(mm.group(i).replace(",", ".")) for i in (1, 4, 5))
            pos = 0 if hi == lo else 100.0 * (v - lo) / (hi - lo)
            out.append('<p class="mh">%s</p><div class="slider"><span class="lo">%s</span><span class="track"><span class="knob" style="left:%.1f%%"></span></span>'
                       '<span class="hi">%s</span></div><p><b>%s %s</b> ± %s</p>' % (
                           e(T(script, "mm_set")), e(mm.group(4)), pos, e(mm.group(5)), e(mm.group(1)), e(mm.group(2)), e(mm.group(3))))
    elif m == "panel_operate":
        out.append('<p class="mh">%s</p><table class="pairs">%s</table>' % (e(T(script, "mm_panel")), "".join(
            "<tr><td>%s</td><td>→</td><td><b>%s</b></td></tr>" % (V(x.split("=", 1)[0].strip()), V(x.split("=", 1)[-1].strip())) for x in ls)))
    elif m == "scenario":
        steps = []
        for n, x in enumerate(ls, 1):
            sit, _, acts = x.partition("=>")
            steps.append('<div class="step"><p><b>%d.</b> %s</p>%s</div>' % (n, V(sit.strip()), "".join(
                '<div class="opt%s">%s</div>' % (" right" if starred(a) else "", V(unstar(a))) for a in acts.split("|") if a.strip())))
        out.append('<p class="mh">%s</p>%s' % (e(T(script, "mm_scenario")), "".join(steps)))
    return "".join(out)


def render_html(course, script):
    e = lambda s: html.escape(str(s if s is not None else ""))
    cl = course_lang(script)
    V = lambda s: '<span class="verb" lang="%s">%s</span>' % (cl, e(s).replace("\n", "<br>")) if s else "—"
    css = "".join(io.open(os.path.join(SKILLS, "course-module-ui", "templates", n), encoding="utf-8").read() + "\n"
                  for n in ("gb_tokens.css", "gb_page.css"))
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)   # the style files' comments are for maintainers (L25)
    css += """
.verb{font-family:var(--font)} .screen{page-break-inside:avoid;break-inside:avoid}
.sid{font-family:var(--mono);color:var(--faint-l);font-size:13px}
.kind{display:inline-block;padding:.15em .6em;border-radius:var(--r-s);font-size:13px;font-weight:700;background:var(--grey)}
.k-slide,.k-activity{background:var(--blue-wash-l);color:var(--navy)} .k-task-slide{background:var(--amber-wash-l);color:var(--amber-ink)}
.k-self-check,.k-module-check{background:var(--good-wash-l);color:var(--good)} .k-final{background:var(--amber-wash-l);color:var(--amber-ink)}
.part{border-top:4px solid var(--navy);margin-top:34px;padding-top:4px}
.slidetext{font-size:17px;line-height:1.5;background:var(--white);border:1px solid var(--line-l);border-radius:var(--r-m);padding:12px 16px}
.slidetext h3{margin:0 0 8px;color:var(--navy)}
.tablet{border:1px solid var(--line-l);border-radius:var(--r-l);padding:16px;max-width:520px;background:var(--white)}
.opt{display:flex;gap:10px;align-items:center;min-height:52px;border:1.5px solid var(--line-l);border-radius:var(--r-m);padding:10px 14px;margin:8px 0}
.opt.right{border-color:var(--good);background:var(--good-wash-l)} .opt b{min-width:1.6em}
.openbtn{display:inline-block;background:var(--navy);color:var(--white);font-weight:700;letter-spacing:.04em;padding:10px 22px;border-radius:var(--r-m)}
.panel{display:flex;gap:14px;align-items:center;flex-wrap:wrap;margin-top:10px}
.result{border:2px dashed var(--line-l);border-radius:var(--r-l);padding:12px 16px;max-width:520px}
dl{display:grid;grid-template-columns:12em 1fr;gap:6px 14px;margin:8px 0 0} dt{color:var(--dim-l);font-weight:700} dd{margin:0}
.instr{border-left:4px solid var(--amber);background:var(--amber-wash-l);padding:8px 12px;border-radius:0 var(--r-s) var(--r-s) 0}
.nums td{padding:4px 12px 4px 0}
.slidebox{display:grid;grid-template-columns:55fr 45fr;gap:12px;align-items:stretch}
.slidebox.l-visual_wide{grid-template-columns:35fr 65fr} .slidebox.l-visual_full{grid-template-columns:1fr}
.slidebox.l-visual_full .vbox{min-height:220px;order:-1}
.vbox{display:flex;flex-direction:column;justify-content:center;gap:6px;min-height:170px;border:2px dashed var(--line-l);
  border-radius:var(--r-m);padding:12px 14px;background:var(--grey);font-size:14.5px}
.vbox.small{min-height:110px;margin:0 0 10px} .vbox.f-moving,.vbox.f-3d,.vbox.f-video,.vbox.f-interactive{border-color:var(--navy)}
.vbox.unknown{border-color:var(--warn)} .vbox.none{min-height:60px;opacity:.7}
.vk{font-weight:700;color:var(--navy)} .vw{color:var(--dim-l);font-size:13px}
.mh{margin:10px 0 4px;color:var(--dim-l);font-size:13.5px;font-weight:700}
.steps li{border:1.5px solid var(--line-l);border-radius:var(--r-m);padding:8px 12px;margin:6px 0;list-style-position:inside}
.pairs td{padding:6px 8px;border-bottom:1px solid var(--line-l)}
.grps{display:flex;gap:10px;flex-wrap:wrap} .grp{flex:1 1 140px;border:1.5px solid var(--line-l);border-radius:var(--r-m);padding:8px}
.grp b{display:block;margin-bottom:6px;color:var(--navy)}
.chip{display:inline-block;border:1.5px solid var(--line-l);border-radius:var(--r-m);padding:4px 10px;margin:3px}
.chip.ok{border-color:var(--good);background:var(--good-wash-l)}
.gap{border-bottom:2px solid var(--navy);padding:0 4px} .ok{color:var(--good)}
.slider{display:flex;align-items:center;gap:10px} .track{position:relative;flex:1;height:8px;background:var(--line-l);border-radius:4px}
.knob{position:absolute;top:-7px;width:22px;height:22px;margin-left:-11px;border-radius:50%;background:var(--navy)}
.step{border-left:3px solid var(--line-l);padding-left:10px;margin:8px 0}
.mech{display:inline-block;padding:.15em .6em;border-radius:var(--r-s);font-size:13px;font-weight:700;background:var(--blue-wash-l);color:var(--navy)}
.mech.hands{background:var(--amber-wash-l);color:var(--amber-ink)}
h1,h2{color:var(--navy)} @media (max-width:640px){dl{grid-template-columns:1fr}.slidebox{grid-template-columns:1fr}} @media print{body{background:#fff}.card{box-shadow:none}}
"""
    status = (T(script, "s_status_approved", by=script.get("approved_by", ""), on=script.get("approved_on", ""))
              if script.get("status") == "approved" and script.get("approved_hash") == content_hash(script)
              else T(script, "s_status_draft"))
    title = T(script, "s_page_title", m=script.get("module"))
    slide_no, sets, set_of = plan_of(script)
    th_found, taught_on = theory_findings(script)
    o = ['<!DOCTYPE html><html lang="%s"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
         '<title>%s</title><style>%s</style></head><body><div class="wrap">' % (e(script.get("operator_language", "en")), e(title), css),
         "<h1>%s</h1><p class=\"sub\">%s · <b>%s</b></p><p class=\"lead\">%s</p>" % (e(title), V(script.get("title", "")), e(status), e(T(script, "s_intro")))]
    sm = summary(script)
    alloc = script.get("minutes_allocated")
    o.append('<div class="card key"><h3>%s</h3><table class="nums">'
             '<tr><td>%s</td><td><b>%d</b></td></tr><tr><td>%s</td><td><b>%g</b> %s</td></tr><tr><td>%s</td><td><b>%g</b> %s</td></tr>%s'
             '<tr><td>%s</td><td><b>%g</b> %s%s</td></tr><tr><td>%s</td><td><b>%d</b> + <b>%d</b> = <b>%d</b> (%s)</td></tr></table></div>' % (
                 e(T(script, "s_sum_title")), e(T(script, "s_sum_slides")), sm["slides"],
                 e(T(script, "s_sum_theory")), sm["theory_min"], e(T(script, "s_min")),
                 e(T(script, "s_sum_tasks")), sm["task_min"], e(T(script, "s_min")),
                 ("<tr><td>%s</td><td><b>%g</b> %s</td></tr>" % (e(T(script, "s_sum_practice")), sm["practice_min"], e(T(script, "s_min")))) if sm["practice_min"] else "",
                 e(T(script, "s_sum_total")), sm["total_min"], e(T(script, "s_min")),
                 (" — " + e(T(script, "s_sum_alloc", a="%g" % float(alloc)))) if alloc else "",
                 e(T(script, "s_sum_words")), sm["slide_words"], sm["note_words"], sm["slide_words"] + sm["note_words"],
                 e(T(script, "s_sum_rate", r="%.0f" % ((sm["slide_words"] + sm["note_words"]) / sm["theory_min"]) if sm["theory_min"] else "—",
                     f=RULES["module"]["min_words_per_theory_minute"]))))
    facts = operator_facts(course, script)
    if facts:
        o.append('<div class="card hot"><h3>%s</h3><p class="note">%s</p><ul>%s</ul></div>' % (
            e(T(script, "s_facts_title")), e(T(script, "s_facts_intro")),
            "".join("<li>%s <span class=\"sid\">(%s%s)</span></li>" % (V(f.get("fact")), e(f.get("where", "")),
                    (", " + e(f["said"])) if f.get("said") else "") for f in facts)))
    row = lambda f: '<li><b>%s%s</b> — %s%s <i>(%s)</i></li>' % (
        e(f["where"]), (" · " + e(f["field"])) if f["field"] else "", e(f["detail"]),
        (" <b>%s:</b> %s" % (e(T(script, "s_textcheck_instead")), e(f["fix"]))) if f["fix"] else "",
        e(T(script, "s_textcheck_must") if f["level"] == FAIL else T(script, "s_textcheck_note")))
    if th_found:
        o.append('<div class="card warn"><h3>%s</h3><p class="note">%s</p><ul>%s</ul></div>' % (
            e(T(script, "s_theory_title")), e(T(script, "s_theory_intro")), "".join(row(f) for f in th_found)))
    else:
        o.append('<p class="note">%s</p>' % e(T(script, "s_theory_clean")))
    mf = media_findings(script)
    if mf:
        o.append('<div class="card warn"><h3>%s</h3><p class="note">%s</p><ul>%s</ul></div>' % (
            e(T(script, "s_media_title")), e(T(script, "s_media_intro")), "".join(row(f) for f in mf)))
    else:
        o.append('<p class="note">%s</p>' % e(T(script, "s_media_clean")))
    tf = text_findings(script)
    if tf:
        o.append('<div class="card warn"><h3>%s</h3><p class="note">%s</p><ul>%s</ul></div>' % (
            e(T(script, "s_textcheck_title")), e(T(script, "s_textcheck_intro")), "".join(row(f) for f in tf)))
    else:
        o.append('<p class="note">%s</p>' % e(T(script, "s_textcheck_clean")))
    o.append(media_summary_html(e, V, script))

    # ---- part 1: the instructor tablet
    o.append('<div class="part"><h2>%s</h2><p class="note">%s</p></div>' % (e(T(script, "s_part1")), e(T(script, "s_part1_intro"))))
    for s in script.get("screens", []):
        k = s.get("kind")
        if k not in INSTRUCTOR:
            continue
        label = {"slide": "s_slide", "task-slide": "s_task_slide", "activity": "s_activity"}[k]
        o.append('<div class="card screen"><h2>%s <span class="kind k-%s">%s</span> <span class="sid">%s</span></h2>' % (
            e(T(script, "s_slide_n", n=slide_no[s["id"]])), e(k), e(T(script, label)), e(s.get("id"))))
        if k == "task-slide":
            o.append('<div class="slidetext"><h3>%s</h3>%s</div>' % (V(s.get("title")), V(s.get("text"))))
        else:
            o.append('<div class="slidebox l-%s"><div class="slidetext"><h3>%s</h3>%s</div>%s</div>' % (
                e(s.get("layout") or "split"), V(s.get("title")), V(s.get("text")),
                visual_box(e, V, script, s.get("visual_kind", ""), s.get("visual"))))
        if k == "task-slide":
            st = set_of.get(s.get("opens"))
            o.append('<div class="panel"><span class="openbtn">%s</span><span>%s</span></div>' % (
                e(T(script, "s_open_task")), e(T(script, "s_opens", set=set_name(script, st) if st else "?",
                                                 q=len(st["questions"]) if st else 0))))
            o.append('<dl><dt>%s</dt><dd>%s</dd></dl>' % (e(T(script, "s_minutes_task")), e(s.get("minutes", "—"))))
        else:
            o.append('<dl><dt>%s</dt><dd>%s</dd><dt>%s</dt><dd>%s</dd><dt>%s</dt><dd>%s</dd></dl>' % (
                e(T(script, "s_layout")), e((MEDIA["layouts"].get(s.get("layout") or "split") or {}).get(script.get("operator_language", "en"), s.get("layout", ""))),
                e(T(script, "s_minutes")), e(s.get("minutes", "—")),
                e(T(script, "s_words")), e(T(script, "s_words_n", a=wc(s.get("title", ""), s.get("text", "")), b=wc(s.get("notes", ""))))))
        if s.get("from_old"):        # L41 - where in the old course this slide comes from, and what changed
            o.append('<p class="note"><b>%s:</b> %s</p>' % (e(T(script, "s_from_old")), e(s["from_old"])))
        if s.get("notes"):
            o.append('<div class="instr"><b>%s</b><ul lang="%s">%s</ul></div>' % (
                e(T(script, "s_notes")), cl, "".join("<li>%s</li>" % e(x[2:]) for x in note_lines(s.get("notes")))))
        o.append("</div>")

    # ---- part 2: the trainee tablet
    o.append('<div class="part"><h2>%s</h2><p class="note">%s</p></div>' % (e(T(script, "s_part2")), e(T(script, "s_part2_intro"))))
    for st in sets:
        opener = st["opened_by"]
        o.append('<h2>%s <span class="kind k-%s">%s</span></h2><p class="note">%s</p>' % (
            e(set_name(script, st)), e(st["kind"]),
            e(T(script, {"self-check": "s_self_check", "module-check": "s_module_check", "final": "s_final"}[st["kind"]])),
            e(T(script, "s_set_intro", slide=slide_no.get(opener, "?"), q=len(st["questions"])))))
        for qn, s in enumerate(st["questions"], 1):
            hands = MEDIA["mechanics"].get(mech(s), {}).get("hands_on")
            o.append('<div class="card screen"><h3>%s <span class="mech%s">%s</span> <span class="sid">%s</span></h3>' % (
                e(T(script, "s_question_n", q=qn, of=len(st["questions"]))), " hands" if hands else "",
                e(mech_label(mech(s), script.get("operator_language", "en"))), e(s["id"])))
            o.append('<div class="tablet"><p><b>%s</b></p>%s</div>' % (V(s.get("question")), task_body(e, V, script, s)))
            tn = taught_on.get(s["id"])
            o.append('<dl>%s<dt>%s</dt><dd>%s</dd><dt>%s</dt><dd>%s</dd>%s</dl></div>' % (
                ("<dt>%s</dt><dd>%s</dd>" % (e(T(script, "s_correct")), e(s.get("correct", "")))) if uses(s, "options") else "",
                e(T(script, "s_feedback")), V(s.get("feedback")),
                e(T(script, "s_mechanic")), e(mech_label(mech(s), script.get("operator_language", "en"))),
                "" if st["kind"] == "final" else "<dt>%s</dt><dd>%s</dd>" % (
                    e(T(script, "s_taught_on")),
                    e(", ".join(T(script, "s_slide_n", n=n) for n in tn)) if tn else "<b>%s</b>" % e(T(script, "s_taught_nowhere")))))
        o.append('<div class="result"><b>%s</b> %s</div>' % (
            e(T(script, "s_result", q=len(st["questions"]))),
            e(T(script, "s_result_graded" if st["kind"] == "final" else "s_result_own"))))
    o.append('<p class="foot">%s %s %s</p></div></body></html>' % (e(T(script, "s_prepared")), date.today().isoformat(), e(T(script, "s_by_factory"))))
    return "\n".join(o)


# ------------------------------------------------------------------ the Word file
def _run(text, lang=None, bold=False, color=None):
    rpr = ""
    if bold or lang or color:
        rpr = "<w:rPr>%s%s%s</w:rPr>" % ("<w:b/>" if bold else "", '<w:color w:val="%s"/>' % color if color else "",
                                         '<w:lang w:val="%s"/>' % lang if lang else "")
    return '<w:r>%s<w:t xml:space="preserve">%s</w:t></w:r>' % (rpr, html.escape(text, quote=False))


def _para(text, style=None, lang=None, bold=False, shade=None, color=None):
    ppr = ""
    if style or shade:
        ppr = "<w:pPr>%s%s</w:pPr>" % ('<w:pStyle w:val="%s"/>' % style if style else "",
                                       '<w:shd w:val="clear" w:color="auto" w:fill="%s"/>' % shade if shade else "")
    return "<w:p>%s%s</w:p>" % (ppr, _run(text, lang, bold, color) if text else "")


def _box(tag, alias, text, lang):
    paras = "".join(_para(line, lang=lang, shade="EEF2F6") for line in (str(text).split("\n") if text != "" else [""]))
    return ('<w:sdt><w:sdtPr><w:alias w:val="%s"/><w:tag w:val="%s"/><w:lock w:val="sdtLocked"/></w:sdtPr>'
            '<w:sdtContent>%s</w:sdtContent></w:sdt>' % (html.escape(alias), html.escape(tag), paras))


def docx_labels(course, script):
    """The fixed text of the Word file - headings and field names. Rebuilt from the script, never
    trusted from the file, because Word may drop parts of a package it does not know when it saves."""
    return build_docx(course, script)[1]


def render_docx(course, script, out):
    doc, _ = build_docx(course, script)
    write_docx_package(doc, out)


def build_docx(course, script):
    cl = course_lang(script)
    body, labels = [], []

    def label(text, style=None, bold=False, color=None):
        labels.append(text)
        body.append(_para(text, style=style, bold=bold, color=color))

    label(T(script, "s_page_title", m=script.get("module")), style="Title")
    labels.append(script.get("title", ""))
    body.append(_para(script.get("title", ""), lang=cl, bold=True))
    label(T(script, "s_docx_help"), color="41556A")
    lang = script.get("operator_language", "en")
    label("%s %s" % (T(script, "s_docx_kinds"), "; ".join(kind_label(k, lang) for k in VISUAL_KINDS)), color="41556A")
    facts = operator_facts(course, script)
    if facts:
        label(T(script, "s_facts_title"), style="Heading1")
        for f in facts:
            body.append(_para("• " + f.get("fact", ""), lang=cl))
    th_found, taught_on = theory_findings(script)
    for head, found in (("s_theory_title", th_found), ("s_media_title", media_findings(script)),
                        ("s_textcheck_title", text_findings(script))):
        if found:
            label(T(script, head), style="Heading1")
            for f in found:
                label("%s%s — %s%s (%s)" % (
                    f["where"], (" · " + f["field"]) if f["field"] else "", f["detail"],
                    (" %s: %s" % (T(script, "s_textcheck_instead"), f["fix"])) if f["fix"] else "",
                    T(script, "s_textcheck_must") if f["level"] == FAIL else T(script, "s_textcheck_note")), color="B4453A")
    names = {"title": "s_title", "text": "s_text", "visual": "s_visual", "notes": "s_notes", "minutes": "s_minutes",
             "question": "s_question", "correct": "s_correct", "feedback": "s_feedback", "mechanic": "s_mechanic",
             "visual_kind": "s_visual_kind", "answer": "s_answer"}
    slide_no, sets, set_of = plan_of(script)

    def boxes(s):
        for f, v in fields_of(s, lang):
            nm = T(script, "s_options") + " " + f[4] if f.startswith("opt.") else T(script, names[f])
            if s["kind"] == "task-slide" and f == "minutes":
                nm = T(script, "s_minutes_task")
            label(nm, bold=True, color="0A2463")
            body.append(_box("%s.%s" % (s["id"], f), "%s · %s" % (s["id"], nm), v, cl))

    label(T(script, "s_part1"), style="Title")
    label(T(script, "s_part1_intro"), color="41556A")
    for s in script.get("screens", []):
        if s["kind"] not in INSTRUCTOR:
            continue
        label("%s · %s · %s" % (T(script, "s_slide_n", n=slide_no[s["id"]]),
                                T(script, {"slide": "s_slide", "task-slide": "s_task_slide", "activity": "s_activity"}[s["kind"]]), s["id"]),
              style="Heading1")
        if s["kind"] == "task-slide":
            st = set_of.get(s.get("opens"))
            label("%s — %s" % (T(script, "s_open_task"), T(script, "s_opens", set=set_name(script, st) if st else "?",
                                                           q=len(st["questions"]) if st else 0)), color="41556A")
        boxes(s)
    label(T(script, "s_part2"), style="Title")
    label(T(script, "s_part2_intro"), color="41556A")
    for st in sets:
        label(set_name(script, st), style="Heading1")
        label(T(script, "s_set_intro", slide=slide_no.get(st["opened_by"], "?"), q=len(st["questions"])), color="41556A")
        for qn, s in enumerate(st["questions"], 1):
            label("%s · %s · %s" % (T(script, "s_question_n", q=qn, of=len(st["questions"])), mech_label(mech(s), lang), s["id"]), bold=True)
            if uses(s, "answer"):
                label("%s %s" % (T(script, "s_answer_how"), T(script, "fmt_" + mech(s))), color="41556A")
            if st["kind"] != "final":
                tn = taught_on.get(s["id"])
                label("%s: %s" % (T(script, "s_taught_on"), ", ".join(T(script, "s_slide_n", n=n) for n in tn) if tn
                                  else T(script, "s_taught_nowhere")), color="41556A")
            boxes(s)
    doc = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document xmlns:w="%s"><w:body>%s'
           '<w:sectPr><w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="1134" w:right="1134" w:bottom="1134" w:left="1134" w:header="708" w:footer="708" w:gutter="0"/></w:sectPr>'
           '</w:body></w:document>' % (W, "".join(body)))
    return doc, labels


def write_docx_package(doc, out):
    styles = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:styles xmlns:w="%s">'
              '<w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="Calibri" w:hAnsi="Calibri" w:cs="Calibri"/><w:sz w:val="22"/></w:rPr></w:rPrDefault></w:docDefaults>'
              '<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/><w:pPr><w:spacing w:after="80"/></w:pPr></w:style>'
              '<w:style w:type="paragraph" w:styleId="Title"><w:name w:val="Title"/><w:basedOn w:val="Normal"/><w:rPr><w:b/><w:color w:val="0A2463"/><w:sz w:val="36"/></w:rPr></w:style>'
              '<w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:basedOn w:val="Normal"/><w:pPr><w:keepNext/><w:spacing w:before="360" w:after="120"/><w:outlineLvl w:val="0"/></w:pPr><w:rPr><w:b/><w:color w:val="0A2463"/><w:sz w:val="28"/></w:rPr></w:style>'
              '</w:styles>' % W)
    ct = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/>'
          '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
          '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/></Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
    drels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
             '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", ct)
        z.writestr("_rels/.rels", rels)
        z.writestr("word/document.xml", doc)
        z.writestr("word/styles.xml", styles)
        z.writestr("word/_rels/document.xml.rels", drels)


def _text(el):
    """Text of an element as it stands with every tracked change accepted."""
    parts = []

    def walk(x, deleted=False):
        tag = x.tag
        if tag in (Q("del"), Q("moveFrom")):
            deleted = True
        if not deleted:
            if tag == Q("t"):
                parts.append(x.text or "")
            elif tag == Q("tab"):
                parts.append("\t")
            elif tag in (Q("br"), Q("cr")):
                parts.append("\n")
        for c in x:
            walk(c, deleted)
    walk(el)
    return "".join(parts)


def read_docx(path, known_labels=()):
    """Fields, comments, tracked changes, text outside the boxes - from the operator's Word file."""
    with zipfile.ZipFile(path) as z:
        doc = ET.fromstring(z.read("word/document.xml"))
        comments = {}
        if "word/comments.xml" in z.namelist():
            for c in ET.fromstring(z.read("word/comments.xml")).iter(Q("comment")):
                comments[c.get(Q("id"))] = {"author": c.get(Q("author"), ""),
                                            "text": "\n".join(_text(p) for p in c.iter(Q("p"))).strip()}
    fields, tracked, placed, outside = {}, [], {}, []
    labels = set(l.strip() for l in known_labels)
    state = {"last": None}
    pending_comments = []

    def walk(x, in_tag=None):
        if x.tag == Q("sdt"):
            tag_el = x.find("%s/%s" % (Q("sdtPr"), Q("tag")))
            tag = tag_el.get(Q("val")) if tag_el is not None else None
            content = x.find(Q("sdtContent"))
            if tag and content is not None:
                paras = [p for p in content.iter(Q("p"))] or [content]
                fields[tag] = "\n".join(_text(p) for p in paras)
                for kind in ("ins", "del", "moveTo", "moveFrom"):
                    for ch in content.iter(Q(kind)):
                        tracked.append({"field": tag, "type": {"ins": "inserted", "del": "deleted", "moveTo": "moved", "moveFrom": "moved"}[kind],
                                        "author": ch.get(Q("author"), "")})
                for cid in pending_comments:
                    placed[cid] = tag
                pending_comments.clear()
                state["last"] = tag
                for c in content.iter(Q("commentRangeStart")):
                    placed[c.get(Q("id"))] = tag
                return
        if x.tag == Q("commentRangeStart"):
            pending_comments.append(x.get(Q("id")))
        if x.tag == Q("p") and in_tag is None:
            t = _text(x).strip()
            if t and t not in labels and not t.startswith("• "):
                outside.append({"after": state["last"], "text": t})
        for c in x:
            walk(c, in_tag)
    walk(doc.find(Q("body")))
    for cid in pending_comments:            # a comment after the last box belongs to it
        placed[cid] = state["last"]
    out_comments = [{"field": placed.get(cid), **c} for cid, c in comments.items()]
    return {"fields": fields, "comments": out_comments, "tracked": tracked, "outside": outside}


def read_pdf(path):
    try:
        import pypdf  # noqa: F401
    except ImportError:
        return None
    import pypdf
    found = []
    r = pypdf.PdfReader(path)
    for n, page in enumerate(r.pages, 1):
        ids = sorted(set(re.findall(r"\b([smqftca]\d{2,3})\b", page.extract_text() or "")))
        for a in (page.get("/Annots") or []):
            a = a.get_object()
            txt = a.get("/Contents")
            if txt:
                found.append({"page": n, "text": str(txt), "author": str(a.get("/T", "")), "screens_on_page": ids})
    return found


# ------------------------------------------------------------------ pending changes
def screen_of(script, sid):
    for s in script.get("screens", []):
        if s["id"] == sid:
            return s
    return None


def short(s, n=90):
    s = (s or "").replace("\n", " / ")
    return s if len(s) <= n else s[:n - 1] + "…"


def changed_words(old, new):
    """Only the words that changed: "rely on the hull for strength" -> "are thin barriers supported by the hull"."""
    a, b = (old or "").split(), (new or "").split()
    parts = []
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b).get_opcodes():
        if op == "replace":
            parts.append("\"%s\" becomes \"%s\"" % (" ".join(a[i1:i2]), " ".join(b[j1:j2])))
        elif op == "delete":
            parts.append("\"%s\" is removed" % " ".join(a[i1:i2]))
        elif op == "insert":
            parts.append("\"%s\" is added%s" % (" ".join(b[j1:j2]), (" after \"%s\"" % " ".join(a[max(0, i1 - 3):i1])) if i1 else " at the start"))
    return "; ".join(parts) or "only line breaks or spacing change"


def describe(script, ch):
    s = screen_of(script, ch["screen"])
    where = "%s (%s)" % (place(script, ch["screen"]), ch["screen"]) if s else ch["screen"]
    f = ch["field"]
    if f == "correct":
        return "%s: the correct answer becomes %s (was %s)" % (where, ch["new"], ch["old"])
    if f.startswith("opt."):
        return "%s: answer %s becomes \"%s\" (was \"%s\")" % (where, f[4], short(ch["new"]), short(ch["old"]))
    name = {"title": "the title", "text": "the slide text", "visual": "the planned picture", "notes": "the instructor notes",
            "minutes": "the minutes", "question": "the question", "feedback": "the feedback", "mechanic": "how the trainee answers",
            "visual_kind": "the kind of picture", "answer": "the answer"}.get(f, f)
    if len(ch["old"] or "") > 60 or len(ch["new"] or "") > 60:
        return "%s, %s: %s" % (where, name, changed_words(ch["old"], ch["new"]))
    return "%s: %s becomes \"%s\" (was \"%s\")" % (where, name, ch["new"], ch["old"])


def write_pending(p, script, changes, notes, source):
    if not changes and not notes:
        if os.path.isfile(p["pending"]):
            os.remove(p["pending"])
        print("What I understood: nothing - the file says exactly what the script says. Nothing is waiting.")
        return 0
    pend = {"_what": "Understood, NOT applied. Show the list to the operator; apply only after they confirm.",
            "source": source, "made": datetime.now().isoformat(timespec="seconds"), "base_hash": content_hash(script),
            "changes": changes, "notes": notes}
    save(p["pending"], pend)
    print("What I understood - nothing has been changed yet:\n")
    for ch in changes:
        print("  - " + describe(script, ch))
    for nt in notes:
        print("  - " + nt)
    print("\nShow this list to the operator. Only when they confirm:  content_script.py apply <course> --module %s --confirmed"
          % script.get("module"))
    return 0


def cmd_read(course, module, docx, pdf):
    p = paths(course, module)
    script = load(p["script"])
    changes, notes = [], []
    p["docx"] = docx or workspace.review_path(course, os.path.basename(p["docx"]), for_reading=True)
    if os.path.isfile(p["docx"]):
        got = read_docx(p["docx"], docx_labels(course, script))
        expected = {}
        for s in script["screens"]:
            for f, v in fields_of(s, script.get("operator_language", "en")):
                expected["%s.%s" % (s["id"], f)] = str(v)
        for tag, old in expected.items():
            if tag not in got["fields"]:
                notes.append("the box for %s was deleted in Word - I cannot tell what was meant; ask the operator" % tag)
                continue
            new = got["fields"][tag]
            if new.strip() != old.strip():
                sid, f = tag.split(".", 1)
                changes.append({"screen": sid, "field": f, "old": old, "new": new.strip()})
        by_field = {}
        for t in got["tracked"]:
            by_field.setdefault(t["field"], set()).add("%s by %s" % (t["type"], t["author"] or "someone"))
        for f, how in sorted(by_field.items()):
            notes.append("tracked changes in %s (%s) - read as if accepted" % (f, ", ".join(sorted(how))))
        for c in got["comments"]:
            where = c["field"] or "a place I could not match to a screen"
            notes.append("comment on %s from %s: \"%s\" - I will say what I would change for it, and do it only when you confirm"
                         % (where, c["author"] or "the operator", short(c["text"], 200)))
        for x in got["outside"]:
            notes.append("text typed outside the boxes (after %s): \"%s\" - I will not guess where it belongs; tell me" % (x["after"] or "the start", short(x["text"], 160)))
        made = script.get("docx_hash")
        if made and made != content_hash(script):
            notes.append("this Word file was made from an older version of the script - the list compares it with the current one")
    if pdf:
        found = read_pdf(pdf)
        if found is None:
            notes.append("PDF comments cannot be read on this computer (the pypdf package is missing) - please give them in the Word file or in the chat")
        else:
            for a in found:
                notes.append("PDF comment on page %d (screens on that page: %s) from %s: \"%s\"" % (
                    a["page"], ", ".join(a["screens_on_page"]) or "not found", a["author"] or "the operator", short(a["text"], 200)))
    return write_pending(p, script, changes, notes, "word" if os.path.isfile(p["docx"]) else "pdf")


def cmd_propose(course, module, changes_file):
    p = paths(course, module)
    script = load(p["script"])
    changes = []
    for c in load(changes_file):
        sid, f = c["field"].split(".", 1) if "." in c["field"] and not c["field"].startswith("opt.") else (c.get("screen"), c["field"])
        s = screen_of(script, sid)
        if s is None:
            print("Stopped - there is no screen %r in this module's script." % sid)
            return 2
        changes.append({"screen": sid, "field": f, "old": get_field(s, f, script.get("operator_language", "en")) or "", "new": c["new"]})
    return write_pending(p, script, changes, [], "chat")


def append_feedback(course, script, changes, source):
    fb = workspace.claude_path(course, "FEEDBACK_LOG.md")
    if not os.path.isfile(fb):
        return
    text = io.open(fb, encoding="utf-8").read()
    nums = [int(c.split("|")[1]) for c in text.splitlines() if re.match(r"^\|\s*\d+\s*\|", c)]
    n = max(nums or [0])
    rows = []
    for ch in changes:
        n += 1
        rows.append("| %d | %s | 3 · %s · %s | %s (%s) | %s | no |" % (
            n, date.today().isoformat(), mid(script["module"]), ch["screen"], short(ch["new"], 120).replace("|", "/"), source,
            describe(script, ch).replace("|", "/")))
    with io.open(fb, "a", encoding="utf-8", newline="\n") as f:
        f.write(("\n" if not text.endswith("\n") else "") + "\n".join(rows) + "\n")


def archive_name(folder, stem, ext):
    """A name in the archive folder that is not taken. A timestamp alone is not enough: two corrections
    applied in the same second gave the same name, the rename failed, and the pending list stayed behind
    and blocked the approval (found by the 2.16.1 test, one run in five)."""
    base = "%s_%s" % (stem, datetime.now().strftime("%Y%m%d_%H%M%S"))
    path, n = os.path.join(folder, base + ext), 2
    while os.path.exists(path):
        path, n = os.path.join(folder, "%s_%d%s" % (base, n, ext)), n + 1
    return path


def cmd_apply(course, module, confirmed):
    p = paths(course, module)
    if not confirmed:
        print("Stopped - apply needs --confirmed, and that is only given after the operator has read the list and said yes.")
        return 2
    if not os.path.isfile(p["pending"]):
        print("Nothing to apply - there is no list of understood changes waiting.")
        return 2
    script, pend = load(p["script"]), load(p["pending"])
    if pend["base_hash"] != content_hash(script):
        print("Stopped - the script changed after the list was made. Read the corrections again, and show the new list.")
        return 1
    for ch in pend["changes"]:
        set_field(screen_of(script, ch["screen"]), ch["field"], ch["new"])
    was_approved = script.get("status") == "approved"
    if pend["changes"]:
        script["status"] = "draft"
    save(p["script"], script)
    append_feedback(course, script, pend["changes"], {"word": "Word file", "pdf": "PDF", "chat": "chat"}.get(pend["source"], pend["source"]))
    os.makedirs(p["old"], exist_ok=True)
    if os.path.isfile(p["docx"]):
        shutil.move(p["docx"], archive_name(p["old"], "%s_SCRIPT" % mid(module), ".docx"))
    os.replace(p["pending"], archive_name(p["old"], "%s.applied" % mid(module), ".json"))
    render(course, module, quiet=True)
    print("Applied %d change(s), logged in FEEDBACK_LOG.md, and made a fresh review page and Word file.%s%s"
          % (len(pend["changes"]), " The module is back to draft: it needs the operator's \"next\" again." if was_approved and pend["changes"] else "",
             ("\n  %d comment(s) and note(s) were NOT applied - they are instructions, not edits. Propose the change for "
              "each (content_script.py propose), show it, and apply it when the operator confirms." % len(pend["notes"])) if pend["notes"] else ""))
    return 0


def cmd_discard(course, module):
    p = paths(course, module)
    if not os.path.isfile(p["pending"]):
        print("Nothing is waiting - there is nothing to discard.")
        return 0
    os.makedirs(p["old"], exist_ok=True)
    os.replace(p["pending"], archive_name(p["old"], "%s.discarded" % mid(module), ".json"))
    print("Discarded - the list of understood changes was not applied. The script is unchanged.")
    return 0


def cmd_approve(course, module, by, despite=False):
    p = paths(course, module)
    script = load(p["script"])
    if os.path.isfile(p["pending"]):
        print("Not approved - there are understood changes waiting. Apply them (after the operator confirms) or discard them first.")
        return 1
    probs = validate(script)
    if probs:
        print("Not approved - the script still has problems:\n" + "\n".join("  - " + x for x in probs))
        return 1
    must = blocking(all_findings(script))
    if must and not despite:
        print("Not approved - the checks found %d thing(s) that must be fixed first:\n%s\n\n"
              "  Fix them in the script (propose, confirm, apply) - or, if the operator has read them and wants the\n"
              "  script as it is (L26), approve with --despite-findings; that decision is recorded with the approval."
              % (len(must), "\n".join("  - %s%s: %s" % (f["where"], (", " + f["field"]) if f["field"] else "", f["detail"]) for f in must)))
        return 1
    script["approved_despite_findings"] = [dict(f, date=date.today().isoformat()) for f in must] if must else []
    script.update({"status": "approved", "approved_by": by, "approved_on": date.today().isoformat(), "approved_hash": content_hash(script)})
    save(p["script"], script)
    render(course, module, quiet=True)
    print("Module %s's script is approved by %s. The slides built from it must say exactly this (check_script_match.py)." % (script["module"], by))
    return 0


def cmd_status(course, module):
    p = paths(course, module)
    script = load(p["script"])
    ok = script.get("status") == "approved" and script.get("approved_hash") == content_hash(script)
    print("Module %s: %s%s" % (script.get("module"), "approved by %s on %s" % (script.get("approved_by"), script.get("approved_on")) if ok else "draft - not approved",
                               "; understood changes are waiting for confirmation" if os.path.isfile(p["pending"]) else ""))
    return 0 if ok else 1


def note_lines(text):
    """Instructor notes as short points, one per line - '- ' added where the line has none."""
    out = []
    for x in (text or "").split("\n"):
        x = x.strip()
        if x:
            out.append(x if x.startswith(("- ", "* ")) else "- " + x)
    return out


def instructor_notes_md(script):
    """The module's instructor notes as the instructor's panel shows them (owner, 2026-09-30, 2.18.1): compact
    points per slide, the OPEN TASK prompt at every task - in the course language, and never on a slide.
    Made from the content script, so the approved script stays the one source."""
    slide_no, sets, set_of = plan_of(script)
    ok = script.get("status") == "approved" and script.get("approved_hash") == content_hash(script)
    total = sum(minutes(s) for s in script.get("screens", []) if s.get("kind") in INSTRUCTOR)
    o = ["# Module %s · %s — instructor notes" % (script.get("module"), script.get("title", "")), "",
         "<!-- Made from the content script (working_claude/script/%s.json) by content_script.py. It is shown on the "
         "instructor's panel, never on a slide. Corrections go through the review Word file or the chat, not "
         "this file. -->" % mid(script.get("module")), "",
         "%s · %g min" % ("Approved by %s on %s" % (script.get("approved_by"), script.get("approved_on")) if ok else "Draft - not yet approved", total), ""]
    for s in script.get("screens", []):
        k = s.get("kind")
        if k not in INSTRUCTOR:
            continue
        o.append("## Slide %d · %s · %g min" % (slide_no[s["id"]], s.get("title", ""), minutes(s)))
        if k == "task-slide":
            st = set_of.get(s.get("opens"))
            if st:
                o.append("**OPEN TASK** → %s, %d question%s, on every trainee tablet." % (
                    {"self-check": "Self-check %s" % st.get("no", ""), "module-check": "Module check",
                     "final": "Final assessment"}[st["kind"]], len(st["questions"]), "" if len(st["questions"]) == 1 else "s"))
        o += note_lines(s.get("notes"))
        o.append("")
    return "\n".join(o).rstrip() + "\n"


def render(course, module, quiet=False):
    p = paths(course, module)
    script = load(p["script"])
    probs = validate(script)
    os.makedirs(p["rdir"], exist_ok=True)
    io.open(p["review"], "w", encoding="utf-8", newline="\n").write(render_html(course, script))
    render_docx(course, script, p["docx"])
    os.makedirs(os.path.dirname(p["notes_md"]), exist_ok=True)
    io.open(p["notes_md"], "w", encoding="utf-8", newline="\n").write(instructor_notes_md(script))
    script["docx_hash"] = content_hash(script)
    save(p["script"], script)
    if not quiet:
        print("Ready for the operator:\n    %s   (opens in the browser, prints to PDF)\n    %s   (Word - correct it here)"
              "\n    %s   (the instructor's panel - short notes per slide, never on a slide)"
              % (p["review"], p["docx"], p["notes_md"]))
        if probs:
            print("\nThe script still has problems - fix them before showing it:\n" + "\n".join("  - " + x for x in probs))
        th, _ = theory_findings(script)
        for head, found in (("The theory check", th), ("The pictures-and-tasks check", media_findings(script)),
                            ("The text check", text_findings(script))):
            if found:
                print("\n%s found %d thing(s) - they are at the top of the review page and the Word file:" % (head, len(found)))
                for f in found:
                    print("  - [%s] %s%s: %s%s" % ("must fix" if f["level"] == FAIL else "note", f["where"],
                                                  (", " + f["field"]) if f["field"] else "", f["detail"],
                                                  (" - use instead: " + f["fix"]) if f["fix"] else ""))
    return 1 if probs else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("render", "read", "propose", "apply", "discard", "approve", "status"):
        s = sub.add_parser(name)
        s.add_argument("course")
        s.add_argument("--module", required=True)
        if name == "read":
            s.add_argument("--docx"); s.add_argument("--pdf")
        if name == "propose":
            s.add_argument("--changes", required=True)
        if name == "apply":
            s.add_argument("--confirmed", action="store_true")
        if name == "approve":
            s.add_argument("--by", required=True)
            s.add_argument("--despite-findings", action="store_true",
                           help="the operator read the findings and wants the script as it is")
    a = ap.parse_args(argv)
    a.course = workspace.work_folder(a.course)
    if not os.path.isfile(paths(a.course, a.module)["script"]):
        print("Stopped - there is no content script for module %s yet:\n    %s" % (a.module, paths(a.course, a.module)["script"]))
        return 2
    return {"render": lambda: render(a.course, a.module), "read": lambda: cmd_read(a.course, a.module, a.docx, a.pdf),
            "propose": lambda: cmd_propose(a.course, a.module, a.changes), "apply": lambda: cmd_apply(a.course, a.module, a.confirmed),
            "discard": lambda: cmd_discard(a.course, a.module),
            "approve": lambda: cmd_approve(a.course, a.module, a.by, a.despite_findings), "status": lambda: cmd_status(a.course, a.module)}[a.cmd]()


if __name__ == "__main__":
    sys.exit(main())
