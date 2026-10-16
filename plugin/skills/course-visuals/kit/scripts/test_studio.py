#!/usr/bin/env python3
"""test_studio.py - the figure studio draws one spec, audits every step at both sizes and photographs it, and the
kit's own layout moves a label off a part by itself (2.48.0). Run: python test_studio.py  (SKIP without Chrome/Edge)"""
from __future__ import annotations

import html
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
import studio  # noqa: E402

FAILS = []


def check(what, ok, detail=""):
    print(("PASS  " if ok else "FAIL  ") + what + ("" if ok else "   -> %s" % (detail,)))
    if not ok:
        FAILS.append(what)


# a valve whose name the spec puts right on the tank under it, and a room's name inside it: the layout must move the
# first clear of the tank and keep the second inside its room
GOOD = {"size": [520, 300], "label": "studio test", "parts": [
    {"id": "R", "type": "space", "x": 20, "y": 20, "w": 480, "h": 260, "label": "FUEL PREPARATION ROOM"},
    {"id": "T", "type": "tank", "x": 60, "y": 120, "w": 260, "h": 120, "label": "fuel tank", "value": 0.5},
    {"id": "P", "type": "pipe", "d": "M320 180 H470", "value": 0},
    {"id": "V", "type": "valve", "x": 400, "y": 180, "label": "master valve", "value": 1}],
    "steps": [{"title": "The valve closes", "play": [["V", 0, 600]]}]}
GOOD["parts"].append({"type": "text", "x": 190, "y": 186, "text": "words printed on the tank's own outline", "fixed": True})
BAD = json.loads(json.dumps(GOOD))
GOOD["parts"].pop()

