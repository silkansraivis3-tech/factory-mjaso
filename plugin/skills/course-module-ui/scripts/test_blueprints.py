# -*- coding: utf-8 -*-
"""test_blueprints - one short file tells the factory how every screen is built, and the live references prove it.

    python test_blueprints.py

knowledge/blueprints.json is what the factory reads instead of the long guides to choose and fill a screen. That is only
safe if it is complete and true, so these are pinned:

  * every slide template and variant of layout-templates.json has a blueprint, and every row of its "picking" table too;
  * every slot is one of the six kinds, every grid is whole, and the empty catalogue design/template-blueprints is the
    one blueprints.py writes from the file today;
  * every reference is there: each slide template has its slide in design/slide-templates, each task its live screen
    or its engine prototype in design/task-templates;
  * the engine prototypes' two themes still come out right: Navy with no near-black, white with the picture boxes Navy.
"""
from __future__ import annotations

import colorsys
import io
import json
import os
import re
import subprocess
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
REPO = os.path.dirname(os.path.dirname(os.path.dirname(SKILL)))
TOOL = os.path.join(HERE, "blueprints.py")
sys.path.insert(0, HERE)
import blueprints as bp  # noqa: E402

PASS: list[str] = []
FAIL: list[str] = []


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print(("  ok    " if ok else "  FAIL  ") + name + (("  -> " + str(detail)) if detail and not ok else ""))


def near_black(css):
    out = set()
    for h in re.findall(r"#([0-9a-fA-F]{6})\b", css):
        hh, l, s = colorsys.rgb_to_hls(*(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)))
        if l < .09 and not (200 <= hh * 360 <= 235 and s > .5):
            out.add("#" + h.upper())
    return out


