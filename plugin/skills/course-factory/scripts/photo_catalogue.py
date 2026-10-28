#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""photo_catalogue.py - every picture the course already owns, indexed once, and given to the slots course-wide (2.73.0).

    photo_catalogue.py index  <course>            at intake, beside the script writers: working_claude\\photo_catalogue.json
    photo_catalogue.py assign <course>            once the scripts are approved, before Phase A: working_claude\\photo_plan.json
                                                  and working_claude\\visuals\\PHOTOS_TO_FIND.md (one sourcing pass for the course)
    photo_catalogue.py show   <course> --module 4 the module's slots, their candidates and picks

WHY (chem advanced, 2026-10-27): 21 builders at once each looked for the same old-course and knowledge-base pictures - in
the guides, in 906 extracted old-course pictures and 1,893 knowledge-base ones - and the one judgement no local build can
make (which picture) held every module back. The pictures are the course's, so they are indexed ONCE: each with its size,
what it shows (the old-course slide's own words, the knowledge base's caption or the words of its page), where it came
from and its rights (L33: every old-course and knowledge-base picture is usable as it is, credited). The scripts' photo
slots ("picture": {"kind": "photo", "shows"}) are then matched to them for the whole course at once, so no picture is
given to two slots (L58) before the parallel builds start. What has no good match is listed for ONE visual-sourcer pass
for the whole course, at 1600 px or more (L52, L64) - not one search per builder.

A pick is only a proposal: the build sheet takes it in Phase B (the builder, or compile/scripts/visual_needs.py fill
--auto for a slide whose top candidate scores at least AUTO and is 800 px or more), marked "auto_picked", and the visual
review looks at it like any other picture.

Standard library (+ course-visuals image_size for the sizes). Reads only the course's own files.
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import io
import json
import math
import os
import re
import sys
import zipfile
from datetime import date
from xml.etree import ElementTree as ET

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "course-visuals", "scripts"))
import content_script as cs  # noqa: E402
import workspace  # noqa: E402
from image_size import PHOTO_FLOOR, pixel_size  # noqa: E402

CATALOGUE, PLAN, TO_FIND = "photo_catalogue.json", "photo_plan.json", "PHOTOS_TO_FIND.md"
MIN_INDEX = 300          # px on the long side: smaller is a logo, an icon or a bullet - not indexed
AUTO = 0.6               # a slide's top candidate at or above this (and PHOTO_FLOOR px or more) may be filled with no agent
FIND = 0.35              # a slot whose best candidate is under this is listed to be found
TOPIC_BONUS = 0.1        # the picture comes from the old course's (or the knowledge base's) section of the module's own topic
FROM_OLD_BONUS = 0.35    # the picture sits on an old-course slide the script's own "from_old" names ("deck 5, slides 28-30")
K1, BM_B = 1.2, 0.75     # BM25: a long description (a whole old slide's words) does not win by length alone
IMAGES = (".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tif", ".tiff")
A_T = "{http://schemas.openxmlformats.org/drawingml/2006/main}t"


# ------------------------------------------------------------------ words
def tokens(text):
    """the words that say what a picture shows: lower case, 3 letters or more, no stop words, a plural's s off"""
    out = []
    for w in re.findall(r"[^\W\d_]{3,}", str(text or "").lower()):
        if w in cs.STOP:
            continue
        if len(w) > 4 and w.endswith("s") and not w.endswith("ss"):
            w = w[:-1]
        out.append(w)
    return out


def topic_of(path):
    """the programme topic a folder path is filed under: "15. Chemical tanker cargo operations/..." -> 15"""
    for part in re.split(r"[\\/]", str(path or "")):
        m = re.match(r"^\s*(\d{1,2})\s*[.)_ -]", part)
        if m:
            return int(m.group(1))
    return None


# ------------------------------------------------------------------ the index
def slide_words(pptx, cache):
    """{slide number: its words} of an old-course deck - read once"""
    if pptx in cache:
        return cache[pptx]
    out = {}
    try:
        with zipfile.ZipFile(pptx) as z:
            for name in z.namelist():
                m = re.match(r"ppt/slides/slide(\d+)\.xml$", name)
                if m:
                    try:
                        out[int(m.group(1))] = " ".join(t.text or "" for t in ET.fromstring(z.read(name)).iter(A_T)).strip()
                    except ET.ParseError:
                        pass
    except (OSError, zipfile.BadZipFile):
        pass
    cache[pptx] = out
    return out


