#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Is every itemised learning outcome the model course asks for actually taught?

The accredited Study Programme gives you TOPICS and hours. The IMO model course
behind it gives you the itemised outcomes under each topic - its "Knowledge,
Understanding and Proficiency" column - and those are the sub-ILOs in
everything but name. A course can cover all 23 programme topics and still miss
individual outcomes inside them.

On GAS BASIC this had never been checked. The topic-level coverage record was
green at 64 of 64 and did not mention the model course once. Checking 1.04's
own 266 outcomes found exactly one real gap - decontamination showers and
eyewash on deck, IMO 9.2.7 - which was in no screen, task, document, handout or
assessment. One gap in 266 is a good result, and it was invisible at topic
level.

A VERDICT HERE IS A POINTER, NOT A PROOF.

    covered   every distinctive word of the outcome is somewhere in the course
    review    some words present, some not - READ IT and decide
    MISSING   almost nothing present; the likely real gaps

This kind of search over-reports misses, always, and for reasons worth knowing
before you trust a number:

  * A good course teaches in its own words. GAS BASIC's screen for "effect of
    pollution on people and marine organisms" says "what it does to people, and
    what it does to the water" - better teaching, invisible to the programme's
    phrasing.
  * Model courses are extracted from PDFs that still carry tracked changes, so
    requirement text arrives corrupted: "DescribesExplains", "fFlammable
    vVapours", "Identifiesy isplays", "areis", "aApplicator". Those tokens can
    never match anything. 14 of 32 review items on GAS BASIC were this.
  * Model courses are written in American spelling and maritime courses often
    in British. Until -ize and -ise were folded together, a dozen outcomes
    looked absent that were on the screen. That folding is built in here.

So: work the `review` list by hand, searching for the CONCEPT rather than the
model course's wording, and record what you find with --resolved so the next
run does not ask again.

Input
-----
--syllabus  a JSON transcription of the model course's detailed syllabus:

    { "source": "IMO Model Course 1.04",
      "items_by_topic": {
        "1": [ {"id": "1.0",   "requirement": "BASIC KNOWLEDGE OF ... (3 hours)"},
               {"id": "1.1.1", "requirement": "States that ..."} ],
        "2": [ ... ] } }

    Items whose text is a heading or an hours note are counted separately -
    they are not outcomes and must not be counted as gaps.

