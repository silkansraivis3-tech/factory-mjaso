#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Stage 3 - the module content script, word for word, and the operator's corrections to it (L29).

    content_script.py render   <course> --module 1           review page + Word file for the operator
    content_script.py read     <course> --module 1 [--docx F] [--pdf F]   what the operator changed -> PENDING
    content_script.py propose  <course> --module 1 --changes changes.json  a chat correction -> PENDING
    content_script.py apply    <course> --module 1 --confirmed           apply PENDING - only after the operator said yes
    content_script.py approve  <course> --module 1 --by "<name>"         the operator's "next"
    content_script.py status   <course> --module 1

WHY THIS EXISTS
Until 2.16.0 the operator saw the real words of a module for the first time in finished HTML, and
every correction landed on built pages. Now the words are approved first. The script is a file -
_factory/script/M01.json - holding every screen in the order the trainee meets it: each slide's exact
visible text, its planned picture and the instructor notes, and every self-check and module-check
question - ONE TASK PER SCREEN, as on the tablet - with its answers, the correct one and the feedback.
The final-assessment bank is the same, as --module final.

THE OPERATOR'S COPY IS A WORD FILE (owner, 2026-09-30)
render writes review/M01_SCRIPT.docx beside a review page that prints to PDF. Every editable text is
its own Word box (a content control, tagged with the screen and field, locked against deletion but
not against typing). The operator may type in the boxes, or add Word comments; read takes both.
Tracked changes are read as they would stand if accepted; the list says which were tracked, and by
whom. What it cannot read reliably, it says plainly: a box deleted outright, text typed outside the
boxes, a comment it cannot place on a screen.

NOTHING IS APPLIED UNTIL THE OPERATOR SAYS YES (owner, 2026-09-30)
read and propose never change the script. They write _factory/script/M01.pending.json and print the
plain list of what was understood - "screen 7: X becomes Y; question 3: the correct answer becomes B".
The factory shows that list to the operator, in their language. Only apply --confirmed changes the
script, logs each change in FEEDBACK_LOG.md, and re-renders both files. Any change after approval
puts the module back to draft; approve records who approved which version.

Standard library only - it runs on any colleague's computer. PDF comments need the pypdf package;
without it, read says so and asks for the comments in Word or in the chat instead.
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import html
import io
import json
import os
import re
import shutil
import sys
import zipfile
from datetime import date, datetime
from xml.etree import ElementTree as ET

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
SKILLS = os.path.dirname(SKILL)
LABELS = json.load(io.open(os.path.join(SKILL, "knowledge", "page-labels.json"), encoding="utf-8"))
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
Q = lambda t: "{%s}%s" % (W, t)

KINDS = ("slide", "self-check", "module-check", "final", "activity")
TASKS = ("self-check", "module-check", "final")
SLIDE_FIELDS = ("title", "text", "visual", "notes", "minutes")
TASK_FIELDS = ("question", "options", "correct", "feedback", "mechanic")


# ------------------------------------------------------------------ files
def mid(module):
    return "FINAL" if str(module).lower() == "final" else "M%02d" % int(module)


def paths(course, module):
    m = mid(module)
    d = os.path.join(course, "_factory", "script")
    r = os.path.join(course, "review")
    return {"script": os.path.join(d, m + ".json"), "pending": os.path.join(d, m + ".pending.json"),
            "old": os.path.join(d, "old"), "review": os.path.join(r, m + "_SCRIPT_REVIEW.html"),
            "docx": os.path.join(r, m + "_SCRIPT.docx"), "dir": d, "rdir": r}


def load(p):
    with io.open(p, encoding="utf-8") as f:
        return json.load(f)


