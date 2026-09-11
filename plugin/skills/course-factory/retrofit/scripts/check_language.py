#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""COURSE_LANGUAGE drift: is any course-facing file drifting out of the course's
own language?

    check_language.py <course_dir> --declare English
    check_language.py <course_dir>                  # detect and report
    check_language.py <course_dir> --declare English --strict

WHY THIS EXISTS
A Latvian operator asks, in Latvian, to redesign an English module. The chat
report may be Latvian. Every slide, task, handout, assessment and instructor
cue must stay English. Translating an accredited course because the request
arrived in another language destroys the artefact, and it is an easy thing to
do a screen at a time without noticing.

WHAT IT IS
A lightweight profile check, not a language model. It looks at script (Cyrillic
vs Latin), at diacritics that only some languages use, and at the commonest
function words - the words that survive any subject matter. That is enough to
catch a screen that changed language; it is not enough to judge a sentence, and
it does not try.

WHAT IS COURSE-FACING
Slides, tasks, handouts, assessment, feedback text, instructor cues, practical
cards, START_HERE, the run script. NOT: factory-notes.md, code comments,
validator output, commit messages, the chat report. Those follow the operator.

Exit 1 only under --strict, and only on a real disagreement.
"""

import argparse
import json
import re
import sys
from pathlib import Path

# Function words, not vocabulary. A maritime English screen and a maritime
# Latvian screen share most of their nouns and almost none of these.
PROFILES = {
    "English": {
        "words": set("the a an and or of to in is are was were be been for with on at by "
                     "this that these those from as it its not no if then than when which "
                     "what who how why must shall may can will would should each every "
                     "before after between under over into out up down".split()),
        "marks": "",
    },
    "Latvian": {
        "words": set("un ir vai ar no uz par kā tas tā to šī šis šo tie tās bet ja tad "
                     "kas kad kur kāpēc jā nē pēc pirms starp zem virs katrs katra visi "
                     "nav var jābūt tikai arī vēl jau pats pati savu sava".split()),
        "marks": "āčēģīķļņšūž",
    },
    "Norwegian": {
        "words": set("og eller av til i er var for med på som det den de dette disse "
                     "ikke men hvis da hva hvem hvordan hvorfor må skal kan vil bør "
                     "hver alle etter før mellom under over".split()),
        "marks": "æøå",
    },
    "Russian": {
        "words": set("и или из для в на с по что это как не но если то все для при "
                     "он она они его ее их быть есть может должен".split()),
        "marks": "",
        "script": "cyrillic",
    },
}

COURSE_FACING = [
    "module.html", "START_HERE.html", "index.html",
    "tasks/", "assessment/", "handout/", "practicals/", "plan/", "record/",
]
NOT_COURSE_FACING = [
    "factory-notes.md", "visual-notes.md", "_work/", "README", "MANIFEST",
    ".bak", "oldversion", "retired",
]

TAG = re.compile(r"<(script|style)[^>]*>.*?</\1>", re.S | re.I)
STRIP = re.compile(r"<[^>]+>")
COMMENT = re.compile(r"<!--.*?-->", re.S)
WORD = re.compile(r"[^\W\d_]+", re.UNICODE)
CYR = re.compile(r"[Ѐ-ӿ]")


def visible_text(path):
    """Only what a learner reads: no script, no style, no comments, no markup.

    data-cue is instructor-facing but still course-facing - it is read aloud in
    the room - so attribute text is kept when it is a cue or a title."""
    raw = path.read_text(encoding="utf-8", errors="replace")
    if path.suffix.lower() in (".html", ".htm"):
        attrs = " ".join(re.findall(r'data-(?:cue|title|foot)="([^"]*)"', raw))
        raw = COMMENT.sub(" ", raw)
        raw = TAG.sub(" ", raw)
        raw = STRIP.sub(" ", raw)
        raw = raw + " " + attrs
    return raw


def profile(text):
    words = [w.lower() for w in WORD.findall(text)]
    if len(words) < 25:
        return None, {}, len(words)
    scores = {}
    for lang, spec in PROFILES.items():
        hits = sum(1 for w in words if w in spec["words"])
        s = hits / len(words)
        if spec.get("script") == "cyrillic":
            s = s * 3 if CYR.search(text) else 0.0
        elif spec["marks"]:
            dia = sum(text.lower().count(c) for c in spec["marks"])
            s += min(0.08, dia / max(1, len(text)) * 4)
        scores[lang] = round(s, 4)
    best = max(scores, key=scores.get)
    return (best if scores[best] > 0.012 else None), scores, len(words)


def is_course_facing(rel):
    r = rel.replace("\\", "/")
    if any(x in r for x in NOT_COURSE_FACING):
        return False
    return any(r == c or r.startswith(c) or ("/" + c) in r or r.endswith(c)
               for c in COURSE_FACING)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("target")
    ap.add_argument("--declare", help="COURSE_LANGUAGE, e.g. English or English+Latvian")
    ap.add_argument("--strict", action="store_true", help="exit 1 on drift")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    root = Path(a.target)
    if root.is_file():
        files = [root]
        root = root.parent
    else:
        files = [f for f in sorted(root.rglob("*"))
                 if f.is_file() and f.suffix.lower() in (".html", ".htm")]

    rows, skipped = [], 0
    for f in files:
        rel = str(f.relative_to(root))
        if not is_course_facing(rel):
            skipped += 1
            continue
        lang, scores, n = profile(visible_text(f))
        rows.append({"file": rel, "lang": lang, "words": n,
                     "scores": dict(sorted(scores.items(), key=lambda x: -x[1])[:3])})

    declared = a.declare
    if not declared and rows:
        seen = {}
        for r in rows:
            if r["lang"]:
                seen[r["lang"]] = seen.get(r["lang"], 0) + r["words"]
        declared = max(seen, key=seen.get) if seen else None

    allowed = set()
    if declared:
        allowed = {x.strip() for x in re.split(r"[+/,]", declared) if x.strip()}

    drift = [r for r in rows if r["lang"] and allowed and r["lang"] not in allowed]

    if a.json:
        print(json.dumps({"declared": declared, "files": rows, "drift": drift},
                         ensure_ascii=False, indent=1))
        return 1 if (drift and a.strict) else 0

    print("=" * 72)
    print("check_language - COURSE_LANGUAGE drift")
    print("=" * 72)
    print("\nCOURSE_LANGUAGE: %s%s\n" % (declared or "UNKNOWN",
          "" if a.declare else "   (detected, not declared - declare it in factory-notes.md)"))
    for r in rows:
        mark = "  " if (not r["lang"] or not allowed or r["lang"] in allowed) else "->"
        print("%s %-42s %-10s %5d words" % (mark, r["file"][:42], r["lang"] or "(too short)", r["words"]))
    print("\n%d course-facing file(s), %d skipped as not course-facing." % (len(rows), skipped))
    if drift:
        print("\n%d FILE(S) DRIFTED OUT OF %s:" % (len(drift), declared))
        for r in drift:
            print("   %s reads as %s" % (r["file"], r["lang"]))
        print("\nA course does not change language because the request arrived in another one.")
        print("The chat report follows the operator; slides, tasks, handouts, assessment and")
        print("instructor cues follow COURSE_LANGUAGE.")
    else:
        print("\nNo course-facing file disagrees with COURSE_LANGUAGE.")
    print("\nThis is a profile check - script, diacritics and function words. It catches a")
    print("screen that changed language. It does not judge a sentence, and does not try.")
    return 1 if (drift and a.strict) else 0


if __name__ == "__main__":
    sys.exit(main())
