#!/usr/bin/env python3
"""test_figure_fit.py - the figure pre-check's fixes in plain numbers (2.50.0), and the compiler drawing a fit only while it
still belongs to its spec and its column. Run: python test_figure_fit.py   (no browser needed)"""
from __future__ import annotations

import io
import json
import os
import re
import shutil
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import figure_fit as ff  # noqa: E402
import compile_module as cm  # noqa: E402  (figure_fit puts the compiler on the path)

PASS, FAIL = [], []


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print(("  ok    " if ok else "  FAIL  ") + name + (("  -> " + str(detail)[:400]) if detail and not ok else ""))


SPEC = {"size": [640, 390], "label": "two ways", "parts": [
    {"type": "text", "x": 20, "y": 24, "text": "GAS SAFE - double-walled pipe"},
    {"id": "PS", "type": "pipe_section", "x": 20, "y": 84, "w": 400, "h": 90, "branchAt": 320},
    {"id": "RA", "type": "readout", "x": 460, "y": 96, "w": 150, "h": 70},
    {"id": "MS", "type": "space", "x": 20, "y": 226, "w": 600, "h": 154},
    {"id": "GP", "type": "pipe", "d": "M30 352 H470 V300 l10 10", "value": 1},
    {"id": "GC", "type": "gas_cloud", "x": 200, "y": 244, "w": 180, "h": 100, "from": [290, 352], "fromIn": "figure"},
    {"id": "E", "type": "engine", "x": 476, "y": 296, "w": 130, "h": 70}]}


# 2.52.0 INSIDE - M01 s04 as the benchmark builder first drew it: the tank connection space over the stern's slope, the fuel
# preparation room's floor under the keel, the tank past its room's side (builds 1-3: "inside ... pokes out of
# path.kit-ga-hull" on the slide and on q01 / q03, which draw the same spec)
GA = {"size": [640, 390], "label": "ship", "parts": [
    {"id": "G", "type": "ga", "x": 20, "y": 120, "w": 600, "h": 150, "label": "LNG-fuelled ship, side view"},
    {"id": "TCS", "type": "space", "x": 26, "y": 130, "w": 130, "h": 100, "label": "Tank connection space"},
    {"id": "FT", "type": "tank", "x": 60, "y": 150, "w": 110, "h": 50, "label": "Fuel tank", "value": 0.6},
    {"id": "FPR", "type": "space", "x": 240, "y": 160, "w": 150, "h": 116, "label": "Fuel preparation room"},
    {"id": "ER", "type": "space", "x": 430, "y": 140, "w": 150, "h": 100, "label": "Engine room"}]}


def in_hull(spec):
    """the parts that poke out of the ga's hull outline (with the 5-unit margin), or past their room"""
    g = next(p for p in spec["parts"] if p["type"] == "ga")
    bad = []
    for p in spec["parts"]:
        if p["type"] == "ga":
            continue
        x0, y0, x1, y1 = p["x"], p["y"], p["x"] + p["w"], p["y"] + p["h"]
        if p["id"] == "FT":
            r = next(q for q in spec["parts"] if q["id"] == "TCS")
            if x0 < r["x"] or x1 > r["x"] + r["w"] or y0 < r["y"] or y1 > r["y"] + r["h"]:
                bad.append("FT past its room")
            continue
        lo, hi = ff.hull_x(g, y0), ff.hull_x(g, y1)
        if x0 < max(lo[0], hi[0]) + 4.9 or x1 > min(lo[1], hi[1]) - 4.9 or y0 < g["y"] + 4.9 or y1 > g["y"] + g["h"] - 4.9:
            bad.append(p["id"])
    return bad