def save(p, obj):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with io.open(p, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.write("\n")


def content_hash(script):
    return hashlib.sha256(json.dumps(script.get("screens", []), ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()[:16]


def T(script, key, **kw):
    lang = script.get("operator_language", "en")
    s = LABELS.get(lang, {}).get(key) or LABELS["en"].get(key) or key
    return s.format(**kw) if kw else s


def course_lang(script):
    return LABELS["course_language_codes"].get(script.get("course_language", ""), "en")


# ------------------------------------------------------------------ fields
def letters(n):
    return [chr(ord("A") + i) for i in range(n)]


def fields_of(screen):
    """Every editable field of one screen as (field id, value) - options become opt.A, opt.B ..."""
    out = []
    if screen["kind"] in TASKS:
        out.append(("question", screen.get("question", "")))
        for L, o in zip(letters(len(screen.get("options", []))), screen.get("options", [])):
            out.append(("opt." + L, o))
        out += [("correct", screen.get("correct", "")), ("feedback", screen.get("feedback", "")),
                ("mechanic", screen.get("mechanic", "tap to choose"))]
    else:
        out += [(f, str(screen.get(f, "")) if screen.get(f, "") is not None else "") for f in SLIDE_FIELDS]
    return out


def get_field(screen, f):
    if f.startswith("opt."):
        i = ord(f[4]) - ord("A")
        opts = screen.get("options", [])
        return opts[i] if 0 <= i < len(opts) else None
    v = screen.get(f, "")
    return "" if v is None else str(v)


def set_field(screen, f, value):
    if f.startswith("opt."):
        i = ord(f[4]) - ord("A")
        opts = screen.setdefault("options", [])
        while len(opts) <= i:
            opts.append("")
        opts[i] = value
    elif f == "minutes":
        try:
            screen[f] = float(value) if "." in value else int(value)
        except ValueError:
            screen[f] = value
    else:
        screen[f] = value


def validate(script):
    probs, seen = [], set()
    screens = script.get("screens", [])
    for i, s in enumerate(screens):
        sid = s.get("id")
        if not sid or sid in seen:
            probs.append("screen %d has no id, or an id used twice (%s)" % (i + 1, sid))
        seen.add(sid)
        if s.get("kind") not in KINDS:
            probs.append("screen %s: unknown kind %r" % (sid, s.get("kind")))
        if s.get("kind") in TASKS:
            opts = s.get("options", [])
            if len(opts) < 2:
                probs.append("screen %s: a task needs at least two answers to choose from" % sid)
            if s.get("correct") not in letters(len(opts)):
                probs.append("screen %s: the correct answer %r is not one of %s" % (sid, s.get("correct"), "/".join(letters(len(opts)))))
            if not s.get("feedback"):
                probs.append("screen %s: no feedback for the trainee after answering" % sid)
            if s.get("kind") == "module-check" and s.get("graded"):
                probs.append("screen %s: a module check is not graded (L27)" % sid)
    kinds = [s.get("kind") for s in screens]
    if "module-check" in kinds:
        first = kinds.index("module-check")
        if any(k == "slide" for k in kinds[first:]):
            probs.append("a slide comes after the module check starts - the module check is the end of the module")
    return probs


# ------------------------------------------------------------------ operator-stated facts
def operator_facts(course, script):
    facts = [dict(f) for f in script.get("operator_facts", [])]
    fb = os.path.join(course, "FEEDBACK_LOG.md")
    if os.path.isfile(fb):
        for line in io.open(fb, encoding="utf-8").read().splitlines():
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) >= 6 and cells[0].isdigit() and cells[5].lower().startswith("yes"):
                if str(script.get("module")) in cells[2] or mid(script.get("module")) in cells[2] or "M%s" % script.get("module") in cells[2]:
                    facts.append({"fact": cells[3], "where": cells[2], "said": cells[1]})
    return facts


# ------------------------------------------------------------------ the review page
def render_html(course, script):
    e = lambda s: html.escape(str(s if s is not None else ""))
    cl = course_lang(script)
    V = lambda s: '<span class="verb" lang="%s">%s</span>' % (cl, e(s).replace("\n", "<br>")) if s else "—"
    css = "".join(io.open(os.path.join(SKILLS, "course-module-ui", "templates", n), encoding="utf-8").read() + "\n"
                  for n in ("gb_tokens.css", "gb_page.css"))
    css += """
.verb{font-family:var(--font)} .screen{page-break-inside:avoid;break-inside:avoid}
.sid{font-family:var(--mono);color:var(--faint-l);font-size:13px}
.kind{display:inline-block;padding:.15em .6em;border-radius:var(--r-s);font-size:13px;font-weight:700;background:var(--grey)}
.k-slide{background:var(--blue-wash-l);color:var(--navy)} .k-self-check,.k-module-check{background:var(--good-wash-l);color:var(--good)}
.k-final{background:var(--amber-wash-l);color:var(--amber-ink)}
.tablet{border:1px solid var(--line-l);border-radius:var(--r-l);padding:16px;max-width:520px;background:var(--white)}
.opt{display:flex;gap:10px;align-items:center;min-height:52px;border:1.5px solid var(--line-l);border-radius:var(--r-m);padding:10px 14px;margin:8px 0}
.opt.right{border-color:var(--good);background:var(--good-wash-l)} .opt b{min-width:1.6em}
dl{display:grid;grid-template-columns:12em 1fr;gap:6px 14px;margin:0} dt{color:var(--dim-l);font-weight:700} dd{margin:0}
.instr{border-left:4px solid var(--amber);background:var(--amber-wash-l);padding:8px 12px;border-radius:0 var(--r-s) var(--r-s) 0}
h1,h2{color:var(--navy)} @media print{body{background:#fff}.card{box-shadow:none}}
"""
    status = (T(script, "s_status_approved", by=script.get("approved_by", ""), on=script.get("approved_on", ""))
              if script.get("status") == "approved" and script.get("approved_hash") == content_hash(script)
              else T(script, "s_status_draft"))
    title = T(script, "s_page_title", m=script.get("module"))
    o = ['<!DOCTYPE html><html lang="%s"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
         '<title>%s</title><style>%s</style></head><body><div class="wrap">' % (e(script.get("operator_language", "en")), e(title), css),
         "<h1>%s</h1><p class=\"sub\">%s · <b>%s</b></p><p class=\"lead\">%s</p>" % (e(title), V(script.get("title", "")), e(status), e(T(script, "s_intro")))]
    facts = operator_facts(course, script)
    if facts:
        o.append('<div class="card hot"><h3>%s</h3><p class="note">%s</p><ul>%s</ul></div>' % (
            e(T(script, "s_facts_title")), e(T(script, "s_facts_intro")),
            "".join("<li>%s <span class=\"sid\">(%s%s)</span></li>" % (V(f.get("fact")), e(f.get("where", "")),
                    (", " + e(f["said"])) if f.get("said") else "") for f in facts)))
    o.append('<p class="note">%s</p>' % e(T(script, "s_one_per_screen")))
    kind_label = {"slide": "s_slide", "self-check": "s_self_check", "module-check": "s_module_check", "final": "s_final", "activity": "s_activity"}
    for n, s in enumerate(script.get("screens", []), 1):
        k = s.get("kind")
        o.append('<div class="card screen"><h2>%s %d <span class="kind k-%s">%s</span> <span class="sid">%s</span></h2>' % (
            e(T(script, "s_screen")), n, e(k), e(T(script, kind_label.get(k, "s_slide"))), e(s.get("id"))))
        if k in TASKS:
            opts = "".join('<div class="opt%s"><b>%s</b> %s</div>' % (" right" if L == s.get("correct") else "", L, V(x))
                           for L, x in zip(letters(len(s.get("options", []))), s.get("options", [])))
            o.append('<div class="tablet"><p><b>%s</b></p>%s</div>' % (V(s.get("question")), opts))
            o.append('<dl><dt>%s</dt><dd>%s</dd><dt>%s</dt><dd>%s</dd><dt>%s</dt><dd>%s</dd></dl>' % (
                e(T(script, "s_correct")), e(s.get("correct", "")), e(T(script, "s_feedback")), V(s.get("feedback")),
                e(T(script, "s_mechanic")), e(s.get("mechanic", "tap to choose"))))
        else:
            o.append('<dl><dt>%s</dt><dd>%s</dd><dt>%s</dt><dd>%s</dd><dt>%s</dt><dd>%s</dd><dt>%s</dt><dd>%s</dd></dl>' % (
                e(T(script, "s_title")), V(s.get("title")), e(T(script, "s_text")), V(s.get("text")),
                e(T(script, "s_visual")), V(s.get("visual")), e(T(script, "s_minutes")), e(s.get("minutes", "—"))))
            if s.get("notes"):
                o.append('<p class="instr"><b>%s:</b> %s</p>' % (e(T(script, "s_notes")), V(s.get("notes"))))
        o.append("</div>")
    o.append('<p class="foot">%s %s %s</p></div></body></html>' % (e(T(script, "s_prepared")), date.today().isoformat(), e(T(script, "s_by_factory"))))
    return "\n".join(o)


# ------------------------------------------------------------------ the Word file
def _run(text, lang=None, bold=False, color=None):
    rpr = ""
    if bold or lang or color:
        rpr = "<w:rPr>%s%s%s</w:rPr>" % ("<w:b/>" if bold else "", '<w:color w:val="%s"/>' % color if color else "",
                                         '<w:lang w:val="%s"/>' % lang if lang else "")
    return '<w:r>%s<w:t xml:space="preserve">%s</w:t></w:r>' % (rpr, html.escape(text, quote=False))


def _para(text, style=None, lang=None, bold=False, shade=None, color=None):
    ppr = ""
    if style or shade:
        ppr = "<w:pPr>%s%s</w:pPr>" % ('<w:pStyle w:val="%s"/>' % style if style else "",
                                       '<w:shd w:val="clear" w:color="auto" w:fill="%s"/>' % shade if shade else "")
    return "<w:p>%s%s</w:p>" % (ppr, _run(text, lang, bold, color) if text else "")


def _box(tag, alias, text, lang):
    paras = "".join(_para(line, lang=lang, shade="EEF2F6") for line in (str(text).split("\n") if text != "" else [""]))
    return ('<w:sdt><w:sdtPr><w:alias w:val="%s"/><w:tag w:val="%s"/><w:lock w:val="sdtLocked"/></w:sdtPr>'
            '<w:sdtContent>%s</w:sdtContent></w:sdt>' % (html.escape(alias), html.escape(tag), paras))


def docx_labels(course, script):
    """The fixed text of the Word file - headings and field names. Rebuilt from the script, never
    trusted from the file, because Word may drop parts of a package it does not know when it saves."""
    return build_docx(course, script)[1]


def render_docx(course, script, out):
    doc, _ = build_docx(course, script)
    write_docx_package(doc, out)


def build_docx(course, script):
    cl = course_lang(script)
    body, labels = [], []

    def label(text, style=None, bold=False, color=None):
        labels.append(text)
        body.append(_para(text, style=style, bold=bold, color=color))

    label(T(script, "s_page_title", m=script.get("module")), style="Title")
    labels.append(script.get("title", ""))
    body.append(_para(script.get("title", ""), lang=cl, bold=True))
    label(T(script, "s_docx_help"), color="41556A")
    facts = operator_facts(course, script)
    if facts:
        label(T(script, "s_facts_title"), style="Heading1")
        for f in facts:
            body.append(_para("• " + f.get("fact", ""), lang=cl))
    kind_label = {"slide": "s_slide", "self-check": "s_self_check", "module-check": "s_module_check", "final": "s_final", "activity": "s_activity"}
    names = {"title": "s_title", "text": "s_text", "visual": "s_visual", "notes": "s_notes", "minutes": "s_minutes",
             "question": "s_question", "correct": "s_correct", "feedback": "s_feedback", "mechanic": "s_mechanic"}
    for n, s in enumerate(script.get("screens", []), 1):
        head = "%s %d · %s · %s" % (T(script, "s_screen"), n, T(script, kind_label.get(s["kind"], "s_slide")), s["id"])
        label(head, style="Heading1")
        for f, v in fields_of(s):
            nm = T(script, "s_options") + " " + f[4] if f.startswith("opt.") else T(script, names[f])
            label(nm, bold=True, color="0A2463")
            body.append(_box("%s.%s" % (s["id"], f), "%s · %s" % (s["id"], nm), v, cl))
    doc = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document xmlns:w="%s"><w:body>%s'
           '<w:sectPr><w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="1134" w:right="1134" w:bottom="1134" w:left="1134" w:header="708" w:footer="708" w:gutter="0"/></w:sectPr>'
           '</w:body></w:document>' % (W, "".join(body)))
    return doc, labels


def write_docx_package(doc, out):
    styles = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:styles xmlns:w="%s">'
              '<w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="Calibri" w:hAnsi="Calibri" w:cs="Calibri"/><w:sz w:val="22"/></w:rPr></w:rPrDefault></w:docDefaults>'
              '<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/><w:pPr><w:spacing w:after="80"/></w:pPr></w:style>'
              '<w:style w:type="paragraph" w:styleId="Title"><w:name w:val="Title"/><w:basedOn w:val="Normal"/><w:rPr><w:b/><w:color w:val="0A2463"/><w:sz w:val="36"/></w:rPr></w:style>'
              '<w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:basedOn w:val="Normal"/><w:pPr><w:keepNext/><w:spacing w:before="360" w:after="120"/><w:outlineLvl w:val="0"/></w:pPr><w:rPr><w:b/><w:color w:val="0A2463"/><w:sz w:val="28"/></w:rPr></w:style>'
              '</w:styles>' % W)
    ct = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/>'
          '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
          '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/></Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
    drels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
             '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", ct)
        z.writestr("_rels/.rels", rels)
        z.writestr("word/document.xml", doc)
        z.writestr("word/styles.xml", styles)
        z.writestr("word/_rels/document.xml.rels", drels)


