#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ILO elevation - every learning outcome raised or kept on purpose, one outcome at a time (2.142.0).

The method behind the experts' learning-outcome review (pedagogy_review.py; L69). Its rules are data:
knowledge/ilo-elevation.json - the pedagogy lead's ILO Elevation spec, with the three frameworks above it (the task of an
outcome is a TLA of the TLA Pool; a revised outcome is written with the Bloom Verb Guide's verbs).

WHY THIS EXISTS
Judged as a whole course, the outcomes were grouped, more than half were quietly left where they were, the same
activities came back everywhere and a raised outcome was re-written from scratch. So here the CODE does everything that
is counting, looping, checking and deciding what is complete; the judgement is one small answer about one outcome:

  * one outcome, one result - the answer is attached to its outcome by code (pedagogy_review.py propose / task);
  * raise is the default - a raise lands on Apply or higher, a keep needs a keep code allowed for the original level
    and a reason, and a raise needs one sentence saying what the learner does at the new level (the honesty test);
  * the rewrite is the verb and a minimal fit - seven checks (ilo-elevation.json "checks"): the verb of the level's
    list, every number and abbreviation kept and none added, most of the content words kept, hardly any longer;
  * one TLA of the pool per outcome at its final level, with variety enforced in syllabus order: not the TLA of either
    of the two outcomes before, and none holding more than 15 % of the course once 20 outcomes have tasks.

