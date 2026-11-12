#!/usr/bin/env python3
"""test_check_kit3d.py - check_kit3d.py does what its docstring says. Run: python -I test_check_kit3d.py"""
from __future__ import annotations

import copy
import io
import json
import os
import shutil
import sys
import tempfile
from contextlib import redirect_stdout

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import check_kit3d as ck  # noqa: E402

FAILS = []


def check(what, ok, detail=""):
    print(("PASS  " if ok else "FAIL  ") + what + ("" if ok else "   -> %s" % (detail,)))
    if not ok:
        FAILS.append(what)


TYPES, why = ck.read_catalog()
check("the catalogue is read from kit3d.js", bool(TYPES) and "tank_c" in TYPES, why)

GOOD = {
    "label": "A fuel tank with a gas pipe leaving it",
    "units": "m",
    "view": {"az": 24, "el": 23},
    "parts": [
        {"id": "tank", "type": "tank_c", "at": [0, 5.2, 0], "r": 3.4, "len": 14, "cut": True, "fill": 0.6},
        {"id": "pipe", "type": "pipe_dw", "at": [0, 0, 0], "subs": {"inner": "gas_in"}},
        {"id": "hull", "type": "hull", "at": [0, 0, 0], "pick": False,
         "spaces": [{"id": "ds", "name": "Double side"}], "bottom_id": "db"},
        {"id": "v1", "type": "valve", "at": [2, 9.5, 0]},
        {"id": "box", "type": "box", "at": [5, 0, 0], "size": [1, 1, 1], "pick": False},
    ],
    "groups": {"leak": ["pipe", "v1"]},
    "states": {"pipe.cut": 0},
}
GOOD["labels"] = [
    {"part": "tank", "text": "Fuel tank", "at": [0, 8.6, 0]},
    {"part": "tank_liquid", "text": "LNG liquid", "tone": "amber"},
    {"part": "pipe", "text": "Gas pipe"},
    {"part": "gas_in", "text": "Gas inside", "when": "pipe.cut > 0.5"},
    {"part": "leak", "text": "The leak", "when": "!pipe.cut"},
    {"part": "ds", "text": "Double side"},
    {"part": "v1", "text": "Valve", "steps": [0, 1]},
    {"text": "A free point", "at": [1, 1, 1]},
]
GOOD["steps"] = [
    {"view": {"az": 24, "el": 23}},
    {"view": {"az": 17, "el": 17, "frame": ["pipe", "leak"]}, "state": {"pipe.cut": 1}, "select": "pipe",
     "labels": ["pipe", "gas_in", "v1"], "line": [2, 3]},
]
GOOD["controls"] = [
    {"text": "Cut the pipe open", "state": {"pipe.cut": 1}, "view": {"az": 17, "el": 17, "frame": ["pipe"]}},
    {"text": "Stop a leak", "select": "leak"},
    {"text": "Step 2", "step": 1},
]


def run(spec):
    return ck.check_spec(spec, TYPES)


def variant(fn):
    s = copy.deepcopy(GOOD)
    fn(s)
    return s


def problem(what, fn, needle):
    p, _ = run(variant(fn))
    check("caught: " + what, any(needle in x for x in p), p)


def note(what, fn, needle):
    p, n = run(variant(fn))
    check("note: " + what, any(needle in x for x in n) and not p, (p, n))


# ---------------------------------------------------------------- a good spec
p, n = run(GOOD)
check("a good spec has no problems", p == [], p)
check("a good spec has no notes", n == [], n)

