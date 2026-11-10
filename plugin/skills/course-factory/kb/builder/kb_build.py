#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""The factory's own knowledge-base builder: a Course Source Processor knowledge base made with PyMuPDF alone.

    kb_build.py <source root> [--out DIR] [--jobs N] [--lang auto|eng|lav|rus] [--tessdata DIR] [--no-images] [--no-tables]

WHAT IT MAKES
The same KNOWLEDGE_BASE folder the Course KB Builder (BUILD_KNOWLEDGE_BASE.exe) makes - SOURCE_MANIFEST.json, sources\\,
search_index\\ (index version 5, the same tokenizer) - so kb_tool.py, fact_check.py and photo_catalogue.py read it
unchanged. The manifest says tool "COURSE FACTORY KB BUILDER". By default it is written into the source root.

HOW
Every PDF is read in page ranges, every scanned page and every Word or PowerPoint file as a task of its own, on several
cores (pool.py). Scanned pages are read by PyMuPDF's own Tesseract; the reading models (eng, lav, rus traineddata) are
looked for on this computer and fetched once when a scanned page needs them and they are missing (ocr.py). A file read
before is not read again (cache.py, in %LOCALAPPDATA%\\NOVIKONTAS\\kb_cache). The knowledge base is built beside the
old one as KNOWLEDGE_BASE.building and swapped in at the end; no source file is ever written to.

Exit 0 made, 2 nothing to read, 3 PyMuPDF missing or too old, 5 failed. Standard library + PyMuPDF; Python 3.9+.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

TOOL_VERSION = "1.0.0"
PYMUPDF_MIN = (1, 24)
RANGE = 20                       # pages per task
OLD_FORMATS = ("doc", "ppt")


def say(text=""):
    print(text)
    sys.stdout.flush()


def pymupdf_version():
    """(major, minor) of PyMuPDF, or None when it cannot be imported."""
    try:
        import pymupdf
    except Exception:                                        # noqa: BLE001
        return None
    import re
    parts = re.findall(r"\d+", str(getattr(pymupdf, "VersionBind", "") or getattr(pymupdf, "__version__", "")))
    return tuple(int(x) for x in parts[:2]) if len(parts) >= 2 else (0, 0)


# ------------------------------------------------------------------ one document's state
class Doc(dict):
    """A source being read. Keys follow the Course Source Processor's model (write.py reads them)."""


def new_doc(f, doc_id, slug):
    d = Doc(doc_id=doc_id, filename=f["name"], rel=f["rel"], path=f["path"], sha256=f["sha256"], size=f["size"],
            slug=slug, fmt=f["fmt"], unit_kind={"pdf": "page", "pptx": "slide", "docx": "section", "image": "image",
                                                 "doc": "section", "ppt": "slide"}[f["fmt"]],
            page_count=0, pages=[], tables=[], images=[], engine="", status="ok", title=None, author=None, warnings=[],
            error=None, ocr_failed_pages=[], ocr_low_pages=[], ocr_empty_pages=[], rejected_tables=[], duplicate_of=None, duplicate_of_path="",
            from_cache=False, chunk_count=0, excluded_headers=[], blank_pages=[], needs_rus_pages=[])
    d["scan"], d["ocr"], d["ranges_left"], d["ocr_left"], d["parts"] = {}, {}, 0, 0, []
    return d


