# -*- coding: utf-8 -*-
"""The trainee task pages of a module, built from its approved script - the words are typed once (L29).

Used by compile_module.py: every task slide that opens a set of questions (SC1, SC2 ..., MC, FA) gets its one page -
tasks\\sc1_<title>.html, assessment\\check.html, assessment\\final.html - with the factory's shared task engine
(course-task-ux/assets/gb_answer.js + gb_answer.css, installed by design_system.py like gb_deck.js). A page is only its
questions as markup; how a trainee answers, grading, the result ring and the classroom messages are the engine's.

THE BUILD SHEET, PER QUESTION (working_claude\\script\\M01.build.json "screens", keyed by the question's id)
  A question answered ON a picture names it, like a slide:
    "q01": {"figure": "assets/fig/m01_ga.svg"}                    tap the picture (hotspot, spot_the_hazard)
    "q03": {"figure": "assets/fig/m01_ga.svg", "areas": {"Funnel": [15.7, 0.9, 6.7, 15.0]}}
    "m01": {"figure": "assets/fig/m01_ga.svg", "labels": {"Fuel tank": {"at": "sp-tank", "box": [41.7, 85.8, 16.7]}}}
  An answer's place on the drawing is found by itself: the drawing's element whose data-name is the answer's words
  (or "at": its id), and in it the shape with class "hit" - a rect or circle. Anything the drawing does not name
  gets its box in the build sheet: [left, top, width, height] in % of the drawing. A label box ("box": [left, top,
  width]) is placed by the compiler when not given: above the drawing's middle line in the top row, else the bottom.
  The drawing's own labels (#labels, or anything marked data-task-hide) are hidden on the task - they give the answer.
  An element of the drawing can also be named by its id: "areas": {"Accommodation": "hs-acc"}; its shape may be a rect,
  a circle or a path of straight lines, and a group's translate() is followed.
  Beside a picture (set_value, find_the_fault, panel_operate) the "figure" is optional and shown above the task.
    "q04": {"step": 0.5}                                          the dial's step (default: worked out from the tolerance)
    "q10": {"states": {"Purge mode": ["Off", "Sweep", "Hold"]}, "start": {"Vent fan": "stopped"}}   a panel's positions
  The page sets: "pass_mark": 70 at the top of the build sheet (checks; default 70), "try_tablet": true|false on the
  task slide's entry (default: the course's first self-check opens with "try your tablet first").

THE KEYS (classroom-system.json task_page.answer_keys) - data-key = gb_key(question id, the item's words, value):
  choose / tap the picture / a gap's words / a reason / a step's action / a line of the document / the faulty part /
  a card that belongs in the plan / the moment to stop 1 right, 0 wrong; put in order the place 1, 2, 3; match the left
  side's words; sort into groups the group's name; label the drawing the place's id; operate the panel the control's
  name for the position it must end in ("-" for the others); set the value one key per accepted step, over the unit
  and the value. A card that is right or wrong AND has a place (build the plan, rebuild the incident) carries its place
  in data-place (0 = it stays out of the plan).

A TEAM TASK (2.39.0) - a task slide with "team" in the script - gets the task-mode / task-roles / task-scope metas
(classroom-system.json team_task) and a bar at the top the engine fills from the classroom's gb-team: the team's name
and the trainee's role. No team arrives: it runs as an individual task.

EVERY WAY OF ANSWERING IS COMPILED (2.38.0) - the nineteen of media-and-tasks.json, exactly what content_script.py
accepts; a question is one or more parts (a scenario's steps, the incident's order and then its stop point), each
with its own Check.
"""
from __future__ import annotations

import io
import json
import os
import re

import compile_module as cm
import content_script as cs

ENGINE = ("gb_answer.css", "gb_answer.js")
PAGE_CSS = ("gb_tokens.css", "gb_page.css", "gb_task.css", "gb_answer.css")
BUILT = {"single_choice", "read_instrument", "multi_select", "hotspot", "spot_the_hazard",
         "match", "categorise", "label_diagram", "order",
         "cloze", "choose_and_justify", "scenario", "set_value", "find_the_fault", "spot_the_error",     # 2.38.0
         "build_the_plan", "timeline", "compare", "panel_operate"}
assert BUILT == set(cs.USES), "every way of answering an approved script can hold is compiled"
ON_PICTURE = {"hotspot", "spot_the_hazard", "label_diagram"}
DEFAULT_PASS = 70
# the task screen's own words - the engine's are in gb_answer.js, overridden per language by GB_ANSWER_TEXT
WORDS = {"en": {
    "back": "Back", "try_title": "Try your tablet first", "try_tap": "Tap here",
    "try_1": "Tap the big blue circle.", "try_drag": "Drag me",
    "try_2": "Drag the box into the frame. Or tap the box, then tap the frame.",
    "try_hello": "Well done. You are ready for the self-check.",
    "pass": "Pass mark {pass} % – {need} of {total} right",
    "score": "Your score", "score_note": "Your score is for you only. Look at the questions below and ask your instructor about any you missed.",
    "again": "Start again", "start_self": "Start the self-check", "start_check": "Start the check",
    "choose_all": "Choose all that are right.", "module_n_check": "Module {n} check",
    "gap_n": "Gap {n}", "cloze_say": "Tap a gap, then choose the words that fit it.",
    "your_action": "What you do", "your_reason": "Why",
    "step_n": "Step {n} of {of}",
    "less": "Less", "more": "More", "decimal": ".",
    "symptoms": "What you notice", "fault_say": "Tap a part to check it. Then tap “This is the fault” on the part that is faulty.",
    "tap_to_check": "Tap to check", "is_fault": "This is the fault",
    "errors_say": "Tap every line that is wrong. Tap it again to take the mark off.",
    "plan_say": "Put the cards that belong into the plan, in order. Not every card belongs – leave those where they are.",
    "timeline_order": "1. Put the events in the order they happened.",
    "timeline_stop": "2. Now tap the event where it should have been stopped.",
    "panel_say": "Put every control in the position it must end in."}}
e, a = cm.e, cm.a


