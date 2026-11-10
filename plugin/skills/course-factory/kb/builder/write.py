# -*- coding: utf-8 -*-
"""Writing the knowledge base in the Course Source Processor's layout, so the factory reads it unchanged:

    KNOWLEDGE_BASE\\SOURCE_MANIFEST.json, COURSE_INDEX.md, NEEDS_ATTENTION.md (only when something needs a person)
    KNOWLEDGE_BASE\\sources\\<slug>__<hash>\\document.md, metadata.json, tables\\table_0001.md|.csv, images\\image_0001.<ext>
    KNOWLEDGE_BASE\\search_index\\chunks.jsonl, index.json   (index.py)

The file names, keys and wording follow the Course Source Processor (csp/output.py). Pictures come from the picture
store (cache.py), linked where the disk allows it, else copied.
"""
from __future__ import annotations

import csv
import io
import json
import os
import re
import shutil
from datetime import datetime, timezone

import cache
from common import IMAGE_MARKER, QUALITY_GOOD, SETTINGS, TABLE_MARKER, table_markdown, unit_label

TOOL = "COURSE FACTORY KB BUILDER"
_TOKEN = re.compile(r"[^\W_]+", re.U)
_MARKER = re.compile(r"^\[\[(TABLE|IMAGE) [^\]]*\]\]$", re.M)
NO_TEXT = ("_[No selectable text here. The page is most likely a scan or a graphic. See NEEDS_ATTENTION.md.]_")


def _write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with io.open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def _json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with io.open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def _place(src, dst):
    try:
        os.link(src, dst)
    except OSError:
        shutil.copyfile(src, dst)


def _unit_heading(doc, u):
    h = "## %s %d" % ((u.get("kind") or doc["unit_kind"]).capitalize(), u["number"])
    if u.get("label"):
        h += " - " + u["label"]
    if u.get("method") == "ocr":
        h += "  (text recovered by OCR)"
    return h


def _expand(block, tables, images, assets):
    s = block.strip()
    m = TABLE_MARKER.match(s)
    if m:
        t = tables.get(m.group("id"))
        if t is None:
            return s
        loc = t["location"]
        rows = SETTINGS["inline_rows_in_document"]
        path = assets["tables"].get(t["table_id"], "")
        lines = ["**Table - %s** (%s, %d rows x %d cols, quality %s)" % (t["caption"] or "table",
                                                                        unit_label(loc["kind"], loc["number"]),
                                                                        t["rows"], t["columns"], t["quality"])]
        if path:
            lines.append("_Grid also stored as_ `%s` _in_ `tables/`" % os.path.basename(path))
        lines.append("")
        lines.append(table_markdown(t["cells"][:rows]))
        if t["rows"] > rows:
            lines += ["", "_(%d more rows - see_ `%s` _)_" % (t["rows"] - rows, path)]
        return "\n".join(lines)
    m = IMAGE_MARKER.match(s)
    if m:
        im = images.get(m.group("id"))
        if im is None:
            return ""
        loc = im["location"]
        size = "%dx%d" % (im["width"], im["height"]) if im["width"] else "unknown size"
        where = "image file" if im.get("standalone_source_file") else unit_label(loc["kind"], loc["number"])
        lines = ["**Image - %s** (%s, %s)" % (im["caption"] or "image", where, size)]
        path = assets["images"].get(im["image_id"], "")
        if path:
            lines.append("_Stored as_ `%s` _in_ `images/`" % os.path.basename(path))
        return "\n".join(lines)
    return block


