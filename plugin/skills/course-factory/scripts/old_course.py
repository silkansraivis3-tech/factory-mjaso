#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""The old course, read whole - L41. It is the foundation the new course is built on.

    old_course.py inventory <old course folder> --course <work folder>
    old_course.py images    <old course folder> --course <work folder>   every picture in its decks, by slide

WHY THIS EXISTS
The owner, 2026-10-01: "he needs to check all of the old course, take it as fundamentals, and from there
think how it can be optimised, modernised and digitalised." So before the architecture is designed, every
file of the old course is opened - every deck slide by slide, every exercise and instructor version, every
handout, test and training film - and listed: what it teaches, how much, with what pictures. That list is
what the architecture's "from the old course" plan per module is written from: what is KEPT as it is,
what is MODERNISED (a static picture becomes an animation or a 3D model, a paper exercise becomes a
tablet task, a film becomes a short clip at the right moment) and what is ADDED that it never had.

It reads only. It writes working_claude/old_course_inventory.json and OLD_COURSE_INVENTORY.md in the work
folder (internal - never shipped). Standard library, plus pypdf for PDF page counts when it is installed.

WHAT IS READ, AND HOW
  .pptx   every slide: its title, its word count, its pictures, its speaker notes' word count
  .docx   its headings and its word count
  .pdf    its page count (pypdf), else its size
  video   its name, type and size - it is listed as a possible "real video" for a slide (L37)
  .doc / .ppt (old binary) - listed and flagged: open it in Word / PowerPoint, or read the knowledge
          base's converted copy; never silently skipped
  lock and temporary files (.~lock, ~$) are left out and counted
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import sys
import zipfile
from datetime import date
from xml.etree import ElementTree as ET

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import workspace  # noqa: E402

A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
P = "{http://schemas.openxmlformats.org/presentationml/2006/main}"
WNS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
VIDEO = {".mp4", ".avi", ".mov", ".mpg", ".mpeg", ".wmv", ".m4v", ".mkv", ".webm"}
IMAGE = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".tif", ".tiff"}
ROLE = [("presentation", ("power point", "powerpoint", "presentation", "slides")),
        ("exercise_trainee", ("exercise for trainee", "trainee")),
        ("exercise_instructor", ("exercise for instructor", "instructor")),
        ("film", ("film", "video")), ("test", ("test", "assessment", "exam")), ("handout", ("hand out", "handout"))]


def words(t):
    return len(re.findall(r"\w+", t or "", re.UNICODE))


def num_key(name):
    m = re.match(r"\s*(\d+)", name)
    return (int(m.group(1)) if m else 999, name.lower())


def read_pptx(path):
    out = {"slides": [], "error": None}
    try:
        with zipfile.ZipFile(path) as z:
            names = z.namelist()
            slides = sorted((n for n in names if re.match(r"ppt/slides/slide\d+\.xml$", n)),
                            key=lambda n: int(re.search(r"(\d+)", n.rsplit("/", 1)[1]).group(1)))
            for n in slides:
                x = ET.fromstring(z.read(n))
                title, texts = "", []
                for sp in x.iter(P + "sp"):
                    ph = sp.find(".//" + P + "ph")
                    t = " ".join((r.text or "") for r in sp.iter(A + "t")).strip()
                    if not t:
                        continue
                    if ph is not None and ph.get("type") in ("title", "ctrTitle") and not title:
                        title = t
                    else:
                        texts.append(t)
                if not title and texts:
                    title = texts.pop(0)
                no = re.search(r"(\d+)", n.rsplit("/", 1)[1]).group(1)
                rels = "ppt/slides/_rels/slide%s.xml.rels" % no
                pics = 0
                if rels in names:
                    pics = sum(1 for r in ET.fromstring(z.read(rels)) if "/image" in (r.get("Type") or ""))
                media = 0
                if rels in names:
                    media = sum(1 for r in ET.fromstring(z.read(rels)) if re.search(r"/(video|media|audio)$", r.get("Type") or ""))
                notes = "ppt/notesSlides/notesSlide%s.xml" % no
                nw = 0
                if notes in names:
                    nw = words(" ".join((r.text or "") for r in ET.fromstring(z.read(notes)).iter(A + "t")))
                out["slides"].append({"n": int(no), "title": title[:140], "words": words(" ".join(texts)) + words(title),
                                      "pictures": pics, "video": media, "notes_words": nw})
    except (zipfile.BadZipFile, ET.ParseError, KeyError, OSError) as err:
        out["error"] = str(err)
    return out


