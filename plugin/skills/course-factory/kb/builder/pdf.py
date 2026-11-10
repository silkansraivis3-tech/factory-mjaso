# -*- coding: utf-8 -*-
"""Reading a PDF: page text with headings, ruled tables, pictures, and which pages are scans.

A PDF is read in two steps, both run in the worker processes (pool.py): doc_stats() reads a sample of 40 pages once -
the body font size, the running headers, the hyphenated words, the language of the text layer - and extract_range()
then reads up to 40 pages at a time with what doc_stats found. Pictures are never decoded to read text (PyMuPDF's
default "dict" decodes every picture: 0.26 s a page on a scanned book), and only the pictures that are kept are taken
out of the file. Scanned pages are only found here; ocr_page() reads them, one task each.
"""
from __future__ import annotations

import contextlib
import io
import os
import re
from collections import Counter

import common
import lang as langmod
import ocr as ocrmod
from common import SETTINGS
from structure import (Line, big_heading_sizes, body_font_size, build_page_text, hyphen_vocabulary, reflow_columns)

_BOLD = 1 << 4
_DIGITS = re.compile(r"\d+")
EDGE = 0.08                      # top and bottom share of the page where a running header or footer sits
SAMPLE = 40
RANGE = 40


def _pymupdf():
    import pymupdf
    try:
        pymupdf.TOOLS.mupdf_display_errors(False)
        pymupdf.TOOLS.mupdf_display_warnings(False)
    except Exception:                                        # noqa: BLE001 - older versions have no such switch
        pass
    return pymupdf


def open_pdf(path):
    pymupdf = _pymupdf()
    try:
        doc = pymupdf.open(path)
    except Exception as e:                                   # noqa: BLE001
        raise ValueError("the file could not be opened as a PDF - it may be damaged, incomplete, or not really a PDF "
                         "(%s)" % e)
    if doc.needs_pass:
        doc.close()
        raise ValueError("PDF is password protected")
    return doc


def page_lines(page):
    """[[Line]] text blocks of a page, pictures left undecoded."""
    pymupdf = _pymupdf()
    raw = page.get_text("dict", flags=pymupdf.TEXTFLAGS_DICT & ~pymupdf.TEXT_PRESERVE_IMAGES)
    blocks = []
    for block in raw.get("blocks", []):
        if block.get("type") != 0:
            continue
        lines = []
        for line in block.get("lines", []):
            spans = line.get("spans", [])
            text = "".join(s.get("text", "") for s in spans)
            if not spans or not text.strip():
                continue
            dominant = max(spans, key=lambda s: len(s.get("text", "")) or 1)
            bold_chars = sum(len(s.get("text", "")) for s in spans
                             if (int(s.get("flags", 0)) & _BOLD) or "bold" in str(s.get("font", "")).lower())
            x0, y0, x1, y1 = line.get("bbox", (0.0, 0.0, 0.0, 0.0))
            lines.append(Line(text, float(dominant.get("size", 0.0) or 0.0), bold_chars * 2 >= max(len(text), 1),
                              float(x0), float(y0), float(x1), float(y1)))
        if lines:
            blocks.append(lines)
    return blocks


def edge_key(line, height):
    """The running-header key of a line at the top or bottom edge of the page (digits as '#'), or None."""
    if height <= 0 or not (line.y0 < height * EDGE or line.y1 > height * (1 - EDGE)):
        return None
    text = common.tidy(line.text)
    if not text or len(text) > 90:
        return None
    return _DIGITS.sub("#", text.lower())