def inside_part():
    print("-- INSIDE (2.52.0): every part drawn inside what it sits in - the hull's outline, its room")
    check("the spec as the builder drew it pokes out (the case it fixes): the stern room, the room under the keel, the room "
          "in the bow's curve, the tank past its room", sorted(in_hull(GA)) == ["ER", "FPR", "FT past its room", "TCS"], in_hull(GA))
    fixed, n = ff.inside_fix(GA)
    check("inside_fix: the stern room and the room under the keel moved or drawn inside the hull, the tank inside its room",
          n >= 3 and in_hull(fixed) == [], (n, in_hull(fixed), fixed["parts"]))
    tcs0, tcs1 = GA["parts"][1], fixed["parts"][1]
    ft0, ft1 = GA["parts"][2], fixed["parts"][2]
    check("... a room takes its parts with it (the tank moved off the stern with the tank connection space, then into it)",
          tcs1["x"] > tcs0["x"] and ft1["x"] > ft0["x"] and tcs1["x"] <= ft1["x"] <= tcs1["x"] + tcs1["w"] - ft1["w"], (tcs1, ft1))
    check("... never smaller than 70 % of the size the spec gave, nothing moved onto another part, the spec not touched",
          all(p1.get("w", 1) >= 0.7 * p0.get("w", 1) - 0.1 and p1.get("h", 1) >= 0.7 * p0.get("h", 1) - 0.1
              for p0, p1 in zip(GA["parts"], fixed["parts"])) and ff.spoiled(GA, fixed) == [] and GA["parts"][1]["x"] == 26,
          fixed["parts"])
    check("a spec with nothing out: no repair", ff.inside_fix(fixed)[1] == 0, ff.inside_fix(fixed)[1])
    eng = {"size": [640, 390], "parts": [{"id": "R", "type": "space", "x": 84, "y": 248, "w": 100, "h": 88},
                                         {"id": "E", "type": "engine", "x": 94, "y": 255, "w": 80, "h": 52}]}
    e2, k2 = ff.inside_fix(eng)
    check("an engine's cylinder heads (10 units over its block) count: the engine moved down inside its room (M01 run, s03: "
          "rect.kit-head poked out of the room)", k2 == 1 and e2["parts"][1]["y"] - 10 >= 248 + 5 - 0.01, e2["parts"][1])
    # the task page draws the fit figure_fit wrote for its question, only while the spec is the one it was made from
    import task_pages
    tmp = tempfile.mkdtemp(prefix="ff_task_")
    try:
        text = json.dumps(GA)
        io.open(os.path.join(tmp, "s04.kit.json"), "w", encoding="utf-8").write(text)
        fp = cm.fit_path(tmp, "s04.kit.json", "q01")
        os.makedirs(os.path.dirname(fp))
        io.open(fp, "w", encoding="utf-8").write(json.dumps({"source": cm.sha(text), "column": ff.TASK_COLUMN, "spec": fixed}))
        q = {"id": "q01", "mechanic": "hotspot", "visual": "The ship."}
        b = {"figure": "s04.kit.json", "areas": {"Tank connection space": "TCS"}}
        got = task_pages.figure_for(q, b, tmp, tmp, [], "q01")
        other = task_pages.figure_for(dict(q, id="q03"), b, tmp, tmp, [], "q03")
        tx = lambda f: next(p["x"] for p in f.spec_parts if p.get("id") == "TCS")   # noqa: E731
        check("task_pages.py draws q01's fit (its tap areas on the moved parts), and q03 - with no fit - the spec as written",
              got and other and tx(got) == tcs1["x"] and tx(other) == 26 and got.name != other.name, (got and tx(got), other and tx(other)))
        io.open(os.path.join(tmp, "s04.kit.json"), "w", encoding="utf-8").write(text.replace('"x": 430', '"x": 420'))
        again = task_pages.figure_for(q, b, tmp, tmp, [], "q01")
        check("... the spec edited since: the spec as written again", again and tx(again) == 26, again and tx(again))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    if not ff.studio.find_browser():
        print("  skip  the task page measured by the drawing check (no Chrome or Edge)")
        return
    # the same check the build runs: a course whose self-check is answered on this ship, measured on the task page as the
    # compile builds it - INSIDE before, the fit made by itself, and the compile's own drawing check clean after
    import test_compile_module as tcm
    tmp = tempfile.mkdtemp(prefix="ff_page_")
    try:
        screens = [
            {"id": "t01", "kind": "task-slide", "opens": "SC1", "title": "Self-check 1 - the new spaces", "text": "Self-check now.", "minutes": 2},
            {"id": "q01", "kind": "self-check", "set": "SC1", "mechanic": "hotspot", "question": "Tap the tank connection space.",
             "visual": "the ship", "answer": "Tank connection space*\nEngine room", "feedback": "Around the tank's valves."}]
        build = {"module": 1, "screens": {"t01": {"try_tablet": False},
                                          "q01": {"figure": "ship.kit.json", "areas": {"Tank connection space": "TCS", "Engine room": "ER"}}}}
        c, md = tcm.figures_course(tmp, build=build, screens=screens)
        figdir = os.path.join(c, "working_claude", "figures", "M01")
        io.open(os.path.join(figdir, "ship.kit.json"), "w", encoding="utf-8").write(json.dumps(GA))
        got, left = ff.fix_tasks(c, 1, figdir)
        check("fix_tasks: the task page measured as the compile builds it finds the parts out, and fixes them by itself",
              len(got) == 1 and got[0].startswith("q01 (ship.kit.json, task page): fixed by itself - INSIDE")
              and os.path.isfile(cm.fit_path(figdir, "ship.kit.json", "q01")), (got, left))
        code, out = tcm.run(tcm.COMPILE, c, "--module", "1", "--only", "tasks", "--drawing-check")
        check("... and the compile's own drawing check of the page finds no part out", "inside" not in out and "pokes out" not in out,
              out[-1200:])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def together_part():
    print("-- 2.56.0 the parts a figure's findings name, with their spec numbers, and the studio command")
    tmp = tempfile.mkdtemp(prefix="test_ff_tog_")
    try:
        sp = os.path.join(tmp, "s02.kit.json")
        io.open(sp, "w", encoding="utf-8").write(json.dumps({"size": [640, 390], "parts": [
            {"id": "SC", "type": "scale", "x": 40, "y": 24, "w": 90, "h": 330},
            {"id": "G1", "type": "gauge", "x": 500, "y": 100, "r": 40}, {"id": "Z", "type": "tank", "x": 1, "y": 1}]}))
        out = ff.parts_together(sp, "    inside - rect.kit-block in g.kit-part [part SC]: pokes out by 4 - path [part G1]\n"
                                    "    empty - ... [part SC]")
        line = out[0] if out else ""
        check("each named part once, in the order named, with its spec numbers; an unnamed part left out",
              "SC scale x 40 y 24 w 90 h 330 · G1 gauge x 500 y 100 r 40" in line and "Z tank" not in line, out)
        check("... and the studio command for the spec", any("studio.py s02.kit.json --step all" in x for x in out), out)
        check("a block that names no part still gets the studio command",
              ff.parts_together(sp, "    empty - blank 57 %") == [out[-1]], ff.parts_together(sp, "x"))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def failing_cache_part():
    """2.59.0 - a figure failing at the last build, nothing about it changed: its report is repeated, nothing measured"""
    print("-- 2.59.0 an unchanged failing figure is not measured or fixed again")
    import compile_module as cm2
    import content_script as cs2
    tmp = tempfile.mkdtemp(prefix="test_ff_fail_")
    calls = {"measure": 0, "fix": 0}
    saved = (ff.deck_figures, ff.all_specs, ff.measure, ff.try_fixes, cs2.paths, cs2.load, cm2.compile_deck, cm2.fitted)
    try:
        figdir = os.path.join(tmp, "figures", "M01")
        os.makedirs(figdir)
        sp = os.path.join(figdir, "s03.kit.json")
        io.open(sp, "w", encoding="utf-8").write(json.dumps({"size": [640, 390], "parts": [{"id": "S5", "type": "space", "x": 1, "y": 1}]}))
        ff.deck_figures = lambda c, m: ([("s03", sp, {})], figdir)
        ff.all_specs = lambda c, m: []
        prob = [(1, 0, "label", "S5 [part S5]", "found no clear place")]
        def measure(spec_path, sid, spec=None, strip=True):
            calls["measure"] += 1
            return list(prob), {"report": {"scale": 1}, "states": [{"svg": [640, 390], "panel": [640, 390]}], "parts": {}}
        def try_fixes(*a):
            calls["fix"] += 1
            return None, "no deterministic fix", None
        ff.measure, ff.try_fixes = measure, try_fixes
        cs2.paths = lambda c, m: {"script": os.path.join(tmp, "M01.json"), "dir": tmp}
        cs2.load = lambda p: {"screens": [{"id": "s03"}]} if p.endswith("M01.json") else {}
        cm2.compile_deck = lambda *a: ('<section id="s03">words</section>', None, None)
        cm2.fitted = lambda *a: None
        c1, t1, _ = ff.run_all(tmp, 1)
        first = dict(calls)
        c2, t2, _ = ff.run_all(tmp, 1)
        check("the first build measures the failing figure and tries its fixes; the second, nothing changed, does neither "
              "and says its last report again", c1 == 1 and c2 == 1 and first == {"measure": 1, "fix": 1} and calls == first
              and "unchanged since the last build" in t2 and "found no clear place" in t2, (calls, t2[-400:]))
        ff.run_all(tmp, 1, full=True)
        check("... --full measures it again", calls["measure"] == 2, calls)
        ff.run_all(tmp, 1, fix=False)
        check("... another fix mode (--no-fix) measures it again", calls["measure"] == 3, calls)
        io.open(sp, "w", encoding="utf-8").write(json.dumps({"size": [640, 390], "parts": [{"id": "S5", "type": "space", "x": 2, "y": 1}]}))
        ff.run_all(tmp, 1)
        check("... and a changed spec is measured again", calls["measure"] == 4, calls)
    finally:
        (ff.deck_figures, ff.all_specs, ff.measure, ff.try_fixes, cs2.paths, cs2.load, cm2.compile_deck, cm2.fitted) = saved
        shutil.rmtree(tmp, ignore_errors=True)