def read_docx(path):
    out = {"headings": [], "words": 0, "error": None}
    try:
        with zipfile.ZipFile(path) as z:
            x = ET.fromstring(z.read("word/document.xml"))
        total = []
        for p in x.iter(WNS + "p"):
            t = "".join((r.text or "") for r in p.iter(WNS + "t")).strip()
            if not t:
                continue
            total.append(t)
            st = p.find("./%spPr/%spStyle" % (WNS, WNS))
            if st is not None and re.match(r"(?i)(heading|title|virsraksts)", st.get(WNS + "val") or ""):
                out["headings"].append(t[:120])
        out["words"] = words(" ".join(total))
    except (zipfile.BadZipFile, ET.ParseError, KeyError, OSError) as err:
        out["error"] = str(err)
    return out


def read_pdf(path):
    try:
        import pypdf
        return {"pages": len(pypdf.PdfReader(path).pages), "error": None}
    except ImportError:
        return {"pages": None, "error": "pypdf is not installed - pages not counted"}
    except Exception as err:  # noqa: BLE001 - a damaged PDF is reported, not fatal
        return {"pages": None, "error": str(err)[:120]}


def role_of(rel):
    low = rel.lower()
    for role, keys in ROLE:
        if any(k in low for k in keys):
            return role
    return "other"


def inventory(old):
    sections, skipped = [], 0
    for top in sorted(os.listdir(old), key=num_key):
        tp = os.path.join(old, top)
        files = []
        walk = [(tp, "")] if os.path.isdir(tp) else []
        if os.path.isfile(tp):
            files.append((tp, top))
        for d, _ in walk:
            for dirpath, dirnames, filenames in os.walk(d):
                dirnames.sort(key=num_key)
                for f in sorted(filenames, key=num_key):
                    files.append((os.path.join(dirpath, f), os.path.relpath(os.path.join(dirpath, f), old)))
        sec = {"section": top if os.path.isdir(tp) else "(files at the top)", "files": []}
        for full, rel in files:
            name = os.path.basename(full)
            if name.startswith((".~lock", "~$")) or name.endswith("#"):
                skipped += 1
                continue
            ext = os.path.splitext(name)[1].lower()
            item = {"file": rel.replace("\\", "/"), "role": role_of(rel), "type": ext.lstrip("."), "kb": round(os.path.getsize(full) / 1024.0)}
            if ext == ".pptx":
                item.update(read_pptx(full))
            elif ext == ".docx":
                item.update(read_docx(full))
            elif ext == ".pdf":
                item.update(read_pdf(full))
            elif ext in VIDEO:
                item["video"] = True
            elif ext in (".doc", ".ppt", ".xls"):
                item["error"] = "old binary format - open it in Word / PowerPoint, or read the knowledge base's converted copy"
            elif ext in IMAGE:
                item["image"] = True
            sec["files"].append(item)
        if sec["files"]:
            sections.append(sec)
    return {"old_course": os.path.abspath(old), "read_on": date.today().isoformat(), "sections": sections,
            "lock_files_left_out": skipped}


