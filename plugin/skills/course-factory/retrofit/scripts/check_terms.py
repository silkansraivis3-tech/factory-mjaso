#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Terminology drift across a whole course: one thing, two names.

    check_terms.py <course_dir>                      # report mixed use, with where each variant is used
    check_terms.py <course_dir> --terms my.json      # a synonym list of your own, on top of the defaults
    check_terms.py <course_dir> --from pages         # judge the built pages (default: the approved scripts)
    check_terms.py <course_dir> --json

WHY THIS EXISTS (2.63.2)
The IGF full build's cross-check found, by hand, one quantity called LEL in three modules and LFL in the
later ones, "bunkering station" in M07-M15 beside "bunker station", the fuel preparation room, space and
area, hazardous zone / space / area, dry powder beside dry chemical powder. Every module was consistent
with itself, so no per-module check could see it: it needs the whole course read together.

THE SYNONYM LIST
A JSON object, one key per PREFERRED term, its value the variants the course should not mix with it:

    {"LEL": ["LFL"], "bunkering station": ["bunker station"]}

The factory's defaults are in course-factory/knowledge/terms-default.json (the five pairs above). The
course's own list is working_claude/terms.json (or --terms FILE): its entries add to the defaults, an
entry with the same preferred term replaces the default one, and an empty list drops it. Keys starting
with "_" are comments. Matching is whole-word, case-insensitive, a plural s / es is the same word.