def applied_candidate_part():
    """2.66.3 - a closer fit (fewer findings, not clean) is written over the spec by the build itself when it adds no meaning
    BLOCK - the builder no longer copies it (2.66 run: every "a closer fit was saved" cost a builder turn and a build);
    one that adds a BLOCK, or was measured without the slide's photo row, is only saved, as before"""
    print("-- 2.66.3 the build applies its own closer fit when it adds no meaning BLOCK")
    import compile_module as cm2
    import content_script as cs2
    tmp = tempfile.mkdtemp(prefix="test_ff_apply_")
    saved = (ff.deck_figures, ff.all_specs, ff.measure, ff.try_fixes, cs2.paths, cs2.load, cm2.compile_deck, cm2.fitted,
             ff.kit_meaning.check, ff.kit_relate.freeze)
    try:
        figdir = os.path.join(tmp, "figures", "M01")
        os.makedirs(figdir)
        sp = os.path.join(figdir, "s03.kit.json")
        orig = {"size": [640, 390], "parts": [{"id": "S5", "type": "space", "x": 1, "y": 1, "w": 300, "h": 200}]}
        cand = {"size": [480, 390], "parts": [{"id": "S5", "type": "space", "x": 1, "y": 1, "w": 230, "h": 200}]}
        io.open(sp, "w", encoding="utf-8").write(json.dumps(orig))
        ff.deck_figures = lambda c, m: ([("s03", sp, {})], figdir)
        ff.all_specs = lambda c, m: []
        five = [("1280x800", 1, "small text", "S5 [part S5]", "12 px")] * 4 + [("1280x800", 1, "label", "S5 [part S5]", "no place")]
        one = [("1280x800", 1, "label", "S5 [part S5]", "found no clear place")]
        state = {"best": (cand, one, 3, True, [480, 343]), "blocks": []}
        ff.measure = lambda spec_path, sid, spec=None, strip=True: (list(five), {"report": {"scale": 0.6}, "parts": {},
                                                                               "states": [{"svg": [480, 343], "panel": [480, 343]}]})
        ff.try_fixes = lambda *a: (None, "re-fitted to its 480 px column: 1 finding(s) left (was 5)", state["best"])
        ff.kit_relate.freeze = lambda s: s
        ff.kit_meaning.check = lambda s, where="", resolved=None: list(state["blocks"]) if s.get("size") == [480, 390] else []
        cs2.paths = lambda c, m: {"script": os.path.join(tmp, "M01.json"), "dir": tmp}
        cs2.load = lambda p: {"screens": [{"id": "s03"}]} if p.endswith("M01.json") else {}
        cm2.compile_deck = lambda *a: ('<section id="s03">words</section>', None, None)
        cm2.fitted = lambda *a: None
        code, text, data = ff.run_all(tmp, 1)
        now = json.load(io.open(sp, encoding="utf-8"))
        before = os.path.join(figdir, cm2.FIT_DIR, "s03.s03.before.kit.json")
        check("the closer fit is written over the spec by the build, the spec as it was kept beside it, and the report says "
              "so and lists only what the fit leaves", now == cand and os.path.isfile(before)
              and json.load(io.open(before, encoding="utf-8")) == orig and "APPLIED to s03.kit.json" in text
              and "found no clear place" in text and "12 px" not in text
              and not os.path.isfile(os.path.join(figdir, cm2.FIT_DIR, "s03.s03.candidate.kit.json")), text[-700:])
        import build_module as bm
        short = "\n".join(bm.short_figures(text.splitlines(), "figures\\M01"))
        check("... and the build's short answer says it was applied - no 'copy it over the spec' for the builder",
              "closer fit was applied" in short and "copy it over" not in short, short)
        io.open(sp, "w", encoding="utf-8").write(json.dumps(orig))
        state["blocks"] = ["fit: INSIDE V: the vent V's outlet is below the deck"]
        code, text, data = ff.run_all(tmp, 1)
        check("a closer fit that adds a meaning BLOCK is not applied - only saved, and the report says why",
              json.load(io.open(sp, encoding="utf-8")) == orig and "saved as" in text and "INSIDE V" in text, text[-700:])
        state["blocks"], state["best"] = [], (cand, one, 3, False, [480, 343])
        code, text, data = ff.run_all(tmp, 1, full=True)
        check("... nor one measured without the slide's photo row (the spec would draw with the row back)",
              json.load(io.open(sp, encoding="utf-8")) == orig and "saved as" in text, text[-500:])
    finally:
        (ff.deck_figures, ff.all_specs, ff.measure, ff.try_fixes, cs2.paths, cs2.load, cm2.compile_deck, cm2.fitted,
         ff.kit_meaning.check, ff.kit_relate.freeze) = saved
        shutil.rmtree(tmp, ignore_errors=True)


