# -*- coding: utf-8 -*-
"""test_kb - both kinds of knowledge base are read, and neither is ever written to.

    python test_kb.py

Two small synthetic knowledge bases - one Course Source Processor, one docling - built in a temp
folder. Pinned below:

  * each kind is recognised by its own files, and a folder that is neither is refused plainly;
  * exact copies are grouped and need no question; the same document as .doc and .docx is a format
    copy, not an edition;
  * editions of one publication are grouped - by name with the year or edition taken out, by an
    acronym (LGHP = liquified gas handling principles), by a typo (SIGGTO / SIGTTO) - and each
    group becomes a ready pop-up question;
  * things that only look alike are NOT grouped: LNG / LPG, two numbered exercises, two model courses;
  * the operator's answer is recorded, and a search then leaves the old edition out;
  * search finds the right piece in both kinds, writes its pack into the COURSE folder, and a course
    folder inside the knowledge base is refused;
  * nothing inside either knowledge base changes.
"""
from __future__ import annotations

import hashlib
import io
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "kb_tool.py")
sys.path.insert(0, HERE)
import kb_tool  # noqa: E402

PASS, FAIL = [], []


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print(("  ok    " if ok else "  FAIL  ") + name + (("  -> " + str(detail)) if detail and not ok else ""))


def run(*a):
    p = subprocess.run([sys.executable, TOOL] + list(a), capture_output=True, text=True, encoding="utf-8", errors="replace")
    return p.returncode, p.stdout + p.stderr


def w(p, s, mode="w"):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with io.open(p, mode, encoding="utf-8", newline="\n") as f:
        f.write(s)


# (file, text, same-content-as) - the fixture library, used for both kinds
DOCS = [
    ("MARPOL-2022.pdf", "Annex VI limits sulphur content of fuel oil used on board to 0.50 percent.", None),
    ("marpol.pdf", "Annex VI older limits on sulphur content of fuel oil were higher.", None),
    ("SIGGTO LGHP (4th).pdf", "Inerting is finished when the dew point in the cargo tank is below minus twenty.", None),
    ("SIGTTO liquified gas handling principles.pdf", "", "SIGGTO LGHP (4th).pdf"),
    ("CDI LNG Chapter 5.pdf", "LNG cargo containment boil off and membrane tanks.", None),
    ("CDI LPG Chapter 5.pdf", "LPG cargo refrigeration plant and pressure tanks.", None),
    ("exercise 14.2.4 - cable termination.docx", "Cable termination defects and their repair.", None),
    ("exercise 14.2.5 - cable termination.docx", "Cable joint defects and their repair.", None),
    ("1.04 IMO Model Course.pdf", "Basic training for liquefied gas tanker cargo operations.", None),
    ("1.35 imo model.pdf", "Advanced training for liquefied gas tanker cargo operations.", None),
    ("ISGOTT 6th.pdf", "Tank cleaning and gas freeing on oil tankers, sixth edition text.", None),
    ("International Safety Guide for Oil Tankers and Terminals 5th.pdf", "Tank cleaning on oil tankers, fifth edition text.", None),
    ("SIGGTO Liquefied Gas Fire Hazard Management.pdf", "Fire hazard management, first printing.", None),
    ("SIGTTO Liquefied Gas Fire Hazard Management 2nd.pdf", "Fire hazard management, second edition.", None),
    ("Course Plan 2025.doc", "The course plan for the gas course.", None),
    ("Course Plan 2025.docx", "The course plan for the gas course, converted.", None),
]