def doc_stats(path):
    """What a PDF's reading needs to know from the whole document, from a sample of its pages."""
    doc = open_pdf(path)
    try:
        n = doc.page_count
        meta = doc.metadata or {}
        if n <= SAMPLE:
            picks = list(range(n))
        else:
            stride = n / float(SAMPLE)
            picks = sorted({min(n - 1, int(i * stride)) for i in range(SAMPLE)})
        sample, edges, text_pages, words = [], Counter(), 0, []
        for i in picks:
            try:
                page = doc[i]
                blocks = page_lines(page)
            except Exception:                                # noqa: BLE001 - one bad page does not stop the sample
                continue
            lines = [l for b in blocks for l in b]
            sample.append(lines)
            if sum(len(l.text) for l in lines) >= SETTINGS["min_chars_per_page"]:
                text_pages += 1
            keys = {edge_key(l, page.rect.height) for l in lines}
            edges.update(k for k in keys if k)
            words.append(" ".join(l.text for l in lines))
        body = body_font_size(sample)
        threshold = max(3, int(text_pages * 0.25))
        headers = sorted(k for k, c in edges.items() if c >= threshold) if text_pages >= 4 else []
        text = "\n".join(words)
        return {"pages": n, "title": meta.get("title") or None, "author": meta.get("author") or None,
                "body_size": body, "big_sizes": big_heading_sizes(sample, body), "headers": headers,
                "vocab": sorted(hyphen_vocabulary(text)), "language": langmod.lang_of(text[:40000])}
    finally:
        doc.close()


def _within(line, rect, pad=1.0):
    """The whole line lies in the region - so every word of it is in the table that covers the region. A line that
    only reaches into a table stays in the page text."""
    return (rect[0] - pad <= line.x0 and line.x1 <= rect[2] + pad
            and rect[1] - pad <= line.y0 and line.y1 <= rect[3] + pad)


def _near(blocks, bbox, reach, side_reach):
    """[(distance, text)] of the text blocks above, below or beside a region."""
    x0, y0, x1, y1 = bbox
    out = []
    for block in blocks:
        bx0, by0 = min(l.x0 for l in block), min(l.y0 for l in block)
        bx1, by1 = max(l.x1 for l in block), max(l.y1 for l in block)
        if bx1 < x0 - side_reach or bx0 > x1 + side_reach:
            continue
        if by1 <= y0:
            d = y0 - by1
        elif by0 >= y1:
            d = by0 - y1
        else:
            d = 0.0
        text = common.tidy(" ".join(l.text for l in block))
        if text and d <= reach:
            out.append((d, text))
    out.sort(key=lambda x: x[0])
    return out


def caption_near(blocks, bbox):
    if not bbox:
        return ""
    return common.pick_caption([t for d, t in _near(blocks, bbox, 60, 40) if d > 0])


def nearby_text(blocks, bbox):
    if not bbox:
        return ""
    return common.tidy(" ".join(t for _, t in _near(blocks, bbox, 140, 80)), 600)


def _overlap(w, c):
    return max(0.0, min(w[2], c[2]) - max(w[0], c[0])) * max(0.0, min(w[3], c[3]) - max(w[1], c[1]))


def words_inside(words, bbox, pad=1.0):
    """The page words whose centre lies in a region."""
    x0, y0, x1, y1 = bbox
    return [w for w in words if x0 - pad <= (w[0] + w[2]) / 2 <= x1 + pad and y0 - pad <= (w[1] + w[3]) / 2 <= y1 + pad]


def fill_cells(rows_cells, words):
    """(grid, words left over): cell text made from WHOLE words. A word goes to the one cell that holds most of it -
    never cut at a cell edge, which split part numbers in two ("63 | 4181" for 634181). rows_cells is a list of rows,
    each a list of cell rectangles (None for a position covered by a merged cell)."""
    grid = [["" for _ in row] for row in rows_cells]
    owner = {}
    left = []
    for w in words:
        best, where = 0.0, None
        for r, row in enumerate(rows_cells):
            for c, cell in enumerate(row):
                if cell is not None:
                    a = _overlap(w, cell)
                    if a > best:
                        best, where = a, (r, c)
        if where is None:
            left.append(w)
        else:
            owner.setdefault(where, []).append(w)
    for (r, c), ws in owner.items():
        ws.sort(key=lambda w: (w[5], w[6], w[7]))           # block, line, word: the page's own reading order
        grid[r][c] = " ".join(w[4] for w in ws)
    return grid, left


