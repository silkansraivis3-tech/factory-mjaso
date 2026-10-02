#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Read a course knowledge base - either kind - without ever writing into it.

    kb_tool.py find    <course folder> [--json]
    kb_tool.py detect  <kb folder>
    kb_tool.py sources <kb folder> --course <course folder> [--json]
    kb_tool.py decide  <course folder> --keep "<source path>" [--keep ...] [--different "<group id>" ...]
    kb_tool.py search  <kb folder> "<what you are looking for>" --course <course folder> [--top 12] [--all]

WHY THIS EXISTS
Until 2.13.0 the factory assumed every knowledge base was a docling extraction, and the owner's
own tool - the Course Source Processor - was unknown to it. Both are read here, by their files:

  COURSE SOURCE PROCESSOR   SOURCE_MANIFEST.json + COURSE_INDEX.md at the top, sources/<name>/
                            {document.md, metadata.json, tables/, images/}, search_index/
                            {index.json, chunks.jsonl}. The index already holds BM25 postings and
                            the byte offset of every piece, so a search reads a few pieces, not books.
  DOCLING                   00_INDEX/SOURCE_MANIFEST.json, and one folder per source with
                            content.md, chunks.jsonl, source_metadata.json. content.md can be over a
                            megabyte and is never read whole.

WHAT IT DOES
  find      every knowledge base in the course folder, its sub-folders and one level up - by its
            files, never by its name. Writes nothing. One found: used. Several: a ready question. (2.13.1)
  sources   lists every source; groups EXACT duplicates (same file content - cited once, no
            question needed) and LIKELY EDITIONS of one publication (MARPOL 2022 beside an older
            MARPOL; "SIGGTO LGHP (4th)" beside "SIGTTO liquified gas handling principles"). For
            each edition group it writes a ready pop-up question - "which edition is current?" -
            into <course>/_factory/kb_sources.json. The operator answers; `decide` records it.
  decide    records the operator's answer in <course>/_factory/intake.json: which one is current,
            or that the group is really different publications.
  search    ranks pieces with the knowledge base's own index (BM25) and writes a retrieval pack -
            the matching extracts with file and page - into <course>/_factory/retrieval/. Sources the
            operator marked as not current, and exact duplicates, are left out (--all keeps them).

WHAT IT NEVER DOES
Write inside the knowledge base (L14). Every write goes to the course folder, and a course folder
inside the knowledge base is refused. The SEARCH program writes its packs into the knowledge
base's own retrieval/ folder; this one does not.
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import io
import json
import math
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import date

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

TOKEN = re.compile(r"[^\W\d_]{2,}", re.U)
STOP = set("""a an and are as at be by for from has have in is it its of on or that the this to was
were will with which into than then there these those not no but can may shall should such""".split())


# ------------------------------------------------------------------ format detection
def detect(kb):
    if os.path.isfile(os.path.join(kb, "SOURCE_MANIFEST.json")) and os.path.isdir(os.path.join(kb, "sources")):
        return "course_source_processor"
    if os.path.isfile(os.path.join(kb, "00_INDEX", "SOURCE_MANIFEST.json")):
        return "docling"
    return None


def load_json(p):
    with io.open(p, encoding="utf-8") as f:
        return json.load(f)


def inside(child, parent):
    c = os.path.normcase(os.path.abspath(child))
    p = os.path.normcase(os.path.abspath(parent))
    return c == p or c.startswith(p.rstrip("\\/") + os.sep)


# ------------------------------------------------------------------ source inventory
def inventory(kb, fmt):
    """One row per source: path, file, title, sha256, the tool's own duplicate mark."""
    rows = []
    if fmt == "course_source_processor":
        for s in load_json(os.path.join(kb, "SOURCE_MANIFEST.json"))["sources"]:
            title = ""
            meta = os.path.join(kb, s.get("output_folder") or "", "metadata.json")
            if s.get("output_folder") and os.path.isfile(meta):
                try:
                    title = load_json(meta).get("title") or ""
                except (OSError, ValueError):
                    pass
            rows.append({"path": s["source_path"], "file": s["original_filename"], "title": title,
                         "sha256": s.get("sha256") or "", "duplicate_of": s.get("duplicate_of_path"),
                         "doc": s.get("doc_id"), "converted_from": s.get("converted_from")})
    else:
        for key, s in load_json(os.path.join(kb, "00_INDEX", "SOURCE_MANIFEST.json"))["sources"].items():
            sha = s.get("source_sha256") or ""
            out = s.get("output_directory")
            if out and not sha and os.path.isfile(os.path.join(kb, out, "source_metadata.json")):
                try:
                    sha = load_json(os.path.join(kb, out, "source_metadata.json")).get("source_sha256") or ""
                except (OSError, ValueError):
                    pass
            rows.append({"path": s.get("source_path") or key, "file": os.path.basename(s.get("source_path") or key),
                         "title": "", "sha256": sha, "duplicate_of": None, "doc": out, "converted_from": None})
    return rows


