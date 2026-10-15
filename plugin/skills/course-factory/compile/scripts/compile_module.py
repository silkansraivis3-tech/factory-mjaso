#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Build a module's presentation from its approved content script - the words are typed once (L29).

    compile_module.py <course folder> --module 1                 build modules\\module01\\presentation\\index.html
    compile_module.py <course folder> --module 1 --init-build    write a starter build sheet, build nothing
    compile_module.py <course folder> --module 1 --draft         build from a script that is not approved yet (preview only)
    compile_module.py <course folder> --module 1 --force         overwrite a deck that was changed by hand

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
  are shipped too (module folder). A figure script that animates registers its per-slide hooks as
      window.GB_HOOKS = window.GB_HOOKS || {};  GB_HOOKS.s05 = {enter: fn, leave: fn};
  and finds the slide's own lines by number: document.querySelector('#s04 [data-i="2"]').

HOW A SLIDE IS LAID OUT (the same for every module)
  layout visual_full  + a photograph   -> .slide.photo, the photo is the screen, the words over it
  layout visual_full  + a drawing      -> composition "stage"
  layout split                         -> "two-col": the words left, the picture right
  layout visual_wide                   -> "stage" when the words are short (<= 45), else "two-col wide-right"
  no layout                            -> ordinary flow
  "composition" in the build sheet overrides: opener, flow, two-col, wide-left, wide-right, stage
  The words: one line -> a statement; several lines -> the first is the statement and the rest its
  support list; a line starting with "• " is a list item, and the other lines are lead paragraphs.
  A task slide -> "activity": the set's code, the title, its lines; data-task-href to the set's page
  (tasks\\sc1_<title>.html, assessment\\check.html, assessment\\final.html). A room activity -> no page,
  data-link-hint from the build sheet or its first line.

THE OUTPUT IS GENERATED - NEVER EDIT IT BY HAND
Its first comment says so. A record of what was written is kept in working_claude\\modules\\module01\\
compiled.json; if the deck was changed by hand since, the build stops instead of overwriting the change
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
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(os.path.dirname(HERE))                 # course-factory
SKILLS = os.path.dirname(SKILL)
PLUGIN = os.path.dirname(SKILLS)
sys.path.insert(0, os.path.join(SKILL, "scripts"))
import content_script as cs  # noqa: E402
import workspace  # noqa: E402

SHELL = os.path.join(SKILLS, "course-module-ui", "templates", "gb_shell.html")
STYLES = ("gb_tokens.css", "gb_shell.css", "gb_compose.css")
IMAGES = (".jpg", ".jpeg", ".png", ".webp", ".gif")
COMPOSITIONS = ("opener", "flow", "two-col", "wide-left", "wide-right", "stage")
STAGE_MAX_WORDS = 45
CHECK_PAGES = {"MC": "../assessment/check.html", "FA": "../assessment/final.html"}
RECORD = "compiled.json"
TABLET_ICON = ('<svg class="act-ico" viewBox="0 0 64 48" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="3" '
               'stroke-linecap="round" stroke-linejoin="round"><rect x="6" y="4" width="52" height="40" rx="5"/>'
               '<path d="M16 33l9-10 7 7 6-5 10 8"/><circle cx="52" cy="24" r="1.6" fill="currentColor"/></svg>')
e = lambda s: html.escape(s or "", quote=False)
a = lambda s: html.escape(s or "", quote=True)


def plugin_version():
    try:
        with io.open(os.path.join(PLUGIN, ".claude-plugin", "plugin.json"), encoding="utf-8") as f:
            return json.load(f).get("version", "unknown")
    except (OSError, ValueError):
        return "unknown"


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def slug(s):
    return re.sub(r"[^a-z0-9]+", "_", (s or "").lower()).strip("_")[:50] or "task"


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


def marked(x, bold=True):
    """a line's words, the term before " - " or ": " in bold when it is a name of four words or fewer
    ("Gas mode: ...", "Tank connection space - ..."). The words are unchanged, so the match check still reads them."""
    m = TERM.match(x) if bold else None
    if m and 1 <= len(m.group(1).split()) <= 4 and not m.group(1)[:1].islower():
        return "<b>%s</b>%s%s" % (e(m.group(1)), e(m.group(2)), e(x[m.end():]))
    return e(x)


