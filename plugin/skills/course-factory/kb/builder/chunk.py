# -*- coding: utf-8 -*-
"""Cutting a document into searchable pieces - one page per piece where it can be.

A piece ends at the end of its page once it holds 400 characters (150 for a slide); a short page is joined to the next
ones up to 2 800 characters; a long page is cut at a chapter heading or at a paragraph so no piece passes 4 200. So a
piece names the page it came from, and a fact is cited "p.40", not "p.40-41". Where a piece does span pages, an inline
[page N] marker shows where each page starts. Tables and pictures are pieces of their own; the page text carries only
their marker, so a table's words are indexed once.

The navigational test (tables of contents, indexes) and the table and picture pieces are ported from the Course
Source Processor (csp/chunker.py). Running headers never reach a piece: the PDF reader leaves them out (pdf.py).
"""
from __future__ import annotations

import re

from common import SETTINGS, table_indexed, table_markdown, unit_label

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+", re.U)
_TOKEN = re.compile(r"[^\W_]+", re.UNICODE)
_INTEGER = re.compile(r"^\d{1,4}$")
_DOT_LEADER = re.compile(r"\.{4,}")
_HEADING = re.compile(r"^(#{3,6})\s+(.*)$")
UNIT_MIN = {"page": 400, "slide": 150, "section": 400, "image": 0}


def is_navigational(text):
    """A table of contents, list of figures or book index: 26-74 % bare page numbers, against 0-4 % in body text."""
    if len(_DOT_LEADER.findall(text)) >= 3:
        return True
    tokens = _TOKEN.findall(text)
    if len(tokens) < 40:
        return False
    numbers = sum(1 for t in tokens if _INTEGER.match(t))
    return numbers >= 15 and numbers / len(tokens) >= 0.18


def _heading_of(block):
    m = _HEADING.match(block.strip())
    return (m.group(2).strip(), max(1, len(m.group(1)) - 2)) if m else None


def split_long(text, maximum):
    """A paragraph longer than the maximum, cut at sentences (any capital letter, Latin or Cyrillic), else at a space."""
    sentences = []
    for s in _SENTENCE_SPLIT.split(text):
        first = s.lstrip("\"'([")[:1]
        if sentences and not (first.isupper() or first.isdigit()):
            sentences[-1] += " " + s
        else:
            sentences.append(s)
    parts, current = [], ""
    for sentence in sentences:
        candidate = (current + " " + sentence).strip() if current else sentence
        if len(candidate) <= maximum or not current:
            current = candidate
        else:
            parts.append(current)
            current = sentence
    if current:
        parts.append(current)
    final = []
    for part in parts:
        while len(part) > maximum:
            cut = part.rfind(" ", 0, maximum)
            cut = cut if cut > 0 else maximum
            final.append(part[:cut].strip())
            part = part[cut:].strip()
        if part:
            final.append(part)
    return final


def chunk_units(doc):
    """The text pieces of one document, in unit order."""
    target, maximum = SETTINGS["chunk_target_chars"], SETTINGS["chunk_max_chars"]
    minimum = UNIT_MIN.get(doc["unit_kind"], 400)
    chunks, stack = [], []
    state = {"buf": [], "len": 0, "p1": 0, "p2": 0, "path": [], "ocr": False, "last": 0}

    def path_now():
        return [t for _, t in stack]

    def flush():
        if state["buf"]:
            text = "\n\n".join(state["buf"]).strip()
            if text:
                chunks.append({"chunk_id": "%s#c%04d" % (doc["doc_id"], len(chunks) + 1), "kind": "text",
                               "doc_id": doc["doc_id"], "source_filename": doc["filename"], "source_path": doc["rel"],
                               "unit_kind": doc["unit_kind"], "page_start": state["p1"], "page_end": state["p2"],
                               "heading_path": list(state["path"]), "text": text, "navigational": is_navigational(text),
                               "from_ocr": state["ocr"]})
        state.update(buf=[], len=0, p1=0, p2=0, ocr=False, last=0, path=path_now(), body=False, carry=False)

    def add(number, piece, ocr):
        if state["buf"] and state["len"] + len(piece) > maximum:
            flush()
        if not state["buf"]:
            state["p1"], state["path"], state["last"] = number, path_now(), number
        elif state.get("carry") and number != state["last"]:
            # only headings and markers came from the page before (a chapter line at the foot of a page): the
            # piece belongs to this page
            state["p1"] = state["last"] = number
        elif number != state["last"]:
            state["buf"].append("[page %d]" % number)
            state["len"] += 12
            state["last"] = number
        state["carry"] = False
        state["buf"].append(piece)
        state["len"] += len(piece) + 2
        state["p2"] = number
        state["ocr"] = state["ocr"] or ocr
        if not (piece.startswith("#") or piece.startswith("[[")):
            state["body"] = True

    for unit in doc["pages"]:
        body = (unit.get("text") or "").strip()
        if not body:
            continue
        edges = set(unit.get("edge_blocks") or ())
        blocks = [b.strip() for b in body.split("\n\n") if b.strip() and b.strip() not in edges]
        if not blocks:
            continue
        size = sum(len(b) + 2 for b in blocks)
        # a short page waiting for the next one: joined only while the two stay under the target size
        if state["buf"] and state["len"] + size > target:
            flush()
        ocr = unit.get("method") == "ocr"
        for block in blocks:
            heading = _heading_of(block)
            if heading is not None:
                text, level = heading
                if (level == 1 and state["len"] >= minimum) or (level == 2 and state["len"] >= target):
                    flush()
                while stack and stack[-1][0] >= level:
                    stack.pop()
                stack.append((level, text))
                if not state["buf"]:
                    state["path"] = path_now()
            for piece in ([block] if len(block) <= maximum else split_long(block, maximum)):
                add(unit["number"], piece, ocr)
        if state["len"] >= minimum:
            flush()
        elif state["buf"] and not state.get("body"):
            state["carry"] = True
    flush()
    return chunks


