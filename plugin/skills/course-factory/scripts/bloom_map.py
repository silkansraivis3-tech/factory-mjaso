#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""The Bloom map - what level the course asks for, what level its tasks reach, and how to lift them (L48).

    bloom_map.py --course <course>                the whole course, from the architecture (Stage 2)
    bloom_map.py --course <course> --module 1     one module, from its content script (Stage 3)

WHY THIS EXISTS (owner, 2026-10-15)
"My main task is to level up pedagogy - bloom taxonomy needs to be on higher level. That's why we
have tablets." On paper and in Google Classroom almost every task was Remember. The tablet lets a
trainee operate a panel, find a hazard, decide and justify. Until 2.25.0 nothing in the factory
measured it. This reads:
  * each ILO's level from its verb (knowledge/bloom.json - en whole words, lv and ru stems; the
    highest verb that leads a clause), or the level written on it ("bloom": 3);
  * each task's level from how the trainee answers it (its mechanic), or the level its author
    stated ("bloom": 4, "bloom_why": "...");
and says, in the operator's language: where the course is now, every task below its ILO, and which
tablet task types would lift it. Every finding is a SUGGESTION in 2.25.0 - it never blocks.

The same results are drawn on the Stage 2 architecture page (make_architecture_page.py) and on each
Stage 3 review page (content_script.py render). The judgement a list cannot make is in bloom/GUIDE.md.
Standard library only.
"""
from __future__ import annotations

import argparse
import html
import io
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
_k = lambda n: json.load(io.open(os.path.join(SKILL, "knowledge", n), encoding="utf-8"))
B, LABELS, MEDIA = _k("bloom.json"), _k("page-labels.json"), _k("media-and-tasks.json")
LEVELS = {int(k): v for k, v in B["levels"].items()}
APPLY = B["apply_level"]
TASK_KINDS = ("self-check", "module-check", "final")


# ------------------------------------------------------------------ words
def T(lang, key, **kw):
    s = LABELS.get(lang, {}).get(key) or LABELS["en"].get(key) or key
    return s.format(**kw) if kw else s


def lang_code(language, default="en"):
    """'Latvian' -> 'lv'; a code passes through."""
    if language in B["verbs"]:
        return language
    return LABELS["course_language_codes"].get(language or "", default)


def level_name(n, lang="en"):
    return (LEVELS.get(n) or {}).get(lang) or (LEVELS.get(n) or {}).get("en") or "?"


def mech_label(m, lang="en"):
    x = MEDIA["mechanics"].get(m) or {}
    return x.get(lang) or x.get("en") or str(m)


# ------------------------------------------------------------------ the level of an ILO
def _en_forms(w):
    """identify -> identifies, identified, identifying; plan -> planned, planning; describe -> describing."""
    head, _, tail = w.partition(" ")
    f = {head, head + "s", head + "es", head + "d", head + "ed", head + "ing"}
    if head.endswith("y") and len(head) > 2 and head[-2] not in "aeiou":
        f |= {head[:-1] + "ies", head[:-1] + "ied"}
    if head.endswith("e"):
        f.add(head[:-1] + "ing")
    if len(head) <= 4 and head[-1] not in "aeiouwy" and head[-2] in "aeiou":
        f |= {head + head[-1] + "ed", head + head[-1] + "ing"}
    return [x + ((" " + tail) if tail else "") for x in f]


_PAT = {}


def _patterns(lang):
    """[(compiled regex, level, weak, the word as written in the list)], longest first."""
    if lang in _PAT:
        return _PAT[lang]
    out = []
    for src, weak in ((B["verbs"].get(lang, {}), False), (B["weak"].get(lang, {}), True)):
        for lvl, words in src.items():
            if lvl.startswith("_"):
                continue
            for w in words:
                w = w.strip().lower()
                if w.endswith("$"):                       # a whole word only: lv 'veic$' is not 'veicināt'
                    w = w[:-1]
                    rx = r"(?<!\w)%s(?!\w)" % re.escape(w).replace(r"\ ", r"\s+")
                elif lang == "en":
                    rx = r"(?<!\w)(?:%s)(?!\w)" % "|".join(re.escape(x).replace(r"\ ", r"\s+") for x in _en_forms(w))
                else:
                    rx = r"(?<!\w)%s\w*" % re.escape(w).replace(r"\ ", r"\s+")
                out.append((re.compile(rx), int(lvl), weak, w))
    out.sort(key=lambda p: -len(p[3]))
    _PAT[lang] = out
    return out


def ilo_level(text, lang="en"):
    """{"level": 1-6 or None, "verb", "weak", "verbs": [(verb, level, weak), ...]} - the highest verb that leads a clause."""
    lang = lang_code(lang)
    if lang not in B["verbs"]:
        lang = "en"
    low = (text or "").lower()
    hits, taken = [], set()
    for rx, lvl, weak, w in _patterns(lang):
        for m in rx.finditer(low):
            span = set(range(m.start(), m.end()))
            if span & taken:
                continue
            taken |= span
            hits.append((m.start(), lvl, weak, m.group(0)))
    if not hits:
        return {"level": None, "verb": "", "weak": False, "verbs": []}
    hits.sort()
    leads = set(B["lead_words"].get(lang, [])) | set(B["lead_words"]["en"][:2])

    def leading(pos):
        before = low[:pos].rstrip()
        if not before or before[-1] in ",;:(•-–—" or re.search(r"(?:^|\s)\d+(?:\.\d+)*[.)]?$", before):
            return True
        last = re.split(r"\s+", before)[-1]
        return last in leads

    lead = [hits[0]] + [h for h in hits[1:] if leading(h[0])]
    strong = [h for h in lead if not h[2]]
    top = max(strong or lead, key=lambda h: h[1])
    return {"level": top[1], "verb": top[3], "weak": not strong, "verbs": [(h[3], h[1], h[2]) for h in lead]}


# ------------------------------------------------------------------ the level of a task
def task_level(mechanic, stated=None):
    m = B["mechanics"].get(mechanic) or B["mechanics"]["single_choice"]
    out = {"typical": m["typical"], "ceiling": m["ceiling"], "stated": False, "over": False, "level": m["typical"]}
    try:
        s = int(stated) if stated not in (None, "") else None
    except (TypeError, ValueError):
        s = None
    if s and 1 <= s <= 6:
        out.update(level=s, stated=True, over=s > m["ceiling"])
    return out


def lift_options(target, n=3):
    """Task types that usually reach the target level - closest first, hands-on first. Then those that can, written for it."""
    hands = lambda k: (MEDIA["mechanics"].get(k) or {}).get("hands_on", False)
    mk = {k: v for k, v in B["mechanics"].items() if not k.startswith("_")}
    usual = sorted((k for k, v in mk.items() if v["typical"] >= target), key=lambda k: (mk[k]["typical"] - target, not hands(k)))
    can = sorted((k for k, v in mk.items() if v["typical"] < target <= v["ceiling"] and v.get("higher")),
                 key=lambda k: (not hands(k), -mk[k]["typical"]))
    return usual[:n], can[:max(0, n - len(usual[:n]))] if len(usual) < n else []


def lift_text(target, lang):
    if target >= 6:      # Create: only a task type written for it comes near (2.28.0); real creation is the practical exercise
        can = [k for k, v in B["mechanics"].items() if not k.startswith("_") and v["ceiling"] >= 6]
        return "; ".join(["%s (%s)" % (mech_label(k, lang), B["mechanics"][k]["higher"]) for k in can] + [T(lang, "b_lift_create")])
    usual, can = lift_options(target)
    parts = [mech_label(k, lang) for k in usual]
    parts += ["%s (%s)" % (mech_label(k, lang), B["mechanics"][k]["higher"]) for k in can]
    return ", ".join(parts) or "—"


def dist(counts, lang):
    return " · ".join("%s %d" % (level_name(n, lang), counts[n]) for n in sorted(counts) if counts[n]) or "—"


# ------------------------------------------------------------------ the ILOs of the course
def _sub_ilos(prog, arch, am):
    """[(id, text, lang, level-info)] - the Sub-ILO as it will be taught (re-expressed / added in the course language)."""
    codes = LABELS["course_language_codes"]
    cl = codes.get((arch.get("course") or {}).get("course_language", ""), "en")
    pl = codes.get((prog or {}).get("language", ""), cl)
    outcomes = {str(k): v for k, v in ((prog or {}).get("outcomes") or {}).items()}
    out = []
    for s in am.get("sub_ilos", []) or []:
        st = s.get("status", "original")
        own = st in ("re-expressed", "added") and s.get("text")
        text = s["text"] if own else (s.get("programme_text") or outcomes.get(str(s.get("id"))) or s.get("text") or "")
        lg = cl if own else pl
        info = ilo_level(text, lg)
        if s.get("bloom"):
            info = dict(info, level=int(s["bloom"]), stated=True)
        out.append({"id": str(s.get("id", "?")), "text": text, "lang": lg, "status": st, **info})
    return out


def course_map(prog, arch, lang=None):
    """Stage 2: the level of every Main ILO and Sub-ILO, what the planned task types reach, the suggestions."""
    prog = prog or {}
    lang = lang or (arch.get("course") or {}).get("operator_language", "en")
    codes = LABELS["course_language_codes"]
    pl = codes.get(prog.get("language", ""), codes.get((arch.get("course") or {}).get("course_language", ""), "en"))
    found = []
    main = []
    for i in arch.get("main_ilos", []):
        info = ilo_level(i.get("text", ""), pl)
        main.append({"id": str(i.get("id")), "text": i.get("text", ""), **info})
        if info["weak"]:
            found.append(("b_weak_main", {"i": i.get("id"), "verb": info["verb"]}))
    fa_topic = str((arch.get("final_assessment") or {}).get("topic") or "")
    mods, asks, reach = [], {n: 0 for n in LEVELS}, {n: 0 for n in LEVELS}
    for am in sorted(arch.get("modules", []), key=lambda m: int(m.get("module", 0))):
        n = am.get("module")
        if str(n) == fa_topic:
            continue
        subs = _sub_ilos(prog, arch, am)
        if not subs:
            ids = [str(x) for x in am.get("main_ilos", [])]
            subs = [dict(x, status="main") for x in main if x["id"] in ids]
        planned = []
        sc = am.get("self_checks") or []
        for x in (sc if isinstance(sc, list) else []):
            planned += list(x.get("mechanics") or [])
        planned += list((am.get("module_check") or {}).get("mechanics") or [])
        planned = [p for p in planned if p in B["mechanics"]]
        lv = [s["level"] for s in subs if s["level"]]
        top = max(lv) if lv else None
        got = max((B["mechanics"][p]["typical"] for p in planned), default=None)
        for s in subs:
            if s["level"]:
                asks[s["level"]] += 1
            if s["status"] == "main":
                continue
            if s["level"] is None:
                found.append(("b_unknown", {"m": n, "s": s["id"]}))
            elif s["weak"] and not s.get("stated"):
                found.append(("b_weak_sub", {"m": n, "s": s["id"], "verb": s["verb"],
                                             "ex": "; ".join("%s (%s)" % ((LEVELS[k].get("examples") or {}).get(s["lang"]) or LEVELS[k]["examples"]["en"],
                                                                           level_name(k, lang)) for k in sorted({s["level"], max(s["level"], APPLY)}))}))
            if s["level"] == 6:
                found.append(("b_create", {"m": n, "s": s["id"]}))
        for p in planned:
            reach[B["mechanics"][p]["typical"]] += 1
        if top and got is not None and got < top:
            want = min(top, 5)
            found.append(("b_plan_below", {"m": n, "want": level_name(top, lang), "got": level_name(got, lang),
                                            "how": lift_text(want, lang), "wantn": level_name(want, lang)}))
        mods.append({"n": n, "title": am.get("title", ""), "subs": subs, "top": top, "planned": planned, "got": got})
    return {"main": main, "modules": mods, "asks": asks, "reach": reach, "findings": found, "lang": lang}


# ------------------------------------------------------------------ the tasks of one module
def module_map(script, arch_module=None, prog=None, arch=None, mech=None, where=None):
    """Stage 3: every question's level, the module's share at Apply or higher, every gap and how to lift it.
    mech(q) -> the question's mechanic; where(id) -> where it is, in words (content_script passes both)."""
    lang = script.get("operator_language", "en")
    mech = mech or (lambda q: q.get("mechanic") or "single_choice")
    where = where or (lambda sid: sid)
    qs = [q for q in script.get("screens", []) if q.get("kind") in TASK_KINDS]
    rows, counts, found = [], {n: 0 for n in LEVELS}, []
    for q in qs:
        m = mech(q)
        tl = task_level(m, q.get("bloom"))
        rows.append({"id": q["id"], "kind": q.get("kind"), "mechanic": m, "sub_ilo": str(q["sub_ilo"]) if q.get("sub_ilo") else "",
                     "why": q.get("bloom_why", ""), **tl})
        counts[tl["level"]] += 1
        if tl["over"]:
            found.append(("b_q_over", {"w": where(q["id"]), "lvl": level_name(tl["level"], lang), "how": mech_label(m, lang),
                                       "ceil": level_name(tl["ceiling"], lang)}))
    n = len(rows)
    share = sum(1 for r in rows if r["level"] >= APPLY) / float(n) if n else 0.0
    floor = B["floors"]["apply_plus_min_share"]
    if n and share < floor:
        low = [r for r in rows if r["level"] < APPLY]
        found.append(("b_share_low", {"pct": "%.0f" % (100 * share), "min": "%.0f" % (100 * floor),
                                      "ids": ", ".join(where(r["id"]) for r in low[:4]) + (" …" if len(low) > 4 else ""),
                                      "how": lift_text(APPLY, lang)}))
    subs = _sub_ilos(prog, arch or {}, arch_module or {}) if arch_module else []
    by_id = {s["id"]: s for s in subs}
    for r in rows:
        s = by_id.get(r["sub_ilo"])
        if s and s["level"] and r["level"] < min(s["level"], 5):
            found.append(("b_q_below", {"w": where(r["id"]), "s": s["id"], "want": level_name(s["level"], lang),
                                        "got": level_name(r["level"], lang), "now": mech_label(r["mechanic"], lang),
                                        "how": lift_text(min(s["level"], 5), lang)}))
    linked = any(r["sub_ilo"] for r in rows)
    checks = [r for r in rows if r["kind"] == "module-check"]
    sub_rows = []
    for s in subs:
        mine = [r for r in checks if r["sub_ilo"] == s["id"]] if linked else checks
        best = max((r["level"] for r in mine), default=None)
        ok = bool(s["level"]) and best is not None and best >= min(s["level"], 5)
        sub_rows.append({"id": s["id"], "level": s["level"], "best": best, "ok": ok, "text": s["text"]})
        if s["level"] and checks and not ok and B["floors"]["module_check_reaches_ilo"]:
            found.append(("b_sub_unchecked", {"s": s["id"], "want": level_name(s["level"], lang),
                                              "how": lift_text(min(s["level"], 5), lang)}))
    return {"rows": rows, "counts": counts, "share": share, "floor": floor, "subs": sub_rows,
            "linked": linked, "findings": found, "lang": lang}


