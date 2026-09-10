#!/usr/bin/env python3
"""Provenance and rights, checked against the schemas.

Every image in an asset folder has an entry beside it; every entry has its
required fields; visually_verified is real; rights states are valid; and
nothing ships at RIGHTS_REVIEW_REQUIRED.

  python check_assets.py <assets-dir> [...] [--strict] [--json]

Exit 0 clean (or warnings only) · 1 failures · 2 bad usage.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
SCHEMA_DIR = os.path.join(SKILL, "source", "schemas")

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".svg", ".webp", ".gif"}
META_FILES = {"_photo_meta.json": "photo", "_figure_meta.json": "figure"}

VALID_RIGHTS = {"CLEARED", "PROJECT_OWNED", "PUBLIC_DOMAIN",
                "ATTRIBUTION_REQUIRED", "RIGHTS_REVIEW_REQUIRED", "REJECTED"}

findings: list[dict] = []


def add(kind, where, msg, hint=""):
    findings.append({"kind": kind, "where": where, "message": msg, "hint": hint})


def fail(w, m, h=""): add("FAIL", w, m, h)
def warn(w, m, h=""): add("WARN", w, m, h)
def block(w, m, h=""): add("BLOCK", w, m, h)


def required_fields(kind: str) -> list[str]:
    path = os.path.join(SCHEMA_DIR,
                        "_photo_meta.schema.json" if kind == "photo"
                        else "_figure_meta.schema.json")
    try:
        with open(path, encoding="utf-8-sig") as fh:
            s = json.load(fh)
        return list(s.get("additionalProperties", {}).get("required", []))
    except Exception:
        return (["source", "rights_state", "description", "teaching_purpose",
                 "used_in", "visually_verified"] if kind == "photo" else
                ["origin", "rights_state", "shows", "teaching_purpose",
                 "used_in", "visually_verified"])


VERIFIED_OK = re.compile(r"^\s*yes\b", re.I)
HAS_DATE = re.compile(r"\d{4}-\d{2}-\d{2}|\d{1,2}\s+\w+\s+\d{4}")


def check_folder(folder: str) -> None:
    entries = [e for e in os.listdir(folder)]
    images = sorted(e for e in entries
                    if os.path.splitext(e)[1].lower() in IMAGE_EXT)
    metas = {m: os.path.join(folder, m) for m in META_FILES if m in entries}

    if not images:
        return

    rel = folder.replace("\\", "/")

    if not metas:
        fail(rel, f"{len(images)} image(s) and no provenance file",
             "add _photo_meta.json (photographs) or _figure_meta.json "
             "(drawings, figures, generated illustrations) beside the files")
        return

    described: dict[str, str] = {}
    for mname, mpath in metas.items():
        kind = META_FILES[mname]
        try:
            with open(mpath, encoding="utf-8-sig") as fh:
                data = json.load(fh)
        except Exception as exc:
            fail(rel + "/" + mname, f"unreadable or invalid JSON: {exc}")
            continue
        if not isinstance(data, dict):
            fail(rel + "/" + mname, "top level must be an object keyed by filename")
            continue

        req = required_fields(kind)
        for fname, meta in data.items():
            where = f"{rel}/{mname}:{fname}"
            if not isinstance(meta, dict):
                fail(where, "entry is not an object")
                continue
            described[fname] = mname

            if not os.path.isfile(os.path.join(folder, fname)):
                warn(where, "entry describes a file that is not here",
                     "an orphan entry means a file was moved or renamed")

            missing = [f for f in req if f not in meta or meta[f] in ("", None)]
            if missing:
                fail(where, "missing required field(s): " + ", ".join(missing),
                     "schema: source/schemas/" +
                     ("_photo_meta.schema.json" if kind == "photo"
                      else "_figure_meta.schema.json"))

            rs = meta.get("rights_state")
            if rs is None:
                pass  # already reported as missing
            elif rs not in VALID_RIGHTS:
                fail(where, f'rights_state "{rs}" is not valid',
                     "one of: " + ", ".join(sorted(VALID_RIGHTS)))
            elif rs == "RIGHTS_REVIEW_REQUIRED":
                block(where, "RIGHTS_REVIEW_REQUIRED - this asset must not ship",
                      "the owner decides; an uncleared publisher figure has "
                      "blocked a whole course in this system before")
            elif rs == "REJECTED":
                warn(where, "rights_state REJECTED but the file is still here",
                     "remove the file, or keep only the entry as a record")

            if rs == "ATTRIBUTION_REQUIRED" and not (
                    meta.get("author") or meta.get("attribution_required")):
                warn(where, "ATTRIBUTION_REQUIRED with no author recorded",
                     "the credit line has to say something")

            vv = str(meta.get("visually_verified", ""))
            if vv:
                if not VERIFIED_OK.match(vv):
                    warn(where, f'visually_verified does not start with yes: "{vv[:50]}"',
                         "that is a legitimate answer - it means somebody must still look")
                elif not HAS_DATE.search(vv):
                    warn(where, "visually_verified says yes but carries no date",
                         "'yes - <what was seen> <date>'; never yes for a file nobody opened")

            if kind == "figure":
                origin = meta.get("origin", "")
                if origin == "generated illustration":
                    for f in ("generated_by", "depicts_what_no_photograph_can"):
                        if not meta.get(f):
                            fail(where, f"generated illustration without {f}")
                    if meta.get("declared_as_drawing_on_page") is not True:
                        fail(where, "generated illustration not declared as a drawing on its page",
                             "a generated image presented as a photograph is a lie "
                             "the learner cannot detect")
                if origin in ("publisher figure", "source technical drawing",
                              "manufacturer diagram") and not meta.get("source_document"):
                    warn(where, f'{origin} without source_document')

    for img in images:
        if img not in described:
            fail(f"{rel}/{img}", "image with no provenance entry",
                 "every asset carries provenance beside it (law L12)")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("targets", nargs="+")
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    folders: set[str] = set()
    for t in a.targets:
        if not os.path.isdir(t):
            print("not a directory: " + t)
            return 2
        for dp, dn, fn in os.walk(t):
            dn[:] = [d for d in dn if d not in (".git", "__pycache__", "oldversion")]
            if any(os.path.splitext(f)[1].lower() in IMAGE_EXT for f in fn):
                folders.add(dp)

    if not folders:
        print("no image folders found in: " + ", ".join(a.targets))
        return 0

    for f in sorted(folders):
        check_folder(f)

    fails = [x for x in findings if x["kind"] == "FAIL"]
    blocks = [x for x in findings if x["kind"] == "BLOCK"]
    warns = [x for x in findings if x["kind"] == "WARN"]

    if a.json:
        print(json.dumps({"folders": len(folders), "findings": findings}, indent=2))
    else:
        print("=" * 72)
        print("check_assets - provenance, licences and rights")
        print("=" * 72)
        for f in findings:
            print("  %-5s %s" % (f["kind"], f["where"]))
            print("        %s" % f["message"])
            if f["hint"]:
                print("        -> %s" % f["hint"])
        if not findings:
            print("  every image has provenance, every entry is complete, "
                  "no rights are outstanding")
        print()
        print("%d folder(s) - %d failure(s), %d blocked, %d warning(s)"
              % (len(folders), len(fails), len(blocks), len(warns)))
        if blocks:
            print()
            print("BLOCKED assets must not ship. Report them to the owner.")

    if fails or blocks:
        return 1
    if warns and a.strict:
        return 1
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(2)
