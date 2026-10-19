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

    print("\n%s - %d passed, %d failed" % ("ALL PASS" if not FAIL else "FAILED", len(PASS), len(FAIL)))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
