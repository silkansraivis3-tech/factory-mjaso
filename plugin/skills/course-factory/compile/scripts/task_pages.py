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

  WHAT A "figure" CAN BE (2.43.0)
    a drawing  "assets/fig/m01_ga.svg"           places found by data-name + class "hit", as above
    a REAL PHOTOGRAPH  "assets/img/pump_room.jpg"   a .jpg / .png / .webp in the module's assets/img with its record in
        assets/img/_photo_meta.json - for tap the place, spot the hazard, read the instrument, label the drawing, a
        picture beside any other question and over a compare column ("figures": {"Plan A": "assets/img/a.jpg"}).
        Its places are boxes in % of the photograph - there is no drawing to find them on:
        "q01": {"figure": "assets/img/pump_room.jpg", "areas": {"Relief valve": [62.5, 31, 12, 18]}}
        A photograph that is not there, has no record, or was made by an image model is reported, never invented.
        It opens full screen only by its corner button (a tap stays the answer); the viewer shows its credit.
    a figure-kit drawing  "m04_chart.kit.json"  the very spec the deck plays, drawn still at its last step
        ("kit_step": 2 or a word of a step's title for another), places = the spec's part ids or the words a part is
        drawn with ("areas": {"Funnel": "ga1"}), "unlabel": "all" | ["P1", "V2"] takes the words off the drawing
        so it does not give the answer away. The engine lays each area on the drawn part itself.
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
import struct

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
# the ways of answering that are not answered ON a picture but may show one above their controls ("figure" in the build sheet)
ABOVE = {"match", "categorise", "order", "cloze", "choose_and_justify", "scenario", "spot_the_error", "build_the_plan", "timeline"}
DEFAULT_PASS = 70
# 2.46.0 (IGF M01-M03): a drawing to tap that is narrower than this (width / height) takes the screen's height with the
# explanation beside it (gb_answer.css data-pic="side"); a list of MANY rows or more to order, build or match has its
# numbered places beside the cards (data-many) - eight rows needed a scroll to reach the cards at 1280 x 800
SIDE_AR, MANY = 1.8, 6


def many(n, how="1"):
    return ' data-many="%s"' % how if n >= MANY else ""


def ga_class(fig):
    """the picture's frame; a figure-kit drawing is a dark screen there too (gb_answer.css .kitfig)"""
    return "ga kitfig" if fig and fig.kind == "kit" else "ga"
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
    "panel_say": "Put every control in the position it must end in."},
    # PROVISIONAL (2.40.0) - written by Claude, to be checked by a native speaker: compile/TRANSLATIONS_REVIEW.md
    "lv": {
    "back": "Atpakaļ", "try_title": "Vispirms izmēģini planšeti", "try_tap": "Pieskaries šeit",
    "try_1": "Pieskaries lielajam zilajam aplim.", "try_drag": "Velc mani",
    "try_2": "Ievelc kartīti rāmī. Vai pieskaries kartītei, tad rāmim.",
    "try_hello": "Labi! Vari sākt paškontroli.",
    "pass": "Ieskaites slieksnis {pass} % – {need} no {total} pareizi",
    "score": "Tavs rezultāts", "score_note": "Rezultāts ir tikai tev. Apskati jautājumus zemāk un pajautā instruktoram par tiem, kas neizdevās.",
    "again": "Sākt no jauna", "start_self": "Sākt paškontroli", "start_check": "Sākt pārbaudi",
    "choose_all": "Izvēlies visas pareizās atbildes.", "module_n_check": "{n}. moduļa pārbaude",
    "gap_n": "{n}. tukšā vieta", "cloze_say": "Pieskaries tukšajai vietai, tad izvēlies vārdus, kas tur der.",
    "your_action": "Ko tu dari", "your_reason": "Kāpēc",
    "step_n": "{n}. solis no {of}",
    "less": "Mazāk", "more": "Vairāk", "decimal": ",",
    "symptoms": "Ko tu pamani", "fault_say": "Pieskaries daļai, lai to pārbaudītu. Tad bojātajai daļai pieskaries “Šī ir kļūme”.",
    "tap_to_check": "Pieskaries, lai pārbaudītu", "is_fault": "Šī ir kļūme",
    "errors_say": "Pieskaries katrai kļūdainajai rindai. Pieskaries vēlreiz, lai atzīmi noņemtu.",
    "plan_say": "Saliec plānā vajadzīgās kartītes pareizā secībā. Ne visas kartītes der – tās atstāj, kur ir.",
    "timeline_order": "1. Sakārto notikumus secībā, kādā tie notika.",
    "timeline_stop": "2. Tagad pieskaries notikumam, kurā tas bija jāaptur.",
    "panel_say": "Iestati katru vadības elementu stāvoklī, kurā tam jābūt beigās."},
    "ru": {
    "back": "Назад", "try_title": "Сначала попробуй планшет", "try_tap": "Коснись здесь",
    "try_1": "Коснись большого синего круга.", "try_drag": "Перетащи меня",
    "try_2": "Перетащи карточку в рамку. Или коснись карточки, затем рамки.",
    "try_hello": "Отлично! Можно начинать самопроверку.",
    "pass": "Проходной балл {pass} % – {need} из {total} правильно",
    "score": "Твой результат", "score_note": "Результат — только для тебя. Посмотри вопросы ниже и спроси инструктора о тех, где была ошибка.",
    "again": "Начать заново", "start_self": "Начать самопроверку", "start_check": "Начать проверку",
    "choose_all": "Выбери все правильные ответы.", "module_n_check": "Проверка по модулю {n}",
    "gap_n": "Пропуск {n}", "cloze_say": "Коснись пропуска, затем выбери подходящие слова.",
    "your_action": "Что ты делаешь", "your_reason": "Почему",
    "step_n": "Шаг {n} из {of}",
    "less": "Меньше", "more": "Больше", "decimal": ",",
    "symptoms": "Что ты замечаешь", "fault_say": "Коснись узла, чтобы проверить его. Затем на неисправном узле нажми «Это неисправность».",
    "tap_to_check": "Коснись, чтобы проверить", "is_fault": "Это неисправность",
    "errors_say": "Коснись каждой строки с ошибкой. Коснись ещё раз, чтобы снять отметку.",
    "plan_say": "Разложи нужные карточки в план по порядку. Не все карточки подходят – их оставь на месте.",
    "timeline_order": "1. Расставь события в том порядке, в котором они произошли.",
    "timeline_stop": "2. Теперь коснись события, на котором его надо было остановить.",
    "panel_say": "Установи каждый орган управления в положение, в котором он должен остаться."}}
