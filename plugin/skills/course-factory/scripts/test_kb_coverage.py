# -*- coding: utf-8 -*-
"""test_kb_coverage - L74: no module's script before the knowledge base covers what it teaches (2.133.0).

    python test_kb_coverage.py

A small Course Source Processor knowledge base in a temp folder holds the study plan (which names both sub-topics of
module 1) and one teaching source (which covers only 1.1). Pinned below:

  * 1.1 has a source; 1.2 is a gap - the study plan that names it does not count (Information Technology, 2026-11-16:
    every sub-topic "found" its own programme line, and seven scripts were written with no source for their basics);
  * the gate (course_gate.py --module 1) stops on the gap, and says how to close it;
  * an accepted gap needs the operator's reason and name, and then opens the gate;
  * a course whose knowledge base was declined, and the final module, are not checked here.
"""
from __future__ import annotations

import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gate_fixture  # noqa: E402
import course_gate  # noqa: E402
import kb_coverage  # noqa: E402
import workspace  # noqa: E402

PASS, FAIL = [], []


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print(("  ok    " if ok else "  FAIL  ") + name + (("  -> " + str(detail)[:600]) if detail and not ok else ""))


def w(p, s):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with io.open(p, "w", encoding="utf-8") as f:
        f.write(s)


def toks(text):
    stop = {"a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "in", "is", "it", "of", "on", "or", "the", "to", "with"}
    return [t for t in re.findall(r"[^\W_]+", text.lower()) if len(t) >= 2 and t not in stop]


SUB_11 = "Liquefied gas carried cold, under pressure, or both."
SUB_12 = "Cargo containment systems and the secondary barrier each needs."


def build_kb(root):
    kb = os.path.join(root, "KNOWLEDGE_BASE")
    texts = {"Gas course study plan.pdf": "Course outline. 1.1 %s 1.2 %s" % (SUB_11, SUB_12),
             "Gas handling.pdf": "Liquefied gas is carried cold at atmospheric pressure, under pressure at ambient "
                                 "temperature, or both: semi-refrigerated.",
             "Fire fighting.pdf": "Dry powder is used on gas fires; water spray cools the tank dome."}
    chunks, lines, off = [], [], 0
    for i, (f, t) in enumerate(texts.items()):
        rec = {"source_filename": f, "source_path": f, "page_start": 1, "page_end": 1, "text": t}
        line = (json.dumps(rec) + "\n").encode("utf-8")
        chunks.append({"i": i, "sp": f, "n": len(toks(t)), "nav": 0, "off": off, "bytes": len(line), "_t": toks(t)})
        lines.append(line)
        off += len(line)
    df, post = Counter(), {}
    for c in chunks:
        for t, n in Counter(c.pop("_t")).items():
            df[t] += 1
            post.setdefault(t, []).append([c["i"], n])
    idx = {"index_version": 5, "chunk_count": len(chunks), "bm25": {"k1": 1.2, "b": 0.75}, "min_token_length": 2,
           "avg_tokens_per_chunk": sum(c["n"] for c in chunks) / len(chunks), "chunks": chunks, "df": dict(df), "postings": post}
    w(os.path.join(kb, "search_index", "index.json"), json.dumps(idx))
    with open(os.path.join(kb, "search_index", "chunks.jsonl"), "wb") as fh:
        fh.write(b"".join(lines))
    w(os.path.join(kb, "SOURCE_MANIFEST.json"), json.dumps({"sources": [{"source_path": f} for f in texts]}))
    os.makedirs(os.path.join(kb, "sources"), exist_ok=True)
    return kb


def make_course(root, kb_decision):
    course = os.path.join(root, "course")
    os.makedirs(workspace.claude_path(course, ""), exist_ok=True)
    w(workspace.claude_path(course, "programme.json"), json.dumps({"topics": {"1": {"title": "Gas", "subtopics": [
        {"ref": "1.1", "title": SUB_11}, {"ref": "1.2", "title": SUB_12}]}}}))
    gate_fixture.open_gate(course, kb=kb_decision)
    return course


def run(*a):
    p = subprocess.run([sys.executable] + list(a), capture_output=True, text=True, encoding="utf-8", errors="replace")
    return p.returncode, p.stdout + p.stderr


def main():
    tmp = tempfile.mkdtemp(prefix="kbcov_")
    try:
        root = os.path.join(tmp, "Gas course")
        kb = build_kb(os.path.join(root, "source_files"))
        built = {"answer": "built", "path": kb, "format": "course_source_processor", "decided": "2026-11-16"}
        course = make_course(root, built)

        print("-- the study plan names a sub-topic; it does not teach it")
        res = {r["id"]: r for r in kb_coverage.check(course, 1)}
        check("1.1 has a source", res["1.1"]["verdict"] == "covered", res["1.1"])
        check("... and it is the teaching source, not the study plan", "Gas handling" in (res["1.1"]["where"] or ""), res["1.1"])
        check("1.2 is a gap (only the study plan names it)", res["1.2"]["verdict"] == "gap", res["1.2"])
        check("the study plan is left out of the search",
              any("study plan" in p.lower() for p in kb_coverage.programme_sources(course, kb, "csp")))

        print("-- the gate stops on it and says how to close it")
        probs = course_gate.problems(course, 1)
        check("course_gate.problems names the L74 gap", any("L74" in p and "1.2" in p for p in probs), probs)
        check("... with both ways out", any("kb_tool.py build" in p and "kb_coverage.py accept" in p for p in probs), probs)
        code, out = run(os.path.join(HERE, "course_gate.py"), course, "--module", "1")
        check("course_gate.py --module 1 exits 2", code == 2 and "L74" in out, out)
        code, out = run(os.path.join(HERE, "course_gate.py"), course)
        check("course_gate.py without a module is not stopped by it", code == 0, out)
        code, out = run(os.path.join(HERE, "kb_coverage.py"), "check", course, "--module", "1")
        check("kb_coverage.py check exits 2 and lists the GAP", code == 2 and "GAP 1.2" in out, out)

        print("-- an accepted gap: the operator's words, then the gate opens")
        code, out = run(os.path.join(HERE, "kb_coverage.py"), "accept", course, "--module", "1", "--ids", "1.2", "--why", " ", "--by", "Op")
        check("accept without a reason is refused", code == 2 and course_gate.problems(course, 1), out)
        code, out = run(os.path.join(HERE, "kb_coverage.py"), "accept", course, "--module", "1", "--ids", "9.9", "--why", "x", "--by", "Op")
        check("accept of an id the module does not have is refused", code == 2 and "9.9" in out, out)
        code, out = run(os.path.join(HERE, "kb_coverage.py"), "accept", course, "--module", "1", "--ids", "1.2",
                        "--why", "the instructor checks it in the script review", "--by", "Op")
        check("accept with a reason and a name is recorded", code == 0, out)
        res = {r["id"]: r for r in kb_coverage.check(course, 1)}
        check("1.2 now reads accepted, with the reason", res["1.2"]["verdict"] == "accepted" and "instructor" in res["1.2"]["why"], res)
        check("the gate is open", course_gate.problems(course, 1) == [], course_gate.problems(course, 1))

        print("-- not checked here")
        check("the final module", kb_coverage.check(course, "final") is None)
        declined = make_course(os.path.join(tmp, "Declined course"), None)
        check("a course whose knowledge base was declined", kb_coverage.check(declined, 1) is None
              and course_gate.problems(declined, 1) == [], course_gate.problems(declined, 1))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("\n%d passed, %d failed" % (len(PASS), len(FAIL)))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
