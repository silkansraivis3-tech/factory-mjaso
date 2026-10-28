# -*- coding: utf-8 -*-
"""placeholder.py - the grey picture a photo slot holds between Phase A and Phase B (2.73.0). Never shipped.

    import placeholder
    rel = placeholder.write(mdir, "s05", "4:3", "A deepwell pump's top plate")    -> "assets/img/_placeholder_s05.png"
    placeholder.is_placeholder(path)                                             -> True for one of these files
    placeholder.found(mdir)                                                      -> [rel, ...] still in a module

WHY (chem advanced, 2026-10-27): build_module.py refused to start a module with no agent - "the build sheet still has the
starter's blanks - fill s07: its picture". Choosing a picture is the one judgement in a build; everything else (the words,
the layout, the navigation, the tasks grading right and wrong, the text audits, the course package) does not depend on it.
`compile_module.py --init-build` now fills every photo slot with one of these, at the slot's own shape (the script's
"picture": {"aspect"}) and 1600 px on its long side, so the pre-check passes and the whole build runs with no agent (Phase A).
The picture itself is chosen afterwards from MNN_VISUAL_NEEDS.md (Phase B, or --auto from the course photo catalogue).

A placeholder is told by the file itself, not by a record that can be lost: a PNG text chunk "novikontas-placeholder" with
the slot it holds. build_module.py never says PASS while one is named (PHASE A CLEAN instead), and check_course_package.py
refuses a module that still has one. Pure standard library (zlib) - no imaging package needed.
"""
from __future__ import annotations

import io
import json
import os
import re
import struct
import zlib

MARK = b"novikontas-placeholder"
LONG = 1600                      # px on the long side: the pre-check's photograph floor (L62) is 800, the target 1600
GREY, EDGE = (214, 219, 226), (150, 160, 175)
NAME = "_placeholder_%s.png"
REL = "assets/img/" + NAME
RECORD_SOURCE = "course-factory placeholder (Phase A) - not a picture: replaced before the module passes"


def size_of(aspect):
    """(w, h) at LONG px on the long side for "16:9" / "4:3" / "1:1" ... - 4:3 when it is not a ratio"""
    m = re.match(r"^\s*(\d+(?:\.\d+)?)\s*:\s*(\d+(?:\.\d+)?)\s*$", str(aspect or ""))
    r = float(m.group(1)) / float(m.group(2)) if m and float(m.group(2)) else 4 / 3.0
    r = min(4.0, max(0.25, r))
    return (LONG, max(1, round(LONG / r))) if r >= 1 else (max(1, round(LONG * r)), LONG)


def _chunk(kind, data):
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)


def png(w, h, slot):
    """a light grey picture with a darker frame and a cross - plainly not a photograph on a review sheet - carrying its mark"""
    edge = max(4, w // 160)
    rows = []
    for y in range(h):
        if y < edge or y >= h - edge:
            row = bytes(EDGE) * w
        else:
            line = bytearray(bytes(GREY) * w)
            for x in list(range(edge)) + list(range(w - edge, w)):
                line[3 * x:3 * x + 3] = bytes(EDGE)
            for x in {round(y * (w - 1) / max(1, h - 1)), round((h - 1 - y) * (w - 1) / max(1, h - 1))}:
                for dx in range(-1, 2):
                    if 0 <= x + dx < w:
                        line[3 * (x + dx):3 * (x + dx) + 3] = bytes(EDGE)
            row = bytes(line)
        rows.append(b"\x00" + row)
    raw = zlib.compress(b"".join(rows), 9)
    text = MARK + b"\x00" + str(slot).encode("ascii", "replace")
    return (b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)) + _chunk(b"tEXt", text)
            + _chunk(b"IDAT", raw) + _chunk(b"IEND", b""))


def is_placeholder(path):
    """the file carries the placeholder mark (it is in the first chunks, before the picture data)"""
    try:
        with io.open(path, "rb") as f:
            head = f.read(256)
    except OSError:
        return False
    return head.startswith(b"\x89PNG") and MARK in head


def write(mdir, slot, aspect=None, shows=""):
    """the placeholder of one slot in the module's assets/img, with its record - the module-relative path. An existing one is
    rewritten (its shape may have changed); a real picture of the same name is never touched"""
    img = os.path.join(mdir, "assets", "img")
    os.makedirs(img, exist_ok=True)
    name = NAME % slot
    p = os.path.join(img, name)
    if os.path.isfile(p) and not is_placeholder(p):
        raise ValueError("%s is a real picture, not a placeholder" % p)
    w, h = size_of(aspect)
    io.open(p, "wb").write(png(w, h, "%s %s" % (os.path.basename(os.path.normpath(mdir)), slot)))   # its own bytes in each module
    mp = os.path.join(img, "_photo_meta.json")
    try:
        meta = json.load(io.open(mp, encoding="utf-8"))
    except (OSError, ValueError):
        meta = {}
    meta[name] = {"placeholder": True, "title": "Placeholder for %s" % slot,
                  "description": "Placeholder - the picture still to come: %s" % (shows or "see MNN_VISUAL_NEEDS.md"),
                  "source": RECORD_SOURCE, "author": "course-factory", "license": "placeholder", "rights_state": "PLACEHOLDER",
                  "width": w, "height": h, "used_in": slot}
    io.open(mp, "w", encoding="utf-8", newline="\n").write(json.dumps(meta, ensure_ascii=False, indent=2) + "\n")
    return REL % slot


def remove(mdir, slot):
    """the placeholder and its record gone, once the slot holds its real picture"""
    img = os.path.join(mdir, "assets", "img")
    p = os.path.join(img, NAME % slot)
    if os.path.isfile(p) and is_placeholder(p):
        os.remove(p)
    mp = os.path.join(img, "_photo_meta.json")
    try:
        meta = json.load(io.open(mp, encoding="utf-8"))
    except (OSError, ValueError):
        return
    if meta.pop(NAME % slot, None) is not None:
        io.open(mp, "w", encoding="utf-8", newline="\n").write(json.dumps(meta, ensure_ascii=False, indent=2) + "\n")


def is_record(meta):
    """a _photo_meta.json record that is a placeholder's - never a picture for the L57 photo row, a tile or a thumbnail"""
    return isinstance(meta, dict) and (meta.get("placeholder") is True or str(meta.get("rights_state") or "").upper() == "PLACEHOLDER")


def found(mdir):
    """every placeholder file still in the module folder, module-relative ("assets/img/_placeholder_s05.png")"""
    out = []
    for root, dirs, files in os.walk(mdir):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for f in files:
            if f.lower().endswith(".png") and is_placeholder(os.path.join(root, f)):
                out.append(os.path.relpath(os.path.join(root, f), mdir).replace(os.sep, "/"))
    return sorted(out)