assert all(set(WORDS[k]) == set(WORDS["en"]) for k in WORDS), "every language has every word"
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


BAND_PX, BOX_PX, WIDTH_PX = 64.0, 56.0, 1240.0     # a label row above and below the drawing; the box; the drawing's widest
LAB_PX = 400.0                                       # the labelled drawing's height at 1280 x 800: 100vh - 400px (gb_answer.css .ga.lab)


def ppu(vb):
    """px per drawing unit at 1280 x 800 - the drawing is as wide as the screen allows, or as tall as .ga.lab allows"""
    return min(WIDTH_PX / vb[2], LAB_PX / vb[3])


def band_vb(vb):
    """the drawing's view box with a band above and below it for the empty label boxes, so none covers what is drawn"""
    x, y, w, h = vb
    band = BAND_PX * h / (LAB_PX - 2 * BAND_PX)          # when the height decides the size
    if LAB_PX / (h + 2 * band) > WIDTH_PX / w:            # the width decides it
        band = BAND_PX * w / WIDTH_PX
    return (x, y - band, w, h + 2 * band)


def with_bands(body, vb):
    """label the drawing: a band above and below it for the empty label boxes, so no box covers what is drawn"""
    nvb = band_vb(vb)
    body = re.sub(r'(<svg\b[^>]*\bviewBox=")[^"]*(")', lambda m: m.group(1) + "%g %g %g %g" % nvb + m.group(2), body, count=1)
    return body, nvb


# ------------------------------------------------------------------ the picture of a task (2.43.0)
class Fig(object):
    """what a question's "figure" is, however it is made: a drawing (.svg), a REAL PHOTOGRAPH (.jpg .png .webp), or a
    figure-kit drawing (*.kit.json - the very spec the deck plays, drawn still)
      kind   "svg" | "img" | "kit"          name  what makes two questions share it     vb  (x, y, w, h) - the units the
      areas are worked out in (a photograph: its pixels)      svg  the drawing's markup, for finding places on it
      parts  {answer words: part id}, a kit drawing's parts   make(shared, uid) -> the markup as the page carries it"""

    def __init__(self, kind, name, vb, make, svg=None, parts=None, ids=()):
        self.kind, self.name, self.vb, self.make, self.svg, self.parts, self.ids = kind, name, vb, make, svg, parts or {}, set(ids)
        self.spec_parts = []

    def html(self, shared=False, uid=""):
        return self.make(shared, uid or self.name)

    def ar(self):
        """' style="--ar:1.6"' - the shape of the picture, so the frame is as large as the screen allows"""
        return ' style="--ar:%.3f"' % (self.vb[2] / self.vb[3]) if self.vb else ""


