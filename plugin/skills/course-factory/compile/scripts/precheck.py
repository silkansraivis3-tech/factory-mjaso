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
  * a slide's photograph nobody recorded opening, whose record copies the script's wanted picture or names little of
    it, that its opener said does not fit, or that the course calls its own with no watermark looked for; one with a
    third party's mark called the course's own, or with printed words enlarged by Real-ESRGAN
  * a task page's picture with no record beside it (_figure_meta.json, _photo_meta.json), and two task pages on the
    same drawing that name the same part differently
NOTE (said, never stops it):
  * a picture whose rights are not cleared (RIGHTS_REVIEW_REQUIRED) - the build carries on; publishing is refused
  * a photograph of 800-1023 px - the compile enlarges it (L62), a larger original would be sharper; from 1024 px it is
    accepted without a note
  * a teaching slide with more than the word guideline's picture_from words and no picture (theory-rules.json "slide"):
    fine when its words read on their own; else a picture goes beside the words, or the slide is shown in steps - past
    steps_from the build does that by itself
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
from image_size import PHOTO_ACCEPT_LONG, PHOTO_FLOOR, PHOTO_MIN_LONG, found_size, pixel_size  # noqa: E402

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
    forced, runs = None, []   # L62's runs of one forced template
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
        for key in ("figure", "figure_b", "aside", "custom_figure"):          # 2.116.0: a custom figure's file is there too
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
            has_pic = has_pic or key in ("figure", "custom_figure")
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
        has_pic = has_pic or bool(b.get("table"))      # the module's comparison table is the slide's picture
        ins = b.get("inset") or {}
        if ins.get("photo"):
            rel = ins["photo"].replace("\\", "/")
            if not os.path.isfile(os.path.join(mdir, rel)) and not parked(mdir, rel):
                must.append("%s: its inset photograph %s is not in the module folder" % (where, rel))
            else:
                photos.setdefault(rel, []).append(sid)
        # 2.116.0 (operator, 2026-11-09): no picture quota - a slide may have no picture when its words read on their own.
        # Dense words with no picture are a note only; the "three in a row" rule is gone.
        if s.get("kind") == "slide" and not s.get("recap"):
            if not has_pic and words > cm.PICTURE_FROM:
                notes.append("%s: %d words and no picture beside them - over %d words a picture goes beside the words, or the "
                             "slide is shown in steps (\"parts\" in the build sheet); past %d words the build shows it in steps "
                             "by itself (theory-rules.json \"slide\")" % (where, words, cm.PICTURE_FROM, cm.STEPS_FROM))
    if forced and len(forced[1]) >= FORCED_RUN:
        runs.append(forced)
    for tid, ids in runs:
        notes.append("the build sheet forces the template %s on %d slides in a row (%s ... %s) - the compiler chooses the template "
                     "and varies the look of neighbouring slides itself (L62); take \"template\" out unless a slide really needs it"
                     % (tid, len(ids), ids[0], ids[-1]))
    soft, kept, renders, ai, unclear = [], [], [], [], []
    # the photographs: found large enough, or kept with a reason
    for rel, ids in sorted(photos.items()):
        if str(cm.photo_meta(mdir, rel).get("rights_state") or "").upper() == "RIGHTS_REVIEW_REQUIRED":
            unclear.append("%s (on %s)" % (os.path.basename(rel), ", ".join(sorted(set(ids)))))
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
            if was and max(was) < PHOTO_ACCEPT_LONG:
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
        elif long < PHOTO_ACCEPT_LONG:
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
    if unclear:
        notes.append("%d picture(s) with rights not cleared - the build carries on; publishing to the tablets is refused while "
                     "any is left (course-tablet-publisher): %s. The owner clears each by name (course-visuals "
                     "check_assets.py clear), or it is replaced" % (len(unclear), ", ".join(unclear)))
    if soft:
        notes.append("%d photograph(s) found under %d px (the size it was found at - the compile's enlargement is not judged; L62) "
                     "- a larger original would be sharper: %s"
                     % (len(soft), PHOTO_ACCEPT_LONG, ", ".join(soft)))
    for found in (photo_looks(script, mdir, photos, rebuild), task_picture_records(script, sheets, mdir, rebuild),
                  same_drawing_names(script, sheets, mdir, rebuild)):
        must += found[0]
        notes += found[1]
    return must, notes


# ------------------------------------------------------------------ what a photograph shows, and what is printed on it
GENERIC = {"photo", "photograph", "picture", "image", "drawing", "view", "close", "seen", "showing", "show", "real", "type",
           "tile", "tiles", "example", "labelled", "labeled", "board", "ship", "vessel"}
COVER = 3                # a photograph's record names at least a third of what its slide's picture must show


def main_words(text):
    """the words that name what a picture must show - the photo catalogue's tokens without the words any picture has"""
    import photo_catalogue as pc
    return {t for t in pc.tokens(text) if t not in GENERIC}