def write_source(kb, doc):
    """One source folder; returns {"tables": {id: path}, "images": {id: path}} relative to the knowledge base."""
    folder = os.path.join(kb, "sources", doc["slug"])
    rel = "sources/" + doc["slug"]
    os.makedirs(folder, exist_ok=True)
    assets = {"tables": {}, "images": {}}
    for i, t in enumerate(doc["tables"], 1):
        stem = "table_%04d" % i
        loc = t["location"]
        md = ["# %s (%s)" % (t["caption"] or "Table", unit_label(loc["kind"], loc["number"])), "",
              "- Source file: `%s`" % doc["rel"], "- Document ID: `%s`" % doc["doc_id"],
              "- Table ID: `%s`" % t["table_id"], "- Location: %s" % unit_label(loc["kind"], loc["number"]),
              "- Grid: %d rows x %d columns" % (t["rows"], t["columns"]),
              "- Extraction quality: **%s**%s" % (t["quality"], (" - " + t["quality_note"]) if t["quality_note"] else ""),
              "- Detected by: %s" % t["detector"]]
        if t["merged_cells"]:
            md.append("- Merged cells: %d" % len(t["merged_cells"]))
        if t["heading_path"]:
            md.append("- Section: %s" % " > ".join(t["heading_path"]))
        md += ["", table_markdown(t["cells"]), ""]
        _write(os.path.join(folder, "tables", stem + ".md"), "\n".join(md))
        assets["tables"][t["table_id"]] = "%s/tables/%s.md" % (rel, stem)
        if t["quality"] != "NEEDS_REVIEW":
            width = t["columns"]
            buf = io.StringIO()
            csv.writer(buf, lineterminator="\n").writerows([list(r) + [""] * (width - len(r)) for r in t["cells"]])
            _write(os.path.join(folder, "tables", stem + ".csv"), buf.getvalue())
    kept = []
    for im in doc["images"]:
        src = cache.image_path(im["sha256"], im["ext"])
        if not os.path.isfile(src):
            continue
        name = "image_%04d.%s" % (len(kept) + 1, im["ext"])
        os.makedirs(os.path.join(folder, "images"), exist_ok=True)
        _place(src, os.path.join(folder, "images", name))
        im["file"] = name
        assets["images"][im["image_id"]] = "%s/images/%s" % (rel, name)
        kept.append(im)
    doc["images"] = kept

    head = ["# Source: %s" % doc["filename"], "", "- Source file: `%s`" % doc["rel"],
            "- Document ID: `%s`" % doc["doc_id"], "- Format: %s" % doc["fmt"].upper(),
            "- %ss: %d" % (doc["unit_kind"].capitalize(), doc["page_count"]),
            "- Tables extracted: %d" % len(doc["tables"]), "- Images extracted: %d" % len(doc["images"]),
            "- Extraction engine: %s" % (doc.get("engine") or "n/a"), "- Status: %s" % doc["status"],
            "- SHA-256: `%s`" % doc["sha256"], "",
            "Verbatim text extracted locally. Nothing has been summarised, rewritten or",
            "interpreted. Each `## %s N` heading is the real" % doc["unit_kind"].capitalize(),
            "%s in the original file." % doc["unit_kind"], ""]
    if doc.get("error"):
        head += ["## This file could not be read", "", "Reason: %s" % doc["error"], "",
                 "No content could be extracted, so there is nothing below. See", "`../../NEEDS_ATTENTION.md`.", ""]
    if doc["warnings"]:
        head += ["Warnings:"] + ["- " + w for w in doc["warnings"]] + [""]
    tables = {t["table_id"]: t for t in doc["tables"]}
    images = {i["image_id"]: i for i in doc["images"]}
    parts = ["\n".join(head)]
    for u in doc["pages"]:
        parts += ["---\n", _unit_heading(doc, u) + "\n"]
        body = (u.get("text") or "").strip()
        if not body:
            parts.append(NO_TEXT + "\n")
            continue
        rendered = [_expand(b, tables, images, assets) for b in body.split("\n\n")]
        parts.append("\n\n".join(b for b in rendered if b.strip()) + "\n")
    _write(os.path.join(folder, "document.md"), "\n".join(parts).rstrip() + "\n")
    return assets


def write_metadata(kb, doc, build_key=""):
    """metadata.json - written last, once the chunk count is known."""
    meta = metadata(doc)
    meta["build_key"] = build_key
    _json(os.path.join(kb, "sources", doc["slug"], "metadata.json"), meta)


def reuse_source(old_kb, kb, doc, build_key):
    """A source read before and unchanged: its folder in the old knowledge base is moved into the new one instead of
    being written again (on Windows every new file is scanned when it is closed - 3 ms each, thousands of tables).
    Returns (assets, (old folder, new folder)) or None when the old folder is not the same reading."""
    old = os.path.join(old_kb, "sources", doc["slug"])
    try:
        with io.open(os.path.join(old, "metadata.json"), encoding="utf-8") as f:
            meta = json.load(f)
    except (OSError, ValueError):
        return None
    if meta.get("sha256") != doc["sha256"] or meta.get("build_key") != build_key or meta.get("doc_id") != doc["doc_id"]:
        return None
    files = {im.get("image_id"): im.get("file") for im in meta.get("images", [])}
    if any(im["image_id"] not in files for im in doc["images"]):
        return None
    new = os.path.join(kb, "sources", doc["slug"])
    os.makedirs(os.path.dirname(new), exist_ok=True)
    os.rename(old, new)
    rel = "sources/" + doc["slug"]
    assets = {"tables": {t["table_id"]: "%s/tables/table_%04d.md" % (rel, i) for i, t in enumerate(doc["tables"], 1)},
              "images": {}}
    for im in doc["images"]:
        im["file"] = files[im["image_id"]]
        assets["images"][im["image_id"]] = "%s/images/%s" % (rel, im["file"])
    return assets, (old, new)


