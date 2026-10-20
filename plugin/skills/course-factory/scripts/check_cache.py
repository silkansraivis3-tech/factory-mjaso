# -*- coding: utf-8 -*-
"""check_cache - a slide or task page judged clean is not judged again until something it shows has changed (2.57.0).

WHY (2026-10-20): every rebuild re-ran the drawing check and the three deck audits on every slide and every task page,
when a review-driven build changes one to three of them. figure_fit.py already kept its clean figures
(figures/MNN/_fit/_clean.json); the drawing check (drawing_check.py) and the audits (run_audits.py) now do the same, per
slide and per task page.

THE FINGERPRINT of a slide (a deck's <section class="slide">) or a task page is a hash of everything it loads and
everything that judges it:
  - its own HTML (the slide's section, or the whole task page), its place in the deck (slide 4 of 17)
  - the rest of the page around it - head, chrome, scripts (the deck without its slides)
  - every file of the module's assets\\ folder except the pictures (gb_*.css, kit.js, kit_parts.js, fonts ...)
  - every file the slide, the page or those files name (its photos, a 3D scene and what that scene names ...)
  - the checker: its probe scripts, its own code, the window size and the browser (path, size, date)
A cached result is only ever a CLEAN one: a slide with a finding, a page that did not finish, a run that aborted is never
written, and is judged again next time. PASS still means every slide and page was judged clean at what it is now.
build_module.py --full judges everything (and records what is clean).
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import re
from urllib.parse import unquote

SLIDE_TAG = re.compile(r"<(?:section|div)\b[^>]*\bclass=\"(?:[^\"]*\s)?slide(?:\s[^\"]*)?\"", re.I)
EXT = ("png|jpe?g|webp|gif|svg|avif|bmp|ico|json|html?|m?js|css|mp4|webm|ogg|mp3|wav|m4a|glb|gltf|bin|hdr|ktx2|"
       "woff2?|ttf|otf|txt|csv")
NAME = re.compile(r"[^\s\"'`()<>=,;:*?|\\/\[\]{}]+\.(?:%s)(?![\w.])" % EXT, re.I)
TEXT = (".html", ".htm", ".js", ".mjs", ".css", ".json", ".svg", ".txt", ".csv")
PAGE_DIRS = ("tasks", "assessment", "instructor")
MAX_FILES = 5000                     # a folder this big is not a module: nothing is cached


def sha(*parts):
    h = hashlib.sha256()
    for p in parts:
        h.update(p if isinstance(p, bytes) else str(p).encode("utf-8", "replace"))
        h.update(b"\0")
    return h.hexdigest()


def read(path):
    try:
        with io.open(path, "rb") as f:
            return f.read()
    except OSError:
        return b"-missing-"


def salt(*files, extra=""):
    """the checker's own part of every fingerprint: its scripts' contents and its settings"""
    return sha(*([os.path.basename(f) + ":" + sha(read(f)) for f in files] + [extra]))


def browser_id(exe):
    """the browser as a fingerprint: a Chrome or Edge update can draw differently"""
    try:
        st = os.stat(exe)
        return "%s|%d|%d" % (os.path.normcase(os.path.abspath(exe)), st.st_size, int(st.st_mtime))
    except (OSError, TypeError):
        return str(exe)


def slide_spans(text):
    """[(start, end)] of every slide of a deck page: from its tag to the next slide's, the last one to </main> (or </body>)"""
    starts = [m.start() for m in SLIDE_TAG.finditer(text)]
    spans = []
    for k, s in enumerate(starts):
        if k + 1 < len(starts):
            e = starts[k + 1]
        else:
            low = text.lower()
            e = next((i for i in (low.find("</main>", s), low.find("</body>", s)) if i >= 0), len(text))
        spans.append((s, e))
    return spans


