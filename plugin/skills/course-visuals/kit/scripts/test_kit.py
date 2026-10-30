#!/usr/bin/env python3
"""test_kit.py - check_kit.py and kit_parts.py do what PARTS.md says (L55). Run: python test_kit.py"""
from __future__ import annotations

import io
import json
import os
import re
import shutil
import sys
import tempfile
from contextlib import redirect_stdout

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import check_kit as ck  # noqa: E402
import kit_parts as kp  # noqa: E402

FAILS = []


def check(what, ok, detail=""):
    print(("PASS  " if ok else "FAIL  ") + what + ("" if ok else "   -> %s" % (detail,)))
    if not ok:
        FAILS.append(what)


GOOD = """/* kit-part: oil_tray */
KIT.define('oil_tray', function (fig, part, g, p) {
  var h = KIT.h, w = p.w || 120, eq = h.equip(g);
  h.body('rect', { width: w, height: 18, rx: 4 }, eq, { mat: 'steel', shade: 'box' });
  var pool = h.el('rect', { x: 4, y: 14, width: w - 8, height: 0, 'class': 'kit-pool' }, g);
  part.render = function (v) { var d = h.clamp(v, 0, 1) * 12; pool.setAttribute('y', 16 - d); pool.setAttribute('height', d); };
}, {
  family: 'piping', status: 'new', look: 'equipment', course: 'IGF Basic', module: 'M03', made: '2026-10-15',
  why: 'M03 s07: liquid caught under the manifold', value: 'how full, 0..1',
  css: '.kit-oil-tray-rim{stroke:var(--dim-d)}',
  example: { size: [300, 120], parts: [{ id: 'D', type: 'oil_tray', x: 90, y: 40 }],
             steps: [{ title: 'A spill is caught', play: [['D', 1, 2000]] }] }
});
/* end kit-part */
"""

# ---------------------------------------------------------------- the contract
check("a part built to the template passes", ck.check_part("oil_tray", ck.blocks(GOOD)[0][1]) == [],
      ck.check_part("oil_tray", ck.blocks(GOOD)[0][1]))
for bad, why in [
    ("{ mat: 'steel', shade: 'box' }", "{ mat: 'steel', fill: '#ff0000' }"),
    ("h.clamp(v, 0, 1)", "h.clamp(v, 0, 1); g.innerHTML = ''"),
    ("var h = KIT.h,", "var h = KIT.h, s = 'font-size:9px',"),
    ("family: 'piping'", "family: 'misc'"),
    ("example: {", "sample: {"),
    ("(--dim-d)}'", "(--dim-d)} .other{fill:var(--x)}'"),
    ("part.render = function", "part.draw = function"),
    ("var(--dim-d)", "rgb(1,2,3)"),
]:
    probs = ck.check_part("oil_tray", ck.blocks(GOOD.replace(bad, why))[0][1])
    check("a part with %s is refused" % why, bool(probs), probs)
CAT = GOOD.replace("css: '.kit-oil-tray-rim{stroke:var(--dim-d)}',",
                   "css: '.kit-oil-tray-rim{stroke:var(--dim-d);' +\n"
                   "       \"fill:var(--kit-steel)}\" + '.kit-oil-tray-pool{fill:var(--water)}',")
check("a css written as 'a' + 'b' is not read as drawing code (finding 1)",
      ck.check_part("oil_tray", ck.blocks(CAT)[0][1]) == [], ck.check_part("oil_tray", ck.blocks(CAT)[0][1]))
check("a concatenated css is still checked as css (a colour in a piece is refused)",
      any("css writes a colour" in p for p in ck.check_part(
          "oil_tray", ck.blocks(CAT.replace("var(--water)", "#fff"))[0][1])))
check("a part named for its module is refused",
      bool(ck.check_part("M03_tray", ck.blocks(GOOD.replace("oil_tray", "M03_tray"))[0][1])))

