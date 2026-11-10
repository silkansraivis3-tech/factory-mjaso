# -*- coding: utf-8 -*-
"""test_builder - the factory's knowledge-base builder makes a knowledge base the factory's own readers read.

    python test_builder.py

Every fixture is made here, at test time, with PyMuPDF and zipfile, in a temp folder: a text PDF with a running
header that names its page, a heading number on its own line and line-end hyphens; a two-column PDF; a ruled table;
a scanned page, the same scan turned a quarter, a Latvian scan, a Russian scan and a blank page; a Russian text PDF; a
PowerPoint deck with speaker notes and a hidden slide; a Russian deck; a Word file with tables and a text box; and an
identical copy. Pinned below:

  * the contract is proved by RUNNING the factory's readers on the result - kb_tool.py detect, sources and search,
    fact_check.py's index, photo_catalogue.py's pictures - never by re-implementing them; every chunk slice parses;
  * one page per piece, running headers in no heading path, a table's words indexed once, "4.1 Goal" as one heading,
    "LNG-fuelled" keeps its hyphen;
  * slides in deck order with their notes and the hidden slide marked; a Word text box and table are read;
  * Cyrillic text is indexed and found by a Cyrillic query with no reading model at all;
  * scanned pages are read (turned, Latvian, Russian) when the reading models are on this computer - else the check
    says it is skipped; with none and no network the build still completes and says which files are needed;
  * the model fetch: fetched and verified, a wrong checksum refused, offline refused (a file:// stand-in, no network);
  * a second run reads nothing again; no source file is ever changed.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
SCRIPTS = os.path.join(os.path.dirname(os.path.dirname(HERE)), "scripts")
KB_TOOL = os.path.join(os.path.dirname(HERE), "scripts", "kb_tool.py")
BUILD = os.path.join(HERE, "kb_build.py")

PASS, FAIL = [], []


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print(("  ok    " if ok else "  FAIL  ") + name + (("  -> " + str(detail)) if detail and not ok else ""))


def skip(name, why):
    print("  skip  %s  (%s)" % (name, why))


try:
    import pymupdf
except ImportError:
    print("PyMuPDF is not installed - nothing to test (python -m pip install pymupdf).")
    sys.exit(1)

import ocr  # noqa: E402

FONT = next((f for f in (r"C:\Windows\Fonts\arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                         "/Library/Fonts/Arial.ttf") if os.path.isfile(f)), None)


# ------------------------------------------------------------------ fixtures
def text(page, x, y, s, size=11, bold=False):
    if FONT:
        page.insert_text((x, y), s, fontsize=size, fontname="F0" if not bold else "F1",
                         fontfile=FONT if not bold else (FONT.replace("arial.ttf", "arialbd.ttf")
                                                         if os.path.isfile(FONT.replace("arial.ttf", "arialbd.ttf")) else FONT))
    else:
        page.insert_text((x, y), s, fontsize=size, fontname="hebo" if bold else "helv")


BODY = ("The fuel containment system shall be designed so that a leak from the tank cannot reach the engine room. "
        "Gas detection is fitted in every space where gas may collect, and the alarm is given at a level well "
        "below the lower explosive limit.")


def para(page, y, words, width=90):
    line = ""
    for w in words.split():
        if len(line) + len(w) + 1 > width:
            text(page, 72, y, line)
            y += 14
            line = w
        else:
            line = (line + " " + w).strip()
    if line:
        text(page, 72, y, line)
        y += 14
    return y + 8


def make_text_pdf(path):
    doc = pymupdf.open()
    for n in range(1, 7):
        page = doc.new_page()
        text(page, 72, 30, "Annex, page %d" % n, 9)                    # a running header that names the page
        text(page, 280, 820, "IGF Code - consolidated edition", 9)     # a running footer
        y = 80
        if n == 2:
            text(page, 72, y, "4.1", 14, bold=True)
            text(page, 72, y + 18, "Goal", 14, bold=True)
            y += 50
        if n == 3:
            text(page, 72, y, "Engines on LNG-")
            text(page, 72, y + 14, "fuelled ships burn low-flashpoint fuel. A low-")
            text(page, 72, y + 28, "flashpoint fuel is kept in a tank with a pump-")
            text(page, 72, y + 42, "room beside it.")
            y += 70
        for k in range(4):
            y = para(page, y, ("Page %d paragraph %d. " % (n, k)) + BODY + " Keyword pagemark%d." % n)
    doc.save(path)


def make_columns_pdf(path):
    doc = pymupdf.open()
    page = doc.new_page()
    left = ["Left column line %d about cargo tanks" % i for i in range(14)]
    right = ["Right column line %d about bunkering" % i for i in range(14)]
    for i, (a, b) in enumerate(zip(left, right)):
        text(page, 50, 80 + i * 14, a)
        text(page, 320, 80 + i * 14, b)
    doc.save(path)


def make_table_pdf(path):
    doc = pymupdf.open()
    page = doc.new_page()
    y = para(page, 70, "The table below gives the alarm settings for the gas detectors in the fuel preparation room.")
    rows = [["Gas", "Alarm", "Shutdown"], ["Methane", "20 % LEL", "40 % LEL"], ["Methanol", "zeltrix 10", "30 % LEL"],
            ["Ammonia", "25 ppm", "300 ppm"]]
    x0, w, h = 72, 150, 22
    rows.append(["Hydrogen", "4 % LEL", ""])
    for r, row in enumerate(rows):
        for c, cell in enumerate(row):
            text(page, x0 + c * w + 4, y + r * h + 15, cell)
    # a part number printed across the column line, as in the KwikDraw manual: the line runs through "463799"
    text(page, x0 + 2 * w - 12, y + (len(rows) - 1) * h + 15, "463799")
    for r in range(len(rows) + 1):
        page.draw_line((x0, y + r * h), (x0 + 3 * w, y + r * h))
    for c in range(4):
        page.draw_line((x0 + c * w, y), (x0 + c * w, y + len(rows) * h))
    para(page, y + len(rows) * h + 30, "Below the table the text goes on about the ventilation of the room. " * 3)
    doc.save(path)


def render(src_page, rotate=0, dpi=150):
    pix = src_page.get_pixmap(dpi=dpi)
    return pix, rotate


def make_scans_pdf(path, words, lang_words=None, russian=None):
    """page 1 a scan, page 2 the same scan turned 90 degrees, page 3 a Latvian scan, page 4 blank, page 5 Russian."""
    src = pymupdf.open()
    for body in (words, words, lang_words, None, russian):
        p = src.new_page()
        if body:
            para(p, 80, body, 70)
    out = pymupdf.open()
    for i, body in enumerate((words, words, lang_words, None, russian)):
        page = out.new_page(width=842, height=595) if i == 1 else out.new_page()
        if body is None:
            continue                                         # a blank page: nothing on it at all
        pix = src[i].get_pixmap(dpi=200)
        page.insert_image(page.rect, pixmap=pix, rotate=90 if i == 1 else 0)     # page 2: the scan lies sideways
    out.save(path)


def make_russian_pdf(path):
    doc = pymupdf.open()
    page = doc.new_page()
    para(page, 80, "Требования к топливной системе: утечка газа из цистерны не должна достигать машинного отделения. "
                   "Газоанализатор устанавливается в каждом помещении.", 70)
    doc.save(path)


def zip_write(path, files):
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in files.items():
            z.writestr(name, data)


PNG = None


def png_bytes():
    global PNG
    if PNG is None:
        # noise, so the picture is not so small in bytes that it counts as decorative
        pix = pymupdf.Pixmap(pymupdf.csRGB, 300, 200, os.urandom(300 * 200 * 3), False)
        PNG = pix.tobytes("png")
    return PNG


def make_pptx(path, slides):
    """slides: [(title, [body lines], notes, hidden)]"""
    P = "http://schemas.openxmlformats.org/presentationml/2006/main"
    A = "http://schemas.openxmlformats.org/drawingml/2006/main"
    R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    files = {"[Content_Types].xml": '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>'}
    ids, prels = [], []
    for n, (title, body, notes, hidden) in enumerate(slides, 1):
        paras = "".join('<a:p><a:r><a:t>%s</a:t></a:r></a:p>' % b for b in body)
        sp_title = ('<p:sp><p:nvSpPr><p:cNvPr id="2" name="t"/><p:cNvSpPr/><p:nvPr><p:ph type="title"/></p:nvPr></p:nvSpPr>'
                    '<p:spPr><a:xfrm><a:off x="0" y="0"/></a:xfrm></p:spPr><p:txBody><a:p><a:r><a:t>%s</a:t></a:r></a:p></p:txBody></p:sp>' % title)
        sp_body = ('<p:sp><p:nvSpPr><p:cNvPr id="3" name="b"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>'
                   '<p:spPr><a:xfrm><a:off x="0" y="1000000"/></a:xfrm></p:spPr><p:txBody>%s</p:txBody></p:sp>' % paras)
        pic = ('<p:pic><p:nvPicPr><p:cNvPr id="4" name="p"/><p:cNvPicPr/><p:nvPr/></p:nvPicPr><p:blipFill>'
               '<a:blip r:embed="rIdImg"/></p:blipFill><p:spPr><a:xfrm><a:off x="100" y="3000000"/></a:xfrm></p:spPr></p:pic>'
               if n == 1 else "")
        files["ppt/slides/slide%d.xml" % n] = (
            '<?xml version="1.0" encoding="UTF-8"?><p:sld xmlns:p="%s" xmlns:a="%s" xmlns:r="%s"%s><p:cSld><p:spTree>%s%s%s'
            '</p:spTree></p:cSld></p:sld>' % (P, A, R, ' show="0"' if hidden else "", pic, sp_body, sp_title))
        rels = ['<Relationship Id="rIdN" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/notesSlide" '
                'Target="../notesSlides/notesSlide%d.xml"/>' % n] if notes else []
        if n == 1:
            rels.append('<Relationship Id="rIdImg" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" '
                        'Target="../media/image1.png"/>')
        files["ppt/slides/_rels/slide%d.xml.rels" % n] = (
            '<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">%s'
            '</Relationships>' % "".join(rels))
        if notes:
            files["ppt/notesSlides/notesSlide%d.xml" % n] = (
                '<?xml version="1.0"?><p:notes xmlns:p="%s" xmlns:a="%s"><p:cSld><p:spTree><p:sp><p:nvSpPr><p:cNvPr id="2" name="n"/>'
                '<p:cNvSpPr/><p:nvPr><p:ph type="body"/></p:nvPr></p:nvSpPr><p:txBody><a:p><a:r><a:t>%s</a:t></a:r></a:p>'
                '</p:txBody></p:sp></p:spTree></p:cSld></p:notes>' % (P, A, notes))
        # deck order is presentation.xml's order, not the file names: the second slide file is listed first
        ids.append((n, '<p:sldId id="%d" r:id="rId%d"/>' % (255 + n, n)))
        prels.append('<Relationship Id="rId%d" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" '
                     'Target="slides/slide%d.xml"/>' % (n, n))
    files["ppt/media/image1.png"] = png_bytes()
    files["ppt/presentation.xml"] = ('<?xml version="1.0"?><p:presentation xmlns:p="%s" xmlns:r="%s"><p:sldIdLst>%s</p:sldIdLst>'
                                     '</p:presentation>' % (P, R, "".join(x for _, x in ids)))
    files["ppt/_rels/presentation.xml.rels"] = ('<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/'
                                                'package/2006/relationships">%s</Relationships>' % "".join(prels))
    zip_write(path, files)


def make_docx(path, body_xml):
    W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    files = {
        "[Content_Types].xml": '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>',
        "word/document.xml": ('<?xml version="1.0" encoding="UTF-8"?><w:document xmlns:w="%s" '
                              'xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006" '
                              'xmlns:wps="http://schemas.microsoft.com/office/word/2010/wordprocessingShape">'
                              '<w:body>%s</w:body></w:document>' % (W, body_xml)),
        "word/styles.xml": ('<?xml version="1.0"?><w:styles xmlns:w="%s"><w:style w:type="paragraph" w:styleId="Heading1">'
                            '<w:name w:val="heading 1"/></w:style><w:style w:type="paragraph" w:default="1" w:styleId="Normal">'
                            '<w:name w:val="Normal"/></w:style></w:styles>' % W),
    }
    zip_write(path, files)


def wp(t, style=None):
    s = '<w:pPr><w:pStyle w:val="%s"/></w:pPr>' % style if style else ""
    return "<w:p>%s<w:r><w:t>%s</w:t></w:r></w:p>" % (s, t)


def wtable(rows):
    return "<w:tbl>%s</w:tbl>" % "".join("<w:tr>%s</w:tr>" % "".join("<w:tc>%s</w:tc>" % wp(c) for c in r) for r in rows)


TEXTBOX = ('<w:p><w:r><mc:AlternateContent><mc:Choice Requires="wps"><w:drawing><wps:txbx><w:txbxContent>%s'
           '</w:txbxContent></wps:txbx></w:drawing></mc:Choice><mc:Fallback><w:pict><w:txbxContent>%s</w:txbxContent>'
           '</w:pict></mc:Fallback></mc:AlternateContent></w:r></w:p>')


def sha_tree(root):
    out = {}
    for d, _s, files in os.walk(root):
        if "KNOWLEDGE_BASE" in d:
            continue
        for f in files:
            p = os.path.join(d, f)
            out[p] = hashlib.sha256(open(p, "rb").read()).hexdigest()
    return out


def run(args, env=None, timeout=300):
    p = subprocess.run([sys.executable] + args, capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env=dict(os.environ, **(env or {})), timeout=timeout)
    return p.returncode, p.stdout + p.stderr


def chunks_of(kb):
    with io.open(os.path.join(kb, "search_index", "chunks.jsonl"), encoding="utf-8") as f:
        return [json.loads(l) for l in f]


def meta_of(kb, filename):
    man = json.load(io.open(os.path.join(kb, "SOURCE_MANIFEST.json"), encoding="utf-8"))
    s = next(x for x in man["sources"] if x["original_filename"] == filename)
    return s, (json.load(io.open(os.path.join(kb, s["output_folder"], "metadata.json"), encoding="utf-8"))
               if s.get("output_folder") else None)


# ------------------------------------------------------------------ the test
def main():
    started = time.time()
    tmp = tempfile.mkdtemp(prefix="kb_builder_test_")
    src = os.path.join(tmp, "master", "source_files")
    course = os.path.join(tmp, "master", "course")
    os.makedirs(os.path.join(course, "working_claude"))
    os.makedirs(os.path.join(src, "regulations"))
    os.makedirs(os.path.join(src, "old_course", "archive"))
    env = {"NOVIKONTAS_KB_CACHE": os.path.join(tmp, "cache")}
    tess, models = ocr.ensure_tessdata(["eng", "lav", "rus"], say=print)      # the same places the build looks in
    print("reading models: %s %s" % (tess or "none found", sorted(models)))
    try:
        make_text_pdf(os.path.join(src, "regulations", "IGF text.pdf"))
        make_columns_pdf(os.path.join(src, "regulations", "two columns.pdf"))
        make_table_pdf(os.path.join(src, "regulations", "alarm table.pdf"))
        make_russian_pdf(os.path.join(src, "regulations", "russian text.pdf"))
        make_scans_pdf(os.path.join(src, "old_course", "scans.pdf"),
                       "Scanned instruction: the bunkering hose must be purged with nitrogen before it is disconnected. "
                       "Check the pressure gauge reads zero before the flange is opened.",
                       "Kuģa drošības instrukcija: degvielas sistēmas pārbaude jāveic pirms bunkurēšanas. "
                       "Personālam jāievēro ugunsdrošības noteikumi un jālieto aizsardzības līdzekļi.",
                       "Инструкция по безопасности: перед бункеровкой необходимо проверить топливную систему. "
                       "Персонал должен соблюдать правила пожарной безопасности.")
        make_pptx(os.path.join(src, "old_course", "deck.pptx"),
                  [("Bunkering safety", ["Check the hoses", "Purge with nitrogen"], "Remind them of the zero reading", False),
                   ("Hidden slide", ["Spare material"], "", True),
                   ("Closing", ["Questions"], "", False)])
        make_pptx(os.path.join(src, "old_course", "russian deck.pptx"),
                  [("Безопасность бункеровки", ["Проверить шланги", "Продуть азотом"], "Напомнить о нуле", False)])
        make_docx(os.path.join(src, "old_course", "exercise.docx"),
                  wp("Exercise one", "Heading1") + wp("Read the procedure below.")
                  + wtable([["Step", "Action"], ["1", "Open the vent valve"], ["2", "Start the purge fan"]])
                  + TEXTBOX % (wp("Text box note: wear gloves"), wp("Text box note: wear gloves"))
                  + wp("Exercise two", "Heading1") + wp("Write down the readings."))
        make_docx(os.path.join(src, "old_course", "russian.docx"), wp("Упражнение", "Heading1") + wp("Записать показания манометра."))
        shutil.copyfile(os.path.join(src, "regulations", "IGF text.pdf"), os.path.join(src, "old_course", "archive", "IGF copy.pdf"))
    except Exception as e:                                     # noqa: BLE001
        check("fixtures made", False, e)
        return finish(tmp, started)
    before = sha_tree(src)

    code, out = run([BUILD, src, "--jobs", "2"], env)
    kb = os.path.join(src, "KNOWLEDGE_BASE")
    check("build exits 0", code == 0, out[-600:])
    check("one progress line per file", len(re.findall(r"^\[\d+/\d+\]", out, re.M)) == 10, out[-400:])
    check("nothing left of the build folder", not os.path.exists(kb + ".building"))
    man = json.load(io.open(os.path.join(kb, "SOURCE_MANIFEST.json"), encoding="utf-8"))
    idx = json.load(io.open(os.path.join(kb, "search_index", "index.json"), encoding="utf-8"))
    check("manifest names the builder", man["tool"] == "COURSE FACTORY KB BUILDER", man["tool"])
    check("index version 5 with BM25", idx["index_version"] == 5 and idx["bm25"]["k1"] == 1.2)
    check("every source listed once", man["source_count"] == 10 and len(man["sources"]) == 10)

    # --- the readers, run as they are
    code, out = run([KB_TOOL, "detect", kb])
    check("kb_tool detect: a Course Source Processor knowledge base", code == 0 and "course_source_processor" in out, out)
    code, out = run([KB_TOOL, "sources", kb, "--course", course, "--json"])
    check("kb_tool sources reads it", code == 0, out[-400:])
    check("kb_tool sources groups the identical copy", "IGF copy.pdf" in out and "IGF text.pdf" in out, out[-400:])
    code, out = run([KB_TOOL, "search", kb, "gas detection alarm lower explosive limit", "--course", course, "--stdout"])
    check("kb_tool search finds the text PDF", code == 0 and "IGF text.pdf" in out, out[-300:])
    code, out = run([KB_TOOL, "search", kb, "pagemark4", "--course", course, "--stdout", "--top", "3"])
    check("a search hit names its own page", "## 1 · IGF text.pdf — page 4" in out, out[:800])
    code, out = run([KB_TOOL, "search", kb, "газоанализатор помещении", "--course", course, "--stdout", "--top", "3"])
    check("a Cyrillic query finds the Russian PDF (no reading model needed)", "russian text.pdf" in out, out[-300:])
    code, out = run([KB_TOOL, "search", kb, "шланги азотом", "--course", course, "--stdout", "--top", "3"])
    check("a Cyrillic query finds the Russian deck", "russian deck.pptx" in out, out[-300:])
    code, out = run([KB_TOOL, "search", kb, "манометра", "--course", course, "--stdout", "--top", "3"])
    check("a Cyrillic query finds the Russian Word file", "russian.docx" in out, out[-300:])
    code, out = run(["-c", "import sys; sys.path.insert(0, %r); import fact_check; "
                           "print(fact_check.Index([%r]).search('purge fan vent valve', 3))" % (SCRIPTS, kb)])
    check("fact_check's index reads it", code == 0 and "exercise.docx" in out, out[-300:])
    code, out = run([KB_TOOL, "decision", course, "--built", kb])
    code2, out2 = run(["-c", "import sys; sys.path.insert(0, %r); import photo_catalogue; "
                             "print(len(photo_catalogue.kb_photos(%r)))" % (SCRIPTS, course)])
    check("photo_catalogue finds the knowledge base's pictures", code == 0 and code2 == 0 and out2.strip().splitlines()[-1] != "0",
          out + out2[-300:])
    bad = 0
    with open(os.path.join(kb, "search_index", "chunks.jsonl"), "rb") as f:
        for i, c in enumerate(idx["chunks"]):
            f.seek(c["off"])
            rec = json.loads(f.read(c["bytes"]).decode("utf-8"))
            bad += rec["chunk_id"] != c["id"] or c["i"] != i
    check("every chunk slice parses at its offset", bad == 0 and idx["chunk_count"] == len(idx["chunks"]), bad)

    # --- PDF reading
    ch = chunks_of(kb)
    igf = [c for c in ch if c["source_filename"] == "IGF text.pdf" and c["kind"] == "text"]
    check("one page per piece", igf and all(c["page_start"] == c["page_end"] for c in igf),
          [(c["page_start"], c["page_end"]) for c in igf])
    check("no heading path names a page", not any(re.search(r"page\s*\d", " ".join(c["heading_path"]), re.I) for c in ch),
          [c["heading_path"] for c in ch if re.search(r"page\s*\d", " ".join(c["heading_path"]), re.I)][:3])
    check("running headers and footers left out of the pieces",
          not any("Annex, page" in c["text"] or "consolidated edition" in c["text"] for c in igf))
    s, meta = meta_of(kb, "IGF text.pdf")
    check("excluded running headers listed in metadata.json", len(meta["excluded_running_headers"]) >= 2,
          meta["excluded_running_headers"])
    md = io.open(os.path.join(kb, s["output_folder"], "document.md"), encoding="utf-8").read()
    check("document.md keeps '## Page N' units", len(re.findall(r"^## Page \d+$", md, re.M)) == 6)
    heads = [h["text"] for u in meta["units"] for h in u["headings"]]
    check("a heading number on its own line joins its title: '4.1 Goal'", "4.1 Goal" in heads, heads[:8])
    alltext = " ".join(c["text"] for c in igf).replace("­", "-")    # the test font writes its hyphen as U+00AD
    check("a line-end hyphen in an upper-case word is kept: LNG-fuelled", "LNG-fuelled" in alltext)
    check("a hyphen the document writes elsewhere is kept: low-flashpoint", "lowflashpoint" not in alltext
          and alltext.count("low-flashpoint") >= 2, re.findall(r"low.?flashpoint", alltext))
    check("an ordinary line-end hyphen is joined: pumproom", "pumproom" in alltext)
    cols = " ".join(c["text"] for c in ch if c["source_filename"] == "two columns.pdf")
    check("two columns read column by column", cols.find("Left column line 13") < cols.find("Right column line 0"))
    tab = [c for c in ch if c["source_filename"] == "alarm table.pdf"]
    check("a ruled table is a piece of its own", any(c["kind"] == "table" and "zeltrix" in c["text"] for c in tab),
          [c["kind"] for c in tab])
    check("a table's words are indexed once (not in the page text)",
          sum(c["text"].count("zeltrix") for c in tab) == 1 and idx["df"].get("zeltrix") == 1, idx["df"].get("zeltrix"))
    check("the page text carries the table marker", any("[[TABLE " in c["text"] for c in tab if c["kind"] == "text"))
    s, meta = meta_of(kb, "alarm table.pdf")
    cells = [c for t in meta["tables"] for row in t["cells"] for c in row]
    check("a number the column line runs through stays whole, in one cell", "463799" in cells
          and not any(("4637" in c or "3799" in c) and c != "463799" for c in cells), [c for c in cells if "37" in c])
    # A number of more than four digits is not a search term in a version-5 index (the Course Source Processor's
    # tokenizer, used by kb_tool on both sides), so the row is searched by its words and must show the number whole.
    code, out = run([KB_TOOL, "search", kb, "hydrogen LEL", "--course", course, "--stdout", "--top", "3"])
    check("kb_tool search returns the row with the number whole", "alarm table.pdf" in out and "463799" in out, out[-300:])
    man_rows = {x["original_filename"]: x for x in man["sources"]}
    check("every page word is kept (words_kept = words_on_pages)",
          all(man_rows[n]["words_kept"] == man_rows[n]["words_on_pages"] > 0 for n in ("alarm table.pdf", "IGF text.pdf")),
          [(n, man_rows[n]["words_on_pages"], man_rows[n]["words_kept"]) for n in ("alarm table.pdf", "IGF text.pdf")])
    unfillable_table_checks()

    # --- Office files
    s, meta = meta_of(kb, "deck.pptx")
    units = meta["units"]
    check("slides numbered in deck order", [u.get("label") for u in units] == ["Bunkering safety", "Hidden slide", "Closing"],
          [u.get("label") for u in units])
    check("a hidden slide is read and marked hidden", units[1].get("hidden") and not units[0].get("hidden"))
    deck = " ".join(c["text"] for c in ch if c["source_filename"] == "deck.pptx")
    check("speaker notes are read", "Speaker notes:** Remind them of the zero reading" in deck)
    check("a slide picture is kept with its slide", meta["images"] and meta["images"][0]["location"] == {"kind": "slide", "number": 1}
          and os.path.isfile(os.path.join(kb, s["output_folder"], "images", meta["images"][0]["file"])))
    s, meta = meta_of(kb, "exercise.docx")
    ex = [c for c in ch if c["source_filename"] == "exercise.docx"]
    check("Word sections start at each top-level heading", meta["unit_count"] == 2, meta["unit_count"])
    check("a Word text box is read once", sum(c["text"].count("Text box note: wear gloves") for c in ex) == 1)
    check("a Word table is a piece of its own", any(c["kind"] == "table" and "purge fan" in c["text"] for c in ex))
    s, _ = meta_of(kb, "IGF copy.pdf")
    check("an identical copy is read once", s["status"] == "duplicate" and s["duplicate_of_path"] == "regulations/IGF text.pdf", s)

    # --- scanned pages
    s, meta = meta_of(kb, "scans.pdf")
    u = {x["number"]: x for x in meta["units"]}
    check("a blank page is not sent to OCR and not counted as missing text", u[4].get("blank") and not u[4]["textless"], u[4])
    md = io.open(os.path.join(kb, s["output_folder"], "document.md"), encoding="utf-8").read()
    if not tess:
        skip("scanned pages read", "no reading models on this computer")
    else:
        check("a scanned page is read", u[1]["method"] == "ocr" and "nitrogen" in md, u[1])
        check("a scan turned a quarter is read", u[2]["method"] == "ocr" and u[2].get("ocr_rotation") in (90, 270), u[2])
        if "lav" in models:
            check("a Latvian scan is read with the Latvian model", u[3].get("ocr_language", "").startswith("lav")
                  and "drošības" in md.lower(), u[3])
        else:
            skip("Latvian scan", "lav.traineddata not found")
        if "rus" in models:
            check("a Russian scan is read with the Russian model", u[5].get("ocr_language", "").startswith("rus")
                  and "безопасност" in md.lower(), u[5])
        else:
            skip("Russian scan", "rus.traineddata not found")

    # --- second run, and the sources untouched
    t0 = time.time()
    code, out = run([BUILD, src, "--jobs", "2"], env)
    man2 = json.load(io.open(os.path.join(kb, "SOURCE_MANIFEST.json"), encoding="utf-8"))
    check("a second run reads nothing again", code == 0 and man2["run"]["documents_reused_from_cache"] == 9,
          (code, man2["run"].get("documents_reused_from_cache"), out[-300:]))
    print("        (second run %.1f s)" % (time.time() - t0))
    check("no source file was changed", sha_tree(src) == before)

    # --- no reading models and no network: the build completes and says what is needed
    bare = os.path.join(tmp, "bare")
    shutil.copytree(os.path.join(src, "old_course"), os.path.join(bare, "old_course"),
                    ignore=shutil.ignore_patterns("archive"))
    code, out = run([BUILD, bare, "--jobs", "1"], {"NOVIKONTAS_KB_CACHE": os.path.join(tmp, "cache2"),
                                                   "NOVIKONTAS_OFFLINE": "1", "LOCALAPPDATA": os.path.join(tmp, "nolocal"),
                                                   "HOME": os.path.join(tmp, "nolocal"), "USERPROFILE": os.path.join(tmp, "nolocal"),
                                                   "NOVIKONTAS_KB_BUILDER": os.path.join(tmp, "nobuilder"),
                                                   "NOVIKONTAS_TESSDATA": "", "TESSDATA_PREFIX": ""})
    na = os.path.join(bare, "KNOWLEDGE_BASE", "NEEDS_ATTENTION.md")
    check("with no reading models the build still completes", code == 0, out[-500:])
    check("the closing lines say how many pages and which files are needed",
          "scanned page(s) could not be read" in out and "eng.traineddata" in out and "lav.traineddata" in out, out[-500:])
    check("the unread scanned pages are listed in NEEDS_ATTENTION.md",
          os.path.isfile(na) and "scans.pdf" in io.open(na, encoding="utf-8").read())

    # --- the model fetch, with a file:// stand-in for the network
    fetch_checks(tmp)
    return finish(tmp, started)


def unfillable_table_checks():
    """A grid whose cells do not cover a word inside it is not kept as a table: its words stay page text."""
    import pdf

    class Row(object):
        def __init__(self, cells):
            self.cells = cells

    class Cand(object):
        bbox = (0, 0, 200, 40)
        rows = [Row([(0, 0, 100, 20), (100, 0, 200, 20)]), Row([(0, 20, 100, 40), None])]   # the lower right not a cell

    class Finder(object):
        tables = [Cand()]

    class Page(object):
        def find_tables(self):
            return Finder()

        def get_text(self, kind):
            return [(5, 5, 40, 15, "Gas", 0, 0, 0), (105, 5, 150, 15, "Alarm", 0, 0, 1),
                    (5, 25, 60, 35, "Methane", 0, 1, 0), (120, 25, 180, 35, "463799", 0, 1, 1)]

    rejected = []
    got = pdf.page_tables(Page(), 1, [], rejected)
    check("a table that cannot hold every word inside it is not kept", got == [] and rejected
          and "463799" in rejected[0]["reason"], (got, rejected))
    grid, left = pdf.fill_cells([[(0, 0, 100, 20), (100, 0, 200, 20)]], [(90, 5, 130, 15, "634181", 0, 0, 0)])
    check("a word across a cell edge goes whole to the cell holding most of it", grid == [["", "634181"]] and not left,
          grid)


def fetch_checks(tmp):
    local = ocr.local_tessdata()
    if not ocr.model_ok(os.path.join(local, "eng.traineddata"), "eng"):
        skip("model fetch", "no verified eng.traineddata in %s to serve as the stand-in" % local)
        return
    good = os.path.join(tmp, "serve_good")
    badd = os.path.join(tmp, "serve_bad")
    os.makedirs(good)
    os.makedirs(badd)
    shutil.copyfile(os.path.join(local, "eng.traineddata"), os.path.join(good, "eng.traineddata"))
    with open(os.path.join(badd, "eng.traineddata"), "wb") as f:
        f.write(b"not a model" * 1000)
    target = os.path.join(tmp, "fetched")
    said = []
    saved = {k: os.environ.get(k) for k in ("NOVIKONTAS_TESSDATA_URL", "NOVIKONTAS_OFFLINE")}
    try:
        os.environ.pop("NOVIKONTAS_OFFLINE", None)
        os.environ["NOVIKONTAS_TESSDATA_URL"] = "file:///" + badd.replace("\\", "/").lstrip("/") + "/%s.traineddata"
        ok = ocr.fetch_model("eng", target, said.append)
        check("a fetched model with the wrong checksum is refused", not ok and not os.listdir(target), (ok, said))
        os.environ["NOVIKONTAS_OFFLINE"] = "1"
        os.environ["NOVIKONTAS_TESSDATA_URL"] = "file:///" + good.replace("\\", "/").lstrip("/") + "/%s.traineddata"
        check("offline, nothing is fetched", not ocr.fetch_model("eng", target, said.append))
        os.environ.pop("NOVIKONTAS_OFFLINE")
        ok = ocr.fetch_model("eng", target, said.append)
        check("a model is fetched, checked by size and SHA-256, and kept",
              ok and ocr.model_ok(os.path.join(target, "eng.traineddata"), "eng") and not os.path.exists(
                  os.path.join(target, "eng.traineddata.part")), said)
        check("the fetch says what it fetches", any("Fetching the English reading model (4.1 MB)" in s for s in said), said)
        n = len(said)
        check("a model already there is not fetched again", ocr.fetch_model("eng", target, said.append) and len(said) == n)
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def finish(tmp, started):
    shutil.rmtree(tmp, ignore_errors=True)
    print("\n%d passed, %d failed  (%.0f s)" % (len(PASS), len(FAIL), time.time() - started))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
