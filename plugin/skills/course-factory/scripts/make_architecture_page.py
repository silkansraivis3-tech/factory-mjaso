#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Stage 2 - the course architecture as ONE page the operator double-clicks, reads, and approves.

    make_architecture_page.py --course <course folder>
        [--programme programme.json] [--plan plan.json] [--architecture architecture.json]
        [--out ARCHITECTURE_REVIEW.html] [--check]

WHY THIS EXISTS
The Stage 2 STOP used to be a table in the chat. The operator could not print it, forward it or
read it next to the programme, and the one thing their "next" most needed to show - which
Sub-ILOs change, and from what wording - was a line in a message. This page is the STOP: the
operator's "next" approves everything on it (L29, L31).

WHAT IS ON IT (owner, 2026-09-30)
  * every module's hours, with the PROGRAMME TOPICS AND ROWS they come from, so the reviewer can
    check them against the programme itself; the plan's minutes checked against them (L1);
  * the Main ILOs exactly as the programme writes them (L2);
  * every Sub-ILO beside the programme's own wording, marked kept / re-expressed / added - the
    operator's "next" ratifies them;
  * where theory is taught as activity (L5), the practical tasks and their equipment (L28), and the
    test plan: self-checks and module checks not graded, the final assessment graded (L27).

TWO LANGUAGES, NEVER MIXED
Programme text, Main ILOs, Sub-ILO wording, module titles and task names are shown exactly as
written, in COURSE_LANGUAGE, and marked with it. The headings and explanations around them are in
the operator's language (architecture.json "operator_language": en | lv | ru), from
knowledge/page-labels.json.

INPUTS - in the course folder unless given
  programme.json     as for hours/scripts/check_hours.py, plus optional per topic "title" (verbatim)
                     and "ref" (where in the programme: page, table, row), and optional "main_ilos"
  plan.json          as for check_hours.py: modules -> topics -> built_min
  architecture.json  the rest - see the docstring of build() below, or the example in
                     scripts/test_architecture_page.py

It writes one self-contained HTML file (the style is inlined, nothing is fetched) that prints to
PDF from the browser. --check writes nothing and exits 1 when the page would show problems.
"""
from __future__ import annotations

import argparse
import html
import io
import json
import os
import sys
from datetime import date

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
SKILLS = os.path.dirname(SKILL)
LABELS = json.load(io.open(os.path.join(SKILL, "knowledge", "page-labels.json"), encoding="utf-8"))
TECHNIQUES = ["self-check", "explain-then-reveal", "predict-then-reveal", "worked-example", "scenario"]


def load(p):
    with io.open(p, encoding="utf-8") as f:
        return json.load(f)


def num(x):
    return float(x or 0)


def fmt_h(x):
    return ("%g" % x) if x else "0"


class Page:
    def __init__(self, lang):
        self.lang = lang if lang in LABELS else "en"

    def t(self, key, **kw):
        s = LABELS[self.lang].get(key) or LABELS["en"].get(key) or key
        return s.format(**kw) if kw else s


def analyse(prog, plan, arch):
    """Every number the page shows, and every problem it must show first."""
    ahm = num(prog.get("academic_hour_min")) or 45
    topics = prog.get("topics", {})
    arch_mods = {int(m["module"]): m for m in arch.get("modules", [])}
    modules, problems, claimed = [], [], set()
    for pm in plan.get("modules", []):
        n = int(pm["module"])
        rows, alloc, th, pr = [], 0.0, 0.0, 0.0
        for t in pm.get("topics", []):
            claimed.add(str(t))
            tp = topics.get(str(t), {})
            m = (num(tp.get("theory")) + num(tp.get("practical"))) * ahm
            rows.append({"topic": str(t), "title": tp.get("title", ""), "ref": tp.get("ref", ""),
                         "theory": num(tp.get("theory")), "practical": num(tp.get("practical")), "minutes": m})
            alloc += m
            th += num(tp.get("theory"))
            pr += num(tp.get("practical"))
        built = num(pm.get("built_min"))
        if built and abs(built - alloc) > 0.5:
            problems.append(("p_hours", {"m": n, "alloc": "%g" % alloc, "built": "%g" % built}))
        modules.append({"n": n, "rows": rows, "alloc": alloc, "built": built, "th": th, "pr": pr,
                        "arch": arch_mods.get(n, {})})
    outside = [str(o.get("topic")) for o in plan.get("outside_modules", [])]
    for t in topics:
        if str(t) not in claimed and str(t) not in outside:
            problems.append(("p_unclaimed", {"t": t}))

    prog_ilos = {str(k): v for k, v in (prog.get("main_ilos") or {}).items()}
    arch_ilos = {str(i["id"]): i["text"] for i in arch.get("main_ilos", [])}
    for i, text in arch_ilos.items():
        if prog_ilos and prog_ilos.get(i) != text:
            problems.append(("p_main_not_verbatim", {"i": i}))
    for m in modules:
        a = m["arch"]
        for i in a.get("main_ilos", []):
            if str(i) not in arch_ilos:
                problems.append(("p_main_unknown", {"m": m["n"], "i": i}))
        for s in a.get("sub_ilos", []):
            st = s.get("status", "original")
            if st in ("original", "re-expressed") and not s.get("programme_text"):
                problems.append(("p_no_wording", {"m": m["n"], "s": s.get("id", "?"), "st": st}))
            if st == "added" and not s.get("why"):
                problems.append(("p_added_why", {"m": m["n"], "s": s.get("id", "?")}))
        if (a.get("module_check") or {}).get("graded"):
            problems.append(("p_module_check_graded", {"m": m["n"]}))
    if arch.get("final_assessment") and not arch["final_assessment"].get("graded"):
        problems.append(("p_final_not_graded", {}))
    if (arch.get("course") or {}).get("course_type") not in ("NEW_ENTRANT", "EXPERIENCED"):
        problems.append(("p_no_type", {}))
    return {"ahm": ahm, "modules": modules, "outside": plan.get("outside_modules", []), "problems": problems}


CSS_EXTRA = """
.verb{font-family:var(--font);background:var(--amber-wash-l);border-left:3px solid var(--amber);
  padding:.1em .45em;border-radius:0 var(--r-s) var(--r-s) 0}
