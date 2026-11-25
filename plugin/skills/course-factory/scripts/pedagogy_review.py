#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""The experts' pedagogy documents - the first thing a course gives its experts, before any module is built.

    pedagogy_review.py draft  --course <course>             add an empty row for every topic not judged yet
    pedagogy_review.py check  --course <course>             what is missing or wrong; exit 2 when something is
    pedagogy_review.py render --course <course> [--no-pdf]  write the three documents into to_review\\pedagogy\\
    pedagogy_review.py expert --course <course> --module 4 --topic 4.1 --level 4 --said "<their words>" --by "<name>"
                                                            an expert's decision on a topic's level, carried out as it is

  one outcome at a time (2.142.0 - the ILO elevation method, knowledge/ilo-elevation.json, scripts/ilo_elevation.py):
    pedagogy_review.py next    --course <course>            the ONE outcome to decide next - or the one task to propose
    pedagogy_review.py propose --course <course> --module 4 --topic 4.1 --decision raise --level 4
                               --text "<the re-worded outcome>" --does "<what the learner does at that level>" --why "<why>"
    pedagogy_review.py propose --course <course> --module 4 --topic 4.2 --decision keep --codes PRE,CNF --why "<why>"
    pedagogy_review.py task    --course <course> --module 4 --topic 4.1 --tla key-feature --how "<the task>" --fit strong
    pedagogy_review.py status  --course <course>            decided n / total, raised and kept, each keep code, each TLA
    pedagogy_review.py golden  --set <golden_set.json> [--packet <ref> | --answers <answers.json>]
  Each answer is checked by code before it is attached to its outcome; one that fails is not saved and the failed
  check is named. A review started before 2.142.0 has no "method": it is finished by the rules it was started with
  (one level a course, no re-wording in a proposal); `draft --elevation` moves it to this method.

WHY THIS EXISTS
The course experts decide how a course is taught. Before a single module is built they get, topic by topic and module
by module:
  1. BLOOM NOW       - the level each learning outcome asks for, and the level the old course actually reached: how it
                       taught the topic and how, if at all, it checked it;
  2. BLOOM PROPOSED  - each topic kept or lifted, to the level its outcome asks for (above it only with the task on
                       board that needs it, `above_why`), how the trainee reaches it on the tablet, the simulator or the
                       equipment, and why;
  3. ACTIVITIES      - the teaching and learning activities proposed for each topic (architecture.json
                       "active_learning", the same proposals the Stage 2 page shows) and the course-wide upgrades.
Each as Word (to review and sign), HTML and PDF. make_architecture_page.py --approve records no Stage 2 approval
until `check` is clean and the documents are written from the current file.

WHAT IS READ, WHAT IS WRITTEN
  the topics and their outcomes, as taught          architecture.json (the Sub-ILOs; a module without any: its Main ILOs)
  the level an outcome asks for                     its verb (bloom_map.py), or the level written on the Sub-ILO
  the activities                                    architecture.json "active_learning"
  the judgement - now, proposed, the upgrades       working_claude\\pedagogy_review.json, written by the factory from
                                                    the old course (OLD_COURSE_INVENTORY.md, its tests and exercises)
                                                    and bloom/GUIDE.md section 5
The outcomes' words are never in pedagogy_review.json: they are read from the architecture, so a document can never
change one. The documents are English only so far; the outcomes are shown in the programme's own words, and a
revised outcome is written in English, as the course will show it (L19).

Standard library only (the PDF is printed by the same hidden browser as the additional materials).
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(SKILL, "compile", "scripts"))
import bloom_map  # noqa: E402
import ilo_elevation as el  # noqa: E402  - raise or keep, one outcome at a time (2.142.0)
import workspace  # noqa: E402

FILE = "pedagogy_review.json"
FOLDER = "pedagogy"
ACTIVE = json.load(io.open(os.path.join(SKILL, "knowledge", "active-learning.json"), encoding="utf-8"))
DOCS = (("1_BLOOM_NOW", "Bloom levels now - the old course"),
        ("2_BLOOM_PROPOSED", "Bloom levels proposed - the new course"),
        ("3_TEACHING_ACTIVITIES", "Teaching and learning activities"))
STATUS = {"proposed": "proposed", "approved": "kept", "kept": "kept", "struck": "struck"}


def _load(path, default=None):
    if not os.path.isfile(path):
        return default
    with io.open(path, encoding="utf-8") as f:
        return json.load(f)


