#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""walk_review - "walk it like a trainee": the deck's stops and the task pages' questions looked at together, by an AI
reviewer, before a module is done.

    python walk_review.py prepare <course> --module N [--slides s03,s07,<task page>] [--stale]
    python walk_review.py sign    <course> --module N --review reviewer.json --built-by "<who built it>" [--built-by "<who fixed it>"]
    python walk_review.py verify  <course> --module N
    python walk_review.py accept  <course> --module N --by "<operator>" --why "<why it can ship>" [--slides s04]
    python walk_review.py reopen  <course> --module N --by "<operator>"

--module is a number or "final". The final assessment has ONE name, FINAL, whether it is asked for as "final" (the build)
or by the number of the folder that holds it (the portal walks the folders): canon().

WHY (operator Aleksis Vejs, 2026-11-09, after the Project Management review): the checks measure fit and overflow; they never
look at the slides the way a trainee does - a drawing that never moves, an empty chart, a picture that says the opposite of
the lit line all passed. fit_gate.py walks the deck (Start, every Next) and, at 1280x800 only, saves each stop as a ~480 px
picture with walk.json (the lit line's text, the room's question / its answer, the figure's signature, and each slide's
fingerprint as the walk began) into working_claude/_build/walk/MNN/. This script turns them into something a reviewer can
judge several slides at once:

  prepare  one CONTACT SHEET per slide (all its stops in a numbered grid) -> walk/MNN/sheets/sNN.png, sheets/manifest.json
           (each sheet's slide fingerprint) and walk/MNN/review_brief.md: the sheets in batches of up to 4 slides, each
           slide's stop texts and its figure's why / why_text, and the RUBRIC. --stale: only the slides with no verdict for
           what they show now (never reviewed, changed since, or reopened by the operator) - after a fix that is the changed
           slides alone. Refused when the pictures are older than the deck. Needs Pillow (python -m pip install pillow).
  sign     the reviewer's answer {"reviewed_by": "...", "slides": {"s03": {"ok": true, "fails": []}}} ->
           working_claude/_build/MNN_walk_review.json: who built and fixed the module, who reviewed it, the round, and for
           every slide its verdict with the fingerprint of the sheet the reviewer SAW (the manifest's, never the deck's at
           sign time). Refused: a slide with no sheet, a sheet older than the walk or the deck, an "ok" that is not true or
           false, a reviewer whose name is a builder's or a fixer's. A slide that already has a verdict for what it shows
           now keeps it - a verdict is replaced only once the slide changes, or the operator reopens it.
  verify   exit 0 only when EVERY slide of the deck has a verdict for what it shows NOW and no fail is open. Exit 1
           otherwise: missing / stale (names the changed slides only) / incomplete / failing.
  accept   the operator lets fails stand: recorded on each slide with who, when, why and how the command was run. A slide
           that changes afterwards needs its review again - the accept was for what the reviewer saw.
  reopen   the operator has the leftovers fixed after all: the two rounds start again, and the open slides may be reviewed
           again as they are.

ONE SLIDE, ONE FINGERPRINT - the same one the audits use (course-factory/scripts/check_cache.py): the slide's own markup, its
place in the deck, the deck around the slides, every file of the module's assets\\ but the pictures (stylesheets, gb_*.js,
kit_parts.js, kit3d_parts.js ...) and every file the slide names (its photographs, a 3D scene). A fix to one slide leaves
every other slide's verdict standing; a changed stylesheet or script makes them all stale; a replaced photograph makes the
slides that show it stale.

THE TASK PAGES ARE WALKED TOO (operator Aleksis Vejs, 2026-11-10: "add trainee task pages as well"). Every page of
tasks\\ and assessment\\ (self-checks, the module check, the final assessment - never an answer key) is answered like a
trainee by review_sheets.mjs --walk-dir, which saves into walk/MNN/tasks/<page>/ each question as asked at 1280 x 800 and at
1024 x 768, answered wrong and checked (its tap areas outlined), answered right and checked - and the page's last screen
after each run, once a group of trainees - with tasks.json. One verdict covers one UNIT: a slide ("s03"), a question of a
task page ("<page>.<question>") or a page's last screen ("<page>.result"). A task page has ONE fingerprint for all of its
units - the page and every file it loads (check_cache.py's, the audits' own) - written by stamp_tasks() before the page is
walked: a changed page makes its own questions stale and no other page's, and no slide's. A task page never walked is a unit
with no picture: verify fails it. Its questions are judged by TASK_RUBRIC. Everything else - the sheets a reviewer saw, the
two rounds, the accept, who may sign - is the same machinery; "slide" below also stands for a task-page unit.

TWO ROUNDS AT MOST. The first review, one fix, the review of what the fix changed - then no third: what still fails is the
operator's, listed with its slide and stop (accept, or reopen). sign refuses a third round, and a fail on a slide that was
renamed or removed still counts toward it.

