#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Every claim of a module's content script proved in the course's own sources - the fact-checker agent's tool (L4).

    fact_check.py prepare   <course> --module 1         every claim, searched; what a source says word for word is proved here
    fact_check.py next      <course> --module 1 [--n 20] the next claims to judge, each with its source passages (JSON)
    fact_check.py search    <course> --module 1 "<words>" [--top 5]   one more search of the course's sources
    fact_check.py judge     <course> --module 1 --file <verdicts.json>  the agent's verdicts, each quote checked
    fact_check.py rewrites  <course> --module 1         the claims no source proves, for the writer to rewrite once
    fact_check.py rewrite   <course> --module 1 --file <changes.json> [--by "<writer>"]   the writer's new words for them
    fact_check.py questions <course> --module 1         what is still not proved after the rewrite: the operator's questions
    fact_check.py answer    <course> --module 1 --id <claim> (--cut | --keep "<source>" | --replace "<words>") --by "<name>"
    fact_check.py fixes     <course> --module 1 [--apply]  the cuts and corrections as a change list for content_script propose
                                                      (--apply: an unattended build applies them itself, each logged)
    fact_check.py status    <course> --module 1

WHY THIS EXISTS
A script is written by a model, and a model writes from memory: a slide can state a pressure, a rule or a reason that no
source of the course holds, and a ship's officer learns it as a fact. So each module's script is checked the moment it is
saved, while the writer goes on with the next module, and every claim is looked up in the course's own sources: the
knowledge base, then the source files themselves (the original documents, not only the knowledge base's pieces), then the
old course; what none of them says the fact-checker looks for on the internet. The mechanical part is here - finding the
claims, searching, proving what a passage says word for word, refusing a quote no source holds, recording where each
claim was searched - so the agent's own rules stay short: it reads a claim and its passages and says found, partly or
not found.

WHAT IS NOT PROVED
A claim found nowhere goes back to the writer once (rewrites): the writer rewrites those lines from what the sources do
say, or leaves a line out, and the fact-checker judges them again. What is still not proved after that one rewrite is
never cut silently: it is a question for the operator (questions) - the sentence and its screen, where it was searched
with the closest passage found, and why it is a problem - answered with cut, keep (the operator names the source) or
replace (the operator's own words). In an unattended build nobody answers: fixes --apply cuts it and writes the question
to working_claude/fact_check/MNN.operator.json for the operator to read. A claim proved only on the internet keeps its
web address and the words quoted from it, is marked a web source and is listed for the operator to look at.

WHAT A CLAIM IS
A line a slide shows (its text or its points, the answer it reveals), a line of the instructor's notes that holds a
number, and the right answer and feedback of a question. Lines of fewer than four words with no number, and questions,
are not claims. A claim is known by its words: an unchanged line keeps its verdict, a changed one is judged again.

The verdicts are in working_claude/fact_check/MNN.json. content_script.py's check refuses the approval while a claim of
a course with a knowledge base is not judged, or one judged not found or partly is still in the script. Exit 0, 1
problems or claims left, 2 bad input.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import os
import re
import sys
import zipfile
from collections import Counter
from xml.etree import ElementTree as ET

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "kb", "scripts"))
import content_script as cs  # noqa: E402
import workspace  # noqa: E402

PROVED_SHARE = 0.8          # a passage sentence holding this share of a claim's words, and all its numbers, proves it
PASSAGE_CHARS = 450
VERDICTS = ("found", "partly", "not_found", "not_a_claim")
NUM = re.compile(r"\d{1,3}(?:[ ,]\d{3})+(?!\d)|\d+(?:[.,]\d+)?")
WORD = re.compile(r"[^\W\d_]{3,}", re.U)
WHERE = ("kb", "source_files", "old_course")          # where a claim is looked for, in this order; then the internet
WHERE_NAMES = {"kb": "the knowledge base", "source_files": "the source files", "old_course": "the old course",
               "web": "the internet", "operator": "the operator"}
DOC_TYPES = (".pdf", ".docx", ".pptx", ".txt", ".md")
PIECE_CHARS = 1500
WEB_QUOTE_WORDS = 5
OPTIONS = ["cut it", "keep it - the operator names the source", "replace it with the operator's own words"]


def store_path(course, module):
    return workspace.claude_path(course, "fact_check", "%s.json" % cs.mid(module))


def load_store(course, module):
    try:
        return json.load(io.open(store_path(course, module), encoding="utf-8"))
    except (OSError, ValueError):
        return {"module": str(module), "claims": {}}


def save_store(course, module, st):
    p = store_path(course, module)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    io.open(p, "w", encoding="utf-8", newline="\n").write(json.dumps(st, ensure_ascii=False, indent=1))
    return p


