#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Is every module folder complete, and does it stand on its own? - L43.

    check_module_folder.py <course folder | modules folder | one module folder>

WHY THIS EXISTS
The owner, 2026-10-01: "it puts all modules in one folder, each module has its own folder, and all assets and
scripts needed for that module to start are inside each module folder; there is a START HERE HTML that opens the
presentation straight away, and an extended start with fast access - buttons for all tasks, the module plan,
the presentation and so on." So the build delivers:

    course\\modules\\
        M01_Gas_tankers\\
            START_HERE.html            opens the presentation straight away
            START_HERE_EXTENDED.html   buttons: presentation · every task · module plan · instructor notes · ...
            presentation\\             the module's one-page presentation
            tasks\\                    every task of the module
            instructor\\               the module plan, the instructor notes (.md), the practical cards
            assets\\                   every picture, 3D model, video, style and script the module uses
        M02_...\\
        M23_Final_assessment\\

A module folder can be copied anywhere - onto a stick, to a colleague (L39), into the tablet system - and opened
with a double-click: nothing in it reaches outside it, and nothing is fetched from the internet (L6).

WHAT IT CHECKS, per module folder
  1  START_HERE.html and START_HERE_EXTENDED.html are there
  2  START_HERE.html goes straight to the presentation (a redirect, or the presentation itself)
  3  START_HERE_EXTENDED.html has a button for the presentation, for every task page in tasks\\, and for the
     module plan and the instructor notes when they exist
  4  every local file a page uses (src, href, url(), a script, a style, a picture, a model) is inside the module
     folder and exists - nothing reaches up and out with ../ beyond the module, nothing is missing
  5  nothing is fetched from the internet: no http:// or https:// source, style, script or font