# ---------------------------------------------------------------- 2.52.0, L63: physical equipment is drawn as it looks on board
def part_with(old, new):
    return ck.check_part("oil_tray", ck.blocks(GOOD.replace(old, new))[0][1])


check("L63: a part that does not say what it is drawn as (look) is refused",
      any("look:" in x for x in part_with("look: 'equipment', ", "")), part_with("look: 'equipment', ", ""))
check("L63: a look that is not equipment, screen or diagram is refused",
      any("look:" in x for x in part_with("look: 'equipment'", "look: 'pretty'")))
FLAT = "h.el('rect', { width: w, height: 18, rx: 4, 'class': 'kit-shell' }, eq);"
probs = part_with("h.body('rect', { width: w, height: 18, rx: 4 }, eq, { mat: 'steel', shade: 'box' });", FLAT)
check("L63: equipment drawn with no material (no KIT.h.body / equip / kit-m-*) is refused",
      any("draws no body in a material" in x for x in probs), probs)
check("L63: equipment drawn with a flat ISA body class (kit-shell) is refused",
      any("flat kit-shell" in x for x in probs), probs)
probs = part_with("'.kit-oil-tray-rim{stroke:var(--dim-d)}'", "'.kit-oil-tray-rim{fill:var(--deep-3);stroke:var(--dim-d)}'")
check("L63: equipment whose css fills a body flat (var(--deep-3)) is refused", any("fills a body flat" in x for x in probs), probs)
check("L63: a body filled with a kit material in css (var(--kit-steel)) passes",
      part_with("'.kit-oil-tray-rim{stroke:var(--dim-d)}'", "'.kit-oil-tray-rim{fill:var(--kit-steel);stroke:var(--dim-d)}'") == [])
SCREEN = GOOD.replace("look: 'equipment'", "look: 'screen'").replace(
    "h.body('rect', { width: w, height: 18, rx: 4 }, eq, { mat: 'steel', shade: 'box' });",
    "h.el('rect', { width: w, height: 18, rx: 4, 'class': 'kit-tile' }, g);")
check("L63: a screen stays a flat ISA-101 HMI - no material asked of it",
      ck.check_part("oil_tray", ck.blocks(SCREEN)[0][1]) == [], ck.check_part("oil_tray", ck.blocks(SCREEN)[0][1]))
merged = dict(ck.blocks(ck.read(ck.KIT_JS)))
bad_look = sorted(n for n, b in merged.items() if ck.meta_field(b, "look") not in ck.LOOKS)
check("L63: every part merged into kit.js says what it is drawn as", not bad_look, bad_look)
equipment = sorted(n for n, b in merged.items() if ck.meta_field(b, "look") == "equipment")
check("L63: the kit's physical parts are drawn as equipment (cylinder, coupling, manifold, person, ga ...)",
      {"cylinder", "coupling", "manifold", "person", "ga", "hose", "relief_valve", "gas_cylinder"} <= set(equipment), equipment)
kitjs, kitcss = ck.read(ck.KIT_JS), ck.read(os.path.join(os.path.dirname(ck.KIT_JS), "kit.css"))
check("L63: kit.js draws the materials once per page and gives parts KIT.h.body, equip, flange",
      all(x in kitjs for x in ("function materials()", "body: body", "equip: equip", "flange: flange", "'kit-materials'")))
check("L63: the materials are tokens (--mat-*), with a set of their own for a light page (.kit-mat-light, .kit.kit-light)",
      all(x in kitcss for x in ("--mat-steel:", "--mat-steel-l:", ".kit-mat-light{", "--kit-steel:url(#kit-m-steel-l)")))
check("L63: the materials' textures are never display:none (Chrome then drops their paint servers)",
      "display:none" not in kitjs.split("function materials()", 1)[1].split("function body(", 1)[0])
for t in ("valve", "tank", "pipe", "exchanger", "pump", "engine", "vent", "well"):
    src = kitjs.split("TYPES.%s = function" % t, 1)[1].split("\n  };", 1)[0]
    check("L63: the kit's own %s is drawn in its material (body / equip / flange)" % t,
          bool(re.search(r"\b(?:body|equip|flange)\(", src)))