def words_html(lines, first_statement=True, dark_photo=False, emph=None, legend=False):
    """the slide's lines, each one marked as approved text (check_script_match reads data-script-field) and
    numbered data-i="1", "2" ... in script order, so a figure that steps can light up its line
    (document.querySelector('#s04 [data-i="3"]')). emph (from the build sheet): {"boxes": [2, 3], "conclusion": 5}"""
    emph = emph or {}
    boxes, concl = list(emph.get("boxes") or []), emph.get("conclusion")
    line = lambda tag, cls, i, x, bold=True: '<%s%s data-script-field="text" data-i="%d">%s</%s>' % (
        tag, ' class="%s"' % cls if cls else "", i, marked(x, bold), tag)
    if legend:
        return ['<ol class="legend">'] + ["  " + line("li", "", i, x) for i, x in enumerate(lines, 1)] + ["</ol>"]
    if dark_photo:            # the shared look styles .lead over a photograph, not a list - a bullet stays a lead line
        return [line("p", "lead", i, x, bold=False) for i, x in enumerate(lines, 1)]
    if len(lines) == 1:
        return [line("p", "statement", 1, lines[0], bold=False)]
    bullets = any(x.startswith("•") for x in lines)
    roles = []
    for i, x in enumerate(lines, 1):
        if i == concl:
            roles.append(("call", x))
        elif i in boxes:
            roles.append(("box alt" if boxes.index(i) % 2 else "box", x))
        elif x.startswith("•"):
            roles.append(("li", x.lstrip("•").strip()))
        elif first_statement and not bullets and i == 1 and not boxes:
            roles.append(("statement", x))
        elif first_statement and not bullets and not boxes:
            roles.append(("li", x))
        else:
            roles.append(("lead", x))
    out, run = [], []
    for i, (role, x) in enumerate(roles + [(None, None)], 1):
        if role == "li":
            run.append((i, x))
            continue
        if run:
            out.append('<ul class="support">')
            out += ["  " + line("li", "", k, r) for k, r in run]
            out.append("</ul>")
            run = []
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


def credit_line(meta, with_title=True):
    """Title · Author · Source · Licence · resized - who made it, where it is from, the licence, and that it was
    changed (CC BY / BY-SA 4.0 require these; the title is good practice, left out beside a caption that already
    says what the photo shows). The title is the meta's own, else the Wikimedia file name; "resized" when the
    stored size is not the original's."""
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


def figure_html(mdir, figdir, s, b, probs, where):
    """the slide's picture, as it goes into the page, and its credit line"""
    rel = (b.get("figure") or "").replace("\\", "/")
    if not rel:
        if (s.get("visual_kind") or "none") != "none":
            probs.append("%s has no picture file in the build sheet - it is planned as %s: %s"
                         % (where, s.get("visual_kind"), first_sentence(s.get("visual")) or "(no description)"))
        return "", "", False
    body, err = read_figure(mdir, rel, figdir)
    if err:
        probs.append("%s: its picture file %s %s" % (where, rel, err))
        return "", "", False
    if body is not None:
        return body, "", False
    meta = photo_meta(mdir, rel)
    alt = b.get("alt") or first_sentence(s.get("visual")) or first_sentence(meta.get("description"))
    credit = b.get("credit") or credit_line(meta)
    if meta.get("attribution_required") and not credit:
        probs.append("%s: the photograph %s needs a credit line, and assets\\img\\_photo_meta.json does not give one" % (where, rel))
    return '<img src="../%s" alt="%s">' % (a(rel), a(alt)), credit, True


# ------------------------------------------------------------------ one slide
def composition(s, b, is_photo, has_fig):
    c = b.get("composition")
    if c:
        return c
    lay = s.get("layout")
    if lay == "visual_full":
        return "photo" if is_photo else "stage"
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
    """a real photograph under the words (L48): {"photo": "assets/img/x.jpg", "caption": "..."} - the caption is
    instructor-chosen context with the credit, marked data-script-ignore so QA sees it counted"""
    rel = (ins.get("photo") or "").replace("\\", "/")
    if not os.path.isfile(os.path.join(mdir, rel)):
        probs.append("%s: its inset photograph %s is not in the module folder" % (where, rel or "(none named)"))
        return ""
    meta = photo_meta(mdir, rel)
    cap = " ".join(x for x in (ins.get("caption") or "", ins.get("credit") or credit_line(meta, with_title=not ins.get("caption"))) if x)
    alt = ins.get("alt") or first_sentence(ins.get("caption")) or first_sentence(meta.get("description"))
    return ('<figure class="inset"><img src="../%s" alt="%s"><figcaption data-script-ignore>%s</figcaption></figure>'
            % (a(rel), a(alt), e(cap)))


def attrs(d):
    return " ".join('%s="%s"' % (k, a(str(v))) for k, v in d.items() if v not in (None, ""))