# ---------------------------------------------------------------- problems (exit 1)
problem("no label", lambda s: s.pop("label"), "no \"label\"")
problem("no parts list", lambda s: s.pop("parts"), "no \"parts\"")
problem("an empty parts list", lambda s: s.update(parts=[]), "no \"parts\"")
problem("a part with no type", lambda s: s["parts"][3].pop("type"), "type None")
problem("a part of an unknown type", lambda s: s["parts"][3].update(type="warp_core"), "warp_core")
# the same id on two entries is one part made of both (a space and its pipes, IGF M01 'tcs') - not a problem
p, _ = run(variant(lambda s: s["parts"][4].update(id="v1")))
check("a repeated id is one part, no problem", not any("twice" in x for x in p), p)
problem("a part 'at' with two numbers", lambda s: s["parts"][0].update(at=[1, 2]), "3 numbers")
problem("a part 'at' with a string in it", lambda s: s["parts"][0].update(at=[1, "2", 3]), "3 numbers")
problem("a label 'at' that is not 3 numbers", lambda s: s["labels"][0].update(at=[1, 2, 3, 4]), "3 numbers")
problem("a label with no text", lambda s: s["labels"][2].pop("text"), "no \"text\"")
problem("a label of a part that is not there", lambda s: s["labels"][2].update(part="ghost"), "'ghost'")
problem("a label with neither part nor at", lambda s: s["labels"].append({"text": "Lost"}), "neither")
problem("a group member that does not exist", lambda s: s["groups"].update(leak=["pipe", "nope"]), "'nope'")
problem("a step state that does not exist", lambda s: s["steps"][1].update(state={"pipe.shut": 1}), "'pipe.shut'")
problem("a state on a part whose type has none", lambda s: s["steps"][1].update(state={"v1.cut": 1}), "'v1.cut'")
problem("a control state that does not exist", lambda s: s["controls"][0].update(state={"tank.cut": 1}), "'tank.cut'")
problem("a top-level state that does not exist", lambda s: s["states"].update({"valve.shut": 1}), "'valve.shut'")
problem("a step view.frame naming nothing", lambda s: s["steps"][1]["view"].update(frame=["pipe", "zzz"]), "'zzz'")
problem("a step select naming nothing", lambda s: s["steps"][1].update(select="zzz"), "'zzz'")
problem("a step labels entry naming no part", lambda s: s["steps"][1].update(labels=["pipe", "zzz"]), "'zzz'")
problem("a step line that is not an int", lambda s: s["steps"][1].update(line="two"), "\"line\"")
problem("a step line list with a string", lambda s: s["steps"][1].update(line=[1, "x"]), "\"line\"")
problem("a control that does nothing", lambda s: s["controls"].append({"text": "Idle"}), "does nothing")
problem("a control step out of range", lambda s: s["controls"][2].update(step=5), "out of range")
problem("a control select naming nothing", lambda s: s["controls"][1].update(select="zzz"), "'zzz'")
problem("a label 'when' that is not well formed", lambda s: s["labels"][3].update(when="pipe.cut >> 3"), "\"when\"")
problem("a label 'when' with a word for a number", lambda s: s["labels"][3].update(when="pipe.cut > high"), "\"when\"")
problem("a label 'when' naming an unknown state", lambda s: s["labels"][3].update(when="!pipe.open"), "'pipe.open'")
problem("a view az that is not a number", lambda s: s["view"].update(az="north"), "az must be a number")
problem("a step view el that is not a number", lambda s: s["steps"][0]["view"].update(el=None), "el must be a number")

# the sub-part rules
LQ = lambda fill: variant(lambda s: (s["parts"][0].update(fill=fill) if fill is not None else s["parts"][0].pop("fill")))
p, _ = run(LQ(None))
check("a tank with no fill makes no liquid sub-part, so a label of it is caught", any("tank_liquid" in x for x in p), p)
p, _ = run(LQ(0.4))
check("a tank with fill > 0 makes 'tank_liquid'", not any("tank_liquid" in x for x in p), p)
p, _ = run(variant(lambda s: s["parts"][0].update(type="tank_prism", layers=[{"id": "ins1"}, {"id": "ins2"}])
                   or s["labels"].append({"part": "ins2", "text": "Insulation"})))
check("tank_prism 'layers' with an id are sub-parts (subs_from)", not any("ins2" in x for x in p), p)
p, _ = run(variant(lambda s: s["labels"].append({"part": "pipe_annulus", "text": "Annulus"})))
check("a pipe_dw sub-part without a name in 'subs' is '<id>_<sub>'", not any("pipe_annulus" in x for x in p), p)
p, _ = run(variant(lambda s: s["labels"].append({"part": "pipe_inner", "text": "Inner"})))
check("a pipe_dw sub-part given another name in 'subs' is no longer '<id>_inner'", any("pipe_inner" in x for x in p), p)
p, _ = run(variant(lambda s: s["labels"].append({"part": "db", "text": "Double bottom"})))
check("a hull 'bottom_id' is a sub-part", not any("'db'" in x for x in p), p)

# ---------------------------------------------------------------- notes (exit 0)
note("a part nobody names", lambda s: s["parts"].append({"id": "lonely", "type": "pump", "at": [9, 0, 0]}),
     "a part nobody names")
p, n = run(variant(lambda s: s["parts"].append({"id": "lonely", "type": "pump", "at": [9, 0, 0]})))
check("a part nobody names is a note, not a problem", p == [] and any("'lonely'" in x for x in n), (p, n))
p, n = run(GOOD)
check("pick:false parts (hull, box) are not reported as nobody-names", not any("'box'" in x or "'hull'" in x for x in n), n)
note("a step showing more than 9 labels",
     lambda s: s["labels"].extend({"part": "tank", "text": "T%d" % i, "at": [i * 1.2 - 6, 8.6, -1.5]} for i in range(10)), "step 0 shows")
note("a step showing fewer than 2 labels", lambda s: s["steps"][1].update(labels=["pipe"]), "step 1 shows 1 label")
note("a scene with no steps and no controls", lambda s: (s.pop("steps"), s.pop("controls")), "one view only")
note("units missing", lambda s: s.pop("units"), "\"units\" missing")