# ---------------------------------------------------------------- specs
types = ck.kit_types()
check("the kit's own parts are known", {"gauge", "level", "pipe", "valve", "tank", "badge"} <= types, types)
spec = {"size": [300, 200], "label": "x", "parts": [
    {"id": "P", "type": "pipe", "d": "M0 0 H10"}, {"id": "V", "type": "valve"},
    {"id": "L", "type": "level", "marks": [{"at": 9, "kind": "trip", "then": [["V", 0, 500]]}]}],
    "steps": [{"title": "go", "play": [["P.fill", 1, 900], ["L", 10, 1000]], "line": 2}]}
check("a good spec passes", ck.check_spec(spec, types, "s") == [], ck.check_spec(spec, types, "s"))
for change, what in [
    (lambda s: s["parts"].append({"id": "X", "type": "spaceship"}), "an unknown part type"),
    (lambda s: s["parts"].append({"id": "P", "type": "valve"}), "an id used twice"),
    (lambda s: s["steps"][0]["play"].append(["Q", 1, 100]), "a move on a missing part"),
    (lambda s: s["steps"][0]["play"].append(["V.fill", 1, 100]), "a .fill on a valve"),
    (lambda s: s["parts"][2]["marks"][0].update(kind="red"), "a mark of an unknown kind"),
    (lambda s: s["steps"].append({"title": "nothing"}), "a step that moves nothing"),
    (lambda s: s.pop("size"), "no size"),
    (lambda s: s.update(theme="blue"), "a theme that is neither light nor dark"),
    (lambda s: s["parts"].append({"type": "text", "text": "vapour space", "to": [1]}), "a callout whose place is not [x, y]"),
]:
    s2 = json.loads(json.dumps(spec))
    change(s2)
    check("a spec with %s is refused" % what, bool(ck.check_spec(s2, types, "s")))
s3 = json.loads(json.dumps(spec))
s3["theme"] = "light"
s3["parts"].append({"type": "text", "x": 10, "y": 10, "text": "vapour space", "to": [40, 60]})
check("a light theme and a callout pass", ck.check_spec(s3, types, "s") == [], ck.check_spec(s3, types, "s"))

# ---------------------------------------------------------------- 2.49.1: the parts and values IGF M06 asked for (K4, K5)
check("lamp, spark and composition_bar are in the kit", {"lamp", "spark", "composition_bar"} <= types, types)
merged_now = dict(ck.blocks(ck.read(ck.KIT_JS)))
check("the new parts are merged blocks that pass the parts contract (colours, helpers, example)",
      all(n in merged_now and ck.check_part(n, merged_now[n]) == [] for n in ("lamp", "spark", "composition_bar", "gas_cloud", "drip_tray", "flame", "fire")),
      [(n, ck.check_part(n, merged_now[n])) for n in ("lamp", "spark", "composition_bar", "gas_cloud") if n in merged_now])
new_spec = {"size": [400, 300], "label": "x", "parts": [
    {"id": "T", "type": "tank", "burst": True}, {"id": "C", "type": "gas_cloud", "drift": [60, 0]},
    {"id": "N", "type": "text", "x": 5, "y": 5, "text": "the answer", "reveal": True},
    {"id": "B", "type": "composition_bar", "segments": [{"label": "methane", "pct": 90}]},
    {"id": "L", "type": "lamp", "ex": True}, {"id": "S", "type": "spark", "kind": "friction"}],
    "steps": [{"title": "go", "play": [["T.burst", 1, 800], ["C.drift", 1, 800], ["N", 1, 300], ["B", 1, 500]]}]}
check("a tank's burst, a cloud's drift, a revealed text and the new parts make a good spec",
      ck.check_spec(new_spec, types, "s") == [], ck.check_spec(new_spec, types, "s"))
