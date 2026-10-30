#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Build the course's own pages - the course start page, the module list and every module's two start pages (L43, L45).

    compile_course.py <course folder>               COURSE.html, _course_shell\\course_map.js, and START_HERE.html +
                                                    START_HERE_EXTENDED.html in every module folder
    compile_course.py <course folder> --module 3    the course files and module 3's start pages only
    compile_course.py <course folder> --force       overwrite a page that was changed by hand

WHY THIS EXISTS
classroom-system.json says the factory writes these files, and until 2.37 no script did: every course got them typed by
hand, a module added later was missing from the list until someone remembered, and a task renamed in the deck kept its
old link on the instructor's quick-access page. They are built from what is already approved and built - nothing in
them is new content:
  the course title          working_claude\\architecture.json "course.title" (the Stage 2 page the operator approved)
  each module's title       its approved content script (working_claude\\script\\M01.json), else architecture.json
  each module's minutes     the script's minutes_allocated
  the hours                 working_claude\\programme.json (total_row.total, academic_hour_min)
  the tasks of a module     its built deck: every task slide's data-activity / data-title / data-task-href
  the instructor's files    what is in the module folder: instructor\\*.html, assessment\\*answer_key*.html, handout\\
  the trainee's handout     handout\\index.html - every slide's title, lines and photographs, from the approved script
                            (handout.py, 2.69.0: the one button on the trainee's tablet)
  how the course is named   working_claude\\course.build.json - delivery, not content (like M01.build.json):
                                {"regulation": "STCW Regulation V/3, Table A-V/3-1",
                                 "programme": "LJA standard programme 13-51-306 v2",
                                 "module_order": [1, 4, 6, 8, 2, 3, 5, 7]}   (2.63.0: the order the classroom shows,
                                 when it is not the folders' - course_map.js and COURSE.html follow it)

THE COURSE ID NEVER CHANGES
The classroom makes the course ID from COURSE.html's <title> when the course is first added. So the title is recorded
at the first build, and a later build with another title stops (also when a hand-made COURSE.html already carries one):
a new title is a new course in the classroom, and its results would be filed apart. --retitle accepts the new title.

course.json is NOT written: in the classroom's folder layout (L45) its importer makes the course descriptor itself, from
COURSE.html and course_map.js. The tablet publisher's course.json is that skill's business (course-tablet-publisher).

THE OUTPUT IS GENERATED - NEVER EDIT IT BY HAND
As compile_module.py: a record of what was written is kept (working_claude\\compiled_course.json for the course files,
working_claude\\modules\\moduleNN\\compiled.json for the start pages); a page changed by hand since - or made by hand
before this tool - is not overwritten without --force.

Exit 0 built; 1 built, but with problems to fix before it is shown; 2 nothing built.
"""
from __future__ import annotations

import argparse
import html
import io
import json
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import compile_module as cm  # noqa: E402
import handout  # noqa: E402
import content_script as cs  # noqa: E402
import ilo_coverage  # noqa: E402
import workspace  # noqa: E402

RECORD = "compiled_course.json"
SHELL_CSS = ("gb_tokens.css", "gb_page.css")          # copied into _course_shell\\ - COURSE.html wears the same look
MODULE = re.compile(r"^module\d{2}$")
SECTION = re.compile(r"<section\b([^>]*\bclass=\"[^\"]*\bslide\b[^>]*)>", re.S)
ATTR = re.compile(r'([\w-]+)="([^"]*)"')
TITLE = re.compile(r"<title[^>]*>([^<]*)</title>", re.I)
e, a = cm.e, cm.a
WORDS = {"en": {
    "start": "Start", "everything": "Everything for this module", "back": "Back", "module": "Module",
    "opening": "Opening the presentation. If nothing happens, press the button.",
    "start_deck": "Start the presentation", "presentation": "Presentation",
    "minutes": "{n} minutes", "min": "{n} min",
    "how": "Open the presentation and press Next to the end - each task opens on the trainee tablets from its own task slide.",
    "tasks": "Trainee tasks", "room": "In the room", "reading": "For the trainee to read", "handout": "Handout",
    "instructor": "Instructor only",
    "foot": "These buttons open the same pages on this device - to look at a task before the class, or after it.",
    "all_files": "All files", "hours": "{h} academic hours ({m} min)", "modules": "{n} modules",
    "later": "Modules {a} to {b} are added as each one is approved.", "later_one": "Module {a} is added when it is approved.",
    "final": "Final assessment", "mc": "Module check",
    "credits": "Picture credits", "credits_note": "Every photograph the course shows, with its author, source and licence. "
                                                  "The same credit is under each photograph when it is opened full screen."},
    # PROVISIONAL (2.40.0) - written by Claude, to be checked by a native speaker: compile/TRANSLATIONS_REVIEW.md.
    # The instructor's pages: the polite form; minutes and hours abbreviated, so no plural depends on the number.
    "lv": {
    "start": "Sākt", "everything": "Viss šim modulim", "back": "Atpakaļ", "module": "Modulis",
    "opening": "Prezentācija tiek atvērta. Ja nekas nenotiek, nospiediet pogu.",
    "start_deck": "Sākt prezentāciju", "presentation": "Prezentācija",
    "minutes": "{n} min", "min": "{n} min",
    "how": "Atveriet prezentāciju un spiediet “Tālāk” līdz beigām – katrs uzdevums atveras kursantu planšetēs no sava uzdevuma slaida.",
    "tasks": "Kursantu uzdevumi", "room": "Telpā", "reading": "Kursantam lasīšanai", "handout": "Izdales materiāls",
    "instructor": "Tikai instruktoram",
    "foot": "Šīs pogas atver tās pašas lapas šajā ierīcē – lai apskatītu uzdevumu pirms nodarbības vai pēc tās.",
    "all_files": "Visi faili", "hours": "{h} akad. st. ({m} min)", "modules": "Moduļi: {n}",
    "later": "Moduļi no {a} līdz {b} tiks pievienoti, kad katrs būs apstiprināts.",
    "later_one": "{a}. modulis tiks pievienots, kad būs apstiprināts.",
    "final": "Noslēguma pārbaudījums", "mc": "Moduļa pārbaude",
    "credits": "Attēlu autori", "credits_note": "Visas kursā rādītās fotogrāfijas ar autoru, avotu un licenci. Tā pati "
                                                "norāde ir zem katras fotogrāfijas, kad to atver pilnekrānā."},
    "ru": {
    "start": "Начать", "everything": "Всё для этого модуля", "back": "Назад", "module": "Модуль",
    "opening": "Презентация открывается. Если ничего не происходит, нажмите кнопку.",
    "start_deck": "Начать презентацию", "presentation": "Презентация",
    "minutes": "{n} мин", "min": "{n} мин",
    "how": "Откройте презентацию и нажимайте «Далее» до конца – каждое задание открывается на планшетах слушателей со своего слайда задания.",
    "tasks": "Задания слушателей", "room": "В аудитории", "reading": "Для чтения слушателю", "handout": "Раздаточный материал",
    "instructor": "Только для инструктора",
    "foot": "Эти кнопки открывают те же страницы на этом устройстве – чтобы посмотреть задание до занятия или после него.",
    "all_files": "Все файлы", "hours": "{h} ак. ч. ({m} мин)", "modules": "Модулей: {n}",
    "later": "Модули с {a} по {b} добавляются по мере утверждения.",
    "later_one": "Модуль {a} будет добавлен после утверждения.",
    "final": "Итоговая аттестация", "mc": "Проверка по модулю",
    "credits": "Авторы изображений", "credits_note": "Все фотографии курса с автором, источником и лицензией. Та же "
                                                     "подпись видна под каждой фотографией, открытой на весь экран."}}
assert all(set(WORDS[k]) == set(WORDS["en"]) for k in WORDS), "every language has every word"


def h(text):
    return html.unescape(text or "").strip()


def read(path):
    with io.open(path, encoding="utf-8") as f:
        return f.read()


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with io.open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def load_or(path, default):
    return cs.load(path) if os.path.isfile(path) else default


def lang_of(arch):
    """the course language's code (L19) - "Latvian" is lv, never "la"; a language the factory does not know keeps its
    first two letters, and main() reports it"""
    lang = ((arch.get("course") or {}).get("course_language") or "English").strip()
    return cm.lang_code(lang) or lang[:2].lower()


# ------------------------------------------------------------------ what a module is
def module_info(course, arch, mod, probs):
    """{n, code, title, minutes, script} for modules\\moduleNN - from its approved script, else the architecture"""
    n = int(mod[-2:])
    planned = {int(x.get("module")): x for x in arch.get("modules") or [] if str(x.get("module", "")).isdigit()}
    sp = cs.paths(course, n)["script"]
    if not os.path.isfile(sp) and n == len(planned) + 1:
        sp = cs.paths(course, "final")["script"]                       # the final assessment is the last module (L34)
    script = load_or(sp, {})
    title = (script.get("title") or (planned.get(n) or {}).get("title") or "").strip()
    if not title and n == len(planned) + 1 and arch.get("final_assessment"):
        title = WORDS.get(lang_of(arch), WORDS["en"])["final"]
    if not title:
        probs.append("%s has no title - neither an approved script (%s) nor a row in architecture.json" % (mod, os.path.basename(sp)))
        title = "Module %d" % n
    elif script and script.get("status") != "approved":
        probs.append("%s: its content script is not approved - the title shown is a draft's" % mod)
    return {"n": n, "code": mod, "title": title, "minutes": script.get("minutes_allocated"), "script": script}


def deck_tasks(deck):
    """[(code, title, href or None, link hint)] - every task slide of the built deck, in the deck's order"""
    out = []
    for m in SECTION.finditer(deck):
        d = dict(ATTR.findall(m.group(1)))
        code = d.get("data-activity")
        if not code:
            continue
        title = h(d.get("data-title"))
        title = title.split(" — ", 1)[1] if " — " in title else title
        href = d.get("data-task-href")
        out.append((code, title, href[3:] if href and href.startswith("../") else href, h(d.get("data-link-hint"))))
    return out


def page_title(path, fallback):
    try:
        m = TITLE.search(read(path))
    except OSError:
        m = None
    return h(m.group(1)) if m and h(m.group(1)) else fallback


def instructor_files(mdir):
    """[(href, label)] - what the module has for the instructor's eyes only, as it is in the folder"""
    out = []
    idir = os.path.join(mdir, "instructor")
    for f in sorted(os.listdir(idir)) if os.path.isdir(idir) else []:
        if f.lower().endswith(".html"):
            out.append(("instructor/" + f, page_title(os.path.join(idir, f), f)))
    for sub in ("assessment", "tasks"):
        d = os.path.join(mdir, sub)
        for f in sorted(os.listdir(d)) if os.path.isdir(d) else []:
            if "answer_key" in f.lower() and f.lower().endswith(".html"):
                out.append(("%s/%s" % (sub, f), page_title(os.path.join(d, f), f)))
    return out


# ------------------------------------------------------------------ the pages
def head(lang, title, css, extra=""):
    return ["<!DOCTYPE html>", '<html lang="%s">' % a(lang), "<head>",
            "<!-- GENERATED by course-factory compile_course.py %s - never edit by hand: change the script, the build sheet "
            "or the module folder, then build again -->" % cm.plugin_version(),
            '<meta charset="utf-8">',
            '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">'] + \
           ([extra] if extra else []) + \
           ["<title>%s</title>" % e(title)] + ['<link rel="stylesheet" href="%s">' % a(c) for c in css] + ["</head>"]


def start_here(info, lang, w):
    m = cs.mid(info["n"])
    return "\n".join(head(lang, "%s — %s" % (m, w["start"]), ["assets/gb_tokens.css", "assets/gb_page.css"],
                          '<meta http-equiv="refresh" content="0; url=presentation/index.html">') + [
        "<body>",
        '<a class="gbt-topback" href="START_HERE_EXTENDED.html"><span class="gbt-ico">◀</span> %s</a>' % e(w["back"]),
        '<div class="wrap">',
        "  <h1>%s %d · %s</h1>" % (e(w["module"]), info["n"], e(info["title"])),
        '  <p class="sub">%s</p>' % e(w["opening"]),
        '  <a class="bigstart" href="presentation/index.html">%s</a>' % e(w["start_deck"]),
        "</div>",
        '<script>try { window.location.replace("presentation/index.html"); } catch (e) {}</script>',
        "</body>", "</html>", ""])


def start_extended(info, course_title, tasks, mdir, lang, w, probs):
    m = cs.mid(info["n"])
    mins = info["minutes"]
    sub = " ".join(x for x in ((w["minutes"].format(n=mins) + ".") if mins else "", w["how"]) if x)
    body = ["<body>",
            # back to the deck, whose own Back opens this page - never ../COURSE.html: a module reaches nothing outside it (L43)
            '<a class="gbt-topback" href="presentation/index.html"><span class="gbt-ico">◀</span> %s</a>' % e(w["back"]),
            '<div class="wrap">',
            "  <h1>%s %d · %s</h1>" % (e(w["module"]), info["n"], e(info["title"])),
            '  <p class="sub">%s</p>' % e(sub),
            '  <div class="meta"><span>%s</span>%s</div>' % (e(course_title), "<span>%s</span>" % e(w["min"].format(n=mins)) if mins else ""),
            "",
            '  <a class="bigstart" href="presentation/index.html">%s</a>' % e(w["presentation"])]
    named = {"MC": w["mc"]}                           # the deck's "MC — Module 3" says which module, not what it is
    codes = [c for c, _, _, _ in tasks]
    named.update({c: cm.final_name(w["final"], c, codes) for c in codes if cm.FINAL_SET.match(c)})   # FA, FB: "Final assessment B"
    links = [(href, "%s · %s" % (code, named.get(code, title))) for code, title, href, _ in tasks if href]
    for href, _ in links:
        if not os.path.isfile(os.path.join(mdir, href)):
            probs.append("%s: the deck opens %s, which is not in the module folder - a task slide announcing a page the "
                         "tablet lacks (build the task pages first: compile_module.py)" % (info["code"], href))
    room = [(code, title, hint) for code, title, href, hint in tasks if not href]

    def block(heading, items):
        if items:
            body.extend(["", "  <h2>%s</h2>" % e(heading), '  <div class="links">'] +
                        ['    <a href="%s">%s</a>' % (a(href), e(label)) for href, label in items] + ["  </div>"])

    block(w["tasks"], links)
    if room:
        body.extend(["", "  <h2>%s</h2>" % e(w["room"])] +
                    ["  <p>%s · %s%s</p>" % (e(c), e(t), (" - " + e(hint)) if hint else "") for c, t, hint in room])
    if os.path.isfile(os.path.join(mdir, "handout", "index.html")):
        block(w["reading"], [("handout/index.html", w["handout"])])
    block(w["instructor"], instructor_files(mdir))
    body += ["", '  <div class="foot"><p>%s</p></div>' % e(w["foot"]), "</div>", "</body>", "</html>", ""]
    return "\n".join(head(lang, "%s — %s" % (m, w["everything"]), ["assets/gb_tokens.css", "assets/gb_page.css"]) + body)


def course_page(title, infos, planned, sheet, prog, lang, w, credits=False):
    hours, ah = (prog.get("total_row") or {}).get("total"), prog.get("academic_hour_min")
    hours_txt = w["hours"].format(h=hours, m=ah) if hours and ah else ""
    named = [x for x in (sheet.get("regulation"), sheet.get("programme")) if x]
    desc = " · ".join(named + [x for x in (hours_txt.split(" (")[0] if hours_txt else "", w["modules"].format(n=planned)) if x])
    sub = " · ".join([x for x in (sheet.get("regulation"), hours_txt) if x])
    rows = []
    for i in infos:
        mins = (" · " + w["min"].format(n=i["minutes"])) if i["minutes"] else ""
        rows.append('  <a href="%s/START_HERE.html">%s · %s%s</a>' % (a(i["code"]), cs.mid(i["n"]), e(i["title"]), e(mins)))
    built = max([i["n"] for i in infos] or [0])
    later = ""
    if planned > built:
        later = (w["later"].format(a=built + 1, b=planned) if planned > built + 1 else w["later_one"].format(a=planned))
    return "\n".join(
        head(lang, title, ["_course_shell/gb_tokens.css", "_course_shell/gb_page.css"],
             '<meta name="description" content="%s">' % a(desc)) + [
            "<body>",
            '<span id="gb-home" hidden></span><!-- the course start page: Android Back leaves the course here, by design -->',
            '<div class="wrap">',
            "  <h1>%s</h1>" % e(title)] +
        (['  <p class="sub">%s</p>' % e(sub)] if sub else []) +
        ['  <div class="links">'] + rows + ["  </div>"] +
        (['  <div class="foot"><p>%s</p></div>' % e(later)] if later else []) +
        (['  <p class="sub"><a href="_course_shell/credits.html">%s</a></p>' % e(w["credits"])] if credits else []) +
        ["</div>", "</body>", "</html>", ""])


IMG_REF = re.compile(r'(?:src|href)="\.\./assets/img/([^"/]+)"')


def credit_rows(root, infos):
    """[(module code, file, what it shows, credit)] - every photograph a module's pages show, with its record's credit; a
    generated picture carries none (L56) and a picture no page shows (assets\\img\\_unused) is not listed"""
    rows = []
    for i in infos:
        md = os.path.join(root, i["code"])
        meta = load_or(os.path.join(md, "assets", "img", "_photo_meta.json"), {})
        shown = []
        for sub in ("presentation", "tasks", "assessment"):
            d = os.path.join(md, sub)
            for f in sorted(os.listdir(d)) if os.path.isdir(d) else []:
                if f.endswith(".html") and not f.startswith("_"):
                    shown += [x for x in IMG_REF.findall(read(os.path.join(d, f))) if x not in shown]
        for f in shown:
            m = meta.get(f) or {}
            line = cm.credit_line(m) if m and not cm.is_generated(m) else ""
            if line:
                rows.append((i["code"], f, cm.first_sentence(m.get("description")) or f, line))
    return rows


def credits_page(title, infos, rows, lang, w):
    """2.63.0 (owner Raivis, 2026-10-21): the photo credits are off the slides - in each photo's full-screen view and here"""
    body = ["<body>", '<a class="gbt-topback" href="../COURSE.html">%s</a>' % e(w["back"]), '<div class="wrap">',
            "  <h1>%s</h1>" % e(w["credits"]), '  <p class="sub">%s · %s</p>' % (e(title), e(w["credits_note"]))]
    for i in infos:
        mine = [r for r in rows if r[0] == i["code"]]
        if mine:
            body.append("  <h2>%s · %s</h2>" % (cs.mid(i["n"]), e(i["title"])))
            body.append("  <ul>" + "".join("<li><b>%s</b> - %s</li>" % (e(r[2]), e(r[3])) for r in mine) + "</ul>")
    return "\n".join(head(lang, "%s — %s" % (title, w["credits"]), ["gb_tokens.css", "gb_page.css"]) + body +
                     ["</div>", "</body>", "</html>", ""])


def ordered(sheet, infos, probs):
    """the modules in the course's own order (2.63.0, the instructors' review of IGF Basic: 1, 4, 6, 8, 2, 3, 5, 7, 9 ...):
    course.build.json "module_order": [module numbers] - delivery, like the course's name; the folders, the scripts and
    "Module n" on each deck stay as they are. A module it leaves out follows in folder order, and is said."""
    order = sheet.get("module_order")
    if not order:
        return infos
    have = [i["n"] for i in infos]
    bad = [x for x in order if not isinstance(x, int) or x not in have]
    if bad or len(set(order)) != len(order):
        probs.append("course.build.json \"module_order\" %s: every entry once, a module number this course has (%s) - %s"
                     % (order, ", ".join(map(str, have)), "not there: %s" % bad if bad else "one is named twice"))
        return infos
    left = [n for n in have if n not in order]
    if left:
        probs.append("course.build.json \"module_order\" leaves out module(s) %s - they follow in folder order; name them" % left)
    by = {i["n"]: i for i in infos}
    return [by[n] for n in list(order) + left]


def course_map(infos):
    rows = ",\n".join('  {"code": %s, "title": %s, "entry": "presentation/index.html"}'
                      % (json.dumps(i["code"]), json.dumps(i["title"], ensure_ascii=False)) for i in infos)
    return "window.COURSE_MAP = [\n%s\n];\n" % rows


# ------------------------------------------------------------------ the build
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("course")
    ap.add_argument("--module", help="only this module's start pages (the course files are always built)")
    ap.add_argument("--force", action="store_true", help="overwrite a page that was changed by hand")
    ap.add_argument("--retitle", action="store_true", help="accept a new course title - the classroom will see a NEW course")
    o = ap.parse_args(argv)
    course = workspace.work_folder(o.course, create=False)
    root = os.path.join(course, workspace.MODULES)
    arch_p = workspace.claude_path(course, "architecture.json")
    if not os.path.isfile(arch_p):
        print("Stopped - there is no approved architecture (working_claude\\architecture.json) - the course title and the\n"
              "  module list come from it (Stage 2).")
        return 2
    arch = cs.load(arch_p)
    title = ((arch.get("course") or {}).get("title") or "").strip()
    if not title:
        print("Stopped - architecture.json has no course.title; the classroom makes the course ID from it.")
        return 2
    mods = sorted(d for d in (os.listdir(root) if os.path.isdir(root) else []) if MODULE.match(d) and os.path.isdir(os.path.join(root, d)))
    # 2.49.2 (F7) - a module built with --draft carries cm.DRAFT_MARK: a preview, not part of the classroom package. It gets no
    # start pages and is not in COURSE.html or the module list - and it is said so, never silently left out
    drafts = [d for d in mods if os.path.isfile(os.path.join(root, d, cm.DRAFT_MARK))]
    for d in drafts:
        print("%s: draft - not packaged (built from a script that is not approved; approve it and compile the module again)" % d)
    mods = [d for d in mods if d not in drafts]
    if not mods:
        if drafts:
            print("Stopped - every module in\n    %s\n  is a draft (not packaged yet)." % root)
            return 2
        print("Stopped - no module folders (module01 ...) in\n    %s" % root)
        return 2
    rec_p = workspace.claude_path(course, RECORD)
    rec = load_or(rec_p, {})
    cp = os.path.join(root, "COURSE.html")
    had = rec.get("title") or (page_title(cp, "") if os.path.isfile(cp) else "")
    if had and had != title and not o.retitle:
        print("Stopped - nothing was written.\n\n  The course is called\n    %s\n  and architecture.json now says\n    %s\n"
              "  The classroom makes the course ID from this title: a new title is a NEW course there, and the results of\n"
              "  the old one stay filed apart. If that is really wanted (the course was never added to the classroom), build\n"
              "  again with --retitle." % (had, title))
        return 2

    lang = lang_of(arch)
    w = WORDS.get(lang, WORDS["en"])
    probs = []
    if lang not in WORDS:
        probs.append("the course is in %s - the start pages' own words exist in English only so far, and were written in English"
                     % (arch.get("course") or {}).get("course_language"))
    sheet = load_or(workspace.claude_path(course, "course.build.json"), {})
    prog = load_or(workspace.claude_path(course, "programme.json"), {})
    infos = ordered(sheet, [module_info(course, arch, m, probs) for m in mods], probs)
    planned = len(arch.get("modules") or []) + (1 if arch.get("final_assessment") else 0)
    only = None
    if o.module:
        only = "module%02d" % int(o.module)
        if only not in mods:
            print("Stopped - %s is a draft (not packaged yet)." % only if only in drafts else
                  "Stopped - there is no %s in\n    %s" % (only, root))
            return 2

    built = []

    def put(path, text, record, key):
        """write unless changed by hand since the last build; True when written"""
        if os.path.isfile(path) and read(path) == text:
            record[key] = cm.sha(text)
            return False
        if os.path.isfile(path) and not o.force and cm.sha(read(path)) != record.get(key):
            probs.append("%s was changed by hand, or was made before this tool - it was not overwritten. Put the change into "
                         "the script, the build sheet or the module folder, then build again with --force"
                         % os.path.relpath(path, root).replace("\\", "/"))
            return False
        write(path, text)
        record[key] = cm.sha(text)
        print("Built %s" % os.path.relpath(path, root).replace("\\", "/"))
        built.append(path)
        return True

    # the course files
    for c in SHELL_CSS:
        src = os.path.join(cm.SKILLS, "course-module-ui", "templates", c)
        dst = os.path.join(root, "_course_shell", c)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(src, dst)
    put(os.path.join(root, "_course_shell", "course_map.js"), course_map(infos), rec, "_course_shell/course_map.js")
    # 2.83.0 - the ILO map the admin shows (every Sub-ILO, where it is taught and checked), read off the scripts on every
    # build. It is generated, so it is rewritten each time; a course with no ILO map yet gets a line, never a stop
    cov, said = ilo_coverage.make(course)
    print(said if cov is None else "Built _course_shell/ilo_coverage.json\n  " + "\n  ".join(said.splitlines()[:-1]))
    # 2.63.0 - the photo credits, off the slides: each photo's full-screen view and this page (CC BY-SA attribution, L56)
    crows = credit_rows(root, infos)
    if crows:
        put(os.path.join(root, "_course_shell", "credits.html"), credits_page(title, infos, crows, lang, w), rec, "_course_shell/credits.html")
    put(cp, course_page(title, infos, planned, sheet, prog, lang, w, credits=bool(crows)), rec, "COURSE.html")
    rec["title"] = title
    cs.save(rec_p, rec)

    # every module's two start pages
    for info in infos:
        if only and info["code"] != only:
            continue
        mdir = os.path.join(root, info["code"])
        deck_p = os.path.join(mdir, "presentation", "index.html")
        if not os.path.isfile(deck_p):
            probs.append("%s has no presentation\\index.html - the classroom finds a module by it (compile_module.py builds it)" % info["code"])
            continue
        for c in SHELL_CSS:
            if not os.path.isfile(os.path.join(mdir, "assets", c)):
                probs.append("%s\\assets has no %s - run course-module-ui\\scripts\\design_system.py install on it" % (info["code"], c))
        mrec_p = workspace.module_record(mdir, cm.RECORD)
        mrec = load_or(mrec_p, {})
        # 2.69.0 - the trainee's handout (handout.py): the classroom's one button on the tablet opens it
        hp = handout.build(course, info["n"], mdir, title, lang)
        if hp:
            put(os.path.join(mdir, "handout", "index.html"), hp, mrec, "handout/index.html")
        put(os.path.join(mdir, "START_HERE.html"), start_here(info, lang, w), mrec, "START_HERE.html")
        put(os.path.join(mdir, "START_HERE_EXTENDED.html"),
            start_extended(info, title, deck_tasks(read(deck_p)), mdir, lang, w, probs), mrec, "START_HERE_EXTENDED.html")
        cs.save(mrec_p, mrec)

    if not built:
        print("Nothing changed - every page is as the last build wrote it.")
    if probs:
        print("\nTo fix before it is shown:")
        for x in probs:
            print("  - " + x)
        return 1
    print("\nNext: check_course_package.py on %s - it runs the classroom's own importer." % root)
    return 0


if __name__ == "__main__":
    sys.exit(main())
