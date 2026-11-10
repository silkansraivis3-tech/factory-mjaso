#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""test_photo_catalogue.py - the words of a page or slide are found whatever else the heading line says."""
from __future__ import annotations

import os
import sys
import tempfile

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "kb", "scripts"))
import photo_catalogue as pc  # noqa: E402

PASS, FAIL = [], []


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print(("  ok    " if ok else "  FAIL  ") + name + (("  -> " + str(detail)[:700]) if detail and not ok else ""))


def main():
    tmp = tempfile.mkdtemp(prefix="photocat_")
    md = os.path.join(tmp, "document.md")
    with open(md, "w", encoding="utf-8", newline="\n") as f:
        f.write("## Page 1\n\nCover words.\n\n## Page 2\n\nPump room layout.\n\n"
                "## Slide 4 - Inert gas plant\n\nScrubber and blowers.\n\n## Section 2 (annex)\n\nAnnex words here.\n\n"
                "## Slide 5\n\nLast slide words.\n")
    cache = {}
    check("a plain '## Page N' heading still works", pc.page_words(md, "page", 2, cache) == "Pump room layout.",
          pc.page_words(md, "page", 2, cache))
    check("'## Slide 4 - Title' carries its words", pc.page_words(md, "slide", 4, cache) == "Scrubber and blowers.",
          pc.page_words(md, "slide", 4, cache))
    check("'## Section 2 (annex)' carries its words", pc.page_words(md, "section", 2, cache) == "Annex words here.",
          pc.page_words(md, "section", 2, cache))
    check("a section ends at the next heading, whatever it says",
          "Annex" not in pc.page_words(md, "slide", 4, cache) and pc.page_words(md, "slide", 5, cache) == "Last slide words.")
    check("a page that is not there has no words", pc.page_words(md, "page", 9, cache) == "")
    print("\n%d passed, %d failed" % (len(PASS), len(FAIL)))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