def page_tables(page, number, blocks, rejected):
    """Tables found from ruling lines on one page (PyMuPDF's own finder, lines strategy only). The finder's grid is
    kept; the cell text is made from the page's whole words (fill_cells). A table that cannot hold every word inside
    it is not kept - its words stay in the page text."""
    found = []
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            candidates = list(page.find_tables().tables)
    except Exception:                                        # noqa: BLE001 - table finding is never fatal
        return found
    words = None
    for cand in candidates[:SETTINGS["tables_max_per_page"]]:
        bbox = [float(x) for x in cand.bbox]
        try:
            rows_cells = [[(None if c is None else [float(v) for v in c]) for c in row.cells] for row in cand.rows]
        except Exception:                                    # noqa: BLE001
            continue
        if len(rows_cells) < 2:
            continue
        if words is None:
            words = page.get_text("words")
        rows, left = fill_cells(rows_cells, words_inside(words, bbox))
        if left:
            rejected.append({"unit": number, "reason": "%d word(s) inside the table fall in no cell (e.g. %s) - kept as "
                                                       "page text, not as a table" % (len(left), left[0][4]),
                             "detector": "pymupdf-find_tables:lines", "rows": len(rows_cells),
                             "columns": max(len(r) for r in rows_cells)})
            continue
        t = common.make_table("", 0, "page", number, rows, "pymupdf-find_tables:lines",
                              caption=caption_near(blocks, bbox), ruled_grid=True, rejected=rejected, bbox=bbox)
        if t:
            found.append(t)
    return found


def _store_image(store, sha, ext, data):
    folder = os.path.join(store, sha[:2])
    path = os.path.join(folder, "%s.%s" % (sha, ext))
    if not os.path.isfile(path):
        os.makedirs(folder, exist_ok=True)
        tmp = path + ".%d.part" % os.getpid()
        with open(tmp, "wb") as f:
            f.write(data)
        try:
            os.replace(tmp, path)
        except OSError:
            if os.path.exists(tmp):
                os.remove(tmp)
    return path


def page_images(doc, page, number, blocks, store, memo):
    """The pictures worth keeping on one page, each saved once in the picture store. Sizes and positions come from
    get_image_info (nothing decoded); only a picture that passes every size test is taken out of the file."""
    s = SETTINGS
    out, seen, cover = [], set(), 0.0
    try:
        infos = page.get_image_info(xrefs=True)
    except Exception:                                        # noqa: BLE001
        return out, cover
    rect = page.rect
    area = float(rect.width * rect.height) or 1.0
    aspect = float(rect.width) / float(rect.height or 1)
    for info in infos:
        bbox = [float(x) for x in info.get("bbox", (0, 0, 0, 0))]
        w_pt, h_pt = max(0.0, bbox[2] - bbox[0]), max(0.0, bbox[3] - bbox[1])
        cover = max(cover, w_pt * h_pt / area)
        xref = info.get("xref") or 0
        if not xref or xref in seen:
            continue
        seen.add(xref)
        width, height = int(info.get("width") or 0), int(info.get("height") or 0)
        if width and height:
            if common.is_decorative(width, height, 0):
                continue
            if (min(width, height) >= s["page_scan_min_pixels"]
                    and abs(width / float(height) - aspect) <= s["page_scan_aspect_tolerance"]):
                continue                                     # the scan of the page itself
        if w_pt * h_pt / area >= s["images_max_page_coverage"]:
            continue
        if w_pt < s["images_min_points_on_page"] or h_pt < s["images_min_points_on_page"]:
            continue
        if xref not in memo:
            try:
                got = doc.extract_image(xref)
            except Exception:                                # noqa: BLE001
                got = None
            data = (got or {}).get("image")
            if not data:
                memo[xref] = None
            else:
                ext = str(got.get("ext") or "png").lower()
                gw, gh = int(got.get("width") or 0), int(got.get("height") or 0)
                if common.is_decorative(gw, gh, len(data)):
                    memo[xref] = None
                else:
                    sha = common.sha256_bytes(data)
                    _store_image(store, sha, ext, data)
                    memo[xref] = (sha, ext, gw, gh, len(data))
        kept = memo[xref]
        if kept:
            sha, ext, gw, gh, size = kept
            out.append({"sha256": sha, "ext": ext, "width": gw, "height": gh, "byte_size": size, "bbox": bbox,
                        "caption": caption_near(blocks, bbox), "nearby_text": nearby_text(blocks, bbox)})
    return out, cover