# ---------------------------------------------------------------- files, the CLI, exit codes
tmp = tempfile.mkdtemp(prefix="kit3d_test_")


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with io.open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)
    return path


def cli(argv, kit=ck.KIT):
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = ck.main(argv, kit)
    return code, buf.getvalue()


try:
    good = write(os.path.join(tmp, "good.kit3d.json"), json.dumps(GOOD))
    bad = write(os.path.join(tmp, "bad.kit3d.json"), json.dumps(variant(lambda s: s["parts"][3].update(type="warp"))))
    junk = write(os.path.join(tmp, "junk.kit3d.json"), "{ not json")
    arr = write(os.path.join(tmp, "arr.kit3d.json"), "[1, 2]")
    noteonly = write(os.path.join(tmp, "note.kit3d.json"), json.dumps(variant(lambda s: s.pop("units"))))

    code, out = cli(["spec", good])
    check("spec: a good file exits 0 and says clean", code == 0 and "clean" in out, (code, out))
    code, out = cli(["spec", good, bad])
    check("spec: one bad file exits 1 and names it", code == 1 and "bad.kit3d.json" in out, (code, out))
    code, out = cli(["spec", junk])
    check("spec: a file that is not JSON exits 1", code == 1 and "not JSON" in out, (code, out))
    code, out = cli(["spec", arr])
    check("spec: JSON that is not an object exits 1", code == 1 and "object" in out, (code, out))
    code, out = cli(["spec", os.path.join(tmp, "nowhere.kit3d.json")])
    check("spec: a file that is not there exits 2", code == 2, (code, out))
    code, out = cli(["spec", noteonly])
    check("spec: a note alone exits 0 and is shown", code == 0 and "note" in out and "units" in out, (code, out))
    code, out = cli(["spec", noteonly, "--strict"])
    check("spec --strict: a note alone exits 1", code == 1, (code, out))
    code, out = cli(["spec", bad, "--json"])
    rep = json.loads(out)
    check("--json prints a machine report", code == 1 and rep["ok"] is False and rep["problems"]
          and rep["problems"][0]["file"] == "bad.kit3d.json", (code, out))
    code, out = cli(["spec", noteonly, "--json"])
    rep = json.loads(out)
    check("--json: a note is listed under notes, exit 0", code == 0 and rep["ok"] and rep["notes"], (code, out))

    # a module's own part type (kit3d_parts.js) is a type
    custom = variant(lambda s: s["parts"].append({"id": "dock", "type": "dock_crane", "at": [1, 1, 1]}))
    custom["labels"].append({"part": "dock", "text": "Crane"})
    cpath = write(os.path.join(tmp, "custom.kit3d.json"), json.dumps(custom))
    code, _ = cli(["spec", cpath])
    check("a type the kit lacks is refused", code == 1)
    pj = write(os.path.join(tmp, "kit3d_parts.js"), "KIT3D.define('dock_crane', function (p) {});\n")
    code, out = cli(["spec", cpath, "--parts", pj])
    check("a type a module's kit3d_parts.js defines is accepted", code == 0, (code, out))

    # ... and its states and sub-parts are the ones its define makes (a needle that moves, a stain that grows)
    pj = write(os.path.join(tmp, "kit3d_parts.js"), """
  window.KIT3D.define('gauge', function (k, p) {
    var self = k.cur, id = self.id;
    k.sub(self.id + '_dial', { pick: true, name: 'Dial' });
    k.state(self.id + '.needle', 0, function (v) {});
    k.state(id + '.alarm', 0, function (v) {});
    (p.sensors || []).forEach(function (sn) { k.sub(sn.id, { pick: true }); });
  }, { family: 'equipment', at: 'base centre', about: 'a gauge' });
  KIT3D.define("det_tube", function (k, p) {
    k.state(k.cur.id + ".stain", 0, function (v) {});
  }, {"family": "equipment"});
""")
    lt = ck.local_types(pj)
    check("local_types reads each define's states, sub-parts and family",
          lt.get("gauge", {}).get("states") == ["needle", "alarm"] and lt["gauge"].get("subs") == ["dial"]
          and lt["gauge"].get("family") == "equipment" and lt.get("det_tube", {}).get("states") == ["stain"], lt)
    moving = variant(lambda s: s["parts"].extend([
        {"id": "g", "type": "gauge", "at": [1, 1, 1], "sensors": [{"id": "g_o2"}]},
        {"id": "dt", "type": "det_tube", "at": [2, 1, 1]}]))
    moving["labels"] += [{"part": "g_dial", "text": "Dial"}, {"part": "g_o2", "text": "Oxygen sensor"},
                         {"part": "dt", "text": "Tube", "when": "dt.stain > 0.5"}]
    moving.setdefault("steps", []).append({"state": {"g.needle": 0.7, "g.alarm": 1, "dt.stain": 1}})
    mpath = write(os.path.join(tmp, "moving.kit3d.json"), json.dumps(moving))
    code, out = cli(["spec", mpath, "--parts", pj])
    check("a module's own part type moves: its states, sub-parts and listed sub-parts are accepted", code == 0, (code, out))
    moving["steps"][-1]["state"]["g.wobble"] = 1
    write(mpath, json.dumps(moving))
    code, out = cli(["spec", mpath, "--parts", pj])
    check("... a state its define does not make is still refused", code == 1 and "g.wobble" in out, (code, out))

    # an unreadable catalogue
    nokit = os.path.join(tmp, "nokit")
    os.makedirs(nokit)
    code, out = cli(["spec", good], kit=nokit)
    check("no kit3d.js: exit 2 with the reason", code == 2 and "catalogue" in out, (code, out))
    write(os.path.join(nokit, "kit3d.js"), "var CATALOG = {};\n")
    code, out = cli(["spec", good], kit=nokit)
    check("a kit3d.js with no catalogue block: exit 2", code == 2 and "@@CATALOG@@" in out, (code, out))

    # ------------------------------------------------------------ module mode
    # a stand-in factory: the real engine (for its catalogue), a stylesheet
    fac = os.path.join(tmp, "factory")
    os.makedirs(fac)
    shutil.copy(os.path.join(ck.KIT, "kit3d.js"), os.path.join(fac, "kit3d.js"))
    write(os.path.join(fac, "kit3d.css"), ".kit3d-stage{}\n")
    mod = os.path.join(tmp, "M03")
    figs = os.path.join(tmp, "figures", "M03")
    write(os.path.join(figs, "s05.kit3d.json"), json.dumps(GOOD))
    DECK = '<div class="kit3d-stage" data-stage data-3d data-kit3d="#k3-s05"></div>'
    write(os.path.join(mod, "presentation", "index.html"), "<html>%s</html>" % DECK)
    assets = os.path.join(mod, "presentation", "assets")

    code, out = cli(["module", mod, "--figures", figs], kit=fac)
    check("module: scene in the deck but no kit3d.js: exit 1, says so",
          code == 1 and "kit3d.js is not in the module" in out and "three.min.js" in out, (code, out))
    os.makedirs(assets, exist_ok=True)
    shutil.copy(os.path.join(fac, "kit3d.js"), os.path.join(assets, "kit3d.js"))
    shutil.copy(os.path.join(fac, "kit3d.css"), os.path.join(assets, "kit3d.css"))
    code, out = cli(["module", mod, "--figures", figs], kit=fac)
    check("module: engine and css there, three.min.js missing: exit 1", code == 1 and "three.min.js" in out
          and "kit3d.js" not in out.replace("three.min.js", ""), (code, out))
    write(os.path.join(assets, "vendor", "three.min.js"), "/* three */")
    code, out = cli(["module", mod, "--figures", figs], kit=fac)
    check("module: everything there and equal: exit 0", code == 0 and "clean" in out, (code, out))
    write(os.path.join(assets, "kit3d.css"), ".kit3d-stage{color:red}\n")
    code, out = cli(["module", mod, "--figures", figs], kit=fac)
    check("module: a changed copy of kit3d.css is caught byte for byte", code == 1 and "kit3d.css is not the factory's" in out,
          (code, out))
    shutil.copy(os.path.join(fac, "kit3d.css"), os.path.join(assets, "kit3d.css"))
    with open(os.path.join(assets, "kit3d.js"), "ab") as f:
        f.write(b"\n// edited in a module\n")
    code, out = cli(["module", mod, "--figures", figs], kit=fac)
    check("module: a changed copy of kit3d.js is caught", code == 1 and "kit3d.js is not the factory's" in out, (code, out))
    shutil.copy(os.path.join(fac, "kit3d.js"), os.path.join(assets, "kit3d.js"))

    write(os.path.join(figs, "s06.kit3d.json"), json.dumps(variant(lambda s: s.pop("parts"))))
    code, out = cli(["module", mod, "--figures", figs], kit=fac)
    check("module: a bad spec in the figures folder is found", code == 1 and "s06.kit3d.json" in out, (code, out))

    # a module with a figures folder but no 3D scene in the deck: only the specs are checked
    mod2 = os.path.join(tmp, "M04")
    write(os.path.join(mod2, "presentation", "index.html"), "<html>2D only</html>")
    figs2 = os.path.join(tmp, "figures", "M04")
    write(os.path.join(figs2, "s01.kit3d.json"), json.dumps(GOOD))
    code, out = cli(["module", mod2, "--figures", figs2], kit=fac)
    check("module: no data-kit3d in the deck: assets are not required, the specs still are checked",
          code == 0 and "assets checked" not in out, (code, out))
    code, out = cli(["module", mod2], kit=fac)
    check("module: no specs and no 3D scene: exit 2, nothing to check", code == 2, (code, out))
    code, out = cli(["module", os.path.join(tmp, "nope")], kit=fac)
    check("module: a folder that is not there: exit 2", code == 2, (code, out))
