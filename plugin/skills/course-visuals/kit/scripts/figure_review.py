#!/usr/bin/env python3
"""figure_review.py - every figure of a module photographed at PROJECTOR size, one picture per step, for the FIGURE review (2.66.0)

  figure_review.py <course> --module N [--only s03,s04] [--out <folder>] [--json]
  figure_review.py --specs <a.kit.json> <b.kit.json> ... --out <folder> [--json]      (figures outside a course)

WHY (IGF 2.65.0, Aleksis: "the vent mast is INSIDE of the ship, the gas is not being ejected, ... not properly connected"):
every check passed and QA's one look at small review sheets rated what it saw POLISH. The FIGURE review gives a reviewer who
did not build the module each figure at 1920 x 1080 (the figure's panel as a projector shows it), at the rest state and the
end of every step, with what it must show: the slide's words, the step titles, the figure kind's must-be-true list
(course-visuals/knowledge/figure-truths.json) and what the meaning checks still say (kit_meaning.py): "block" (a clear
physical error), "note" (to judge in context), "waived" (accepted in the spec's "meaning_ok", with its reason).

Writes <out>/figures.json ([{slide, spec, pictures, words, step_titles, kinds, meaning}]) and the pictures beside it;
default out: <course>/working_claude/review/MNN_figures/. One figure at a time (the computer's browser pool).
Exit 0 written, 2 nothing to review / no browser.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import studio  # noqa: E402
import kit_meaning  # noqa: E402

sys.path.insert(0, studio.COMPILE)
sys.path.insert(0, studio.FACTORY_SCRIPTS)

PROJECTOR = (1920, 1080)


def module_figures(course, module, only=None):
    """[(slide id, spec path, its words)] - every kit figure on a slide or a task question of the module"""
    import content_script as cs
    import figure_fit
    p = cs.paths(course, module)
    script = cs.load(p["script"]) if os.path.isfile(p["script"]) else {"screens": []}
    by = {s["id"]: s for s in script.get("screens") or []}
    out, seen = [], set()
    figs, _ = figure_fit.deck_figures(course, module)
    rows = [(sid, sp) for sid, sp, _ in figs] + [(sid, sp) for sid, sp, _, _, _ in figure_fit.task_figures(course, module)]
    for sid, sp in rows:
        if (only and sid not in only) or sp in seen or not os.path.isfile(sp):
            continue
        seen.add(sp)
        s = by.get(sid) or {}
        words = {"title": s.get("title") or s.get("question") or "", "lines": cs.lines_of(s.get("text")) if s.get("text") else [],
                 "visual": s.get("visual") or "", "kind": s.get("kind") or ""}
        if s.get("question"):
            words["question"] = s["question"]
        out.append((sid, sp, words))
    return out


def review(items, out):
    """photograph each figure and write figures.json - [entries]"""
    os.makedirs(out, exist_ok=True)
    entries = []
    for sid, sp, words in items:
        spec = json.load(io.open(sp, encoding="utf-8"))
        res, why = studio.run(sp, sizes=(PROJECTOR,), step="all", out=out, split=True)
        r = ((res or {}).get("sizes") or {}).get("%dx%d" % PROJECTOR) or {}
        entries.append({
            "slide": sid, "spec": sp,
            "pictures": r.get("pictures") or ([r["shot"]] if r.get("shot") else []),
            "error": why or r.get("error"),
            "words": words,
            "step_titles": ["Start (before Next)"] + [str(s.get("title") or "") for s in spec.get("steps") or []],
            "kinds": kit_meaning.figure_kinds(spec),
            # BLOCK: a clear physical error (BROKEN); NOTE: judge it in context; waived: accepted on purpose, with the reason
            "meaning": {k: v for k, v in kit_meaning.analyse(spec, os.path.basename(sp)).items() if k in ("block", "note", "waived")},
        })
    io.open(os.path.join(out, "figures.json"), "w", encoding="utf-8").write(json.dumps(entries, ensure_ascii=False, indent=1))
    return entries


def main(argv=None):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("course", nargs="?")
    ap.add_argument("--module")
    ap.add_argument("--only", help="slide ids, comma separated")
    ap.add_argument("--specs", nargs="+")
    ap.add_argument("--out")
    ap.add_argument("--json", action="store_true")
    o = ap.parse_args(argv)
    if not studio.find_browser():
        print("no Chrome or Edge on this computer (set CF_BROWSER)")
        return 2
    if o.specs:
        items = [(os.path.basename(s).replace(".kit.json", ""), s, {}) for s in o.specs]
        out = o.out or os.path.join(os.path.dirname(os.path.abspath(o.specs[0])), "_figure_review")
    else:
        if not (o.course and o.module):
            ap.error("give <course> --module N, or --specs")
        items = module_figures(o.course, o.module, set(o.only.split(",")) if o.only else None)
        out = o.out or os.path.join(o.course, "working_claude", "review", "M%02d_figures" % int(o.module))
    if not items:
        print("No kit figure to review")
        return 2
    entries = review(items, out)
    if o.json:
        print(json.dumps({"out": out, "figures": entries}, ensure_ascii=False, indent=1))
    else:
        for e in entries:
            m = e["meaning"]
            print("%s  %d picture(s)%s%s" % (e["slide"], len(e["pictures"]), "  kinds: " + ", ".join(k["kind"] for k in e["kinds"]) if e["kinds"] else "",
                                              "  meaning: %d block, %d note, %d waived" % (len(m["block"]), len(m["note"]), len(m["waived"]))
                                              if any(m.values()) else ""))
        print("written: %s" % os.path.join(out, "figures.json"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
