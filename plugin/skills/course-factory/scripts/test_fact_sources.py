# -*- coding: utf-8 -*-
"""test_fact_sources - every measured value on a slide is found in a source the course holds (L4).

    python test_fact_sources.py

Pinned:
  * a number with its unit that no source holds is a must-fix; one the retrieval packs, the old course, the knowledge
    base or the operator's facts hold is not;
  * "7,500 m3" on the slide is "7500" in the source; a range checks both ends; the number is matched, whatever way the
    source spells its unit;
  * the instructor's notes are not checked - only what the slide shows;
  * a course with no sources of its own (no knowledge base, no retrieval packs) is not checked.
"""
from __future__ import annotations

import io
import json
import os
import shutil
import sys
import tempfile

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import content_script as cs  # noqa: E402

PASS, FAIL = [], []


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print(("  ok    " if ok else "  FAIL  ") + name + (("  -> " + str(detail)[:600]) if detail and not ok else ""))


def script(*texts, notes="- Say it."):
    return {"module": 1, "operator_language": "en", "screens": [
        {"id": "s%02d" % i, "kind": "slide", "title": "Slide %d" % i, "text": t, "notes": notes} for i, t in enumerate(texts, 1)]}


def flagged(course, sc):
    return sorted(f["screen"] for f in cs.fact_findings(course, sc) if f["rule"] == "f_untraced")


def main():
    tmp = tempfile.mkdtemp(prefix="facts_")
    try:
        c = os.path.join(tmp, "course")
        os.makedirs(os.path.join(c, "working_claude", "retrieval"))
        io.open(os.path.join(c, "working_claude", "retrieval", "pack.md"), "w", encoding="utf-8").write(
            "Type C tanks are designed for about 18 bar gauge. Semi-refrigerated ships carry up to 7500 m3. Pressure 5-7 bar.")
        kb = os.path.join(tmp, "KB")
        os.makedirs(os.path.join(kb, "search_index"))
        io.open(os.path.join(kb, "search_index", "chunks.jsonl"), "w", encoding="utf-8").write(
            json.dumps({"text": "Ammonia has an occupational exposure limit of 25 ppm."}) + "\n")
        io.open(os.path.join(c, "working_claude", "kb_sources.json"), "w", encoding="utf-8").write(json.dumps({"knowledge_base": kb}))

        check("values the sources hold pass: the retrieval pack, the thousands written apart, a range, the knowledge base",
              flagged(c, script("Built for about 18 bar gauge.", "Up to 7,500 m3 of LPG.", "Tanks for 5-7 bar.",
                                "The limit is 25 ppm.")) == [], cs.fact_findings(c, script("Up to 7,500 m3 of LPG.")))
        check("a value no source holds is a must-fix (written from memory)", flagged(c, script("Built for about 23 bar gauge.")) == ["s01"])
        check("... a range is checked at both ends", flagged(c, script("Tanks for 5-9 bar.")) == ["s01"])
        sc = script("Built for about 26 bar gauge.")
        sc["operator_facts"] = [{"fact": "Our simulator's tanks are built for 26 bar.", "where": "M01", "said": "2026-11-06"}]
        check("... unless the operator stated it", flagged(c, sc) == [])
        check("the instructor's notes are not checked - only what the slide shows",
              flagged(c, script("Built for about 18 bar gauge.", notes="- On the old ship it was 31 bar.")) == [])
        check("... and the finding is said in the operator's language", cs.LABELS["lv"].get("f_untraced") and cs.LABELS["ru"].get("f_untraced"))
        bare = os.path.join(tmp, "bare")
        os.makedirs(os.path.join(bare, "working_claude"))
        check("a course with no sources of its own is not checked", flagged(bare, script("Built for about 99 bar gauge.")) == [])
        check("numbers read the same in every form", cs.numbers_in("7,500 and 7 500 and 0,5 and 18") >= {"7500", "0.5", "18"})
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("\n%d passed, %d failed" % (len(PASS), len(FAIL)))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
