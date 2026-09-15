#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""L24 - which parts of this module are somebody's decision?

    detect_expert_edits.py <module_dir>              what is protected, and why
    detect_expert_edits.py <module_dir> --record      write the build record
    detect_expert_edits.py <module_dir> --json

WHY THIS EXISTS
Law 5 says the existing delivery implementation is not preserved by default - rebuild
it. That is right for material nobody has touched since it was generated, and exactly
wrong for a screen a maritime expert went in and changed on purpose.

The difference between the two is not what the code looks like. Good expert edits often
look untidy and generated filler often looks deliberate, so judging by eye is the one
thing this script refuses to do. It answers a narrower question that can actually be
answered: WHO LAST TOUCHED THIS FILE.

  1  the expert said so         data-sme=, <!-- SME: -->, _sme/
  2  the factory's own record   _factory/build.json - the hash no longer matches
  3  version control            a commit the factory did not author
  4  nothing to go on           ASK. Never assume untouched because you cannot
                                prove touched.

A protected region is treated as LOCKED CONTENT: restyle it, never rewrite it. Where it
breaks a factory law, REPORT the conflict and propose the fix - do not apply it. An
expert who finds their change quietly corrected stops making changes, and the course
loses the only maritime judgement in it.

`knowledge/expert-edits.json` is the authority. Edit that file, not this script.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
LANE = os.path.dirname(HERE)
RULES = os.path.join(LANE, "knowledge", "expert-edits.json")
RECORD = os.path.join("_factory", "build.json")

COURSE_EXT = (".html", ".htm", ".css", ".js", ".json", ".md", ".svg")
SKIP_DIR = {"_factory", "_work", "__pycache__", ".git", "node_modules",
            "oldversion", "retired", "_visual_briefs"}

SME_ATTR = re.compile(r'<[^>]*\bdata-sme(?:=("([^"]*)"|\'([^\']*)\'))?[^>]*>', re.I)
SME_COMMENT = re.compile(r"<!--\s*SME\s*[:\-]\s*(.*?)-->", re.S | re.I)


def load_rules():
    with open(RULES, encoding="utf-8-sig") as fh:
        return json.load(fh)


def course_files(module):
    for dp, dn, fn in os.walk(module):
        dn[:] = [d for d in dn if d not in SKIP_DIR]
        for f in sorted(fn):
            if os.path.splitext(f)[1].lower() in COURSE_EXT:
                p = os.path.join(dp, f)
                yield p, os.path.relpath(p, module).replace("\\", "/")


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def line_of(raw, pos):
    return raw.count("\n", 0, pos) + 1


def markers_in(path, rel):
    """Signal 1 - a person left a note. The cheapest and most reliable evidence."""
    out = []
    try:
        raw = io.open(path, encoding="utf-8", errors="replace").read()
    except OSError:
        return out
    for m in SME_ATTR.finditer(raw):
        why = (m.group(2) or m.group(3) or "").strip()
        out.append({"rel": rel, "line": line_of(raw, m.start()), "signal": "marker",
                    "what": "data-sme" + (' = "%s"' % why if why else ""),
                    "note": why or "no reason given - protected anyway"})
    for m in SME_COMMENT.finditer(raw):
        out.append({"rel": rel, "line": line_of(raw, m.start()), "signal": "marker",
                    "what": "<!-- SME: ... -->",
                    "note": re.sub(r"\s+", " ", m.group(1)).strip()[:160]})
    return out