def _units_for_metadata(doc):
    out = []
    for u in doc["pages"]:
        d = {"number": u["number"], "kind": u.get("kind") or doc["unit_kind"], "method": u.get("method", "text"),
             "char_count": u.get("char_count", 0), "textless": bool(u.get("textless")),
             "headings": [{"text": h, "level": lvl, "page": u["number"]} for h, lvl in u.get("headings", [])]}
        wc = u.get("word_count")
        if wc and wc[1] < wc[0]:
            d["words_lost"] = wc[2]
        for k in ("label", "has_speaker_notes", "hidden", "blank", "ocr_language", "ocr_rotation", "ocr_note"):
            if u.get(k):
                d[k] = u[k]
        out.append(d)
    return out


def metadata(doc):
    tables = [{k: v for k, v in t.items() if k not in ("bbox", "key")} for t in doc["tables"]]
    images = [{k: v for k, v in i.items() if k not in ("ext", "key")} for i in doc["images"]]
    return {"doc_id": doc["doc_id"], "original_filename": doc["filename"], "source_path": doc["rel"],
            "format": doc["fmt"], "converted_from": None, "sha256": doc["sha256"], "size_bytes": doc["size"],
            "unit_kind": doc["unit_kind"], "unit_count": doc["page_count"], "extracted_characters": total_chars(doc),
            "extraction_engine": doc.get("engine") or "", "status": doc["status"], "title": doc.get("title"),
            "author": doc.get("author"), "units_requiring_ocr": textless_pages(doc),
            "units_ocr_failed": doc.get("ocr_failed_pages", []), "units_blank": doc.get("blank_pages", []),
            "table_count": len(doc["tables"]), "image_count": len(doc["images"]), "table_repair": {},
            "tables_rejected_as_layout": len(doc.get("rejected_tables", [])),
            "rejected_table_pages": [r.get("unit") for r in doc.get("rejected_tables", [])],
            "complex_table_pages_detected": [], "complex_table_pages_attempted": [], "complex_table_pages_rebuilt": [],
            "complex_table_pages_not_rebuilt": [], "fallback_seconds": 0.0, "chunk_count": doc.get("chunk_count", 0),
            "words_on_pages": word_totals(doc)[0], "words_kept": word_totals(doc)[1],
            "words_lost": [{"unit": n, "words": w} for n, w in words_lost(doc)][:40],
            "warnings": doc["warnings"], "error": doc.get("error"), "units": _units_for_metadata(doc),
            "tables": tables, "images": images, "output_folder": doc["slug"],
            "excluded_running_headers": doc.get("excluded_headers", []),
            "notes": ("Running headers and footers listed in 'excluded_running_headers' were left out of the page text "
                      "and of the retrieval chunks. Table grids are stored under tables/ and referenced from "
                      "document.md; the words of an indexed table are in its own chunk, not in the page text. Images "
                      "are stored under images/ with their surrounding text in this file.")}


def word_totals(doc):
    """(words on the pages, words kept): every word of a PDF's text layer must be kept somewhere in the knowledge base -
    page text, running header, table. Word and PowerPoint text is never stripped, so all of it is kept."""
    on = kept = 0
    for u in doc["pages"]:
        wc = u.get("word_count")
        if wc:
            on += wc[0]
            kept += wc[1]
        else:
            n = len(_TOKEN.findall(_MARKER.sub("", u.get("text") or "")))
            on += n
            kept += n
    return on, kept


def words_lost(doc):
    return [(u["number"], u["word_count"][2]) for u in doc["pages"] if u.get("word_count") and u["word_count"][1] < u["word_count"][0]]


def textless_pages(doc):
    return [u["number"] for u in doc["pages"] if u.get("textless")]


def total_chars(doc):
    return sum(u.get("char_count", 0) for u in doc["pages"])


