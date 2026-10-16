#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""The ILO map - what every module owes, built from the Stage 2 files, never typed twice (2.38.0).

    ilo_map.py build <course>                 write working_claude/ilo_map.json from programme.json + architecture.json
    ilo_map.py show  <course> --module 4      a module's rows - what its content script is written against
    ilo_map.py check <course>                 is ilo_map.json there, and does it say what architecture.json says?

WHY THIS EXISTS
Owner, 2026-10-16: "before creating any module the AI should have already made the ILO mapping".
Until 2.38.0 the ILO map was a build step with no file: a module's script could be written and
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

Standard library only.
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import io
import json
import os
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
    for am in sorted(arch.get("modules", []) or [], key=lambda m: mkey(m.get("module")) or 0):
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


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("build", "show", "check"):
        s = sub.add_parser(name)
        s.add_argument("course")
        if name == "show":
            s.add_argument("--module", required=True)
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
