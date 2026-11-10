# -*- coding: utf-8 -*-
"""Reading .pptx and .docx with zipfile and ElementTree - no python-pptx, no python-docx - and picture files.

PowerPoint: a unit is a slide, numbered in the order presentation.xml lists them (the order the deck shows them).
The title comes first, then the shapes top to bottom and left to right, tables as grids, pictures, and the speaker
notes. A hidden slide is read too and marked hidden. Word: a unit is a section that starts at every top-level heading
(the Course Source Processor's rule, so the numbers match); paragraphs, tables, text boxes and content controls in the
order the document holds them. The shape order, the slide text layout and the section rule follow the Course Source
Processor (csp/extractors/pptx_reader.py, docx_reader.py).
"""
from __future__ import annotations

import os
import posixpath
import re
import xml.etree.ElementTree as ET
import zipfile

import common
from common import SETTINGS, tidy

A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
P = "{http://schemas.openxmlformats.org/presentationml/2006/main}"
R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
PR = "{http://schemas.openxmlformats.org/package/2006/relationships}"
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
MC = "{http://schemas.openxmlformats.org/markup-compatibility/2006}"
V = "{urn:schemas-microsoft-com:vml}"
DC = "{http://purl.org/dc/elements/1.1/}"
ROW_TOLERANCE = 182880          # 0.2 inch in EMU: shapes this close vertically are on one row


def _rels(z, part):
    folder, base = posixpath.split(part)
    rp = posixpath.join(folder, "_rels", base + ".rels")
    try:
        root = ET.fromstring(z.read(rp))
    except KeyError:
        return {}
    out = {}
    for r in root.iter(PR + "Relationship"):
        target = r.get("Target") or ""
        external = r.get("TargetMode") == "External"
        path = target if external else posixpath.normpath(posixpath.join(folder, target))
        out[r.get("Id")] = ((r.get("Type") or "").rsplit("/", 1)[-1], path.lstrip("/") if not external else None)
    return out


def _core(z):
    try:
        root = ET.fromstring(z.read("docProps/core.xml"))
    except (KeyError, ET.ParseError):
        return None, None
    title, author = root.find(DC + "title"), root.find(DC + "creator")
    return ((title.text or None) if title is not None else None), ((author.text or None) if author is not None else None)


def _store(store, data, ext):
    sha = common.sha256_bytes(data)
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
    return sha


def _ext_of(name):
    ext = posixpath.splitext(name or "")[1].lower().lstrip(".") or "png"
    return "jpg" if ext == "jpeg" else ext


def _picture(z, rels, rid, store, need_size):
    """(sha, ext, width, height, bytes) of a related picture, or None."""
    kind, target = rels.get(rid, (None, None))
    if kind != "image" or not target:
        return None
    try:
        data = z.read(target)
    except KeyError:
        return None
    if not data:
        return None
    w, h = common.image_size_any(data)
    if need_size and not (w and h):
        return None                                           # a picture whose size cannot be read (EMF, WMF)
    if common.is_decorative(w, h, len(data)):
        return None
    ext = _ext_of(target)
    return _store(store, data, ext), ext, w, h, len(data)


def _unit(number, kind, blocks, headings, label="", **extra):
    text = "\n\n".join(b for b in blocks if b.strip()).strip()
    u = {"number": number, "kind": kind, "text": text, "method": "text" if text else "none", "char_count": len(text),
         "textless": not text, "headings": headings, "label": label}
    u.update(extra)
    return u


def _doc(fmt, unit_kind, units, tables, images, title, author, warnings, engine):
    return {"fmt": fmt, "unit_kind": unit_kind, "pages": units, "page_count": len(units), "tables": tables,
            "images": images, "title": title, "author": author, "warnings": warnings, "engine": engine,
            "rejected_tables": [], "scanned_pages": [], "blank_pages": []}


# ------------------------------------------------------------------ PowerPoint
def _children(el):
    """Shape children, with markup-compatibility wrappers opened (the first Choice is taken)."""
    for ch in el:
        if ch.tag == MC + "AlternateContent":
            choice = ch.find(MC + "Choice")
            if choice is None:
                choice = ch.find(MC + "Fallback")
            if choice is not None:
                for sub in _children(choice):
                    yield sub
        else:
            yield ch