EDITION_WORDS = re.compile(r"\b(consolidated|edition|editions|ed|rev|revision|revised|version|ver|v\d+(\.\d+)*|"
                           r"\d+(st|nd|rd|th)|first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth|"
                           r"pdf|docx?|pptx?|final|draft|copy|new|old|updated|latest)\b")
YEAR = re.compile(r"\b(19|20)\d{2}\b")
SUPPLEMENT = re.compile(r"\b(amendment|amendments|supplement|circular|circ|corrigendum|errata|addendum|annex)\b", re.I)


def name_key(row):
    """The publication's name with its edition, year and file type taken out."""
    base = os.path.splitext(row["file"])[0]
    s = base.lower().replace("_", " ").replace("-", " ")
    s = re.sub(r"[\[\](){},]", " ", s)
    s = YEAR.sub(" ", s)
    s = re.sub(r"\bv\d+(\.\d+)*\b", " ", s)            # a version number is an edition marker
    s = EDITION_WORDS.sub(" ", s)
    # other numbers stay: "1.04" and "1.35" are two different IMO model courses
    s = re.sub(r"(?<!\d)\.|\.(?!\d)", " ", s)
    return " ".join(w for w in s.split() if w not in STOP)


def edition_hint(row):
    s = row["file"] + " " + (row["title"] or "")
    bits = YEAR.findall(s) and [m.group(0) for m in YEAR.finditer(s)] or []
    bits += re.findall(r"\b\d+(?:st|nd|rd|th)\b", s, re.I)
    return ", ".join(dict.fromkeys(bits)) or "no year or edition in the name"


def initials(words):
    return "".join(w[0] for w in words if w)


def same_publication(a, b):
    """Two name keys that are probably one publication in different editions."""
    if not a or not b:
        return False
    if a == b:
        return True
    wa, wb = a.split(), b.split()
    # different numbers are different documents: exercise 14.2.4 is not 14.2.5, model course 1.04 is not 1.35
    if {w for w in wa if any(ch.isdigit() for ch in w)} != {w for w in wb if any(ch.isdigit() for ch in w)}:
        return False
    # an acronym on one side spelling out the other: LGHP = liquified gas handling principles
    for x, y in ((wa, wb), (wb, wa)):
        for tok in x:
            if len(tok) >= 3 and len(y) >= 3:
                for i in range(len(y) - len(tok) + 1):
                    if initials(y[i:i + len(tok)]) == tok:
                        rest_x = [t for t in x if t != tok]
                        # the rest of the short name must agree with the long one (typo-tolerant)
                        if all(any(difflib.SequenceMatcher(None, r, t).ratio() >= 0.8 for t in y) for r in rest_x):
                            return True
    # word by word: identical, or a real typo (SIGTTO / SIGGTO). A short word that differs is a
    # different thing, not a typo: LNG / LPG, membrane / spherical.
    if len(wa) == len(wb):
        pairs = [(x, y) for x, y in zip(wa, wb) if x != y]
        if pairs and all(min(len(x), len(y)) >= 5 and difflib.SequenceMatcher(None, x, y).ratio() >= 0.8
                         for x, y in pairs):
            return True
    sa, sb = set(wa), set(wb)
    small, big = (sa, sb) if len(sa) <= len(sb) else (sb, sa)
    return len(small) >= 2 and small <= big and len(small) / len(big) >= 0.5


