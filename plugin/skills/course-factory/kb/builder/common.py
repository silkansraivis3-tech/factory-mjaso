# -*- coding: utf-8 -*-
"""Small pieces every reader uses: tidy text, captions, decorative pictures, picture sizes, table grids.

Ported from the Course Source Processor (csp/extractors/base.py, csp/model.py): the caption words, the decorative-picture
test, the layout-box test and the grid quality rules are the owner's, unchanged. The picture size is read from the
file's own header, so no picture is decoded to learn how big it is.
"""
from __future__ import annotations

import hashlib
import re
import struct

QUALITY_GOOD, QUALITY_PARTIAL, QUALITY_REVIEW = "GOOD", "PARTIAL", "NEEDS_REVIEW"
QUALITY_ORDER = {QUALITY_REVIEW: 0, QUALITY_PARTIAL: 1, QUALITY_GOOD: 2}

# the Course Source Processor's own defaults (its config.json), the ones that change what is read
SETTINGS = {
    "min_chars_per_page": 60,
    "scanned_document_page_ratio": 0.5,
    "chunk_target_chars": 2800,
    "chunk_max_chars": 4200,
    "chunk_min_chars": 400,
    "pdf_vector_hint": 8,
    "tables_max_per_page": 6,
    "inline_rows_in_document": 40,
    "images_min_pixels": 90,
    "images_min_area_pixels": 20000,
    "images_min_bytes": 3000,
    "images_max_aspect_ratio": 12.0,
    "images_max_per_document": 300,
    "images_max_page_coverage": 0.85,
    "images_min_points_on_page": 40.0,
    "page_scan_min_pixels": 600,
    "page_scan_aspect_tolerance": 0.02,
    "docx_section_heading_level": 1,
    "docx_max_section_chars": 12000,
    "ocr_dpi": 200,
}

_WS = re.compile(r"\s+")
_CAPTION = re.compile(
    r"^\s*(fig\.?|figure|table|tab\.?|diagram|picture|photo|image|chart|graph"
    r"|attēls|att\.?|tabula|zīm\.?|рис\.?|рисунок|таблица)\s*"
    r"[\s\-–—:.]*[\dIVXА-Яa-zA-Z]", re.IGNORECASE)


def tidy(text, limit=0):
    cleaned = _WS.sub(" ", text or "").strip()
    if limit and len(cleaned) > limit:
        cleaned = cleaned[:limit].rstrip() + "..."
    return cleaned


def looks_like_caption(text):
    stripped = (text or "").strip()
    return bool(stripped) and len(stripped) <= 300 and bool(_CAPTION.match(stripped))


def pick_caption(candidates):
    """The first candidate that reads like a caption, else ''."""
    for text in candidates:
        if looks_like_caption(text):
            return tidy(text, 300)
    return ""


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


# ------------------------------------------------------------------ pictures
def is_decorative(width, height, byte_size):
    """Icons, bullets, rules and logos - judged by size alone, as the Course Source Processor does."""
    s = SETTINGS
    if width and height:
        if width < s["images_min_pixels"] or height < s["images_min_pixels"]:
            return True
        if width * height < s["images_min_area_pixels"]:
            return True
        if max(width, height) / max(1, min(width, height)) > s["images_max_aspect_ratio"]:
            return True
    return bool(byte_size and byte_size < s["images_min_bytes"])


def image_size(data):
    """(width, height) from a PNG, JPEG, GIF or BMP header, without decoding the picture. (0, 0) when unknown."""
    try:
        if data[:8] == b"\x89PNG\r\n\x1a\n":
            return struct.unpack(">II", data[16:24])
        if data[:6] in (b"GIF87a", b"GIF89a"):
            return struct.unpack("<HH", data[6:10])
        if data[:2] == b"BM":
            w, h = struct.unpack("<ii", data[18:26])
            return abs(w), abs(h)
        if data[:2] == b"\xff\xd8":
            i, n = 2, len(data)
            while i + 9 < n:
                if data[i] != 0xFF:
                    i += 1
                    continue
                marker = data[i + 1]
                if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:
                    i += 2
                    continue
                length = struct.unpack(">H", data[i + 2:i + 4])[0]
                if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                    h, w = struct.unpack(">HH", data[i + 5:i + 9])
                    return w, h
                i += 2 + length
    except (struct.error, IndexError):
        pass
    return 0, 0


def image_size_any(data):
    """image_size, and PyMuPDF's own reading of the header for any other kind (TIFF, WebP, ...)."""
    w, h = image_size(data)
    if w and h:
        return w, h
    try:
        import pymupdf
        pix = pymupdf.Pixmap(data)
        return pix.width, pix.height
    except Exception:                                      # noqa: BLE001 - EMF, WMF, damaged: size unknown
        return 0, 0


def image_record(doc_id, ordinal, unit_kind, number, sha, ext, width, height, byte_size, bbox=None, caption="",
                 nearby=""):
    return {"image_id": "%s#i%04d" % (doc_id, ordinal), "doc_id": doc_id,
            "location": {"kind": unit_kind, "number": number}, "file": "", "sha256": sha, "width": int(width or 0),
            "height": int(height or 0), "byte_size": int(byte_size or 0), "bbox": bbox, "caption": caption,
            "nearby_text": tidy(nearby, 600), "ocr_text": "", "standalone_source_file": False, "original_filename": None,
            "ext": (ext or "png").lower().lstrip(".")}


