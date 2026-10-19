#!/usr/bin/env python3
"""test_figure_fit.py - the figure pre-check's fixes in plain numbers (2.50.0), and the compiler drawing a fit only while it
still belongs to its spec and its column. Run: python test_figure_fit.py   (no browser needed)"""
from __future__ import annotations

import io
import json
import os
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


def main():
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

    print("-- crop: EMPTY - a window around what is drawn, in the panel's shape; the parts are not moved")
    sparse = {"size": [640, 390], "parts": [{"id": "T", "type": "tank", "x": 40, "y": 40, "w": 120, "h": 60}]}
    c = ff.crop(sparse, {"0": [40, 40, 160, 100, "T", "tank"]}, [682, 415])
    v = c and c["view"]
    check("a view around the tank (8 units clear), in the panel's shape",
          v and v[0] <= 32 and v[1] <= 32 and v[0] + v[2] >= 168 and v[1] + v[3] >= 108 and abs(v[2] / v[3] - 682 / 415.0) < 0.01, v)
    check("the parts are where they were", c["parts"] == sparse["parts"])
    check("a drawing that fills its frame is not cropped", ff.crop(sparse, {"0": [0, 0, 640, 390, "T", "tank"]}, [682, 415]) is None)

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

    print("\n%s - %d passed, %d failed" % ("ALL PASS" if not FAIL else "FAILED", len(PASS), len(FAIL)))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