# ------------------------------------------------------------------ drawn on the review pages
CSS = """
.bl{display:inline-block;padding:.12em .55em;border-radius:var(--r-s);font-size:12.5px;font-weight:700;white-space:nowrap}
.bl1,.bl2{background:var(--grey);color:var(--ink)} .bl3,.bl4{background:var(--blue-wash-l);color:var(--navy)}
.bl5,.bl6{background:var(--good-wash-l);color:var(--good)} .bl0{background:var(--warn-wash-l);color:var(--warn)}
.bbar{display:inline-block;height:10px;background:var(--navy);border-radius:3px;vertical-align:middle}
.blegend li{margin:2px 0}
"""


def _esc(s):
    return html.escape(str(s if s is not None else ""))


def badge(n, lang):
    return '<span class="bl bl%d">%s</span>' % (n or 0, html.escape(level_name(n, lang) if n else "?"))


def legend_html(lang):
    e = _esc
    return '<ul class="blegend note">%s</ul>' % "".join(
        "<li>%s %s</li>" % (badge(n, lang), e(LEVELS[n]["means"].get(lang) or LEVELS[n]["means"]["en"])) for n in sorted(LEVELS))


def course_html(cm, V=None):
    """The Bloom section of the Stage 2 architecture page."""
    lang, e = cm["lang"], _esc
    V = V or (lambda s: e(s))
    o = ["<h2>%s</h2><p>%s</p>%s" % (e(T(lang, "b_title")), e(T(lang, "b_intro")), legend_html(lang))]
    o.append("<p>%s<br>%s</p>" % (e(T(lang, "b_course_asks", d=dist(cm["asks"], lang))), e(T(lang, "b_course_reach", d=dist(cm["reach"], lang)))))
    if cm["main"]:
        o.append("<h3>%s</h3><table>%s</table>" % (e(T(lang, "b_main_title")), "".join(
            "<tr><td>%s</td><td>%s</td><td>%s</td></tr>" % (e(x["id"]), V(x["text"]), badge(x["level"], lang)) for x in cm["main"])))
    o.append("<table><tr><th>%s</th><th>%s</th><th>%s</th><th>%s</th></tr>" % (
        e(T(lang, "module")), e(T(lang, "b_col_subs")), e(T(lang, "b_col_asks")), e(T(lang, "b_col_reach"))))
    for m in cm["modules"]:
        subs = " ".join("%s %s" % (e(s["id"]), badge(s["level"], lang)) for s in m["subs"]) or "—"
        gap = m["top"] and m["got"] is not None and m["got"] < m["top"]
        reach = (badge(m["got"], lang) + (' <span class="badge b-bad">%s</span>' % e(T(lang, "b_below")) if gap else
                                          ' <span class="badge b-ok">%s</span>' % e(T(lang, "b_fits")) if m["top"] else "")) if m["got"] else "—"
        o.append('<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>' % (e(m["n"]), subs, badge(m["top"], lang) if m["top"] else "—", reach))
    o.append("</table>")
    o.append(findings_html(cm["findings"], lang))
    return "\n".join(o)


