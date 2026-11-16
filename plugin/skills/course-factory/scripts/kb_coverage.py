#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""L74 - no script before its sources: every sub-topic of a module has a passage in the knowledge base (2.133.0).

    kb_coverage.py check  <course> [--module N] [--json]    exit 0: every sub-topic has a source (or the operator
                                                             accepted the gap); exit 2: the gaps, and what to do
    kb_coverage.py accept <course> --module N --ids 2.4,2.5 --why "<the operator's reason>" --by "<name>"

WHY THIS EXISTS
Information Technology, 2026-11-16. The knowledge base was built from the programme's bibliography only (IMO, IACS,
BIMCO, MASS Code, EU AI Act) and the gate opened: a knowledge base was "built". Three agents then wrote seven content
scripts, and every module's basic teaching - computer parts, Excel functions, cable categories, PoE, how an LLM
answers, ROV / AUV - had no source at all: about 200 claims the fact-checker could only cut. The operator: "wait did
we build the modules before the knowledge base?" The decision that a knowledge base exists said nothing about whether
it covers what each module teaches. Worse, the programme itself sits in the knowledge base, so a search for any
sub-topic finds the programme's own line naming it - every topic looked covered.

WHAT IT DOES
For each Sub-ILO row of the module (working_claude/ilo_map.json) it searches the knowledge base with the programme's
own sub-topic wording (programme.json topics[].subtopics[ref == the row's id], else the Sub-ILO text), LEAVING OUT the
programme, the study plan and the expert's brief (they name a subject, they do not teach it), and scores the best
passage by how many of the sub-topic's subject words it holds (verbs like "explain", "identify" and words like "ship"
do not count). Below COVERED (half the subject words in one passage) the sub-topic is a gap. A course whose
knowledge base was declined is not checked here (the expert checks every fact in the script review instead).

This is a screen, not a proof: a passage that holds the words may still not teach the point, and the fact-checker
(L4) still proves every claim of the written script. What it stops is a script written with nothing to stand on.

A gap closes in one of two ways, both the operator's:
  1. sources for it are added to the course material folder and the knowledge base is built again
     (kb_tool.py build <folder> --course <course>) - then check again;
  2. the operator accepts it in their own words (accept --why): e.g. "general Excel skills, the instructor checks
     them in the script review". Accepted sub-topics are listed on every check, so the script review shows them.

Standard library only (kb_tool.py's own search).
"""
from __future__ import annotations

import argparse
import io
import json
import os
import re
import sys
from datetime import date

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "kb", "scripts"))
import workspace  # noqa: E402
import ilo_map  # noqa: E402
import kb_tool  # noqa: E402

COVERED = 0.5          # share of a sub-topic's subject words one passage must hold
TOP = 8                # passages looked at per sub-topic

# words that say what the trainee does or where, not what the subject is
GENERIC = set("""identify explain describe name list choose follow match classify show use apply compare state recognise
recognize give say find make build check write read select distinguish demonstrate plan prepare carry out perform
outline define know understand evaluate assess decide justify sort mark tell work set keep take
ship ship's ships shipboard board onboard on-board vessel vessels one two three each given example examples basic basics
principles principle concept concepts main types type kinds kind areas area their including incl etc way ways
practical tasks task variant deck engine""".split())

# a source that only NAMES the course's subjects: the programme, the study plan, the expert's brief
PROGRAMME_NAME = re.compile(r"(study[ _-]?plan|programme|program(?![a-z])|curricul|syllabus|course[ _-]?brief|"
                            r"project[ _-]?brief|course[ _-]?outline)", re.I)


def _load(p):
    try:
        with io.open(p, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def record_path(course):
    return workspace.claude_path(course, "kb_coverage.json")


def accepted(course, module):
    rec = _load(record_path(course)) or {}
    return dict(rec.get("accepted", {}).get(str(ilo_map.mkey(module)), {}))


def _intake_programme_names(course):
    i = _load(workspace.claude_path(course, "intake.json")) or {}
    names = set()
    for k in ("programme", "expert_brief", "brief"):
        v = i.get(k)
        for x in (v if isinstance(v, list) else [v]):
            if isinstance(x, str) and x.strip():
                names.add(os.path.basename(x.strip()).lower())
    return names


def kb_sources(kb, fmt):
    """[(source_path the search skips by, file name)]"""
    out = []
    if fmt == "csp":
        man = _load(os.path.join(kb, "SOURCE_MANIFEST.json")) or {}
        rows = man.get("sources") or []
        rows = rows.values() if isinstance(rows, dict) else rows
        for s in rows:
            p = (s or {}).get("source_path") or ""
            out.append((p, os.path.basename(p.replace("\\", "/"))))
    else:
        man = (_load(os.path.join(kb, "00_INDEX", "SOURCE_MANIFEST.json")) or {}).get("sources") or {}
        for key, s in man.items():
            p = (s or {}).get("source_path") or key
            out.append((p, os.path.basename(str(p).replace("\\", "/"))))
    return out


def programme_sources(course, kb, fmt):
    named = _intake_programme_names(course)
    return {p for p, name in kb_sources(kb, fmt) if PROGRAMME_NAME.search(name) or name.lower() in named}


def subtopic_text(course):
    prog = _load(workspace.claude_path(course, "programme.json")) or {}
    topics = prog.get("topics") or {}
    topics = topics.values() if isinstance(topics, dict) else topics
    out = {}
    for t in topics:
        for s in (t or {}).get("subtopics") or []:
            if isinstance(s, dict) and s.get("ref") and s.get("title"):
                out[str(s["ref"])] = s["title"]
    return out


class _Searcher:
    """kb_tool's own search, with the index read once for the whole module"""

    def __init__(self, kb, fmt):
        self.kb, self.fmt = kb, fmt
        self.memo = {}
        self._orig = kb_tool.load_json

        def cached(p):
            if p not in self.memo:
                self.memo[p] = self._orig(p)
            return self.memo[p]
        kb_tool.load_json = cached
        idx = cached(os.path.join(kb, "search_index", "index.json")) if fmt == "csp" else {}
        self.tok = kb_tool.toks_for(idx) if fmt == "csp" else kb_tool.toks

    def close(self):
        kb_tool.load_json = self._orig

    def search(self, q, skip):
        if self.fmt == "csp":
            return kb_tool.search_csp(self.kb, q, TOP, skip)
        return kb_tool.search_docling(self.kb, q, TOP, skip)


def subject_words(tok, text):
    return [t for t in dict.fromkeys(tok(text)) if t not in GENERIC and not t.isdigit()]


def score(searcher, query, skip):
    """(share of subject words in the best passage, the words, the best passage's file and page, the words it lacks)"""
    words = subject_words(searcher.tok, query)
    if not words:
        return 1.0, words, None, []
    best, best_hit, best_missing = 0.0, None, list(words)
    for h in searcher.search(query, skip):
        have = set(searcher.tok(h.get("text") or ""))
        missing = [w for w in words if w not in have]
        share = 1 - len(missing) / len(words)
        if share > best:
            best, best_hit, best_missing = share, h, missing
    where = None
    if best_hit:
        p1 = best_hit.get("p1")
        where = "%s%s" % (best_hit.get("file"), (" p. %s" % p1) if p1 else "")
    return best, words, where, best_missing


def applies(course):
    """the knowledge base this check reads, or None (declined / not decided / not readable - course_gate.py says those)"""
    import course_gate
    d = course_gate.kb_decision(course)
    if not d or d.get("answer") not in ("yes", "built"):
        return None
    paths = d.get("path") if isinstance(d.get("path"), list) else [d.get("path")]
    return [p for p in paths if p]


def check(course, module):
    """[{id, query, share, where, missing, verdict: covered|gap|accepted, why}] for every Sub-ILO row of the module.
    None when the check does not apply (no knowledge base to read, the final module, no rows)."""
    kbs = applies(course)
    if not kbs or ilo_map.mkey(module) in (None, "final"):
        return None
    rows = ilo_map.module_rows(ilo_map.read(course), module)
    if not rows:
        return None
    subs = subtopic_text(course)
    acc = accepted(course, module)
    best, searched = {}, False
    for kb in kbs:
        fmt = {"course_source_processor": "csp", "docling": "docling"}.get(kb_tool.detect(kb))
        if not fmt:
            continue
        skip = programme_sources(course, kb, fmt)
        try:
            s = _Searcher(kb, fmt)
        except (OSError, ValueError, KeyError):       # no search index (a test's bare folder, a build in progress): not checked
            continue
        searched = True
        try:
            for r in rows:
                rid = str(r.get("sub_ilo_id"))
                q = subs.get(rid) or r.get("sub_ilo_en") or r.get("sub_ilo") or ""
                share, words, where, missing = score(s, q, skip)
                if rid not in best or share > best[rid]["share"]:
                    best[rid] = {"id": rid, "query": q, "share": round(share, 2), "where": where, "missing": missing}
        except (OSError, ValueError, KeyError) as e:
            print("  (kb_coverage: %s could not be searched - %s)" % (kb, e))
        finally:
            s.close()
    if not searched:
        return None
    out = []
    for r in rows:
        rid = str(r.get("sub_ilo_id"))
        b = best.get(rid) or {"id": rid, "query": r.get("sub_ilo_en") or "", "share": 0.0, "where": None, "missing": []}
        if b["share"] >= COVERED:
            b["verdict"] = "covered"
        elif rid in acc:
            b["verdict"], b["why"] = "accepted", acc[rid].get("why")
        else:
            b["verdict"] = "gap"
        out.append(b)
    return out


def gaps(course, module):
    res = check(course, module)
    return [r for r in (res or []) if r["verdict"] == "gap"]


def problem(course, module):
    """one plain sentence for course_gate.py, or None"""
    g = gaps(course, module)
    if not g:
        return None
    lines = "; ".join("%s \"%s\" (best passage holds %d %% of its subject words%s)" % (
        r["id"], (r["query"][:70] + "...") if len(r["query"]) > 70 else r["query"], round(r["share"] * 100),
        (", lacks: " + ", ".join(r["missing"][:5])) if r["missing"] else "") for r in g)
    return ("L74 - the knowledge base has no source for %d sub-topic(s) of module %s, leaving out the programme and the "
            "brief, which only name them: %s. Add sources for them to the course material folder and build the "
            "knowledge base again (kb_tool.py build <folder> --course <course>), or record the operator's answer: "
            "kb_coverage.py accept <course> --module %s --ids %s --why \"<their words>\" --by \"<name>\""
            % (len(g), module, lines, module, ",".join(r["id"] for r in g)))


def cmd_check(course, module, as_json):
    mods = [module] if module else sorted({ilo_map.mkey(r.get("module")) for r in (ilo_map.read(course) or {}).get("rows", [])
                                           if ilo_map.mkey(r.get("module")) not in (None, "final")}, key=str)
    if applies(course) is None:
        print("No knowledge base to check against (declined, not decided or not readable) - course_gate.py says what to do.")
        return 0
    allres, bad = {}, 0
    for m in mods:
        res = check(course, m) or []
        allres[str(m)] = res
        bad += sum(1 for r in res if r["verdict"] == "gap")
    if as_json:
        print(json.dumps(allres, ensure_ascii=False, indent=2))
        return 2 if bad else 0
    for m, res in allres.items():
        print("Module %s - %d sub-topic(s): %d with a source, %d accepted, %d with none" % (
            m, len(res), sum(r["verdict"] == "covered" for r in res), sum(r["verdict"] == "accepted" for r in res),
            sum(r["verdict"] == "gap" for r in res)))
        for r in res:
            mark = {"covered": "ok ", "accepted": "acc", "gap": "GAP"}[r["verdict"]]
            print("  %s %-5s %3d %%  %s%s" % (mark, r["id"], round(r["share"] * 100), r["where"] or "-",
                                             ("  (accepted: %s)" % r.get("why")) if r["verdict"] == "accepted" else ""))
    if bad:
        print("\n%d sub-topic(s) have no source (L74). Add sources and build the knowledge base again, or record the "
              "operator's answer with: kb_coverage.py accept <course> --module N --ids ... --why \"...\" --by \"...\"" % bad)
        return 2
    return 0


def cmd_accept(course, module, ids, why, by):
    if not (why or "").strip() or not (by or "").strip():
        print("Stopped - an accepted gap needs the operator's own reason (--why) and their name (--by).")
        return 2
    rows = {str(r.get("sub_ilo_id")) for r in ilo_map.module_rows(ilo_map.read(course), module)}
    want = [i.strip() for i in ids.split(",") if i.strip()]
    unknown = [i for i in want if i not in rows]
    if unknown:
        print("Stopped - module %s has no Sub-ILO %s (it has: %s)." % (module, ", ".join(unknown), ", ".join(sorted(rows))))
        return 2
    p = record_path(course)
    rec = _load(p) or {}
    acc = rec.setdefault("accepted", {}).setdefault(str(ilo_map.mkey(module)), {})
    for i in want:
        acc[i] = {"why": why.strip(), "by": by.strip(), "on": date.today().isoformat()}
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with io.open(p, "w", encoding="utf-8", newline="\n") as f:
        json.dump(rec, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print("Recorded: module %s, sub-topic(s) %s accepted without a source by %s - \"%s\".\n"
          "  The script review lists them, and the fact-checker still judges every claim." % (module, ", ".join(want), by, why))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check"); c.add_argument("course"); c.add_argument("--module"); c.add_argument("--json", action="store_true")
    a = sub.add_parser("accept"); a.add_argument("course"); a.add_argument("--module", required=True)
    a.add_argument("--ids", required=True); a.add_argument("--why", required=True); a.add_argument("--by", required=True)
    o = ap.parse_args(argv)
    course = workspace.work_folder(o.course, create=False)
    if o.cmd == "check":
        return cmd_check(course, o.module, o.json)
    return cmd_accept(course, o.module, o.ids, o.why, o.by)


if __name__ == "__main__":
    sys.exit(main())
