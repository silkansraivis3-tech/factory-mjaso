# -*- coding: utf-8 -*-
"""Which files a knowledge base is made from, and the stable names each one gets.

The slug, document id and duplicate rules are ported from the Course Source Processor (csp/discovery.py,
csp/pipeline.py), so a source keeps the same folder name and id whichever builder made the knowledge base.
"""
from __future__ import annotations

import hashlib
import os
import re
import unicodedata

# the same file types kb_tool.CSP_FORMATS counts as sources
FORMATS = {".pdf": "pdf", ".docx": "docx", ".pptx": "pptx", ".doc": "doc", ".ppt": "ppt",
           ".jpg": "image", ".jpeg": "image", ".png": "image", ".webp": "image"}
SKIP_DIRS = {".git", ".svn", ".hg", "__pycache__", "__macosx", ".idea", ".vscode", "node_modules", "$recycle.bin",
             "system volume information", ".venv", "venv", "working_claude", "_factory", "to_review"}
SKIP_NAMES = {"thumbs.db", ".ds_store", "desktop.ini"}
QUIET = {".txt", ".md", ".json", ".csv", ".xml", ".log", ".ini", ".cfg", ".bat", ".exe", ".dll", ".zip", ".rar", ".7z",
         ".tmp", ".lnk", ".url", ".db", ".gz"}


def sha256_of(path):
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def skipped_dir(name):
    low = name.lower()
    return low in SKIP_DIRS or low.startswith(".") or low.startswith("knowledge_base")


def discover(root):
    """([{path, rel, name, ext, fmt, size}], [unsupported rel paths]) in case-insensitive path order. Never walks into a
    knowledge base (any folder named KNOWLEDGE_BASE*), the factory's own folders or a dot-folder."""
    found, other = [], []
    for dirpath, dirnames, files in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if not skipped_dir(d))
        for name in files:
            if name.startswith("~$") or name.startswith(".") or name.lower() in SKIP_NAMES:
                continue
            path = os.path.join(dirpath, name)
            rel = os.path.relpath(path, root).replace(os.sep, "/")
            ext = os.path.splitext(name)[1].lower()
            if ext in FORMATS:
                try:
                    size = os.path.getsize(path)
                except OSError:
                    other.append(rel)
                    continue
                found.append({"path": path, "rel": rel, "name": name, "ext": ext, "fmt": FORMATS[ext], "size": size})
            elif ext not in QUIET:
                other.append(rel)
    found.sort(key=lambda f: f["path"].lower())
    other.sort(key=str.lower)
    return found, other


def canonical_copies(found):
    """{sha256: canonical rel path} for content held by two or more files: the shallowest path wins, ties by name."""
    by_hash = {}
    for f in found:
        by_hash.setdefault(f["sha256"], []).append(f["rel"])
    return {h: min(paths, key=lambda rel: (rel.count("/"), rel)) for h, paths in by_hash.items() if len(paths) > 1}


def doc_id_for(sha):
    return "d" + sha[:10]


def unique_doc_id(sha, taken):
    base = doc_id_for(sha)
    if base not in taken:
        taken.add(base)
        return base
    n = 2
    while "%s_%d" % (base, n) in taken:
        n += 1
    taken.add("%s_%d" % (base, n))
    return "%s_%d" % (base, n)


def slugify(name, max_length=48):
    stem = os.path.splitext(name)[0]
    text = unicodedata.normalize("NFKD", stem).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"_{2,}", "_", re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_"))
    return (text or "source")[:max_length].strip("_") or "source"


def unique_slug(base, taken, sha):
    candidate = "%s__%s" % (base, sha[:6])
    if candidate not in taken:
        taken.add(candidate)
        return candidate
    n = 2
    while "%s_%d" % (candidate, n) in taken:
        n += 1
    taken.add("%s_%d" % (candidate, n))
    return "%s_%d" % (candidate, n)
