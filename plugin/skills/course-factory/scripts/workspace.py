#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Where the factory works - L40, L44. The operator's folder holds the course material; the factory works beside it.

    workspace.py <folder>          print the work folder for this folder (and create it if needed)
    workspace.py tidy <folder>     move an older course's files into the three folders below - moved, never deleted

WHY THIS EXISTS
The operator points the factory at ONE folder - the master folder - that holds what the course is made
from: source_files, the knowledge base, the old course (owner, 2026-10-01). Those stay exactly as they
are: the factory reads them and never writes into them. Everything the factory makes goes into ONE folder
beside them, and inside it into three places (owner, 2026-10-02 - "it was chaos in the folder structure"):

    <master folder>\\
        source_files\\        read only
        KNOWLEDGE_BASE\\      read only
        old_course\\          read only
        course\\
            to_review\\       everything the operator or instructor opens and checks: the architecture page,
                             each module's content script (page and Word file), the instructor notes, a pattern
                             draft - one place, nothing else in it
            modules\\         the finished modules, one complete folder each (L43)
            working_claude\\  everything only the factory uses: COURSE_STATE.md, FEEDBACK_LOG.md, factory-notes.md,
                             programme.json, architecture.json, the scripts' own data, intake, the knowledge-base
                             decisions, the old-course inventory and pictures, research, retrieval - all kept

