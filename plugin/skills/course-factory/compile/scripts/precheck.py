#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""precheck.py - what would make a build fail or look poor, found in seconds BEFORE anything is built (2.65.0).

    precheck.py <course> --module 1            exit 0 nothing stops the build · 1 something must be fixed first · 2 bad input

WHY (owner, 2026-10-26: "how can we cut time and usage, but quality the same or better"): a failed build costs a whole
round - the figures, the compile, every check, a review - and what failed it was often already visible in the files.
The gas course's Module 1 came out with one layout on 29 of 33 slides because its build sheet forced it, and with
photographs of 350-770 px stretched across half a projector. This reads the approved script, the build sheet and the
picture files - no browser, no build - and says what to fix first.

MUST (the build stops before its figures; build_module.py runs this first):
  * a template or variant the factory does not have (L61), named in the build sheet
  * a picture the build sheet names that is not there (figure, figure_b, inset, aside, a photograph inside a drawing)
  * a photograph under 800 px on its long side - enlarging cannot make it sharp: find a larger original (1600 px or
    more), or record in its _photo_meta.json entry why this one stays: "low_resolution_ok": "<reason>"
  * a teaching slide with more than 60 words and no picture (L61: dense text has a picture beside it)
  * three teaching slides in a row with no picture (L61)
NOTE (said, never stops it):
  * a photograph of 800-1599 px - the compile enlarges it (L62), a larger original would be sharper
  * the same template forced on three slides in a row or more - the compiler chooses and varies the look (L62); a
    forced template only takes that away
