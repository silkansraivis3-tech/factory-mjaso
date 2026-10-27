#!/usr/bin/env python3
"""Provenance and rights, checked against the schemas.

Every image in an asset folder has an entry beside it; every entry has its
required fields; visually_verified is real; rights states are valid; and
nothing ships at RIGHTS_REVIEW_REQUIRED.

  python check_assets.py <assets-dir> [...] [--strict] [--json]
  python check_assets.py clear <assets-dir> <file> --by "<name>" --reason "..." --source-work "<book, edition, page / figure>"

`clear` (2.63.2, L52) records a person's decision that a source-book figure may be used: rights_state OWNER_CLEARED,
cleared_by "<name>, <date> - <reason>", source_work. Without a whole cleared_by the figure stays blocked.

Exit 0 clean (or warnings only) · 1 failures · 2 bad usage.
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from image_size import PHOTO_FLOOR, PHOTO_MIN_LONG, found_size, pixel_size  # noqa: E402
SKILL = os.path.dirname(HERE)
SCHEMA_DIR = os.path.join(SKILL, "source", "schemas")

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".svg", ".webp", ".gif"}
META_FILES = {"_photo_meta.json": "photo", "_figure_meta.json": "figure"}

def valid_rights():
    """every rights state the asset pipeline defines, and the ones a subject library ships with (2.56.0). This list was
    typed here and drifted: OWNER_CLEARED (asset-pipeline.json since 2.19.2) and a library's GENERATED failed every
    record that carried them - found by the IGF M02 build with the Gas Library, 2026-10-20"""
    out = {"CLEARED", "PROJECT_OWNED", "PUBLIC_DOMAIN", "ATTRIBUTION_REQUIRED", "RIGHTS_REVIEW_REQUIRED", "REJECTED"}
    know = os.path.join(SKILL, "source", "knowledge")
    for name, pick in (("asset-pipeline.json", lambda d: d.get("rights_states", {}).keys()),
                       ("subject-libraries.json", lambda d: d.get("ship_states", []))):
        try:
            with open(os.path.join(know, name), encoding="utf-8") as fh:
                out |= {k for k in pick(json.load(fh)) if not str(k).startswith("_")}
        except (OSError, ValueError, AttributeError):
            pass
    return out


VALID_RIGHTS = valid_rights()


def design_files():
    """the factory's own files that design_system.py install copies into a module's assets\\ (the logo among them): the
    brand's, never a course asset - an assets\\ root holding only the logo failed "1 image(s) and no provenance file"
    (2.60.0, IGF modules)"""
    try:
        with open(os.path.join(os.path.dirname(SKILL), "course-module-ui", "knowledge", "design-system.json"), encoding="utf-8") as fh:
            return {f["name"] for f in json.load(fh).get("files", []) if f.get("name")}
    except (OSError, ValueError, KeyError, TypeError):
        return {"novikontas_logo.svg"}


DESIGN_FILES = design_files()
# folders that are not shipped and not asset folders: a picture set aside (assets\img\_unused) has no provenance to keep
SKIP_DIRS = (".git", "__pycache__", "oldversion", "_unused")

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


# 2.63.2 (item 10, L52): a source-book figure ships only on a named person's decision, recorded in the picture's record as
# `cleared_by: "<name>, <date> - <reason>"` with `rights_state: OWNER_CLEARED` and `source_work` (book, edition, page / figure).
# Set by `check_assets.py clear` - never by a script on its own. compile_module.py keeps the same pattern (NAMED_CLEARANCE).
NAMED_CLEARANCE = re.compile(r"^[^,\n]{2,},\s*\d{4}-\d{2}-\d{2}\s+-\s+\S")
VERIFIED_OK = re.compile(r"^\s*yes\b", re.I)
HAS_DATE = re.compile(r"\d{4}-\d{2}-\d{2}|\d{1,2}\s+\w+\s+\d{4}")


# 2.63.3 (the 2.63.2 full-course run, M09: a photo copied from the Gas Library with its library record - no `source`, no
# `shows` - failed check_assets --strict). The library's own schema names where a picture is from in other fields; read
# as the factory's `source`, and written so by `check_assets.py normalise <assets-dir>`
LIBRARY_SOURCE = ("page_url", "source_url", "url_or_origin", "url", "commons_title")


def library_source(meta: dict) -> str:
    for k in LIBRARY_SOURCE:
        if meta.get(k):
            return "%s%s" % (meta[k], (" (%s)" % meta["credit"]) if meta.get("credit") and k != "commons_title" else "")
    return ""


def normalise(argv) -> int:
    """check_assets.py normalise <assets-dir> [--library <Gas Library root>]: a photo record in the library's schema gets the
    factory's fields - `source` from its page or title, `shows` from the library's ASSETS.json entry (by library_id or file
    name) or, failing that, from its description. Nothing else is touched."""
    ap = argparse.ArgumentParser(prog="check_assets.py normalise")
    ap.add_argument("folder")
    ap.add_argument("--library", default=os.environ.get("NOVIKONTAS_GAS_LIBRARY", ""))
    a = ap.parse_args(argv)
    mp = os.path.join(a.folder, "_photo_meta.json")
    try:
        with open(mp, encoding="utf-8-sig") as fh:
            data = json.load(fh)
    except Exception as exc:                          # noqa: BLE001
        print("cannot read %s: %s" % (mp, exc))
        return 2
    lib = {}
    idx = os.path.join(a.library, "assets", "ASSETS.json") if a.library else ""
    if idx and os.path.isfile(idx):
        try:
            with open(idx, encoding="utf-8-sig") as fh:
                raw = json.load(fh)
            rows = raw if isinstance(raw, list) else raw.get("assets", list(raw.values()) if isinstance(raw, dict) else [])
            for r in rows:
                if isinstance(r, dict):
                    lib[r.get("id")] = r
                    lib[os.path.basename(str(r.get("file") or ""))] = r
        except Exception:                             # noqa: BLE001
            lib = {}
    done = []
    for fname, meta in data.items():
        if not isinstance(meta, dict):
            continue
        got = []
        if not meta.get("source") and library_source(meta):
            meta["source"] = library_source(meta)
            got.append("source")
        if not meta.get("shows"):
            row = lib.get(meta.get("library_id")) or lib.get(fname) or {}
            if row.get("shows"):
                meta["shows"] = list(row["shows"])
                got.append("shows (library)")
            elif meta.get("description"):
                meta["shows"] = [re.split(r"[.;]\s", str(meta["description"]), 1)[0].strip()]
                got.append("shows (description)")
        if got:
            done.append("%s: %s" % (fname, ", ".join(got)))
    if done:
        with open(mp, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps(data, ensure_ascii=False, indent=1))
    print("Normalised %d record(s) in %s%s" % (len(done), mp, "".join("\n  " + x for x in done)))
    return 0


def original_of(folder: str, fname: str) -> str:
    """the photograph as it was found: a module's compile enlarges one under 1600 px (L62) and keeps the original in
    <course>/working_claude/photo_originals/M01/ - the size that says whether a larger one is needed is that one's"""
    parts = os.path.abspath(folder).replace("\\", "/").split("/")
    for i in range(len(parts) - 1, 0, -1):
        if parts[i - 1] == "modules" and parts[i].startswith("module") and parts[i][6:].isdigit():
            keep = os.path.join("/".join(parts[:i - 1]), "working_claude", "photo_originals", "M%02d" % int(parts[i][6:]), fname)
            if os.path.isfile(keep):
                return keep
            break
    return os.path.join(folder, fname)


