#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""The experts' pedagogy documents - the first thing a course gives its experts, before any module is built.

    pedagogy_review.py draft  --course <course>             add an empty row for every topic not judged yet
    pedagogy_review.py check  --course <course>             what is missing or wrong; exit 2 when something is
    pedagogy_review.py render --course <course> [--no-pdf]  write the three documents into to_review\\pedagogy\\
    pedagogy_review.py expert --course <course> --module 4 --topic 4.1 --level 4 --said "<their words>" --by "<name>"
                                                            an expert's decision on a topic's level, carried out as it is

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
change one. The documents are English only so far.

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

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(SKILL, "compile", "scripts"))
import bloom_map  # noqa: E402
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
        rows = [{"id": s["id"], "text": s["text"], "asks": s["level"]} for s in bloom_map._sub_ilos(prog, arch, am)]
        if not rows:
            rows = [{"id": i, "text": main.get(i, ""), "asks": bloom_map.ilo_level(main.get(i, ""))["level"]}
                    for i in (str(x) for x in am.get("main_ilos", []))]
        out.append({"n": int(am["module"]), "title": am.get("title", ""), "rows": rows,
                    "active": [a for a in (am.get("active_learning") or []) if isinstance(a, dict)]})
    return out


def decision(now, new, asks):
    """kept, lifted, above the outcome or the expert's decision - what the experts read first"""
    a, b = (now or {}).get("level"), (new or {}).get("level")
    if not (isinstance(a, int) and isinstance(b, int)):
        return "-"
    if (new or {}).get("expert"):
        return "the expert's decision"
    if b <= a:
        return "kept"
    return "above the outcome" if asks and b > max(a, asks) else "lifted"


def _blank():
    return {"now": {"level": None, "how": "", "checked": "", "where": ""},
            "proposed": {"level": None, "how": "", "why": "", "limit": "", "above_why": ""}}


def draft(course):
    f = files(course)
    arch = _load(f["arch"])
    if not arch:
        print("Stopped - there is no architecture yet (working_claude/architecture.json). The documents follow its topics.")
        return 2
    rev = _load(f["review"], {}) or {}
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
    return 0


def _filled(x):
    return isinstance(x, str) and x.strip()


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
            if isinstance(a, int) and isinstance(b, int) and b < a:
                probs.append("%s: the proposal (%s) is below what the old course reached (%s)" % (where, level(b), level(a)))
            if new.get("expert"):
                pass                          # the expert's decision is carried out as it is (record_expert)
            elif isinstance(a, int) and isinstance(b, int) and b > a and not r["asks"]:
                probs.append("%s: a lift needs the level the outcome asks for - write it on the Sub-ILO (\"bloom\": n)" % where)
            elif isinstance(a, int) and isinstance(b, int) and b > max(a, r["asks"] or 0) and not _filled(new.get("above_why")):
                probs.append("%s: %s is above what the outcome asks (%s) - keep it at %s, or say in 'above_why' which task on "
                             "board needs it" % (where, level(b), level(r["asks"]), level(max(a, r["asks"]))))
            if isinstance(b, int) and r["asks"] and b < r["asks"] and not new.get("expert"):
                if _filled(new.get("limit")):
                    notes.append("%s: proposed %s stays below what the outcome asks (%s) - %s"
                                 % (where, level(b), level(r["asks"]), new["limit"]))
                else:
                    probs.append("%s: proposed %s is below what the outcome asks (%s) - lift it, or say in 'limit' what stops "
                                 "this course reaching it" % (where, level(b), level(r["asks"])))
            if b == 6:
                notes.append("%s: Create is reached by a practical exercise, not a tablet task - say which one" % where)
            probs += open_notes(x, where)
    for n, m in mods.items():
        for i in (m or {}).get("rows") or {}:
            if (str(n), i) not in known:
                probs.append("module %s, topic %s: not a topic of the architecture any more - remove the row" % (n, i))
    for n, m in mods.items():
        probs += open_notes(m or {}, "module %s" % n)
    probs += open_notes(rev, "the whole course")
    return probs, notes