def _text(el):
    """Text of an element as it stands with every tracked change accepted."""
    parts = []

    def walk(x, deleted=False):
        tag = x.tag
        if tag in (Q("del"), Q("moveFrom")):
            deleted = True
        if not deleted:
            if tag == Q("t"):
                parts.append(x.text or "")
            elif tag == Q("tab"):
                parts.append("\t")
            elif tag in (Q("br"), Q("cr")):
                parts.append("\n")
        for c in x:
            walk(c, deleted)
    walk(el)
    return "".join(parts)


def read_docx(path, known_labels=()):
    """Fields, comments, tracked changes, text outside the boxes - from the operator's Word file."""
    with zipfile.ZipFile(path) as z:
        doc = ET.fromstring(z.read("word/document.xml"))
        comments = {}
        if "word/comments.xml" in z.namelist():
            for c in ET.fromstring(z.read("word/comments.xml")).iter(Q("comment")):
                comments[c.get(Q("id"))] = {"author": c.get(Q("author"), ""),
                                            "text": "\n".join(_text(p) for p in c.iter(Q("p"))).strip()}
    fields, tracked, placed, outside = {}, [], {}, []
    labels = set(l.strip() for l in known_labels)
    state = {"last": None}
    pending_comments = []

    def walk(x, in_tag=None):
        if x.tag == Q("sdt"):
            tag_el = x.find("%s/%s" % (Q("sdtPr"), Q("tag")))
            tag = tag_el.get(Q("val")) if tag_el is not None else None
            content = x.find(Q("sdtContent"))
            if tag and content is not None:
                paras = [p for p in content.iter(Q("p"))] or [content]
                fields[tag] = "\n".join(_text(p) for p in paras)
                for kind in ("ins", "del", "moveTo", "moveFrom"):
                    for ch in content.iter(Q(kind)):
                        tracked.append({"field": tag, "type": {"ins": "inserted", "del": "deleted", "moveTo": "moved", "moveFrom": "moved"}[kind],
                                        "author": ch.get(Q("author"), "")})
                for cid in pending_comments:
                    placed[cid] = tag
                pending_comments.clear()
                state["last"] = tag
                for c in content.iter(Q("commentRangeStart")):
                    placed[c.get(Q("id"))] = tag
                return
        if x.tag == Q("commentRangeStart"):
            pending_comments.append(x.get(Q("id")))
        if x.tag == Q("p") and in_tag is None:
            t = _text(x).strip()
            if t and t not in labels and not t.startswith("• "):
                outside.append({"after": state["last"], "text": t})
        for c in x:
            walk(c, in_tag)
    walk(doc.find(Q("body")))
    for cid in pending_comments:            # a comment after the last box belongs to it
        placed[cid] = state["last"]
    out_comments = [{"field": placed.get(cid), **c} for cid, c in comments.items()]
    return {"fields": fields, "comments": out_comments, "tracked": tracked, "outside": outside}