for change, what in [
    (lambda s: s["parts"][0].pop("burst"), "T.burst on a tank that has no \"burst\""),
    (lambda s: s["parts"][1].pop("drift"), "C.drift on a cloud that has no \"drift\""),
    (lambda s: s["steps"][0]["play"].append(["L.burst", 1, 100]), "a burst on a lamp"),
]:
    s4 = json.loads(json.dumps(new_spec))
    change(s4)
    check("a spec with %s is refused" % what, bool(ck.check_spec(s4, types, "s")))

# ---------------------------------------------------------------- 2.49.2: what IGF M07-M15 found (F3, F22)
def cloud(**kw):
    p = {"id": "C", "type": "gas_cloud", "x": 350, "y": 110, "w": 250, "h": 120}
    p.update(kw)
    return {"size": [640, 390], "label": "x", "parts": [p],
            "steps": [{"title": "gas", "play": [["C", 1, 500]]}]}


check("F3 gas_cloud: an origin in the cloud's own box (an old spec) is clean", ck.check_spec(cloud(**{"from": [100, 80]}), types, "s") == [])
check("F3 gas_cloud: an origin in figure coordinates (only inside the box that way) is clean",
      ck.check_spec(cloud(**{"from": [450, 190]}), types, "s") == [])
check("F3 gas_cloud: the same point read in the box with \"fromIn\": \"box\" lands off the figure and is warned",
      any("off the picture" in x for x in ck.check_spec(cloud(**{"from": [450, 190], "fromIn": "box"}), types, "s")))
check("F3 gas_cloud: an origin off the figure either way is warned, with where it landed",
      any("off the picture" in x and "[" in x for x in ck.check_spec(cloud(**{"from": [900, 700]}), types, "s")))
check("F3 gas_cloud: \"fromIn\": \"figure\" reads a point that is inside the box both ways as figure coordinates",
      ck.cloud_origin({"x": 20, "y": 20, "w": 280, "h": 150, "from": [110, 130], "fromIn": "figure"}) == ((110, 130), "figure")
      and ck.cloud_origin({"x": 20, "y": 20, "w": 280, "h": 150, "from": [110, 130]}) == ((130, 150), "box"))
check("F3 gas_cloud: a \"from\" that is not [x, y] is refused", bool(ck.check_spec(cloud(**{"from": "left"}), types, "s")))
person = {"size": [400, 330], "label": "x", "parts": [
    {"id": "A", "type": "person", "x": 100, "y": 290, "wear": ["goggles", "respirator", "apron", "gloves", "boots"],
     "labels": {"respirator": "HALF MASK"}}], "steps": [{"title": "on", "play": [["A", 5, 500]]}]}
check("F22 person: goggles, respirator, apron and a labels option are a good spec", ck.check_spec(person, types, "s") == [], ck.check_spec(person, types, "s"))
p2 = json.loads(json.dumps(person)); p2["parts"][0]["wear"].append("cape")
check("F22 person: a wear item the kit cannot draw is refused", bool(ck.check_spec(p2, types, "s")))
p3 = json.loads(json.dumps(person)); p3["parts"][0]["labels"]["suit"] = "OVERALL"
check("F22 person: a label for an item that is not worn is refused (its words would never show)", bool(ck.check_spec(p3, types, "s")))

# ---------------------------------------------------------------- 2.50.4: a vent's "mast" (M01 benchmark run 4, issue 3)
def vent(mast):
    return {"size": [400, 300], "label": "x", "parts": [{"id": "V", "type": "vent", "x": 200, "y": 60, "mast": mast}]}


for good in (True, False, 80, 42.5):
    check("vent \"mast\": %r is a good spec" % (good,), ck.check_spec(vent(good), types, "s") == [], ck.check_spec(vent(good), types, "s"))
for wrong in ("tall", 0, -20, None, [0, 80]):
    probs = ck.check_spec(vent(wrong), types, "s")
    check("vent \"mast\": %r is refused, saying what it takes" % (wrong,), any("true (a mast)" in x for x in probs), probs)

