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
        {"id": "tank", "type": "tank_c", "at": [0, 3, 0], "r": 3.4, "len": 14, "cut": True, "fill": 0.6},
        {"id": "pipe", "type": "pipe_dw", "at": [0, 0, 0], "subs": {"inner": "gas_in"}},
        {"id": "hull", "type": "hull", "at": [0, 0, 0], "pick": False,
         "spaces": [{"id": "ds", "name": "Double side"}], "bottom_id": "db"},
        {"id": "v1", "type": "valve", "at": [2, 1, 0]},
        {"id": "box", "type": "box", "at": [5, 0, 0], "size": [1, 1, 1], "pick": False},
    ],
    "groups": {"leak": ["pipe", "v1"]},
    "states": {"pipe.cut": 0},
}
GOOD["labels"] = [
    {"part": "tank", "text": "Fuel tank", "at": [0, 6, 0]},
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
     lambda s: s["labels"].extend({"part": "tank", "text": "T%d" % i} for i in range(10)), "step 0 shows")
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

# 2.66.0 - a part that stands on the open deck is never below it; "on": "<hull>.deck" places it there
print("\n-- 2.66.0: deck parts on the deck")
HULL = {"id": "H", "type": "hull", "at": [0, 0, 0], "x": [-10, 10], "half": 6, "top": 9}
low = {"label": "t", "units": "m", "parts": [HULL, {"id": "V", "type": "vent_mast", "at": [2, 4, 0], "h": 10}]}
check("a vent mast whose foot is below the hull's deck (inside the hull) fails",
      any("below the deck" in x for x in run(low)[0]), run(low)[0])
ok = {"label": "t", "units": "m", "parts": [HULL, {"id": "V", "type": "vent_mast", "on": "H.deck", "at": [2, 0, 0], "h": 10}]}
check("the same mast \"on\": \"H.deck\" passes", not [x for x in run(ok)[0] if "deck" in x])
check("deck_level reads the hull's deck as kit3d.js does (top 9 over its origin)", ck.deck_level(HULL) == 9)
js = io.open(os.path.join(os.path.dirname(HERE), "kit3d.js"), encoding="utf-8").read()
check("kit3d.js places a part \"on\" a hull's deck before it builds it", "function deckRelation" in js and "deckRelation(list, list[i], S)" in js)

print("\n%s" % ("ALL PASS" if not FAILS else "%d FAILED" % len(FAILS)))
sys.exit(1 if FAILS else 0)