def write_manifest(kb, run, docs, unsupported, source_root):
    payload = {"tool": TOOL, "tool_version": run["tool_version"],
               "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "source_root": source_root,
               "run": run, "source_count": len(docs), "unsupported_files_found": unsupported, "sources": []}
    for d in docs:
        payload["sources"].append({
            "doc_id": d["doc_id"], "original_filename": d["filename"], "source_path": d["rel"], "format": d["fmt"],
            "converted_from": None, "output_folder": ("sources/" + d["slug"]) if d.get("slug") else None,
            "sha256": d["sha256"], "size_bytes": d["size"], "unit_kind": d["unit_kind"], "unit_count": d["page_count"],
            "extracted_characters": total_chars(d), "table_count": len(d["tables"]), "image_count": len(d["images"]),
            "chunk_count": d.get("chunk_count", 0), "status": d["status"], "extraction_engine": d.get("engine") or "",
            "words_on_pages": word_totals(d)[0], "words_kept": word_totals(d)[1],
            "warnings": d["warnings"], "units_requiring_ocr": textless_pages(d),
            "ocr_languages": sorted({u["ocr_language"] for u in d["pages"] if u.get("ocr_language")}),
            "duplicate_of": d.get("duplicate_of"), "duplicate_of_path": d.get("duplicate_of_path") or "",
            "tables_rejected_as_layout": len(d.get("rejected_tables", [])), "rejected_tables": d.get("rejected_tables", []),
            "complex_table_pages_detected": [], "complex_table_pages_attempted": [], "complex_table_pages_rebuilt": [],
            "complex_table_pages_not_rebuilt": [], "reused_from_cache": bool(d.get("from_cache")), "error": d.get("error")})
    _json(os.path.join(kb, "SOURCE_MANIFEST.json"), payload)


def write_course_index(kb, docs):
    L = ["# Course index", "", "One row per source file, in the order they were found. Open a document",
         "folder to read the full extracted text with page, slide or section numbers.", "",
         "| # | Source file | Type | Units | Tables | Images | Chunks | Status |",
         "|---|-------------|------|-------|--------|--------|--------|--------|"]
    by_id = {d["doc_id"]: d for d in docs}
    for n, d in enumerate(docs, 1):
        units = "%d %s%s" % (d["page_count"], d["unit_kind"], "" if d["page_count"] == 1 else "s")
        if d.get("duplicate_of"):
            c = by_id.get(d["duplicate_of"])
            link = "[%s](sources/%s/document.md)" % (d["filename"], c["slug"]) if c and c.get("slug") else d["filename"]
            L.append("| %d | %s | %s | %s | - | - | - | identical copy of `%s` |"
                     % (n, link, d["fmt"].upper(), units, d.get("duplicate_of_path")))
            continue
        L.append("| %d | [%s](sources/%s/document.md) | %s | %s | %d | %d | %d | %s |"
                 % (n, d["filename"], d.get("slug"), d["fmt"].upper(), units, len(d["tables"]), len(d["images"]),
                    d.get("chunk_count", 0), d["status"]))
    L += ["", "## Where each file came from", ""] + ["- %s - `%s`" % (d["filename"], d["rel"]) for d in docs]
    L += ["", "## Detected section headings", "",
          "Detected from typography, numbering and Word/PowerPoint styles - never",
          "from meaning. Numbers are the original page, slide or section numbers.", ""]
    for d in docs:
        L += ["### %s" % d["filename"], "", "- Document ID: `%s`" % d["doc_id"], ""]
        seen = {}
        for u in d["pages"]:
            for h, _ in u.get("headings", []):
                seen[h] = seen.get(h, 0) + 1
        with_text = max(1, sum(1 for u in d["pages"] if (u.get("text") or "").strip()))
        boiler = {h for h, c in seen.items() if c >= max(5, int(with_text * 0.6))}
        heads = [(h, lvl, u["number"]) for u in d["pages"] for h, lvl in u.get("headings", []) if lvl <= 2 and h not in boiler]
        if not heads:
            L += ["_No headings detected._", ""]
            continue
        for h, lvl, num in heads[:400]:
            L.append("%s- %s.%d - %s" % ("  " * (lvl - 1), d["unit_kind"][0], num, h))
        if len(heads) > 400:
            L.append("  - _...%d more headings (see metadata.json)_" % (len(heads) - 400))
        L.append("")
    _write(os.path.join(kb, "COURSE_INDEX.md"), "\n".join(L).rstrip() + "\n")


def _pages_list(pages):
    shown = ", ".join(str(p) for p in pages[:40])
    return shown + (", ... (+%d more)" % (len(pages) - 40) if len(pages) > 40 else "")