finally:
    shutil.rmtree(tmp, ignore_errors=True)

# 2.72.0 - a part that stands on the open deck is never below it; "on": "<hull>.deck" places it there
print("\n-- 2.72.0: deck parts on the deck")
HULL = {"id": "H", "type": "hull", "at": [0, 0, 0], "x": [-10, 10], "half": 6, "top": 9}
low = {"label": "t", "units": "m", "parts": [HULL, {"id": "V", "type": "vent_mast", "at": [2, 4, 0], "h": 10}]}
check("a vent mast whose foot is below the hull's deck (inside the hull) fails",
      any("below the deck" in x for x in run(low)[0]), run(low)[0])
ok = {"label": "t", "units": "m", "parts": [HULL, {"id": "V", "type": "vent_mast", "on": "H.deck", "at": [2, 0, 0], "h": 10}]}
check("the same mast \"on\": \"H.deck\" passes", not [x for x in run(ok)[0] if "deck" in x])
check("deck_level reads the hull's deck as kit3d.js does (top 9 over its origin)", ck.deck_level(HULL) == 9)
js = io.open(os.path.join(os.path.dirname(HERE), "kit3d.js"), encoding="utf-8").read()
check("kit3d.js places a part \"on\" a hull's deck before it builds it", "function deckRelation" in js and "deckRelation(list, list[i], S)" in js)