# ---------------------------------------------------------------- 2.49.1: what IGF M06 found in the kit (K1-K13, C11)
# each spec below failed (or lacked the part) in the kit as it was at 2.49.0
SPECS = {
    # K2: tick numbers did not grow with the 12.5 px text growth -> over the bar at 1024 x 768
    "ticks": {"size": [800, 330], "label": "scales with ticks", "parts": [
        {"id": "S", "type": "scale", "x": 40, "y": 60, "orient": "h", "len": 700, "w": 18, "min": 0, "max": 50, "every": 10, "unit": "ppm"},
        {"id": "V", "type": "scale", "x": 40, "y": 180, "h": 130, "w": 18, "min": 0, "max": 2500, "every": 500, "unit": "ppm",
         "reach": 200, "limits": [{"at": 1500, "label": "limit"}]}],
        "steps": [{"title": "x", "play": [["S", 0.5, 500]]}]},
    # K1: marker words and notes are labels the layout places - two markers 50 ppm apart no longer print over each other
    "close": {"size": [640, 330], "label": "two close markers", "parts": [
        {"id": "S", "type": "scale", "x": 50, "y": 300, "orient": "h", "len": 540, "w": 18, "min": 0, "max": 2500, "every": 500, "unit": "ppm",
         "markers": [{"label": "TWA 200 ppm", "note": "8-hour average", "at": 200, "rise": 170},
                     {"label": "STEL 250 ppm", "note": "up to 15 minutes", "at": 250, "rise": 170}]}],
        "steps": [{"title": "a", "play": [["S", 1, 800]]}, {"title": "b", "play": [["S", 2, 800]]}]},
    # K7: a flame burns over a tank and a room by its nature. K8: a box laid over a tank's end is meant to cross it; the
    # name of a narrow room goes outside it instead of poking out of its side
    "fire_space": {"size": [640, 330], "label": "flames and boxes over a tank", "parts": [
        {"id": "T", "type": "tank", "x": 30, "y": 120, "w": 300, "h": 130, "label": "fuel tank", "value": 0.6},
        {"id": "R", "type": "space", "x": 250, "y": 130, "w": 150, "h": 110, "label": "CONNECTION SPACE", "crosses": True},
        {"id": "S", "type": "space", "x": 470, "y": 130, "w": 70, "h": 60, "label": "FUEL PREPARATION ROOM"},
        {"id": "F", "type": "flame", "x": 150, "y": 120, "size": 90, "label": "burning at the tank top"},
        {"id": "G", "type": "flame", "x": 330, "y": 190, "size": 60}],
        "steps": [{"title": "lit", "play": [["R", 1, 600], ["S", 1, 600], ["F", 1, 600], ["G", 1, 600]]}]},
    # K6: the static_charge's own words stood on its hose line at every size
    "static": {"size": [640, 390], "label": "static charge, not bonded and bonded (IGF M06 s05, with its words and callouts)", "parts": [
        {"id": "A", "type": "static_charge", "x": 165, "y": 130, "label": "not bonded"},
        {"id": "B", "type": "static_charge", "x": 475, "y": 130, "bonded": True, "label": "bonded to earth"},
        {"type": "text", "x": 250, "y": 100, "text": "fuel flowing fast", "to": [169, 160]},
        {"type": "text", "x": 80, "y": 335, "text": "isolated metal part", "to": [150, 250]},
        {"type": "text", "x": 300, "y": 345, "text": "a few millijoules light the gas", "to": [245, 230]},
        {"type": "text", "x": 380, "y": 40, "text": "LNG conducts poorly -\nit holds its charge", "to": [195, 185]},
        {"type": "text", "x": 470, "y": 374, "text": "bonded to the hull", "to": [383, 265]}],
        "steps": [{"title": "charge", "play": [["A", 1, 2600, 0, "linear"]]}, {"title": "spark", "play": [["A", 1.1, 600]]},
                  {"title": "bonded", "play": [["A", 1.25, 300], ["B", 1, 2600, 0, "linear"]]}]},
    # K3: "0" crowded a lower limit of 4 - 6 %; K3b the "nums" option
    "range": {"size": [640, 330], "label": "ranges", "parts": [
        {"id": "M", "type": "range_bar", "x": 40, "y": 110, "w": 240, "lel": 4, "uel": 75, "label": "hydrogen in air", "value": 0},
        {"id": "H", "type": "range_bar", "x": 340, "y": 110, "w": 260, "lel": 5, "uel": 15, "nums": [5, 15, 100], "label": "methane in air", "value": 0}],
        "steps": [{"title": "lean", "play": [["M", 2, 800], ["H", 2, 800]]}, {"title": "burns", "play": [["M", 10, 800], ["H", 10, 800]]}]},
}
# for kit_eval: what a part does in the page, read back as numbers and words
EVALS = {
    # K5: words a step brings in; K11: a wrapped alarm keeps its space; K4: the new tank/cloud values; K10: no pipe stub
    "reveal": ({"size": [640, 300], "label": "reveal", "parts": [
        {"id": "T", "type": "text", "x": 320, "y": 40, "text": "the answer", "reveal": True},
        {"id": "C", "type": "text", "x": 200, "y": 70, "text": "vapour space", "to": [100, 190], "reveal": True},
        {"id": "P", "type": "text", "x": 500, "y": 40, "text": "always there"},
        {"id": "K", "type": "tank", "x": 60, "y": 150, "w": 200, "h": 100, "value": 0.5}],
        "steps": [{"title": "show", "play": [["T", 1, 300], ["C", 1, 300]]}]},
        "var g=function(i){return svg.querySelector('[data-kit-id=\"'+i+'\"]');};f.layout(true);f.go(0,true);"
        "var lv=function(){return [].map.call(svg.querySelectorAll('.kit-leaders line'),function(l){return l.style.opacity;});};"
        "var a={T:g('T').style.opacity,C:g('C').style.opacity,P:g('P').style.opacity,L:lv()};f.go(1,true);"
        "return {a:a,b:{T:g('T').style.opacity,C:g('C').style.opacity,L:lv()}};"),
    "log": ({"size": [640, 240], "label": "log", "parts": [
        {"id": "L", "type": "level", "x": 40, "y": 40, "h": 150, "marks": [{"at": 50, "kind": "alarm", "alarm": "HIGH PRESSURE ALARM"}]},
        {"id": "G", "type": "log", "x": 300, "y": 60, "w": 220, "rows": 1}],
        "steps": [{"title": "alarm", "play": [["L", 60, 600]]}]},
        "f.layout(true);f.go(1,true);return [].map.call(svg.querySelectorAll('text.kit-msg'),function(t){return t.textContent;});"),
    "burst": ({"size": [520, 300], "label": "burst", "parts": [
        {"id": "T", "type": "tank", "x": 120, "y": 90, "w": 240, "h": 120, "burst": {"r": 110, "label": "tank ruptures"}, "value": 0.7},
        {"id": "C", "type": "gas_cloud", "x": 20, "y": 20, "w": 200, "h": 100, "from": [60, 70], "drift": [80, 0]}],
        "steps": [{"title": "burst", "play": [["T.burst", 1, 800]]}, {"title": "drift", "play": [["C", 1, 500], ["C.drift", 1, 800]]}]},
        "var q=function(s){return svg.querySelector(s);};f.layout(true);f.go(0,true);"
        "var nm=function(){return [].filter.call(svg.querySelectorAll('[data-kit-id=\"T\"] .kit-lbl'),function(x){return /ruptures/.test(x.textContent);})[0].style.opacity;};"
        "var a={ball:q('.kit-tank-fireball').style.opacity,hot:q('[data-kit-id=\"T\"]').classList.contains('kit-tank-burst'),name:nm()};"
        "f.go(1,true);var b={ball:q('.kit-tank-fireball').style.opacity,tf:q('.kit-tank-fireball').getAttribute('transform'),"
        "hot:q('[data-kit-id=\"T\"]').classList.contains('kit-tank-burst'),name:nm()};f.go(2,true);"
        "return {a:a,b:b,drift:q('[data-kit-id=\"C\"] > g').getAttribute('transform')};"),
    "stub": ({"size": [400, 200], "label": "stub", "parts": [
        {"id": "A", "type": "fire", "kind": "jet", "x": 100, "y": 100, "length": 200, "value": 1},
        {"id": "B", "type": "fire", "kind": "jet", "x": 100, "y": 170, "length": 200, "value": 1, "stub": False}]},
        "return [svg.querySelectorAll('[data-kit-id=\"A\"] .kit-pipe').length,svg.querySelectorAll('[data-kit-id=\"B\"] .kit-pipe').length];"),
    "bar": ({"size": [520, 220], "label": "composition", "parts": [
        {"id": "C", "type": "composition_bar", "x": 30, "y": 90, "w": 460, "label": "natural gas",
         "segments": [{"label": "methane", "pct": 90}, {"label": "ethane", "pct": 6}, {"label": "nitrogen", "pct": 4}]}],
        "steps": [{"title": "two", "play": [["C", 2, 500]]}]},
        "f.layout(true);f.go(1,true);var r=[].map.call(svg.querySelectorAll('.kit-composition-bar-s'),function(x){return +x.getAttribute('width');});"
        "var l=[].map.call(svg.querySelectorAll('.kit-lbl'),function(x){return x.style.opacity;});return {w:r,l:l};"),
    # a value set from outside the steps (a task page's panel valve turned to "closed") survives a layout (a font arriving, a resize)
    "keep": ({"size": [200, 100], "label": "valve", "parts": [{"id": "c", "type": "valve", "x": 100, "y": 50, "size": 22, "state": False, "value": 1}]},
             "f.set(f.parts.c,0);f.layout(true);return [f.parts.c.v,svg.querySelectorAll('g.kit-shut').length];"),
    "drip": ({"size": [420, 240], "label": "drip", "parts": [
        {"id": "D", "type": "drip_tray", "x": 110, "y": 80, "w": 200, "label": "drip tray", "labelAt": "right"}]},
        "f.layout(true);var t=svg.querySelector('[data-kit-id=\"D\"] .kit-lbl text');return +t.getAttribute('x');"),
}