def git_touched(module):
    """Signal 3 - only where the course is in git, which a desktop folder rarely is."""
    try:
        top = subprocess.run(["git", "-C", module, "rev-parse", "--show-toplevel"],
                             capture_output=True, text=True, timeout=10)
        if top.returncode != 0:
            return None
        log = subprocess.run(
            ["git", "-C", module, "log", "--no-merges", "--format=%H%x1f%an%x1f%s",
             "--name-only", "--", "."],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30)
        if log.returncode != 0:
            return None
    except (OSError, subprocess.SubprocessError):
        return None

    human = {}
    author = subject = None
    for line in log.stdout.split("\n"):
        if "\x1f" in line:
            _, author, subject = line.split("\x1f", 2)
            continue
        f = line.strip()
        if not f or author is None:
            continue
        # A commit the factory authored is the factory's own work, not a person's.
        if "claude" in author.lower() or "course factory" in (subject or "").lower():
            continue
        human.setdefault(os.path.basename(f), (author, subject))
    return human


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("module")
    ap.add_argument("--record", action="store_true",
                    help="write _factory/build.json - run at the END of a build, after "
                         "verification passes")
    ap.add_argument("--version", default="", help="factory version, for the record")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    if not os.path.isdir(a.module):
        sys.stderr.write("not a folder: %s\n" % a.module)
        return 2
    load_rules()  # fail loudly if the authority file is broken

    files = list(course_files(a.module))
    rec_path = os.path.join(a.module, RECORD)

    if a.record:
        os.makedirs(os.path.dirname(rec_path), exist_ok=True)
        doc = {"_what": "Every course-facing file this factory wrote, and its hash. A file "
                        "whose hash no longer matches was changed by a person afterwards, "
                        "and L24 protects it.",
               "factory_version": a.version or "unrecorded",
               "written": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
               "files": {rel: sha(p) for p, rel in files}}
        io.open(rec_path, "w", encoding="utf-8", newline="\n").write(
            json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
        print("build record written: %s\n  %d file(s). The next retrofit will protect "
              "anything that has changed since." % (rec_path, len(files)))
        return 0

    # ---- signal 1 · the expert said so ------------------------------------
    found = []
    for p, rel in files:
        if os.path.splitext(rel)[1].lower() in (".html", ".htm", ".md"):
            found.extend(markers_in(p, rel))
    sme_dir = os.path.join(a.module, "_sme")
    if os.path.isdir(sme_dir):
        for f in sorted(os.listdir(sme_dir)):
            found.append({"rel": "_sme/" + f, "line": 0, "signal": "marker",
                          "what": "a file the expert left in _sme/",
                          "note": "read it before changing anything it refers to"})

    # ---- signal 2 · the factory's own build record ------------------------
    record = None
    changed, added = [], []
    if os.path.exists(rec_path):
        try:
            record = json.load(io.open(rec_path, encoding="utf-8-sig"))
        except ValueError:
            record = None
    if record:
        known = record.get("files", {})
        for p, rel in files:
            h = sha(p)
            if rel not in known:
                added.append(rel)
            elif known[rel] != h:
                changed.append(rel)
        for rel in changed:
            found.append({"rel": rel, "line": 0, "signal": "build-record",
                          "what": "changed since the factory wrote it",
                          "note": "last factory build %s" % record.get("written", "?")})
        for rel in added:
            found.append({"rel": rel, "line": 0, "signal": "build-record",
                          "what": "added after the factory wrote this module",
                          "note": "the factory did not create this file"})

    # ---- signal 3 · version control ---------------------------------------
    human_git = git_touched(a.module) if not record else None
    if human_git:
        for p, rel in files:
            base = os.path.basename(rel)
            if base in human_git and not any(f["rel"] == rel for f in found):
                who, subj = human_git[base]
                found.append({"rel": rel, "line": 0, "signal": "git",
                              "what": "last touched by a commit the factory did not author",
                              "note": "%s - %s" % (who, (subj or "")[:80])})

    state = ("marker" if any(f["signal"] == "marker" for f in found)
             else "build-record" if record
             else "git" if human_git is not None
             else "nothing-to-go-on")

    if a.json:
        print(json.dumps({"state": state, "protected": found,
                          "record_exists": bool(record), "files": len(files)},
                         indent=1, ensure_ascii=False))
        return 0

    print("=" * 72)
    print("detect_expert_edits - which parts of this module are somebody's decision?")
    print("=" * 72)
    print("%d course-facing file(s) examined" % len(files))

    if state == "nothing-to-go-on":
        print("""
NO EVIDENCE EITHER WAY - and that is not the same as untouched.

There is no _factory/build.json, no SME marker and no usable history, so this factory
has no way to tell what a person changed here on purpose. ASK, in one line, before
rebuilding anything:

    "Has anyone edited this module by hand since it was produced? If so, which parts -
     I will restyle them but not rewrite them."

Then run this again with --record at the end, so the next retrofit never has to ask.""")
        return 0

    if not found:
        print("\nNothing protected. Every file still matches the record the factory wrote"
              "\n%s, so nothing here is a person's later decision. Law 5 applies in full:"
              "\nrebuild the delivery." % ("on " + record.get("written", "?") if record else ""))
        return 0

    by_sig = {}
    for f in found:
        by_sig.setdefault(f["signal"], []).append(f)

    NAME = {"marker": "THE EXPERT SAID SO",
            "build-record": "CHANGED SINCE THE FACTORY WROTE IT",
            "git": "TOUCHED BY SOMEBODY ELSE'S COMMIT"}
    for sig in ("marker", "build-record", "git"):
        g = by_sig.get(sig)
        if not g:
            continue
        print("\n%s (%d):" % (NAME[sig], len(g)))
        for f in g:
            where = "%s:%d" % (f["rel"], f["line"]) if f["line"] else f["rel"]
            print("  %-46s %s" % (where, f["what"]))
            if f["note"]:
                print("  %-46s   %s" % ("", f["note"]))

    print("""
WHAT THIS MEANS FOR THE REBUILD

Everything above is LOCKED CONTENT - the same tier as a technical fact or an ILO.

  restyle it        tokens, typography, the layout shell, accessibility, broken markup
  do not rewrite it the words, the order, the facts, a screen they added, a screen they
                    deleted - all stay exactly as they are

Where one of these breaks a factory law, NAME THE LAW AND PROPOSE THE FIX IN THE REPORT.
Do not apply it. An expert who finds their change quietly corrected stops making
changes, and then the course has no maritime judgement in it at all.""")
    return 0


if __name__ == "__main__":
    sys.exit(main())