# ------------------------------------------------------------------ the sets
def sets(script):
    """[(task slide, code, [questions])] in the script's order - a set's questions follow its task slide"""
    out, by = [], {}
    for s in script["screens"]:
        if s["kind"] == "task-slide" and (s.get("opens") or "").strip():
            by[s["opens"].strip()] = (s, [])
            out.append(s["opens"].strip())
    for s in script["screens"]:
        if s["kind"] in cs.TASKS:
            code = (s.get("set") or "").strip() or {"self-check": "SC1", "module-check": "MC", "final": "FA"}[s["kind"]]
            if code in by:
                by[code][1].append(s)
    return [(by[c][0], c, by[c][1]) for c in out if by[c][1]]


def short_title(t):
    t = t or ""
    s = t.split(" - ", 1)[1] if " - " in t else t
    return s[:1].upper() + s[1:]


def shuffle(sid, items, key=lambda x: x):
    """the tablet shows items out of order - always the same order for the same script (one script, one file)"""
    if len(items) < 2:
        return list(items)
    out = sorted(items, key=lambda x: cs.gb_key(sid, key(x), "order"))
    if [key(x) for x in out] == [key(x) for x in items]:
        out = out[1:] + out[:1]
    return out


# ------------------------------------------------------------------ the drawing
NUM = r"-?\d+(?:\.\d+)?"


def attr(tag, name):
    m = re.search(r'\b%s\s*=\s*"([^"]*)"' % re.escape(name), tag)
    return m.group(1) if m else None


def viewbox(svg):
    m = re.search(r"<svg\b[^>]*>", svg)
    vb = attr(m.group(0), "viewBox") if m else None
    if not vb:
        return None
    try:
        x, y, w, h = (float(v) for v in re.split(r"[\s,]+", vb.strip()))
        return x, y, w, h
    except ValueError:
        return None


def element(svg, eid):
    """the markup of the element with this id - a whole <g> with what is in it"""
    m = re.search(r'<(\w+)\b[^>]*\bid="%s"[^>]*?(/?)>' % re.escape(eid), svg)
    if not m:
        return None
    if m.group(2) == "/" or m.group(1) != "g":
        return m.group(0)
    depth, i = 1, m.end()
    for t in re.finditer(r"<(/?)g\b[^>]*?(/?)>", svg[m.end():]):
        if t.group(2) == "/":
            continue
        depth += -1 if t.group(1) else 1
        if not depth:
            return svg[m.start():m.end() + t.end()]
    return svg[m.start():]


def named(svg, name):
    """the id of the drawing's element named this (data-name), case and spaces ignored"""
    want = re.sub(r"\s+", " ", name).strip().lower()
    for m in re.finditer(r"<\w+\b[^>]*>", svg):
        dn, i = attr(m.group(0), "data-name"), attr(m.group(0), "id")
        if dn and i and re.sub(r"\s+", " ", dn).strip().lower() == want:
            return i
    return None


def path_box(d):
    """(x, y, w, h) of a path written in absolute M / L / H / V / Z (a room's outline, a pipe) - None for curves or
    relative moves, which are left to a rect or circle of class "hit" """
    if not d or re.search(r"[^MLHVZ\d\s,.\-eE]", d):
        return None
    xs, ys, x, y = [], [], 0.0, 0.0
    for cmd, args in re.findall(r"([MLHVZ])([^MLHVZ]*)", d):
        n = [float(v) for v in re.findall(NUM, args)]
        if cmd in "ML":
            for i in range(0, len(n) - 1, 2):
                x, y = n[i], n[i + 1]
                xs.append(x), ys.append(y)
        elif cmd == "H":
            for v in n:
                x = v
                xs.append(x), ys.append(y)
        elif cmd == "V":
            for v in n:
                y = v
                xs.append(x), ys.append(y)
    return (min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)) if xs else None


def shift(tag):
    """the translate(x y) a tag moves what is in it by"""
    m = re.search(r"translate\(\s*(%s)(?:[\s,]+(%s))?\s*\)" % (NUM, NUM), attr(tag, "transform") or "")
    return (float(m.group(1)), float(m.group(2) or 0)) if m else (0.0, 0.0)


def shape_box(el):
    """(x, y, w, h) of the element's tappable shape: class "hit" first, else the element itself (rect / circle /
    path) - moved by the element's own translate() and the shape's"""
    tags = re.findall(r"<(?:rect|circle|ellipse|path)\b[^>]*>", el)
    hit = [t for t in tags if "hit" in (attr(t, "class") or "").split()] or tags[:1]
    if not hit:
        return None
    t = hit[0]
    try:
        if t.startswith("<rect"):
            box = tuple(float(attr(t, k) or 0) for k in ("x", "y", "width", "height"))
        elif t.startswith("<path"):
            box = path_box(attr(t, "d"))
            if box is None:
                return None
        else:
            r = float(attr(t, "r") or 0)
            rx, ry = float(attr(t, "rx") or r), float(attr(t, "ry") or r)
            cx, cy = float(attr(t, "cx") or 0), float(attr(t, "cy") or 0)
            box = cx - rx, cy - ry, 2 * rx, 2 * ry
    except ValueError:
        return None
    (ax, ay), (bx, by) = shift(re.match(r"<[^>]*>", el).group(0)) if el != t else (0.0, 0.0), shift(t)
    return box[0] + ax + bx, box[1] + ay + by, box[2], box[3]


def pct_box(box, vb, pad=8.0, min_px=56.0, width_px=1240.0):
    """a shape in the drawing's units as [left, top, width, height] in %, grown to a 56 px tap target (L42)"""
    x, y, w, h = box
    vx, vy, vw, vh = vb
    px = width_px / vw                                  # pixels per drawing unit at the tablet's width
    grow_w = max(pad, (min_px / px - w) / 2.0)
    grow_h = max(pad, (min_px / px - h) / 2.0)
    x, w = max(vx, x - grow_w), w + 2 * grow_w
    y, h = max(vy, y - grow_h), h + 2 * grow_h
    w, h = min(w, vx + vw - x), min(h, vy + vh - y)
    return [round(100.0 * (x - vx) / vw, 2), round(100.0 * (y - vy) / vh, 2), round(100.0 * w / vw, 2), round(100.0 * h / vh, 2)]


def taskfig(body, name):
    """the drawing as the page carries it: once, marked so the engine moves it into the question on screen"""
    return re.sub(r"<svg\b", '<svg class="taskfig" data-fig="%s"' % a(name), body, count=1)


BAND_PX, BOX_PX, WIDTH_PX = 64.0, 56.0, 1240.0     # a label row above and below the drawing; the box; the drawing's widest
LAB_PX = 400.0                                       # the labelled drawing's height at 1280 x 800: 100vh - 400px (gb_answer.css .ga.lab)