.badge{display:inline-block;padding:.15em .6em;border-radius:var(--r-s);font-size:13px;font-weight:700}
.b-original{background:var(--grey);color:var(--ink)}
.b-re-expressed{background:var(--blue-wash-l);color:var(--navy)}
.b-added{background:var(--good-wash-l);color:var(--good)}
.b-ok{background:var(--good-wash-l);color:var(--good)}
.b-bad{background:var(--warn-wash-l);color:var(--warn)}
table{width:100%;border-collapse:collapse;font-size:14.5px;margin:0 0 18px}
th,td{text-align:left;vertical-align:top;padding:8px 10px;border-bottom:1px solid var(--line-l)}
th{background:var(--grey);color:var(--navy);font-weight:700}
tr.total td{font-weight:700;border-top:2px solid var(--navy)}
h1{color:var(--navy);margin:8px 0 6px} h2{color:var(--navy);margin:28px 0 8px} h3{color:var(--navy);margin:18px 0 6px}
.approves li{margin:4px 0}
.module{page-break-inside:avoid;break-inside:avoid}
@media print{ body{background:#fff} .wrap{max-width:none;padding:0} .card{box-shadow:none}
  h2{page-break-after:avoid} tr{page-break-inside:avoid} }
"""


def style():
    css = ""
    for p in (os.path.join(SKILLS, "course-module-ui", "templates", "gb_tokens.css"),
              os.path.join(SKILLS, "course-module-ui", "templates", "gb_page.css")):
        css += io.open(p, encoding="utf-8").read() + "\n"
    return css + CSS_EXTRA


def build(prog, plan, arch, a):
    """architecture.json:
    {"course": {"title", "course_language", "operator_language", "course_type", "programme_file",
                "model_course"},
     "main_ilos": [{"id", "text" (verbatim), "ref"}],
     "modules": [{"module": 1, "title", "main_ilos": ["1"],
                  "sub_ilos": [{"id", "status": "original|re-expressed|added", "programme_text", "text", "why"}],
                  "active_learning": [{"where", "instead_of", "technique", "note"}],
                  "practicals": [{"task", "equipment", "place", "minutes"}],
                  "self_checks": 4, "module_check": {"questions": 10, "graded": false}}],
     "final_assessment": {"questions", "pass_mark", "graded": true, "ref"},
     "notes": ["...in the operator's language"]}"""
    c = arch.get("course", {})
    P = Page(c.get("operator_language", "en"))
    cl = LABELS["course_language_codes"].get(c.get("course_language", ""), "en")
    e = lambda s: html.escape(str(s if s is not None else ""))
    V = lambda s: '<span class="verb" lang="%s">%s</span>' % (cl, e(s)) if s else ""
    out = ['<!DOCTYPE html><html lang="%s"><head><meta charset="utf-8">' % P.lang,
           '<meta name="viewport" content="width=device-width,initial-scale=1">',
           "<title>%s</title><style>%s</style></head><body><div class=\"wrap\">" % (e(P.t("page_title")), style())]
    out.append("<h1>%s</h1><p class=\"lead\">%s</p>" % (e(P.t("page_title")), e(P.t("intro"))))

    if a["problems"]:
        out.append('<div class="card warn"><h3>%s</h3><ul>%s</ul></div>' % (
            e(P.t("problems_title")), "".join("<li>%s</li>" % e(P.t(k, **kw)) for k, kw in a["problems"])))

    subs = [s for m in arch.get("modules", []) for s in m.get("sub_ilos", [])]
    cnt = {k: sum(1 for s in subs if s.get("status", "original") == k) for k in ("original", "re-expressed", "added")}
    out.append('<div class="card key approves"><h3>%s</h3><ul><li>%s</li><li>%s</li><li>%s</li><li>%s</li></ul></div>' % (
        e(P.t("approves_title")), e(P.t("approves_split")),
        e(P.t("approves_subilo", re=cnt["re-expressed"], add=cnt["added"], orig=cnt["original"])),
        e(P.t("approves_tests")), e(P.t("approves_practice"))))
    out.append('<p class="note">%s %s</p>' % (V("Aa"), e(P.t("verbatim_note"))))

    ctype = c.get("course_type", "")
    out.append("<table>")
    for k, v in (("course", V(c.get("title"))), ("course_type", e(P.t(ctype)) if ctype else "—"),
                 ("course_language", e(c.get("course_language", ""))), ("programme", e(c.get("programme_file", ""))),
                 ("model_course", e(c.get("model_course", "")) or "—"),
                 ("academic_hour", "%g %s" % (a["ahm"], e(P.t("minutes"))))):
        out.append("<tr><th>%s</th><td>%s</td></tr>" % (e(P.t(k)), v))
    out.append("</table>")

    # ---- hours, from the programme rows
    out.append("<h2>%s</h2><p>%s</p>" % (e(P.t("hours_title")), e(P.t("hours_intro"))))
    tot_min = tot_th = tot_pr = 0
    for m in a["modules"]:
        am = m["arch"]
        ok = (not m["built"]) or abs(m["built"] - m["alloc"]) <= 0.5
        out.append('<div class="module"><h3>%s %d · %s</h3><table><tr><th>%s</th><th>%s</th><th>%s</th><th>%s</th><th>%s</th></tr>'
                   % (e(P.t("module")), m["n"], V(am.get("title", "")), e(P.t("col_topic")), e(P.t("col_row")),
                      e(P.t("col_theory")), e(P.t("col_practical")), e(P.t("col_minutes"))))
        for r in m["rows"]:
            out.append("<tr><td>%s %s</td><td>%s</td><td>%s</td><td>%s</td><td>%g</td></tr>" % (
                e(r["topic"]), V(r["title"]), e(r["ref"]) or "—", fmt_h(r["theory"]), fmt_h(r["practical"]), r["minutes"]))
        out.append('<tr class="total"><td colspan="2">%s</td><td>%s</td><td>%s</td><td>%g%s</td></tr></table>' % (
            e(P.t("module_total")), fmt_h(m["th"]), fmt_h(m["pr"]), m["alloc"],
            "" if not m["built"] else ' &nbsp;<span class="badge %s">%s %g · %s</span>' % (
                "b-ok" if ok else "b-bad", e(P.t("planned")), m["built"], e(P.t("matches" if ok else "differs")))))
        out.append("</div>")
        tot_min += m["alloc"]; tot_th += m["th"]; tot_pr += m["pr"]
    for o in a["outside"]:
        tp = prog.get("topics", {}).get(str(o.get("topic")), {})
        out.append("<p>%s: %s %s — %s h</p>" % (e(P.t("outside")), e(o.get("topic")), V(tp.get("title", "")), e(o.get("hours", ""))))
    total_row = prog.get("total_row") or {}
    out.append('<p><b>%s:</b> %g %s (%s h + %s h)</p>' % (e(P.t("course_total")), tot_min, e(P.t("minutes")),
                                                          fmt_h(tot_th), fmt_h(tot_pr)))
    th_all = num(total_row.get("theory")) or tot_th
    pr_all = num(total_row.get("practical")) or tot_pr
    pct = round(100 * pr_all / (th_all + pr_all)) if (th_all + pr_all) else 0
    out.append("<h2>%s</h2><p>%s</p>" % (e(P.t("ratio_title")), e(P.t("ratio_text", th=fmt_h(th_all), pr=fmt_h(pr_all), pct=pct))))

    # ---- Main ILOs, verbatim
    out.append("<h2>%s</h2><table>" % e(P.t("main_ilos_title")))
    for i in arch.get("main_ilos", []):
        out.append("<tr><td>%s</td><td>%s</td><td>%s</td></tr>" % (e(i.get("id")), V(i.get("text")), e(i.get("ref", ""))))
    out.append("</table>")

    # ---- per module: Sub-ILOs, activity, practice, tests
    for m in a["modules"]:
        am = m["arch"]
        out.append('<div class="module"><h2>%s %d · %s</h2>' % (e(P.t("module")), m["n"], V(am.get("title", ""))))
        if am.get("main_ilos"):
            out.append("<p><b>%s:</b> %s</p>" % (e(P.t("main_ilos")), ", ".join(e(x) for x in am["main_ilos"])))
        if am.get("sub_ilos"):
            out.append("<h3>%s</h3><p class=\"note\">%s</p><table><tr><th>%s</th><th>%s</th><th>%s</th><th>%s</th><th>%s</th></tr>" % (
                e(P.t("subilo_title")), e(P.t("subilo_intro")), e(P.t("col_subilo")), e(P.t("col_status")),
                e(P.t("col_programme_wording")), e(P.t("col_new_wording")), e(P.t("col_why"))))
            for s in am["sub_ilos"]:
                st = s.get("status", "original")
                prog_txt = V(s.get("programme_text")) if s.get("programme_text") else "<i>%s</i>" % e(P.t("no_programme_wording"))
                new_txt = V(s.get("text") or s.get("programme_text", "")) if st != "original" else V(s.get("programme_text", ""))
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
        if am.get("practicals"):
            out.append("<h3>%s</h3><p class=\"note\">%s</p><table><tr><th>%s</th><th>%s</th><th>%s</th><th>%s</th></tr>" % (
                e(P.t("practice_title")), e(P.t("equipment_note")), e(P.t("col_task")), e(P.t("col_equipment")),
                e(P.t("col_place")), e(P.t("col_minutes"))))
            for x in am["practicals"]:
                out.append("<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>" % (
                    V(x.get("task")), V(x.get("equipment")), e(x.get("place", "")), e(x.get("minutes", ""))))
            out.append("</table>")
        mc = am.get("module_check") or {}
        out.append("<h3>%s</h3><ul><li>%s: %s</li><li>%s: %s %s — <b>%s</b></li></ul></div>" % (
            e(P.t("tests_title")), e(P.t("self_checks")), e(am.get("self_checks", "—")),
            e(P.t("module_check")), e(mc.get("questions", "—")), e(P.t("questions")),
            e(P.t("graded") if mc.get("graded") else P.t("not_graded"))))

    fa = arch.get("final_assessment") or {}
    if fa:
        out.append("<h2>%s</h2><p>%s %s — <b>%s</b>. %s: %s %s</p>" % (
            e(P.t("final")), e(fa.get("questions", "—")), e(P.t("questions")),
            e(P.t("graded") if fa.get("graded") else P.t("not_graded")), e(P.t("pass_mark")), V(fa.get("pass_mark", "")),
            ("(" + e(fa["ref"]) + ")") if fa.get("ref") else ""))
    if arch.get("notes"):
        out.append("<h2>%s</h2><ul>%s</ul>" % (e(P.t("notes_title")), "".join("<li>%s</li>" % e(n) for n in arch["notes"])))
    out.append('<p class="foot">%s %s %s</p></div></body></html>' % (e(P.t("prepared")), date.today().isoformat(), e(P.t("by_factory"))))
    return "\n".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--course", required=True)
    ap.add_argument("--programme"); ap.add_argument("--plan"); ap.add_argument("--architecture")
    ap.add_argument("--out", default="ARCHITECTURE_REVIEW.html")
    ap.add_argument("--check", action="store_true", help="write nothing; exit 1 if the page would show problems")
    x = ap.parse_args(argv)
    path = lambda given, name: given or os.path.join(x.course, name)
    try:
        prog, plan, arch = load(path(x.programme, "programme.json")), load(path(x.plan, "plan.json")), load(path(x.architecture, "architecture.json"))
    except (OSError, ValueError) as err:
        print("Stopped - one of the three files the page is made from could not be read:\n    %s\n"
              "  They are programme.json, plan.json and architecture.json in the course folder." % err)
        return 2
    a = analyse(prog, plan, arch)
    P = Page((arch.get("course") or {}).get("operator_language", "en"))
    if x.check:
        for k, kw in a["problems"]:
            print("  - " + P.t(k, **kw))
        print("%d problem(s)." % len(a["problems"]))
        return 1 if a["problems"] else 0
    out = x.out if os.path.isabs(x.out) else os.path.join(x.course, x.out)
    with io.open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write(build(prog, plan, arch, a))
    print("The architecture page is ready:\n    %s\n  Open it with a double-click; it opens in the web browser and prints to PDF from there.%s"
          % (out, ("\n  It shows %d problem(s) at the top - they are for the operator to see before approving." % len(a["problems"]))
                  if a["problems"] else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