def read_pdf(path):
    try:
        import pypdf  # noqa: F401
    except ImportError:
        return None
    import pypdf
    found = []
    r = pypdf.PdfReader(path)
    for n, page in enumerate(r.pages, 1):
        ids = sorted(set(re.findall(r"\b([smqf]\d{2,3})\b", page.extract_text() or "")))
        for a in (page.get("/Annots") or []):
            a = a.get_object()
            txt = a.get("/Contents")
            if txt:
                found.append({"page": n, "text": str(txt), "author": str(a.get("/T", "")), "screens_on_page": ids})
    return found


# ------------------------------------------------------------------ pending changes
def screen_no(script, sid):
    for n, s in enumerate(script.get("screens", []), 1):
        if s["id"] == sid:
            return n, s
    return None, None


def short(s, n=90):
    s = (s or "").replace("\n", " / ")
    return s if len(s) <= n else s[:n - 1] + "…"


def changed_words(old, new):
    """Only the words that changed: "rely on the hull for strength" -> "are thin barriers supported by the hull"."""
    a, b = (old or "").split(), (new or "").split()
    parts = []
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b).get_opcodes():
        if op == "replace":
            parts.append("\"%s\" becomes \"%s\"" % (" ".join(a[i1:i2]), " ".join(b[j1:j2])))
        elif op == "delete":
            parts.append("\"%s\" is removed" % " ".join(a[i1:i2]))
        elif op == "insert":
            parts.append("\"%s\" is added%s" % (" ".join(b[j1:j2]), (" after \"%s\"" % " ".join(a[max(0, i1 - 3):i1])) if i1 else " at the start"))
    return "; ".join(parts) or "only line breaks or spacing change"