def kit_eval(spec, js, width=640):
    """the spec drawn by the factory's kit.js in a page `width` px wide; `js` (a function body, with f = the figure and svg)
    runs once it is up and returns what it found, as JSON"""
    exe = studio.find_browser()
    tmp = tempfile.mkdtemp(prefix="kit_eval_")
    try:
        css = "".join('<link rel="stylesheet" href="%s">' % studio.uri(os.path.join(d, n)) for d, n in
                      ((studio.TOKENS, "gb_tokens.css"), (studio.KIT, "kit.css")) if os.path.isfile(os.path.join(d, n)))
        run = ("<script>setTimeout(function(){var svg=document.querySelector('svg[data-kit]'),f=svg.__kit,o;"
               "try{o=(function(f,svg){%s})(f,svg);}catch(e){o={error:String(e)};}"
               "var p=document.createElement('pre');p.id='o';p.textContent=JSON.stringify(o);document.body.appendChild(p);},500);</script>" % js)
        page = os.path.join(tmp, "eval.html")
        io.open(page, "w", encoding="utf-8").write(
            '<!DOCTYPE html><html><head><meta charset="utf-8">%s</head><body style="margin:0"><div class="kit-screen" style="width:%dpx">'
            '<svg data-kit="#s"></svg></div><script type="application/json" id="s">%s</script><script src="%s"></script>%s</body></html>'
            % (css, width, json.dumps(spec).replace("</", "<\\/"), studio.uri(os.path.join(studio.KIT, "kit.js")), run))
        ok, dom = studio.chrome(exe, studio.uri(page), (width + 40, 700), os.path.join(tmp, "p")).wait(60)
        m = re.search(r'<pre id="o">(.*?)</pre>', dom or "", re.S)
        return json.loads(html.unescape(m.group(1))) if m else None
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def png_size(path):
    with io.open(path, "rb") as fh:
        head = fh.read(24)
    return int.from_bytes(head[16:20], "big"), int.from_bytes(head[20:24], "big")


