# -*- coding: utf-8 -*-
"""test_guard_writes - the L40 write guard, run as Claude Code runs it: the event on stdin, the decision on stdout.

    python test_guard_writes.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
GUARD = os.path.join(HERE, "guard_writes.py")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
FAILS = []


def check(name, ok, detail=""):
    print("  %s  %s%s" % ("ok  " if ok else "FAIL", name, "" if ok else "  -> %s" % (detail,)))
    if not ok:
        FAILS.append(name)


def decide(tool, path):
    key = "notebook_path" if tool == "NotebookEdit" else "file_path"
    p = subprocess.run([sys.executable, GUARD], input=json.dumps({"tool_name": tool, "tool_input": {key: path}}),
                       capture_output=True, text=True, encoding="utf-8")
    out = p.stdout.strip()
    return (json.loads(out)["hookSpecificOutput"]["permissionDecision"] if out else "allow"), p.returncode


def main():
    with tempfile.TemporaryDirectory() as tmp:
        master = os.path.join(tmp, "IGF Basic")
        for d in ("source_files", "KNOWLEDGE_BASE_IGF", "old_course", os.path.join("course", "working_claude")):
            os.makedirs(os.path.join(master, d))
        alone = os.path.join(tmp, "elsewhere", "sources")
        os.makedirs(alone)
        for what, tool, path, want in (
                ("a source file", "Write", os.path.join(master, "source_files", "programme.pdf"), "deny"),
                ("a file deep in the knowledge base", "Edit", os.path.join(master, "KNOWLEDGE_BASE_IGF", "retrieval", "a.md"), "deny"),
                ("a page of the old course", "MultiEdit", os.path.join(master, "old_course", "m01", "index.html"), "deny"),
                ("a notebook in the old course", "NotebookEdit", os.path.join(master, "old_course", "calc.ipynb"), "deny"),
                ("the factory's own work folder", "Write", os.path.join(master, "course", "working_claude", "COURSE_STATE.md"), "allow"),
                ("a folder named sources with no course beside it", "Write", os.path.join(alone, "x.py"), "allow"),
                ("a file that is not there yet, in a folder not there yet", "Write", os.path.join(master, "course", "new", "a.html"), "allow")):
            got, code = decide(tool, path)
            check("%s: %s" % (want, what), got == want and code == 0, (got, code))
        p = subprocess.run([sys.executable, GUARD], input="not json", capture_output=True, text=True)
        check("an event it cannot read is let through, never a crash", p.returncode == 0 and not p.stdout.strip(), p)
    with open(os.path.join(HERE, "hooks.json"), encoding="utf-8") as f:
        hk = json.load(f)["hooks"]["PreToolUse"][0]
    check("hooks.json runs the guard on every tool that writes a file",
          all(t in hk["matcher"].split("|") for t in ("Write", "Edit", "MultiEdit", "NotebookEdit"))
          and "guard_writes.py" in hk["hooks"][0]["command"], hk)
    print("\n%s" % ("ALL PASS" if not FAILS else "%d FAILED" % len(FAILS)))
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