def describe(script, ch):
    n, s = screen_no(script, ch["screen"])
    where = "screen %s (%s, %s)" % (n, ch["screen"], s["kind"] if s else "?")
    f = ch["field"]
    if f == "correct":
        return "%s: the correct answer becomes %s (was %s)" % (where, ch["new"], ch["old"])
    if f.startswith("opt."):
        return "%s: answer %s becomes \"%s\" (was \"%s\")" % (where, f[4], short(ch["new"]), short(ch["old"]))
    name = {"title": "the title", "text": "the slide text", "visual": "the planned picture", "notes": "the instructor notes",
            "minutes": "the minutes", "question": "the question", "feedback": "the feedback", "mechanic": "how the trainee answers"}.get(f, f)
    if len(ch["old"] or "") > 60 or len(ch["new"] or "") > 60:
        return "%s, %s: %s" % (where, name, changed_words(ch["old"], ch["new"]))
    return "%s: %s becomes \"%s\" (was \"%s\")" % (where, name, ch["new"], ch["old"])


def write_pending(p, script, changes, notes, source):
    if not changes and not notes:
        if os.path.isfile(p["pending"]):
            os.remove(p["pending"])
        print("What I understood: nothing - the file says exactly what the script says. Nothing is waiting.")
        return 0
    pend = {"_what": "Understood, NOT applied. Show the list to the operator; apply only after they confirm.",
            "source": source, "made": datetime.now().isoformat(timespec="seconds"), "base_hash": content_hash(script),
            "changes": changes, "notes": notes}
    save(p["pending"], pend)
    print("What I understood - nothing has been changed yet:\n")
    if not changes and not notes:
        print("  nothing: the file says exactly what the script says.")
    for ch in changes:
        print("  - " + describe(script, ch))
    for nt in notes:
        print("  - " + nt)
    print("\nShow this list to the operator. Only when they confirm:  content_script.py apply <course> --module %s --confirmed"
          % script.get("module"))
    return 0