def sha_of(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def text_of(name):
    for f, t, same in DOCS:
        if f == name:
            return text_of(same) if same else t


def build_csp(root):
    kb = os.path.join(root, "KNOWLEDGE_BASE")
    sources, chunks, lines = [], [], []
    off = 0
    first_of_sha = {}
    for i, (f, _, _) in enumerate(DOCS):
        t = text_of(f)
        sha = sha_of(t)
        dup = first_of_sha.get(sha)
        folder = "sources/%s__%02d" % (re.sub(r"\W+", "_", f), i)
        entry = {"doc_id": "d%02d" % i, "original_filename": f, "source_path": "source_files/%s" % f,
                 "output_folder": folder if not dup else "sources/", "sha256": sha,
                 "duplicate_of": dup and dup["doc_id"], "duplicate_of_path": dup and dup["source_path"],
                 "converted_from": None, "status": "duplicate" if dup else "ok"}
        sources.append(entry)
        if dup:
            continue
        first_of_sha[sha] = entry
        w(os.path.join(kb, folder, "metadata.json"), json.dumps({"doc_id": entry["doc_id"], "title": ""}))
        w(os.path.join(kb, folder, "document.md"), t)
        rec = {"chunk_id": "d%02d#c0001" % i, "doc_id": entry["doc_id"], "source_filename": f,
               "source_path": entry["source_path"], "page_start": 3, "page_end": 3, "unit_kind": "page",
               "heading_path": ["Chapter"], "text": t, "asset_path": "", "kind": "text"}
        line = (json.dumps(rec, ensure_ascii=False) + "\n").encode("utf-8")
        toks = kb_tool.toks(t)
        chunks.append({"i": len(chunks), "doc": entry["doc_id"], "sp": entry["source_path"], "n": len(toks),
                       "nav": 0, "off": off, "bytes": len(line), "_t": toks})
        lines.append(line)
        off += len(line)
    df, post = Counter(), {}
    for c in chunks:
        for t, n in Counter(c["_t"]).items():
            df[t] += 1
            post.setdefault(t, []).append([c["i"], n])
    for c in chunks:
        del c["_t"]
    idx = {"index_version": 5, "chunk_count": len(chunks), "bm25": {"k1": 1.2, "b": 0.75},
           "avg_tokens_per_chunk": sum(c["n"] for c in chunks) / len(chunks), "chunks": chunks,
           "df": dict(df), "postings": post, "documents": {}}
    w(os.path.join(kb, "search_index", "index.json"), json.dumps(idx))
    os.makedirs(os.path.join(kb, "search_index"), exist_ok=True)
    with open(os.path.join(kb, "search_index", "chunks.jsonl"), "wb") as fh:
        fh.write(b"".join(lines))
    w(os.path.join(kb, "SOURCE_MANIFEST.json"), json.dumps({"tool": "COURSE SOURCE PROCESSOR", "sources": sources}))
    w(os.path.join(kb, "COURSE_INDEX.md"), "# Course index\n")
    return kb


def build_docling(root):
    kb = os.path.join(root, "knowledge_base")
    man = {}
    for i, (f, _, _) in enumerate(DOCS):
        t = text_of(f)
        out = "%s__pdf__%02d" % (re.sub(r"\W+", "_", os.path.splitext(f)[0]), i)
        man[f] = {"source_path": f, "output_directory": out, "source_sha256": sha_of(t), "status": "SUCCESS"}
        w(os.path.join(kb, out, "chunks.jsonl"), json.dumps({"filename": f, "chunk_index": 0, "text": t,
                                                             "headings": ["Chapter"], "page_numbers": [7]}) + "\n")
        w(os.path.join(kb, out, "content.md"), t)
        w(os.path.join(kb, out, "source_metadata.json"), json.dumps({"source_sha256": sha_of(t)}))
    w(os.path.join(kb, "00_INDEX", "SOURCE_MANIFEST.json"), json.dumps({"sources": man}))
    return kb


def snapshot(folder):
    h = hashlib.sha256()
    for d, _, fs in sorted(os.walk(folder)):
        for f in sorted(fs):
            p = os.path.join(d, f)
            h.update(p.encode("utf-8"))
            h.update(open(p, "rb").read())
    return h.hexdigest()


def groups(course):
    r = json.load(io.open(os.path.join(course, "working_claude", "kb_sources.json"), encoding="utf-8"))
    names = lambda paths: sorted(os.path.basename(p) for p in paths)
    return r, [names(g["members"]) for g in r["edition_groups"]]


def main():
    tmp = tempfile.mkdtemp(prefix="kb_")
    try:
        for kind, build in (("course_source_processor", build_csp), ("docling", build_docling)):
            print("\n-- %s" % kind)
            kb = build(os.path.join(tmp, kind))
            before = snapshot(kb)
            course = os.path.join(tmp, kind + "_course")
            os.makedirs(course)
            code, out = run("detect", kb)
            check("recognised as %s" % kind, code == 0 and out.strip() == kind, out)

            code, out = run("sources", kb, "--course", course)
            check("the inventory runs", code == 0, out)
            rep, eg = groups(course)
            check("exact copies are grouped, with no question",
                  any(sorted(os.path.basename(p) for p in g) == ["SIGGTO LGHP (4th).pdf",
                      "SIGTTO liquified gas handling principles.pdf"] for g in rep["exact_duplicates"]),
                  rep["exact_duplicates"])
            check("the same document as .doc and .docx is a format copy, not an edition",
                  any(sorted(os.path.basename(p) for p in g) == ["Course Plan 2025.doc", "Course Plan 2025.docx"]
                      for g in rep["format_copies"]) and not any("Course Plan 2025.doc" in g for g in eg),
                  (rep["format_copies"], eg))
            check("MARPOL 2022 and the older MARPOL are one publication in two editions",
                  ["MARPOL-2022.pdf", "marpol.pdf"] in eg, eg)
            check("an acronym is matched to its full name (ISGOTT)",
                  ["ISGOTT 6th.pdf", "International Safety Guide for Oil Tankers and Terminals 5th.pdf"] in eg, eg)
            check("a misspelt publisher is still the same publication (SIGGTO / SIGTTO)",
                  ["SIGGTO Liquefied Gas Fire Hazard Management.pdf", "SIGTTO Liquefied Gas Fire Hazard Management 2nd.pdf"] in eg, eg)
            for a, b in (("CDI LNG Chapter 5.pdf", "CDI LPG Chapter 5.pdf"),
                         ("exercise 14.2.4 - cable termination.docx", "exercise 14.2.5 - cable termination.docx"),
                         ("1.04 IMO Model Course.pdf", "1.35 imo model.pdf")):
                check("NOT grouped: %s / %s" % (a[:22], b[:22]), not any(a in g and b in g for g in eg), eg)
            q = next(g for g in rep["edition_groups"] if any(m.endswith("MARPOL-2022.pdf") for m in g["members"]))
            check("each edition group carries a ready pop-up question",
                  "Which edition is current?" in q["question"] and 2 <= len(q["options"]) <= 4
                  and len(q["header"]) <= 12, q)

            code, out = run("search", kb, "sulphur content fuel oil", "--course", course, "--top", "3")
            pack = [os.path.join(course, "working_claude", "retrieval", f) for f in os.listdir(os.path.join(course, "working_claude", "retrieval"))]
            txt = io.open(pack[0], encoding="utf-8").read() if pack else ""
            check("search writes its pack into the COURSE folder", code == 0 and len(pack) == 1, out)
            check("before any decision, both MARPOL editions are found", "MARPOL-2022.pdf" in txt and "marpol.pdf" in txt, txt[:400])
            check("an exact copy is never cited twice", txt.count("SIGTTO liquified gas handling principles.pdf") == 0, txt[:300])

            code, out = run("decide", course, "--keep", q["members"][[i for i, m in enumerate(q["members"]) if m.endswith("MARPOL-2022.pdf")][0]])
            intake = json.load(io.open(os.path.join(course, "working_claude", "intake.json"), encoding="utf-8"))
            check("the operator's answer is recorded in intake.json",
                  code == 0 and any(d["superseded"] and d["superseded"][0].endswith("marpol.pdf")
                                    for d in intake["editions"].values()), intake)
            os.remove(pack[0])
            run("search", kb, "sulphur content fuel oil", "--course", course, "--top", "3")
            pack = [os.path.join(course, "working_claude", "retrieval", f) for f in os.listdir(os.path.join(course, "working_claude", "retrieval"))]
            txt = io.open(pack[0], encoding="utf-8").read()
            check("after it, only the current edition is cited", "MARPOL-2022.pdf" in txt and "## 2 · marpol.pdf" not in txt and "· marpol.pdf" not in txt, txt[:500])
            code, out = run("search", kb, "inerting dew point", "--course", course, "--top", "1")
            check("the right piece ranks first", "SIGGTO LGHP (4th).pdf" in io.open(
                os.path.join(course, "working_claude", "retrieval", [f for f in os.listdir(os.path.join(course, "working_claude", "retrieval")) if "inerting" in f][0]),
                encoding="utf-8").read().split("## 1 ·")[1].split("\n")[0])

            inner = os.path.join(kb, "my_course")
            code, out = run("search", kb, "fuel oil", "--course", inner)
            check("a course folder inside the knowledge base is refused", code == 2 and not os.path.exists(inner), out)
            check("nothing inside the knowledge base changed", snapshot(kb) == before)

        print("\n-- find (2.13.1): every knowledge base, by its files, writing nothing")
        course = os.path.join(tmp, "a_course")
        os.makedirs(os.path.join(course, "materials", "deep"))
        build_csp(os.path.join(course, "materials"))            # a_course/materials/KNOWLEDGE_BASE
        build_docling(tmp)                                       # knowledge_base right beside a_course
        before_all = snapshot(tmp)
        code, out = run("find", course, "--json")
        r = json.loads(out)
        paths = [os.path.normcase(k["path"]) for k in r["found"]]
        check("a knowledge base in a sub-folder is found", code == 0 and
              os.path.normcase(os.path.join(course, "materials", "KNOWLEDGE_BASE")) in paths, out)
        check("... and one beside the course folder (one level up), but nothing further away",
              len(r["found"]) == 2 and os.path.normcase(os.path.join(tmp, "knowledge_base")) in paths, [k["path"] for k in r["found"]])
        check("several found -> one ready question with an option each", r.get("question") and
              len(r["question"]["options"]) == 2 and len(r["question"]["header"]) <= 12, r.get("question"))
        check("it never walks inside a knowledge base",
              not any("sources" in os.path.normcase(p).split(os.sep) for p in paths), paths)
        code, out = run("find", os.path.join(course, "materials", "deep"), "--json")
        check("from a sub-folder, the knowledge base next to it is found (one level up)",
              any(p.endswith(os.path.normcase(os.path.join("materials", "KNOWLEDGE_BASE"))) for p in
                  [os.path.normcase(k["path"]) for k in json.loads(out)["found"]]), out)
        empty = os.path.join(tmp, "nothing", "here")
        os.makedirs(empty)
        code, out = run("find", empty)
        check("none found -> the factory suggests making one, unasked: what, how, and what is lost without it (2.42.0)",
              code == 1 and "SUGGESTS MAKING A KNOWLEDGE BASE" in out and "Course Source Processor" in out
              and "the factory has no tool that builds one" in out and "Without it:" in out and "kb_tool.py decision" in out, out)
        os.rmdir(empty); os.rmdir(os.path.dirname(empty))
        check("find wrote nothing anywhere", snapshot(tmp) == before_all)

        print("\n-- no knowledge base: suggested unasked, and the operator's answer recorded once (2.42.0)")
        master = os.path.join(tmp, "m", "IGF basic")
        for rel in ("source_files/regulations/IGF CODE 2016.pdf", "source_files/model_course/IMO_Model_Course_7.13.pdf",
                    "source_files/Study programme 13-51-306.pdf", "source_files/equipment/gas detector.pdf",
                    "old course/ch1.pptx", "source_files/notes.txt", "course/to_review/M01_SCRIPT.docx"):
            w(os.path.join(master, rel), "x")
        before = snapshot(os.path.join(tmp, "m"))
        code, out = run("find", master, "--json")
        sg = json.loads(out).get("suggestion") or {}
        g = sg.get("groups") or {}
        check("the suggestion names the files it would be built from, sorted as the operator knows them",
              code == 1 and sg.get("files") == 5 and len(g.get("programme", [])) == 1 and len(g.get("model_course", [])) == 1
              and len(g.get("codes", [])) == 1 and len(g.get("old_course", [])) == 1 and len(g.get("other", [])) == 1, sg)
        check("... from source_files and the old course - never the factory's own course\\ folder or a .txt",
              not any("course" + os.sep + "to_review" in f or f.endswith(".txt") for v in g.values() for f in v)
              and os.path.normcase(sg.get("source_root", "")) == os.path.normcase(os.path.join(master, "source_files")), sg)
        q = sg.get("question") or {}
        check("--json carries the ready pop-up question, making one first and marked Recommended",
              q.get("header") == "Sources" and len(q.get("options", [])) == 3 and "(Recommended)" in q["options"][0]["label"], q)
        check("the suggestion says what the operator must run - and never that the factory builds it",
              "Course Source Processor" in sg.get("text", "") and "has no tool that builds one" in sg.get("text", "")
              and os.path.join(master, "source_files") in sg.get("text", ""), sg.get("text"))
        check("finding and suggesting wrote nothing", snapshot(os.path.join(tmp, "m")) == before)

        wc = os.path.join(master, "course")
        code, out = run("decision", master)
        check("no decision yet: decision with no answer says so (exit 1)", code == 1 and "none recorded" in out, out)
        code, out = run("decision", master, "--declined", "  ")
        check("declined needs the operator's reason", code == 2 and "reason" in out, out)
        code, out = run("decision", master, "--yes", os.path.join(master, "source_files"))
        check("--yes refuses a folder that is not a knowledge base", code == 2 and "not a knowledge base" in out, out)
        code, out = run("decision", master, "--declined", "the programme is two pages; we read it directly")
        intake = json.load(io.open(os.path.join(wc, "working_claude", "intake.json"), encoding="utf-8"))
        d = intake.get("knowledge_base_decision") or {}
        check("declined with the reason is recorded in course\\working_claude\\intake.json, and in 'asked'",
              code == 0 and d.get("answer") == "declined" and d.get("reason", "").startswith("the programme is two pages")
              and any(x.get("question") == "knowledge base" for x in intake.get("asked", [])), (out, intake))
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "scripts"))
        import course_gate
        check("course_gate reads the decision", (course_gate.kb_decision(wc) or {}).get("answer") == "declined")
        code, out = run("decision", master, "--built", os.path.join(course, "materials", "KNOWLEDGE_BASE"))
        d = json.load(io.open(os.path.join(wc, "working_claude", "intake.json"), encoding="utf-8")).get("knowledge_base_decision")
        check("--built records the new knowledge base with its kind", code == 0 and d["answer"] == "built"
              and d["format"] == "course_source_processor" and "reason" not in d, d)
        check("... and the knowledge base itself was never written to",
              not os.path.exists(os.path.join(course, "materials", "KNOWLEDGE_BASE", "intake.json")))
        legacy = os.path.join(tmp, "legacy")
        w(os.path.join(legacy, "working_claude", "intake.json"), json.dumps(
            {"knowledge_base": [{"path": "C:\\a\\KNOWLEDGE_BASE", "format": "course_source_processor"}]}))
        check("an intake from before 2.42.0 that names a knowledge base counts as the decision",
              (course_gate.kb_decision(legacy) or {}).get("answer") == "yes")
        w(os.path.join(legacy, "working_claude", "intake.json"), json.dumps({"knowledge_base": {"path": "none", "format": "none"}}))
        check("... and one that answered 'no knowledge base' counts as declined",
              (course_gate.kb_decision(legacy) or {}).get("answer") == "declined")
        w(os.path.join(legacy, "working_claude", "intake.json"), json.dumps({"programme": "x.pdf"}))
        check("... an intake that never asked is no decision", course_gate.kb_decision(legacy) is None)

        print("\n-- not a knowledge base")
        code, out = run("detect", tmp)
        check("a plain folder is refused plainly", code == 2, out)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("\n" + "=" * 72)
    print("%d passed, %d failed" % (len(PASS), len(FAIL)))
    if FAIL:
        return 1
    print("\nBoth kinds of knowledge base are read, copies and editions are sorted out before anything is\n"
          "cited, the operator's choice of edition is obeyed, and the knowledge base is never written to.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
