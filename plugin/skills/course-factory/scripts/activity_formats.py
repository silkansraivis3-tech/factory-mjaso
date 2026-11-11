#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Varied practical-activity formats, chosen while a module is written (L68, 2.128.0).

WHY THIS EXISTS (Aigars Kluga, course expert, 2026-11-11)
"The factory is good but cannot vary - fine for one-direction courses like Gas, but narrow." The guideline's TLA pool
(knowledge/instructor-led.json "tla_pool") was only checked after the course was written, so every practical of the
Project Management course came out as one format - solo or pair project work - until the guideline file was filled by
hand. This module is the part of the guideline the factory uses WHILE it writes:

  * task_type_of   a Sub-ILO's dominant task type (R2): the register's, else read from its verb (formats "verbs")
  * pick           one or two TLAs for it from the pool, near its Bloom level, varied across the module
  * format_of      what format a written screen is: an activity's "format" (or its sign words), an active slide's technique
  * moments        the module's practice moments - its activity screens and active slides - with their formats
  * practical      a practical for instructor_led.json: cycle rows that add up to the screen's minutes, the cards' fields

The catalogue (how each TLA is written in a script, its roles, what the debrief must observe) is knowledge/instructor-led.json
"formats" - edit it there, not here. Used by instructor_led.py (plan, draft) and content_script.py (a_one_direction,
a_type_unserved). Standard library only.
"""
from __future__ import annotations

import io
import json
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import bloom_map  # noqa: E402

KNOW = json.load(io.open(os.path.join(SKILL, "knowledge", "instructor-led.json"), encoding="utf-8"))
F = KNOW["formats"]
TASK_TYPES = [k for k in KNOW["task_types"] if not k.startswith("_")]
LEVEL = {"Remember": 1, "Understand": 2, "Apply": 3, "Analyse": 4, "Evaluate": 5, "Create": 6}
_POOL = {t["tla"]: dict(t, task_type=tt) for tt, v in KNOW["tla_pool"].items() if not tt.startswith("_") for t in v}
FORMATS = {}
for _k, _f in F["pool"].items():
    _t = _POOL[_f["tla"]]                       # a format names a TLA of the pool exactly (test_activity_formats pins it)
    FORMATS[_k] = dict(_f, key=_k, task_type=_t["task_type"], level=LEVEL[_t["bloom"]], label=_t["tla"], min=_t["min"])
UNNAMED = dict(F["unnamed"], drafts="activity", level=3, min="", features=[])
ORDER = list(FORMATS)
D = F["defaults"]


def get(key):
    return FORMATS.get(key) or (UNNAMED if key == UNNAMED["key"] else None)


def label(key):
    f = get(key)
    return f["label"] if f else str(key)


# ------------------------------------------------------------------ the task type, from the register or the verb
def _verb_rx(v):
    return re.compile(r"(?<![\w])" + re.escape(v).replace(r"\ ", r"\s+") + r"(?:s|es|ed|d|ing)?(?![\w])", re.I)


_VERBS = [(tt, v, _verb_rx(v)) for tt in TASK_TYPES for v in F["verbs"].get(tt) or []]


def verb_type(text):
    """(task type, the verb that decided it) - the EARLIEST verb of formats "verbs" in the text; a decision when none"""
    best = None
    for tt, v, rx in _VERBS:
        m = rx.search(text or "")
        if m and (best is None or m.start() < best[0] or (m.start() == best[0] and len(m.group(0)) > len(best[2]))):
            best = (m.start(), tt, m.group(0))
    return (best[1], best[2].lower()) if best else ("decision", None)


def task_type_of(sid, text, register=None):
    """(task type, where it came from: "register" | "verb 'x'" | "no verb read - decision")"""
    r = (register or {}).get(str(sid)) or {}
    if r.get("task_type") in TASK_TYPES:
        return r["task_type"], "register"
    tt, verb = verb_type(text)
    return tt, ("verb %r" % verb) if verb else "no verb read - decision"


def level_of(text, lang="en"):
    lv = bloom_map.ilo_level(text or "", lang) if text else None
    return (lv or {}).get("level") or 3


# ------------------------------------------------------------------ picking TLAs
def _allowed(f, text, experienced):
    only = f.get("only")
    if only == "experienced":
        return experienced
    if isinstance(only, list):
        return any(_verb_rx(v).search(text or "") for v in only)
    return True


def pick(task_type, level=3, text="", used=None, experienced=False, n=2):
    """[format keys] - one or two TLAs of the task type for a Sub-ILO: the nearest Bloom level, the least used in the module
    so far (the score is the distance plus the uses), the second of another kind (an activity beside a slide or a tablet task)
    where there is one; the task type's core format (formats "core") counts one closer and wins a tie. A TLA the outcome's own verb asks for ("only": prepare, plan, draft, write) comes first. A team
    format brings its features (observers, a trainee-led debrief). `used` is updated - pass one Counter for the module."""
    used = used if used is not None else {}
    cands = [k for k in ORDER if FORMATS[k]["task_type"] == task_type and FORMATS[k]["drafts"] != "feature"
             and _allowed(FORMATS[k], text, experienced)]
    core = F["core"].get(task_type)
    score = lambda k: (abs(FORMATS[k]["level"] - level) + used.get(k, 0) - (k == core), k != core, ORDER.index(k))
    forced = [k for k in cands if isinstance(FORMATS[k].get("only"), list)]
    ranked = forced + sorted([k for k in cands if k not in forced], key=score)
    out = ranked[:1]
    if n > 1 and ranked:
        rest = [k for k in ranked[1:]]
        other = [k for k in rest if FORMATS[k]["drafts"] != FORMATS[out[0]]["drafts"]]
        out += (sorted(other, key=score) or rest)[:1] if (other or rest) else []
    for k in out:
        used[k] = used.get(k, 0) + 1
    feats = [x for k in out for x in FORMATS[k].get("features") or [] if x in FORMATS]
    return out + [x for i, x in enumerate(feats) if x not in out and x not in feats[:i]]


def plan(rows, register=None, lang="en", experienced=False):
    """[{sid, text, task_type, source, level, picks}] - a module's Sub-ILOs (ILO map rows), each with its formats, varied
    across the module"""
    used, out = {}, []
    for r in rows:
        sid, text = str(r.get("sub_ilo_id")), r.get("sub_ilo_en") or r.get("sub_ilo") or ""
        tt, src = task_type_of(sid, text, register)
        lv = level_of(text, lang)
        out.append({"sid": sid, "text": text, "task_type": tt, "source": src, "level": lv,
                    "picks": pick(tt, lv, text, used, experienced)})
    return out


# ------------------------------------------------------------------ what format a written screen is
def _signed(text):
    """the format whose longest sign word is in the text, or None"""
    best = None
    low = (text or "").lower()
    for k in ORDER:
        for w in FORMATS[k].get("signs") or []:
            if w.lower() in low and (best is None or len(w) > best[1]):
                best = (k, len(w))
    return best[0] if best else None


def format_of(s):
    """the format of a screen: an activity's "format" (or its sign words, else 'exercise'); an active slide's technique, a
    claim or a drill on a slide; None for a screen that is no practice moment"""
    k = s.get("kind")
    if k == "activity":
        f = str(s.get("format") or "").strip()
        if f in FORMATS:
            return f
        return _signed(" ".join(str(s.get(x) or "") for x in ("title", "text"))) or UNNAMED["key"]
    if k == "slide" and not s.get("recap"):
        for field, key in F["slide_fields"].items():
            if not field.startswith("_") and s.get(field):
                return key
        a = s.get("active")
        if a and a in F["slide_active"]:
            return F["slide_active"][a]
    return None


def moments(script):
    """[(screen, format)] - the module's practice moments on the instructor tablet: activity screens and active slides"""
    return [(s, f) for s in script.get("screens", []) for f in [format_of(s)] if f]


