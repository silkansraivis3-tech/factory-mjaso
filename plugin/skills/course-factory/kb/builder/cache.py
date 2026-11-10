# -*- coding: utf-8 -*-
"""What was read before, kept by file content - a second run reads only what changed.

    %LOCALAPPDATA%\\NOVIKONTAS\\kb_cache\\<sha256>_<settings>.json.gz   one file's reading
    %LOCALAPPDATA%\\NOVIKONTAS\\kb_cache\\images\\<ab>\\<sha256>.<ext>      every picture, once, by its own content

The key is the file's SHA-256, the builder's reading version and the settings that change what is read (tables,
pictures). The OCR language is NOT in the key: a file's scanned pages are kept with the reading models they were read
with, and only those pages are read again when the models change. NOVIKONTAS_KB_CACHE names another folder.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import os

EXTRACT_VERSION = 1


def cache_root():
    named = os.environ.get("NOVIKONTAS_KB_CACHE")
    if named:
        return os.path.abspath(named)
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or os.path.join(os.path.expanduser("~"), "AppData", "Local")
        return os.path.join(base, "NOVIKONTAS", "kb_cache")
    return os.path.join(os.path.expanduser("~"), ".novikontas", "kb_cache")


def image_store():
    return os.path.join(cache_root(), "images")


def image_path(sha, ext):
    return os.path.join(image_store(), sha[:2], "%s.%s" % (sha, ext))


def settings_key(settings):
    raw = json.dumps({"v": EXTRACT_VERSION, "s": settings}, sort_keys=True)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:8]


def _path(sha, key):
    return os.path.join(cache_root(), "%s_%s.json.gz" % (sha, key))


def load(sha, key):
    """The cached reading, or None - also None when a picture it names is no longer in the store."""
    try:
        with gzip.open(_path(sha, key), "rt", encoding="utf-8") as f:
            got = json.load(f)
    except (OSError, ValueError, EOFError):
        return None
    for im in got.get("images", []):
        if not os.path.isfile(image_path(im["sha256"], im["ext"])):
            return None
    return got


def save(sha, key, payload):
    os.makedirs(cache_root(), exist_ok=True)
    path = _path(sha, key)
    tmp = path + ".%d.part" % os.getpid()
    with gzip.open(tmp, "wt", encoding="utf-8", compresslevel=5) as f:
        json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
    os.replace(tmp, path)
