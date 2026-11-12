# -*- coding: utf-8 -*-
"""measure_word_budgets.py - how many words each slide layout holds, measured with the real compiler, templates and
run_audits.py (2.63.0). The numbers in course-module-ui/knowledge/layout-templates.json "budgets" come from here.

    python measure_word_budgets.py --course <course folder> --out <results.json> [--layouts a,b] [--words 40,50,...]

For every layout and word count it builds a small deck (like a module, never in the course): four texts of that length,
cut from the course's own approved scripts (a statement and bullets), each measured slide between three short text
slides so the layout plan keeps its own layout; then run_audits.py at 1024 x 768, 1280 x 800 and 1280 x 720 says what
spills and by how much. A layout's budget is the longest count at which all four texts fit at every size. Re-run it when a template, the type or the logo
changes. Writes nothing in the course. Needs Chrome or Edge.

Each layout's photograph is the shape its box takes (PICTURES): a picture is never put in a box of another shape. The
templates that have the room answer (a scenario, a worked example, a true or false - ACTIVE) open more on their last Next,
so their decks are walked with fit_gate.py, every Next, instead of run_audits.py.
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
FIT = os.path.join(HERE, "fit_gate.py")
KIT = {"size": [640, 390], "label": "a drawing", "parts": [
    {"id": "T", "type": "tank", "x": 40, "y": 150, "w": 260, "h": 140, "label": "Fuel tank", "value": 0.5},
    {"id": "R", "type": "space", "x": 360, "y": 60, "w": 250, "h": 260, "label": "Tank connection space"},
    {"id": "V", "type": "valve", "x": 485, "y": 220, "label": "Master valve", "value": 1}]}
KIT_WIDE = {"size": [960, 380], "label": "a wide drawing", "parts": [      # a ship's run of tanks: wide enough for a band
    {"id": "T1", "type": "tank", "x": 40, "y": 120, "w": 240, "h": 150, "label": "Fuel tank 1", "value": 0.5},
    {"id": "R", "type": "space", "x": 330, "y": 60, "w": 300, "h": 260, "label": "Tank connection space"},
    {"id": "T2", "type": "tank", "x": 680, "y": 120, "w": 240, "h": 150, "label": "Fuel tank 2", "value": 0.7},
    {"id": "V", "type": "valve", "x": 470, "y": 220, "label": "Master valve", "value": 1}]}
LAYOUTS = {   # layout -> (the picture, the build-sheet entry)
    "beside-drawing": ("kit", {"composition": "two-col"}),
    "beside-drawing+inset": ("kit", {"composition": "two-col", "inset": {"photo": "", "caption": "A ship's deck tank."}}),
    "beside-photo-column": ("column", {"composition": "wide-left"}),
    "under-top-photo": ("photo", {"composition": "stage", "template": "figure-stage", "variant": "figure-top"}),
    "photo-full": ("photo", {"composition": "photo", "dark": True}),
    "photo-framed": ("column", {"composition": "two-col", "template": "photo-explain", "variant": "split", "dark": True}),
    "parts": ("kit", {"composition": "two-col", "template": "content-in-parts"}),
    "under-top-tiles": ("tiles", {"composition": "two-col", "variant": "figure-top"}),
    "parts-under-top-tiles": ("tiles", {"composition": "two-col", "template": "content-in-parts", "variant": "figure-top"}),
    "over-bottom-tiles": ("tiles", {"composition": "two-col", "variant": "figure-bottom"}),
    "over-bottom-photo": ("photo", {"composition": "wide-left", "template": "explain-figure", "variant": "figure-bottom"}),
    "beside-tall-photo": ("portrait", {"composition": "two-col", "template": "explain-figure", "variant": "figure-tall"}),
    "under-band-drawing": ("wide", {"composition": "two-col", "variant": "figure-top"}),
    "over-band-drawing": ("wide", {"composition": "two-col", "variant": "figure-bottom"}),
    "parts-under-band-drawing": ("wide", {"composition": "two-col", "template": "content-in-parts", "variant": "figure-top"}),
    "table-beside-drawing": ("kit", {"composition": "two-col", "template": "reference-table", "variant": "with-figure"}),
    "table-beside-photo": ("column", {"composition": "wide-left", "template": "reference-table", "variant": "figure-left"}),
    "table-under-top-tiles": ("tiles", {"composition": "two-col", "template": "reference-table", "variant": "figure-top"}),
    "table-over-bottom-tiles": ("tiles", {"composition": "two-col", "template": "reference-table", "variant": "figure-bottom"}),
    "table-under-band-drawing": ("wide", {"composition": "two-col", "template": "reference-table", "variant": "figure-top"}),
    "table-over-band-drawing": ("wide", {"composition": "two-col", "template": "reference-table", "variant": "figure-bottom"}),
    "table-alone": ("none", {"template": "reference-table", "variant": "text-only"}),
    "scenario-under-band": ("band", {"variant": "figure-top"}),
    "scenario-over-band": ("band", {"variant": "figure-bottom"}),
    "scenario-choices-under-band": ("band", {"variant": "figure-top"}),
    "scenario-choices-over-band": ("band", {"variant": "figure-bottom"}),
    "worked-under-band": ("band", {"variant": "figure-top"}),
    "worked-over-band": ("band", {"variant": "figure-bottom"}),
    "true-false-under-band": ("band", {"variant": "figure-top"}),
    "true-false-over-band": ("band", {"variant": "figure-bottom"}),
}
# the templates that have the room answer, in their band (a wide photograph across the slide, their two columns under it or
# over it): the words measured are the column's - the situation, the choices (the question, the choices and why each), the
# steps, the why - the other column kept short, as the columns stand side by side
ACTIVE = {"scenario-under-band": "situation", "scenario-over-band": "situation", "scenario-choices-under-band": "choices",
          "scenario-choices-over-band": "choices", "worked-under-band": "steps", "worked-over-band": "steps",
          "true-false-under-band": "why", "true-false-over-band": "why"}
PICTURES = {"photo": (1600, 1067), "portrait": (1200, 1600), "column": (1600, 1333), "band": (2000, 800)}   # the photographs' shapes
TABLE_ROWS = (4, 5, 6, 7, 8)       # a table layout is measured by its rows and the words of a row: --words are the row's
SIZES = ("1024x768", "1280x800", "1280x720")


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


def table_of(pool, rows, per, k):
    """rows lines "a b | c d e ..." of per words each (the first cell two words), cut from the course's own lines"""
    out = []
    for r in range(rows):
        w = pool[(k + 5 * r) % len(pool)].split()
        w = (w * 3)[:per]
        out.append("%s | %s" % (" ".join(w[:2]), " ".join(w[2:]).rstrip(",;:")))
    return "\n".join(out)