def image_size(path):
    """(width, height) of a .png .jpg .webp .gif from its header, no imaging library - None when it cannot be read"""
    try:
        f = io.open(path, "rb")
    except OSError:
        return None
    with f:
        head = f.read(32)
        if head[:8] == b"\x89PNG\r\n\x1a\n":
            return struct.unpack(">II", head[16:24])
        if head[:6] in (b"GIF87a", b"GIF89a"):
            return struct.unpack("<HH", head[6:10])
        if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
            kind = head[12:16]
            if kind == b"VP8X":
                return 1 + int.from_bytes(head[24:27], "little"), 1 + int.from_bytes(head[27:30], "little")
            if kind == b"VP8L":
                bits = int.from_bytes(head[21:25], "little")
                return (bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1
            if kind == b"VP8 ":
                w, h = struct.unpack("<HH", head[26:30])
                return w & 0x3FFF, h & 0x3FFF
            return None
        if head[:2] == b"\xff\xd8":                       # walk the segments to the frame header
            f.seek(2)
            while True:
                b = f.read(1)
                if not b:
                    return None
                if b != b"\xff":
                    continue
                m = f.read(1)
                while m == b"\xff":
                    m = f.read(1)
                if not m:
                    return None
                if m in (b"\xd8", b"\x01") or b"\xd0" <= m <= b"\xd7":
                    continue
                n = f.read(2)
                if len(n) < 2:
                    return None
                if b"\xc0" <= m <= b"\xcf" and m not in (b"\xc4", b"\xc8", b"\xcc"):
                    d = f.read(5)
                    return (struct.unpack(">HH", d[1:5])[1], struct.unpack(">HH", d[1:5])[0]) if len(d) == 5 else None
                f.seek(struct.unpack(">H", n)[0] - 2, 1)
    return None


def photo_fig(q, b, rel, mdir, probs, where, bands=False, wrap=False):
    """a REAL photograph of real equipment as the picture of a task: the file is in the module (read_figure reported it
    when it is not), its record is assets\\img\\_photo_meta.json - a missing record is reported, never invented. Its
    credit goes into the full-screen viewer (gb_zoom); what it shows (the record's "description") does not - on a task
    it could give the answer away. A picture made by an image model is refused for what a trainee must recognise."""
    meta = cm.photo_meta(mdir, rel)
    if not meta:
        probs.append("%s: the photograph %s has no record in %s - add its source, licence and what it shows; a photograph is "
                     "never shown on a task without its record" % (where, rel, os.path.join(os.path.dirname(rel), "_photo_meta.json").replace("/", "\\")))
    elif cm.is_generated(meta):
        probs.append("%s: %s was made by an image model - a task that asks the trainee to recognise, find or read real equipment "
                     "shows a real photograph of it (take one at Novikontas, or find a free-licensed one)" % (where, rel))
    credit = b.get("credit") or cm.credit_line(meta)
    if meta and meta.get("attribution_required") and not credit:
        probs.append("%s: the photograph %s needs a credit line, and _photo_meta.json does not give one" % (where, rel))
    size = image_size(os.path.join(mdir, rel))
    if not size:
        probs.append("%s: the size of the photograph %s cannot be read (is it a .jpg, .png or .webp?) - the places on it cannot be worked out" % (where, rel))
        size = (4, 3)
    name = cm.slug(rel)
    alt = b.get("alt") or q.get("visual") or ""
    cred = ' data-credit="%s"' % a(credit) if credit else ""
    if wrap:                                           # labels need a band round the picture: the photo inside a drawing
        w, h = 1000.0, round(1000.0 * size[1] / size[0], 2)
        body = ('<svg viewBox="0 0 %g %g" role="img" aria-label="%s" data-audit-ignore%s><image href="../%s" x="0" y="0" width="%g" height="%g" '
                'preserveAspectRatio="none"/></svg>' % (w, h, a(alt), cred, a(rel), w, h))
        return svg_fig(body, name, (0.0, 0.0, w, h), where, rel, probs, bands)
    return Fig("img", name, (0.0, 0.0, float(size[0]), float(size[1])),
               lambda shared, uid: '<img class="taskfig" src="../%s" alt="%s"%s%s>' % (
                   a(rel), a(alt), ' data-fig="%s"' % a(name) if shared else "", cred))


def svg_fig(body, name, vb, where, rel, probs, bands):
    if not vb:
        probs.append("%s: the drawing %s has no viewBox - the places on it cannot be worked out" % (where, rel))
    elif bands:
        body, vb = with_bands(body, vb)
    return Fig("svg", name, vb, lambda shared, uid: re.sub(r"<svg\b", '<svg class="taskfig"' + (' data-fig="%s"' % a(name) if shared else ""),
                                                          body, count=1), svg=body)


# a kit part's words on the drawing - what "unlabel" takes off, so the drawing does not give the answer away
KIT_WORDS = ("label", "caption", "title", "tag", "labels", "cofferdamLabel", "hullLabel", "liquidLabel", "vapourLabel", "heatLabel")


def kit_box(p):
    """a kit part's rough box in the drawing's units - only where the engine places the tappable area before the drawn
    part is measured (gb_answer.js placeParts replaces it with the part's own box)"""
    x, y = p.get("x") or 0, p.get("y") or 0
    try:
        if p.get("w") and p.get("h"):
            return (x, y, float(p["w"]), float(p["h"]))
        r = p.get("r") or p.get("size")
        return (x - float(r), y - float(r), 2.0 * float(r), 2.0 * float(r)) if r else None
    except (TypeError, ValueError):
        return None


def kit_fig(q, b, text, rel, probs, where, bands):
    """a figure-kit drawing in a task: the same *.kit.json the deck plays (course-visuals/kit/SPEC.md), drawn STILL at
    the end of its last step - or of the step the build sheet names ("kit_step": 2, or a word of a step's title). The
    parts the answers are about are found by their ids; "unlabel": "all" or ["P1", "V2"] takes the words off the parts,
    so the drawing does not give the answer away. One spec, so a chart is drawn once and can never drift."""
    try:
        spec = json.loads(text)
    except ValueError as err:
        probs.append("%s: its kit figure %s is not valid JSON - %s" % (where, rel, err))
        return None
    parts = spec.get("parts") if isinstance(spec, dict) else None
    if not parts:
        probs.append("%s: its kit figure %s has no parts" % (where, rel))
        return None
    ids = [p.get("id") for p in parts if p.get("id")]
    names = {}                                          # the words of a part (before "unlabel") -> its id
    for p in parts:
        for k in ("id", "label", "tag", "title"):
            if p.get("id") and isinstance(p.get(k), str):
                names.setdefault(re.sub(r"\s+", " ", p[k]).strip().lower(), p["id"])
    hide = b.get("unlabel")
    if hide not in (None, False, "all") and not isinstance(hide, list):
        probs.append("%s: \"unlabel\" is \"all\" or a list of part ids" % where)
        hide = None
    if isinstance(hide, list):
        for x in hide:
            if x not in ids:
                probs.append("%s: \"unlabel\" names %s, which is not a part of %s (parts: %s)" % (where, x, rel, ", ".join(ids)))
    if hide:
        keep = []
        for p in parts:
            mine = hide == "all" or p.get("id") in hide
            if mine and p.get("type") == "text":        # a bare caption is nothing but words: it goes
                continue
            keep.append(dict((k, v) for k, v in p.items() if k not in KIT_WORDS) if mine else p)
        spec = dict(spec, parts=keep)
    steps = spec.get("steps") or []
    want = b.get("kit_step", "final")
    n = len(steps)
    if isinstance(want, int) and not isinstance(want, bool):
        n = want
    elif isinstance(want, str) and want.strip() and want != "final":
        hit = [i for i, s in enumerate(steps, 1) if want.strip().lower() in str(s.get("title") or "").lower()]
        if not hit:
            probs.append("%s: \"kit_step\" %r is no step of %s - its steps: %s" % (where, want, rel, "; ".join(str(s.get("title")) for s in steps) or "none"))
        else:
            n = hit[0]
    if not 0 <= n <= len(steps):
        probs.append("%s: \"kit_step\" %s is outside the %d step(s) of %s" % (where, n, len(steps), rel))
        n = len(steps)
    try:
        size = [float(x) for x in spec.get("size") or (600, 440)]
        vb = (0.0, 0.0, size[0], size[1])
    except (TypeError, ValueError):
        probs.append("%s: the kit figure %s has no usable \"size\"" % (where, rel))
        return None
    if bands:
        vb = band_vb(vb)
        spec = dict(spec, view=[round(v, 3) for v in vb])
    if not spec.get("label"):
        spec["label"] = cm.first_sentence(q.get("visual")) or ""
    key = json.dumps([n, hide, bool(bands)], sort_keys=True)
    name = cm.slug(rel) + ("" if key == json.dumps([len(steps), None, False]) else "-" + cm.sha(key)[:6])
    data = json.dumps(spec, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")

    def make(shared, uid):
        sid = "kit-task-" + uid
        return ('<svg class="taskfig" data-kit="#%s" data-kit-step="%d"%s></svg><script type="application/json" id="%s">%s</script>'
                % (sid, n, ' data-fig="%s"' % a(name) if shared else "", sid, data))
    fig = Fig("kit", name, vb, make, parts=names, ids=ids)
    fig.spec_parts = parts
    return fig


def figure_for(q, b, mdir, figdir, probs, where, bands=False, wrap=False):
    """a Fig: a drawing, a real photograph or a figure-kit drawing - or None, with the reason in probs"""
    rel = (b.get("figure") or "").strip().replace("\\", "/")
    if not rel:
        probs.append("%s: '%s' is answered on a picture - put its drawing or photograph in the build sheet (\"figure\")" % (where, q.get("mechanic")))
        return None
    body, err = cm.read_figure(mdir, rel, figdir)
    if err:
        probs.append("%s: its %s %s %s" % (where, "photograph" if rel.lower().endswith(cm.IMAGES) else "drawing", rel, err))
        return None
    if rel.lower().endswith(cm.KIT_SPEC):
        return kit_fig(q, b, body, rel, probs, where, bands)
    if body is None:                                   # a photograph: shipped in the module folder
        return photo_fig(q, b, rel, mdir, probs, where, bands, wrap)
    return svg_fig(body, cm.slug(rel), viewbox(body), where, rel, probs, bands)


def area(fig, name, b, where, probs):
    """([left, top, width, height] in %, the answer's id) for one answer on the picture"""
    given = (b.get("areas") or {}).get(name)
    if isinstance(given, list) and len(given) == 4:
        return given, (b.get("ids") or {}).get(name) or cm.slug(name)
    if fig.kind == "kit":                              # a part of the spec: by id, or by the words it is drawn with
        pid = given if isinstance(given, str) else fig.parts.get(re.sub(r"\s+", " ", name).strip().lower())
        if pid not in fig.ids:
            probs.append("%s: \"%s\" is not a part of the kit figure - name its part id in the build sheet: \"areas\": {\"%s\": \"<part id>\"} "
                         "(parts: %s)" % (where, name, name, ", ".join(sorted(fig.ids))))
            return None, pid or cm.slug(name)
        part = next((p for p in (fig.spec_parts or []) if p.get("id") == pid), None)
        box = kit_box(part) if part else None
        return (pct_box(box, fig.vb) if box else [40.0, 40.0, 20.0, 20.0]), pid
    if fig.kind == "img":
        probs.append("%s: \"%s\" has no place on the photograph - give its box in %% of the photograph in the build sheet: "
                     "\"areas\": {\"%s\": [left, top, width, height]}" % (where, name, name))
        return None, cm.slug(name)
    svg = fig.svg or ""
    eid = given if isinstance(given, str) else named(svg, name)
    el = element(svg, eid) if eid else None
    box = shape_box(el) if el else None
    if not (box and fig.vb):
        probs.append("%s: \"%s\" is not on the drawing - give the drawing an element with data-name=\"%s\" and a "
                     "shape of class \"hit\" in it, or its box in the build sheet: \"areas\": {\"%s\": [left, top, width, height]}"
                     % (where, name, name, name))
        return None, eid or cm.slug(name)
    return pct_box(box, fig.vb), eid


# ------------------------------------------------------------------ one question
def q_head(n, q):
    return ('    <h1 class="q"><span class="num">%d</span><span class="stem" data-script-field="question">%s</span></h1>'
            % (n, e(q.get("question"))))


def q_why(q):
    return ('    <div class="why"><b class="vd"></b><p data-script-field="feedback">%s</p></div>' % e(q.get("feedback")))


def opt_buttons(sid, q, multi=False, cls="opts"):
    opts, right = q.get("options", []), cs.correct_letters(q)
    out = ['    <div class="%s%s">' % (cls, " multi" if multi else "")]
    # out of the script's order, like every other answer: a script writes the right one first (IGF M05: A was right in
    # every choose-one question, so always tapping the first option passed) - the same order on every build
    for L, o in shuffle(sid, list(zip(cs.letters(len(opts)), opts)), key=lambda x: x[1]):
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
    fig = figure_for(q, b, mdir, figdir, probs, where)
    if not fig:
        return []
    figs["_pic"] = True
    figs["_kit"] = figs.get("_kit") or fig.kind == "kit"
    return ['    <div class="instrument"><div class="ga"%s>%s</div></div>' % (fig.ar(), fig.html(False, q["id"]))]


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


# 2.46.0 - a label box is as wide as its words need. The 17 % box cut off "Tank connection space" once the tick
# appeared, and IGF M01 and M03 placed their boxes by hand. A card can be dropped in any box, so every box of a drawing
# is as wide as its longest label needs, in at most two lines of 16 px (gb_answer.css .lbox .chip).
NARROW, WIDE = set("ijlt.,:;'!|()[]f ·-"), set("mwMW@%")
CORNER_PX = 60.0                                     # the ⤢ button: 48 px, 8 px from the drawing's top right (gb_zoom.css)


def text_px(s, size=16.0):
    """the width of words at 16 px semibold - measured for Raleway, the widest of the course fonts (Segoe UI, Roboto are
    narrower), so a box sized by it is never too small"""
    w = 0.0
    for ch in s:
        w += (0.30 if ch in NARROW else 0.86 if ch in WIDE else 0.70 if ch.isupper() else 0.62 if ch.isdigit() else 0.57) * size
    return w


def label_px(t):
    """px a label's box needs: the words in one or two lines, the box's and the card's borders and padding, and the
    tick (or the arrow of a card moved to its place) the engine adds after Check"""
    words = t.split()
    lines = [text_px(t)] + [max(text_px(" ".join(words[:k])), text_px(" ".join(words[k:]))) for k in range(1, len(words))]
    return min(lines) * 1.06 + 46.0


def label_boxes(places, vb, probs=None, where=""):
    """where the empty label boxes go when the build sheet does not say: in the band above the drawing for what is in
    its upper half, in the band below for the rest, in order across - the same order as what they point at. Every box
    is as wide as the longest label needs (label_px); label_layout.py places them (2.48.0): each as near its place as
    the others allow, the order kept, never off the edge, onto another or under the ⤢; a row that cannot hold its boxes
    passes the one nearest the middle to the other row, and what still does not fit is reported, never cut off"""
    import label_layout
    if not places:
        return places
    wp = vb[2] * ppu(vb)                                   # the drawing's width in px at 1280 x 800
    w = min(max(max(label_px(p["t"]) for p in places), BOX_PX * 2) * 100.0 / wp, 96.0)
    corner = CORNER_PX * 100.0 / wp                        # the top row keeps clear of the ⤢ button (gb_zoom, top right)
    if not label_layout.label_boxes(places, vb, ppu(vb), w, BAND_PX, BOX_PX, corner) and probs is not None:
        probs.append("%s: %d label boxes as wide as their words need (%.0f %% of the drawing) do not fit in its two label rows - "
                     "shorten the longest labels in the script, or place the boxes in the build sheet (\"labels\": {\"...\": "
                     "{\"box\": [left, top, width]}})" % (where, len(places), w))
    return places


def label_width_problems(places, vb, where):
    """a box placed by hand in the build sheet that is narrower than the longest label needs - a card would be cut off.
    label_px is measured for the widest font, so a hand box within 5 % of it still fits (IGF M01-M03, measured)"""
    if not vb:
        return []
    need = max(label_px(p["t"]) for p in places) * 100.0 / (vb[2] * ppu(vb))
    return ["%s: the label box of \"%s\" in the build sheet is %.1f %% wide - the longest label needs %.1f %%; leave \"box\" out "
            "and the compiler places and sizes it" % (where, p["t"], p["at"][2], need)
            for p in places if p.get("hand") and p["at"][2] < 0.95 * need]


def question_html(n, q, b, mdir, figdir, figs, probs, w=None):
    w = w or WORDS["en"]
    sid, m = q["id"], cs.mech(q)
    where = "%s (%s)" % (q.get("set") or "", sid)
    out = ['  <section class="scr" data-script="%s" data-mech="%s"%s>' % (sid, m, "%s"), q_head(n, q)]
    extra = ""
    if m in ABOVE:                                      # a picture above the question's own controls, when the build sheet names one
        out += picture(q, b, mdir, figdir, figs, probs, where)
    if m in ("single_choice", "multi_select"):
        if m == "multi_select":
            out.append('    <p class="opts-say">%s</p>' % e(w["choose_all"]))
            extra = ' data-multi="1"'          # gb_answer.js keeps every tapped option only on data-multi="1"
        pic = picture(q, b, mdir, figdir, figs, probs, where)    # "what is this?" - a real photograph beside the choices
        if pic:
            out += pic
            extra += ' data-pic="beside"'
        out += opt_buttons(sid, q, multi=m == "multi_select")
    elif m == "read_instrument":
        fig = figure_for(q, b, mdir, figdir, probs, where, (b.get("figure") or "").strip() in figs["_bands"])
        if fig:
            figs["_pic"] = True
            figs["_kit"] = figs.get("_kit") or fig.kind == "kit"
            out.append('    <div class="instrument"><div class="ga"%s>%s</div></div>' % (fig.ar(), fig.html(False, sid)))
            extra = ' data-pic="beside"'       # the picture beside the choices, never over four stacked ones (gb_answer.css)
        out += opt_buttons(sid, q)
    elif m in ("hotspot", "spot_the_hazard"):
        items, right = cs.answer_items(q)
        fig = figure_for(q, b, mdir, figdir, probs, where, (b.get("figure") or "").strip() in figs["_bands"])
        if len(right) > 1:
            extra = ' data-multi="1"'
        holder = []
        if fig and (fig.kind == "img" or fig.name not in figs):         # a drawing is in the page once; a photo is cached
            figs[fig.name] = True
            holder.append(fig.html(True))
        if fig:
            figs["_kit"] = figs.get("_kit") or fig.kind == "kit"
            if fig.vb and fig.vb[2] / fig.vb[3] < SIDE_AR:      # not a wide drawing: the screen's height, the explanation beside it
                extra += ' data-pic="side"'
        for t in items:
            box, pid = area(fig, t, b, where, probs) if fig else (None, None)
            if box is None:
                continue
            holder.append('      <button type="button" class="hot" style="left:%s%%;top:%s%%;width:%s%%;height:%s%%"%s '
                          'data-script-field="answer" data-key="%s"><span class="vh">%s</span></button>'
                          % (box[0], box[1], box[2], box[3], ' data-part="%s"' % a(pid) if fig.kind == "kit" else "",
                             cs.gb_key(sid, t, 1 if t in right else 0), e(t)))
        out.append('    <div class="stage"><div class="%s" data-fig="%s" data-zoom="button"%s>'
                   % (ga_class(fig), a(fig.name if fig else ""), fig.ar() if fig else ""))
        out += holder
        out.append("    </div></div>")
    elif m == "label_diagram":
        items, _ = cs.answer_items(q)
        fig = figure_for(q, b, mdir, figdir, probs, where, (b.get("figure") or "").strip() in figs["_bands"], wrap=True)
        vb = fig.vb if fig else None
        places = []
        for t in items:
            given = (b.get("labels") or {}).get(t) or {}
            box, eid = area(fig, t, dict(b, areas={t: given["at"]} if given.get("at") else b.get("areas") or {}),
                            where, probs) if fig else (None, None)
            if box is None:
                continue
            places.append({"t": t, "id": eid, "box": box, "at": given.get("box"), "hand": bool(given.get("box"))})
        auto = [p for p in places if not p["at"]]
        if auto and vb:
            label_boxes(auto, vb, probs, where)
        probs += label_width_problems(places, vb, where)
        out.append('    <div class="stage"><div class="%s lab" data-fig="%s" data-zoom="button"%s>'
                   % (ga_class(fig), a(fig.name if fig else ""), fig.ar() if fig else ""))
        if fig and fig.name not in figs:
            figs[fig.name] = True
            out.append(fig.html(True))
        if fig:
            figs["_kit"] = figs.get("_kit") or fig.kind == "kit"
        if places:
            out.append('      <svg class="leaders" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true" data-audit-ignore data-no-zoom>')
            for p in places:
                bx, by, bw = p["at"]
                bh = 100.0 * BOX_PX / (vb[3] * ppu(vb)) if vb else 0.0
                x1, y1 = bx + bw / 2, by + (bh if by < 50 else 0)
                x2, y2 = p["box"][0] + p["box"][2] / 2, p["box"][1] + p["box"][3] / 2
                out.append('        <line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" vector-effect="non-scaling-stroke"%s/>'
                           % (x1, y1, x2, y2, ' data-part="%s"' % a(p["id"]) if fig.kind == "kit" else ""))
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
        extra = many(len(pairs))
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
        extra = many(len(items))
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
        pic = picture(q, b, mdir, figdir, figs, probs, where)
        if pic:                                         # the picture beside the symptoms, so the cards fit the screen
            out.append('    <div class="ffhead">')
            out += ["  " + x for x in pic]
        out.append('    <div class="sym"><p class="phead">%s</p>' % e(w["symptoms"]))
        out += ['      <p data-script-field="answer">%s</p>' % e(x.strip().lstrip("!").strip()) for x in ls if x.lstrip().startswith("!")]
        out.append("    </div>")
        if pic:
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
        extra = ' data-need="slots"' + many(max(len(good), MANY if len(ls) >= 9 else 0))
        out.append('    <p class="opts-say">%s</p>' % e(w["plan_say"]))
        out += slots(len(good))
        out.append('    <div class="tray">')
        out += chips(sid, [(cs.unstar(x), 1 if cs.starred(x) else 0) for x in ls], {t: i for i, t in enumerate(good, 1)})
        out.append("    </div>")
    elif m == "timeline":                               # part 1 the order, part 2 the moment it should have stopped
        ls = cs.lines_of(q.get("answer"))
        extra = many(len(ls), "part")
        out.append('    <div class="part%s">' % (" lay" if extra else ""))
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
        shown = b.get("figures") or {}                  # "figures": {"Plan A": "assets/img/plan_a.jpg"} - a picture over its column

        def head_fig(L, o):
            rel = shown.get(L) or shown.get(o)
            if not rel:
                return ""
            fig = figure_for(q, dict(b, figure=rel), mdir, figdir, probs, where)
            if not fig:
                return ""
            figs["_pic"] = True
            figs["_kit"] = figs.get("_kit") or fig.kind == "kit"
            return '<div class="cmpfig"><div class="ga"%s>%s</div></div>' % (fig.ar(), fig.html(False, "%s-%s" % (sid, L)))
        out.append('    <table class="cmp cg">')
        out.append('      <thead><tr><th class="what"></th>%s</tr></thead>' % "".join(
            '<th>%s<button type="button" class="opt" id="%s-%s" data-script-field="opt.%s" data-key="%s">%s</button></th>'
            % (head_fig(L, o), a(sid), L, L, cs.gb_key(sid, o, 1 if L in right else 0), e(o)) for L, o in zip(cs.letters(len(opts)), opts)))
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


def pass_mark_of(script, build, probs=None):
    """the check's pass mark in %: the approved script's "pass_mark" (2.46.0 - the operator corrects it like any
    other word of the script: content_script.py propose {"script_field": "pass_mark"}), else the build sheet's, else 70"""
    s, b = script.get("pass_mark"), build.get("pass_mark")
    if s and b and int(s) != int(b) and probs is not None and not any("pass mark" in x and "build sheet" in x for x in probs):
        probs.append("the script's pass mark is %s %%, the build sheet still says %s %% - the script's is used; take "
                     "\"pass_mark\" out of the build sheet" % (s, b))
    return int(s or b or DEFAULT_PASS)


def page_html(script, slide, code, qs, build, mdir, figdir, version, approved, first_set, probs):
    m = cs.mid(script.get("module"))
    lang = (script.get("course_language") or "English")
    code_l = cm.lang_code(lang)                         # L19: the whole page in the course language
    w = WORDS.get(code_l) or WORDS["en"]
    short = short_title(slide.get("title"))
    if code == "MC":                                    # "Module check - Module 1" -> "Module 1 check"
        short = w["module_n_check"].format(n=script.get("module"))
    is_check = code in cm.CHECK_PAGES
    pass_mark = pass_mark_of(script, build, probs) if is_check else 0
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
    head = ["<!DOCTYPE html>", '<html lang="%s">' % a(code_l or lang[:2].lower()), "<head>", "<!-- %s -->" % stamp,
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
        if os.path.isfile(os.path.join(mdir, cm.KIT_PARTS)):   # the course's own parts, as the deck loads them
            body.append('<script src="../%s"></script>' % cm.KIT_PARTS)
    body += ['<script src="../assets/gb_answer.js"></script>']
    if pictures:
        body.append('<script src="../assets/gb_zoom.js"></script>')
    body += ["</body>", "</html>", ""]
    if code_l not in WORDS:                             # reported, never a silent fall-back
        probs.append("%s: the course is in %s - the task screen's own words (Check, Next, Your score ...) are not in the factory in "
                     "that language, so they were written in English (task_pages.py WORDS, gb_answer.js)" % (code, lang))
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
    import answer_key                                   # 2.46.0 - the instructor's key, from the same approved script
    key = answer_key.key_page(script, build, mdir, version, approved, probs)
    if key:
        pages[key[0]] = key[1]
    return pages, probs, left