WHO IS WHO is an honour system the factory records, not one it can enforce: the reviewer is an AI agent that did not build
or fix the module, the accept and the reopen are the operator's own decisions. sign refuses a reviewer named like a builder
or a fixer; accept and reopen refuse a builder's, a fixer's or a reviewer's name and record whether they were typed in a
terminal or run by a session. In the whole-course workflow the reviewer is the walk judge (one a module, reading the sheets
a batch at a time - orchestration/workflows/build_course.js); in a single session compile/GUIDE.md 2i and fix/GUIDE.md say
how: one Sonnet subagent per batch of up to 4 contact sheets (several images in one look), returning the reviewer JSON.
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import re
import sys
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
FACTORY_SCRIPTS = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(HERE))), "course-factory", "scripts")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BATCH = 4
MAX_ROUNDS = 2
SALT = "walk"       # the walk's part of a fingerprint: no checker script is in it - a factory update is no change of a slide
RUBRIC = [
    "Something visibly changes on each Next (the lit line, the figure, the question or its answer) - a stop that looks like the one before it is a fail.",
    "The picture shows what the lit line says (a bar rises when the line says it rises; the highlighted part is the part named).",
    "Nothing is empty, hidden, cut, duplicated or contradictory - an empty chart or axis, a label off the edge, the same thing drawn twice, a figure that says one thing while the words say another.",
    "A trainee would know what to do / what the slide teaches - the slide has one point and it is readable from the sheet.",
    "The drawing has a reason and serves it - its why / why_text (below) is what the trainee sees change or see; a drawing that is decoration, or a 3D model of a flat idea, fails.",
    "The answer / reveal is visible when it should be and does not cover the figure.",
    "Nothing on screen is the factory's instead of the trainee's - a file path, a drive letter, a placeholder, a credit line that is cut or lies over the picture.",
    "The picture is the thing the words name, and a seafarer would not call it wrong - another instrument, part or place than the slide names, a part drawn where it cannot be, a pipe or label ending on nothing.",
]
TASK_RUBRIC = [
    "The question and every choice are readable and whole at 1280 x 800 (picture 1) and at 1024 x 768 (picture 2) - nothing cut, overlapping, off the edge or too small to read; every line and label of a drawing stands out from what is behind it, and no leader line runs through words.",
    "The picture is the one the question is about - the instrument, part or place the words name, drawn so that a seafarer would not call it wrong (a part where it cannot be, a pipe or label ending on nothing) - and its tap areas / drop zones (the pink dashes of picture 3) sit on the right parts: each covers the whole thing it stands for; an area on nothing, on the wrong part, or two areas on one part is a fail.",
    "The feedback after Check says which it was and explains (why it is right, or what to look at again; after a wrong answer the right one is marked on the right thing) and does not hand over the answer of a later question of the same page (each page's questions are listed below, in order).",
    "Nothing a trainee needs is under the Check bar or below the screen - the last choice, the lower part of the picture, a drop zone.",
    "A trainee with zero tablet experience can do it: tap and drag only, big controls well apart, and the screen says what to do (L42).",
    "The page's last screen (<page>.result) is the last screen: the trainee's own score, and no way onward to another task or back into the questions (L27, L45). A blind page (the final assessment) does not tell right from wrong after a question, by design - that alone is no fail.",
    "Nothing on screen is the factory's instead of the trainee's - a file path, a drive letter, a placeholder, a question's id, a note to the builder.",
]


def mid(module):
    return "FINAL" if str(module).lower() == "final" else "M%02d" % int(module)


def _work(course):
    return os.path.abspath(course)


def build_dir(course):
    p = os.path.join(_work(course), "working_claude", "_build")
    if os.path.isdir(p):
        return p
    for old in (os.path.join(_work(course), "_build"), os.path.join(_work(course), "_factory", "_build")):
        if os.path.isdir(old):
            return old
    return p


def _deck_in(folder):
    for n in (os.path.join("presentation", "index.html"), "module.html", "index.html"):
        if folder and os.path.isfile(os.path.join(folder, n)):
            return os.path.join(folder, n)
    return None


def _numbered(course, n):
    """modules\\module01, else modules\\M01_<title>, else modules\\m1 - the folder fix.py also finds"""
    mods = os.path.join(_work(course), "modules")
    for pat, rx in (("module[0-9][0-9]", r"module(\d+)$"), ("M[0-9][0-9]_*", r"M(\d+)_"), ("m[0-9]*", r"m(\d+)$")):
        for d in sorted(glob.glob(os.path.join(mods, pat))):
            m = re.match(rx, os.path.basename(d))
            if m and os.path.isdir(d) and int(m.group(1)) == n:
                return d
    return None


def holds_final(folder):
    """the folder's deck is the final assessment's (its block is FINAL...) - the rule compile_module.module_folder finds
    the final by"""
    deck = _deck_in(folder)
    try:
        with open(deck, encoding="utf-8", errors="replace") as f:
            return 'data-block="FINAL' in f.read()
    except (OSError, TypeError):
        return False


def canon(course, module):
    """one name for one module -> "final" or its number. The final assessment is "final" however it is asked for: by name
    (the build: --module final) or by the number of the folder that holds it (the portal and fix.py go by folder)"""
    m = str(module).strip().lower()
    if m == "final":
        return "final"
    n = int(m)
    return "final" if holds_final(_numbered(course, n)) else n


def walk_dir(course, module):
    return os.path.join(build_dir(course), "walk", mid(canon(course, module)))


def review_file(course, module):
    return os.path.join(build_dir(course), "%s_walk_review.json" % mid(canon(course, module)))


def manifest_file(course, module):
    return os.path.join(walk_dir(course, module), "sheets", "manifest.json")


def module_dir(course, module):
    """the module's folder; for the final assessment the folder whose deck is the final's"""
    module = canon(course, module)
    if module != "final":
        return _numbered(course, module)
    mods = os.path.join(_work(course), "modules")
    found = [d for pat in ("module[0-9][0-9]", "M[0-9][0-9]_*", "m[0-9]*") for d in sorted(glob.glob(os.path.join(mods, pat)))
             if os.path.isdir(d)]
    return next((d for d in found if holds_final(d)), None)


def deck_file(course, module):
    return _deck_in(module_dir(course, module))


STAMP = re.compile(r"\b20\d\d-\d\d-\d\d[T ]\d\d:\d\d(?::\d\d)?(?:\.\d+)?(?:Z|[+-]\d\d:?\d\d)?")
COMMENT = re.compile(r"<!--.*?-->", re.S)


def deck_sha256(path):
    """the deck's markup alone, ignoring HTML comments and build timestamps - what a review signed before the fingerprints
    was signed for. Nothing new is signed with it"""
    with open(path, encoding="utf-8") as f:
        text = STAMP.sub("", COMMENT.sub("", f.read()))
    return hashlib.sha256(re.sub(r"\s+", " ", text).encode("utf-8")).hexdigest()


def _check_cache():
    if FACTORY_SCRIPTS not in sys.path:
        sys.path.insert(0, FACTORY_SCRIPTS)
    import check_cache
    return check_cache


def fingerprints(path):
    """-> (the whole deck's fingerprint, {slide id: fingerprint}, [slide ids in the deck's order]) - check_cache.py's
    fingerprint, the one the audits skip a clean slide by. A deck with no slide of its own id has the whole's alone"""
    cc = _check_cache()
    fps = cc.fingerprints(path, True, SALT)
    each, order = {}, []
    for name, fp in fps or []:
        m = re.match(r"slide \d+ \((.+)\)$", name)
        if m and m.group(1) not in each:
            each[m.group(1)] = fp
            order.append(m.group(1))
    if fps:
        return cc.sha(*[fp for _, fp in fps]), each, order
    page = cc.fingerprints(path, False, SALT)
    return (page[0][1] if page else cc.sha(cc.read(path))), each, order


