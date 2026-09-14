# -*- coding: utf-8 -*-
"""preview.py - build the course's REVIEW surface and open it in the normal browser.

WHY THIS EXISTS. Most course developers have no tablet, no Android Studio and no reason to
learn either. Until now the only way to see a course the way it will be delivered was to
publish it, which put an unreviewed course into the production repository to look at it.
That is backwards: PREVIEW comes first, and it happens entirely outside the Android project.

WHAT IT MAKES. One file, `REVIEW.html`, beside the course. It lists every surface the course
actually has - found by looking, not by assuming a layout - and links each one. It carries no
course CSS of its own: a review surface that depends on the thing under review tells you
nothing on the day that thing is broken.

file:// IS ENOUGH, and that was measured rather than assumed. On the real default browser,
on a real file:// origin, with the real course:

    external CSS LOADED · external JS LOADED · localStorage OK · sessionStorage OK
    SVG LOADED · deck engine LOADED · 6/6 figures built · 44 slides · 0 console errors
    fetch() of a local file BLOCKED

Only fetch is blocked, and Course Factory output uses no fetch, no XMLHttpRequest and no ES
modules - `gates.py --only browser` keeps it that way. So the colleague double-clicks a file.
No server, no port, no terminal, no localhost to understand.

    python preview.py --course <course folder>            build REVIEW.html
    python preview.py --course <course folder> --open      build it and open the browser

REVIEW.html is INTERNAL. It is matched by `internal_globs` in knowledge/platform.json and can
never reach a tablet.
"""
from __future__ import annotations

import argparse
import datetime
import html
import io
import json
import os
import re
import sys
import webbrowser

HERE = os.path.dirname(os.path.abspath(__file__))

REVIEW_FILE = "REVIEW.html"

# What a surface is called, in the order a reviewer should walk them. The matcher is a
# predicate over the course-relative path, because courses do not all use the same folders
# and a reviewer does not care what a folder is named.
GROUPS = [
    ("The presentation", "what the instructor drives in front of the room",
     lambda p: re.match(r"^module[^/]*\.html$", p) or re.match(r"^modules?/[^/]+\.html$", p)),
    ("Start here", "the page that opens the class",
     lambda p: p in ("START_HERE.html", "index.html")),
    ("Trainee tasks", "what the tablets carry - open one and answer it",
     lambda p: p.startswith("tasks/") and p.endswith(".html")),
    ("Handout", "what the trainee takes away",
     lambda p: p.startswith("handout/") and p.endswith(".html")),
    ("Practicals", "the practical cards",
     lambda p: p.startswith("practicals/") and p.endswith(".html")),
    ("Assessment", "the check and the record",
     lambda p: p.startswith("assessment/") and p.endswith(".html")),
    ("Instructor", "the plan and the run sheet - instructor-only, never on a trainee tablet",
     lambda p: (p.startswith("plan/") or p.startswith("instructor/") or
                p.startswith("run/")) and p.endswith(".html")),
]

SKIP_DIRS = {"_work", "__pycache__", ".git", "node_modules", "_backup", "oldversion"}


def walk(root: str):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
        for fn in filenames:
            yield os.path.join(dirpath, fn)


def relpath(root: str, path: str) -> str:
    return os.path.relpath(path, root).replace(os.sep, "/")


def is_fragment(path: str) -> bool:
    """A figure fragment is markup pasted INTO a page, not a page.

    Opening one on its own shows unstyled markup and teaches a reviewer nothing, so it does
    not belong on the review grid. Same test the rest of the factory uses (check_navigation
    reports them as "fragment(s) skipped"): no doctype, no <html>, no <body>.
    """
    try:
        head = io.open(path, encoding="utf-8", errors="replace").read(2000).lower()
    except OSError:
        return False
    return not ("<!doctype" in head or "<html" in head or "<body" in head)


def title_of(path: str, fallback: str) -> str:
    try:
        txt = io.open(path, encoding="utf-8", errors="replace").read(4000)
    except OSError:
        return fallback
    m = re.search(r"<title[^>]*>(.*?)</title>", txt, re.S | re.I)
    if not m:
        return fallback
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", m.group(1))).strip() or fallback


