#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Build a module's presentation from its approved content script - the words are typed once (L29).

    compile_module.py <course folder> --module 1                 build modules\\module01\\presentation\\index.html
    compile_module.py <course folder> --module 1 --init-build    write a starter build sheet, make the module folder with the factory's style files, build nothing
    compile_module.py <course folder> --module 1 --draft         build from a script that is not approved yet (preview only)
    compile_module.py <course folder> --module 1 --force         overwrite a deck that was changed by hand
    compile_module.py <course folder> --module 1 --only plan     build only instructor\\M01_PLAN.html (2.47.0: the module's plan,
                                                                 from the same approved script - compile\\scripts\\module_plan.py)

WHY THIS EXISTS
Until 2.25 every module was written twice: the content script the operator approves, then the same words
typed again by hand as HTML, and check_script_match.py proving afterwards that nothing drifted. Each module
also grew its own style file for slide text and task screens, so modules slowly stopped looking alike
(docs/PROPOSAL_SCRIPT_COMPILER.md). This builds the deck from the approved script with the factory's own
frame (course-module-ui/templates/gb_shell.html), style files and deck engine, so every module of every
course has the same slide layouts, and a wording fix is made once - in the script - and built again.

TWO FILES IN, ONE PAGE OUT
  working_claude\\script\\M01.json        the approved words - never touched by this tool
  working_claude\\script\\M01.build.json  how it is delivered: the picture file of each slide, a layout
                                         choice where the script's own is not enough, the module's own
                                         drawing styles and figure scripts. Not content, so changing it
                                         never undoes the operator's approval.

    {"module": 1,
     "landing_rule": "Basic training · IGF Code",
     "foot": "IGF SHIP DESIGN",                          the footer's short title (default: the title, whole words, 40 letters)
     "styles": ["assets/m01_figures.css"],              drawing colours only (proposal §3a)
     "scripts": ["assets/vendor/three.min.js", "assets/js/m01_hull3d.js"],
     "inline": ["m01_defs.svg"],                         put at the top of the page (shared drawing parts)
     "screens": {
       "s01": {"figure": "assets/img/m01_ship.jpg", "alt": "..."},
       "s04": {"figure": "m01_s04.html", "composition": "stage", "dark": true},
       "p01": {"link_hint": "Work in pairs at the simulator"}}}

  A drawing (.svg, or an .html fragment with its own markup) is SOURCE: it lives in
  working_claude\\figures\\M01\\ and is placed into the slide as it is - written as the deck sees it, so its
  links start ../assets/. An .html fragment is never put in the module folder: the classroom would take it
  for a page and send it to the tablets. A picture (.jpg .png .webp .gif) is SHIPPED: it is in the module
  folder and becomes an <img>; its credit line comes from assets\\img\\_photo_meta.json. Styles and scripts
  are shipped too (module folder). Only what a built page shows ships (2.52.0): after the build a picture no page,
  style or script names goes with its record to assets\\img\\_unused\\ (the classroom skips a _ folder), and comes back
  when the build sheet names it again; each shown picture's "used_in" is written from where the pages show it.
  A figure script that animates registers its per-slide hooks as
      window.GB_HOOKS = window.GB_HOOKS || {};  GB_HOOKS.s05 = {enter: fn, leave: fn};
  and finds the slide's own lines by number: document.querySelector('#s04 [data-i="2"]').
  A figure named *.kit.json is a FIGURE KIT spec (course-visuals/kit/SPEC.md): parts and steps, no drawing.
  It goes into the page as data, with the deck's step buttons; kit.js and kit.css are shipped with the
  module like gb_deck.js, and assets/kit_parts.js too when the course has added parts of its own.

