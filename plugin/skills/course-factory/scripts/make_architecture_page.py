#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Stage 2 - the course architecture as ONE page the operator double-clicks, reads, and approves.

    make_architecture_page.py --course <course folder>
        [--programme programme.json] [--architecture architecture.json] [--plan plan.json]
        [--out ARCHITECTURE_REVIEW.html] [--check]

WHY THIS EXISTS
The Stage 2 STOP used to be a table in the chat. The operator could not print it, forward it or
read it next to the programme. This page is the STOP: the operator's "next" approves everything
on it (L29, L31).

ONE MODULE PER PROGRAMME TOPIC (owner, 2026-09-30 - L34)
The modules are the programme's own topics, one each, in the programme's order and with the
programme's hours: GAS BASIC has 22 topics, so 22 teaching modules. The programme's final
assessment topic is the LAST module and it is the assessment only - no slides, no teaching. Topics
are never merged into one module and never split across two. An academic hour is whatever the
programme says; at Novikontas it is 40 minutes, and that is used when the programme is silent.

WHAT IS ON IT
  * an overview of every module - programme topic word for word, theory and practice hours,
    minutes, self-checks, module check - totalled against the programme's own total row (L1);
  * how the course runs on the two tablets (L35): slides on the instructor tablet, mirrored to the
    classroom screen; tasks only on the trainee tablet, opened by the instructor's OPEN TASK;
  * the Main ILOs exactly as the programme writes them (L2);
  * per module: the programme topic and its sub-topics verbatim, the time budget, every Sub-ILO
    beside the programme's own wording (kept / re-expressed / added), theory taught as activity
    (L5), practical tasks and equipment (L28), and the tests - whether the planned self-checks fit
    the module's theory time is checked against knowledge/theory-rules.json (L36).

TWO LANGUAGES, NEVER MIXED
Programme text is shown exactly as written, marked with the programme's language; course text
(module titles in the course language, task names) with COURSE_LANGUAGE. The headings and
explanations around them are in the operator's language (architecture.json "operator_language":
en | lv | ru), from knowledge/page-labels.json.