def course_kbs(course):
    """the course's knowledge bases with a search index (kb_tool.py sources wrote where they are)"""
    try:
        src = json.load(io.open(workspace.claude_path(course, "kb_sources.json"), encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return []
    rows = src if isinstance(src, list) else src.get("entries") or [src]
    return [x["knowledge_base"] for x in rows if isinstance(x, dict) and x.get("knowledge_base")
            and os.path.isfile(os.path.join(x["knowledge_base"], "search_index", "index.json"))]


def stems(text):
    return [w[:5] for w in WORD.findall((text or "").lower()) if w not in cs.STOP]


def numbers(text):
    return {cs.plain_number(x) for x in NUM.findall(text or "")}


def norm(text):
    return re.sub(r"\s+", " ", re.sub(r"[^\w%.,-]+", " ", (text or "").lower())).strip()


def claim_id(sid, field, text):
    return hashlib.sha1(("%s|%s|%s" % (sid, field, norm(text))).encode("utf-8")).hexdigest()[:10]


INSTRUCTION = re.compile(r"^(?:in pairs|in teams|pairs|write|tap|look|find|choose|mark|drag|match|sort|discuss|open|turn|"
                         r"compare|name|say|vote|read|watch|show|point|put|fill|draw|check)\b|\byour (?:card|screen|tablet|answers?)\b",
                         re.I)


def is_claim(line):
    """a line that states something: four words or a number - not a question, not an instruction to the room"""
    t = line.strip()
    return bool(t) and not t.endswith("?") and not INSTRUCTION.search(t) and (len(t.split()) >= 4 or bool(NUM.search(t)))


def field_lines(s, field):
    """a field's lines: a list as it is (a scenario's "why"), a text by its lines"""
    v = s.get(field)
    return [str(x) for x in v] if isinstance(v, list) else cs.lines_of(cs.as_text(v))


def claims_of(script):
    """[(id, screen, field, line number, words)] - every claim of the script"""
    out = []

    def add(sid, field, n, line):
        line = re.sub(r"^\s*[-*•]\s*", "", line).strip()
        if is_claim(line):
            out.append((claim_id(sid, field, line), sid, field, n, line))
    for s in script.get("screens", []):
        sid, k = s.get("id"), s.get("kind")
        if k == "slide":
            field = "points" if s.get("points") else "text"
            if s.get("choices"):              # a scenario: its lines set the situation, its "why" lines state the facts
                field = "why"
            for n, x in enumerate(field_lines(s, field), 1):
                add(sid, field, n, x)
            for n, x in enumerate(cs.lines_of(cs.as_text(s.get("reveal"))), 1):
                add(sid, "reveal", n, x)
            for n, x in enumerate(cs.lines_of(s.get("notes")), 1):
                if NUM.search(x):
                    add(sid, "notes", n, x)
        elif k in cs.TASKS:
            _, right, _ = cs.read_answer(s)
            for n, x in enumerate(right, 1):
                add(sid, "answer", n, x)
            for n, x in enumerate(cs.lines_of(cs.as_text(s.get("feedback"))), 1):
                add(sid, "feedback", n, x)
    return out


class Index:
    """the knowledge bases' BM25 indexes, loaded once"""

    def __init__(self, kbs):
        import kb_tool
        self.kb_tool, self.kbs = kb_tool, []
        for kb in kbs:
            idx = json.load(io.open(os.path.join(kb, "search_index", "index.json"), encoding="utf-8"))
            self.kbs.append((kb, idx))

    def search(self, q, top=3):
        hits = []
        for kb, idx in self.kbs:
            k1, b = idx["bm25"]["k1"], idx["bm25"]["b"]
            N, avg, chunks, df, post = idx["chunk_count"], idx["avg_tokens_per_chunk"], idx["chunks"], idx["df"], idx["postings"]
            score = Counter()
            for t in dict.fromkeys(self.kb_tool.toks_for(idx)(q)):
                if t in post:
                    idf = math.log(1 + (N - df[t] + 0.5) / (df[t] + 0.5))
                    for ci, tf in post[t]:
                        n = chunks[ci].get("n") or avg
                        score[ci] += idf * tf * (k1 + 1) / (tf + k1 * (1 - b + b * n / avg))
            with open(os.path.join(kb, "search_index", "chunks.jsonl"), "rb") as f:
                for ci, sc in score.most_common(top * 3):
                    c = chunks[ci]
                    if c.get("nav"):
                        continue
                    f.seek(c["off"])
                    rec = json.loads(f.read(c["bytes"]).decode("utf-8"))
                    pages = rec.get("page_start"), rec.get("page_end")
                    hits.append({"score": sc, "src": "%s p.%s" % (rec.get("source_filename"), pages[0] if pages[0] == pages[1] or not pages[1]
                                                                 else "%s-%s" % pages), "text": rec.get("text") or "", "where": "kb"})
        hits.sort(key=lambda h: -h["score"])
        out, seen = [], set()
        for h in hits:
            if h["text"] not in seen:
                seen.add(h["text"])
                out.append(h)
            if len(out) >= top:
                break
        return out


W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"


def read_doc(path):
    """[(where in the file, its words)] of one document - a PDF by its pages, a deck by its slides, a Word file or a text
    in pieces of about PIECE_CHARS; None when it cannot be read here (a PDF with no PDF reader installed, a damaged file)"""
    ext = os.path.splitext(path)[1].lower()
    try:
        if ext == ".pdf":
            try:
                import pymupdf
                with pymupdf.open(path) as d:
                    return [("p.%d" % (i + 1), pg.get_text()) for i, pg in enumerate(d)]
            except ImportError:
                pass
            try:
                import pypdf
            except ImportError:
                return None
            return [("p.%d" % (i + 1), pg.extract_text() or "") for i, pg in enumerate(pypdf.PdfReader(path).pages)]
        if ext == ".pptx":
            with zipfile.ZipFile(path) as z:
                names = sorted((n for n in z.namelist() if re.match(r"ppt/slides/slide\d+\.xml$", n)),
                               key=lambda n: int(re.findall(r"\d+", n)[-1]))
                return [("slide %s" % re.findall(r"\d+", n)[-1], " ".join((t.text or "") for t in ET.fromstring(z.read(n)).iter(A + "t")))
                        for n in names]
        if ext == ".docx":
            with zipfile.ZipFile(path) as z:
                x = ET.fromstring(z.read("word/document.xml"))
            paras = ["".join((t.text or "") for t in p.iter(W + "t")) for p in x.iter(W + "p")]
        else:
            paras = io.open(path, encoding="utf-8", errors="replace").read().split("\n")
    except Exception:  # noqa: BLE001 - a damaged document is listed as not read, never fatal
        return None
    pieces, cur = [], ""
    for p in (x.strip() for x in paras):
        if not p:
            continue
        if cur and len(cur) + len(p) > PIECE_CHARS:
            pieces.append(cur)
            cur = ""
        cur = cur + "\n" + p if cur else p
    if cur:
        pieces.append(cur)
    return [("part %d" % (i + 1), t) for i, t in enumerate(pieces)]


class Docs:
    """the words of a folder's documents (the source files, the old course), read once and kept in
    working_claude/fact_check/texts_<where>.json, and searched by their words and numbers"""

    def __init__(self, course, where, root, skip=(), extra=()):
        self.where, self.pieces, self.unread = where, [], []
        cache_p = workspace.claude_path(course, "fact_check", "texts_%s.json" % where)
        try:
            cache = json.load(io.open(cache_p, encoding="utf-8"))
        except (OSError, ValueError):
            cache = {}
        kept = {}
        skip = [os.path.normcase(os.path.abspath(x)) for x in skip if x]
        for dirpath, dirs, files in os.walk(root) if root else []:
            dirs[:] = sorted(d for d in dirs if not self.skipped(os.path.join(dirpath, d), skip))
            for f in sorted(files):
                if os.path.splitext(f)[1].lower() not in DOC_TYPES or f.startswith(("~$", ".~lock")):
                    continue
                p = os.path.join(dirpath, f)
                rel = os.path.relpath(p, root).replace("\\", "/")
                key = "%s|%d|%d" % (rel, os.path.getsize(p), int(os.path.getmtime(p)))
                got = cache.get(key) or read_doc(p)
                if got is None:
                    self.unread.append(rel)
                    continue
                kept[key] = got
                self.pieces += [{"src": "%s/%s %s" % (where, rel, label), "text": text} for label, text in got if text.strip()]
        self.pieces += list(extra)
        if kept != cache:
            os.makedirs(os.path.dirname(cache_p), exist_ok=True)
            io.open(cache_p, "w", encoding="utf-8", newline="\n").write(json.dumps(kept, ensure_ascii=False))
        self.post, self.nums = {}, {}
        for i, pc in enumerate(self.pieces):
            for w in set(stems(pc["text"])):
                self.post.setdefault(w, []).append(i)
            for n in numbers(pc["text"]):
                self.nums.setdefault(n, []).append(i)

    @staticmethod
    def skipped(d, skip):
        """a knowledge base kept inside the folder (its pieces are searched as the knowledge base), the course's own folder"""
        name = os.path.basename(d).lower()
        return (os.path.normcase(os.path.abspath(d)) in skip or name.startswith("knowledge_base")
                or os.path.isdir(os.path.join(d, "search_index")))

    def search(self, q, top=3):
        score, n = Counter(), float(len(self.pieces) or 1)
        for w in set(stems(q)):
            ids = self.post.get(w) or []
            for i in ids:
                score[i] += math.log(1 + n / len(ids))
        for x in numbers(q):
            for i in self.nums.get(x) or []:
                score[i] += 1.0
        return [dict(self.pieces[i], score=sc, where=self.where) for i, sc in score.most_common(top)]


def _json(p):
    try:
        return json.load(io.open(p, encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return None


def source_files_dir(course):
    """the course's source_files folder in its master folder (L40) - the documents the knowledge base was made from"""
    master = workspace.master_of(course)
    for name in ("source_files", "source files", "sources"):
        p = os.path.join(master, name)
        if os.path.isdir(p):
            return p
    return None


def old_course_dir(course):
    """the old course the intake recorded (intake.json "old_course", the inventory's folder), or the master folder's"""
    master = workspace.master_of(course)
    said = [(_json(workspace.claude_path(course, "intake.json")) or {}).get("old_course"),
            (_json(workspace.claude_path(course, "old_course_inventory.json")) or {}).get("old_course"),
            os.path.join(master, "old_course"), os.path.join(master, "old course")]
    for p in said:
        if isinstance(p, str) and p.strip().lower() not in ("", "none") and os.path.isdir(p):
            return p
    return None


def inventory_pieces(course):
    """the old course's slides as the intake's inventory read them - used when the old course's folder is not there"""
    out = []
    for sec in (_json(workspace.claude_path(course, "old_course_inventory.json")) or {}).get("sections") or []:
        for f in sec.get("files") or []:
            for x in f.get("slides") or []:
                text = ". ".join(t for t in (x.get("title"), x.get("text")) if t)
                if text:
                    out.append({"src": "old_course/%s slide %s" % (f.get("file", ""), x.get("n")), "text": text})
    return out


class Sources:
    """where a claim is looked for, in order - the knowledge base, the source files, the old course - each opened the first
    time a claim needs it"""

    def __init__(self, course, index=None):
        self.course, self.got = course, {"kb": index} if index else {}

    def get(self, where):
        if where not in self.got:
            c = self.course
            if where == "kb":
                kbs = course_kbs(c)
                self.got[where] = Index(kbs) if kbs else None
            elif where == "source_files":
                root = source_files_dir(c)
                self.got[where] = Docs(c, where, root, skip=course_kbs(c) + [c, old_course_dir(c)]) if root else None
            else:
                root = old_course_dir(c)
                extra = [] if root else inventory_pieces(c)
                self.got[where] = Docs(c, where, root, skip=course_kbs(c) + [c], extra=extra) if root or extra else None
        return self.got[where]

    def why_none(self, where):
        return {"kb": "the course has no knowledge base", "source_files": "the course has no source_files folder",
                "old_course": "the course has no old course"}[where]

    def search(self, where, q, top=3):
        src = self.get(where)
        return src.search(q, top) if src else []

    def everywhere(self, q, top=3):
        return [h for w in WHERE for h in self.search(w, q, top)]


CUT_OFF = re.compile(r"(?<![(\w])(?:the|a|an|of|to|in|within|with|without|for|from|by|at|on|into|onto|upon|between|and|or|"
                     r"but|nor|that|which|whose|than|as|its|their|is|are|was|were|be)\s*[.!?]$")


def cut_off(quote):
    """a source sentence that ends mid-clause ("... should trip the electric motors within.") - the knowledge base may
    have cut it off, and a slide line proved by it can be a broken sentence. A quoted fragment (no full stop) is not one"""
    return bool(CUT_OFF.search((quote or "").strip()))


def sentences(text):
    return [x.strip() for x in re.split(r"(?<=[.;:!?])\s+|\n+", text or "") if len(x.strip()) > 3]


def best_sentence(claim, text):
    """(share of the claim's words the best sentence holds, has all its numbers, the sentence)"""
    want, nums = set(stems(claim)), numbers(claim)
    best = (0.0, False, "")
    for x in sentences(text):
        got = set(stems(x))
        share = len(want & got) / float(len(want)) if want else 0.0
        has = nums <= numbers(x)
        if (share, has) > best[:2]:
            best = (share, has, x)
    return best


def passage(claim, text):
    """the part of a source piece around the sentence that best matches the claim, at most PASSAGE_CHARS"""
    _, _, s = best_sentence(claim, text)
    i = text.find(s) if s else 0
    lo = max(0, i - (PASSAGE_CHARS - len(s)) // 2)
    return re.sub(r"\s+", " ", text[lo:lo + PASSAGE_CHARS]).strip()


def prepare(course, module, index=None, sources=None):
    """every claim searched - the knowledge base, then the source files, then the old course, each searched recorded; the
    ones a source sentence says word for word are proved. -> (store, new, proved here)"""
    script = cs.load(cs.paths(course, module)["script"])
    st = load_store(course, module)
    if not course_kbs(course):
        return st, 0, 0
    sources = sources or Sources(course, index)
    old, st["claims"], new, auto = st.get("claims") or {}, {}, 0, 0
    for cid, sid, field, n, text in claims_of(script):
        if cid in old:
            st["claims"][cid] = dict(old[cid], line=n)
            continue
        new += 1
        row = {"screen": sid, "field": field, "line": n, "text": text, "passages": [], "searched": []}
        for where in WHERE:
            if sources.get(where) is None:
                row["searched"].append({"where": where, "none": sources.why_none(where)})
                continue
            hits = sources.search(where, text, 3)
            got = [{"where": where, "src": h["src"], "text": passage(text, h["text"])} for h in hits]
            row["passages"] += got
            row["searched"].append({"where": where, "closest": got[0] if got else None})
            proved = next(((h, s) for h in hits for share, has, s in [best_sentence(text, h["text"])]
                           if share >= PROVED_SHARE and has), None)
            if proved:
                row.update(verdict="found", quote=proved[1][:300], source=proved[0]["src"], where=where, by="the words match")
                auto += 1
                break
        st["claims"][cid] = row
    save_store(course, module, st)
    return st, new, auto


def quote_in(quote, texts):
    """the quote word for word in one of the texts - spaces, line breaks and case aside ("150m" is "150 m")"""
    q = norm(quote).replace(" ", "")
    return len(q) >= 10 and any(q in norm(t).replace(" ", "") for t in texts)


def judge(course, module, verdicts, index=None):
    """-> (recorded, [problems]) - a verdict whose quote no source passage holds is refused, so nothing is proved from
    memory"""
    st = load_store(course, module)
    probs, done, sources = [], 0, None
    for v in verdicts if isinstance(verdicts, list) else []:
        cid = str((v or {}).get("id") or "")
        row = st["claims"].get(cid)
        if not row:
            probs.append("%s: no such claim (run prepare, then next)" % cid)
            continue
        verdict, quote, fix = v.get("verdict"), (v.get("quote") or "").strip(), (v.get("fix") or "").strip()
        if verdict not in VERDICTS:
            probs.append("%s: verdict is one of %s" % (cid, ", ".join(VERDICTS)))
            continue
        if verdict == "not_a_claim":
            why = (v.get("why") or "").strip()
            if not why:
                probs.append("%s: not_a_claim needs its why - an instruction, a made-up example, a situation, a statement "
                             "meant to be wrong" % cid)
                continue
            row.update(verdict=verdict, why=why, by="fact-checker")
            done += 1
            continue
        web = (v.get("web") if isinstance(v.get("web"), dict) else None) or {}
        web = {k: str(web.get(k) or "").strip() for k in ("query", "url", "quote")}
        if verdict == "partly" and not fix:
            probs.append("%s: partly needs its fix - the corrected words with the quote they come from" % cid)
            continue
        if row["field"] == "points" and fix and fix.lower() != "cut" and cs.wc(fix) > cs.POINT_WORDS:
            probs.append("%s: a point is %d words or fewer - give the corrected words in short; the quote proves them"
                         % (cid, cs.POINT_WORDS))
            continue
        if web["url"] and not re.match(r"https?://\S+$", web["url"]):
            probs.append("%s: a page on the internet is named by its whole address (https://...)" % cid)
            continue
        where = None
        if verdict in ("found", "partly") or (fix and fix.lower() != "cut"):
            where = where_of(quote, row.get("passages") or [])
            if where is None and quote:
                sources = sources or Sources(course, index)
                where = where_of(quote, sources.everywhere(quote, 5))
            if (where is None and web["url"] and len(web["quote"].split()) >= WEB_QUOTE_WORDS
                    and (not quote or norm(quote) == norm(web["quote"]))):
                where, quote = "web", web["quote"]          # proved only on the internet: kept with its address and words
            if where is None:
                probs.append("%s: the quote is not in the sources word for word - copy it from a passage (or search again); "
                             "from a page on the internet: web {url, quote}, its words copied" % cid)
                continue
        said = v.get("contradicts") if isinstance(v.get("contradicts"), dict) else {}
        other = (said.get("quote") or "").strip()
        if other:
            sources = sources or Sources(course, index)
            if where_of(other, (row.get("passages") or []) + sources.everywhere(other, 5)) is None:
                probs.append("%s: what a source says otherwise is quoted from it word for word" % cid)
                continue
        searched = [x for x in row.get("searched") or [] if x.get("where") != "web"]
        if web["url"] or web["query"]:
            searched.append({"where": "web", "query": web["query"],
                             "closest": {"where": "web", "src": web["url"], "text": web["quote"]} if web["url"] else None})
        for k in ("web", "contradicts", "where"):
            row.pop(k, None)
        row.update(verdict=verdict, quote=quote, source=web["url"] if where == "web" else (v.get("source") or "").strip(),
                   fix=fix, searched=searched, by="fact-checker")
        if where:
            row["where"] = where
        if where == "web":
            row["web"] = web
        if other:
            row["contradicts"] = {"quote": other, "source": (said.get("source") or "").strip()}
        done += 1
    save_store(course, module, st)
    save_web(course, module, st)
    return done, probs


def where_of(quote, passages):
    """which source holds the quote word for word - the "where" of the passage that holds it, or None"""
    return next((p.get("where", "kb") for p in passages if quote_in(quote, [p["text"]])), None)


def save_web(course, module, st):
    """the words a claim was proved by on the internet, with their address, in working_claude/retrieval/ - so the course
    holds them (a measured value on a slide is checked against what the course holds) and the operator can read them"""
    rows = [r for r in st["claims"].values() if r.get("where") == "web" and r.get("verdict") in ("found", "partly")]
    p = workspace.claude_path(course, "retrieval", "fact_check_web_%s.md" % cs.mid(module))
    if not rows and not os.path.isfile(p):
        return
    os.makedirs(os.path.dirname(p), exist_ok=True)
    io.open(p, "w", encoding="utf-8", newline="\n").write(
        "# Proved only on the internet - module %s\n\nFound by the fact-checker on these pages, not in the course's own sources: "
        "for the operator to look at.\n\n" % module
        + "".join("- %s %s: \"%s\"\n  \"%s\" - %s\n" % (r["screen"], r["field"], r["text"], r["quote"], r["source"]) for r in rows))


def unproved(row):
    """a claim judged not found, with no words a source gave for it, that the operator has not answered"""
    return row.get("verdict") == "not_found" and (row.get("fix") or "cut").lower() == "cut" and not row.get("answer")


def rewrite_state(st, cid, row):
    """where a claim no source proves stands: "rewrite" - for the writer; "with the writer" - sent, not rewritten yet;
    "operator" - rewritten once (or written in that rewrite) and still not proved. A line added to the field later gets
    its own rewrite"""
    sent = st.get("rewrite") or {}
    if cid in sent:
        return "operator" if sent[cid].get("done") else "with the writer"
    if any(cid in (e.get("after") or []) for e in sent.values() if e.get("done")):
        return "operator"
    if any((e["screen"], e["field"]) == (row["screen"], row["field"]) and not e.get("done") for e in sent.values()):
        return "with the writer"
    return "rewrite"


def closest(row, n=3):
    """the passages that come nearest to the claim, from every source searched - what the sources do say"""
    ranked = sorted(row.get("passages") or [], key=lambda p: -best_sentence(row["text"], p["text"])[0])
    return ranked[:n]


def side_path(course, module, what):
    return os.path.join(os.path.dirname(store_path(course, module)), "%s.%s.json" % (cs.mid(module), what))


def rewrites(course, module):
    """the claims no source proves, sent to the writer once - each with its screen, where it was searched and the passages
    nearest to it -> [entries], also in MNN.rewrite.json"""
    script = cs.load(cs.paths(course, module)["script"])
    st = load_store(course, module)
    sent = st.setdefault("rewrite", {})
    for cid, row in st["claims"].items():
        if unproved(row) and rewrite_state(st, cid, row) == "rewrite":
            sent[cid] = {"screen": row["screen"], "title": (cs.screen_of(script, row["screen"]) or {}).get("title") or "",
                         "field": row["field"], "line": row["line"], "text": row["text"], "searched": row.get("searched") or [],
                         "closest": closest(row), "done": False}
    save_store(course, module, st)
    out = [dict(e, id=cid) for cid, e in sent.items() if not e.get("done")]
    io.open(side_path(course, module, "rewrite"), "w", encoding="utf-8", newline="\n").write(json.dumps(out, ensure_ascii=False, indent=1))
    return out


def apply_rewrite(course, module, changes, by=None):
    """the writer's new words for the lines sent to it - only those lines, only in a draft nobody has approved; every line
    sent is then rewritten once (one left as it was stays as it was). -> (changes applied, [problems])"""
    p = cs.paths(course, module)
    script = cs.load(p["script"])
    st = load_store(course, module)
    open_ = {(e["screen"], e["field"]) for e in (st.get("rewrite") or {}).values() if not e.get("done")}
    if not open_:
        return 0, ["nothing is with the writer - run rewrites first"]
    if script.get("status") == "approved":
        return 0, ["the script is approved: a change to it goes through content_script.py propose"]
    if not isinstance(changes, list) or any(not isinstance(c, dict) or (c.get("screen"), c.get("field")) not in open_ for c in changes):
        return 0, ["only the lines sent for a rewrite change here - a list of {screen, field, new} for: %s"
                   % ", ".join("%s %s" % x for x in sorted(open_))]
    try:
        ch, work = cs.build_changes(script, changes)
    except cs.Stop as e:
        return 0, [str(e)]
    if ch:
        cs.save(p["script"], work)
        cs.append_feedback(course, work, ch, "fact-check rewrite", (by or "").strip() or "the script writer",
                           "the writer's own draft, before review")
    written = {}                                   # the claims each rewritten field holds now: written in the rewrite
    for cid, sid, field, _, _ in claims_of(work):
        written.setdefault((sid, field), []).append(cid)
    for e in st["rewrite"].values():
        if (e["screen"], e["field"]) in open_:
            e.update(done=True, after=written.get((e["screen"], e["field"]), []))
    save_store(course, module, st)
    return len(ch), []


def why_of(row):
    """why a claim not proved is a problem: a source says something different (quoted), or no source says it"""
    said = row.get("contradicts")
    if said:
        return "a source says something different: \"%s\" (%s)" % (said["quote"], said.get("source") or "")
    nums = numbers(row["text"])
    for p in closest(row):
        share, has, s = best_sentence(row["text"], p["text"])
        if nums and share >= 0.5 and not has and numbers(s):
            return "a source says something different: \"%s\" (%s)" % (s[:300], p["src"])
    where = [WHERE_NAMES[x["where"]] for x in row.get("searched") or [] if not x.get("none")]
    named = ", ".join(where[:-1]) + (" and " if len(where) > 1 else "") + where[-1] if where else "nothing"
    return "no source says it: %s %s searched and none of them states it" % (named, "was" if len(where) == 1 else "were")


def question_of(script, st, cid, row):
    """the operator's question on a claim still not proved after its rewrite: the sentence and its screen, where it was
    searched with the closest passage, why it is a problem, and the options"""
    was = next((e["text"] for e in (st.get("rewrite") or {}).values() if cid in (e.get("after") or [])
                and e["text"] != row["text"]), "")
    searched = [{"where": WHERE_NAMES.get(x["where"], x["where"]),
                 "closest": ("%s: \"%s\"" % (x["closest"]["src"], x["closest"]["text"][:300])) if x.get("closest")
                 else x.get("none") or "nothing near it"} for x in row.get("searched") or []]
    if not any(x.get("where") == "web" for x in row.get("searched") or []):
        searched.append({"where": WHERE_NAMES["web"], "closest": "not searched"})
    return {"id": cid, "module": str(script.get("module")), "screen": row["screen"], "place": cs.place(script, row["screen"]),
            "title": (cs.screen_of(script, row["screen"]) or {}).get("title") or "", "field": row["field"],
            "sentence": row["text"], "was": was, "searched": searched, "why": why_of(row), "options": OPTIONS}


def questions(course, module, script=None):
    """the operator's questions of a module: every claim still not proved after its one rewrite"""
    script = script or cs.load(cs.paths(course, module)["script"])
    st = load_store(course, module)
    have = st.get("claims") or {}
    return [question_of(script, st, cid, have[cid]) for cid, _, _, _, _ in claims_of(script)
            if cid in have and unproved(have[cid]) and rewrite_state(st, cid, have[cid]) == "operator"]


def changed_field(s, field, edits):
    """a field's new value after its lines are cut (None) or given new words: edits = [(line number, the line's words, new)];
    None when nothing changes"""
    lines = field_lines(s, field)
    for n, text, new in edits:
        i = n - 1
        if 0 <= i < len(lines) and lines[i] is not None and norm(re.sub(r"^\s*[-*•]\s*", "", lines[i])) == norm(text):
            lines[i] = None if new is None else (("- " if lines[i].lstrip().startswith("-") else "") + new)
    kept = [x for x in lines if x is not None]
    value = kept if isinstance(s.get(field), list) else "\n".join(kept)
    return None if value == s.get(field) or value == cs.as_text(s.get(field)) else value


def fixes(course, module, cut_unproven=False):
    """the change list for content_script.py propose: a line judged partly (or not found with sourced words) gets its
    corrected words. A line no source proves goes to the writer first (rewrites); still not proved after that, it is the
    operator's question - cut only when cut_unproven (an unattended build, nobody to ask). Questions, and the answer a
    slide reveals to the room's question, are listed for the person - an answer is never changed here, so a question
    never loses it. -> (changes, asks, the operator's questions, [(state, row)] still with the writer or not sent yet)"""
    script = cs.load(cs.paths(course, module)["script"])
    st = load_store(course, module)
    edits, asks, held, waiting = {}, [], [], []
    for cid, row in list(st["claims"].items()):
        if row.get("verdict") == "partly" or (row.get("verdict") == "not_found" and (row.get("fix") or "cut").lower() != "cut"):
            if row["field"] in ("answer", "feedback", "reveal"):
                asks.append(row)
            else:
                edits.setdefault((row["screen"], row["field"]), []).append((row["line"], row["text"], row["fix"]))
                # the corrected words come from the source's quote: proved with it
                st["claims"][claim_id(row["screen"], row["field"], row["fix"])] = {
                    "screen": row["screen"], "field": row["field"], "line": row["line"], "text": row["fix"], "verdict": "found",
                    "quote": row.get("quote", ""), "source": row.get("source", ""), "where": row.get("where", "kb"),
                    "by": "corrected from the source"}
        elif unproved(row):
            state = rewrite_state(st, cid, row)
            if state != "operator":
                waiting.append((state, row))
                continue
            held.append(question_of(script, st, cid, row))
            if cut_unproven and row["field"] not in ("answer", "reveal"):
                edits.setdefault((row["screen"], row["field"]), []).append((row["line"], row["text"], None))
    changes = []
    for (sid, field), rows in sorted(edits.items()):
        s = cs.screen_of(script, sid)
        new = changed_field(s, field, rows) if s is not None else None
        if new is not None:
            changes.append({"screen": sid, "field": field, "new": new})
    save_store(course, module, st)
    return changes, asks, held, waiting


def answer(course, module, cid, cut=False, keep=None, replace=None, by=None):
    """the operator's answer to a question on a claim no source proves: cut it, keep it (the source they name), or replace
    it with their own words - their answer is their yes, so it is applied and logged as theirs. -> (exit code, message)"""
    p = cs.paths(course, module)
    script = cs.load(p["script"])
    st = load_store(course, module)
    row = (st.get("claims") or {}).get(cid)
    keep, replace, by = (keep or "").strip(), (replace or "").strip(), (by or "").strip()
    if not row or not unproved(row) or rewrite_state(st, cid, row) != "operator":
        return 2, "no open question %s - fact_check.py questions lists them" % cid
    if [bool(cut), bool(keep), bool(replace)].count(True) != 1 or not by:
        return 2, "one answer - --cut, --keep \"<the source>\" or --replace \"<the operator's words>\" - and --by \"<the operator's name>\""
    if row["field"] == "answer" and not keep:
        return 2, "a question's right answer changes with its question - content_script.py propose"
    if os.path.isfile(p["pending"]):
        return 1, "other changes wait to be applied or discarded first"
    today = cs.date.today().isoformat()
    changes = []
    if not keep:
        s = cs.screen_of(script, row["screen"])
        new = changed_field(s, row["field"], [(row["line"], row["text"], replace or None)]) if s is not None else None
        if new is None:
            return 1, "the line is no longer in the script as it was - run prepare again"
        changes.append({"screen": row["screen"], "field": row["field"], "new": new})
    if keep or replace:
        changes.append({"script_field": "operator_facts", "new": list(script.get("operator_facts") or []) + [
            {"fact": replace or row["text"], "where": row["screen"], "said": today, "source": keep or "the operator's own words"}]})
    f = side_path(course, module, "answer")
    io.open(f, "w", encoding="utf-8", newline="\n").write(json.dumps(changes, ensure_ascii=False, indent=1))
    code = cs.cmd_propose(course, module, f, "the fact-checker (a claim no source proves)")
    code = code or cs.cmd_apply(course, module, True, by)
    if code:
        return code, "not applied"
    row["answer"] = {"cut": True} if cut else {"keep": keep} if keep else {"replace": replace}
    row["answer"].update(by=by, on=today)
    if keep:
        row.update(verdict="found", where="operator", source=keep, by="the operator (%s)" % by)
    if replace:
        st["claims"][claim_id(row["screen"], row["field"], replace)] = {
            "screen": row["screen"], "field": row["field"], "line": row["line"], "text": replace, "verdict": "found",
            "where": "operator", "source": "the operator's own words", "by": "the operator (%s)" % by}
    save_store(course, module, st)
    return 0, "applied: %s" % ("cut" if cut else "kept, its source: %s" % keep if keep else "replaced with the operator's words")


def to_operator(course, module, held, cut):
    """an unattended build's questions nobody could answer, with what it did, in MNN.operator.json - the operator reads
    them later, and the factory trial's scorecard and FAULTS report show them"""
    p = side_path(course, module, "operator")
    have = {q["id"]: q for q in (_json(p) or [])}
    for q in held:
        have[q["id"]] = dict(q, done="cut - an unattended build, nobody to ask" if cut and q["field"] not in ("answer", "reveal")
                             else "left in the script - a question's answer is never cut by the factory: the operator decides")
    io.open(p, "w", encoding="utf-8", newline="\n").write(json.dumps(list(have.values()), ensure_ascii=False, indent=1))
    return p


def status(course, module, script=None):
    """{"claims", "judged", "unchecked": [claim texts], "unproven": [(screen, text, verdict)], "set_aside": [(screen, text,
    why)], "cut_off": [(screen, text, quote)], "web": [(screen, text, address, quote)], "questions": n, "with_writer": n,
    "to_operator": n} for the script as it is now - a line set aside as no claim, one proved by a source sentence that ends
    mid-clause, and one proved only on the internet are listed for the person, never held"""
    script = script or cs.load(cs.paths(course, module)["script"])
    st = load_store(course, module)
    have = st.get("claims") or {}
    out = {"claims": 0, "judged": 0, "unchecked": [], "unproven": [], "set_aside": [], "cut_off": [], "web": [],
           "questions": 0, "with_writer": 0, "to_operator": len(_json(side_path(course, module, "operator")) or [])}
    for cid, sid, field, n, text in claims_of(script):
        out["claims"] += 1
        row = have.get(cid)
        if not row or not row.get("verdict"):
            out["unchecked"].append(text)
            continue
        out["judged"] += 1
        if row["verdict"] == "not_a_claim":
            out["set_aside"].append((sid, text, row.get("why", "")))
        elif row["verdict"] != "found":
            out["unproven"].append((sid, text, row["verdict"]))
            if unproved(row):
                out["questions" if rewrite_state(st, cid, row) == "operator" else "with_writer"] += 1
        elif row.get("where") == "web":
            out["web"].append((sid, text, row.get("source", ""), row.get("quote", "")))
        elif cut_off(row.get("quote")):
            out["cut_off"].append((sid, text, row["quote"]))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("cmd", choices=("prepare", "next", "search", "judge", "rewrites", "rewrite", "questions", "answer", "fixes", "status"))
    ap.add_argument("course")
    ap.add_argument("words", nargs="?")
    ap.add_argument("--module", required=True)
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--top", type=int, default=5)
    ap.add_argument("--file")
    ap.add_argument("--apply", action="store_true", help="fixes: apply the change list - an unattended build only")
    ap.add_argument("--id", help="answer: the claim the operator answered")
    ap.add_argument("--cut", action="store_true", help="answer: the operator cuts the line")
    ap.add_argument("--keep", help="answer: the operator keeps it - the source they name")
    ap.add_argument("--replace", help="answer: the operator's own words for the line")
    ap.add_argument("--by", help="answer: the operator's name; rewrite: the writer")
    a = ap.parse_args(argv)
    course = workspace.work_folder(a.course, create=False)
    if not os.path.isfile(cs.paths(course, a.module)["script"]):
        print("Stopped - module %s has no content script yet" % a.module)
        return 2
    if a.cmd in ("prepare", "next", "search", "judge") and not course_kbs(course):
        print("Nothing to check against - the course has no knowledge base with a search index (kb_tool.py find / sources).")
        return 2
    me = "python %s" % os.path.join(HERE, "fact_check.py")
    if a.cmd == "prepare":
        st, new, auto = prepare(course, a.module)
        left = sum(1 for r in st["claims"].values() if not r.get("verdict"))
        print("Module %s: %d claim(s), %d new - %d proved here (a source says them word for word); %d for the fact-checker "
              "(next).\n    %s" % (a.module, len(st["claims"]), new, auto, left, store_path(course, a.module)))
        return 1 if left else 0
    if a.cmd == "next":
        st, _, _ = prepare(course, a.module)            # a line changed since: judged again
        rows = [dict(id=cid, screen=r["screen"], claim=r["text"], passages=r.get("passages") or [],
                     searched=[x["where"] for x in r.get("searched") or [] if not x.get("none")])
                for cid, r in st["claims"].items() if not r.get("verdict")][:a.n]
        print(json.dumps(rows, ensure_ascii=False, indent=1) if rows else "[] - every claim is judged: run rewrites, then fixes")
        return 0
    if a.cmd == "search":
        if not (a.words or "").strip():
            print("Stopped - search needs the words to look for")
            return 2
        hits = Sources(course).everywhere(a.words, a.top)
        print(json.dumps([{"where": h["where"], "src": h["src"], "text": passage(a.words, h["text"])} for h in hits],
                         ensure_ascii=False, indent=1))
        return 0
    if a.cmd in ("judge", "rewrite"):
        try:
            data = json.load(io.open(a.file, encoding="utf-8"))
        except (OSError, ValueError, TypeError) as err:
            print("Stopped - --file is a JSON list of %s: %s" % (
                "{id, verdict, quote, source, fix, web, contradicts} (not_a_claim: {id, verdict, why})" if a.cmd == "judge"
                else "{screen, field, new}", err))
            return 2
        if a.cmd == "judge":
            done, probs = judge(course, a.module, data)
            print("Recorded %d verdict(s).%s" % (done, "".join("\n  refused: " + p for p in probs)))
            return 1 if probs else 0
        done, probs = apply_rewrite(course, a.module, data, a.by)
        if probs:
            print("Stopped - %s" % probs[0])
            return 2
        print("Rewritten: %d field(s) changed, every line sent is rewritten once. The fact-checker judges them again:\n"
              "    %s next %s --module %s" % (done, me, a.course, a.module))
        return 0
    if a.cmd == "rewrites":
        out = rewrites(course, a.module)
        if not out:
            print("Nothing for the writer - every claim no source proves has had its rewrite (questions), or there is none.")
            return 0
        print("%d claim(s) no source proves - back to the writer, once, for a rewrite from what the sources do say (or the line "
              "left out). Each with where it was searched and the passages nearest to it:\n    %s\n"
              "The writer gives the new words as [{screen, field, new}] and runs:\n    %s rewrite %s --module %s --file <file> "
              "--by \"<writer>\"" % (len(out), side_path(course, a.module, "rewrite"), me, a.course, a.module))
        for e in out:
            print("  %s %s: \"%s\"" % (e["screen"], e["field"], e["text"][:110]))
        return 1
    if a.cmd == "questions":
        qs = questions(course, a.module)
        p = side_path(course, a.module, "questions")
        io.open(p, "w", encoding="utf-8", newline="\n").write(json.dumps(qs, ensure_ascii=False, indent=1))
        if not qs:
            print("No question for the operator - nothing is left unproved after its rewrite.")
            return 0
        print("%d claim(s) still not proved after the rewrite - the operator decides each (%s):" % (len(qs), p))
        for q in qs:
            print("\n  %s (%s, %s): \"%s\"%s\n  searched: %s\n  why: %s\n  options: %s\n  answer: %s answer %s --module %s --id %s "
                  "--cut | --keep \"<source>\" | --replace \"<words>\" --by \"<operator>\""
                  % (q["place"], q["screen"], q["field"], q["sentence"], ("\n  (rewritten from: \"%s\")" % q["was"]) if q["was"] else "",
                     "; ".join("%s - %s" % (x["where"], x["closest"]) for x in q["searched"]), q["why"], " / ".join(q["options"]),
                     me, a.course, a.module, q["id"]))
        return 1
    if a.cmd == "answer":
        code, said = answer(course, a.module, a.id or "", a.cut, a.keep, a.replace, a.by)
        print(("Stopped - " if code else "") + said)
        return code
    if a.cmd == "fixes":
        auto = a.apply and os.environ.get("NOVIKONTAS_AUTO_BUILD") == "1"
        if a.apply and not auto:
            print("Stopped - --apply is for an unattended build (NOVIKONTAS_AUTO_BUILD=1); attended, the operator sees the "
                  "changes first: content_script.py propose")
            return 2
        changes, asks, held, waiting = fixes(course, a.module, cut_unproven=auto)
        p = side_path(course, a.module, "changes")
        io.open(p, "w", encoding="utf-8", newline="\n").write(json.dumps(changes, ensure_ascii=False, indent=1))
        if auto and changes:
            # an unattended build has nobody to say yes: the source's own words go in, and a claim still not proved after
            # its rewrite is cut and written to the operator's list - each logged in FEEDBACK_LOG.md for the expert
            if os.path.isfile(cs.paths(course, a.module)["pending"]):
                print("Stopped - other changes wait to be applied or discarded first")
                return 1
            import task_cover
            before = task_cover.status(course, a.module)
            code = cs.cmd_propose(course, a.module, p, "fact-checker")
            code = code or cs.cmd_apply(course, a.module, True, "fact-checker, unattended - from the course's sources")
            after = task_cover.status(course, a.module) if not code else None
            again = [q for q in (after or {}).get("unjudged", []) if q in before["rows"]]
            if again:
                # a cut or a corrected line on a slide a covered verdict cites (or before a task judged partly or not
                # covered) voids that verdict: the task-coverage-checker judges it again before approval, and a line it relied
                # on that is gone is said here. The apply itself succeeded - exit 0; the approval holds the rest
                print("\nThe task cover of module %s must be judged again - a slide %d question(s) rely on changed: %s\n"
                      "    python %s next %s --module %s"
                      % (a.module, len(again), ", ".join(again), os.path.join(HERE, "task_cover.py"), a.course, a.module))
                for q in again:
                    if q in after["lost"]:
                        print("  %s relied on \"%s\" - no slide before it shows that now: teach it again, or the question "
                              "changes" % (q, after["lost"][q][0][:100]))
        else:
            code = 0
            print("%d slide field(s) to correct - shown to the operator first:\n    python %s propose %s --module %s --changes \"%s\" "
                  "--proposed-by \"fact-checker\"" % (len(changes), os.path.join(HERE, "content_script.py"), a.course, a.module, p))
        for r in asks:
            print("  %s %s - for the person, never changed here: \"%s\" -> %s"
                  % ("the room's answer on" if r["field"] == "reveal" else "question", r["screen"], r["text"], r["fix"]))
        if waiting:
            print("%d claim(s) no source proves are not cut: they go to the writer first, once (%s) - %s rewrites %s --module %s"
                  % (len(waiting), ", ".join(sorted({s for s, _ in waiting})), me, a.course, a.module))
        if held and auto and not code:
            print("%d claim(s) still not proved after the rewrite - nobody to ask: cut, and each written to the operator's list "
                  "with where it was searched and why:\n    %s" % (len(held), to_operator(course, a.module, held, True)))
        elif held:
            print("%d claim(s) still not proved after the rewrite - the operator decides each: %s questions %s --module %s"
                  % (len(held), me, a.course, a.module))
        return code
    s = status(course, a.module)
    print("Module %s: %d claim(s), %d judged, %d not judged yet, %d not proved (found in no source, or only partly) - %d with "
          "the writer or not sent to it yet, %d for the operator; %d on the operator's list."
          % (a.module, s["claims"], s["judged"], len(s["unchecked"]), len(s["unproven"]), s["with_writer"], s["questions"],
             s["to_operator"]))
    for sid, text, v in s["unproven"][:20]:
        print("  %s  %-9s %s" % (sid, v, text[:110]))
    if s["web"]:
        print("Proved only on the internet (%d) - for the operator to look at:" % len(s["web"]))
        for sid, text, url, quote in s["web"][:20]:
            print("  %s  %s  (%s: \"%s\")" % (sid, text[:80], url, quote[:80]))
    if s["set_aside"]:
        print("Set aside as no claim (%d) - for the person to glance at:" % len(s["set_aside"]))
        for sid, text, why in s["set_aside"][:20]:
            print("  %s  %s  (%s)" % (sid, text[:90], why[:60]))
    return 0 if not s["unchecked"] and not s["unproven"] else 1


if __name__ == "__main__":
    sys.exit(main())