def walk_stamp(deck):
    """what fit_gate.py writes into walk.json as the walk BEGINS: each slide's fingerprint and the whole deck's - so a
    picture of an older slide, or of a deck that changed while it was walked, is told from a picture of this one"""
    whole, each, _ = fingerprints(str(deck))
    return {"fingerprints": each, "deck": whole}


def _id(name):
    return re.sub(r"[^\w-]+", "_", str(name), flags=re.ASCII)


def task_pages(folder):
    """{page id: {"file": "tasks/x.html", "fingerprint": ...}} - every task page of a module folder as it is now: tasks\\
    and assessment\\, never an answer key (the pages review_sheets.mjs answers). The fingerprint is check_cache.py's for a
    page: the page and every file it loads"""
    cc, out = _check_cache(), {}
    for sub in ("tasks", "assessment"):
        for p in sorted(glob.glob(os.path.join(folder or "", sub, "*.html"))):
            base = os.path.basename(p)
            if "answer_key" in base.lower():
                continue
            pid = _id(os.path.splitext(base)[0])
            fp = cc.fingerprints(p, False, SALT)
            out[sub + "_" + pid if pid in out else pid] = {"file": sub + "/" + base,
                                                           "fingerprint": fp[0][1] if fp else cc.sha(SALT, cc.read(p))}
    return out


def page_named(pages, name):
    """the id of the task page a name stands for - its id, its file (tasks/x.html) or the file's name - or None"""
    f = str(name).replace("\\", "/")
    return name if name in pages else next((p for p, e in pages.items() if f in (e["file"], e["file"].split("/")[-1])), None)


def touches_tasks(pages, names):
    """the names (fix.py check --slides) reach a task page: none given, a page, or one of its questions"""
    return bool(pages) and (not names or any(page_named(pages, n) or str(n).split(".")[0] in pages for n in names))


def stamp_tasks(course, module):
    """-> the module's walk folder, with tasks_stamp.json in it: each task page's id and its fingerprint as its walk
    BEGINS. review_sheets.mjs --walk-dir copies them into tasks.json beside the pictures it takes, so a picture of an older
    page is told from a picture of this one"""
    wdir = walk_dir(course, module)
    save_json(os.path.join(wdir, "tasks_stamp.json"), {"pages": task_pages(module_dir(course, module))})
    return wdir


def walk_tasks(course, module):
    """-> (exit code, output). The module's task pages walked now: stamped, then answered and photographed by
    review_sheets.mjs (0 walked and every answer graded as expected, 1 an answer graded wrongly, 2 could not run). A page
    unchanged since it was walked clean keeps its pictures"""
    import subprocess
    folder = module_dir(course, module)
    if not folder:
        return 2, "walk_review: no module folder for %s" % mid(canon(course, module))
    wdir = stamp_tasks(course, module)
    r = subprocess.run(["node", os.path.join(HERE, "review_sheets.mjs"), folder, wdir, "--tasks-only", "--walk-dir=" + wdir],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.returncode, ((r.stdout or "") + (r.stderr or "")).strip()


def load_json(p, default=None):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def save_json(p, data):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, indent=1, ensure_ascii=False, sort_keys=True)


def figure_why(course, module):
    """{slide id: (why, why_text)} from the module's build sheet (kit figure, kit3d model or custom figure)"""
    name, out = mid(canon(course, module)), {}
    for d in (os.path.join(_work(course), "working_claude", "script"), os.path.join(_work(course), "script")):
        b = load_json(os.path.join(d, name + ".build.json"))
        if b:
            for sid, e in (b.get("screens") or {}).items():
                if isinstance(e, dict) and (e.get("why") or e.get("why_text")):
                    out[sid] = (e.get("why", ""), e.get("why_text", ""))
            break
    # the reason may live in the figure's own spec (figures/MNN/sNN.kit.json, .kit2d.json, .kit3d.json)
    for spec in sorted(glob.glob(os.path.join(_work(course), "working_claude", "figures", name, "*.kit*.json"))):
        sid = os.path.basename(spec).split(".")[0]
        s = load_json(spec) or {}
        if sid not in out and isinstance(s, dict) and (s.get("why") or s.get("why_text")):
            out[sid] = (s.get("why", ""), s.get("why_text", ""))
    return out


def is_open(v):
    """a slide's verdict still has a fail nobody accepted"""
    return bool(not v.get("ok") or v.get("fails")) and not v.get("accepted")


def who(name):
    return re.sub(r"[^a-z0-9]+", " ", str(name or "").lower()).strip()


def same(a, b):
    """two labels name the same agent: the same words, or one's words inside the other's ("build:1 (workflow builder)" and
    "build 1 workflow-builder agent")"""
    a, b = who(a), who(b)
    return bool(a and b and (" %s " % a in " %s " % b or " %s " % b in " %s " % a))


def _names(*given):
    out = []
    for g in given:
        for n in (g if isinstance(g, (list, tuple)) else [g]):
            n = str(n or "").strip()
            if n and not any(who(n) == who(x) for x in out):
                out.append(n)
    return out