# ------------------------------------------------------------------ tables
def layout_box_reason(rows):
    """Is this PDF grid a boxed area of the page rather than a table? The reason, or None."""
    cells = [(c or "").strip() for row in rows for c in row]
    populated = [c for c in cells if c]
    if not populated:
        return None
    longest = max(len(c) for c in populated)
    if longest < 200:
        return None
    if len(populated) <= 2:
        return ("all %d filled cell(s) in one block of %d characters - a boxed area of the page, not a table"
                % (len(populated), longest))
    columns = {i for row in rows for i, c in enumerate(row) if (c or "").strip()}
    if len(columns) < 2:
        return ("every filled cell is in one column and one holds %d characters - a framed text panel, not a table"
                % longest)
    share = longest / max(1, sum(len(c) for c in populated))
    if share >= 0.70 and len(populated) <= 4:
        return ("one cell holds %d%% of the text across only %d filled cells - a boxed area, not a table"
                % (round(share * 100), len(populated)))
    return None


def assess_table(rows, trusted_grid=False, ruled_grid=False):
    """Judge the grid, not the content: (quality, note)."""
    if not rows:
        return QUALITY_REVIEW, "no rows detected"
    widths = {len(r) for r in rows}
    if max(widths) < 2:
        return QUALITY_REVIEW, "only one column detected"
    cells = [c for row in rows for c in row]
    filled_cells = [c.strip() for c in cells if c and c.strip()]
    empty_share = 1.0 - len(filled_cells) / max(1, len(cells))
    if not trusted_grid and filled_cells:
        single = sum(1 for c in filled_cells if len(c) == 1 and c.islower() and c.isalpha())
        lower_start = sum(1 for c in filled_cells if c[:1].islower())
        if single / len(filled_cells) > 0.10 or lower_start / len(filled_cells) > 0.25:
            return QUALITY_REVIEW, "cell boundaries appear to cut through words"
    if empty_share > 0.6:
        if trusted_grid:
            return QUALITY_PARTIAL, "%d%% of cells are empty (merged or layout cells)" % round(empty_share * 100)
        if ruled_grid:
            return QUALITY_PARTIAL, "%d%% of cells are empty (ruled grid, most likely a blank form)" % round(empty_share * 100)
        return QUALITY_REVIEW, "%d%% of cells are empty" % round(empty_share * 100)
    if len(widths) > 1:
        return QUALITY_PARTIAL, "rows have differing column counts"
    if len(rows) < 2:
        return QUALITY_PARTIAL, "only one row detected"
    if empty_share > 0.35:
        return QUALITY_PARTIAL, "%d%% of cells are empty" % round(empty_share * 100)
    return QUALITY_GOOD, ""


def make_table(doc_id, ordinal, unit_kind, number, rows, detector, caption="", heading_path=None, merged=None,
               trusted_grid=False, ruled_grid=False, rejected=None, bbox=None):
    """A table record, or None for an empty grid or a boxed page area (that one is added to `rejected`)."""
    cleaned = [[tidy(c) for c in row] for row in rows]
    cleaned = [row for row in cleaned if any(row)]
    if not cleaned:
        return None
    reason = None if trusted_grid else layout_box_reason(cleaned)
    if reason:
        if rejected is not None:
            rejected.append({"unit": number, "reason": reason, "detector": detector, "rows": len(cleaned),
                             "columns": max(len(r) for r in cleaned)})
        return None
    quality, note = assess_table(cleaned, trusted_grid=trusted_grid, ruled_grid=ruled_grid)
    return {"table_id": "%s#t%04d" % (doc_id, ordinal), "doc_id": doc_id,
            "location": {"kind": unit_kind, "number": number}, "rows": len(cleaned),
            "columns": max(len(r) for r in cleaned), "caption": caption, "heading_path": list(heading_path or []),
            "quality": quality, "quality_note": note, "merged_cells": list(merged or []), "detector": detector,
            "rectangular": len({len(r) for r in cleaned}) == 1, "cells": cleaned, "bbox": bbox}


def table_indexed(table):
    """Tables below PARTIAL are not indexed (their text stays in the page text instead)."""
    return QUALITY_ORDER.get(table["quality"], 0) >= QUALITY_ORDER[QUALITY_PARTIAL]


def table_markdown(cells):
    if not cells:
        return "_(empty table)_"
    width = max(len(r) for r in cells)

    def line(row):
        padded = list(row) + [""] * (width - len(row))
        return "| " + " | ".join(c.replace("|", "\\|").replace("\n", "<br>").strip() for c in padded) + " |"
    return "\n".join([line(cells[0]), "|" + "|".join([" --- "] * width) + "|"] + [line(r) for r in cells[1:]])


def table_text(table):
    """A table's cells as plain lines - for a grid that is not indexed on its own, so its words stay searchable."""
    return "\n".join(" ".join(c for c in row if c) for row in table["cells"] if any(row))


def unit_label(kind, number):
    return "%s %s" % (kind, number)


def table_marker(table):
    label = table["caption"] or " > ".join(table["heading_path"]) or "table"
    return "[[TABLE %s | %s | %d rows x %d cols | %s]]" % (table["table_id"], label, table["rows"], table["columns"],
                                                          table["quality"])


def image_marker(image):
    size = "%dx%d" % (image["width"], image["height"]) if image["width"] and image["height"] else "image"
    return "[[IMAGE %s | %s | %s]]" % (image["image_id"], image["caption"] or "image", size)


TABLE_MARKER = re.compile(r"^\[\[TABLE (?P<id>[^\s|\]]+)\s*\|(?P<rest>[^\]]*)\]\]$")
IMAGE_MARKER = re.compile(r"^\[\[IMAGE (?P<id>[^\s|\]]+)\s*\|(?P<rest>[^\]]*)\]\]$")
