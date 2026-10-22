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
    the final assessment reports head PASSED / NOT PASSED against its pass mark, a module check has none (2.63.0);
    no task list page (L35)
  every file: no space in its name, at most 15 MB, nothing from the internet, every src/href/url() inside the module
    folder (or _course_shell) and present; no trainee page links to an instructor-only file
  the whole course: at most 6000 files and 300 MB of distinct files
  3D (L46): at most half of a presentation's teaching slides are 3D (each .slide says its kind in data-visual); and
    notes from the module's own scripts where a 3D scene would lag on the tablet (knowledge/media-and-tasks.json three_d)
  team tasks (rulebook 4b): a slide with data-mode="team" and its page with task-mode / task-scope metas, both or
    neither; the page listens for gb-team; scope team hands in with scope: 'team'; a sensible data-team-size
  every task page (rulebook of 2026-10-19): never leaves itself - no link to a file, no new window, no navigation of
    the frame; no 'Answers' / 'Review' / 'Show solution' / 'Next task' / 'Menu' / 'Home' button - the result is last
  every trainee page: no answer readable in its source (data-correct, data-answer); no link into a _ folder;
    notes when a page that hears the timer never reports timeout: true, or offers "try again" inside the classroom
  honesty markers (2.63.2): the alt, data-about, data-credit and title attributes of the deck and every trainee page carry none of
    the factory's markers (PLACEHOLDER, UNKNOWN, VERIFY, TODO, TBD, PROVISIONAL, RIGHTS_REVIEW_REQUIRED, GENERATED_ASSET_REQUIRED ...)
  the recap (L51): every teaching module's deck has the recap slide straight before its module-check slide -
    class "recap", data-kind "Summary", 3 to 6 points (.rc-item) - the same design in every module
  the picture viewer (L51): every page of a module that shows a picture loads gb_zoom.js and gb_zoom.css
  a draft (2.49.2): a module marked DRAFT_NOT_PACKAGED.txt by compile_module.py --draft (its script is not approved) is
    left out of every check and of the importer's run, and reported as a note - "draft - not packaged"; a final
    assessment variant (FA, FB) must be a Check slide that opens a graded page in assessment/
  the person's design choices (L26, design_choices.py): a rule the operator chose against, after hearing the risk,
    is reported as their choice - a note, never a problem
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
import design_choices  # noqa: E402  - the operator's design choices are theirs, not problems (L26, 2.30.0)

