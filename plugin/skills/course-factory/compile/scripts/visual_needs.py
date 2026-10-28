# -*- coding: utf-8 -*-
"""visual_needs.py - what a module's pictures still need, in one file the picture agent reads instead of the guides (2.73.0).

    visual_needs.py write <course> --module 4             working_claude\\visuals\\M04_VISUAL_NEEDS.md (and .json)
    visual_needs.py fill  <course> --module 4 --auto      each photo slot whose catalogue pick is good enough takes it - no agent

WHY (chem advanced, 2026-10-27): a builder read SKILL.md, the compile guide, the script guide and the kit catalogue, then the
module's script and build sheet, to find out which pictures were missing - for every module, 21 at once. Phase A
(compile_module.py --init-build, build_module.py) now builds the whole module with placeholders and writes this file:
one row per picture slot still to fill - its kind, its shape and its REAL size in px at 1280x800, 1024x768 and 1280x720
(measured by the audits on the placeholder, data-slot), the words of the slide it teaches, what it must show, and up to five
candidates from the course photo catalogue (scripts\\photo_catalogue.py) with their match scores; then the figures still at
their starter and the 3D scenes whose parts are not placed. Phase B reads this, course-visuals\\kit\\CATALOGUE.md and the
catalogue rows - nothing else - fills the slots, and runs ONE build.

--auto: a SLIDE's photo slot whose catalogue pick scored photo_catalogue.AUTO or more and is 800 px or more (each picture
given to one slot of the whole course - L58) is filled with no agent: the picture copied into the module with its record
(what it shows, where it came from, its rights - L56), the build sheet's entry pointed at it and marked "auto_picked", the
placeholder removed. A question's picture is never filled this way - its answers' places must be put on the real things.
Every auto pick is listed here and in the build's answer, and the visual review looks at it like any other picture.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import re
import shutil
import sys
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
SKILLS = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(SKILLS, "course-factory", "scripts"))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import content_script as cs  # noqa: E402
import workspace  # noqa: E402

SIZES = ("1280x800", "1024x768", "1280x720")


def paths(course, module):
    m = cs.mid(module)
    vdir = workspace.claude_path(course, "visuals")
    return m, os.path.join(vdir, "%s_VISUAL_NEEDS.json" % m), os.path.join(vdir, "%s_VISUAL_NEEDS.md" % m)


def catalogue():
    import photo_catalogue
    return photo_catalogue


def rows_of(course, module):
    """(rows, figures at their starter, scenes to place, auto picks already made)"""
    import compile_module as cm
    m = cs.mid(module)
    script = cs.load(cs.paths(course, module)["script"])
    build = cs.load(cm.build_path(course, module))
    try:
        slots = json.load(io.open(workspace.claude_path(course, "_build", "%s_slots.json" % m), encoding="utf-8"))
    except (OSError, ValueError):
        slots = {}
    figdir = workspace.claude_path(course, "figures", m)
    screens = build.get("screens") or {}
    rows, figs, scenes, picked = [], [], [], []
    for s in script.get("screens") or []:
        e = screens.get(s["id"])
        if not isinstance(e, dict):
            continue
        fig = (e.get("figure") or "").strip()
        p = cs.picture_of(s)
        if e.get("auto_picked"):
            picked.append({"id": s["id"], "where": cs.place(script, s["id"]), "picture": fig, "shows": p["shows"],
                           "score": (e["auto_picked"] or {}).get("score") if isinstance(e["auto_picked"], dict) else None})
        if e.get("placeholder") or cm.PLACEHOLDER_IMG.search(fig):
            words = s.get("question") if s.get("kind") in cs.TASKS else "%s\n%s" % (s.get("title") or "", s.get("text") or "")
            row = {"id": s["id"], "where": cs.place(script, s["id"]), "screen": s.get("kind"), "kind": p["kind"], "aspect": p["aspect"],
                   "shows": p["shows"], "words": (words or "").strip(), "placeholder": fig,
                   "px": {v: slots.get(v, {}).get(s["id"]) for v in SIZES if slots.get(v, {}).get(s["id"])},
                   "answers_on_it": sorted((e.get("areas") or {}).keys()) if s.get("kind") in cs.TASKS else [], "candidates": []}
            try:
                c = catalogue().candidates_for(course, module, s["id"])
            except Exception:                            # noqa: BLE001 - no catalogue yet: the row says so
                c = None
            if c:
                row["candidates"] = [{"path": x["path"], "score": x["score"], "px": [x.get("w"), x.get("h")], "origin": x.get("origin"),
                                      "what": (x.get("description") or "")[:200]} for x in c["candidates"]]
                row["pick"] = c["pick"]["path"] if c.get("pick") else None
            rows.append(row)
        elif fig.endswith(cm.KIT3D_SPEC) and os.path.isfile(os.path.join(figdir, fig)):
            try:
                if cs.load(os.path.join(figdir, fig)).get("_todo"):
                    scenes.append({"id": s["id"], "where": cs.place(script, s["id"]), "spec": os.path.join(figdir, fig),
                                   "shows": p["shows"]})
            except (OSError, ValueError):
                pass
        elif fig.endswith(".kit.json") and e.get("_figure"):
            figs.append({"id": s["id"], "where": cs.place(script, s["id"]), "spec": os.path.join(figdir, fig), "shows": p["shows"]})
    return rows, figs, scenes, picked


def write(course, module):
    """the needs file, JSON and Markdown - the Markdown's path"""
    m, jp, mp = paths(course, module)
    rows, figs, scenes, picked = rows_of(course, module)
    os.makedirs(os.path.dirname(jp), exist_ok=True)
    data = {"module": m, "written": datetime.now().isoformat(timespec="seconds"), "slots": rows, "figures_at_starter": figs,
            "scenes_to_place": scenes, "auto_picked": picked}
    io.open(jp, "w", encoding="utf-8", newline="\n").write(json.dumps(data, ensure_ascii=False, indent=1))
    L = ["# %s - the pictures still to fill (Phase B)" % m, "",
         "*Written by the build (2.73.0) - read this, `course-visuals\\kit\\CATALOGUE.md` and the candidates below; not the guides. "
         "Fill each slot in the build sheet (`working_claude\\script\\%s.build.json`), then ONE build: "
         "`build_module.py <course> --module %s` (only the changed slides are judged). Internal - never shipped.*" % (m, module), ""]
    if not (rows or figs or scenes):
        L.append("Nothing left to fill: every slot holds its picture.")
    for r in rows:
        px = ", ".join("%s: %d x %d px" % (v, r["px"][v][0], r["px"][v][1]) for v in SIZES if v in r["px"]) or "measured by the first build"
        L += ["## %s (%s) - %s slot, %s" % (r["where"], r["id"], r["kind"], r["aspect"]), "",
              "- **Must show:** %s" % (r["shows"] or "-"), "- **Its slot:** %s" % px,
              "- **The words it teaches:** %s" % " / ".join(x.strip() for x in r["words"].splitlines() if x.strip())[:700]]
        if r["answers_on_it"]:
            L.append("- **Answers placed on it** (move each box onto its thing, `\"areas\"` in %% of the picture): %s" % "; ".join(r["answers_on_it"]))
        if r["candidates"]:
            L += ["- **From the course's own pictures** (score 0-1 - %s):" % ("the pick: %s" % os.path.basename(r["pick"]) if r.get("pick")
                                                                            else "none good enough to fill with no agent")]
            L += ["    - %.2f · %s x %s px · `%s` - %s - %s" % (c["score"], c["px"][0], c["px"][1], c["path"], c["origin"], c["what"])
                  for c in r["candidates"]]
        else:
            L.append("- **From the course's own pictures:** no catalogue yet, or nothing matches - `photo_catalogue.py assign <course>`; "
                     "missing ones are in `visuals\\PHOTOS_TO_FIND.md`")
        L.append("")
    if figs:
        L += ["## Figures at their starter - check each teaches its slide (edit in the studio, never from nothing)", ""]
        L += ["- %s (%s): `%s` - %s" % (f["where"], f["id"], f["spec"], f["shows"]) for f in figs] + [""]
    if scenes:
        L += ["## 3D scenes whose parts are not placed yet (course-visuals\\kit3d\\SPEC.md)", ""]
        L += ["- %s (%s): `%s` - %s" % (x["where"], x["id"], x["spec"], x["shows"]) for x in scenes] + [""]
    if picked:
        L += ["## Picked with no agent (--auto) - the visual review checks each shows what its slide says", ""]
        L += ["- %s (%s): `%s`%s - %s" % (x["where"], x["id"], x["picture"], " (score %.2f)" % x["score"] if x["score"] else "", x["shows"])
              for x in picked] + [""]
    io.open(mp, "w", encoding="utf-8", newline="\n").write("\n".join(L))
    return mp