def check_folder(folder: str) -> None:
    entries = [e for e in os.listdir(folder)]
    images = sorted(e for e in entries
                    if os.path.splitext(e)[1].lower() in IMAGE_EXT and e not in DESIGN_FILES)
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
            # 2.65.0 - a photograph found at 1600 px or more on its long edge; under 800 px no enlargement makes it sharp
            if kind == "photo" and os.path.splitext(fname)[1].lower() in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
                kept = original_of(folder, fname)
                size = found_size(os.path.join(folder, fname), kept if kept != os.path.join(folder, fname) else None)
                if size and max(size) < PHOTO_FLOOR and not str(meta.get("low_resolution_ok") or "").strip():
                    warn(where, "only %d x %d px - no enlargement makes it sharp, and the module's pre-check stops the build on it"
                         % size, "find the original (%d px or more on its long edge - not a web preview), a photograph to take, "
                         "or record why it stays: \"low_resolution_ok\": \"<reason>\"" % PHOTO_MIN_LONG)
                elif size and max(size) < PHOTO_MIN_LONG:
                    warn(where, "%d x %d px - under %d px the compile enlarges it; the original would be sharper"
                         % (size[0], size[1], PHOTO_MIN_LONG), "the original file, not a web preview")

            if not os.path.isfile(os.path.join(folder, fname)):
                warn(where, "entry describes a file that is not here",
                     "an orphan entry means a file was moved or renamed")

            missing = [f for f in req if f not in meta or meta[f] in ("", None)]
            if "source" in missing and kind == "photo" and library_source(meta):
                missing.remove("source")      # 2.63.3: a Gas Library record says where it is from in its own words
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
                      "the owner decides, by name: check_assets.py clear <assets-dir> %s --by \"<name>\" --reason \"...\" "
                      "--source-work \"<book, edition, page / figure>\" (a source-book figure); an uncleared publisher "
                      "figure has blocked a whole course in this system before" % fname)
            elif rs == "REJECTED":
                warn(where, "rights_state REJECTED but the file is still here",
                     "remove the file, or keep only the entry as a record")

            # a source-book figure (`source_work`) or any record that names a clearance must carry a whole one; OWNER_CLEARED
            # alone stays what it was (the knowledge base and the old course, owner 2026-10-01)
            if rs == "OWNER_CLEARED" and (meta.get("source_work") or "cleared_by" in meta) \
                    and not NAMED_CLEARANCE.match(str(meta.get("cleared_by") or "").strip()):
                fail(where, "OWNER_CLEARED source-book figure without a valid cleared_by - it stays blocked",
                     'cleared_by: "<name>, <YYYY-MM-DD> - <reason>"; set it with check_assets.py clear (a person\'s decision)')

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