def findings(r, drop=("empty",)):
    """every finding but the ones named, at every size - the studio judges 1280 and only states 1024; these specs are held to both"""
    return [p for p in studio.problems(r) if p[2] not in drop]


def main():
    if not studio.find_browser():
        print("SKIP - no Chrome or Edge (set CF_BROWSER)")
        return 0
    tmp = tempfile.mkdtemp(prefix="kit_studio_test_")
    try:
        good, bad = os.path.join(tmp, "good.kit.json"), os.path.join(tmp, "bad.kit.json")
        io.open(good, "w", encoding="utf-8").write(json.dumps(GOOD))
        io.open(bad, "w", encoding="utf-8").write(json.dumps(BAD))
        r, why = studio.run(good, panel="two-col", out=os.path.join(tmp, "shots"))
        check("the studio runs", r is not None, why)
        if r:
            text, probs = studio.summary(r, good)
            check("a well-made figure is clean at 1280 x 800, every step", not probs, text)
            big = r["sizes"].get("1280x800", {})
            check("both sizes are drawn", set(r["sizes"]) == {"1280x800", "1024x768"}, sorted(r["sizes"]))
            check("each step is audited (2 states)", len(big.get("states", [])) == 2, big.get("states"))
            rep = big.get("report") or {}
            check("the layout reports what it did", {"scale", "up", "labels", "moved", "unplaced", "theme"} <= set(rep), rep)
            check("on a deck's dark panel the figure is dark", rep.get("theme") == "dark", rep.get("theme"))
            check("no word under 12.5 px", (rep.get("minTextPx") or 0) >= 12.45, rep.get("minTextPx"))
            check("a screenshot per size", all(os.path.isfile(v.get("shot") or "") for v in r["sizes"].values()),
                  [v.get("shot") for v in r["sizes"].values()])
        r2, _ = studio.run(good, panel="task", sizes=((1280, 800),), out=os.path.join(tmp, "shots2"))
        check("on a task page the figure is the deck's dark screen too (2.46.0 gb_answer.css) - the kit sees it", r2 and
              (r2["sizes"]["1280x800"].get("report") or {}).get("theme") == "dark")
        light = os.path.join(tmp, "light.kit.json")
        io.open(light, "w", encoding="utf-8").write(json.dumps(dict(GOOD, theme="light")))
        r4, _ = studio.run(light, panel="task", sizes=((1280, 800),), out=os.path.join(tmp, "shots4"))
        _, p4 = studio.summary(r4, light) if r4 else (None, ["no run"])
        check("\"theme\": \"light\" takes the light colours, and it is clean on them (contrast by construction)", r4 and
              (r4["sizes"]["1280x800"].get("report") or {}).get("theme") == "light" and not p4, p4)
        r3, _ = studio.run(bad, panel="two-col", sizes=((1280, 800),), out=os.path.join(tmp, "shots3"))
        _, p3 = studio.summary(r3, bad) if r3 else (None, [])
        check("words fixed on a line are found (text zone)", any(c == "text zone" for _, _, c, _, _ in p3), p3)

        # ------------------------------------------------------------ 2.49.1 - IGF M06's kit and checker problems
        runs = {}
        for name, spec in SPECS.items():
            f = os.path.join(tmp, name + ".kit.json")
            io.open(f, "w", encoding="utf-8").write(json.dumps(spec))
            runs[name] = studio.run(f, panel="two-col", out=os.path.join(tmp, "shots_" + name))[0]
            check("%s: the studio runs" % name, runs[name] is not None)
        rep = lambda name, size="1280x800": (runs[name]["sizes"].get(size) or {}).get("report") or {}
        if all(runs.values()):
            check("K2 scale ticks: numbers keep clear of the bar and their ticks as the type grows (1280 and 1024)",
                  not findings(runs["ticks"]), findings(runs["ticks"]))
            check("K1 scale markers: words, notes and a limit's name are labels the layout places (1 limit + 2 markers = 3, 2 markers = 2)",
                  rep("ticks")["labels"] == 1 and rep("close")["labels"] == 2, (rep("ticks"), rep("close")))
            check("K1 two markers 50 ppm apart: their words are moved clear of each other, at both sizes",
                  not findings(runs["close"]) and rep("close")["moved"] >= 1, (findings(runs["close"]), rep("close")))
            check("K7 + K8: a flame over a tank and a room, a box over a tank's end (crosses), the name of a narrow room: clean at both sizes",
                  not findings(runs["fire_space"]), findings(runs["fire_space"]))
            check("K6 static_charge: its label and state stand above the hose line, at both sizes",
                  not [p for p in findings(runs["static"]) if "pipe" in p[3] or "kit-pipe" in p[4]],
                  findings(runs["static"]))
            check("K3 range_bar: no \"0\" crowding a lower limit of 4 or 5 %, and \"nums\" names the numbers (1280 and 1024)",
                  not [p for p in findings(runs["range"]) if "kit-tick" in p[3]], findings(runs["range"]))

        v = kit_eval(*EVALS["reveal"])
        check("K5 text with \"reveal\" is not drawn at rest, and fades in with its value; a plain text always stands",
              v and v["a"]["T"] == "0" and v["a"]["C"] == "0" and v["a"]["P"] == "" and v["b"]["T"] == "1" and v["b"]["C"] == "1", v)
        check("K5 a revealed callout's leader line is hidden at rest and shown with it",
              v and v["a"]["L"] and set(v["a"]["L"]) == {"0"} and set(v["b"]["L"]) == {"1"}, v)
        v = kit_eval(*EVALS["log"])
        check("K11 a wrapped alarm keeps its space (\"HIGH PRESSURE ALARM\", not \"HIGH PRESSUREALARM\")",
              v and any(m == "HIGH PRESSURE ALARM" for m in v), v)
        v = kit_eval(*EVALS["burst"])
        check("K4 tank \"burst\": no fireball at rest, a fireball and a red shell once \"<id>.burst\" has played",
              v and v["a"]["ball"] == "0" and not v["a"]["hot"] and v["b"]["ball"] == "1" and v["b"]["hot"]
              and "scale(1.000)" in v["b"]["tf"] and v["a"]["name"] == "0" and v["b"]["name"] == "1", v)
        check("K4 gas_cloud \"drift\": \"<id>.drift\" carries the cloud its distance", v and v["drift"] == "translate(80.0 0.0)", v)
        v = kit_eval(*EVALS["stub"])
        check("K10 a jet fire draws its pipe stub unless \"stub\": false", v == [1, 0], v)
        v = kit_eval(*EVALS["bar"])
        check("K4 composition_bar: segment k fills while the value goes k to k+1, its name shows once it is half drawn",
              v and v["w"][0] > 300 and v["w"][1] > 20 and v["w"][2] == 0 and v["l"][:3] == ["1", "1", "0"], v)
        v = kit_eval(*EVALS["keep"])
        check("a value set from outside the steps survives a layout (the task page's panel valve stayed closed only by luck)", v == [0, 1], v)
        v = kit_eval(*EVALS["drip"])
        check("K9 drip_tray: \"labelAt\" puts the name beside the pan", v is not None and v > 200, v)

        # K13: one browser run draws every step - a contact sheet, as wide as the real slide's panels
        sheet_spec = os.path.join(tmp, "sheet.kit.json")
        io.open(sheet_spec, "w", encoding="utf-8").write(json.dumps(SPECS["close"]))
        rs, _ = studio.run(sheet_spec, panel="two-col", sizes=((1280, 800),), step="all", out=os.path.join(tmp, "sheet"))
        shot = ((rs or {}).get("sizes", {}).get("1280x800") or {}).get("shot") or ""
        check("K13 --step all: one contact sheet of every step (rest + 2 steps = 3 panels) in one picture",
              shot.endswith("_all.png") and os.path.isfile(shot) and png_size(shot)[0] >= 1300 and png_size(shot)[1] >= 700, shot)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("\n%s" % ("ALL PASS" if not FAILS else "%d FAILED" % len(FAILS)))
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