def photo_looks(script, mdir, photos, rebuild=False):
    """(must, notes) - each slide photograph's record written by whoever OPENED it: a dated look, what it shows in its own
    words (never the script's wanted picture copied in), something the slide's picture names in it, its verdict for the
    slide, a watermark or credit looked for; never a third party's mark on one the record calls the course's own, and never
    printed words enlarged by Real-ESRGAN. A must for the course's own pictures (matched only by their old slide's words) and
    a note for a downloaded one; a rebuild's photographs: notes, but a mark, invented letters and a copied record stop it"""
    import compile_module as cm
    import content_script as cs
    import photo_catalogue as pc
    from check_assets import NAMED_CLEARANCE, NO_MARK, OWN_RIGHTS
    from upscale_photos import holds_words
    by_id = {s.get("id"): s for s in script.get("screens", [])}
    must, notes = [], []
    for rel, ids in sorted(photos.items()):
        if cm.PLACEHOLDER_IMG.search(rel) or not rel.startswith("assets/"):
            continue
        meta, on = cm.photo_meta(mdir, rel), ", ".join(sorted(set(ids)))
        name = os.path.basename(rel)
        if not meta:
            (notes if rebuild else must).append("%s (on %s) has no record in its _photo_meta.json - where it is from, its rights "
                                                "and what it shows (L12)" % (rel, on))
            continue
        # the course's own pictures (old course, knowledge base, the catalogue's picks) are matched by the words of the slide
        # or page they sat on - what they show is known only from a look; a downloaded one comes with its page's own words
        own = origin_of(meta) == "old" or bool(meta.get("catalogue_id") or meta.get("auto_picked"))
        soft = notes if rebuild or not own else must
        said = " ".join(pc.as_words(meta.get(k) or "") for k in ("title", "description", "shows", "fits_slide"))
        rs, cleared = str(meta.get("rights_state") or ""), NAMED_CLEARANCE.match(str(meta.get("cleared_by") or "").strip())
        marks = meta.get("marks_seen")
        if marks is not None and not NO_MARK.match(str(marks)) and rs in OWN_RIGHTS and not cleared:
            must.append("%s (on %s) carries a third party's mark (\"%s\"), yet its record says %s - it is not the course's own: "
                        "rights_state RIGHTS_REVIEW_REQUIRED and the credit recorded, or another picture" % (rel, on, str(marks)[:60], rs))
        if str(meta.get("enlarged") or "").startswith("Real-ESRGAN") and holds_words(name, meta):
            must.append("%s (on %s) holds printed words or labels (%s) and was enlarged by Real-ESRGAN, which makes them sharp "
                        "and wrong: put back its original (working_claude/photo_originals) and record \"ai_enlarge\": false"
                        % (rel, on, holds_words(name, meta)))
        if not pc.VERIFIED.match(str(meta.get("visually_verified") or "")):
            if not own:
                continue                                 # check_assets asks a downloaded one's record for it
            soft.append("%s (on %s): nobody has recorded opening it - \"visually_verified\": \"yes - <what you saw> <YYYY-MM-DD>\" "
                        "once you looked, with what it shows in your own words" % (rel, on))
            continue
        if marks is None and rs in OWN_RIGHTS and not cleared and not cm.is_generated(meta):
            soft.append("%s (on %s) is called the course's own (%s), and nobody recorded looking for a watermark or credit "
                        "printed on it: \"marks_seen\": the mark word for word, or \"none\"" % (rel, on, rs))
        if str(meta.get("fits_slide") or "").strip().lower().startswith("no"):
            soft.append("%s (on %s): whoever opened it said it does not show what the slide names (\"%s\") - another picture"
                        % (rel, on, str(meta["fits_slide"])[:80]))
            continue
        for sid in sorted(set(ids)):
            pic = cs.picture_of(by_id[sid]) if sid in by_id else {}
            if pic.get("kind") != "photo" or not pic.get("shows"):
                continue
            wants = pic["shows"]
            if not cm.is_generated(meta) and pc.copied(" ".join(pc.as_words(meta.get(k) or "") for k in ("description", "shows")), wants):
                (notes if rebuild else must).append(
                    "%s (on %s): its record's description is the script's wanted picture, word for word (\"%s\") - not what the "
                    "file shows. Open it and write what is in it" % (rel, sid, wants[:80]))
            elif not own or str(meta.get("fits_slide") or "").strip().lower().startswith("yes"):
                continue                                 # its page's own words, or whoever opened it said how it fits
            elif len(main_words(wants) & main_words(said)) * COVER < len(main_words(wants)):
                soft.append("%s (on %s): what its record says it shows (\"%s\") has little of what the slide's picture names "
                            "(\"%s\"; missing: %s) - another picture, or the record says how it shows them (\"fits_slide\")"
                            % (rel, sid, pc.as_words(meta.get("description") or meta.get("shows") or "")[:80], wants[:80],
                               ", ".join(sorted(main_words(wants) - main_words(said)))))
    return must, notes