def _position(shape):
    for path in ("./" + P + "spPr/" + A + "xfrm/" + A + "off", "./" + P + "xfrm/" + A + "off",
                 "./" + P + "grpSpPr/" + A + "xfrm/" + A + "off"):
        off = shape.find(path)
        if off is not None:
            return int(off.get("y") or 0), int(off.get("x") or 0)
    return 0, 0


def _flat_shapes(tree):
    out = []
    for sh in _children(tree):
        if sh.tag == P + "grpSp":
            out.extend(_flat_shapes(sh))
        elif sh.tag in (P + "sp", P + "pic", P + "graphicFrame"):
            out.append(sh)
    return sorted(out, key=lambda s: (_position(s)[0] // ROW_TOLERANCE, _position(s)[1], _position(s)[0]))


def _para_text(p):
    return tidy("".join(t.text or "" for r in p.findall(A + "r") for t in r.findall(A + "t")))


def _shape_lines(sp):
    body = sp.find(P + "txBody")
    if body is None:
        return ""
    lines = []
    for p in body.findall(A + "p"):
        text = _para_text(p)
        if not text:
            continue
        ppr = p.find(A + "pPr")
        level = int(ppr.get("lvl") or 0) if ppr is not None else 0
        lines.append(("  " * level + "- " + text) if level or lines else text)
    return "\n".join(lines)


def _cell_text(tc):
    return tidy("\n".join("".join(t.text or "" for t in p.iter(A + "t")) for p in tc.iter(A + "p")))


def _pptx_grid(tbl):
    grid, merged = [], []
    for ri, tr in enumerate(tbl.findall(A + "tr")):
        row = []
        for ci, tc in enumerate(tr.findall(A + "tc")):
            if tc.get("hMerge") == "1" or tc.get("vMerge") == "1":
                row.append("")
                continue
            row.append(_cell_text(tc))
            gs, rs = int(tc.get("gridSpan") or 1), int(tc.get("rowSpan") or 1)
            if gs > 1 or rs > 1:
                merged.append({"row": ri, "col": ci, "rowspan": rs, "colspan": gs})
        grid.append(row)
    return grid, merged


def _placeholder(sp):
    ph = sp.find("./" + P + "nvSpPr/" + P + "nvPr/" + P + "ph")
    return ph.get("type") if ph is not None else None


def read_pptx(path, doc_id, store, want_tables=True, want_images=True):
    try:
        z = zipfile.ZipFile(path)
        pres = ET.fromstring(z.read("ppt/presentation.xml"))
    except (zipfile.BadZipFile, KeyError, ET.ParseError, OSError) as e:
        raise ValueError("the file could not be opened as a PowerPoint file - it may be damaged, password protected, "
                         "or not really a .pptx (%s)" % e)
    with z:
        prel = _rels(z, "ppt/presentation.xml")
        units, tables, images, warnings, seen, dupes = [], [], [], [], set(), 0
        lst = pres.find(P + "sldIdLst")
        ids = list(lst.findall(P + "sldId")) if lst is not None else []
        for number, sid in enumerate(ids, 1):
            part = prel.get(sid.get(R + "id"), (None, None))[1]
            try:
                root = ET.fromstring(z.read(part))
            except (KeyError, ET.ParseError, TypeError):
                warnings.append("slide %d could not be read" % number)
                units.append(_unit(number, "slide", [], []))
                continue
            srel = _rels(z, part)
            tree = root.find("./" + P + "cSld/" + P + "spTree")
            shapes = _flat_shapes(tree) if tree is not None else []
            title_el = next((s for s in shapes if s.tag == P + "sp" and _placeholder(s) in ("title", "ctrTitle")), None)
            title = tidy(" ".join(_para_text(p) for p in title_el.iter(A + "p"))) if title_el is not None else ""
            blocks = ["### " + title] if title else []
            texts, pictures = [], []
            for sh in shapes:
                if sh is title_el:
                    continue
                if sh.tag == P + "graphicFrame":
                    tbl = sh.find(".//" + A + "tbl")
                    if tbl is not None and want_tables:
                        grid, merged = _pptx_grid(tbl)
                        t = common.make_table(doc_id, len(tables) + 1, "slide", number, grid, "pptx-native",
                                              caption=common.pick_caption(texts[-2:][::-1]),
                                              heading_path=[title] if title else [], merged=merged, trusted_grid=True)
                        if t:
                            tables.append(t)
                            blocks.append(common.table_marker(t) if common.table_indexed(t) else common.table_text(t))
                    continue
                if sh.tag == P + "pic":
                    blip = sh.find(".//" + A + "blip")
                    if want_images and blip is not None:
                        got = _picture(z, srel, blip.get(R + "embed") or blip.get(R + "link"), store, True)
                        if got:
                            sha, ext, w, h, size = got
                            if sha in seen:
                                dupes += 1
                                continue
                            seen.add(sha)
                            y, x = _position(sh)
                            im = common.image_record(doc_id, len(images) + 1, "slide", number, sha, ext, w, h, size,
                                                     bbox=[float(x), float(y)])
                            images.append(im)
                            pictures.append(im)
                            blocks.append(common.image_marker(im))
                    continue
                text = _shape_lines(sh)
                if text:
                    texts.append(text)
                    blocks.append(text)
            context = tidy(" ".join([title] + texts), 600)
            for im in pictures:
                im["nearby_text"] = context
                if not im["caption"]:
                    im["caption"] = common.pick_caption(texts)
            notes = ""
            for kind, target in srel.values():
                if kind == "notesSlide" and target:
                    try:
                        nroot = ET.fromstring(z.read(target))
                    except (KeyError, ET.ParseError):
                        continue
                    for sp in nroot.iter(P + "sp"):
                        if _placeholder(sp) == "body":
                            notes = tidy(" ".join("".join(t.text or "" for t in p.iter(A + "t"))
                                                  for p in sp.iter(A + "p")))
                            break
            if notes:
                blocks.append("**Speaker notes:** " + notes)
            extra = {"has_speaker_notes": True} if notes else {}
            if root.get("show") == "0":
                extra["hidden"] = True
            units.append(_unit(number, "slide", blocks, [[title, 1]] if title else [], label=title, **extra))
        if dupes:
            warnings.append("%d repeated image(s) (logos) stored once" % dupes)
        title, author = _core(z)
    return _doc("pptx", "slide", units, tables, images, title, author, warnings, "zipfile-pptx")


# ------------------------------------------------------------------ Word
def _heading_level(name):
    name = (name or "").strip().lower()
    if name in ("title", "subtitle"):
        return 1
    if name.startswith("heading"):
        tail = name.replace("heading", "").strip()
        return max(1, min(int(tail), 4)) if tail.isdigit() else 2
    return None


def _styles(z):
    try:
        root = ET.fromstring(z.read("word/styles.xml"))
    except (KeyError, ET.ParseError):
        return {}, ""
    names, default = {}, ""
    for st in root.iter(W + "style"):
        n = st.find(W + "name")
        sid = st.get(W + "styleId")
        names[sid] = (n.get(W + "val") if n is not None else sid) or ""
        if st.get(W + "type") == "paragraph" and st.get(W + "default") == "1":
            default = names[sid]
    return names, default


_SKIP_IN_PARA = {W + "txbxContent", MC + "Fallback", W + "del", W + "delText"}


def _runs_text(el, out):
    """The paragraph's own words, leaving out text boxes (read on their own), fallbacks and deleted text."""
    for ch in el:
        if ch.tag in _SKIP_IN_PARA:
            continue
        if ch.tag == W + "t":
            out.append(ch.text or "")
        elif ch.tag in (W + "tab", W + "ptab"):
            out.append("\t")
        elif ch.tag in (W + "br", W + "cr"):
            out.append("\n")
        elif ch.tag == W + "noBreakHyphen":
            out.append("-")
        else:
            _runs_text(ch, out)


def _text_boxes(p):
    """Paragraph texts of the text boxes anchored in a paragraph (the Choice copy only)."""
    out = []

    def walk(el):
        for ch in el:
            if ch.tag == MC + "Fallback":
                continue
            if ch.tag == W + "txbxContent":
                for bp in ch.iter(W + "p"):
                    words = []
                    _runs_text(bp, words)
                    t = tidy("".join(words))
                    if t:
                        out.append(t)
                continue
            walk(ch)
    walk(p)
    return out


def _picture_ids(p):
    ids = []
    for el in p.iter():
        if el.tag == A + "blip":
            rid = el.get(R + "embed") or el.get(R + "link")
            if rid:
                ids.append(rid)
        elif el.tag == V + "imagedata" and el.get(R + "id"):
            ids.append(el.get(R + "id"))
    return ids


def _cell_words(tc):
    """A Word table cell's text: its paragraphs, and the text of any table nested in it."""
    parts = []
    for p in tc.iter(W + "p"):
        words = []
        _runs_text(p, words)
        if "".join(words).strip():
            parts.append("".join(words))
    return tidy("\n".join(parts))


def _docx_grid(tbl):
    grid, merged, origins = [], [], {}
    for ri, tr in enumerate(tbl.findall(W + "tr")):
        row, col = [], 0
        for tc in tr.findall(W + "tc"):
            pr = tc.find(W + "tcPr")
            span = int(pr.find(W + "gridSpan").get(W + "val") or 1) if pr is not None and pr.find(W + "gridSpan") is not None else 1
            vm = pr.find(W + "vMerge") if pr is not None else None
            if vm is not None and (vm.get(W + "val") or "continue") == "continue":
                row += [""] * span
                if col in origins:
                    origins[col]["rowspan"] += 1
            else:
                row += [_cell_words(tc)] + [""] * (span - 1)
                rec = {"row": ri, "col": col, "rowspan": 1, "colspan": span}
                if vm is not None or span > 1:
                    origins[col] = rec
                    merged.append(rec)
                else:
                    origins.pop(col, None)
            col += span
        grid.append(row)
    return grid, [m for m in merged if m["rowspan"] > 1 or m["colspan"] > 1]


def read_docx(path, doc_id, store, want_tables=True, want_images=True):
    try:
        z = zipfile.ZipFile(path)
        root = ET.fromstring(z.read("word/document.xml"))
    except (zipfile.BadZipFile, KeyError, ET.ParseError, OSError) as e:
        raise ValueError("the file could not be opened as a Word document - it may be damaged, password protected, "
                         "or not really a .docx (%s)" % e)
    with z:
        rels = _rels(z, "word/document.xml")
        names, default_style = _styles(z)
        section_level = SETTINGS["docx_section_heading_level"]
        max_chars = SETTINGS["docx_max_section_chars"]
        units, tables, images, warnings = [], [], [], []
        st = {"blocks": [], "label": "", "number": 1, "stack": [], "pending": [], "seen": set(), "dupes": 0}

        def headings_in(blocks):
            out = []
            for b in blocks:
                if b.startswith("#"):
                    hashes = len(b) - len(b.lstrip("#"))
                    out.append([b.lstrip("# ").strip(), max(1, hashes - 2)])
            return out

        def flush(next_label=""):
            text = "\n\n".join(b for b in st["blocks"] if b.strip()).strip()
            if text or units:
                units.append({"number": st["number"], "kind": "section", "text": text,
                              "method": "text" if text else "none", "char_count": len(text), "textless": not text,
                              "headings": headings_in(st["blocks"]), "label": st["label"]})
                st["number"] += 1
            st["blocks"], st["label"] = [], next_label

        def paragraph(p):
            blocks = st["blocks"]
            ppr = p.find(W + "pPr")
            sid = ppr.find(W + "pStyle").get(W + "val") if ppr is not None and ppr.find(W + "pStyle") is not None else None
            style = names.get(sid, sid or "") if sid else default_style
            level = _heading_level(style)
            if want_images:
                for rid in _picture_ids(p):
                    got = _picture(z, rels, rid, store, False)
                    if not got:
                        continue
                    sha, ext, w, h, size = got
                    if sha in st["seen"]:
                        st["dupes"] += 1
                        continue
                    st["seen"].add(sha)
                    im = common.image_record(doc_id, len(images) + 1, "section", st["number"], sha, ext, w, h, size,
                                             nearby=" ".join(b for b in blocks[-2:] if not b.startswith("[[")))
                    images.append(im)
                    blocks.append(common.image_marker(im))
                    st["pending"].append(im)
            words = []
            _runs_text(p, words)
            text = tidy("".join(words))
            boxes = _text_boxes(p)
            if text:
                if st["pending"] and common.looks_like_caption(text):
                    for im in st["pending"]:
                        if not im["caption"]:
                            im["caption"] = tidy(text, 300)
                    st["pending"] = []
                if level is not None and level <= section_level and (blocks or units):
                    flush(next_label=text)
                    st["stack"] = [(level, text)]
                    st["blocks"].append("#" * (level + 2) + " " + text)
                elif level is not None:
                    while st["stack"] and st["stack"][-1][0] >= level:
                        st["stack"].pop()
                    st["stack"].append((level, text))
                    if not st["label"]:
                        st["label"] = text
                    blocks.append("#" * (min(level, 4) + 2) + " " + text)
                elif (style and "list" in style.lower()) or (ppr is not None and ppr.find(W + "numPr") is not None):
                    blocks.append("- " + text)
                else:
                    blocks.append(text)
                    st["pending"] = []
            st["blocks"].extend(boxes)
            if text and sum(len(b) for b in st["blocks"]) > max_chars:
                label = st["label"]
                flush(next_label=(label + " (continued)") if label else "")

        def table(tbl):
            grid, merged = _docx_grid(tbl)
            blocks = st["blocks"]
            t = common.make_table(doc_id, len(tables) + 1, "section", st["number"], grid, "docx-native",
                                  caption=common.pick_caption(list(reversed(blocks[-2:]))),
                                  heading_path=[h for _, h in st["stack"]], merged=merged, trusted_grid=True)
            if t:
                tables.append(t)
                blocks.append(common.table_marker(t) if common.table_indexed(t) else common.table_text(t))

        def walk(container):
            for ch in container:
                if ch.tag == W + "p":
                    paragraph(ch)
                elif ch.tag == W + "tbl" and want_tables:
                    table(ch)
                elif ch.tag == W + "sdt":
                    content = ch.find(W + "sdtContent")
                    if content is not None:
                        walk(content)

        body = root.find(W + "body")
        if body is not None:
            walk(body)
        flush()
        if st["dupes"]:
            warnings.append("%d repeated image(s) (logos/headers) stored once" % st["dupes"])
        title, author = _core(z)
    return _doc("docx", "section", units, tables, images, title, author, warnings, "zipfile-docx")


# ------------------------------------------------------------------ picture files
_CAMEL = re.compile(r"(?<=[a-z])(?=[A-Z])")
_SPLIT = re.compile(r"[\s_\-.,;:()\[\]{}]+")


def search_context(rel):
    """A picture file's searchable words: its folders and its name, split into words."""
    seen, out = set(), []
    for part in [p for p in (rel or "").replace("\\", "/").split("/") if p]:
        part = re.sub(r"\.[A-Za-z0-9]{1,5}$", "", part)
        for w in _SPLIT.split(_CAMEL.sub(" ", part)):
            if w and w.lower() not in seen:
                seen.add(w.lower())
                out.append(w)
    return " ".join(out)


def read_image(path, rel, doc_id, store):
    with open(path, "rb") as f:
        data = f.read()
    w, h = common.image_size_any(data)
    if not data or not (w and h):
        raise ValueError("the image file could not be read - it may be damaged, incomplete, or not really an image")
    ext = _ext_of(path)
    sha = _store(store, data, ext)
    im = common.image_record(doc_id, 1, "image", 1, sha, ext, w, h, len(data), nearby=search_context(rel))
    im["standalone_source_file"] = True
    im["original_filename"] = os.path.basename(path)
    unit = {"number": 1, "kind": "image", "text": common.image_marker(im), "method": "image", "char_count": 0,
            "textless": False, "headings": [], "label": os.path.basename(path)}
    return _doc("image", "image", [unit], [], [im], None, None, [], "pymupdf:%s" % ext)
