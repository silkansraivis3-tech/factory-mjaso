#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Will the classroom take this course folder, and will every task open and report from its slide? - L45.

    check_course_package.py <master folder | course folder | course\\modules folder>

WHY THIS EXISTS
The owner, 2026-10-05, gave the classroom system's own rules for a course folder
(tablet-system-win/COURSE_FACTORY_PROMPT.md, now knowledge/classroom-system.json): "follow the rules and a course
imports with no errors, every task opens on the trainee tablets from its slide, and every result reaches the
instructor and the admin panel." This is the "before handing a course over, check" list, done by the factory, and
then the admin panel's own importer run on the same folder (course-tablet-publisher/vendor/package-core.mjs,
byte-identical to admin/package-core.mjs) - so a folder that passes here is one the panel takes.

WHAT IT CHECKS - the course folder is course\\modules\\ (L44, L45)
  COURSE.html with a <title>; _course_shell/course_map.js readable as data, listing every module in order
  module folders named module01, module02 ... and nothing else loose (anything of the factory's own starts with _)
  per module: presentation/index.html; START_HERE.html and START_HERE_EXTENDED.html (L43); every .slide has data-title;
    every Task / Check slide has data-activity, and either data-task-href to a page that exists or (work in the room)
    data-link-hint; one slide, one page; every task page in tasks/ and the module check are opened by a slide;
    teaching slides carry the instructor notes in data-cue
  per task page: <title> "CODE — Title" with the slide's code; reports gb-task-done with ok, total and items;
    module checks and the final assessment report head PASSED / NOT PASSED; no task list page (L35)
  every file: no space in its name, at most 6 MB, nothing from the internet, every src/href/url() inside the module
    folder (or _course_shell) and present; no trainee page links to an instructor-only file
  the whole course: at most 6000 files and 300 MB of distinct files
  then the importer itself (needs Node): its errors are problems, its warnings notes
Exit 0 when the classroom will take it as it is, 1 when anything must be fixed, 2 on bad input. Read only.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
from html.parser import HTMLParser
from urllib.parse import unquote, urlparse

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
SKILLS = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import workspace  # noqa: E402

CONTRACT = json.load(io.open(os.path.join(os.path.dirname(HERE), "knowledge", "classroom-system.json"), encoding="utf-8"))
LIM = CONTRACT["limits"]
IMPORTER = os.path.join(SKILLS, "course-tablet-publisher", "vendor", "import_check.mjs")
MODULE = re.compile(r"^module\d{2}$")
# the importer's own two rules, word for word from package-core.mjs
INSTRUCTOR_ONLY = re.compile(
    r"(^|/)(?:instructor[^/]*|presentation|plan|plans|prepare|record|answers|instructor_screens)(/|$)"
    r"|(?:answer[_-]?key|model[_-]?answer|_criteria|instructor[_-]analysis|observation_checklist|practical_skills_record|atbildes"
    r"|pasniedzejam|pasniedzējam|gb_answers|gb_review|gb_roster|gb_observe|_paper\.html|START_HERE\.html|START_COURSE\.html|COURSE\.html"
    r"|module\.html|assessment/record\.html|MODULE_\d+_PLAN|ROTATION_PLAN|SAFETY_BRIEF)", re.I)
TRAINEE_FOLDERS = re.compile(r"(^|/)(tasks|handout|documents|assets|assessment)/", re.I)
REF_ATTR = {"src", "href", "poster", "data-src", "data-model", "data-video"}
CSS_URL = re.compile(r"url\(\s*['\"]?([^'\")\s]+)['\"]?\s*\)")
DASH = "—"


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.refs, self.links, self.slides, self.title, self._t, self.css = [], [], [], "", False, []
        self._style = False

    def handle_starttag(self, tag, attrs):
        a = {k: (v or "") for k, v in attrs}
        for k, v in a.items():
            if k in REF_ATTR and v:
                self.refs.append((tag, k, v))
                if tag == "a" and k == "href":
                    self.links.append(v)
        if "slide" in a.get("class", "").split():
            self.slides.append(a)
        if a.get("style"):
            self.css.append(a["style"])
        if tag == "title":
            self._t = True
        if tag == "style":
            self._style = True

    def handle_endtag(self, tag):
        if tag == "title":
            self._t = False
        if tag == "style":
            self._style = False

    def handle_data(self, data):
        if self._t:
            self.title += data
        if self._style:
            self.css.append(data)


def course_folder(given):
    g = os.path.abspath(given)
    if os.path.isfile(os.path.join(g, "COURSE.html")) or any(MODULE.match(d) for d in os.listdir(g)):
        return g
    w = workspace.work_folder(g, create=False)
    m = os.path.join(w, workspace.MODULES)
    return m if os.path.isdir(m) else g


def read(p):
    return io.open(p, encoding="utf-8", errors="replace").read()


def parse(p):
    pg = Page()
    try:
        pg.feed(read(p))
    except Exception:  # noqa: BLE001 - reported, not fatal
        pass
    return pg


def local(ref):
    u = urlparse(ref)
    if ref.startswith("//") or u.scheme in ("http", "https"):
        return None, "internet"
    if u.scheme or ref.startswith("#") or not ref.strip():
        return None, None
    return unquote(u.path), None


def run_importer(folder):
    node = shutil.which("node")
    if not node:
        return None, "the admin panel's own import check did not run - Node is not installed on this computer; the factory's checks above did"
    try:
        p = subprocess.run([node, IMPORTER, folder], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600)
        return json.loads(p.stdout.strip().splitlines()[-1]), None
    except Exception as err:  # noqa: BLE001
        return None, "the admin panel's own import check could not run: %s" % err


def check(folder):
    probs, notes = [], []
    rel = lambda p: os.path.relpath(p, folder).replace("\\", "/")
    # ---- the course root
    cp = os.path.join(folder, "COURSE.html")
    if not os.path.isfile(cp):
        probs.append("COURSE.html is missing - the course start page; its title is the course title")
    elif not parse(cp).title.strip():
        probs.append("COURSE.html has no <title> - the classroom takes the course title (and its ID) from it")
    mods = sorted(d for d in os.listdir(folder) if os.path.isdir(os.path.join(folder, d)) and MODULE.match(d))
    if not mods:
        probs.append("no module folders named module01, module02 ...")
    for d in sorted(os.listdir(folder)):
        full = os.path.join(folder, d)
        if os.path.isdir(full) and not MODULE.match(d) and not d.startswith("_") and d != "assets":
            probs.append("%s\\ is not a module (module01 ...) - the factory's own material belongs in working_claude, or in a folder starting with _" % d)
        if os.path.isfile(full) and d not in ("COURSE.html",) and not d.lower().endswith((".html", ".css", ".js", ".png", ".jpg", ".jpeg", ".svg", ".webp", ".ico")):
            notes.append("%s at the top of the course folder is skipped by the classroom or not used" % d)
    mp = os.path.join(folder, "_course_shell", "course_map.js")
    if os.path.isfile(mp):
        m = re.search(r"window\.COURSE_MAP\s*=\s*(\[[\s\S]*\])\s*;?\s*$", read(mp))
        try:
            cmap = json.loads(m.group(1)) if m else None
        except ValueError:
            cmap = None
        if cmap is None:
            probs.append("_course_shell/course_map.js cannot be read as data - it must be: window.COURSE_MAP = [ ... ];")
        else:
            codes = [x.get("code") for x in cmap]
            if codes != mods:
                probs.append("_course_shell/course_map.js lists %s, the folder has %s" % (", ".join(map(str, codes)), ", ".join(mods)))
            for x in cmap:
                if not os.path.isfile(os.path.join(folder, str(x.get("code")), str(x.get("entry", "")))):
                    probs.append("_course_shell/course_map.js: %s's entry %s is not there" % (x.get("code"), x.get("entry")))
    else:
        notes.append("_course_shell/course_map.js is not there - the classroom then takes the order from the folder names and the titles from each deck")

    # ---- every file
    count, distinct, seen = 0, 0, set()
    for dp, dn, fn in os.walk(folder):
        for x in dn + fn:
            if " " in x:
                probs.append("a space in the name: %s - the classroom needs names without spaces" % rel(os.path.join(dp, x)))
        for f in fn:
            p = os.path.join(dp, f)
            count += 1
            size = os.path.getsize(p)
            if size > LIM["file_bytes"]:
                probs.append("%s is %.1f MB - the classroom takes at most 6 MB per file" % (rel(p), size / 1048576.0))
            h = hashlib.sha256(open(p, "rb").read()).hexdigest()
            if h not in seen:
                seen.add(h)
                distinct += size
    if count > LIM["files"]:
        probs.append("%d files - the classroom takes at most %d" % (count, LIM["files"]))
    if distinct > LIM["course_bytes_distinct"]:
        probs.append("%.0f MB of distinct files - the classroom takes at most 300 MB" % (distinct / 1048576.0))

    # ---- every module
    for mod in mods:
        md = os.path.join(folder, mod)
        deck = os.path.join(md, "presentation", "index.html")
        for need, why in ((deck, "the deck - the classroom finds a module by it"), (os.path.join(md, "START_HERE.html"), "opens the presentation (L43)"),
                          (os.path.join(md, "START_HERE_EXTENDED.html"), "the instructor's quick-access page (L43)")):
            if not os.path.isfile(need):
                probs.append("%s is missing - %s" % (rel(need), why))
        if os.path.isfile(os.path.join(md, "tasks", "index.html")):
            probs.append("%s/tasks/index.html is a task list - the trainee never sees one; tasks open from their slide (L35)" % mod)
        opened = {}
        if os.path.isfile(deck):
            pg = parse(deck)
            if not pg.slides:
                probs.append("%s/presentation/index.html has no element with class \"slide\"" % mod)
            for n, s in enumerate(pg.slides, 1):
                where = "%s slide %d%s" % (mod, n, (" (%s)" % s["id"]) if s.get("id") else "")
                if not s.get("data-title"):
                    probs.append("%s has no data-title" % where)
                kind = s.get("data-kind", "")
                if kind in ("Task", "Check"):
                    code, href = s.get("data-activity", ""), s.get("data-task-href", "")
                    if not code:
                        probs.append("%s is a %s slide with no data-activity code" % (where, kind))
                    if href:
                        target = os.path.normpath(os.path.join(md, "presentation", unquote(href)))
                        if not os.path.isfile(target):
                            probs.append("%s opens %s, which is not there - the trainees' tablets would get nothing" % (where, href))
                        elif rel(target) in opened:
                            probs.append("%s and %s open the same page %s - one slide, one task page" % (opened[rel(target)][0], where, rel(target)))
                        else:
                            opened[rel(target)] = (where, code, kind)
                    elif kind == "Check":
                        probs.append("%s is the module check slide but has no data-task-href (../assessment/check.html)" % where)
                    elif not s.get("data-link-hint"):
                        probs.append("%s sends the room to work but says neither where (data-task-href) nor how (data-link-hint)" % where)
                elif kind in ("", "Theory") and not s.get("data-cue", "").strip():
                    notes.append("%s has no instructor notes (data-cue) - the instructor's panel shows them" % where)
        for sub in ("tasks", "assessment"):
            d = os.path.join(md, sub)
            if not os.path.isdir(d):
                continue
            for f in sorted(os.listdir(d)):
                p = os.path.join(d, f)
                if not f.lower().endswith(".html") or INSTRUCTOR_ONLY.search(rel(p)):
                    continue
                if rel(p) not in opened:
                    probs.append("%s is opened by no slide - add data-task-href on its slide" % rel(p))
                    code, kind = "", "Task" if sub == "tasks" else "Check"
                else:
                    _, code, kind = opened[rel(p)]
                txt = read(p)
                title = parse(p).title.strip()
                if code and not title.startswith(code + " " + DASH + " "):
                    probs.append("%s: its <title> must be \"%s %s <title>\" - it is \"%s\"" % (rel(p), code, DASH, title))
                if "gb-task-done" not in txt:
                    probs.append("%s never reports its result (gb-task-done) - the instructor would see nothing" % rel(p))
                else:
                    for key in ("ok", "total", "items"):
                        if not re.search(r"\b%s\s*:" % key, txt):
                            probs.append("%s reports gb-task-done without %s" % (rel(p), key))
                    if sub == "assessment" and not ("PASSED" in txt and "NOT PASSED" in txt):
                        probs.append("%s is a check: it must report head 'PASSED' or 'NOT PASSED', with the pass mark on the page" % rel(p))
                if "gb-timer" not in txt:
                    notes.append("%s does not listen for the instructor's timer (gb-timer)" % rel(p))
        # ---- every page and style of the module: inside the module, present, offline, no trainee link to instructor files
        for dp, _, fn in os.walk(md):
            for f in fn:
                if not f.lower().endswith((".html", ".htm", ".css", ".svg")):
                    continue
                p = os.path.join(dp, f)
                pg = parse(p) if f.lower().endswith((".html", ".htm", ".svg")) else None
                text = read(p)
                refs = ([v for _, _, v in pg.refs] + [u for c in pg.css for u in CSS_URL.findall(c)]) if pg else CSS_URL.findall(text)
                if re.search(r"<script\b[^>]*\bsrc\s*=\s*[\"'](?:https?:)?//", text, re.I):
                    probs.append("%s loads a script from the internet - the classroom is offline" % rel(p))
                if re.search(r"fonts\.(?:googleapis|gstatic)\.com", text):
                    notes.append("%s asks for Google Fonts - they are not loaded; it falls back to a system font" % rel(p))
                trainee = TRAINEE_FOLDERS.search(rel(p)) and not INSTRUCTOR_ONLY.search(rel(p))
                for ref in refs:
                    path, kind = local(ref)
                    if kind == "internet":
                        probs.append("%s uses %s from the internet - put the file in the module's assets" % (rel(p), ref))
                        continue
                    if path is None:
                        continue
                    target = os.path.normpath(os.path.join(dp, path))
                    inside_mod = os.path.commonpath([os.path.abspath(target), os.path.abspath(md)]) == os.path.abspath(md)
                    shell = os.path.commonpath([os.path.abspath(target), os.path.abspath(os.path.join(folder, "_course_shell"))]) == os.path.abspath(os.path.join(folder, "_course_shell"))
                    if not (inside_mod or shell):
                        probs.append("%s reaches outside its module: %s - the module needs everything in its own folder (L43)" % (rel(p), ref))
                    elif not os.path.exists(target):
                        probs.append("%s uses %s, which is not there" % (rel(p), ref))
                    elif trainee and INSTRUCTOR_ONLY.search(rel(target)):
                        probs.append("%s (a trainee page) links to %s, which is instructor-only - it would not open on the tablet" % (rel(p), rel(target)))
    return probs, notes, mods


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("folder")
    ap.add_argument("--no-importer", action="store_true", help="only the factory's own checks")
    a = ap.parse_args(argv)
    if not os.path.isdir(a.folder):
        print("Stopped - that folder is not there:\n    %s" % a.folder)
        return 2
    folder = course_folder(a.folder)
    probs, notes, mods = check(folder)
    imp, why = (None, None) if a.no_importer else run_importer(folder)
    if imp:
        probs += ["the classroom's importer: " + e for e in imp.get("errors", [])]
        notes += ["the classroom's importer: " + w for w in imp.get("warnings", [])
                  if not w.startswith("Module checks, marking sheets and Word documents are instructor-only for now")]
    print("Course folder: %s\n  %d module(s)%s" % (folder, len(mods), (" - the classroom would add it as \"%s\" (id %s, version %s), %d file(s) for the trainee tablets"
          % (imp["manifest"].get("title"), imp["manifest"].get("id"), imp["manifest"].get("version"), len(imp.get("trainee", []))) if imp and imp.get("manifest") else "")))
    if why:
        notes.append(why)
    if probs:
        print("\n%d thing(s) to fix before it goes into the classroom:" % len(probs))
        for x in probs:
            print("  - " + x)
    if notes:
        print("\nWorth a look (does not stop it):")
        for x in notes:
            print("  - " + x)
    if not probs:
        print("\nReady: the classroom takes this folder as it is%s." % ("" if imp else " (the importer itself did not run here)"))
    return 1 if probs else 0


if __name__ == "__main__":
    sys.exit(main())