# ------------------------------------------------------------------ the pictures of the trainee task pages
def task_picture_records(script, sheets, mdir, rebuild=False):
    """(must, notes) - every picture a task page shows from the module folder carries its record beside it: a drawing its
    _figure_meta.json entry, a photograph its _photo_meta.json entry (L12) - found here, before the build, not by the QA's
    check_assets after it"""
    import content_script as cs
    out = []
    for s in script.get("screens", []):
        if s.get("kind") not in cs.TASKS:
            continue
        rel = str((sheets.get(s["id"]) or {}).get("figure") or "").replace("\\", "/")
        if not rel.startswith("assets/") or "_placeholder_" in rel or not os.path.isfile(os.path.join(mdir, rel)):
            continue
        meta_name = "_photo_meta.json" if rel.lower().endswith(PHOTO_EXT) else "_figure_meta.json"
        try:
            rec = json.load(io.open(os.path.join(mdir, os.path.dirname(rel), meta_name), encoding="utf-8")).get(os.path.basename(rel))
        except (OSError, ValueError, AttributeError):
            rec = None
        if not isinstance(rec, dict):
            out.append("%s (%s's picture) has no entry in %s/%s beside it - what it shows, whose it is, its rights, that it was "
                       "looked at (L12)" % (rel, s["id"], os.path.dirname(rel), meta_name))
    return ([], out) if rebuild else (out, [])


AREA_TAG = re.compile(r"<g\b([^>]*?)(/?)>|</g>|<rect\b([^>]*)>")
SHAPE_TAG = re.compile(r"<(?:rect|polygon|polyline|path|line|circle|ellipse)\b[^>]*>")


def named_areas(svg):
    """[(name, (x, y, w, h))] - each data-name group of a drawing and its tap area (its rect class="hit")"""
    out, stack = [], []
    for m in AREA_TAG.finditer(svg):
        if m.group(0) == "</g>":
            if stack:
                stack.pop()
        elif m.group(0).startswith("<g"):
            if not m.group(2):
                n = re.search(r'\bdata-name="([^"]+)"', m.group(1) or "")
                stack.append(n.group(1) if n else None)
        elif re.search(r'\bclass="[^"]*\bhit\b', m.group(3) or ""):
            name = next((x for x in reversed(stack) if x), None)
            box = [re.search(r'\b%s="(-?[\d.]+)"' % k, m.group(3)) for k in ("x", "y", "width", "height")]
            if name and all(box):
                out.append((name, tuple(float(b.group(1)) for b in box)))
    return out


def overlap(a, b):
    """how much two boxes are one: their shared area over their joint area"""
    w = min(a[0] + a[2], b[0] + b[2]) - max(a[0], b[0])
    h = min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1])
    if w <= 0 or h <= 0:
        return 0.0
    both = w * h
    return both / (a[2] * a[3] + b[2] * b[3] - both)


def same_drawing_names(script, sheets, mdir, rebuild=False):
    """(must, notes) - two task pages drawn on the same drawing call the same part by the same name: a door that is an
    "air intake" on one question and an "entrance" on the next teaches the trainee nothing true"""
    import content_script as cs
    import photo_catalogue as pc
    draws = {}
    for s in script.get("screens", []):
        rel = str((sheets.get(s.get("id")) or {}).get("figure") or "").replace("\\", "/")
        if s.get("kind") in cs.TASKS and rel.lower().endswith(".svg") and rel not in draws:
            try:
                svg = io.open(os.path.join(mdir, rel), encoding="utf-8").read()
            except OSError:
                continue
            draws[rel] = (s["id"], set(x for x in SHAPE_TAG.findall(svg) if "hit" not in x), named_areas(svg))
    out, keys = [], sorted(draws)
    for i, a in enumerate(keys):
        for b in keys[i + 1:]:
            (qa, sa, na), (qb, sb, nb) = draws[a], draws[b]
            if not sa or not sb or len(sa & sb) < 0.5 * len(sa | sb):
                continue                                  # not the same drawing underneath
            for name_a, box_a in na:
                for name_b, box_b in nb:
                    ta, tb = set(pc.tokens(name_a)), set(pc.tokens(name_b))
                    if overlap(box_a, box_b) >= 0.6 and ta and tb and len(ta & tb) < 0.5 * len(ta | tb):
                        out.append("%s and %s are the same drawing, but the part at one place is \"%s\" on %s and \"%s\" on %s "
                                   "- one part, one name; draw a different part where a different one is meant"
                                   % (a, b, name_a, qa, name_b, qb))
    return ([], out) if rebuild else (out, [])


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