def _near_white(page):
    """True when the page shows (almost) nothing when drawn small - a blank scan, a white back cover."""
    pymupdf = _pymupdf()
    try:
        pix = page.get_pixmap(matrix=pymupdf.Matrix(0.25, 0.25), colorspace=pymupdf.csGRAY, alpha=False)
    except Exception:                                        # noqa: BLE001
        return False
    data = pix.samples
    dark = len(data) - len(data.translate(None, bytes(range(200))))
    return dark / float(len(data) or 1) < 0.001          # five lines of print are 0.017; a single line about 0.003


def _insert_markers(blocks, markers):
    """Table markers go where the table sits on the page: before the first block that starts below it."""
    out = list(blocks)
    for y, marker in sorted(markers, key=lambda m: m[0], reverse=True):
        at = len(out)
        for i, b in enumerate(out):
            if not isinstance(b, str) and min(l.y0 for l in b) >= y:
                at = i
                break
        out.insert(at, marker)
    return out


def read_page(doc, page, number, ctx, memo):
    """One page: its text (running headers left out, the words of an indexed table left to the table), its tables,
    its pictures and whether it is a scan."""
    height = page.rect.height
    headers = set(ctx["headers"])
    raw = page_lines(page)
    excluded, top, bottom, blocks = set(), [], [], []
    for b in raw:
        kept = []
        for l in b:
            k = edge_key(l, height) if headers else None
            if k and k in headers:
                excluded.add(k)
                (top if l.y0 < height / 2 else bottom).append(l)
            else:
                kept.append(l)
        if kept:
            blocks.append(kept)
    native = sum(len(l.text.strip()) for b in raw for l in b)
    edges = [common.tidy(" ".join(l.text for l in sorted(side, key=lambda l: (l.y0, l.x0)))) for side in (top, bottom)]
    try:
        drawings = len(page.get_cdrawings())
    except Exception:                                        # noqa: BLE001
        drawings = 0
    flow, columns = reflow_columns(blocks)

    tables, rejected = [], []
    if ctx["tables"] and (columns > 1 or drawings >= SETTINGS["pdf_vector_hint"]):
        tables = page_tables(page, number, blocks, rejected)
    markers = []
    for k, t in enumerate(tables):
        t["key"] = "p%dt%d" % (number, k)
        if common.table_indexed(t):
            flow = [[l for l in b if not _within(l, t["bbox"])] if not isinstance(b, str) else b for b in flow]
            flow = [b for b in flow if isinstance(b, str) or b]
        markers.append((t["bbox"][1], "[[TABLE ?%s]]" % t["key"]))
    flow = _insert_markers(flow, markers)

    images, cover = ([], 0.0)
    if ctx["images"]:
        images, cover = page_images(doc, page, number, blocks, ctx["store"], memo)
    else:
        try:
            area = float(page.rect.width * page.rect.height) or 1.0
            cover = max([0.0] + [(i["bbox"][2] - i["bbox"][0]) * (i["bbox"][3] - i["bbox"][1]) / area
                                 for i in page.get_image_info()])
        except Exception:                                    # noqa: BLE001
            cover = 0.0
    for k, im in enumerate(images):
        im["key"] = "p%di%d" % (number, k)

    vocab = set(ctx["vocab"]) | hyphen_vocabulary(" ".join(l.text for b in blocks for l in b))
    text, headings = build_page_text(flow, ctx["body_size"], ctx["big_sizes"], tabular=columns > 1, vocab=vocab)
    if images:
        text = (text + "\n\n" + "\n\n".join("[[IMAGE ?%s]]" % im["key"] for im in images)).strip()

    minimum = SETTINGS["min_chars_per_page"]
    has_ink = cover > 0 or drawings > 0
    scanned = blank = False
    if native < minimum:
        if not has_ink or _near_white(page):
            blank = native == 0
            scanned = False
        else:
            scanned = True
    elif cover >= SETTINGS["images_max_page_coverage"] and native < 400:
        scanned = True                                       # a scan carrying a thin text layer (a stamp, a number)
    raw_text = "\n".join(l.text for b in raw for l in b)
    kept_text = "\n".join([text] + edges + [c for t in tables for row in t["cells"] for c in row])
    return {"number": number, "text": text, "headings": headings, "native_chars": native, "columns": columns,
            "tables": tables, "images": images, "rejected": rejected, "scanned": scanned, "blank": blank,
            "thin_layer": scanned and native >= minimum, "excluded": sorted(excluded), "edges": edges,
            "word_count": word_counts(raw_text, kept_text)}