class Module(object):
    """the module folder a page sits in (the page's folder's parent): its files by name, and its shared part"""

    def __init__(self, page):
        self.dir = os.path.dirname(os.path.dirname(os.path.abspath(page)))
        self.by_name, self.ok = {}, True
        n = 0
        for root, dirs, files in os.walk(self.dir):
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            for f in files:
                n += 1
                if n > MAX_FILES:
                    self.ok = False
                    return
                self.by_name.setdefault(f.lower(), []).append(os.path.join(root, f))
        self._file, self._shared = {}, None

    def is_page(self, path):
        """a page of the module - never part of another page's fingerprint (a link to it does not load it)"""
        rel = os.path.relpath(path, self.dir).replace("\\", "/").lower()
        top = rel.split("/")[0]
        return ("/" not in rel and rel.endswith((".html", ".htm"))) or rel == "presentation/index.html" or top in PAGE_DIRS

    def file_hash(self, path, seen):
        """a file's contents and, for a text file, every file it names in turn"""
        if path in seen:
            return ""
        seen.add(path)
        if path not in self._file:
            data = read(path)
            self._file[path] = (sha(data), self.names(data.decode("utf-8", "replace")) if path.lower().endswith(TEXT) else [])
        own, names = self._file[path]
        return sha(own, *[self.file_hash(p, seen) for p in names])

    def names(self, text):
        """the module files a piece of text names (by file name, wherever in the module it is)"""
        out = set()
        for tok in NAME.findall(text):
            for p in self.by_name.get(unquote(tok).lower(), []):
                if not self.is_page(p):
                    out.add(p)
        return sorted(out)

    def refs(self, text):
        seen = set()
        return sha(*[os.path.relpath(p, self.dir) + ":" + self.file_hash(p, seen) for p in self.names(text)])

    def shared(self):
        """every file of assets\\ but the pictures (and what those files name)"""
        if self._shared is None:
            assets, seen, parts = os.path.join(self.dir, "assets"), set(), []
            for root, dirs, files in os.walk(assets):
                rel = os.path.relpath(root, assets).replace("\\", "/").lower()
                if rel == "img" or rel.startswith("img/"):
                    dirs[:] = []
                    continue
                dirs.sort()
                for f in sorted(files):
                    p = os.path.join(root, f)
                    parts.append(os.path.relpath(p, self.dir) + ":" + self.file_hash(p, seen))
            self._shared = sha(*parts)
        return self._shared


def fingerprints(page, deck, check_salt):
    """[(unit name, fingerprint)] - one per slide of a deck (in order), else one for the page; None when the page cannot
    be fingerprinted (it is then always judged whole)"""
    try:
        text = io.open(page, encoding="utf-8", errors="replace").read()
    except OSError:
        return None
    mod = Module(page)
    if not mod.ok:
        return None
    base = sha(check_salt, mod.shared())
    if not deck:
        return [("page", sha(base, text, mod.refs(text)))]
    spans = slide_spans(text)
    if not spans:
        return None
    shell = text[:spans[0][0]] + "".join("<!--slide-->" + text[spans[k][1]:spans[k + 1][0] if k + 1 < len(spans) else len(text)]
                                         for k in range(len(spans)))
    base = sha(base, shell, mod.refs(shell))
    out = []
    for k, (s, e) in enumerate(spans):
        unit = text[s:e]
        m = re.search(r'\bid="([^"]+)"', unit[:unit.find(">") + 1])
        out.append(("slide %d%s" % (k + 1, " (%s)" % m.group(1) if m else ""),
                    sha(base, "%d/%d" % (k + 1, len(spans)), unit, mod.refs(unit))))
    return out


class Cache(object):
    """{unit key: fingerprint} of the units last judged clean. use=False (--full): nothing is skipped, clean results
    are still recorded. path=None: no cache at all"""

    def __init__(self, path, use=True):
        self.path, self.use, self.data, self.dirty = path, use, {}, False
        if path:
            try:
                self.data = json.load(io.open(path, encoding="utf-8"))
            except (OSError, ValueError):
                self.data = {}
            if not isinstance(self.data, dict):
                self.data = {}

    def clean(self, key, fp):
        return bool(self.path and self.use and fp and self.data.get(key) == fp)

    def ok(self, key, fp):
        if self.path and fp and self.data.get(key) != fp:
            self.data[key] = fp
            self.dirty = True

    def bad(self, key):
        if self.data.pop(key, None) is not None:
            self.dirty = True

    def save(self):
        if not (self.path and self.dirty):
            return
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            tmp = "%s.%d.tmp" % (self.path, os.getpid())
            io.open(tmp, "w", encoding="utf-8").write(json.dumps(self.data, indent=0, sort_keys=True))
            os.replace(tmp, self.path)
        except OSError:
            pass
