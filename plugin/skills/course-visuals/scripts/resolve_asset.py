#!/usr/bin/env python3
"""Run levels 1 and 2 of the asset pipeline mechanically.

  LEVEL 1  PROJECT  - source_files/, operator assets, the course's own assets
  LEVEL 2  FACTORY  - the plugin's resources/ library

Level 3 (internet) is judgement and belongs to the visual-sourcer agent.
Level 4 (create) is the outcome when 1-3 find nothing.

A level is exhausted only when it has been SEARCHED. This script expands the
query into the terms a search should actually try - plurals, hyphenation,
abbreviations, both spellings - because one failed grep for the requester's
phrasing is the commonest way an existing asset gets missed.

Exit codes
  0  at least one candidate found
  3  nothing found at levels 1-2 -> GENERATED_ASSET_REQUIRED (or level 3)
  2  bad usage

  python resolve_asset.py "LNG membrane cargo tank" --project <dir> [--factory <dir>] [--json]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".svg", ".webp", ".gif"}
DOC_EXT = {".pdf", ".md", ".txt", ".html", ".htm"}

# British <-> American pairs that actually bite in technical corpora.
SPELLING = [
    ("ise", "ize"), ("isation", "ization"), ("ised", "ized"), ("ising", "izing"),
    ("our", "or"), ("re", "er"), ("ll", "l"), ("ae", "e"), ("oe", "e"),
]

STOP = {"a", "an", "the", "of", "for", "and", "or", "in", "on", "at", "to",
        "with", "image", "photo", "photograph", "picture", "diagram", "need",
        "technically", "credible"}


def expand(query: str) -> list[str]:
    """The terms a real search would try, strongest first."""
    q = query.lower().strip()
    words = [w for w in re.split(r"[^a-z0-9]+", q) if w and w not in STOP]
    terms: list[str] = []

    def add(t: str) -> None:
        t = t.strip("_-")
        if t and t not in terms:
            terms.append(t)

    add(q)
    add("_".join(words))
    add("-".join(words))
    add("".join(words))
    for w in words:
        add(w)
        # plural / singular
        if w.endswith("s") and len(w) > 3:
            add(w[:-1])
        else:
            add(w + "s")
        # spelling variants, both directions
        for a, b in SPELLING:
            if w.endswith(a):
                add(w[: -len(a)] + b)
            if w.endswith(b):
                add(w[: -len(b)] + a)
    # abbreviation of the multi-word query
    if len(words) > 1:
        add("".join(w[0] for w in words))
    return terms


def score(name: str, terms: list[str], words: list[str]) -> int:
    """How well a filename matches. Whole-query hits beat single words."""
    n = name.lower()
    s = 0
    for i, t in enumerate(terms):
        if len(t) < 3:
            continue
        if t in n:
            s += max(1, 12 - i)
    hits = sum(1 for w in words if len(w) > 2 and w in n)
    if words and hits == len(words):
        s += 25          # every content word present
    elif hits:
        s += 4 * hits
    return s


def walk(root: str, want_docs: bool) -> list[str]:
    out = []
    skip = {".git", "__pycache__", "node_modules", ".venv", "oldversion",
            "_to_delete", "test_area"}
    for dp, dn, fn in os.walk(root):
        dn[:] = [d for d in dn if d not in skip and not d.startswith(".")]
        for f in fn:
            ext = os.path.splitext(f)[1].lower()
            if ext in IMAGE_EXT or (want_docs and ext in DOC_EXT):
                out.append(os.path.join(dp, f))
    return out


def meta_for(path: str) -> dict:
    """Provenance sitting beside the file, if any."""
    d = os.path.dirname(path)
    base = os.path.basename(path)
    for mf in ("_photo_meta.json", "_figure_meta.json"):
        p = os.path.join(d, mf)
        if os.path.isfile(p):
            try:
                with open(p, encoding="utf-8-sig") as fh:
                    data = json.load(fh)
                if base in data:
                    return {"meta_file": mf, **data[base]}
            except Exception:
                pass
    return {}


def search(root: str, level: int, label: str, terms: list[str],
           words: list[str], limit: int) -> list[dict]:
    if not root or not os.path.isdir(root):
        return []
    found = []
    for p in walk(root, want_docs=False):
        s = score(os.path.basename(p), terms, words)
        if s <= 0:
            continue
        m = meta_for(p)
        found.append({
            "level": level,
            "level_name": label,
            "path": p.replace("\\", "/"),
            "score": s,
            "rights_state": m.get("rights_state", "UNRECORDED"),
            "visually_verified": m.get("visually_verified", ""),
            "note": m.get("description") or m.get("shows") or "",
        })
    found.sort(key=lambda c: -c["score"])
    return found[:limit]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("query")
    ap.add_argument("--project", action="append", default=[],
                    help="project root to search at LEVEL 1 (repeatable)")
    ap.add_argument("--factory", default=None,
                    help="factory resources root for LEVEL 2; defaults to the "
                         "plugin's resources/ relative to this script")
    ap.add_argument("--limit", type=int, default=5)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    terms = expand(a.query)
    words = [w for w in re.split(r"[^a-z0-9]+", a.query.lower()) if w and w not in STOP]

    factory = a.factory
    if factory is None:
        here = os.path.dirname(os.path.abspath(__file__))
        # scripts/ -> course-visuals/ -> skills/ -> plugin root
        factory = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(here))),
                               "resources")

    cands: list[dict] = []
    for root in a.project:
        cands += search(root, 1, "PROJECT", terms, words, a.limit)
    if not cands:
        cands += search(factory, 2, "FACTORY", terms, words, a.limit)

    blocked = [c for c in cands if c["rights_state"] == "RIGHTS_REVIEW_REQUIRED"]
    usable = [c for c in cands if c["rights_state"] != "RIGHTS_REVIEW_REQUIRED"]
    outcome = "FOUND" if usable else "GENERATED_ASSET_REQUIRED"

    result = {
        "query": a.query,
        "terms_tried": terms,
        "levels_searched": (["1 PROJECT"] if a.project else [])
                           + (["2 FACTORY"] if not [c for c in cands if c["level"] == 1] else []),
        "outcome": outcome,
        "candidates": usable,
        "blocked_by_rights": blocked,
    }

    if a.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print("=" * 72)
        print("asset resolve: " + a.query)
        print("=" * 72)
        print("  terms tried    : " + ", ".join(terms[:14]) +
              (" …" if len(terms) > 14 else ""))
        print("  levels searched: " + ", ".join(result["levels_searched"] or ["(none - no root given)"]))
        print()
        if usable:
            for c in usable:
                print("  LEVEL %d %-8s %s" % (c["level"], c["level_name"], c["path"]))
                print("      score=%-4d rights=%s" % (c["score"], c["rights_state"]))
                if c["note"]:
                    print("      %s" % c["note"][:90])
        if blocked:
            print()
            for c in blocked:
                print("  BLOCKED  RIGHTS_REVIEW_REQUIRED  " + c["path"])
        print()
        print("=" * 72)
        if usable:
            print("%d candidate(s). Levels 1-2 answered - do not search the internet." % len(usable))
        else:
            print("GENERATED_ASSET_REQUIRED")
            print("Nothing at levels 1-2. Try level 3 (visual-sourcer agent) before creating;")
            print("if level 3 also fails, write the brief in")
            print("source/schemas/GENERATED_ASSET_BRIEF.md - every field, especially")
            print("'forbidden inaccuracies'.")
    return 0 if usable else 3


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(2)