def ppu(vb):
    """px per drawing unit at 1280 x 800 - the drawing is as wide as the screen allows, or as tall as .ga.lab allows"""
    return min(WIDTH_PX / vb[2], LAB_PX / vb[3])


def with_bands(body, vb):
    """label the drawing: a band above and below it for the empty label boxes, so no box covers what is drawn"""
    x, y, w, h = vb
    band = BAND_PX * h / (LAB_PX - 2 * BAND_PX)          # when the height decides the size
    if LAB_PX / (h + 2 * band) > WIDTH_PX / w:            # the width decides it
        band = BAND_PX * w / WIDTH_PX
    nvb = (x, y - band, w, h + 2 * band)
    body = re.sub(r'(<svg\b[^>]*\bviewBox=")[^"]*(")', lambda m: m.group(1) + "%g %g %g %g" % nvb + m.group(2), body, count=1)
    return body, nvb


def figure_for(q, b, mdir, figdir, probs, where, bands=False):
    """(svg markup, view box, figure name) - or an <img> for a photograph"""
    rel = (b.get("figure") or "").strip()
    if not rel:
        probs.append("%s: '%s' is answered on a picture - put its drawing in the build sheet (\"figure\")" % (where, q.get("mechanic")))
        return None, None, None
    body, err = cm.read_figure(mdir, rel, figdir)
    if err:
        probs.append("%s: its drawing %s %s" % (where, rel, err))
        return None, None, None
    if body is None:                                   # a photograph: shipped in the module folder
        return '<img class="taskfig" src="../%s" alt="%s" data-fig="%s">' % (a(rel), a(q.get("visual") or ""), a(cm.slug(rel))), None, cm.slug(rel)
    vb = viewbox(body)
    if not vb:
        probs.append("%s: the drawing %s has no viewBox - the places on it cannot be worked out" % (where, rel))
    elif bands:
        body, vb = with_bands(body, vb)
    return body, vb, cm.slug(rel)


def area(svg, vb, name, b, where, probs):
    """[left, top, width, height] in % for one answer on the drawing"""
    given = (b.get("areas") or {}).get(name)
    if isinstance(given, list) and len(given) == 4:
        return given, (b.get("ids") or {}).get(name) or cm.slug(name)
    eid = given if isinstance(given, str) else named(svg or "", name)
    el = element(svg or "", eid) if eid else None
    box = shape_box(el) if el else None
    if not (box and vb):
        probs.append("%s: \"%s\" is not on the drawing - give the drawing an element with data-name=\"%s\" and a "
                     "shape of class \"hit\" in it, or its box in the build sheet: \"areas\": {\"%s\": [left, top, width, height]}"
                     % (where, name, name, name))
        return None, eid or cm.slug(name)
    return pct_box(box, vb), eid


# ------------------------------------------------------------------ one question
def q_head(n, q):
    return ('    <h1 class="q"><span class="num">%d</span><span class="stem" data-script-field="question">%s</span></h1>'
            % (n, e(q.get("question"))))


def q_why(q):
    return ('    <div class="why"><b class="vd"></b><p data-script-field="feedback">%s</p></div>' % e(q.get("feedback")))


def opt_buttons(sid, q, multi=False, cls="opts"):
    opts, right = q.get("options", []), cs.correct_letters(q)
    out = ['    <div class="%s%s">' % (cls, " multi" if multi else "")]
    for L, o in zip(cs.letters(len(opts)), opts):
        out.append('      <button type="button" class="opt" data-script-field="opt.%s" data-key="%s">%s</button>'
                   % (L, cs.gb_key(sid, o, 1 if L in right else 0), e(o)))
    out.append("    </div>")
    return out


def chips(sid, items, places=None):
    """items: [(words, value)] - shuffled; places: {words: place} - a card that is right or wrong AND has a place
    (build the plan, the incident) carries the place in data-place (0 = it stays out)"""
    out = []
    for t, v in shuffle(sid, items, key=lambda x: x[0]):
        place = ' data-place="%s"' % cs.gb_key(sid, t, places.get(t, 0)) if places is not None else ""
        out.append('      <button type="button" class="chip" data-script-field="answer" data-key="%s"%s>%s</button>'
                   % (cs.gb_key(sid, t, v), place, e(t)))
    return out


def answer_buttons(sid, items, seed=None, cls="opt", order=True):
    """items: [(words, 1 right / 0 wrong)] as answer buttons - shuffled (a script writes the right one first)"""
    items = shuffle(seed or sid, items, key=lambda x: x[0]) if order else items
    return ['<button type="button" class="%s" data-script-field="answer" data-key="%s">%s</button>'
            % (cls, cs.gb_key(sid, t, v), e(t)) for t, v in items]


def picks(text):
    """'right* | wrong | wrong' -> [(words, 1 / 0)]"""
    return [(cs.unstar(p), 1 if cs.starred(p) else 0) for p in text.split("|") if p.strip()]


def slots(n):
    out = ['    <div class="rows order">']
    out += ['      <div class="row"><div class="name">%d</div><div class="zone slot" data-cap="1" data-val="%d"></div></div>' % (i, i)
            for i in range(1, n + 1)]
    return out + ["    </div>"]


def picture(q, b, mdir, figdir, figs, probs, where):
    """a picture beside a task that is not answered on it (set the value, find the fault, the panel): optional"""
    if not (b.get("figure") or "").strip():
        return []
    if b["figure"].lower().endswith(cm.KIT_SPEC):
        probs.append("%s: a figure-kit spec (%s) is not shown on a task page yet - name a drawing (.svg) or a photograph"
                     % (where, b["figure"]))
        return []
    body, vb, _ = figure_for(q, b, mdir, figdir, probs, where)
    if not body:
        return []
    figs["_pic"] = True
    ar = ' style="--ar:%.3f"' % (vb[2] / vb[3]) if vb else ""
    return ['    <div class="instrument"><div class="ga"%s>%s</div></div>' % (ar, re.sub(r"<svg\b", '<svg class="taskfig"', body, count=1) if vb else body)]


# ------------------------------------------------------------------ set the value: the dial
def decimals(x):
    s = ("%.10f" % x).rstrip("0").rstrip(".")
    return len(s.split(".")[1]) if "." in s else 0