def serves(key):
    """the task type a format serves ('explore', a slide technique with no TLA, serves a decision)"""
    f = get(key)
    return f["task_type"] if f else "decision"


# ------------------------------------------------------------------ the practical
def _num(x):
    return int(x) if float(x).is_integer() else round(float(x), 2)


def lines(v):
    if isinstance(v, list):
        return [str(x).strip() for x in v if str(x).strip()]
    return [x.strip(" -•\t") for x in str(v or "").splitlines() if x.strip(" -•\t")]


def cycle(minutes, team=False, runs=False, practice_runs=2, show=True, diagnostic=False, events=(), recorded=False):
    """(rows, warning) - brief / show (or diagnostic) / run(s) / debrief inside the exercise's own minutes (R8, L1): the
    brief 3-5 min, the debrief 15-20 for a team and 5-10 alone, a show of about a tenth on first exposure, the rest the
    runs - split in two practice runs where the format repeats (R9). The warning says when the minutes are too few."""
    M = float(minutes or 0)
    lo, hi = D["show_min"]
    brief = 3 if M < 30 else 4 if M < 60 else 5
    debrief = (15 if M < 90 else 20) if team else (5 if M < 60 else 10)
    sh = 0 if (recorded or not show) else max(lo, min(hi, int(round(M * D["show_share"]))))
    run = M - brief - sh - debrief
    if run < 5 and sh > lo:
        sh, run = lo, M - brief - lo - debrief
    if run < 5 and brief > 3:
        brief, run = 3, M - 3 - sh - debrief
    warn = None
    if run < 5:
        warn = ("%g min is too few for a %s with its %d-min debrief - give it at least %d min, or make it a run row of a "
                "longer practical" % (M, "team drill" if team else "drill", debrief, brief + sh + debrief + 5))
    rows = [{"kind": "brief", "min": _num(brief)}]
    if sh:
        rows.append({"kind": "diagnostic" if diagnostic else "show", "min": _num(sh)})
    ev = "; ".join(lines(events))
    if runs and practice_runs >= 2 and run >= 10:
        r1 = math.floor(run / 2)
        what = (["run 1: one team performs, another observes", "run 2: the teams swap"] if team
                else ["practice run 1", "practice run 2"])
        if ev:
            what[0] += " - planned events: " + ev
        rows += [{"kind": "run", "min": _num(r1), "what": what[0]}, {"kind": "run", "min": _num(run - r1), "what": what[1]}]
    else:
        rows.append(dict({"kind": "run", "min": _num(max(run, 0))}, **({"what": "planned events: " + ev} if ev else {})))
    rows.append(dict({"kind": "debrief", "min": _num(debrief)}, **({"what": D["debrief_team_what"]} if team else {})))
    return rows, warn