The still picture inside a 3D scene (its poster) is not judged: the live scene is what the room sees. A still the module
renders from its own 3D model is a note (render it again larger), never a stop. A picture from the old course has no
larger original anywhere: the stop says so - find a larger photograph of the same thing, or write why it stays.
A REBUILD of a module already built (fix.py rebuild, check(..., rebuild=True)) is never stopped by the small pictures
it already had: they are notes - a factory update must not wait on replacing them (gas course: 100+ old-course
pictures under 800 px across 22 modules).
"""
from __future__ import annotations

import argparse
import io
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
SKILLS = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(SKILLS, "course-factory", "scripts"))
sys.path.insert(0, os.path.join(SKILLS, "course-visuals", "scripts"))
from image_size import PHOTO_FLOOR, PHOTO_MIN_LONG, found_size, pixel_size  # noqa: E402

PHOTO_EXT = (".jpg", ".jpeg", ".png", ".webp", ".gif")
FORCED_RUN = 3


def parked(mdir, rel):
    """a picture the build sheet names that waits in assets/img/_unused/ - the compile brings it back with its record
    (compile_module.restore), so it is there (2.66.0: the timed gas M02 build's run 5 was stopped for one)"""
    rel = rel.replace("\\", "/")
    if not rel.startswith("assets/img/"):
        return None
    p = os.path.join(mdir, "assets", "img", "_unused", rel[len("assets/img/"):])
    return p if os.path.isfile(p) else None


def photo_size(course, mdir, m, rel):
    """the size the photograph was found at - its kept original's while the module's file is still the compile's
    enlargement of it (L62), the file's own once a new picture has been put in its place"""
    keep = os.path.join(course, "working_claude", "photo_originals", m, os.path.basename(rel))
    here = os.path.join(mdir, rel)
    return found_size(here if os.path.isfile(here) else (parked(mdir, rel) or here), keep if os.path.isfile(keep) else None)


def origin_of(meta):
    """'render' (a still of the module's own 3D model), 'old' (the old course's material - no larger original), or ''"""
    o = "%s %s %s" % (meta.get("url_or_origin") or "", meta.get("source") or "", " ".join(meta.get("shows") or []))
    if re.search(r"render of|3D model still", o, re.I):
        return "render"
    if re.search(r"old.course|\.pptx\b|course hand-out|knowledge base", o, re.I):
        return "old"
    return ""


def check(course, module, rebuild=False):
    """(must, notes) - each a line the person reads; rebuild: a module already built - its small pictures are notes"""
    import content_script as cs
    import compile_module as cm
    m = cs.mid(module)
    p = cs.paths(course, module)["script"]
    if not os.path.isfile(p):
        return None, ["there is no content script for module %s: %s" % (module, p)]
    script = cs.load(p)
    bp = cm.build_path(course, module)
    build = json.load(io.open(bp, encoding="utf-8")) if os.path.isfile(bp) else {}
    mdir, _ = cm.module_folder(course, module)
    mdir = mdir or os.path.join(course, "modules", "module%02d" % int(module))
    figdir = os.path.join(course, "working_claude", "figures", m)
    sheets = build.get("screens") or {}
    must, notes = [], []
    photos = {}                     # rel -> [slide ids]
    run_plain, forced, runs = [], None, []   # L61's run of slides with no picture; L62's runs of one forced template
    for s in script.get("screens", []):
        if s.get("kind") not in cs.INSTRUCTOR:
            continue
        sid, b = s["id"], sheets.get(s["id"]) or {}
        where = "%s (%s)" % (cs.place(script, sid), sid)
        lines = cs.lines_of(s.get("text"))
        words = cs.wc(" ".join(lines))
        # the template and variant asked for by name
        want = (b.get("template") or "").split(".v")[0]
        if want and want not in cm.TEMPLATES:
            must.append("%s: the build sheet asks for the template \"%s\" - the templates are %s (L61)"
                        % (where, b["template"], ", ".join(sorted(cm.TEMPLATES))))
        elif want and b.get("variant") and b["variant"] not in cm.TEMPLATES[want]["variants"]:
            must.append("%s: the template %s has no variant \"%s\" - its variants are %s (L61)"
                        % (where, want, b["variant"], ", ".join(cm.TEMPLATES[want]["variants"])))
        if s.get("kind") == "slide":
            if want and forced and forced[0] == want:
                forced[1].append(sid)
            else:
                if forced and len(forced[1]) >= FORCED_RUN:
                    runs.append(forced)
                forced = (want, [sid]) if want else None
        # every picture the slide names is there
        has_pic = False
        for key in ("figure", "figure_b", "aside"):
            rel = (b.get(key) or "").replace("\\", "/")
            if not rel:
                continue
            body, err = cm.read_figure(mdir, rel, figdir)
            if err and parked(mdir, rel):
                body, err = "", None
                notes.append("%s: its %s %s waits in assets/img/_unused/ - the build brings it back, with its record" % (where, key, rel))
            if err:
                must.append("%s: its %s %s %s" % (where, key, rel, err))
                continue
            has_pic = has_pic or key == "figure"
            if rel.lower().endswith(PHOTO_EXT):
                photos.setdefault(rel, []).append(sid)
            poster = bool(re.search(r"\bdata-(?:3d|model3d|model)\b", body or ""))   # a 3D scene's still: not judged
            for inner in ([] if poster else cm.IMG_SRC.findall(body or "")):
                if inner.lower().endswith(PHOTO_EXT):
                    photos.setdefault(inner, []).append(sid)
                    if not os.path.isfile(os.path.join(mdir, inner)):
                        must.append("%s: its drawing %s shows %s, which is not in the module folder" % (where, rel, inner))
        for t in b.get("tiles") or []:                 # 2.67.0 - photo tiles: each is there, and is a picture of the slide
            rel = str(t.get("photo") if isinstance(t, dict) else t or "").replace("\\", "/")
            if not rel:
                continue
            if not os.path.isfile(os.path.join(mdir, rel)) and not parked(mdir, rel):
                must.append("%s: its tile %s is not in the module folder" % (where, rel))
            else:
                photos.setdefault(rel, []).append(sid)
                has_pic = True
        ins = b.get("inset") or {}
        if ins.get("photo"):
            rel = ins["photo"].replace("\\", "/")
            if not os.path.isfile(os.path.join(mdir, rel)) and not parked(mdir, rel):
                must.append("%s: its inset photograph %s is not in the module folder" % (where, rel))
            else:
                photos.setdefault(rel, []).append(sid)
        # L61 - dense words have a picture; never three teaching slides in a row without one
        if s.get("kind") == "slide" and not s.get("recap"):
            if not has_pic and words > cm.DENSE_WORDS:
                must.append("%s: %d words and no picture beside them - dense text always has a drawing, a photograph, an "
                            "animation or a 3D model beside it (L61); add one in the build sheet, or shorten it in the script"
                            % (where, words))
            run_plain = run_plain + [sid] if not has_pic else []
            if len(run_plain) == cm.NO_VISUAL_RUN + 1:
                must.append("%s: three teaching slides in a row without a picture (%s) - give one of them a picture (L61)"
                            % (where, ", ".join(run_plain)))
    if forced and len(forced[1]) >= FORCED_RUN:
        runs.append(forced)
    for tid, ids in runs:
        notes.append("the build sheet forces the template %s on %d slides in a row (%s ... %s) - the compiler chooses the template "
                     "and varies the look of neighbouring slides itself (L62); take \"template\" out unless a slide really needs it"
                     % (tid, len(ids), ids[0], ids[-1]))
    soft, kept, renders, ai = [], [], [], []
    # the photographs: found large enough, or kept with a reason
    for rel, ids in sorted(photos.items()):
        size = photo_size(course, mdir, m, rel)
        if not size:
            continue
        long = max(size)
        meta = cm.photo_meta(mdir, rel)
        on = ", ".join(sorted(set(ids)))
        origin = origin_of(meta)
        # 2.68.0 - made sharp by the local enlarger (upscale_photos.py): judged at the size it was FOUND, said, never a stop
        keep = os.path.join(course, "working_claude", "photo_originals", m, os.path.basename(rel))
        if str(meta.get("enlarged") or "").startswith("Real-ESRGAN") and os.path.isfile(keep):
            was = pixel_size(keep)
            if was and max(was) < PHOTO_MIN_LONG:
                ai.append("%s from %dx%d" % (os.path.basename(rel), was[0], was[1]))
            continue
        if long < PHOTO_MIN_LONG and origin == "render":
            renders.append("%s %dx%d" % (os.path.basename(rel), size[0], size[1]))
        elif long < PHOTO_FLOOR and not (meta.get("low_resolution_ok") or "").strip() and (rebuild or origin == "old"):
            # 2.73.2 (owner, 2026-10-28: "if there is any pictures in old course it rescales upgrades quality for them and
            # reuses them") - the course's own picture is reused, enlarged on this computer by the build (upscale_photos.py)
            kept.append("%s %dx%d" % (os.path.basename(rel), size[0], size[1]))
        elif long < PHOTO_FLOOR and not (meta.get("low_resolution_ok") or "").strip():
            find = ("it comes from the old course (%s), which has no larger original: find a larger photograph of the same "
                    "thing (course-visuals, visual-sourcer)" % (meta.get("source") or "its own material")[:60]
                    if origin == "old" else "find a larger original")
            must.append("%s (on %s) is only %d x %d px - no enlargement makes it sharp: %s (%d px or more on its long side), "
                        "or write why this one stays in its _photo_meta.json entry: \"low_resolution_ok\": \"<reason>\""
                        % (rel, on, size[0], size[1], find, PHOTO_MIN_LONG))
        elif long < PHOTO_MIN_LONG:
            soft.append("%s %dx%d" % (os.path.basename(rel), size[0], size[1]))
    if kept:
        notes.append("%d picture(s) under %d px - the course's own (old course, knowledge base) or ones the module already "
                     "had - reused and enlarged (Real-ESRGAN when it is installed here: upscale_photos.py --check); a "
                     "photorealistic generated one would be sharper: %s" % (len(kept), PHOTO_FLOOR, ", ".join(kept)))
    if ai:
        notes.append("%d photograph(s) made sharp by the local enlarger (Real-ESRGAN) - it rebuilds detail, so a real larger "
                     "photograph would still be truer: %s" % (len(ai), ", ".join(ai)))
    else:
        tiny = [x for x in soft + kept + [m_.split(" (on ")[0] for m_ in must if "no enlargement makes it sharp" in m_]]
        if tiny:
            notes.append("course-visuals/scripts/upscale_photos.py <course> --modules N makes the photographs under 1000 px sharp "
                         "on this computer (Real-ESRGAN, nothing sent anywhere; never one with words or numbers in it)")
    if renders:
        notes.append("%d still(s) rendered from the module's own 3D model under %d px - render again at %d px or more: %s"
                     % (len(renders), PHOTO_MIN_LONG, PHOTO_MIN_LONG, ", ".join(renders)))
    if soft:
        notes.append("%d photograph(s) found under %d px (the size it was found at - the compile's enlargement is not judged; L62) "
                     "- a larger original would be sharper: %s"
                     % (len(soft), PHOTO_MIN_LONG, ", ".join(soft)))
    return must, notes


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("course")
    ap.add_argument("--module", required=True)
    ap.add_argument("--rebuild", action="store_true", help="a module already built: the small pictures it has are notes")
    a = ap.parse_args(argv)
    import workspace
    course = workspace.work_folder(a.course, create=False)
    must, notes = check(course, a.module, rebuild=a.rebuild)
    if must is None:
        print("Stopped - " + notes[0])
        return 2
    if must:
        print("PRE-CHECK - %d thing(s) to fix before building module %s:" % (len(must), a.module))
        print("\n".join("  - " + x for x in must))
    if notes:
        print("PRE-CHECK notes:")
        print("\n".join("  - " + x for x in notes))
    if not must:
        print("PRE-CHECK - nothing stops module %s from building." % a.module)
    return 1 if must else 0


if __name__ == "__main__":
    sys.exit(main())
