# -*- coding: utf-8 -*-
"""measure_word_budgets.py - how many words each slide layout holds, measured with the real compiler, templates and
run_audits.py (2.63.0). The numbers in course-module-ui/knowledge/layout-templates.json "budgets" come from here.

    python measure_word_budgets.py --course <course folder> --out <results.json> [--layouts a,b] [--words 40,50,...]

For every layout and word count it builds a small deck (like a module, never in the course): four texts of that length,
cut from the course's own approved scripts (a statement and bullets), each measured slide between three short text
slides so L62 keeps its own layout; then run_audits.py at 1024 x 768 and 1280 x 800 says what spills and by how much.
A layout's budget is the longest count at which all four texts fit. Re-run it when a template, the type or the logo
changes. Writes nothing in the course. Needs Chrome or Edge.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import glob
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SK = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(SK, "course-factory", "compile", "scripts"))
sys.path.insert(0, os.path.join(SK, "course-factory", "scripts"))
RUN = os.path.join(HERE, "run_audits.py")
KIT = {"size": [640, 390], "label": "a drawing", "parts": [
    {"id": "T", "type": "tank", "x": 40, "y": 150, "w": 260, "h": 140, "label": "Fuel tank", "value": 0.5},
    {"id": "R", "type": "space", "x": 360, "y": 60, "w": 250, "h": 260, "label": "Tank connection space"},
    {"id": "V", "type": "valve", "x": 485, "y": 220, "label": "Master valve", "value": 1}]}
LAYOUTS = {   # layout -> (the picture, the build-sheet entry)
    "beside-drawing": ("kit", {"composition": "two-col"}),
    "beside-drawing+inset": ("kit", {"composition": "two-col", "inset": {"photo": "", "caption": "A ship's deck tank."}}),
    "beside-photo-column": ("photo", {"composition": "wide-left"}),
    "under-top-photo": ("photo", {"composition": "stage", "template": "figure-stage", "variant": "figure-top"}),
    "photo-full": ("photo", {"composition": "photo", "dark": True}),
    "photo-framed": ("photo", {"composition": "two-col", "template": "photo-explain", "variant": "split", "dark": True}),
    "parts": ("kit", {"composition": "two-col", "template": "content-in-parts"}),
}


def lines_of(course):
    pool = []
    for sp in sorted(glob.glob(os.path.join(course, "working_claude", "script", "M*.json"))):
        if sp.endswith(".build.json") or "cue_fixes" in sp:
            continue
        for s in json.load(io.open(sp, encoding="utf-8")).get("screens", []):
            if s.get("kind") == "slide" and not s.get("recap"):
                pool += [x.strip().lstrip("•").strip() for x in (s.get("text") or "").split("\n") if len(x.split()) >= 5]
    return pool


def text_of(pool, n, k):
    out, w, i = [], 0, k
    while w < n:
        line = pool[i % len(pool)].split()
        i += 1
        take = line[:max(1, n - w)]
        out.append(" ".join(take).rstrip(",;:") + ("" if take == line else "."))
        w += len(take)
    return "\n".join([out[0]] + ["• " + x for x in out[1:]])


def measure(tcm, pool, lay, n0):
    pic, entry = LAYOUTS[lay]
    tmp = tempfile.mkdtemp(prefix="budget_")
    try:
        screens, sheet = [], {"module": 1, "screens": {}}
        for j in range(4):
            sid = "s%02d" % (j + 1)
            screens.append({"id": sid, "kind": "slide", "title": "The fuel system of an IGF ship", "layout": "split",
                            "visual_kind": "photo" if pic == "photo" else "comparison", "text": text_of(pool, n0, 7 * j + 3 * n0),
                            "visual": "A picture.", "notes": "- Say it.", "minutes": 2})
            e = dict(entry, figure=("assets/img/p%02d.jpg" % j) if pic == "photo" else "k.kit.json", declined_3d="flat")
            if "inset" in e:
                e["inset"] = dict(e["inset"], photo="assets/img/i%02d.jpg" % j)
            sheet["screens"][sid] = e
            for f in range(3):
                fid = "f%02d%d" % (j + 1, f)
                screens.append({"id": fid, "kind": "slide", "title": "Between %d" % f, "layout": "split", "visual_kind": "none",
                                "text": "A short line of words on a slide with no picture %d." % f, "notes": "- Say it.", "minutes": 1})
                sheet["screens"][fid] = {"figure": "", "visual_kind": "none"}
        c, md = tcm.new_course(tmp, tcm.script(screens=screens), build=False)
        img, meta = os.path.join(md, "assets", "img"), {}
        for j in range(4):
            for f in ("p%02d.jpg" % j, "i%02d.jpg" % j):
                io.open(os.path.join(img, f), "wb").write(tcm.png(1600, 1067, (60 + 3 * j, 90, 120)))
                meta[f] = {"source": "Wikimedia Commons", "author": "A. Person", "licence": "CC BY 4.0", "description": "A ship."}
        tcm.cs.save(os.path.join(img, "_photo_meta.json"), meta)
        tcm.cs.save(os.path.join(c, "working_claude", "figures", "M01", "k.kit.json"), KIT)
        tcm.cs.save(os.path.join(c, "working_claude", "script", "M01.build.json"), sheet)
        tcm.run(tcm.COMPILE, c, "--module", "1", "--only", "deck")
        page = os.path.join(md, "presentation", "index.html")
        deck = io.open(page, encoding="utf-8").read()
        built = {}
        for m in re.finditer(r"<section ([^>]*)>", deck):
            sid, t = re.search(r'\bid="(s\d+)"', m.group(1)), re.search(r'data-template="([^"]+)"[^>]*data-variant="([^"]+)"', m.group(1))
            if sid and t:
                built[sid.group(1)] = "%s/%s" % t.groups()
        row = {}
        for size in ("1024x768", "1280x800"):
            p = subprocess.run([sys.executable, RUN, page, "--quiet", "--viewport", size], capture_output=True, text=True,
                               encoding="utf-8", errors="replace")
            block = re.split(r"\n\d+x\d+\s", p.stdout.split(size, 1)[1] if size in p.stdout else "")[0]
            for j in range(4):
                sid = "s%02d" % (j + 1)
                px = [int(float(x)) for x in re.findall(r"\(%s\): (?:spills|scrolls) [^\n]*? by (\d+(?:\.\d+)?) px" % sid, block)]
                row.setdefault(sid, {"built": built.get(sid)})[size] = max(px) if px else 0
            if "NOT MEASURED" in p.stdout:
                row["error"] = "not measured at %s" % size
        return lay, n0, row
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main(argv=None):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--course", required=True, help="a course folder whose approved scripts give the texts")
    ap.add_argument("--out", required=True)
    ap.add_argument("--layouts", default="")
    ap.add_argument("--words", default="40,50,55,60,65,70,75,80,85,90,95,100,110,120,130")
    o = ap.parse_args(argv)
    import test_compile_module as tcm  # noqa: E402 - the same fixture course the compiler's own tests build
    pool = lines_of(o.course)
    if not pool:
        print("Stopped - no approved script lines in %s\\working_claude\\script" % o.course)
        return 2
    jobs = [(lay, int(n)) for lay in (o.layouts.split(",") if o.layouts else LAYOUTS) for n in o.words.split(",")]
    res = {}
    with cf.ThreadPoolExecutor(2) as ex:
        for lay, n, row in ex.map(lambda a: measure(tcm, pool, *a), jobs):
            res.setdefault(lay, {})[str(n)] = row
    json.dump(res, io.open(o.out, "w", encoding="utf-8"), indent=1)
    for lay, rows in res.items():
        fit = [int(n) for n, r in rows.items() if all(v.get("1024x768", 1) == 0 for k, v in r.items() if k != "error")]
        bad = sorted(int(n) for n in rows if int(n) not in fit)
        print("%-22s fits all four up to %s words; first spill at %s" % (lay, max([x for x in fit if not bad or x < bad[0]] or [0]),
                                                                          bad[0] if bad else "-"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