def slide_html(script, s, n, total, b, mdir, figdir, foot, probs):
    m = cs.mid(script.get("module"))
    sid, kind = s["id"], s["kind"]
    where = "%s (%s)" % (cs.place(script, sid), sid)
    lines = cs.lines_of(s.get("text"))
    base = {"id": sid, "data-script": sid, "data-track": "theory", "data-mins": ("%g" % cs.minutes(s)) if cs.minutes(s) else "",
            "data-foot": foot, "data-cue": (s.get("notes") or "").strip()}

    if kind in ("task-slide", "activity"):
        code = (s.get("opens") or "").strip() or sid.upper()
        title = s.get("title") or ""
        short = title.split(" - ", 1)[1] if " - " in title else title
        is_check = code in CHECK_PAGES
        d = {"class": "slide dark activity", "data-title": "%s — %s" % (code, short[:1].upper() + short[1:]),
             "data-kind": "Check" if is_check else "Task", "data-block": "%s · %s" % (m, code), "data-visual": "none",
             "data-activity": code}
        if kind == "task-slide":
            d["data-task-href"] = CHECK_PAGES.get(code) or "../tasks/%s_%s.html" % (code.lower(), slug(short))
            team = s.get("team") or {}
            if team:
                d.update({"data-mode": "team", "data-team-size": team.get("size", ""),
                          "data-roles": "|".join(cs.team_roles(team))})
        else:
            d["data-link-hint"] = b.get("link_hint") or (lines[0] if lines else "")
        d.update(base)
        d["data-track"] = "practice" if kind == "activity" else "theory"
        body = ['<p class="act-code" data-script-ignore>%s</p>' % e(code),
                '<h2 class="act-title" data-script-field="title">%s</h2>' % e(title)]
        if kind == "task-slide":
            body.append(TABLET_ICON)
        body.append('<div class="act-lines">')
        body += ['  <p class="act-inst" data-script-field="text">%s</p>' % e(x) for x in lines]
        body.append("</div>")
        return ('<section %s>\n  <div class="slide-kind"><b>%s</b> · %s · %s</div>\n  <div class="slide-body activity">\n    %s\n  </div>\n</section>'
                % (attrs(d), d["data-kind"], m, code, "\n    ".join(body)))

    fig, credit, is_photo = figure_html(mdir, figdir, s, b, probs, where)
    comp = composition(s, b, is_photo, bool(fig))
    if comp not in COMPOSITIONS + ("photo",):
        probs.append("%s: the build sheet asks for the layout \"%s\" - the layouts are %s" % (where, comp, ", ".join(COMPOSITIONS)))
        comp = "flow"
    if comp == "photo" and not is_photo:
        comp = "stage"
    # a photograph beside the words fills the right of the screen - never a small photo in a column
    split_photo = is_photo and comp in ("two-col", "wide-left", "wide-right")
    if split_photo:
        comp = "photo"
    emph = {k: b[k] for k in ("boxes", "conclusion") if k in b}
    inset = inset_html(mdir, b["inset"], probs, where) if b.get("inset") else ""
    own = re.sub(r"[^\w -]", "", b.get("class") or "")          # a hook for the module's drawing styles, never a look
    d = {"class": "slide" + (" photo split" if split_photo else " photo" if comp == "photo" else " dark" if b.get("dark") else "")
                  + (" " + own if own else ""),
         "data-title": s.get("title"), "data-kind": "Theory", "data-block": "%s · %d" % (m, n),
         "data-visual": s.get("visual_kind") or "none"}
    d.update(base)
    head = '  <div class="slide-kind"><b>Theory</b> · %s · %d / %d</div>' % (m, n, total)
    h2 = '<h2 data-script-field="title">%s</h2>' % e(s.get("title"))
    credit_html = '\n  <div class="credit">%s</div>' % e(credit) if credit else ""
    ind = lambda xs, k: ("\n" + " " * k).join(xs)
    copy = lambda xs, k: ('<div class="copy">\n' + " " * (k + 2) + ind(xs + ([inset] if inset else []), k + 2)
                          + "\n" + " " * k + "</div>")

    if comp == "photo":
        return ('<section %s>\n  <div class="photo-wrap">%s</div>\n  <div class="photo-scrim"></div>\n%s\n'
                '  <div class="photo-copy">\n    %s\n    %s\n  </div>%s\n</section>'
                % (attrs(d), fig, head, h2, ind(words_html(lines, dark_photo=True), 4), credit_html))
    if comp == "stage":
        words = words_html(lines, first_statement=False, emph=emph, legend=bool(b.get("legend")))
        below = ind(words, 4) if b.get("legend") else copy(words, 4)
        return ('<section %s>\n%s\n  %s\n  <div class="slide-body stage">\n    %s\n    %s\n  </div>%s\n</section>'
                % (attrs(d), head, h2, fill(fig), below, credit_html))
    if comp in ("two-col", "wide-left", "wide-right"):
        # a drawing, an animation or a 3D model gets the wider column (owner, 2026-10-15: bigger pictures)
        cls = "two-col " + (comp if comp != "two-col" else "fig-wide")
        return ('<section %s>\n%s\n  %s\n  <div class="slide-body %s">\n    %s\n    %s\n  </div>%s\n</section>'
                % (attrs(d), head, h2, cls, copy(words_html(lines, emph=emph), 4), fill(fig), credit_html))
    if comp == "opener":
        return ('<section %s>\n%s\n  <div class="slide-body opener mid">\n    %s\n    %s\n  </div>%s\n</section>'
                % (attrs(d), head, h2, ind(words_html(lines, first_statement=False), 4), credit_html))
    figure = ("\n    " + fill(fig)) if fig else ""
    return ('<section %s>\n%s\n  %s\n  <div class="slide-body">\n    %s%s\n  </div>%s\n</section>'
            % (attrs(d), head, h2, copy(words_html(lines, emph=emph), 4), figure, credit_html))


