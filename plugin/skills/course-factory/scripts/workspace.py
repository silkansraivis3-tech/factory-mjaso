#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Where the factory works - L40. The operator's folder holds the course material; the factory works beside it.

    workspace.py <folder>          print the work folder for this folder (and create it if needed)

WHY THIS EXISTS
The operator points the factory at ONE folder - the master folder - that holds what the course is made
from: source_files, the knowledge base, the old course (owner, 2026-10-01). Those stay exactly as they
are: the factory reads them and never writes into them. Everything the factory makes - COURSE_STATE.md,
FEEDBACK_LOG.md, _factory/, programme.json, architecture.json, the review pages, the Word files, the
instructor notes, the built modules - goes into ONE folder beside them:

    <master folder>\\
        source_files\\        read only
        KNOWLEDGE_BASE\\      read only
        old_course\\          read only
        course\\              <- the factory works here, and only here

work_folder() is what every tool calls on the folder it was given, so the operator may name either the
master folder or the course folder and the result is the same.
"""
from __future__ import annotations

import os
import sys

WORK = "course"
# what marks a folder as the factory's own work folder
WORK_MARKS = ("COURSE_STATE.md", "FEEDBACK_LOG.md", "_factory", "architecture.json", "programme.json")
# what marks a folder as the operator's master folder - the material the course is made from
MASTER_MARKS = ("source_files", "knowledge_base", "old_course", "sources", "source files", "old course")


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


def main(argv=None):
    a = argv if argv is not None else sys.argv[1:]
    if len(a) != 1 or not os.path.isdir(a[0]):
        print(__doc__.split("\n")[0] + "\n\n    workspace.py <folder>")
        return 2
    w = work_folder(a[0])
    m = master_of(w)
    print("Work folder - the factory writes here and only here:\n    %s" % w)
    if m != w:
        print("Course material - read only:\n    %s" % m)
        for n in sorted(os.listdir(m)):
            if os.path.isdir(os.path.join(m, n)) and n.lower() != WORK:
                print("      %s\\" % n)
    return 0


if __name__ == "__main__":
    sys.exit(main())