# ---------------------------------------------------------------- the 2.48.0 layout contract in kit.js itself
kit = ck.read(ck.KIT_JS)
check("kit.js lays figures out (labels, the floor, the frame) and exports the helpers parts use",
      all(x in kit for x in ("function lay(f)", "function place(", "label: label", "widest: widest", "layoutAll")))
check("every kit type size grows with --kit-up (the 12.5 px floor)",
      not [l for l in ck.read(os.path.join(os.path.dirname(ck.KIT_JS), "kit.css")).splitlines()
           if "font-size:" in l and ".kit" in l and "kit-up" not in l and "figcaption" not in l])
check("kit.css maps the dark-panel tokens for a light ground (.kit-light)", ".kit.kit-light{" in ck.read(os.path.join(os.path.dirname(ck.KIT_JS), "kit.css")))
bare = []
for name, block in ck.blocks(kit):
    body = ck.strip_comments(block)
    if re.search(r"h\.lines\(g,\s*\{[^}]*'class':\s*'kit-cap'", body):
        bare.append(name)
check("no part merged into kit.js draws a caption as bare text - it is a label the layout places", not bare, bare)
check("a module's new part makes its type known",
      ck.check_spec({"size": [1, 1], "label": "x", "parts": [{"id": "D", "type": "oil_tray"}]},
                    types | {"oil_tray"}, "s") == [])

# ---------------------------------------------------------------- the gallery's own specs and the real kit.js
gal = io.open(os.path.join(os.path.dirname(HERE), "GALLERY.html"), encoding="utf-8").read()
s14 = json.loads(gal.split('id="spec-s14">', 1)[1].split("</script>", 1)[0])
check("the gallery's s14 spec passes", ck.check_spec(s14, types, "s14") == [], ck.check_spec(s14, types, "s14"))
check("kit.js carries the promotion marker", kp.END in ck.read(ck.KIT_JS))

# ---------------------------------------------------------------- promotion, end to end in a temp folder
tmp = tempfile.mkdtemp()
try:
    fac = os.path.join(tmp, "factory")
    kdir = os.path.dirname(os.path.join(fac, kp.KIT_REL))
    os.makedirs(kdir)
    shutil.copy(ck.KIT_JS, os.path.join(fac, kp.KIT_REL))
    os.makedirs(os.path.dirname(os.path.join(fac, kp.PLUGIN_REL)))
    io.open(os.path.join(fac, kp.PLUGIN_REL), "w").write('{\n  "name": "course-factory",\n  "version": "2.26.0"\n}\n')
    mods = []
    for m in ("module03", "module04"):
        d = os.path.join(tmp, m, "assets")
        os.makedirs(d)
        io.open(os.path.join(d, "kit_parts.js"), "w", encoding="utf-8").write(GOOD)
        mods.append(os.path.join(tmp, m))
    out = io.StringIO()
    with redirect_stdout(out):
        rc = kp.cmd_promote(mods, fac, dry=False)
    kit_after = ck.read(os.path.join(fac, kp.KIT_REL))
    check("promote writes the part into the factory's kit.js", rc == 0 and "KIT.define('oil_tray'" in kit_after, out.getvalue())
    check("the promoted copy is status 'kit' with its origin", "status: 'kit', merged_from: \"IGF Basic M03\"" in kit_after)
    check("two modules' copies are promoted once", kit_after.count("kit-part: oil_tray") == 1)
    check("the second copy is reported", "module04" in out.getvalue() and "made one too" in out.getvalue(), out.getvalue())
    check("the plugin version is bumped", '"version": "2.26.1"' in ck.read(os.path.join(fac, kp.PLUGIN_REL)))
    check("promote never pushes - it prints the steps and says to ask",
          "ASK THE OPERATOR" in out.getvalue() and "gh pr create" in out.getvalue())
    with redirect_stdout(io.StringIO()):
        rc2 = kp.cmd_promote(mods[:1], fac, dry=False)
    check("promoting again adds nothing", rc2 == 0 and ck.read(os.path.join(fac, kp.KIT_REL)).count("kit-part: oil_tray") == 1)
    io.open(os.path.join(mods[1], "assets", "kit_parts.js"), "w", encoding="utf-8").write(
        GOOD.replace("oil_tray", "spill_tray").replace("{ mat: 'steel', shade: 'box' }", "{ mat: 'steel', fill: '#fff' }"))
    with redirect_stdout(io.StringIO()):
        rc3 = kp.cmd_promote(mods[1:], fac, dry=False)
    check("a part that fails its check stops the promotion", rc3 == 1 and "spill_tray" not in ck.read(os.path.join(fac, kp.KIT_REL)))