def course_meta(root: str) -> dict:
    """course.json if the course has one; otherwise what can be seen."""
    meta = {}
    cj = os.path.join(root, "course.json")
    if os.path.isfile(cj):
        try:
            meta = json.load(io.open(cj, encoding="utf-8"))
        except ValueError:
            meta = {}
    meta.setdefault("id", os.path.basename(os.path.abspath(root)))
    meta.setdefault("title", meta["id"])
    meta.setdefault("version", "—")
    meta.setdefault("status", "draft")
    return meta


# --------------------------------------------------------------------------- the page
CSS = """
:root{--ink:#011111;--dim:#40566a;--faint:#71839a;--line:#d4dce6;--bg:#f4f7fa;
  --card:#fff;--navy:#0A2463;--blue:#2EB6F8;--good:#0a7d55;--good-bg:#e9f5ef;
  --warn:#8a4b0b;--warn-bg:#fdf6ea;--mono:ui-monospace,Consolas,monospace}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
  font:15px/1.55 "Segoe UI",Roboto,Arial,Helvetica,sans-serif}
.wrap{max-width:1120px;margin:0 auto;padding:22px 18px 70px}
h1{font-size:26px;margin:6px 0 2px;letter-spacing:-.01em}
.sub{color:var(--dim);margin:0 0 14px}
.meta{display:flex;gap:8px;flex-wrap:wrap;margin:0 0 22px}
.meta span{background:#e7eff6;border:1px solid var(--line);border-radius:999px;
  padding:5px 13px;font-size:13.5px;color:var(--dim)}
.meta span b{color:var(--navy)}
h2{font-size:18px;margin:28px 0 4px;padding-top:14px;border-top:2px solid var(--line)}
h2 small{display:block;font-weight:400;font-size:14px;color:var(--faint);margin-top:3px}
.grid{display:grid;gap:10px;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));
  margin:12px 0 4px}
a.item{display:block;background:var(--card);border:1px solid var(--line);
  border-left:5px solid var(--blue);border-radius:10px;padding:11px 14px;
  text-decoration:none;color:inherit}
a.item:hover{border-color:var(--blue);box-shadow:0 2px 8px rgba(1,17,17,.09)}
a.item b{display:block;font-size:15.5px;margin-bottom:2px}
a.item span{font-family:var(--mono);font-size:12.5px;color:var(--faint);word-break:break-all}
a.item.instructor{border-left-color:var(--warn)}
.panel{background:var(--card);border:1px solid var(--line);border-radius:12px;
  padding:14px 17px;margin:16px 0}
.panel.ok{background:var(--good-bg);border-color:#a8ceb8}
.panel.warn{background:var(--warn-bg);border-color:#e0bd82}
.panel h3{margin:0 0 7px;font-size:16px}
.panel p{margin:0 0 7px}
.panel p:last-child{margin:0}
ul.check{margin:8px 0 0;padding-left:20px}
ul.check li{margin:0 0 5px}
code{font-family:var(--mono);font-size:.92em;background:#eef3f8;padding:1px 5px;
  border-radius:4px}
.foot{color:var(--faint);font-size:13px;margin:34px 0 0;padding-top:13px;
  border-top:1px solid var(--line)}
.big{display:inline-block;margin:2px 0 8px;padding:13px 24px;background:var(--navy);
  color:#fff;border-radius:10px;text-decoration:none;font-weight:700;font-size:16.5px}
.big:hover{background:#0d2f7d}
"""

CHECKLIST = [
    "Press <b>Start</b> and drive the whole deck with <b>Next</b>, to the end. "
    "Every screen should look composed - nothing crammed, nothing marooned in empty space.",
    "Touch every interactive figure. A slider should move something; a toggle should change "
    "something; an animation should run. A drawing that does nothing is a drawing that could "
    "have been a photograph.",
    "Open each trainee task, answer one question right and one wrong, and check the feedback "
    "actually looks different.",
    "Follow every <b>Back</b> link. You should never reach a page with no way out.",
    "Read the handout and the practical cards as a trainee would.",
    "Check the language: everything a trainee or instructor sees must be in the course's "
    "language, with no stray English (or Latvian) left in a heading.",
]


