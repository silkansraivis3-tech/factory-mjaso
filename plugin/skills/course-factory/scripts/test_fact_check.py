# -*- coding: utf-8 -*-
"""test_fact_check - every claim of a content script proved in the course's own knowledge base (fact_check.py).

    python test_fact_check.py

Pinned:
  * the claims: a slide's lines (or its points) and its revealed answer, a note's line with a number, a question's
    right answer and feedback - not a short line, not a question, not a note without a number;
  * prepare proves a claim a source sentence says word for word, with every number; a reworded one goes to the agent;
  * judge refuses a quote no source holds (nothing proved from memory), a not found or partly without its fix, and new
    words without the quote they come from; a quote a fresh search finds is accepted;
  * fixes rewrites a line found partly as the source says it - a change list content_script propose accepts; a
    question's answer is never changed, only listed;
  * the sources, in order: the knowledge base, the source files (the documents themselves), the old course the intake
    recorded - each search recorded with the closest passage; a claim proved only on the internet keeps its address and
    the words quoted, is marked a web source and listed for the operator;
  * a claim found nowhere is never cut first: it goes to the writer once (rewrites / rewrite, only those lines); still not
    proved after that, it is the operator's question - the sentence, its screen, where it was searched with the closest
    passage, and why (no source says it, or a source says otherwise, quoted) - answered cut, keep (the source named) or
    replace; an unattended build cuts it and writes the question to the operator's list;
  * the approval: a course with a knowledge base is refused while a claim is not judged or one not proved is still in
    the script; a changed line is judged again; a course without a knowledge base is not checked.
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import re
import shutil
import sys
import tempfile
import zipfile
from collections import Counter

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "kb", "scripts"))
import content_script as cs  # noqa: E402
import fact_check as fc  # noqa: E402
import kb_tool  # noqa: E402

PASS, FAIL = [], []
PIECES = [("Handout.pdf", 5, "Type C tanks are pressure vessels designed for about 18 bar gauge. They need no secondary barrier."),
          ("Handout.pdf", 6, "A semi-refrigerated ship cools the cargo, so its tanks can be lighter, and it needs a reliquefaction plant."),
          ("Guide.pdf", 40, "Ammonia attacks copper and zinc, so brass fittings are never used in ammonia service.")]


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print(("  ok    " if ok else "  FAIL  ") + name + (("  -> " + str(detail)[:700]) if detail and not ok else ""))


def make_kb(kb):
    """a Course Source Processor knowledge base with its BM25 index - the format kb_tool.py reads"""
    os.makedirs(os.path.join(kb, "search_index"))
    chunks, df, post, off = [], Counter(), {}, 0
    with open(os.path.join(kb, "search_index", "chunks.jsonl"), "wb") as f:
        for i, (name, page, text) in enumerate(PIECES):
            b = (json.dumps({"source_filename": name, "source_path": name, "page_start": page, "page_end": page, "text": text}) + "\n").encode("utf-8")
            f.write(b)
            toks = kb_tool.toks(text)
            chunks.append({"n": len(toks), "off": off, "bytes": len(b), "nav": 0})
            for t, tf in Counter(toks).items():
                df[t] += 1
                post.setdefault(t, []).append([i, tf])
            off += len(b)
    io.open(os.path.join(kb, "search_index", "index.json"), "w", encoding="utf-8").write(json.dumps({
        "bm25": {"k1": 1.5, "b": 0.75}, "chunk_count": len(chunks), "avg_tokens_per_chunk": sum(c["n"] for c in chunks) / float(len(chunks)),
        "chunks": chunks, "df": dict(df), "postings": post}))


SCRIPT = {"module": 1, "title": "Gas tankers", "operator_language": "en", "status": "draft", "screens": [
    {"id": "s01", "kind": "slide", "title": "Type C tanks",
     "text": "Type C tanks are pressure vessels designed for about 18 bar gauge.\nType C tanks are painted green on every ship.\nShort line",
     "notes": "- Ask the room first.\n- The gauge on deck reads 18 bar.", "minutes": 3},
    {"id": "s03", "kind": "slide", "title": "Alarm", "text": "Loading of propane is in progress alongside the terminal.",
     "choices": "Stop the loading\nCarry on", "right": "A",
     "why": "Right: the emergency shutdown stops the loading at once.\nWrong: the gas-safe space is no longer safe.",
     "notes": "- Vote first.", "minutes": 3},
    {"id": "s04", "kind": "slide", "title": "Your turn", "text": "Write your six answers on your card.\nTap every part that holds cargo.",
     "notes": "- Pairs.", "minutes": 2},
    {"id": "s02", "kind": "slide", "title": "Cold", "text": "A semi-refrigerated ship cools its cargo to make the tanks lighter.\nWhy does it cool?",
     "ask": "What does cooling cost?", "reveal": "It needs a reliquefaction plant.", "notes": "- Pairs.", "minutes": 3},
    {"id": "q01", "kind": "self-check", "set": "SC1", "mechanic": "single_choice", "question": "Which metal does ammonia attack?",
     "options": ["Copper and zinc", "Stainless steel"], "correct": "A", "feedback": "Ammonia attacks copper and zinc - no brass fittings."}]}


def make_sources(master, c):
    """the master folder's source_files (a document the knowledge base left out) and the old course the intake recorded,
    in a folder of its own name"""
    os.makedirs(os.path.join(master, "source_files", "KNOWLEDGE_BASE", "search_index"))
    io.open(os.path.join(master, "source_files", "Manual.txt"), "w", encoding="utf-8").write(
        "Section 4. Relief valves of a Type C tank lift at 18 bar gauge, as set at the yard.\n"
        "Ammonia has an exposure limit of 25 ppm over eight hours.\n")
    io.open(os.path.join(master, "source_files", "KNOWLEDGE_BASE", "chunk.txt"), "w", encoding="utf-8").write(
        "The ESD push buttons are tested before every cargo operation.")
    old = os.path.join(master, "Previous course")
    os.makedirs(old)
    slide = ('<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
             'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><a:t>Emergency shutdown</a:t>'
             '<a:t>The ESD push buttons are tested before every cargo operation.</a:t></p:sld>')
    with zipfile.ZipFile(os.path.join(old, "1. Gas tankers.pptx"), "w") as z:
        z.writestr("ppt/slides/slide1.xml", slide)
    io.open(os.path.join(c, "working_claude", "intake.json"), "w", encoding="utf-8").write(json.dumps({"old_course": old}))


SCRIPT2 = {"module": 2, "title": "Gas safety", "operator_language": "en", "status": "draft", "screens": [
    {"id": "s01", "kind": "slide", "title": "Relief valves", "text": "Relief valves of a Type C tank lift at 18 bar gauge.", "minutes": 3},
    {"id": "s02", "kind": "slide", "title": "ESD", "text": "The ESD push buttons are tested before every cargo operation.", "minutes": 3},
    {"id": "s03", "kind": "slide", "title": "Methane", "text": "Methane is lighter than air at ambient temperature.", "minutes": 3},
    {"id": "s04", "kind": "slide", "title": "Loading", "text": "Discuss in pairs what slows loading.\nShips painted blue load faster in the winter months.", "minutes": 3},
    {"id": "s05", "kind": "slide", "title": "Ammonia", "text": "Ammonia has an exposure limit of 50 ppm over eight hours.", "minutes": 3}]}


def flow(c):
    """module 2: where each claim was found, the internet, the rewrite, the operator's question and answer"""
    cs.save(cs.paths(c, 2)["script"], json.loads(json.dumps(SCRIPT2)))
    st, _, _ = fc.prepare(c, 2)
    by = {r["screen"]: r for r in st["claims"].values()}
    check("a claim the knowledge base does not hold is proved in the source files themselves - the documents, not only "
          "the knowledge base's pieces - and where it was searched is recorded, in order",
          by["s01"].get("verdict") == "found" and by["s01"].get("where") == "source_files"
          and by["s01"]["source"] == "source_files/Manual.txt part 1"
          and [x["where"] for x in by["s01"]["searched"]] == ["kb", "source_files"], by["s01"])
    check("... then in the old course the intake recorded (its own folder name) - a knowledge base kept inside source_files "
          "is not read as a source file", by["s02"].get("where") == "old_course"
          and by["s02"]["source"] == "old_course/1. Gas tankers.pptx slide 1"
          and [x["where"] for x in by["s02"]["searched"]] == ["kb", "source_files", "old_course"], by["s02"])
    blue, ammonia, methane = by["s04"], by["s05"], by["s03"]
    check("... a claim found in none of them goes to the fact-checker with the nearest passage of each",
          not blue.get("verdict") and [x["where"] for x in blue["searched"]] == ["kb", "source_files", "old_course"]
          and {p["where"] for p in ammonia["passages"]} >= {"kb", "source_files"}, (blue, ammonia))
    ids = {r["screen"]: cid for cid, r in st["claims"].items()}
    done, probs = fc.judge(c, 2, [{"id": ids["s03"], "verdict": "found", "web": {"query": "methane lighter than air",
                                   "url": "www.example.org/methane", "quote": "Methane is lighter than air at ambient temperature"}}])
    check("a web source is named by its whole address", done == 0 and "whole address" in probs[0], probs)
    done, probs = fc.judge(c, 2, [{"id": ids["s03"], "verdict": "found", "web": {"url": "https://example.org/methane", "quote": "lighter"}}])
    check("... and its words are quoted, not one word", done == 0 and "not in the sources" in probs[0], probs)
    done, probs = fc.judge(c, 2, [
        {"id": ids["s03"], "verdict": "found", "web": {"query": "methane lighter than air", "url": "https://example.org/methane",
                                                       "quote": "Methane is lighter than air at ambient temperature"}},
        {"id": ids["s04"], "verdict": "not_found", "web": {"query": "ship hull colour loading rate"}},
        {"id": ids["s05"], "verdict": "not_found", "contradicts": {"quote": "Ammonia is very toxic and corrosive", "source": "x"}}])
    check("what a source says otherwise is quoted from it word for word", done == 2 and "word for word" in probs[0], probs)
    done, probs = fc.judge(c, 2, [{"id": ids["s05"], "verdict": "not_found", "web": {"query": "ammonia exposure limit"}}])
    st = fc.load_store(c, 2)
    m = st["claims"][ids["s03"]]
    web_file = os.path.join(c, "working_claude", "retrieval", "fact_check_web_M02.md")
    check("a claim proved only on the internet is kept with its address and the words quoted, marked a web source",
          m["verdict"] == "found" and m["where"] == "web" and m["source"] == "https://example.org/methane"
          and m["quote"] == "Methane is lighter than air at ambient temperature" and m["searched"][-1]["where"] == "web", m)
    check("... written where the course holds it, with its address, so a value on the slide is in a source the course holds",
          os.path.isfile(web_file) and "https://example.org/methane" in io.open(web_file, encoding="utf-8").read())
    s = fc.status(c, 2)
    f = [x for x in cs.proof_findings(c, cs.load(cs.paths(c, 2)["script"])) if x["rule"] == "c_web"]
    check("... and listed for the operator to look at - a note on the review page, never a stop",
          [x[0] for x in s["web"]] == ["s03"] and [(x["screen"], x["level"]) for x in f] == [("s03", cs.NOTE)]
          and "https://example.org/methane" in f[0]["detail"], (s["web"], f))

    print("\n-- not proved: the writer once, then the operator")
    changes, asks, held, waiting = fc.fixes(c, 2, cut_unproven=True)
    check("a claim found nowhere is not cut - not even unattended - before the writer has rewritten it",
          changes == [] and not held and sorted((w, r["screen"]) for w, r in waiting) == [("rewrite", "s04"), ("rewrite", "s05")],
          (changes, waiting))
    sent = fc.rewrites(c, 2)
    e = {x["screen"]: x for x in sent}
    check("rewrites sends those claims to the writer with their screen, where each was searched and the passages nearest "
          "to it (what the sources do say)", sorted(e) == ["s04", "s05"] and e["s05"]["title"] == "Ammonia"
          and any("25 ppm" in p["text"] for p in e["s05"]["closest"]) and [x["where"] for x in e["s04"]["searched"]][-1] == "web"
          and json.load(io.open(fc.side_path(c, 2, "rewrite"), encoding="utf-8")) == sent, sent)
    check("... and once: asked again, nothing new is sent, and nothing is cut while it is with the writer",
          fc.rewrites(c, 2) == sent and [w for w, _ in fc.fixes(c, 2, cut_unproven=True)[3]] == ["with the writer"] * 2)
    n, probs = fc.apply_rewrite(c, 2, [{"screen": "s01", "field": "text", "new": "Relief valves lift at 20 bar."}])
    check("the writer changes only the lines sent to it", n == 0 and "only the lines sent" in probs[0], probs)
    n, probs = fc.apply_rewrite(c, 2, [{"screen": "s04", "field": "text", "new": "Ships painted blue load faster in the winter season."}],
                                "script:2 (writer)")
    check("... its new words go into the draft; a line it could not rewrite from a source stays as it was",
          n == 1 and not probs and cs.load(cs.paths(c, 2)["script"])["screens"][3]["text"].endswith("winter season."), probs)
    check("... in place of the line sent: the writer gives the new line, and the field's other lines stay",
          cs.load(cs.paths(c, 2)["script"])["screens"][3]["text"]
          == "Discuss in pairs what slows loading.\nShips painted blue load faster in the winter season.")
    st, new, _ = fc.prepare(c, 2)
    blue2 = next(cid for cid, r in st["claims"].items() if r["screen"] == "s04")
    check("... and the rewritten line is checked again", new == 1 and not st["claims"][blue2].get("verdict"), st["claims"][blue2])
    fc.judge(c, 2, [{"id": blue2, "verdict": "not_found", "web": {"query": "blue hull loading winter"}}])
    qs = {q["screen"]: q for q in fc.questions(c, 2)}
    q4, q5 = qs.get("s04", {}), qs.get("s05", {})
    check("still not proved after the one rewrite: an operator question with the exact sentence and its screen, what it was "
          "rewritten from, where it was searched with the closest passage, why, and the three options",
          q4.get("sentence") == "Ships painted blue load faster in the winter season." and q4.get("title") == "Loading"
          and q4.get("place") and q4.get("was") == "Ships painted blue load faster in the winter months."
          and [x["where"] for x in q4["searched"]] == ["the knowledge base", "the source files", "the old course", "the internet"]
          and all(x["closest"] for x in q4["searched"]) and q4["why"].startswith("no source says it")
          and q4["options"] == fc.OPTIONS, q4)
    check("... a source that says something different is quoted as the why",
          q5.get("why", "").startswith("a source says something different") and "25 ppm" in q5["why"] and "Manual.txt" in q5["why"], q5)
    f = cs.proof_findings(c, cs.load(cs.paths(c, 2)["script"]))
    check("... and the approval waits for the operator's answer",
          sorted(x["screen"] for x in f if x["rule"] == "c_unproven") == ["s04", "s05"], f)
    code = fc.main(["questions", c, "--module", "2"])
    check("questions writes them for the chat's question (exit 1 while one is open)",
          code == 1 and len(json.load(io.open(fc.side_path(c, 2, "questions"), encoding="utf-8"))) == 2)
    code, said = fc.answer(c, 2, q5["id"], keep="Company SMS 4.2")
    check("an answer names the operator", code == 2 and "--by" in said, said)
    code, said = fc.answer(c, 2, q5["id"], keep="Company SMS 4.2", by="Test Operator")
    sc = cs.load(cs.paths(c, 2)["script"])
    check("keep: the line stays, proved by the source the operator named, an operator-stated fact",
          code == 0 and "50 ppm" in sc["screens"][4]["text"] and fc.load_store(c, 2)["claims"][q5["id"]]["where"] == "operator"
          and any(x.get("source") == "Company SMS 4.2" for x in sc.get("operator_facts") or []), (said, sc.get("operator_facts")))
    code, said = fc.answer(c, 2, q4["id"], replace="Loading rates depend on the terminal and the cargo plant.", by="Test Operator")
    sc = cs.load(cs.paths(c, 2)["script"])
    check("replace: the operator's own words take the line's place, proved as theirs; nothing is left to ask",
          code == 0 and sc["screens"][3]["text"].split(chr(10)) == ["Discuss in pairs what slows loading.", "Loading rates depend on the terminal and the cargo plant."]
          and not fc.questions(c, 2) and not [x for x in cs.proof_findings(c, sc) if x["rule"] in ("c_unproven", "c_unchecked")],
          (said, sc["screens"][3], cs.proof_findings(c, sc)))


