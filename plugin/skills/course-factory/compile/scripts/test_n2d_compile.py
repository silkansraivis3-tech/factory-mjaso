#!/usr/bin/env python3
"""test_n2d_compile.py - the compiler and the 2D kit for new courses (course-visuals/n2d): a .n2d.json figure goes into
the page as it is, with the module's system ("world") joined in; a spec the check refuses, or a starter not yet written
("_todo"), fails the build with the reason; --init-build lets code choose each drawing slide's figure and writes the
starter, or says why the slide gets a photo, the task screen or no figure.

    python -I test_n2d_compile.py
"""
from __future__ import annotations

import io
import json
import os
import sys
import tempfile

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import compile_module as cm  # noqa: E402

FAILS = []


def check(what, ok, detail=""):
    print("  %s  %s%s" % ("ok  " if ok else "FAIL", what, "" if ok else "  -> %s" % str(detail)[:500]))
    if not ok:
        FAILS.append(what)


SLIDE = {"id": "s14", "kind": "slide", "title": "Engine data: from sensor to shore", "visual_kind": "flow_animation",
         "text": "Sensors send readings to controllers.\nThe alarm system gathers them.\nRemote monitoring sends them ashore."}
SPEC = {"form": "path", "world": "engine", "say": "A reading travels from the sensor to the office ashore.",
        "steps": [{"line": 1, "go": "s>a"}, {"line": 3, "go": "a>o", "tag": {"o": "Maker or company"}}]}
WORLDS = {"engine": {"things": [{"id": "s", "is": "sensor", "name": "Sensor"}, {"id": "a", "is": "screen", "name": "Alarm system"},
                                {"id": "o", "is": "office", "name": "Office ashore"}], "links": ["s>a>o"]}}


def main():
    figdir = tempfile.mkdtemp(prefix="n2d_")
    io.open(os.path.join(figdir, "worlds.n2d.json"), "w", encoding="utf-8").write(json.dumps(WORLDS))
    probs = []
    page = cm.n2d_figure(json.dumps(SPEC), SLIDE, probs, "M03 s14", figdir)
    check("a written figure builds", not probs and 'data-n2d="#n2-s14"' in page, probs)
    data = json.loads(page.split('id="n2-s14">')[1].split("</script>")[0].replace("<\\/", "</"))
    check("the module's system is joined in", len(data["things"]) == 3 and "world" not in data, data)
    probs = []
    bad = dict(SPEC, steps=[{"line": 1, "tag": {"o": "The maker or the company ashore reads every reading"}}])
    check("a refused figure fails the build with the reason",
          cm.n2d_figure(json.dumps(bad), SLIDE, probs, "M03 s14", figdir) == "" and any("tag" in p and "SPEC.md" in p for p in probs), probs)
    probs = []
    cm.n2d_figure(json.dumps(dict(SPEC, steps=[{"line": 7}])), SLIDE, probs, "M03 s14", figdir)
    check("a step naming a line the slide has not fails", any("line 7" in p for p in probs), probs)
    probs = []
    cm.n2d_figure(json.dumps(dict(SPEC, _todo="things")), SLIDE, probs, "M03 s14", figdir)
    check("a starter not yet written fails", any("still the starter" in p for p in probs), probs)

    out, entry = {}, {}
    cm.n2d_starter(SLIDE, entry, figdir, out)
    check("--init-build: code chose a path and named its starter", entry.get("figure") == "s14.n2d.json" and out["s14"]["form"] == "path"
          and len(out["s14"]["steps"]) == 3 and out["s14"].get("_todo") and entry.get("_brief", "").startswith("path"), (entry, out))
    out, entry = {}, {}
    cm.n2d_starter({"id": "s17", "kind": "slide", "title": "True or false: a VPN makes the link faster", "text": "A VPN encrypts."}, entry, figdir, out)
    check("--init-build: a question slide gets no figure, and says why", not out and entry.get("no_figure") and "figure" not in entry, entry)
    out, entry = {}, {"figure": "s14.svg"}
    cm.n2d_starter(SLIDE, entry, figdir, out)
    check("--init-build never replaces a figure the sheet names", entry == {"figure": "s14.svg"} and not out, entry)

    for f in cm.N2D_FILES:
        check("ships %s" % f, os.path.isfile(os.path.join(cm.SKILLS, "course-visuals", "n2d", f)))
    print("\n%s" % ("ALL PASS" if not FAILS else "FAILED: %d - %s" % (len(FAILS), "; ".join(FAILS))))
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