def cmd_read(course, module, docx, pdf):
    p = paths(course, module)
    script = load(p["script"])
    changes, notes = [], []
    if docx or os.path.isfile(p["docx"]):
        got = read_docx(docx or p["docx"], docx_labels(course, script))
        expected = {}
        for s in script["screens"]:
            for f, v in fields_of(s):
                expected["%s.%s" % (s["id"], f)] = str(v)
        for tag, old in expected.items():
            if tag not in got["fields"]:
                notes.append("the box for %s was deleted in Word - I cannot tell what was meant; ask the operator" % tag)
                continue
            new = got["fields"][tag]
            if new.strip() != old.strip():
                sid, f = tag.split(".", 1)
                changes.append({"screen": sid, "field": f, "old": old, "new": new.strip()})
        by_field = {}
        for t in got["tracked"]:
            by_field.setdefault(t["field"], set()).add("%s by %s" % (t["type"], t["author"] or "someone"))
        for f, how in sorted(by_field.items()):
            notes.append("tracked changes in %s (%s) - read as if accepted" % (f, ", ".join(sorted(how))))
        for c in got["comments"]:
            where = c["field"] or "a place I could not match to a screen"
            notes.append("comment on %s from %s: \"%s\" - I will say what I would change for it, and do it only when you confirm"
                         % (where, c["author"] or "the operator", short(c["text"], 200)))
        for x in got["outside"]:
            notes.append("text typed outside the boxes (after %s): \"%s\" - I will not guess where it belongs; tell me" % (x["after"] or "the start", short(x["text"], 160)))
        made = script.get("docx_hash")
        if made and made != content_hash(script):
            notes.append("this Word file was made from an older version of the script - the list compares it with the current one")
    if pdf:
        found = read_pdf(pdf)
        if found is None:
            notes.append("PDF comments cannot be read on this computer (the pypdf package is missing) - please give them in the Word file or in the chat")
        else:
            for a in found:
                notes.append("PDF comment on page %d (screens on that page: %s) from %s: \"%s\"" % (
                    a["page"], ", ".join(a["screens_on_page"]) or "not found", a["author"] or "the operator", short(a["text"], 200)))
    return write_pending(p, script, changes, notes, "word" if (docx or os.path.isfile(p["docx"])) else "pdf")