# a step's "line" is the slide's line counted from 1 (M01 s01: "line": 0 for the first line - the highlight a step ahead of
# the words on about 12 slides, and nothing caught it)
print("\n-- step lines from 1, up to the slide's last line")
zero = copy.deepcopy(GOOD)
zero["steps"] = [{"view": {"az": 24, "el": 23}}, {"select": "pipe", "line": 0}, {"select": "tank", "line": 1}]
check("spec: a step lighting line 0 fails - the deck counts lines from 1",
      any("\"line\" 0 is not a line" in x and "never 0" in x for x in run(zero)[0]), run(zero)[0])
check("spec: lines from 1 pass", not [x for x in run(GOOD)[0] if "line" in x], run(GOOD)[0])
four = {"steps": [{"view": {}}, {"line": 0}, {"line": 1}]}
lp = ck.line_problems(four, 4)
check("a slide of 4 lines: line 0 is named, and lines 2-4 after the last one lit (the scene standing still)",
      len(lp) == 2 and "step 1 lights line 0" in lp[0] and "lines 2, 3, 4 come after line 1" in lp[1], lp)
check("... a line past the slide's last fails", any("lights line 5" in x for x in ck.line_problems({"steps": [{"line": 5}]}, 4)))
check("... steps lighting 1..4 pass; a line no step lights before the last is the deck's own stop",
      not ck.line_problems({"steps": [{"line": 1}, {"line": 2}, {"line": 4}]}, 4))
check("... steps lighting no line pass (the deck walks the lines with them)", not ck.line_problems({"steps": [{}, {"view": {}}]}, 4))
page = ('<section class="slide" id="s01"><div data-kit3d="#k3-s01"></div><script type="application/json" id="k3-s01">%s</script>'
        '<p data-i="1">a</p><p data-i="2">b</p><p data-i="3">c</p><p data-i="4">d</p></section>'
        '<section class="slide" id="s02"><p data-i="1">a</p></section>' % json.dumps(dict(GOOD, steps=four["steps"])))
dl = ck.deck_line_problems(page)
check("deck: each scene against its own slide's lines", [x[0] for x in dl] == ["s01", "s01"], dl)
tmp2 = tempfile.mkdtemp(prefix="ck3l_")
try:
    m = os.path.join(tmp2, "M01")
    write(os.path.join(m, "presentation", "index.html"), page)
    code, out = cli(["module", m])
    check("module: the deck's step lines are refused (exit 1) beside its assets", code == 1 and "lights line 0" in out, out)
finally:
    shutil.rmtree(tmp2, ignore_errors=True)