def group_sources(rows):
    exact = defaultdict(list)
    for r in rows:
        if r["sha256"]:
            exact[r["sha256"]].append(r)
    exact_groups = [g for g in exact.values() if len(g) > 1]
    # tool-marked duplicates whose sha was not given still form a group
    by_path = {r["path"]: r for r in rows}
    for r in rows:
        if r["duplicate_of"] and r["duplicate_of"] in by_path:
            pair = [by_path[r["duplicate_of"]], r]
            if not any(r in g for g in exact_groups):
                exact_groups.append(pair)
    in_exact = {id(r) for g in exact_groups for r in g[1:]}     # the extra copies

    # one representative per distinct content
    reps = [r for r in rows if id(r) not in in_exact]
    keys = {id(r): name_key(r) for r in reps}
    parent = {id(r): id(r) for r in reps}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    for i, a in enumerate(reps):
        for b in reps[i + 1:]:
            if same_publication(keys[id(a)], keys[id(b)]):
                parent[find(id(a))] = find(id(b))
    buckets = defaultdict(list)
    for r in reps:
        buckets[find(id(r))].append(r)
    edition_groups, format_copies = [], []
    for g in buckets.values():
        if len(g) < 2:
            continue
        stems = {os.path.splitext(r["file"])[0].lower() for r in g}
        exts = {os.path.splitext(r["file"])[1].lower().lstrip(".").rstrip("x") for r in g}
        if len(stems) == 1 and len(exts) == 1:      # plan.doc + plan.docx: one document, two formats
            format_copies.append(sorted(g, key=lambda r: r["file"], reverse=True))
        else:
            edition_groups.append(g)
    return exact_groups, edition_groups, format_copies


def group_id(g):
    return "ed-" + hashlib.sha1("|".join(sorted(r["path"] for r in g)).encode("utf-8")).hexdigest()[:8]


def question_for(g):
    """A ready pop-up question (the ask-question tool: 2-4 options, header <= 12 characters)."""
    opts = []
    for r in sorted(g, key=lambda r: r["file"])[:3]:
        label = r["file"] if len(r["file"]) <= 60 else r["file"][:57] + "..."
        opts.append({"label": label, "description": "Current: cite this one. %s. %s"
                     % (edition_hint(r), r["path"])})
    supp = any(SUPPLEMENT.search(r["file"]) for r in g)
    opts.append({"label": "Different publications — keep all",
                 "description": ("One of them looks like an amendment or supplement, not an edition. "
                                 if supp else "") + "They only look alike; the factory cites each where it applies."})
    names = " · ".join(r["file"] for r in g)
    return {"id": group_id(g), "header": "Edition",
            "question": "The knowledge base has what looks like the same publication more than once: %s. "
                        "Which edition is current?" % names,
            "multiSelect": False, "options": opts, "members": [r["path"] for r in g]}


