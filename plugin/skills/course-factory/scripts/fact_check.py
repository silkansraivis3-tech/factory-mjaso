#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Every claim of a module's content script proved in the course's own sources - the fact-checker agent's tool (L4).

    fact_check.py prepare <course> --module 1         every claim, searched; what a source says word for word is proved here
    fact_check.py next    <course> --module 1 [--n 20] the next claims to judge, each with its source passages (JSON)
    fact_check.py search  <course> --module 1 "<words>" [--top 5]   one more search of the knowledge base
    fact_check.py judge   <course> --module 1 --file <verdicts.json>  the agent's verdicts, each quote checked
    fact_check.py fixes   <course> --module 1 [--apply]  the cuts and corrections as a change list for content_script propose
                                                      (--apply: an unattended build applies them itself, each logged)
    fact_check.py status  <course> --module 1

WHY THIS EXISTS
A script is written by a model, and a model writes from memory: a slide can state a pressure, a rule or a reason that no
source of the course holds, and a ship's officer learns it as a fact. So once a module's script is written, every claim
is looked up in the course's own knowledge base (built from source_files). The mechanical part is here - finding the
claims, searching, proving what a passage says word for word, refusing a quote no source holds - so the agent's own
rules stay short: it reads a claim and its passages and says found, partly or not found.

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
from collections import Counter

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
            for t in dict.fromkeys(self.kb_tool.toks(q)):
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
                                                                 else "%s-%s" % pages), "text": rec.get("text") or ""})
        hits.sort(key=lambda h: -h["score"])
        out, seen = [], set()
        for h in hits:
            if h["text"] not in seen:
                seen.add(h["text"])
                out.append(h)
            if len(out) >= top:
                break
        return out


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


def prepare(course, module, index=None):
    """every claim searched; the ones a source sentence says word for word are proved. -> (store, new, proved here)"""
    script = cs.load(cs.paths(course, module)["script"])
    st = load_store(course, module)
    kbs = course_kbs(course)
    if not kbs:
        return st, 0, 0
    index = index or Index(kbs)
    old, st["claims"], new, auto = st.get("claims") or {}, {}, 0, 0
    for cid, sid, field, n, text in claims_of(script):
        if cid in old:
            st["claims"][cid] = dict(old[cid], line=n)
            continue
        new += 1
        hits = index.search(text, 3)
        row = {"screen": sid, "field": field, "line": n, "text": text,
               "passages": [{"src": h["src"], "text": passage(text, h["text"])} for h in hits]}
        for h in hits:
            share, has, s = best_sentence(text, h["text"])
            if share >= PROVED_SHARE and has:
                row.update(verdict="found", quote=s[:300], source=h["src"], by="the words match")
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
    probs, done = [], 0
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
        if verdict != "found" and not fix:
            probs.append("%s: %s needs its fix - \"cut\", or the corrected words with the quote they come from" % (cid, verdict))
            continue
        needs_quote = verdict in ("found", "partly") or (fix and fix.lower() != "cut")
        if needs_quote:
            texts = [p["text"] for p in row.get("passages") or []]
            if not quote_in(quote, texts):
                index = index or Index(course_kbs(course))
                texts = [h["text"] for h in index.search(quote, 5)] if quote else []
                if not quote_in(quote, texts):
                    probs.append("%s: the quote is not in the sources word for word - copy it from a passage (or search again)" % cid)
                    continue
        row.update(verdict=verdict, quote=quote, source=(v.get("source") or "").strip(), fix=fix, by="fact-checker")
        done += 1
    save_store(course, module, st)
    return done, probs


def fixes(course, module):
    """the change list for content_script.py propose: a line judged not found is cut, one judged partly (or not found
    with sourced words) gets its corrected words. Questions are listed for the person - an answer is never changed here"""
    script = cs.load(cs.paths(course, module)["script"])
    st = load_store(course, module)
    by_field, asks = {}, []
    for row in st["claims"].values():
        if row.get("verdict") in ("partly", "not_found") and row.get("fix"):
            if row["field"] in ("answer", "feedback"):
                asks.append(row)
            else:
                by_field.setdefault((row["screen"], row["field"]), []).append(row)
    changes = []
    for (sid, field), rows in sorted(by_field.items()):
        s = cs.screen_of(script, sid)
        if s is None:
            continue
        lines = field_lines(s, field)
        for r in rows:
            i = r["line"] - 1
            if 0 <= i < len(lines) and norm(re.sub(r"^\s*[-*•]\s*", "", lines[i])) == norm(r["text"]):
                lines[i] = None if r["fix"].lower() == "cut" else (("- " if lines[i].lstrip().startswith("-") else "") + r["fix"])
                if lines[i] is not None:          # the corrected words come from the source's quote: proved with it
                    st["claims"][claim_id(sid, field, r["fix"])] = {"screen": sid, "field": field, "line": r["line"], "text": r["fix"],
                                                                   "verdict": "found", "quote": r.get("quote", ""),
                                                                   "source": r.get("source", ""), "by": "corrected from the source"}
        kept = [x for x in lines if x is not None]
        new = kept if isinstance(s.get(field), list) else "\n".join(kept)
        if new != s.get(field) and new != cs.as_text(s.get(field)):
            changes.append({"screen": sid, "field": field, "new": new})
    save_store(course, module, st)
    return changes, asks