def module_html(mm, V=None):
    """The Bloom card of a Stage 3 review page."""
    lang, e = mm["lang"], _esc
    if not mm["rows"]:
        return ""
    tot = len(mm["rows"])
    o = ['<div class="card"><h3>%s</h3><p class="note">%s</p>' % (e(T(lang, "b_title_module")), e(T(lang, "b_intro")))]
    o.append("<p><b>%s</b></p>" % e(T(lang, "b_now", pct="%.0f" % (100 * mm["share"]), min="%.0f" % (100 * mm["floor"]))))
    o.append("<table class=\"nums\">%s</table>" % "".join(
        '<tr><td>%s</td><td class="n">%d</td><td><span class="bbar" style="width:%dpx"></span></td></tr>' % (
            badge(n, lang), mm["counts"][n], int(160 * mm["counts"][n] / tot)) for n in sorted(LEVELS) if n < 6 or mm["counts"][n]))
    if mm["subs"]:
        o.append("<h4>%s</h4><table><tr><th>%s</th><th>%s</th><th>%s</th></tr>%s</table>" % (
            e(T(lang, "b_sub_title")), e(T(lang, "b_col_sub")), e(T(lang, "b_col_asks1")), e(T(lang, "b_col_check")), "".join(
                "<tr><td>%s</td><td>%s</td><td>%s %s</td></tr>" % (
                    e(s["id"]), badge(s["level"], lang), badge(s["best"], lang) if s["best"] else "—",
                    '<span class="badge %s">%s</span>' % (("b-ok", e(T(lang, "b_fits"))) if s["ok"] else ("b-bad", e(T(lang, "b_below")))))
                for s in mm["subs"])))
        if not mm["linked"]:
            o.append('<p class="note">%s</p>' % e(T(lang, "b_link_hint")))
    o.append(findings_html(mm["findings"], lang))
    o.append("</div>")
    return "\n".join(o)