def cmd_sources(kb, course, as_json):
    fmt = detect(kb)
    if not fmt:
        return no_kb(kb)
    if inside(course, kb):
        return refuse_inside(course, kb)
    rows = inventory(kb, fmt)
    exact, editions, fmt_copies = group_sources(rows)
    report = {
        "_what": "Written by course-factory/kb/scripts/kb_tool.py sources. Internal - never shipped.",
        "knowledge_base": os.path.abspath(kb), "format": fmt, "written": date.today().isoformat(),
        "source_count": len(rows),
        "exact_duplicates": [[r["path"] for r in g] for g in exact],
        "format_copies": [[r["path"] for r in g] for g in fmt_copies],
        "edition_groups": [question_for(g) for g in editions],
    }
    out = _claude(course, "kb_sources.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with io.open(out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
        f.write("\n")
    if as_json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    print("The knowledge base is readable.\n\n  Folder:  %s\n  Kind:    %s\n  Sources: %d"
          % (os.path.abspath(kb), {"course_source_processor": "Course Source Processor",
                                   "docling": "docling (older)"}[fmt], len(rows)))
    if exact:
        print("\n  %d file(s) are exact copies of another file. Each is cited once; nothing to decide:" % sum(len(g) - 1 for g in exact))
        for g in exact[:12]:
            names = sorted({r["file"] for r in g})
            print("    - %s  -  %d copies%s" % (names[0], len(g),
                  (" (also named %s)" % ", ".join(names[1:])) if len(names) > 1 else ""))
        if len(exact) > 12:
            print("    ... and %d more - every path is listed in %s" % (len(exact) - 12, out))
    if fmt_copies:
        print("\n  %d document(s) exist in two file formats (for example .doc and .docx). The newer format\n"
              "  is cited; nothing to decide:" % len(fmt_copies))
        for g in fmt_copies:
            print("    - %s  (also %s)" % (g[0]["file"], ", ".join(r["file"] for r in g[1:])))
    if editions:
        print("\n  %d publication(s) appear in more than one edition. These go into the intake pop-up\n"
              "  as \"which edition is current?\":" % len(editions))
        for g in editions:
            print("    - " + "  |  ".join("%s (%s)" % (r["file"], edition_hint(r)) for r in g))
    else:
        print("\n  No publication appears in more than one edition.")
    print("\n  Written to %s" % out)
    return 0


# ------------------------------------------------------------------ decisions
def cmd_decide(course, keep, different):
    rep_p = _claude(course, "kb_sources.json")
    if not os.path.isfile(rep_p):
        print("Stopped - run `kb_tool.py sources <kb> --course %s` first; there is nothing to decide yet." % course)
        return 2
    rep = load_json(rep_p)
    ip = _claude(course, "intake.json")
    intake = load_json(ip) if os.path.isfile(ip) else {}
    ed = intake.setdefault("editions", {})
    done = []
    for g in rep["edition_groups"]:
        members = g["members"]
        if g["id"] in different:
            ed[g["id"]] = {"decision": "different publications", "current": members, "superseded": []}
            done.append(g["id"])
            continue
        chosen = [m for m in members if m in keep]
        if chosen:
            ed[g["id"]] = {"decision": "current edition chosen by the operator", "current": chosen,
                           "superseded": [m for m in members if m not in chosen], "decided": date.today().isoformat()}
            done.append(g["id"])
    open_ = [g["id"] for g in rep["edition_groups"] if g["id"] not in ed]
    with io.open(ip, "w", encoding="utf-8", newline="\n") as f:
        json.dump(intake, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print("Recorded %d decision(s) in %s.%s" % (len(done), ip,
          ("\n  Still open: %s" % ", ".join(open_)) if open_ else "\n  Every edition question is answered."))
    return 0


def superseded(course):
    ip = _claude(course, "intake.json")
    if not os.path.isfile(ip):
        return set()
    return {p for d in load_json(ip).get("editions", {}).values() for p in d.get("superseded", [])}


# ------------------------------------------------------------------ search
def toks(s):
    return [t for t in TOKEN.findall(s.lower()) if t not in STOP]


def search_csp(kb, q, top, skip_paths):
    idx = load_json(os.path.join(kb, "search_index", "index.json"))
    k1, b = idx["bm25"]["k1"], idx["bm25"]["b"]
    N, avg = idx["chunk_count"], idx["avg_tokens_per_chunk"]
    chunks, df, post = idx["chunks"], idx["df"], idx["postings"]
    score = Counter()
    for t in dict.fromkeys(toks(q)):
        if t not in post:
            continue
        idf = math.log(1 + (N - df[t] + 0.5) / (df[t] + 0.5))
        for ci, tf in post[t]:
            n = chunks[ci].get("n") or avg
            score[ci] += idf * tf * (k1 + 1) / (tf + k1 * (1 - b + b * n / avg))
    hits = []
    with open(os.path.join(kb, "search_index", "chunks.jsonl"), "rb") as f:
        for ci, s in score.most_common():
            c = chunks[ci]
            if c.get("sp") in skip_paths or c.get("nav"):
                continue
            f.seek(c["off"])
            rec = json.loads(f.read(c["bytes"]).decode("utf-8"))
            hits.append({"score": s, "file": rec["source_filename"], "path": rec["source_path"],
                         "p1": rec.get("page_start"), "p2": rec.get("page_end"), "unit": rec.get("unit_kind") or "page",
                         "heading": " › ".join(rec.get("heading_path") or []), "text": rec["text"],
                         "asset": rec.get("asset_path") or ""})
            if len(hits) >= top:
                break
    return hits


def search_docling(kb, q, top, skip_paths):
    man = load_json(os.path.join(kb, "00_INDEX", "SOURCE_MANIFEST.json"))["sources"]
    docs = []
    for key, s in man.items():
        path = s.get("source_path") or key
        out = s.get("output_directory")
        cj = os.path.join(kb, out or "", "chunks.jsonl")
        if path in skip_paths or not out or not os.path.isfile(cj):
            continue
        with io.open(cj, encoding="utf-8", errors="replace") as f:
            for line in f:
                try:
                    c = json.loads(line)
                except ValueError:
                    continue
                t = toks(c.get("text") or "")
                docs.append((path, c, Counter(t), len(t)))
    if not docs:
        return []
    N = len(docs)
    avg = sum(d[3] for d in docs) / N or 1
    qt = list(dict.fromkeys(toks(q)))
    dfc = {t: sum(1 for d in docs if t in d[2]) for t in qt}
    k1, b = 1.2, 0.75
    scored = []
    for path, c, tf, n in docs:
        s = 0.0
        for t in qt:
            if tf.get(t):
                idf = math.log(1 + (N - dfc[t] + 0.5) / (dfc[t] + 0.5))
                s += idf * tf[t] * (k1 + 1) / (tf[t] + k1 * (1 - b + b * n / avg))
        if s > 0:
            pages = c.get("page_numbers") or []
            scored.append({"score": s, "file": os.path.basename(path), "path": path,
                           "p1": min(pages) if pages else None, "p2": max(pages) if pages else None, "unit": "page",
                           "heading": " › ".join(c.get("headings") or []), "text": c.get("text") or "", "asset": ""})
    scored.sort(key=lambda h: -h["score"])
    return scored[:top]


def slug(s):
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")[:60] or "search"


def cmd_search(kb, q, course, top, keep_all):
    fmt = detect(kb)
    if not fmt:
        return no_kb(kb)
    if inside(course, kb):
        return refuse_inside(course, kb)
    rows = inventory(kb, fmt)
    exact, _, fmt_copies = group_sources(rows)
    skip = set() if keep_all else (superseded(course) | {r["path"] for g in exact + fmt_copies for r in g[1:]})
    hits = (search_csp if fmt == "course_source_processor" else search_docling)(kb, q, top, skip)
    outdir = _claude(course, "retrieval")
    os.makedirs(outdir, exist_ok=True)
    out = os.path.join(outdir, "%s_%s.md" % (date.today().isoformat(), slug(q)))
    L = ["# Retrieval pack — %s" % q, "",
         "*Written %s by course-factory/kb/scripts/kb_tool.py from `%s` (%s). Extracts are the source's own "
         "text, never summarised. Cite the file and page shown, not this pack.*" % (date.today().isoformat(),
                                                                                   os.path.abspath(kb), fmt), ""]
    if skip:
        n_old = len(superseded(course) & skip)
        L += ["Left out: %d exact copy / other-format copy of a file that is searched, and %d edition(s) the "
              "operator marked as not current." % (len(skip) - n_old, n_old), ""]
    if not hits:
        L += ["**Nothing in the knowledge base matched.** Try the equipment's other names, the abbreviation, "
              "or the older term. A stated gap is a good answer (L4)."]
    for i, h in enumerate(hits, 1):
        where = "%s %s" % (h["unit"], h["p1"]) if h["p1"] == h["p2"] or h["p2"] is None else "%ss %s–%s" % (h["unit"], h["p1"], h["p2"])
        L += ["---", "", "## %d · %s — %s" % (i, h["file"], where)]
        if h["heading"]:
            L.append("*%s*" % h["heading"])
        L += ["", "`%s`" % h["path"], ""]
        if h["asset"]:
            L += ["Picture: `%s`" % h["asset"], ""]
        L += [h["text"].strip(), ""]
    with io.open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(L) + "\n")
    print("%d extract(s) for \"%s\" written to\n  %s" % (len(hits), q, out))
    return 0


# ------------------------------------------------------------------ find
SKIP_DIRS = {".git", "node_modules", "__pycache__", "_factory", "working_claude", "to_review", ".venv", "venv", "$recycle.bin"}


def kb_summary(path, fmt):
    try:
        if fmt == "course_source_processor":
            m = load_json(os.path.join(path, "SOURCE_MANIFEST.json"))
            n = m.get("source_count") or len(m.get("sources") or [])
        else:
            n = len(load_json(os.path.join(path, "00_INDEX", "SOURCE_MANIFEST.json")).get("sources") or {})
    except (OSError, ValueError):
        n = None
    return {"path": os.path.abspath(path), "format": fmt, "sources": n}


def _claude(course, *parts):
    """working_claude/<parts> in the work folder - an older course's _factory/ copy is found too (L44)."""
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "scripts"))
    import workspace
    return workspace.claude_path(course, *parts)