def dial_step(v, tol, lo, hi, given=None):
    """(step, decimals) of the dial: the tolerance when the value and the range fall on it, else the largest round
    step under it that they do - 4 to 400 steps along the track; the build sheet's "step" when it gives one"""
    if given:
        cands = [float(given)]
    else:
        cands = ([tol] if tol > 0 else []) + [m * 10 ** p for p in range(3, -4, -1) for m in (5, 2, 1)]
        cands = [c for c in cands if tol <= 0 or c <= tol + 1e-12]
    for st in cands:
        n, k = (hi - lo) / st, (v - lo) / st
        if 4 <= round(n) <= 400 and abs(n - round(n)) < 1e-6 and abs(k - round(k)) < 1e-6:
            return st, max(decimals(st), decimals(lo))
    return None, 0


def dial(sid, q, b, w, where, probs):
    mm = cs.SET_VALUE.match(q.get("answer") or "")
    if not mm:
        probs.append("%s: 'set the value' is not written as: value unit ± tolerance, range low to high" % where)
        return []
    num = lambda s: float(s.replace(",", "."))
    v, unit, tol, lo, hi = num(mm.group(1)), mm.group(2), num(mm.group(3)), num(mm.group(4)), num(mm.group(5))
    step, dec = dial_step(v, tol, lo, hi, b.get("step"))
    if step is None:
        probs.append("%s: the dial's steps cannot be worked out from %s - give them in the build sheet: \"step\": 0.5"
                     % (where, q.get("answer")))
        return []
    S = 10 ** dec
    LO, ST, n = round(lo * S), round(step * S), round((hi - lo) / step)
    keys = [cs.gb_key(sid, unit, "%.*f" % (dec, (LO + k * ST) / S)) for k in range(n + 1)
            if abs((LO + k * ST) / S - v) <= tol + step * 1e-6]          # one key per accepted step
    shown = lambda x: ("%.*f" % (decimals(x), x)).replace("-", "−").replace(".", w["decimal"])
    return ['    <div class="dial" data-lo="%g" data-hi="%g" data-step="%g" data-dec="%d" data-unit="%s" data-key="%s">'
            % (lo, hi, step, dec, a(unit), " ".join(keys)),
            '      <div class="dial-read"><b class="dial-val">&#8211;</b> <span class="dial-unit">%s</span></div>' % e(unit),
            '      <div class="dial-row"><button type="button" class="dial-minus" aria-label="%s">&#8722;</button>'
            '<div class="dial-track"><i class="dial-band"></i><i class="dial-fill"></i><span class="dial-thumb"></span></div>'
            '<button type="button" class="dial-plus" aria-label="%s">+</button></div>' % (a(w["less"]), a(w["more"])),
            '      <div class="dial-scale"><span>%s %s</span><span>%s %s</span></div>' % (shown(lo), e(unit), shown(hi), e(unit)),
            "    </div>"]


# ------------------------------------------------------------------ operate the panel
# a control's other positions, when the build sheet does not list them ("states": {"control": ["open", "closed"]})
PAIRS = [("open", "closed"), ("open", "shut"), ("on", "off"), ("running", "stopped"), ("start", "stop"),
         ("started", "stopped"), ("auto", "manual"), ("automatic", "manual"), ("local", "remote"), ("locked", "unlocked"),
         ("in service", "out of service"), ("enabled", "disabled"), ("energised", "de-energised"),
         ("energized", "de-energized"), ("connected", "disconnected"), ("engaged", "disengaged"), ("reset", "tripped"),
         ("atvērts", "aizvērts"), ("ieslēgts", "izslēgts"), ("darbojas", "apturēts"), ("automātisks", "manuāls"),
         ("открыт", "закрыт"), ("открыто", "закрыто"), ("включен", "выключен"), ("включён", "выключен"),
         ("работает", "остановлен"), ("автомат", "ручной")]
# a control the figure kit draws: its part and the value of each position (course-visuals/kit/SPEC.md)
KIT_STATE = {"open": ("valve", 1), "closed": ("valve", 0), "shut": ("valve", 0), "atvērts": ("valve", 1),
             "aizvērts": ("valve", 0), "открыт": ("valve", 1), "закрыт": ("valve", 0), "открыто": ("valve", 1),
             "закрыто": ("valve", 0), "running": ("pump", 1), "stopped": ("pump", 0), "darbojas": ("pump", 1),
             "apturēts": ("pump", 0), "работает": ("pump", 1), "остановлен": ("pump", 0)}


def cased(word, like):
    return word.upper() if like.isupper() and len(like) > 1 else word[:1].upper() + word[1:] if like[:1].isupper() else word


def positions(control, target, b):
    """the positions a control can be put in, the one it must end in among them - or None"""
    given = (b.get("states") or {}).get(control)
    if given:
        return [str(x).strip() for x in given] if target.lower() in [str(x).strip().lower() for x in given] else None
    for p in PAIRS:
        if target.lower() in p:
            return [target if x == target.lower() else cased(x, target) for x in p]
    return None


def kit_symbol(sid, n, states, start):
    """a little figure-kit drawing of the control (a valve, a pump) when every position is one the kit draws"""
    kinds = {KIT_STATE.get(s.lower(), (None,))[0] for s in states}
    if len(kinds) != 1 or None in kinds:
        return ""
    kind = kinds.pop()
    v = KIT_STATE[start.lower()][1] if start and start.lower() in KIT_STATE else (0.5 if kind == "valve" else 0)
    part = ({"id": "c", "type": "valve", "x": 100, "y": 58, "size": 22, "state": False, "trip": False, "value": v}
            if kind == "valve" else {"id": "c", "type": "pump", "x": 92, "y": 50, "r": 26, "value": v})
    spec = {"size": [200, 100], "parts": [part]}
    sid_ = "kit-%s-%d" % (sid, n)
    return ('<svg class="csym" data-kit="#%s" data-no-zoom aria-hidden="true"></svg>'
            '<script type="application/json" id="%s">%s</script>' % (sid_, sid_, json.dumps(spec, separators=(",", ":"))))


