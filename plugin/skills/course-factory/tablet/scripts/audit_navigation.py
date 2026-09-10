#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Can a person actually GET to every page, and get back out of it?

`verify_links.py` answers "does every link resolve". That is not the same
question. A page can have perfect links and be reachable from nothing, and a
whole section can sit in the build with no door into it. On GAS BASIC that was
28 pages - the safety briefs, rotation plans, entry permit, first-aid card and
every practical write-up for four modules. Its own index linked them all
correctly, so `verify_links.py` was green. Nothing linked the index.

TWO THINGS THIS HAS TO MODEL, and both caught me out the first time.

1  ONE MERGED ASSET ROOT. Gradle merges the flavour source sets, so at runtime
   the terminals are siblings. A page living in one flavour and opened from the
   other is one tap away in the shipped app and looks unreachable if you audit
   a flavour at a time. Pass every `--assets` root, as with verify_links.py.

2  NAVIGATION IS BUILT IN JAVASCRIPT. A front door that renders its cards from
   a manifest has no <a href> to follow. Walking only href= reported an entire
   terminal as unreachable - a fact about the walk, not the course. So any
   .html string inside a terminal's own .js counts as an edge from that
   terminal's front door. Paths BUILT by concatenation ('plans/MODULE_0' + n +
   '_PLAN.html') cannot be seen by any static tool; those show up as orphans
   and are reported as UNVERIFIABLE rather than dead.

A page may legitimately have no way back: a deck-driven page, or a final
assessment nobody should wander out of. It has to SAY so. The convention this
course family uses is an hrefless element carrying the home id - the run script
reads the href off it and does nothing when there is none - and that is the
difference between a decision and an oversight.

Usage
-----
    audit_navigation.py --assets app/src/main/assets \\
                        --assets app/src/instructor/assets
    audit_navigation.py --assets <dir> [--assets <dir> ...]
                        [--front <relpath> ...] [--learner-prefix <name>]
                        [--code-pattern <regex>] [--max-depth N] [--quiet]

--front            a front-door page, relative to the merged root. Repeat.
                   Default: every `<top-level>/index.html`.
--learner-prefix   top-level folder whose pages a TRAINEE sees. Repeat.
                   Those pages are checked for outcome/administrative codes.
--code-pattern     what counts as an administrative code on a learner page.
                   Default catches ILO / sub-ILO / learning-outcome numbering.
--max-depth        taps from a front door before a page counts as buried (3).