def write_needs_attention(kb, docs, unsupported, missing_models):
    failed = [d for d in docs if d["status"] == "failed"]
    empty = [d for d in docs if d["status"] == "empty"]
    scanned = [d for d in docs if textless_pages(d)]
    ocr_failed = [d for d in docs if d.get("ocr_failed_pages")]
    russian = [d for d in docs if d.get("needs_rus_pages")]
    weak = [(d, t) for d in docs for t in d["tables"] if t["quality"] != QUALITY_GOOD]
    rejected = [d for d in docs if d.get("rejected_tables")]
    copies = [d for d in docs if d.get("duplicate_of")]
    path = os.path.join(kb, "NEEDS_ATTENTION.md")
    if not (failed or empty or scanned or ocr_failed or weak or rejected or copies or unsupported or russian):
        if os.path.exists(path):
            os.remove(path)
        return False
    L = ["# Needs attention", "", "Everything else processed normally. This file lists only the items a human",
         "should look at.", ""]
    if failed:
        L += ["## Files that could not be processed", ""]
        L += ["- **%s** (`%s`) - %s" % (d["filename"], d["rel"], d.get("error") or "unknown error") for d in failed]
        L += ["", "What to do: open the file yourself. If it opens, it may be password",
              "protected or damaged. Re-save it (an old .doc or .ppt as .docx or .pptx) and run the builder again.", ""]
    if empty:
        L += ["## Files with no readable content", ""] + ["- **%s** (`%s`)" % (d["filename"], d["rel"]) for d in empty] + [""]
    if ocr_failed:
        L += ["## Scanned pages that could not be read", "",
              "These pages are photographs of paper and the reader could not turn them into text - usually a very",
              "poor scan or handwriting. Everything else in the document was processed normally.", ""]
        L += ["- **%s** - page(s) %s" % (d["filename"], _pages_list(d["ocr_failed_pages"])) for d in ocr_failed] + [""]
    if russian:
        L += ["## Russian scanned pages not read", "",
              "These scanned pages are in Russian. They are read with the Russian reading model, rus.traineddata,",
              "which is not on this computer and could not be fetched.", ""]
        L += ["- **%s** - page(s) %s" % (d["filename"], _pages_list(d["needs_rus_pages"])) for d in russian] + [""]
    if scanned:
        L += ["## Pages with no selectable text (scans / graphics)", "",
              "These pages are in the package but hold no text, so they cannot be found by searching.", ""]
        if missing_models:
            L += ["They were not read because the reading models are not on this computer: %s." % missing_models, ""]
        else:
            L += ["The reader ran on them and found no words (a photograph, a diagram with no text, a divider).", ""]
        L += ["- **%s** - %d of %d %ss: %s" % (d["filename"], len(textless_pages(d)), d["page_count"], d["unit_kind"],
                                               _pages_list(textless_pages(d))) for d in scanned] + [""]
    if weak:
        L += ["## Tables worth checking by eye", "",
              "The grid of these tables could not be read cleanly. The text is still",
              "there, but do not trust the row and column layout without looking.", ""]
        for d, t in weak[:80]:
            loc = t["location"]
            L.append("- **%s** %s - `%s` - %s: %s" % (d["filename"], unit_label(loc["kind"], loc["number"]), t["table_id"],
                                                     t["quality"], t["quality_note"] or "see the table file"))
        if len(weak) > 80:
            L.append("- _...(+%d more)_" % (len(weak) - 80))
        L.append("")
    if rejected:
        L += ["## Boxed page areas not kept as tables", "",
              "Grids offered by the table finder that look like a boxed area of the page (a title page border, a",
              "framed notice) rather than data. Not written to `tables/`; their text is in the page text.", ""]
        for d in rejected[:40]:
            for r in d["rejected_tables"][:6]:
                L.append("- **%s** page %s - %sx%s - %s" % (d["filename"], r.get("unit"), r.get("rows"), r.get("columns"),
                                                           r.get("reason")))
        L.append("")
    if copies:
        L += ["## Identical copies (read once)", "",
              "These files are byte-for-byte the same as another file in the folder, so they were read once.", ""]
        L += ["- `%s` - identical to `%s`" % (d["rel"], d.get("duplicate_of_path")) for d in copies[:60]] + [""]
    if unsupported:
        L += ["## Files ignored (type not supported)", "",
              "The builder reads PDF, Word (.docx), PowerPoint (.pptx) and picture files.", ""]
        L += ["- %s" % n for n in unsupported[:60]] + [""]
    _write(path, "\n".join(L).rstrip() + "\n")
    return True
