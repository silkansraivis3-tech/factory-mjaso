# -*- coding: utf-8 -*-
"""minify_engines.py - the small copies of the two big engines a module ships: kit.js and kit3d.js (2.70.0).

    python minify_engines.py            make (or refresh) min/kit.js and min/kit3d.js beside their sources
    python minify_engines.py --check    exit 1 when a copy is missing or older than its source

WHY (owner, 2026-10-27: "optimize ... so it does better work in smaller usage and less time"): every module carries its
own copy of the figure kit (388 KB) and the 3D kit (162 KB) - most of it comments for the people who keep the factory. The
copy a module ships is the same code minified by esbuild: kit.js 227 KB, kit3d.js 91 KB (about 5 MB less on a 20-module
course's tablets, and less for a slow tablet to read when a deck opens). Globals and property names are kept, so the page,
the audits and the studios see the same KIT / KIT3D.

THE SOURCE IS THE ONE TO EDIT. Each copy's first line names the source's sha256; design_system.py ships the copy only while
that matches (design_system.shipped_src), else the source itself - a copy left behind by an edit is never shipped. esbuild is
only needed here, by whoever changes a kit: NOVIKONTAS_ESBUILD, else the copy the Vercel command line brings
(%APPDATA%\\npm\\node_modules\\vercel\\node_modules\\esbuild), else `esbuild` on the PATH.
"""
from __future__ import annotations

import hashlib
import io
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILLS = os.path.dirname(os.path.dirname(HERE))
ENGINES = [os.path.join(SKILLS, "course-visuals", "kit", "kit.js"), os.path.join(SKILLS, "course-visuals", "kit3d", "kit3d.js")]
HEAD = "/*! %s sha256:%s - the minified copy a module ships (course-module-ui/scripts/minify_engines.py); edit the source */\n"


def sha(path):
    """the source's sha256 with its line ends as LF - a checkout that writes CRLF (git on Windows) is the same source"""
    return hashlib.sha256(io.open(path, "rb").read().replace(b"\r\n", b"\n")).hexdigest()


def min_path(src):
    return os.path.join(os.path.dirname(src), "min", os.path.basename(src))


def fresh(src):
    """the minified copy of src when it was made from src as it is now - else None"""
    m = min_path(src)
    try:
        with io.open(m, encoding="utf-8") as f:
            first = f.readline()
    except OSError:
        return None
    return m if ("sha256:%s " % sha(src)) in first else None


def esbuild():
    cands = [os.environ.get("NOVIKONTAS_ESBUILD"),
             os.path.join(os.environ.get("APPDATA", ""), "npm", "node_modules", "vercel", "node_modules", "esbuild")]
    for c in cands:
        if c and os.path.isdir(c) and os.path.isfile(os.path.join(c, "package.json")):
            return c
    return None


def make(src):
    mod = esbuild()
    if not mod:
        raise SystemExit("esbuild is not on this computer - set NOVIKONTAS_ESBUILD to its package folder (the copies are "
                         "made only by whoever changes a kit; the modules ship the source meanwhile)")
    js = ("const es=require(%r);const fs=require('fs');const r=es.transformSync(fs.readFileSync(%r,'utf8'),"
          "{minify:true,target:'es2015',legalComments:'none'});process.stdout.write(r.code);" % (mod.replace("\\", "/"), src.replace("\\", "/")))
    p = subprocess.run(["node", "-e", js], capture_output=True, text=True, encoding="utf-8")
    if p.returncode or not p.stdout.strip():
        raise SystemExit("esbuild failed on %s:\n%s" % (src, p.stderr[-800:]))
    m = min_path(src)
    os.makedirs(os.path.dirname(m), exist_ok=True)
    with io.open(m, "w", encoding="utf-8", newline="\n") as f:
        f.write(HEAD % (os.path.basename(src), sha(src)) + p.stdout.strip() + "\n")
    return m


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if "--check" in argv:
        stale = [os.path.relpath(s, SKILLS) for s in ENGINES if not fresh(s)]
        for s in stale:
            print("%s: its minified copy is missing or older than it - run course-module-ui\\scripts\\minify_engines.py "
                  "(meanwhile the modules ship the full source)" % s)
        print("every minified copy is current" if not stale else "")
        return 1 if stale else 0
    for s in ENGINES:
        m = make(s)
        print("%s  %d KB -> %d KB" % (os.path.relpath(m, SKILLS), os.path.getsize(s) // 1024, os.path.getsize(m) // 1024))
    return 0


if __name__ == "__main__":
    sys.exit(main())