def cmd_propose(course, module, changes_file):
    p = paths(course, module)
    script = load(p["script"])
    changes = []
    for c in load(changes_file):
        sid, f = c["field"].split(".", 1) if "." in c["field"] and not c["field"].startswith("opt.") else (c.get("screen"), c["field"])
        n, s = screen_no(script, sid)
        if s is None:
            print("Stopped - there is no screen %r in this module's script." % sid)
            return 2
        changes.append({"screen": sid, "field": f, "old": get_field(s, f) or "", "new": c["new"]})
    return write_pending(p, script, changes, [], "chat")


def append_feedback(course, script, changes, source):
    fb = os.path.join(course, "FEEDBACK_LOG.md")
    if not os.path.isfile(fb):
        return
    text = io.open(fb, encoding="utf-8").read()
    nums = [int(c.split("|")[1]) for c in text.splitlines() if re.match(r"^\|\s*\d+\s*\|", c)]
    n = max(nums or [0])
    rows = []
    for ch in changes:
        n += 1
        rows.append("| %d | %s | 3 · %s · %s | %s (%s) | %s | no |" % (
            n, date.today().isoformat(), mid(script["module"]), ch["screen"], short(ch["new"], 120).replace("|", "/"), source,
            describe(script, ch).replace("|", "/")))
    with io.open(fb, "a", encoding="utf-8", newline="\n") as f:
        f.write(("\n" if not text.endswith("\n") else "") + "\n".join(rows) + "\n")


def cmd_apply(course, module, confirmed):
    p = paths(course, module)
    if not confirmed:
        print("Stopped - apply needs --confirmed, and that is only given after the operator has read the list and said yes.")
        return 2
    if not os.path.isfile(p["pending"]):
        print("Nothing to apply - there is no list of understood changes waiting.")
        return 2
    script, pend = load(p["script"]), load(p["pending"])
    if pend["base_hash"] != content_hash(script):
        print("Stopped - the script changed after the list was made. Read the corrections again, and show the new list.")
        return 1
    for ch in pend["changes"]:
        n, s = screen_no(script, ch["screen"])
        set_field(s, ch["field"], ch["new"])
    was_approved = script.get("status") == "approved"
    if pend["changes"]:
        script["status"] = "draft"
    save(p["script"], script)
    append_feedback(course, script, pend["changes"], {"word": "Word file", "pdf": "PDF", "chat": "chat"}.get(pend["source"], pend["source"]))
    os.makedirs(p["old"], exist_ok=True)
    if os.path.isfile(p["docx"]):
        shutil.move(p["docx"], os.path.join(p["old"], "%s_SCRIPT_%s.docx" % (mid(module), datetime.now().strftime("%Y%m%d_%H%M%S"))))
    os.rename(p["pending"], os.path.join(p["old"], "%s.applied_%s.json" % (mid(module), datetime.now().strftime("%Y%m%d_%H%M%S"))))
    render(course, module, quiet=True)
    print("Applied %d change(s), logged in FEEDBACK_LOG.md, and made a fresh review page and Word file.%s%s"
          % (len(pend["changes"]), " The module is back to draft: it needs the operator's \"next\" again." if was_approved and pend["changes"] else "",
             ("\n  %d comment(s) and note(s) were NOT applied - they are instructions, not edits. Propose the change for "
              "each (content_script.py propose), show it, and apply it when the operator confirms." % len(pend["notes"])) if pend["notes"] else ""))
    return 0