def open_notes(x, where):
    """An expert's 'needs change' from editor mode is carried out before the stage goes on: until its 'done' says
    what the factory changed, it stops the approval."""
    return ["%s: %s asked in editor mode: \"%s\" - carry it out, then write in its 'done' what was changed"
            % (where, n.get("by") or "the expert", n.get("said", "")) for n in (x.get("expert_notes") or [])
            if isinstance(n, dict) and not _filled(n.get("done"))]


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
    return ((["Kept because the old course already reaches what the outcome asks (%s)." % level(r["asks"])] if met else [])
            + ["On board: " + (new.get("why") or "-")]
            + (["Not higher because: " + new["limit"]] if _filled(new.get("limit")) else [])
            + (["Above the outcome: " + new["above_why"]] if _filled(new.get("above_why")) else [])
            + (["The expert (%s, %s): %s" % (ex.get("by", ""), ex.get("on", ""), ex.get("said", ""))] if ex else []))


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
    b.append(("table", ["", "Topics"], [[k.capitalize(), str(tally.get(k, 0))] for k in ("kept", "lifted", "above the outcome", "the expert's decision")],
              [5000, 4638]))
    b.append(("table", ["Level", "Old course", "Proposed"],
              [[level(n), str(now_n.get(n, 0)), str(new_n.get(n, 0))] for n in range(0, 7)], [3600, 3000, 3038]))
    for m in mods:
        got = (rev.get("modules") or {}).get(str(m["n"]), {}).get("rows", {})
        b.append(("h2", "Module %d - %s" % (m["n"], m["title"])))
        rows = []
        for r in m["rows"]:
            x = got.get(r["id"]) or {}
            now, new = x.get("now") or {}, x.get("proposed") or {}
            rows.append([r["id"], r["text"], level(r["asks"]),
                         ["%s -> %s" % (level(now.get("level")), level(new.get("level"))), decision(now, new, r["asks"])],
                         new.get("how") or "not judged yet", proposed_why(r, now, new)])
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
                 "now": {"level": level(now.get("level")), "how": now.get("how") or "not judged yet",
                         "checked": now.get("checked") or "-", "where": now.get("where") or "-"},
                 "proposed": {"level": level(new.get("level")), "change": "%s -> %s" % (level(now.get("level")), level(new.get("level"))),
                              "decision": d, "how": new.get("how") or "not judged yet", "why": proposed_why(r, now, new)},
                 "activities": [a for a in acts if str(a["topic"]) == str(r["id"])], "changes_made": _done(x),
                 "activity_changes": _done(x, "activities")}
            items[t["item"]] = _hash([t["outcome"], t["asks"], t["now"], t["proposed"], t["changes_made"]])
            if t["activities"]:
                t["act_item"] = "act/" + t["item"]
                items[t["act_item"]] = _hash([t["outcome"], t["activities"], t["activity_changes"]])
            topics.append(t)
        mod = {"n": m["n"], "title": m["title"], "note": got.get("note") or "", "topics": topics,
               "module_activities": [a for a in acts if a["topic"] == "module"], "activity_changes": _done(got, "activities")}
        if mod["module_activities"]:
            mod["act_item"] = "act/%s/module" % m["n"]
            items[mod["act_item"]] = _hash([mod["module_activities"], mod["activity_changes"]])
        out["modules"].append(mod)
    out["decisions"] = [{"decision": k, "topics": tally.get(k, 0)} for k in ("kept", "lifted", "above the outcome", "the expert's decision")]
    out["active_minutes"] = sum(int(a.get("minutes") or 0) for m in mods for a in m["active"] if a.get("status") != "struck")
    return {"content": out, "items": items, "fingerprint": _hash([out, items])}


def carry_out(row, lvl, said, by, how="", why=None):
    """An expert's decision on one topic, carried out as it is: their level, their words, and the 'how' they agreed to
    (empty, for the factory to write, when they gave none)."""
    from datetime import date
    new = row.setdefault("proposed", {})
    new.update(level=lvl, how=how, limit="", above_why="", expert={"by": by.strip(), "on": date.today().isoformat(), "said": said.strip()})
    if why:
        new["why"] = why


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


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("draft", "check", "render", "expert"):
        s = sub.add_parser(name)
        s.add_argument("--course", required=True)
        if name == "render":
            s.add_argument("--no-pdf", action="store_true")
        if name == "expert":
            for a in ("--module", "--topic", "--said", "--by"):
                s.add_argument(a, required=True)
            s.add_argument("--level", type=int, required=True)
    x = ap.parse_args(argv)
    course = workspace.work_folder(x.course)
    if x.cmd == "draft":
        return draft(course)
    if x.cmd == "expert":
        return record_expert(course, x.module, x.topic, x.level, x.said, x.by)
    if x.cmd == "render":
        return render(course, pdf=not x.no_pdf)
    probs, notes = check(course)
    for p in probs:
        print("  - " + p)
    for n in notes:
        print("  note: " + n)
    print("Clean - the experts' documents can be written." if not probs else "%d thing(s) to do first." % len(probs))
    return 2 if probs else 0


if __name__ == "__main__":
    sys.exit(main())