def sha_of(path):
    try:
        return hashlib.sha256(io.open(path, "rb").read()).hexdigest()
    except OSError:
        return ""


def old_course_photos(course):
    """the old course's pictures (old_course.py images): each with its slide's words"""
    work = workspace.work_folder(course, create=False)
    idx = workspace.claude_path(work, "old_course_images", "_index.json")
    try:
        rows = json.load(io.open(idx, encoding="utf-8"))
    except (OSError, ValueError):
        return []
    try:
        root = json.load(io.open(workspace.claude_path(work, "old_course_inventory.json"), encoding="utf-8")).get("old_course") or ""
    except (OSError, ValueError):
        root = ""
    decks, out = {}, []
    for r in rows:
        if r.get("repeat") or r.get("error") or not r.get("file"):
            continue
        p = os.path.join(work, r["file"])
        if not os.path.isfile(p):
            continue
        words = slide_words(os.path.join(root, r["deck"]), decks).get(r.get("slide"), "") if root else ""
        deck = os.path.splitext(os.path.basename(r["deck"]))[0]
        out.append({"path": p, "source": "old course", "origin": "%s, slide %s" % (r["deck"], r.get("slide")),
                    "description": ("%s - %s" % (deck, words)).strip(" -")[:600], "topic": topic_of(r["deck"]),
                    "rights": r.get("rights") or "OWNER_CLEARED - old course (L33)", "sha256": sha_of(p)})
    return out


def kb_paths(course):
    try:
        import course_gate
        d = course_gate.kb_decision(workspace.work_folder(course, create=False)) or {}
    except Exception:                                   # noqa: BLE001 - no decision, no knowledge base pictures
        d = {}
    p = d.get("path")
    return [x for x in (p if isinstance(p, list) else [p]) if x and os.path.isdir(x)]


def page_words(md, kind, number, cache):
    """the words of one page or slide of a knowledge-base document (its "## Page N" section)"""
    if md not in cache:
        try:
            text = io.open(md, encoding="utf-8").read()
        except OSError:
            text = ""
        secs = {}
        for m in re.finditer(r"^##\s+(Page|Slide|Section)\s+(\d+)\s*$(.*?)(?=^##\s+(?:Page|Slide|Section)\s+\d+\s*$|\Z)", text, re.M | re.S):
            secs[(m.group(1).lower(), int(m.group(2)))] = " ".join(m.group(3).split())
        cache[md] = secs
    return cache[md].get((str(kind or "page").lower(), number), "")


def kb_photos(course):
    """the knowledge base's pictures (Course Source Processor: sources\\*\\images, each in its metadata.json)"""
    out, pages = [], {}
    for kb in kb_paths(course):
        for meta_p in sorted(glob.glob(os.path.join(kb, "sources", "*", "metadata.json"))):
            folder = os.path.dirname(meta_p)
            try:
                meta = json.load(io.open(meta_p, encoding="utf-8"))
            except (OSError, ValueError):
                continue
            title = meta.get("title") if meta.get("title") not in (None, "", "Word Document", "PowerPoint Presentation") else \
                os.path.splitext(meta.get("original_filename") or "")[0]
            for im in meta.get("images") or []:
                p = os.path.join(folder, "images", im.get("file") or "")
                if not im.get("file") or not os.path.isfile(p):
                    continue
                loc = im.get("location") or {}
                words = (im.get("caption") or "").strip() or page_words(os.path.join(folder, "document.md"), loc.get("kind"),
                                                                       loc.get("number"), pages)
                out.append({"path": p, "source": "knowledge base",
                            "origin": "%s, %s %s" % (meta.get("source_path") or meta.get("original_filename"), loc.get("kind") or "page",
                                                     loc.get("number")),
                            "description": ("%s - %s" % (title, " ".join(words.split()[:80]))).strip(" -")[:600],
                            "topic": topic_of(meta.get("source_path")), "rights": "OWNER_CLEARED - knowledge base (L33)",
                            "sha256": im.get("sha256") or sha_of(p), "w": im.get("width"), "h": im.get("height")})
    return out


FOUND = "photos_found"      # working_claude\photos_found: the course's one sourcing pass saves here, each with its record


