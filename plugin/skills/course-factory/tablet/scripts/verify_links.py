#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Resolve every link the way the BUILT app sees it: source sets merged.

Why this exists: Gradle merges the flavour source sets into one asset root, so
at runtime the trainee and instructor terminals are siblings. A cross-terminal
link written for that root does not resolve in the split source tree - so a
CORRECT link looks dead, and "fixing" it breaks it. Checking one source set at
a time reported 39 dead links on a tree whose real count was zero.

This builds a read-only merged VIEW (a map of asset path -> real file). Nothing
is copied and nothing is written.

Usage
-----
    verify_links.py --assets app/src/main/assets --assets app/src/instructor/assets
    verify_links.py --assets <dir> [--assets <dir> ...] [--anchors] [--quiet]

--anchors also checks that a link's #fragment exists as an id in the target.
          Off by default: many pages route their own hash in JavaScript, so a
          missing id is not automatically a defect.

Exit codes: 0 no dead links · 1 dead links found · 2 bad input
"""
import argparse
import os
import pathlib
import re
import sys
from urllib.parse import unquote

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# An ATTRIBUTE, not a JavaScript assignment. `href\s*=` also matches
# `window.location.href = "plans/MODULE_0" + n + ".html"`, which reported a
# truncated path as a dead link. An attribute has no space before the `=`.
LINK = re.compile(r'(?:href|src)=\s*"([^"]+)"', re.I)
SKIP_PREFIX = ("#", "http://", "https://", "//", "data:", "mailto:", "tel:",
               "javascript:", "blob:")
# a JS template concatenation caught by the attribute regex, e.g. src="' + x + '"
TEMPLATE = re.compile(r"[\"']?\s*\+|\+\s*[\"']?|\$\{")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--assets", action="append", required=True,
                    help="an asset source-set root; repeat for each flavour")
    ap.add_argument("--anchors", action="store_true")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()

    roots = [pathlib.Path(x) for x in a.assets]
    for r in roots:
        if not r.is_dir():
            print("INPUT ERROR: not a directory: %s" % r)
            sys.exit(2)

    # ---- the merged view: asset-root-relative posix path (lowered) -> real file
    merged = {}
    for root in roots:
        for dp, dn, fn in os.walk(root):
            for f in fn:
                p = pathlib.Path(dp) / f
                key = p.relative_to(root).as_posix()
                merged.setdefault(key.lower(), p)

    print("merged asset root: %d file(s) from %d source set(s)" % (len(merged), len(roots)))
    print("top level: %s" % ", ".join(sorted({k.split("/")[0] for k in merged})))

    def resolve(from_key, href):
        base = pathlib.PurePosixPath(from_key).parent
        parts = []
        for seg in (base / unquote(href)).as_posix().split("/"):
            if seg in ("", "."):
                continue
            if seg == "..":
                if not parts:
                    return None          # escaped the asset root
                parts.pop()
            else:
                parts.append(seg)
        return "/".join(parts)

    dead, templates, anchors = {}, {}, {}
    checked = 0
    for key, real in sorted(merged.items()):
        if not key.endswith((".html", ".htm")):
            continue
        s = real.read_text(encoding="utf-8", errors="replace")
        for m in LINK.finditer(s):
            href = m.group(1).strip()
            if not href or href.startswith(SKIP_PREFIX):
                continue
            if TEMPLATE.search(href):
                templates.setdefault(href[:60], []).append(key)
                continue
            checked += 1
            path = href.split("#")[0].split("?")[0]
            frag = href.split("#")[1] if "#" in href else None
            if not path:
                continue
            r = resolve(key, path)
            if r is None or r.lower() not in merged:
                dead.setdefault(href, []).append(key)
                continue
            if a.anchors and frag:
                t = merged[r.lower()].read_text(encoding="utf-8", errors="replace")
                if not re.search(r'(?:id|name)\s*=\s*["\']%s["\']' % re.escape(frag), t):
                    anchors.setdefault("%s#%s" % (r, frag), []).append(key)

    print("\nlinks checked: %d" % checked)
    print("DEAD: %d distinct target(s)" % len(dead))
    for href, srcs in sorted(dead.items()):
        print("   %-62s  from %s%s" % (href[:62], srcs[0],
                                       "  +%d" % (len(srcs) - 1) if len(srcs) > 1 else ""))

    if templates and not a.quiet:
        print("\nskipped - built in JavaScript, not static links: %d" % len(templates))
        for h, srcs in sorted(templates.items())[:6]:
            print("   %-62s  e.g. %s" % (h[:62], srcs[0]))

    if a.anchors:
        print("\nlinks whose #anchor is not an id in the target: %d" % len(anchors))
        for k, srcs in sorted(anchors.items())[:20]:
            print("   %-62s  from %s" % (k[:62], srcs[0]))
        print("   (not automatically a defect - a page may route its own hash in JS)")

    print("\n" + "=" * 72)
    if dead:
        print("%d dead link target(s). A link into the other terminal is written relative to"
              % len(dead))
        print("the MERGED root - if one of those is listed, check the hop count, not the file.")
        sys.exit(1)
    print("every static link resolves in the merged asset root")
    sys.exit(0)


if __name__ == "__main__":
    main()