This file is the checks and the counts. It writes nothing. Standard library only.
"""
from __future__ import annotations

import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import bloom_map  # noqa: E402
import activity_formats as af  # noqa: E402
import workspace  # noqa: E402

E = json.load(io.open(os.path.join(SKILL, "knowledge", "ilo-elevation.json"), encoding="utf-8"))
RAISE = sorted(int(k) for k in E["raise_levels"] if not k.startswith("_"))
CODES = {k: v for k, v in E["keep_codes"].items() if not k.startswith("_")}
WRITE = {int(k): v for k, v in E["write_verbs"].items() if not k.startswith("_")}
CK = E["checks"]
TASK = E["task"]
VAR = TASK["variety"]
FITS = [k for k in TASK["fit"]]
SMALL = set(CK["small_words"])
METHOD = "elevation"                   # pedagogy_review.json "method": a review judged by this file
WAIVABLE = (5, 6, 7)                   # the content checks a row's "attention" may hand to the expert; 1-4 never


def _filled(x):
    return isinstance(x, str) and bool(x.strip())


def level(n):
    return "%d %s" % (n, bloom_map.level_name(n, "en")) if isinstance(n, int) and 1 <= n <= 6 else "-"


# ------------------------------------------------------------------ the verb a raised outcome starts with
def third_person(v):
    """carry out -> carries out; analyse -> analyses (and analyzes); find the cause of -> finds the cause of"""
    head, _, tail = v.partition(" ")
    if re.search(r"[^aeiou]y$", head):
        heads = [head[:-1] + "ies"]
    elif re.search(r"(s|x|z|ch|sh|o)$", head):
        heads = [head + "es"]
    else:
        heads = [head + "s"]
    heads += [h.replace("yses", "yzes").replace("ises", "izes") for h in heads if re.search(r"(yses|ises)$", h)]
    return [h + ((" " + tail) if tail else "") for h in dict.fromkeys(heads)]


def lead_verb(text, lvl=None):
    """(verb, its level) - the verb of "write_verbs" an outcome starts with, in the third person; of one level's list
    when lvl is given. ("", None) when it starts with none."""
    low = (text or "").strip().lower()
    for n in ([lvl] if lvl else sorted(WRITE)):
        for v in sorted(WRITE.get(n, []), key=len, reverse=True):
            for form in third_person(v):
                if re.match(re.escape(form).replace(r"\ ", r"\s+") + r"(?!\w)", low):
                    return v, n
    return "", None


def verbs_for(lvl):
    """'Differentiates, Traces, ...' - the verbs of one level as an outcome starts with them"""
    return ", ".join(third_person(v)[0].capitalize() for v in WRITE.get(lvl, []))


# ------------------------------------------------------------------ what a rewrite must keep
_NUM = re.compile(r"\d+(?:[.,]\d+)*")
_ABBR = re.compile(r"\b[A-Z][A-Z0-9]{1,}\b")
_WORD = re.compile(r"[a-z][a-z'\-]*")


def marks(text):
    """The numbers and the capitalised abbreviations of a text: 19, 21, MARVS, ESD, IGC, CH4"""
    return set(_NUM.findall(text or "")) | set(_ABBR.findall(text or ""))


def _stem(w):
    w = w.strip("'-")
    for suf in ("'s", "ing", "ies", "es", "ed", "s"):
        if w.endswith(suf) and len(w) - len(suf) >= 3:
            return w[:-len(suf)] + ("y" if suf == "ies" else "")
    return w


def content_words(text):
    """The content words of an outcome, each once, as stems - without its leading verb and the small words"""
    words = _WORD.findall((text or "").lower())
    return {_stem(w) for w in words[1:] if w not in SMALL and len(w) > 1}


def n_words(text):
    return len((text or "").split())


# ------------------------------------------------------------------ one outcome proposal
def allowed_codes(orig):
    return [k for k, v in CODES.items() if orig in v["levels"]]


def outcome_problems(original, orig, p, main=False, comparable=True):
    """[(check number, words)] - the checks of ilo-elevation.json "checks" one outcome proposal fails; [] when it passes.
    original: the outcome's own wording; orig: its Bloom level; p: the proposal (decision, level, keep_codes, why, does,
    revised_outcome). main: a Main ILO, never re-worded (L2). comparable False: the original is in another language and
    has no English rendering - the wording checks 5-7 cannot be made."""
    d = p.get("decision")
    if d not in ("raise", "keep"):
        return [(1, "no decision - every outcome is raised or kept (\"decision\": \"raise\" or \"keep\"); the default is raise")]
    if not (isinstance(orig, int) and 1 <= orig <= 6):
        return [(1, "the level of the original outcome is not known - its verb is not in the list; say it "
                    "(\"original_level\": 1-6 on the row), then decide")]
    out, lvl, rw = [], p.get("level"), (p.get("revised_outcome") or "").strip()
    if d == "keep":
        codes = [str(c).strip().upper() for c in p.get("keep_codes") or []]
        ok = allowed_codes(orig)
        if not codes:
            out.append((2, "kept without a keep code - at %s one of: %s" % (level(orig), "; ".join("%s (%s)" % (c, CODES[c]["means"]) for c in ok))))
        for c in codes:
            if c not in CODES:
                out.append((2, "%r is not a keep code - one of: %s" % (c, ", ".join(ok))))
            elif c not in ok:
                out.append((2, "%s (%s) is not allowed for an outcome at %s - there: %s" % (c, CODES[c]["means"], level(orig), ", ".join(ok))))
        if not _filled(p.get("why")):
            out.append((2, "kept without a reason ('why') - one or two sentences, about this outcome"))
        if rw:
            out.append((2, "a kept outcome keeps its wording, character for character - empty 'revised_outcome'"))
        if isinstance(lvl, int) and lvl != orig:
            out.append((2, "a kept outcome stays at its level (%s), not %s - a level is never lowered, and a higher one is a raise" % (level(orig), level(lvl))))
        return out
    if not (isinstance(lvl, int) and RAISE[0] <= lvl <= 6 and lvl > orig):
        out.append((3, "a raise lands on Apply, Analyse, Evaluate or Create and above the original (%s) - not %s; Remember to "
                       "Understand is not a raise" % (level(orig), level(lvl))))
        return out
    if not _filled(p.get("does")):
        out.append((3, "a raise says in one sentence what the learner does with this content at %s ('does') - the honesty test; "
                       "if it needs content the outcome does not contain, keep it" % level(lvl)))
    if main:
        return out                     # a Main ILO is never re-worded: its raise is the level and the task (L2)
    if not rw:
        return out + [(4, "a raise carries the re-worded outcome ('revised_outcome'): the verb changed, the content in the original words")]
    v, _ = lead_verb(rw, lvl)
    if not v:
        other, at = lead_verb(rw)
        first = " ".join(rw.split()[:2])
        out.append((4, "the revised outcome starts with %r%s - it starts with one verb of %s, in the third person: %s"
                    % (first, " (a verb of %s)" % level(at) if other else "", level(lvl), verbs_for(lvl))))
    else:
        m = re.match(r"\s*(?:%s)\s*,?\s+(?:and|or)\s+([A-Za-z]+)" % "|".join(re.escape(f).replace(r"\ ", r"\s+") for f in third_person(v)), rw, re.I)
        if m and m.group(1).lower().endswith("s") and bloom_map.ilo_level(m.group(1))["level"]:
            out.append((4, "one verb only - not %r" % m.group(0).strip()))
    if comparable:
        a, b = marks(original), marks(rw)
        if a - b:
            out.append((5, "leaves out %s of the original" % ", ".join(sorted(a - b))))
        if b - a:
            out.append((5, "adds %s, not in the original - no new number, abbreviation, equipment or document" % ", ".join(sorted(b - a))))
        ow, rwords = content_words(original), content_words(rw)
        if ow:
            share = len(ow & rwords) / len(ow)
            if share < CK["content_words_min"]:
                out.append((6, "keeps %d %% of the original's content words (at least %d %%) - gone: %s; keep the technical content "
                               "in the original words" % (round(share * 100), round(CK["content_words_min"] * 100), ", ".join(sorted(ow - rwords)[:8]))))
        if n_words(rw) > CK["length_max"] * n_words(original):
            out.append((7, "is %d words against the original's %d (at most %.1f times as long) - change the verb and as little else "
                           "as possible" % (n_words(rw), n_words(original), CK["length_max"])))
    return out


# ------------------------------------------------------------------ the TLA of one outcome
def tlas():
    """[{name, key, task_type, level, route, modality}] - the TLA pool, in its own order"""
    return [{"name": f["label"], "key": k, "task_type": f["task_type"], "level": f["level"],
             "route": af._POOL[f["label"]]["route"], "modality": af._POOL[f["label"]]["modality"]} for k, f in af.FORMATS.items()]


TLAS = tlas()
_BY = {}
for _t in TLAS:
    _BY[_t["name"].lower()] = _t
    _BY[_t["key"].lower()] = _t


def tla(name):
    """The TLA a row names - by its key ("case-dilemma") or its full name - or None"""
    return _BY.get(str(name or "").strip().lower())


def allowed_tlas(lvl, used, previous):
    """(allowed, blocked) for an outcome at lvl. allowed: the keys of the pool's TLAs tagged at that level, less the ones
    variety blocks; blocked: {key: why}. used: {key: outcomes that already have it}; previous: the keys of the outcomes
    before this one, in syllabus order."""
    base = [t["key"] for t in TLAS if t["level"] == lvl]
    done = sum(used.values())
    prev = set(previous[-VAR["previous"]:]) if VAR["previous"] else set()
    over = {k for k in base if done >= VAR["share_from"] and used.get(k, 0) / done > VAR["share_max"]}
    why = {k: "holds more than %d %% of the course's tasks" % round(VAR["share_max"] * 100) for k in over}
    why.update({k: "used by one of the %d outcomes before this one" % VAR["previous"] for k in base if k in prev})
    allowed = [k for k in base if k not in over and k not in prev]
    if len(allowed) < VAR["min_choices"]:
        allowed = [k for k in base if k not in prev]              # the share block is dropped first
    if len(allowed) < VAR["min_choices"]:
        allowed = list(base)                                      # then the previous-outcomes block
    return allowed, {k: v for k, v in why.items() if k not in allowed}


def task_problems(p, lvl, used, previous):
    """(problems, the TLA's key or None) - the task proposal of one outcome at its final level lvl"""
    t = tla(p.get("tla"))
    allowed, blocked = allowed_tlas(lvl, used, previous) if isinstance(lvl, int) else ([], {})
    names = "; ".join("%s (%s)" % (k, _BY[k]["name"]) for k in allowed)
    out = []
    if not _filled(p.get("tla")):
        out.append("no TLA named ('tla') - at %s one of: %s" % (level(lvl), names))
    elif not t:
        out.append("%r is not a TLA of the pool - at %s one of: %s" % (p["tla"], level(lvl), names))
    elif t["level"] != lvl:
        out.append("%s is a %s activity and the outcome ends at %s - one of: %s" % (t["key"], level(t["level"]), level(lvl), names))
    elif t["key"] not in allowed:
        out.append("%s is blocked for variety (%s) - one of: %s" % (t["key"], blocked.get(t["key"], "variety"), names))
    if _filled(p.get("how")) and n_words(p["how"]) > TASK["words_max"]:
        out.append("the task is %d words - an outline of one or two sentences, at most %d" % (n_words(p["how"]), TASK["words_max"]))
    fit = str(p.get("fit") or "").strip().lower()
    if fit not in FITS:
        out.append("no fit ('fit': %s)" % ", ".join(FITS))
    elif fit != "strong" and not _filled(p.get("fit_note")):
        out.append("fit %r says in 'fit_note' what it needs (%s)" % (fit, TASK["fit"][fit]))
    return out, (t["key"] if t else None)


# ------------------------------------------------------------------ the counts
def summary(rows):
    """rows: [{"orig": level or None, "p": the proposal, "main": bool}] in syllabus order -> the counts, all made here"""
    s = {"total": len(rows), "decided": 0, "tasked": 0, "raise": 0, "keep": 0, "codes": {}, "tla": {}, "fit": {},
         "original": {n: 0 for n in range(1, 7)}, "final": {n: 0 for n in range(1, 7)}, "attention": 0}
    for r in rows:
        p = r["p"] or {}
        if r["orig"] in s["original"]:
            s["original"][r["orig"]] += 1
        if p.get("decision") in ("raise", "keep"):
            s["decided"] += 1
            s[p["decision"]] += 1
            if p.get("level") in s["final"]:
                s["final"][p["level"]] += 1
            for c in (p.get("keep_codes") or []) if p["decision"] == "keep" else []:
                s["codes"][c] = s["codes"].get(c, 0) + 1
        t = tla(p.get("tla"))
        if t and _filled(p.get("how")):
            s["tasked"] += 1
            s["tla"][t["key"]] = s["tla"].get(t["key"], 0) + 1
            f = str(p.get("fit") or "-").lower()
            s["fit"][f] = s["fit"].get(f, 0) + 1
        if _filled(p.get("attention")):
            s["attention"] += 1
    return s


def summary_lines(s):
    pct = lambda a, b: ("%d %%" % round(100 * a / b)) if b else "-"
    out = ["Outcomes decided: %d / %d   tasks: %d / %d" % (s["decided"], s["total"], s["tasked"], s["total"]),
           "Raised %d, kept %d (%s of the decided)%s" % (s["raise"], s["keep"], pct(s["keep"], s["decided"]),
                                                        " - flagged for the expert: %d" % s["attention"] if s["attention"] else "")]
    if s["codes"]:
        out.append("Kept by code: " + ", ".join("%s %d" % (c, n) for c, n in sorted(s["codes"].items(), key=lambda x: -x[1])))
    out.append("Level        original  final")
    out += ["  %-11s %7d %6d" % (level(n), s["original"][n], s["final"][n]) for n in range(1, 7)]
    if s["tla"]:
        out.append("TLA use: " + ", ".join("%s %d (%s)" % (k, n, pct(n, s["tasked"])) for k, n in sorted(s["tla"].items(), key=lambda x: -x[1])))
        out.append("Fit: " + ", ".join("%s %d" % (k, n) for k, n in sorted(s["fit"].items())))
    return out


# ------------------------------------------------------------------ what one answer is asked - one outcome at a time
EXAMPLE = ("  Original: States that a cargo tank is entered only when the oxygen reading is 21 % and the permit is signed\n"
           "  A correct raise: Verifies that a cargo tank is entered only when the oxygen reading is 21 % and the permit is signed\n"
           "  Not acceptable (adds a task and a document): Verifies the entry conditions and completes an enclosed-space permit")


def outcome_packet(ref, original, orig, heading="", where=""):
    """The whole question about ONE outcome: raise it or keep it. Nothing about any other outcome is in it."""
    codes = allowed_codes(orig) if isinstance(orig, int) else []
    up = [n for n in RAISE if isinstance(orig, int) and n > orig]
    lines = ["ONE OUTCOME - %s%s" % (ref, "  (%s)" % where if where else ""),
             "Heading above it (context only): %s" % (heading or "-"),
             "Original outcome: %s" % original,
             "Original Bloom level: %s" % (level(orig) if isinstance(orig, int) else "not known - say it first (original_level)"),
             "",
             "Decide: raise it or keep it. Raise is the default; pick the level this content naturally supports, not the",
             "highest you can argue for. The honesty test: one sentence on what the learner would actually do with this content",
             "at the new level, on board or in training ('does'). If that sentence needs content the outcome does not contain, keep it."]
    lines += ["  %s - %s. Starts with: %s" % (level(n), E["raise_levels"][str(n)], verbs_for(n)) for n in up]
    lines += ["  " + x for x in E["judgement"]["raise"]]
    lines += ["Keep only with a code and a reason about this outcome: " + "; ".join("%s %s" % (c, CODES[c]["means"]) for c in codes)]
    lines += ["  " + x for x in (E["judgement"]["keep_low"] if isinstance(orig, int) and orig <= 2 else [])]
    lines += [
              "If you raise: change the verb and as little else as possible - the technical content stays in the original words,",
              "nothing added (no fact, number, equipment, document, regulation, condition or task), nothing removed, one verb.",
              EXAMPLE,
              "If you keep: write no revised wording - the original is shown as it is."]
    return "\n".join(lines)


def task_packet(ref, text, lvl, used, previous, last=()):
    """The whole question about ONE outcome's task: the TLAs the code allows, how often each is used, the two before"""
    allowed, blocked = allowed_tlas(lvl, used, previous)
    lines = ["ONE TASK - %s" % ref, "Outcome, as decided: %s" % text, "Bloom level: %s" % level(lvl), "",
             "Choose ONE TLA of these - the only ones available for this outcome (used so far in this course):"]
    lines += ["  %-18s %s - %s; %s; used %d" % (k, _BY[k]["name"], _BY[k]["task_type"].replace("_", " "), _BY[k]["modality"], used.get(k, 0))
              for k in allowed]
    lines += ["  (blocked: %s - %s)" % (k, v) for k, v in blocked.items()]
    lines += ["Choose by what this outcome asks the learner to do; where two fit equally, the one used less.",
              "The two tasks before this one: " + ("; ".join(last) if last else "none yet"),
              "Then the task ('how'): one or two sentences, under %d words, an outline - it names this outcome's own equipment," % TASK["words_max"],
              "values, procedure or situation, the learner does what the level says, and no fact is added that is not in the outcome.",
              "Fit: " + "; ".join("%s - %s" % (k, v) for k, v in TASK["fit"].items())]
    return "\n".join(lines)


# ------------------------------------------------------------------ the three frameworks, enforced
ENF = E["enforced"]


def enforced(course):
    """True when the three frameworks are ENFORCED for this course (ilo-elevation.json "enforced"): its learning-outcome
    review is of the elevation method. A course started before 2.142.0 finishes by the rules it was started with."""
    if not course:
        return False
    p = workspace.claude_path(course, "pedagogy_review.json")
    try:
        with io.open(p, encoding="utf-8") as f:
            return (json.load(f) or {}).get("method") == METHOD
    except (OSError, ValueError):
        return False


def stage2_problems(course, prog, arch):
    """What stops the Stage 2 approval of an enforced course: a Sub-ILO with no Bloom level (rule B1), and a Sub-ILO we
    wrote that opens with a verb no assessor can see (the Bloom Verb Guide). [] for a course that is not enforced."""
    if not enforced(course) or not arch:
        return []
    out = []
    cm = bloom_map.course_map(prog or {}, arch)
    for m in cm["modules"]:
        for s in m["subs"]:
            if s.get("status") == "main":
                continue
            where = "module %s, Sub-ILO %s" % (m["n"], s["id"])
            ours = s.get("status") in ("re-expressed", "added")
            if ENF["stage2"]["untagged"] and s["level"] is None:
                key, kw = bloom_map.unread(m["n"], s, "en")
                if key == "b_depends":
                    out.append("%s has no Bloom level: %r is %s or %s - %s Write it on the Sub-ILO (\"bloom\": n)." % (where, kw["verb"], kw["low"], kw["high"], kw["how"]))
                elif key == "b_unknown":
                    out.append("%s has no Bloom level: its verb is not read - write the level on the Sub-ILO (\"bloom\": n). Every outcome is tagged." % where)
            if ENF["stage2"]["unobservable"] and ours:
                av = bloom_map.avoided(s["text"]) if s.get("lang") == "en" else None
                if s.get("weak"):
                    out.append("%s: %r cannot be watched - we wrote this outcome, so it starts with a verb an assessor can see (bloom/GUIDE.md 2a)" % (where, s["verb"]))
                elif av and not av["observable"]:
                    out.append("%s: %r %s - we wrote this outcome, so write instead: %s" % (where, av["verb"], av["problem"], av["instead"]))
    return ["the frameworks: " + x for x in out]


# ------------------------------------------------------------------ the golden set
LEVELS_BY_NAME = {"remember": 1, "understand": 2, "apply": 3, "analyze": 4, "analyse": 4, "evaluate": 5, "create": 6}


def golden(items, answers):
    """(lines, passed) - the answers to the golden set, each checked like any proposal and compared with the decision and
    the level the reference reached. It tests the decision and the level, never the wording."""
    lines, match, lv_match, failed, missing = [], 0, 0, 0, 0
    for it in items:
        a = answers.get(str(it["ref"]))
        orig = LEVELS_BY_NAME.get(str(it.get("original_level", "")).lower())
        want_l = LEVELS_BY_NAME.get(str(it.get("expected_level", "")).lower())
        if not a:
            missing += 1
            lines.append("  %-9s not answered" % it["ref"])
            continue
        probs = outcome_problems(it["original_text"], orig, a)
        failed += 1 if probs else 0
        want = it.get("expected_decision")         # a set without the reference (the questions only): the checks alone
        same = a.get("decision") == want
        match += 1 if same else 0
        lv_match += 1 if same and a.get("level") == want_l else 0
        if probs or (want and (not same or a.get("level") != want_l)):
            lines.append("  %-9s %s at %s%s%s" % (it["ref"], a.get("decision"), level(a.get("level")),
                         " - the reference: %s at %s" % (want, level(want_l)) if want else "",
                         "".join("\n            check %d: %s" % p for p in probs)))
    if not any(it.get("expected_decision") for it in items):
        return (["Questions only, no reference: %d outcomes - a check failed on %d; not answered %d" % (len(items), failed, missing)]
                + lines + ["CHECKS PASS" if not failed and not missing else "CHECKS NOT PASSED"]), not failed and not missing
    need = E["golden"]["match_min"] * len(items) / E["golden"]["of"]
    ok = not failed and not missing and match >= need
    head = ["Golden set: %d outcomes - decisions that match the reference: %d (at least %d); the level too: %d; a check "
            "failed on %d; not answered %d" % (len(items), match, round(need), lv_match, failed, missing)]
    return head + lines + ["PASS" if ok else "NOT PASSED"], ok