def find_kbs(folder, max_depth=5, up=1):
    """Every knowledge base in the folder, its sub-folders, and `up` levels above. Read-only."""
    found, seen = [], set()

    def walk(top, depth_limit, exclude=None):
        top_depth = os.path.abspath(top).rstrip("\\/").count(os.sep)
        for dirpath, dirnames, _ in os.walk(top):
            here = os.path.abspath(dirpath)
            if exclude and os.path.normcase(here) == os.path.normcase(exclude):
                dirnames[:] = []
                continue
            fmt = detect(here)
            if fmt:
                key = os.path.normcase(here)
                if key not in seen:
                    seen.add(key)
                    found.append(kb_summary(here, fmt))
                dirnames[:] = []                      # never walk inside a knowledge base
                continue
            depth = here.rstrip("\\/").count(os.sep) - top_depth
            dirnames[:] = [d for d in dirnames if d.lower() not in SKIP_DIRS and not d.startswith(".")] \
                if depth < depth_limit else []

    walk(folder, max_depth)
    above, prev = os.path.abspath(folder), None
    for _ in range(up):
        prev, above = above, os.path.dirname(above)
        if not above or above == prev:
            break
        walk(above, 1, exclude=prev)                  # the folder above and its direct sub-folders only
    return found


def cmd_find(folder, as_json):
    if not os.path.isdir(folder):
        print("Stopped - that folder does not exist:\n    %s" % folder)
        return 2
    kbs = find_kbs(folder)
    result = {"looked_in": os.path.abspath(folder), "found": kbs}
    if len(kbs) > 1:
        result["question"] = {
            "header": "Sources", "multiSelect": False,
            "question": "More than one knowledge base was found. Which one is this course's?",
            "options": [{"label": os.path.basename(k["path"]) or k["path"],
                         "description": "%s - %s sources - %s" % (
                             {"course_source_processor": "Course Source Processor", "docling": "docling"}[k["format"]],
                             k["sources"] if k["sources"] is not None else "?", k["path"])} for k in kbs[:4]]}
    if as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if kbs else 1
    if not kbs:
        print("No knowledge base was found in\n    %s\n  or its sub-folders, or one level up. It goes into the intake pop-up as\n"
              "  \"Where is the knowledge base for this course?\"" % os.path.abspath(folder))
        return 1
    print("Found %d knowledge base(s) - nothing was written anywhere:\n" % len(kbs))
    for k in kbs:
        print("  - %s\n      %s · %s sources" % (k["path"], {"course_source_processor": "Course Source Processor",
                                                             "docling": "docling (older)"}[k["format"]],
                                               k["sources"] if k["sources"] is not None else "?"))
    print("\n  %s" % ("One found - it is used, no question needed." if len(kbs) == 1 else
                      "More than one - the intake pop-up asks which is this course's (the question is ready with --json)."))
    return 0