_TOK = re.compile(r"[^\W_]+", re.U)
_MARKER_LINE = re.compile(r"^\[\[(TABLE|IMAGE) [^\]]*\]\]$", re.M)


def word_counts(raw_text, kept_text):
    """[words on the page, words kept, a few lost ones]: every word of the page's text layer must be in what the
    knowledge base keeps of the page (its text, its running headers, its tables). A word joined across a line-end
    hyphen ("pump-" + "room" -> "pumproom") counts as kept."""
    raw = Counter(t.lower() for t in _TOK.findall(_MARKER_LINE.sub("", raw_text)))
    kept = Counter(t.lower() for t in _TOK.findall(_MARKER_LINE.sub("", kept_text)))
    longer = [k for k in kept if len(k) > 2]
    lost, sample = 0, []
    for t, n in (raw - kept).items():
        if any(k != t and (k.startswith(t) or k.endswith(t)) for k in longer):
            continue
        lost += n
        if len(sample) < 8:
            sample.append(t)
    total = sum(raw.values())
    return [total, total - lost, sample]


def extract_range(path, first, last, ctx):
    """Pages first..last (1-based, inclusive) of one PDF. A page that cannot be read is one failed page."""
    doc = open_pdf(path)
    memo, out = {}, []
    try:
        for number in range(first, last + 1):
            try:
                out.append(read_page(doc, doc[number - 1], number, ctx, memo))
            except Exception as e:                           # noqa: BLE001 - one bad page must not lose the rest
                out.append({"number": number, "text": "", "headings": [], "native_chars": 0, "columns": 1,
                            "tables": [], "images": [], "rejected": [], "scanned": False, "blank": False,
                            "thin_layer": False, "excluded": [], "word_count": [0, 0, []], "failed": str(e)[:200]})
    finally:
        doc.close()
    return out


def ocr_page(path, number, tessdata, models, prior, forced, dpi):
    """One scanned page read by OCR: {number, text, headings, language, rotation, quality, note, seconds}."""
    import time
    started = time.time()
    doc = open_pdf(path)
    try:
        page = doc[number - 1]
        # No second try at 300 dpi when nothing is found: measured on the IMO model course covers, a photograph read
        # at 300 dpi gives 5 000-7 000 characters of noise (word quality 0.2-0.3) and costs 20-30 s.
        got = ocrmod.read_scanned_page(page, tessdata, set(models), prior=prior, forced=forced, dpi=dpi)
    finally:
        doc.close()
    text, headings = build_page_text(got["blocks"], 0.0, [], vocab=hyphen_vocabulary(got["text"]))
    return {"number": number, "text": text, "headings": headings, "language": got["language"],
            "rotation": got["rotation"], "quality": got["quality"], "note": got["note"], "cover": got.get("cover"),
            "print_cells": got.get("print_cells"), "low": bool(got.get("low")),
            "seconds": round(time.time() - started, 2)}