# portable foam: the parts join by their ports - never set side by side by hand - and the kit's parts, not stand-ins
print("\n-- portable foam: joined by ports, the kit's own parts")
FOAM = json.loads(io.open(os.path.join(os.path.dirname(HERE), "examples", "m16_foam.kit3d.json"), encoding="utf-8").read())
check("the foam rig example is clean (hydrant, hose, inductor, branch pipe, container joined by their ports)", run(FOAM) == ([], []), run(FOAM))
for t, ports in (("foam_inductor", {"in", "out", "pickup"}), ("foam_branch_pipe", {"in", "out"}), ("foam_container", {"mouth"}),
                 ("fire_hydrant", {"out"}), ("hose", {"start", "end"})):
    check("the catalogue gives %s its ports %s" % (t, sorted(ports)), ports <= set(TYPES.get(t, {}).get("ports") or []), TYPES.get(t))
check("the inductor's states cut and on, its sub-parts valve, pick-up tube and venturi are known",
      {"cut", "on"} <= set(TYPES["foam_inductor"].get("states") or []) and
      {"valve", "pickup", "venturi"} <= set(TYPES["foam_inductor"].get("subs") or []), TYPES["foam_inductor"])


def foam(fn):
    s = copy.deepcopy(FOAM)
    fn(s)
    return run(s)[0]


def part(s, pid):
    return [q for q in s["parts"] if q.get("id") == pid][0]


p = foam(lambda s: (part(s, "br").pop("connect"), part(s, "br").update(at=[0.4, 0.14, 0])))
check("caught: a branch pipe set beside the inductor by hand, joined to nothing (a gap between them)",
      any("branch pipe br is joined to nothing" in x for x in p) and any("inductor ind: its outlet is joined to nothing" in x for x in p), p)
p = foam(lambda s: part(s, "hose").update(to="ind.inlet"))
check("caught: a port the part does not have (ind.inlet - an inductor has in, out, pickup)", any("has no port 'inlet'" in x for x in p), p)
p = foam(lambda s: part(s, "br").update(connect="nope.out"))
check("caught: a joint to a part that is not there", any("names no part's port" in x for x in p), p)
p = foam(lambda s: part(s, "ind").pop("pickup"))
check("caught: an inductor's pick-up tube that goes nowhere beside a container", any("pick-up tube goes nowhere" in x for x in p), p)
p = foam(lambda s: part(s, "hose").pop("to"))
check("caught: an inductor whose inlet no hose reaches", any("inductor ind: its inlet is joined to nothing" in x for x in p), p)
STAND = {"label": "t", "units": "m", "parts": [
    {"id": "hydrant", "type": "cylinder", "axis": "y", "r": 0.1, "len": 0.8, "at": [-2, 0.4, 0], "mat": "red"},
    {"id": "inductor", "type": "cylinder", "axis": "x", "r": 0.07, "len": 0.4, "at": [0, 0.12, 0]},
    {"id": "branch", "type": "cylinder", "axis": "x", "r": 0.05, "len": 0.8, "at": [0.6, 0.12, 0]},
    {"id": "container", "type": "cylinder", "axis": "y", "r": 0.16, "len": 0.3, "at": [0, 0.15, 1]}],
    "labels": [{"part": "hydrant", "text": "Fire hydrant"}, {"part": "inductor", "text": "Inductor (foam ejector)"},
               {"part": "branch", "text": "Foam branch pipe"}, {"part": "container", "text": "20-litre foam container"}]}
p = run(STAND)[0]
check("caught: cylinders standing in for the hydrant, the inductor, the branch pipe and the container - each named with its kit part",
      all(any(n in x and k in x for x in p) for n, k in (("hydrant", "fire_hydrant"), ("inductor", "foam_inductor"),
                                                          ("branch", "foam_branch_pipe"), ("container", "foam_container"))), p)
check("a cylinder named for something the kit does not draw is no stand-in",
      not run(dict(STAND, labels=[{"part": "branch", "text": "Spare pipe"}]))[0])
js = io.open(os.path.join(os.path.dirname(HERE), "kit3d.js"), encoding="utf-8").read()
check("kit3d.js builds the parts a joint names first, then joins them (joinOrder, joinRelation)",
      "joinOrder(list, S)" in js and "joinRelation(inRelation(list, deckRelation(list, list[i], S), S), S)" in js)

# ---------------------------------------------------------------- a gas carrier's hull and tanks (factory trial M01, 3D review)
print("\n-- gas carriers: hulls, tanks, what is measured, what a label names")
GAS = json.loads(io.open(os.path.join(os.path.dirname(HERE), "examples", "m01_gas_carriers.kit3d.json"), encoding="utf-8").read())
check("the gas carrier example is clean (five sections, every tank \"in\" its hull, every label on a hull's or a tank's own sub-part)",
      run(GAS) == ([], []), run(GAS))


def scene(parts, labels=(), steps=None):
    s = {"label": "a hull section", "units": "m", "view": {"az": 24, "el": 18}, "parts": parts, "labels": list(labels)}
    if steps is not None:
        s["steps"] = steps
    return run(s)[0]


def caught(what, p, needle):
    check("caught: " + what, any(needle in x for x in p), p)


