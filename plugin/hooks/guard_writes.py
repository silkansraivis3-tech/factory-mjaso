#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""guard_writes - PreToolUse hook on Write / Edit / MultiEdit / NotebookEdit (L40).

The master folder's source files, knowledge base and old course are read only: the factory reads them and writes
into course\\ beside them. A write into one of them is refused here, whatever the model remembers. A folder counts as
read only when its name is one of workspace.MASTER_MARKS (or starts with knowledge_base) and the folder that holds it
is a master folder with the factory's course\\ beside it.

    python test_guard_writes.py
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "skills", "course-factory", "scripts"))
import workspace  # noqa: E402


def read_only_root(path):
    """the read-only folder path lies in, or None"""
    p = os.path.abspath(path)
    while True:
        up = os.path.dirname(p)
        if up == p:
            return None
        name = os.path.basename(p).lower()
        if (name in workspace.MASTER_MARKS or name.startswith("knowledge_base")) \
                and os.path.isdir(os.path.join(up, workspace.WORK)):
            return p
        p = up


def main():
    try:
        event = json.load(sys.stdin)
    except ValueError:
        return 0
    args = event.get("tool_input") or {}
    path = args.get("file_path") or args.get("notebook_path") or ""
    root = read_only_root(path) if path else None
    if root:
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse", "permissionDecision": "deny",
            "permissionDecisionReason": "%s is read only (L40): the factory reads the master folder's source files, knowledge "
                                        "base and old course and writes only into %s beside them." % (
                                            root, os.path.join(os.path.dirname(root), workspace.WORK))}}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
