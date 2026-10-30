#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""The ILO map of a course as the admin shows it - every Sub-ILO, where it is taught, where it is checked (2.83.0).

    ilo_coverage.py <course folder> [<output file>]

The course folder is the factory's: working_claude/ beside modules/. ilo_map.json says what every module owes; the
approved scripts (working_claude/script/M01.json ... FINAL.json) tag every slide and every question with its
Sub-ILO; assessment_map.json names the practical exercises. Nothing is typed here - the file is read off those, so
it says what the course does, not what somebody hoped it did.

It is written to modules/_course_shell/ilo_coverage.json. The classroom's importer keeps _course_shell/ under
instructor/, so it is published with the course and never reaches a trainee tablet. compile_course.py calls it on
every build, so a course carries its map without anyone running it.

    {"kind": "ilo-coverage", "version": 1, "course", "built", "approved", "final_rule", "main": [...],
     "modules": [...], "rows": [{main, id, text, status, programme, module, module_title,
                                 taught: [{slide, title, module}], checked: [{set, kind, module, q: [...]}],
                                 practical: [{id, title, module, place?}], final: N, whole?, exam?}]}

A port of tools/ilo-coverage.mjs of the training app (the format is the admin panel's), kept line for line so the two
write the same file. Exit 0 written; 1 no ILO map or no modules folder; 2 usage.
"""
from __future__ import annotations

import io
import json
import os
import re
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import workspace  # noqa: E402

OUT_REL = os.path.join("_course_shell", "ilo_coverage.json")


def load(path):
    with io.open(path, encoding="utf-8-sig") as f:
        return json.load(f)


def js_str(x):
    """JavaScript's String(x): None is "" here (the tool only ever calls it on x ?? '')."""
    if x is None:
        return ""
    if isinstance(x, bool):
        return "true" if x else "false"
    if isinstance(x, float) and x == int(x):
        return str(int(x))
    if isinstance(x, list):                                  # a script may tag a screen "sub_ilo": ["1.b", "1.c"]
        return ",".join(js_str(i) for i in x)
    return str(x)


def natural(s):
    """localeCompare(.., 'en', {numeric: true}): digits by value, letters without regard to case."""
    return [(0, int(p), "") if p.isdigit() else (1, 0, p.lower()) for p in re.split(r"(\d+)", s) if p != ""]


def mod_code(m):
    n = re.search(r"\d+", js_str(m))
    return "M" + n.group(0).rjust(2, "0") if n else js_str(m or "")


def main_of(r):
    ids = r.get("main_ilo_ids")
    first = ids[0] if ids else None
    if first:
        return js_str(first)
    m = re.match(r"\s*(\d+)\.", js_str(r.get("main_ilo") or ""))
    if m:
        return m.group(1)
    return js_str(r.get("sub_ilo_id") or "").split(".")[0]


def clean(s):
    s = re.sub(r"^\s*\d+\.\s*", "", js_str(s or ""))
    return re.sub(r"[;\s]+$", "", s).strip()


def get_dict(d, k):
    v = d.get(k)
    return v if isinstance(v, dict) else {}


def build(root, out=None):
    """-> (doc, report). root is the course folder (working_claude/ and modules/). Nothing is written."""
    work = os.path.join(root, workspace.CLAUDE)
    has = os.path.exists
    map_ = load(os.path.join(work, "ilo_map.json"))
    arch = load(os.path.join(work, "architecture.json")) if has(os.path.join(work, "architecture.json")) else {}
    assess = load(os.path.join(work, "assessment_map.json")) if has(os.path.join(work, "assessment_map.json")) else {}

    # What each module owes, in the factory's order.
    rows = []
    for r in map_.get("rows") or []:
        row = {
            "main": main_of(r), "id": js_str(r.get("sub_ilo_id")), "text": r.get("sub_ilo") or "",
            "status": r.get("sub_ilo_status") or "", "programme": r.get("programme_wording") or "",
            "module": mod_code(r.get("module")), "module_title": r.get("module_title") or "",
            "taught": [], "checked": [], "practical": [], "final": 0,
        }
        # A pilot's map carries its own words for where and how; they are kept for a module whose script does
        # not tag its screens.
        if r.get("where_taught"):
            row["note_taught"] = r["where_taught"]
        if r.get("assessed"):
            row["note_assessed"] = r["assessed"]
        rows.append(row)

    def row_of(module, id_):
        return next((r for r in rows if r["module"] == module and r["id"] == id_), None)

    def any_row(id_):
        return [r for r in rows if r["id"] == id_]

    main_text = {}
    for m in arch.get("main_ilos") or []:
        main_text[js_str(m.get("id"))] = clean(m.get("text"))
    for r in map_.get("rows") or []:
        mo = main_of(r)
        if mo not in main_text and re.search(r"\w", mo) and r.get("main_ilo"):
            main_text[mo] = clean(r["main_ilo"])

    # Every slide and question of every approved script. A deck slide is a screen without a task set; its number
    # is its place in the deck, as the instructor sees it.
    script_dir = os.path.join(work, "script")
    scripts = sorted((f for f in (os.listdir(script_dir) if os.path.isdir(script_dir) else [])
                      if re.fullmatch(r"(M\d+|FINAL)\.json", f, re.I)), key=natural)
    lost = []
    for f in scripts:
        s = load(os.path.join(script_dir, f))
        module = "final" if re.match(r"final", f, re.I) else mod_code(f)
        slide = 0
        checks = {}
        for x in s.get("screens") or []:
            if not x.get("set"):
                slide += 1
            # A screen may serve two Sub-ILOs ("1.b,1.c"); it counts for each.
            for id_ in [p for p in re.split(r"[,;\s]+", js_str(x.get("sub_ilo") or "")) if p]:
                if module == "final":
                    owners = any_row(id_)
                    if not owners:
                        lost.append("FINAL %s -> %s" % (x.get("id"), id_))
                    for r in owners:
                        r["final"] += 1
                    continue
                r = row_of(module, id_) or (any_row(id_) or [None])[0]
                if r is None:
                    lost.append("%s %s -> %s" % (module, x.get("id"), id_))
                    continue
                if not x.get("set") and x.get("kind") == "activity":
                    r["practical"].append({"id": x.get("exercise") or x.get("id"), "title": x.get("title") or "", "module": module})
                elif not x.get("set"):
                    r["taught"].append({"slide": slide, "title": x.get("title") or "", "module": module})
                else:
                    key = "%s|%s|%s" % (r["module"], r["id"], x["set"])
                    if key not in checks:
                        checks[key] = {"set": x["set"], "kind": x.get("kind") or "", "module": module, "q": []}
                        r["checked"].append(checks[key])
                    checks[key]["q"].append(x.get("id"))
    # A module's own outcome row ("6" beside 6.a ... 6.e) is met through its Sub-ILOs; only a module with no
    # Sub-ILO of its own is taught and checked against it directly.
    for r in rows:
        if "." not in r["id"] and any(o is not r and o["module"] == r["module"] and o["id"].startswith(r["id"] + ".") for o in rows):
            r["whole"] = True
    # The final assessment's row owes no outcome of its own ("-"): it says how the course is examined.
    for r in rows:
        if not re.search(r"\w", r["id"]):
            r["whole"] = True
            r["exam"] = True
    # Exercises the assessment map assigns to a Sub-ILO, when the deck's activity slide did not.
    for e in assess.get("exercises") or []:
        for id_ in e.get("sub_ilos") or []:
            id_ = js_str(id_)
            r = row_of(mod_code(e.get("module")), id_) or (any_row(id_) or [None])[0]
            if r is not None and not any(p["title"] == e.get("title") or js_str(p["id"]) == js_str(e.get("id")) for p in r["practical"]):
                r["practical"].append({"id": e.get("id"), "title": e.get("title") or "", "module": mod_code(e.get("module")),
                                       "place": e.get("place") or ""})

    modules = []
    for r in rows:
        if not any(m["code"] == r["module"] for m in modules):
            modules.append({"code": r["module"], "title": r["module_title"]})
    approved = arch.get("approved")
    doc = {
        "kind": "ilo-coverage", "version": 1,
        "course": get_dict(arch, "course").get("title") or "",
        "built": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "approved": {"by": approved.get("by") or "", "on": approved.get("on") or ""} if isinstance(approved, dict) and approved else None,
        "final_rule": get_dict(assess, "final_test").get("rule") or "",
        "main": [{"id": i, "text": t} for i, t in sorted(main_text.items(), key=lambda kv: natural(kv[0]))],
        "modules": modules,
        "rows": [],
    }
    for r in rows:
        o = dict(r)
        for k in ("taught", "checked", "practical"):
            if not o[k]:
                del o[k]
        if not o["final"]:
            del o["final"]
        doc["rows"].append(o)

    owed = [r for r in rows if not r.get("whole")]
    report = {
        "rows": len(rows), "modules": len(modules), "scripts": len(scripts), "lost": lost,
        "not_taught": [r for r in owed if not r["taught"] and not r["practical"] and not r.get("note_taught")],
        "not_checked": [r for r in owed if not r["checked"] and not r["final"] and not r["practical"] and not r.get("note_assessed")],
    }
    return doc, report


def write(doc, out):
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with io.open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(doc, ensure_ascii=False, indent=1) + "\n")