def _save(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with io.open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def files(course):
    return {"arch": workspace.claude_path(course, "architecture.json"),
            "prog": workspace.claude_path(course, "programme.json"),
            "review": workspace.claude_path(course, FILE),
            "out": workspace.review_path(course, FOLDER)}


def level(n):
    if n == 0:
        return "not taught"
    return "%d %s" % (n, bloom_map.level_name(n, "en")) if isinstance(n, int) and 1 <= n <= 6 else "-"


def technique(t):
    return (t or "").replace("-", " ").capitalize() if t in ACTIVE["patterns"] or t == "plain" else (t or "-")


def course_title(arch, course):
    c = arch.get("course") or {}
    return c.get("title") or c.get("name") or os.path.basename(os.path.dirname(os.path.abspath(course)))


def modules(prog, arch):
    """[{n, title, rows: [{id, text, asks}], active: [...]}] - every module but the final assessment, in order."""
    fa = str((arch.get("final_assessment") or {}).get("topic") or "")
    main = {str(i.get("id")): i.get("text", "") for i in arch.get("main_ilos", [])}
    out = []
    for am in sorted(arch.get("modules", []), key=lambda m: int(m.get("module", 0))):
        if str(am.get("module")) == fa:
            continue
        en = {str(s.get("id")): s.get("text_en") or "" for s in am.get("sub_ilos") or [] if isinstance(s, dict)}
        rows = [{"id": s["id"], "text": s["text"], "asks": s["level"], "main": False, "lang": s["lang"],
                 "programme_text": s.get("programme_text") or s["text"], "programme_lang": s.get("programme_lang") or s["lang"],
                 "status": s.get("status"), "orig": _orig_level(s), "text_en": en.get(s["id"], "")}
                for s in bloom_map._sub_ilos(prog, arch, am)]
        if not rows:
            rows = [{"id": i, "text": main.get(i, ""), "asks": bloom_map.ilo_level(main.get(i, ""))["level"], "main": True,
                     "lang": "en", "programme_text": main.get(i, ""), "programme_lang": "en", "status": "original",
                     "orig": bloom_map.ilo_level(main.get(i, ""))["level"], "text_en": ""}
                    for i in (str(x) for x in am.get("main_ilos", []))]
        out.append({"n": int(am["module"]), "title": am.get("title", ""), "rows": rows,
                    "active": [a for a in (am.get("active_learning") or []) if isinstance(a, dict)]})
    return out


def _orig_level(s):
    """The Bloom level of an outcome as the programme words it - before any re-wording an expert took (2.142.0)"""
    given = s.get("programme_text") or ""
    if s.get("status") == "re-expressed" and given and given != s["text"]:
        return bloom_map.ilo_level(given, s.get("programme_lang") or s["lang"])["level"]
    return s["level"]


def original_of(r, x=None):
    """(the wording a re-wording is compared with, its Bloom level, comparable) - the programme's own words when they are
    English, else their English rendering (architecture "text_en"); comparable False when there is none, so the wording
    checks cannot be made. The level is the row's "original_level" when the verb is not in the list and it was said."""
    said = (x or {}).get("original_level")
    lvl = said if isinstance(said, int) and 1 <= said <= 6 else r.get("orig")
    if (r.get("programme_lang") or "en") == "en":
        return r["programme_text"], lvl, True
    if _filled(r.get("text_en")) and r.get("status") != "re-expressed":
        return r["text_en"], lvl, True
    return r["programme_text"], lvl, False


def not_english(text, lang):
    """True when the words lead with a verb of the programme's language and none of English - not written in English"""
    return lang != "en" and bool(bloom_map.ilo_level(text, lang)["verb"]) and not bloom_map.ilo_level(text, "en")["verb"]


def decision(now, new, asks):
    """kept, lifted, above the outcome or the expert's decision - what the experts read first"""
    a, b = (now or {}).get("level"), (new or {}).get("level")
    if not (isinstance(a, int) and isinstance(b, int)):
        return "-"
    if (new or {}).get("expert"):
        return "the expert's decision"
    if (new or {}).get("decision") in ("raise", "keep"):          # the elevation method: said, not worked out
        return "raised" if new["decision"] == "raise" else "kept"
    if b <= a:
        return "kept"
    return "above the outcome" if asks and b > max(a, asks) else "lifted"


def _blank():
    return {"now": {"level": None, "how": "", "checked": "", "where": ""},
            "proposed": {"level": None, "how": "", "why": "", "limit": "", "above_why": ""}}


def draft(course, elevation=False):
    f = files(course)
    arch = _load(f["arch"])
    if not arch:
        print("Stopped - there is no architecture yet (working_claude/architecture.json). The documents follow its topics.")
        return 2
    rev = _load(f["review"], {}) or {}
    if elevation or not rev.get("modules"):
        rev["method"] = el.METHOD          # a new review raises or keeps every outcome, one at a time (2.142.0)
    rev.setdefault("now_summary", "")
    rev.setdefault("proposed_summary", "")
    rev.setdefault("upgrades", [])
    mods = rev.setdefault("modules", {})
    added = 0
    for m in modules(_load(f["prog"], {}) or {}, arch):
        rows = mods.setdefault(str(m["n"]), {}).setdefault("rows", {})
        for r in m["rows"]:
            if r["id"] not in rows:
                rows[r["id"]] = _blank()
                added += 1
    _save(f["review"], rev)
    print("%s: %d topic row(s) added, to be judged (bloom/GUIDE.md section 5)." % (f["review"], added))
    if rev.get("method") == el.METHOD:
        print("One outcome at a time: pedagogy_review.py next --course <course>, answer it with propose, then the tasks.")
    return 0


def _filled(x):
    return isinstance(x, str) and x.strip()


LIFT_MAX = 1                           # levels a topic is lifted in one course, unless the expert decides more


def check(course):
    """(problems, notes) - a problem stops the Stage 2 approval; a note is said and never stops it."""
    f = files(course)
    arch, rev = _load(f["arch"]), _load(f["review"])
    if not arch:
        return ["there is no architecture yet (working_claude/architecture.json)"], []
    if not rev:
        return ["not started yet - pedagogy_review.py draft, then judge every topic"], []
    probs, notes = [], []
    if not _filled(rev.get("now_summary")):
        probs.append("now_summary is empty - how the old course taught and checked, in two or three sentences")
    if not _filled(rev.get("proposed_summary")):
        probs.append("proposed_summary is empty - what changes, in two or three sentences")
    ups = rev.get("upgrades") or []
    if not ups:
        probs.append("upgrades is empty - name at least one course-wide pedagogy upgrade")
    for i, u in enumerate(ups, 1):
        if not (isinstance(u, dict) and _filled(u.get("what")) and _filled(u.get("why"))):
            probs.append("upgrade %d needs its 'what' and its 'why'" % i)
    mods = rev.get("modules") or {}
    known = set()
    elev = rev.get("method") == el.METHOD      # raise or keep, one outcome at a time (2.142.0) - else the rules it was started with
    used, before = {}, []                      # the TLAs of the outcomes so far, in syllabus order: variety is counted here
    for m in modules(_load(f["prog"], {}) or {}, arch):
        rows = (mods.get(str(m["n"])) or {}).get("rows") or {}
        if not m["active"]:
            notes.append("module %d: no teaching and learning activity is proposed (architecture.json active_learning)" % m["n"])
        for r in m["rows"]:
            known.add((str(m["n"]), r["id"]))
            x = rows.get(r["id"])
            where = "module %d, topic %s" % (m["n"], r["id"])
            if not x:
                probs.append("%s: not judged yet" % where)
                continue
            now, new = x.get("now") or {}, x.get("proposed") or {}
            for side, d, need, low in (("now", now, ("how", "checked", "where"), 0), ("proposed", new, ("how", "why"), 1)):
                if not (isinstance(d.get("level"), int) and low <= d["level"] <= 6):
                    probs.append("%s: %s level must be %d-6%s" % (where, side, low, " (0: not taught)" if not low else ""))
                for k in need:
                    if not _filled(d.get(k)):
                        probs.append("%s: %s '%s' is empty" % (where, side, k))
            a, b = now.get("level"), new.get("level")
            if elev:
                p2, n2 = elevation_row(r, x, where, used, before)
                probs += p2
                notes += n2
            elif isinstance(a, int) and isinstance(b, int) and b < a:
                probs.append("%s: the proposal (%s) is below what the old course reached (%s)" % (where, level(b), level(a)))
            if elev or new.get("expert"):
                pass                          # the expert's decision is carried out as it is (record_expert)
            elif isinstance(a, int) and isinstance(b, int) and a >= 1 and b > a + LIFT_MAX:
                # one level a course: GAS BASIC lifted 33 topics two or three levels at once and thinned its theory
                probs.append("%s: %s to %s lifts it %d levels - a course lifts a topic one level (to %s); the expert can "
                             "decide more (pedagogy_review.py expert)" % (where, level(a), level(b), b - a, level(a + LIFT_MAX)))
            elif isinstance(a, int) and isinstance(b, int) and b > a and not r["asks"]:
                probs.append("%s: a lift needs the level the outcome asks for - write it on the Sub-ILO (\"bloom\": n)" % where)
            elif isinstance(a, int) and isinstance(b, int) and b > max(a, r["asks"] or 0) and not _filled(new.get("above_why")):
                probs.append("%s: %s is above what the outcome asks (%s) - keep it at %s, or say in 'above_why' which task on "
                             "board needs it" % (where, level(b), level(r["asks"]), level(max(a, r["asks"]))))
            if not elev and isinstance(b, int) and r["asks"] and b < r["asks"] and not new.get("expert"):
                if isinstance(a, int) and a >= 1 and b == a + LIFT_MAX:
                    notes.append("%s: proposed %s, one level above the old course - the outcome asks %s; the next course, or the "
                                 "expert, takes it further" % (where, level(b), level(r["asks"])))
                elif _filled(new.get("limit")):
                    notes.append("%s: proposed %s stays below what the outcome asks (%s) - %s"
                                 % (where, level(b), level(r["asks"]), new["limit"]))
                else:
                    probs.append("%s: proposed %s is below what the outcome asks (%s) - lift it, or say in 'limit' what stops "
                                 "this course reaching it" % (where, level(b), level(r["asks"])))
            if b == 6:
                notes.append("%s: Create is reached by a practical exercise, not a tablet task - say which one" % where)
            probs += open_notes(x, where, course)
            rw = (new.get("revised_outcome") or "").strip()
            if rw and r["main"]:
                probs.append("%s: a Main ILO is never re-worded (L2) - empty its 'revised_outcome'" % where)
            elif rw and elev and new.get("decision") == "raise" and not new.get("expert") and not_english(rw, r["programme_lang"]):
                probs.append("%s: 'revised_outcome' is in the programme's language - write it in English, as the course will "
                             "show it; the programme's own words stay beside it (L19)" % where)
            elif rw and elev and not new.get("expert"):
                pass                          # a raise carries its re-wording; ilo_elevation checked it (elevation_row)
            elif rw and not new.get("expert"):
                # the outcomes are the programme's: a proposal never re-words one, only an expert's decision may
                probs.append("%s: the outcome is the programme's - a proposal never re-words it; empty its 'revised_outcome' "
                             "(an expert who wants it re-worded says so, and it is recorded as their decision)" % where)
            elif rw and not_english(rw, r["programme_lang"]):
                probs.append("%s: 'revised_outcome' is in the programme's language - write it in English, as the course will "
                             "show it; the programme's own words stay beside it (L19)" % where)
    for n, m in mods.items():
        for i in (m or {}).get("rows") or {}:
            if (str(n), i) not in known:
                probs.append("module %s, topic %s: not a topic of the architecture any more - remove the row" % (n, i))
    for n, m in mods.items():
        probs += open_notes(m or {}, "module %s" % n, course)
    probs += open_notes(rev, "the whole course", course)
    return probs, notes


def elevation_row(r, x, where, used, before):
    """(problems, notes) of one row judged by the elevation method (ilo_elevation.py): its outcome proposal, then its
    task. used and before are the TLAs of the outcomes so far, in syllabus order - this row's TLA is added to them, so
    variety is counted by code. An expert's own decision is only warned about; a row whose "attention" says why a
    wording check cannot be met is shown to the expert flagged, and no longer stops."""
    now, new = x.get("now") or {}, x.get("proposed") or {}
    basis, orig, comparable = original_of(r, x)
    probs, notes = [], []
    flagged = _filled(new.get("attention"))
    for n, words in el.outcome_problems(basis, orig, new, main=r["main"], comparable=comparable):
        if new.get("expert"):
            notes.append("%s: %s - the expert's decision stands, this is only a warning" % (where, words))
        elif flagged and n in el.WAIVABLE:
            notes.append("FLAGGED for the expert - %s: %s (check %d). Because: %s" % (where, words, n, new["attention"].strip()))
        else:
            probs.append("%s: %s (check %d)" % (where, words, n))
    if new.get("decision") == "raise" and not comparable and not r["main"]:
        notes.append("%s: the programme's wording is not in English and the architecture has no English rendering of it - "
                     "the wording of the raise could not be checked against it" % where)
    a, b = now.get("level"), new.get("level")
    if isinstance(a, int) and isinstance(b, int) and b < a and not new.get("expert"):
        notes.append("%s: the old course reached %s and the outcome ends at %s - keep what it taught in the task" % (where, level(a), level(b)))
    key = None
    if new.get("decision") in ("raise", "keep") and isinstance(b, int) and 1 <= b <= 6:
        found, key = el.task_problems(new, b, used, before)
        theirs = new.get("expert") or new.get("task_expert")      # the expert's own task (2.142.1) is only warned about too
        for words in found:
            (notes if theirs else probs).append("%s: %s" % (where, words) + (" - the expert's decision stands" if theirs else ""))
        t = el.tla(new.get("tla"))
        if t and str(new.get("fit") or "").lower() == "strong" and not r["main"]:
            import activity_formats as af
            tt = af.verb_type(new.get("revised_outcome") or r["text"])[0]
            if t["task_type"] != tt:
                notes.append("%s: %s is a %s activity and the outcome reads as a %s - if that is so, the fit is 'adapted'"
                             % (where, t["key"], t["task_type"].replace("_", " "), tt.replace("_", " ")))
    before.append(key)
    if key:
        used[key] = used.get(key, 0) + 1
    return probs, notes


def elevation_rows(course):
    """[{n, title, r, x, where}] - every outcome of the course in syllabus order with its row of the review, or None when
    there is no architecture or no review yet"""
    f = files(course)
    arch, rev = _load(f["arch"]), _load(f["review"])
    if not arch or not rev:
        return None
    out = []
    for m in modules(_load(f["prog"], {}) or {}, arch):
        got = ((rev.get("modules") or {}).get(str(m["n"])) or {}).get("rows") or {}
        for r in m["rows"]:
            out.append({"n": m["n"], "title": m["title"], "r": r, "x": got.get(r["id"]) or {},
                        "where": "module %d, topic %s" % (m["n"], r["id"])})
    return out


def counts(course):
    """The counts of the review, all made by code: decided n / total, raised and kept, each keep code, each TLA"""
    rows = elevation_rows(course) or []
    return el.summary([{"orig": original_of(e["r"], e["x"])[1], "p": e["x"].get("proposed") or {}, "main": e["r"]["main"]} for e in rows])


FILE_NAMED = re.compile(r"[\w.\-\\/:]*\w\.(?:json|md|html|docx|xlsx|pptx|pdf|py|js|css|txt|csv)\b", re.I)


def changed_file(course, done, on=""):
    """the course file a note's 'done' names that was changed on or after the note's date ("on"), or None"""
    try:
        since = time.mktime(time.strptime(str(on or "")[:10], "%Y-%m-%d"))
    except ValueError:
        since = 0.0
    # the review file itself changes when "done" is written into it, so naming it proves nothing
    own = os.path.basename(files(course)["review"]).lower() if course else "pedagogy_review.json"
    names = [n for n in FILE_NAMED.findall(done or "") if os.path.basename(n.replace("\\", "/")).lower() != own]
    for name in names:
        if os.path.isabs(name):
            ways = [name]
        else:
            ways = [os.path.join(course, name), workspace.claude_path(course, name)]
        for p in ways:
            if os.path.isfile(p) and os.path.getmtime(p) >= since:
                return p
    want = {os.path.basename(n.replace("\\", "/")).lower() for n in names}
    for root, _, fs in os.walk(course) if want and course else ():
        for f in fs:
            if f.lower() in want and os.path.getmtime(os.path.join(root, f)) >= since:
                return os.path.join(root, f)
    return None


def open_notes(x, where, course=None):
    """An expert's 'needs change' from editor mode is carried out before the stage goes on: until its 'done' says
    what the factory changed and names the course file it changed (changed on or after the note's date), it stops the
    approval. The expert's own task (a note "Task: ...", carried out at the pull) is done as it is."""
    out = []
    own_task = bool((x.get("proposed") or {}).get("task_expert"))
    for n in x.get("expert_notes") or []:
        if not isinstance(n, dict):
            continue
        who, said = n.get("by") or "the expert", n.get("said", "")
        if not _filled(n.get("done")):
            out.append("%s: %s asked in editor mode: \"%s\" - carry it out, then write in its 'done' what was changed "
                       "and the file it was changed in" % (where, who, said))
        elif course and not (own_task and said.lower().startswith("task:")) and not changed_file(course, n["done"], n.get("on")):
            out.append("%s: the 'done' of %s's note (\"%s\") names no course file changed%s - carry the change out, and "
                       "name the file it is in (architecture.json, pedagogy_review.json, a module's script ...)"
                       % (where, who, said, " since %s" % n["on"][:10] if _filled(n.get("on")) else ""))
    return out


def fingerprint(course):
    f = files(course)
    h = hashlib.sha256()
    for k in ("arch", "review"):
        if os.path.isfile(f[k]):
            with open(f[k], "rb") as fh:
                h.update(fh.read())
    return h.hexdigest()[:16]


def approval_problems(course):
    """What stops the Stage 2 approval: the documents judged, checked and written from the current files."""
    probs, _ = check(course)
    out = ["experts' pedagogy documents: " + p for p in probs]
    if not probs:
        stamp = os.path.join(files(course)["out"], "fingerprint.txt")
        have = open(stamp, encoding="utf-8").read().strip() if os.path.isfile(stamp) else ""
        if have != fingerprint(course):
            out.append("the experts' pedagogy documents are not written from the current files - "
                       "pedagogy_review.py render --course <course>")
    return out


# ------------------------------------------------------------------ the three documents
def _glance(mods, rev, cols):
    rows = []
    for m in mods:
        got = (rev.get("modules") or {}).get(str(m["n"]), {}).get("rows", {})
        asks = max((r["asks"] or 0 for r in m["rows"]), default=0)
        now = [((got.get(r["id"]) or {}).get("now") or {}).get("level") for r in m["rows"]]
        new = [((got.get(r["id"]) or {}).get("proposed") or {}).get("level") for r in m["rows"]]
        now = max((x for x in now if isinstance(x, int)), default=None)
        new = max((x for x in new if isinstance(x, int)), default=None)
        row = ["%d" % m["n"], m["title"], level(asks), level(now)]
        rows.append(row + [level(new)] if cols == 5 else row)
    return rows


def _intro(title, which):
    return [("h1", which), ("p", title),
            ("p", "For the course experts, before any module is built. Topic by topic and module by module. The learning "
                  "outcomes are the programme's and are not changed here: these pages are about how each one is taught "
                  "and checked."),
            ("table", ["Level", "The trainee can ..."],
             [[level(n), (bloom_map.LEVELS[n].get("means") or {}).get("en", "")] for n in range(1, 7)],
             [2000, 7638])]


def _signoff(rev=None):
    """The expert's Ready from editor mode signs it with their name; without one, blank lines to sign on paper."""
    r = (rev or {}).get("ready") or {}
    if r.get("by"):
        return [("h2", "Expert's review"),
                ("facts", [("Reviewed by", r["by"]), ("Date", r.get("on") or " "),
                           ("Agreed / changes asked", "Ready, in editor mode%s" % (" - %d change(s) asked" % r["changes"]
                                                                                   if r.get("changes") else "")),
                           ("Signature", r["by"])])]
    return [("h2", "Expert's review"),
            ("facts", [("Reviewed by", " "), ("Date", " "), ("Agreed / changes asked", " "), ("Signature", " ")])]


def proposed_why(r, now, new):
    """The 'Why' cell of Bloom proposed: what the experts read beside each decision."""
    ex = new.get("expert") or {}
    met = decision(now, new, r["asks"]) == "kept" and r["asks"] and (now.get("level") or 0) >= r["asks"]
    codes = [c for c in new.get("keep_codes") or [] if c in el.CODES] if new.get("decision") == "keep" else []
    return ((["Kept because the old course already reaches what the outcome asks (%s)." % level(r["asks"])] if met else [])
            + (["Kept as it is worded: " + "; ".join("%s - %s" % (c, el.CODES[c]["means"]) for c in codes)] if codes else [])
            + (["The trainee: " + new["does"]] if new.get("decision") == "raise" and _filled(new.get("does")) else [])
            + (["Please check this one: " + new["attention"]] if _filled(new.get("attention")) else [])
            + ["On board: " + (new.get("why") or "-")]
            + (["Not higher because: " + new["limit"]] if _filled(new.get("limit")) else [])
            + (["Above the outcome: " + new["above_why"]] if _filled(new.get("above_why")) else [])
            + (["The expert (%s, %s): %s" % (ex.get("by", ""), ex.get("on", ""), ex.get("said", ""))] if ex else []))


def _decisions(rev):
    """The decisions a review counts: raised or kept by the elevation method, kept / lifted / above before it"""
    return (("raised", "kept", "the expert's decision") if (rev or {}).get("method") == el.METHOD
            else ("kept", "lifted", "above the outcome", "the expert's decision"))


def activity_row(a, ids):
    return {"topic": a.get("subtopic") if str(a.get("subtopic")) in ids else "module", "does": a.get("does") or "",
            "kind": technique(a.get("technique")), "minutes": str(a.get("minutes") or "-"),
            "instead_of": a.get("instead_of") or "-", "needs": a.get("needs") or "-",
            "status": STATUS.get(a.get("status"), a.get("status") or "proposed")}


def doc_now(title, mods, rev):
    b = _intro(title, DOCS[0][1])
    b += [("h2", "The course at a glance"),
          ("table", ["Module", "Topic", "Outcomes ask (highest)", "Old course reached (highest)"],
           _glance(mods, rev, 4), [900, 4138, 2300, 2300]),
          ("p", rev.get("now_summary") or "")]
    for m in mods:
        got = (rev.get("modules") or {}).get(str(m["n"]), {}).get("rows", {})
        b.append(("h2", "Module %d - %s" % (m["n"], m["title"])))
        if (rev.get("modules") or {}).get(str(m["n"]), {}).get("note"):
            b.append(("p", rev["modules"][str(m["n"])]["note"]))
        b.append(("table", ["Topic", "Learning outcome", "Asks", "Old course reached", "How it was taught and checked", "Where"],
                  [[r["id"], r["text"], level(r["asks"]),
                    level(((got.get(r["id"]) or {}).get("now") or {}).get("level")),
                    [((got.get(r["id"]) or {}).get("now") or {}).get("how") or "not judged yet",
                     "Checked: " + (((got.get(r["id"]) or {}).get("now") or {}).get("checked") or "-")],
                    ((got.get(r["id"]) or {}).get("now") or {}).get("where") or "-"] for r in m["rows"]],
                  [650, 2600, 1000, 1000, 3000, 1388]))
    return b + _signoff(rev)


def doc_proposed(title, mods, rev):
    b = _intro(title, DOCS[1][1])
    b += [("h2", "The course at a glance"),
          ("table", ["Module", "Topic", "Outcomes ask", "Now", "Proposed"], _glance(mods, rev, 5),
           [900, 3538, 1800, 1700, 1700]),
          ("p", rev.get("proposed_summary") or "")]
    tally, now_n, new_n = {}, {}, {}
    for m in mods:
        got = (rev.get("modules") or {}).get(str(m["n"]), {}).get("rows", {})
        for r in m["rows"]:
            x = got.get(r["id"]) or {}
            d = decision(x.get("now"), x.get("proposed"), r["asks"])
            tally[d] = tally.get(d, 0) + 1
            for side, box in (("now", now_n), ("proposed", new_n)):
                lv = (x.get(side) or {}).get("level")
                box[lv] = box.get(lv, 0) + 1
    b.append(("table", ["", "Topics"], [[k.capitalize(), str(tally.get(k, 0))] for k in _decisions(rev)], [5000, 4638]))
    b.append(("table", ["Level", "Old course", "Proposed"],
              [[level(n), str(now_n.get(n, 0)), str(new_n.get(n, 0))] for n in range(0, 7)], [3600, 3000, 3038]))
    for m in mods:
        got = (rev.get("modules") or {}).get(str(m["n"]), {}).get("rows", {})
        b.append(("h2", "Module %d - %s" % (m["n"], m["title"])))
        rows = []
        for r in m["rows"]:
            x = got.get(r["id"]) or {}
            now, new = x.get("now") or {}, x.get("proposed") or {}
            rw = (new.get("revised_outcome") or "").strip() if new.get("decision") == "raise" and not r["main"] else ""
            act = el.tla(new.get("tla"))
            rows.append([r["id"], [r["programme_text"], "Raised, proposed wording: " + rw] if rw else r["text"], level(r["asks"]),
                         ["%s -> %s" % (level(now.get("level")), level(new.get("level"))), decision(now, new, r["asks"])],
                         [new.get("how") or "not judged yet"] + (["Activity: %s (%s fit)" % (act["name"], new.get("fit") or "-")] if act else []),
                         proposed_why(r, now, new)])
        b.append(("table", ["Topic", "Learning outcome", "Asks", "Now -> proposed", "How the trainee reaches it", "Why"],
                  rows, [650, 2400, 1000, 1500, 2600, 1488]))
    return b + _signoff(rev)


def doc_activities(title, mods, rev):
    b = [("h1", DOCS[2][1]), ("p", title),
         ("p", "For the course experts, before any module is built. What the trainees do, topic by topic: each activity "
               "takes its minutes from the plain theory of its topic - the theory slides stay, the instructor goes "
               "through them faster. Every activity is proposed; the experts keep or strike it."),
         ("h2", "Upgrades for the whole course")]
    b.append(("table", ["Upgrade", "Why", "Where"],
              [[u.get("what", ""), u.get("why", ""), ", ".join("M%s" % x for x in u["modules"])
                if isinstance(u.get("modules"), list) else (u.get("modules") or "all modules")]
               for u in rev.get("upgrades") or []], [3600, 4238, 1800]))
    total = sum(int(a.get("minutes") or 0) for m in mods for a in m["active"] if a.get("status") != "struck")
    b.append(("p", "Class time moved from listening to doing, with every activity kept: %d minutes." % total))
    for m in mods:
        b.append(("h2", "Module %d - %s" % (m["n"], m["title"])))
        ids = {r["id"] for r in m["rows"]}
        b.append(("table", ["Topic", "What the trainees do", "Kind", "Min", "Instead of", "Needs", "Status"],
                  [list(activity_row(a, ids).values()) for a in m["active"]]
                  or [["-", "none proposed", "-", "-", "-", "-", "-"]],
                  [650, 3300, 1300, 600, 1700, 1300, 788]))
    return b + _signoff(rev)


def render(course, pdf=True):
    import additional_materials as am
    f = files(course)
    arch = _load(f["arch"])
    if not arch:
        print("Stopped - there is no architecture yet (working_claude/architecture.json).")
        return 2
    rev = _load(f["review"], {}) or {}
    mods = modules(_load(f["prog"], {}) or {}, arch)
    title = course_title(arch, course)
    os.makedirs(f["out"], exist_ok=True)
    exe = am.browser() if pdf else None
    written = []
    for (name, head), blocks in zip(DOCS, (doc_now(title, mods, rev), doc_proposed(title, mods, rev),
                                         doc_activities(title, mods, rev))):
        base = os.path.join(f["out"], name)
        am.to_docx(blocks, base + ".docx")
        with io.open(base + ".html", "w", encoding="utf-8", newline="\n") as fh:
            fh.write(am.to_html("%s - %s" % (head, title), blocks))
        written += [base + ".docx", base + ".html"]
        if exe and am.print_pdf(exe, base + ".html", base + ".pdf"):
            written.append(base + ".pdf")
    probs, notes = check(course)
    with io.open(os.path.join(f["out"], "fingerprint.txt"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write((fingerprint(course) if not probs else "") + "\n")
    print("Written for the experts, in %s:" % f["out"])
    for p in written:
        print("  " + os.path.basename(p))
    if pdf and not exe:
        print("  (no PDF: no Chrome or Edge found - the Word and HTML files are complete)")
    for p in probs:
        print("  STILL OPEN: " + p)
    for n in notes:
        print("  note: " + n)
    return 2 if probs else 0


# ------------------------------------------------------------------ the same documents in editor mode
def _hash(x):
    return hashlib.sha256(json.dumps(x, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()[:16]


def _done(x, about=None):
    """The changes an expert asked in editor mode and what the factory changed - shown on the row, so they see it.
    about: None for the Bloom row (or the course summary), "activities" or "upgrades" for those rows."""
    return [{"by": n.get("by", ""), "said": n.get("said", ""), "done": n["done"]} for n in (x.get("expert_notes") or [])
            if isinstance(n, dict) and _filled(n.get("done")) and n.get("about") == about]


def item_key(module, topic):
    return ("%s/%s" % (module, re.sub(r"[^A-Za-z0-9._-]+", "-", str(topic)).strip("-")))[:60]


def view(course):
    """The three documents as the training app's editor shows them (course_portal.py push --pedagogy): the same words
    as the Word files, topic by topic, and a hash for every row the experts answer - the summaries ("course"), the
    upgrades ("upgrades"), each topic's Bloom level ("4/4.1"), each topic's activities ("act/4/4.1") and the module's
    own ("act/4/module"). A row whose words do not change keeps its answers when the documents are sent again."""
    f = files(course)
    arch = _load(f["arch"])
    if not arch:
        return None
    rev = _load(f["review"], {}) or {}
    mods = modules(_load(f["prog"], {}) or {}, arch)
    out = {"title": course_title(arch, course),
           "levels": [{"level": level(n), "means": (bloom_map.LEVELS[n].get("means") or {}).get("en", "")} for n in range(1, 7)],
           "now_summary": rev.get("now_summary") or "", "proposed_summary": rev.get("proposed_summary") or "",
           "upgrades": [{"what": u.get("what", ""), "why": u.get("why", ""),
                         "where": ", ".join("M%s" % x for x in u["modules"]) if isinstance(u.get("modules"), list)
                         else (u.get("modules") or "all modules")} for u in rev.get("upgrades") or []],
           "glance": [dict(zip(("module", "title", "asks", "now", "proposed"), g)) for g in _glance(mods, rev, 5)],
           "modules": []}
    out["changes_made"], out["upgrade_changes"] = _done(rev), _done(rev, "upgrades")
    items = {"course": _hash([out["now_summary"], out["proposed_summary"], out["glance"], out["changes_made"]]),
             "upgrades": _hash([out["upgrades"], out["upgrade_changes"]])}
    tally = {}
    for m in mods:
        got = (rev.get("modules") or {}).get(str(m["n"]), {})
        ids = {r["id"] for r in m["rows"]}
        acts = [activity_row(a, ids) for a in m["active"]]
        topics = []
        for r in m["rows"]:
            x = (got.get("rows") or {}).get(r["id"]) or {}
            now, new = x.get("now") or {}, x.get("proposed") or {}
            d = decision(now, new, r["asks"])
            tally[d] = tally.get(d, 0) + 1
            t = {"item": item_key(m["n"], r["id"]), "id": r["id"], "outcome": r["text"], "asks": level(r["asks"]),
                 **outcome_columns(r, new),
                 "now": {"level": level(now.get("level")), "how": now.get("how") or "not judged yet",
                         "checked": now.get("checked") or "-", "where": now.get("where") or "-"},
                 "proposed": {"level": level(new.get("level")), "change": "%s -> %s" % (level(now.get("level")), level(new.get("level"))),
                              "decision": d, "how": new.get("how") or "not judged yet", "why": proposed_why(r, now, new)},
                 "activities": [a for a in acts if str(a["topic"]) == str(r["id"])],
                 "changes_made": _done(x) + _done(x, "activities")}
            if new.get("decision") in ("raise", "keep"):       # the elevation method: what was decided, and the task's TLA
                act = el.tla(new.get("tla")) or {}
                t["elevation"] = {"decision": new["decision"], "codes": list(new.get("keep_codes") or []) if new["decision"] == "keep" else [],
                                  "why": new.get("why") or "", "does": new.get("does") or "", "activity": act.get("name", ""),
                                  "activity_id": act.get("key", ""), "route": act.get("route", ""),
                                  "fit": new.get("fit") or "", "fit_note": new.get("fit_note") or "", "attention": new.get("attention") or ""}
            items[t["item"]] = _hash([t["intended"], t["revised"], t["asks"], t["now"], t["proposed"], t["activities"],
                                      t["changes_made"]] + ([t["elevation"]] if "elevation" in t else []))
            topics.append(t)
        mod = {"n": m["n"], "title": m["title"], "note": got.get("note") or "", "topics": topics,
               "module_activities": [a for a in acts if a["topic"] == "module"], "activity_changes": _done(got, "activities")}
        if mod["module_activities"]:
            mod["act_item"] = "act/%s/module" % m["n"]
            items[mod["act_item"]] = _hash([mod["module_activities"], mod["activity_changes"]])
        out["modules"].append(mod)
    out["decisions"] = [{"decision": k, "topics": tally.get(k, 0)} for k in _decisions(rev)]
    if rev.get("method") == el.METHOD:
        out["counts"] = counts(course)
    out["active_minutes"] = sum(int(a.get("minutes") or 0) for m in mods for a in m["active"] if a.get("status") != "struck")
    # What the editor shows is the outcomes form (the owner's Excel, 2026-11-23): one row per outcome, the rows the
    # experts answer. The documents' own view stays beside it ("review") for the pull and the Word files.
    form = outcomes_form(out, arch)
    rows = {r["item"]: items[r["item"]] for t in form["topics"] for r in t["rows"] if r.get("item")}
    return {"content": form, "items": rows, "fingerprint": _hash([form, rows]), "review": out, "review_items": items}


def _lv(label):
    """'3 Apply' -> 3; 'not taught', '-', 'not judged yet' -> None"""
    m = re.match(r"^\s*([1-6])\b", str(label or ""))
    return int(m.group(1)) if m else None


def _verb(text):
    """'describe · 2 Understand' -> 'describe'; a level alone or '-' -> ''"""
    v = str(text or "").split(" · ")[0].strip()
    return "" if v == "-" or re.match(r"^\d", v) else v


def outcomes_form(out, arch):
    """The learning-outcome review as the editor shows it (2026-11-23, the owner's Excel "IMO 1.04 Part C - Bloom
    distribution"): topic (the module) -> ILO (its Main ILO) -> sub-ILO, each row the original wording and its level
    beside the proposed one, and the practical task. An expert who does not agree with a proposed level picks another
    and presses Regenerate: Claude words the outcome again at that level (a Main ILO keeps its words) - an answer the
    pull carries out as a decision with Claude. A module's Main ILO heads its Sub-ILOs (a "heading" row, not
    answered); a module without Sub-ILOs is answered on its Main ILOs."""
    main_text = {str(i.get("id")): i.get("text", "") for i in arch.get("main_ilos", [])}
    arch_mod = {str(am.get("module")): am for am in arch.get("modules", [])}
    topics = []
    for m in out["modules"]:
        mains = [str(x) for x in (arch_mod.get(str(m["n"])) or {}).get("main_ilos") or []]
        subs = any(not t["main"] for t in m["topics"])
        rows = []
        if subs:
            for i in mains:
                info = bloom_map.ilo_level(main_text.get(i, ""))
                rows.append({"ref": i, "heading": True, "main": True,
                             "original": {"verb": info.get("verb") or "", "text": main_text.get(i, ""), "level": info.get("level") or None}})
        parent = mains[0] if subs and len(mains) == 1 else None
        for t in m["topics"]:
            lv, rw = _lv(t["proposed"]["level"]), t["revised"]
            ev = t.get("elevation") or {}
            acts = [a for a in t["activities"] if a.get("status") != "struck"]
            rows.append({"item": t["item"], "ref": t["id"], "parent": None if t["main"] else parent, "main": t["main"],
                         "original": {"verb": _verb(t["existing_verb"]), "text": t["intended"], "level": _lv(t["asks"])},
                         "proposed": {"verb": _verb(t["revised_verb"]) if rw else _verb(t["existing_verb"]), "text": rw or t["intended"], "level": lv} if lv else None,
                         "task": dict({"name": ev.get("activity") or (acts[0]["kind"] if acts else ""), "does": t["tla"]},
                                      **({"id": ev["activity_id"], "route": ev["route"], "fit": ev["fit"], "fit_note": ev["fit_note"]} if ev.get("activity_id") else {}))
                         if _filled(t["tla"]) and t["tla"] != "not judged yet" else None,
                         # the elevation method (2.142.0), in the editor's own words for a row: what was decided, why a
                         # kept outcome is kept, and a row the expert should see first. The outcome and its task are ONE
                         # decision in the editor (owner, 2026-11-24): keep the old outcome, or accept the new one
                         **({"decision": ev["decision"]} if ev else {}),
                         **({"kept": {"criteria": ev["codes"], "why": ev["why"]}} if ev.get("decision") == "keep" else {}),
                         **({"flag": ev["attention"]} if ev.get("attention") else {}),
                         "old": {"level": t["now"]["level"], "how": t["now"]["how"]} if _filled(t["now"]["how"]) and t["now"]["how"] != "not judged yet" else None})
        topics.append({"n": m["n"], "title": m["title"], "rows": rows})
    form = {"form": "outcomes", "title": out["title"], "levels": out["levels"], "topics": topics}
    if out.get("counts"):
        # the elevation method: the rules the editor shows and checks a Regenerate with - sent with the form, so the
        # training app never keeps a copy of its own (knowledge/ilo-elevation.json is the one source)
        form.update(method=el.METHOD, counts=out["counts"],
                    archetypes=[{"id": a["key"], "name": a["name"], "level": a["level"], "levels": level(a["level"]),
                                 "route": a["route"], "task_type": a["task_type"]} for a in el.TLAS],
                    keep_codes=[{"code": c, "means": v["means"], "levels": v["levels"]} for c, v in el.CODES.items()],
                    write_verbs={str(n): [el.third_person(v)[0].capitalize() for v in vs] for n, vs in el.WRITE.items()},
                    checks={"content_words_min": el.CK["content_words_min"], "length_max": el.CK["length_max"],
                            "small_words": el.CK["small_words"], "task_words_max": el.TASK["words_max"],
                            "variety": {k: v for k, v in el.VAR.items() if not k.startswith("_")}},
                    judgement=el.E["judgement"]["raise"] + el.E["judgement"]["keep_low"])
    return form


def verb_of(text, lang, lvl=None):
    """'describe · 2 Understand' - the verb that leads the outcome and the level it names (or the level taught)."""
    info = bloom_map.ilo_level(text or "", lang or "en")
    if not info["verb"] and (lang or "en") != "en":           # an English Sub-ILO in a course whose programme is not
        info = bloom_map.ilo_level(text or "", "en")
    n = lvl if lvl else info["level"]
    v = info["verb"]
    return ("%s · %s" % (v, level(n)) if v and n else v or (level(n) if n else "-"))


def outcome_columns(r, new):
    """Intended learning outcome | existing verb | revised learning outcome | revised verb, as the experts read them.
    The intended outcome is the programme's words; a Sub-ILO may be re-worded (L2: proposed, ratified by the expert),
    a Main ILO never."""
    rw = "" if r["main"] else ((new.get("revised_outcome") or "").strip()
                               or (r["text"] if r.get("status") == "re-expressed" and r["text"] != r["programme_text"] else ""))
    return {"main": r["main"], "intended": r["programme_text"],
            "existing_verb": verb_of(r["programme_text"], r.get("programme_lang")),
            "revised": rw, "revised_verb": verb_of(rw, r.get("lang"), new.get("level")) if rw else "",
            "tla": new.get("how") or "not judged yet"}


def ratify(course, module, sub_id, text, by):
    """A Sub-ILO's new wording, taken by an expert: written into the architecture as re-expressed, the programme's own
    words kept beside it (L2). False when the row is a Main ILO or not in the architecture."""
    from datetime import date
    f = files(course)
    arch = _load(f["arch"])
    for am in (arch or {}).get("modules", []):
        if str(am.get("module")) != str(module):
            continue
        for s in am.get("sub_ilos") or []:
            if isinstance(s, dict) and str(s.get("id")) == str(sub_id):
                if not s.get("programme_text") and s.get("status", "original") == "original":
                    prog = _load(f["prog"], {}) or {}
                    s["programme_text"] = (prog.get("outcomes") or {}).get(str(sub_id)) or s.get("text") or ""
                s.update(status="re-expressed", text=text.strip(), ratified={"by": by, "on": date.today().isoformat()})
                rev = _load(f["review"], {}) or {}
                lvl = ((((rev.get("modules") or {}).get(str(module)) or {}).get("rows") or {}).get(str(sub_id)) or {}).get("proposed", {}).get("level")
                if rev.get("method") == el.METHOD and isinstance(lvl, int) and 1 <= lvl <= 6:
                    s["bloom"] = lvl          # a raised outcome carries its level: the tag is said, not read from the verb (rule B1)
                _save(f["arch"], arch)
                return True
    return False


def carry_out(row, lvl, said, by, how="", why=None, decision=None, keep_codes=None):
    """An expert's decision on one topic, carried out as it is: their level, their words, and the 'how' they agreed to
    (empty, for the factory to write, when they gave none). decision ("raise" / "keep"), for a row judged by the
    elevation method: what the expert's answer makes of the outcome, so the counts stay true - Keep old ILO is a keep
    (with the keep codes the editor's Regenerate named, else the row's own), a re-wording they took is a raise."""
    from datetime import date
    new = row.setdefault("proposed", {})
    new.update(level=lvl, how=how, limit="", above_why="", expert={"by": by.strip(), "on": date.today().isoformat(), "said": said.strip()})
    new.pop("revised_outcome", None)
    if why:
        new["why"] = why
    if decision in ("raise", "keep") and new.get("decision") in ("raise", "keep"):
        new["decision"] = decision
        if decision == "keep":
            new["keep_codes"] = [str(c).strip().upper() for c in (keep_codes or new.get("keep_codes") or []) if str(c).strip().upper() in el.CODES]
            new.pop("does", None)
        else:
            new.pop("keep_codes", None)
        new.pop("attention", None)


def record_expert(course, module, topic, lvl, said, by):
    """An expert's decision on a topic's level - carried out whatever the keep-or-lift rules say. 'how' is emptied, so
    check asks the factory to write what the trainee does at the new level before the documents are written again."""
    f = files(course)
    rev = _load(f["review"])
    row = ((rev or {}).get("modules", {}).get(str(module), {}).get("rows", {}) or {}).get(str(topic))
    if not row:
        print("Stopped - module %s has no topic %s in %s." % (module, topic, f["review"]))
        return 2
    if not (1 <= lvl <= 6 and said.strip() and by.strip()):
        print("Stopped - nothing was recorded: a level 1-6, the expert's own words (--said) and who (--by) are needed.")
        return 2
    carry_out(row, lvl, said, by)
    _save(f["review"], rev)
    print("Recorded: module %s, topic %s at %s, by %s. Write what the trainee does at that level ('how'), then render."
          % (module, topic, level(lvl), by.strip()))
    return 0


# ------------------------------------------------------------------ one outcome at a time (the elevation method)
def _elevation(course):
    """(review, its rows in syllabus order) or (None, a message) when the review is not there or not of this method"""
    f = files(course)
    rev = _load(f["review"])
    rows = elevation_rows(course)
    if rows is None:
        return None, "Stopped - not started yet: pedagogy_review.py draft --course <course>."
    if rev.get("method") != el.METHOD:
        return None, ("Stopped - this review was started before 2.142.0 and is finished by the rules it was started with. "
                      "To raise or keep every outcome one at a time: pedagogy_review.py draft --course <course> --elevation.")
    return rev, rows


def _tla_state(rows, upto):
    """(used, before, last) - the TLAs of the outcomes before row number `upto`, counted by code"""
    used, before, last = {}, [], []
    for e in rows[:upto]:
        p = e["x"].get("proposed") or {}
        t = el.tla(p.get("tla"))
        before.append(t["key"] if t else None)
        if t:
            used[t["key"]] = used.get(t["key"], 0) + 1
            last.append("%s - %s" % (t["key"], p.get("how") or ""))
    return used, before, last[-el.VAR["previous"]:]


def _decided(e):
    p = e["x"].get("proposed") or {}
    return p.get("decision") in ("raise", "keep") and isinstance(p.get("level"), int)


def next_one(course):
    """Print the ONE question to answer next: an outcome not decided yet, in syllabus order; when all are, the first
    outcome without its task. Never two."""
    rev, rows = _elevation(course)
    if rev is None:
        print(rows)
        return 2
    c = counts(course)
    print("Outcomes decided %d / %d, tasks %d / %d." % (c["decided"], c["total"], c["tasked"], c["total"]))
    for e in rows:
        if not _decided(e) and not (e["x"].get("proposed") or {}).get("expert"):
            basis, orig, _ = original_of(e["r"], e["x"])
            print(el.outcome_packet("module %d, topic %s" % (e["n"], e["r"]["id"]), basis, orig, heading="Module %d - %s" % (e["n"], e["title"]),
                                    where="a Main ILO: its words never change (L2) - a raise is the level and the task only" if e["r"]["main"] else ""))
            print("\nAnswer with: pedagogy_review.py propose --course <course> --module %d --topic %s --decision raise|keep ..." % (e["n"], e["r"]["id"]))
            return 0
    for i, e in enumerate(rows):
        p = e["x"].get("proposed") or {}
        if _decided(e) and not (el.tla(p.get("tla")) and _filled(p.get("how")) and p.get("fit")):
            used, before, last = _tla_state(rows, i)
            text = (p.get("revised_outcome") or "").strip() if p.get("decision") == "raise" and not e["r"]["main"] else original_of(e["r"], e["x"])[0]
            print(el.task_packet("module %d, topic %s" % (e["n"], e["r"]["id"]), text or e["r"]["text"], p["level"], used, before, last))
            print("\nAnswer with: pedagogy_review.py task --course <course> --module %d --topic %s --tla <key> --how \"...\" --fit strong|adapted|gap" % (e["n"], e["r"]["id"]))
            return 0
    print("Every outcome is decided and has its task. Now: pedagogy_review.py check --course <course>.")
    return 0


def _row(rev, rows, module, topic):
    for i, e in enumerate(rows):
        if str(e["n"]) == str(module) and str(e["r"]["id"]) == str(topic):
            x = rev.setdefault("modules", {}).setdefault(str(e["n"]), {}).setdefault("rows", {}).setdefault(e["r"]["id"], _blank())
            return i, e, x
    return None, None, None


def propose(course, a):
    """One outcome's answer, checked and attached to it by code. Nothing is saved when a check fails."""
    rev, rows = _elevation(course)
    if rev is None:
        print(rows)
        return 2
    i, e, x = _row(rev, rows, a.module, a.topic)
    if e is None:
        print("Stopped - module %s has no topic %s." % (a.module, a.topic))
        return 2
    if a.original_level:
        x["original_level"] = a.original_level
    basis, orig, comparable = original_of(e["r"], x)
    new = dict(x.get("proposed") or {})
    was = new.get("level")
    new.update(decision=a.decision, why=(a.why or new.get("why") or "").strip())
    if a.decision == "keep":
        new.update(level=orig, keep_codes=[c.strip().upper() for c in (a.codes or "").split(",") if c.strip()])
        for k in ("revised_outcome", "does", "attention"):
            new.pop(k, None)
        if a.text:
            print("Not saved - a kept outcome keeps its wording, character for character: leave --text out.")
            return 2
    else:
        new.update(level=a.level, does=(a.does or "").strip())
        new.pop("keep_codes", None)
        if not e["r"]["main"]:
            new["revised_outcome"] = (a.text or "").strip()
        if a.attention:
            new["attention"] = a.attention.strip()
        else:
            new.pop("attention", None)
    found = [(n, w) for n, w in el.outcome_problems(basis, orig, new, main=e["r"]["main"], comparable=comparable)
             if not (_filled(new.get("attention")) and n in el.WAIVABLE)]
    if found:
        print("Not saved - %s:" % e["where"])
        for n, w in found:
            print("  check %d: %s" % (n, w))
        print("Answer this outcome once more for that check. If a wording check (5-7) still cannot pass and the raise is honest, "
              "add --attention \"<why>\": the row is saved flagged, and the expert sees it first.")
        return 2
    if was != new.get("level"):                # the task was written for another level: it is out of date
        for k in ("tla", "fit", "fit_note"):
            new.pop(k, None)
        new["how"] = ""
    x["proposed"] = new
    _save(files(course)["review"], rev)
    c = counts(course)
    print("Saved - %s: %s at %s. Outcomes decided %d / %d." % (e["where"], "raised" if a.decision == "raise" else "kept", level(new["level"]), c["decided"], c["total"]))
    return 0


def task(course, a):
    """One outcome's task, checked against the TLAs the code allows at that place in the syllabus, and attached to it."""
    rev, rows = _elevation(course)
    if rev is None:
        print(rows)
        return 2
    i, e, x = _row(rev, rows, a.module, a.topic)
    if e is None or not _decided(e):
        print("Stopped - %s." % ("module %s has no topic %s" % (a.module, a.topic) if e is None else "decide the outcome first (propose): the task is built for its final level"))
        return 2
    new = dict(x.get("proposed") or {})
    new.update(tla=(el.tla(a.tla) or {}).get("key") or a.tla, how=a.how.strip(), fit=a.fit.strip().lower())
    if a.fit_note:
        new["fit_note"] = a.fit_note.strip()
    else:
        new.pop("fit_note", None)
    used, before, _ = _tla_state(rows, i)
    found, _ = el.task_problems(new, new["level"], used, before)
    if not _filled(new["how"]):
        found.append("the task is empty ('--how')")
    if found:
        print("Not saved - %s:" % e["where"])
        for w in found:
            print("  " + w)
        return 2
    x["proposed"] = new
    _save(files(course)["review"], rev)
    c = counts(course)
    print("Saved - %s: %s. Tasks %d / %d." % (e["where"], new["tla"], c["tasked"], c["total"]))
    return 0


def status(course):
    rev, rows = _elevation(course)
    if rev is None:
        print(rows)
        return 2
    for line in el.summary_lines(counts(course)):
        print(line)
    return 0


def golden(a):
    """The golden set: one outcome's question (--packet), or the answers scored against the reference (--answers)."""
    items = _load(a.set)
    if not isinstance(items, list):
        print("Stopped - %s is not a golden set (a list of outcomes with their expected decision and level)." % a.set)
        return 2
    if a.packet:
        it = next((i for i in items if str(i["ref"]) == str(a.packet)), None)
        if not it:
            print("Stopped - no outcome %s in the set. There are: %s" % (a.packet, ", ".join(str(i["ref"]) for i in items)))
            return 2
        print(el.outcome_packet(it["ref"], it["original_text"], el.LEVELS_BY_NAME.get(str(it.get("original_level", "")).lower()),
                                heading="%s - %s" % (it.get("competence", ""), it.get("topic", ""))))
        return 0
    if not a.answers:
        print("%d outcomes: %s" % (len(items), ", ".join(str(i["ref"]) for i in items)))
        return 0
    lines, ok = el.golden(items, _load(a.answers, {}) or {})
    for line in lines:
        print(line)
    return 0 if ok else 2


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("draft", "check", "render", "expert", "next", "propose", "task", "status"):
        s = sub.add_parser(name)
        s.add_argument("--course", required=True)
        if name == "draft":
            s.add_argument("--elevation", action="store_true", help="move a review started before 2.142.0 to the raise-or-keep method")
        if name == "render":
            s.add_argument("--no-pdf", action="store_true")
        if name == "expert":
            for a in ("--module", "--topic", "--said", "--by"):
                s.add_argument(a, required=True)
            s.add_argument("--level", type=int, required=True)
        if name in ("propose", "task"):
            s.add_argument("--module", required=True)
            s.add_argument("--topic", required=True)
        if name == "propose":
            s.add_argument("--decision", required=True, choices=("raise", "keep"))
            s.add_argument("--level", type=int, help="raise: 3-6")
            s.add_argument("--text", help="raise: the re-worded outcome")
            s.add_argument("--does", help="raise: what the learner does with this content at the new level")
            s.add_argument("--codes", help="keep: one or more keep codes, comma-separated")
            s.add_argument("--why", help="one or two sentences: why, for this outcome")
            s.add_argument("--attention", help="why a wording check cannot be met - the row is saved flagged for the expert")
            s.add_argument("--original-level", type=int, help="the original outcome's level, when its verb is not in the list")
        if name == "task":
            s.add_argument("--tla", required=True)
            s.add_argument("--how", required=True)
            s.add_argument("--fit", required=True)
            s.add_argument("--fit-note")
    g = sub.add_parser("golden")
    g.add_argument("--set", required=True)
    g.add_argument("--packet")
    g.add_argument("--answers")
    x = ap.parse_args(argv)
    if x.cmd == "golden":
        return golden(x)
    course = workspace.work_folder(x.course)
    if x.cmd == "draft":
        return draft(course, elevation=x.elevation)
    if x.cmd == "expert":
        return record_expert(course, x.module, x.topic, x.level, x.said, x.by)
    if x.cmd == "render":
        return render(course, pdf=not x.no_pdf)
    if x.cmd in ("next", "propose", "task", "status"):
        return {"next": next_one, "status": status}[x.cmd](course) if x.cmd in ("next", "status") else {"propose": propose, "task": task}[x.cmd](course, x)
    probs, notes = check(course)
    for p in probs:
        print("  - " + p)
    for n in notes:
        print("  note: " + n)
    rev = _load(files(course)["review"], {}) or {}
    if rev.get("method") == el.METHOD:
        c = counts(course)
        print("Outcomes decided %d / %d, tasks %d / %d." % (c["decided"], c["total"], c["tasked"], c["total"]))
    print("Clean - the experts' documents can be written." if not probs else "%d thing(s) to do first." % len(probs))
    return 2 if probs else 0


if __name__ == "__main__":
    sys.exit(main())