def build(root: str, meta: dict, groups: list, safety: dict, lang_note: str) -> str:
    esc = html.escape
    out = [
        "<!DOCTYPE html>", '<html lang="en">', "<head>", '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        "<title>Review — %s</title>" % esc(str(meta.get("title", ""))),
        "<style>%s</style>" % CSS, "</head>", "<body>", '<div class="wrap">',
        "<h1>%s</h1>" % esc(str(meta.get("title", ""))),
        '<p class="sub">Review this course in your normal browser. '
        "Nothing here touches the Android app.</p>",
        '<div class="meta">',
        "<span>course id <b>%s</b></span>" % esc(str(meta.get("id", ""))),
        "<span>version <b>%s</b></span>" % esc(str(meta.get("version", ""))),
        "<span>status <b>%s</b></span>" % esc(str(meta.get("status", ""))),
    ]
    if lang_note:
        out.append("<span>language <b>%s</b></span>" % esc(lang_note))
    out.append("<span>built <b>%s</b></span>"
               % datetime.datetime.now().strftime("%Y-%m-%d %H:%M"))
    out.append("</div>")

    # the one obvious way in
    # START_HERE is the door a class actually comes through; the deck is what it opens.
    opener = None
    for want in ("Start here", "The presentation"):
        for name, _desc, items in groups:
            if name == want and items:
                opener = items[0]
                break
        if opener:
            break
    if opener:
        out.append('<a class="big" href="%s">▶ Open the course</a>' % esc(opener[0]))

    # what to look at
    out.append('<div class="panel"><h3>What to check before you approve</h3><ul class="check">')
    for line in CHECKLIST:
        out.append("<li>%s</li>" % line)
    out.append("</ul></div>")

    # every surface
    for name, desc, items in groups:
        if not items:
            continue
        out.append("<h2>%s <small>%s</small></h2>" % (esc(name), esc(desc)))
        out.append('<div class="grid">')
        cls = " instructor" if name == "Instructor" else ""
        for href, label in items:
            out.append('<a class="item%s" href="%s"><b>%s</b><span>%s</span></a>'
                       % (cls, esc(href), esc(label), esc(href)))
        out.append("</div>")

    # the browser-safety verdict
    ok = not safety["findings"]
    out.append('<div class="panel %s"><h3>Opening this from a file, without a server</h3>'
               % ("ok" if ok else "warn"))
    if ok:
        out.append("<p>Every page here uses only what a browser allows a local file to use. "
                   "Double-clicking works; no server, no port, no terminal.</p>")
        out.append("<p>Measured, not assumed: external CSS, external JS, SVG, "
                   "<code>localStorage</code> and <code>sessionStorage</code> all work from "
                   "<code>file://</code> in the default browser. Only <code>fetch()</code> of "
                   "a local file is blocked, and nothing here uses it.</p>")
    else:
        out.append("<p><b>Some pages will not work correctly when opened as a file.</b> "
                   "A browser refuses these to a local file:</p><ul class='check'>")
        for f in safety["findings"][:12]:
            out.append("<li><code>%s</code> — %s</li>" % (esc(f["file"]), esc(f["why"])))
        out.append("</ul><p>Fix these, or review over a local server instead.</p>")
    out.append("</div>")

    out.append('<div class="panel"><h3>When you are satisfied</h3>'
               "<p>Say so in your own words, naming this course — for example:</p>"
               "<p><code>Approved. Publish this course to the NOVIKONTAS training app.</code></p>"
               "<p>Nothing reaches the Android application until you do. Asking for the course "
               "to be improved, fixed or redesigned never publishes it.</p></div>")

    out.append('<p class="foot">This page is a review surface generated by the NOVIKONTAS '
               "Course Factory. It is never published to a tablet. Regenerate it after "
               "changing the course.</p>")
    out.append("</div></body></html>")
    return "\n".join(out)


