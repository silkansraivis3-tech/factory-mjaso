#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""figure_library.py - the drawings a module passed with, kept for the next slide that draws the same things (2.67.0).

    figure_library.py save <course> --module 1      keep every kit drawing of a module that passed its build
    figure_library.py list [<course>]               what the libraries hold

WHY (owner, 2026-10-26: "optimise as much as I can"; the timed gas M02 build): 90 % of a builder's time is designing the
module's ~20 drawings, and the gas course's 22 modules draw the same things again and again - tank types, a cargo's
vapour pressure, a detector on a compressor room. A drawing that passed a build is saved; the next slide that names the
same things starts from it (compile_module.starter_figure, through find()) instead of a grid of placeholders - its parts
as they were, its steps made again for that slide's own lines.

Two libraries, both read and both written: the course's own (working_claude/figure_library/), and this computer's
(%USERPROFILE%/.novikontas/figure-library, or NOVIKONTAS_FIGURE_LIBRARY) - a drawing one course passed with is there for
the next course. Nothing in the factory depends on either: an empty library is a grid starter, as before.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "scripts"))
INDEX = "index.json"
MIN_SHARED, MIN_COVER = 2, 0.6       # a slide reuses a drawing that names at least two of its things and 60 % of them


def norm(t):
    return " ".join(re.findall(r"[a-z0-9]+", str(t or "").lower()))


def dirs(course=None):
    """the libraries: the course's own, then this computer's"""
    out = []
    if course:
        import workspace
        out.append(workspace.claude_path(workspace.work_folder(course, create=False), "figure_library"))
    if os.environ.get("NOVIKONTAS_FIGURE_LIBRARY"):
        out.append(os.environ["NOVIKONTAS_FIGURE_LIBRARY"])
    elif not course or not os.path.abspath(course).lower().startswith(os.path.abspath(tempfile.gettempdir()).lower()):
        # a course in the temp folder (every test's) never reads or fills this computer's library: a test's sample
        # drawings would turn up as a real course's starters, and a test's starters would depend on what ran before
        out.append(os.path.join(os.path.expanduser("~"), ".novikontas", "figure-library"))
    return out


def labels_of(spec):
    """the things a drawing names: its parts' labels and text callouts, normalised"""
    out = []
    for p in spec.get("parts") or []:
        if isinstance(p, dict):
            for k in ("label", "text", "formula"):
                if isinstance(p.get(k), str) and norm(p[k]):
                    out.append(norm(p[k]))
    return sorted(set(out))


def load(d):
    try:
        return json.load(io.open(os.path.join(d, INDEX), encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save(course, module):
    """every kit drawing the module's build sheet shows, into both libraries - called when the module passes its build"""
    import compile_module as cm
    import content_script as cs
    m = cs.mid(module)
    try:
        build = cs.load(cm.build_path(course, module))
    except (OSError, ValueError):
        return 0
    import workspace
    figdir = workspace.claude_path(workspace.work_folder(course, create=False), "figures", m)
    kept = 0
    for sid, b in sorted((build.get("screens") or {}).items()):
        rel = str(b.get("figure") or "")
        if not rel.endswith(".kit.json") or not os.path.isfile(os.path.join(figdir, rel)):
            continue
        try:
            spec = json.load(io.open(os.path.join(figdir, rel), encoding="utf-8"))
        except (OSError, ValueError):
            continue
        labs = labels_of(spec)
        if len(labs) < MIN_SHARED or spec.get("_todo"):
            continue
        body = json.dumps({k: v for k, v in spec.items() if k != "steps"}, sort_keys=True, ensure_ascii=False)
        key = hashlib.sha1(body.encode("utf-8")).hexdigest()[:16]
        for d in dirs(course):
            try:
                os.makedirs(d, exist_ok=True)
                io.open(os.path.join(d, key + ".kit.json"), "w", encoding="utf-8").write(json.dumps(spec, ensure_ascii=False, indent=1))
                idx = load(d)
                idx[key] = {"labels": labs, "types": sorted({p.get("type") for p in spec.get("parts") or [] if isinstance(p, dict)}),
                            "from": "%s %s %s" % (os.path.basename(os.path.dirname(os.path.abspath(course))) or course, m, sid),
                            "saved": time.strftime("%Y-%m-%d")}
                io.open(os.path.join(d, INDEX), "w", encoding="utf-8").write(json.dumps(idx, ensure_ascii=False, indent=1, sort_keys=True))
            except OSError:
                continue
        kept += 1
    return kept


def find(course, labels):
    """(spec, where it is from) - the saved drawing that names most of `labels` (at least MIN_SHARED of them and MIN_COVER of
    the slide's), the course's own library first; None when none does"""
    want = {norm(x) for x in labels if norm(x)}
    if not course or len(want) < MIN_SHARED:           # no course (a starter made on its own): no library
        return None
    best = None
    for rank, d in enumerate(dirs(course)):
        for key, e in load(d).items():
            have = set(e.get("labels") or [])
            shared = len(want & have)
            if shared < MIN_SHARED or shared < MIN_COVER * len(want):
                continue
            score = (shared / float(len(want | have)), -rank)
            if best is None or score > best[0]:
                best = (score, d, key, e)
    if not best:
        return None
    try:
        spec = json.load(io.open(os.path.join(best[1], best[2] + ".kit.json"), encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return spec, best[3].get("from") or ""


def main(argv=None):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sp = ap.add_subparsers(dest="cmd", required=True)
    sv = sp.add_parser("save")
    sv.add_argument("course")
    sv.add_argument("--module", required=True)
    ls = sp.add_parser("list")
    ls.add_argument("course", nargs="?")
    a = ap.parse_args(argv)
    if a.cmd == "save":
        print("kept %d drawing(s) in %s" % (save(a.course, a.module), " and ".join(dirs(a.course))))
        return 0
    for d in dirs(a.course):
        idx = load(d)
        print("%s - %d drawing(s)" % (d, len(idx)))
        for k, e in sorted(idx.items(), key=lambda kv: kv[1].get("from", "")):
            print("  %s  %-28s %s" % (k, e.get("from", "")[:28], ", ".join(e.get("labels") or [])[:90]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