def label_boxes(places, vb):
    """where the empty label boxes go when the build sheet does not say: in the band above the drawing for what is in
    its upper half, in the band below for the rest, in order across - the same order as what they point at"""
    top = sorted([p for p in places if p["box"][1] + p["box"][3] / 2 < 50], key=lambda p: p["box"][0] + p["box"][2] / 2)
    bot = sorted([p for p in places if p not in top], key=lambda p: p["box"][0] + p["box"][2] / 2)
    hp = vb[3] * ppu(vb)                                  # the drawing's height in px at 1280 x 800
    gap = (BAND_PX - BOX_PX) / 2
    for row, y in ((top, round(100 * gap / hp, 2)), (bot, round(100 * (hp - gap - BOX_PX) / hp, 2))):
        n = len(row)
        w = min(17.0, 96.0 / max(n, 1) - 1.5)
        for i, p in enumerate(row):
            cx = p["box"][0] + p["box"][2] / 2
            left = min(max(cx - w / 2, 1.0), 99.0 - w)
            if i and left < row[i - 1]["at"][0] + row[i - 1]["at"][2] + 1.0:
                left = row[i - 1]["at"][0] + row[i - 1]["at"][2] + 1.0
            p["at"] = [round(left, 2), y, round(w, 2)]
    return places