def merge_pdf(d, stats, parts):
    """The page-range results put together: table and picture ids in page order, repeated pictures kept once."""
    pages = sorted((p for part in parts for p in part), key=lambda p: p["number"])
    import common
    tables, images, seen, rejected, excluded = [], [], set(), [], set()
    limit = common.SETTINGS["images_max_per_document"]
    units, failed = [], []
    for p in pages:
        text = p["text"]
        for t in p["tables"]:
            tables.append(t)
            t["table_id"] = "%s#t%04d" % (d["doc_id"], len(tables))
            text = text.replace("[[TABLE ?%s]]" % t["key"], common.table_marker(t))
        for im in p["images"]:
            ph = "[[IMAGE ?%s]]" % im["key"]
            if im["sha256"] in seen or len(images) >= limit:
                text = text.replace("\n\n" + ph, "").replace(ph, "")
                continue
            seen.add(im["sha256"])
            rec = common.image_record(d["doc_id"], len(images) + 1, "page", p["number"], im["sha256"], im["ext"],
                                      im["width"], im["height"], im["byte_size"], bbox=im["bbox"],
                                      caption=im["caption"], nearby=im["nearby_text"])
            images.append(rec)
            text = text.replace(ph, common.image_marker(rec))
        rejected += p["rejected"]
        excluded.update(p["excluded"])
        if p.get("failed"):
            failed.append(p["number"])
        # running headers and footers stay in document.md, as the page shows them, but no piece of the index holds
        # them and no heading path names them (chunk.py leaves the edge blocks out)
        top, bottom = (p.get("edges") or ["", ""])
        edge_blocks = [e for e in (top, bottom) if e]
        text = "\n\n".join(x for x in (top, text.strip(), bottom) if x).strip()
        u = {"number": p["number"], "kind": "page", "text": text, "method": "text", "char_count": len(text),
             "textless": False, "headings": [list(h) for h in p["headings"]],
             "word_count": p.get("word_count") or [0, 0, []]}
        if edge_blocks:
            u["edge_blocks"] = edge_blocks
        if p["blank"]:
            u.update(method="none", blank=True)
            d["blank_pages"].append(p["number"])
        if p["scanned"]:
            markers = [b for b in text.split("\n\n") if b.startswith("[[IMAGE ")]
            d["scan"][str(p["number"])] = {"thin": p["thin_layer"], "markers": markers, "native": text,
                                           "native_chars": p["native_chars"]}
        units.append(u)
    d.update(pages=units, page_count=stats["pages"], tables=tables, images=images, rejected_tables=rejected,
             excluded_headers=sorted(excluded), title=stats["title"], author=stats["author"],
             engine="pymupdf", prior=stats["language"])
    if failed:
        d["warnings"].append("%d page(s) could not be read: %s" % (len(failed), ", ".join(map(str, failed[:20]))))


def apply_ocr(d):
    """Scanned pages get their OCR reading, where it found words; the rest stay marked as having no text."""
    import common
    minimum = common.SETTINGS["min_chars_per_page"]
    by_number = {u["number"]: u for u in d["pages"]}
    d["ocr_failed_pages"], d["needs_rus_pages"], d["ocr_low_pages"], d["ocr_empty_pages"] = [], [], [], []
    recovered = 0
    for key, scan in d["scan"].items():
        u = by_number.get(int(key))
        if u is None:
            continue
        got = d["ocr"].get(key)
        u.pop("ocr_language", None)
        if isinstance(got, str):
            d["ocr_failed_pages"].append(u["number"])
        elif isinstance(got, dict) and got.get("note") == "needs rus.traineddata":
            d["needs_rus_pages"].append(u["number"])
        if isinstance(got, dict) and len(got["text"].strip()) >= minimum and (
                not scan["thin"] or len(got["text"]) > scan["native_chars"] * 1.3 + 100):
            text = "\n\n".join([got["text"]] + scan["markers"]).strip()
            import pdf
            native_words = pdf.word_counts(scan["native"], text)
            if native_words[1] < native_words[0]:
                # the reading misses words the page's own text layer holds: those stay too - text is never dropped
                # for a reading that does not hold all of it
                text = "\n\n".join([got["text"], scan["native"]]).strip()
            u.update(text=text, method="ocr", char_count=len(text), textless=False, headings=got["headings"],
                     ocr_language=got["language"])
            u.pop("edge_blocks", None)
            u.pop("ocr_low", None)
            if got.get("low"):
                # much print on the page, few of its squares under a word read: never reported as simply read
                u["ocr_low"] = True
                d["ocr_low_pages"].append(u["number"])
            if got.get("cover") is not None:
                u["ocr_cover"] = got["cover"]
            if u.get("word_count") and u["word_count"][0]:
                # the page's own text layer (a stamp, a page number) against what replaces it
                u["word_count"] = pdf.word_counts(scan["native"], text)
            if got.get("rotation"):
                u["ocr_rotation"] = got["rotation"]
            recovered += 1
        elif scan["thin"] or (isinstance(got, dict) and got.get("language") and scan["native_chars"] > 0):
            # the page was read and holds no more words than its text layer: those few words are all there is
            u.update(textless=False)
        else:
            u.update(text=scan["native"], method="none", char_count=len(scan["native"]), textless=True)
            if isinstance(got, dict) and got.get("language"):
                d["ocr_empty_pages"].append(u["number"])     # read, and fewer than 60 characters found
    d["ocr_failed_pages"].sort()
    d["ocr_low_pages"].sort()
    d["ocr_empty_pages"].sort()
    d["needs_rus_pages"].sort()
    return recovered