--course    a directory the course is built in; repeat for each root (the
            source tree, each terminal's assets). Everything a trainee or an
            instructor can read counts as taught.

--resolved  optional JSON: { "9.2.7": "closed 2026-09-07: added to the M5
            handout with its ICS citation", ... }. Ids listed here are reported
            as resolved instead of as gaps.

Usage
-----
    check_syllabus_coverage.py --syllabus syllabus.json \\
        --course course --course app/src/main/assets --out imo_coverage.json

Exit codes: 0 nothing MISSING · 1 MISSING items · 2 bad input
"""
import argparse
import collections
import json
import pathlib
import re
import sys

STOP = set("""a an the and or but if of in on at to for from by with without as is are was were
be been being it its this that these those there here what which who whom whose when where why
how all any both each few more most other some such no nor not only own same so than too very
can will just should now also into out up down over under again further then once about above
below between during before after you your they their them we our us he she his her i me my
one two three four five six seven eight nine ten states state describes describe explains
explain lists list identifies identify outlines outline knows know understands understand
generally general following follows shall must may given etc used use uses using including
include includes""".split())

HEADING = re.compile(r"^[A-Z][A-Z \-/(),&']{8,}|^\s*BASIC KNOWLEDGE|"
                     r"\(\s*\d+(?:\.\d+)?\s*hours?\s*\)", re.M)
VERB = re.compile(r"^\s*(?:states?|describes?|explains?|lists?|identifies|outlines?|knows?|"
                  r"understands?|defines?|demonstrates?)\s+(?:that\s+|generally\s+)?", re.I)
# tracked-changes damage: a lower-to-upper run inside one word ("DescribesExplains"),
# a doubled first letter ("fFlammable"), or a verb glued to a fragment
DAMAGE = re.compile(r"\b[a-z]+[A-Z][a-z]+|\b([A-Za-z])\1[a-z]{3,}|\bDe[sc]ribes[a-z]|"
                    r"\bareis\b|\bares\b|\bisplays?\b|\bIdentifiesy\b")


def words(t):
    t = VERB.sub("", t)
    t = re.sub(r"[^A-Za-zÀ-ɏ\- ]", " ", t.lower())
    out = []
    for w in t.split():
        w = w.strip("-")
        if len(w) < 4 or w in STOP or NOISE.search(w):
            continue
        out.append(w)
    return out


def stem(w):
    """Only endings that change nothing about meaning - plus the -ise/-ize fold.

    The model course writes "pressurized", the course writes "pressurised".
    Both must reach the same stem or a dozen taught outcomes read as absent.
    """
    w = re.sub(r"is(e|ed|es|ing|ation|ations)$", r"iz\1", w)
    for suf in ("ations", "ation", "ings", "ing", "ies", "ers", "er", "ed", "s"):
        if w.endswith(suf) and len(w) - len(suf) >= 4:
            w = w[:-len(suf)]
            break
    return re.sub(r"iz$", "", w)


NOISE = re.compile(r"[^aeiouyà-ÿ]{5,}|^[a-f0-9]{12,}$|.{25,}", re.I)


def read_course(roots):
    """Only what a person can READ.

    Getting this wrong makes the whole check useless in the direction that
    matters. Leaving <script> in gave 520,000 distinct "words" from 16 MB -
    minified code and base64 image data - and against a vocabulary that large
    almost any requirement scores as covered, so a real gap hides. Scripts and
    styles go; so do tokens that are not words (long consonant runs, hex
    strings, anything over 24 characters).

    Duplicate single-file builds are skipped too: a course that ships the same
    module twice should not get two votes.
    """
    texts, seen = [], set()
    for root in roots:
        for p in root.rglob("*"):
            if p.suffix.lower() not in (".html", ".md"):
                continue
            parts = set(p.parts)
            if parts & {"oldversion", "test_area", "node_modules", "__pycache__",
                        "apps_script_ready", "build"}:
                continue
            if ".bak" in p.name:
                continue
            key = (p.name, p.stat().st_size)
            if key in seen:
                continue
            seen.add(key)
            s = p.read_text(encoding="utf-8", errors="replace")
            s = re.sub(r"<(script|style)\b.*?</\1>", " ", s, flags=re.S | re.I)
            s = re.sub(r"<!--.*?-->", " ", s, flags=re.S)
            s = re.sub(r"\bdata:[^\s\"')]+", " ", s)
            texts.append(re.sub(r"<[^>]+>", " ", s))
    return " ".join(texts)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--syllabus", required=True)
    ap.add_argument("--course", action="append", required=True)
    ap.add_argument("--resolved")
    ap.add_argument("--out")
    ap.add_argument("--covered-at", type=float, default=0.85)
    ap.add_argument("--review-at", type=float, default=0.55)
    a = ap.parse_args()

    sf = pathlib.Path(a.syllabus)
    if not sf.is_file():
        print("INPUT ERROR: no such file: %s" % sf)
        sys.exit(2)
    syl = json.loads(sf.read_text(encoding="utf-8"))
    items = syl.get("items_by_topic")
    if not items:
        print("INPUT ERROR: --syllabus has no `items_by_topic`. Shape is in the docstring.")
        sys.exit(2)

    roots = [pathlib.Path(x) for x in a.course]
    for r in roots:
        if not r.is_dir():
            print("INPUT ERROR: not a directory: %s" % r)
            sys.exit(2)

    resolved = {}
    if a.resolved:
        rf = pathlib.Path(a.resolved)
        if rf.is_file():
            resolved = json.loads(rf.read_text(encoding="utf-8"))

    src = syl.get("source") or syl.get("_source")
    if isinstance(src, dict):
        src = src.get("imo") or src.get("model_course") or json.dumps(src)[:90]
    print("source: %s" % (src or "not stated  [VERIFY: name the model course]"))
    corpus = read_course(roots)
    have = set(stem(w) for w in words(corpus))
    print("course: %.1f MB of readable text, %d distinct stems" % (len(corpus) / 1e6, len(have)))

    rows = []
    for topic, lst in items.items():
        for it in lst:
            req = it.get("requirement", "")
            uniq = sorted(set(stem(w) for w in words(req)))
            if not uniq:
                continue
            hit = [w for w in uniq if w in have]
            miss = [w for w in uniq if w not in have]
            score = len(hit) / float(len(uniq))
            is_head = bool(HEADING.search(req)) or re.match(r"^\d+\.0$", str(it.get("id", "")))
            damaged = bool(DAMAGE.search(req))
            if is_head:
                verdict = "heading"
            elif str(it.get("id")) in resolved:
                verdict = "covered"
            elif score >= a.covered_at:
                verdict = "covered"
            elif score >= a.review_at:
                verdict = "review"
            else:
                verdict = "MISSING"
            row = {"topic": topic, "id": it.get("id"), "requirement": req,
                   "verdict": verdict, "score": round(score, 2),
                   "terms_absent": miss}
            if damaged:
                row["source_text_damaged"] = True
            if str(it.get("id")) in resolved:
                row["resolved"] = resolved[str(it.get("id"))]
            rows.append(row)

    c = collections.Counter(r["verdict"] for r in rows)
    outcomes = [r for r in rows if r["verdict"] != "heading"]
    print()
    print("=" * 78)
    print("%d item(s): %d heading(s)/hours note(s), %d learning outcome(s)"
          % (len(rows), c.get("heading", 0), len(outcomes)))
    print("=" * 78)
    for k in ("covered", "review", "MISSING"):
        print("   %-9s %d" % (k, c.get(k, 0)))
    if outcomes:
        print("   covered outright: %.0f %%" % (100.0 * c.get("covered", 0) / len(outcomes)))

    print()
    print("%-7s %7s %8s %8s %9s" % ("topic", "items", "covered", "review", "MISSING"))
    print("-" * 78)
    for t in sorted(items, key=lambda x: (len(str(x)), str(x))):
        tr = [r for r in rows if r["topic"] == t and r["verdict"] != "heading"]
        cc = collections.Counter(r["verdict"] for r in tr)
        print("%-7s %7d %8d %8d %9d" % (t, len(tr), cc.get("covered", 0),
                                        cc.get("review", 0), cc.get("MISSING", 0)))

    work = [r for r in rows if r["verdict"] in ("review", "MISSING")]
    if work:
        print()
        print("=" * 78)
        print("the work list - read each one and search for the CONCEPT, not this wording")
        print("=" * 78)
        dmg = 0
        for r in work:
            flag = ""
            if r.get("source_text_damaged"):
                dmg += 1
                flag = "   [source text damaged - tracked changes in the model course PDF]"
            print("\n   [%s %.2f] %s%s" % (r["verdict"], r["score"], r["id"], flag))
            print("        %s" % re.sub(r"\s+", " ", r["requirement"])[:160])
            print("        absent: %s" % ", ".join(r["terms_absent"][:10]))
        if dmg:
            print("\n   %d of %d carry damage in the model course's own extracted text. Their"
                  % (dmg, len(work)))
            print("   keywords could never have matched; read the requirement, not the score.")

    if a.out:
        p = pathlib.Path(a.out)
        p.write_text(json.dumps(
            {"_what": ("Every itemised outcome of the model course, checked against the course "
                       "by keyword. A verdict is a POINTER, not a proof: work `review` and "
                       "`MISSING` by hand and record the answers with --resolved. The accredited "
                       "Study Programme, not the model course, governs the hours."),
             "source": syl.get("source"), "counts": dict(c), "rows": rows},
            indent=1, ensure_ascii=False), encoding="utf-8")
        print("\nwrote %s" % p)

    print("\n" + "=" * 78)
    if c.get("MISSING"):
        print("%d outcome(s) look absent. Read them before believing it - but if one really is"
              % c["MISSING"])
        print("absent, it is a gap in an accredited course and it has to be taught or removed")
        print("from the claim.")
        sys.exit(1)
    if c.get("review"):
        print("nothing MISSING. %d item(s) need reading by hand - the list is above."
              % c["review"])
        sys.exit(0)
    print("every itemised outcome of the model course is present in the course")
    sys.exit(0)


if __name__ == "__main__":
    main()
