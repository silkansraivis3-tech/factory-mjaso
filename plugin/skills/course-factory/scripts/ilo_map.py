#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""The ILO map - what every module owes, built from the Stage 2 files, never typed twice (2.42.0).

    ilo_map.py build <course>                 write working_claude/ilo_map.json from programme.json + architecture.json
    ilo_map.py show  <course> --module 4      a module's rows - what its content script is written against
    ilo_map.py check <course>                 is ilo_map.json there, and does it say what architecture.json says?
    ilo_map.py refresh <course> [--module 4] [--dry-run]   the slide and question columns, from the scripts' "sub_ilo" tags

WHY THIS EXISTS
Owner, 2026-10-16: "before creating any module the AI should have already made the ILO mapping".
Until 2.42.0 the ILO map was a build step with no file: a module's script could be written and
approved without anyone having laid out, per module, which Main ILO and which Sub-ILOs it owes.

WHAT IT IS
One row per Sub-ILO, per module, in the programme's order:
    {"module": "M04", "module_title", "topic" (programme, verbatim), "main_ilo_ids": ["2"],
     "main_ilo" (programme, verbatim - L2), "sub_ilo_id": "4.a",
     "sub_ilo_status": "original | re-expressed | added | main", "sub_ilo" (as it is taught),
     "programme_wording" (the programme's own words beside a re-expressed one),
     "model_course": ["4.1.2", ...]  (optional - from the Sub-ILO's own "model_course" in architecture.json)}
A module with no Sub-ILO of its own gets one row per Main ILO it serves ("main") - it is written against
that.
Plus "model_course_items": {"M04": [...]} - every item of the model course's syllabus under that
programme topic (coverage/GUIDE.md §1), when the syllabus has been transcribed.

The core fields are rebuilt from architecture.json every time. Anything else on a row (how it is
taught, where, how it is assessed - the IGF pilot's own tool adds those) and any other top-level key
is kept as it is. make_architecture_page.py builds it whenever it makes the Stage 2 page, and the
operator's "next" on that page approves it (course_gate.py).

SLIDES AND QUESTIONS COME FROM THE SCRIPTS (2.49.2, F23)
The per-module tables of slides and questions are no longer typed by hand. refresh reads each module's
content script (working_claude/script/M04.json) and, for every row, writes where_taught ("slide 3 Title;
slide 5 Title"), checked_by ("SC1 q01, q02 · MC m03"), and the same as ids - taught_on, checked_on - from the
"sub_ilo" tag of each slide, activity and question (a row meets the tags of the Sub-ILOs below it). It writes
nothing else: the Main ILO, the Sub-ILO, their status and wording, and every other field of a row stay as
they are, so the operator's approval of the map stays valid. A module with no script yet is left alone; a tag
no row owns, and a Sub-ILO taught or checked nowhere, are reported. Run it after a script is approved or its
slides move (a course's own table tool reads these fields instead of keeping its own lists).

Standard library only.
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import io
import json
import os
import re
import sys
from datetime import date

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import workspace  # noqa: E402

FILE = "ilo_map.json"
CORE = ("module", "module_title", "topic", "main_ilo_ids", "main_ilo", "sub_ilo_id", "sub_ilo_status", "sub_ilo", "programme_wording")


def load(p):
    with io.open(p, encoding="utf-8") as f:
        return json.load(f)


def save(p, obj):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with io.open(p, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
        f.write("\n")


def mkey(module):
    """"M04", 4, "4", "module04" -> 4; "final" / "FINAL" -> "final"; anything else -> None."""
    s = str(module).strip().lower()
    if s in ("final", "fa"):
        return "final"
    digits = "".join(ch for ch in s if ch.isdigit())
    return int(digits) if digits else None


def mname(module):
    k = mkey(module)
    return "FINAL" if k == "final" else "M%02d" % k


def path(course):
    return workspace.claude_path(course, FILE)


def course_files(course):
    """programme.json and architecture.json of the course (None where missing)."""
    rd = lambda n: load(workspace.claude_path(course, n)) if os.path.isfile(workspace.claude_path(course, n)) else None
    return rd("programme.json"), rd("architecture.json")


def find_syllabus(course):
    """The model course's transcribed syllabus (coverage/GUIDE.md §1) - any *syllabus*.json in working_claude."""
    d = workspace.claude_path(course)
    for p in sorted(glob.glob(os.path.join(d, "*syllabus*.json"))):
        try:
            s = load(p)
        except (OSError, ValueError):
            continue
        if isinstance(s.get("items_by_topic"), dict):
            return s
    return None


def final_topic(arch):
    return str((arch.get("final_assessment") or {}).get("topic") or "")


def derive(prog, arch, syllabus=None):
    """The core rows, from the approved files. Pure - writes nothing."""
    prog, arch = prog or {}, arch or {}
    topics = {str(k): v for k, v in (prog.get("topics") or {}).items()}
    outcomes = {str(k): v for k, v in (prog.get("outcomes") or {}).items()}
    mains = {str(i.get("id")): i.get("text", "") for i in arch.get("main_ilos", []) or []}
    mains.update({str(k): v for k, v in (prog.get("main_ilos") or {}).items()})      # the programme's words win (L2)
    fa = final_topic(arch)
    rows, owed = [], {}
    # a "final" row sorts last - comparing it with the numbers raised TypeError
    order = lambda m: (lambda n: n if isinstance(n, int) else 10 ** 9)(mkey(m.get("module")))
    for am in sorted(arch.get("modules", []) or [], key=order):
        n = mkey(am.get("module"))
        if not isinstance(n, int) or str(n) == fa:
            continue
        M = mname(n)
        t = topics.get(str(n)) or {}
        mids = [str(x) for x in am.get("main_ilos", []) or []]
        for s in am.get("sub_ilos", []) or []:
            sid, st = str(s.get("id", "")), s.get("status", "original")
            wording = s.get("programme_text") or outcomes.get(sid) or ""
            text = s["text"] if st in ("re-expressed", "added") and s.get("text") else (wording or s.get("text", ""))
            row = {"module": M, "module_title": am.get("title", ""), "topic": t.get("title", ""), "main_ilo_ids": mids,
                   "main_ilo": " | ".join(mains.get(i, "") for i in mids if mains.get(i)), "sub_ilo_id": sid,
                   "sub_ilo_status": st, "sub_ilo": text, "programme_wording": wording if st != "added" else ""}
            if s.get("model_course"):
                row["model_course"] = list(s["model_course"]) if isinstance(s["model_course"], list) else [s["model_course"]]
            rows.append(row)
        if not am.get("sub_ilos"):                   # no Sub-ILO of its own: the module answers to its Main ILO (as bloom_map does)
            for i in mids:
                rows.append({"module": M, "module_title": am.get("title", ""), "topic": t.get("title", ""), "main_ilo_ids": mids,
                             "main_ilo": mains.get(i, ""), "sub_ilo_id": i, "sub_ilo_status": "main", "sub_ilo": mains.get(i, ""),
                             "programme_wording": mains.get(i, "")})
        if syllabus:
            items = (syllabus.get("items_by_topic") or {}).get(str(n)) or []
            owed[M] = [str(i.get("id")) for i in items if i.get("id")]
    return rows, owed


def fingerprint(rows):
    """What the operator approves: every module's Sub-ILOs, their status and their words."""
    core = sorted((r.get("module", ""), str(r.get("sub_ilo_id", "")), r.get("sub_ilo_status", ""), (r.get("sub_ilo") or "").strip())
                  for r in rows)
    return hashlib.sha256(json.dumps(core, ensure_ascii=False).encode("utf-8")).hexdigest()[:16]


def merged(rows, owed, existing=None):
    """The new map, keeping every field and key the old one had beyond the core."""
    existing = existing or {}
    old = {(mname(r.get("module")) if mkey(r.get("module")) is not None else r.get("module"), str(r.get("sub_ilo_id"))): r
           for r in existing.get("rows", []) or [] if isinstance(r, dict)}
    out_rows = []
    for r in rows:
        prev = old.get((r["module"], r["sub_ilo_id"])) or {}
        extra = {k: v for k, v in prev.items() if k not in CORE and k not in r}
        out_rows.append(dict(r, **extra))
    mods = {r["module"] for r in rows}
    out_rows += [r for k, r in old.items() if k[0] not in mods]     # e.g. a final-assessment row kept by the course's own tool
    m = {k: v for k, v in existing.items() if k not in ("rows", "model_course_items", "written", "ilo_map_hash", "_what", "built_by")}
    m.update({"_what": "The ILO map (build-order step 4): what every module owes. Built by scripts/ilo_map.py from "
                       "programme.json + architecture.json - change those, never this file's core fields.",
              "built_by": "ilo_map.py", "written": date.today().isoformat(), "ilo_map_hash": fingerprint(rows), "rows": out_rows})
    if owed:
        m["model_course_items"] = owed
    elif existing.get("model_course_items"):
        m["model_course_items"] = existing["model_course_items"]
    return m


def build(course, quiet=False):
    """Write working_claude/ilo_map.json. Returns (map, error)."""
    prog, arch = course_files(course)
    if not arch:
        return None, "there is no architecture.json yet - the Main ILOs and Sub-ILOs are written there first (Stage 2)"
    rows, owed = derive(prog, arch, find_syllabus(course))
    p = path(course)
    existing = None
    if os.path.isfile(p):
        try:
            existing = load(p)
        except (OSError, ValueError):
            existing = None
    m = merged(rows, owed, existing)
    save(p, m)
    if not quiet:
        print("The ILO map is written - %d Sub-ILO(s) in %d module(s):\n    %s"
              % (len(rows), len({r["module"] for r in rows}), p))
    return m, None


def read(course):
    p = path(course)
    if not os.path.isfile(p):
        return None
    try:
        m = load(p)
    except (OSError, ValueError):
        return None
    return m if isinstance(m.get("rows"), list) else None


def module_rows(m, module):
    k = mkey(module)
    return [r for r in (m or {}).get("rows", []) or [] if isinstance(r, dict) and mkey(r.get("module")) == k]


def leaves(rows):
    """The Sub-ILOs a module must teach and check: a programme result re-expressed as 1.a and 1.b is met
    through them, so "1" is not asked for on its own when "1.a" exists."""
    ids = [str(r.get("sub_ilo_id")) for r in rows]
    return [i for i in ids if not any(o != i and o.startswith(i + ".") for o in ids)]


def stale(course, m=None):
    """Rows of a module in architecture.json that the file lacks or words differently - [(module, id)]."""
    m = m if m is not None else read(course)
    prog, arch = course_files(course)
    if m is None or not arch:
        return []
    want, _ = derive(prog, arch)
    have = {(mname(r.get("module")) if mkey(r.get("module")) is not None else "", str(r.get("sub_ilo_id"))): r
            for r in m.get("rows", []) if isinstance(r, dict)}
    mods = {r["module"] for r in want}
    diff = [(r["module"], r["sub_ilo_id"]) for r in want
            if (r["module"], r["sub_ilo_id"]) not in have
            or (have[(r["module"], r["sub_ilo_id"])].get("sub_ilo") or "").strip() != r["sub_ilo"].strip()]
    diff += [k for k in have if k[0] in mods and k not in {(r["module"], r["sub_ilo_id"]) for r in want}]
    return diff


SCRIPT_KEYS = ("where_taught", "checked_by", "taught_on", "checked_on")      # the only row fields refresh writes (2.49.2)


def script_tags(v):
    """the Sub-ILO(s) a screen names: "sub_ilo": "1.a" or ["1.a", "1.b"]"""
    return [str(x).strip() for x in (v if isinstance(v, list) else [v]) if x not in (None, "") and str(x).strip()]


def under(tag, sid):
    """a tag meets a row when it is the row's own id or one of the Sub-ILOs below it ("1.a" meets "1")"""
    return tag == sid or tag.startswith(sid + ".")


def refresh_rows(rows, script):
    """The slide and question columns of one module's rows, from its content script's "sub_ilo" tags (F23, 2.49.2).
    Returns (new field values per sub_ilo_id, unknown tags [(screen id, tag)]). Pure - writes nothing."""
    import content_script as cs                       # late: content_script imports this module
    slide_no, sets, _ = cs.plan_of(script)
    screens = script.get("screens", [])
    ids = [str(r.get("sub_ilo_id")) for r in rows]
    unknown = [(s.get("id"), t) for s in screens for t in script_tags(s.get("sub_ilo")) if t not in ids]
    made = {}
    for sid in ids:
        slides = [s for s in screens if s.get("kind") in ("slide", "activity") and any(under(t, sid) for t in script_tags(s.get("sub_ilo")))]
        by_set = []
        for st in sets:
            q = [x["id"] for x in st["questions"] if any(under(t, sid) for t in script_tags(x.get("sub_ilo")))]
            if q:
                by_set.append((st["id"], q))
        made[sid] = {"where_taught": "; ".join("slide %d %s" % (slide_no[s["id"]], s.get("title", "")) for s in slides),
                     "checked_by": " · ".join("%s %s" % (k, ", ".join(q)) for k, q in by_set),
                     "taught_on": [s["id"] for s in slides], "checked_on": [i for _, q in by_set for i in q]}
    return made, unknown


def refresh(course, module=None, write=True):
    """Refresh the slide/question rows of the ILO map from the modules' content scripts (working_claude/script/MNN.json).
    Only where_taught, checked_by, taught_on, checked_on of a row change - never the Main ILO, the Sub-ILO or any other
    wording (the approval stays valid). A module with no script is left as it is. Returns (report lines, error)."""
    m = read(course)
    if m is None:
        return [], "there is no ILO map yet"
    only = mkey(module) if module is not None else None
    report, changed = [], False
    for k in sorted({mkey(r.get("module")) for r in m["rows"] if isinstance(r, dict) and isinstance(mkey(r.get("module")), int)}):
        if only is not None and k != only:
            continue
        if all(str(r.get("sub_ilo_id")) in ("-", "") for r in module_rows(m, k)):      # the final assessment's own row
            continue
        sp = workspace.claude_path(course, "script", "%s.json" % mname(k))
        if not os.path.isfile(sp):
            report.append("%s: no content script yet - rows left as they are" % mname(k))
            continue
        rows = module_rows(m, k)
        made, unknown = refresh_rows(rows, load(sp))
        n = 0
        for r in rows:
            new = made[str(r.get("sub_ilo_id"))]
            if any(r.get(f) != new[f] for f in SCRIPT_KEYS):
                r.update(new)
                n += 1
        changed = changed or n > 0
        need = [str(r.get("sub_ilo_id")) for r in rows if str(r.get("sub_ilo_id")) in leaves(rows)]
        gaps = ["%s not taught on any slide" % i for i in need if not made[i]["taught_on"]] + \
               ["%s not checked by any question" % i for i in need if not made[i]["checked_on"]]
        report.append("%s: %d of %d row(s) refreshed from %s%s%s" % (
            mname(k), n, len(rows), os.path.basename(sp),
            ("; unknown tag(s): " + ", ".join("%s on %s" % (t, s) for s, t in unknown)) if unknown else "",
            ("; " + "; ".join(gaps)) if gaps else ""))
    # 2.63.3 (the 2.63.2 full-course run: 186 of 268 model-course rows still said "planned - module not built yet" after
    # every module was built) - an item list beside the rows (mc713_items ...: "module" + "status") follows its module's script
    built, items = {}, 0
    for key, lst in list(m.items()):
        if key == "rows" or not isinstance(lst, list):
            continue
        for it in lst:
            if not (isinstance(it, dict) and str(it.get("status") or "").startswith("planned - module not built")):
                continue
            k = mkey(it.get("module"))
            if not isinstance(k, int) or (only is not None and k != only):
                continue
            if k not in built:
                built[k] = os.path.isfile(workspace.claude_path(course, "script", "%s.json" % mname(k)))
            if not built[k]:
                continue
            tag = (re.match(r"\s*([\w.]+)", str(it.get("sub_ilo") or "")) or [None, ""])[1]
            hit = [r for r in module_rows(m, k) if tag and r.get("taught_on") and under(str(r.get("sub_ilo_id")), tag)]
            it["status"] = ("taught: %s" % "; ".join(r.get("where_taught") or "" for r in hit[:2])) if hit else \
                "module built - %s" % ("Sub-ILO %s not tagged on a slide" % tag if tag else "see its Sub-ILO rows")
            changed, items = True, items + 1
    if items:
        report.append("model-course items: %d \"planned - module not built\" item(s) of built modules refreshed" % items)
    if write and changed:
        m["script_synced"] = date.today().isoformat()
        save(path(course), m)
    return report, None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("build", "show", "check", "refresh"):
        s = sub.add_parser(name)
        s.add_argument("course")
        if name == "show":
            s.add_argument("--module", required=True)
        if name == "refresh":
            s.add_argument("--module", help="one module (default: every module that has a script)")
            s.add_argument("--dry-run", action="store_true", help="say what would change; write nothing")
    a = ap.parse_args(argv)
    a.course = workspace.work_folder(a.course, create=False)
    if a.cmd == "build":
        m, err = build(a.course)
        if err:
            print("Stopped - nothing was written: %s." % err)
            return 2
        return 0
    m = read(a.course)
    if m is None:
        print("There is no ILO map yet:\n    %s\n  It is written with the Stage 2 page (make_architecture_page.py), or with: ilo_map.py build <course>."
              % path(a.course))
        return 2
    if a.cmd == "refresh":
        lines, err = refresh(a.course, a.module, write=not a.dry_run)
        for x in lines:
            print("  " + x)
        print("%s - the Main ILO and Sub-ILO wording is untouched." % ("Nothing written (--dry-run)" if a.dry_run else "The ILO map's slide and question rows are refreshed"))
        return 0
    if a.cmd == "check":
        d = stale(a.course, m)
        if d:
            print("The ILO map is out of date - it does not say what architecture.json says for: %s.\n"
                  "  Make the Stage 2 page again (or ilo_map.py build) and show it to the operator." % ", ".join("%s %s" % x for x in d[:12]))
            return 1
        print("The ILO map matches architecture.json - %d row(s)." % len(m.get("rows", [])))
        return 0
    rows = module_rows(m, a.module)
    if not rows:
        print("Module %s has no rows in the ILO map." % a.module)
        return 1
    r0 = rows[0]
    print("%s - %s\n  Programme topic: %s\n  Main ILO (verbatim, L2): %s\n" % (mname(a.module), r0.get("module_title", ""), r0.get("topic", ""), r0.get("main_ilo", "")))
    need = set(leaves(rows))
    for r in rows:
        print("  %-6s %-13s %s%s%s" % (r.get("sub_ilo_id"), "[" + (r.get("sub_ilo_status") or "") + "]", r.get("sub_ilo", ""),
                                       ("\n         model course: " + ", ".join(r["model_course"])) if r.get("model_course") else "",
                                       "" if str(r.get("sub_ilo_id")) in need else "\n         (met through the Sub-ILOs below it)"))
    owed = (m.get("model_course_items") or {}).get(mname(a.module)) or []
    if owed:
        print("\n  Model-course items under this topic (%d): %s" % (len(owed), ", ".join(owed)))
    print("\n  Every Sub-ILO without \"(met through ...)\" is taught on a slide (\"sub_ilo\") and checked by a question (\"sub_ilo\").")
    return 0


if __name__ == "__main__":
    sys.exit(main())