def summary_md(inv):
    o = ["# The old course, read whole", "",
         "<!-- Made by old_course.py - internal, never shipped. Read only: nothing in the old course was changed. -->", "",
         "Old course: `%s` · read %s" % (inv["old_course"], inv["read_on"]), ""]
    tot = {"slides": 0, "pictures": 0, "files": 0, "films": 0, "unread": 0}
    for s in inv["sections"]:
        o.append("## %s" % s["section"])
        for f in s["files"]:
            tot["files"] += 1
            if f.get("slides") is not None and f["type"] == "pptx":
                sl = f["slides"]
                tot["slides"] += len(sl)
                pics = sum(x["pictures"] for x in sl)
                tot["pictures"] += pics
                w = sum(x["words"] for x in sl)
                o.append("- **%s** - %d slides, %d pictures, about %d words a slide%s" % (
                    f["file"], len(sl), pics, (w // len(sl)) if sl else 0,
                    (", %d with speaker notes" % sum(1 for x in sl if x["notes_words"])) if any(x["notes_words"] for x in sl) else ""))
                for x in sl:
                    o.append("    %d. %s%s" % (x["n"], x["title"] or "(no title)", " · %d pic" % x["pictures"] if x["pictures"] else ""))
            elif f["type"] == "docx":
                o.append("- **%s** (%s) - %d words%s" % (f["file"], f["role"].replace("_", " "), f.get("words", 0),
                                                       ("; " + "; ".join(f["headings"][:8])) if f.get("headings") else ""))
            elif f.get("video"):
                tot["films"] += 1
                o.append("- **%s** - training film (%s, %d MB) - a possible real video for a slide" % (f["file"], f["type"], f["kb"] // 1024))
            elif f["type"] == "pdf":
                o.append("- **%s** - PDF, %s pages" % (f["file"], f.get("pages") or "?"))
            else:
                o.append("- **%s** - %s" % (f["file"], f["type"]))
            if f.get("error"):
                tot["unread"] += 1
                o.append("    - NOT READ: %s" % f["error"])
        o.append("")
    o.insert(5, "**%d files in %d sections: %d slides with %d pictures, %d training films; %d file(s) could not be read%s.**\n" % (
        tot["files"], len(inv["sections"]), tot["slides"], tot["pictures"], tot["films"], tot["unread"],
        (", %d lock files left out" % inv["lock_files_left_out"]) if inv["lock_files_left_out"] else ""))
    return "\n".join(o).rstrip() + "\n", tot


def extract_images(old, work):
    """Every picture in the old course's decks, copied out with the slide it sits on (owner, 2026-10-01: every
    image in the old course is usable). Read only on the old course; the copies go to
    course\\_factory\\old_course_images\\<section>\\<deck>\\slideNN_<name>, with an index."""
    out_dir = workspace.claude_path(work, "old_course_images")
    index, n, seen = [], 0, {}
    for dirpath, _, files in os.walk(old):
        for f in sorted(files, key=num_key):
            if not f.lower().endswith(".pptx") or f.startswith(("~$", ".~lock")):
                continue
            full = os.path.join(dirpath, f)
            rel = os.path.relpath(full, old)
            sec = rel.split(os.sep)[0] if os.sep in rel else ""
            dest = os.path.join(out_dir, re.sub(r"[^\w.\- ]", "_", sec), re.sub(r"[^\w.\- ]", "_", os.path.splitext(f)[0]))
            try:
                with zipfile.ZipFile(full) as z:
                    names = set(z.namelist())
                    for rels in sorted((x for x in names if re.match(r"ppt/slides/_rels/slide\d+\.xml\.rels$", x)),
                                       key=lambda x: int(re.search(r"slide(\d+)", x).group(1))):
                        no = int(re.search(r"slide(\d+)", rels).group(1))
                        for r in ET.fromstring(z.read(rels)):
                            if "/image" not in (r.get("Type") or ""):
                                continue
                            target = os.path.normpath(os.path.join("ppt/slides", r.get("Target") or "")).replace("\\", "/")
                            if target not in names:
                                continue
                            data = z.read(target)
                            h = hashlib.sha256(data).hexdigest()
                            if h in seen:             # the same picture again - a logo on every slide: kept once
                                index.append({"deck": rel.replace("\\", "/"), "slide": no, "file": seen[h], "repeat": True})
                                continue
                            os.makedirs(dest, exist_ok=True)
                            name = "slide%02d_%s" % (no, os.path.basename(target))
                            with open(os.path.join(dest, name), "wb") as o:
                                o.write(data)
                            n += 1
                            seen[h] = os.path.relpath(os.path.join(dest, name), work).replace("\\", "/")
                            index.append({"deck": rel.replace("\\", "/"), "slide": no, "file": seen[h],
                                          "rights": "OWNER_CLEARED - old course, owner 2026-10-01"})
            except (zipfile.BadZipFile, ET.ParseError, OSError) as err:
                index.append({"deck": rel.replace("\\", "/"), "error": str(err)})
    os.makedirs(out_dir, exist_ok=True)
    with io.open(os.path.join(out_dir, "_index.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(index, fh, ensure_ascii=False, indent=1)
    return n, out_dir


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    i = sub.add_parser("inventory"); i.add_argument("old"); i.add_argument("--course", required=True)
    im = sub.add_parser("images"); im.add_argument("old"); im.add_argument("--course", required=True)
    a = ap.parse_args(argv)
    if not os.path.isdir(a.old):
        print("Stopped - the old course folder is not there:\n    %s" % a.old)
        return 2
    work = workspace.work_folder(a.course)
    if a.cmd == "images":
        n, d = extract_images(a.old, work)
        print("Copied %d picture(s) out of the old course's decks, each named by its slide - the old course itself was not changed:\n"
              "    %s\n  The index says which deck and slide each came from. All are usable (owner, 2026-10-01)." % (n, d))
        return 0
    inv = inventory(a.old)
    md, tot = summary_md(inv)
    d = os.path.join(work, workspace.CLAUDE)
    os.makedirs(d, exist_ok=True)
    with io.open(os.path.join(d, "old_course_inventory.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(inv, f, ensure_ascii=False, indent=1)
    with io.open(os.path.join(d, "OLD_COURSE_INVENTORY.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write(md)
    print("The old course was read whole - nothing in it was changed:\n    %s\n  %d files in %d sections: %d slides with %d pictures, "
          "%d training films; %d could not be read.\n  The list:\n    %s" % (
              a.old, tot["files"], len(inv["sections"]), tot["slides"], tot["pictures"], tot["films"], tot["unread"],
              os.path.join(d, "OLD_COURSE_INVENTORY.md")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