H = {"id": "h", "type": "hull", "pick": False, "x": [-9, 9], "half": 6, "bottom": 0, "floor": 1.2, "top": 9}
HD = dict(H, double=1.5, hopper=[2, 2], topwing=[2, 2])
caught("a membrane tank standing free in its hold (M01 s08, s11)",
       scene([H, {"id": "m", "type": "tank_prism", "at": [0, 5, 0], "size": [16, 7, 9], "kind": "membrane"}]), "stands free in hull h")
check("... \"in\": \"h\" lines the hold: clean", not scene([HD, {"id": "m", "type": "tank_prism", "kind": "membrane", "in": "h"}]))
caught("two Type C cylinders side by side through each other - a bilobe (M01 s15, s17)",
       scene([H, {"id": "t", "type": "tank_c", "at": [0, 5, -1.9], "r": 3, "len": 8, "base": -3.8},
              {"id": "t", "type": "tank_c", "at": [0, 5, 1.9], "r": 3, "len": 8, "base": -3.8}]), "\"lobes\": 2")
check("... one tank_c \"lobes\": 2 \"in\": \"h\": clean", not scene([H, {"id": "t", "type": "tank_c", "in": "h", "r": 3, "lobes": 2}]))
caught("two tanks in tandem through each other and out through the hull's end walls (M01 s11)",
       scene([dict(H, x=[16, 26]), {"id": "c", "type": "tank_c", "at": [19, 4.6, 0], "r": 2.8, "len": 5, "head": 1.4, "base": -3.4},
              {"id": "c", "type": "tank_c", "at": [23, 4.6, 0], "r": 2.8, "len": 5, "head": 1.4, "base": -3.4}]), "pass through each other")
caught("... and out through the end wall", scene([dict(H, x=[16, 26]), {"id": "c", "type": "tank_c", "at": [23, 4.6, 0], "r": 2.8,
                                                                         "len": 5, "head": 1.4, "base": -3.4}]), "end walls of hull h")
caught("a Moss sphere whose skirt does not reach the inner bottom (M01 s13: \"base\" 1.2)",
       scene([H, {"id": "s", "type": "tank_sphere", "at": [0, 7.5, 0], "r": 5, "base": 1.2, "cut": True}]), "Moss sphere s: its skirt")
check("... \"in\": \"h\": the skirt from the equator to the inner bottom, clean",
      not scene([H, {"id": "s", "type": "tank_sphere", "in": "h", "r": 5, "cut": True, "drip": True, "cover": True}],
                [{"part": "s_skirt", "text": "Skirt"}, {"part": "s_drip", "text": "Drip tray"}, {"part": "s_cover", "text": "Tank cover"}]))
caught("saddles that end in the air above the inner bottom (M01 s03: base = -r)",
       scene([H, {"id": "t", "type": "tank_c", "at": [0, 5, 0], "r": 3.2, "len": 8, "base": -3.2}]), "stands on nothing")
caught("a Type A tank placed by hand: no clearance, chocks, insulation or centreline bulkhead (M01 s07)",
       scene([H, {"id": "a", "type": "tank_prism", "kind": "type_a", "at": [0, 5, 0], "size": [12, 6, 9]}]), "prismatic tank a is placed by hand")
check("... \"in\": \"h\" with kind type_a makes <id>_bulkhead, _insulation, _shell, _chocks (labels on them pass)",
      not scene([HD, {"id": "a", "type": "tank_prism", "kind": "type_a", "in": "h"}],
                [{"part": "a_" + n, "text": n} for n in ("bulkhead", "insulation", "shell", "chocks")] +
                [{"part": "h_" + n, "text": n} for n in ("outer", "inner", "bottom", "wing", "hopper", "topwing")]))
check("... a hull with no double hull makes none of those sub-parts: a label on h_wing is refused",
      any("'h_wing'" in x for x in scene([H], [{"part": "h_wing", "text": "Wing tank"}])))
caught("a dimension ending past the tank's end, in the air (M01 s09: B/5 to z 2.6 at x 6.5)",
       scene([dict(H, x=[-7, 7]), {"id": "t", "type": "tank_c", "at": [0, 4.2, 0], "r": 2.6, "len": 9, "head": 1.3, "cut": True, "base": -3},
              {"id": "d", "type": "dimension", "a": [6.5, 4.2, -6], "b": [6.5, 4.2, -2.6]}]), "dimension d: its end b")
check("... the same dimension across the drawn half, from the side shell to the tank wall: clean",
      not scene([dict(H, x=[-7, 7]), {"id": "t", "type": "tank_c", "at": [0, 4.2, 0], "r": 2.6, "len": 9, "head": 1.3, "cut": True, "base": -3},
                 {"id": "d", "type": "dimension", "a": [0, 4.2, -6], "b": [0, 4.2, -2.6]}]))
