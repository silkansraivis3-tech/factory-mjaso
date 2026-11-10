# -*- coding: utf-8 -*-
"""test_fact_check - every claim of a content script proved in the course's own knowledge base (fact_check.py).

    python test_fact_check.py

Pinned:
  * the claims: a slide's lines (or its points) and its revealed answer, a note's line with a number, a question's
    right answer and feedback - not a short line, not a question, not a note without a number;
  * prepare proves a claim a source sentence says word for word, with every number; a reworded one goes to the agent;
  * judge refuses a quote no source holds (nothing proved from memory), a not found or partly without its fix, and new
    words without the quote they come from; a quote a fresh search finds is accepted;
  * fixes cuts a line found nowhere and rewrites one found partly - a change list content_script propose accepts; a
    question's answer is never changed, only listed;
  * the approval: a course with a knowledge base is refused while a claim is not judged or one not proved is still in
    the script; a changed line is judged again; a course without a knowledge base is not checked.
"""
from __future__ import annotations

import io
import json
import os
import re
import shutil
import sys
import tempfile
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


def main():
    tmp = tempfile.mkdtemp(prefix="factcheck_")
    try:
        c = os.path.join(tmp, "course")
        os.makedirs(os.path.join(c, "working_claude", "script"))
        cs.save(cs.paths(c, 1)["script"], json.loads(json.dumps(SCRIPT)))
        kb = os.path.join(tmp, "KB")
        make_kb(kb)

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
        done, probs = fc.judge(c, 1, [{"id": green, "verdict": "not_found"}])
        check("... not found without its fix is refused", done == 0 and "needs its fix" in probs[0], probs)
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
        changes, asks = fc.fixes(c, 1)
        by_f = {(x["screen"], x["field"]): x["new"] for x in changes}
        check("fixes cuts the line found nowhere, keeps the others", by_f.get(("s01", "text")) ==
              "Type C tanks are pressure vessels designed for about 18 bar gauge.\nShort line", changes)
        check("... and rewrites the line found partly as the source says it",
              by_f.get(("s02", "text")) == "A semi-refrigerated ship cools the cargo, so its tanks can be lighter.\nWhy does it cool?", changes)
        script = cs.load(cs.paths(c, 1)["script"])
        ch, work = cs.build_changes(script, changes)
        check("... as a change list content_script propose understands", len(ch) == 2)
        cs.save(cs.paths(c, 1)["script"], work)
        check("once the change is applied, nothing holds the approval", cs.proof_findings(c, work) == [], cs.proof_findings(c, work))
        work["screens"][0]["text"] += "\nType C tanks are designed for about 40 bar gauge."
        cs.save(cs.paths(c, 1)["script"], work)
        f = cs.proof_findings(c, work)
        check("a line written after the check is judged again", [x["rule"] for x in f] == ["c_unchecked"] and "1 of" in f[0]["detail"], f)
        st = fc.load_store(c, 1)
        q = [cid for cid, r in st["claims"].items() if r["field"] == "feedback"]
        fc.judge(c, 1, [{"id": q[0], "verdict": "not_found", "fix": "cut"}])
        changes, asks = fc.fixes(c, 1)
        check("a question's answer or feedback is never changed by fixes, only listed for the person",
              not any(x["screen"] == "q01" for x in changes) and asks and asks[0]["screen"] == "q01", (changes, asks))
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
        os.environ["NOVIKONTAS_AUTO_BUILD"] = "1"
        try:
            code = fc.main(["fixes", c, "--module", "1", "--apply"])
        finally:
            del os.environ["NOVIKONTAS_AUTO_BUILD"]
        after = cs.load(cs.paths(c, 1)["script"])
        check("an unattended build applies the cuts itself (nobody there to say yes)", code == 0
              and "40 bar" not in after["screens"][0]["text"] and "18 bar" in after["screens"][0]["text"]
              and not os.path.isfile(cs.paths(c, 1)["pending"]), after["screens"][0])
        check("... and every finding is said in Latvian and Russian too",
              all(cs.LABELS[lang].get(k) for lang in ("lv", "ru") for k in ("c_unchecked", "c_unproven")))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("\n%d passed, %d failed" % (len(PASS), len(FAIL)))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