def question_html(n, q, b, mdir, figdir, figs, probs, w=None):
    w = w or WORDS["en"]
    sid, m = q["id"], cs.mech(q)
    where = "%s (%s)" % (q.get("set") or "", sid)
    out = ['  <section class="scr" data-script="%s" data-mech="%s"%s>' % (sid, m, "%s"), q_head(n, q)]
    extra = ""
    if m in ("single_choice", "multi_select"):
        if m == "multi_select":
            out.append('    <p class="opts-say">%s</p>' % e(w["choose_all"]))
        out += opt_buttons(sid, q, multi=m == "multi_select")
    elif m == "read_instrument":
        body, vb, name = figure_for(q, b, mdir, figdir, probs, where, (b.get("figure") or "").strip() in figs["_bands"])
        if body:
            ar = ' style="--ar:%.3f"' % (vb[2] / vb[3]) if vb else ""
            out.append('    <div class="instrument"><div class="ga"%s>%s</div></div>' % (ar, body if not vb else re.sub(r"<svg\b", '<svg class="taskfig"', body, count=1)))
        out += opt_buttons(sid, q)
    elif m in ("hotspot", "spot_the_hazard"):
        items, right = cs.answer_items(q)
        body, vb, name = figure_for(q, b, mdir, figdir, probs, where, (b.get("figure") or "").strip() in figs["_bands"])
        if len(right) > 1:
            extra = ' data-multi="1"'
        holder = []
        if body and name not in figs:
            figs[name] = True
            holder.append(taskfig(body, name) if vb else body)
        for t in items:
            box, _ = area(body if vb else None, vb, t, b, where, probs) if body else (None, None)
            if box is None:
                continue
            holder.append('      <button type="button" class="hot" style="left:%s%%;top:%s%%;width:%s%%;height:%s%%" '
                          'data-script-field="answer" data-key="%s"><span class="vh">%s</span></button>'
                          % (box[0], box[1], box[2], box[3], cs.gb_key(sid, t, 1 if t in right else 0), e(t)))
        ar = ' style="--ar:%.3f"' % (vb[2] / vb[3]) if vb else ""
        out.append('    <div class="stage"><div class="ga" data-fig="%s"%s>' % (a(name or ""), ar))
        out += holder
        out.append("    </div></div>")
    elif m == "label_diagram":
        items, _ = cs.answer_items(q)
        body, vb, name = figure_for(q, b, mdir, figdir, probs, where, (b.get("figure") or "").strip() in figs["_bands"])
        places = []
        for t in items:
            given = (b.get("labels") or {}).get(t) or {}
            box, eid = area(body if vb else None, vb, t, dict(b, areas={t: given["at"]} if given.get("at") else b.get("areas") or {}),
                            where, probs) if body else (None, None)
            if box is None:
                continue
            places.append({"t": t, "id": eid, "box": box, "at": given.get("box")})
        auto = [p for p in places if not p["at"]]
        if auto:
            label_boxes(auto, vb)
        ar = ' style="--ar:%.3f"' % (vb[2] / vb[3]) if vb else ""
        out.append('    <div class="stage"><div class="ga lab" data-fig="%s"%s>' % (a(name or ""), ar))
        if body and name not in figs:
            figs[name] = True
            out.append(taskfig(body, name) if vb else body)
        if places:
            out.append('      <svg class="leaders" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true" data-audit-ignore data-no-zoom>')
            for p in places:
                bx, by, bw = p["at"]
                bh = 100.0 * BOX_PX / (vb[3] * ppu(vb)) if vb else 0.0
                x1, y1 = bx + bw / 2, by + (bh if by < 50 else 0)
                x2, y2 = p["box"][0] + p["box"][2] / 2, p["box"][1] + p["box"][3] / 2
                out.append('        <line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" vector-effect="non-scaling-stroke"/>' % (x1, y1, x2, y2))
            out.append("      </svg>")
        for p in places:
            out.append('      <div class="lbox zone" data-cap="1" data-zone data-val="%s" style="left:%s%%;top:%s%%;width:%s%%;height:%.2f%%"></div>'
                       % (a(p["id"]), p["at"][0], p["at"][1], p["at"][2], 100.0 * BOX_PX / (vb[3] * ppu(vb)) if vb else 12))
        out.append("    </div></div>")
        out.append('    <div class="tray">')
        out += chips(sid, [(p["t"], p["id"]) for p in places])
        out.append("    </div>")
    elif m == "match":
        pairs = [[x.strip() for x in ln.split("=", 1)] for ln in cs.lines_of(q.get("answer")) if "=" in ln]
        out.append('    <div class="rows">')
        for left, _ in pairs:
            out.append('      <div class="row"><div class="name" data-script-field="answer">%s</div>'
                       '<div class="zone slot" data-cap="1" data-val="%s"></div></div>' % (e(left), a(left)))
        out.append("    </div>")
        out.append('    <div class="tray">')
        out += chips(sid, [(right, left) for left, right in pairs])
        out.append("    </div>")
    elif m == "categorise":
        groups = []
        for ln in cs.lines_of(q.get("answer")):
            g, _, rest = ln.partition(":")
            groups.append((g.strip(), [i.strip() for i in rest.split(";") if i.strip()]))
        out.append('    <div class="tray">')
        out += chips(sid, [(i, g) for g, its in groups for i in its])
        out.append("    </div>")
        out.append('    <div class="grps">')
        for g, _ in groups:
            out.append('      <div class="grp"><div class="gname" data-script-field="answer">%s</div><div class="zone" data-val="%s"></div></div>'
                       % (e(g), a(g)))
        out.append("    </div>")
    elif m == "order":
        items, _ = cs.answer_items(q)
        out.append('    <div class="rows order">')
        for i in range(1, len(items) + 1):
            out.append('      <div class="row"><div class="name">%d</div><div class="zone slot" data-cap="1" data-val="%d"></div></div>' % (i, i))
        out.append("    </div>")
        out.append('    <div class="tray">')
        out += chips(sid, [(t, i) for i, t in enumerate(items, 1)])
        out.append("    </div>")
    elif m == "cloze":                                  # the sentence with its gaps; each gap's choices under it
        sent, groups = [], []
        for bit in re.split(r"(\[[^\]]+\])", q.get("answer", "")):
            if bit.startswith("[") and bit.endswith("]"):
                groups.append(picks(bit[1:-1]))
                sent.append('<button type="button" class="gap" data-g="%d" aria-label="%s"></button>'
                            % (len(groups), a(w["gap_n"].format(n=len(groups)))))
            elif bit.strip():
                sent.append('%s<span data-script-field="answer">%s</span>%s'
                            % (" " if bit[0].isspace() else "", e(bit.strip()), " " if bit[-1].isspace() else ""))
            elif bit:
                sent.append(" ")
        out.append('    <p class="cloze">%s</p>' % "".join(sent))
        out.append('    <p class="opts-say">%s</p>' % e(w["cloze_say"]))
        out.append('    <div class="cgs">')
        for n_, g in enumerate(groups, 1):
            out.append('      <div class="cg opts" data-g="%d">' % n_)
            out += ["        " + x for x in answer_buttons(sid, g, "%s.g%d" % (sid, n_))]
            out.append("      </div>")
        out.append("    </div>")
    elif m == "choose_and_justify":                     # the actions and the reasons side by side, one Check
        out.append('    <div class="cj">')
        out.append('      <div><p class="phead">%s</p>' % e(w["your_action"]))
        out += ["  " + x for x in opt_buttons(sid, q, cls="cg opts")]
        out.append("      </div>")
        out.append('      <div><p class="phead">%s</p>' % e(w["your_reason"]))
        out.append('      <div class="cg opts">')
        out += ["        " + x for x in answer_buttons(sid, [(cs.unstar(x), 1 if cs.starred(x) else 0) for x in cs.lines_of(q.get("answer"))])]
        out.append("      </div></div>")
        out.append("    </div>")
    elif m == "scenario":                               # one part per step: decide, see, decide again
        steps = cs.lines_of(q.get("answer"))
        for n_, ln in enumerate(steps, 1):
            sit, _, acts = ln.partition("=>")
            out.append('    <div class="part step">')
            out.append('      <p class="phead">%s</p>' % e(w["step_n"].format(n=n_, of=len(steps))))
            out.append('      <p class="sit" data-script-field="answer">%s</p>' % e(sit.strip()))
            out.append('      <div class="cg opts">')
            out += ["        " + x for x in answer_buttons(sid, picks(acts), "%s.s%d" % (sid, n_))]
            out.append("      </div>")
            out.append("    </div>")
    elif m == "set_value":
        out += picture(q, b, mdir, figdir, figs, probs, where)
        out += dial(sid, q, b, w, where, probs)
    elif m == "find_the_fault":                         # the symptoms; each part a card - tap to check, then name it
        ls = cs.lines_of(q.get("answer"))
        out += picture(q, b, mdir, figdir, figs, probs, where)
        out.append('    <div class="sym"><p class="phead">%s</p>' % e(w["symptoms"]))
        out += ['      <p data-script-field="answer">%s</p>' % e(x.strip().lstrip("!").strip()) for x in ls if x.lstrip().startswith("!")]
        out.append("    </div>")
        out.append('    <p class="opts-say">%s</p>' % e(w["fault_say"]))
        out.append('    <div class="cg ffs">')
        parts = [(cs.unstar(x).partition(":")[0].strip(), cs.unstar(x).partition(":")[2].strip(), 1 if cs.starred(x) else 0)
                 for x in ls if not x.lstrip().startswith("!")]
        for part, seen, bad in shuffle(sid, parts, key=lambda x: x[0]):
            out.append('      <div class="ffc"><button type="button" class="ff-look"><span class="ff-part" data-script-field="answer" '
                       'data-key="%s">%s</span><span class="ff-tap">%s</span><span class="ff-seen" data-script-field="answer">%s</span>'
                       '</button><button type="button" class="opt ff-pick">%s</button></div>'
                       % (cs.gb_key(sid, part, bad), e(part), e(w["tap_to_check"]), e(seen), e(w["is_fault"])))
        out.append("    </div>")
    elif m == "spot_the_error":                         # the document as written; tap a line to flag it
        out.append('    <p class="opts-say">%s</p>' % e(w["errors_say"]))
        out.append('    <div class="cg opts multi doc" data-multi="1">')
        for ln in cs.lines_of(q.get("answer")):
            line, _, why = ln.partition("=>")
            out.append('      <div class="dl">%s%s</div>' % (
                answer_buttons(sid, [(cs.unstar(line), 1 if cs.starred(line) else 0)], order=False)[0],
                '<p class="ewhy" data-script-field="answer">%s</p>' % e(why.strip()) if why.strip() else ""))
        out.append("    </div>")
    elif m == "build_the_plan":                         # numbered slots for the cards that belong; the rest stay out
        ls = cs.lines_of(q.get("answer"))
        good = [cs.unstar(x) for x in ls if cs.starred(x)]
        extra = ' data-need="slots"'
        out.append('    <p class="opts-say">%s</p>' % e(w["plan_say"]))
        out += slots(len(good))
        out.append('    <div class="tray">')
        out += chips(sid, [(cs.unstar(x), 1 if cs.starred(x) else 0) for x in ls], {t: i for i, t in enumerate(good, 1)})
        out.append("    </div>")
    elif m == "timeline":                               # part 1 the order, part 2 the moment it should have stopped
        ls = cs.lines_of(q.get("answer"))
        out.append('    <div class="part">')
        out.append('      <p class="phead">%s</p>' % e(w["timeline_order"]))
        out += ["  " + x for x in slots(len(ls))]
        out.append('      <div class="tray">')
        out += ["  " + x for x in chips(sid, [(cs.unstar(x), 1 if cs.starred(x) else 0) for x in ls],
                                        {cs.unstar(x): i for i, x in enumerate(ls, 1)})]
        out.append("      </div>")
        out.append("    </div>")
        out.append('    <div class="part" data-kind="stop"><p class="phead">%s</p></div>' % e(w["timeline_stop"]))
    elif m == "compare":                                # the options as columns, one row per figure
        opts, right = q.get("options", []), cs.correct_letters(q)
        out.append('    <table class="cmp cg">')
        out.append('      <thead><tr><th class="what"></th>%s</tr></thead>' % "".join(
            '<th><button type="button" class="opt" id="%s-%s" data-script-field="opt.%s" data-key="%s">%s</button></th>'
            % (a(sid), L, L, cs.gb_key(sid, o, 1 if L in right else 0), e(o)) for L, o in zip(cs.letters(len(opts)), opts)))
        out.append("      <tbody>")
        for ln in cs.lines_of(q.get("answer")):
            what, _, vals = ln.partition(":")
            out.append('        <tr><th class="what" data-script-field="answer">%s</th>%s</tr>' % (e(what.strip()), "".join(
                '<td data-for="%s-%s" data-script-field="answer">%s</td>' % (a(sid), L, e(v.strip()))
                for L, v in zip(cs.letters(len(opts)), vals.split("|")))))
        out.append("      </tbody>")
        out.append("    </table>")
    elif m == "panel_operate":                          # each control and its positions; the kit draws what it can
        out += picture(q, b, mdir, figdir, figs, probs, where)
        out.append('    <p class="opts-say">%s</p>' % e(w["panel_say"]))
        out.append('    <div class="panel">')
        for n_, ln in enumerate(cs.lines_of(q.get("answer")), 1):
            control, _, target = (x.strip() for x in ln.partition("="))
            states = positions(control, target, b)
            if not states:
                probs.append("%s: the positions of \"%s\" are not known - give them in the build sheet: \"states\": {\"%s\": [\"%s\", ...]}"
                             % (where, control, control, target))
                continue
            start = ((b.get("start") or {}).get(control) or "").strip()
            sym = kit_symbol(sid, n_, states, start)
            figs["_kit"] = figs.get("_kit") or bool(sym)
            out.append('      <div class="ctl cg%s" data-val="%s"><p class="cname" data-script-field="answer">%s</p>%s'
                       % ("" if start else " unset", a(control), e(control), sym))
            out.append('        <div class="opts">%s</div></div>' % "".join(
                '<button type="button" class="opt seg%s" data-state%s data-script-field="answer" data-key="%s">%s</button>'
                % (" sel" if start and s.lower() == start.lower() else "",
                   ' data-kv="%g"' % KIT_STATE[s.lower()][1] if sym else "",
                   cs.gb_key(sid, s, control if s.lower() == target.lower() else "-"), e(s)) for s in states))
        out.append("    </div>")
    out.append(q_why(q))
    out.append("  </section>")
    out[0] = out[0] % extra
    return "\n".join(out)