caught("... a dimension to the half a cut took away",
       scene([dict(H, x=[-7, 7]), {"id": "t", "type": "tank_c", "at": [0, 4.2, 0], "r": 2.6, "len": 9, "head": 1.3, "cut": True, "base": -3},
              {"id": "d", "type": "dimension", "a": [0, 4.2, 6], "b": [0, 4.2, 2.6]}]), "the half its cut took away")
caught("a pump placed inside a tank (M01 s04)",
       scene([H, {"id": "t", "type": "tank_c", "in": "h", "r": 3}, {"id": "p", "type": "pump", "at": [1, 4.6, 0.5]}]), "pump p stands inside tank t")
check("... a submerged pump \"in\" its tank: clean",
      not scene([H, {"id": "t", "type": "tank_c", "in": "h", "r": 3}, {"id": "p", "type": "pump", "at": [1, 4.6, 0.5], "in": "t"}]))
for txt, part, typ, needle in (("Double hull", "w", "box", "\"double\""), ("Skirt at the equator", "k", "cylinder", "<tank>_skirt"),
                               ("Centreline bulkhead", "b", "box", "<tank>_bulkhead"), ("Drip pan: partial secondary barrier", "d", "box", "<tank>_drip"),
                               ("Complete secondary barrier: the hull", "s", "box", "\"double\"")):
    caught("a %s named %r stands in for what the kit draws" % (typ, txt),
           scene([H, {"id": part, "type": typ, "at": [0, 2, -5.5], "size": [8, 1, 1]}], [{"part": part, "text": txt}]), needle)
caught("\"Double hull\" on the double bottom (M01 s08)",
       scene([dict(H, bottom_id="db")], [{"part": "db", "text": "Double hull"}]), "the double bottom")
check("... on the inner hull of a hull with \"double\": clean", not scene([HD], [{"part": "h_inner", "text": "Double hull: the inner hull"}]))
caught("\"Single hull\" on a double bottom (M01 s15)", scene([dict(H, bottom_id="db")], [{"part": "db", "text": "Single hull is acceptable"}]),
       "a single hull is the side shell")
caught("a hull's words on a tank: the secondary barrier, the side shell (M01 s12, s17)",
       scene([H, {"id": "t", "type": "tank_c", "in": "h", "r": 3}], [{"part": "t", "text": "Complete secondary barrier"}]), "its dot is on tank t")
check("... \"Type C: no secondary barrier\" on the tank says what the tank has not: clean",
      not scene([H, {"id": "t", "type": "tank_c", "in": "h", "r": 3}], [{"part": "t", "text": "Type C: no secondary barrier"}]))
caught("two dots of one part on one spot on a step (M01 s19b)",
       scene([H, {"id": "t", "type": "tank_c", "in": "h", "r": 3}], [{"part": "t", "text": "Type 2G", "at": [0, 7.8, 0]},
                                                                    {"part": "t", "text": "Type 2PG", "at": [0, 7.8, 0.3]}]), "two dots on one spot")
caught("a dot behind a tank from the step's view (M01 s15: the side shell's dot seen on the tank)",
       scene([dict(H, side_id="side"), {"id": "t", "type": "tank_c", "in": "h", "r": 3}],
             [{"part": "side", "text": "Side shell", "at": [-1, 4.6, -6]}], [{"view": {"az": 0, "el": 5}}]), "has its dot behind tank_c t")
check("... the same dot from a view where the tank does not hide it: clean",
      not scene([dict(H, side_id="side"), {"id": "t", "type": "tank_c", "in": "h", "r": 3}],
                [{"part": "side", "text": "Side shell", "at": [-1, 4.6, -6]}], [{"view": {"az": 90, "el": 5}}]))
caught("a tank \"in\" a hull that is not there", scene([H, {"id": "t", "type": "tank_c", "in": "nohull", "r": 3}]), "no hull or hull space")
check("kit3d.js seats a tank \"in\" its hull before it builds it, and holds the hold's section (inRelation, holdSection)",
      "function inRelation" in js and "function holdSection" in js)
# the kit and the checker seat a tank the same way: the numbers of kit3d.js inRelation, read in its source
check("check_kit3d.seat mirrors kit3d.js inRelation (the skirt 1.25 (r + insulation), the clearance max(0.5, 0.15 r))",
      "(R + ins) * 1.25" in js and "Math.max(0.5, R * 0.15)" in js
      and ck.seat({"type": "tank_sphere", "in": "h", "r": 4}, [H])["base"] == -5.0
      and ck.seat({"type": "tank_c", "in": "h", "r": 4}, [H])["base"] == -(0.6 + 4))

print("\n%s" % ("ALL PASS" if not FAILS else "%d FAILED" % len(FAILS)))
sys.exit(1 if FAILS else 0)