# ------------------------------------------------------------------ plain messages
def no_kb(kb):
    print("Stopped - this folder is not a knowledge base the factory can read:\n    %s\n"
          "  A Course Source Processor knowledge base has SOURCE_MANIFEST.json and a sources folder at\n"
          "  the top; an older docling one has 00_INDEX\\SOURCE_MANIFEST.json. Point at the folder that\n"
          "  holds one of those (often called KNOWLEDGE_BASE or knowledge_base)." % kb)
    return 2


def refuse_inside(course, kb):
    print("Stopped - nothing was written.\n\n  The course folder is inside the knowledge base:\n    %s\n"
          "  The knowledge base is read-only; the factory never writes into it. Give the course's own\n"
          "  folder instead, outside the knowledge base." % course)
    return 2


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    fi = sub.add_parser("find"); fi.add_argument("folder"); fi.add_argument("--json", action="store_true")
    d = sub.add_parser("detect"); d.add_argument("kb")
    s = sub.add_parser("sources"); s.add_argument("kb"); s.add_argument("--course", required=True); s.add_argument("--json", action="store_true")
    c = sub.add_parser("decide"); c.add_argument("course"); c.add_argument("--keep", action="append", default=[])
    c.add_argument("--different", action="append", default=[])
    q = sub.add_parser("search"); q.add_argument("kb"); q.add_argument("query"); q.add_argument("--course", required=True)
    q.add_argument("--top", type=int, default=12); q.add_argument("--all", action="store_true")
    a = ap.parse_args(argv)
    if getattr(a, "course", None):                 # what the factory writes goes to course\ (L40)
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "scripts"))
        import workspace
        a.course = workspace.work_folder(a.course)
    if a.cmd == "find":
        return cmd_find(a.folder, a.json)
    if a.cmd == "detect":
        fmt = detect(a.kb)
        print(fmt or "not a knowledge base")
        return 0 if fmt else 2
    if a.cmd == "sources":
        return cmd_sources(a.kb, a.course, a.json)
    if a.cmd == "decide":
        return cmd_decide(a.course, set(a.keep), set(a.different))
    return cmd_search(a.kb, a.query, a.course, a.top, a.all)


if __name__ == "__main__":
    sys.exit(main())