def status_of(d, recovered):
    if d.get("error"):
        return "failed"
    if d["page_count"] == 0:
        return "empty"
    textless = sum(1 for u in d["pages"] if u.get("textless"))
    if not textless:
        return "ocr_applied" if recovered else "ok"
    return "needs_ocr" if textless / float(d["page_count"]) >= 0.5 else "ok_with_gaps"


def cache_payload(d):
    keep = ("doc_id", "fmt", "unit_kind", "page_count", "pages", "tables", "images", "title", "author", "warnings",
            "engine", "rejected_tables", "excluded_headers", "blank_pages", "scan", "ocr", "ocr_key", "prior")
    return {k: d.get(k) for k in keep}


def from_cache(d, got):
    if got.get("doc_id") != d["doc_id"]:
        got = json.loads(json.dumps(got, ensure_ascii=False).replace(got["doc_id"] + "#", d["doc_id"] + "#"))
    for k, v in got.items():
        if k != "doc_id":
            d[k] = v
    d["from_cache"] = True


# ------------------------------------------------------------------ the build
def parse(argv):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("root", help="the folder of source files")
    ap.add_argument("--out", help="where the knowledge base goes (default: <root>\\KNOWLEDGE_BASE)")
    ap.add_argument("--jobs", type=int, default=0, help="worker processes (default: cores - 1, at most 6)")
    ap.add_argument("--lang", choices=("auto", "eng", "lav", "rus"), default="auto",
                    help="language of scanned pages: auto chooses per page by its own words")
    ap.add_argument("--tessdata", help="the folder with the reading models (eng/lav/rus.traineddata)")
    ap.add_argument("--no-images", action="store_true", help="keep no pictures")
    ap.add_argument("--no-tables", action="store_true", help="find no tables in PDFs")
    ap.add_argument("--cli", action="store_true", help=argparse.SUPPRESS)        # what the .exe is called with
    return ap.parse_args(argv)