class Deck(object):
    """a module as it is now: every slide's and every task page's fingerprint, the walk beside them and the review signed
    so far. A unit is what one verdict covers: a slide of the deck ("s03"), a question of a task page
    ("<page>.<question>"), a task page's last screen ("<page>.result") - or a task page never walked ("<page>", no picture)"""

    def __init__(self, course, module):
        self.module = canon(course, module)
        self.name = mid(self.module)
        self.path = deck_file(course, self.module)
        self.whole, self.each, self.ids = fingerprints(self.path) if self.path else ("", {}, [])
        wdir = walk_dir(course, self.module)
        self.walk = load_json(os.path.join(wdir, "walk.json"), {}) or {}
        self.stops = {}
        for s in self.walk.get("stops", []):
            self.stops.setdefault(s["slide"], []).append(s)
        self.walked = list(self.stops)                       # the deck's walked slides
        self.pages = task_pages(module_dir(course, self.module))
        self.tasks = (load_json(os.path.join(wdir, "tasks.json"), {}) or {}).get("pages") or {}
        self.tasks_whole = _check_cache().sha(*[p["fingerprint"] for p in self.pages.values()]) if self.pages else ""
        self.units, self.about = {}, {}                      # unit -> its page's id; unit -> the walked question, or None
        for pid in self.pages:
            page = self.tasks.get(pid) or {}
            if not page.get("questions"):
                self.units[pid] = pid
                continue
            for q in page["questions"]:
                u = "%s.%s" % (pid, _id(q.get("id", "")))
                self.units[u], self.about[u] = pid, q
                ask = q["ask"] = re.sub(r"^(\d{1,2})(?=[^\d\s.])", r"\1. ", q.get("ask", ""))   # the number's badge, then the words
                self.stops[u] = [{"slide": u, "k": k, "file": s["file"], "title": ask, "state": s.get("state", ""),
                                  "said": s.get("said", "")} for k, s in enumerate(q.get("states") or [], 1)]
            u = pid + ".result"
            self.units[u], self.about[u] = pid, None
            self.stops[u] = [{"slide": u, "k": k, "file": s["file"], "title": "the last screen", "state": s.get("state", ""),
                              "said": ""} for k, s in enumerate(page.get("result") or [], 1)]
        self.review = load_json(review_file(course, self.module), {}) or {}
        self.got = self.review.get("slides") or {}
        self._older = None

    def is_task(self, sid):
        return sid in self.units or ("." in sid and sid not in self.each and sid not in self.walked)

    def page_of(self, sid):
        return self.units.get(sid) or sid.split(".")[0]

    def gone(self, sid):
        """a verdict's slide, question or task page is no longer in the module"""
        return sid not in self.units if self.is_task(sid) else bool(self.ids and sid not in self.ids)

    def now(self, sid):
        if self.is_task(sid):
            return (self.pages.get(self.page_of(sid)) or {}).get("fingerprint", "")
        return self.each.get(sid, self.whole)

    def slides(self):
        """the units a review must cover: every slide of the deck (a deck with no slide of its own id: the walked ones)
        and every task page - its questions and its last screen once walked, the page itself until then"""
        return (self.ids or self.walked) + list(self.units)

    def expand(self, names):
        """a task page named by its id or its file (tasks/x.html, x.html) stands for all of its units"""
        out = []
        for n in names or []:
            p = page_named(self.pages, n)
            out += [u for u, q in self.units.items() if q == p] if p else [n]
        return out

    def short(self, units):
        """the units named for a person: a task page all of whose units are meant is named once"""
        out, done = [], set()
        for u in units:
            p = self.units.get(u)
            if p is None:
                out.append(u)
            elif p not in done and all(x in units for x, q in self.units.items() if q == p):
                done.add(p)
                out.append("task page " + p)
            elif p not in done:
                out.append(u)
        return out

    def walked_as(self, sid):
        """the unit's fingerprint as its walk began; None for a walk that does not say (an older factory's)"""
        if self.is_task(sid):
            return (self.tasks.get(self.page_of(sid)) or {}).get("fingerprint") or None
        fps = self.walk.get("fingerprints")
        return fps.get(sid, self.walk.get("deck")) if isinstance(fps, dict) else None

    def same_as_signed(self):
        """nothing the deck or a task page shows changed since the last sign"""
        if self.review.get("deck"):
            return self.review["deck"] == self.whole and self.review.get("tasks", self.tasks_whole) == self.tasks_whole
        return bool(self.got) and not self.stale(next(iter(self.got)))

    def stale(self, sid):
        """the unit changed after its verdict. A slide's verdict from before the fingerprints stands only for the deck it
        was signed for (its markup - the files around it were not recorded then)"""
        v = self.got[sid]
        if v.get("fingerprint") or self.is_task(sid):
            return v.get("fingerprint") != self.now(sid)
        if self._older is None:
            self._older = deck_sha256(self.path)
        return self.review.get("deck_sha256") != self._older

    def to_review(self):
        """the slides with no verdict for what they show now: never reviewed, changed since, or reopened by the operator"""
        return [s for s in self.slides() if s not in self.got or self.stale(s) or self.got[s].get("reopened")]

    def open(self, slides=None):
        slides = self.expand(slides) if slides else None
        return [s for s in self.slides() if s in self.got and is_open(self.got[s]) and (not slides or s in slides)]


def stops_by_slide(course, module):
    return Deck(course, module).stops


def to_review(course, module):
    return Deck(course, module).to_review()