# ------------------------------------------------------------------ the page
def try_screen(w):
    return "\n".join([
        '  <!-- first screen of the course\'s first task: try the tablet (not scored, never repeated) -->',
        '  <section class="scr" id="tryScr">',
        '    <h1 class="q"><span class="stem">%s</span></h1>' % e(w["try_title"]),
        '    <div class="try">',
        '      <div class="try-step" id="try1">',
        '        <button type="button" class="try-tap" id="tryTap"><span class="vh">%s</span></button>' % e(w["try_tap"]),
        '        <p class="txt"><b>1.</b> %s</p>' % e(w["try_1"]),
        '        <span class="tick">&#10003;</span>',
        "      </div>",
        '      <div class="try-step" id="try2">',
        '        <div class="try-drop">',
        '          <div class="tray" id="tryTray"><button type="button" class="chip" id="tryChip">%s</button></div>' % e(w["try_drag"]),
        '          <span class="try-arrow">&#10140;</span>',
        '          <div class="zone slot" id="tryZone" data-cap="1"></div>',
        "        </div>",
        '        <p class="txt"><b>2.</b> %s</p>' % e(w["try_2"]),
        '        <span class="tick">&#10003;</span>',
        "      </div>",
        "    </div>",
        '    <p class="try-hello" id="tryHello">%s</p>' % e(w["try_hello"]),
        "  </section>"])