def cmd_discard(course, module):
    p = paths(course, module)
    if not os.path.isfile(p["pending"]):
        print("Nothing is waiting - there is nothing to discard.")
        return 0
    os.makedirs(p["old"], exist_ok=True)
    os.rename(p["pending"], os.path.join(p["old"], "%s.discarded_%s.json" % (mid(module), datetime.now().strftime("%Y%m%d_%H%M%S"))))
    print("Discarded - the list of understood changes was not applied. The script is unchanged.")
    return 0


def cmd_approve(course, module, by):
    p = paths(course, module)
    script = load(p["script"])
    if os.path.isfile(p["pending"]):
        print("Not approved - there are understood changes waiting. Apply them (after the operator confirms) or discard them first.")
        return 1
    probs = validate(script)
    if probs:
        print("Not approved - the script still has problems:\n" + "\n".join("  - " + x for x in probs))
        return 1
    script.update({"status": "approved", "approved_by": by, "approved_on": date.today().isoformat(), "approved_hash": content_hash(script)})
    save(p["script"], script)
    render(course, module, quiet=True)
    print("Module %s's script is approved by %s. The slides built from it must say exactly this (check_script_match.py)." % (script["module"], by))
    return 0


def cmd_status(course, module):
    p = paths(course, module)
    script = load(p["script"])
    ok = script.get("status") == "approved" and script.get("approved_hash") == content_hash(script)
    print("Module %s: %s%s" % (script.get("module"), "approved by %s on %s" % (script.get("approved_by"), script.get("approved_on")) if ok else "draft - not approved",
                               "; understood changes are waiting for confirmation" if os.path.isfile(p["pending"]) else ""))
    return 0 if ok else 1


def render(course, module, quiet=False):
    p = paths(course, module)
    script = load(p["script"])
    probs = validate(script)
    os.makedirs(p["rdir"], exist_ok=True)
    io.open(p["review"], "w", encoding="utf-8", newline="\n").write(render_html(course, script))
    render_docx(course, script, p["docx"])
    script["docx_hash"] = content_hash(script)
    save(p["script"], script)
    if not quiet:
        print("Ready for the operator:\n    %s   (opens in the browser, prints to PDF)\n    %s   (Word - correct it here)"
              % (p["review"], p["docx"]))
        if probs:
            print("\nThe script still has problems - fix them before showing it:\n" + "\n".join("  - " + x for x in probs))
    return 1 if probs else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("render", "read", "propose", "apply", "discard", "approve", "status"):
        s = sub.add_parser(name)
        s.add_argument("course")
        s.add_argument("--module", required=True)
        if name == "read":
            s.add_argument("--docx"); s.add_argument("--pdf")
        if name == "propose":
            s.add_argument("--changes", required=True)
        if name == "apply":
            s.add_argument("--confirmed", action="store_true")
        if name == "approve":
            s.add_argument("--by", required=True)
    a = ap.parse_args(argv)
    if not os.path.isfile(paths(a.course, a.module)["script"]):
        print("Stopped - there is no content script for module %s yet:\n    %s" % (a.module, paths(a.course, a.module)["script"]))
        return 2
    return {"render": lambda: render(a.course, a.module), "read": lambda: cmd_read(a.course, a.module, a.docx, a.pdf),
            "propose": lambda: cmd_propose(a.course, a.module, a.changes), "apply": lambda: cmd_apply(a.course, a.module, a.confirmed),
            "discard": lambda: cmd_discard(a.course, a.module),
            "approve": lambda: cmd_approve(a.course, a.module, a.by), "status": lambda: cmd_status(a.course, a.module)}[a.cmd]()


if __name__ == "__main__":
    sys.exit(main())
