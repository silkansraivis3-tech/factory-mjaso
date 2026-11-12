#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Day sheets - what is done on each day of an instructor-led course, in order - and the course on one page.

    day_sheets.py <course folder> --out <folder>             a preview: the day sheets and the one-page overview as HTML in
                                                             <folder>; nothing in the course is written
    day_sheets.py <course folder> --out <folder> --no-data   the same from the scripts alone (day_sheets.json not read)

The course build writes them (additional_materials.py plan() calls files() below) into
course\\additional-materials\\day-sheets\\ - HTML, PDF and Word, linked from INDEX.html.

WHAT A DAY SHEET IS (course lead Aigars Kluga, Project Management, 2026-11-10 and 2026-11-12)
  the title and an intro; "Today, in this order" - What is done | Where - with NO clock times and NO break or lunch rows
  (the real times always differ); then each task of the day with its requirements; the day's extra sections (consistency
  checks, a rubric ...); "Before you leave" (the AI log, the daily sign-off ...).

WHERE EVERY WORD COMES FROM - nothing is typed here
  which screen falls on which day    course.build.json "days" - the Advanced Course Plan's own split
                                     (additional_materials.days_of); the final's activities fall on the last day
  the rows, in the class's order     the approved content scripts: a run of teaching slides and self-checks = one
                                     "Theory" row (its passive slides' titles, its class exercises and self-checks counted);
                                     each activity = one row; a module check = one row; a team task = one row; the course's
                                     opening slides without a Sub-ILO = "Course start"; a project block's briefing slides
                                     (no Sub-ILO, just before an activity) and recap slides make no row
  the tasks and their requirements   day_sheets.json "tasks" - each placed on the day of the activity whose words name
                                     "Task N" (or its "at": "M03.a01"); with no "tasks", each activity of the day is a
                                     task and its own lines - the words the trainee sees on the screen - its requirements
  titles, intros, Before you leave,  day_sheets.json (instructor-led/GUIDE.md section 4) - else the day's module titles,
  extra sections, the one-page words no intro, and no Before you leave
  the hours on the one-page table    the scripts' minutes: slides and task slides = lecture, activities = practical

Exit 0 written; 1 written, with problems to fix; 2 nothing written.
"""
from __future__ import annotations

import argparse
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "..", "scripts"))
import additional_materials as am  # noqa: E402
import compile_module as cm  # noqa: E402
import content_script as cs  # noqa: E402
import instructor_led as il  # noqa: E402
import workspace  # noqa: E402

NAME = "day_sheets.json"
FOLDER = "day-sheets"
TASK_REF = re.compile(r"\bTasks?\s+(\d+)((?:\s*(?:,|and|&)\s*\d+)*)", re.I)
TITLES_SHOWN = 6                    # a theory row names at most this many slides, then "and N more"
W = {
    "sheet": "Day {n} - {title}", "today": "Today, in this order", "cols": ["What is done", "Where"],
    "tasks": "Tasks", "leave": "Before you leave", "continued": "{t} (continued)", "final_t": "Final assessment",
    "theory": "Theory: {what}", "theory_of": "Theory, {topic}: {what}", "more": "and {n} more",
    "with": "with {x}", "exercise": ["one class exercise", "{n} class exercises"],
    "self_check": ["one self-check", "{n} self-checks"], "about_h": "about {h} academic hours",
    "start": "Course start: {what}", "check": "Module check on the tablet", "check_practice": "practice, not graded",
    "check_graded": "graded", "team": "Team task on the tablets: {t}", "final": "Final assessment on the tablet",
    "task": "Task {n}", "where": {"instructor": "Instructor", "tablet": "Tablet", "room": "Classroom",
                                  "simulator": "Simulator", "equipment": "Real equipment"},
    # the one-page overview
    "one": "{course} - the {n} days on one page", "one_sub": "{h} academic hours over {n} days.",
    "order": "The order of the work", "by_day": "Day by day",
    "one_cols": ["Day", "Lecture", "Practical, in this order", "At the end of the day"],
    "day_h": "{n}  {title} - lecture about {l} h, practical about {p} h", "no_lecture": "No lecture.",
    "made": "Made from the approved course files by course-factory {v}. Never edit it by hand: correct the content "
            "script or working_claude\\day_sheets.json and build again.",
}


def path(course):
    return workspace.claude_path(course, NAME)


def load(course):
    d = am.load_or(path(course), {})
    return d if isinstance(d, dict) else {}


def _n(word, n):
    return word[0] if n == 1 else word[1].format(n=n)


def _hours(minutes, hour):
    """academic hours, to the half hour"""
    return "%g" % (round(2.0 * minutes / hour) / 2.0)


def _lines(x):
    return x if isinstance(x, list) else [x] if x else []


# ------------------------------------------------------------------ what falls on which day
def items_by_day(course, mods, days, probs):
    """{day: [{"key", "mid", "s", "kind", "task"}]} - every instructor-device screen in the class's order"""
    by = {d: [] for d in range(1, len(days) + 1)}
    built_final = False
    for m in mods:
        tasks = {id(t["slide"]): t for t in m["tasks"]}
        is_final = str(m["script"].get("module") or "").upper() == "FINAL"     # the final built as a module folder
        built_final = built_final or is_final
        t = 0.0
        for s in m["script"]["screens"]:
            if s.get("kind") not in cs.INSTRUCTOR:
                continue
            d = am.day_of(days, m, t)
            by.setdefault(d, []).append({"key": il.key("FINAL" if is_final else m["mid"], s.get("id")), "mid": m["mid"],
                                         "m": m, "s": s, "start": t, "task": tasks.get(id(s)), "final": is_final})
            t += cs.minutes(s)
    final = {} if built_final else dict(il.scripts(course)).get("FINAL") or {}
    if final and days:
        if not am.approved(final):
            probs.append("FINAL: its content script is not approved - the last day sheet leaves the final out")
        else:
            last = by.setdefault(len(days), [])
            asked = False
            for s in final.get("screens") or []:
                if s.get("kind") in cs.INSTRUCTOR:
                    last.append({"key": il.key("FINAL", s.get("id")), "mid": "FINAL", "m": None, "s": s, "start": 0.0,
                                 "task": None, "final": True})
                    asked = asked or s.get("kind") == "task-slide"
                elif not asked and s.get("kind") not in ("activity",):
                    last.append({"key": il.key("FINAL", s.get("id")), "mid": "FINAL", "m": None, "s": {"kind": "task-slide"},
                                 "start": 0.0, "task": None, "final": True})
                    asked = True
    for row in by.values():
        for x in row:
            x["kind"] = kind_of(x)
    return by


def kind_of(x):
    """act, check, team, final, theory, brief or skip"""
    s = x["s"]
    k = s.get("kind")
    if k == "activity":
        return "act"
    if k == "task-slide":
        if x.get("final"):
            return "final"
        tk = (x.get("task") or {}).get("kind")
        return {"module-check": "check", "team": "team", "final": "final"}.get(tk, "theory")
    if s.get("recap"):
        return "skip"
    return "theory" if cs.sub_ilos_of(s) else "brief"


# ------------------------------------------------------------------ the tasks of day_sheets.json
def task_refs(text):
    out = []
    for a, rest in TASK_REF.findall(text or ""):
        for n in [a] + re.findall(r"\d+", rest):
            if int(n) not in out:
                out.append(int(n))
    return out


def place_tasks(data, by, probs):
    """{day: [task]} and {item key: [task]} - day_sheets.json's tasks on the day of the activity that names them"""
    tasks = [t for t in data.get("tasks") or [] if isinstance(t, dict) and t.get("n") is not None]
    num = {int(t["n"]): t for t in tasks}
    on_item, placed = {}, set()
    for d in sorted(by):
        for x in by[d]:
            if x["kind"] != "act":
                continue
            ns = [n for n in task_refs(" ".join(str(y or "") for y in (x["s"].get("title"), x["s"].get("text"))))
                  if n in num and n not in placed]
            ns += [int(t["n"]) for t in tasks if str(t.get("at") or "").upper() == x["key"] and int(t["n"]) not in ns]
            for n in ns:
                placed.add(n)
                on_item.setdefault(x["key"], []).append(num[n])
    for t in tasks:
        if int(t["n"]) not in placed:
            probs.append("day_sheets.json: task %s is named by no activity's words - give it \"at\": \"M03.a01\"" % t["n"])
    day_tasks = {d: [t for x in by[d] for t in on_item.get(x["key"], [])] for d in by}
    return day_tasks, on_item


def task_name(t):
    return (W["task"].format(n=t["n"]) + (" " + t["name"] if t.get("name") else "")).strip()


# ------------------------------------------------------------------ the rows of "Today, in this order"
def rows_of(items, on_item, data, hour, course_first):
    """[{"what", "where", "kind", "key", "minutes", "titles"}] for one day"""
    over = {str(k).upper(): v for k, v in (data.get("rows") or {}).items()}
    rows, i = [], 0
    while i < len(items):
        x = items[i]
        k = x["kind"]
        if k == "skip":
            i += 1
            continue
        if k == "brief":
            j = i
            while j < len(items) and items[j]["kind"] == "brief":
                j += 1
            nxt = items[j]["kind"] if j < len(items) else None
            if x["key"] == course_first:
                rows.append(row(x["key"], "start", W["start"].format(what="; ".join(y["s"].get("title") or "" for y in items[i:j])),
                                W["where"]["instructor"], sum(cs.minutes(y["s"]) for y in items[i:j]), over))
                i = j
                continue
            if nxt in ("act", None) or nxt == "check":
                i = j                 # a block's briefing: the activity's own row says it
                continue
            k = "theory"              # a slide without a Sub-ILO inside teaching: part of the theory run
        if k == "theory":
            j, run = i, []
            while j < len(items) and items[j]["kind"] in ("theory", "brief") and not (
                    items[j]["kind"] == "brief" and _brief_before_act(items, j)):
                run.append(items[j])
                j += 1
            rows.append(theory_row(run, rows, hour, over))
            i = j
            continue
        s = x["s"]
        if k == "act":
            ts = on_item.get(x["key"]) or []
            what = s.get("title") or x["key"]
            if ts:
                what += " (" + ", ".join(task_name(t) for t in ts) + ")"
            wh = [t.get("where") for t in ts if t.get("where")]
            where = ", ".join(dict.fromkeys(wh)) if wh else W["where"].get((x.get("task") or {}).get("where") or am.classify(
                " ".join(str(y or "") for y in (s.get("title"), s.get("text")))), W["where"]["room"])
            rows.append(row(x["key"], "act", what, where, cs.minutes(s), over, tasks=ts))
        elif k == "check":
            qs = (x.get("task") or {}).get("questions") or []
            tag = W["check_graded"] if any(q.get("graded") for q in qs) else W["check_practice"]
            rows.append(row(x["key"], "check", "%s (%s)" % (W["check"], tag), W["where"]["tablet"], cs.minutes(s), over))
        elif k == "team":
            rows.append(row(x["key"], "team", W["team"].format(t=(x.get("task") or {}).get("title") or s.get("title")),
                            W["where"]["tablet"], cs.minutes(s), over))
        elif k == "final":
            rows.append(row(x["key"], "final", W["final"], W["where"]["tablet"], cs.minutes(s), over))
        i += 1
    return [r for r in rows if not r.get("drop")]


def _brief_before_act(items, j):
    while j < len(items) and items[j]["kind"] == "brief":
        j += 1
    return j >= len(items) or items[j]["kind"] in ("act", "check")


def row(key, kind, what, where, minutes, over, tasks=None, titles=None):
    r = {"key": key, "kind": kind, "what": what, "where": where, "minutes": minutes, "tasks": tasks or [],
         "titles": titles or []}
    if key in over:                   # day_sheets.json "rows": the course lead's own words for this row (or [] to drop it)
        v = over[key]
        r["rows"] = [list(y) + [""] * (2 - len(y)) for y in v if isinstance(y, (list, tuple)) and y]
        r["drop"] = not r["rows"]
    return r


def theory_row(run, rows, hour, over):
    titles = [y["s"].get("title") for y in run
              if y["kind"] == "theory" and y["s"].get("kind") == "slide" and not y["s"].get("active") and y["s"].get("title")]
    ex = sum(1 for y in run if y["s"].get("kind") == "slide" and y["s"].get("active"))
    sc = sum(1 for y in run if y["s"].get("kind") == "task-slide")
    mins = sum(cs.minutes(y["s"]) for y in run)
    what = "; ".join(titles[:TITLES_SHOWN]) + (("; " + W["more"].format(n=len(titles) - TITLES_SHOWN))
                                               if len(titles) > TITLES_SHOWN else "")
    extra = [x for x in (_n(W["exercise"], ex) if ex else "", _n(W["self_check"], sc) if sc else "") if x]
    if extra:
        what += (" - " if what else "") + W["with"].format(x=" and ".join(extra))
    if mins >= hour:
        what += " (%s)" % W["about_h"].format(h=_hours(mins, hour))
    m = run[0].get("m")
    seen = any(r["kind"] == "theory" and r.get("mid") == run[0]["mid"] for r in rows)
    topic = ((m or {}).get("script") or {}).get("title") or (m or {}).get("title")
    text = W["theory_of"].format(topic=topic, what=what) if topic and not seen else W["theory"].format(what=what)
    r = row(run[0]["key"], "theory", text, W["where"]["instructor"], mins, over, titles=titles)
    r["mid"] = run[0]["mid"]
    return r


def table_rows(rows):
    out = []
    for r in rows:
        out += [y[:2] for y in r["rows"]] if r.get("rows") else [[r["what"], r["where"]]]
    return out


# ------------------------------------------------------------------ one day sheet
def day_title(d, row_, data, final_today):
    info = (data.get("days") or {}).get(str(d)) or {}
    if info.get("title"):
        return info["title"]
    names = []
    for m, take, k, of, at in row_:
        t = (m["script"].get("title") or m["title"])
        names.append(W["continued"].format(t=t) if k > 1 else t)
    if final_today:
        names.append(W["final_t"])
    return " / ".join(names)


def resolve(lines, data):
    """day_sheets.json lines: "@name" is the course's "lines" entry of that name"""
    named = data.get("lines") or {}
    out = []
    for x in _lines(lines):
        if isinstance(x, str) and x.startswith("@"):
            out += _lines(named.get(x[1:]) or [])
        else:
            out.append(x)
    return out


def section_blocks(names, data, probs):
    out = []
    secs = data.get("sections") or {}
    for nm in _lines(names):
        sec = secs.get(nm)
        if not isinstance(sec, list):
            probs.append("day_sheets.json: section \"%s\" is named on a day but not written in \"sections\"" % nm)
            continue
        for b in sec:
            if isinstance(b, list) and b and b[0] in ("h2", "h3", "p", "small", "ul", "ol", "table"):
                out.append(tuple(b))
    return out


def day_sheet(d, title, rows, tasks, acts, data, probs, v):
    info = (data.get("days") or {}).get(str(d)) or {}
    name = (data.get("sheet_name") or W["sheet"]).format(n=d, title=title)
    blocks = [("h1", name)]
    if data.get("subtitle"):
        blocks.append(("p", am.b_(data["subtitle"])))
    if data.get("audience"):
        blocks.append(("small", data["audience"]))
    if info.get("intro"):
        blocks.append(("p", info["intro"]))
    blocks += [("h2", W["today"]), ("table", [W["cols"][0], data.get("where_head") or W["cols"][1]], table_rows(rows), [7200, 2438])]
    if tasks:
        blocks.append(("h2", W["tasks"]))
        for t in tasks:
            blocks += [("h3", t.get("title") or task_name(t))] + ([("ul", resolve(t.get("requirements"), data))]
                                                                   if t.get("requirements") else [])
    elif acts:
        blocks.append(("h2", W["tasks"]))
        for s in acts:
            ls = cs.lines_of(s.get("text"))
            blocks += [("h3", s.get("title") or "")] + ([("ul", ls)] if ls else [])
    blocks += section_blocks(info.get("sections"), data, probs)
    leave = resolve(info["before_leave"] if "before_leave" in info else data.get("before_leave"), data)
    if leave:
        blocks += [("h2", W["leave"]), ("ul", leave)]
    blocks.append(("small", W["made"].format(v=v)))
    return name, blocks


# ------------------------------------------------------------------ the course on one page
def one_page(title, prog, days, per_day, data, probs, v):
    op = data.get("one_page") or {}
    hour = float(prog.get("academic_hour_min") or 45)
    n = len(days)
    tot = (prog.get("total_row") or {}).get("total")
    blocks = [("h1", op.get("title") or W["one"].format(course=title, n=n))]
    sub = op.get("subtitle") or (W["one_sub"].format(h=tot, n=n) if tot else "")
    if sub:
        blocks.append(("p", sub))
    order = op.get("order")
    if not order:
        chain = [task_name(t) for d in sorted(per_day) for t in per_day[d]["tasks"]] or \
                [r["what"] for d in sorted(per_day) for r in per_day[d]["rows"] if r["kind"] == "act"]
        order = "  >  ".join(chain)
    if order:
        blocks += [("h2", W["order"]), ("p", order)]
    if op.get("order_note"):
        blocks.append(("p", op["order_note"]))
    rows = []
    for d in sorted(per_day):
        pd = per_day[d]
        info = (data.get("days") or {}).get(str(d)) or {}
        # every screen of the day counts, also those that make no row (a briefing, a recap): activities and team tasks
        # are the practical, the rest the lecture
        pra = sum(cs.minutes(x["s"]) for x in pd["items"] if x["kind"] in ("act", "team"))
        lec = sum(cs.minutes(x["s"]) for x in pd["items"]) - pra
        titles = [t for r in pd["rows"] if r["kind"] == "theory" for t in r["titles"]]
        cap = 2 * TITLES_SHOWN
        lecture = info.get("lecture") or ("; ".join(titles[:cap]) + (("; " + W["more"].format(n=len(titles) - cap))
                                                                     if len(titles) > cap else "")) or W["no_lecture"]
        practical = info.get("practical") or ". ".join(y[0] for y in table_rows([r for r in pd["rows"] if r["kind"] != "theory"]))
        output = info.get("output") or ", ".join(task_name(t) for t in pd["tasks"]) or \
            ", ".join(r["what"] for r in pd["rows"] if r["kind"] == "act")
        rows.append([W["day_h"].format(n=d, title=pd["title"], l=_hours(lec, hour), p=_hours(pra, hour)), lecture, practical, output])
    blocks += [("h2", W["by_day"]), ("table", op.get("cols") or W["one_cols"], rows, [1700, 2900, 3500, 1538])]
    files = op.get("files") or {}
    if files.get("rows"):
        blocks += [("h2", files.get("title") or "Which file when"), ("table", files.get("head") or ["", "", ""], files["rows"])]
    blocks.append(("small", W["made"].format(v=v)))
    return blocks


# ------------------------------------------------------------------ everything for one course
def documents(course, title, prog, mods, days, probs, data=None):
    """[(file stem, document title, blocks)] - the day sheets, then the course on one page"""
    if not mods or not days:
        return []
    data = load(course) if data is None else data
    hour = float(prog.get("academic_hour_min") or 45)
    by = items_by_day(course, mods, days, probs)
    day_tasks, on_item = place_tasks(data, by, probs)
    first = by.get(1, [{}])[0].get("key") if by.get(1) else None
    v = cm.plugin_version()
    out, per_day = [], {}
    for d in range(1, len(days) + 1):
        items = by.get(d) or []
        rows = rows_of(items, on_item, data, hour, first)
        final_apart = any(x.get("final") for x in items) and not any(
            str(m["script"].get("module") or "").upper() == "FINAL" for m, *_ in days[d - 1])
        title_ = day_title(d, days[d - 1], data, final_apart)
        acts = [x["s"] for x in items if x["kind"] == "act"]
        name, blocks = day_sheet(d, title_, rows, day_tasks.get(d) or [], acts, data, probs, v)
        per_day[d] = {"title": title_, "rows": rows, "tasks": day_tasks.get(d) or [], "items": items}
        out.append(("Day_%d_%s" % (d, cm.slug(title_)), name, blocks))
    op = one_page(title, prog, days, per_day, data, probs, v)
    out.append(("Course_on_one_page", op[0][1], op))
    return out


def files(course, title, prog, mods, days, root, probs):
    """for additional_materials.plan(): [(path, kind, payload)] - each document as HTML, PDF and Word"""
    out = []
    for stem, name, blocks in documents(course, title, prog, mods, days, probs):
        base = os.path.join(root, FOLDER, stem)
        out += [(base + ".html", "html", am.to_html(name, blocks)), (base + ".pdf", "pdf", am.to_html(name, blocks)),
                (base + ".docx", "docx", blocks)]
    return out


# ------------------------------------------------------------------ the preview
def course_parts(course, probs):
    """(title, prog, mods, days) as additional_materials.plan() makes them"""
    import compile_course as cc
    arch = am.load_or(workspace.claude_path(course, "architecture.json"), {})
    title = ((arch.get("course") or {}).get("title") or "").strip()
    prog = am.load_or(workspace.claude_path(course, "programme.json"), {})
    sheet = am.load_or(workspace.claude_path(course, "course.build.json"), {})
    plan_j = am.load_or(workspace.claude_path(course, "plan.json"), {})
    root = os.path.join(course, workspace.MODULES)
    names = sorted(d for d in (os.listdir(root) if os.path.isdir(root) else []) if cc.MODULE.match(d)
                   and not os.path.isfile(os.path.join(root, d, cm.DRAFT_MARK)))
    infos = cc.ordered(sheet, [cc.module_info(course, arch, m, probs) for m in names], probs)
    mods = am.modules_of(course, arch, infos, probs)
    for m in mods:
        m["hour"] = float(prog.get("academic_hour_min") or 45)
        m["tasks"] = am.tasks_of(m, sheet)
    final = sum(float(x.get("hours") or 0) for x in plan_j.get("outside_modules") or []) * float(prog.get("academic_hour_min") or 45)
    days = am.days_of(mods, prog, sheet, final, probs) if mods else []
    return title, prog, mods, days


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("course")
    ap.add_argument("--out", required=True, help="the folder the preview HTML is written to")
    ap.add_argument("--no-data", action="store_true", help="from the scripts alone - day_sheets.json is not read")
    o = ap.parse_args(argv)
    course = workspace.work_folder(o.course, create=False)
    probs = []
    title, prog, mods, days = course_parts(course, probs)
    if not title or not mods:
        print("Stopped - no approved architecture with a course title, or no approved module.")
        return 2
    docs = documents(course, title, prog, mods, days, probs, data={} if o.no_data else None)
    os.makedirs(o.out, exist_ok=True)
    for stem, name, blocks in docs:
        p = os.path.join(o.out, stem + ".html")
        am.write(p, am.to_html(name, blocks))
        print("wrote", p)
    if probs:
        print("\nTo fix:")
        for x in probs:
            print("  - " + x)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