def column_order_part():
    """2.65.0 - the COLUMN search one width at a time, stopping at the first clean fit: the same fit the parallel search kept
    (its first clean attempt in this order), fewer measurements"""
    print("-- 2.65.0 COLUMN: one width at a time, the first clean fit in the parallel search's order")
    spec = json.loads(json.dumps(SPEC))
    boxes = {str(i): [p.get("x", 0), p.get("y", 0), p.get("x", 0) + p.get("w", 40), p.get("y", 0) + p.get("h", 40), p.get("id"),
                      p["type"]] for i, p in enumerate(spec["parts"])}
    r0 = {"states": [{"panel": [480, 300]}], "parts": boxes, "report": {"scale": 0.7}}
    probs0 = [("1280x800", "0", "small text", "x", "")] * 4
    calls = []

    def fake(clean_below, gain=True):
        def measure(spec_path, sid, cand=None, strip=True):
            calls.append((cand["size"][0] if cand else None, strip))
            w = cand["size"][0] if cand else 640
            n = 0 if w <= clean_below else (3 if gain else 4)
            return [("1280x800", "0", "small text", "x", "")] * n, {"parts": boxes, "states": [{"panel": [480, 300]}]}
        return measure
    real, strip_ = ff.measure, ff.has_strip
    try:
        ff.has_strip = lambda sp, sid: False
        ff.measure = fake(10000)                         # every width is clean: the first one (0.88 of the column) is kept
        del calls[:]
        new, how, _ = ff.try_fixes("x.kit.json", "s01", spec, r0, probs0, None)
        check("every width would fit: only the first width is tried (its first unspoiled step), and the fit is the width the "
              "parallel search ranked first (0.88 of the 480 px column - its first clean attempt)",
              new and len(calls) <= 3 and len({c[0] for c in calls}) <= 2 and new["size"][0] == round(480 * 0.88)
              and how.startswith("COLUMN"), (calls, how))
        ff.measure = fake(0, gain=False)                # no width is ever clean
        del calls[:]
        new, how, best = ff.try_fixes("x.kit.json", "s01", spec, r0, probs0, None)
        n_all = len(calls)
        ff.MAX_MEASURES = 6
        del calls[:]
        new, how, best = ff.try_fixes("x.kit.json", "s01", spec, r0, probs0, None)
        check("a search that finds nothing stops at CF_FIT_MEASURES measurements (here 6 of the %d it would take) and says so; "
              "the default is 16 - every real IGF fit on record was found within 11" % n_all,
              new is None and len(calls) == 6 < n_all and "stopped after 6" in how, (len(calls), how))
        ff.MAX_MEASURES = 16
        del calls[:]
        inside = [("1280x800", "0", "inside", "E", "pokes out of ER")] * 2
        new, how, best = ff.try_fixes("x.kit.json", "s03", spec, r0, inside, None)
        check("2.66.4 a figure whose only finding is INSIDE (not its words' size) gets at most %d re-fit measurements, not 16 "
              "(the 2.66.3 run: IGF M01 s03 / s04, two searches of 16 probes at 10-17 s, every build, none found a fit)"
              % ff.INSIDE_MEASURES, len(calls) <= ff.INSIDE_MEASURES and "stopped after" in how, (len(calls), how))
    finally:
        ff.measure, ff.has_strip, ff.MAX_MEASURES = real, strip_, 16