Exit codes: 0 clean · 1 dead ends or buried pages · 2 bad input
"""
import argparse
import collections
import pathlib
import re
import sys
import urllib.parse

HREF = re.compile(r'(?:href|src)\s*=\s*["\']([^"\']+)["\']', re.I)
JSHTML = re.compile(r"""["']([A-Za-z0-9_./\-]+\.html)["']""")
# an element that declares "no way back on purpose": carries a home/deck id and
# has no href of its own
DECLARED = re.compile(r'<(?!a\b)[a-z]+[^>]*\bid=["\'](?:gb-home|gb-deck|home|back)["\'][^>]*>',
                      re.I)
BACKISH = re.compile(r'id=["\'](?:gb-home|gb-deck)["\']|'
                     r'class=["\'][^"\']*(?:gb-back|topback|it-back|\bback\b|\bhome\b)', re.I)
# Courses name their outcomes differently - ILO, sub-ILO, "Main learning
# outcome 1", "sub-outcome 1.2". All of it is administrative numbering and none
# of it is subject matter. GAS BASIC used three spellings, and a pattern
# covering only the first left five pages still carrying the mapping after a
# strip that was reported as complete.
DEFAULT_CODE = (r"\bsub-?ILOs?\b|\bMain ILOs?\b|\bILO\s*\d"
                r"|\b(?:main|sub)[- ]?outcomes?\s*(?:<[^>]+>)?\s*\d"
                r"|\blearning outcome\s*(?:<[^>]+>)?\s*\d")


def strip(s):
    s = re.sub(r"<!--.*?-->", " ", s, flags=re.S)
    s = re.sub(r"<(script|style)\b.*?</\1>", " ", s, flags=re.S | re.I)
    return s


def visible(s):
    return re.sub(r"<[^>]+>", " ", strip(s))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--assets", action="append", required=True,
                    help="an asset source-set root; repeat for each flavour")
    ap.add_argument("--front", action="append", default=None)
    ap.add_argument("--learner-prefix", action="append", default=None)
    ap.add_argument("--code-pattern", default=DEFAULT_CODE)
    ap.add_argument("--max-depth", type=int, default=3)
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()

    roots = [pathlib.Path(x) for x in a.assets]
    for r in roots:
        if not r.is_dir():
            print("INPUT ERROR: not a directory: %s" % r)
            sys.exit(2)

    # ---- the merged view: first root wins, as Gradle's priority does --------
    merged = {}
    for root in roots:
        for p in root.rglob("*"):
            if not p.is_file() or p.suffix.lower() not in (".html", ".js"):
                continue
            if ".bak" in p.name or "node_modules" in p.parts:
                continue
            merged.setdefault(p.relative_to(root).as_posix(), p)

    html = {r: p for r, p in merged.items() if r.endswith(".html")}
    js = {r: p for r, p in merged.items() if r.endswith(".js")}
    if not html:
        print("INPUT ERROR: no .html found under the given roots")
        sys.exit(2)
    text = {r: p.read_text(encoding="utf-8", errors="replace") for r, p in merged.items()}

    terminals = sorted({r.split("/")[0] for r in html if "/" in r})
    fronts = a.front or [f for f in ("%s/index.html" % t for t in terminals) if f in html]
    fronts = [f for f in fronts if f in html]
    if not fronts:
        print("INPUT ERROR: no front door found; pass --front")
        sys.exit(2)

    print("merged root: %d html + %d js from %d source set(s)" % (len(html), len(js), len(roots)))
    print("terminals:   %s" % ", ".join(terminals))
    print("front doors: %s" % ", ".join(fronts))

    def resolve(frm, raw):
        raw = urllib.parse.unquote(raw.split("#")[0].split("?")[0])
        if not raw or not raw.endswith(".html"):
            return None
        if raw.startswith(("http", "mailto:", "data:", "javascript:")):
            return None
        base = pathlib.PurePosixPath(frm).parent
        cand = raw.lstrip("/") if raw.startswith("/") else str(base / raw)
        parts = []
        for seg in pathlib.PurePosixPath(cand).parts:
            if seg == "..":
                if parts:
                    parts.pop()
            elif seg != ".":
                parts.append(seg)
        r = "/".join(parts)
        return r if r in html else None

    edges = collections.defaultdict(set)
    for r in html:
        # NOT strip(): a page that writes '<a href="x.html">' from a script is
        # still opening x.html. Stripping scripts first cost 29 reachable pages
        # the first time this ran.
        for raw in HREF.findall(text[r]):
            t = resolve(r, raw)
            if t and t != r:
                edges[r].add(t)
    # a terminal's own scripts wire its front door
    for jr in js:
        term = jr.split("/")[0]
        for front in fronts:
            if front.split("/")[0] != term:
                continue
            for raw in JSHTML.findall(text[jr]):
                t = resolve(jr, raw) or (raw if raw in html else None)
                if t and t != front:
                    edges[front].add(t)

    # ---- 1 reachability ----------------------------------------------------
    seen = set(fronts)
    depth = {f: 0 for f in fronts}
    queue = list(fronts)
    while queue:
        cur = queue.pop(0)
        for nxt in sorted(edges.get(cur, ())):
            if nxt not in seen:
                seen.add(nxt)
                depth[nxt] = depth[cur] + 1
                queue.append(nxt)
    orphans = sorted(set(html) - seen)

    print("\n1 - reachability")
    print("    pages %d   reachable %d   not reached %d" % (len(html), len(seen), len(orphans)))
    # A page whose NAME is assembled in JavaScript cannot be seen by any static
    # walk: 'plans/MODULE_0' + n + '_PLAN.html' is a working door that looks
    # like an orphan. Report those separately rather than sending someone to
    # "fix" navigation that already works. The test: replace the digits in the
    # filename with \d+ and look for that shape in any script.
    computed, real = [], []
    for o in orphans:
        name = pathlib.PurePosixPath(o).name
        shape = re.sub(r"\d+", r"\\d+", re.escape(name))
        head = re.escape(re.split(r"\d", name)[0])
        assembled = any(
            re.search(shape, text[f]) or
            (len(head) > 3 and re.search(head + r"\d*['\"]?\s*\+", text[f]))
            for f in merged)
        (computed if assembled else real).append(o)
    for o in real:
        print("       NOT REACHED   %s" % o)
    for o in computed:
        print("       UNVERIFIABLE  %s   (its path looks assembled in JavaScript)" % o)

    # ---- 2 a way back ------------------------------------------------------
    has, declared, none = [], [], []
    for r in sorted(html):
        if r in fronts:
            continue
        s = text[r]
        if DECLARED.search(s):
            declared.append(r)
        elif BACKISH.search(s):
            has.append(r)
        else:
            none.append(r)
    print("\n2 - a way back")
    print("    has a back or home control      %d" % len(has))
    print("    DECLARES none, on purpose       %d" % len(declared))
    print("    neither - real dead ends        %d" % len(none))
    for r in none:
        print("       DEAD END  %s" % r)

    # ---- 3 depth -----------------------------------------------------------
    print("\n3 - depth from a front door")
    dist = collections.Counter(depth.values())
    for d in sorted(dist):
        print("    %d tap(s)  %3d page(s)" % (d, dist[d]))
    buried = sorted((r for r, v in depth.items() if v > a.max_depth), key=lambda x: -depth[x])
    if buried:
        print("    deeper than %d taps:" % a.max_depth)
        for r in buried:
            print("       %d  %s" % (depth[r], r))

    # ---- 4 one mechanism per folder ---------------------------------------
    print("\n4 - navigation mechanism, by section")
    kinds = collections.defaultdict(collections.Counter)
    for r in sorted(html):
        parts = r.split("/")
        folder = "/".join(parts[:2]) if len(parts) > 2 else parts[0]
        s = text[r]
        k = ("declares none" if DECLARED.search(s)
             else "back control" if BACKISH.search(s) else "NONE")
        kinds[folder][k] += 1
    mixed = 0
    for folder in sorted(kinds):
        tot = sum(kinds[folder].values())
        mix = ", ".join("%s %d" % (k, v) for k, v in kinds[folder].most_common())
        flag = ""
        if len(kinds[folder]) > 2:
            mixed += 1
            flag = "   <- %d mechanisms in one section" % len(kinds[folder])
        if not a.quiet or flag:
            print("    %-38s %3d  %s%s" % (folder[:38], tot, mix, flag))

    # ---- 5 administrative codes on learner pages ---------------------------
    code = re.compile(a.code_pattern, re.I)
    prefixes = a.learner_prefix or [t for t in terminals if "train" in t or "learn" in t]
    print("\n5 - outcome codes on learner-facing pages")
    if not prefixes:
        print("    no learner prefix given or guessed - skipped "
              "[VERIFY: pass --learner-prefix]")
        hits = []
    else:
        print("    learner sections: %s" % ", ".join(prefixes))
        hits = []
        for r in sorted(html):
            if not any(r.startswith(p + "/") for p in prefixes):
                continue
            n = len(code.findall(visible(text[r])))
            if n:
                hits.append((r, n))
        if hits:
            print("    %d page(s), %d mention(s) a trainee can read:"
                  % (len(hits), sum(n for _, n in hits)))
            for r, n in sorted(hits, key=lambda x: -x[1]):
                print("       x%-3d %s" % (n, r))
            print("    These are administrative labels, not subject matter. Removing them")
            print("    changes no technical word - and the instructor's own terminal is where")
            print("    the mapping belongs.")
        else:
            print("    none  OK")

    print("\n" + "=" * 72)
    # Depth is ADVISORY. A page four taps down is worth knowing about, but it is
    # a judgement about the shape of the course, not a defect - an instructor's
    # printed card living under a module's practicals folder is deep and right.
    # Only pages nothing can reach, and dead ends that do not declare
    # themselves, fail this check.
    if buried:
        print("ADVISORY: %d page(s) more than %d taps deep - read them, they are not failures."
              % (len(buried), a.max_depth))
    bad = len(none) + len(real)
    if bad:
        if real:
            print("%d page(s) reachable from nothing. A section whose own index is not linked"
                  % len(real))
            print("is invisible in the built app however good its own links are.")
        if none:
            print("%d dead end(s): no way back and no declaration that this is deliberate."
                  % len(none))
        sys.exit(1)
    print("every page is reachable, every page has a way back or declares it has none")
    if hits:
        print("(outcome codes on learner pages are reported above and are not a failure)")
    sys.exit(0)


if __name__ == "__main__":
    main()