def table_chunk(doc, table, ordinal, asset_path):
    limit = SETTINGS["chunk_max_chars"]
    loc = table["location"]
    header = ["[TABLE] %s" % (table["caption"] or "table"),
              "Source: %s | %s | grid %d rows x %d cols | quality %s%s"
              % (doc["filename"], unit_label(loc["kind"], loc["number"]), table["rows"], table["columns"],
                 table["quality"], (" (%s)" % table["quality_note"]) if table["quality_note"] else "")]
    if table["heading_path"]:
        header.append("Section: " + " > ".join(table["heading_path"]))
    body = table_markdown(table["cells"])
    if len(body) > limit:
        kept, used = [], 0
        for line in body.split("\n"):
            if used + len(line) > limit:
                kept.append("_(table truncated here - full grid in %s)_" % asset_path)
                break
            kept.append(line)
            used += len(line) + 1
        body = "\n".join(kept)
    return {"chunk_id": "%s#tc%04d" % (doc["doc_id"], ordinal), "kind": "table", "doc_id": doc["doc_id"],
            "source_filename": doc["filename"], "source_path": doc["rel"], "unit_kind": loc["kind"],
            "page_start": loc["number"], "page_end": loc["number"], "heading_path": list(table["heading_path"]),
            "text": "\n".join(header) + "\n\n" + body, "navigational": False, "asset_path": asset_path,
            "asset_id": table["table_id"]}


def image_chunk(doc, image, ordinal, asset_path):
    """A picture's piece: what the document says about it. None when it says nothing (the picture is still kept)."""
    context = "\n".join(x for x in (image["caption"], image["nearby_text"], image["ocr_text"]) if x and x.strip())
    if not context.strip():
        return None
    loc = image["location"]
    if image.get("standalone_source_file"):
        lines = ["[IMAGE] %s" % (image.get("original_filename") or doc["filename"]), "Source: %s" % doc["rel"],
                 "Knowledge Base asset: %s" % asset_path, "Size: %dx%d px" % (image["width"], image["height"])]
        if image["nearby_text"]:
            lines.append("Named and filed under: %s" % image["nearby_text"])
        lines.append("OCR text: none (the picture itself has not been read as text)")
    else:
        lines = ["[IMAGE] %s" % (image["caption"] or "image"),
                 "Source: %s | %s | %dx%d px" % (doc["filename"], unit_label(loc["kind"], loc["number"]),
                                                 image["width"], image["height"]),
                 "File: %s" % asset_path]
        if image["caption"]:
            lines.append("Caption: %s" % image["caption"])
        if image["nearby_text"]:
            lines.append("Text near this image: %s" % image["nearby_text"])
    return {"chunk_id": "%s#ic%04d" % (doc["doc_id"], ordinal), "kind": "image", "doc_id": doc["doc_id"],
            "source_filename": doc["filename"], "source_path": doc["rel"], "unit_kind": loc["kind"],
            "page_start": loc["number"], "page_end": loc["number"], "heading_path": [], "text": "\n".join(lines),
            "navigational": False, "asset_path": asset_path, "asset_id": image["image_id"]}


def asset_chunks(doc, assets):
    out = []
    for i, table in enumerate(doc["tables"], 1):
        if table_indexed(table):
            out.append(table_chunk(doc, table, i, assets["tables"].get(table["table_id"], "")))
    for i, image in enumerate(doc["images"], 1):
        c = image_chunk(doc, image, i, assets["images"].get(image["image_id"], ""))
        if c:
            out.append(c)
    return out
