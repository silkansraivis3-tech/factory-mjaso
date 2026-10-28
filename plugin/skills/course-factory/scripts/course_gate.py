#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""The gate before any module: an approved ILO map and a recorded knowledge-base decision (2.42.0).

    course_gate.py <course> [--module 4]      exit 0: a module may start; exit 2: what has to happen first

WHY THIS EXISTS
Owner, 2026-10-16: "before creating any module the AI should have already made the ILO mapping and
suggested for KNOWLEDGE_BASE to be created". A session building IGF Module 4 got neither until a
follow-up message - nothing in the factory stopped a module's script being written first. Now three
things must stand before a module's content script is started or approved (content_script.py), a
build sheet is started (compile_module.py --init-build), or a module agent runs (build_course.js):

  1. working_claude/ilo_map.json - the ILO map, built from architecture.json (scripts/ilo_map.py);
  2. the Stage 2 page approved, and the Sub-ILOs not changed since - architecture.json "approved":
     {"by", "on", "ilo_map_hash"}, written by make_architecture_page.py --approve --by "<name>";
  3. a knowledge-base decision in working_claude/intake.json - "knowledge_base_decision": yes, built,
     or declined with the operator's reason (kb_tool.py decision). A declined one is allowed; the
     Stage 2 page keeps showing it.

2.73.0 - only the record kb_tool.py decision writes counts: "knowledge_base_decision" with its answer
and date, and for yes / built a folder that IS a knowledge base now. The older intake field
"knowledge_base" never does (chem advanced, 2026-10-27: the reader wrote it with the path of a
knowledge base still being built, and the gate and --approve both passed on it). A module whose
script was approved before this gate existed keeps its approval: nothing here touches a script.

Standard library only.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import workspace  # noqa: E402
import ilo_map  # noqa: E402

ANSWERS = ("yes", "built", "declined")


def _load(p):
    try:
        with io.open(p, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def intake(course):
    return _load(workspace.claude_path(course, "intake.json")) or {}


def is_kb(path):
    """a folder the factory can read as a knowledge base - kb_tool.detect's two shapes"""
    return isinstance(path, str) and bool(path.strip()) and (
        os.path.isfile(os.path.join(path, "SOURCE_MANIFEST.json")) and os.path.isdir(os.path.join(path, "sources"))
        or os.path.isfile(os.path.join(path, "00_INDEX", "SOURCE_MANIFEST.json")))


def kb_decision(course):
    """{"answer": yes|built|declined, "path", "format", "reason", "decided"} - or None when no real decision is recorded.
    2.73.0: only kb_tool.py decision's record, with its date; a yes / built one names a folder that is a knowledge base."""
    d = intake(course).get("knowledge_base_decision")
    if not isinstance(d, dict) or d.get("answer") not in ANSWERS or not d.get("decided"):
        return None
    if d["answer"] == "declined":
        return dict(d) if (d.get("reason") or "").strip() else None
    paths = d.get("path") if isinstance(d.get("path"), list) else [d.get("path")]
    return dict(d) if paths and all(is_kb(x) for x in paths) else None


def kb_problem(course):
    """why there is no knowledge-base decision, said so the next step is plain (2.73.0)"""
    i = intake(course)
    d = i.get("knowledge_base_decision")
    cmd = "kb_tool.py decision <course> --yes <folder> | --built <folder> | --declined \"<their reason>\""
    if isinstance(d, dict) and d.get("answer") in ("yes", "built") and d.get("decided"):
        return ("The knowledge-base decision names %s, which is not a knowledge base the factory can read (yet) - wait until it "
                "is built, then record it again: %s" % (d.get("path"), cmd))
    if i.get("knowledge_base") and not isinstance(d, dict):
        return ("intake.json names a knowledge base (\"knowledge_base\"), but that is an intake field, not a decision. Record "
                "the operator's answer: %s" % cmd)
    return ("Nobody has decided yet whether this course gets a knowledge base. At intake: kb_tool.py find <the course "
            "material folder>. If none is found it suggests making one - tell the operator, and record their answer: " + cmd)


def approval(arch):
    a = (arch or {}).get("approved")
    return a if isinstance(a, dict) and a.get("by") and a.get("ilo_map_hash") else None


def current_hash(course):
    prog, arch = ilo_map.course_files(course)
    rows, _ = ilo_map.derive(prog, arch)
    return ilo_map.fingerprint(rows), rows


def problems(course, module=None):
    """What still has to happen before a module may start - plain sentences, each saying what to do. [] = open."""
    out = []
    prog, arch = ilo_map.course_files(course)
    page = "make_architecture_page.py --course \"%s\"" % course
    if not arch:
        out.append("The course architecture is not written yet (Stage 2: working_claude\\architecture.json - the modules, "
                   "the Main ILOs and every Sub-ILO). Write it, make the Stage 2 page (%s) and show it to the operator." % page)
    m = ilo_map.read(course)
    if arch and m is None:
        out.append("There is no ILO map yet (working_claude\\ilo_map.json). Making the Stage 2 page writes it: %s" % page)
    elif arch and ilo_map.stale(course, m):
        out.append("The ILO map is out of date - it does not say what architecture.json says. Make the Stage 2 page again (%s) "
                   "and show it to the operator." % page)
    if arch:
        ok = approval(arch)
        h, rows = current_hash(course)
        if not ok:
            out.append("The operator has not approved the Stage 2 page yet - the module split, the hours and the ILO map. "
                       "Show them to_review\\ARCHITECTURE_REVIEW.html; when they say \"next\", record it: "
                       "%s --approve --by \"<their name>\"" % page)
        elif ok["ilo_map_hash"] != h:
            out.append("The Sub-ILOs changed after the operator approved the Stage 2 page on %s. Make the page again, show "
                       "what changed, and record the new approval: %s --approve --by \"<their name>\"" % (ok.get("on", "?"), page))
        if module is not None and ilo_map.mkey(module) != "final" and m is not None and not ilo_map.module_rows(m, module):
            out.append("Module %s has no Sub-ILO in the ILO map - write its Sub-ILOs into architecture.json, make the Stage 2 "
                       "page again and have it approved." % module)
    if kb_decision(course) is None:
        out.append(kb_problem(course))
    return out


def stop_message(module, probs, what="started"):
    who = "Module %s" % module if module is not None else "No module"
    return ("Stopped - nothing was written. %s cannot be %s yet: every module is written against the approved\n"
            "ILO map, with the knowledge-base decision made (owner, 2026-10-16). First:\n%s"
            % (who, what, "\n".join("  - " + p for p in probs)))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("course")
    ap.add_argument("--module")
    a = ap.parse_args(argv)
    course = workspace.work_folder(a.course, create=False)
    probs = problems(course, a.module)
    if probs:
        print(stop_message(a.module, probs))
        return 2
    d = kb_decision(course)
    arch = ilo_map.course_files(course)[1]
    ok = approval(arch)
    print("Open - the ILO map was approved by %s on %s; knowledge base: %s.%s" % (
        ok["by"], ok.get("on", "?"), d["answer"] + ((" (" + d["reason"] + ")") if d.get("reason") else ""),
        ("\n  Module %s's rows: ilo_map.py show <course> --module %s" % (a.module, a.module)) if a.module else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