def lines_cut(pool, n, k, per=12):
    """n words of the course's own lines, as lines of about per words, no bullets"""
    words = []
    while len(words) < n:
        words += pool[k % len(pool)].rstrip(".,;:").split()
        k += 1
    words = words[:n]
    return "\n".join(" ".join(words[i:i + per]).rstrip(",;:") + "." for i in range(0, len(words), per))


def active_of(kind, pool, n, k):
    """the fields of a scenario, a worked example or a true or false whose measured column (kind) holds n words"""
    if kind in ("situation", "choices"):
        sit = lines_cut(pool, n if kind == "situation" else 15, k, 30)
        why = 5 if kind == "situation" else max(3, (n - 7 - 12) // 3)
        return {"active": "scenario", "text": sit, "ask": lines_cut(pool, 7 if kind == "choices" else 5, k + 1, 99).rstrip(".") + "?",
                "choices": "\n".join(lines_cut(pool, 4, k + 2 + i, 99) for i in range(3)),
                "why": "\n".join(lines_cut(pool, why, k + 5 + i, 99) for i in range(3)), "right": "A"}
    if kind == "steps":
        return {"active": "worked-example", "text": lines_cut(pool, n, k, 10), "ask": lines_cut(pool, 10, k + 3, 99).rstrip(".") + "?",
                "reveal": lines_cut(pool, 12, k + 4, 99)}
    return {"claim": lines_cut(pool, 9, k + 2, 99), "claim_is": "false", "text": lines_cut(pool, n, k, 14)}


def measure(tcm, pool, lay, n0, rows=0):
    pic, entry = LAYOUTS[lay]
    tmp = tempfile.mkdtemp(prefix="budget_")
    try:
        screens, sheet = [], {"module": 1, "screens": {}}
        for j in range(4):
            sid = "s%02d" % (j + 1)
            screens.append({"id": sid, "kind": "slide", "title": "The fuel system of an IGF ship", "layout": "split",
                            "visual_kind": "photo" if pic in PICTURES else "none" if pic == "none" else "comparison", "text": table_of(pool, rows, n0, 7 * j + 3 * n0) if rows else text_of(pool, n0, 7 * j + 3 * n0),
                            "visual": "A picture.", "notes": "- Say it.", "minutes": 2})
            if lay in ACTIVE:
                screens[-1].update(active_of(ACTIVE[lay], pool, n0, 7 * j + 3 * n0))
            e = dict(entry, figure=("assets/img/p%02d.jpg" % j) if pic in PICTURES else "w.kit.json" if pic == "wide" else "k.kit.json",
                     declined_3d="flat")
            if pic == "none":
                e = dict(entry, figure="", visual_kind="none")
            if pic == "tiles":           # two wide photographs: a row on top, the words under them
                e = dict(entry, figure="", tiles=["assets/img/p%02d.jpg" % j, "assets/img/i%02d.jpg" % j], declined_3d="flat")
            if e.get("template") == "content-in-parts" and pic in ("tiles", "wide"):   # in parts: two of about n words each
                a = text_of(pool, n0, 7 * j + 3 * n0).split("\n")
                b2 = text_of(pool, n0, 7 * j + 3 * n0 + 5).split("\n")
                screens[-1]["text"] = "\n".join(a + [x.lstrip("• ") for x in b2[:1]] + b2[1:])
                e["parts"] = [[1, len(a)], [len(a) + 1, len(a) + len(b2)]]
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
                size = PICTURES.get(pic, PICTURES["photo"])       # each layout's photograph the shape its box takes
                io.open(os.path.join(img, f), "wb").write(tcm.png(size[0], size[1], (60 + 3 * j, 90, 120)))
                meta[f] = {"source": "Wikimedia Commons", "author": "A. Person", "licence": "CC BY 4.0", "description": "A ship."}
        tcm.cs.save(os.path.join(img, "_photo_meta.json"), meta)
        tcm.cs.save(os.path.join(c, "working_claude", "figures", "M01", "k.kit.json"), KIT)
        tcm.cs.save(os.path.join(c, "working_claude", "figures", "M01", "w.kit.json"), KIT_WIDE)
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
        if lay in ACTIVE:              # the answer opens on the last Next: fit_gate.py walks every Next, run_audits.py does not
            out = os.path.join(tmp, "fit.json")
            p = subprocess.run([sys.executable, FIT, page, "--json", out] + ["--viewport=" + z for z in SIZES], capture_output=True,
                               text=True, encoding="utf-8", errors="replace")
            found = json.load(io.open(out, encoding="utf-8")) if os.path.isfile(out) else {}
            for j in range(4):
                sid = "s%02d" % (j + 1)
                for size in SIZES:
                    row.setdefault(sid, {"built": built.get(sid)})[size] = sum(
                        1 for x in found.get(size, []) if x[0] == sid and x[2] in ("cut", "spill", "picture"))
            if p.returncode == 2 or not found and p.returncode:
                row["error"] = "not measured: %s" % p.stdout[-300:]
            return lay, n0, row
        for size in SIZES:
            p = subprocess.run([sys.executable, RUN, page, "--quiet", "--viewport", size], capture_output=True, text=True,
                               encoding="utf-8", errors="replace")
            block = re.split(r"\n\d+x\d+\s", p.stdout.split(size, 1)[1] if size in p.stdout else "")[0]
            for j in range(4):
                sid = "s%02d" % (j + 1)
                # a full-screen or framed photograph's slow zoom (lt-kb) "scrolls" its own box the same at any word count:
                # it is the picture moving, not the words, and is not counted
                px = [int(float(x)) for x in re.findall(r"\(%s\): (?:spills|scrolls) (?!div\.photo-wrap )[^\n]*? by (\d+(?:\.\d+)?) px" % sid, block)]
                row.setdefault(sid, {"built": built.get(sid)})[size] = max(px) if px else 0
            if "NOT MEASURED" in p.stdout:
                row["error"] = "not measured at %s" % size
        return lay, ("%dx%d" % (rows, n0)) if rows else n0, row
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main(argv=None):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--course", required=True, help="a course folder whose approved scripts give the texts")
    ap.add_argument("--out", required=True)
    ap.add_argument("--layouts", default="")
    ap.add_argument("--words", default="40,50,55,60,65,70,75,80,85,90,95,100,110,120,130")
    ap.add_argument("--rows", default=",".join(str(r) for r in TABLE_ROWS), help="the table layouts' rows")
    ap.add_argument("--row-words", default="6,9,12,16", help="the table layouts' words in a row")
    o = ap.parse_args(argv)
    import test_compile_module as tcm  # noqa: E402 - the same fixture course the compiler's own tests build
    pool = lines_of(o.course)
    if not pool:
        print("Stopped - no approved script lines in %s\\working_claude\\script" % o.course)
        return 2
    jobs = []
    for lay in (o.layouts.split(",") if o.layouts else LAYOUTS):
        if lay.startswith("table-"):                  # a table: rows by the words of a row (--rows, --row-words)
            jobs += [(lay, int(n), int(r)) for r in o.rows.split(",") for n in o.row_words.split(",")]
        else:
            jobs += [(lay, int(n)) for n in o.words.split(",")]
    res = {}
    with cf.ThreadPoolExecutor(2) as ex:
        for lay, n, row in ex.map(lambda a: measure(tcm, pool, *a), jobs):
            res.setdefault(lay, {})[str(n)] = row
    json.dump(res, io.open(o.out, "w", encoding="utf-8"), indent=1)
    for lay, rows in res.items():
        if lay.startswith("table-"):
            fits = sorted(k for k, r in rows.items() if all(v.get(z, 1) == 0 for q, v in r.items() if q != "error" for z in SIZES))
            print("%-26s fits all four: %s; spills: %s" % (lay, " ".join(fits) or "none", " ".join(sorted(set(rows) - set(fits))) or "-"))
            continue
        fit = [int(n) for n, r in rows.items() if all(v.get(z, 1) == 0 for k, v in r.items() if k != "error" for z in SIZES)]
        bad = sorted(int(n) for n in rows if int(n) not in fit)
        print("%-22s fits all four up to %s words; first spill at %s" % (lay, max([x for x in fit if not bad or x < bad[0]] or [0]),
                                                                          bad[0] if bad else "-"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
