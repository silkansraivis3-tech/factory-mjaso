# -*- coding: utf-8 -*-
"""test_minify_engines - a module ships a kit's minified copy only while it was made from the kit as it is (2.70.0).

    python test_minify_engines.py
"""
from __future__ import annotations

import io
import os
import shutil
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import design_system  # noqa: E402
import minify_engines as me  # noqa: E402

PASS, FAIL = [], []


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print(("  ok    " if ok else "  FAIL  ") + name + (("  -> " + str(detail)[:400]) if detail and not ok else ""))


def main():
    tmp = tempfile.mkdtemp(prefix="minify_")
    try:
        src = os.path.join(tmp, "kit.js")
        io.open(src, "w", encoding="utf-8", newline="\n").write("/* words for the people who keep it */\nvar KIT = {a: 1};\n")
        check("no minified copy: the module gets the source", design_system.shipped_src(src) == src)
        m = me.min_path(src)
        os.makedirs(os.path.dirname(m))
        io.open(m, "w", encoding="utf-8").write(me.HEAD % ("kit.js", me.sha(src)) + "var KIT={a:1};\n")
        check("a copy made from the source as it is: the module gets the copy", design_system.shipped_src(src) == m)
        body = io.open(src, "rb").read()
        io.open(src, "wb").write(body.replace(b"\n", b"\r\n"))
        check("... the same source checked out with CRLF line ends is still the same source", design_system.shipped_src(src) == m)
        io.open(src, "a", encoding="utf-8").write("KIT.b = 2;\n")
        check("the source changed since: the module gets the source, never the old copy", design_system.shipped_src(src) == src)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    stale = [os.path.relpath(s, me.SKILLS) for s in me.ENGINES if not me.fresh(s)]
    check("the factory's minified kit.js and kit3d.js are current (else: python course-module-ui\\scripts\\minify_engines.py)",
          not stale, stale)
    spec = design_system.load_list()
    ships = {i["name"]: i["src"] for i in spec["files"]}
    check("design_system ships the minified copies", ships["kit.js"].replace("\\", "/").endswith("kit/min/kit.js")
          and ships["kit3d.js"].replace("\\", "/").endswith("kit3d/min/kit3d.js"), ships)
    print("\n%d passed, %d failed" % (len(PASS), len(FAIL)))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