CONTRACT = json.load(io.open(os.path.join(os.path.dirname(HERE), "knowledge", "classroom-system.json"), encoding="utf-8"))
LIM = CONTRACT["limits"]
MEDIA = json.load(io.open(os.path.join(os.path.dirname(HERE), "knowledge", "media-and-tasks.json"), encoding="utf-8"))
TD = MEDIA["three_d"]
THREE_LIB = re.compile(r"^three(\.module)?(\.min)?\.js$|^draco|^meshopt", re.I)
SLOW = (   # what makes a 3D scene lag on the classroom tablet - each a note, with the fix (L46)
    (re.compile(r"preserveDrawingBuffer\s*:\s*true"), "keeps preserveDrawingBuffer on - every frame is kept in memory; leave it off"),
    (re.compile(r"setPixelRatio\(\s*(?:window\.|w\.)?devicePixelRatio\s*\)"), "draws at an uncapped pixel ratio - Math.min(devicePixelRatio, 2) looks the same and costs less"),
    (re.compile(r"setPixelRatio\(\s*1(?:\.0)?\s*\)"), "draws at pixel ratio 1 - blurry on the tablet's sharp screen; Math.min(devicePixelRatio, 2)"),
)
SHADOWS_ON = re.compile(r"shadowMap\.enabled\s*=\s*true")
SHADOWS_ONCE = re.compile(r"shadowMap\.autoUpdate\s*=\s*false")
RENDERER = re.compile(r"new\s+[\w.]*WebGLRenderer\s*\(")
ANSWER_ATTR = re.compile(r"<[^>]*\sdata-(?:correct|answer|right|solution)\s*=", re.I)
RETRY = re.compile(r"(?i)\b(?:try|start|play)\s+again\b|m\u0113\u0123in\u0101t v\u0113lreiz|s\u0101kt no jauna")
IN_FRAME = re.compile(r"(?:window\.)?parent\s*[!=]==?\s*(?:window|self)|(?:window\.)?self\s*[!=]==?\s*(?:window\.)?top|(?:window\.)?top\s*[!=]==?\s*(?:window|self)")
LEAVES = (   # a task page never leaves itself - the tablet has no back button (rulebook of 2026-10-19)
    (re.compile(r"<a\b[^>]*\bhref\s*=\s*[\"'](?!#|javascript:void)[^\"']+", re.I), "has a link to another page"),
    (re.compile(r"\btarget\s*=\s*[\"']_blank", re.I), "opens a new window (target=_blank)"),
    (re.compile(r"\bwindow\.open\s*\("), "opens a new window (window.open)"),
    (re.compile(r"\blocation\.(?:href\s*=(?!=)|assign\s*\(|replace\s*\()|\b(?:window\.|document\.)?location\s*=(?!=)"), "sends the frame to another page (location)"),
)
NO_PRESS = r"(?:answers?|show answers?|correct answers?|review|review answers?|show (?:the )?solutions?|solutions?|next task|menu|main menu|home|back|back to (?:menu|tasks|the guide)|all tasks)"
AFTER_BUTTON = re.compile(r"<(?:button|a)\b[^>]*>\s*(?:<[^>]+>\s*)*(" + NO_PRESS + r")\s*(?:<[^>]+>\s*)*</(?:button|a)>"
                          r"|(?:textContent|innerText|innerHTML|value)\s*=\s*[\"'](" + NO_PRESS + r")[\"']", re.I)
TIMEOUT_TRUE = re.compile(r"timeout\s*:\s*(?!false\b)[\w!(]")
TEAM_SIZE = re.compile(r"^\d+(?:-\d+)?$")
IMPORTER = os.path.join(SKILLS, "course-tablet-publisher", "vendor", "import_check.mjs")
MODULE = re.compile(r"^module\d{2}$")
DRAFT_MARK = "DRAFT_NOT_PACKAGED.txt"       # written by compile/scripts/compile_module.py --draft
FINAL_SET = re.compile(r"^F[A-Z]$")           # a final assessment's set: FA, FB ... (2.49.2)
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
# 2.63.2 - the attributes a trainee page shows or reads aloud (a photo's alt, its credit, its hover title) are scanned for the
# factory's honesty markers with the SAME list check_slide_text.py uses for text, plus the upper-case words that are only
# markers in an attribute (IGF M03 s16: a photo's alt said "RIGHTS_REVIEW_REQUIRED" and only a human cross-check saw it)
MARKED_ATTRS = ("alt", "data-about", "data-credit", "title")
_HONESTY = json.load(io.open(os.path.join(os.path.dirname(HERE), "knowledge", "slide-text-rules.json"), encoding="utf-8"))["honesty_markers"]
ATTR_MARKERS = [(re.compile(p["pattern"]), p["label"]) for p in _HONESTY["patterns"] + _HONESTY.get("attribute_only_patterns", [])]
# the deck is projected in front of the class, so it is a page a trainee reads although the importer files it as instructor-side
DECK_PAGE = re.compile(r"(^|/)presentation/[^/]+\.html?$|(^|/)module\.html$", re.I)
INSTRUCTOR_NAMES = re.compile(r"gb_review|gb_answers|gb_roster|gb_observe|answer[_-]?key|_paper\.html", re.I)


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.refs, self.links, self.slides, self.title, self._t, self.css, self.metas = [], [], [], "", False, [], {}
        self._style = False
        self.pictures = 0
        self.marked = []      # (tag, attribute, value) of MARKED_ATTRS

    def handle_starttag(self, tag, attrs):
        a = {k: (v or "") for k, v in attrs}
        for k in MARKED_ATTRS:
            if a.get(k, "").strip():
                self.marked.append((tag, k, a[k]))
        for k, v in a.items():
            if k in REF_ATTR and v:
                self.refs.append((tag, k, v))
                if tag == "a" and k == "href":
                    self.links.append(v)
        cls = a.get("class", "").split()
        if "slide" in cls:
            a["_points"] = 0
            self.slides.append(a)
        if "rc-item" in cls and self.slides:
            self.slides[-1]["_points"] += 1
        if tag in ("img", "svg") and "data-no-zoom" not in a:     # the result ring, a control's symbol: not a picture
            self.pictures += 1
        if a.get("style"):
            self.css.append(a["style"])
        if tag == "meta" and a.get("name"):
            self.metas[a["name"].lower()] = a.get("content", "").strip()
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