INPUTS - in the course folder unless given
  programme.json     "academic_hour_min", "language", "source", "total_row", "main_ilos",
                     "outcomes" (the programme's own numbered learning outcomes, verbatim), and
                     "topics": {"1": {"title", "theory", "practical", "ref",
                                      "subtopics": [{"ref", "title"}], "assessment": false}}
  architecture.json  see build() below, or the example in scripts/test_architecture_page.py
  plan.json          optional: {"modules": [{"module": 1, "built_min": 80}]} - the minutes as built

It writes one self-contained HTML file (the style is inlined, nothing is fetched) that prints to
PDF from the browser. --check writes nothing and exits 1 when the page would show problems.
"""
from __future__ import annotations

import argparse
import html
import io
import json
import os
import re
import sys
from datetime import date

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
SKILLS = os.path.dirname(SKILL)
LABELS = json.load(io.open(os.path.join(SKILL, "knowledge", "page-labels.json"), encoding="utf-8"))
RULES = json.load(io.open(os.path.join(SKILL, "knowledge", "theory-rules.json"), encoding="utf-8"))
MEDIA = json.load(io.open(os.path.join(SKILL, "knowledge", "media-and-tasks.json"), encoding="utf-8"))
FAMILY_MARK = {"still": "▣", "moving": "▶", "interactive": "☝", "3d": "⬢", "video": "●"}
MOVING = ("moving", "interactive", "3d", "video")
TECHNIQUES = ["self-check", "explain-then-reveal", "predict-then-reveal", "worked-example", "scenario"]
NOVIKONTAS_ACADEMIC_HOUR = 40


def load(p):
    with io.open(p, encoding="utf-8") as f:
        return json.load(f)


def num(x):
    return float(x or 0)


def fmt_h(x):
    return ("%g" % x) if x else "0"


def topic_key(k):
    try:
        return (0, float(str(k).rstrip(".")))
    except ValueError:
        return (1, str(k))


class Page:
    def __init__(self, lang):
        self.lang = lang if lang in LABELS else "en"

    def t(self, key, **kw):
        s = LABELS[self.lang].get(key) or LABELS["en"].get(key) or key
        return s.format(**kw) if kw else s


def self_check_list(am):
    """architecture.json may give self_checks as a number or as a list of {questions, minutes, after}."""
    sc = am.get("self_checks") or []
    if isinstance(sc, (int, float)):
        sc = [{} for _ in range(int(sc))]
    out = []
    for x in sc:
        q = int(x.get("questions") or RULES["self_check"]["min_questions"])
        out.append({"questions": q, "minutes": num(x.get("minutes")) or q * RULES["self_check"]["minutes_per_question"],
                    "after": x.get("after", ""), "mechanics": list(x.get("mechanics") or [])})
    return out


def module_check_of(am):
    mc = am.get("module_check") or {}
    if not mc:
        return {}
    q = int(mc.get("questions") or RULES["module_check"]["min_questions"])
    return {"questions": q, "minutes": num(mc.get("minutes")) or q * RULES["module_check"]["minutes_per_question"],
            "graded": bool(mc.get("graded")), "mechanics": list(mc.get("mechanics") or [])}


def media_of(am):
    """architecture.json "media": [{"kind", "what"}] - the pictures, animation and 3D a module plans (L37)."""
    return [x for x in (am.get("media") or []) if isinstance(x, dict)]


def analyse(prog, arch, plan=None):
    """Every number the page shows, and every problem it must show first."""
    plan = plan or {}
    ahm = num(prog.get("academic_hour_min"))
    ahm_assumed = not ahm
    ahm = ahm or NOVIKONTAS_ACADEMIC_HOUR
    topics = prog.get("topics", {})
    order = sorted(topics, key=topic_key)
    arch_mods = {int(m["module"]): m for m in arch.get("modules", [])}
    built = {int(m["module"]): num(m.get("built_min")) for m in plan.get("modules", [])}
    fa = arch.get("final_assessment") or {}
    assess_topic = str(fa.get("topic")) if fa.get("topic") else next(
        (t for t in order if topics[t].get("assessment")), None)
    problems, modules, suggestions = [], [], []   # suggestions never stop the course (owner, 2.18.1)

    for pm in plan.get("modules", []) + arch.get("modules", []):
        ts = pm.get("topics")
        if ts is not None and len(ts) != 1:
            problems.append(("p_one_topic", {"m": pm.get("module"), "ts": ", ".join(str(x) for x in ts) or "—"}))

    for i, t in enumerate(order, 1):
        tp = topics[t]
        try:
            n = int(float(str(t).rstrip(".")))
        except ValueError:
            n = i
        am = arch_mods.get(n, {})
        th, pr = num(tp.get("theory")), num(tp.get("practical"))
        is_assess = str(t) == assess_topic
        m = {"n": n, "topic": str(t), "title": tp.get("title", ""), "ref": tp.get("ref", ""),
             "subtopics": tp.get("subtopics", []), "th": th, "pr": pr, "th_min": th * ahm, "pr_min": pr * ahm,
             "alloc": (th + pr) * ahm, "built": built.get(n, 0), "arch": am, "assessment": is_assess,
             "sc": [] if is_assess else self_check_list(am), "mc": {} if is_assess else module_check_of(am)}
        modules.append(m)
        if m["built"] and abs(m["built"] - m["alloc"]) > 0.5:
            problems.append(("p_hours", {"m": n, "alloc": "%g" % m["alloc"], "built": "%g" % m["built"]}))
        if is_assess:
            if am.get("sub_ilos") or am.get("self_checks") or am.get("module_check") or am.get("practicals"):
                problems.append(("p_assessment_only", {"m": n}))
            continue
        if not am:
            problems.append(("p_no_design", {"m": n}))
            continue
        if not m["mc"]:
            problems.append(("p_no_module_check", {"m": n}))
        elif m["mc"]["graded"]:
            problems.append(("p_module_check_graded", {"m": n}))
        rb = RULES["before_self_check"]
        need = sum(rb["min_minutes"] + s["minutes"] for s in m["sc"]) + (m["mc"].get("minutes", 0))
        if m["sc"] and need > m["th_min"] + 0.5:
            problems.append(("p_selfcheck_room", {"m": n, "k": len(m["sc"]), "need": "%g" % need,
                                                  "have": "%g" % m["th_min"], "min": rb["min_minutes"]}))
        for s in m["sc"]:
            if not RULES["self_check"]["min_questions"] <= s["questions"] <= RULES["self_check"]["max_questions"]:
                problems.append(("p_selfcheck_size", {"m": n, "q": s["questions"], "lo": RULES["self_check"]["min_questions"],
                                                      "hi": RULES["self_check"]["max_questions"]}))
        if m["mc"] and m["mc"]["questions"] < RULES["module_check"]["min_questions"]:
            problems.append(("p_modcheck_size", {"m": n, "q": m["mc"]["questions"], "lo": RULES["module_check"]["min_questions"]}))
        # L37 - the pictures, animation and 3D; L38 - the ways of answering
        F = MEDIA["floors"]
        md = media_of(am)
        for x in md:
            if x.get("kind") not in MEDIA["visual_kinds"]:
                problems.append(("p_media_kind", {"m": n, "k": x.get("kind")}))
        if not md:
            suggestions.append(("p_no_media", {"m": n}))
        elif m["th_min"] >= F["moving_or_3d_per_module_from_min"] and not any(
                MEDIA["visual_kinds"].get(x.get("kind"), {}).get("family") in MOVING for x in md):
            suggestions.append(("p_no_motion", {"m": n, "min": "%g" % m["th_min"]}))
        planned = [x for s in m["sc"] for x in s["mechanics"]] + (m["mc"].get("mechanics") or [])
        for x in planned:
            if x not in MEDIA["mechanics"] or x.startswith("_"):
                problems.append(("p_mech_unknown", {"m": n, "x": x}))
        for k, s in enumerate(m["sc"], 1):
            if s["mechanics"] and len(set(s["mechanics"])) < F["self_check_min_mechanics"]:
                problems.append(("p_sc_mix", {"m": n, "k": k, "lo": F["self_check_min_mechanics"]}))
        if m["mc"].get("mechanics") and len(set(m["mc"]["mechanics"])) < F["module_check_min_mechanics"]:
            problems.append(("p_mc_mix", {"m": n, "lo": F["module_check_min_mechanics"]}))
        if planned and not any(MEDIA["mechanics"].get(x, {}).get("hands_on") for x in planned):
            problems.append(("p_no_hands_on", {"m": n}))

    if assess_topic is None:
        problems.append(("p_no_assessment", {}))
    elif modules and not modules[-1]["assessment"]:
        problems.append(("p_assessment_not_last", {"t": assess_topic}))
    for n in arch_mods:
        if n not in {m["n"] for m in modules}:
            problems.append(("p_module_not_topic", {"m": n}))

    prog_ilos = {str(k): v for k, v in (prog.get("main_ilos") or {}).items()}
    arch_ilos = {str(i["id"]): i["text"] for i in arch.get("main_ilos", [])}
    for i, text in arch_ilos.items():
        if prog_ilos and prog_ilos.get(i) != text:
            problems.append(("p_main_not_verbatim", {"i": i}))
    outcomes = {str(k): v for k, v in (prog.get("outcomes") or {}).items()}
    for m in modules:
        a = m["arch"]
        for i in a.get("main_ilos", []):
            if str(i) not in arch_ilos:
                problems.append(("p_main_unknown", {"m": m["n"], "i": i}))
        for s in a.get("sub_ilos", []):
            st = s.get("status", "original")
            wording = s.get("programme_text") or outcomes.get(str(s.get("id")))
            if st in ("original", "re-expressed") and not wording:
                problems.append(("p_no_wording", {"m": m["n"], "s": s.get("id", "?"), "st": st}))
            if st == "original" and s.get("programme_text") and outcomes.get(str(s.get("id"))) \
                    and s["programme_text"] != outcomes[str(s["id"])]:
                problems.append(("p_sub_not_verbatim", {"m": m["n"], "s": s["id"]}))
            if st == "added" and not s.get("why"):
                problems.append(("p_added_why", {"m": m["n"], "s": s.get("id", "?")}))
    if not fa:
        problems.append(("p_no_final", {}))
    elif not fa.get("graded"):
        problems.append(("p_final_not_graded", {}))
    if (arch.get("course") or {}).get("course_type") not in ("NEW_ENTRANT", "EXPERIENCED"):
        problems.append(("p_no_type", {}))

    tr = prog.get("total_row") or {}
    tot_th, tot_pr = sum(m["th"] for m in modules), sum(m["pr"] for m in modules)
    if tr and (abs(num(tr.get("theory")) - tot_th) > 0.01 or abs(num(tr.get("practical")) - tot_pr) > 0.01):
        problems.append(("p_total_row", {"th": fmt_h(tot_th), "pr": fmt_h(tot_pr),
                                         "pth": fmt_h(num(tr.get("theory"))), "ppr": fmt_h(num(tr.get("practical")))}))
    return {"ahm": ahm, "ahm_assumed": ahm_assumed, "modules": modules, "problems": problems, "suggestions": suggestions,
            "tot_th": tot_th, "tot_pr": tot_pr, "outcomes": outcomes}


CSS_EXTRA = """
.verb{font-family:var(--font);background:var(--amber-wash-l);border-left:3px solid var(--amber);
  padding:.1em .45em;border-radius:0 var(--r-s) var(--r-s) 0}
.badge{display:inline-block;padding:.15em .6em;border-radius:var(--r-s);font-size:13px;font-weight:700}
.b-original{background:var(--grey);color:var(--ink)}
.b-re-expressed{background:var(--blue-wash-l);color:var(--navy)}
.b-added{background:var(--good-wash-l);color:var(--good)}
.b-ok{background:var(--good-wash-l);color:var(--good)}
.b-bad{background:var(--warn-wash-l);color:var(--warn)}
.b-assess{background:var(--amber-wash-l);color:var(--amber-ink)}
table{width:100%;border-collapse:collapse;font-size:14.5px;margin:0 0 18px}
th,td{text-align:left;vertical-align:top;padding:8px 10px;border-bottom:1px solid var(--line-l)}
th{background:var(--grey);color:var(--navy);font-weight:700}
td.n,th.n{text-align:right;white-space:nowrap}
tr.total td{font-weight:700;border-top:2px solid var(--navy)}
tr.assess td{background:var(--amber-wash-l)}
h1{color:var(--navy);margin:8px 0 6px} h2{color:var(--navy);margin:28px 0 8px} h3{color:var(--navy);margin:18px 0 6px}
.approves li,.tablets li{margin:4px 0}
.tablets{display:grid;grid-template-columns:1fr 1fr;gap:14px}
.tablets .card{margin:0}
.module{page-break-inside:avoid;break-inside:avoid;border-top:3px solid var(--navy);padding-top:6px;margin-top:26px}
.subs{margin:4px 0 10px;padding-left:1.2em} .subs li{margin:2px 0}
.own{margin-top:4px;font-size:13.5px} .own .verb{background:none;border-left-color:var(--line-l)}
@media (max-width:700px){.tablets{grid-template-columns:1fr}}
@media print{ body{background:#fff} .wrap{max-width:none;padding:0} .card{box-shadow:none}
  h2{page-break-after:avoid} tr{page-break-inside:avoid} }
"""


def style():
    css = ""
    for p in (os.path.join(SKILLS, "course-module-ui", "templates", "gb_tokens.css"),
              os.path.join(SKILLS, "course-module-ui", "templates", "gb_page.css")):
        css += io.open(p, encoding="utf-8").read() + "\n"
    # the style files' own comments are for the factory's maintainers, not the operator (L25)
    return re.sub(r"/\*.*?\*/", "", css, flags=re.S) + CSS_EXTRA


def build(prog, arch, a):
    """architecture.json:
    {"course": {"title", "course_language", "operator_language", "course_type", "programme_file",
                "model_course"},
     "main_ilos": [{"id", "text" (verbatim), "ref"}],
     "modules": [{"module": 1 (= the programme topic number), "title" (in the course language),
                  "main_ilos": ["1"],
                  "sub_ilos": [{"id", "status": "original|re-expressed|added", "programme_text", "text", "why"}],
                  "active_learning": [{"where", "instead_of", "technique", "note"}],
                  "practicals": [{"task", "equipment", "place", "minutes"}],
                  "self_checks": [{"questions": 4, "after": "sub-topic 1.1"}],
                  "module_check": {"questions": 6}}],
     "final_assessment": {"topic": "23", "questions", "pass_mark", "graded": true, "ref"},
     "notes": ["...in the operator's language"]}
    The assessment module has no entry in "modules" - it is the final assessment, nothing else."""
    c = arch.get("course", {})
    P = Page(c.get("operator_language", "en"))
    codes = LABELS["course_language_codes"]
    cl = codes.get(c.get("course_language", ""), "en")
    pl = codes.get(prog.get("language", ""), cl)
    e = lambda s: html.escape(str(s if s is not None else ""))
    V = lambda s, lang=None: '<span class="verb" lang="%s">%s</span>' % (lang or cl, e(s)) if s else ""
    VP = lambda s: V(s, pl)
    L = P.lang
    kl = lambda k: (MEDIA["visual_kinds"].get(k) or {}).get(L) or (MEDIA["visual_kinds"].get(k) or {}).get("en") or str(k)
    ml = lambda x: (MEDIA["mechanics"].get(x) or {}).get(L) or (MEDIA["mechanics"].get(x) or {}).get("en") or str(x)
    fam = lambda k: (MEDIA["visual_kinds"].get(k) or {}).get("family", "still")
    who = lambda k: MEDIA["made_by"].get((MEDIA["visual_kinds"].get(k) or {}).get("made_by"), {})
    out = ['<!DOCTYPE html><html lang="%s"><head><meta charset="utf-8">' % P.lang,
           '<meta name="viewport" content="width=device-width,initial-scale=1">',
           "<title>%s</title><style>%s</style></head><body><div class=\"wrap\">" % (e(P.t("page_title")), style())]
    out.append("<h1>%s</h1><p class=\"lead\">%s</p>" % (e(P.t("page_title")), e(P.t("intro"))))

    if a["suggestions"]:
        out.append('<div class="card"><h3>%s</h3><p class="note">%s</p><ul>%s</ul></div>' % (
            e(P.t("suggestions_title")), e(P.t("suggestions_intro")),
            "".join("<li>%s</li>" % e(P.t(k, **kw)) for k, kw in a["suggestions"])))
    if a["problems"]:
        out.append('<div class="card warn"><h3>%s</h3><ul>%s</ul></div>' % (
            e(P.t("problems_title")), "".join("<li>%s</li>" % e(P.t(k, **kw)) for k, kw in a["problems"])))

    mods = a["modules"]
    teaching = [m for m in mods if not m["assessment"]]
    assess = next((m for m in mods if m["assessment"]), None)
    subs = [s for m in mods for s in m["arch"].get("sub_ilos", [])]
    cnt = {k: sum(1 for s in subs if s.get("status", "original") == k) for k in ("original", "re-expressed", "added")}
    out.append('<div class="card key approves"><h3>%s</h3><ul><li>%s</li><li>%s</li><li>%s</li><li>%s</li><li>%s</li><li>%s</li></ul></div>' % (
        e(P.t("approves_title")),
        e(P.t("approves_split", n=len(mods), t=len(teaching), last=assess["n"] if assess else "—")),
        e(P.t("approves_subilo", re=cnt["re-expressed"], add=cnt["added"], orig=cnt["original"])),
        e(P.t("approves_tests")), e(P.t("approves_media")), e(P.t("approves_tablets")), e(P.t("approves_practice"))))
    out.append('<p class="note">%s %s</p>' % (VP("Aa"), e(P.t("verbatim_note"))))

    ctype = c.get("course_type", "")
    out.append("<table>")
    for k, v in (("course", V(c.get("title"))), ("course_type", e(P.t(ctype)) if ctype else "—"),
                 ("course_language", e(c.get("course_language", ""))), ("programme", e(c.get("programme_file", ""))),
                 ("model_course", e(c.get("model_course", "")) or "—"),
                 ("academic_hour", "%g %s%s" % (a["ahm"], e(P.t("minutes")),
                                                (" — " + e(P.t("ahm_assumed"))) if a["ahm_assumed"] else ""))):
        out.append("<tr><th>%s</th><td>%s</td></tr>" % (e(P.t(k)), v))
    out.append("</table>")

    # ---- the two tablets (L35)
    out.append('<h2>%s</h2><div class="tablets"><div class="card"><h3>%s</h3><ul>%s</ul></div>'
               '<div class="card"><h3>%s</h3><ul>%s</ul></div></div><p class="note">%s</p>' % (
                   e(P.t("tablets_title")), e(P.t("tab_instructor")),
                   "".join("<li>%s</li>" % e(P.t(k)) for k in ("tab_i1", "tab_i2", "tab_i3")),
                   e(P.t("tab_trainee")), "".join("<li>%s</li>" % e(P.t(k)) for k in ("tab_t1", "tab_t2", "tab_t3", "tab_t4")),
                   e(P.t("tab_scores"))))

    # ---- pictures, animation and 3D - who makes them (L37)
    plan = [(m["n"], x) for m in mods for x in media_of(m["arch"])]
    if plan:
        by = {}
        for n, x in plan:
            by.setdefault((MEDIA["visual_kinds"].get(x.get("kind")) or {}).get("made_by", "?"), []).append((n, x))
        rows = "".join("<tr><td>%s</td><td class=\"n\">%d</td></tr>" % (
            e((MEDIA["made_by"].get(k) or {}).get(L) or (MEDIA["made_by"].get(k) or {}).get("en") or k), len(v))
            for k, v in sorted(by.items(), key=lambda kv: -len(kv[1])))
        moving = sum(1 for _, x in plan if fam(x.get("kind")) in MOVING)
        out.append('<h2>%s</h2><p>%s</p><table>%s</table>' % (
            e(P.t("media_title")), e(P.t("media_intro", n=len(plan), mv=moving)), rows))
        for key in ("novikontas", "outside"):
            if by.get(key):
                mb = MEDIA["made_by"][key]
                out.append('<div class="card hot"><h3>%s (%d)</h3><p class="note">%s</p><ul>%s</ul></div>' % (
                    e(mb.get(L) or mb["en"]), len(by[key]), e(mb["how"]),
                    "".join("<li><b>%s %d</b> · %s — %s</li>" % (e(P.t("module")), n, e(kl(x.get("kind"))), V(x.get("what")))
                            for n, x in by[key])))

    # ---- overview: one module per programme topic
    out.append("<h2>%s</h2><p>%s</p><table><tr><th class=\"n\">%s</th><th>%s</th><th class=\"n\">%s</th><th class=\"n\">%s</th>"
               "<th class=\"n\">%s</th><th>%s</th><th>%s</th></tr>" % (
                   e(P.t("overview_title")), e(P.t("overview_intro", ahm="%g" % a["ahm"])), e(P.t("module")),
                   e(P.t("col_topic")), e(P.t("col_theory")), e(P.t("col_practical")), e(P.t("col_minutes")),
                   e(P.t("self_checks_short")), e(P.t("module_check"))))
    out[-1] = out[-1].replace("</tr>", "<th>%s</th></tr>" % e(P.t("col_media")), 1)
    marks = lambda am: " ".join("%s%d" % (FAMILY_MARK[f], c) for f, c in sorted(
        {f: sum(1 for x in media_of(am) if fam(x.get("kind")) == f) for f in FAMILY_MARK}.items(),
        key=lambda fc: list(FAMILY_MARK).index(fc[0])) if c) or "—"
    for m in mods:
        badge = ""
        if m["built"]:
            ok = abs(m["built"] - m["alloc"]) <= 0.5
            badge = ' <span class="badge %s">%s %g</span>' % ("b-ok" if ok else "b-bad", e(P.t("planned")), m["built"])
        if m["assessment"]:
            fa = arch.get("final_assessment") or {}
            out.append('<tr class="assess"><td class="n">%d</td><td>%s <span class="badge b-assess">%s</span></td><td class="n">%s</td>'
                       '<td class="n">%s</td><td class="n">%g%s</td><td colspan="3">%s</td></tr>' % (
                           m["n"], VP(m["title"]), e(P.t("assessment_only")), fmt_h(m["th"]), fmt_h(m["pr"]), m["alloc"], badge,
                           e(P.t("final_short", q=fa.get("questions", "—"), pm=fa.get("pass_mark", "—")))))
            continue
        own = m["arch"].get("title")
        out.append('<tr><td class="n">%d</td><td>%s%s</td><td class="n">%s</td><td class="n">%s</td><td class="n">%g%s</td><td>%s</td><td>%s</td><td>%s</td></tr>' % (
            m["n"], VP(m["title"]), ('<div class="own">%s</div>' % V(own)) if own and own != m["title"] else "", fmt_h(m["th"]), fmt_h(m["pr"]), m["alloc"], badge,
            e(len(m["sc"])) if m["arch"] else "—",
            e(P.t("mc_short", q=m["mc"]["questions"])) if m["mc"] else "—", e(marks(m["arch"]))))
    tot_min = (a["tot_th"] + a["tot_pr"]) * a["ahm"]
    out.append('<tr class="total"><td></td><td>%s</td><td class="n">%s</td><td class="n">%s</td><td class="n">%g</td><td>%d</td><td>%d</td><td></td></tr></table>' % (
        e(P.t("course_total")), fmt_h(a["tot_th"]), fmt_h(a["tot_pr"]), tot_min,
        sum(len(m["sc"]) for m in teaching), sum(1 for m in teaching if m["mc"])))
    tr = prog.get("total_row") or {}
    if tr:
        ok = not any(k == "p_total_row" for k, _ in a["problems"])
        out.append('<p>%s <span class="badge %s">%s</span></p>' % (
            e(P.t("total_row_line", th=fmt_h(num(tr.get("theory"))), pr=fmt_h(num(tr.get("practical"))),
                  tot=fmt_h(num(tr.get("total")) or num(tr.get("theory")) + num(tr.get("practical"))))),
            "b-ok" if ok else "b-bad", e(P.t("matches" if ok else "differs"))))
    pct = round(100 * a["tot_pr"] / (a["tot_th"] + a["tot_pr"])) if (a["tot_th"] + a["tot_pr"]) else 0
    out.append("<h2>%s</h2><p>%s</p>" % (e(P.t("ratio_title")), e(P.t("ratio_text", th=fmt_h(a["tot_th"]), pr=fmt_h(a["tot_pr"]), pct=pct))))

    # ---- Main ILOs, verbatim
    out.append("<h2>%s</h2><table>" % e(P.t("main_ilos_title")))
    for i in arch.get("main_ilos", []):
        out.append("<tr><td>%s</td><td>%s</td><td>%s</td></tr>" % (e(i.get("id")), VP(i.get("text")), e(i.get("ref", ""))))
    out.append("</table>")

    # ---- per module
    rb = RULES["before_self_check"]
    for m in mods:
        am = m["arch"]
        head = '<div class="module"><h2>%s %d · %s%s</h2>' % (
            e(P.t("module")), m["n"], VP(m["title"]),
            (" &nbsp;" + V(am["title"])) if am.get("title") and am.get("title") != m["title"] else "")
        out.append(head)
        out.append("<p><b>%s</b> · %s %s h · %s %s h · <b>%g %s</b>%s</p>" % (
            e(P.t("from_programme", t=m["topic"])), e(P.t("col_theory_short")), fmt_h(m["th"]),
            e(P.t("col_practical_short")), fmt_h(m["pr"]), m["alloc"], e(P.t("minutes")),
            (" <span class=\"note\">(%s)</span>" % e(m["ref"])) if m["ref"] else ""))
        if m["subtopics"]:
            out.append('<ul class="subs">%s</ul>' % "".join("<li>%s %s</li>" % (e(s.get("ref", "")), VP(s.get("title", "")))
                                                            for s in m["subtopics"]))
        if m["assessment"]:
            fa = arch.get("final_assessment") or {}
            out.append('<div class="card key"><p><b>%s</b></p><p>%s</p><p>%s %s — <b>%s</b>. %s: %s %s</p></div></div>' % (
                e(P.t("assessment_only_long")), e(P.t("assessment_how")),
                e(fa.get("questions", "—")), e(P.t("questions")),
                e(P.t("graded") if fa.get("graded") else P.t("not_graded")), e(P.t("pass_mark")), VP(fa.get("pass_mark", "")),
                ("(" + e(fa["ref"]) + ")") if fa.get("ref") else ""))
            continue
        if not am:
            out.append('<p class="note">%s</p></div>' % e(P.t("not_designed")))
            continue
        # time budget
        sc_min = sum(s["minutes"] for s in m["sc"])
        mc_min = m["mc"].get("minutes", 0)
        slides_min = m["th_min"] - sc_min - mc_min
        out.append("<h3>%s</h3><table><tr><td>%s</td><td class=\"n\">%g %s</td></tr>" % (
            e(P.t("budget_title")), e(P.t("budget_slides")), slides_min, e(P.t("minutes"))))
        for k, s in enumerate(m["sc"], 1):
            out.append("<tr><td>%s</td><td class=\"n\">%g %s</td></tr>" % (
                e(P.t("budget_sc", k=k, q=s["questions"], after=s["after"] or P.t("after_theory", min=rb["min_minutes"]))),
                s["minutes"], e(P.t("minutes"))))
        if m["mc"]:
            out.append("<tr><td>%s</td><td class=\"n\">%g %s</td></tr>" % (e(P.t("budget_mc", q=m["mc"]["questions"])), mc_min, e(P.t("minutes"))))
        if m["pr_min"]:
            out.append("<tr><td>%s</td><td class=\"n\">%g %s</td></tr>" % (e(P.t("budget_practice")), m["pr_min"], e(P.t("minutes"))))
        out.append('<tr class="total"><td>%s</td><td class="n">%g %s</td></tr></table>' % (e(P.t("module_total")), m["alloc"], e(P.t("minutes"))))
        if am.get("main_ilos"):
            ilo_text = {str(i["id"]): i["text"] for i in arch.get("main_ilos", [])}
            out.append("<p><b>%s:</b> %s</p>" % (e(P.t("main_ilos")), "; ".join(
                "%s %s" % (e(x), VP(ilo_text.get(str(x), ""))) for x in am["main_ilos"])))
        if am.get("sub_ilos"):
            out.append("<h3>%s</h3><p class=\"note\">%s</p><table><tr><th>%s</th><th>%s</th><th>%s</th><th>%s</th><th>%s</th></tr>" % (
                e(P.t("subilo_title")), e(P.t("subilo_intro")), e(P.t("col_subilo")), e(P.t("col_status")),
                e(P.t("col_programme_wording")), e(P.t("col_new_wording")), e(P.t("col_why"))))
            for s in am["sub_ilos"]:
                st = s.get("status", "original")
                wording = s.get("programme_text") or a["outcomes"].get(str(s.get("id")))
                prog_txt = VP(wording) if wording else "<i>%s</i>" % e(P.t("no_programme_wording"))
                new_txt = V(s.get("text") or wording or "") if st != "original" else VP(wording or "")
                out.append('<tr><td>%s</td><td><span class="badge b-%s">%s</span></td><td>%s</td><td>%s</td><td>%s</td></tr>' % (
                    e(s.get("id")), e(st), e(P.t("status_" + st)), prog_txt, new_txt, e(s.get("why", "")) or "—"))
            out.append("</table>")
        if am.get("active_learning"):
            out.append("<h3>%s</h3><table><tr><th>%s</th><th>%s</th><th>%s</th></tr>" % (
                e(P.t("active_title")), e(P.t("col_where")), e(P.t("col_instead")), e(P.t("col_technique"))))
            for x in am["active_learning"]:
                tech = x.get("technique", "other")
                out.append("<tr><td>%s</td><td>%s</td><td>%s%s</td></tr>" % (
                    e(x.get("where", "")), e(x.get("instead_of", "")),
                    e(P.t("tech_" + (tech if tech in TECHNIQUES else "other"))), (" — " + e(x["note"])) if x.get("note") else ""))
            out.append("</table>")
        if media_of(am):
            out.append("<h3>%s</h3><table><tr><th>%s</th><th>%s</th><th>%s</th></tr>%s</table>" % (
                e(P.t("media_module_title")), e(P.t("col_kind")), e(P.t("col_what")), e(P.t("col_who")),
                "".join("<tr><td>%s %s</td><td>%s</td><td>%s</td></tr>" % (
                    FAMILY_MARK.get(fam(x.get("kind")), "?"), e(kl(x.get("kind"))), V(x.get("what")),
                    e(who(x.get("kind")).get(L) or who(x.get("kind")).get("en") or "")) for x in media_of(am))))
        if am.get("practicals"):
            out.append("<h3>%s</h3><p class=\"note\">%s</p><table><tr><th>%s</th><th>%s</th><th>%s</th><th>%s</th></tr>" % (
                e(P.t("practice_title")), e(P.t("equipment_note")), e(P.t("col_task")), e(P.t("col_equipment")),
                e(P.t("col_place")), e(P.t("col_minutes"))))
            for x in am["practicals"]:
                out.append("<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>" % (
                    V(x.get("task")), VP(x.get("equipment")), e(x.get("place", "")), e(x.get("minutes", ""))))
            out.append("</table>")
        items = []
        for k, s in enumerate(m["sc"], 1):
            items.append("<li>%s%s</li>" % (e(P.t("test_sc", k=k, q=s["questions"])),
                                            ("<br><span class=\"note\">%s: %s</span>" % (e(P.t("how_answered")), e(", ".join(ml(x) for x in s["mechanics"])))) if s["mechanics"] else ""))
        if not m["sc"]:
            items.append("<li>%s</li>" % e(P.t("test_no_sc", min=rb["min_minutes"])))
        if m["mc"]:
            items.append("<li>%s — <b>%s</b>%s</li>" % (e(P.t("test_mc", q=m["mc"]["questions"])),
                                                       e(P.t("graded") if m["mc"]["graded"] else P.t("not_graded")),
                                                       ("<br><span class=\"note\">%s: %s</span>" % (e(P.t("how_answered")), e(", ".join(ml(x) for x in m["mc"]["mechanics"])))) if m["mc"].get("mechanics") else ""))
        out.append("<h3>%s</h3><ul>%s</ul></div>" % (e(P.t("tests_title")), "".join(items)))

    if arch.get("notes"):
        out.append("<h2>%s</h2><ul>%s</ul>" % (e(P.t("notes_title")), "".join("<li>%s</li>" % e(n) for n in arch["notes"])))
    out.append('<p class="foot">%s %s %s</p></div></body></html>' % (e(P.t("prepared")), date.today().isoformat(), e(P.t("by_factory"))))
    return "\n".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--course", required=True)
    ap.add_argument("--programme"); ap.add_argument("--architecture"); ap.add_argument("--plan")
    ap.add_argument("--out", default="ARCHITECTURE_REVIEW.html")
    ap.add_argument("--check", action="store_true", help="write nothing; exit 1 if the page would show problems")
    x = ap.parse_args(argv)
    path = lambda given, name: given or os.path.join(x.course, name)
    try:
        prog, arch = load(path(x.programme, "programme.json")), load(path(x.architecture, "architecture.json"))
        pp = path(x.plan, "plan.json")
        plan = load(pp) if (x.plan or os.path.isfile(pp)) else {}
    except (OSError, ValueError) as err:
        print("Stopped - one of the files the page is made from could not be read:\n    %s\n"
              "  They are programme.json and architecture.json in the course folder (plan.json is optional)." % err)
        return 2
    a = analyse(prog, arch, plan)
    P = Page((arch.get("course") or {}).get("operator_language", "en"))
    if x.check:
        for k, kw in a["suggestions"]:
            print("  (suggestion) " + P.t(k, **kw))
        for k, kw in a["problems"]:
            print("  - " + P.t(k, **kw))
        print("%d problem(s)." % len(a["problems"]))
        return 1 if a["problems"] else 0
    out = x.out if os.path.isabs(x.out) else os.path.join(x.course, x.out)
    with io.open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write(build(prog, arch, a))
    print("The architecture page is ready:\n    %s\n  %d modules - one per programme topic, the last is the final assessment only.\n"
          "  Open it with a double-click; it opens in the web browser and prints to PDF from there.%s"
          % (out, len(a["modules"]), ("\n  It shows %d problem(s) at the top - they are for the operator to see before approving." % len(a["problems"]))
                                     if a["problems"] else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
