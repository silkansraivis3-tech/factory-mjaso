# -*- coding: utf-8 -*-
"""build_order - the modules of a parallel build, biggest first (2.65.0).

    python build_order.py <course> --modules 1,2,3 [--seed-from <predecessor course>] [--json]

WHY (the 2.63.3 M01-M03 workflow run, Desktop\\IGF_course_2.63.3_speed\\SPEED.md): the wave's wall clock was 114 min against
95 because it waited for M02 - 107 builder minutes, 43 of them drawing ~15 figures before its first build. A workflow that
starts modules in the order they were listed puts the long pole wherever the list put it; started first, it overlaps the
others instead of running alone at the end.

The cost is read from the approved scripts, before anything is built: every screen counts 1, a screen whose picture must be
DRAWN (a kit figure: technical drawing, schematic, cutaway, chart, comparison, an animation, an interactive diagram) 3 more,
one that a predecessor already drew for the same words (seed_from - compile_module.py --init-build copies it) 1 more, a 3D
scene 6 more. A screen with a photo or no picture adds nothing. The weights are checked against the builder minutes of the
2.63.0 and 2.63.2 whole-course runs (test_build_order.py: the biggest module by this cost is among the three slowest).

Prints one line per module, biggest first, and with --json the list the workflow reads:
    [{"id": 2, "cost": 112, "screens": 40, "drawn": 22, "seeded": 0, "scenes": 1}, ...]
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import workspace  # noqa: E402

DRAWN = ("technical_drawing", "schematic", "cutaway", "chart", "comparison", "step_animation", "flow_animation",
         "process_animation", "interactive_diagram")
SCENES = ("model_3d", "model_3d_scan", "model_3d_licensed")
W_SCREEN, W_DRAWN, W_SEEDED, W_SCENE = 1, 3, 1, 6


def _load(p):
    try:
        with io.open(p, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def _kind(v):
    """a script's visual_kind ("schematic", "schematic + photo", None) -> its first word"""
    words = str(v or "").replace("+", " ").replace(",", " ").split()
    return words[0] if words else ""


def _norm(s):
    return " ".join(str(s or "").split())


def seed_course(course, given=None):
    """the predecessor a rebuild starts from - compile_module.seed_course's rule, without importing the compiler: --seed-from,
    else working_claude\\course.build.json "seed_from"; None when neither names one"""
    p = given
    if not p:
        b = _load(workspace.claude_path(course, "course.build.json")) or {}
        p = b.get("seed_from")
    if p and not os.path.isabs(p):
        p = os.path.normpath(os.path.join(course, p))
    return p or None


def seeded_ids(script, seed, mid):
    """the screens whose words are the predecessor's own and whose predecessor sheet names a picture - what --init-build seeds"""
    if not seed:
        return set()
    pwork = os.path.join(seed, "working_claude", "script")
    ps, pb = _load(os.path.join(pwork, mid + ".json")) or {}, _load(os.path.join(pwork, mid + ".build.json")) or {}
    before, sheet = {s.get("id"): s for s in ps.get("screens") or []}, pb.get("screens") or {}
    out = set()
    for s in script.get("screens") or []:
        p = before.get(s.get("id"))
        if not p or s.get("kind") != p.get("kind") or not (sheet.get(s["id"]) or {}).get("figure"):
            continue
        keys = ("title", "text") if s.get("kind") == "slide" else ("question", "answer", "options", "mechanic")
        if all(_norm(p.get(k)) == _norm(s.get(k)) for k in keys):
            out.add(s["id"])
    return out


def cost(course, module, seed=None):
    mid = "M%02d" % int(module)
    script = _load(workspace.claude_path(course, "script", mid + ".json"))
    if not script:
        return {"id": module, "cost": 0, "screens": 0, "drawn": 0, "seeded": 0, "scenes": 0, "note": "no script"}
    seeded = seeded_ids(script, seed, mid)
    screens = script.get("screens") or []
    drawn = [s for s in screens if _kind(s.get("visual_kind")) in DRAWN]
    scenes = [s for s in screens if _kind(s.get("visual_kind")) in SCENES]
    n_seeded = sum(1 for s in drawn if s.get("id") in seeded)
    c = (W_SCREEN * len(screens) + W_DRAWN * (len(drawn) - n_seeded) + W_SEEDED * n_seeded + W_SCENE * len(scenes))
    return {"id": module, "cost": c, "screens": len(screens), "drawn": len(drawn), "seeded": n_seeded, "scenes": len(scenes)}


def order(course, modules, seed=None):
    """the modules' costs, biggest first (a tie keeps the given order)"""
    seed = seed_course(course, seed)
    rows = [cost(course, m, seed) for m in modules]
    return sorted(rows, key=lambda r: -r["cost"])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("course")
    ap.add_argument("--modules", required=True, help="the module numbers, comma-separated")
    ap.add_argument("--seed-from", help="the predecessor course (default: course.build.json \"seed_from\")")
    ap.add_argument("--json", action="store_true")
    o = ap.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    course = workspace.work_folder(o.course, create=False)
    rows = order(course, [int(x) for x in o.modules.split(",") if x.strip()], o.seed_from)
    if o.json:
        print(json.dumps(rows))
        return 0
    seed = seed_course(course, o.seed_from)
    print("Build order, biggest first%s:" % (" (seeded from %s)" % seed if seed else ""))
    for r in rows:
        print("  M%02d  cost %3d  - %d screens, %d drawn (%d seeded), %d 3D" % (
            int(r["id"]), r["cost"], r["screens"], r["drawn"], r["seeded"], r["scenes"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