finally:
    shutil.rmtree(tmp, ignore_errors=True)

# ---------------------------------------------------------------- CATALOGUE.md (the one short file a spec is written from)
import subprocess  # noqa: E402

cat_py = os.path.join(HERE, "kit_catalogue.py")
rc_cat = subprocess.run([sys.executable, cat_py, "--check"], capture_output=True, text=True, encoding="utf-8")
check("CATALOGUE.md is what kit_catalogue.py writes now (stale? run: python scripts/kit_catalogue.py)",
      rc_cat.returncode == 0, rc_cat.stdout + rc_cat.stderr)
cat_txt = ck.read(os.path.join(os.path.dirname(HERE), "CATALOGUE.md"))
missing = sorted(t for t in ck.kit_types() if "`%s`" % t not in cat_txt)
check("CATALOGUE.md names every part the kit has", not missing, missing)
check("CATALOGUE.md starts with its GENERATED stamp", cat_txt.startswith("GENERATED by kit_catalogue.py"))
# 18 KB since 2.81.0: eleven machines, vessels and quayside structures the IGF Advanced figures drew as boxes (L55 (4)) -
# a part a builder cannot find in the catalogue is drawn as a box again, so the list grows with the kit, one line a part
check("CATALOGUE.md stays short (under 18 KB)", len(cat_txt.encode("utf-8")) < 18000, len(cat_txt.encode("utf-8")))

# ---------------------------------------------------------------- 2.63.0: the bands' zone fills read 3:1 on their dark track
# (IGF M02 v262 s11: zone 2's amber at opacity .5 on --deep read 2.9:1 - the builder overrode it in module CSS)
def lum(hx):
    c = [int(hx.lstrip("#")[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]
    c = [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def over(fg, bg, a):
    return "#" + "".join("%02x" % round(int(fg.lstrip("#")[i:i + 2], 16) * a + int(bg.lstrip("#")[i:i + 2], 16) * (1 - a)) for i in (0, 2, 4))


tokens = dict(re.findall(r"--([\w-]+):\s*(#[0-9A-Fa-f]{6})", ck.read(os.path.join(HERE, "..", "..", "..", "course-module-ui", "templates", "gb_tokens.css"))))
kit_src = ck.read(os.path.join(os.path.dirname(HERE), "kit.js"))
bands_css = re.search(r"/\* kit-part: bands \*/.*?css: '([^']*)'", kit_src, re.S).group(1)
low = []
for tone in ("z0", "z1", "z2"):
    rule = re.search(r"\.kit-bands-%s \.kit-bands-gas[^{]*\{fill:var\(--([\w-]+)\);opacity:([\d.]+)\}" % tone, bands_css)
    if not rule:
        low.append((tone, "no fill rule"))
        continue
    shown = over(tokens[rule.group(1)], tokens["deep"], float(rule.group(2)))
    a, b = sorted((lum(shown), lum(tokens["deep"])))
    if (b + 0.05) / (a + 0.05) < 3.0:
        low.append((tone, rule.group(1), rule.group(2), round((b + 0.05) / (a + 0.05), 2)))
check("bands: every zone's gas reads at least 3:1 on its dark track (zone 2 was 2.9:1)", not low, low)

print("\n%s" % ("ALL PASS" if not FAILS else "%d FAILED" % len(FAILS)))
sys.exit(1 if FAILS else 0)