def main(argv=None):
    a = parse(argv)
    started = time.time()
    have = pymupdf_version()
    if have is None or have < PYMUPDF_MIN:
        say("Stopped - this builder needs PyMuPDF %d.%d or newer (%s).\n  Install it once:  python -m pip install pymupdf"
            % (PYMUPDF_MIN + ("not installed" if have is None else "found %d.%d" % have,)))
        return 3
    import cache
    import chunk
    import discover
    import index
    import ocr as ocrmod
    import pdf
    import write
    from pool import Pool, default_jobs

    root = os.path.abspath(a.root)
    if not os.path.isdir(root):
        say("Stopped - that folder does not exist:\n    %s" % root)
        return 2
    out = os.path.abspath(a.out) if a.out else os.path.join(root, "KNOWLEDGE_BASE")
    building = out + ".building"
    found, unsupported = discover.discover(root)
    found = [f for f in found if not (f["path"].lower() + os.sep).startswith(out.lower() + os.sep)]
    if not found:
        say("Stopped - there is nothing to make a knowledge base from in\n    %s\n  The builder reads PDF, Word (.docx), "
            "PowerPoint (.pptx) and picture files, in every sub-folder." % root)
        return 2

    jobs = a.jobs or default_jobs()
    say("Making the knowledge base from %d file(s) in\n    %s\n  into %s, with %d worker(s)." % (len(found), root, out, jobs))
    for f in found:
        f["sha256"] = discover.sha256_of(f["path"])
    canonical = discover.canonical_copies(found)
    copies = [f for f in found if canonical.get(f["sha256"]) not in (None, f["rel"])]
    primary = [f for f in found if f not in copies]
    ids, slugs, docs = set(), set(), {}
    for f in primary:
        docs[f["rel"]] = new_doc(f, discover.unique_doc_id(f["sha256"], ids),
                                 discover.unique_slug(discover.slugify(f["name"]), slugs, f["sha256"]))
    for f in copies:
        d = new_doc(f, discover.unique_doc_id(f["sha256"], ids), "")
        d["status"] = "duplicate"
        docs[f["rel"]] = d

    want_tables, want_images = not a.no_tables, not a.no_images
    key = cache.settings_key({"tables": want_tables, "images": want_images})
    store = cache.image_store()
    os.makedirs(store, exist_ok=True)
    forced = None if a.lang == "auto" else a.lang
    tess = {"dir": None, "models": set(), "asked": False}

    def tessdata():
        if not tess["asked"]:
            tess["asked"] = True
            need = {"auto": ["eng", "lav", "rus"], "eng": ["eng"], "lav": ["lav"], "rus": ["eng", "rus"]}[a.lang]
            tess["dir"], tess["models"] = ocrmod.ensure_tessdata(need, a.tessdata, root, say)
        return tess["dir"], tess["models"]

    def ocr_key():
        t, m = tessdata()
        return json.dumps({"lang": a.lang, "models": sorted(m)}) if t else None

    pool = Pool(jobs)
    total, done_files = len(found), [0]
    counters = {"ocr_seconds": 0.0, "ocr_pages": 0, "reused": 0}

    def finish(d):
        recovered = apply_ocr(d) if d["fmt"] == "pdf" else 0
        d["recovered"] = recovered
        d["status"] = status_of(d, recovered)
        if not d.get("error") and not d["from_cache_clean"]:
            try:
                cache.save(d["sha256"], key, cache_payload(d))
            except OSError:
                pass
        done_files[0] += 1
        extra = []
        if d["tables"]:
            extra.append("%d table(s)" % len(d["tables"]))
        if d["images"]:
            extra.append("%d image(s)" % len(d["images"]))
        if recovered:
            extra.append("%d scanned page(s) read" % recovered)
        gaps = sum(1 for u in d["pages"] if u.get("textless"))
        if gaps:
            extra.append("%d %s(s) with no text" % (gaps, d["unit_kind"]))
        say("[%d/%d] %s - %s%s%s" % (done_files[0], total, d["filename"],
                                     d.get("error") or "%d %s%s" % (d["page_count"], d["unit_kind"],
                                                                     "" if d["page_count"] == 1 else "s"),
                                     (", " + ", ".join(extra)) if extra and not d.get("error") else "",
                                     " (unchanged, read before)" if d["from_cache"] else ""))

    def start_ocr(d, numbers, prior):
        t, m = tessdata()
        for n in numbers:
            pool.submit(("ocr", d["rel"], n), pdf.ocr_page, d["path"], n, t, sorted(m), prior, forced, 200, first=True)
            d["ocr_left"] += 1

    def after_text(d):
        """The text pass of a PDF is done: read its scanned pages, all at once. The first model is the one the
        document's text layer (or its name) points to; each page then checks its own words (ocr.read_scanned_page)."""
        pending = sorted(int(k) for k in d["scan"] if k not in d["ocr"])
        t, _m = tessdata() if pending else (None, None)
        if not pending or not t:
            finish(d)
            return
        d["ocr_key"] = ocr_key()
        import lang as langmod
        prior = forced or (d.get("prior") if d.get("prior") in ("eng", "lav", "rus") else langmod.lang_of_name(d["filename"]))
        start_ocr(d, pending, prior)

    for f in primary:
        d = docs[f["rel"]]
        d["from_cache_clean"] = False
        if d["fmt"] in OLD_FORMATS:
            d["error"] = ("an old Word/PowerPoint format (.%s) - this builder reads .docx and .pptx; save the file in "
                          "the new format and build again" % d["fmt"])
            finish(d)
            continue
        got = cache.load(d["sha256"], key)
        if got:
            from_cache(d, got)
            counters["reused"] += 1
            scanned_left = [k for k in d["scan"] if k not in d["ocr"]]
            stale = bool(d["scan"]) and d.get("ocr_key") != ocr_key() and tessdata()[0]
            if stale:
                d["ocr"] = {}
            if (scanned_left or stale) and d["fmt"] == "pdf" and tessdata()[0]:
                after_text(d)
            else:
                d["from_cache_clean"] = True
                finish(d)
            continue
        if d["fmt"] == "pdf":
            pool.submit(("stats", d["rel"]), pdf.doc_stats, d["path"])
        else:
            import office
            if d["fmt"] == "pptx":
                pool.submit(("office", d["rel"]), office.read_pptx, d["path"], d["doc_id"], store, want_tables, want_images)
            elif d["fmt"] == "docx":
                pool.submit(("office", d["rel"]), office.read_docx, d["path"], d["doc_id"], store, want_tables, want_images)
            else:
                pool.submit(("office", d["rel"]), office.read_image, d["path"], d["rel"], d["doc_id"], store)

    last_said = time.time()
    try:
        for tag, ok, res in pool.results(timeout=5.0):
            if time.time() - last_said >= 30:
                busy = [x for x in docs.values() if x["ranges_left"] or x["ocr_left"]]
                say("  ... %d of %d files done; %d page part(s) and %d scanned page(s) in work%s"
                    % (done_files[0], total, sum(x["ranges_left"] for x in busy), sum(x["ocr_left"] for x in busy),
                       ("; reading " + busy[0]["filename"]) if busy else ""))
                last_said = time.time()
            if tag is None:
                continue
            kind, rel = tag[0], tag[1]
            d = docs[rel]
            if kind == "stats":
                if not ok:
                    d["error"] = res if "PDF" in res or "password" in res else "the PDF could not be read (%s)" % res
                    finish(d)
                    continue
                d["stats"] = res
                ctx = {"body_size": res["body_size"], "big_sizes": res["big_sizes"], "headers": res["headers"],
                       "vocab": res["vocab"], "tables": want_tables, "images": want_images, "store": store}
                if res["pages"] == 0:
                    merge_pdf(d, res, [])
                    finish(d)
                    continue
                for first in range(1, res["pages"] + 1, RANGE):
                    pool.submit(("range", rel, first), pdf.extract_range, d["path"], first,
                                min(res["pages"], first + RANGE - 1), ctx)
                    d["ranges_left"] += 1
            elif kind == "range":
                d["ranges_left"] -= 1
                if ok:
                    d["parts"].append(res)
                else:
                    first = tag[2]
                    last = min(d["stats"]["pages"], first + RANGE - 1)
                    d["parts"].append([{"number": n, "text": "", "headings": [], "native_chars": 0, "columns": 1,
                                        "tables": [], "images": [], "rejected": [], "scanned": False, "blank": False,
                                        "thin_layer": False, "excluded": [], "word_count": [0, 0, []],
                                        "failed": res} for n in range(first, last + 1)])
                if d["ranges_left"] == 0:
                    merge_pdf(d, d["stats"], d.pop("parts"))
                    d["parts"] = []
                    after_text(d)
            elif kind == "ocr":
                d["ocr_left"] -= 1
                d["ocr"][str(tag[2])] = res if ok else str(res)
                if ok:
                    counters["ocr_seconds"] += res.get("seconds", 0.0)
                    counters["ocr_pages"] += 1
                if d["ocr_left"] == 0:
                    finish(d)
            elif kind == "office":
                if not ok:
                    d["error"] = res
                else:
                    for k in ("fmt", "unit_kind", "pages", "page_count", "tables", "images", "title", "author",
                              "warnings", "engine", "rejected_tables"):
                        d[k] = res[k]
                finish(d)
    finally:
        pool.close()

    # identical copies point at the copy that was read
    by_rel = {f["rel"]: docs[f["rel"]] for f in primary}
    for f in copies:
        d = docs[f["rel"]]
        c = by_rel.get(canonical[f["sha256"]])
        if c is not None and c["status"] != "failed":
            d.update(duplicate_of=c["doc_id"], duplicate_of_path=c["rel"], unit_kind=c["unit_kind"],
                     page_count=c["page_count"], fmt=c["fmt"])
        else:
            d.update(status="failed", error="this file is identical to another one that could not be read, so neither "
                                            "copy produced any text")
        done_files[0] += 1
        say("[%d/%d] %s - identical to %s, not read again" % (done_files[0], total, d["filename"],
                                                              d.get("duplicate_of_path") or "a file that failed"))

    build_key = "%s/%s" % (TOOL_VERSION, key)
    moved = []
    try:
        # the copy that was read is listed before its identical copies: kb_tool keeps the first of a group of
        # identical files and leaves the others out of a search, so a copy listed first would hide the text
        ordered = [docs[f["rel"]] for f in primary] + [docs[f["rel"]] for f in copies]
        if os.path.exists(building):
            shutil.rmtree(building)
        ix = index.IndexWriter(os.path.join(building, "search_index"))
        for d in ordered:
            if d.get("duplicate_of") or d["status"] == "duplicate":
                continue
            reused = write.reuse_source(out, building, d, build_key) if d.get("from_cache_clean") else None
            if reused:
                assets = reused[0]
                moved.append(reused[1])
            else:
                assets = write.write_source(building, d)
            if not d.get("error"):
                chunks = chunk.chunk_units(d) + chunk.asset_chunks(d, assets)
                d["chunk_count"] = len(chunks)
                for c in chunks:
                    ix.add(c)
            write.write_metadata(building, d, build_key)
            ix.add_document(d["doc_id"], {"file": d["filename"], "source_path": d["rel"], "format": d["fmt"],
                                          "folder": "sources/" + d["slug"], "unit_kind": d["unit_kind"],
                                          "units": d["page_count"], "status": d["status"]})
        stats = ix.close()
        t, m = tess["dir"], tess["models"]
        scanned_unread = sum(1 for d in ordered for u in d["pages"] if u.get("textless") and str(u["number"]) in d.get("scan", {}))
        missing = [x + ".traineddata" for x in ("eng", "lav") if x not in m] if scanned_unread and not t else []
        rus_pages = sum(len(d.get("needs_rus_pages", [])) for d in ordered)
        if rus_pages and "rus" not in m:
            missing.append("rus.traineddata")
        run = {"tool_version": TOOL_VERSION, "source_root": root, "knowledge_base": out,
               "pdf_engine": "pymupdf %s" % ".".join(map(str, have)), "jobs": jobs,
               "formats_supported": sorted(discover.FORMATS), "ocr_usable": bool(t), "tessdata": t or "",
               "ocr_models": sorted(m), "ocr_language": a.lang,
               "ocr_languages_used": sorted({u["ocr_language"] for d in ordered for u in d["pages"] if u.get("ocr_language")}),
               "ocr_pages_recovered": sum(d.get("recovered", 0) for d in ordered),
               "ocr_pages_read_this_run": counters["ocr_pages"], "ocr_seconds": round(counters["ocr_seconds"], 1),
               "ocr_pages_failed": sum(len(d["ocr_failed_pages"]) for d in ordered),
               "ocr_pages_low": sum(len(d.get("ocr_low_pages", [])) for d in ordered),
               "ocr_pages_empty": sum(len(d.get("ocr_empty_pages", [])) for d in ordered),
               "scanned_pages_not_read": scanned_unread, "blank_pages_skipped": sum(len(d["blank_pages"]) for d in ordered),
               "documents_reused_from_cache": counters["reused"], "images_kept": sum(len(d["images"]) for d in ordered),
               "duplicate_files_skipped": len(copies),
               "tables_rejected_as_layout": sum(len(d["rejected_tables"]) for d in ordered),
               "chunk_count": stats["chunk_count"], "unique_terms": stats["unique_terms"],
               "seconds": round(time.time() - started, 1), "finished_local": datetime.now().strftime("%Y-%m-%d %H:%M")}
        write.write_manifest(building, run, ordered, unsupported, root)
        write.write_course_index(building, ordered)
        write.write_needs_attention(building, ordered, unsupported, ", ".join(missing))
        run["seconds"] = round(time.time() - started, 1)
        write.write_manifest(building, run, ordered, unsupported, root)
        swap(building, out)
    except Exception as e:                                   # noqa: BLE001 - say what happened, never a traceback only
        import traceback
        traceback.print_exc()
        for old, new in reversed(moved):                    # source folders taken from the old one go back
            try:
                os.rename(new, old)
            except OSError:
                pass
        say("Stopped - the knowledge base could not be written: %s: %s\n  The earlier one (if any) is untouched." %
            (type(e).__name__, e))
        return 5

    read = [d for d in ordered if d["status"] in ("ok", "ok_with_gaps", "ocr_applied")]
    bad = [d for d in ordered if d["status"] in ("failed", "empty", "needs_ocr")]
    say("")
    say("Knowledge base made in %.0f s:\n    %s" % (time.time() - started, out))
    say("  %d source(s): %d read, %d identical copies, %d not read; %d searchable pieces; %d pictures; %d scanned page(s) read."
        % (len(ordered), len(read), len(copies), len(bad), stats["chunk_count"], run["images_kept"],
           run["ocr_pages_recovered"]))
    short = []
    for d in ordered:
        on, kept = write.word_totals(d)
        if on and kept < on * 0.995:
            short.append("%s %.1f %%" % (d["filename"], 100.0 * kept / on))
    words_on = sum(write.word_totals(d)[0] for d in ordered)
    words_kept = sum(write.word_totals(d)[1] for d in ordered)
    say("  Words of the page text kept: %d of %d (%.2f %%)." % (words_kept, words_on, 100.0 * words_kept / max(1, words_on)))
    if short:
        say("  %d source(s) keep less than 99.5 %% of their page words (metadata.json words_lost names them): %s"
            % (len(short), "; ".join(short[:10])))
    if os.path.exists(os.path.join(out, "NEEDS_ATTENTION.md")):
        say("  What to look at is in NEEDS_ATTENTION.md there.")
    if run["ocr_pages_low"]:
        say("  %d scanned page(s) may be read incompletely: much print on the page, few of its words found "
            "(listed in NEEDS_ATTENTION.md)." % run["ocr_pages_low"])
    if scanned_unread or rus_pages:
        empty = sum(len(d.get("ocr_empty_pages", [])) for d in ordered)
        broke = run["ocr_pages_failed"]
        unread = scanned_unread - empty - broke - rus_pages
        why = []
        if empty:
            why.append("%d read and found to hold fewer than 60 characters (a photograph, a diagram with no words)" % empty)
        if broke:
            why.append("%d where the reader failed" % broke)
        if rus_pages:
            why.append("%d Russian, with no Russian reading model" % rus_pages)
        if unread > 0:
            why.append("%d not read for want of a reading model" % unread)
        say("  %d scanned page(s) have no text: %s." % (scanned_unread, "; ".join(why)))
        if missing:
            say("  Reading them needs %s - put the file(s) in %s and build again (no network was available to fetch them)."
                % (" and ".join(missing), ocrmod.local_tessdata()))
    if primary and len(bad) == len(ordered) and not read:
        return 5
    return 0


def swap(building, out):
    """Put the new knowledge base in place of the old one. Where Windows holds a file of the old one open, the new
    one is moved in piece by piece instead."""
    old = out + ".old"
    if os.path.exists(old):
        shutil.rmtree(old, ignore_errors=True)
    if not os.path.exists(out):
        os.rename(building, out)
        return
    try:
        os.rename(out, old)
    except OSError:
        new_note = os.path.exists(os.path.join(building, "NEEDS_ATTENTION.md"))
        for name in os.listdir(building):
            target = os.path.join(out, name)
            if os.path.isdir(target):
                shutil.rmtree(target, ignore_errors=True)
            elif os.path.exists(target):
                os.remove(target)
            shutil.move(os.path.join(building, name), target)
        stale = os.path.join(out, "NEEDS_ATTENTION.md")
        if not new_note and os.path.exists(stale):
            try:
                os.remove(stale)
            except OSError:
                pass
        shutil.rmtree(building, ignore_errors=True)
        return
    os.rename(building, out)
    shutil.rmtree(old, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