def found_photos(course):
    """the photographs the course's sourcing pass found (working_claude\\photos_found, any sub-folder), each with its
    _photo_meta.json record - "found_for": "M04 s05" names the slot it was found for; one under rights review is left out"""
    work = workspace.work_folder(course, create=False)
    out = []
    for mp in sorted(glob.glob(os.path.join(workspace.claude_path(work, FOUND), "**", "_photo_meta.json"), recursive=True)):
        try:
            meta = json.load(io.open(mp, encoding="utf-8"))
        except (OSError, ValueError):
            continue
        for name, rec in sorted(meta.items()):
            p = os.path.join(os.path.dirname(mp), name)
            state = str((rec or {}).get("rights_state") or "").upper() if isinstance(rec, dict) else ""
            if not isinstance(rec, dict) or not os.path.isfile(p) or "REVIEW" in state or "REJECT" in state:
                continue
            out.append({"path": p, "source": "found", "origin": rec.get("url_or_origin") or rec.get("source") or name,
                        "description": " - ".join(x for x in (rec.get("title"), rec.get("shows"), rec.get("description")) if x)[:600],
                        "topic": None, "rights": rec.get("rights_state") or "", "record": rec,
                        "found_for": str(rec.get("found_for") or "").strip(), "sha256": sha_of(p)})
    return out


def index(course):
    """working_claude\\photo_catalogue.json - every picture of the course's own, once (the same bytes in the old course and the
    knowledge base are one picture: the old course's slide words are kept)"""
    work = workspace.work_folder(course, create=False)
    seen, photos, small = set(), [], 0
    for ph in found_photos(course) + old_course_photos(course) + kb_photos(course):
        if ph["sha256"] and ph["sha256"] in seen:
            continue
        if not ph.get("w"):
            size = pixel_size(ph["path"])
            ph["w"], ph["h"] = size if size else (0, 0)
        if max(ph["w"] or 0, ph["h"] or 0) < MIN_INDEX:
            small += 1
            continue
        seen.add(ph["sha256"])
        ph["id"] = "p%04d" % (len(photos) + 1)
        photos.append(ph)
    cat = {"made": date.today().isoformat(), "photos": photos, "left_out_small": small}
    p = workspace.claude_path(work, CATALOGUE)
    io.open(p, "w", encoding="utf-8", newline="\n").write(json.dumps(cat, ensure_ascii=False, indent=1))
    return p, cat


def load(course, name):
    try:
        return json.load(io.open(workspace.claude_path(workspace.work_folder(course, create=False), name), encoding="utf-8"))
    except (OSError, ValueError):
        return None


# ------------------------------------------------------------------ the slots and their candidates
def slots(course):
    """[(key "M04 s05", module, screen, its picture slot)] - every photo slot of every approved script, in course order"""
    work = workspace.work_folder(course, create=False)
    out = []
    for sp in sorted(glob.glob(os.path.join(workspace.claude_path(work, "script"), "M*.json"))):
        if not re.match(r"M\d+\.json$", os.path.basename(sp)):
            continue
        try:
            sc = cs.load(sp)
        except (OSError, ValueError):
            continue
        for s in sc.get("screens") or []:
            if cs.on_picture(s) and cs.picture_of(s)["kind"] == "photo":
                out.append(("%s %s" % (cs.mid(sc.get("module")), s["id"]), sc.get("module"), s, cs.picture_of(s)))
    return out


def query_of(s, pic):
    """{word: weight} - what the slot must show counts most, then the title, then the slide's own words"""
    q = {}
    for text, w in ((s.get("text") or s.get("question") or "", 0.5), (s.get("title") or "", 1.5), (pic.get("shows") or "", 2.0)):
        for t in tokens(text):
            q[t] = max(q.get(t, 0), w)
    return q


def from_old_refs(s):
    """[(deck, {slide numbers})] the script's "from_old" names: "deck 1, slides 39-41 (...)", "deck 5 slide 29 and 31" """
    out = []
    for m in re.finditer(r"deck\s*(\d+)\b([^;]*)", str(s.get("from_old") or ""), re.I):
        nums = set()
        for mm in re.finditer(r"slides?\s*([\d\s,\-–and]+)", m.group(2), re.I):
            for a, b in re.findall(r"(\d+)(?:\s*[-–]\s*(\d+))?", mm.group(1)):
                lo, hi = int(a), int(b or a)
                nums |= set(range(lo, min(hi, lo + 60) + 1))
        out.append((int(m.group(1)), nums))
    return out


def old_slide(ph):
    """(deck topic, slide number) of an old-course picture, from its origin "...pptx, slide 29" """
    m = re.search(r", slide (\d+)$", ph.get("origin") or "")
    return (ph.get("topic"), int(m.group(1))) if ph.get("source") == "old course" and m else None