def main():
    print("-- the spec")
    r = subprocess.run([sys.executable, TOOL, "--check"], capture_output=True, text=True, encoding="utf-8", errors="replace")
    check("blueprints.py --check: every template and variant has a blueprint, the slots and grids are whole, every reference "
          "is there, the empty catalogue is up to date", r.returncode == 0, r.stdout[-1500:])
    ids = {b["id"].split(".")[0] for b in bp.BP["slides"]}
    rows = [x["template"].split(" ")[0].split("/")[0] for x in bp.LAYOUTS["picking"]["rows"]]
    check("every row of the picking table has a blueprint", all(t.strip() in ids for t in rows), sorted(set(rows) - ids))
    check("the spec is short: one line a blueprint, the whole file under 40 KB",
          os.path.getsize(os.path.join(SKILL, "knowledge", "blueprints.json")) < 40000)
    keep = json.loads(json.dumps(bp.BP))
    bp.BP["slides"][0]["fill"]["x"] = ["Words", "text"]
    bp.BP["slides"][1]["grid"] = ["x p", "x"]
    bp.BP["slides"] = [b for b in bp.BP["slides"] if b["id"] != "drill.say-it"]
    bp.BP["tasks"][-1]["ref"] = "engines#99_none"
    for b in bp.BP["slides"]:
        if b["id"] == "scenario.picture-left":          # the trial's M01 s21: a box no rule judged
            del b["fits"]
        if b["id"] == "scenario.figure-top":
            b["fits"]["parts"] = dict(b["fits"]["parts"], t_part_choices="scenario_choices_guess")
    probs = bp.problems()
    bp.BP.clear()
    bp.BP.update(keep)
    for what, word in (("a slot that is not one of the six kinds", "is a 'Words'"), ("a grid whose rows differ", "not all as wide"),
                       ("a template variant with no blueprint", "drill.say-it has no blueprint"), ("a reference that is not there", "99_none"),
                       ("a picture box that says no shape of picture (scenario.picture-left, M01 s21)",
                        "scenario.picture-left: it holds a picture and says no picture shape"),
                       ("a part's budget that was never measured", "\"scenario_choices_guess\", is not a measured budget")):
        check("... and it catches %s" % what, any(word in p for p in probs), probs)
    slides = [bp.resolved(b, bp.BP["slides"]) for b in bp.BP["slides"]]
    one = [b["id"] for b in slides if b.get("shape") not in ("", "two") and any(k in ("Picture", "3D") for k, _ in b["fill"].values())]
    check("every teaching slide that holds one picture says the shapes of picture its box takes, a mirror its base's (%d)" % len(one),
          one and all((b.get("fits") or {}).get("aspect") for b in slides if b["id"] in one),
          [b["id"] for b in slides if b["id"] in one and not (b.get("fits") or {}).get("aspect")])
    bands = {"%s.%s" % (t, v) for t in ("scenario", "worked-example", "true-false", "name-parts") for v in ("figure-top", "figure-bottom")}
    check("a scenario, a worked example, a true or false and naming the parts each have a band for a wide picture, of their "
          "own template", bands <= {b["id"] for b in slides} and all(b["fits"]["group"] == b["template"] for b in slides if b["id"] in bands))

    print("\n-- the catalogue")
    page = io.open(bp.OUT, encoding="utf-8").read()
    check("the catalogue holds no words of a course: only the six kinds and what fills them",
          all(k in page for k in bp.KINDS) and "LNG" not in page and "propane" not in page.lower())
    check("... a card for every blueprint", page.count('<article class="bp">') == len(bp.BP["slides"]) + len(bp.BP["tasks"]))

    print("\n-- the references")
    tt = os.path.join(REPO, "design", "task-templates")
    eng = os.path.join(tt, "engines", "demo", "tasks")
    tasks = sorted(f for f in os.listdir(eng) if f.endswith(".html"))
    check("the nineteen engine prototypes and the twelve live task screens are kept",
          len(tasks) == 19 and len(re.findall(r'<section class="tk[^"]*" id="s\d+"', io.open(os.path.join(tt, "live", "index.html"), encoding="utf-8").read())) == 12)
    check("each prototype reads the factory's own colour tokens", all(
        "../../../../../plugin/skills/course-module-ui/templates/gb_tokens.css" in io.open(os.path.join(eng, f), encoding="utf-8").read() for f in tasks))
    check("every prototype has its picture in both themes", all(
        os.path.isfile(os.path.join(tt, "shots", "%s_%s.jpg" % (t, f[:-5]))) for f in tasks for t in ("pd", "pl")))
    out = tempfile.mkdtemp()
    r = subprocess.run([sys.executable, os.path.join(tt, "themes.py"), out], capture_output=True, text=True, encoding="utf-8", errors="replace")
    check("themes.py writes both themes", r.returncode == 0 and "dark written" in r.stdout and "light written" in r.stdout, r.stdout + r.stderr)
    if r.returncode == 0:
        root = lambda t: os.path.join(out, t, "design", "task-templates", "engines")
        dark = io.open(os.path.join(root("dark"), "gb_lab.css"), encoding="utf-8").read() + "".join(
            "".join(re.findall(r"<style>(.*?)</style>", io.open(os.path.join(root("dark"), "demo", "tasks", f), encoding="utf-8").read(), re.S)) for f in tasks)
        check("the Navy theme has no near-black left", not near_black(dark), sorted(near_black(dark)))
        light = io.open(os.path.join(root("light"), "gb_lab.css"), encoding="utf-8").read()
        page = io.open(os.path.join(root("light"), "demo", "tasks", "04_survey_space.html"), encoding="utf-8").read()
        check("the white theme: a white page, the simulator, the 3D stage and an instrument's display Navy",
              re.search(r"--tl-bg:\s*#FFFFFF", light) and ".tl-stage,.hm,.sv-lcd{" in page and ".sv-lcd .sv-" in page, light[:300])
        check("... and a colour rule copied into a picture box carries only its colours, never a layout line",
              not re.search(r"\.tl-stage [^{},]+,\.hm [^{}]*\{[^}]*(bottom|top|height|width|display)\s*:", light))
        check("a bold word inside an opening card's step stays a word", ".tl-how li > b" in light and ".tl-how li b" not in light)
        check("the photographs and the 3D renders come with them", os.path.isfile(os.path.join(root("light"), "demo", "img3d", "s3d_radio.jpg"))
              and len(os.listdir(os.path.join(root("light"), "demo", "img"))) > 50)

    print("\n" + "=" * 72)
    print("%d passed, %d failed" % (len(PASS), len(FAIL)))
    if FAIL:
        return 1
    print("\nOne short file says how every screen is built, the empty catalogue is drawn from it, and every\n"
          "blueprint points at a live reference that is kept and still comes out right.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