def summary(root, doc, report, out):
    ids = lambda rs: ", ".join("%s %s" % (r["module"], r["id"]) for r in rs) or "none"
    lines = ["%s: %d Sub-ILO rows in %d modules, %d scripts read." % (doc["course"] or root, report["rows"], report["modules"], report["scripts"]),
             "Not taught on any slide: " + ids(report["not_taught"]),
             "Not checked by any question or exercise: " + ids(report["not_checked"])]
    if report["lost"]:
        lost = report["lost"]
        lines.append("Tagged with a Sub-ILO the map does not have (%d): %s%s" % (len(lost), ", ".join(lost[:12]), " ..." if len(lost) > 12 else ""))
    lines.append("Written: " + out)
    return "\n".join(lines)


def make(course, out=None):
    """The compiler's call: write modules/_course_shell/ilo_coverage.json. -> (path or None, printed text).
    A course with no ILO map or no modules folder gets no file and a line saying why; it never raises."""
    root = workspace.work_folder(course, create=False)
    mp = os.path.join(root, workspace.CLAUDE, "ilo_map.json")
    if not os.path.isfile(mp):
        return None, "No ILO map: %s" % mp
    here = os.path.join(root, workspace.MODULES)
    if out is None:
        out, folder = os.path.join(here, OUT_REL), here      # _course_shell/ itself is made
    else:
        folder = os.path.dirname(os.path.abspath(out))
    if not os.path.isdir(folder):
        return None, "No published course here: %s" % folder
    try:
        doc, report = build(root, out)
    except (ValueError, OSError) as e:
        return None, "The ILO coverage was not written - %s" % e
    write(doc, out)
    return out, summary(root, doc, report, out)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 2
    path, text = make(argv[0], argv[1] if len(argv) > 1 else None)
    print(text)
    return 0 if path else 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