class Scorer:
    def __init__(self, photos):
        self.photos = photos
        self.bags = []
        for p in photos:
            bag = {}
            for t in tokens(p.get("description")):
                bag[t] = bag.get(t, 0) + 1
            self.bags.append(bag)
        n = len(photos) or 1
        self.avg = (sum(sum(b.values()) for b in self.bags) / float(n)) or 1.0
        df = {}
        for b in self.bags:
            for t in b:
                df[t] = df.get(t, 0) + 1
        self.idf = {t: math.log(1 + (n - c + 0.5) / (c + 0.5)) for t, c in df.items()}
        self.idf_unknown = math.log(1 + (n + 0.5) / 0.5)

    def score(self, q, k, topic=None, refs=(), slot=None):
        """0..1: BM25 of the picture's description for the slot's words (what it must show counts most, then the title, then
        the slide's own words) against what a description holding each main word once would score; a picture on an old-course
        slide the script's "from_old" names, or from the module's own topic, more"""
        bag, ln = self.bags[k], sum(self.bags[k].values()) or 1
        norm = K1 * (1 - BM_B + BM_B * ln / self.avg)
        main = sum(w * self.idf.get(t, self.idf_unknown) for t, w in q.items() if w >= 1.5) or 1.0
        got = sum(w * self.idf.get(t, self.idf_unknown) * bag[t] * (K1 + 1) / (bag[t] + norm) for t, w in q.items() if t in bag)
        s = got / (main * (K1 + 1) / (1 + K1))
        if slot and self.photos[k].get("found_for") == slot:      # the sourcing pass found it for this very slot
            return 1.0
        here = old_slide(self.photos[k])
        if here and any(here[0] == d and (not nums or here[1] in nums) for d, nums in refs):
            s += FROM_OLD_BONUS
        elif topic is not None and self.photos[k].get("topic") == topic:
            s += TOPIC_BONUS
        return round(min(1.0, s), 3)

    def top(self, q, n=5, topic=None, skip=(), refs=(), slot=None):
        hits = [(self.score(q, k, topic, refs, slot), k) for k in range(len(self.photos)) if self.photos[k]["id"] not in skip]
        hits = [h for h in hits if h[0] > 0]
        hits.sort(key=lambda x: (-x[0], -max(self.photos[x[1]].get("w") or 0, self.photos[x[1]].get("h") or 0)))
        return hits[:n]


def used_in_modules(course):
    """the catalogue pictures a built module already ships (its record's url_or_origin names the catalogue path)"""
    work = workspace.work_folder(course, create=False)
    out = set()
    for mp in glob.glob(os.path.join(work, workspace.MODULES, "module*", "assets", "img", "_photo_meta.json")):
        try:
            for rec in json.load(io.open(mp, encoding="utf-8")).values():
                if isinstance(rec, dict) and rec.get("catalogue_id"):
                    out.add(rec["catalogue_id"])
        except (OSError, ValueError):
            pass
    return out