WHAT IT READS
The approved content scripts working_claude/script/M*.json and FINAL.json (every string a trainee or the
instructor can meet - not the sources, hashes or picture briefs). A module with no approved script - a
retrofit - is read from its built pages (modules/*/ .html, not instructor/ or old/). --from scripts|pages
forces one; --from both reads both.

WHAT IT REPORTS
For each group: every form that is used, how often, and where (module, slide). MIXED when the course uses
more than one form of a group; a group with only one form used is consistent and is not listed. A REPORT,
never a build block: some pairs are legitimate in one place (a hazardous "zone 1" inside a hazardous
"area"), so the operator decides which form the course keeps. Exit 0 always, 1 only with --strict.
"""

import argparse
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DEFAULTS = Path(__file__).resolve().parents[2] / "knowledge" / "terms-default.json"
# what is not words a reader meets: the record around the script, the picture brief, the source quotes
SKIP_KEYS = {"module", "course_language", "operator_language", "status", "minutes_allocated",
             "operator_facts", "sources", "docx_hash", "approved_despite_findings", "approved_by",
             "approved_on", "approved_hash", "approved_checks", "kind", "layout", "visual_kind", "visual",
             "from_old", "sub_ilo", "minutes", "mechanic", "figure", "template"}
SKIP_DIRS = {"instructor", "old", "_build", "_course_shell", "assets"}
COMMENT = re.compile(r"<!--.*?-->", re.S)
TAG = re.compile(r"<(script|style)[^>]*>.*?</\1>", re.S | re.I)
STRIP = re.compile(r"<[^>]+>")
SECTION = re.compile(r"<section\b[^>]*?\bid=[\"']([^\"']+)[\"'][^>]*>", re.I)


def load_terms(extra=None):
    """The merged list: {preferred: [variants]} - defaults, then the course's own on top."""
    out = {}
    for p in (DEFAULTS, extra):
        if not p or not Path(p).is_file():
            continue
        d = json.loads(Path(p).read_text(encoding="utf-8"))
        for k, v in d.items():
            if k.startswith("_"):
                continue
            for old in [o for o in out if o.lower() == k.lower()]:
                del out[old]
            if v:
                out[k] = [str(x) for x in v]
    return out


def pattern(term):
    """Whole word(s), any run of white space between the words, a plural s / es ignored."""
    return re.compile(r"(?<![\w])" + r"\s+".join(re.escape(w) for w in term.split()) + r"(?:e?s)?(?![\w])", re.I)


def count_forms(text, forms):
    """{form: n} for one text. Longest form first, each match blanked, so a form that sits inside a longer one of the
    same group (a user's "gas room" beside "gas room door") is not counted twice."""
    n = {}
    for f in sorted(forms, key=len, reverse=True):
        text, k = pattern(f).subn(" ", text)
        if k:
            n[f] = k
    return n


def script_chunks(path):
    """(location, text) for every string of an approved script, located by the nearest enclosing id."""
    d = json.loads(path.read_text(encoding="utf-8"))
    tag = path.stem

    def walk(o, loc):
        if isinstance(o, dict):
            here = "%s %s" % (tag, o["id"]) if isinstance(o.get("id"), str) and o["id"] else loc
            for k, v in o.items():
                if k not in SKIP_KEYS:
                    yield from walk(v, here)
        elif isinstance(o, list):
            for v in o:
                yield from walk(v, loc)
        elif isinstance(o, str):
            yield loc, o
    yield from walk(d, tag)


def page_chunks(path, root):
    """(location, text) for a built page: its visible words, split at each <section id=...>."""
    raw = path.read_text(encoding="utf-8", errors="replace")
    raw = STRIP.sub(" ", TAG.sub(" ", COMMENT.sub(" ", SECTION.sub(lambda m: "\0" + m.group(1) + "\0", raw))))
    parts = raw.split("\0")
    rel = path.relative_to(root).as_posix()
    yield rel, parts[0]
    for i in range(1, len(parts) - 1, 2):
        yield "%s %s" % (rel, parts[i]), parts[i + 1]


def sources(course, mode):
    """Every (location, text) the course says, by `mode`: auto = the approved scripts, and the built pages of a
    module that has none."""
    course = Path(course)
    work = course / "working_claude"
    scripts = {}
    for p in sorted((work / "script").glob("*.json")) if (work / "script").is_dir() else []:
        if re.fullmatch(r"(M\d+|FINAL)", p.stem):
            try:
                d = json.loads(p.read_text(encoding="utf-8"))
            except ValueError:
                continue
            if d.get("status") == "approved":
                scripts[p.stem] = p
    pages = {}
    mods = course / "modules"
    for f in sorted(mods.rglob("*.html")) if mods.is_dir() else []:
        rel = f.relative_to(mods).parts
        if len(rel) < 2 or rel[0].startswith("_") or any(x in SKIP_DIRS or x.startswith("_") for x in rel[1:-1]) or "gb_review" in f.name:
            continue
        m = re.fullmatch(r"module(\d+)", rel[0])
        pages.setdefault("M%02d" % int(m.group(1)) if m else rel[0], []).append(f)
    # the final test's script is FINAL.json, its pages are the assessment/ folder of the last module (IGF: module16): one
    # text, read once (2.63.2: check_numbers.py counted its answers twice, from the script and from the page)
    if mode == "auto" and "FINAL" in scripts:
        loose = sorted(t for t in pages if t not in scripts and re.fullmatch(r"M\d+", t))
        if loose:
            pages[loose[-1]] = [f for f in pages[loose[-1]] if f.parent.name != "assessment"]
    out = []
    if mode in ("scripts", "both", "auto"):
        for tag, p in scripts.items():
            out.extend(script_chunks(p))
    for tag, fs in pages.items():
        if mode == "both" or mode == "pages" or (mode == "auto" and tag not in scripts):
            for f in fs:
                out.extend(page_chunks(f, mods))
    return out


def analyse(course, terms, mode="auto"):
    """[{preferred, forms: {form: {"count", "where": {location: n}}}, mixed}] for every group that is used at all."""
    chunks = sources(course, mode)
    report = []
    for pref, variants in terms.items():
        forms = [pref] + [v for v in variants if v.lower() != pref.lower()]
        used = {}
        for loc, text in chunks:
            for f, n in count_forms(text, forms).items():
                u = used.setdefault(f, {"count": 0, "where": {}})
                u["count"] += n
                u["where"][loc] = u["where"].get(loc, 0) + n
        if used:
            report.append({"preferred": pref, "forms": used, "mixed": len(used) > 1})
    return report


def modules_of(where):
    """The modules a form is used in, in order: 'M02 s05' -> M02, 'module07/presentation/index.html s03' -> M07."""
    seen = []
    for loc in where:
        m = re.match(r"M(\d+)|module(\d+)|FINAL", loc)
        tag = ("M%02d" % int(m.group(1) or m.group(2))) if m and (m.group(1) or m.group(2)) else (m.group(0) if m else loc.split()[0])
        if tag not in seen:
            seen.append(tag)
    return sorted(seen)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("course", help="the course folder (it has working_claude/ and modules/)")
    ap.add_argument("--terms", help="a synonym list; default <course>/working_claude/terms.json when it exists")
    ap.add_argument("--from", dest="mode", choices=("auto", "scripts", "pages", "both"), default="auto")
    ap.add_argument("--strict", action="store_true", help="exit 1 when any group is mixed")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    course = Path(a.course)
    own = Path(a.terms) if a.terms else course / "working_claude" / "terms.json"
    terms = load_terms(own)
    rep = analyse(course, terms, a.mode)
    mixed = [r for r in rep if r["mixed"]]

    if a.json:
        print(json.dumps({"groups": len(terms), "report": rep}, ensure_ascii=False, indent=1))
        return 1 if (mixed and a.strict) else 0

    print("=" * 72)
    print("check_terms - one thing, one name, across the whole course")
    print("=" * 72)
    print("\n%d synonym group(s) (factory defaults%s)\n" % (len(terms), " + " + own.as_posix() if own.is_file() else ""))
    for r in mixed:
        print("MIXED  %s   (preferred)" % r["preferred"])
        for f, u in sorted(r["forms"].items(), key=lambda kv: (kv[0].lower() != r["preferred"].lower(), -kv[1]["count"])):
            locs = sorted(u["where"])
            show = ", ".join(locs[:6]) + (" ... +%d more" % (len(locs) - 6) if len(locs) > 6 else "")
            print("   %-26s %4d x  in %s: %s" % (f, u["count"], ", ".join(modules_of(u["where"])), show))
        print()
    if not mixed:
        print("No group is used under more than one name.")
    else:
        print("%d group(s) mixed. A report, not a failure: the operator picks the form the course keeps" % len(mixed))
        print("(some pairs are right in one place - a hazardous \"zone 1\" inside a hazardous \"area\"); the")
        print("script is changed by content_script.py propose, never by hand, and the module rebuilt.")
    return 1 if (mixed and a.strict) else 0


if __name__ == "__main__":
    sys.exit(main())