def fill(course, module, auto=True):
    """--auto: every slide's placeholder photo slot whose catalogue pick is good enough takes it. [(id, file)] filled"""
    import compile_module as cm
    import placeholder
    pc = catalogue()
    mdir, why = cm.module_folder(course, module)
    if not mdir:
        raise SystemExit("Stopped - " + why)
    bp = cm.build_path(course, module)
    build = cs.load(bp)
    script = cs.load(cs.paths(course, module)["script"])
    kinds = {s["id"]: s for s in script.get("screens") or []}
    used = pc.used_in_modules(course)
    done = []
    for sid, e in sorted((build.get("screens") or {}).items()):
        s = kinds.get(sid) or {}
        if not (isinstance(e, dict) and e.get("placeholder") and s.get("kind") == "slide"):
            continue
        c = pc.candidates_for(course, module, sid)
        pick = (c or {}).get("pick")
        if not pick or pick.get("id") in used or pick["score"] < pc.AUTO or max(pick.get("w") or 0, pick.get("h") or 0) < pc.PHOTO_FLOOR:
            continue
        ext = os.path.splitext(pick["path"])[1].lower() or ".jpg"
        stem = re.sub(r"[^a-z0-9]+", "_", (cs.picture_of(s)["shows"] or sid).lower()).strip("_")[:40] or sid
        name = "%s_%s_%s%s" % (cs.mid(module).lower(), sid, stem, ext)
        img = os.path.join(mdir, "assets", "img")
        os.makedirs(img, exist_ok=True)
        shutil.copyfile(pick["path"], os.path.join(img, name))
        rec = dict(pick.get("record") or {})
        rec.update({"title": rec.get("title") or (pick.get("description") or "")[:80],
                    "description": rec.get("description") or cs.picture_of(s)["shows"] or pick.get("description"),
                    "shows": rec.get("shows") or cs.picture_of(s)["shows"],
                    "source": rec.get("source") or ("Novikontas old course" if pick["source"] == "old course" else "course knowledge base"),
                    "author": rec.get("author") or "Novikontas", "license": rec.get("license") or "owner-cleared (L33)",
                    "rights_state": rec.get("rights_state") or "OWNER_CLEARED", "url_or_origin": rec.get("url_or_origin") or pick["origin"],
                    "catalogue_id": pick["id"], "teaching_purpose": "%s - %s" % (sid, s.get("title") or ""), "auto_picked": True,
                    "width": pick.get("w"), "height": pick.get("h")})
        mp = os.path.join(img, "_photo_meta.json")
        try:
            meta = json.load(io.open(mp, encoding="utf-8"))
        except (OSError, ValueError):
            meta = {}
        meta[name] = rec
        io.open(mp, "w", encoding="utf-8", newline="\n").write(json.dumps(meta, ensure_ascii=False, indent=2) + "\n")
        placeholder.remove(mdir, sid)
        for k in ("placeholder", "_placeholder"):
            e.pop(k, None)
        e["figure"] = "assets/img/" + name
        e["auto_picked"] = {"catalogue_id": pick["id"], "score": pick["score"], "from": pick["origin"]}
        used.add(pick["id"])
        done.append((sid, name))
    if done:
        cs.save(bp, build)
    write(course, module)
    return done


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("cmd", choices=("write", "fill"))
    ap.add_argument("course")
    ap.add_argument("--module", required=True)
    ap.add_argument("--auto", action="store_true")
    a = ap.parse_args(argv)
    course = workspace.work_folder(a.course, create=False)
    if a.cmd == "write":
        print(write(course, a.module))
        return 0
    if not a.auto:
        print("fill needs --auto (a person or an agent fills the rest by hand, from the needs file)")
        return 2
    done = fill(course, a.module)
    print("Filled with no agent: %s" % (", ".join("%s <- %s" % x for x in done) if done else "nothing - no slot's pick is good enough"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