def needs_practical(key, where):
    """a practical (cards, cycle) for every simulator and equipment exercise, and every room drill, team scenario and
    project block; a case, a map or a discussion needs none (guideline 5.3)"""
    f = get(key) or UNNAMED
    return where in ("simulator", "equipment") or bool(f.get("practical"))


def practical(s, key, where, subs=(), criteria=(), experienced=False, minutes=None):
    """(entry, [warnings]) - a practical for instructor_led.json "practicals", from the activity screen's own approved words
    ("objective", "roles", "safety", "observe", "events", "team") and, where it has none, from the format's catalogue entry
    and the Sub-ILOs it serves. Safety on a simulator or real equipment is never drafted: it comes from the material."""
    f = get(key) or UNNAMED
    warns = []
    team = bool(s.get("team")) if "team" in s and not isinstance(s.get("team"), dict) else bool(f.get("team"))
    m = _minutes(s) if minutes is None else float(minutes)
    rows, warn = cycle(m, team=team, runs=bool(f.get("runs")), diagnostic=experienced, events=s.get("events") or ())
    if warn:
        warns.append(warn)
    subs = [x.rstrip(". ") for x in subs if x]
    obj = str(s.get("objective") or "").strip()
    if not obj:
        obj = ("By the end, each trainee %s." % "; and ".join(x[:1].lower() + x[1:] for x in subs[:2]) if subs
               else "By the end, each trainee has done: %s." % (s.get("title") or "the exercise"))
    safety = lines(s.get("safety"))
    if not safety and where == "room":
        safety = list(D["safety_room"])
    elif not safety:
        warns.append("safety: the hazards and limits of the %s come from its own material - write them in the activity's "
                     "\"safety\" or here" % ("simulator" if where == "simulator" else "equipment"))
    pb = {"objective": obj, "roles": str(s.get("roles") or f.get("roles") or D["roles_team" if team else "roles_solo"]),
          "safety": safety, "stop_word": str(s.get("stop_word") or "STOP")}
    if s.get("intervention") or f.get("intervention"):
        pb["intervention"] = str(s.get("intervention") or f["intervention"])
    seen, obs = set(), []
    own = lines(s.get("observe"))
    for x in own + ([] if len(own) >= 2 else list(criteria) + [f.get("observe") or ""] + subs + [D["observe_unnamed"]]):
        x = str(x or "").strip().rstrip(".")
        if x and x.lower() not in seen:
            seen.add(x.lower())
            obs.append(x)
    entry = {"_title": s.get("title"), "_minutes": _num(m), "_format": key, "team": team, "practice_runs": 2,
             "cycle": rows, "prebrief": pb, "debrief": {"must_observe": obs[:3]}}
    return entry, warns


def _minutes(s):
    try:
        return float(s.get("minutes") or 0)
    except (TypeError, ValueError):
        return 0.0