def status(course, module, script=None):
    """{"claims", "judged", "unchecked": [claim texts], "unproven": [(screen, text, verdict)], "set_aside": [(screen, text,
    why)]} for the script as it is now - a line set aside as no claim is listed for the person, never held"""
    script = script or cs.load(cs.paths(course, module)["script"])
    st = load_store(course, module)
    have = st.get("claims") or {}
    out = {"claims": 0, "judged": 0, "unchecked": [], "unproven": [], "set_aside": []}
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
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("cmd", choices=("prepare", "next", "search", "judge", "fixes", "status"))
    ap.add_argument("course")
    ap.add_argument("words", nargs="?")
    ap.add_argument("--module", required=True)
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--top", type=int, default=5)
    ap.add_argument("--file")
    ap.add_argument("--apply", action="store_true", help="fixes: apply the change list - an unattended build only")
    a = ap.parse_args(argv)
    course = workspace.work_folder(a.course, create=False)
    if not os.path.isfile(cs.paths(course, a.module)["script"]):
        print("Stopped - module %s has no content script yet" % a.module)
        return 2
    if a.cmd in ("prepare", "next", "search", "judge") and not course_kbs(course):
        print("Nothing to check against - the course has no knowledge base with a search index (kb_tool.py find / sources).")
        return 2
    if a.cmd == "prepare":
        st, new, auto = prepare(course, a.module)
        left = sum(1 for r in st["claims"].values() if not r.get("verdict"))
        print("Module %s: %d claim(s), %d new - %d proved here (a source says them word for word); %d for the fact-checker "
              "(next).\n    %s" % (a.module, len(st["claims"]), new, auto, left, store_path(course, a.module)))
        return 1 if left else 0
    if a.cmd == "next":
        st, _, _ = prepare(course, a.module)            # a line changed since: judged again
        rows = [dict(id=cid, screen=r["screen"], claim=r["text"], passages=r.get("passages") or [])
                for cid, r in st["claims"].items() if not r.get("verdict")][:a.n]
        print(json.dumps(rows, ensure_ascii=False, indent=1) if rows else "[] - every claim is judged: run fixes")
        return 0
    if a.cmd == "search":
        if not (a.words or "").strip():
            print("Stopped - search needs the words to look for")
            return 2
        hits = Index(course_kbs(course)).search(a.words, a.top)
        print(json.dumps([{"src": h["src"], "text": passage(a.words, h["text"])} for h in hits], ensure_ascii=False, indent=1))
        return 0
    if a.cmd == "judge":
        try:
            verdicts = json.load(io.open(a.file, encoding="utf-8"))
        except (OSError, ValueError, TypeError) as err:
            print("Stopped - --file is a JSON list of {id, verdict, quote, source, fix} (not_a_claim: {id, verdict, why}): %s" % err)
            return 2
        done, probs = judge(course, a.module, verdicts)
        print("Recorded %d verdict(s).%s" % (done, "".join("\n  refused: " + p for p in probs)))
        return 1 if probs else 0
    if a.cmd == "fixes":
        changes, asks = fixes(course, a.module)
        p = os.path.join(os.path.dirname(store_path(course, a.module)), "%s.changes.json" % cs.mid(a.module))
        io.open(p, "w", encoding="utf-8", newline="\n").write(json.dumps(changes, ensure_ascii=False, indent=1))
        if a.apply and changes:
            # an unattended build has nobody to say yes: the cuts and the source's own words go in, each logged in
            # FEEDBACK_LOG.md for the expert to see in the editor
            if os.environ.get("NOVIKONTAS_AUTO_BUILD") != "1":
                print("Stopped - --apply is for an unattended build (NOVIKONTAS_AUTO_BUILD=1); attended, the operator sees the "
                      "changes first: content_script.py propose")
                return 2
            if os.path.isfile(cs.paths(course, a.module)["pending"]):
                print("Stopped - other changes wait to be applied or discarded first")
                return 1
            code = cs.cmd_propose(course, a.module, p, "fact-checker")
            code = code or cs.cmd_apply(course, a.module, True, "fact-checker, unattended - from the course's sources")
            return code
        print("%d slide field(s) to correct - shown to the operator first:\n    python %s propose %s --module %s --changes \"%s\" "
              "--proposed-by \"fact-checker\"" % (len(changes), os.path.join(HERE, "content_script.py"), a.course, a.module, p))
        for r in asks:
            print("  question %s - for the person, never changed here: \"%s\" -> %s" % (r["screen"], r["text"], r["fix"]))
        return 0
    s = status(course, a.module)
    print("Module %s: %d claim(s), %d judged, %d not judged yet, %d not proved (found in no source, or only partly)."
          % (a.module, s["claims"], s["judged"], len(s["unchecked"]), len(s["unproven"])))
    for sid, text, v in s["unproven"][:20]:
        print("  %s  %-9s %s" % (sid, v, text[:110]))
    if s["set_aside"]:
        print("Set aside as no claim (%d) - for the person to glance at:" % len(s["set_aside"]))
        for sid, text, why in s["set_aside"][:20]:
            print("  %s  %s  (%s)" % (sid, text[:90], why[:60]))
    return 0 if not s["unchecked"] and not s["unproven"] else 1


if __name__ == "__main__":
    sys.exit(main())