def with_scripts(p, pg):
    """The page's text and the text of every script file of its own it loads - a shared task file
    (gb_task.js) does the reporting for the page, so gb-task-done / gb-timer may live there."""
    parts = [read(p)]
    for tag, k, v in pg.refs:
        path, _ = local(v)
        if tag == "script" and k == "src" and path:
            js = os.path.normpath(os.path.join(os.path.dirname(p), path))
            if os.path.isfile(js):
                parts.append(read(js))
    return "\n".join(parts)


def run_importer(folder):
    node = shutil.which("node")
    if not node:
        return None, "the admin panel's own import check did not run - Node is not installed on this computer; the factory's checks above did"
    try:
        p = subprocess.run([node, IMPORTER, folder], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600)
        return json.loads(p.stdout.strip().splitlines()[-1]), None
    except Exception as err:  # noqa: BLE001
        return None, "the admin panel's own import check could not run: %s" % err


def run_importer_without_drafts(folder):
    """the importer on the package as the classroom would get it: a module marked as a draft (DRAFT_NOT_PACKAGED.txt) is left out -
    on a copy made of hard links (a copy of the files where the disk will not link), removed again afterwards"""
    drafts = {d for d in os.listdir(folder) if MODULE.match(d) and os.path.isfile(os.path.join(folder, d, DRAFT_MARK))}
    if not drafts:
        return run_importer(folder)
    import tempfile

    def link(src, dst):
        try:
            os.link(src, dst)
        except OSError:
            shutil.copy2(src, dst)
    tmp = tempfile.mkdtemp(prefix="package_")
    try:
        dst = os.path.join(tmp, os.path.basename(os.path.abspath(folder)))
        shutil.copytree(folder, dst, ignore=lambda d, names: [n for n in names if d == folder and n in drafts], copy_function=link)
        return run_importer(dst)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


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
    # 2.49.2 (F7) - a module built with compile_module.py --draft carries DRAFT_NOT_PACKAGED.txt: a preview from a script that is
    # not approved. It is not part of the classroom package - left out of every check below, and said so, never silently
    drafts = [d for d in mods if os.path.isfile(os.path.join(folder, d, DRAFT_MARK))]
    for d in drafts:
        notes.append("%s: draft - not packaged (its script is not approved; it is left out of this check and of the classroom "
                     "package until it is approved and compiled again)" % d)
    mods = [d for d in mods if d not in drafts]
    if not mods:
        probs.append("no module folders named module01, module02 ...")
    for d in sorted(os.listdir(folder)):
        full = os.path.join(folder, d)
        if os.path.isdir(full) and d.startswith(".") and not any(fs for _, _, fs in os.walk(full)):
            # an empty sync-tool folder (Google Drive's .tmp.drivedownload / .tmp.driveupload): nothing in it ships (2.58.0 -
            # the IGF full build: every module's package check failed on two of them copied in from a synced folder)
            notes.append("%s\\ is an empty sync-tool folder - nothing in it ships; delete it when the sync tool is done" % d)
            continue
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
            # 2.63.0 - a course may declare its own order (working_claude\course.build.json "module_order", the
            # instructors' review of IGF Basic): course_map.js may then list every module once, in that order
            declared = None
            cbp = os.path.join(os.path.dirname(os.path.abspath(folder)), "working_claude", "course.build.json")
            if os.path.isfile(cbp):
                try:
                    declared = ["module%02d" % int(x) for x in (json.loads(read(cbp)).get("module_order") or [])] or None
                except (ValueError, TypeError):
                    declared = None
            same_set = sorted(map(str, codes)) == sorted(mods) and len(set(codes)) == len(codes)
            if codes != mods and not (same_set and declared and codes == declared + [x for x in mods if x not in declared]):
                probs.append("_course_shell/course_map.js lists %s, the folder has %s%s" % (
                    ", ".join(map(str, codes)), ", ".join(mods),
                    " (course.build.json \"module_order\" says %s)" % ", ".join(declared) if declared else
                    " - a course in its own order names it in working_claude\\course.build.json \"module_order\""))
            for x in cmap:
                if not os.path.isfile(os.path.join(folder, str(x.get("code")), str(x.get("entry", "")))):
                    probs.append("_course_shell/course_map.js: %s's entry %s is not there" % (x.get("code"), x.get("entry")))
    else:
        notes.append("_course_shell/course_map.js is not there - the classroom then takes the order from the folder names and the titles from each deck")

    # ---- every file
    count, distinct, seen = 0, 0, set()
    for dp, dn, fn in os.walk(folder):
        if dp == folder:
            dn[:] = [x for x in dn if x not in drafts]          # a draft module is not part of the package
        # 2.52.0 - a folder starting with _ (assets\img\_unused\, the pictures no page shows) is skipped by the classroom's
        # importer (package-core.mjs internal()), so it is no part of the package's files, sizes or names either
        dn[:] = [x for x in dn if not x.startswith("_") or x == "_course_shell"]
        for x in dn + fn:
            if " " in x:
                probs.append("a space in the name: %s - the classroom needs names without spaces" % rel(os.path.join(dp, x)))
        for f in fn:
            p = os.path.join(dp, f)
            count += 1
            size = os.path.getsize(p)
            if size > LIM["file_bytes"]:
                probs.append("%s is %.1f MB - the classroom takes at most %d MB per file" % (rel(p), size / 1048576.0, LIM["file_bytes"] // 1048576))
            h = hashlib.sha256(open(p, "rb").read()).hexdigest()
            if h not in seen:
                seen.add(h)
                distinct += size
    if count > LIM["files"]:
        probs.append("%d files - the classroom takes at most %d" % (count, LIM["files"]))
    if distinct > LIM["course_bytes_distinct"]:
        probs.append("%.0f MB of distinct files - the classroom takes at most 300 MB" % (distinct / 1048576.0))

    recap_probs, viewer_probs = [], []
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
                    if FINAL_SET.match(code) and (kind != "Check" or "/assessment/" not in "/" + unquote(href).replace("\\", "/").lstrip("./")):
                        probs.append("%s: a final assessment variant (%s) must be a Check slide that opens a graded page in assessment/ "
                                     "(final.html, or final_a.html, final_b.html for variants) - not a task page; it opens %s as a %s slide"
                                     % (where, code, href or "nothing", kind))
                    if href:
                        target = os.path.normpath(os.path.join(md, "presentation", unquote(href)))
                        if not os.path.isfile(target):
                            probs.append("%s opens %s, which is not there - the trainees' tablets would get nothing" % (where, href))
                        elif rel(target) in opened:
                            probs.append("%s and %s open the same page %s - one slide, one task page" % (opened[rel(target)][0], where, rel(target)))
                        else:
                            opened[rel(target)] = (where, code, kind, s)
                    elif kind == "Check":
                        probs.append("%s is the module check slide but has no data-task-href (../assessment/check.html)" % where)
                    elif not s.get("data-link-hint"):
                        probs.append("%s sends the room to work but says neither where (data-task-href) nor how (data-link-hint)" % where)
                elif kind in ("", "Theory") and not s.get("data-cue", "").strip():
                    notes.append("%s has no instructor notes (data-cue) - the instructor's panel shows them" % where)
            # L46 - 3D where it makes sense: at most half of the presentation's teaching slides
            vis = [s.get("data-visual", "").strip() for s in pg.slides if s.get("data-visual", "").strip() not in ("", "none")]
            teach = [s for s in pg.slides if s.get("data-kind", "") in ("", "Theory")]
            three = [s for s in teach if MEDIA["visual_kinds"].get(s.get("data-visual", "").strip(), {}).get("family") in TD["families"]]
            if len(three) >= TD["count_from"] and len(three) > TD["max_share"] * len(teach):
                probs.append("%s: %d of the %d teaching slides are 3D (%.0f %%) - at most %.0f %%; keep 3D where a shape, an inside or a "
                             "layout in space is taught, the rest a photograph, a drawing or an animation - at full quality (L46)"
                             % (mod, len(three), len(teach), 100.0 * len(three) / len(teach), 100 * TD["max_share"]))
            # L51 - the module closes with the recap, straight before its module check, in the one shared design
            checks = [i for i, s in enumerate(pg.slides) if s.get("data-kind", "") == "Check"
                      and os.path.basename(s.get("data-task-href", "")).lower() == "check.html"]
            if checks:
                i = checks[-1]
                prev = pg.slides[i - 1] if i else {}
                if "recap" not in prev.get("class", "").split():
                    recap_probs.append("%s has no recap slide straight before its module check - every teaching module closes with "
                                       "\"what to take away\" in the shared design (class \"slide dark recap\", gb_compose.css 15; L51)" % mod)
                else:
                    n = prev.get("_points", 0)
                    if not 3 <= n <= 6:
                        recap_probs.append("%s: the recap slide has %d point(s) (.rc-item) - it needs 3 to 6 (L51)" % (mod, n))
                    if prev.get("data-kind", "") != "Summary":
                        notes.append("%s: the recap slide says data-kind=\"%s\" - it is \"Summary\"" % (mod, prev.get("data-kind", "")))
            uses3d = any(THREE_LIB.match(f) for _, _, fn in os.walk(md) for f in fn)
            if uses3d and not vis:
                notes.append("%s uses 3D, but its slides do not say their kind of picture (data-visual) - the 3D share cannot be counted" % mod)
        # L46 - would a 3D scene lag on the tablet? read from the module's own scripts
        slow, renderers = {}, []
        for dp, _, fn in os.walk(md):
            for f in fn:
                p = os.path.join(dp, f)
                if f.lower().endswith((".glb", ".gltf")) and os.path.getsize(p) > 5 * 1048576:
                    notes.append("%s is %.1f MB - compress it without visible loss (gltf-transform: meshopt, KTX2)" % (rel(p), os.path.getsize(p) / 1048576.0))
                if not f.lower().endswith((".js", ".html", ".htm")) or THREE_LIB.match(f):
                    continue
                text = read(p)
                renderers += [rel(p)] * len(RENDERER.findall(text))
                for rx, why in SLOW:
                    if rx.search(text):
                        slow.setdefault(why, []).append(rel(p))
                if SHADOWS_ON.search(text) and not SHADOWS_ONCE.search(text):
                    slow.setdefault("works out its shadows again on every frame - keep them as they are and work them out once while the model "
                                    "is still (shadowMap.autoUpdate = false, needsUpdate when something moves): the same look, far less work", []).append(rel(p))
        if len(renderers) > 1:
            notes.append("%s makes %d separate 3D renderers (%s) - one shared renderer for the whole deck runs smoother" % (mod, len(renderers), ", ".join(sorted(set(renderers)))))
        for why, files in slow.items():
            notes.append("%s %s (L46)" % (", ".join(files), why))
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
                    code, kind, sa = "", "Task" if sub == "tasks" else "Check", {}
                else:
                    _, code, kind, sa = opened[rel(p)]
                tp = parse(p)
                txt = with_scripts(p, tp)
                title = tp.title.strip()
                if code and not title.startswith(code + " " + DASH + " "):
                    probs.append("%s: its <title> must be \"%s %s <title>\" - it is \"%s\"" % (rel(p), code, DASH, title))
                if "gb-task-done" not in txt:
                    probs.append("%s never reports its result (gb-task-done) - the instructor would see nothing" % rel(p))
                else:
                    for key in ("ok", "total", "items"):
                        if not re.search(r"\b%s\s*:" % key, txt):
                            probs.append("%s reports gb-task-done without %s" % (rel(p), key))
                    # 2.63.0 (owner Raivis, 2026-10-21): the final assessment reports PASSED / NOT PASSED against its pass
                    # mark; a module check has no pass mark (data-pass="0") - its score is for the trainee and the instructor
                    dp = re.search(r'<body[^>]*\bdata-pass="(\d+)"', io.open(p, encoding="utf-8", errors="replace").read())
                    final = os.path.basename(p).lower().startswith("final")
                    if sub == "assessment" and final and not ("PASSED" in txt and "NOT PASSED" in txt and (not dp or int(dp.group(1)) > 0)):
                        probs.append("%s is the final assessment: it must report head 'PASSED' or 'NOT PASSED', with the pass mark "
                                     "on the page" % rel(p))
                    if sub == "assessment" and not final and dp and int(dp.group(1)) > 0:
                        probs.append("%s is a module check: it has no pass mark and no PASSED / NOT PASSED (data-pass=\"0\"; L27, "
                                     "owner 2026-10-21) - only the final assessment has one" % rel(p))
                if "gb-timer" not in txt:
                    notes.append("%s does not listen for the instructor's timer (gb-timer)" % rel(p))
                elif not TIMEOUT_TRUE.search(txt):
                    notes.append("%s hears the timer but never reports timeout: true - when the time is up it marks what was done and reports it" % rel(p))
                if RETRY.search(txt) and not IN_FRAME.search(txt):
                    notes.append("%s offers to try again - inside the classroom one opening gives one result; allow it only outside the frame (window.parent === window)" % rel(p))
                # rulebook of 2026-10-19 - the result is the last screen, and the page never leaves itself
                for rx, why in LEAVES:
                    if rx.search(txt):
                        probs.append("%s %s - the trainee tablet has no back button, so it would be a dead end; a task moves only between its own steps" % (rel(p), why))
                m = AFTER_BUTTON.search(txt)
                if m:
                    probs.append("%s has a \"%s\" button - after the result there is nothing to press; the classroom shows the answers in the debrief" % (rel(p), (m.group(1) or m.group(2)).strip()))
                # rulebook 4b - a team task is marked in both places, and works without teams too
                slide_team, page_team = sa.get("data-mode", "") == "team", tp.metas.get("task-mode", "") == "team"
                if slide_team and not page_team:
                    probs.append("%s is opened by a team-task slide (data-mode=\"team\") but has no <meta name=\"task-mode\" content=\"team\">" % rel(p))
                if page_team and not slide_team:
                    probs.append("%s says it is a team task (task-mode) but its slide has no data-mode=\"team\" - the classroom would not sort it into teams" % rel(p))
                if slide_team or page_team:
                    scope = tp.metas.get("task-scope", "")
                    if kind == "Check":
                        probs.append("%s: a check is answered by each trainee alone - it cannot be a team task" % rel(p))
                    if scope not in ("team", "member"):
                        probs.append("%s: <meta name=\"task-scope\"> must be team (one answer per team) or member (everyone answers) - it is \"%s\"" % (rel(p), scope))
                    if "gb-team" not in txt:
                        probs.append("%s is a team task but never listens for gb-team - it cannot show the team and the trainee's role" % rel(p))
                    elif "setTimeout" not in txt:
                        notes.append("%s: when no team arrives within about 2 seconds the task runs alone - no timer for that fallback was found" % rel(p))
                    if scope == "team" and not re.search(r"scope\s*:\s*['\"]team['\"]", txt):
                        probs.append("%s hands in one answer per team (task-scope team) but its gb-task-done has no scope: 'team'" % rel(p))
                    size = sa.get("data-team-size", "").strip()
                    if slide_team and not size:
                        notes.append("%s has no data-team-size on its slide - the instructor splits the class by it" % rel(p))
                    elif slide_team and not TEAM_SIZE.match(size):
                        probs.append("%s: data-team-size is \"%s\" - a number, or a range such as 3-4" % (rel(p), size))
                    if sa.get("data-roles") and tp.metas.get("task-roles") and sa["data-roles"] != tp.metas["task-roles"]:
                        notes.append("%s: the roles on the slide (%s) and on the page (%s) differ" % (rel(p), sa["data-roles"], tp.metas["task-roles"]))
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
                if pg is not None and f.lower().endswith((".html", ".htm")) and pg.pictures and \
                        re.search(r"(^|/)(presentation|tasks|assessment|handout)/", rel(p)):
                    loaded = {os.path.basename(local(v)[0] or "") for _, _, v in pg.refs}
                    if not {"gb_zoom.js", "gb_zoom.css"} <= loaded:
                        viewer_probs.append("%s shows pictures but does not load gb_zoom.js and gb_zoom.css - every picture opens full "
                                            "screen and closes again (L51; design_system.py install copies them)" % rel(p))
                trainee = TRAINEE_FOLDERS.search(rel(p)) and not INSTRUCTOR_ONLY.search(rel(p))
                seen_marks = set()
                if pg is not None and f.lower().endswith((".html", ".htm")) and not INSTRUCTOR_NAMES.search(rel(p)) \
                        and (DECK_PAGE.search(rel(p)) or trainee):
                    for tag, attr, val in pg.marked:
                        for rx, label in ATTR_MARKERS:
                            if rx.search(val) and (attr, val, label) not in seen_marks and len(seen_marks) < 6:
                                seen_marks.add((attr, val, label))
                                probs.append("%s: <%s %s=\"%s\"> carries the marker %s - a message to the owner (factory-notes.md), never on a page "
                                             "a trainee sees or hears; write the real words, or take the picture out (2.63.2)"
                                             % (rel(p), tag, attr, val if len(val) <= 90 else val[:87] + "...", label))
                if trainee and f.lower().endswith((".html", ".htm")) and ANSWER_ATTR.search(text):
                    probs.append("%s (a trainee page) carries its answers in the page (data-correct / data-answer) - they can be read without doing "
                                 "the task; mark answers with data-key (classroom-system.json task_page.answer_keys)" % rel(p))
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
                    elif re.search(r"(^|/)_(?!course_shell/)[^/]*/", rel(target)):
                        probs.append("%s links into %s - a folder starting with _ is skipped by the classroom" % (rel(p), rel(target)))
                    elif not os.path.exists(target):
                        probs.append("%s uses %s, which is not there" % (rel(p), ref))
                    elif trainee and INSTRUCTOR_ONLY.search(rel(target)):
                        probs.append("%s (a trainee page) links to %s, which is instructor-only - it would not open on the tablet" % (rel(p), rel(target)))
    # L26 (2.30.0) - where the operator chose against a design rule after hearing the risk, it is their choice
    choices = design_choices.load(folder)
    for rule, found in (("recap", recap_probs), ("picture-viewer", viewer_probs)):
        keep, waived = design_choices.split(found, choices, rule, lambda x: True)
        probs += keep
        notes += waived
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
    imp, why = (None, None) if a.no_importer else run_importer_without_drafts(folder)
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
