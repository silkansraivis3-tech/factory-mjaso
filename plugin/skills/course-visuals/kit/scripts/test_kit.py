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
  var h = KIT.h, w = p.w || 120;
  h.el('rect', { width: w, height: 18, rx: 4, 'class': 'kit-steel' }, g);
  var pool = h.el('rect', { x: 4, y: 14, width: w - 8, height: 0, 'class': 'kit-pool' }, g);
  part.render = function (v) { var d = h.clamp(v, 0, 1) * 12; pool.setAttribute('y', 16 - d); pool.setAttribute('height', d); };
}, {
  family: 'piping', status: 'new', course: 'IGF Basic', module: 'M03', made: '2026-10-15',
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
    ("'class': 'kit-steel'", "fill: '#ff0000'"),
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
                   "       \"fill:var(--steel)}\" + '.kit-oil-tray-pool{fill:var(--water)}',")
check("a css written as 'a' + 'b' is not read as drawing code (finding 1)",
      ck.check_part("oil_tray", ck.blocks(CAT)[0][1]) == [], ck.check_part("oil_tray", ck.blocks(CAT)[0][1]))
check("a concatenated css is still checked as css (a colour in a piece is refused)",
      any("css writes a colour" in p for p in ck.check_part(
          "oil_tray", ck.blocks(CAT.replace("var(--water)", "#fff"))[0][1])))
check("a part named for its module is refused",
      bool(ck.check_part("M03_tray", ck.blocks(GOOD.replace("oil_tray", "M03_tray"))[0][1])))

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
        GOOD.replace("oil_tray", "spill_tray").replace("'kit-steel'", "'kit-steel', fill: '#fff'"))
    with redirect_stdout(io.StringIO()):
        rc3 = kp.cmd_promote(mods[1:], fac, dry=False)
    check("a part that fails its check stops the promotion", rc3 == 1 and "spill_tray" not in ck.read(os.path.join(fac, kp.KIT_REL)))
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print("\n%s" % ("ALL PASS" if not FAILS else "%d FAILED" % len(FAILS)))
sys.exit(1 if FAILS else 0)