def findings_html(found, lang):
    e = _esc
    if not found:
        return '<p class="note">%s</p>' % e(T(lang, "b_clean"))
    return '<div class="card"><h4>%s</h4><p class="note">%s</p><ul>%s</ul></div>' % (
        e(T(lang, "b_suggest_title")), e(T(lang, "suggestions_intro")), "".join("<li>%s</li>" % e(T(lang, k, **kw)) for k, kw in found))


def question_line(row, lang):
    """One line under a question on the review page: its level, and whether it was stated or estimated."""
    how = T(lang, "b_stated", why=row["why"]) if row["stated"] and row["why"] else (
        T(lang, "b_stated_plain") if row["stated"] else T(lang, "b_estimated"))
    return "%s — %s" % (level_name(row["level"], lang), how)


# ------------------------------------------------------------------ the command
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--course", required=True)
    ap.add_argument("--module", help="one module, from its content script; leave out for the whole course")
    x = ap.parse_args(argv)
    sys.path.insert(0, HERE)
    import workspace
    course = workspace.work_folder(x.course)
    rd = lambda n: json.load(io.open(workspace.claude_path(course, n), encoding="utf-8")) if os.path.isfile(workspace.claude_path(course, n)) else None
    prog, arch = rd("programme.json") or {}, rd("architecture.json")
    if x.module is None:
        if not arch:
            print("Stopped - there is no architecture yet (working_claude/architecture.json). The Bloom map of the course is made from it.")
            return 2
        cm = course_map(prog, arch)
        L = cm["lang"]
        print(T(L, "b_title"))
        print("  " + T(L, "b_course_asks", d=dist(cm["asks"], L)))
        print("  " + T(L, "b_course_reach", d=dist(cm["reach"], L)))
        for m in cm["modules"]:
            print("  %s %s: %s -> %s" % (T(L, "module"), m["n"], level_name(m["top"], L) if m["top"] else "?",
                                         level_name(m["got"], L) if m["got"] else "—"))
        found = cm["findings"]
    else:
        import content_script as cs
        p = cs.paths(course, x.module)["script"]
        if not os.path.isfile(p):
            print("Stopped - there is no content script for module %s yet:\n    %s" % (x.module, p))
            return 2
        script = json.load(io.open(p, encoding="utf-8"))
        am = next((m for m in (arch or {}).get("modules", []) if str(m.get("module")) == str(script.get("module"))), None)
        mm = module_map(script, am, prog, arch, mech=cs.mech, where=lambda sid: cs.place(script, sid))
        L = mm["lang"]
        print(T(L, "b_title_module"))
        print("  " + T(L, "b_now", pct="%.0f" % (100 * mm["share"]), min="%.0f" % (100 * mm["floor"])))
        print("  " + dist(mm["counts"], L))
        found = mm["findings"]
    if found:
        print("\n" + T(L, "b_suggest_title") + ":")
        for k, kw in found:
            print("  - " + T(L, k, **kw))
    else:
        print("\n" + T(L, "b_clean"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
