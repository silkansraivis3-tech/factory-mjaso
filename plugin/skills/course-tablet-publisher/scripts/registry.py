#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Regenerate the installed-course registry from the course packs themselves.

The collision problem this solves
---------------------------------
Several colleagues publish different courses at the same time. If each of them
hand-edits one shared list, they conflict on that file every time. So the list
is not hand-edited: each course owns exactly one file nobody else touches
(`courses/<id>/course.json`), and this script DERIVES the shared registry by
scanning them.

That makes the shared file conflict-free in practice: two colleagues who both
regenerate it produce identical bytes, because the output is sorted by course
id and formatted deterministically. If git still reports a conflict on it -
because both added a course in the same region - the resolution is never to
merge the text by hand. Take either side, run this script again, commit the
result. The generator is the truth; the file is a cache of it.

Output format is a plain JS global, matching how every other registry on this
platform is loaded (GB_TASKS, IT_MODULES, IT_RUN). A .json file fetched at
runtime would be a second mechanism, and an offline WebView is a bad place to
introduce one.

Usage
-----
    registry.py --repo <android project> [--write] [--check]

Default is a dry run that prints the registry it would write. `--write`
writes it. `--check` exits non-zero if the file on disk is out of date, which
is the useful thing to run in a validation pass.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PLATFORM = os.path.join(os.path.dirname(HERE), "knowledge", "platform.json")

HEADER = """/* ==========================================================================
   NOVIKONTAS tablet platform - INSTALLED COURSES

   GENERATED FILE - DO NOT HAND-EDIT.
   Written by the course-tablet-publisher skill (scripts/registry.py) by
   scanning courses/<id>/course.json. Regenerate after adding, removing or
   re-versioning a course:

       python registry.py --repo <android project> --write

   On a merge conflict here: do not merge the text. Take either side, run the
   generator again, commit what it writes.

   Consumed by: nothing yet. The two terminals still carry their course
   identity in code (gb_config.js, it_auth.js and the module lists beside
   them). This file is the data those should read, and the publisher writes it
   from today so the wiring is a small change later rather than an archaeology
   project. See the skill's references/course-package.md.
   ========================================================================== */
"""


def load_platform(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def collect(repo: str, plat: dict) -> list[dict]:
    """One entry per courses/<id>/course.json, plus any legacy course the
    platform file declares - a registry that omitted the course actually
    installed today would be a lie."""
    out = []
    tr = os.path.join(repo, plat["asset_roots"]["trainee"].replace("/", os.sep), "courses")
    if os.path.isdir(tr):
        for cid in sorted(os.listdir(tr)):
            cj = os.path.join(tr, cid, "course.json")
            if not os.path.isfile(cj):
                continue
            with open(cj, "r", encoding="utf-8") as fh:
                meta = json.load(fh)
            out.append({
                "id": meta.get("id", cid),
                "title": meta.get("title", cid),
                "version": meta.get("version", "0.0.0"),
                "status": meta.get("status", "draft"),
                "modules": meta.get("modules"),
                "layout": "pack",
                "trainee": "courses/" + cid + "/",
                "instructor": "courses/" + cid + "/",
            })
    for cid, leg in sorted((plat.get("legacy_courses") or {}).items()):
        if any(e["id"] == cid for e in out):
            continue
        out.append({
            "id": cid,
            "title": leg.get("title", cid),
            "version": leg.get("version", "0.0.0"),
            "status": leg.get("status", "released"),
            "modules": leg.get("modules"),
            "layout": "legacy",
            "trainee": "",
            "instructor": "",
        })
    return sorted(out, key=lambda e: e["id"])


def render(entries: list[dict]) -> str:
    body = ",\n".join("  " + json.dumps(e, ensure_ascii=False, sort_keys=True) for e in entries)
    return HEADER + "window.GB_COURSES = [\n" + body + "\n];\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo", required=True)
    ap.add_argument("--platform", default=PLATFORM)
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--check", action="store_true",
                    help="exit non-zero if the file on disk is not what the packs say")
    a = ap.parse_args(argv)

    repo = os.path.abspath(a.repo)
    plat = load_platform(a.platform)
    entries = collect(repo, plat)
    text = render(entries)

    target = os.path.join(repo, plat["asset_roots"]["trainee"].replace("/", os.sep),
                          "courses", "registry.js")
    current = ""
    if os.path.isfile(target):
        with open(target, "r", encoding="utf-8") as fh:
            current = fh.read()

    print(f"{len(entries)} course(s): " + ", ".join(
        f"{e['id']} {e['version']} ({e['layout']})" for e in entries))

    if a.check:
        if current.replace("\r\n", "\n") != text:
            print("OUT OF DATE: " + os.path.relpath(target, repo)
                  + "\n  regenerate with --write")
            return 1
        print("up to date")
        return 0

    if a.write:
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
        print("written: " + os.path.relpath(target, repo))
    else:
        print("\n--- dry run, would write " + os.path.relpath(target, repo) + " ---")
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