# ------------------------------------------------------------------- browser safety
BROWSER_RULES = [
    (re.compile(r"\bfetch\s*\(", re.I),
     "uses fetch(), which a browser blocks for a local file"),
    (re.compile(r"\bnew\s+XMLHttpRequest\b"),
     "uses XMLHttpRequest, which a browser blocks for a local file"),
    (re.compile(r'<script[^>]+type\s*=\s*["\']module["\']', re.I),
     "loads an ES module, which a browser blocks for a local file"),
    (re.compile(r'\bimport\s+[\w{*][^;\n]*\bfrom\s+["\']'),
     "uses an ES module import, which a browser blocks for a local file"),
]


def scan_safety(root: str) -> dict:
    findings = []
    for f in walk(root):
        ext = os.path.splitext(f)[1].lower()
        if ext not in (".html", ".htm", ".js"):
            continue
        rp = relpath(root, f)
        if rp == REVIEW_FILE:
            continue
        txt = io.open(f, encoding="utf-8", errors="replace").read()
        # a comment that merely mentions fetch is not a call; strip block comments first
        txt = re.sub(r"/\*.*?\*/", " ", txt, flags=re.S)
        txt = re.sub(r"(?m)^\s*//.*$", " ", txt)
        for rx, why in BROWSER_RULES:
            if rx.search(txt):
                findings.append({"file": rp, "why": why})
                break
    return {"findings": findings}


def detect_language(root: str) -> str:
    """Best effort, for the header chip only. course.json wins if it says."""
    cj = os.path.join(root, "course.json")
    if os.path.isfile(cj):
        try:
            v = json.load(io.open(cj, encoding="utf-8")).get("language")
            if v:
                return str(v)
        except ValueError:
            pass
    return ""


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--course", required=True, help="the course folder to review")
    ap.add_argument("--open", action="store_true",
                    help="open the review page in the default browser")
    ap.add_argument("--out", help="where to write it (default: REVIEW.html in the course)")
    args = ap.parse_args(argv)

    root = os.path.abspath(args.course)
    if not os.path.isdir(root):
        sys.stderr.write("not a folder: %s\n" % root)
        return 2

    pages = []
    frag_count = 0
    for f in walk(root):
        if os.path.splitext(f)[1].lower() not in (".html", ".htm"):
            continue
        rp = relpath(root, f)
        if rp == REVIEW_FILE:
            continue
        if is_fragment(f):
            frag_count += 1
            continue
        pages.append((rp, f))
    if not pages:
        sys.stderr.write("no .html pages under %s — is this a course folder?\n" % root)
        return 2

    claimed = set()
    groups = []
    for name, desc, match in GROUPS:
        items = []
        for rp, full in sorted(pages):
            if rp in claimed or not match(rp):
                continue
            claimed.add(rp)
            items.append((rp, title_of(full, rp)))
        groups.append((name, desc, items))

    rest = [(rp, title_of(full, rp)) for rp, full in sorted(pages) if rp not in claimed]
    if rest:
        groups.append(("Everything else", "other pages found in this course", rest))

    meta = course_meta(root)
    safety = scan_safety(root)
    page = build(root, meta, groups, safety, detect_language(root))

    dest = os.path.abspath(args.out) if args.out else os.path.join(root, REVIEW_FILE)
    io.open(dest, "w", encoding="utf-8", newline="\n").write(page)

    total = sum(len(i) for _n, _d, i in groups)
    print("REVIEW surface written: %s" % dest)
    if frag_count:
        print("  %d figure fragment(s) set aside - they are pasted into a page, not pages"
              % frag_count)
    print("  %d page(s) across %d group(s)"
          % (total, len([1 for _n, _d, i in groups if i])))
    for n, _d, i in groups:
        if i:
            print("    %-20s %d" % (n, len(i)))
    if safety["findings"]:
        print("\n  %d file(s) will NOT work when opened as a file:" % len(safety["findings"]))
        for f in safety["findings"][:8]:
            print("    %-44s %s" % (f["file"], f["why"]))
        print("  Review over a local server, or remove the dependency.")
    else:
        print("\n  file:// safe — double-clicking REVIEW.html is enough. "
              "No server, no port, no terminal.")

    if args.open:
        webbrowser.open("file:///" + dest.replace(os.sep, "/"))
        print("\n  opened in the default browser")
    return 0


if __name__ == "__main__":
    sys.exit(main())