def task_empty_part():
    """2.65.0 - EMPTY on a task page cropped by itself, as a slide's figure is - kept only when the page is then clean"""
    print("-- 2.65.0 EMPTY on a task page: cropped to what it shows, in the page's panel shape, the page measured again")
    if not ff.studio.find_browser():
        print("  skip  (no Chrome or Edge)")
        return
    import test_compile_module as tcm
    tmp = tempfile.mkdtemp(prefix="ff_empty_")
    try:
        small = {"size": [640, 390], "label": "a tank", "parts": [
            {"id": "FT", "type": "tank", "x": 30, "y": 30, "w": 150, "h": 70, "label": "Fuel tank", "value": 0.6},
            {"id": "V", "type": "valve", "x": 200, "y": 55, "label": "Tank valve"}]}
        screens = [
            {"id": "t01", "kind": "task-slide", "opens": "SC1", "title": "Self-check 1 - the tank", "text": "Self-check now.", "minutes": 2},
            {"id": "q01", "kind": "self-check", "set": "SC1", "mechanic": "hotspot", "question": "Tap the fuel tank.",
             "visual": "the tank", "answer": "Fuel tank*\nTank valve", "feedback": "The tank holds the fuel."}]
        build = {"module": 1, "screens": {"t01": {"try_tablet": False},
                                          "q01": {"figure": "tank.kit.json", "areas": {"Fuel tank": "FT", "Tank valve": "V"}}}}
        c, md = tcm.figures_course(tmp, build=build, screens=screens)
        figdir = os.path.join(c, "working_claude", "figures", "M01")
        io.open(os.path.join(figdir, "tank.kit.json"), "w", encoding="utf-8").write(json.dumps(small))
        got, left = ff.fix_tasks(c, 1, figdir)
        check("fix_tasks: a small drawing in a big task-page frame is cropped by itself (EMPTY)",
              any("EMPTY: cropped" in x for x in got) and os.path.isfile(cm.fit_path(figdir, "tank.kit.json", "q01")), (got, left))
        code, out = tcm.run(tcm.COMPILE, c, "--module", "1", "--only", "tasks", "--drawing-check")
        check("... and the compile's own drawing check of the page finds no empty space on it", "empty" not in out.lower(), out[-1200:])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    together_part()
    failing_cache_part()
    applied_candidate_part()
    column_order_part()
    task_empty_part()
    print("-- squeeze: positions and stretchable lengths follow the column, part sizes stay")
    s = ff.squeeze(SPEC, 0.5, x0=20)
    p = {q.get("id") or q["type"]: q for q in s["parts"]}
    check("the frame is half as wide, as tall as before", s["size"] == [320, 390], s["size"])
    check("a position maps x0 + (x - x0) k", p["RA"]["x"] == 240 and p["E"]["x"] == 248, (p["RA"]["x"], p["E"]["x"]))
    check("a room and a pipe section stretch (w, branchAt)", p["MS"]["w"] == 300 and p["PS"]["w"] == 200 and p["PS"]["branchAt"] == 160)
    check("a readout and an engine keep their size", p["RA"]["w"] == 150 and p["E"]["w"] == 130)
    check("a pipe's absolute x maps, its y stays, a relative step only scales", p["GP"]["d"] == "M25 352 H245 V300 l5 10", p["GP"]["d"])
    check("a gas cloud's origin in figure units moves with it", p["GC"]["from"] == [155, 352], p["GC"]["from"])
    check("the spec given is not changed", SPEC["parts"][2]["x"] == 460 and SPEC["size"] == [640, 390])

    print("-- shift_path: y moves too")
    check("M/H/V/L absolute, l relative", ff.shift_path("M10 20 H30 V40 L50 60 l5 5", lambda v: v, lambda v: v + 100)
          == "M10 120 H30 V140 L50 160 l5 5")

    print("-- tidy: a part past its room's edge moves left into free room, or is drawn narrower (never under 70 %)")
    t = {"size": [400, 300], "parts": [
        {"id": "R", "type": "space", "x": 10, "y": 10, "w": 380, "h": 200},
        {"id": "A", "type": "readout", "x": 30, "y": 40, "w": 100, "h": 50},
        {"id": "B", "type": "engine", "x": 300, "y": 120, "w": 120, "h": 60}]}
    boxes = {"0": [10, 10, 390, 210, "R", "space"], "1": [30, 40, 130, 90, "A", "readout"], "2": [300, 120, 420, 180, "B", "engine"]}
    out, n = ff.tidy(t, boxes, 400)
    b = out["parts"][2]
    check("the engine moved left by what poked out (40) - free room there", n == 1 and b["x"] == 260 and b["w"] == 120, b)
    boxes2 = dict(boxes, **{"1": [30, 110, 290, 200, "A", "readout"], "2": [300, 120, 410, 180, "B", "engine"]})  # left room taken
    out2, n2 = ff.tidy(t, boxes2, 400)
    b2 = out2["parts"][2]
    check("no free room: drawn narrower instead, by what poked out (30)", n2 == 1 and b2["x"] == 300 and b2["w"] == 90, b2)
    out3, _ = ff.tidy(t, dict(boxes2, **{"2": [300, 120, 480, 180, "B", "engine"]}), 400, w0={2: 120})
    check("never under 70 % of the size the spec gave", out3["parts"][2]["w"] == 84, out3["parts"][2])
    wide = {"size": [200, 100], "parts": [{"type": "text", "x": 10, "y": 20, "text": "ESD-PROTECTED - single-wall pipe"}]}
    out4, n4 = ff.tidy(wide, {"0": [10, 5, 260, 25, "", "text"]}, 200)
    check("a free text wider than the frame breaks at the space nearest its middle - the same words",
          n4 == 1 and out4["parts"][0]["text"].replace("\n", " ") == wide["parts"][0]["text"] and "\n" in out4["parts"][0]["text"],
          out4["parts"][0]["text"])

    print("-- pack: a figure laid into a narrower width, row by row, room by room (2.50.1)")
    fig = {"size": [640, 300], "parts": [
        {"id": "PS", "type": "pipe_section", "x": 20, "y": 40, "w": 400, "h": 80, "branchAt": 320},
        {"id": "VT", "type": "vent", "x": 340, "y": 20},
        {"id": "RA", "type": "readout", "x": 460, "y": 50, "w": 150, "h": 60},
        {"id": "MS", "type": "space", "x": 20, "y": 150, "w": 600, "h": 140},
        {"id": "GP", "type": "pipe", "d": "M30 260 H470"},
        {"id": "GD", "type": "readout", "x": 30, "y": 160, "w": 150, "h": 56},
        {"id": "E", "type": "engine", "x": 476, "y": 220, "w": 130, "h": 60}]}
    bx = {"0": [20, 40, 420, 120, "PS", "pipe_section"], "1": [340, 20, 360, 40, "VT", "vent"],
          "2": [460, 50, 610, 110, "RA", "readout"], "3": [20, 150, 620, 290, "MS", "space"],
          "4": [30, 258, 470, 262, "GP", "pipe"], "5": [30, 160, 180, 216, "GD", "readout"],
          "6": [476, 220, 606, 280, "E", "engine"]}
    b0 = {int(k): v[:4] for k, v in bx.items()}
    own = ff.owners(fig["parts"], b0)
    hst = ff.hosts(fig["parts"], b0, own)
    check("rooms decided on the spec as written: the readout, the engine and the pipe are in the machinery space",
          own.get(5) == 3 and own.get(6) == 3 and own.get(4) == 3 and own.get(2) is None, own)
    check("the vent sits ON the pipe section: it keeps its place there", hst == {1: 0}, hst)
    out, ok = ff.pack(fig, bx, 480, owner=own, host=hst)
    q = {p.get("id"): p for p in out["parts"]}
    check("the rows fit: the frame is 480 wide", ok and out["size"][0] == 480, out["size"])
    check("a readout keeps its width, the pipe section gives way", q["RA"]["w"] == 150 and q["PS"]["w"] < 400, (q["RA"], q["PS"]))
    check("the readout is still right of the pipe section, inside the frame",
          q["RA"]["x"] > q["PS"]["x"] + q["PS"]["w"] and q["RA"]["x"] + 150 <= 480, (q["PS"], q["RA"]))
    vent_at = (q["VT"]["x"] - q["PS"]["x"]) / float(q["PS"]["w"])
    check("the vent stays at the same share of its pipe section (on its branch)", abs(vent_at - 0.8) < 0.06, vent_at)
    check("the room shrinks with the frame and the engine stays inside it",
          q["MS"]["w"] <= 470 and q["E"]["x"] + 130 <= q["MS"]["x"] + q["MS"]["w"], (q["MS"], q["E"]))
    end = float(re.findall(r"H(-?[\d.]+)", q["GP"]["d"])[0])
    check("the gas pipe still runs into the engine (it ends at the engine's new left side)",
          abs(end - (q["E"]["x"] - 6)) < 8, (q["GP"]["d"], q["E"]["x"]))
    nothing_moved_vertically = all(p.get("y") == o.get("y") for p, o in zip(out["parts"], fig["parts"]))
    check("nothing moves up or down", nothing_moved_vertically)

    print("-- keep_in: a part past its room's floor grows the room; a part past a side moves in")
    k_spec = {"size": [300, 200], "parts": [{"id": "R", "type": "space", "x": 10, "y": 10, "w": 280, "h": 150},
                                            {"id": "C", "type": "gas_cloud", "x": 250, "y": 120, "w": 60, "h": 60}]}
    k_out, kn = ff.keep_in(k_spec, {"0": [10, 10, 290, 160, "R", "space"], "1": [250, 120, 310, 180, "C", "gas_cloud"]}, {1: 0})
    check("the room grew by what poked out below, the cloud moved in from the right",
          kn == 2 and k_out["parts"][0]["h"] > 150 and k_out["parts"][1]["x"] < 250, k_out["parts"])

    print("-- crop: EMPTY - a window around what is drawn, in the panel's shape; the parts are not moved")
    sparse = {"size": [640, 390], "parts": [{"id": "T", "type": "tank", "x": 40, "y": 40, "w": 120, "h": 60}]}
    c = ff.crop(sparse, {"0": [40, 40, 160, 100, "T", "tank"]}, [682, 415])
    v = c and c["view"]
    check("a view around the tank (8 units clear), in the panel's shape",
          v and v[0] <= 32 and v[1] <= 32 and v[0] + v[2] >= 168 and v[1] + v[3] >= 108 and abs(v[2] / v[3] - 682 / 415.0) < 0.01, v)
    check("the parts are where they were", c["parts"] == sparse["parts"])
    check("a drawing that fills its frame is not cropped", ff.crop(sparse, {"0": [0, 0, 640, 390, "T", "tank"]}, [682, 415]) is None)

    print("-- 2.50.4: never a fit or a saved candidate with a part out of its frame or on another part (M01 run 4, s05)")
    ga = {"size": [600, 330], "parts": [
        {"id": "RL", "type": "space", "x": 6, "y": 30, "w": 284, "h": 290},
        {"id": "G1", "type": "pipe", "d": "M6 240 H160"},
        {"id": "V1", "type": "valve", "x": 44, "y": 240},
        {"id": "E1", "type": "engine", "x": 160, "y": 208, "w": 110, "h": 72},
        {"id": "C2", "type": "gas_cloud", "x": 300, "y": 80, "w": 250, "h": 110},
        {"id": "L2", "type": "lamp", "x": 560, "y": 70},
        {"id": "TK", "type": "tank", "x": 320, "y": 220, "w": 200, "h": 80},
        {"id": "TV", "type": "valve", "x": 420, "y": 230}]}
    lamp_out = json.loads(json.dumps(ga))
    lamp_out["parts"][5]["x"] = 635.4                       # the run-4 candidate's lamp
    why = ff.spoiled(ga, lamp_out)
    check("a part moved past the frame (the lamp at x 635 in a 600-wide spec) spoils the re-fit",
          len(why) == 1 and "L2 (lamp) moved outside the 600 x 330 frame" in why[0], why)
    eng_on = json.loads(json.dumps(ga))
    eng_on["parts"][3]["x"] = 20                            # the engine drawn over the valve
    why = ff.spoiled(ga, eng_on)
    check("a part moved onto one it was clear of (the engine over the valve) spoils the re-fit",
          why == ["V1 (valve) moved onto E1 (engine)"], why)
    calm = json.loads(json.dumps(ga))
    calm["parts"][4]["x"] = 40                              # a cloud over the engine room is a cloud
    calm["parts"][6]["x"], calm["parts"][7]["x"] = 300, 400  # a valve drawn on its tank moves with it
    check("a cloud over parts, a valve kept on its tank and a crop (a view, nothing moved) are not spoiled",
          ff.spoiled(ga, calm) == [] and ff.spoiled(ga, dict(ga, view=[300, 60, 280, 160])) == [],
          (ff.spoiled(ga, calm), ff.spoiled(ga, dict(ga, view=[300, 60, 280, 160]))))
    new, how, best = ff.usable(ga, lamp_out, "COLUMN: re-fitted", (eng_on, [("1280x800", 1, "empty", "", "")], 3, True, [600, 330]))
    check("figure_fit keeps no such fit and saves no such candidate - and says why",
          new is None and best is None and "lamp" in how and "no candidate saved" in how and "onto E1" in how, how)
    new, how, best = ff.usable(ga, calm, "COLUMN: re-fitted", None)
    check("... a usable fit is kept as it is", new is calm and how == "COLUMN: re-fitted", how)

    print("-- the compiler draws a fit only while it belongs to its spec and its column")
    tmp = tempfile.mkdtemp(prefix="fit_test_")
    try:
        text = json.dumps(SPEC)
        s05 = {"id": "s05", "layout": "split"}
        b_two, b_wide = {"composition": "two-col", "dark": True}, {"composition": "wide-left", "dark": True}
        fp = cm.fit_path(tmp, "s05.kit.json", "s05")
        os.makedirs(os.path.dirname(fp))
        rec = {"source": cm.sha(text), "column": cm.composition_key(s05, b_wide), "spec": ff.squeeze(SPEC, 0.6, 20)}
        io.open(fp, "w", encoding="utf-8").write(json.dumps(rec))
        got = cm.fitted(tmp, "s05.kit.json", text, cm.composition_key(s05, b_wide), "s05")
        check("same spec, same column: the fit is drawn", got and json.loads(got)["size"] == rec["spec"]["size"])
        check("the slide's layout changed back: the spec as written",
              cm.fitted(tmp, "s05.kit.json", text, cm.composition_key(s05, b_two), "s05") is None)
        check("the spec was edited: the spec as written",
              cm.fitted(tmp, "s05.kit.json", text.replace("640", "600"), cm.composition_key(s05, b_wide), "s05") is None)
        check("another slide showing the same spec has its own fit",
              cm.fitted(tmp, "s05.kit.json", text, cm.composition_key(s05, b_wide), "s07") is None)
        check("a photo strip choice is part of the column",
              cm.composition_key(s05, dict(b_wide, no_photo=["gas detector"])) != cm.composition_key(s05, b_wide))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    inside_part()
    print("\n%s - %d passed, %d failed" % ("ALL PASS" if not FAIL else "FAILED", len(PASS), len(FAIL)))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