# ------------------------------------------------------------------ the page
def build_path(course, module):
    return os.path.join(cs.paths(course, module)["dir"], cs.mid(module) + ".build.json")


def starter_build(script):
    return {"module": script.get("module"), "landing_rule": "", "styles": [], "scripts": [], "inline": [],
            "screens": {s["id"]: ({"figure": "", "visual_kind": s.get("visual_kind") or "none"} if s["kind"] == "slide" else
                                  {"link_hint": ""} if s["kind"] == "activity" else {})
                        for s in script["screens"] if s["kind"] in cs.INSTRUCTOR}}


def compile_deck(script, build, mdir, figdir, version, approved):
    probs = []
    m = cs.mid(script.get("module"))
    title = script.get("title") or ""
    screens = [s for s in script["screens"] if s["kind"] in cs.INSTRUCTOR]
    short = title.upper()
    if len(short) > 40:                                  # whole words only - never "CHARACTE"
        short = short[:41].rsplit(" ", 1)[0].rstrip(" -·,")
    foot = "%s · %s · NOVIKONTAS" % (m, build.get("foot") or short)
    total = len(screens)
    slides = []
    teach = 0
    for n, s in enumerate(screens, 1):
        b = (build.get("screens") or {}).get(s["id"]) or {}
        teach += s["kind"] == "slide"
        slides.append(slide_html(script, s, n, total, b, mdir, figdir, foot, probs))
    for x in STYLES:                    # the compiled layouts need the factory's current style files in the module
        mine, canon = os.path.join(mdir, "assets", x), os.path.join(SKILLS, "course-module-ui", "templates", x)
        if os.path.isfile(canon) and (not os.path.isfile(mine) or io.open(mine, "rb").read() != io.open(canon, "rb").read()):
            probs.append("the module's copy of %s is not the factory's current one - run course-module-ui\\scripts\\"
                         "design_system.py install --update on the module folder" % x)
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
    codes = [(s.get("opens") or "").strip() for s in screens if s["kind"] == "task-slide"]
    chips = ["%s min" % script.get("minutes_allocated")] if script.get("minutes_allocated") else []
    chips.append("%d teaching screens" % teach)
    chips += ["Self-check %s" % c if c.startswith("SC") else "Module check MC" if c == "MC" else
              "Final assessment" if c == "FA" else "Task %s" % c for c in codes if c]
    stamp = ("GENERATED by course-factory %s compile_module.py from working_claude/script/%s.json (%s) and %s.build.json.\n"
             "     Do not edit this file: change the script (content_script.py propose) or the build sheet, and compile again."
             % (version, m, ("approved " + script.get("approved_hash", "")) if approved else "DRAFT - NOT APPROVED", m))
    head = ['<!DOCTYPE html>', '<html lang="%s">' % a((script.get("course_language") or "English")[:2].lower()), "<head>",
            "<!-- %s -->" % stamp, '<meta charset="utf-8">',
            '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">',
            "<title>%s — %s</title>" % (m, e(title))]
    head += ['<link rel="stylesheet" href="../assets/%s">' % x for x in STYLES]
    head += ['<link rel="stylesheet" href="../%s">' % a(x) for x in build.get("styles", [])]
    head.append("</head>")
    rule = build.get("landing_rule") or ""
    landing = ['<div id="landing">', '  <div class="landing-card">',
               '    <div class="brand-chip"><img src="../assets/novikontas_logo.svg" alt="Novikontas Academy"></div>']
    if rule:
        landing.append('    <div class="landing-rule">%s</div>' % e(rule))
    landing += ['    <div class="landing-mod">%s · Module %s</div>' % (m, e(str(script.get("module")))),
                '    <h1 class="landing-title">%s</h1>' % e(title),
                '    <div class="landing-meta">%s</div>' % "".join('<span class="chip">%s</span>' % e(c) for c in chips),
                '    <button id="startBtn" type="button">%s<span class="btn-label">Start</span></button>' % start_icon(),
                '    <div class="landing-hint">→ / Space next · ← back · F fullscreen · G all screens · N instructor cue</div>',
                "  </div>", "</div>"]
    body = ["<body>", '<a class="gbt-topback" href="../START_HERE_EXTENDED.html" hidden>Back</a>']
    body += inline + landing + [chrome_block(), '<main id="stage">', "\n\n".join(slides), "</main>",
                                '<script src="../assets/gb_deck.js"></script>']
    body += ['<script src="../%s"></script>' % a(x) for x in build.get("scripts", [])]
    body += ["<script>",
             'GBDeck.init({ text: { cue: "Instructor cue", start: "Start" }, hooks: window.GB_HOOKS || {} });',
             "</script>", "</body>", "</html>", ""]
    return "\n".join(head + body), probs


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("course")
    ap.add_argument("--module", required=True)
    ap.add_argument("--module-dir", help="the module folder (default: <course>\\modules\\module01)")
    ap.add_argument("--init-build", action="store_true", help="write a starter build sheet and stop")
    ap.add_argument("--draft", action="store_true", help="build from a script that is not approved yet - a preview")
    ap.add_argument("--force", action="store_true", help="overwrite a deck that was changed by hand")
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
        cs.save(bp, starter_build(script))
        print("Done - a starter build sheet:\n    %s\n  Next: put each slide's picture file in \"figure\", then compile." % bp)
        return 0
    approved = script.get("status") == "approved" and script.get("approved_hash") == cs.content_hash(script)
    if not approved and not o.draft:
        print("Stopped - the content script of module %s is not approved (or changed after approval).\n"
              "  The deck is built only from approved words (L29). For a preview, add --draft." % o.module)
        return 2
    build = cs.load(bp) if os.path.isfile(bp) else {}
    mdir = o.module_dir or os.path.join(o.course, workspace.MODULES, "module%02d" % int(o.module))
    if not os.path.isdir(os.path.join(mdir, "assets")):
        print("Stopped - the module folder has no assets\\ yet:\n    %s\n"
              "  Run course-module-ui\\scripts\\design_system.py install on it first - it copies the factory's\n"
              "  style files and engines the deck uses." % mdir)
        return 2
    out = os.path.join(mdir, "presentation", "index.html")
    rec_path = workspace.module_record(mdir, RECORD)
    rec = cs.load(rec_path) if os.path.isfile(rec_path) else {}
    if os.path.isfile(out) and not o.force:
        now = sha(io.open(out, encoding="utf-8").read())
        if now != rec.get("index.html"):
            print("Stopped - nothing was overwritten.\n\n  The deck was changed by hand, or was built before the compiler:\n    %s\n"
                  "  A change made in the deck would be lost. Put it into the script (content_script.py propose) or the\n"
                  "  build sheet, then compile again with --force." % out)
            return 2
    figdir = os.path.join(o.course, workspace.CLAUDE, "figures", cs.mid(o.module))
    page, probs = compile_deck(script, build, mdir, figdir, plugin_version(), approved)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with io.open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write(page)
    rec.update({"index.html": sha(page), "script_hash": cs.content_hash(script), "plugin_version": plugin_version()})
    cs.save(rec_path, rec)
    n = sum(1 for s in script["screens"] if s["kind"] in cs.INSTRUCTOR)
    if not approved:
        probs.insert(0, "the script is not approved - this deck is a preview only, never handed over")
    print("Built %s - %d screens from the %s script.\n    %s" % (cs.mid(o.module), n, "approved" if approved else "DRAFT", out))
    if probs:
        print("\nTo fix before it is shown:")
        for x in probs:
            print("  - " + x)
        return 1
    print("\nNext: check_script_match.py, then look at it in the browser (the audit_*.js checks).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