def main():
    tmp = tempfile.mkdtemp(prefix="factcheck_")
    try:
        c = os.path.join(tmp, "course")
        os.makedirs(os.path.join(c, "working_claude", "script"))
        cs.save(cs.paths(c, 1)["script"], json.loads(json.dumps(SCRIPT)))
        kb = os.path.join(tmp, "KB")
        make_kb(kb)
        make_sources(tmp, c)

        print("-- the search tokenizes a query the way the index was built (digits kept)")
        kd = os.path.join(tmp, "KBD")
        os.makedirs(os.path.join(kd, "search_index"))
        digit_texts = [("Gas.pdf", 3, "Hydrogen sulphide H2S exposure limit is 10 ppm for a working shift."),
                       ("Lng.pdf", 9, "Methane boils at -162 degrees C at atmospheric pressure in an LNG tank."),
                       ("Fire.pdf", 2, "Fire extinguishing with CO2 in the engine room needs a release alarm.")]
        dchunks, ddf, dpost, doff = [], Counter(), {}, 0
        with open(os.path.join(kd, "search_index", "chunks.jsonl"), "wb") as f:
            for i, (name, page, text) in enumerate(digit_texts):
                b = (json.dumps({"source_filename": name, "source_path": name, "page_start": page, "page_end": page, "text": text}) + "\n").encode("utf-8")
                f.write(b)
                dt = [t for t in re.findall(r"[^\W_]+", text.lower()) if len(t) >= 2 and t not in kb_tool.CSP_STOP]
                dchunks.append({"n": len(dt), "off": doff, "bytes": len(b), "nav": 0})
                for t, tf in Counter(dt).items():
                    ddf[t] += 1
                    dpost.setdefault(t, []).append([i, tf])
                doff += len(b)
        io.open(os.path.join(kd, "search_index", "index.json"), "w", encoding="utf-8").write(json.dumps({
            "index_version": 5, "bm25": {"k1": 1.2, "b": 0.75}, "chunk_count": len(dchunks),
            "avg_tokens_per_chunk": sum(c["n"] for c in dchunks) / float(len(dchunks)), "chunks": dchunks, "df": dict(ddf), "postings": dpost}))
        di = fc.Index([kd])
        check("'H2S exposure limit' finds the H2S passage", (di.search("H2S exposure limit", 1) or [{}])[0].get("src") == "Gas.pdf p.3",
              di.search("H2S exposure limit", 1))
        check("'boiling point -162' finds the passage with 162", (di.search("boiling point -162", 1) or [{}])[0].get("src") == "Lng.pdf p.9",
              di.search("boiling point -162", 1))

        print("\n-- the claims")
        got = [(sid, field, text) for _, sid, field, _, text in fc.claims_of(SCRIPT)]
        texts = [x[2] for x in got]
        check("a slide's lines are claims; a short line and a question are not",
              "Type C tanks are painted green on every ship." in texts and "Short line" not in texts and "Why does it cool?" not in texts, got)
        check("... the revealed answer is one; a note with a number is one, a note without one is not",
              ("s02", "reveal", "It needs a reliquefaction plant.") in got and ("s01", "notes", "The gauge on deck reads 18 bar.") in got
              and not any("Ask the room" in t for t in texts), got)
        check("an instruction to the room is not a claim (GAS BASIC: \"Write your six answers on your card\" was judged a fact)",
              not any(sid == "s04" for sid, _, _ in got), got)
        check("a scenario's situation is not a claim; its why lines are",
              not any(t.startswith("Loading of propane") for t in texts) and ("s03", "why", "Right: the emergency shutdown stops the loading at once.") in got, got)
        check("... a question's right answer and its feedback are claims; its wrong answers are not",
              ("q01", "answer", "Copper and zinc") not in got and any(f == "feedback" for _, f, _ in got) and "Stainless steel" not in texts, got)

        print("\n-- prepare: nothing to check against without a knowledge base")
        code = fc.main(["prepare", c, "--module", "1"])
        check("no knowledge base: exit 2, nothing written", code == 2 and not os.path.isfile(fc.store_path(c, 1)))
        check("... and the approval is not held by it", cs.proof_findings(c, cs.load(cs.paths(c, 1)["script"])) == [])
        io.open(os.path.join(c, "working_claude", "kb_sources.json"), "w", encoding="utf-8").write(json.dumps({"knowledge_base": kb}))
        f = cs.proof_findings(c, cs.load(cs.paths(c, 1)["script"]))
        check("with a knowledge base, a script whose claims are not judged is refused", [x["rule"] for x in f] == ["c_unchecked"], f)

        st, new, auto = fc.prepare(c, 1)
        by = {r["text"]: r for r in st["claims"].values()}
        check("a claim a source sentence says word for word, with its number, is proved here",
              by["Type C tanks are pressure vessels designed for about 18 bar gauge."].get("verdict") == "found"
              and by["Type C tanks are pressure vessels designed for about 18 bar gauge."]["source"] == "Handout.pdf p.5", by)
        check("... a reworded or unsourced one goes to the agent, with its passages",
              not by["Type C tanks are painted green on every ship."].get("verdict")
              and any(p["src"] == "Handout.pdf p.5" for p in by["Type C tanks are painted green on every ship."]["passages"]), by)
        ids = {r["text"]: cid for cid, r in st["claims"].items()}

        print("\n-- judge")
        green, cold = ids["Type C tanks are painted green on every ship."], ids["A semi-refrigerated ship cools its cargo to make the tanks lighter."]
        done, probs = fc.judge(c, 1, [{"id": green, "verdict": "found", "quote": "Type C tanks are painted green", "source": "Handout.pdf p.5"}])
        check("a quote no source holds is refused - nothing is proved from memory", done == 0 and "not in the sources" in probs[0], probs)
        done, probs = fc.judge(c, 1, [{"id": green, "verdict": "partly"}])
        check("... partly without its fix is refused", done == 0 and "needs its fix" in probs[0], probs)
        done, probs = fc.judge(c, 1, [{"id": cold, "verdict": "partly", "fix": "A semi-refrigerated ship cools the cargo, so its tanks can be lighter."}])
        check("... new words without the quote they come from are refused", done == 0 and "not in the sources" in probs[0], probs)
        verdicts = [{"id": green, "verdict": "not_found", "fix": "cut"},
                    {"id": cold, "verdict": "partly", "quote": "A semi-refrigerated ship cools the cargo, so its tanks can be lighter",
                     "source": "Handout.pdf p.6", "fix": "A semi-refrigerated ship cools the cargo, so its tanks can be lighter."}]
        for text, cid in ids.items():
            if cid not in (green, cold) and not st["claims"][cid].get("verdict"):
                verdicts.append({"id": cid, "verdict": "found", "quote": "brass fittings are never used in ammonia service" if "mmonia" in text
                                 else "needs a reliquefaction plant" if "reliquefaction" in text else "designed for about 18 bar gauge",
                                 "source": "Guide.pdf p.40"})
        done, probs = fc.judge(c, 1, verdicts)
        check("verdicts with quotes the sources hold are recorded - one found only by a fresh search too", not probs and done == len(verdicts), probs)
        check("a quote matches whatever its spacing (\"18bar\" is \"18 bar\")", fc.quote_in("designed for about 18bar gauge", [PIECES[0][2]]))

        print("\n-- the approval, and the fixes")
        f = cs.proof_findings(c, cs.load(cs.paths(c, 1)["script"]))
        check("a claim judged not found or partly and still in the script is refused",
              sorted((x["rule"], x["screen"]) for x in f) == [("c_unproven", "s01"), ("c_unproven", "s02")], f)
        changes, asks, held, waiting = fc.fixes(c, 1)
        by_f = {(x["screen"], x["field"]): x["new"] for x in changes}
        check("fixes does not cut the line found nowhere - it goes to the writer for a rewrite first",
              ("s01", "text") not in by_f and [(w, r["screen"]) for w, r in waiting] == [("rewrite", "s01")] and not held, (changes, waiting))
        check("... and rewrites the line found partly as the source says it",
              by_f.get(("s02", "text")) == "A semi-refrigerated ship cools the cargo, so its tanks can be lighter.\nWhy does it cool?", changes)
        sent = fc.rewrites(c, 1)
        check("... rewrites sends it to the writer with where it was searched (the knowledge base, the source files, the old "
              "course) and the passages nearest to it", [x["id"] for x in sent] == [green]
              and [x["where"] for x in sent[0]["searched"]] == ["kb", "source_files", "old_course"] and sent[0]["closest"], sent)
        n, probs = fc.apply_rewrite(c, 1, [{"screen": "s01", "field": "text",
                                            "new": "Type C tanks are pressure vessels designed for about 18 bar gauge.\nShort line"}])
        check("... the writer leaves the line out when no source says anything near it", n == 1 and not probs
              and "green" not in cs.load(cs.paths(c, 1)["script"])["screens"][0]["text"], probs)
        fc.prepare(c, 1)
        changes, asks, held, waiting = fc.fixes(c, 1)
        script = cs.load(cs.paths(c, 1)["script"])
        ch, work = cs.build_changes(script, changes)
        check("... the correction is a change list content_script propose understands", len(ch) == 1 and not held and not waiting)
        cs.save(cs.paths(c, 1)["script"], work)
        check("once the change is applied, nothing holds the approval", cs.proof_findings(c, work) == [], cs.proof_findings(c, work))
        work["screens"][0]["text"] += "\nType C tanks are designed for about 40 bar gauge."
        cs.save(cs.paths(c, 1)["script"], work)
        f = cs.proof_findings(c, work)
        check("a line written after the check is judged again", [x["rule"] for x in f] == ["c_unchecked"] and "1 of" in f[0]["detail"], f)
        st = fc.load_store(c, 1)
        q = [cid for cid, r in st["claims"].items() if r["field"] == "feedback"]
        fc.judge(c, 1, [{"id": q[0], "verdict": "partly", "quote": "Ammonia attacks copper and zinc, so brass fittings are never used",
                         "source": "Guide.pdf p.40", "fix": "Ammonia attacks copper and zinc, so brass fittings are never used."}])
        changes, asks, _, _ = fc.fixes(c, 1)
        check("a question's answer or feedback is never changed by fixes, only listed for the person",
              not any(x["screen"] == "q01" for x in changes) and asks and asks[0]["screen"] == "q01", (changes, asks))
        rv = [cid for cid, r in fc.load_store(c, 1)["claims"].items() if r["field"] == "reveal"]
        fc.judge(c, 1, [{"id": rv[0], "verdict": "partly", "quote": "needs a reliquefaction plant", "source": "Handout.pdf p.6",
                         "fix": "It needs a reliquefaction plant."}])
        changes, asks, _, _ = fc.fixes(c, 1)
        check("... nor the answer a slide reveals to the room's question - the ask would lose it (factory trial M08 s15)",
              not any(x["field"] == "reveal" for x in changes) and any(r["field"] == "reveal" and r["screen"] == "s02" for r in asks),
              (changes, asks))
        fc.judge(c, 1, [{"id": rv[0], "verdict": "found", "quote": "needs a reliquefaction plant", "source": "Handout.pdf p.6"}])
        st = fc.load_store(c, 1)
        st["claims"]["pt"] = {"screen": "s01", "field": "points", "line": 1, "text": "Type C - about 18 bar"}
        fc.save_store(c, 1, st)
        done, probs = fc.judge(c, 1, [{"id": "pt", "verdict": "partly", "quote": "Type C tanks are pressure vessels designed for about 18 bar gauge",
                                       "source": "Handout.pdf p.5", "fix": "Type C tanks are pressure vessels designed for about 18 bar gauge, "
                                       "and they need no secondary barrier."}])
        check("a correction of a short point that is no longer short is refused - the point is rewritten short",
              done == 0 and "%d words or fewer" % cs.POINT_WORDS in probs[0], probs)
        st = fc.load_store(c, 1)
        del st["claims"]["pt"]
        fc.save_store(c, 1, st)
        check("a source sentence that ends mid-clause is known (the knowledge base cut it off), a whole one is not",
              fc.cut_off("In addition, loss of over-pressure in the motor room should trip the electric motors within.")
              and not fc.cut_off("They need no secondary barrier.") and not fc.cut_off("Ammonia attacks copper and zinc."))
        st = fc.load_store(c, 1)
        eighteen = next(cid for cid, r in st["claims"].items() if r["text"].startswith("Type C tanks are pressure vessels"))
        kept_quote = st["claims"][eighteen]["quote"]
        st["claims"][eighteen]["quote"] = "Type C tanks are pressure vessels designed for about 18 bar gauge within."
        fc.save_store(c, 1, st)
        f = [x for x in cs.proof_findings(c, cs.load(cs.paths(c, 1)["script"])) if x["rule"] == "c_cut_quote"]
        check("... a slide line proved by one is listed for the person - a note, never a stop",
              [(x["screen"], x["level"]) for x in f] == [("s01", cs.NOTE)], f)
        st["claims"][eighteen]["quote"] = kept_quote
        fc.save_store(c, 1, st)
        work = cs.load(cs.paths(c, 1)["script"])
        work["screens"][0]["text"] += "\nThe example ship A carries 3,500 m3 of LPG at sea."
        cs.save(cs.paths(c, 1)["script"], work)
        st, _, _ = fc.prepare(c, 1)
        ex = next(cid for cid, r in st["claims"].items() if r["text"].startswith("The example ship A"))
        done, probs = fc.judge(c, 1, [{"id": ex, "verdict": "not_a_claim"}])
        check("a line set aside as no claim needs its why", done == 0 and "needs its why" in probs[0], probs)
        done, probs = fc.judge(c, 1, [{"id": ex, "verdict": "not_a_claim", "why": "an example made up for the task"}])
        s = fc.status(c, 1)
        check("... with it, it holds nothing and is listed for the person to glance at (GAS BASIC: the photo key A-F was "
              "judged a fact and cut)", done == 1 and any(t.startswith("The example ship A") for _, t, _ in s["set_aside"])
              and not any(t.startswith("The example ship A") for _, t, _ in s["unproven"]), s)
        st, _, _ = fc.prepare(c, 1)
        forty = next(cid for cid, r in st["claims"].items() if "40 bar" in r["text"])
        fc.judge(c, 1, [{"id": forty, "verdict": "not_found", "fix": "cut"}])
        buf_code = fc.main(["fixes", c, "--module", "1", "--apply"])
        check("attended, fixes --apply is refused: the operator sees the changes first", buf_code == 2)

        def unattended(*args):
            os.environ["NOVIKONTAS_AUTO_BUILD"] = "1"
            buf = io.StringIO()
            try:
                with contextlib.redirect_stdout(buf):
                    code = fc.main(list(args))
            finally:
                del os.environ["NOVIKONTAS_AUTO_BUILD"]
            return code, buf.getvalue()
        code, out = unattended("fixes", c, "--module", "1", "--apply")
        check("an unattended build does not cut a claim found nowhere before its rewrite",
              code == 0 and "40 bar" in cs.load(cs.paths(c, 1)["script"])["screens"][0]["text"] and "to the writer first" in out, out)
        fc.rewrites(c, 1)
        fc.apply_rewrite(c, 1, [], "script:1 (writer)")       # the writer found nothing in the sources to rewrite it from
        import task_cover
        h = task_cover.current(cs.load(cs.paths(c, 1)["script"]))["q01"][0]
        task_cover.save_store(c, 1, {"module": "1", "questions": {"q01": {"hash": h, "verdict": "covered", "slides": ["s01"],
                                                                         "quote": ["designed for about 40 bar gauge"], "by": "test"}}})
        code, out = unattended("fixes", c, "--module", "1", "--apply")
        after = cs.load(cs.paths(c, 1)["script"])
        check("still not proved after the rewrite, an unattended build cuts it itself (nobody there to say yes) - and exits 0: "
              "the apply worked (the factory trial read an exit 1 after it as a failed apply)", code == 0
              and "40 bar" not in after["screens"][0]["text"] and "18 bar" in after["screens"][0]["text"]
              and not os.path.isfile(cs.paths(c, 1)["pending"]), after["screens"][0])
        check("... and says the task cover must be judged again, naming the line a covered question relied on (factory trial "
              "M04 s04, M01 s15)", "must be judged again" in out and "q01 relied on \"designed for about 40 bar gauge\"" in out, out)
        check("... and prints what approve would stop on, after the correction it made", "Approve would stop" in out, out)
        f = cs.task_cover_findings(c, after)
        check("... a must-fix until it is judged again, which says what is gone",
              [(x["screen"], x["level"]) for x in f] == [("q01", cs.FAIL)] and "40 bar" in f[0]["detail"], f)
        listed = json.load(io.open(fc.side_path(c, 1, "operator"), encoding="utf-8"))
        check("... and writes it to the operator's list with the question's fields and what it did",
              len(listed) == 1 and listed[0]["sentence"] == "Type C tanks are designed for about 40 bar gauge." and listed[0]["screen"] == "s01"
              and listed[0]["searched"] and listed[0]["why"] and listed[0]["done"].startswith("cut")
              and "operator's list" in out and fc.status(c, 1)["to_operator"] == 1, (listed, out))
        check("... and every finding is said in Latvian and Russian too",
              all(cs.LABELS[lang].get(k) for lang in ("lv", "ru") for k in ("c_unchecked", "c_unproven")))

        print("\n-- the sources in order, the internet, the rewrite and the operator (module 2)")
        flow(c)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("\n%d passed, %d failed" % (len(PASS), len(FAIL)))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