work_folder() is what every tool calls on the folder it was given, so the operator may name either the
master folder or the course folder and the result is the same. claude_path() and review_path() say where a
file goes; an older course that still has its files in the old places keeps working (they are found where they
are) until `tidy` moves them.
"""
from __future__ import annotations

import os
import shutil
import sys

WORK = "course"
REVIEW = "to_review"
CLAUDE = "working_claude"
MODULES = "modules"
# what marks a folder as the factory's own work folder
WORK_MARKS = (REVIEW, CLAUDE, "COURSE_STATE.md", "FEEDBACK_LOG.md", "_factory", "architecture.json", "programme.json")
# what marks a folder as the operator's master folder - the material the course is made from
MASTER_MARKS = ("source_files", "knowledge_base", "old_course", "sources", "source files", "old course")

# the older layout (2.19.x and before), and where each piece belongs now
LEGACY_TO_CLAUDE = ("COURSE_STATE.md", "FEEDBACK_LOG.md", "factory-notes.md", "programme.json", "architecture.json",
                    "plan.json", "BUILD_BRIEF.md")
LEGACY_TO_REVIEW = ("ARCHITECTURE_REVIEW.html", "ARCHITECTURE_REVIEW.pdf")
LEGACY_DIRS = {"_factory": CLAUDE, "review": REVIEW, "instructor_notes": REVIEW, "build": os.path.join(CLAUDE, "build")}


def is_work(folder):
    base = os.path.basename(os.path.abspath(folder).rstrip("\\/")).lower()
    return base == WORK or any(os.path.exists(os.path.join(folder, m)) for m in WORK_MARKS)


def is_master(folder):
    try:
        names = [n.lower() for n in os.listdir(folder)]
    except OSError:
        return False
    return any(n in MASTER_MARKS or n.startswith("knowledge_base") for n in names)


def work_folder(folder, create=True):
    """The folder the factory writes into. A master folder gets its course\\ beside the material; a work folder
    is itself; any other folder is used as it is (an old layout keeps working)."""
    folder = os.path.abspath(folder)
    if is_work(folder) and not is_master(folder):
        return folder
    if is_master(folder):
        w = os.path.join(folder, WORK)
        if create:
            os.makedirs(w, exist_ok=True)
        return w
    return folder


def master_of(folder):
    """The master folder for a work folder - the folder that holds the course material."""
    w = work_folder(folder, create=False)
    up = os.path.dirname(w)
    return up if os.path.basename(w).lower() == WORK and is_master(up) else w


def review_dir(work):
    return os.path.join(work, REVIEW)


def claude_path(work, *parts):
    """Where a file only the factory uses lives: working_claude\\<parts>. An older course that still has it in the
    old place - the work folder itself, or _factory\\ - keeps using that copy until `tidy` moves it."""
    new = os.path.join(work, CLAUDE, *parts)
    if os.path.exists(new) or not parts:
        return new
    for old in (os.path.join(work, *parts), os.path.join(work, "_factory", *parts)):
        if os.path.exists(old):
            return old
    return new


def review_path(work, name, for_reading=False):
    """Where a file the operator checks lives: to_review\\<name>. Pages are always written there; for reading
    (the operator's Word file), an older course's copy in review\\ or the work folder is found too."""
    new = os.path.join(work, REVIEW, name)
    if for_reading and not os.path.exists(new):
        for old in (os.path.join(work, "review", name), os.path.join(work, name), os.path.join(work, "instructor_notes", name)):
            if os.path.exists(old):
                return old
    return new


def module_record(module_dir, name):
    """A tool's own record about one module (the style copy, the build hashes). A module in course\\modules\\ keeps
    its folder clean (L43, L44): the record goes to working_claude\\modules\\<module>\\. A module anywhere else - an
    operator's own folder in a retrofit - keeps it in <module>\\_factory\\ as before. An existing old record is used."""
    m = os.path.abspath(module_dir)
    parent = os.path.dirname(m)
    if os.path.basename(parent).lower() == MODULES and is_work(os.path.dirname(parent)):
        old = os.path.join(m, "_factory", name)
        if os.path.exists(old):
            return old
        return os.path.join(os.path.dirname(parent), CLAUDE, MODULES, os.path.basename(m), name)
    return os.path.join(m, "_factory", name)


def _move(src, dst, moved):
    if not os.path.exists(src):
        return
    if os.path.isdir(src):
        os.makedirs(dst, exist_ok=True)
        for n in sorted(os.listdir(src)):
            _move(os.path.join(src, n), os.path.join(dst, n), moved)
        try:
            os.rmdir(src)                      # empty now - every file in it was moved, not deleted
        except OSError:
            pass
        return
    if os.path.exists(dst):                    # never overwrite: keep both
        root, ext = os.path.splitext(dst)
        dst = root + "_from_old_layout" + ext
        k = 2
        while os.path.exists(dst):
            dst, k = "%s_from_old_layout_%d%s" % (root, k, ext), k + 1
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.move(src, dst)
    moved.append((src, dst))


def tidy(work):
    """Move an older course's files into to_review\\, modules\\ and working_claude\\. Moves only what it knows;
    names what it left alone; overwrites nothing; deletes nothing."""
    moved = []
    for n in LEGACY_TO_CLAUDE:
        _move(os.path.join(work, n), os.path.join(work, CLAUDE, n), moved)
    for n in LEGACY_TO_REVIEW:
        _move(os.path.join(work, n), os.path.join(work, REVIEW, n), moved)
    for n in sorted(os.listdir(work)):
        p = os.path.join(work, n)
        if os.path.isfile(p) and n.startswith("COURSE_PATTERN_"):
            _move(p, os.path.join(work, REVIEW if n.endswith(".draft.md") else CLAUDE, n), moved)
    for old, new in LEGACY_DIRS.items():
        _move(os.path.join(work, old), os.path.join(work, new), moved)
    left = sorted(n for n in os.listdir(work) if n not in (REVIEW, CLAUDE, MODULES))
    return moved, left


def main(argv=None):
    a = argv if argv is not None else sys.argv[1:]
    if a[:1] == ["tidy"] and len(a) == 2 and os.path.isdir(a[1]):
        w = work_folder(a[1], create=False)
        moved, left = tidy(w)
        print("Tidied %s - %d file(s) moved into to_review\\, working_claude\\ (nothing deleted, nothing overwritten)." % (w, len(moved)))
        for src, dst in moved:
            print("    %s  ->  %s" % (os.path.relpath(src, w), os.path.relpath(dst, w)))
        if left:
            print("  Left where they are - not something the factory made in the old layout:\n    " + "\n    ".join(left))
        return 0
    if len(a) != 1 or not os.path.isdir(a[0]):
        print(__doc__.split("\n")[0] + "\n\n    workspace.py <folder>\n    workspace.py tidy <folder>")
        return 2
    w = work_folder(a[0])
    m = master_of(w)
    print("Work folder - the factory writes here and only here:\n    %s" % w)
    print("  to_review\\       what you open and check\n  modules\\         the finished modules\n"
          "  working_claude\\  the factory's own working files")
    if m != w:
        print("Course material - read only:\n    %s" % m)
        for n in sorted(os.listdir(m)):
            if os.path.isdir(os.path.join(m, n)) and n.lower() != WORK:
                print("      %s\\" % n)
    return 0


if __name__ == "__main__":
    sys.exit(main())