def intro_screen(slide, title, n, pass_mark, w):
    need = -(-n * pass_mark // 100)
    lines = cs.lines_of(slide.get("text"))[1:] or [""]
    body = ['    <p>%s</p>' % e(lines[0]),
            '    <p><span class="pass">%s</span></p>' % e(w["pass"].format(**{"pass": pass_mark, "need": need, "total": n}))]
    body += ['    <p>%s</p>' % e(x) for x in lines[1:]]
    return "\n".join(['  <!-- before the first question: what this is and the pass mark -->',
                      '  <section class="scr" id="introScr">',
                      '    <h1 class="q"><span class="stem">%s</span></h1>' % e(title),
                      '    <div class="intro">'] + ["  " + x for x in body] + ["    </div>", "  </section>"])


def result_screen(w):
    return "\n".join([
        '  <!-- result : the trainee\'s own score, for them only -->',
        '  <section class="scr" id="resScr">',
        '    <div class="res">',
        '      <div class="res-top">',
        '        <div class="ring" id="resRing">',
        '          <svg viewBox="0 0 190 190" aria-hidden="true" data-no-zoom><circle class="trk" cx="95" cy="95" r="80"/>'
        '<circle class="arc" id="resArc" cx="95" cy="95" r="80" stroke-dasharray="502.65" stroke-dashoffset="502.65"/></svg>',
        '          <div class="num" id="resNum"></div>',
        "        </div>",
        "        <div>",
        '          <h1>%s</h1>' % e(w["score"]),
        '          <span class="badge" id="resBadge" style="display:none"></span>',
        '          <p id="resLine"></p>',
        '          <p id="resNote">%s</p>' % e(w["score_note"]),
        "        </div>",
        "      </div>",
        '      <ol id="resList"></ol>',
        '      <button type="button" class="sub" id="again">%s</button>' % e(w["again"]),
        "    </div>",
        "  </section>"])


def page_html(script, slide, code, qs, build, mdir, figdir, version, approved, first_set, probs):
    m = cs.mid(script.get("module"))
    lang = (script.get("course_language") or "English")
    w = WORDS["en"]
    short = short_title(slide.get("title"))
    if code == "MC":                                    # "Module check - Module 1" -> "Module 1 check"
        short = w["module_n_check"].format(n=script.get("module"))
    is_check = code in cm.CHECK_PAGES
    pass_mark = int(build.get("pass_mark") or DEFAULT_PASS) if is_check else 0
    sheet = build.get("screens") or {}
    try_tablet = (sheet.get(slide["id"]) or {}).get("try_tablet")
    if try_tablet is None:
        try_tablet = first_set and not is_check
    # a drawing labelled on this page gets its label bands on every question of the page - it is in the page once
    figs, sections = {"_bands": {((sheet.get(q["id"]) or {}).get("figure") or "").strip() for q in qs
                                 if cs.mech(q) == "label_diagram"}}, []
    for n, q in enumerate(qs, 1):
        sections.append(("  <!-- %s : %s -->\n" % (q["id"], cs.mech(q))) + question_html(n, q, sheet.get(q["id"]) or {}, mdir, figdir, figs, probs, w))
    pictures = any(not k.startswith("_") for k in figs) or figs.get("_pic") or any(cs.mech(q) == "read_instrument" for q in qs)
    kit = figs.get("_kit")
    if kit:                                             # the panel's controls are drawn by the figure kit, shipped like the engine
        for x in cm.KIT_FILES:
            canon, mine = os.path.join(cm.SKILLS, "course-visuals", "kit", x), os.path.join(mdir, "assets", x)
            if not os.path.isfile(mine) or io.open(mine, "rb").read() != io.open(canon, "rb").read():
                probs.append("the module's copy of %s is not the factory's current one - run course-module-ui\\scripts\\"
                             "design_system.py install --update on the module folder" % x)
    stamp = ("GENERATED by course-factory %s compile_module.py from working_claude/script/%s.json (%s) and %s.build.json.\n"
             "     Do not edit this file: change the script (content_script.py propose) or the build sheet, and compile again."
             % (version, m, ("approved " + script.get("approved_hash", "")) if approved else "DRAFT - NOT APPROVED", m))
    head = ["<!DOCTYPE html>", '<html lang="%s">' % a(lang[:2].lower()), "<head>", "<!-- %s -->" % stamp,
            '<meta charset="utf-8">', '<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">',
            "<title>%s — %s</title>" % (e(code), e(short))]
    team = slide.get("team") or {}
    if team:                                            # classroom-system.json team_task: marked on the slide AND the page
        head += ['<meta name="task-mode" content="team">',
                 '<meta name="task-roles" content="%s">' % a("|".join(cs.team_roles(team))),
                 '<meta name="task-scope" content="%s">' % a(team.get("scope") if team.get("scope") in cs.TEAM_SCOPES else "team")]
    head += ['<link rel="stylesheet" href="../assets/%s">' % x for x in PAGE_CSS + (("gb_zoom.css",) if pictures else ()) + (("kit.css",) if kit else ())]
    head.append("</head>")
    first = try_screen(w) if try_tablet else intro_screen(slide, short, len(qs), pass_mark, w) if is_check else ""
    body = ['<body data-code="%s" data-title="%s" data-pass="%d">' % (a(code), a(short), pass_mark),
            '<a class="gbt-topback" href="#"><span class="gbt-ico">&#9664;</span> %s</a>' % e(w["back"]), ""]
    if team:                                            # filled by the engine from the classroom's gb-team
        body += ['<div class="teambar" id="teamBar" hidden><span class="tname" id="teamName"></span><span class="trole" id="teamRole">'
                 '</span><span class="tnote" id="teamNote"></span><span class="tdone" id="teamDone"></span></div>', ""]
    body += ['<header class="state">',
            '  <span class="part" id="partLbl"></span>', '  <span class="got" id="gotLbl"></span>',
            '  <div class="bar"><i id="barFill"></i></div>', "</header>", "", '<main class="wrap">', ""]
    if first:
        body += [first, ""]
    body += ["\n\n".join(sections), "", result_screen(w), "", "</main>", "",
             '<div class="dock" id="dock"><button type="button" class="sub" id="go" disabled>%s</button></div>'
             % e(w["start_check"] if is_check else w["start_self"]), ""]
    if kit:
        body.append('<script src="../assets/kit.js"></script>')
    body += ['<script src="../assets/gb_answer.js"></script>']
    if pictures:
        body.append('<script src="../assets/gb_zoom.js"></script>')
    body += ["</body>", "</html>", ""]
    if lang.lower() not in ("english", "en"):
        probs.append("%s: the task screen's own words (Check, Next, Your score ...) are English - the %s words are not in the factory yet"
                     % (code, lang))
    return "\n".join(head + body)


def page_path(mdir, slide, code):
    """the page the deck's task slide opens - the same name compile_module.py gives data-task-href"""
    href = cm.task_href(code, short_title(slide.get("title")), mdir)
    return os.path.normpath(os.path.join(mdir, "presentation", href))


def compile_tasks(script, build, mdir, figdir, version, approved):
    """{path: page} for every set the engine can build, the problems, and the sets left as they are"""
    probs, pages, left = [], {}, []
    for x in ENGINE:
        canon, mine = os.path.join(cm.SKILLS, "course-task-ux", "assets", x), os.path.join(mdir, "assets", x)
        if not os.path.isfile(mine) or io.open(mine, "rb").read() != io.open(canon, "rb").read():
            probs.append("the module's copy of %s is not the factory's current one - run course-module-ui\\scripts\\"
                         "design_system.py install --update on the module folder" % x)
    first_module = str(script.get("module")) in ("1", "01")
    seen_sc = False
    for slide, code, qs in sets(script):
        not_yet = sorted({cs.mech(q) for q in qs} - BUILT)
        first_set = first_module and not seen_sc and code.startswith("SC")
        seen_sc = seen_sc or code.startswith("SC")
        if not_yet:                                     # only a script the factory would not accept has one
            probs.append("%s: unknown way(s) of answering %s - a script uses those of knowledge/media-and-tasks.json"
                         % (code, ", ".join(str(x) for x in not_yet)))
            continue
        pages[page_path(mdir, slide, code)] = page_html(script, slide, code, qs, build, mdir, figdir, version, approved,
                                                       first_set, probs)
    return pages, probs, left
