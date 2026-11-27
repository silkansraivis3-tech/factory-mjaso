#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""A module's skeleton, made by code before its script is written: the structure the structural checks ask for, with
every word field empty, so the writer only writes words.

    module_skeleton.py make  <course> --module 4 [--minutes 160] [--force] [--out F]   write working_claude/script/M04.json
    module_skeleton.py show  <course> --module 4 [--minutes 160]                       print the skeleton's outline, nothing written

WHAT IT HOLDS (theory-rules.json "skeleton" - every number is there)
From the approved ILO map (the module's Sub-ILOs, in order), the programme's hours (programme.json: theory and practical
hours x academic_hour_min) and the planners instructor_led.py plan uses (activity_formats.py: each Sub-ILO's task type and
formats; task_plan.py: each Sub-ILO's question mechanics and the module check's order):
  * the blocks in teaching order, block_size Sub-ILOs each, each closed by a self-check;
  * in a block, per Sub-ILO: plain theory slides with their minutes, words (on screen and in the notes) and picture slot,
    an active slide in the format the plan picked (a worked example where a task works something out); then the activity
    screens of the block in their planned formats, tagged with their Sub-ILOs, with the timing of their cycle; then the
    self-check's task slide and its questions - Part A, then Part B - in the planned mechanics, one on an earlier block from
    the second block on;
  * the team task after the self-check of the block with the highest Bloom level, where the module qualifies;
  * the recap, then the module check's task slide and its questions in the planned order;
  * minutes adding up exactly to the programme's: the practical hours on the activity screens, the theory hours on the
    slides and task slides.
Each screen carries "to_write": what its words are to say and how many. content_script.py check lists the empty word
fields as words to write (one must-fix) and holds back the checks that need those words until they are written; render
drops "to_write" from a written screen. Standard library only.
"""
from __future__ import annotations

import argparse
import io
import json
import math
import os
import sys
from collections import Counter
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import activity_formats as af  # noqa: E402
import bloom_map  # noqa: E402
import content_script as cs  # noqa: E402
import course_gate  # noqa: E402
import ilo_map  # noqa: E402
import instructor_led as il  # noqa: E402
import task_plan  # noqa: E402
import workspace  # noqa: E402

SK = cs.RULES["skeleton"]
DENSITY = cs.RULES["module"]["min_words_per_theory_minute"]
NOTES = cs.RULES["notes"]
SC_RULES = cs.RULES["self_check"]
MEDIA = cs.MEDIA["mechanics"]

# the slide formats a skeleton writes, and the fields each one's words go in (activity_formats "slide_active")
SLIDE_FORMATS = {
    "worked-example": {"active": "worked-example", "fields": ("text", "ask", "reveal")},
    "case-dilemma": {"active": "scenario", "fields": ("text", "ask", "choices", "why", "right")},
    "predict-reveal": {"active": "predict-then-reveal", "fields": ("text", "ask", "reveal")},
    "explain-why": {"active": "explain-then-reveal", "fields": ("text", "ask", "reveal")},
    "refutation": {"claim_is": "false", "fields": ("claim", "text")},
}
WORKS_EXAMPLE = ("worked-example", "case-dilemma", "predict-reveal", "explain-why")   # content_script.worked_example
SECOND_FORMATS = ("explain-why", "case-dilemma", "predict-reveal", "refutation")
HANDS = ("fixed_sequence", "real_time_judgement")


# ------------------------------------------------------------------ inputs
def module_minutes(course, module):
    """(theory, practical) minutes of the module from programme.json, or None"""
    _, prog, _ = il.course_files(course)
    hour = (prog or {}).get("academic_hour_min")
    topic = ((prog or {}).get("topics") or {}).get(str(ilo_map.mkey(module)))
    if not hour or not isinstance(topic, dict):
        return None
    h = lambda k: float(topic.get(k) or 0)
    return int(round(h("theory") * hour)), int(round(h("practical") * hour))


def _split(total, n, lo=0):
    """n whole numbers adding up to total, as even as can be"""
    if n <= 0:
        return []
    base, extra = divmod(int(total), n)
    return [max(lo, base + (1 if i < extra else 0)) for i in range(n)]


def _mechanic_q(m, sid, set_id, kind, part, n):
    """a question screen with its mechanic and empty words"""
    q = {"id": n, "kind": kind, "set": set_id, "sub_ilo": sid, "mechanic": m, "question": ""}
    if cs.uses({"mechanic": m}, "options"):
        q.update(options=[], correct="")
    if cs.uses({"mechanic": m}, "values"):
        q["values"] = ""
    if cs.uses({"mechanic": m}, "answer"):
        q["answer"] = ""
    if cs.uses({"mechanic": m}, "visual"):
        q.update(visual_kind="photo", visual="", picture={"kind": "photo", "aspect": "4:3", "shows": ""})
    q.update(feedback="", brief="")
    if kind == "module-check":
        q["graded"] = False
    how = (MEDIA.get(m) or {}).get("answer")
    q["to_write"] = "%s on %s (%s): %s%s; \"feedback\" what the trainee sees after answering; \"brief\" one line on why a " \
                    "wrong answer is not right, never which is." % (
                        task_plan.label(m), sid, part, "\"question\" one ask", ("; \"answer\": " + how) if how else "")
    return q


# ------------------------------------------------------------------ the plan
def _plan(course, module, write=False):
    out = il.plan(course, module, write=write)
    if not out:
        return None
    mid, rows, mc = out[0]
    m = ilo_map.read(course)
    raw = {str(r.get("sub_ilo_id")): r for r in il.leaf_rows(m, mid)}
    return mid, rows, mc, raw


def _needs_practice(course, module, rows, raw, lang):
    """the Sub-ILOs an activity screen must be tagged with: doing ones (Apply or higher, the outcome review's level first -
    content_script i_not_practised) and those whose task type a slide does not train (a_type_unserved)"""
    settled = course_gate.settled_levels(course, module)
    stub = {"course_language": lang}
    need = []
    for p in rows:
        r = raw.get(p["sid"]) or {"sub_ilo": p["text"]}
        lv = cs.doing_level(dict(r, bloom=settled[p["sid"]]) if p["sid"] in settled else r, stub)
        if lv or p["task_type"] != "decision":
            need.append(p["sid"])
    return need


def _activity_format(p, used, experienced):
    """an activity format for the Sub-ILO: its own pick first, then its task type's, the least used in the module"""
    picks = [k for k in p["picks"] if af.FORMATS.get(k, {}).get("drafts") == "activity"]
    pool = [k for k in af.ORDER if af.FORMATS[k]["drafts"] == "activity" and af.FORMATS[k]["task_type"] == p["task_type"]
            and af._allowed(af.FORMATS[k], p["text"], experienced)]
    if p["task_type"] == "decision":
        pool += [k for k in af.ORDER if af.FORMATS[k]["drafts"] == "activity" and k not in pool
                 and af._allowed(af.FORMATS[k], p["text"], experienced) and not af.FORMATS[k].get("team")]
    cands = picks + [k for k in pool if k not in picks]
    return (min(cands, key=lambda k: (af.FORMATS[k]["task_type"] != p["task_type"], used[k], cands.index(k))) if cands
            else af.UNNAMED["key"])


def _slide_format(p, need_example):
    """the active slide of a Sub-ILO: the slide format the plan picked; a worked example where a task works something out
    and the pick does not work one with the room; None where neither"""
    picks = [k for k in p["picks"] if k in SLIDE_FORMATS]
    if need_example:
        good = [k for k in picks if k in WORKS_EXAMPLE]
        return good[0] if good else "worked-example"
    return picks[0] if picks else None


def _second_format(p, first):
    """a second active slide for a Sub-ILO with much theory: another slide format the plan picked, else the next of
    SECOND_FORMATS - never the first's"""
    picks = [k for k in p["picks"] if k in SLIDE_FORMATS and k != first]
    rest = [k for k in SECOND_FORMATS if k != first]
    return (picks + rest)[0] if picks + rest else None


def course_groups(course, module):
    """the course's groups of trainees ("groups" at the top of its other modules' scripts), or None"""
    d = os.path.dirname(cs.paths(course, module)["script"])
    for n in sorted(os.listdir(d)) if os.path.isdir(d) else []:
        if il.SCRIPT_FILE.match(n) and n != cs.mid(module) + ".json":
            try:
                g = cs.load(os.path.join(d, n)).get("groups")
            except (OSError, ValueError):
                continue
            if isinstance(g, dict) and len(g) >= 2:
                return g
    return None


def build(course, module, minutes=None, write_register=False, with_groups=True):
    """the skeleton script (dict), or raise ValueError with what is missing. write_register: the plan's task types and TLA
    names go into instructor_led.json's register where it has none, as instructor_led.py plan does"""
    got = _plan(course, module, write_register)
    if not got:
        raise ValueError("no Sub-ILOs for module %s in the ILO map (working_claude/ilo_map.json)" % module)
    mid, rows, mc_plan, raw = got
    arch, prog, _ = il.course_files(course)
    cinfo = arch.get("course") or {}
    lang_name = cinfo.get("course_language") or "English"
    lang = bloom_map.lang_code(lang_name)
    exp = il.experienced(arch)
    if minutes:
        theory, practical = int(minutes), 0
    else:
        mm = module_minutes(course, module)
        if not mm:
            raise ValueError("no hours for module %s in programme.json - give --minutes" % module)
        theory, practical = mm
    alloc = theory + practical
    by_sid = {p["sid"]: p for p in rows}
    n_sub = len(rows)

    # -- the questions: each Sub-ILO's planned self-check mechanic, blocks of block_size, filled to a self-check's size
    bs = max(1, int(SK["block_size"]))
    if theory / float(n_sub) >= SK["block_alone_from_minutes"]:      # much theory a Sub-ILO: a self-check after each one
        bs = 1
    blocks = [rows[i:i + bs] for i in range(0, n_sub, bs)]
    if len(blocks) > 1 and len(blocks[-1]) < bs:          # a short last block joins the one before
        last = blocks.pop()
        blocks[-1] = blocks[-1] + last
    used_m = Counter(p["questions"]["self_check"] for p in rows if p["questions"]["self_check"])
    used_m.update(s["mechanic"] for s in mc_plan)
    used_f = Counter(task_plan.family(m) for m in used_m.elements())
    level = lambda m: bloom_map.task_level(m)["level"]

    def pick(p, lv, avoid=(), rich=False, avoid_fam=None):
        u = Counter(used_m)
        for m in avoid:
            u[m] += 99
        m = task_plan._pick(lv, p["task_type"], u, used_f, avoid_fam=avoid_fam, rich=rich)
        if m:
            used_m[m] += 1
            used_f[task_plan.family(m)] += 1
        return m

    # the level each Sub-ILO is checked and practised at (the outcome review's where it settled one - bloom_map B5)
    lv_of = {s["id"]: s["level"] for s in cs.bloom_of(course, {"module": ilo_map.mkey(module), "screens": []})["subs"]
             if s.get("level")}
    want = {p["sid"]: min(lv_of.get(p["sid"]) or p["level"], 5) for p in rows}

    def reach(p, avoid=(), avoid_fam=None, rich=False, fams=()):
        """a mechanic that reaches the Sub-ILO's level (its typical level), of the families its task type prefers - the
        family least in fams (the set's other questions) first"""
        prefer = task_plan.TP["by_task_type"].get(p["task_type"]) or task_plan.TP["by_task_type"]["decision"]
        cands = [m for m in task_plan._pool(p["task_type"]) if task_plan.LEVELS[m]["typical"] >= want[p["sid"]]
                 and m not in avoid and task_plan.family(m) != avoid_fam and (not rich or cs.rich_task({"mechanic": m}))]
        if not cands:
            return None
        fams = Counter(fams)
        rank = lambda m: prefer.index(task_plan.family(m)) if task_plan.family(m) in prefer else len(prefer)
        m = min(cands, key=lambda m: (fams[task_plan.family(m)], used_m[m] + used_f[task_plan.family(m)], rank(m),
                                      task_plan.LEVELS[m]["typical"] - want[p["sid"]], task_plan.ORDER.index(m)))
        used_m[m] += 1
        used_f[task_plan.family(m)] += 1
        return m

    mc = [(s["sid"], s["mechanic"]) for s in mc_plan]
    for i, (sid, m) in enumerate(mc):                        # the module check reaches each Sub-ILO's level (b_sub_unchecked)
        if level(m) < want[sid] and not any(x == sid and level(y) >= want[sid] for x, y in mc):
            sc = by_sid[sid]["questions"]["self_check"]
            m2 = reach(by_sid[sid], avoid=[y for _, y in mc], avoid_fam=task_plan.family(sc) if sc else None,
                       fams=[task_plan.family(y) for k, (_, y) in enumerate(mc) if k != i])
            if m2:
                mc[i] = (sid, m2)
    for p in rows:                                           # the self-check practises it at that level (b_sub_unpractised)
        sc = p["questions"]["self_check"]
        if not sc or level(sc) < want[p["sid"]]:
            m2 = reach(p, avoid_fam=task_plan.family(dict(mc).get(p["sid"], "")) or None)
            if m2:
                p["questions"]["self_check"] = m2
    order = task_plan.spread([task_plan.family(m) for _, m in mc])
    mc = [mc[i] for i in order] if order else mc

    def is_rich(m):
        return cs.rich_task({"mechanic": m})

    def is_basic(m):
        return not is_rich(m) and task_plan.family(m) in SC_RULES["basic_families"]

    sc_sets, earlier = [], []
    for b in blocks:
        qs = [(p["sid"], p["questions"]["self_check"]) for p in b if p["questions"]["self_check"]]
        if earlier:                                          # a quick Part A on an earlier block (t_not_spaced)
            e = earlier[-1]
            quick = [m for m in task_plan._pool(e["task_type"]) if task_plan.LEVELS[m]["typical"] <= 2
                     and m not in [x for _, x in qs]]
            if quick:
                m = min(quick, key=lambda m: (used_m[m] + used_f[task_plan.family(m)], is_basic(m), task_plan.ORDER.index(m)))
                used_m[m] += 1
                used_f[task_plan.family(m)] += 1
                qs.append((e["sid"], m))
        top = max(b, key=lambda p: p["level"])
        while len(qs) < SC_RULES["min_questions"]:
            m = (reach(top, avoid=[x for _, x in qs], rich=True, fams=[task_plan.family(x) for _, x in qs])
                 or pick(top, max(3, top["level"]), avoid=[x for _, x in qs], rich=True))
            if not m:
                break
            qs.append((top["sid"], m))
        n = len(qs)
        need = min(SC_RULES["rich_min"], max(0, n - SC_RULES["basic_max"]))
        for i in range(n):                                   # the mix: at most basic_max basic, enough rich (t_sc_mix)
            basic = sum(is_basic(m) for _, m in qs)
            rich = sum(is_rich(m) for _, m in qs)
            if basic <= SC_RULES["basic_max"] and rich >= need:
                break
            # a basic one first, then one below its Sub-ILO's level - never the question that reaches the level
            js = [k for k in range(n - 1, -1, -1) if not is_rich(qs[k][1])]
            js = sorted(js, key=lambda k: (not is_basic(qs[k][1]), level(qs[k][1]) >= want[qs[k][0]]))
            if not js:
                break
            j = js[0]
            sid = qs[j][0]
            m = pick(by_sid[sid], max(3, by_sid[sid]["level"]), avoid=[x for _, x in qs], rich=True)
            if m:
                qs[j] = (sid, m)
        fams = [task_plan.family(m) for _, m in qs]
        parts = [int(level(m) >= 3) for _, m in qs]
        order = task_plan.spread(fams, parts) or sorted(range(n), key=lambda i: parts[i])
        sc_sets.append([qs[i] for i in order])
        earlier += b

    team = None
    tops = [p for p in rows if p["level"] >= task_plan.TP["challenge_from_level"]]
    if alloc >= cs.RULES["team_task"]["from_module_minutes"] and tops:
        top = max(tops, key=lambda p: p["level"])
        bi = next(i for i, b in enumerate(blocks) if top in b)
        others = [p for p in blocks[bi] if p is not top] or [top]
        tq = []
        for p in ([top] + others * SK["team_questions"])[:SK["team_questions"]]:
            af_ = task_plan.family(tq[-1][1]) if tq else None
            m = (reach(p, avoid=[x for _, x in sc_sets[bi]] + [x for _, x in tq], rich=True, avoid_fam=af_)
                 or reach(p, avoid=[x for _, x in tq], rich=True, avoid_fam=af_)
                 or reach(p, avoid=[x for _, x in tq], avoid_fam=af_)
                 or pick(p, max(3, p["level"]), avoid=[x for _, x in sc_sets[bi]] + [x for _, x in tq], rich=True,
                         avoid_fam=task_plan.family(tq[-1][1]) if tq else None))
            if m:
                tq.append((p["sid"], m))
        if tq:
            team = (bi, tq)
    allq = [m for st in sc_sets for _, m in st] + [m for _, m in (team[1] if team else [])] + [m for _, m in mc]
    if not any((MEDIA.get(m) or {}).get("hands_on") for m in allq) and mc:        # m_no_hands_on
        top = max(rows, key=lambda p: p["level"])
        hands = [m for m in task_plan.ORDER if (MEDIA.get(m) or {}).get("hands_on") and m in task_plan._pool(top["task_type"])]
        k = next(i for i, (sid, _) in enumerate(mc) if sid == top["sid"])
        mc[k] = (top["sid"], min(hands, key=lambda m: (used_m[m], abs(level(m) - top["level"]))))

    # -- which Sub-ILOs work something out (t_no_worked_example) and which need an activity (i_not_practised, a_type_unserved)
    works = {sid for st in sc_sets + [team[1] if team else [], mc] for sid, m in st
             if cs.works_it_out({"mechanic": m})}
    need = _needs_practice(course, module, rows, raw, lang)
    active = {p["sid"]: _slide_format(p, p["sid"] in works) for p in rows}
    n_active = sum(1 for f in active.values() if f)
    # one activity a block, tagged with its Sub-ILOs that need one - one for each task type that is not a decision
    groups = []                                              # [block index, [rows]]
    for bi, b in enumerate(blocks):
        by_tt = {}
        for p in b:
            if p["sid"] in need:
                by_tt.setdefault(p["task_type"], []).append(p)
        groups += [[bi, ps] for ps in by_tt.values()]
    if practical and not groups:                             # practical hours and nothing that needs one: the highest
        top = max(rows, key=lambda p: p["level"])
        groups = [[next(i for i, b in enumerate(blocks) if top in b), [top]]]
    # the practical hours pay for the active slides too, where the activities keep their least
    act_total = practical - n_active * SK["active_slide_minutes"]
    if act_total < SK["activity_min_minutes"] * max(1, len(groups)):
        act_total = practical
    if not practical:
        act_total = SK["activity_minutes_from_theory"] * len(groups)
    while groups and act_total / float(len(groups)) > SK["activity_max_minutes"]:    # a long one is split by Sub-ILO
        g = max((g for g in groups if len(g[1]) > 1), key=lambda g: len(g[1]), default=None)
        if not g:
            break
        groups.insert(groups.index(g) + 1, [g[0], g[1][1:]])
        g[1] = g[1][:1]
    used_f2 = Counter()
    acts = []                                                # [block index, [sids], format]
    for bi, ps in groups:
        f = _activity_format(max(ps, key=lambda p: p["level"]), used_f2, exp)
        used_f2[f] += 1
        acts.append([bi, [p["sid"] for p in ps], f])
    act_min = _split(act_total, len(acts)) if acts else []
    theory_left = alloc - sum(act_min)

    # -- the slides' minutes
    sc_min = [len(st) * SC_RULES["minutes_per_question"] + SK["task_slide_extra_minutes"] for st in sc_sets]
    mc_min = len(mc) * cs.RULES["module_check"]["minutes_per_question"] + SK["task_slide_extra_minutes"]
    fixed = sum(sc_min) + mc_min + SK["recap_minutes"] + (SK["team_minutes"] if team else 0)
    plain_total = lambda: theory_left - fixed - sum(1 for f in active.values() if f) * SK["active_slide_minutes"]
    want = n_sub * SK["plain_slide_min_minutes"]
    while plain_total() < want and act_min and max(act_min) > SK["activity_min_minutes"]:   # the activities lend minutes
        act_min[act_min.index(max(act_min))] -= 1
        theory_left += 1
    for p in reversed(rows):                                # then the active slides no task needs go
        if plain_total() >= want:
            break
        if active[p["sid"]] and p["sid"] not in works:
            active[p["sid"]] = None
    plain_total = plain_total()
    if plain_total < want:
        raise ValueError("module %s: %d minutes leave %d for the theory slides of %d Sub-ILOs - too few (theory %d, practical "
                         "%d, tasks %d)" % (module, alloc, plain_total, n_sub, theory, practical, fixed))
    plain_per = _split(plain_total, n_sub)
    second = {}                       # much theory a Sub-ILO: past the cap, a second active slide, the rest to the activities
    cap = SK["plain_max_per_sub_ilo"]
    if act_min and any(x > cap for x in plain_per):
        spare = 0
        for i, p in enumerate(rows):
            if plain_per[i] <= cap:
                continue
            spare += plain_per[i] - cap
            plain_per[i] = cap
            f2 = _second_format(p, active[p["sid"]])
            if f2 and spare >= SK["active_slide_max_minutes"]:
                second[p["sid"]] = f2
                spare -= SK["active_slide_max_minutes"]
        for j, x in enumerate(_split(spare, len(act_min))):
            act_min[j] += x

    # -- the screens
    screens, ids = [], Counter()

    def nid(prefix):
        ids[prefix] += 1
        return "%s%02d" % (prefix, ids[prefix])

    def plain_slide(p, i, k, mins, points):
        words = int(math.ceil(DENSITY * mins / 5.0) * 5) + 5
        text = min(SK["text_words"], max(10, words - NOTES["min_words"]))
        notes = max(NOTES["min_words"], min(NOTES["max_words"], words - text))
        photo = i % 2 == 0 or rows.index(p) % 2 == 0 or p["task_type"] in HANDS    # real photographs first (L52)
        fig = SK["figure_kinds"][sum(1 for x in screens if (x.get("picture") or {}).get("kind") == "figure") % len(SK["figure_kinds"])]
        s = {"id": nid("s"), "kind": "slide", "sub_ilo": p["sid"], "title": "", "text": ""}
        if points:
            s["points"] = ""
        s.update({"visual_kind": "photo" if photo else fig, "visual": "",
                  "picture": {"kind": "photo" if photo else "figure", "aspect": "4:3", "shows": ""}, "layout": "split",
                  "notes": "", "minutes": mins})
        s["to_write"] = ("Teach %s (%d of %d): %s - about %d words in \"text\"%s; \"notes\" about %d words, Say: / Ask: / Show: "
                         "lines; the picture: %s (\"visual\", and \"shows\" in the slot)." % (
                             p["sid"], i + 1, k, (p["text"] or "")[:120], text,
                             ", the same in 2-6 short \"points\" for the screen" if points
                             else " - on screen as written, no \"points\" (the slide before has them)",
                             notes, "a real photograph" if photo else "a figure (schematic, chart, comparison or animation)"))
        return s

    def active_slide(p, f, mins=SK["active_slide_minutes"]):
        spec = SLIDE_FORMATS[f]
        s = {"id": nid("s"), "kind": "slide", "sub_ilo": p["sid"], "title": ""}
        if spec.get("active"):
            s["active"] = spec["active"]
        for fld in spec["fields"]:
            s[fld] = ""
        if spec.get("claim_is"):
            s["claim_is"] = spec["claim_is"]
        s.update(visual_kind="none", visual="", picture={"kind": "none"}, layout="split", notes="", minutes=mins)
        s["to_write"] = "%s on %s (%s): %s; \"notes\" about %d words - what the trainees do first." % (
            af.label(f), p["sid"], f, af.FORMATS[f]["write"], SK["active_notes_words"])
        return s

    def task_slide(set_id, qs, mins, team_t=None):
        s = {"id": nid("t"), "kind": "task-slide", "opens": set_id, "title": "", "text": ""}
        if team_t:
            s["team"] = {"size": "3", "roles": list(cs.RULES["team_task"]["roles"]), "scope": "team"}
        elif set_id.startswith("SC"):
            s["before"] = ""
        s.update(notes="", minutes=mins)
        what = ("a team task on %s - one answer per team" % ", ".join(sorted({x for x, _ in qs})) if team_t else
                "the module check" if set_id == "MC" else "self-check %s on %s" % (set_id[2:], ", ".join(sorted({x for x, _ in qs}))))
        s["to_write"] = ("Opens %s (%s): \"text\" says only that a task starts now and what it is about%s; \"notes\" Say: how it "
                         "runs, Ask: the debrief question." % (set_id, what, "; \"before\" 2-4 things to check, one a line"
                                                               if "before" in s else ""))
        return s

    grp = course_groups(course, module) if with_groups else None

    def emit(set_id, kind, qs, part, prefix):
        """a set's questions; with groups of trainees its last one is written once for each group (every group has a
        question of its own in every set - script/GUIDE.md "Groups of trainees")"""
        for j, (sid, m) in enumerate(qs):
            if grp and j == len(qs) - 1:
                for g, name in grp.items():
                    q = _mechanic_q(m, sid, set_id, kind, part(m), nid(prefix))
                    q["group"] = g
                    q["to_write"] = ("Only for %s: the same task, its case from their work (where the subject does not differ "
                                     "for the groups, keep one version for everyone - no \"group\" - and remove the other). "
                                     % name + q["to_write"])
                    screens.append(q)
            else:
                screens.append(_mechanic_q(m, sid, set_id, kind, part(m), nid(prefix)))

    for bi, b in enumerate(blocks):
        for p in b:
            mins = plain_per[rows.index(p)]
            k = max(1, int(math.ceil(mins / float(SK["plain_slide_max_minutes"]))))
            each = _split(mins, k)
            f = active[p["sid"]]
            for i in range(k):
                prev = screens[-1] if screens else {}
                pts = not (prev.get("kind") == "slide" and "points" in prev)
                screens.append(plain_slide(p, i, k, each[i], pts))
                if f and i == 0:
                    screens.append(active_slide(p, f))
                if p["sid"] in second and i == min(1, k - 1):
                    screens.append(active_slide(p, second[p["sid"]], SK["active_slide_max_minutes"]))
        for (abi, sids, fmt), mins in zip(acts, act_min):
            if abi != bi:
                continue
            fd = af.get(fmt)
            rows_, _ = af.cycle(mins, team=bool(fd.get("team")), runs=bool(fd.get("runs")), diagnostic=exp)
            a = {"id": nid("a"), "kind": "activity", "title": "", "format": fmt, "sub_ilo": sids if len(sids) > 1 else sids[0],
                 "minutes": mins, "text": "", "roles": "", "safety": "", "observe": ""}
            if fmt == "scenario-run":
                a["events"] = ""
            a.update(visual_kind="none", visual="", notes="")
            a["to_write"] = ("%s on %s [%s]: %s. \"text\" what the trainees do, step by step, on the module's running case; "
                             "\"roles\", \"safety\", \"observe\" one line each; \"notes\" Say: the timing - %s." % (
                                 af.label(fmt), ", ".join(sids), fmt, fd.get("write") or "",
                                 ", ".join("%s %s" % (r["kind"], r["min"]) for r in rows_)))
            screens.append(a)
        set_id = "SC%d" % (bi + 1)
        screens.append(task_slide(set_id, sc_sets[bi], sc_min[bi]))
        emit(set_id, "self-check", sc_sets[bi], lambda m: "Part B" if level(m) >= 3 else "Part A", "q")
        if team and team[0] == bi:
            screens.append(task_slide("TT1", team[1], SK["team_minutes"], team_t=True))
            emit("TT1", "self-check", team[1], lambda m: "team task", "q")
    screens.append({"id": nid("s"), "kind": "slide", "recap": True, "title": "What to take away", "text": "", "asks": "",
                    "visual_kind": "none", "visual": "", "notes": "", "minutes": SK["recap_minutes"],
                    "to_write": "The recap: 3-6 lines, one a line, \"Short title - one sentence\", 24 words or fewer, the "
                                "module's main points in the words its slides used; \"asks\" one question for each line."})
    screens.append(task_slide("MC", mc, mc_min))
    emit("MC", "module-check", mc, lambda m: "module check", "m")
    got_min = sum(cs.minutes(s) for s in screens if s.get("kind") in cs.INSTRUCTOR)
    assert got_min == alloc, (got_min, alloc)
    topic = ((prog or {}).get("topics") or {}).get(str(ilo_map.mkey(module))) or {}
    return {"module": ilo_map.mkey(module), "title": topic.get("title") or "", "course_language": lang_name,
            "operator_language": cinfo.get("operator_language") or "en", "status": "draft", "minutes_allocated": alloc,
            "operator_facts": [], "sources": [], **({"groups": grp} if grp else {}),
            "skeleton": {"made": date.today().isoformat(), "theory_minutes": theory, "practical_minutes": practical,
                         "blocks": [[p["sid"] for p in b] for b in blocks]},
            "screens": screens}


def outline(script):
    """one line a screen: id, kind, Sub-ILO, minutes, format or mechanic"""
    out = []
    for s in script["screens"]:
        out.append("  %-4s %-12s %-14s %4s  %s" % (
            s["id"], s["kind"], ",".join(cs.sub_ilos_of(s)) or s.get("opens") or "", cs.minutes(s) if s["kind"] in cs.INSTRUCTOR else "",
            s.get("format") or s.get("active") or ("claim" if "claim" in s else "") or s.get("mechanic") or
            ("recap" if s.get("recap") else "") or ("team" if s.get("team") else "") or (s.get("picture") or {}).get("kind", "")))
    return "\n".join(out)


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("cmd", choices=("make", "show"))
    ap.add_argument("course")
    ap.add_argument("--module", required=True)
    ap.add_argument("--minutes", type=int, help="the module's minutes, where programme.json has no hours for it")
    ap.add_argument("--force", action="store_true", help="write over a script that is there (it is kept in script/old)")
    ap.add_argument("--out")
    ap.add_argument("--no-groups", action="store_true", help="no versions per group, though the course's other modules have groups")
    o = ap.parse_args(argv)
    course = workspace.work_folder(o.course, create=False)
    if not ilo_map.read(course):
        print("No ILO map yet (working_claude/ilo_map.json) - the skeleton is made from its Sub-ILOs")
        return 2
    try:
        script = build(course, o.module, o.minutes, write_register=o.cmd == "make", with_groups=not o.no_groups)
    except ValueError as e:
        print(str(e))
        return 2
    sk = script["skeleton"]
    head = ("%s - %d min (theory %d, practical %d), blocks %s" % (
        cs.mid(o.module), script["minutes_allocated"], sk["theory_minutes"], sk["practical_minutes"],
        " | ".join(", ".join(b) for b in sk["blocks"])))
    if o.cmd == "show":
        print(head + "\n" + outline(script))
        return 0
    p = o.out or cs.paths(course, o.module)["script"]
    if os.path.isfile(p) and not o.force and not o.out:
        print("%s is there already - the skeleton is for a module not yet written: --force keeps the old one in script/old "
              "and writes the skeleton, --out F writes it beside it" % p)
        return 2
    if os.path.isfile(p) and not o.out:
        old = cs.paths(course, o.module)["old"]
        os.makedirs(old, exist_ok=True)
        stem = os.path.splitext(os.path.basename(p))[0]
        io.open(cs.archive_name(old, stem, ".json"), "w", encoding="utf-8").write(
            io.open(p, encoding="utf-8").read())
    cs.save(p, script)
    print("Wrote %s\n%s\nWrite the words into its empty fields (\"to_write\" on each screen says what), then run "
          "content_script.py check." % (p, head))
    return 0


if __name__ == "__main__":
    sys.exit(main())