def assign(course):
    """working_claude\\photo_plan.json: each photo slot's five best candidates and - course-wide, the best match first - one
    pick a slot may take with no agent (score AUTO or more, PHOTO_FLOOR px or more, never given twice); and
    visuals\\PHOTOS_TO_FIND.md: the slots nothing in the course's own pictures shows"""
    work = workspace.work_folder(course, create=False)
    cat = load(course, CATALOGUE)
    if cat is None:
        _, cat = index(course)
    photos = cat["photos"]
    by_id = {p["id"]: p for p in photos}
    sc = Scorer(photos)
    taken = used_in_modules(course)
    rows, offers = {}, []
    for key, module, s, pic in slots(course):
        q = query_of(s, pic)
        topic = int(module) if str(module).isdigit() else None
        top = sc.top(q, 5, topic, refs=from_old_refs(s), slot=key)
        rows[key] = {"module": module, "screen": s["id"], "shows": pic["shows"], "aspect": pic["aspect"],
                     "question": s.get("kind") in cs.TASKS, "pick": None,
                     "candidates": [{"id": photos[k]["id"], "score": v} for v, k in top]}
        for v, k in top:
            p = photos[k]
            if v >= AUTO and max(p.get("w") or 0, p.get("h") or 0) >= PHOTO_FLOOR and s.get("kind") == "slide":
                offers.append((v, key, p["id"]))
    for v, key, pid in sorted(offers, key=lambda x: -x[0]):           # the best match first, each picture once (L58)
        if rows[key]["pick"] is None and pid not in taken:
            rows[key]["pick"] = {"id": pid, "score": v}
            taken.add(pid)
    plan = {"made": date.today().isoformat(), "auto": AUTO, "floor_px": PHOTO_FLOOR, "slots": rows}
    p = workspace.claude_path(work, PLAN)
    io.open(p, "w", encoding="utf-8", newline="\n").write(json.dumps(plan, ensure_ascii=False, indent=1))
    find = [(k, r) for k, r in rows.items() if not r["pick"] and (not r["candidates"] or r["candidates"][0]["score"] < FIND
                                                                   or all(max(by_id[c["id"]].get("w") or 0, by_id[c["id"]].get("h") or 0)
                                                                          < PHOTO_FLOOR for c in r["candidates"]))]
    vdir = workspace.claude_path(work, "visuals")
    os.makedirs(vdir, exist_ok=True)
    lines = ["# Photographs to find - the whole course, one sourcing pass (2.73.0)", "",
             "*Written by `photo_catalogue.py assign`. Nothing in the course's own pictures (old course, knowledge base) shows these "
             "well enough at 800 px or more. ONE visual-sourcer pass finds them for the whole course, 1600 px or larger (L52, L64), "
             "saved into the module's assets\\img with its record (`_photo_meta.json`, `shows`). Internal - never shipped.*", "",
             "| Slot | Shape | Must show | Best of the course's own (score, px) |", "|---|---|---|---|"]
    for k, r in find:
        best = r["candidates"][0] if r["candidates"] else None
        bp = by_id.get(best["id"]) if best else None
        lines.append("| %s%s | %s | %s | %s |" % (k, " (question)" if r["question"] else "", r["aspect"], r["shows"].replace("|", "/"),
                                                  "%s (%.2f, %sx%s)" % (os.path.basename(bp["path"]), best["score"], bp.get("w"), bp.get("h"))
                                                  if bp else "-"))
    io.open(os.path.join(vdir, TO_FIND), "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
    return p, plan, len(find)


def candidates_for(course, module, sid):
    """the plan's row for one slot, its candidates with their records - [] when the course has no plan yet"""
    plan = load(course, PLAN) or {}
    cat = load(course, CATALOGUE) or {}
    by_id = {p["id"]: p for p in cat.get("photos") or []}
    r = (plan.get("slots") or {}).get("%s %s" % (cs.mid(module), sid))
    if not r:
        return None
    out = dict(r)
    out["candidates"] = [dict(by_id[c["id"]], score=c["score"]) for c in r["candidates"] if c["id"] in by_id]
    if r.get("pick") and r["pick"]["id"] in by_id:
        out["pick"] = dict(by_id[r["pick"]["id"]], score=r["pick"]["score"])
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("index", "assign", "show"):
        x = sub.add_parser(name)
        x.add_argument("course")
        if name == "show":
            x.add_argument("--module", required=True)
    a = ap.parse_args(argv)
    if a.cmd == "index":
        p, cat = index(a.course)
        by = {}
        for ph in cat["photos"]:
            by[ph["source"]] = by.get(ph["source"], 0) + 1
        print("Indexed %d picture(s) - %s; %d left out under %d px (logos, icons). Written: %s"
              % (len(cat["photos"]), ", ".join("%d from the %s" % (n, k) for k, n in sorted(by.items())) or "none",
                 cat["left_out_small"], MIN_INDEX, p))
        return 0
    if a.cmd == "assign":
        p, plan, n_find = assign(a.course)
        rows = plan["slots"]
        print("%d photo slot(s) in the approved scripts: %d with a pick that can be filled with no agent (score %.2f+, %d px+, each "
              "picture once), %d with candidates for the builder, %d to find (visuals\\%s). Written: %s"
              % (len(rows), sum(1 for r in rows.values() if r["pick"]), AUTO, PHOTO_FLOOR,
                 sum(1 for r in rows.values() if not r["pick"] and r["candidates"]), n_find, TO_FIND, p))
        return 0
    plan = load(a.course, PLAN)
    if not plan:
        print("No photo plan yet - photo_catalogue.py assign <course>")
        return 1
    for key, r in plan["slots"].items():
        if key.split()[0] == cs.mid(a.module):
            c = candidates_for(a.course, a.module, r["screen"])
            print("%s  %s  shows: %s" % (key, "PICK " + os.path.basename(c["pick"]["path"]) if c.get("pick") else "no pick", r["shows"]))
            for x in c["candidates"]:
                print("    %.2f  %sx%s  %s  (%s)" % (x["score"], x.get("w"), x.get("h"), os.path.basename(x["path"]), x["origin"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