def clear(argv) -> int:
    """2.63.2 (item 10, L52): record a person's decision that a source-book figure may be used - never automatic.
    Sets rights_state OWNER_CLEARED, cleared_by "<name>, <date> - <reason>" and source_work on the picture's record.
    Refuses without --by, --reason and --source-work, for a file with no record, and for a generated or rejected one."""
    ap = argparse.ArgumentParser(prog="check_assets.py clear", description=clear.__doc__.split("\n")[0])
    ap.add_argument("folder", help="the assets folder holding the picture and its _photo_meta.json / _figure_meta.json")
    ap.add_argument("file", help="the picture's file name")
    ap.add_argument("--by", default="", help="who decides (a name)")
    ap.add_argument("--reason", default="", help="why it may be used")
    ap.add_argument("--source-work", default="", help="its real source: book, edition, page / figure")
    ap.add_argument("--date", default="", help="YYYY-MM-DD (today when left out)")
    a = ap.parse_args(argv)
    by, reason, work = a.by.strip(), a.reason.strip(), a.source_work.strip()
    if not (by and reason and work):
        print("refused: a clearance is a named person's decision with a reason and the real source - give --by, --reason "
              "and --source-work (book, edition, page / figure)")
        return 2
    if "," in by:
        print("refused: --by is one name, without a comma")
        return 2
    date = a.date.strip() or datetime.date.today().isoformat()
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
        print("refused: --date is YYYY-MM-DD")
        return 2
    for mname in META_FILES:
        mpath = os.path.join(a.folder, mname)
        try:
            with open(mpath, encoding="utf-8-sig") as fh:
                data = json.load(fh)
        except (OSError, ValueError):
            continue
        meta = data.get(a.file) if isinstance(data, dict) else None
        if not isinstance(meta, dict):
            continue
        if meta.get("rights_state") == "REJECTED" or meta.get("generated") is True:
            print("refused: %s is rejected or generated - there is nothing to clear" % a.file)
            return 2
        meta["rights_state"] = "OWNER_CLEARED"
        meta["cleared_by"] = "%s, %s - %s" % (by, date, reason)
        meta["source_work"] = work
        meta.setdefault("credit", work)
        with open(mpath, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        print("cleared: %s in %s - %s" % (a.file, mname, meta["cleared_by"]))
        return 0
    print("refused: %s has no record in %s - bring the picture in with its record first" % (a.file, a.folder))
    return 2


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "clear":
        return clear(sys.argv[2:])
    if len(sys.argv) > 1 and sys.argv[1] == "normalise":
        return normalise(sys.argv[2:])
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
            dn[:] = [d for d in dn if d not in SKIP_DIRS]
            if any(os.path.splitext(f)[1].lower() in IMAGE_EXT and f not in DESIGN_FILES for f in fn):
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