Exit 0 when every module passes, 1 when anything fails, 2 on bad input. Read only.
"""
from __future__ import annotations

import argparse
import io
import os
import re
import sys
from html.parser import HTMLParser
from urllib.parse import unquote, urlparse

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import workspace  # noqa: E402

MODULE_DIR = re.compile(r"^M\d{2}[_ -]")
REF_ATTRS = {"src", "href", "data-src", "poster", "data", "data-model", "data-video"}
CSS_URL = re.compile(r"url\(\s*['\"]?([^'\")]+)['\"]?\s*\)")
REDIRECT = re.compile(r"""(?:http-equiv\s*=\s*["']refresh["'][^>]*url\s*=\s*([^"'>]+))|(?:location\.(?:replace|href)\s*\(?\s*=?\s*["']([^"']+))""", re.I)


class Refs(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.refs, self.links, self.in_style, self.css = [], [], False, []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        for k, v in a.items():
            if k in REF_ATTRS and v:
                self.refs.append((tag, k, v))
                if tag == "a" and k == "href":
                    self.links.append(v)
        if a.get("style"):
            self.css.append(a["style"])
        if tag == "style":
            self.in_style = True

    def handle_endtag(self, tag):
        if tag == "style":
            self.in_style = False

    def handle_data(self, data):
        if self.in_style:
            self.css.append(data)


def modules_in(folder):
    folder = os.path.abspath(folder)
    if MODULE_DIR.match(os.path.basename(folder)):
        return [folder]
    w = workspace.work_folder(folder, create=False)
    for cand in (os.path.join(w, "modules"), folder):
        if os.path.isdir(cand):
            ms = sorted(os.path.join(cand, d) for d in os.listdir(cand)
                        if os.path.isdir(os.path.join(cand, d)) and MODULE_DIR.match(d))
            if ms:
                return ms
    return []


def local(ref):
    u = urlparse(ref)
    if u.scheme in ("http", "https"):
        return None, "internet"
    if u.scheme in ("data", "mailto", "tel", "javascript", "blob") or ref.startswith("#") or not ref.strip():
        return None, None
    if u.scheme:                              # file: or anything else
        return None, "scheme"
    return unquote(u.path), None


def check_module(mdir):
    probs = []
    pages = [os.path.join(dp, f) for dp, _, fs in os.walk(mdir) for f in fs if f.lower().endswith((".html", ".htm"))]
    start, ext = os.path.join(mdir, "START_HERE.html"), os.path.join(mdir, "START_HERE_EXTENDED.html")
    for p, what in ((start, "START_HERE.html - the page that opens the presentation straight away"),
                    (ext, "START_HERE_EXTENDED.html - the page with a button for everything in the module")):
        if not os.path.isfile(p):
            probs.append("%s is missing" % what)
    pres = sorted(os.path.relpath(p, mdir).replace("\\", "/") for p in pages
                  if os.path.relpath(p, mdir).replace("\\", "/").startswith("presentation/"))
    if not pres:
        probs.append("there is no presentation in presentation\\")
    tasks = sorted(os.path.relpath(p, mdir).replace("\\", "/") for p in pages
                   if os.path.relpath(p, mdir).replace("\\", "/").startswith("tasks/"))
    for p in pages:
        txt = io.open(p, encoding="utf-8", errors="replace").read()
        r = Refs()
        try:
            r.feed(txt)
        except Exception:  # noqa: BLE001 - a page that does not parse is reported, not fatal
            probs.append("%s could not be read as a web page" % os.path.relpath(p, mdir))
            continue
        refs = [v for _, _, v in r.refs] + [m for css in r.css for m in CSS_URL.findall(css)]
        base = os.path.dirname(p)
        for ref in refs:
            path, kind = local(ref)
            where = os.path.relpath(p, mdir)
            if kind == "internet":
                probs.append("%s fetches from the internet: %s - the tablet is offline; put the file in assets\\" % (where, ref))
                continue
            if kind == "scheme":
                probs.append("%s points at %s - use a path inside the module folder" % (where, ref))
                continue
            if path is None:
                continue
            target = os.path.normpath(os.path.join(base, path))
            if os.path.commonpath([os.path.abspath(target), os.path.abspath(mdir)]) != os.path.abspath(mdir):
                probs.append("%s reaches outside the module folder: %s - copy what it needs into the module" % (where, ref))
            elif not os.path.exists(target):
                probs.append("%s uses %s, which is not there" % (where, ref))
        if os.path.abspath(p) == os.path.abspath(start):
            goes = [g for m in REDIRECT.findall(txt) for g in m if g] + r.links
            if not any(local(g)[0] and local(g)[0].lstrip("./").startswith("presentation/") for g in goes) \
                    and "presentation" not in os.path.relpath(p, mdir):
                probs.append("START_HERE.html does not open the presentation straight away")
        if os.path.abspath(p) == os.path.abspath(ext):
            linked = {os.path.normpath(os.path.join(base, local(x)[0])) for x in r.links if local(x)[0]}
            for t in pres[:1] + tasks:
                if os.path.normpath(os.path.join(mdir, t)) not in linked:
                    probs.append("START_HERE_EXTENDED.html has no button for %s" % t)
            for f in ("instructor",):
                d = os.path.join(mdir, f)
                if os.path.isdir(d):
                    for g in sorted(os.listdir(d)):
                        if re.search(r"(PLAN|INSTRUCTOR_NOTES)", g, re.I) and os.path.normpath(os.path.join(d, g)) not in linked:
                            probs.append("START_HERE_EXTENDED.html has no button for instructor/%s" % g)
    return probs, len(tasks)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("folder")
    a = ap.parse_args(argv)
    if not os.path.isdir(a.folder):
        print("Stopped - that folder is not there:\n    %s" % a.folder)
        return 2
    mods = modules_in(a.folder)
    if not mods:
        print("No module folders were found (named like M01_Gas_tankers) in\n    %s" % a.folder)
        return 2
    bad = 0
    for m in mods:
        probs, nt = check_module(m)
        name = os.path.basename(m)
        if probs:
            bad += 1
            print("%s - %d thing(s) to fix:" % (name, len(probs)))
            for x in probs:
                print("    - " + x)
        else:
            print("%s - complete, opens on its own, nothing fetched (%d task page(s))" % (name, nt))
    print("\n%d of %d module folder(s) ready." % (len(mods) - bad, len(mods)))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