EVERY SLIDE IS ONE OF THE OWNER'S LAYOUT TEMPLATES (L61, 2.52.0)
  course-module-ui/knowledge/layout-templates.json names thirteen templates (explain-figure, figure-stage, photo-explain,
  compare-two, procedure, task-launch, recap, opening, long-explanation, three-content-blocks, reference-table,
  reading-with-figure, content-in-parts). Each slide carries data-template="<id>.v1" and data-variant, chosen from the
  layout below - or asked for in the build sheet: "template": "reference-table", "variant": "figure-left",
  "split": 0.55 (text share, 0.5-0.6), "blocks": [[1, 3], [4, 6]] (compare-two, three-content-blocks), "parts":
  [[1, 4], [5, 9]] (content-in-parts), "figure_b" (compare-two's second picture). An unknown or unsuitable template is
  a problem with the slide's id. gb_layouts.css gives every template the owner's look, in the brandbook's colours,
  with the official logo. The owner's rules are checked here: a dense slide (more than 60 words) always has a picture
  beside it; never three teaching slides in a row without a teaching picture; words that need more room than a
  figure slide holds (more than 135) go into readable parts - never cut, never smaller type.
  L62 (2.53.0): two slides next to each other never look the same - a slide's look is its template, its variant and its
  ground (light, or dark / photo); when a slide would repeat the slide before it, it is built another way that holds
  its words and picture (the picture on the other side, the other ground, a photograph framed on the dark ground, a
  drawing on the stage), avoiding the slide before that one too. A photograph smaller than 1600 px on its long side is
  enlarged in the module (Lanczos, a light sharpening) so a projector never shows blocks of pixels; the original is
  kept in working_claude/photo_originals/M01/, and one under 800 px is still listed - find a larger one.

HOW A SLIDE IS LAID OUT (the same for every module)
  layout visual_full  + a photograph   -> .slide.photo, the photo is the screen, the words over it
  layout visual_full  + a drawing      -> composition "stage"
  layout split                         -> "two-col": the words left, the picture right
  layout visual_wide                   -> "stage" when the words are short (<= 45), else "two-col wide-right"
  no layout                            -> ordinary flow
  "composition" in the build sheet overrides: opener, flow, two-col, wide-left, wide-right, stage
  The words: one line -> a statement; several lines -> the first is the statement and the rest its
  support list; a line starting with "• " is a list item, and the other lines are lead paragraphs.
  Over a photograph there is no list: a "• " line is a .lead.sub (the list's square marker) and the
  lines it hangs under are .lead.head (bold) - the same heading-and-points look as a text slide.
  Lines the script numbers itself, 1, 2, 3 ... in order, are one numbered list (ol.support.seq; over a photo
  .lead.sub.step): every step the same size, its own number the marker.
  A task slide -> "activity": the set's code, the title, its lines; data-task-href to the set's page
  (tasks\\sc1_<title>.html, assessment\\check.html, assessment\\final.html). A room activity -> no page,
  data-link-hint from the build sheet or its first line.

THE OUTPUT IS GENERATED - NEVER EDIT IT BY HAND
Its first comment says so. A record of what was written is kept in working_claude\\modules\\module01\\
compiled.json, saved with each file as it is written (so a crash part-way never leaves the compiler's own file looking
hand-changed); if the deck was changed by hand since, the build stops instead of overwriting the change
(--force overwrites; a hand-built deck from before the compiler is also protected this way).

Exit 0 built; 1 built, but with problems to fix before it is shown (a missing picture, a draft script);
2 nothing built (no script, script not approved, a hand-changed deck, bad input).
"""
from __future__ import annotations

import argparse
import hashlib
import html
import io
import json
import os
import re
import shutil
import sys
import unicodedata

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(os.path.dirname(HERE))                 # course-factory
SKILLS = os.path.dirname(SKILL)
PLUGIN = os.path.dirname(SKILLS)
sys.path.insert(0, os.path.join(SKILL, "scripts"))
if HERE not in sys.path:                                       # 2.49.1 - `python -I` leaves the script's own folder off
    sys.path.insert(0, HERE)                                   # sys.path: task_pages, module_plan, answer_key, label_layout
import content_script as cs  # noqa: E402
import workspace  # noqa: E402

SHELL = os.path.join(SKILLS, "course-module-ui", "templates", "gb_shell.html")
STYLES = ("gb_tokens.css", "gb_shell.css", "gb_compose.css", "gb_layouts.css")   # gb_layouts.css: the owner's templates (L61)
IMAGES = (".jpg", ".jpeg", ".png", ".webp", ".gif")
KIT_SPEC = ".kit.json"                       # a figure made from the figure kit (course-visuals/kit)
KIT_FILES = ("kit.css", "kit.js")             # shipped with the module by design_system.py, like gb_deck.js
KIT_PARTS = "assets/kit_parts.js"             # parts this course added to the kit, until they are merged
PHOTO_FILES = ("gb_zoom.css", "gb_zoom.js")    # every picture opens full screen with its record (L51, L56), like gb_deck.js
COMPOSITIONS = ("opener", "flow", "two-col", "wide-left", "wide-right", "stage")
STAGE_MAX_WORDS = 45
STATEMENT_MAX_WORDS = 22
# 2.49.2 (F4) - how many words a column keeps room for when a photograph sits under them (inset), at 1280 x 800. Measured on IGF:
# M01 s03 (58 words) and M04 s02 (82, audit_deck clean) fitted; M07 s08 (95), s12 (101) and M09 s06 (91) spilled
# 105 / 92 / 79 px off the slide - so the line is drawn between 82 and 91
INSET_MAX_WORDS = {"two-col": 86, "wide-left": 86, "wide-right": 86, "photo-split": 96}   # 2.63.0: set from the budgets below
CHECK_PAGES = {"MC": "../assessment/check.html", "FA": "../assessment/final.html"}   # the module check and the (single) final
LAYOUTS = json.load(io.open(os.path.join(SKILLS, "course-module-ui", "knowledge", "layout-templates.json"), encoding="utf-8"))
TEMPLATES = LAYOUTS["templates"]
DENSE_WORDS = LAYOUTS["dense"]["words"]
PARTS_FROM, PART_WORDS = LAYOUTS["parts"]["auto_from_words"], LAYOUTS["parts"]["part_words"]
SPLIT_LO, SPLIT_HI = LAYOUTS["split"]["text"]
NO_VISUAL_RUN = LAYOUTS["sequence"]["max_without_visual_in_a_row"]
FRAMED_PHOTO_WORDS = LAYOUTS["variety"]["photo_framed_max_words"]
# 2.63.0 - the words each layout holds, measured at 1024 x 768 with the real templates (layout-templates.json "budgets")
BUDGETS = LAYOUTS["budgets"]
INSET_MAX_WORDS.update({k: BUDGETS["beside_picture_with_inset"] for k in ("two-col", "wide-left", "wide-right")})


def word_budget(tid, variant, inset=False):
    """(words the layout holds, what it is) - None for one with no measured budget (a recap, a task launch, a comparison)"""
    if inset and tid not in ("photo-explain", "figure-stage"):
        return BUDGETS["beside_picture_with_inset"], "beside a picture with a photo under the words"
    if tid == "photo-explain":
        return {"full": (BUDGETS["photo_full"], "on a full-screen photograph"), "split": (BUDGETS["photo_framed"], "beside a framed photograph"),
                "column": (BUDGETS["photo_column"], "beside a photo column")}.get(variant)
    if tid == "figure-stage" and variant == "figure-top":
        return BUDGETS["under_top_photo"], "under a photograph across the slide"
    if tid == "content-in-parts":
        return BUDGETS["part"], "in a part"
    if tid in ("explain-figure", "reading-with-figure", "long-explanation", "procedure", "three-content-blocks") and variant != "text-only":
        return BUDGETS["beside_picture"], "beside a picture"
    return None
STAGE_WORDS = LAYOUTS["variety"]["stage_max_words"]
TOP_WORDS = LAYOUTS["variety"]["picture_top_max_words"]
VARIETY_WINDOW = LAYOUTS["variety"]["window"]
DARK_SHARE = 0.2            # 2.62.1 - 80 / 20 (owner, 2026-10-21): at most a fifth of a module's slides on the dark ground
PHOTO_LONG, PHOTO_LOW = 1600, 800        # L62: a photograph is shipped at 1600 px on its long side or more; under 800 is low
FIGURE_FREE = {("explain-figure", "text-only"), ("procedure", "text-only"), ("opening", "statement")}
FIGURE_FREE_IDS = {"opening"}
RECORD = "compiled.json"
FINAL_SET = re.compile(r"^F[A-Z]$")           # 2.49.2 - a final assessment's set: FA, and FB when it has a second variant
DRAFT_MARK = "DRAFT_NOT_PACKAGED.txt"         # 2.49.2 - in a module folder built from a script that is not approved (--draft)
DRAFT_TEXT = ("DRAFT - NOT PACKAGED\n\nThis module was built with --draft from a content script that is not approved yet: it is a\n"
              "preview. check_course_package.py and compile_course.py leave it out of the classroom package (they report it as\n"
              "\"draft - not packaged\"). Approve the script and compile the module again: this file is then removed.\n")


def is_check(code):
    """a graded set: the module check (MC) or a final assessment variant (FA, FB ...)"""
    return code == "MC" or bool(FINAL_SET.match(code or ""))


def final_codes(script):
    """the final assessment's variants in the script, in order: ["FA"], or ["FA", "FB"] (2.49.2 - variants are first-class)"""
    out = []
    for s in (script or {}).get("screens", []):
        code = ((s.get("set") if s.get("kind") == "final" else s.get("opens") if s.get("kind") == "task-slide" else "") or "").strip()
        if s.get("kind") == "final" and not code:
            code = "FA"
        if FINAL_SET.match(code) and code not in out:
            out.append(code)
    return sorted(out)


def check_page(code, script=None):
    """where a graded set's page is, as the deck links it. One final: assessment/final.html (as it always was); two or more
    variants: each its own graded page, assessment/final_a.html, final_b.html - never a task page (IGF final, 2.49.2)"""
    if code == "MC":
        return CHECK_PAGES["MC"]
    if code == "FA" and len(final_codes(script)) < 2:
        return CHECK_PAGES["FA"]
    return "../assessment/final_%s.html" % code[1].lower()


def final_name(word, code, script_or_codes=None):
    """the final assessment's name for the landing card, the key and the start page: 'Final assessment', and the variant's
    letter after it when there is more than one variant"""
    codes = script_or_codes if isinstance(script_or_codes, (list, tuple, set)) else final_codes(script_or_codes)
    return "%s %s" % (word, code[1]) if len({c for c in codes if FINAL_SET.match(c or "")}) > 1 else word
# 2.46.0 - a task slide's icon says what the trainees will DO on the tablet: the way of answering most of its set's
# questions use (IGF M01-M03: every task slide showed the same generic tablet). The tablet's outline stays, the gesture
# inside it changes.
ICON_FAMILY = {"single_choice": "choose", "multi_select": "choose", "choose_and_justify": "choose", "compare": "choose",
               "read_instrument": "choose", "scenario": "choose", "hotspot": "tap", "spot_the_hazard": "tap",
               "label_diagram": "drag", "match": "drag", "categorise": "drag", "order": "order", "build_the_plan": "order",
               "timeline": "order", "set_value": "dial", "panel_operate": "dial", "find_the_fault": "find",
               "spot_the_error": "find", "cloze": "cloze"}
ICON_GLYPH = {
    "choose": '<circle cx="19" cy="17" r="4"/><circle cx="19" cy="31" r="4" fill="currentColor"/><path d="M28 17h17M28 31h17"/>',
    "tap": '<circle cx="32" cy="22" r="9"/><circle cx="32" cy="22" r="2.4" fill="currentColor"/><path d="M32 8v4M32 32v4M18 22h4M42 22h4"/>',
    "drag": '<rect x="13" y="12" width="15" height="10" rx="2"/><rect x="36" y="26" width="15" height="10" rx="2" stroke-dasharray="3 3"/>'
            '<path d="M24 28h7m-3-3 3 3-3 3"/>',
    "order": '<path d="M24 14h20M24 24h20M24 34h20"/><circle cx="17" cy="14" r="1.8" fill="currentColor"/>'
             '<circle cx="17" cy="24" r="1.8" fill="currentColor"/><circle cx="17" cy="34" r="1.8" fill="currentColor"/>',
    "dial": '<path d="M14 30h36"/><circle cx="38" cy="30" r="5" fill="currentColor"/><path d="M14 17h36" stroke-dasharray="2 6"/>',
    "find": '<circle cx="29" cy="21" r="8"/><path d="M35 27l9 9"/>',
    "cloze": '<path d="M13 18h11M40 18h11M13 31h38"/><rect x="26" y="13" width="12" height="10" rx="2" stroke-dasharray="3 2"/>'}


# 2.63.0 (the instructors' review of IGF Basic, 2026-10-21: "bad iconography - use an exercise photo or better icons"):
# the icon says what the trainee does - a tablet with the way of answering on its screen, a check list for a graded
# check, two people at a table for work in the room. The build sheet's "photo" shows the exercise's real photograph instead.
ICON_FRAME = {
    "tablet": '<rect x="3" y="4" width="58" height="40" rx="7"/><rect x="10" y="9" width="44" height="30" rx="2" stroke-width="2"/>'
              '<circle cx="6.6" cy="24" r="1.2" fill="currentColor" stroke="none"/>',
    "check": '<rect x="14" y="7" width="36" height="38" rx="4"/><rect x="24" y="3" width="16" height="8" rx="2" fill="currentColor"/>'
             '<path d="M20 20l3 3 5-6M33 20h11M20 32l3 3 5-6M33 32h11"/>',
    "room": '<circle cx="21" cy="14" r="5"/><circle cx="43" cy="14" r="5"/><path d="M11 36c0-7 4.5-12 10-12s10 5 10 12'
            'M33 36c0-7 4.5-12 10-12s10 5 10 12M6 42h52"/>'}


def task_icon(script, code, kind="tablet"):
    """the task slide's icon - for a tablet task the way of answering most of the set's questions use (the first one on
    a tie), on a tablet's screen; a graded check's is a check list, a room activity's two people at a table"""
    svg = ('<svg class="act-ico" data-icon="%s" viewBox="0 0 64 48" aria-hidden="true" fill="none" stroke="currentColor" '
           'stroke-width="3" stroke-linecap="round" stroke-linejoin="round">%s</svg>')
    if kind in ("check", "room"):
        return svg % (kind, ICON_FRAME[kind])
    qs = [s for s in script.get("screens", []) if s.get("kind") in cs.TASKS and
          ((s.get("set") or "").strip() or {"self-check": "SC1", "module-check": "MC", "final": "FA"}[s["kind"]]) == code]
    fams = [ICON_FAMILY.get(cs.mech(s), "choose") for s in qs] or ["choose"]
    fam = max(fams, key=lambda f: (fams.count(f), -fams.index(f)))
    return svg % (fam, ICON_FRAME["tablet"] + '<g transform="translate(32 24) scale(.78) translate(-32 -24)">%s</g>' % ICON_GLYPH[fam])


def task_picture(mdir, b, probs, where):
    """the exercise's real photograph on its task slide (build sheet "photo"), opening full screen with its record - or ''"""
    rel = (b.get("photo") or "").replace("\\", "/")
    if not rel:
        return ""
    if not os.path.isfile(os.path.join(mdir, rel)):
        probs.append("%s: its \"photo\" %s is not in the module folder" % (where, rel))
        return ""
    meta = photo_meta(mdir, rel)
    alt = b.get("alt") or first_sentence(meta.get("description")) or "The exercise"
    return '<img class="act-photo" src="../%s" alt="%s"%s>' % (a(rel), a(alt), photo_panel(meta, credit_line(meta), rel, probs, where))
e = lambda s: html.escape(s or "", quote=False)
a = lambda s: html.escape(s or "", quote=True)


NATIVE = {"latviešu": "lv", "latviesu": "lv", "русский": "ru", "english": "en"}
# the deck's landing card: the compiler's own words beside the engine's (gb_deck.js LANG). PROVISIONAL (2.41.0) - written
# by Claude, to be checked by a native speaker: compile/TRANSLATIONS_REVIEW.md. Counts as "label: n" - no plural forms.
LANDING = {"en": {"module": "Module {n}"}, "lv": {"module": "{n}. modulis"}, "ru": {"module": "Модуль {n}"}}
assert all(set(LANDING[k]) == set(LANDING["en"]) for k in LANDING), "every language has every word"


def lang_code(name):
    """the course language (L19 COURSE_LANGUAGE) as its two-letter code - "Latvian", "lv", "Latviešu" -> "lv";
    None when it is not a language the factory knows (never "la" from "Latvian"[:2])"""
    n = (name or "English").strip()
    codes = cs.LABELS["course_language_codes"]
    if n in codes:
        return codes[n]
    low = n.lower()
    if low in codes.values():
        return low
    return NATIVE.get(low) or next((c for k, c in codes.items() if k.lower() == low), None)


def plugin_version():
    try:
        with io.open(os.path.join(PLUGIN, ".claude-plugin", "plugin.json"), encoding="utf-8") as f:
            return json.load(f).get("version", "unknown")
    except (OSError, ValueError):
        return "unknown"


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


CYRILLIC = dict(zip("абвгдеёжзийклмнопрстуфхцчшщъыьэюя",
                    ["a", "b", "v", "g", "d", "e", "e", "zh", "z", "i", "i", "k", "l", "m", "n", "o", "p", "r", "s", "t", "u", "f",
                     "kh", "ts", "ch", "sh", "shch", "", "y", "", "e", "iu", "ia"]))


def slug(s):
    """a file name from a title, in plain letters: "Vārsti" -> varsti, "клапаны" -> klapany (2.40.0 - before, every
    letter outside a-z was dropped: sc1_v_rsti.html)"""
    t = "".join(CYRILLIC.get(ch, ch) for ch in (s or "").lower())
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "_", t).strip("_")[:50] or "task"


def chrome_block():
    """the chrome from the factory's own frame, word for word - never retyped here"""
    t = io.open(SHELL, encoding="utf-8").read()
    i, j = t.find('<div id="progress">'), t.find("<!-- ============================= STAGE")
    if i < 0 or j < 0:
        raise SystemExit("Stopped - the factory's frame %s no longer has the chrome block this tool copies." % SHELL)
    return t[i:j].rstrip() + "\n"


def start_icon():
    m = re.search(r'<button id="startBtn"[^>]*>\s*(<svg.*?</svg>)', io.open(SHELL, encoding="utf-8").read(), re.S)
    return m.group(1) if m else ""


# ------------------------------------------------------------------ the words
TERM = re.compile(r"^([^:]{2,60}?)(\s-\s|:\s)(?=\S)")
STEP_NUM = re.compile(r"^(\d{1,2}[.)]?)(\s+)(?=\S)")      # "1 Risk ...", "2. Isolate ...", "3) Ventilate ..."


def marked(x, bold=True):
    """a line's words, the term before " - " or ": " in bold when it is a name of four words or fewer
    ("Gas mode: ...", "Tank connection space - ..."). The words are unchanged, so the match check still reads them."""
    m = TERM.match(x) if bold else None
    if m and 1 <= len(m.group(1).split()) <= 4 and not m.group(1)[:1].islower():
        return "<b>%s</b>%s%s" % (e(m.group(1)), e(m.group(2)), e(x[m.end():]))
    return e(x)


HOOK_ATTR = re.compile(r"^data-[a-z0-9-]+$")


def hook_attrs(h):
    """a figure script's hook on a line: extra class words and data-* attributes - never a look of its own"""
    out = []
    for k, v in sorted((h or {}).items()):
        if k == "class":
            continue
        if HOOK_ATTR.match(k):
            out.append(' %s="%s"' % (k, a(str(v))))
    return "".join(out), re.sub(r"[^\w -]", "", (h or {}).get("class") or "").strip()


def words_html(lines, first_statement=True, dark_photo=False, emph=None, legend=False, idx=None):
    """the slide's lines, each one marked as approved text (check_script_match reads data-script-field) and
    numbered data-i="1", "2" ... in script order, so a figure that steps can light up its line
    (document.querySelector('#s04 [data-i="3"]')). `idx` gives the script numbers when only some lines are drawn here.

    emph (from the build sheet):
      "boxes": [2, 3]            each line in a box (blue - all of them; amber is kept for the line a figure is on)
      "box_alt": [4]             these boxes grey: the other of two options side by side
      "conclusion": 5            the line the room leaves with (navy)
      "groups": [{"lines": [2, 7], "class": "box z1"}]   lines 2-7 in one box: the first as its heading
      "hooks": {"3": {"class": "m02-steptext", "data-step": "2"}}   a figure script's hook on a line"""
    emph = emph or {}
    idx = list(idx or range(1, len(lines) + 1))
    boxes, concl = list(emph.get("boxes") or []), emph.get("conclusion")
    alts = emph.get("box_alt")
    hooks = {str(k): v for k, v in (emph.get("hooks") or {}).items()}

    def line(tag, cls, i, x, bold=True, num=False):
        extra, hcls = hook_attrs(hooks.get(str(i)))
        cls = " ".join(c for c in (cls, hcls) if c)
        m = STEP_NUM.match(x) if num else None
        # a step's own number becomes its marker (.n); the words stay whole, so the match check still reads "1 Risk ..."
        words = ('<span class="n">%s</span>%s%s' % (e(m.group(1)), m.group(2), marked(x[m.end():], bold)) if m
                 else marked(x, bold))
        return '<%s%s data-script-field="text" data-i="%d"%s>%s</%s>' % (
            tag, ' class="%s"' % cls if cls else "", i, extra, words, tag)

    pairs = list(zip(idx, lines))
    if not pairs:             # a title-and-figure slide: the script may have no words for it
        return []
    if legend:
        # the badge counts 1, 2, 3 in the row (data-n); when the approved words already start with their own
        # number ("1 Fuel tank ...") the row shows those and draws no second number
        own = all(re.match(r"^\d+[ .)]", x) for _, x in pairs)
        rows = [line("li", "", i, x).replace(' data-i="%d"' % i, ' data-i="%d" data-n="%d"' % (i, n), 1)
                for n, (i, x) in enumerate(pairs, 1)]
        return ['<ol class="legend%s">' % (" own-numbers" if own else "")] + ["  " + r for r in rows] + ["</ol>"]
    if dark_photo:            # the shared look styles .lead over a photograph, not a list - a bullet stays a lead line,
        # marked .sub (the list's square marker); the lines between them are their headings, .head - bold, as a
        # text slide marks its opening line
        # steps the script numbers itself are .lead.sub too, their own number the marker, as on a text slide
        nums = [int(m.group(1).rstrip(".)")) for m in (STEP_NUM.match(x) for _, x in pairs) if m]
        steps = len(nums) >= 2 and nums == list(range(1, len(nums) + 1))
        head = "lead head" if any(x.startswith("•") for _, x in pairs) or steps else "lead"
        return [line("p", "lead sub", i, x.lstrip("•").strip(), bold=False) if x.startswith("•")
                else line("p", "lead sub step", i, x, bold=False, num=True) if steps and STEP_NUM.match(x)
                else line("p", head, i, x, bold=False) for i, x in pairs]
    if len(pairs) == 1 and not boxes and not concl and not emph.get("groups"):
        # one line is a statement - except around a stage drawing, where it is reading text and the drawing is the point
        return [line("p", "statement" if first_statement else "lead", pairs[0][0], pairs[0][1], bold=not first_statement)]
    group_of = {}
    for g in emph.get("groups") or []:
        lo, hi = (g.get("lines") or [0, 0])[0], (g.get("lines") or [0, 0])[-1]
        for k in range(lo, hi + 1):
            group_of[k] = (lo, hi, re.sub(r"[^\w -]", "", g.get("class") or "box"))
    bullets = any(x.startswith("•") for x in lines)
    # steps the script numbers itself ("1 Risk assessment ...", "2 Isolate ...") are one numbered list: every step
    # the same size, its number the marker - not step 1 as the headline and the rest as squares (IGF M11 s04)
    nums = [int(m.group(1).rstrip(".)")) for m in (STEP_NUM.match(x) for x in lines) if m]
    seq = len(nums) >= 2 and nums == list(range(1, len(nums) + 1)) and not boxes and not group_of
    # a first line is the headline only when it is short - a long opening paragraph set as a headline fills the column
    plain = (first_statement and not bullets and not seq and not boxes and not group_of
             and cs.wc(lines[0]) <= STATEMENT_MAX_WORDS)
    roles = []
    for n, (i, x) in enumerate(pairs):
        if i in group_of:
            roles.append(("group", i, x))
        elif i == concl:
            roles.append(("call", i, x))
        elif i in boxes:
            # no automatic second colour: blue / amber in turn read as "selected" (IGF M05, 2026-10-19)
            alt = i in (alts or ())
            # a box sets its line apart already - a typed "•" in it is a second bullet look (IGF M03, 2026-10-19)
            roles.append(("box alt" if alt else "box", i, x.lstrip("•").strip()))
        elif x.startswith("•"):
            roles.append(("li", i, x.lstrip("•").strip()))
        elif seq and STEP_NUM.match(x):
            roles.append(("li", i, x))
        elif plain and n == 0:
            roles.append(("statement", i, x))
        elif plain:
            roles.append(("li", i, x))
        else:
            roles.append(("lead", i, x))
    out, run, grp = [], [], []

    def flush_run(dest):
        if run:
            steps = seq and all(STEP_NUM.match(r) for _, r in run)
            dest.append('<ol class="support seq">' if steps else '<ul class="support">')
            dest.extend("  " + line("li", "", k, r, num=steps) for k, r in run)
            dest.append("</ol>" if steps else "</ul>")
            del run[:]

    def flush_group():
        if grp:
            lo, hi, cls = group_of[grp[0][0]]
            inner = []
            for n, (i, x) in enumerate(grp):
                if x.startswith("•"):
                    run.append((i, x.lstrip("•").strip()))
                    continue
                flush_run(inner)
                inner.append(line("p", "lead" if n else "", i, x))
            flush_run(inner)
            out.append('<div class="%s">' % cls)
            out.extend("  " + y for y in inner)
            out.append("</div>")
            del grp[:]

    for role, i, x in roles + [(None, None, None)]:
        if role == "group":
            if grp and group_of[grp[0][0]][0] != group_of[i][0]:
                flush_group()
            flush_run(out)
            grp.append((i, x))
            continue
        flush_group()
        if role == "li":
            run.append((i, x))
            continue
        flush_run(out)
        if role:
            out.append(line("p", role, i, x, bold=role != "statement"))
    return out


# ------------------------------------------------------------------ the pictures
def read_figure(mdir, rel, figdir=None):
    """a drawing (.svg / .html) is source: looked for in working_claude\\figures\\M01\\ first, then the module
    folder; a picture (.jpg ...) is shipped, so it must be in the module folder"""
    low = rel.lower()
    tries = [] if low.endswith(IMAGES) or not figdir else [figdir]
    tries.append(mdir)
    for base in tries:
        p = os.path.normpath(os.path.join(base, rel))
        if not p.startswith(os.path.abspath(base)):
            return None, "is outside %s" % ("the module folder" if base == mdir else "working_claude\\figures")
        if os.path.isfile(p):
            break
    else:
        return None, "is not there" + ("" if low.endswith(IMAGES) else " (looked in working_claude\\figures\\%s\\ and the module folder)"
                                       % os.path.basename(figdir or ""))
    if low.endswith(IMAGES):
        return None, None
    if low.endswith((".html", ".htm")) and base == mdir:
        return None, ("is an .html file in the module folder - the classroom would take it for a page and send it to the "
                      "tablets; keep drawing fragments in working_claude\\figures\\%s\\" % os.path.basename(figdir or "M01"))
    t = io.open(p, encoding="utf-8").read()
    t = re.sub(r"^\s*<\?xml[^>]*\?>\s*", "", t)
    t = re.sub(r"^\s*<!DOCTYPE[^>]*>\s*", "", t, flags=re.I)
    return t.strip(), None


def photo_meta(mdir, rel):
    p = os.path.join(mdir, os.path.dirname(rel), "_photo_meta.json")
    try:
        return json.load(io.open(p, encoding="utf-8")).get(os.path.basename(rel)) or {}
    except (OSError, ValueError):
        return {}


def is_generated(meta):
    """a picture made by an image model (nano banana and the like) - its record says so. It carries no credit line
    (no third-party rights; operator 2026-10-15: no on-screen label) and is never an L57 thumbnail"""
    return bool(meta) and (meta.get("generated") is True or str(meta.get("source") or "").upper() == "GENERATED")


def credit_line(meta, with_title=True):
    """Title · Author · Source · Licence · resized - who made it, where it is from, the licence, and that it was
    changed (CC BY / BY-SA 4.0 require these; the title is good practice, left out beside a caption that already
    says what the photo shows). The title is the meta's own, else the Wikimedia file name; "resized" when the
    stored size is not the original's. A generated picture has none."""
    if is_generated(meta):
        return ""
    if not meta or not (meta.get("attribution_required") or meta.get("licence")):
        return ""
    author = re.split(r"\s*[(,]", meta.get("author") or "")[0].strip()
    title = meta.get("title") or ""
    m = re.search(r"/File:([^/?#]+?)\.(?:jpe?g|png|webp|gif|tiff?)$", meta.get("url_or_origin") or "", re.I)
    if not with_title:
        title, m = "", None
    if not title and m:
        from urllib.parse import unquote
        title = unquote(m.group(1)).replace("_", " ").strip()
    o, st = str(meta.get("orig_size") or ""), str(meta.get("stored_size") or "")
    changed = meta.get("modification") or ("resized" if "resized" in st or (o and st and o.split()[0] != st.split()[0]) else "")
    parts = [x for x in (title, author, meta.get("source"), meta.get("licence"), changed) if x]
    return "Photo: " + " · ".join(parts) if parts else ""


def first_sentence(s):
    s = re.split(r"(?<=[.!?])\s|\s-\s", (s or "").strip())[0]
    return s.strip()


OVERRIDE = {}      # {spec file name: spec} - drawn instead of the file: the studio trying a candidate on its real slide
FIT_DIR = "_fit"


def composition_key(s, b):
    """what decides the figure's column: the layout and the slide's dark / figure-first / inset choices"""
    return "|".join(str(x) for x in (b.get("composition") or s.get("layout") or "", bool(b.get("dark")), bool(b.get("figure_first")),
                                      json.dumps(b.get("inset") or {}, sort_keys=True), json.dumps(b.get("no_photo") or [], sort_keys=True)))


def fit_path(figdir, name, sid):
    """one fit per slide: a spec shown on two slides may sit in two columns"""
    return os.path.join(figdir or "", FIT_DIR, "%s.%s" % (sid, name))


def strip_off(figdir, s, b):
    """2.50.1 - the L57 photo row is left off this slide: a candidate the studio is trying without it ("_no_strip"), or an
    active fit made that way by figure_fit.py - the drawing fits its column only with the row's height (IGF M01 s05 at
    wide-left: 369 x 239 px with the row, 369 x 361 without; round 2 of the benchmark chose the same by hand)"""
    if b.get("_no_strip"):
        return True
    rel = (b.get("figure") or "").replace("\\", "/")
    if not figdir or not rel.lower().endswith(KIT_SPEC):
        return False
    p = fit_path(figdir, os.path.basename(rel), s["id"])
    if not os.path.isfile(p):
        return False
    try:
        rec = json.load(io.open(p, encoding="utf-8"))
        text = io.open(os.path.join(figdir, rel), encoding="utf-8").read().strip()
    except (OSError, ValueError):
        return False
    return rec.get("strip") is False and rec.get("source") == sha(text) and rec.get("column") == composition_key(s, b)


def fitted(figdir, name, text, key, sid):
    """2.50.0 (lever 7, M01 round 2) - a kit figure re-fitted to the column it is shown in, by figure_fit.py, when its slide's
    layout changed and the spec no longer fits: kept beside the spec in figures\\MNN\\_fit\\, used only while the spec and the
    slide's layout are the ones it was made from (else the spec is drawn as written, and the drawing check judges it).
    The spec itself is never rewritten."""
    p = fit_path(figdir, name, sid)
    if not figdir or not os.path.isfile(p):
        return None
    try:
        rec = json.load(io.open(p, encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if rec.get("source") != sha(text) or rec.get("column") != key:
        return None
    return json.dumps(rec.get("spec"), ensure_ascii=False)


def kit_svg_attrs(spec, view=None):
    """what kit.js sets on its drawing when it draws - role, the spec's label, the viewBox - already in the page (2.60.0):
    check_visuals.py reads the page as written and warned 22-79 times a module on the empty <svg data-kit>"""
    try:
        vb = [float(v) for v in (view or spec.get("view") or [0, 0] + list(spec.get("size") or [])[:2])]
    except (TypeError, ValueError):
        vb = []
    return ' role="img" aria-label="%s"%s' % (html.escape(spec.get("label") or "", quote=True),
                                               ' viewBox="%s"' % " ".join("%g" % v for v in vb) if len(vb) == 4 else "")


def kit_figure(text, s, probs, where):
    """a figure made from the figure kit (course-visuals/kit): its spec goes into the page as it is, and
    kit.js draws it there. The step buttons are the deck's own .mediabar. course-visuals/kit/scripts/
    check_kit.py checks the spec itself; here only what would stop the page from drawing it."""
    try:
        spec = json.loads(text)
    except ValueError as err:
        probs.append("%s: its kit figure is not valid JSON - %s" % (where, err))
        return ""
    if not isinstance(spec, dict) or not spec.get("parts"):
        probs.append("%s: its kit figure has no parts" % where)
        return ""
    if not spec.get("label"):
        spec["label"] = first_sentence(s.get("visual")) or s.get("title") or ""
    sid = "kit-" + s["id"]
    data = json.dumps(spec, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    out = ['<div class="fill fig kit-fig" data-kit-scope>',
           '<div class="kit-screen"><svg data-kit="#%s"%s></svg></div>' % (sid, kit_svg_attrs(spec)),
           '<script type="application/json" id="%s">%s</script>' % (sid, data)]
    if spec.get("steps"):
        chev = '<svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor"><path d="%s"/></svg>'
        out.append('<div class="mediabar">'
                   '<button class="fbtn" type="button" data-act="prev">%s Previous step</button>'
                   '<span class="dots"></span>'
                   '<button class="fbtn primary" type="button" data-act="next">Next step %s</button>'
                   '<button class="fbtn" type="button" data-act="replay">Replay</button></div>'
                   % (chev % "M15.4 7.4 14 6l-6 6 6 6 1.4-1.4L10.8 12z", chev % "M8.6 16.6 10 18l6-6-6-6-1.4 1.4L13.2 12z"))
    out.append("</div>")
    return "".join(out)


# 2.60.0 - a 3D scene's control hint ("Drag to turn - tap a part to look closer") is the scene's own words for the screen,
# not the script's: its holder [data-hint] is marked data-script-ignore as the figure goes in, so check_script_match counts
# it instead of failing the build (IGF M05 s06, M13 s07, M15 s05 - each builder marked it by hand after a FAIL)
HINT_TAG = re.compile(r"<([a-zA-Z][\w-]*)(\s[^>]*?\bdata-hint\b[^>]*)>")


def hint_ignored(page):
    return HINT_TAG.sub(lambda m: m.group(0) if "data-script-ignore" in m.group(2)
                        else "<%s data-script-ignore%s>" % (m.group(1), m.group(2)), page)


def figure_html(mdir, figdir, s, b, probs, where):
    """the slide's picture, as it goes into the page, and its credit line"""
    rel = (b.get("figure") or "").replace("\\", "/")
    if not rel:
        if (s.get("visual_kind") or "none") != "none":
            probs.append("%s has no picture file in the build sheet - it is planned as %s: %s%s"
                         % (where, s.get("visual_kind"), first_sentence(s.get("visual")) or "(no description)",
                            NO_PHOTO_YET if s.get("visual_kind") in ("photo", "annotated_photo", "photo_to_take") else ""))
        return "", "", False
    body, err = read_figure(mdir, rel, figdir)
    if err:
        probs.append("%s: its picture file %s %s" % (where, rel, err))
        return "", "", False
    if cs.flat_3d(s, b, body):                         # 2.49.7 (IGF M01 s05): a 3D slide is never quietly built in 2D
        probs.append(FLAT_3D % (where, s.get("visual_kind"), rel))
    if rel.lower().endswith(KIT_SPEC):
        name = os.path.basename(rel)
        if name in OVERRIDE:                           # the studio trying a candidate on the real slide
            body = json.dumps(OVERRIDE[name], ensure_ascii=False)
        else:
            body = fitted(figdir, name, body, composition_key(s, b), s["id"]) or body
        return kit_figure(body, s, probs, where), "", False
    if body is not None:
        credits = []
        page = hint_ignored(photos_in(body, mdir, probs, where, credits))
        return page, b.get("credit") or fragment_credit(page, credits), False
    meta = photo_meta(mdir, rel)
    alt = b.get("alt") or first_sentence(s.get("visual")) or first_sentence(meta.get("description"))
    credit = b.get("credit") or credit_line(meta)
    if meta.get("attribution_required") and not credit:
        probs.append("%s: the photograph %s needs a credit line, and assets\\img\\_photo_meta.json does not give one" % (where, rel))
    return '<img src="../%s" alt="%s"%s>' % (a(rel), a(alt), photo_panel(meta, credit, rel, probs, where)), credit, True


def photo_panel(meta, credit, rel, probs, where):
    """L56: every photograph carries its record into the L51 viewer (gb_zoom.js), which shows it under the picture
    full screen: what it shows and its credit. What it shows is the photo's own record, written when the photo was
    brought in: its "description" says what is in the picture and never more than the picture evidences."""
    about = (meta.get("description") or "").strip()
    if not about:
        probs.append("%s: the photograph %s has no \"description\" in its _photo_meta.json - full screen (L51, L56) it "
                     "would say nothing about what it shows" % (where, rel))
    return "".join(' %s="%s"' % (k, a(v)) for k, v in (("data-about", about), ("data-credit", credit)) if v)


# a file-system path where a trainee reads a credit or a caption (IGF M04, 2026-10-16: a photograph's record carried the
# folder it was copied from, and the credit showed it on the slide - every automatic probe was green)
PATH_IN_TEXT = re.compile(
    r"(?<![A-Za-z])[A-Za-z]:[\\/]"                              # a drive letter: C:\ or D:/
    r"|\\\\[\w.$-]+\\"                                          # a network path
    r"|[\w.)-]\\[\w.(-]"                                        # a backslash path: Photos\x.jpg
    r"|/(?:Users|home|mnt|tmp|var)/\w"                          # a user or system folder
    r"|\bfile://|\bworking_claude\b|\bAppData\b"                 # the factory's own working folders
    r"|(?:^|[\s\"'(])(?:\.\./|\./|assets/|img/)\S*\.(?:jpe?g|png|webp|gif|svg)\b", re.I)    # a relative picture path
CREDIT_TEXT = re.compile(r'<div class="credit">(.*?)</div>|<figcaption\b[^>]*>(.*?)</figcaption>|\bdata-(?:credit|about)="([^"]*)"', re.S)


def credit_path_problems(page, name):
    """every credit, caption and full-screen record on a built page that shows a file-system path or a drive letter - a
    build problem: the trainee must never read where a file lives on somebody's computer"""
    probs, seen = [], set()
    for m in CREDIT_TEXT.finditer(page):
        raw = next(g for g in m.groups() if g is not None)
        text = html.unescape(re.sub(r"<[^>]+>", "", raw)).strip()
        hit = PATH_IN_TEXT.search(text)
        if hit and text not in seen:
            seen.add(text)
            probs.append("%s: a credit or caption shows a file-system path (%r in \"%s\") - the trainee would read where the file "
                         "lives on a computer. Fix the photograph's record in assets\\img\\_photo_meta.json (source, author, "
                         "title, description) or the caption in the build sheet" % (name, hit.group(0).strip(), text[:90]))
    return probs


IMG_TAG = re.compile(r'<img\b(?![^>]*\bdata-(?:about|no-zoom)\b)[^>]*\bsrc="\.\./([^"]+)"[^>]*?(/?)>', re.I)


def photos_in(body, mdir, probs, where, credits=None):
    """a photograph inside a drawing fragment (four photo cards, a photo in an aside) opens like any other (L56):
    its <img> gets the photo's description and credit from the module's own _photo_meta.json. `credits`, when given,
    collects each photo's credit line (2.49.1)"""
    def one(m):
        rel = m.group(1)
        if not rel.lower().endswith(IMAGES) or not os.path.isfile(os.path.join(mdir, rel)):
            return m.group(0)
        meta = photo_meta(mdir, rel)
        if not meta:
            return m.group(0)
        tag, close = m.group(0), m.group(2)
        cut = len(tag) - (2 if close else 1)
        if credits is not None and credit_line(meta) not in credits:
            credits.append(credit_line(meta))
        return tag[:cut].rstrip() + photo_panel(meta, credit_line(meta), rel, probs, where) + tag[cut:]
    return IMG_TAG.sub(one, body)


def fragment_credit(page, credits):
    """2.49.1 - a photograph inside a figure fragment keeps the slide's visible credit line, like a photograph slide's:
    the credit of its one or two photographs, unless the fragment already says it in its own words (a card's caption)"""
    seen = html.unescape(re.sub(r"<[^>]+>", " ", page))
    credits = [x for x in credits if x and x not in seen]
    return " / ".join(credits) if 0 < len(credits) <= 2 else ""


# ------------------------------------------------------------------ 2.52.0: what the built picture is, and can do
def kit_spec_of(fig):
    """the figure-kit spec inside a built figure, or None"""
    for m in JSON_DATA.finditer(fig or ""):
        try:
            spec = json.loads(m.group(1).replace("<\\/", "</"))
        except ValueError:
            continue
        if isinstance(spec, dict) and spec.get("parts"):
            return spec
    return None


def built_kind(s, fig, is_photo, meta=None):
    """the kind of picture the slide really has (media-and-tasks.json visual_kinds), from the figure built - the script's
    planned kind when the figure is one: a 3D kind only for a 3D scene, a photograph kind only for a photograph. A 3D slide
    the operator kept 2D ("declined_3d") is a 2D drawing here, so nothing downstream promises a model to turn"""
    planned = cs.parse_kind(s.get("visual_kind") or "") or "none"
    fam = lambda k: (cs.MEDIA["visual_kinds"].get(k) or {}).get("family")
    if not fig:
        return "none"
    if is_photo:
        return "ai_illustration" if is_generated(meta) else planned if planned in PHOTO_KINDS else "photo"
    drawn = planned != "none" and fam(planned) not in ("3d", "video") and planned not in PHOTO_KINDS + ("ai_illustration",)
    if cs.scene_in(fig):                               # a mounted figure ([data-stage]) may be 2D; a canvas or data-3d is a scene
        return planned if fam(planned) == "3d" or drawn else (
            "model_3d" if re.search(r"<canvas\b|\bdata-(?:3d|scene)\b", fig, re.I) else "interactive_diagram")
    if re.search(r"<video\b", fig, re.I):
        return planned if fam(planned) == "video" else "video_real"
    if drawn:
        return planned
    spec = kit_spec_of(fig)
    if spec is not None:
        return "step_animation" if spec.get("steps") else FLAT_KIND
    if IMG_SRC.search(fig) and not re.search(r"<svg\b", fig, re.I):
        return "photo"
    return FLAT_KIND


def slide_visual(s, b, mdir, figdir):
    """built_kind of one slide, from its build-sheet entry - for the instructor's plan (module_plan.py)"""
    if s.get("kind") != "slide" and not (s.get("kind") == "activity" and b.get("figure")):
        return ""
    fig, _credit, is_photo = figure_html(mdir, figdir, s, b, [], "")
    return built_kind(s, fig, is_photo, photo_meta(mdir, (b.get("figure") or "").replace("\\", "/")) if is_photo else None)


def hooked(build, mdir, sid):
    """a module figure script of the build sheet ("scripts") that works on this slide - what it lets the presenter do is
    its own, so a cue on it is never second-guessed"""
    for rel in build.get("scripts") or []:
        try:
            text = io.open(os.path.join(mdir, rel), encoding="utf-8").read()
        except (OSError, UnicodeDecodeError):
            continue
        if re.search(r"(?:GB_HOOKS\.|['\"#])%s\b" % re.escape(sid), text):
            return True
    return False


def figure_can(fig, kind, is_photo, build, mdir, sid):
    """what the presenter can do with the built picture: turn (a 3D scene), drag, tap, tap_part (its drawn parts)"""
    if not fig:
        return set()
    if cs.scene_in(fig) or hooked(build, mdir, sid):
        return {"turn", "drag", "tap", "tap_part"}
    if is_photo:
        return {"tap"}                                 # it opens full screen (L51)
    spec = kit_spec_of(fig)
    if spec is not None:                               # the step buttons and the lines its steps light are buttons (kit.js)
        return {"tap"} if spec.get("steps") else set()
    can = set()
    if TAP_MARK.search(fig):
        can |= {"tap", "tap_part"}
    if DRAG_MARK.search(fig):
        can.add("drag")
    return can


CUE_FIXES = {}      # {slide id: its notes with every drafted cue line} - written by main() as a changes file for propose
CUE_FIX_HOW = "<cue-fix>"


def draft_cue(ln, fig, is_photo):
    """a cue line that asks the picture only for what it can do - a draft for the operator, never applied by the build.
    What follows a colon in the old line (what the picture shows) is kept; "" = drop the line"""
    tail = ln.split(":", 1)[1].strip() if ":" in ln else ""
    spec = kit_spec_of(fig)
    if spec is not None and spec.get("steps"):
        do = "Step through the drawing with Next, or tap a lit line"
    elif is_photo:
        do = "Open the photo full screen and point out what it shows"
    elif fig:
        do = "Point to each part on the drawing in turn"
    else:
        return ""
    return do + (": " + tail if tail else ".")


def cue_problems(s, fig, kind, is_photo, build, mdir, where):
    """2.52.0 (IGF M01 s04 / s05, M02 s09) - a line of the instructor's cue that asks the picture for what the built picture
    cannot do ("Rotate the model and cut the pipe open" on a 2D drawing once the 3D was declined; "Tap each part" on a
    drawing whose parts do not answer a tap). The approved words are never changed by the build (L29) - they are said,
    with a drafted line in their place (CUE_FIXES: main() writes them as a changes file for content_script.py propose)"""
    can, out = figure_can(fig, kind, is_photo, build, mdir, s["id"]), []
    what = kind.replace("_", " ") if kind != "none" else "no picture"
    notes = s.get("notes") or ""
    for ln in [x.strip().lstrip("-•").strip() for x in notes.splitlines() if x.strip()]:
        need = [k for k, rx in (("turn", CUE_TURN), ("drag", CUE_DRAG), ("tap_part", CUE_TAP_PART)) if rx.search(ln) and k not in can]
        if "tap_part" not in need and CUE_TAP.search(ln) and "tap" not in can and not CUE_TAP_PART.search(ln):
            need.append("tap")
        if not need:
            continue
        new = draft_cue(ln, fig, is_photo)
        notes = notes.replace(ln, new, 1) if new else "\n".join(x for x in notes.splitlines() if x.strip().lstrip("-•").strip() != ln)
        out.append("%s: the instructor's cue says \"%s\" - the picture built here (%s) %s. The build never changes the approved "
                   "words (L29). Drafted in its place: %s - %s; or give the slide a picture that does it, or keep the cue with "
                   "the operator's reason in the build sheet: \"cue_kept\": \"<their reason>\""
                   % (where, ln, what, "; it ".join(CANNOT[k] for k in need), "\"%s\"" % new if new else "drop the line", CUE_FIX_HOW))
    if out:
        CUE_FIXES[s["id"]] = notes
    return out


def write_cue_fixes(course, module, probs):
    """the drafted cue lines as a changes file beside the script (never applied by the build: propose shows them to the
    operator, apply --confirmed only after their yes), and the exact command in each cue line of "To fix" """
    p = os.path.join(cs.paths(course, module)["dir"], "%s.cue_fixes.json" % cs.mid(module))
    if not CUE_FIXES:
        if os.path.isfile(p):
            os.remove(p)
        return probs
    cs.save(p, [{"field": "%s.notes" % sid, "new": notes} for sid, notes in sorted(CUE_FIXES.items())])
    how = "to propose the drafted lines (all of this module's, in %s): python \"%s\" propose \"%s\" --module %s --changes \"%s\"" % (
        os.path.basename(p), os.path.join(SKILL, "scripts", "content_script.py"), course, module, p)
    return [x.replace(CUE_FIX_HOW, how) for x in probs]


# ------------------------------------------------------------------ L57: a drawing of real things carries their photos
THINGS = None
JSON_DATA = re.compile(r'<script type="application/json"[^>]*>(.*?)</script>', re.S)
SVG_TEXT = re.compile(r"<text\b[^>]*>(.*?)</text>", re.S | re.I)
IMG_SRC = re.compile(r'<img\b[^>]*\bsrc="\.\./([^"]+)"', re.I)
NOT_CLEARED = ("REVIEW", "REJECT")
GENERIC = {"tank", "space", "room", "engine", "pipe", "line", "valve", "pump", "unit", "deck", "panel", "station", "door",
           "hold", "vessel", "ship", "gas", "fuel", "button", "hose", "arm", "fan", "door"}
ACRONYMS = {"LNG", "CNG", "LPG", "ESD", "GVU", "TCS", "FPR", "IGF", "LEL", "BOG", "GCU", "PRV", "ERS", "QCDC", "IMO"}
TO_TAKE = "PHOTOS_TO_TAKE.md"
CHART_PARTS = ("scale", "bands", "curve_chart", "flammability", "range_bar")   # the kit's chart family (SPEC.md family 6)
# 2.49.0 (operator, 2026-10-16: AI pictures when needed) - what a missing photograph can become, said at the build
NO_PHOTO_YET = (" - find the real photograph (the project, the factory library, a free-licence one: course-visuals); "
                "if none exists and the slide only sets the scene, propose an AI picture unasked (nano-banana: described, "
                "priced, said yes to, then made; never equipment to recognise, L33); equipment stays a photo to take")
# 2.49.7 (IGF M01 s05) - the script plans a 3D scene and the build sheet gives a 2D figure: said, until the operator keeps it
FLAT_3D = ("%s asks for a 3D scene (%s); it has a 2D figure (%s) - build the scene (compile GUIDE 2b: an .html figure with a "
           "[data-stage], its three.js file in \"scripts\", like M03's m03_station3d.js), or keep the 2D figure with the "
           "operator's reason in the build sheet: \"declined_3d\": \"<their reason>\"")
# 2.52.0 (IGF M01/M02 benchmark, 2026-10-20) - what the slide's picture IS once built: the deck's data-visual and the plan's
# kind say this, never the script's plan when the build sheet gave something else (a 3D slide kept 2D with "declined_3d")
PHOTO_KINDS = ("photo", "photo_to_take")
FLAT_KIND = "schematic"
# the instructor's cue asks the picture to do something: turn it, drag in it, tap it, tap its parts
CUE_TURN = re.compile(r"(?i)\b(?:rotat\w*|spin\w*|pinch\w*|zoom\w*|turn\s+(?:it|the\s+(?:model|scene|view|section|hull|tank)s?)\b"
                      r"|cut\b[^.;\n]{0,30}\bopen\b)")
CUE_DRAG = re.compile(r"(?i)\bdrag\w*")
CUE_TAP_PART = re.compile(r"(?i)\b(?:tap|click)\w*\s+(?:on\s+)?(?:each|every|a|the)\s+(?:\w+\s+)?(?:part|space|component)s?\b")
CUE_TAP = re.compile(r"(?i)\b(?:tap|click)(?:s|ped|ping)?\b")
TAP_MARK = re.compile(r"<button\b|\bonclick=|role=\"button\"|\bdata-tap\b|addEventListener\(\s*['\"](?:click|pointerup|pointerdown)", re.I)
DRAG_MARK = re.compile(r"\bdraggable\b|pointermove|mousemove|touchmove", re.I)
CANNOT = {"turn": "cannot be turned, zoomed or cut open - it is not a 3D scene",
          "drag": "has nothing to drag",
          "tap_part": "does not answer a tap on its parts",
          "tap": "has nothing to tap"}


def norm(s):
    """lower case, plain words, a plural made singular - "Fuel tanks" and "fuel tank" are one thing"""
    words = re.sub(r"[^a-z0-9 ]+", " ", (s or "").lower()).split()
    return [w[:-1] if len(w) > 3 and w.endswith("s") and not w.endswith("ss") else w for w in words]


def same_thing(a_, b_):
    """one name is the other, or the longer holds the shorter whole when the shorter has two words or more
    ("LNG fuel tank" holds "fuel tank"; "tank" alone never matches every tank)"""
    x, y = norm(a_), norm(b_)
    if not x or not y:
        return False
    if x == y:
        return True
    short, long_ = sorted((x, y), key=len)
    return len(short) >= 2 and any(long_[i:i + len(short)] == short for i in range(len(long_) - len(short) + 1))


def shows_it(shown, name):
    """the photo shows the drawn thing: the same name, or the photo's name is MORE specific and holds the drawn one
    whole ("LNG fuel tank" shows a "fuel tank"). Never the other way: a photo of a "fuel tank" is no "oil fuel tank"."""
    x, y = norm(name), norm(shown)
    if not x or not y:
        return False
    return x == y or (len(x) >= 2 and any(y[i:i + len(x)] == x for i in range(len(y) - len(x) + 1)))


def is_thing(name):
    global THINGS
    if THINGS is None:
        THINGS = {" ".join(norm(w)) for w in cs.MEDIA["floors"].get("photo_things") or []}
    w = norm(name)
    return 1 <= len(w) <= 5 and w[-1] in THINGS


def drawn_labels(fig):
    """the names a drawing writes on itself: a kit spec's part labels and text, an SVG's <text>"""
    out = []
    for m in JSON_DATA.finditer(fig):
        try:
            spec = json.loads(m.group(1).replace("<\\/", "</"))
        except ValueError:
            continue
        for p in spec.get("parts") or [] if isinstance(spec, dict) else []:
            out += [p[k] for k in ("label", "text") if isinstance(p.get(k), str)]
    out += [re.sub(r"<[^>]+>", " ", m.group(1)) for m in SVG_TEXT.finditer(JSON_DATA.sub("", fig))]
    return [" ".join(html.unescape(x).split()) for x in out]


def step_numbers(fig):
    """a kit figure's numbered steps: {slide line: step number}, so a thumbnail carries the drawing's own number"""
    nums = {}
    for m in JSON_DATA.finditer(fig):
        try:
            spec = json.loads(m.group(1).replace("<\\/", "</"))
        except ValueError:
            continue
        for k, st in enumerate(spec.get("steps") or [] if isinstance(spec, dict) else [], 1):
            ln = st.get("line") if isinstance(st, dict) else None
            for x in ln if isinstance(ln, list) else [ln]:       # a step may light one line or several
                if isinstance(x, int) or (isinstance(x, str) and x.isdigit()):
                    nums.setdefault(int(x), k)
    return nums


def chart_only(fig):
    """2.49.1 - a drawing that is only a chart (its parts are of the kit's chart family, bare words aside): what it names
    is an axis, a line, a zone or a scale - never a real thing to photograph"""
    types = []
    for m in JSON_DATA.finditer(fig or ""):
        try:
            spec = json.loads(m.group(1).replace("<\\/", "</"))
        except ValueError:
            continue
        types += [p.get("type") for p in spec.get("parts") or [] if isinstance(p, dict)] if isinstance(spec, dict) else []
    types = [t for t in types if t != "text"]
    return bool(types) and all(t in CHART_PARTS for t in types)


def drawn_parts(lines, fig):
    """the real things a drawn slide names, in order: the slide's own terms ("Tank connection space - ...") with the
    drawing's step number, then the labels the drawing writes on itself. An abbreviation alone (TCS) is skipped -
    the slide or the key names it in full. A chart names no things (2.49.1)."""
    if chart_only(fig):
        return []
    nums, parts = step_numbers(fig), []

    def add(num, name):
        name = re.sub(r"^\d+\s*[.)·:-]?\s*", "", name)
        name = re.sub(r"(?i)^(?:(?:in|to|from|at|on|of|into|up|down|over|through|via)\s+)?(?:(?:the|a|an|its|two|three|four|both)\s+)+",
                      "", name)
        name = name.strip(" .·,;:-–")
        if not name or (name.isupper() and " " not in name and len(name) <= 5) or len(name.split()) > 5:
            return
        if " " not in name and norm(name) and norm(name)[0] in GENERIC:
            return                                         # "Tank", "Engine" alone - the slide names which one
        if any(w in name for w in "=→/%°") or re.search(r"\d", name):
            return                                         # a key or a reading, not a thing
        if name.isupper():                                 # "LNG LIQUID LINE" -> "LNG liquid line"
            name = " ".join(w if w in ACRONYMS else w.lower() for w in name.split())
        if not any(same_thing(name, n) for _, n in parts):
            parts.append((num, name[:1].upper() + name[1:]))

    for i, x in enumerate(lines, 1):
        m = TERM.match(x.lstrip("•").strip())
        if m and 1 <= len(m.group(1).split()) <= 5:
            add(nums.get(i), m.group(1))
    for lab in drawn_labels(fig):
        add(None, lab)
    return parts


def photo_pool(mdir):
    """every cleared photograph that says what it shows: the module's own first, then the other modules' of the
    course (a match there is copied in with its record)"""
    def of(d):
        meta = {}
        for sub in (UNUSED, ""):                           # 2.52.0: a photo left out of the package is still the course's
            p = os.path.join(d, "assets", "img", sub, "_photo_meta.json")
            try:
                meta.update(json.load(io.open(p, encoding="utf-8")))
            except (OSError, ValueError, TypeError):
                continue
        return [(name, m, d, photo_id(d, os.path.relpath(img_file(d, name), d).replace("\\", "/"), m))
                for name, m in sorted(meta.items()) if isinstance(m, dict)
                and not any(x in str(m.get("rights_state") or "").upper() for x in NOT_CLEARED)
                and not is_generated(m)                    # L57 places real photographs only
                and os.path.isfile(img_file(d, name))]
    return of(mdir) + [x for d in other_modules(mdir) for x in of(d)]


# ------------------------------------------------------------------ 2.52.0: only what is shown ships
UNUSED = "_unused"          # assets\img\_unused\ - a folder starting with _ is skipped by the classroom (package-core.mjs)
SHOWN_EXT = (".html", ".htm", ".css", ".js", ".svg", ".json")


def img_file(d, name):
    """where a module's picture is: assets\\img\\, or assets\\img\\_unused\\ when it was left out of the package"""
    p = os.path.join(d, "assets", "img", name)
    q = os.path.join(d, "assets", "img", UNUSED, name)
    return q if not os.path.isfile(p) and os.path.isfile(q) else p


def move_record(src_dir, dst_dir, name):
    """a picture's _photo_meta.json record goes with it"""
    sp, dp = os.path.join(src_dir, "_photo_meta.json"), os.path.join(dst_dir, "_photo_meta.json")
    try:
        src = json.load(io.open(sp, encoding="utf-8"))
    except (OSError, ValueError):
        return
    if name not in src:
        return
    dst = json.load(io.open(dp, encoding="utf-8")) if os.path.isfile(dp) else {}
    dst[name] = src.pop(name)
    cs.save(dp, dst)
    cs.save(sp, src)


def restore(mdir, names):
    """pictures left out of the package before and now named again (the build sheet, a drawing, an L57 thumbnail): back in
    assets\\img\\ with their records, so the build finds them"""
    img = os.path.join(mdir, "assets", "img")
    back = []
    for name in names:
        src = os.path.join(img, UNUSED, name)
        if os.path.isfile(src) and not os.path.isfile(os.path.join(img, name)):
            os.replace(src, os.path.join(img, name))
            move_record(os.path.join(img, UNUSED), img, name)
            back.append(name)
    return back


def named_again(mdir, build, figdir):
    """the pictures in assets\\img\\_unused\\ that the build sheet, the module's drawings or its own styles and scripts name"""
    left = os.path.join(mdir, "assets", "img", UNUSED)
    names = [f for f in (os.listdir(left) if os.path.isdir(left) else []) if f.lower().endswith(IMAGES)]
    if not names:
        return []

    def said(o):                    # a key starting with _ is a note in the build sheet ("_inset": "... was placed ..."), no use
        if isinstance(o, dict):
            return {k: said(v) for k, v in o.items() if not str(k).startswith("_")}
        return [said(v) for v in o] if isinstance(o, list) else o
    sheet = json.dumps(said(build), ensure_ascii=False)
    texts = [sheet]
    for rel in set(re.findall(r'"([^"]+\.(?:html?|svg|json))"', sheet)):      # the drawings the build sheet names
        p = os.path.join(figdir or "", rel.replace("\\", "/"))
        if figdir and os.path.isfile(p):
            texts.append(re.sub(r"<!--.*?-->", "", io.open(p, encoding="utf-8", errors="replace").read(), flags=re.S))
    for rel in build.get("styles", []) + build.get("scripts", []):
        p = os.path.join(mdir, rel)
        if os.path.isfile(p):
            texts.append(io.open(p, encoding="utf-8", errors="replace").read())
    blob = "\n".join(texts)
    return [n for n in names if re.search(r"(?<![\w.-])%s(?![\w.-])" % re.escape(n), blob)]


def where_shown(mdir, name, texts):
    """["M01 presentation, slide s01", "M01 tasks, q03" ...] - every place a shipped page shows the picture"""
    m, out = module_label(mdir), []
    rx = re.compile(r"(?<![\w.-])%s(?![\w.-])" % re.escape(name))
    for rel, text in texts:
        hits = [h.start() for h in rx.finditer(text)]
        if not hits:
            continue
        what = ("presentation" if rel.startswith("presentation/") else "plan" if rel.startswith("instructor/")
                else "final assessment" if rel.startswith("assessment/final") else "module check" if rel.startswith("assessment/")
                else "tasks" if rel.startswith("tasks/") else rel)
        ids = []
        for h in hits:
            sec = None
            for s in re.finditer(r'<section\b[^>]*?\b(?:id|data-script)="([^"]+)"', text[:h]):
                sec = s.group(1)
            if sec and sec not in ids:
                ids.append(sec)
        if what == "presentation" and ids:
            out.append("%s presentation, slide %s" % (m, ", ".join(ids)))
        elif ids and what in ("tasks", "module check", "final assessment"):
            out.append("%s %s, %s" % (m, what, ", ".join(ids)))
        else:
            out.append("%s %s" % (m, what))
    return out


PHOTO_TASKS = ("hotspot", "spot_the_hazard", "label_diagram", "read_instrument")


def task_photo_notes(script, build, mdir):
    """2.52.0 (IGF M01/M02: no task page showed a real photograph; M02's licensed fire-plan photo went unused although its
    Sub-ILO is reading a fire control plan) - each question answered on a picture (tap the place, spot the hazard, label,
    read the instrument) whose subject is what a real photograph of the module's own pool shows: the photo and the
    build-sheet line that would use it. A note, never a block - whether the photo fits the question is the author's call"""
    pool = [(n, m) for n, m, d, _ in photo_pool(mdir) if os.path.abspath(d) == os.path.abspath(mdir)]
    sheet, out = build.get("screens") or {}, []
    for q in [s for s in script.get("screens", []) if s.get("kind") in cs.TASKS and cs.mech(s) in PHOTO_TASKS]:
        b = sheet.get(q["id"]) or {}
        if (b.get("figure") or "").lower().endswith(IMAGES):
            continue                                       # already on a photograph
        subject = norm(" ".join(str(x) for x in [q.get("question"), q.get("answer"), q.get("visual")] + list(q.get("options") or [])))
        for n, meta in pool:
            # a thing of two words or more, said whole ("fire control plan"); one word only when it names one thing
            # ("airlock", never "tank")
            hit = next((x for x in meta.get("shows") or [] if norm(x) and (len(norm(x)) >= 2 or (norm(x)[0] not in GENERIC
                        and len(norm(x)[0]) > 4)) and any(subject[i:i + len(norm(x))] == norm(x)
                                                           for i in range(len(subject) - len(norm(x)) + 1))), None)
            if not hit:
                continue
            line = {"figure": "assets/img/" + n}
            if cs.mech(q) in ("hotspot", "spot_the_hazard"):
                line["areas"] = {x: "[left, top, width, height] in % of the photo" for x in cs.answer_items(q)[0]}
            elif cs.mech(q) == "label_diagram":
                line["labels"] = {x: {"at": "[left, top, width, height] in % of the photo"} for x in (cs.answer_items(q)[0] or [])}
            out.append("%s (%s, %s): the real photograph %s shows \"%s\" - build-sheet line: \"%s\": %s"
                       % (cs.place(script, q["id"]), q["id"], cs.mech(q), n, hit, q["id"], json.dumps(line, ensure_ascii=False)))
            break
    return out


def ship_only_shown(mdir):
    """2.52.0 (IGF M01/M02 benchmark: M01 shipped an AI picture and an M07 photo it never shows, M02 seven pictures) - after a
    build, every picture in assets\\img\\ that no built page, style or script of the module names is moved, with its record,
    to assets\\img\\_unused\\ - kept for the course (an L57 thumbnail or the build sheet brings it back), but left out of
    the classroom package. Each shown picture's "used_in" is rewritten from where the pages really show it.
    Returns (the pictures left out, the records whose "used_in" changed)."""
    img = os.path.join(mdir, "assets", "img")
    if not os.path.isdir(img):
        return [], []
    texts = []
    for dp, dirs, fs in os.walk(mdir):
        dirs[:] = [x for x in dirs if not x.startswith("_") and os.path.abspath(os.path.join(dp, x)) != os.path.abspath(img)]
        for f in fs:
            if f.lower().endswith(SHOWN_EXT) and not f.startswith("_"):     # a record (_photo_meta.json ...) shows nothing
                p = os.path.join(dp, f)
                texts.append((os.path.relpath(p, mdir).replace("\\", "/"), io.open(p, encoding="utf-8", errors="replace").read()))
    mp = os.path.join(img, "_photo_meta.json")
    try:
        meta = json.load(io.open(mp, encoding="utf-8")) if os.path.isfile(mp) else {}
    except ValueError:
        meta = {}
    left, changed = [], []
    for name in sorted(f for f in os.listdir(img) if f.lower().endswith(IMAGES) and os.path.isfile(os.path.join(img, f))):
        places = where_shown(mdir, name, texts)
        if not places:
            os.makedirs(os.path.join(img, UNUSED), exist_ok=True)
            os.replace(os.path.join(img, name), os.path.join(img, UNUSED, name))
            left.append(name)
            continue
        rec = meta.get(name)
        if isinstance(rec, dict) and rec.get("used_in") != "; ".join(places):
            rec["used_in"] = "; ".join(places)
            changed.append(name)
    if changed:
        cs.save(mp, meta)
    for name in left:
        move_record(img, os.path.join(img, UNUSED), name)
    return left, changed


def other_modules(mdir):
    root = os.path.dirname(os.path.abspath(mdir))
    return sorted(os.path.join(root, x) for x in os.listdir(root)
                  if os.path.join(root, x) != os.path.abspath(mdir) and os.path.isdir(os.path.join(root, x, "assets")))


# ------------------------------------------------------------------ L58: every photograph once in the whole course
def photo_id(d, rel, meta=None):
    """what makes two files the same photograph: where it came from (url_or_origin), else the same bytes - so a
    copy under another name in another module is still the same picture"""
    meta = meta if meta is not None else photo_meta(d, rel)
    u = str((meta or {}).get("url_or_origin") or "").strip().lower()
    if u:
        return "u:" + u
    try:
        return "h:" + hashlib.sha256(io.open(os.path.join(d, rel), "rb").read()).hexdigest()
    except OSError:
        return "f:" + rel


_LOOKS = {}
LOOK_ALIKE = 6      # bits of 64: one photograph resized or saved again is 0-1 apart, two different IGF photos 17 or more


def photo_look(d, rel):
    """the picture's look as 64 bits - a difference hash of its 9 x 8 grey thumbnail - or None when it cannot be read.
    2.62.1: L58 by record and bytes alone missed one photograph saved twice under two names (IGF M02 v262: the same
    Commons photo as m02_viking_grace_tanks_at_yard.jpg and m01_typec_tanks_shipyard.jpg, "Own work" and no origin)"""
    p = os.path.join(d, rel)
    try:
        k = (os.path.abspath(p), os.path.getmtime(p))
    except OSError:
        return None
    if k not in _LOOKS:
        try:
            from PIL import Image
            with Image.open(p) as im:
                px = im.convert("L").resize((9, 8), Image.LANCZOS).tobytes()
            h = sum(1 << i for i, (r, c) in enumerate((r, c) for r in range(8) for c in range(8))
                    if px[r * 9 + c] > px[r * 9 + c + 1])
            # a plain or evenly shaded picture (a flat colour, a gradient) has too little in it to tell two apart
            _LOOKS[k] = h if 8 <= bin(h).count("1") <= 56 else None
        except Exception:                                  # noqa: BLE001 - an SVG, a broken file: no look, no match
            _LOOKS[k] = None
    return _LOOKS[k]


def same_look(a, b):
    return a is not None and b is not None and bin(a ^ b).count("1") <= LOOK_ALIKE


def looks_in(d, page):
    """[(look, "M01 s04", placed by hand?, rel)] for every photograph a built deck shows - as shown_in, by look"""
    out = []
    for sec in re.finditer(r'<section [^>]*\bid="([^"]+)".*?</section>', page, re.S):
        thumbs = set(IMG_SRC.findall("".join(STRIP.findall(sec.group(0)))))
        for rel in set(IMG_SRC.findall(sec.group(0))):
            if rel.startswith("assets/img/"):
                out.append((photo_look(d, rel), "%s %s" % (module_label(d), sec.group(1)), rel not in thumbs, rel))
    return out


def module_label(d):
    m = re.search(r"(\d+)$", os.path.basename(os.path.abspath(d)))
    return "M%02d" % int(m.group(1)) if m else os.path.basename(d)


STRIP = re.compile(r'<div class="photo-strip".*?</div>', re.S)


def shown_in(d, page):
    """{photo: ("M01 s04", placed by hand?)} for every photograph a built deck shows. A thumbnail (L57) is not placed
    by hand: it gives way on its module's next build"""
    out = {}
    for sec in re.finditer(r'<section [^>]*\bid="([^"]+)".*?</section>', page, re.S):
        thumbs = set(IMG_SRC.findall("".join(STRIP.findall(sec.group(0)))))
        for rel in IMG_SRC.findall(sec.group(0)):
            if rel.startswith("assets/img/"):
                out.setdefault(photo_id(d, rel), ("%s %s" % (module_label(d), sec.group(1)), rel not in thumbs))
    return out


def shown_elsewhere(mdir, looks=None):
    """the photographs the course's other built decks already show; looks = a list to fill with looks_in's rows"""
    out = {}
    for d in other_modules(mdir):
        p = os.path.join(d, "presentation", "index.html")
        if os.path.isfile(p):
            page = io.open(p, encoding="utf-8").read()
            for k, v in shown_in(d, page).items():
                out.setdefault(k, v)
            if looks is not None:
                looks += looks_in(d, page)
    return out


def bring_in(mdir, name, meta, src):
    """a photograph of another module of the course, copied into this one with its record, so the module ships whole"""
    import shutil
    dst = os.path.join(mdir, "assets", "img", name)
    if os.path.abspath(src) == os.path.abspath(mdir):  # this module's own, left out of the package before: back in
        restore(mdir, [name])
        return
    if not os.path.isfile(dst):
        shutil.copyfile(img_file(src, name), dst)
    p = os.path.join(mdir, "assets", "img", "_photo_meta.json")
    own = json.load(io.open(p, encoding="utf-8")) if os.path.isfile(p) else {}
    if name not in own:
        own[name] = dict(meta, copied_from=os.path.basename(src))
        cs.save(p, own)


def part_photos(lines, fig, on_slide, mdir, pool, notes, where, taken=None, refuse=(), not_things=()):
    """L57: each real thing a drawing names gets its real photograph beside the drawing - a small tappable photo
    that opens in the L56 panel. Matched by the photo's "shows"; a thing with no photo is noted for the list.
    L58: a photograph the course already shows anywhere (`taken`) is never shown again - a different one, or none.
    `not_things` (build sheet "not_things", 2.49.1): words the drawing writes that are no real thing - an axis, a line
    of a chart - are left off the list altogether (`refuse` = "no photo fits", which stays on it)"""
    strip, taken = [], taken if taken is not None else {}
    for num, name in drawn_parts(lines, fig):
        if any(same_thing(name, x) for x in not_things):
            continue
        if any("assets/img/" + n in on_slide and any(shows_it(x, name) for x in m.get("shows") or []) for n, m, _, _ in pool):
            continue                                      # its photograph is already on the slide
        if any(same_thing(name, x) for x in refuse):
            if is_thing(name):                            # the build sheet says no photo we have fits how it is drawn here
                notes.append((where, num, name))
            continue
        hit = next(((n, m, d, pid) for n, m, d, pid in pool if pid not in taken
                    and any(shows_it(x, name) for x in m.get("shows") or [])), None)
        if not hit:
            if is_thing(name):
                notes.append((where, num, name))
            continue
        if len(strip) >= cs.MEDIA["floors"].get("photo_strip_max", 4):
            continue
        n, meta, d, pid = hit
        if os.path.abspath(d) != os.path.abspath(mdir) or not os.path.isfile(os.path.join(mdir, "assets", "img", n)):
            bring_in(mdir, n, meta, d)
        rel = "assets/img/" + n
        taken[pid] = where
        label = ("%d · " % num if num else "") + name
        alt = first_sentence(meta.get("description")) or name
        strip.append('<figure class="pthumb"><img src="../%s" alt="%s" data-name="%s"%s><figcaption>%s%s</figcaption></figure>'
                     % (a(rel), a(alt), a(label), photo_panel(meta, credit_line(meta), rel, [], where),
                        '<b>%d</b> ' % num if num else "", e(name)))
    return ('<div class="photo-strip" data-script-ignore>%s</div>' % "".join(strip)) if strip else ""


FILL_BOX = re.compile(r'\s*<\w+\b[^>]*\bclass="[^"]*\bfill\b')
OWN_BOX = re.compile(r'\s*<div class="fill fig\b')            # the compiler's own column (fill(), a kit figure)


KIT_SCREEN = re.compile(r'<div class="kit-screen">(<svg data-kit="#([\w-]+)"[^>]*></svg>)</div>')


def over_figure(fig, inset, over, probs, where):
    """an inset photograph laid over a blank part of a kit drawing (owner, 2026-10-16: keep the photo, but never at the
    cost of the drawing's size): "over": {"x": 140, "y": 10, "w": 180} in the drawing's own units. The photo stays an
    <img> - it opens full screen with its record - and the drawing keeps the whole column. Returns (figure, "") or,
    when it cannot be placed, (figure, inset) so the photo goes where it would have gone."""
    m = KIT_SCREEN.search(fig or "")
    spec = re.search(r'<script type="application/json" id="%s">(.*?)</script>' % re.escape(m.group(2)), fig, re.S) if m else None
    try:
        sw, sh = json.loads(spec.group(1)).get("size") or (0, 0)
        x, y, w = float(over["x"]), float(over["y"]), float(over["w"])
    except (AttributeError, ValueError, TypeError, KeyError):
        probs.append("%s: \"over\" places a photo on a figure-kit drawing, in its units: {\"x\": 140, \"y\": 10, \"w\": 180}" % where)
        return fig, inset
    if not (sw and sh and 0 <= x and 0 <= y and x + w <= sw and y < sh):
        probs.append("%s: \"over\" puts the photo outside the drawing (%g x %g)" % (where, sw, sh))
        return fig, inset
    style = "left:%.2f%%;top:%.2f%%;width:%.2f%%" % (100 * x / sw, 100 * y / sh, 100 * w / sw)
    photo = inset.replace('<figure class="inset">', '<figure class="inset over" style="%s">' % style, 1)
    return fig.replace(m.group(0), '<div class="kit-screen"><div class="kit-holder">%s%s</div></div>' % (m.group(1), photo), 1), ""


# 2.49.1 - an inset laid under a drawing takes its own height out of the drawing's panel. Measured on IGF M06 s05 at
# 1280 x 800: the wide column is 682 px wide, its panel 417 px high, the inset (photo, 26 vh up to 230 px, + caption) ~220 px
PANEL_W, INSET_H, UNDER_MIN_SHARE = 682.0, 220.0, 0.6


def under_share(fig):
    """(share, panel height) - the part of the drawing's panel the drawing keeps once an inset sits under it, from the
    drawing's own shape (a kit spec's "size", an SVG's viewBox); None when the shape is not known"""
    size = None
    for m in JSON_DATA.finditer(fig or ""):
        try:
            sz = json.loads(m.group(1).replace("<\\/", "</")).get("size")
            size = [float(x) for x in sz][:2]
            break
        except (ValueError, TypeError, AttributeError):
            continue
    if not size:
        m = re.search(r'viewBox="\s*[-\d.]+[ ,]+[-\d.]+[ ,]+([\d.]+)[ ,]+([\d.]+)"', fig or "")
        size = [float(m.group(1)), float(m.group(2))] if m else None
    if not size or size[0] <= 0 or size[1] <= 0:
        return None
    panel = PANEL_W * size[1] / size[0]
    return max(0.0, (panel - INSET_H) / panel), panel


def under_figure(fig, extra):
    """put something under the drawing, inside its box when the drawing is its own .fill"""
    if not FILL_BOX.match(fig):
        return fig + "\n" + extra
    # a function, not a replacement string: a caption or credit with a backslash (C:\Users\...) is text, not an escape
    return re.sub(r"</div>\s*$", lambda _: extra + "\n</div>", fig.rstrip(), count=1)


def by_thing(notes):
    """one row per thing, with every slide that draws it: "Tank connection space · s04 (2), s05, s10" """
    rows = []
    for w, num, name in notes:
        row = next((r for r in rows if same_thing(r[0], name)), None)
        if row is None:
            row = (name, [])
            rows.append(row)
        ref = "%s (%d)" % (w, num) if num else w
        if ref not in row[1] and not any(x.split(" ")[0] == w for x in row[1]):
            row[1].append(ref)
    return ["%s · %s" % (name, ", ".join(refs)) for name, refs in rows]


def write_to_take(course, script, notes):
    """working_claude\\PHOTOS_TO_TAKE.md - this module's section rewritten on every build, the rest kept"""
    p = workspace.claude_path(course, TO_TAKE)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    m = cs.mid(script.get("module"))
    head = ("# Photos to take at Novikontas\n\n"
            "Every real thing a drawing names that has no real photograph yet (L57). The `## Mnn` sections are written by\n"
            "compile_module.py on every build - add a photo with its `shows` in `_photo_meta.json` and build again.\n"
            "Notes of your own go under `## Notes`, which is never touched.\n")
    text = io.open(p, encoding="utf-8").read() if os.path.isfile(p) else head + "\n## Notes\n"
    rows = ["- " + r for r in by_thing(notes)] or ["- every drawn thing has its photograph"]
    sec = "## %s · %s\n\n%s\n" % (m, script.get("title") or "", "\n".join(rows))
    parts = re.split(r"(?m)^(?=## )", text)
    keep = [x for x in parts if not x.startswith("## %s " % m) and not x.startswith("## %s\n" % m)]
    i = next((k for k, x in enumerate(keep) if x.startswith("## ")), len(keep))
    sections = sorted([x for x in keep[i:] if not x.startswith("## Notes")] + [sec], key=lambda x: x[:7])
    notes_sec = [x for x in keep[i:] if x.startswith("## Notes")] or ["## Notes\n"]
    out = "".join(keep[:i]).rstrip() + "\n\n" + "\n".join(x.rstrip() + "\n" for x in sections + notes_sec)
    with io.open(p, "w", encoding="utf-8", newline="\n") as f:
        f.write(out)
    return p


# ------------------------------------------------------------------ facts a drawing states (2.63.0)
# IGF M01 v262 s02: the kit drawing said "LNG flashpoint −188 °C" - not in the approved script, every check green. The words
# on a slide are the script's by construction (check_script_match); a drawing's are not. A number with its unit that a
# figure prints must be in the approved script or in what the course read from its knowledge base (working_claude: the
# retrieval packs, the fact sheets, the text extracts) - or the build sheet names where it is from ("facts").
FACT_UNIT = (r"°\s?C|°\s?F|degrees?\s+C\b|K\b|barg?\b|mbar\b|kPa\b|MPa\b|%\s?LEL\b|%|ppm\b|m³|m3\b|mm\b|cm\b|km\b|m\b|kg\b|"
             r"tonnes?\b|t\b|kW\b|MW\b|kV\b|V\b|min\b|h\b|s\b|nm\b|kn\b|knots\b")
# a sign is "minus", a true minus, or a dash right before the digits - "Vent mast - 6 m" is a separator, not -6 m
FACT = re.compile(r"(?<![\w.,])(minus\s+|−\s?|[-–](?=\d))?(\d+(?:[.,]\d+)?)(?:\s?(?:-|–|to)\s?(\d+(?:[.,]\d+)?))?\s?(" + FACT_UNIT + r")",
                  re.I)
FACT_SKIP = {"id", "type", "d", "fluid", "kind", "dir", "captionAt", "class", "from", "fromIn", "src", "look", "mat", "shade",
             "fill", "tone", "side", "anchor", "path", "ease", "mode"}


def fact_unit(u):
    u = re.sub(r"\s+", "", u.lower())
    return {"degreesc": "°c", "degreec": "°c", "°c": "°c", "°f": "°f", "barg": "bar", "m3": "m³", "tonne": "t", "tonnes": "t",
            "knots": "kn", "%lel": "%"}.get(u, u)


def facts_in(text):
    """[(the fact as written, (sign, value, unit))] - a range is two facts"""
    out = []
    for m in FACT.finditer(text or ""):
        unit = fact_unit(m.group(4))
        for k, v in enumerate((m.group(2), m.group(3))):
            if v:
                v = v.replace(",", ".")
                v = v.rstrip("0").rstrip(".") if "." in v else v
                out.append((m.group(0).strip(), ("-" if m.group(1) and k == 0 else "", v, unit)))
    return out


def figure_texts(raw):
    """the words a figure source prints: a kit spec's strings (not its ids, types or path data), an SVG's / fragment's text"""
    out = []

    def walk(x, key=None):
        if isinstance(x, dict):
            for k, v in x.items():
                if k not in FACT_SKIP:
                    walk(v, k)
        elif isinstance(x, list):
            for v in x:
                walk(v, key)
        elif isinstance(x, str) and key not in FACT_SKIP:
            out.append(x)
    try:
        walk(json.loads(raw))
        return out
    except ValueError:
        pass
    for m in re.finditer(r'<script type="application/json"[^>]*>(.*?)</script>', raw, re.S):
        try:
            walk(json.loads(m.group(1).replace("<\\/", "</")))
        except ValueError:
            pass
    body = re.sub(r"<script\b.*?</script>|<style\b.*?</style>", " ", raw, flags=re.S | re.I)
    out.append(html.unescape(re.sub(r"<[^>]+>", " ", body)))
    return out


def fact_corpus(course, script):
    """every (sign, value, unit) the approved script and the course's sources state"""
    texts = [json.dumps(script, ensure_ascii=False)]
    wc = workspace.claude_path(course)
    for d in (wc, os.path.join(wc, "retrieval")):
        for f in sorted(os.listdir(d)) if os.path.isdir(d) else []:
            if f.lower().endswith((".md", ".txt")) and os.path.isfile(os.path.join(d, f)):
                texts.append(io.open(os.path.join(d, f), encoding="utf-8", errors="replace").read())
    return {k for t in texts for _, k in facts_in(t)}


def unsupported_facts(script, build, figdir, mdir, course):
    """[(where, figure, fact as drawn)] for each number with a unit a figure of the module prints that neither the approved
    script nor the course's sources state, and the build sheet does not cite"""
    corpus, found, seen = None, [], set()
    for sid, b in sorted((build.get("screens") or {}).items()):
        cited = {re.sub(r"\s+", "", k.lower()) for k in (b.get("facts") or {})}
        for rel in (b.get("figure"), b.get("aside")):
            if not rel or not str(rel).lower().endswith((".kit.json", ".svg", ".html")):
                continue
            raw, err = read_figure(mdir, rel, figdir)
            if err or not raw:
                continue
            for text in figure_texts(raw):
                for shown, key in facts_in(text):
                    if (sid, shown) in seen or re.sub(r"\s+", "", shown.lower()) in cited:
                        continue
                    corpus = fact_corpus(course, script) if corpus is None else corpus
                    if key not in corpus:
                        seen.add((sid, shown))
                        found.append((cs.place(script, sid) if sid in {s["id"] for s in script.get("screens", [])} else sid, rel, shown))
    return found


# ------------------------------------------------------------------ one slide
def composition(s, b, is_photo, has_fig):
    c = b.get("composition")
    if c:
        return c
    lay = s.get("layout")
    if lay == "visual_full":
        # 2.52.0 - words over a full-screen photograph sit in a fixed column on a scrim: past STAGE_MAX_WORDS they spill off
        # the slide (IGF M01 s01, 70 words: 18 px at 1280 x 800, 42 px at 1024 x 768, every benchmark build; M02 s01, 82
        # words: 8 / 32 px), and M03-M15 each set "two-col" by hand. A long one is the photo beside the words.
        # 2.62.1 - in its own column (wide-left), not the split photo: the split's words sit in one fixed box with no parts,
        # and with the larger logo the openings spilled 19-46 px in all 5 runs of the M01 / M02 build (14 of 64 logged
        # runs since 2.56, M01 M02 M13); a builder's "parts" there did nothing. The column takes parts and is measured
        if is_photo:
            return "photo" if cs.wc(s.get("text", "")) <= STAGE_MAX_WORDS else "wide-left"
        return "stage"
    if lay == "split":
        return "two-col" if has_fig else "flow"
    if lay == "visual_wide":
        if not has_fig:
            return "flow"
        return "stage" if cs.wc(s.get("text", "")) <= STAGE_MAX_WORDS else "wide-right"
    return "two-col" if has_fig else "flow"


def fill(fig):
    """the picture's box: .fill makes it take the room the words leave. A fragment whose own outer element is
    already a .fill is its own box - wrapping it again would leave its contents no width (a 3D canvas at 0 px)"""
    if re.match(r'\s*<\w+\b[^>]*\bclass="[^"]*\bfill\b', fig or ""):
        return fig
    return '<div class="fill fig">%s</div>' % (fig or "")


def inset_html(mdir, ins, probs, where):
    """a real photograph under the words (L52): {"photo": "assets/img/x.jpg", "caption": "..."} - the caption is
    instructor-chosen context with the credit, marked data-script-ignore so QA sees it counted"""
    rel = (ins.get("photo") or "").replace("\\", "/")
    if not os.path.isfile(os.path.join(mdir, rel)):
        probs.append("%s: its inset photograph %s is not in the module folder" % (where, rel or "(none named)"))
        return ""
    meta = photo_meta(mdir, rel)
    credit = ins.get("credit") or credit_line(meta, with_title=not ins.get("caption"))
    caption = (ins.get("caption") or "").strip()
    if is_generated(meta):              # no credit line for a generated picture
        credit = ""
    cap = caption[:1].upper() + caption[1:]           # 2.63.0: the credit is in the full-screen view, never on the slide
    alt = ins.get("alt") or first_sentence(ins.get("caption")) or first_sentence(meta.get("description"))
    return ('<figure class="inset"><img src="../%s" alt="%s"%s>%s</figure>'
            % (a(rel), a(alt), photo_panel(meta, credit or credit_line(meta), rel, probs, where),
               '<figcaption data-script-ignore>%s</figcaption>' % e(cap) if cap else ""))


def task_href(code, short, mdir, script=None):
    """the set's one page, as the deck links it: assessment\\check.html / final.html (final_a.html, final_b.html when the
    final has variants), or tasks\\<code>_<title>.html - a page already there for this code keeps its name, so the deck
    and task_pages.py always agree"""
    if is_check(code):
        return check_page(code, script)
    tdir = os.path.join(mdir, "tasks")
    have = sorted(f for f in (os.listdir(tdir) if os.path.isdir(tdir) else [])
                  if f.lower().startswith(code.lower() + "_") and f.lower().endswith(".html"))
    return "../tasks/" + have[0] if len(have) == 1 else "../tasks/%s_%s.html" % (code.lower(), slug(short))


def attrs(d):
    return " ".join('%s="%s"' % (k, a(str(v))) for k, v in d.items() if v not in (None, ""))


# ------------------------------------------------------------------ the layout templates (L61)
def template_attrs(d, tid, variant, split=None):
    """name the slide's template on it: data-template="<id>.v1" and data-variant - gb_layouts.css styles by them, so the
    slide's classes stay what every check already reads"""
    d["data-template"] = "%s.v%d" % (tid, TEMPLATES[tid]["version"])
    d["data-variant"] = variant
    if split:
        d["style"] = "--lt-text:%g" % round(100 * split, 1)
    return d


def is_steps(lines):
    """the script numbers its own steps 1, 2, 3 ... - all lines but at most one (a lead) are those steps"""
    nums = [int(m.group(1).rstrip(".)")) for m in (STEP_NUM.match(x) for x in lines) if m]
    return len(nums) >= 2 and nums == list(range(1, len(nums) + 1)) and len(nums) >= len(lines) - 1


def is_table(lines):
    rows = [x for x in lines if " | " in x]
    return len(rows) >= 2 and len({len(x.split(" | ")) for x in rows}) == 1


def is_3d(s):
    return (cs.MEDIA["visual_kinds"].get(s.get("visual_kind") or "", {}) or {}).get("family") == "3d"


def auto_template(s, b, comp, is_photo, has_fig, lines, split_photo, photo_col):
    """the template the approved script and the build sheet already describe"""
    words = cs.wc(" ".join(lines))
    side = "figure-left" if b.get("figure_first") else "figure-right"
    if comp == "opener":
        return "opening", "photo" if is_photo else "statement"
    if is_photo and comp == "photo":
        return "photo-explain", "split" if split_photo else "full"
    if photo_col:                       # 2.63.0: past the column's measured budget, its words in parts beside the photo
        return ("content-in-parts", "with-figure") if words > PARTS_FROM else ("photo-explain", "column")
    if not has_fig:
        return ("procedure", "text-only") if is_steps(lines) else ("explain-figure", "text-only")
    if comp == "stage":
        return "figure-stage", "figure"
    if is_table(lines):
        return "reference-table", "with-figure"
    if is_steps(lines):
        return "procedure", "with-figure"
    if words > PARTS_FROM:
        return "content-in-parts", "with-figure"
    if words > DENSE_WORDS:
        return ("long-explanation", "model") if is_3d(s) else ("reading-with-figure", side)
    return "explain-figure", side


TEMPLATE_COMPOSITION = {"figure-stage": "stage", "opening": "opener", "explain-figure": "two-col", "reading-with-figure": "two-col",
                        "long-explanation": "two-col", "procedure": "two-col", "content-in-parts": "two-col",
                        "three-content-blocks": "two-col", "reference-table": "two-col"}


def asked_composition(b):
    """a template asked for in the build sheet decides the composition, unless the sheet names one itself"""
    tid = (b.get("template") or "").split(".v")[0]
    if tid in TEMPLATE_COMPOSITION and not b.get("composition"):
        return dict(b, composition=TEMPLATE_COMPOSITION[tid])
    return b


def line_ranges(spec, n, howmany=None):
    """[[1, 3], [4, 6]] - line ranges in order, each line once; None when they are not that"""
    try:
        rs = [(int(r[0]), int(r[-1])) for r in spec]
    except (TypeError, ValueError, IndexError):
        return None
    if howmany and len(rs) != howmany:
        return None
    if any(lo < 1 or hi > n or lo > hi for lo, hi in rs) or any(a_[1] >= b_[0] for a_, b_ in zip(rs, rs[1:])):
        return None
    return rs


def pick_template(s, b, comp, is_photo, has_fig, lines, split_photo, photo_col, probs, where):
    auto = auto_template(s, b, comp, is_photo, has_fig, lines, split_photo, photo_col)
    want = (b.get("template") or "").split(".v")[0]
    if not want:
        tid, var = auto
    elif want not in TEMPLATES:
        probs.append("%s: the build sheet asks for the template \"%s\" - the templates are %s (L61)"
                     % (where, b["template"], ", ".join(sorted(TEMPLATES))))
        tid, var = auto
    else:
        tid, var = want, auto[1] if auto[0] == want else TEMPLATES[want]["variants"][0]
        why = None
        if tid in ("task-launch", "recap"):
            why = "is for a task slide or the module's recap, not a teaching slide"
        elif tid == "photo-explain" and not is_photo:
            why = "needs a photograph"
        elif tid not in ("explain-figure", "procedure", "opening") and not has_fig:
            why = "needs a picture beside the words"
        elif tid == "procedure" and not is_steps(lines):
            why = "needs steps the script numbers itself (1, 2, 3 ...)"
        elif tid == "reference-table" and not is_table(lines):
            why = "needs table rows - the cells of a line separated by \" | \""
        elif tid == "long-explanation" and not is_3d(s):
            why = "is the 3D template - the slide's picture is not a 3D model"
        elif tid == "compare-two" and not (line_ranges(b.get("blocks"), len(lines), 2) and b.get("figure_b")):
            why = "needs \"blocks\": two line ranges and \"figure_b\", the second picture"
        elif tid == "three-content-blocks" and not line_ranges(b.get("blocks"), len(lines), 3):
            why = "needs \"blocks\": three line ranges"
        if why:
            probs.append("%s: the build sheet asks for the template %s, which %s (L61)" % (where, tid, why))
            tid, var = auto
    if b.get("variant") and tid == want:
        if b["variant"] in TEMPLATES[tid]["variants"]:
            var = b["variant"]
        else:
            probs.append("%s: the template %s has no variant \"%s\" - its variants are %s (L61)"
                         % (where, tid, b["variant"], ", ".join(TEMPLATES[tid]["variants"])))
    if not has_fig and (tid, var) not in FIGURE_FREE and tid != "photo-explain":
        var = "text-only" if "text-only" in TEMPLATES[tid]["variants"] else var
    return tid, var


def auto_parts(lines, ranges=None):
    """the slide's lines in readable parts, in order: the build sheet's "parts", or about PART_WORDS words each"""
    if ranges:
        return [list(range(lo, hi + 1)) for lo, hi in ranges]
    total = cs.wc(" ".join(lines))
    k = max(2, -(-total // PART_WORDS))
    target = total / float(k)
    parts, cur, acc = [], [], 0
    for i, x in enumerate(lines, 1):
        w = cs.wc(x)
        if cur and acc + w / 2.0 > target and len(parts) < k - 1:
            parts.append(cur)
            cur, acc = [], 0
        cur.append(i)
        acc += w
    parts.append(cur)
    return parts


def parts_html(lines, parts, emph):
    """content-in-parts: every part on the slide, the first shown; Next walks them (gb_deck.js), the numbered tabs too"""
    out = ['<div class="lt-parts" data-parts="%d">' % len(parts)]
    for k, ix in enumerate(parts, 1):
        words = words_html([lines[i - 1] for i in ix], first_statement=(k == 1), emph=emph, idx=ix)
        out.append('  <div class="lt-part%s" data-part="%d">' % (" on" if k == 1 else "", k))
        out += ["    " + y for y in words]
        out.append("  </div>")
    out.append('  <div class="lt-tabs">%s</div>' % "".join(
        '<button type="button" class="lt-tab%s" data-part="%d" aria-label="Part %d of %d">%d</button>'
        % (" on" if k == 1 else "", k, k, len(parts), k) for k in range(1, len(parts) + 1)))
    out.append("</div>")
    return out


def table_html(lines, idx=None):
    """reference-table: the lines with " | " are the rows; the separator stays in the line (hidden), so the slide
    still says exactly the approved words"""
    idx = list(idx or range(1, len(lines) + 1))
    pre, rows, post = [], [], []
    for i, x in zip(idx, lines):
        (rows if " | " in x else (post if rows else pre)).append((i, x))
    out = words_html([x for _, x in pre], idx=[i for i, _ in pre]) if pre else []
    tr = []
    for i, x in rows:
        cells = x.split(" | ")
        tr.append('<tr data-script-field="text" data-i="%d">%s</tr>' % (i, "".join(
            '<td>%s%s</td>' % (e(c), '<span class="lt-sep"> | </span>' if n < len(cells) - 1 else "") for n, c in enumerate(cells))))
    out.append('<table class="lt-table"><tbody>%s</tbody></table>' % "".join(tr))
    if post:
        out += words_html([x for _, x in post], first_statement=False, idx=[i for i, _ in post])
    return out


def shape_of(tid, variant, left=False):
    """the shape the eye sees (L62) - two templates that look alike are one shape"""
    if tid in ("task-launch", "recap", "opening", "compare-two"):
        return tid
    if variant == "text-only":
        return "text"
    if tid == "photo-explain" and variant in ("full", "split"):
        return "photo-full" if variant == "full" else "photo-framed"
    if tid == "figure-stage":
        return "picture-top"
    return "picture-left" if left or variant == "figure-left" else "picture-right"


def layout_key(slide):
    """what the eye sees of a slide (L62): its shape and its ground - light, or dark / photo"""
    t = re.search(r'\bdata-template="([\w-]+)\.v\d+"', slide)
    v = re.search(r'\bdata-variant="([\w-]+)"', slide)
    c = re.search(r'<section class="([^"]*)"', slide)
    body = re.search(r'<div class="slide-body ([^"]*)"', slide)
    ground = "dark" if c and re.search(r"\b(dark|photo)\b", c.group(1)) else "light"
    left = bool(body and "fig-first" in body.group(1).split())
    return (shape_of(t.group(1) if t else "", v.group(1) if v else "", left), ground)


LEFT = {"explain-figure": "figure-left", "reading-with-figure": "figure-left", "long-explanation": "figure-left",
        "procedure": "figure-left", "content-in-parts": "figure-left", "three-content-blocks": "figure-left",
        "reference-table": "figure-left"}
RIGHT = {"explain-figure": "figure-right", "reading-with-figure": "figure-right", "long-explanation": "model",
         "procedure": "with-figure", "content-in-parts": "with-figure", "three-content-blocks": "with-figure",
         "reference-table": "with-figure"}


def layout_options(tid, variant, is_photo, words, b, comp, own_left, own_dark, dark_ok=True):
    """the ways one slide can be built - the first is its own; each a dict the slide builder applies (L62)"""
    own = {"tid": tid, "variant": variant, "comp": None, "first": own_left, "dark": own_dark,
           "key": (shape_of(tid, variant, own_left), "dark" if own_dark or comp == "photo" else "light")}
    opts = [own]
    if tid in ("compare-two", "opening", "recap", "task-launch"):
        return opts
    if variant == "text-only":                                   # no picture: the other ground is all there is
        return opts + [dict(own, dark=not own_dark, key=("text", "light" if own_dark else "dark"))]
    side = tid if tid in RIGHT else ("content-in-parts" if words > PARTS_FROM else "reading-with-figure" if words > DENSE_WORDS
                                     else "explain-figure")
    col = "wide-left" if is_photo else "two-col"
    # 2.62.1 - the ground is never a way to vary (owner, 2026-10-21: 80 / 20 - at least 80 % of a module's slides light;
    # the instructors: "a lot of dark slides"): a slide keeps its own ground and varies its shape. dark_ok is kept for
    # the callers: a picture made for one ground never changed it
    for dark in (bool(own_dark),):
        g = "dark" if dark else "light"
        opts.append({"tid": side, "variant": RIGHT[side], "comp": col, "first": False, "dark": dark, "key": ("picture-right", g)})
        opts.append({"tid": side, "variant": LEFT[side], "comp": col, "first": True, "dark": dark, "key": ("picture-left", g)})
        if is_photo and words <= TOP_WORDS:     # a photograph across the slide; a chart, 3D or a drawing needs its height
            opts.append({"tid": "figure-stage", "variant": "figure" if words <= STAGE_WORDS else "figure-top", "comp": "stage",
                         "first": False, "dark": dark, "key": ("picture-top", g)})
        if is_photo and words <= FRAMED_PHOTO_WORDS and own_dark:     # the framed photo is a dark slide: dark ones only
            opts.append({"tid": "photo-explain", "variant": "split", "comp": "photo", "first": False, "dark": False,
                         "key": ("photo-framed", "dark")})
    return opts


def choose_layout(opts, recent, measured_out=(), prefer=None):
    """the first way that looks unlike the last VARIETY_WINDOW slides - the slide's own first; failing that, unlike the
    slide before; failing that, its own (the build then reports the repeat). measured_out: the other ways this slide was
    built and the audit found did not fit (build_module.py, 2.62.0) - never tried again while its words are the same.
    prefer (2.62.1): the way it was built last time, kept while it is still unlike the slide before - a fix on one slide
    no longer moves its neighbours to a new way the audit has not seen (every 2.62.0 build retried other slides)"""
    opts = opts[:1] + [o for o in opts[1:] if o["key"] not in measured_out]
    if prefer:
        p = next((o for o in opts if o["key"] == tuple(prefer)), None)
        if p and (not recent or p["key"] != recent[-1]):
            return p, p is not opts[0]
    for avoid in (recent[-VARIETY_WINDOW:], recent[-1:]):
        for o in opts:
            if o["key"] not in avoid:
                return o, o is not opts[0]
    return opts[0], False


def enlarge_photos(mdir, keep_dir, rels, notes):
    """L62: a photograph shipped smaller than PHOTO_LONG px on its long side is enlarged in the module - Lanczos and a
    light sharpening, so a projector shows a soft photograph instead of blocks of pixels. The original is kept once in
    keep_dir. Under PHOTO_LOW px it is listed too: no enlargement makes detail that is not there - find a larger one."""
    try:
        from PIL import Image, ImageFilter
    except ImportError:
        if rels:
            notes.append((None, None, "small photographs are not enlarged: the image library Pillow is not installed "
                                      "(python -m pip install pillow) - L62"))
        return []
    done = []
    for rel in sorted(set(rels)):
        if not rel.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
            continue
        p = os.path.join(mdir, rel)
        try:
            im = Image.open(p)
            im.load()
        except (OSError, ValueError):
            continue
        w, h = im.size
        if max(w, h) >= PHOTO_LONG:
            continue
        keep = os.path.join(keep_dir, os.path.basename(rel))
        if not os.path.isfile(keep):
            os.makedirs(keep_dir, exist_ok=True)
            with open(p, "rb") as src, open(keep, "wb") as dst:
                dst.write(src.read())
        k = min(4.0, PHOTO_LONG / float(max(w, h)))
        size = (int(round(w * k)), int(round(h * k)))
        fmt = (im.format or "").upper()
        if fmt in ("JPEG", "JPG") and im.mode not in ("RGB", "L"):
            im = im.convert("RGB")
        big = im.resize(size, Image.LANCZOS).filter(ImageFilter.UnsharpMask(radius=1.4, percent=60, threshold=2))
        if fmt == "PNG":
            big.save(p, "PNG", optimize=True)
        elif fmt == "WEBP":
            big.save(p, "WEBP", quality=90)
        else:
            big.save(p, "JPEG", quality=90, optimize=True, progressive=True)
        done.append((rel, w, h, size))
        if max(w, h) < PHOTO_LOW:
            notes.append((None, None, "%s was only %d x %d px - enlarged to %d x %d so it is not blocky, but a larger original "
                                      "would be sharper; find one (L62)" % (rel, w, h, size[0], size[1])))
    return done


def has_teaching_visual(slide):
    """for the sequence rule: a teaching slide with a picture - not a task launch or the recap (they do not count)"""
    t = re.search(r'\bdata-template="([\w-]+)\.v\d+"', slide)
    v = re.search(r'\bdata-variant="([\w-]+)"', slide)
    if not t:
        return None
    tid, var = t.group(1), v.group(1) if v else ""
    if tid in ("task-launch", "recap"):
        return None
    return (tid, var) not in FIGURE_FREE


def recap_html(s, base, m, n, total, lines, dark=False):
    """L51 - the module's closing slide, "what to take away", in the one shared design (gb_compose.css 15): one box
    per approved line, "Short title - one sentence"; the numbers are drawn by CSS, so the slide says exactly the
    approved words. No picture, no layout choice - every module the same. 2.62.1: on the light ground unless the build
    sheet asks "dark" (owner, 2026-10-21: 80 / 20)"""
    d = {"class": "slide %srecap" % ("dark " if dark else ""), "data-title": s.get("title"), "data-kind": "Summary",
         "data-block": "%s · %d" % (m, n), "data-visual": "none"}
    d.update(base)
    template_attrs(d, "recap", "cards")
    items = []
    for x in lines:
        t, sep, rest = x.partition(" - ")
        items.append('<li class="rc-item" data-script-field="text">'
                     + ('<b class="rc-t">%s</b><span class="rc-sep"> - </span><span class="rc-d">%s</span>' % (e(t), e(rest))
                        if sep else '<span class="rc-d">%s</span>' % e(x)) + "</li>")
    return ('<section %s>\n  <div class="slide-kind"><b>Summary</b> · %s · %d / %d</div>\n'
            '  <h2 data-script-field="title">%s</h2>\n  <div class="slide-body recap">\n    <ol class="rc-grid" data-n="%d">\n'
            '      %s\n    </ol>\n    <p class="rc-next" data-script-ignore>Next: the module check</p>\n  </div>\n</section>'
            % (attrs(d), m, n, total, e(s.get("title")), len(items), "\n      ".join(items)))


def active_mins(s):
    """2.52.0 - the block's learner-active minutes for check_balance.py (data-active, Track B), as the script's L49 split
    counts them: a slide marked "active", a task slide and a room activity are the trainees doing; a plain theory slide 0"""
    if not cs.minutes(s):
        return ""
    on = s.get("kind") in ("task-slide", "activity") or (s.get("kind") == "slide" and bool(s.get("active")))
    return "%g" % cs.minutes(s) if on else "0"


# build-sheet fields that never decide a slide's layout - an edit to them keeps what was measured and built (2.62.1)
NOT_LAYOUT = ("alt", "labels", "unlabel", "areas", "link_hint", "not_things", "declined_3d")


def words_key(s, b=None):
    """the slide's approved words and the build-sheet fields that decide its layout, short - a layout measured out
    (layout_avoid) or kept from the last build (layouts) holds only while they are the same. 2.62.1: an edit to a label
    or an alt text keeps it (every such edit used to forget what was measured and try the misfits again); a builder's
    own "composition", "template", "split", picture ... always wins over a remembered layout"""
    # the entry as slide_html reads it (asked_composition: a template's composition) - the same key wherever it is made
    keep = {k: v for k, v in asked_composition(b or {}).items() if k not in NOT_LAYOUT and not k.startswith("_")}
    return hashlib.sha1(("%s\n%s\n%s" % (s.get("title") or "", s.get("text") or "", json.dumps(keep, sort_keys=True)))
                        .encode("utf-8")).hexdigest()[:12]


def load_layout_avoid(work, mid_):
    """working_claude\\_build\\<M01>_layout_avoid.json - the layouts build_module.py measured out; {} when there is none.
    Every builder of the deck reads it - the compile and the studio / figure_fit alike, so a figure is measured on the
    layout the deck really has (2.62.1)"""
    try:
        return json.load(io.open(os.path.join(work, "_build", "%s_layout_avoid.json" % mid_), encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def load_layouts(work, mid_):
    """working_claude\\_build\\<M01>_layouts.json - each teaching slide's way as the last compile built it
    {sid: {"words": words_key, "key": [shape, ground]}}; {} when there is none (2.62.1)"""
    try:
        return json.load(io.open(os.path.join(work, "_build", "%s_layouts.json" % mid_), encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def measured_out(avoid, s, b=None):
    """the layouts build_module.py measured out for this slide: [(shape, ground), ...] while its words and picture are
    unchanged"""
    a = (avoid or {}).get(s.get("id")) or {}
    return [tuple(k) for k in a.get("avoid") or []] if a.get("words") == words_key(s, b) else []


def last_layout(last, s, b=None):
    """the way this slide was built at the last compile, while its words and picture are unchanged - or None"""
    a = (last or {}).get(s.get("id")) or {}
    return tuple(a["key"]) if a.get("key") and a.get("words") == words_key(s, b) else None


def slide_html(script, s, n, total, b, mdir, figdir, foot, probs, notes=None, pool=None, taken=None, build=None,
               recent=None, avoid=None, last=None):
    m = cs.mid(script.get("module"))
    sid, kind = s["id"], s["kind"]
    where = "%s (%s)" % (cs.place(script, sid), sid)
    lines = cs.lines_of(s.get("text"))
    base = {"id": sid, "data-script": sid, "data-track": "theory", "data-mins": ("%g" % cs.minutes(s)) if cs.minutes(s) else "",
            "data-active": active_mins(s), "data-foot": foot, "data-cue": (s.get("notes") or "").strip()}

    # a room activity that has its own figure (trace a path on a drawing) is laid out like a teaching slide,
    # and keeps the classroom's Task marks: its code and how the room works
    act = kind == "activity" and bool(b.get("figure"))
    if kind in ("task-slide", "activity") and not act:
        code = (s.get("opens") or "").strip() or sid.upper()
        title = s.get("title") or ""
        short = title.split(" - ", 1)[1] if " - " in title else title
        graded = is_check(code)
        # 2.62.1 - on the light ground unless the build sheet asks "dark" (owner, 2026-10-21: 80 / 20 - every task
        # launch and module check was dark: 4-6 of a 20-slide module before any teaching slide)
        d = {"class": "slide %sactivity" % ("dark " if b.get("dark") else ""), "data-title": "%s — %s" % (code, short[:1].upper() + short[1:]),
             "data-kind": "Check" if graded else "Task", "data-block": "%s · %s" % (m, code), "data-visual": "none",
             "data-activity": code}
        if kind == "task-slide":
            d["data-task-href"] = task_href(code, short, mdir, script)
            team = s.get("team") or {}
            if team:
                d.update({"data-mode": "team", "data-team-size": team.get("size", ""),
                          "data-roles": "|".join(cs.team_roles(team))})
        else:
            d["data-link-hint"] = b.get("link_hint") or (lines[0] if lines else "")
        d.update(base)
        d["data-track"] = "practice" if kind == "activity" else "theory"
        template_attrs(d, "task-launch", "room" if kind == "activity" else "check" if graded else "tablet")
        body = ['<p class="act-code" data-script-ignore>%s</p>' % e(code),
                '<h2 class="act-title" data-script-field="title">%s</h2>' % e(title)]
        pic = task_picture(mdir, b, probs, where)          # 2.63.0: the exercise's photo, else an icon that says what it is
        body.append(pic or task_icon(script, code, "room" if kind == "activity" else "check" if graded else "tablet"))
        body.append('<div class="act-lines">')
        body += ['  <p class="act-inst" data-script-field="text">%s</p>' % e(x) for x in lines]
        body.append("</div>")
        return ('<section %s>\n  <div class="slide-kind"><b>%s</b> · %s · %s</div>\n  <div class="slide-body activity">\n    %s\n  </div>\n</section>'
                % (attrs(d), d["data-kind"], m, code, "\n    ".join(body)))

    if kind == "slide" and s.get("recap"):
        return recap_html(s, base, m, n, total, lines, bool(b.get("dark")))

    b = asked_composition(b)                      # L61: a template asked for by name decides the composition
    fig, credit, is_photo = figure_html(mdir, figdir, s, b, probs, where)
    # what picture was BUILT (2.54.0) - its own name: `kind` stays the slide's kind, which L61's dense rule below reads
    # (the merge of 2.52.0 and 2.54.0 had both under one name, so a dense slide with no picture went uncaught)
    vkind = built_kind(s, fig, is_photo, photo_meta(mdir, (b.get("figure") or "").replace("\\", "/")) if is_photo else None)
    if not str(b.get("cue_kept") or "").strip():       # the operator kept the cue as it is, with their reason
        probs += cue_problems(s, fig, vkind, is_photo, build or {}, mdir, where)
    comp = composition(s, b, is_photo, bool(fig))
    if comp not in COMPOSITIONS + ("photo",):
        probs.append("%s: the build sheet asks for the layout \"%s\" - the layouts are %s" % (where, comp, ", ".join(COMPOSITIONS)))
        comp = "flow"
    if comp == "photo" and not is_photo:
        comp = "stage"
    # a photograph beside the words fills the right of the screen (two-col: the words on a scrim, fixed width) - never a
    # small photo in a column. 2.49.1: "wide-left" / "wide-right" are honoured for a photograph - a real column layout, the
    # words as wide as asked and the photo filling its own column (cropped to it), its credit line still on the slide
    split_photo = is_photo and comp == "two-col"
    photo_col = is_photo and comp in ("wide-left", "wide-right")
    if split_photo:
        comp = "photo"
    # L61 - the slide's template, and the owner's rules for it
    tid, variant = pick_template(s, b, comp, is_photo, bool(fig), lines, split_photo, photo_col, probs, where)
    nwords_all = cs.wc(" ".join(lines))
    if kind == "slide" and not fig and nwords_all > DENSE_WORDS:
        probs.append("%s: %d words and no picture beside them - dense text always has a drawing, a photograph, an animation or a "
                     "3D model beside it (L61, more than %d words is dense)" % (where, nwords_all, DENSE_WORDS))
    split = b.get("split")
    if split is not None:
        try:
            split = float(split)
        except (TypeError, ValueError):
            split = -1
        if not SPLIT_LO <= split <= SPLIT_HI:
            probs.append("%s: \"split\": %s - the text takes %d-%d %% of a split slide, the picture the rest (L61)"
                         % (where, b.get("split"), 100 * SPLIT_LO, 100 * SPLIT_HI))
            split = None
    if tid == "compare-two" and comp not in ("photo",):
        comp = "compare"
    if tid == "opening" and variant == "photo":            # the opening's photograph is the screen, the title over it
        comp = "photo"
    # L62 (owner, 2026-10-21) - never the same look on two slides in a row: built another way when it would repeat
    varied, wkey = None, words_key(s, b)
    if recent is not None and kind == "slide" and not s.get("recap"):
        # a photograph, or a figure-kit drawing (made for the dark panel), may move to the dark ground; a drawing or a
        # widget made for a white page keeps the light one - its own controls would vanish (gas M01 s07, s15, s19, s26)
        dark_ok = is_photo or bool(re.search(r'data-kit="|class="kit-screen', fig or ""))
        pick, moved = choose_layout(layout_options(tid, variant, is_photo, nwords_all, b, comp, bool(b.get("figure_first")),
                                                   bool(b.get("dark")), dark_ok), recent, measured_out(avoid, s, b),
                                     last_layout(last, s, b))
        if moved:
            varied = pick["key"]
            tid, variant = pick["tid"], pick["variant"]
            b = dict(b, figure_first=pick["first"], dark=pick["dark"])
            if pick["comp"] == "photo":
                comp, split_photo, photo_col = "photo", True, False
            elif pick["comp"] == "stage":
                comp, split_photo, photo_col = "stage", False, False
            elif pick["comp"] in ("wide-left", "two-col"):
                comp, split_photo, photo_col = pick["comp"], False, is_photo and pick["comp"] == "wide-left"
    if b.get("panel") not in (None, "light"):
        probs.append("%s: \"panel\": %s - the picture's panel is the Navy one, or \"light\" for a drawing made for a white page (L61)"
                     % (where, b.get("panel")))
    light = b.get("panel") == "light"                         # a drawing made for a white page: the light panel (gb_layouts.css)
    box_of = lambda f: fill(f).replace('class="fill fig"', 'class="fill fig lt-light"', 1) if light else fill(f)
    emph = {k: b[k] for k in ("boxes", "box_alt", "conclusion", "groups", "hooks") if k in b}
    if tid == "three-content-blocks":
        emph["groups"] = [{"lines": [lo, hi], "class": "lt-block"} for lo, hi in line_ranges(b.get("blocks"), len(lines), 3)]
    inset = inset_html(mdir, b["inset"], probs, where) if b.get("inset") else ""
    aside = ""
    if b.get("aside"):                    # a small drawing that belongs with the words (two mini figures on a photo)
        aside, err = read_figure(mdir, b["aside"], figdir)
        if err:
            probs.append("%s: its aside %s %s" % (where, b["aside"], err))
            aside = ""
        elif aside:
            aside = '<div class="aside">%s</div>' % photos_in(aside, mdir, probs, where)
    # an inset photo goes under the words - or under the drawing ("under": "figure") when the words fill their column
    on_slide = set(IMG_SRC.findall(fig + inset + aside))
    # under the drawing only when the drawing's box is the compiler's own column; a fragment that is its own .fill and
    # lays itself out (a 3D model beside its controls, a row) would put it beside the canvas and squeeze it to 0 px -
    # there it goes with the words
    room_under = fig and not is_photo and (OWN_BOX.match(fig) or not FILL_BOX.match(fig))
    if inset and (b.get("inset") or {}).get("over"):
        fig, inset = over_figure(fig, inset, b["inset"]["over"], probs, where)
    cap = INSET_MAX_WORDS.get("photo-split" if split_photo else comp)
    nwords = cs.wc(" ".join(lines))
    if inset and (b.get("inset") or {}).get("under") == "figure" and room_under:
        sh = under_share(fig)
        if sh and sh[0] < UNDER_MIN_SHARE and not (cap and nwords > cap):
            # 2.63.0 - the drawing keeps its size and the photo goes under the words, which now give it the room they leave
            # (gb_compose.css): reported, a run lost each time (IGF M01 v262 run 3: s02 / s03 / s04 / s07 at 33-49 %)
            print("Note: %s - the inset is under the words, not under the drawing: there it would leave the drawing only about "
                  "%d %% of its panel" % (where, round(100 * sh[0])))
        elif sh and sh[0] < UNDER_MIN_SHARE:
            probs.append("%s: the inset under the drawing leaves the drawing only about %d %% of its panel (about %d of %d px high at "
                         "1280 x 800), so the drawing is drawn at about half its size - put the inset under the words, lay it "
                         "over a blank part of the drawing (\"over\"), or draw the figure wider and less tall"
                         % (where, round(100 * sh[0]), round(sh[1] - INSET_H), round(sh[1])))
            fig, inset = under_figure(fig, inset), ""
        else:
            fig, inset = under_figure(fig, inset), ""
    if inset and cap and nwords > cap:                 # F4 (2.49.2): said at build, before the drawing check finds the spill
        probs.append("%s: %d words in the reading column and an inset photograph under them - the column holds about %d words "
                     "with a photograph, so the photograph will spill about %d px off the slide at 1280 x 800 (IGF M07 s08 / s12, "
                     "M09 s06: 79-105 px at 91-101 words). Cut the words, show the photograph on a task question or another slide, "
                     "or lay it over a blank part of a kit drawing (\"over\")" % (where, nwords, cap, round((nwords - cap) * 4.5)))
    # 2.63.0 - an early warning, before the audit measures it: the slide's words past the measured budget of its layout
    bud = word_budget(tid, variant, bool(inset))
    if bud and not (inset and cap and nwords > cap):
        many = nwords
        if tid == "content-in-parts":
            rr = line_ranges(b.get("parts"), len(lines)) if b.get("parts") else None
            many = max(cs.wc(" ".join(lines[i - 1] for i in ix)) for ix in auto_parts(lines, rr))
        if many > bud[0]:
            print("Note: %s - %d words %s; the layout holds about %d at 1024 x 768 (measured, layout-templates.json \"budgets\"): "
                  "expect the audit to find it spilling - %s" % (where, many, bud[1], bud[0],
                  "make the parts smaller (\"parts\")" if tid == "content-in-parts" else
                  "let the compiler choose the layout, or put the words in parts (\"template\": \"content-in-parts\")"))
    # L57: a drawing of real things carries their real photographs, under the drawing - unasked
    strip = ""
    if fig and not is_photo and comp != "photo" and notes is not None and not strip_off(figdir, s, b):
        strip = part_photos(lines, fig, on_slide, mdir, pool or [], notes, sid, taken, b.get("no_photo") or [], b.get("not_things") or [])
        if strip and room_under:
            fig, strip = under_figure(fig, strip), ""
    extra = [x for x in (inset, aside, strip) if x]
    own = re.sub(r"[^\w -]", "", b.get("class") or "")          # a hook for the module's drawing styles, never a look
    d = {"class": "slide" + (" photo split" if split_photo else " photo" if comp == "photo" else " dark" if b.get("dark") else "")
                  + (" " + own if own else ""),
         "data-title": s.get("title"), "data-kind": "Theory", "data-block": "%s · %d" % (m, n),
         "data-visual": vkind}
    d.update(base)
    template_attrs(d, tid, variant, split)
    if varied:              # built another way for L62: build_module.py measures it out if the audit finds it does not fit
        d["data-varied"] = "%s|%s|%s" % (varied[0], varied[1], wkey)
    label = "Theory"
    if act:
        code = (s.get("opens") or "").strip() or sid.upper()
        d.update({"data-kind": "Task", "data-activity": code, "data-track": "practice", "data-block": "%s · %s" % (m, code),
                  "data-link-hint": b.get("link_hint") or (lines[0] if lines else "")})
        label = "Task"
    head = '  <div class="slide-kind"><b>%s</b> · %s · %d / %d</div>' % (label, m, n, total)
    h2 = '<h2 data-script-field="title">%s</h2>' % e(s.get("title"))
    # 2.63.0 (owner Raivis, 2026-10-21, the instructors' review: "remove the kallerna credit"): no credit text on the slide.
    # It is the photo's record in its full-screen view (data-credit, gb_zoom) and the course's credits page
    # (compile_course.py CREDITS.html) - CC BY-SA attribution kept. L56
    credit_html = ""
    ind = lambda xs, k: ("\n" + " " * k).join(xs)
    copy = lambda xs, k: ('<div class="copy">\n' + " " * (k + 2) + ind(xs + extra, k + 2)
                          + "\n" + " " * k + "</div>")

    if comp == "photo":
        return ('<section %s>\n  <div class="photo-wrap">%s</div>\n  <div class="photo-scrim"></div>\n%s\n'
                '  <div class="photo-copy">\n    %s\n    %s\n  </div>%s\n</section>'
                % (attrs(d), fig, head, h2, ind(words_html(lines, dark_photo=True) + extra, 4), credit_html))
    if comp == "stage":
        leg = b.get("legend")
        if isinstance(leg, list) and len(leg) == 2:
            # "legend": [2, 6] - lines 2-6 are the numbered row under the drawing; the lines before it go above,
            # the lines after it below
            lo, hi = leg
            nums = list(range(1, len(lines) + 1))
            pre = [(i, x) for i, x in zip(nums, lines) if i < lo]
            mid = [(i, x) for i, x in zip(nums, lines) if lo <= i <= hi]
            post = [(i, x) for i, x in zip(nums, lines) if i > hi]
            part = lambda ps, **kw: words_html([x for _, x in ps], first_statement=False, emph=emph,
                                               idx=[i for i, _ in ps], **kw) if ps else []
            above = ind(part(pre), 4) if pre else ""
            below = "\n    ".join(y for y in (ind(part(mid, legend=True), 4), ind(part(post), 4), ind(extra, 4)) if y)
            body = "\n    ".join(y for y in (above, box_of(fig), below) if y)
        else:
            words = words_html(lines, first_statement=False, emph=emph, legend=bool(leg))
            body = box_of(fig) + "\n    " + (ind(words + extra, 4) if leg else copy(words, 4))
        return ('<section %s>\n%s\n  %s\n  <div class="slide-body stage">\n    %s\n  </div>%s\n</section>'
                % (attrs(d), head, h2, body, credit_html))
    if comp in ("two-col", "wide-left", "wide-right"):
        # a drawing, an animation or a 3D model gets the wider column (owner, 2026-10-15: bigger pictures)
        cls = "two-col " + (comp if comp != "two-col" else "fig-wide")
        box = box_of(fig)
        if photo_col:                      # the photograph is cropped to its column, which has the slide's height
            box = box.replace('class="fill fig"', 'class="fill fig photo-col"', 1)
            cls += " photo-col"
            if credit_html:                # 2.60.0 - its credit is a strip at the column's foot, under the photo: the photo
                # crops a little, the words beside it lose nothing (IGF M15 s01 / s06: a three-line credit under the slide
                # made 108-133 words spill at 1024 x 768)
                head_, tail_ = box.rsplit("</div>", 1)
                box, credit_html = head_ + credit_html.strip() + "</div>" + tail_, ""
        if tid == "content-in-parts":
            ranges = line_ranges(b.get("parts"), len(lines)) if b.get("parts") else None
            if b.get("parts") and not ranges:
                probs.append("%s: \"parts\" must be line ranges in order, each line once - e.g. [[1, 4], [5, 9]] (L61)" % where)
            if ranges and sum(hi - lo + 1 for lo, hi in ranges) != len(lines):
                probs.append("%s: \"parts\" leave out some lines - every approved line is in a part (L61)" % where)
                ranges = None
            reading = copy(parts_html(lines, auto_parts(lines, ranges), emph), 4)
        elif tid == "reference-table":
            reading = copy(table_html(lines), 4)
        else:
            reading = copy(words_html(lines, emph=emph), 4)
        # 2.54.0 (L23; built as 2.52.0 on its own branch) - the figure first in the markup: a portrait tablet (one column)
        # shows it in its first screen. On a landscape screen gb_compose.css (.dom-fig) puts the words back first, so the
        # template's text column (gb_layouts.css, L61) holds the words - the projector picture is unchanged
        cols = [box, reading]
        if b.get("figure_first"):          # the drawing on the left, the words on the right
            cls = cls.replace("fig-wide", "fig-wide fig-first") if "fig-wide" in cls else cls + " fig-first"
        else:
            cls += " dom-fig"
        return ('<section %s>\n%s\n  %s\n  <div class="slide-body %s">\n    %s\n    %s\n  </div>%s\n</section>'
                % (attrs(d), head, h2, cls, cols[0], cols[1], credit_html))
    if comp == "compare":
        fig_b, credit_b, _ = figure_html(mdir, figdir, s, dict(b, figure=b.get("figure_b")), probs, where)
        rs = line_ranges(b.get("blocks"), len(lines), 2)
        inside = set(i for lo, hi in rs for i in range(lo, hi + 1))
        cards = []
        for (lo, hi), pic in zip(rs, (fig, fig_b)):
            ix = list(range(lo, hi + 1))
            cards.append('<div class="lt-card"><div class="lt-card-visual">%s</div><div class="lt-card-copy">\n      %s\n    </div></div>'
                         % (pic, ind(words_html([lines[i - 1] for i in ix], first_statement=False, idx=ix, emph=emph), 6)))
        rest = [i for i in range(1, len(lines) + 1) if i not in inside]
        note = ind(words_html([lines[i - 1] for i in rest], first_statement=False, idx=rest), 4) if rest else ""
        return ('<section %s>\n%s\n  %s\n  <div class="slide-body lt-compare">\n    %s\n  </div>%s%s\n</section>'
                % (attrs(d), head, h2, "\n    ".join(cards), ("\n  <div class=\"lt-compare-note\">%s</div>" % note) if note else "",
                   credit_html))                       # 2.63.0: the credits are in each photo's full-screen view
    if comp == "opener":
        return ('<section %s>\n%s\n  <div class="slide-body opener mid">\n    %s\n    %s\n  </div>%s\n</section>'
                % (attrs(d), head, h2, ind(words_html(lines, first_statement=False), 4), credit_html))
    figure = (box_of(fig) + "\n    ") if fig else ""      # 2.54.0 (L23): first in the markup, placed under the words by CSS
    return ('<section %s>\n%s\n  %s\n  <div class="slide-body%s">\n    %s%s\n  </div>%s\n</section>'
            % (attrs(d), head, h2, " dom-fig" if fig else "", figure, copy(words_html(lines, emph=emph), 4), credit_html))


# ------------------------------------------------------------------ the page
def build_path(course, module):
    return os.path.join(cs.paths(course, module)["dir"], cs.mid(module) + ".build.json")


def short_title(title):
    """the module's title as the deck's foot has it: upper case, whole words only, never "CHARACTE" """
    short = (title or "").upper()
    if len(short) > 40:
        short = short[:41].rsplit(" ", 1)[0].rstrip(" -·,")
    return short


# the ways of answering ON a picture: their starter entry names the picture and the places (2.49.1)
STARTER_ON_PICTURE = {"hotspot": {"figure": "", "areas": {}}, "spot_the_hazard": {"figure": "", "areas": {}},
                      "label_diagram": {"figure": "", "labels": {}}}


def sibling_sheets(bp):
    """the course's other module build sheets (M01.build.json ...), the nearest first - what every module shares"""
    here = os.path.dirname(bp)
    out = []
    for name in sorted(os.listdir(here)) if os.path.isdir(here) else []:
        p = os.path.join(here, name)
        if name.endswith(".build.json") and os.path.abspath(p) != os.path.abspath(bp):
            try:
                out.append(cs.load(p))
            except (OSError, ValueError):
                pass
    return out


THREE_JS = "assets/vendor/three.min.js"
THREE_SRC = os.path.join(SKILLS, "course-module-ui", "templates", "vendor", "three.min.js")   # the factory's copy (2.59.0)


def starter_scene(script, sid, scripts):
    """2.49.7 (IGF M01 s05) - a model_3d slide's starter entry plans its 3D scene by default: the figure and the scene file are
    named, and the scene's two files go into the sheet's "scripts" - the build reports them missing until they are written,
    so the 3D is built, or kept 2D with the operator's reason ("declined_3d"), never dropped without a word"""
    m = cs.mid(script.get("module")).lower()
    js = "assets/js/%s_%s_3d.js" % (m, sid)
    for x in (THREE_JS, js):
        if x not in scripts:
            scripts.append(x)
    return {"figure": "%s_%s_3d.html" % (m, sid),
            "_figure": ("A 3D scene, planned by default (L46). Write the figure working_claude\\figures\\%s\\%s_%s_3d.html - a "
                        "[data-stage] holder, a flat fallback drawing and, if the scene says how to use it, an empty "
                        "<div data-hint></div> its script fills (the compile marks it data-script-ignore: the control hint is "
                        "not script words); no class of the module's own that no rule styles - and the scene %s, built like IGF M03's "
                        "m03_station3d.js (compile GUIDE 2b): one shared renderer, the scene built while the slide before is "
                        "on screen (its GB_HOOKS), window.__noPrepare and window.__scene3d for perf3d.mjs, a tap highlights a "
                        "part; first frame under 1 s at 4x CPU (measure GUIDE 2b). three.min.js (r128) is the factory's - the compile puts it in assets\\vendor\\. "
                        "Or keep a 2D figure: put it in \"figure\" (--init-build writes its starter, see \"_2d\"), take the two "
                        "scene files off \"scripts\", and write the operator's reason in \"declined_3d\"." % (m.upper(), m, sid, js))}


# ------------------------------------------------------------------ starter figure-kit specs (2.50.0)
# The visual kinds a figure-kit spec can draw: a drawing, a chart, a comparison, an animation. Not a photograph, not a
# drawing from the sources (technical_drawing), not a 3D scene (those get starter_scene).
STARTER_FIGURE_KINDS = ("schematic", "cutaway", "chart", "comparison", "step_animation", "flow_animation",
                        "process_animation", "interactive_diagram")
# the script's own word -> the kit part that draws it; an unknown word becomes a text callout
KIT_WORDS = {
    "tank": "tank", "pipe": "pipe", "pipeline": "pipe", "hose": "pipe", "duct": "pipe", "valve": "valve",
    "engine": "engine", "generator": "engine", "vent": "vent", "mast": "vent", "pump": "pump", "compressor": "pump",
    "detector": "detector", "sensor": "detector", "gauge": "gauge", "pressure": "gauge", "manometer": "gauge",
    "level": "level", "room": "space", "space": "space", "hold": "space", "compartment": "space", "enclosure": "space",
    "scale": "scale", "flashpoint": "scale", "temperature": "scale", "thermometer": "scale",
    "ship": "ga", "hull": "ga", "vessel": "ga", "vaporizer": "exchanger", "vaporiser": "exchanger",
    "heater": "exchanger", "exchanger": "exchanger", "cylinder": "cylinder"}
KIT_WORD = re.compile(r"\b(%s)(?:s|es)?\b" % "|".join(sorted(KIT_WORDS, key=len, reverse=True)), re.I)
# per part type: anchor ("tl" = x, y is its top left, "c" = its centre), the room it takes (w, h), what it starts at and
# where a step takes it
STARTER_PART = {
    "tank": ("tl", 170, 74, 0.2, 0.9), "pipe": ("pipe", 190, 0, 0, 1), "valve": ("c", 40, 40, 0, 1),
    "engine": ("tl", 120, 70, 0, 1), "vent": ("c", 40, 40, 0, 1), "pump": ("c", 40, 50, 0, 1),
    "detector": ("c", 50, 50, 0, 20), "gauge": ("c", 90, 90, 0, 7), "level": ("tl", 50, 110, 20, 80),
    "space": ("tl", 160, 80, 0, 1), "scale": ("tl", 90, 120, 0, 1), "ga": ("tl", 190, 56, 0, 1),
    "exchanger": ("c", 40, 56, 0, 1), "cylinder": ("tl", 140, 230, 0, 1)}
STARTER_MAX_PARTS = 9


def kit_hit(text, last=False):
    """(kit part type, the word as the script wrote it) for the first - or, for a name, the last (its head noun) - word in
    `text` the kit has a part for, else None"""
    hits = [(m.start(), KIT_WORDS[m.group(1).lower()], m.group(0)) for m in KIT_WORD.finditer(text or "")]
    if not hits:
        return None
    _, kind, word = hits[-1] if last else hits[0]
    return kind, word


def wrap_words(text, width):
    """the same words on lines of at most `width` characters, broken at spaces with \\n (a text part's own line break)"""
    out, cur = [], ""
    for w in text.split():
        if cur and len(cur) + 1 + len(w) > width:
            out.append(cur)
            cur = w
        else:
            cur = (cur + " " + w).strip()
    return "\n".join(out + [cur]) if cur else ""


# 2.52.0 - the starter is drawn to the shape of the column the deck shows it in, its parts spread over all of it. Laid
# 640 x 390 on a grid of small fixed-size parts, ~20 of 25 failing M01 builds had a figure over half blank (EMPTY - s02 in
# every one): each part kept its default size in a cell twice as large, a row of three left a blank cell, and a slide with
# an L57 photo row under the drawing showed it in a 682 x 292 px panel, so the 390-high canvas was drawn at 0.75 with
# bands of blank either side (M01 workflow benchmark, 2026-10-20).
STARTER_W = 640
STARTER_PANEL = (682.0, 416.0)       # the two-col figure column at 1280 x 800, the composition every starter is given
STARTER_STRIP_H = 124.0              # the L57 photo row under a drawing at 1280 x 800 (M01 s04: the panel 682 x 292 px)
STARTER_MARGIN, STARTER_LABEL = 14, 30   # round each part inside its cell; the room its label takes beside it
STARTER_CELL_ASPECT = 1.5            # the cell shape the parts draw best in (a tank, an engine, a room: wider than tall)
# the parts that are a fixed small symbol (and a text callout) take a narrower cell than the parts that grow to theirs
STARTER_GLYPH = {"valve", "vent", "detector", "pump", "exchanger", "text"}


def starter_size(lines, items, pool, taken=None):
    """the canvas: 640 wide and as high as the deck's column is for that width - less the L57 photo row when a cleared
    photograph shows one of the things the starter draws (the row goes under the drawing and takes its height)"""
    W, H = STARTER_PANEL
    if pool:                                            # what part_photos() will find for this drawing, nothing copied
        spec = {"parts": [{"type": it["kind"], ("text" if it["kind"] == "text" else "label"): it["label"]} for it in items]}
        fig = '<script type="application/json">%s</script>' % json.dumps(spec)
        taken = taken or {}
        if any(pid not in taken and any(shows_it(x, name) for x in (m.get("shows") or []))
               for _, name in drawn_parts(lines, fig) for _, m, _, pid in pool):
            H -= STARTER_STRIP_H
    return STARTER_W, int(round(STARTER_W * H / W))


def starter_rows(n):
    """every way to share n parts out over rows in reading order (5: [5], [4, 1], [3, 2] ... [1, 1, 1, 1, 1])"""
    if n <= 1:
        return [[n]]
    out = []
    for first in range(n, 0, -1):
        out += [[first] + rest for rest in starter_rows(n - first)] if first < n else [[n]]
    return out


def starter_cells(items, size):
    """each part's cell (x, y, w, h), in reading order: of every way to share the parts out over rows, the one whose cells
    come nearest each part's own shape (STARTER_SHAPE: a ship long and low, a level tall). The cells of a row are as wide
    as their parts need - a symbol or a text callout about 0.6 of a growing part, a dial 0.7; a row of text callouts only
    is as high as its words, and the rows with drawn parts share the rest. A scale stands the whole height at the left."""
    import math
    kinds = [it["kind"] for it in items]
    if "scale" in kinds and len(kinds) > 1:
        i = kinds.index("scale")
        col = min(260, size[0] // 3)
        rest = starter_cells(items[:i] + items[i + 1:], (size[0] - col, size[1]))
        rest = [(x + col, y, w, h) for x, y, w, h in rest]
        return rest[:i] + [(0, 0, col, size[1])] + rest[i:]
    best = None
    for rows in starter_rows(len(items)):
        cells = starter_grid(items, size, rows)
        cost = sum(abs(math.log((w / max(h, 1)) / STARTER_SHAPE.get(k, STARTER_CELL_ASPECT))) for k, (_, _, w, h) in zip(kinds, cells))
        if best is None or cost < best[0] - 1e-9:
            best = (cost, cells)
    return best[1]


# the cell shape (w / h) each part draws best in
STARTER_SHAPE = {"ga": 3.2, "text": 3.0, "pipe": 3.0, "tank": 2.0, "engine": 1.6, "space": 1.7, "gauge": 1.0, "level": 0.6,
                 "valve": 1.6, "vent": 0.8, "pump": 1.0, "exchanger": 1.0, "detector": 1.2, "cylinder": 0.7}


def starter_grid(items, size, rows):
    """the cells for one way of sharing the parts out over rows (starter_cells)"""
    kinds = [it["kind"] for it in items]
    weight = lambda k: 0.6 if k in STARTER_GLYPH else 0.7 if k == "gauge" else 1.0
    cells, k = [], 0
    fixed, grow = [], []
    for c in rows:
        row = items[k:k + c]
        if all(it["kind"] == "text" for it in row) and len(rows) > 1:
            per = size[0] / c
            n = max(len(wrap_words(it["label"], max(10, int((per - 2 * STARTER_MARGIN) / 8.5))).split("\n")) for it in row)
            fixed.append(n * 22 + 2 * STARTER_MARGIN + 12)
            grow.append(0)
        else:
            fixed.append(0)
            grow.append(max(weight(x) for x in kinds[k:k + c]))
        k += c
    left = size[1] - sum(fixed)
    k, y = 0, 0.0
    for c, fx, rw in zip(rows, fixed, grow):
        h = fx or left * rw / (sum(grow) or 1)
        ws = [weight(x) for x in kinds[k:k + c]]
        x = 0.0
        for wt in ws:
            w = size[0] * wt / sum(ws)
            cells.append((x, y, w, h))
            x += w
        k += c
        y += h
    return cells


def starter_part(pid, it, cell):
    """the part (and a pipe's words) drawn to fill its cell - a tank, a room, an engine, a ship as large as the cell
    leaves room for its label; a symbol at its own size in the middle"""
    kind, (x0, y0, cw, ch) = it["kind"], cell
    m, lab = STARTER_MARGIN, STARTER_LABEL
    cx, cy = int(round(x0 + cw / 2)), int(round(y0 + ch / 2))
    iw, ih = int(cw - 2 * m), int(ch - 2 * m)            # the room inside the cell
    if kind == "text":
        return [{"id": pid, "type": "text", "x": cx, "y": cy, "anchor": "middle", "reveal": True,
                 "text": wrap_words(it["label"], max(10, int(iw / 8.5)))}]
    p = {"id": pid, "type": kind}
    top = lambda w, h: p.update(x=int(round(cx - w / 2)), y=int(round(y0 + m + (ih - lab - h) / 2)), w=int(w), h=int(h))
    if kind == "tank":
        top(iw, max(56, min(ih - lab, iw * 0.5)))
    elif kind == "space":
        top(iw, max(60, ih - lab))
    elif kind == "engine":
        w = min(iw, 300)
        top(w, max(60, min(ih - lab, w * 0.55)))
    elif kind == "cylinder":                             # an engine cylinder: tall, its own words beside it
        h = max(120, min(ih, 340))
        p.update(x=int(round(cx - h * 0.3)), y=int(round(y0 + m + (ih - h) / 2)), w=int(h * 0.6), h=int(h))
    elif kind == "ga":                                   # the house and the funnel stand above the hull: room for them
        w = iw
        h = max(40, min(ih - lab - 44, w * 0.24))
        p.update(x=int(round(cx - w / 2)), y=int(round(y0 + m + 44 + (ih - lab - 44 - h) / 2)), w=int(w), h=int(h))
    elif kind == "level":
        top(50, max(80, min(ih - lab, 240)))
    elif kind == "scale":                                # its marker's words stand to its right, and the marker moves
        h = max(80, ih - 24)
        p.update(x=int(round(x0 + m + 30)), y=int(round(y0 + m + 12)), w=90, h=int(h), reach=int(max(60, iw - 150)))
    elif kind == "gauge":
        p.update(x=cx, y=int(round(cy - lab / 2)), r=int(max(25, min(90, iw / 2 - 6, (ih - lab) / 2 - 6))))
    elif kind in ("pump", "exchanger"):
        p.update(x=cx, y=int(round(cy - lab / 2)), r=int(max(20, min(40, iw / 4, (ih - lab) / 3))))
    elif kind == "detector":
        p.update(x=cx - 24, y=cy - 10, r=int(max(19, min(30, ih / 5))))
    elif kind == "valve":                                # a valve sits on its line: the line drawn across the cell with it
        p.update(x=cx, y=cy, size=18)
    elif kind == "vent":                                 # the outlet on top of its mast, the mast down the cell
        p.update(x=cx - 24, y=int(round(y0 + m + 20)), mast=int(max(30, ih - 40)))
    if kind == "pipe":
        p.update(d="M%d %d H%d" % (int(x0 + m), cy, int(x0 + cw - m)), fluid="liquid")
    if kind == "gauge":
        p.update(min=0, max=10, numbers=False)                # a small dial: no numbers round it
    if kind == "level":
        p.update(min=0, max=100)
    if kind == "valve":
        p.update(labelAt="right", trip=False)
    if kind == "vent":
        p.update(labelAt="right")
    if kind == "scale":
        p.update(min=0, max=100, every=50, markers=[{"label": it["label"], "at": 50}])
    if kind not in ("pipe", "scale"):
        p["label"] = it["label"]
    if it["start"]:
        p["value"] = it["start"]
    out = [p]
    if kind == "valve":
        out.insert(0, {"id": pid + "L", "type": "pipe", "d": "M%d %d H%d" % (int(x0 + m), cy, int(x0 + cw - m)), "fluid": "liquid"})
    if kind == "pipe":                                    # a pipe has no words of its own: its name stands over it
        out.append({"type": "text", "x": cx, "y": cy - 16, "anchor": "middle", "text": wrap_words(it["label"], max(10, int(iw / 8.5)))})
    return out


def starter_figure(script, s, pool=None, taken=None):
    """2.50.0 - a starter figure-kit spec for a drawing slide, so the build starts from something to edit, not from nothing
    (IGF M01 benchmark: 27 Edit/Write calls writing specs from scratch). One part per thing the script names - the term before
    " - " or ": " in each line (the rule words_html bolds by), else the kit's word in the line, else its first words as a text
    callout - each labelled in the script's own words, plus the kit's words in the first sentence of `visual` that the lines
    did not name. 2.52.0: drawn to the column's real shape (starter_size: `pool` = the course's cleared photographs, for the
    L57 photo row) and spread over all of it, each part grown to its cell (starter_cells, starter_part) - none overlap.
    One step per line after the opening statement, lighting that line and moving the part it names. Returns the spec, or
    None when the slide has no lines to draw."""
    lines = cs.lines_of(s.get("text"))
    if not lines:
        return None
    # an opening statement: a plain sentence before lines that name things ("Many IGF ships have dual-fuel engines."); a list of
    # bare names ("Fuel tank." "Tank connection space.") has none
    statement = len(lines) > 1 and not TERM.match(lines[0]) and any(TERM.match(x) for x in lines[1:])
    items, index = [], {}                              # items: {"kind", "label", "start", "to"}; index: (kind, label) -> n
    steps = []                                         # (line number, part n, flipped)
    for i in range(2 if statement else 1, len(lines) + 1):
        line = lines[i - 1]
        m = TERM.match(line)
        term = m.group(1).strip() if m and 1 <= len(m.group(1).split()) <= 4 and not m.group(1)[:1].islower() else ""
        bare = re.sub(r"[.,;:!?]+$", "", line).strip()
        if not term and not m and len(bare.split()) <= 4:        # a line that is only a name: "Tank connection space."
            term = bare
        hit = kit_hit(term, last=True) if term else kit_hit(line)
        if hit and term:
            kind, label = hit[0], term
        elif hit:
            kind, label = hit
        else:
            kind = "text"
            label = term or " ".join(re.sub(r"[.,;:!?]+$", "", line).split()[:5])
        key = (kind, label.lower())
        flipped = key in index
        if not flipped:
            if len(items) >= STARTER_MAX_PARTS:
                continue
            index[key] = len(items)
            start, to = (0, 1) if kind == "text" else STARTER_PART[kind][3:5]
            items.append({"kind": kind, "label": label, "start": start, "to": to})
        steps.append((i, index[key], flipped))
    if not steps:
        return None
    have = {it["kind"] for it in items}
    visual = (s.get("visual") or "").strip()
    first = re.split(r"(?<=[.!?])\s", visual, 1)[0] if visual else ""
    for m in KIT_WORD.finditer(first):                 # the things the picture is described as holding
        kind = KIT_WORDS[m.group(1).lower()]
        if kind in have or len(items) >= STARTER_MAX_PARTS:
            continue
        have.add(kind)
        items.append({"kind": kind, "label": m.group(0).lower(), "start": STARTER_PART[kind][3], "to": STARTER_PART[kind][4]})
    size = starter_size(lines, items, pool, taken)
    parts, ids, now = [], [], []
    for k, (it, cell) in enumerate(zip(items, starter_cells(items, size))):
        pid = "P%d" % (k + 1)
        ids.append(pid)
        now.append(it["start"])
        parts += starter_part(pid, it, cell)
    plan = []
    for i, k, flipped in steps:
        it = items[k]
        to = it["to"] if not flipped else (it["start"] if now[k] == it["to"] else it["to"])
        if flipped and it["kind"] == "text":
            to = 1
        now[k] = to
        words = " ".join(lines[i - 1].split())
        title = "%d · %s" % (len(plan) + 1, words[:60].rstrip())
        plan.append({"title": title, "line": i, "play": [[ids[k], to, 600]]})
    label = first or (s.get("title") or "")
    return {"size": list(size), "label": label, "idle": "Press Next step", "parts": parts, "steps": plan}


def starter_figures(script, build_screens, figdir, skip=(), out=None, fallback=(), pool=None, taken=None):
    """the starter figure of every slide whose picture the kit can draw - written into `out` ({slide id: spec}) when its
    file is not there yet (never overwritten) - and the slide's entry in `build_screens` set to name it.
    `fallback` (2.50.6): the slides a 3D scene is planned for - a model_3d slide, or the one proposed unasked (L60). Each
    gets its 2D starter too, written but not named in "figure" (the scene stays the plan): declining the 3D
    ("declined_3d") means editing that starter, never writing a spec from nothing (M01 benchmark run 5, s05)."""
    for s in script["screens"]:
        if s["kind"] != "slide" or s.get("recap") or s["id"] not in build_screens:
            continue
        two_d = s["id"] in fallback
        if not two_d and (s["id"] in skip or cs.parse_kind(s.get("visual_kind", "")) not in STARTER_FIGURE_KINDS):
            continue
        spec = starter_figure(script, s, pool, taken)
        if not spec:
            continue
        name = "%s.kit.json" % s["id"]
        entry = build_screens[s["id"]]
        if two_d:
            if not os.path.isfile(os.path.join(figdir, name)):
                entry["_2d"] = ("Keeping a 2D figure instead of the 3D scene? Its starter is written: working_claude\\figures\\%s\\%s - "
                                "set \"figure\": \"%s\", \"composition\": \"two-col\", \"dark\": true, take the scene files off "
                                "\"scripts\", write the operator's reason in \"declined_3d\", and edit the starter (SPEC.md) - "
                                "never write one from nothing." % (cs.mid(script.get("module")), name, name))
                if out is not None:
                    out[s["id"]] = spec
            continue
        entry.update({"figure": name, "composition": "two-col"})   # 2.62.1: its own Navy panel on the light slide (80 / 20)
        if not os.path.isfile(os.path.join(figdir, name)):
            entry["_figure"] = ("starter written by --init-build: replace the placeholder parts with the real drawing, one part per "
                                "thing the script names (SPEC.md); the parts are placed on a grid and the steps light the slide's "
                                "lines. Try it with studio.py before compiling.")
            if out is not None:
                out[s["id"]] = spec


def starter_build(script, shared=(), figdir=None, specs=None, mdir=None):
    """A starter build sheet. 2.49.1: the landing rule and the pass mark are the same in every module of a course, so they
    come from the course's other build sheets (the latest module that has them); the foot is this module's title; each
    question answered on a picture gets its entry (figure + places) to fill in. `mdir` (2.52.0): the module folder, whose
    cleared photographs (and the course's) decide whether a starter figure gets the L57 photo row under it."""
    def first(key):
        for sheet in reversed(list(shared)):
            if sheet.get(key) not in (None, ""):
                return sheet[key]
        return None
    sheet = {"module": script.get("module"), "landing_rule": first("landing_rule") or "",
             "foot": short_title(script.get("title"))}
    if first("pass_mark") is not None:
        sheet["pass_mark"] = first("pass_mark")
    sheet.update({"styles": [], "scripts": [], "inline": []})
    screens = {}
    for s in script["screens"]:
        if s["kind"] in cs.INSTRUCTOR:
            screens[s["id"]] = ({"figure": "", "visual_kind": s.get("visual_kind") or "none"} if s["kind"] == "slide" else
                                {"link_hint": ""} if s["kind"] == "activity" else {})
            if s["kind"] == "slide" and cs.parse_kind(s.get("visual_kind", "")) == "model_3d":
                screens[s["id"]].update(starter_scene(script, s["id"], sheet["scripts"]))
        elif s["kind"] in cs.TASKS and cs.mech(s) in STARTER_ON_PICTURE:
            screens[s["id"]] = json.loads(json.dumps(STARTER_ON_PICTURE[cs.mech(s)]))
    # L60 - at least one 3D scene in every module where the subject allows it: with none planned, the best slide gets one, unasked
    best = None if any(cs.parse_kind(s.get("visual_kind", "")) == "model_3d" for s in script["screens"]) else cs.best_3d(script)
    if best and best[0] in screens:
        screens[best[0]].update(starter_scene(script, best[0], sheet["scripts"]))
        screens[best[0]]["_3d"] = ("Proposed by the factory, unasked (L60): this module has no 3D scene and this slide's lesson has a "
                                   "shape, an inside or a layout in space (%s). Strongly recommended, never required: to decline it, "
                                   "give the slide its 2D figure, take the scene files off \"scripts\", and write the operator's reason "
                                   "in the sheet's top-level \"declined_3d\" - it is not proposed again." % best[1])
    if figdir is not None:             # 2.50.0: a starter figure-kit spec for every drawing slide - not a photo; a 3D one's
        three_d = {s["id"] for s in script["screens"] if s["kind"] == "slide" and cs.parse_kind(s.get("visual_kind", "")) == "model_3d"}
        pool = photo_pool(mdir) if mdir and os.path.isdir(mdir) else []
        taken = {k: v[0] for k, v in shown_elsewhere(mdir).items()} if pool else {}
        starter_figures(script, screens, figdir, skip={best[0]} if best else (), out=specs,      # is its 2D fallback (2.50.6)
                        fallback=three_d | ({best[0]} if best else set()), pool=pool, taken=taken)
    sheet["screens"] = screens
    return sheet


def compile_deck(script, build, mdir, figdir, version, approved, avoid=None, last=None, chosen=None):
    probs = []
    CUE_FIXES.clear()
    m = cs.mid(script.get("module"))
    title = script.get("title") or ""
    screens = [s for s in script["screens"] if s["kind"] in cs.INSTRUCTOR]
    short = short_title(title)                           # whole words only - never "CHARACTE"
    foot = "%s · %s · NOVIKONTAS" % (m, build.get("foot") or short)
    total = len(screens)
    slides = []
    notes, pool = [], photo_pool(mdir)
    # L58 - every photograph once in the whole course. First the photographs placed by hand (slide pictures, insets,
    # photos in drawings): one shown twice, or already shown by an EARLIER module, is a problem to fix. Then the L57
    # thumbnails take only what no deck of the course shows yet.
    here, me, mine = {}, module_label(mdir), []
    for s in screens:
        b = (build.get("screens") or {}).get(s["id"]) or {}
        page = slide_html(script, s, 0, total, b, mdir, figdir, foot, [])
        for rel in IMG_SRC.findall(page):
            if rel.startswith("assets/img/"):
                pid, at = photo_id(mdir, rel), "%s %s" % (me, s["id"])
                if pid in here and here[pid] != at:
                    probs.append("%s (%s): the photograph %s is already shown on %s - a photograph is shown once in the "
                                 "course (L58): choose a different one, or none" % (cs.place(script, s["id"]), s["id"], rel, here[pid]))
                elif pid not in here:
                    mine.append((photo_look(mdir, rel), at, rel, pid))
                here.setdefault(pid, at)
    looks = []
    elsewhere = shown_elsewhere(mdir, looks)
    for pid, at in sorted(here.items(), key=lambda x: x[1]):
        other, by_hand = elsewhere.get(pid, ("", False))
        if by_hand and other.split()[0] < me:      # the earlier module keeps it; a thumbnail there gives way instead
            probs.append("%s: its photograph is already shown on %s - a photograph is shown once in the course (L58): "
                         "choose a different one, or none" % (at, other))
    # 2.62.1 - the same photograph under another name and another record: matched by its look
    for i, (lk, at, rel, pid) in enumerate(mine):
        twin = next((x for x in mine[:i] if x[1] != at and same_look(lk, x[0])), None)
        if twin:
            probs.append("%s: the photograph %s looks the same as %s on %s - one photograph saved twice under two names "
                         "(L58: choose a different one, or none; and check both records - credit and rights)" % (at, rel, twin[2], twin[1]))
            continue
        old = next((x for x in looks if x[2] and x[1].split()[0] < me and same_look(lk, x[0])), None)
        if old and pid not in elsewhere:
            probs.append("%s: the photograph %s looks the same as %s already shown on %s - one photograph under two names "
                         "(L58: choose a different one, or none; and check both records - credit and rights)" % (at, rel, old[3], old[1]))
    taken = dict({k: v[0] for k, v in elsewhere.items()}, **here)
    seen = [(lk, at) for lk, at, _, _ in mine] + [(x[0], x[1]) for x in looks]
    for item in pool:                              # an L57 thumbnail never shows a look-alike of a shown photograph
        lk = photo_look(item[2], os.path.relpath(img_file(item[2], item[0]), item[2]).replace("\\", "/"))
        hit = next((at for l2, at in seen if same_look(lk, l2)), None)
        if hit and item[3] not in taken:
            taken[item[3]] = hit
    for n, s in enumerate(screens, 1):
        b = (build.get("screens") or {}).get(s["id"]) or {}
        recent =[layout_key(x) for x in slides[-VARIETY_WINDOW:]]   # L62: the look of the slides just before this one
        slides.append(slide_html(script, s, n, total, b, mdir, figdir, foot, probs, notes, pool, taken, build, recent, avoid,
                                 last))
        if chosen is not None and s["kind"] == "slide" and not s.get("recap"):    # 2.62.1: kept for the next compile
            chosen[s["id"]] = {"words": words_key(s, b), "key": list(layout_key(slides[-1]))}
    for a_, b_, s in zip(slides, slides[1:], screens[1:]):
        if layout_key(a_) == layout_key(b_) and layout_key(b_)[0] not in ("task-launch", "recap", ""):
            probs.append("%s: looks exactly like the slide before it (%s, %s ground) - two slides in a row never look the same "
                         "(L62); give one of them a picture, or ask for another template" % ((cs.place(script, s["id"]),) + layout_key(b_)))
    # 2.62.1 - 80 / 20 (owner, 2026-10-21): at least 80 % of the module's slides on the light ground. The rule is the
    # background's colour: a slide on the Navy ground ("dark") and a photograph framed on it count; a full-screen
    # photograph is its own background and does not
    dark = [s["id"] for s, x in zip(screens, slides)
            if re.search(r'<section class="[^"]*\b(dark|split)\b', x) and re.search(r'<section class="[^"]*\b(dark|photo)\b', x)]
    if len(dark) > DARK_SHARE * len(slides):
        probs.append("%s: %d of its %d slides are on the dark ground (%s) - at most %d (80 / 20: at least 80 %% light, owner "
                     "2026-10-21); give the others the light ground - take out \"dark\", or show a full-screen photograph in its "
                     "own column (\"composition\": \"wide-left\")" % (m, len(dark), len(slides), ", ".join(dark),
                                                                          int(DARK_SHARE * len(slides))))
    enlarge_photos(mdir, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(mdir))), "working_claude", "photo_originals", m),
                   [r for x in slides for r in IMG_SRC.findall(x) if r.startswith("assets/img/")], notes)
    # L61 - never three teaching slides in a row without a teaching picture (a task launch and the recap do not count)
    run = []
    for s, page in zip(screens, slides):
        seen = has_teaching_visual(page)
        if seen is None:
            continue
        run = [] if seen else run + [s["id"]]
        if len(run) == NO_VISUAL_RUN + 1:
            probs.append("%s: three teaching slides in a row without a teaching picture (%s) - at most %d; give one of them a drawing, "
                         "a photograph, an animation or a 3D model (L61)" % (cs.place(script, s["id"]), ", ".join(run), NO_VISUAL_RUN))
    blind = sorted(n for n, m, d, _ in pool if os.path.abspath(d) == os.path.abspath(mdir) and not m.get("shows"))
    if blind:
        notes.append((None, None, "%d photograph(s) without \"shows\" in _photo_meta.json, so no drawing can use them (L57): %s"
                      % (len(blind), ", ".join(blind))))
    for x in STYLES:                    # the compiled layouts need the factory's current style files in the module
        mine, canon = os.path.join(mdir, "assets", x), os.path.join(SKILLS, "course-module-ui", "templates", x)
        if os.path.isfile(canon) and (not os.path.isfile(mine) or io.open(mine, "rb").read() != io.open(canon, "rb").read()):
            probs.append("the module's copy of %s is not the factory's current one - run course-module-ui\\scripts\\"
                         "design_system.py install --update on the module folder" % x)
    uses_kit = any(' data-kit="' in x for x in slides)
    kit_parts = uses_kit and os.path.isfile(os.path.join(mdir, KIT_PARTS))
    shipped = [(x, os.path.join(SKILLS, "course-module-ux", "assets", x)) for x in PHOTO_FILES]
    shipped += [(x, os.path.join(SKILLS, "course-visuals", "kit", x)) for x in (KIT_FILES if uses_kit else ())]
    for x, canon in shipped:                  # shipped like the deck engine: the factory's copy, byte for byte
        mine = os.path.join(mdir, "assets", x)
        if os.path.isfile(canon) and (not os.path.isfile(mine) or io.open(mine, "rb").read() != io.open(canon, "rb").read()):
            probs.append("the module's copy of %s is not the factory's current one - run course-module-ui\\scripts\\"
                         "design_system.py install --update on the module folder" % x)
    # 2.59.0 - the 3D engine every scene is written for ships with the factory (three.js r128, MIT): a sheet that names it
    # gets the factory's copy - before, a builder had to find one, and IGF M03's declined its 3D scene for the lack of it
    if THREE_JS in build.get("scripts", []) and os.path.isfile(THREE_SRC):
        mine = os.path.join(mdir, *THREE_JS.split("/"))
        if not os.path.isfile(mine) or io.open(mine, "rb").read() != io.open(THREE_SRC, "rb").read():
            os.makedirs(os.path.dirname(mine), exist_ok=True)
            shutil.copyfile(THREE_SRC, mine)
    for rel in build.get("styles", []) + build.get("scripts", []):
        if not os.path.isfile(os.path.join(mdir, rel)):
            probs.append("the build sheet names %s, which is not in the module folder" % rel)
    inline = []
    for rel in build.get("inline", []):
        body, err = read_figure(mdir, rel, figdir)
        if err:
            probs.append("the build sheet's shared drawing parts %s %s" % (rel, err))
        elif body:
            inline.append(body)
    lang =script.get("course_language") or "English"
    lc = lang_code(lang)                                # L19: the landing card and the engine's controls in the course language
    w = LANDING.get(lc) or LANDING["en"]
    if lc not in LANDING:                               # reported, never a silent fall-back
        probs.append("the deck: the course is in %s - the deck's own words (Start, Next, Back ...) are not in the factory in "
                     "that language, so they were written in English (compile_module.py LANDING, gb_deck.js)" % lang)
    stamp =("GENERATED by course-factory %s compile_module.py from working_claude/script/%s.json (%s) and %s.build.json.\n"
             "     Do not edit this file: change the script (content_script.py propose) or the build sheet, and compile again."
             % (version, m, ("approved " + script.get("approved_hash", "")) if approved else "DRAFT - NOT APPROVED", m))
    head = ['<!DOCTYPE html>', '<html lang="%s">' % a(lc or lang[:2].lower()), "<head>",
            "<!-- %s -->" % stamp, '<meta charset="utf-8">',
            '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">',
            "<title>%s — %s</title>" % (m, e(title))]
    head += ['<link rel="stylesheet" href="../assets/%s">' % x for x in STYLES + ("gb_zoom.css",)]
    if uses_kit:
        head.append('<link rel="stylesheet" href="../assets/kit.css">')
    head += ['<link rel="stylesheet" href="../%s">' % a(x) for x in build.get("styles", [])]
    head.append("</head>")
    rule = build.get("landing_rule") or ""
    landing = ['<div id="landing">', '  <div class="landing-card">',
               '    <div class="brand-chip"><img src="../assets/novikontas_logo.svg" alt="Novikontas Academy"></div>']
    if rule:
        landing.append('    <div class="landing-rule">%s</div>' % e(rule))
    landing += ['    <div class="landing-mod">%s · %s</div>' % (m, e(w["module"].format(n=script.get("module")))),
                # 2.63.0 - no stats chips under the title ("40 min · 9 teaching screens · Self-check SC1 · Module check MC"):
                # the instructors' review of IGF Basic, 2026-10-21 - the module and its title only
                '    <h1 class="landing-title">%s</h1>' % e(title),
                '    <button id="startBtn" type="button">%s<span class="btn-label">Start</span></button>' % start_icon(),
                '    <div class="landing-hint">→ / Space next · ← back · F fullscreen · G all screens · N instructor cue</div>',
                "  </div>", "</div>"]
    body = ["<body>", '<a class="gbt-topback" href="../START_HERE_EXTENDED.html" hidden>Back</a>']
    body += inline + landing + [chrome_block(), '<main id="stage">', "\n\n".join(slides), "</main>",
                                '<script src="../assets/gb_deck.js"></script>',
                                '<script src="../assets/gb_fit.js"></script>',
                                '<script src="../assets/gb_zoom.js"></script>']
    if uses_kit:                        # before GBDeck.init: kit.js registers each figure's slide hooks
        body.append('<script src="../assets/kit.js"></script>')
    if kit_parts:
        body.append('<script src="../%s"></script>' % KIT_PARTS)
    body += ['<script src="../%s"></script>' % a(x) for x in build.get("scripts", [])]
    body += ["<script>",
             'GBDeck.init({ hooks: window.GB_HOOKS || {} });',      # its words: the engine's, by <html lang>
             "</script>", "</body>", "</html>", ""]
    return "\n".join(head + body), probs, notes


NEXT_STEPS = """
Next: compile\\scripts\\build_module.py <course> --module N runs this compile AND every check in one command, prints only
  what fails, and on a pass makes the visual review's sheets (GUIDE 2f - required: one review subagent reads them with
  compile\\REVIEW_PROMPT.md). A module is not handed over until the review is done and what it found is fixed."""


def module_folder(course, module, module_dir=None):
    """(folder, why not) - the module's folder: --module-dir as given; moduleNN for a number; for "final" (2.49.2) the
    folder after the course's last planned module - architecture.json's modules + 1, the same rule compile_course.py
    uses for the final assessment's title (IGF: 15 planned modules, so module16)"""
    if module_dir:
        return module_dir, None
    m = str(module).strip().lower()
    if m.isdigit():
        return os.path.join(course, workspace.MODULES, "module%02d" % int(m)), None
    if m == "final":
        ap_ = workspace.claude_path(course, "architecture.json")
        try:
            n = len(cs.load(ap_).get("modules") or []) + 1 if os.path.isfile(ap_) else 0
        except (OSError, ValueError):
            n = 0
        if n > 1:
            return os.path.join(course, workspace.MODULES, "module%02d" % n), None
        return None, ("the final assessment's folder is the one after the last planned module, and there is no approved "
                      "architecture.json (%s) to count them in - give the folder with --module-dir" % ap_)
    return None, "--module is a number (1, 2 ...) or \"final\", not \"%s\"" % module


def ensure_design(mdir):
    """2.49.2 (IGF M01-M15 builds, F1 / F2) - before anything is built the module's design files (the style files, the engines,
    kit.js ...) are checked against the factory's with design_system.py's own check, and put right when they only fell behind:
    a module built with another kit.js than the factory's gave false findings (27 small-text 'problems' that the factory's
    kit did not have), and a module folder made before --init-build had no design files at all.
    Returns (exit code, the sentence that says what happened). 0 = the files are the factory's now (said which: they were
    already, or MISSING / OUTDATED ones were installed); 2 = stopped, with the exact command, because a file was edited
    inside the module (a second dialect - replacing it is the owner's decision, design_choices.py records a chosen one)."""
    sys.path.insert(0, os.path.join(SKILLS, "course-module-ui", "scripts"))
    import design_system
    rows = design_system.states(mdir)
    bad = {}
    for r in rows:
        if r["state"] not in ("OK", "CHOSEN"):
            bad.setdefault(r["state"], []).append(r["file"])
    ver = design_system.plugin_version()
    if not bad:
        return 0, "Design files: all %d are the factory's own (version %s) - checked, nothing changed." % (len(rows), ver)
    cmd = 'python "%s" install "%s" --update' % (os.path.join(SKILLS, "course-module-ui", "scripts", "design_system.py"), mdir)
    if "CHANGED" in bad:
        return 2, ("Stopped - nothing was built.\n\n  These design files in\n    %s\n  were edited inside the module, so they are not "
                   "the factory's own (a second look for one course):\n%s\n  If that was not meant, put the factory's files back "
                   "(it also brings %s up to date):\n      %s\n  If the operator chose the different look, record it first "
                   "(design_choices.py add <course> --rule shared-design ...) and build again."
                   % (os.path.join(mdir, "assets"), "".join("    - %s\n" % x for x in bad["CHANGED"]),
                      "every other file" if len(bad) > 1 else "nothing else", cmd))
    import contextlib
    quiet = io.StringIO()
    with contextlib.redirect_stdout(quiet):
        code = design_system.install(mdir, update=True)
    if code != 0:
        return 2, "Stopped - the design files could not be put in the module:\n%s\n  By hand: %s" % (quiet.getvalue().rstrip(), cmd)
    if len(bad.get("MISSING", [])) == len(rows):
        say = "Design files were missing in %s - installed the factory's %d (version %s)." % (os.path.join(mdir, "assets"), len(rows), ver)
    else:
        say = ("Design files: %d were not the factory's current ones - updated from the factory (version %s): %s." % (
            sum(len(v) for v in bad.values()), ver,
            ", ".join("%s (%s)" % (f, "missing" if k == "MISSING" else "older version") for k, fs in sorted(bad.items()) for f in fs)))
    return 0, say


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("course")
    ap.add_argument("--module", required=True)
    ap.add_argument("--module-dir", help="the module folder (default: <course>\\modules\\module01)")
    ap.add_argument("--init-build", action="store_true", help="write a starter build sheet and stop")
    ap.add_argument("--draft", action="store_true", help="build from a script that is not approved yet - a preview")
    ap.add_argument("--force", action="store_true", help="overwrite a deck or task page that was changed by hand")
    ap.add_argument("--only", choices=("all", "deck", "tasks", "plan"), default="all",
                    help="build only the deck, only the trainee task pages (and the answer key), or only the instructor's "
                         "plan (default: all three)")
    ap.add_argument("--no-drawing-check", action="store_true",
                    help="skip the automatic drawing check (L54) - only while working on a drawing, never before showing")
    ap.add_argument("--full", action="store_true",
                    help="the drawing check judges every slide and task page again, not only those changed since their last "
                         "clean check (2.57.0)")
    o = ap.parse_args(argv)
    o.course = workspace.work_folder(o.course, create=False)
    p = cs.paths(o.course, o.module)
    if not os.path.isfile(p["script"]):
        print("Stopped - there is no content script for module %s:\n    %s" % (o.module, p["script"]))
        return 2
    script = cs.load(p["script"])
    bp = build_path(o.course, o.module)
    if o.init_build:
        if os.path.isfile(bp):
            print("Stopped - the build sheet is already there; it is changed with the Edit tool, never replaced:\n    %s" % bp)
            return 2
        gate = cs.course_gate.problems(o.course, o.module)      # belt and braces (2.42.0): content_script.py stops first
        if gate:
            print(cs.course_gate.stop_message(o.module, gate, "built"))
            return 2
        shared = sibling_sheets(bp)
        try:                                            # the course's own sheet, when it names a landing rule or pass mark
            cp = workspace.claude_path(o.course, "course.build.json")
            shared.insert(0, cs.load(cp) if os.path.isfile(cp) else {})
        except (OSError, ValueError):
            pass
        figdir, specs = workspace.claude_path(o.course, "figures", cs.mid(o.module)), {}
        cs.save(bp, starter_build(script, shared, figdir=figdir, specs=specs, mdir=module_folder(o.course, o.module, o.module_dir)[0]))
        print("Done - a starter build sheet:\n    %s\n  Next: fill in each slide's picture, edit the starter figures (parts and "
              "options: course-visuals\\kit\\CATALOGUE.md), then build and check in one command:\n    compile\\scripts\\"
              "build_module.py <course> --module %s" % (bp, o.module))
        sheet_screens = cs.load(bp).get("screens") or {}
        for sid, spec in specs.items():                 # 2.50.0: starter figure-kit specs - edited, never written from nothing
            cs.save(os.path.join(figdir, "%s.kit.json" % sid), spec)
            print("  starter figure: figures\\%s\\%s.kit.json - %d parts, %d steps (edit it: the parts are placed on a grid)%s"
                  % (cs.mid(o.module), sid, len(spec["parts"]), len(spec["steps"]),
                     " - the 2D figure if the 3D scene is declined" if (sheet_screens.get(sid) or {}).get("_2d") else ""))
        # the module's folder does not exist for a new module: make it and put the factory's style files and engines
        # in it, so the first compile does not stop (never inside the Android project - design_system.py refuses that).
        # 2.49.2: also when the folder is already there (assets\img made first) - the files are checked, not the folder
        mdir, why = module_folder(o.course, o.module, o.module_dir)
        if not mdir:
            print("\nStopped before the module's folder - %s" % why)
            return 2
        code, say = ensure_design(mdir)
        print("\n" + say)
        return 0 if code == 0 else 2
    approved = script.get("status") == "approved" and script.get("approved_hash") == cs.content_hash(script)
    if not approved and not o.draft:
        print("Stopped - the content script of module %s is not approved (or changed after approval).\n"
              "  The deck is built only from approved words (L29). For a preview, add --draft." % o.module)
        return 2
    build = cs.load(bp) if os.path.isfile(bp) else {}
    mdir, why = module_folder(o.course, o.module, o.module_dir)
    if not mdir:
        print("Stopped - %s" % why)
        return 2
    code, say = ensure_design(mdir)         # 2.49.2: the module's design files are the factory's, or this says what it did
    print(say + "\n" if code == 0 else say)
    if code != 0:
        return 2
    out = os.path.join(mdir, "presentation", "index.html")
    rec_path = workspace.module_record(mdir, RECORD)
    rec = cs.load(rec_path) if os.path.isfile(rec_path) else {}
    by_hand = lambda path, key: os.path.isfile(path) and not o.force and sha(io.open(path, encoding="utf-8").read()) != rec.get(key)
    if o.only in ("all", "deck") and by_hand(out, "index.html"):
        print("Stopped - nothing was overwritten.\n\n  The deck was changed by hand, or was built before the compiler:\n    %s\n"
              "  A change made in the deck would be lost. Put it into the script (content_script.py propose) or the\n"
              "  build sheet, then compile again with --force." % out)
        return 2
    # 2.49.2 (F7) - a preview built from a script that is not approved stays where its assets are, in the module's folder, but is
    # marked: check_course_package.py and compile_course.py leave a marked module out of the classroom package and say so
    mark = os.path.join(mdir, DRAFT_MARK)
    if not approved:
        with io.open(mark, "w", encoding="utf-8", newline="\n") as f:
            f.write(DRAFT_TEXT)
        print("Preview - this module is marked as a draft (%s): the classroom package leaves it out until the script is approved\n"
              "  and the module is built again." % DRAFT_MARK)
    elif os.path.isfile(mark) and o.only in ("all", "deck"):
        os.remove(mark)
        print("The draft mark (%s) is gone - the script is approved, so the module is part of the classroom package." % DRAFT_MARK)
    elif os.path.isfile(mark):     # the deck on disk is still the draft's - the mark goes only when the deck is built again
        print("The draft mark (%s) stays - the deck was built from the draft and --only %s does not rebuild it.\n"
              "  Compile with --only deck (or all) to bring the approved module into the classroom package." % (DRAFT_MARK, o.only))
    figdir = workspace.claude_path(o.course, "figures", cs.mid(o.module))
    back = restore(mdir, named_again(mdir, build, figdir))       # 2.52.0: named again - back in the package
    if back:
        print("Back in the package (named again; they were in assets\\img\\%s\\): %s\n" % (UNUSED, ", ".join(back)))
    probs, notes = [], []
    rec.update({"script_hash": cs.content_hash(script), "plugin_version": plugin_version()})
    written = []
    # 2.49.1 - the build record is saved with each file as it is written, so a crash later in the run never leaves a
    # file of the compiler's own that the next run refuses as "changed by hand"
    if o.only in ("all", "deck"):
        written.append(out)
        # 2.62.0 - the layouts build_module.py measured out (a slide built another way for L62 that the audit found does
        # not fit), per slide while its words are unchanged
        work_, mid_ = workspace.claude_path(o.course), cs.mid(o.module) if str(o.module).isdigit() else str(o.module)
        avoid, chosen = load_layout_avoid(work_, mid_), {}
        page, probs, notes = compile_deck(script, build, mdir, figdir, plugin_version(), approved, avoid,
                                          load_layouts(work_, mid_), chosen)
        try:                    # 2.62.1 - each slide's way, so the next compile keeps it while its words are unchanged
            os.makedirs(os.path.join(work_, "_build"), exist_ok=True)
            with io.open(os.path.join(work_, "_build", "%s_layouts.json" % mid_), "w", encoding="utf-8", newline="\n") as f:
                f.write(json.dumps(chosen, indent=1, sort_keys=True))
        except OSError:
            pass
        probs = write_cue_fixes(o.course, o.module, probs)            # 2.52.0: the drafted cue lines, ready for propose
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with io.open(out, "w", encoding="utf-8", newline="\n") as f:
            f.write(page)
        rec["index.html"] = sha(page)
        cs.save(rec_path, rec)
        probs += credit_path_problems(page, "presentation/index.html")
        # 2.63.0 - a number with its unit a figure prints is the approved script's or the course's sources' (L29)
        for where, rel, shown in unsupported_facts(script, build, figdir, mdir, o.course):
            probs.append("%s: its figure %s says \"%s\" - not in the approved script or the course's sources (working_claude: "
                         "retrieval packs, fact sheets, text extracts). Take it off the drawing, put it in the script "
                         "(content_script.py propose), or name where it is from in the build sheet: \"facts\": {\"%s\": "
                         "\"<source, page>\"}" % (where, rel, shown, shown))
        n = sum(1 for s in script["screens"] if s["kind"] in cs.INSTRUCTOR)
        print("Built %s - %d screens from the %s script.\n    %s" % (cs.mid(o.module), n, "approved" if approved else "DRAFT", out))
    if o.only in ("all", "tasks"):
        import task_pages
        pages, tprobs, left = task_pages.compile_tasks(script, build, mdir, figdir, plugin_version(), approved)
        probs += tprobs
        for path, page in sorted(pages.items()):
            key = os.path.relpath(path, mdir).replace("\\", "/")
            probs += credit_path_problems(page, key)
            if by_hand(path, key):
                probs.append("%s was changed by hand, or was built before the compiler - it was not overwritten. Put the change "
                             "into the script or the build sheet, then compile again with --force" % key)
                continue
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with io.open(path, "w", encoding="utf-8", newline="\n") as f:
                f.write(page)
            rec[key] = sha(page)
            cs.save(rec_path, rec)
            written.append(path)
            print("Built the task page %s" % key)
        for x in left:
            print("  left as it is: %s" % x)
    if o.only in ("all", "plan"):                      # 2.47.0 - the instructor's plan, from the same approved script
        import module_plan
        ppath, ppage = module_plan.plan_page(script, build, mdir, o.course, plugin_version(), approved, probs)
        key = os.path.relpath(ppath, mdir).replace("\\", "/")
        if by_hand(ppath, key):
            probs.append("%s was changed by hand, or was made before the compiler - it was not overwritten. Put the change "
                         "into the script or the build sheet, then compile again with --force" % key)
        else:
            os.makedirs(os.path.dirname(ppath), exist_ok=True)
            with io.open(ppath, "w", encoding="utf-8", newline="\n") as f:
                f.write(ppage)
            rec[key] = sha(ppage)
            cs.save(rec_path, rec)
            written.append(ppath)
            print("Built the module plan %s" % key)
    cs.save(rec_path, rec)
    if written:                     # 2.52.0 - only what a page shows ships; "used_in" says where it is shown
        left, changed = ship_only_shown(mdir)
        if left:
            print("\nPictures no page shows - left out of the package, kept in assets\\img\\%s\\ with their records (named in "
                  "the build sheet or a drawing again, they come back on the next build):\n%s"
                  % (UNUSED, "\n".join("  - %s" % x for x in left)))
        if changed:
            print("\"used_in\" rewritten from where the pages show them (assets\\img\\_photo_meta.json): %s" % ", ".join(changed))
    # L54 - every drawing whole and clean: checked by itself on every page just written, never left to memory
    if written and not o.no_drawing_check:
        import drawing_check
        # 2.57.0 - a slide or task page judged clean before, and unchanged in everything it loads since, is not judged again
        clean = workspace.claude_path(o.course, "_build", "%s_drawing_clean.json"
                                      % (cs.mid(o.module) if str(o.module).isdigit() else str(o.module)))
        dprobs, dnote = drawing_check.check(written, root=mdir, cache=clean, full=o.full)
        if dnote:
            print("\nNot checked: " + dnote)
        else:
            sl, pg = drawing_check.LAST.get("slides", (0, 0)), drawing_check.LAST.get("pages", (0, 0))
            print("Drawing check (L54): %s (judged %d of %d slides, %d of %d task pages - the rest unchanged since their last "
                  "clean check)" % ("%d problem(s)" % len(dprobs) if dprobs else "every drawing whole and clean",
                                    sl[0], sl[1], pg[0], pg[1]))
        probs += dprobs
    if not approved:
        probs.insert(0, "the script is not approved - what was built is a preview only, never handed over")
    if o.only in ("all", "deck"):                      # L60 - a strong recommendation, said loud, never a block (2.18.1)
        for f in cs.build_findings(o.course, script):
            if f["rule"] == "v_3d_none_built":
                print("\n" + "=" * 78 + "\nRECOMMENDED (L60) - " + f["detail"] + "\n" + "=" * 78)
    parts = [x for x in notes if x[0]]
    if o.only in ("all", "deck"):
        listed = write_to_take(o.course, script, parts)
        if notes:
            print("\nReal photographs still missing for what the drawings show (L57) - listed in\n    %s" % listed)
            for r in by_thing(parts) + [x[2] for x in notes if not x[0]]:
                print("  - " + r)
    if o.only in ("all", "tasks"):                     # 2.52.0 - a note, never a block
        tnotes = task_photo_notes(script, build, mdir)
        if tnotes:
            print("\nReal photographs a task question could be answered on (a note - nothing is blocked; the places are "
                  "boxes in % of the photo, measured on it):")
            for x in tnotes:
                print("  - " + x)
    if probs:
        print("\nTo fix before it is shown:")
        for x in probs:
            print("  - " + x)
        return 1
    print(NEXT_STEPS if o.only != "plan" else "\nNext: read the plan beside the deck - its minutes, its tasks and its sources are the script's.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