def contact_sheet(stops, wdir, out_path, cols=3):
    """all of a slide's stops in a numbered grid -> out_path (needs Pillow). The number - and, for a task page, what the
    picture shows - stands in a band above its picture: on the picture it hid the screen's own first words"""
    from PIL import Image, ImageDraw, ImageFont
    ims = []
    for s in stops:
        p = os.path.join(wdir, s["file"])
        if os.path.isfile(p):
            ims.append((s["k"], re.split(r" \(| - ", s.get("state") or "")[0], Image.open(p).convert("RGB")))
    if not ims:
        return False
    w, h = max(i.width for _, _, i in ims), max(i.height for _, _, i in ims)
    cols = min(cols, len(ims))
    rows = (len(ims) + cols - 1) // cols
    pad, band = 8, 30
    sheet = Image.new("RGB", (cols * (w + pad) + pad, rows * (h + band + pad) + pad), (255, 255, 255))
    try:
        font, words = ImageFont.load_default(size=22), ImageFont.load_default(size=17)
    except TypeError:
        font = words = ImageFont.load_default()
    d = ImageDraw.Draw(sheet)
    for n, (k, state, im) in enumerate(ims):
        x, y = pad + (n % cols) * (w + pad), pad + (n // cols) * (h + band + pad)
        d.rectangle([x, y, x + 34, y + band - 1], fill=(10, 36, 99))
        d.text((x + 8, y + 3), str(k), fill=(255, 255, 255), font=font)
        while state and d.textlength(state, font=words) > w - 50:
            state = state[:-1]
        if state:
            d.text((x + 44, y + 5), state, fill=(10, 36, 99), font=words)
        y += band
        sheet.paste(im, (x, y))
        d.rectangle([x, y, x + im.width - 1, y + im.height - 1], outline=(180, 180, 180))
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    sheet.save(out_path)
    return True


BUILD_AGAIN = "build again (build_module.py, or fit_gate.py --walk-dir), then prepare"


def prepare(course, module, slides=None, stale_only=False):
    """-> (exit code, [lines]). Makes the sheets, their manifest and the brief for every walked slide, only `slides`, or
    (stale_only) only the slides with no verdict for what they show now"""
    d = Deck(course, module)
    wdir = walk_dir(course, d.module)
    by = d.stops
    if not d.walked:
        return 2, ["walk_review: no walk for %s in %s - run the build (or fit_gate.py --walk-dir) first" % (d.name, wdir)]
    try:
        import PIL  # noqa: F401
    except ImportError:
        return 2, ["walk_review: Pillow is not installed - python -m pip install pillow"]
    if not d.path:
        return 2, ["walk_review: no deck for %s" % d.name]
    if not isinstance(d.walk.get("fingerprints"), dict):
        return 2, ["walk_review: the walk of %s does not say which deck it was made of (an older factory made it) - %s"
                   % (d.name, BUILD_AGAIN)]
    want = d.expand([x.strip() for x in slides if x.strip()]) if slides else None
    ids = [s for s in by if not want or s in want]
    missing = [s for s in (want or []) if s not in by]
    if not ids:
        return 2, ["walk_review: none of %s was walked" % ", ".join(d.short(want or []))]
    due = d.to_review()
    if stale_only:
        ids = [s for s in ids if s in due]
    # a slide of the deck or a task page with no picture: added after the walk, or one the walk did not reach
    lost = [s for s in (due if stale_only else d.slides()) if s not in by and (not want or s in want)]
    old = [s for s in ids if d.walked_as(s) != d.now(s)]
    if old:
        return 2, ["walk_review: %s was walked before the deck changed (%s) - the pictures are of an older slide; %s"
                   % (d.name, ", ".join(d.short(old)), BUILD_AGAIN)]
    gap = ["walk_review: the walk of %s has no picture of %s - no reviewer can pass a slide it was not shown; %s"
           % (d.name, ", ".join(d.short(lost)), BUILD_AGAIN)] if lost else []
    if not ids:
        return (2, gap) if lost else (0, ["walk_review: nothing to review for %s - every slide%s has a verdict for "
                                          "what it shows now" % (d.name, " and task-page screen" if d.units else "")])
    why = figure_why(course, d.module)
    sheets = {}
    for sid in ids:
        out = os.path.join(wdir, "sheets", sid + ".png")
        if contact_sheet(by[sid], wdir, out, cols=2 if d.is_task(sid) else 3):
            sheets[sid] = out
    # the manifest: what each sheet is a picture of - sign records THIS, never what the deck is when the answer comes back
    seen = (load_json(manifest_file(course, d.module), {}) or {}).get("slides") or {}
    seen = {s: fp for s, fp in seen.items() if fp == d.walked_as(s)}
    seen.update({s: d.walked_as(s) for s in sheets})
    save_json(manifest_file(course, d.module), {"slides": seen})
    order = [s for s in by if s in sheets and not d.is_task(s)]
    asked = [s for s in by if s in sheets and d.is_task(s)]
    lines = ["# Walk review - %s" % d.name, ""]
    if order:
        lines += ["Look at each contact sheet below: every stop of the slide, numbered, as the trainee sees it at 1280x800 "
                  "(Start, then each Next). Judge the whole set of a batch in one look. Judge by this RUBRIC - one slide, each point:", ""]
        lines += ["%d. %s" % (i, r) for i, r in enumerate(RUBRIC, 1)]
        lines += [""]
    if asked:
        lines += ["TASK PAGES - the trainee's own pages on the tablet, answered like a trainee. A question's contact sheet "
                  "(\"<page>.<question>\") has numbered pictures: 1 as asked at 1280 x 800, 2 as asked at 1024 x 768, 3 answered "
                  "WRONG and checked (the pink dashes outline every tap area / drop zone - the review's overlay, not the page's), "
                  "4 answered RIGHT and checked. A blind page (the final assessment) records an answer and goes straight on, "
                  "with no verdict and no feedback: its pictures 3 and 4 show the answer in place before the press that "
                  "records it, and point 3 has nothing to judge there. A page's last screen (\"<page>.result\") is shown after "
                  "a whole run answered wrong and one answered right, once a group of trainees - and scrolled to its end "
                  "where it is longer than the screen (a list longer than two screens: its start and its end). The band above a picture says what it shows. Judge by this TASK "
                  "RUBRIC - one question, each "
                  "point (points 6 and 7 for a last screen):", ""]
        lines += ["%d. %s" % (i, r) for i, r in enumerate(TASK_RUBRIC, 1)]
        lines += [""]
    lines += ["Return ONLY this JSON (every slide of the batch and no other; \"ok\" is true or false, never a word in "
              "quotes; \"fails\" are short, concrete sentences naming the stop number):", "",
              "    {\"reviewed_by\": \"<your name / model>\", \"slides\": {\"s03\": {\"ok\": true, \"fails\": []},",
              "                                                     \"s07\": {\"ok\": false, \"fails\": [\"stop 3: the chart is still an empty axis\"]}}}",
              ""]
    if asked:
        lines += ["A task-page question or last screen goes into \"slides\" under its own name, exactly as its heading has "
                  "it (\"%s\"); its fails name the picture number." % asked[0], ""]
    lines += ["You did not build or fix this module: a builder never signs its own walk (walk_review.py sign --built-by refuses it)."]
    batches = [order[b:b + BATCH] for b in range(0, len(order), BATCH)] + [asked[b:b + BATCH] for b in range(0, len(asked), BATCH)]
    listed = False
    for n, batch in enumerate(batches, 1):
        if d.is_task(batch[0]) and not listed:                 # each page's questions in order, once: point 3 needs them
            listed = True
            lines += ["", "## The task pages of this review", ""]
            for pid in dict.fromkeys(d.page_of(s) for s in asked):
                page = d.tasks.get(pid) or {}
                lines += ["- `%s` (%s%s): %s" % (page.get("file", pid), pid, ", a blind page" if page.get("blind") else "", "; ".join(
                    "%s%s %s" % (q.get("id", ""), " [group %s]" % q["group"] if q.get("group") else "", q.get("ask", ""))
                    for q in page.get("questions") or []))]
        lines += ["", "## Batch %d - %s" % (n, ", ".join(batch)), ""]
        for sid in batch:
            lines += ["### %s - %s" % (sid, by[sid][0].get("title", "")), "", "Sheet: `%s`" % sheets[sid]]
            was = (d.got.get(sid) or {}).get("fails") or []
            if d.is_task(sid):
                q, page = d.about.get(sid), d.tasks.get(d.page_of(sid)) or {}
                lines += ["Task page: %s - %s" % (page.get("file", ""), "question %s (%s)%s" % (
                    q.get("id", ""), q.get("mech", "") or "?", ", shown to group %s only" % q["group"] if q.get("group") else "")
                    if q else "its last screen%s" % (" (a blind page)" if page.get("blind") else ""))]
            else:
                w = why.get(sid)
                lines += ["Figure why: %s - %s" % w if w else "Figure why: (none declared - a slide with no drawing, or the build sheet has no why)"]
            if was:
                lines += ["Failed in the last review - say for each whether it is fixed now: %s" % " | ".join(was)]
            for s in by[sid]:
                if d.is_task(sid):
                    lines.append("- picture %d: %s%s" % (s["k"], s.get("state", ""),
                                                        " - the screen says: \"%s\"" % s["said"][:160] if s.get("said") else ""))
                    continue
                bits = ["lit: " + " / ".join(s.get("lit") or []) if s.get("lit") else "lit: -"]
                if s.get("ask"):
                    bits.append("question on screen: " + " / ".join(s["ask"])[:120])
                if s.get("reveal"):
                    bits.append("answer on screen: " + " / ".join(s["reveal"])[:120])
                lines.append("- stop %d: %s" % (s["k"], "; ".join(bits)))
            lines.append("")
    if missing or lost:
        lines += ["", "(not walked: %s)" % ", ".join(d.short(missing + [s for s in lost if s not in missing]))]
    path = os.path.join(wdir, "review_brief.md")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    return 0, ["walk_review: %d contact sheet(s) in %s%s%s" % (
                   len(sheets), os.path.join(wdir, "sheets"),
                   " (%d slide(s), %d task-page question(s) and last screen(s))" % (len(order), len(asked)) if asked else "",
                   " - only the slides not reviewed as they are now: %s" % ", ".join(d.short(order + asked)) if stale_only else ""),
               "walk_review: the brief for the reviewer: %s (%d batch(es) of up to %d slides)" % (path, len(batches), BATCH)] + gap


def choices(module):
    """what the operator can do with fails left after the last round"""
    return ("accept them: walk_review.py accept <course> --module %s --by \"<operator>\" --why \"<why it can ship>\"; or have "
            "them fixed and start again: walk_review.py reopen <course> --module %s --by \"<operator>\"" % (module, module))


def _fails(d, slides=None):
    return ["%s - %s" % (s, f) for s in d.open(slides) for f in (d.got[s].get("fails") or ["not ok"])]


def open_fails(course, module, slides=None):
    """["s04 - stop 3: the chart is still an empty axis", ...] - every fail nobody accepted, with its slide and stop"""
    return _fails(Deck(course, module), slides)


def accepted(course, module):
    """["s04 - stop 3: ... - accepted by <operator>, <date> (<how>): <why>", ...] - every fail the operator let stand on a
    slide as it is now: what an upload shows before the course leaves"""
    d = Deck(course, module)
    out = []
    for s in d.slides():
        a = (d.got.get(s) or {}).get("accepted")
        if a and not d.stale(s):
            out += ["%s - %s - accepted by %s, %s%s: %s" % (s, f, a.get("by", "?"), a.get("date", "?"),
                                                           " (%s)" % a["how"] if a.get("how") else "", a.get("why", ""))
                    for f in (a.get("fails") or ["not ok"])]
    return out


def _verdict(sid, r):
    """-> why the reviewer's answer for a slide cannot be signed, or '' """
    if not isinstance(r, dict) or "ok" not in r:
        return "slide %s has no \"ok\" in the reviewer JSON" % sid
    if not isinstance(r["ok"], bool):
        return "slide %s: \"ok\" must be true or false, not %s" % (sid, json.dumps(r["ok"]))
    f = r.get("fails")
    if f is not None and not (isinstance(f, list) and all(isinstance(x, str) for x in f)):
        return "slide %s: \"fails\" must be a list of sentences" % sid
    return ""


def sign(course, module, review_path, built_by=None):
    """-> (exit code, [lines]). Writes MNN_walk_review.json from the reviewer's JSON: 0 signed and clean, 1 signed with open
    fails, 2 refused (bad input, a builder's or fixer's own signature, a slide the reviewer was not shown as it is now, a
    verdict that already stands), 3 refused (a third round). built_by: one name or several - who built and who fixed"""
    d = Deck(course, module)
    if not d.path:
        return 2, ["walk_review: no deck for %s" % d.name]
    rv = load_json(review_path)
    if not isinstance(rv, dict) or not isinstance(rv.get("slides"), dict) or not rv["slides"]:
        return 2, ["walk_review: %s is not reviewer JSON ({\"reviewed_by\", \"slides\": {...}})" % review_path]
    by = str(rv.get("reviewed_by") or "").strip()
    if not by:
        return 2, ["walk_review: the reviewer JSON has no \"reviewed_by\""]
    prior = d.review
    builders = _names(prior.get("builders") or prior.get("built_by"), built_by, rv.get("built_by"))
    if not builders:
        return 2, ["walk_review: say who built %s - sign ... --built-by \"<who built the module>\" (the reviewer is someone else)" % d.name]
    own = [b for b in builders if same(by, b)]
    if own:
        return 2, ["walk_review: \"%s\" built or fixed %s (\"%s\") - a builder never signs its own walk review; a reviewer "
                   "that did not build or fix it looks at the sheets and signs" % (by, d.name, own[0])]
    for sid, r in rv["slides"].items():
        no = _verdict(sid, r)
        if no:
            return 2, ["walk_review: " + no]
    seen = (load_json(manifest_file(course, d.module), {}) or {}).get("slides") or {}
    unseen = [s for s in rv["slides"] if s not in seen]
    if unseen:
        return 2, ["walk_review: no contact sheet was made for %s - a reviewer signs only what prepare showed it: "
                   "walk_review.py prepare (--stale), look at the sheets, then sign" % ", ".join(d.short(unseen))]
    moved = [s for s in rv["slides"] if seen[s] != d.walked_as(s) or seen[s] != d.now(s)]
    if moved:
        return 2, ["walk_review: %s changed after its contact sheet was made (%s) - the reviewer saw an older slide; run "
                   "prepare --stale again (it says so when the module must be built first) and review the sheets it makes"
                   % (d.name, ", ".join(d.short(moved)))]
    was = d.got
    stands = [s for s in rv["slides"] if s in was and not d.stale(s) and not was[s].get("reopened")]
    new = [s for s in rv["slides"] if s not in stands]
    if not new:
        return 2, ["walk_review: %s already has a verdict for what %s - a verdict is replaced only once the slide changes "
                   "(fix, build, prepare --stale) or the operator reopens it (walk_review.py reopen)"
                   % (", ".join(stands), "it shows now" if len(stands) == 1 else "they show now")]
    # the round counts every fail still open - also one on a slide renamed or removed since
    was_open = sorted(s for s, v in was.items() if is_open(v))
    if not was:
        rnd = 1
    elif d.same_as_signed():                                 # more batches of the same review
        rnd = max(1, int(prior.get("rounds", 1)))
    elif not was_open:                                       # the last review ended clean: a new change, a new first round
        rnd = 1
    else:
        rnd = int(prior.get("rounds", 1)) + 1
    if rnd > MAX_ROUNDS:
        return 3, ["walk_review: %s has had its %d walk rounds - no third. Still failing: %s" % (
            d.name, MAX_ROUNDS, ", ".join(s if s in d.slides() else s + " (no longer in the deck)" for s in was_open)),
            "  The operator's choice - %s" % choices(d.module)]
    today = date.today().isoformat()
    slides = {}
    for sid in new:
        r = rv["slides"][sid]
        fails = [x for x in (r.get("fails") or []) if x.strip()]
        slides[sid] = {"ok": r["ok"] and not fails, "fails": fails or ([] if r["ok"] else ["(the reviewer failed this slide without saying why)"]),
                       "fingerprint": seen[sid], "reviewed_by": by, "date": today, "round": rnd}
    kept, history = {}, list(prior.get("history") or [])
    for k, v in was.items():
        if k in slides:
            continue
        if d.gone(k):                                        # its slide or question is gone: counted above, then out of the way
            history.append(dict(v, slide=k, left=today, why="no longer in the deck"))
        else:
            # a verdict from before the fingerprints: it stands for the deck it was signed for, and for no other
            kept[k] = v if v.get("fingerprint") else dict(v, fingerprint="signed-for-an-older-deck" if d.stale(k) else d.now(k))
    out = dict({k: v for k, v in prior.items() if k == "reopened"}, deck=d.whole, tasks=d.tasks_whole, reviewed_by=by,
               built_by=builders[0], builders=builders, date=today, rounds=rnd, slides=dict(kept, **slides))
    if history:
        out["history"] = history
    save_json(review_file(course, d.module), out)
    d = Deck(course, d.module)
    bad = d.open()
    head = "walk_review: signed %s by %s (round %d of %d; built by %s) - %s reviewed now%s" % (
        d.name, by, rnd, MAX_ROUNDS, ", ".join(builders), count(d, slides),
        "; %s kept the verdict it has (unchanged since)" % ", ".join(stands) if stands else "")
    if not bad:
        return 0, [head]
    if rnd < MAX_ROUNDS:
        head += "; OPEN FAILS on %s - fix them, build, then prepare --stale and ONE more review of what changed" % ", ".join(bad)
        return 1, [head] + ["  " + x for x in _fails(d)]
    head += "; OPEN FAILS on %s - that was the last round" % ", ".join(bad)
    return 1, [head] + ["  " + x for x in _fails(d)] + ["  The operator's choice - %s" % choices(d.module)]


def verify(course, module, slides=None):
    """-> (ok, "missing" | "stale" | "failing" | "incomplete" | "", message). Every slide of the deck needs a verdict for
    what it shows now - walked or not; `slides`: only these must be covered"""
    d = Deck(course, module)
    if not d.review:
        return False, "missing", "walk review missing for %s - walk the module, then run the reviewer (walk_review.py prepare / sign)" % d.name
    if not d.path:
        return False, "missing", "no deck for %s" % d.name
    got = d.got
    slides = d.expand(slides) if slides else None
    need = [s for s in d.slides() if not slides or s in slides]
    judged = [s for s in need if s in got]
    stale = [s for s in judged if d.stale(s)]
    if stale:
        return False, "stale", ("walk review stale for %s - %d of %d slide(s)%s changed after the review: %s; build, then "
                                "walk_review.py prepare --stale shows the reviewer only those%s" % (
                                    d.name, len(stale), len(judged), " and task-page screen(s)" if d.units else "",
                                    ", ".join(d.short(stale)),
                                    " (the two rounds are used: the operator reopens it first - walk_review.py reopen)"
                                    if int(d.review.get("rounds", 1)) >= MAX_ROUNDS and d.open() else ""))
    gaps = [s for s in need if s not in got]
    if gaps or not need:
        return False, "incomplete", "walk review incomplete for %s - not reviewed: %s%s" % (
            d.name, ", ".join(d.short(gaps)) or "any slide", "" if all(s in d.stops for s in gaps) and need
            else " (the walk has no picture of every one: build, then walk_review.py prepare --stale)")
    bad = [s for s in judged if is_open(got[s])]
    if bad:
        last = int(d.review.get("rounds", 1)) >= MAX_ROUNDS
        return False, "failing", "walk review failing for %s - open fails on %s (%s) - round %s of %d%s" % (
            d.name, ", ".join(bad), "; ".join(got[bad[0]].get("fails") or ["not ok"])[:160], max(1, int(d.review.get("rounds", 1))), MAX_ROUNDS,
            ", no third: the operator accepts what is left or reopens it (walk_review.py accept / reopen)" if last
            else ": fix them, build, and one more review of what changed")
    let = sorted({(got[s].get("accepted") or {}).get("by", "?") for s in judged if got[s].get("accepted")})
    n = [s for s in judged if got[s].get("accepted")]
    return True, "", "walk review passed for %s (%s, %s%s)" % (
        d.name, d.review.get("reviewed_by", "?"), d.review.get("date", "?"),
        "; fails on %s accepted by %s" % (count(d, n), ", ".join(let)) if n else "")


def count(d, units):
    """how many of what, for a person: "3 slide(s)", "2 task-page question(s) and last screen(s)", or both"""
    asked = sum(1 for u in units if u in d.units)
    return " and ".join(x for x in ("%d slide(s)" % (len(units) - asked) if len(units) > asked or not asked else "",
                                    "%d task-page question(s) and last screen(s)" % asked if asked else "") if x)


def _operator(rv, by):
    """-> why this name cannot act as the operator, or '' """
    if not who(by):
        return "say who decides - --by \"<operator>\""
    names = _names(rv.get("builders"), rv.get("built_by"), rv.get("reviewed_by"),
                   [v.get("reviewed_by") for v in (rv.get("slides") or {}).values()])
    if any(same(by, n) for n in names):
        return "\"%s\" built, fixed or reviewed this module - the accept is the operator's, never the builder's or the reviewer's" % by
    return ""


def accept(course, module, by, why, slides=None, how=""):
    """-> (exit code, [lines]). The operator lets the open fails (of `slides`, or all) stand - recorded on each slide.
    how: how the command was run (typed in a terminal, or run by a session) - recorded beside the name"""
    d = Deck(course, module)
    rv = d.review
    if not rv or not d.path:
        return 2, ["walk_review: no walk review to accept for %s" % d.name]
    no = _operator(rv, by)
    if no:
        return 2, ["walk_review: " + no]
    if not str(why or "").strip():
        return 2, ["walk_review: say why it can ship - --why \"...\" (it is recorded beside the fail)"]
    todo = d.open(slides)
    if not todo:
        return 2, ["walk_review: no open fail to accept for %s%s" % (d.name, " on %s" % ", ".join(slides) if slides else "")]
    changed = [s for s in todo if d.stale(s)]
    if changed:
        return 2, ["walk_review: %s changed after the review (%s) - an accept is for what the reviewer saw; have it reviewed "
                   "first (build, prepare --stale)%s" % (
                       d.name, ", ".join(changed), " - its two rounds are used, so reopen it for that: walk_review.py reopen "
                       "<course> --module %s --by \"<operator>\"" % d.module if int(rv.get("rounds", 1)) >= MAX_ROUNDS else "")]
    lines = []
    for s in todo:
        d.got[s]["accepted"] = dict({"by": str(by).strip(), "date": date.today().isoformat(), "why": str(why).strip(),
                                     "fails": list(d.got[s].get("fails") or [])}, **({"how": how} if how else {}))
        lines += ["  %s - %s" % (s, f) for f in d.got[s]["accepted"]["fails"] or ["not ok"]]
    save_json(review_file(course, d.module), rv)
    return 0, ["walk_review: %s - %s accepted %s as they are (%s): %s" % (d.name, str(by).strip(), count(d, todo), str(why).strip(), ", ".join(todo))] + lines


def reopen(course, module, by, how=""):
    """-> (exit code, [lines]). The operator has the leftovers fixed after all: the rounds start again, and the open
    slides may be reviewed again as they are"""
    d = Deck(course, module)
    rv = d.review
    if not rv:
        return 2, ["walk_review: no walk review to reopen for %s" % d.name]
    no = _operator(rv, by)
    if no:
        return 2, ["walk_review: " + no]
    today, again = date.today().isoformat(), []
    for s, v in list(d.got.items()):
        if not is_open(v):
            continue
        if d.gone(s):
            rv.setdefault("history", []).append(dict(d.got.pop(s), slide=s, left=today, why="no longer in the deck"))
        else:
            v["reopened"] = True
            again.append(s)
    rv["rounds"] = 0
    rv.setdefault("reopened", []).append(dict({"by": str(by).strip(), "date": today, "slides": again}, **({"how": how} if how else {})))
    save_json(review_file(course, d.module), rv)
    return 0, ["walk_review: %s reopened by %s - fix what is open, build, prepare --stale, and the rounds start again (%d at most)" % (
        d.name, str(by).strip(), MAX_ROUNDS)]


AGENT_ENV = ("AI_AGENT", "CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT")


def how_run(env=None, tty=None):
    """how this command was run, for the record of an accept or a reopen: an agent's shell says so in its environment
    (and may still have a terminal for its input), a script has no terminal"""
    env = os.environ if env is None else env
    tty = bool(sys.stdin and sys.stdin.isatty()) if tty is None else tty
    return "typed in a terminal" if tty and not any(env.get(k) for k in AGENT_ENV) else "run by a session or a script"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("cmd", choices=("prepare", "sign", "verify", "accept", "reopen"))
    ap.add_argument("course")
    ap.add_argument("--module", required=True)
    ap.add_argument("--slides")
    ap.add_argument("--stale", action="store_true", help="prepare: only the slides with no verdict for what they show now")
    ap.add_argument("--review")
    ap.add_argument("--built-by", action="append", help="sign: who built the module, and again for each one who fixed it - "
                                                         "the reviewer must be someone else")
    ap.add_argument("--by", help="accept / reopen: the operator")
    ap.add_argument("--why", help="accept: why the fails can ship")
    o = ap.parse_args(argv)
    slides = [x for x in (o.slides or "").split(",") if x.strip()] or None
    # the accept and the reopen are the operator's own: the factory cannot tell who runs them, so it records how
    how = how_run()
    if o.cmd == "prepare":
        rc, lines = prepare(o.course, o.module, slides, o.stale)
    elif o.cmd == "sign":
        if not o.review:
            print("walk_review: sign needs --review <reviewer.json>")
            return 2
        rc, lines = sign(o.course, o.module, o.review, o.built_by)
    elif o.cmd == "accept":
        rc, lines = accept(o.course, o.module, o.by, o.why, slides, how)
    elif o.cmd == "reopen":
        rc, lines = reopen(o.course, o.module, o.by, how)
    else:
        ok, kind, msg = verify(o.course, o.module, slides)
        print(("OK: " if ok else "NOT DONE: ") + msg)
        if kind == "failing":
            print("\n".join("  " + x for x in open_fails(o.course, o.module, slides)))
        return 0 if ok else 1
    print("\n".join(lines))
    return rc


if __name__ == "__main__":
    sys.exit(main())
