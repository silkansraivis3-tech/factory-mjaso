# -*- coding: utf-8 -*-
"""fault_report - where a built course broke the factory's own rules, for the owner to read (factory_trial.py report).

    FAULTS.html + faults.json + faults/<pictures>   written beside the trial's scorecard

One entry per fault, by module and slide or task page: the picture of that slide, the rule that applies (quoted short, with
its file), what the build did (a measured fact), the kind, which check found it, and an empty field for the owner's decision.
Two sources: the rule checks this script runs on the built deck itself (a picture's shape against the box of the blueprint it
landed in, the words against that blueprint's budget, slides the fit gate found cut) and what the judges of the run found
(the walk review, QA, the 3D and figure reviews). Nothing here changes a course or the factory.
"""
from __future__ import annotations

import html
import io
import json
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
COMPILE = os.path.join(os.path.dirname(HERE), "compile", "scripts")
KNOWLEDGE = "course-module-ui/knowledge/"
KINDS = ("layout", "overflow_cut", "words", "blueprint", "3d", "highlight", "task_page", "script", "other")
CUT_KINDS = ("cut", "spill", "picture", "figure")
DECISIONS = ("fix it in the factory", "leave it", "not a fault")

SLIDE = re.compile(r'<section class="slide"[^>]*>.*?(?=<section class="slide"|\Z)', re.S)
IMG = re.compile(r'<img\b[^>]*?\bsrc="([^"]+)"')


def kind_of(text):
    """the kind a judge's sentence is about"""
    t = str(text or "")
    if re.search(r"(?i)\b(overflow|cut off|cut|cropped|clipped|spill|scrolls?|off the screen|overlap)", t):
        return "overflow_cut"
    if re.search(r"(?i)\b(3d|scene|camera|turn the model)\b", t):
        return "3d"
    if re.search(r"(?i)\b(highlight|lit|stop \d+: .*light)", t):
        return "highlight"
    if re.search(r"(?i)\b(blueprint|template|same look)\b", t):
        return "blueprint"
    if re.search(r"(?i)\b(layout|aspect|portrait|landscape|box|vertical)\b", t):
        return "layout"
    if re.search(r"(?i)\btask page|\btasks/|\bquestion page", t):
        return "task_page"
    if re.search(r"(?i)\b(words?|text|wording|caption|reads|too much)\b", t):
        return "words"
    return "other"


def _json(path):
    try:
        with io.open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def _aspect_of_file(p):
    try:
        from PIL import Image
        with Image.open(p) as im:
            w, h = im.size
        return w / float(h) if h else None
    except Exception:  # noqa: BLE001
        return None


def slide_picture(html_slide, deck_dir):
    """(family, aspect, how it is said) of a slide's main picture as the compiler plans one: a photograph or a row of them
    (their files' own shape), a 3D scene, a drawing - (None, None, "") for a slide with none"""
    if COMPILE not in sys.path:
        sys.path.insert(0, COMPILE)
    import layout_plan
    files = [s for s in IMG.findall(html_slide) if "/assets/img/" in s.replace("\\", "/")]
    if files:
        asp = [_aspect_of_file(os.path.normpath(os.path.join(deck_dir, s))) for s in files]
        asp = [a for a in asp if a]
        if not asp:
            return None, None, ""
        family = "tiles" if len(files) > 1 else "photo"
        return family, min(asp), "a photograph" if len(files) == 1 else "%d photographs (the narrowest counts)" % len(files)
    if " data-kit3d=" in html_slide:
        return "3d", layout_plan.figure_aspect(html_slide), "a 3D scene"
    if " data-kit2d=" in html_slide:
        return "drawing", layout_plan.figure_aspect(html_slide), "a drawing"
    return None, None, ""


def rule_checks(deck, slides):
    """[fault] the deck breaks by its own blueprints: the picture's shape against its box, the words against its budget.
    slides: factory_trial.scan_deck's list (id, template, variant, seen_words, parts)"""
    if COMPILE not in sys.path:
        sys.path.insert(0, COMPILE)
    import layout_plan as lp
    page = io.open(deck, encoding="utf-8", errors="replace").read()
    deck_dir = os.path.dirname(deck)
    by_id = {s["id"]: s for s in slides}
    out = []
    for block in SLIDE.findall(page):
        sid = (re.search(r'\bid="([^"]+)"', block) or [None, ""])[1]
        tid = (re.search(r'\bdata-template="([\w-]+)', block) or [None, ""])[1]
        var = (re.search(r'\bdata-variant="([\w-]+)"', block) or [None, ""])[1]
        bp_id = "%s.%s" % (tid, var)
        bp = lp.LIB.get(bp_id) or {}
        fits = bp.get("fits") or {}
        if not fits or sid not in by_id:
            continue
        s = by_id[sid]
        family, aspect, said = slide_picture(block, deck_dir)
        src = "%s%sblueprints/%s.json" % (KNOWLEDGE, "", bp_id)
        if family and family not in (fits.get("pictures") or []):
            out.append(_fault(sid, "layout", "rule check: picture against its blueprint",
                              "%s: \"%s\" - it takes %s" % (bp_id, bp.get("for", ""), ", ".join(fits.get("pictures") or []) or "no picture"),
                              src + " fits.pictures",
                              "%s sits in %s, which takes no %s" % (said, bp_id, family) + _suit(lp, bp_id, s, family, aspect)))
        elif family and aspect:
            lo, hi = (fits.get("aspect") or {}).get(family) or [0, 99]
            if not lo <= aspect <= hi:
                out.append(_fault(sid, "layout", "rule check: picture against its blueprint",
                                  "%s: \"%s\" - its box is for a %s of %g-%g:1" % (bp_id, bp.get("for", ""), family, lo, hi),
                                  src + " fits.aspect.%s = [%g, %g]" % (family, lo, hi),
                                  "%s, %.2f:1, placed in %s (%s box, %s) - outside %g-%g:1" % (
                                      said, aspect, bp_id, bp.get("shape"), bp.get("cols") or bp.get("grid") or "", lo, hi)
                                  + _suit(lp, bp_id, s, family, aspect)))
        key = (fits.get("budget") or {}).get(family) if family else None
        most = lp.budget(key) if key is not None else None
        use = max(s["parts"].values(), default=0) if fits.get("group") == "parts" else s["seen_words"]
        if isinstance(most, dict):
            most = most.get("words")
        limit, name = most, "layout-templates.json budgets.%s" % key
        if fits.get("words") and fits["words"][1] < (limit if limit is not None else 10 ** 6):
            limit, name = fits["words"][1], src + " fits.words"
        if limit is not None and use > limit:
            out.append(_fault(sid, "words", "rule check: words against the budget of the slide's own shape",
                              "a slide in %s holds up to %d words (%s)" % (bp_id, limit, name), name,
                              "%d words the room sees at once against %d in %s" % (use, limit, bp_id)))
    return out


def _suit(lp, bp_id, s, family, aspect):
    """what the plan would have taken: the blueprints that take this picture and these words"""
    try:
        opts, _ = lp.options(bp_id, s["seen_words"], family, aspect or 1.3)
        names = [o["bp"] for o in opts if o["bp"] != bp_id][:3]
        return "; the blueprints that fit it: %s" % ", ".join(names) if names else ""
    except Exception:  # noqa: BLE001
        return ""


def _fault(slide, kind, found_by, rule, source, did, picture_stop=None):
    return {"slide": slide, "kind": kind, "found_by": found_by, "rule": rule, "source": source, "did": did,
            "stop": picture_stop}


def fit_faults(found, misses):
    """[fault] for the slides the fit gate found cut or cropped: found = {size: [[slide, step, kind, what]]}, or - with no
    browser now - misses, the build's own list of slides it measured out (no size kept)"""
    out = []
    src = "course-module-ux/measure/scripts/fit_gate.py - the text is never made smaller; a slide too full is two slides"
    seen = set()
    for size, rows in sorted((found or {}).items()):
        for sid, step, kind, what in rows:
            if kind not in CUT_KINDS or (sid, size) in seen:
                continue
            seen.add((sid, size))
            out.append(_fault(sid, "overflow_cut", "fit gate at %s" % size,
                              "every slide fits whole at every Next, at 1280x800 and 1024x768 - nothing cut or cropped", src,
                              "%s at %s, Next %s: %s" % (kind, size, step, what), step))
    if not found:
        for sid in misses or []:
            out.append(_fault(sid, "overflow_cut", "the build's fit measurement (no size kept)",
                              "every slide fits whole at every Next, at 1280x800 and 1024x768 - nothing cut or cropped", src,
                              "the build measured %s out of its layout: its words did not fit" % sid))
    return out


def judge_faults(course, mod):
    """[fault] the run's judges found on module `mod`: the walk review, QA, the 3D and figure reviews - from their answer
    files, and from the workflow's result.json when it is there"""
    agents = os.path.join(course, "working_claude", "_build", "agents")
    out = []

    def add(slide, text, by, rule, src):
        k = "task_page" if re.search(r"(?i)\btasks?/", str(slide)) else kind_of(text)
        out.append(_fault(slide, k, by, rule, src, str(text)))

    walk_rule = "every slide, at every stop a trainee sees at 1280x800, shows its words and its picture whole, readable and right"
    walk_src = "course-module-ux/measure/scripts/walk_review.py (the walk review's rubric)"
    for name in sorted(os.listdir(agents)) if os.path.isdir(agents) else []:
        m = re.match(r"^(walk|qa|review3d|reviewfig)_(\w+?)(\+\w+)?\.json$", name)
        if not m or m.group(2) != str(mod):
            continue
        data = _json(os.path.join(agents, name)) or {}
        if m.group(1) == "walk":
            for f in data.get("fails") or []:
                add(f.get("slide", ""), f.get("what", ""), "walk review", walk_rule, walk_src)
        elif m.group(1) == "qa":
            for f in data.get("findings") or []:
                if f.get("severity") == "BROKEN":
                    sid = re.match(r"\s*(?:SCRIPT:?\s*)?(s\w+)", f.get("where", ""))
                    if re.match(r"\s*SCRIPT\b", f.get("where", "")):
                        out.append(_fault(sid.group(1) if sid else "", "script", "QA", "the approved script and the sources it cites",
                                          "course-factory/script/GUIDE.md", "%s: %s" % (f.get("where"), f.get("what"))))
                    else:
                        add(sid.group(1) if sid else f.get("where", ""), f.get("what", ""), "QA",
                            "the words, the teaching, the photographs and the checks of the module", "course-factory/compile/GUIDE.md (QA)")
        elif m.group(1) == "review3d":
            for f in data.get("findings") or []:
                if f.get("severity") == "BROKEN":
                    sid = re.match(r"\s*(s\w+)", f.get("where", ""))
                    out.append(_fault(sid.group(1) if sid else "", "3d", "3D review", "a 3D scene shows what its slide teaches, with its labels on its parts",
                                      "course-visuals/kit3d/SPEC.md", "%s: %s" % (f.get("where"), f.get("what"))))
        else:
            for fig in data.get("figures") or []:
                for f in fig.get("findings") or []:
                    if f.get("severity") == "BROKEN":
                        out.append(_fault(fig.get("slide", ""), "3d", "figure review", "a figure is physically right and shows what its slide says",
                                          "course-visuals/kit/scripts/figure_review.py (the figure kinds' truths)", f.get("what", "")))
    return out


def stop_picture(course, mod, slide, stop=None, text=""):
    """the walk's picture of a slide (or a task page) at the stop it names - the first stop when none: the path, or None"""
    root = os.path.join(course, "working_claude", "_build", "walk", "M%02d" % int(mod))
    if re.match(r"(?i)^tasks?/", str(slide)):
        d = os.path.join(root, slide.replace("\\", "/"))
        files = sorted(f for f in os.listdir(d) if f.endswith(".png")) if os.path.isdir(d) else []
        return os.path.join(d, files[0]) if files else None
    k = stop
    if k is None:
        m = re.search(r"(?i)\bstop (\d+)", str(text))
        k = int(m.group(1)) if m else 1
    for n in (k, 1):
        p = os.path.join(root, "%s_k%s.png" % (slide, n))
        if os.path.isfile(p):
            return p
    return None


def collect(course, mods, decks):
    """every fault of the modules: decks = {module: (deck path, scan_deck's slides, fit findings {size: rows} or None)};
    each fault gets its module, its picture (the walk's, a path) and its place in the report"""
    out = []
    for mod in mods:
        faults = []
        deck, slides, fit = decks.get(mod) or (None, None, None)
        if deck and slides:
            try:
                faults += rule_checks(deck, slides)
            except Exception as err:  # noqa: BLE001
                faults.append(_fault("", "other", "rule checks", "the factory's own rule checks run on the built deck", "scripts/fault_report.py",
                                     "the rule checks could not run: %s" % err))
        misses = _json(os.path.join(course, "working_claude", "_build", "M%02d_fit_misses.json" % int(mod)))
        faults += fit_faults(fit, misses if isinstance(misses, list) else None)
        faults += judge_faults(course, mod)
        seen = set()
        for f in faults:
            key = (f["slide"], f["kind"], f["did"][:80])
            if key in seen:
                continue
            seen.add(key)
            f["module"] = int(mod)
            st = f.pop("stop", None)
            f["picture_from"] = stop_picture(course, mod, f["slide"], int(st) if str(st).isdigit() else None, f["did"]) if f["slide"] else None
            out.append(f)
    return out


def write(run_dir, faults):
    """FAULTS.html, faults.json and faults/ in run_dir; -> the html path"""
    pics = os.path.join(run_dir, "faults")
    os.makedirs(pics, exist_ok=True)
    for i, f in enumerate(faults, 1):
        f["id"] = "F%03d" % i
        src = f.pop("picture_from", None)
        f["picture"] = None
        if src and os.path.isfile(src):
            name = "M%02d_%s_%s" % (f["module"], re.sub(r"[^\w.-]+", "_", f["slide"]), os.path.basename(src))
            shutil.copy2(src, os.path.join(pics, name))
            f["picture"] = "faults/" + name
        f["decision"] = ""
    with io.open(os.path.join(run_dir, "faults.json"), "w", encoding="utf-8") as fh:
        json.dump(faults, fh, indent=1, ensure_ascii=False)
    path = os.path.join(run_dir, "FAULTS.html")
    with io.open(path, "w", encoding="utf-8") as fh:
        fh.write(render(faults))
    return path


def render(faults):
    e = html.escape
    body, last = [], None
    for f in sorted(faults, key=lambda x: (x["module"], x["slide"], x["id"])):
        if (f["module"], f["slide"]) != last:
            last = (f["module"], f["slide"])
            body.append('<h2>Module %d - %s</h2>' % (f["module"], e(f["slide"] or "the module")))
        body.append(
            '<section class="f"><div class="pic">%s</div><div class="tx"><p class="h"><b>%s</b> &middot; %s &middot; found by %s</p>'
            '<p><span>The rule</span> %s<br><small>%s</small></p><p><span>What it did</span> %s</p>'
            '<p class="d"><span>Owner\'s decision</span> %s - to be filled in chat</p></div></section>'
            % ('<img src="%s" alt="%s">' % (e(f["picture"]), e(f["slide"])) if f.get("picture") else "<em>no picture</em>",
               e(f["id"]), e(f["kind"].replace("_", " ")), e(f["found_by"]), e(f["rule"]), e(f["source"]), e(f["did"]),
               " / ".join(DECISIONS)))
    count = {}
    for f in faults:
        count[f["kind"]] = count.get(f["kind"], 0) + 1
    head = ", ".join("%s %d" % (k.replace("_", " "), n) for k, n in sorted(count.items())) or "none"
    return ('<!doctype html><html lang="en"><meta charset="utf-8"><title>Trial faults</title>'
            '<style>body{font:15px/1.45 system-ui,sans-serif;margin:24px auto;max-width:1100px;padding:0 16px;color:#16212e;background:#fff}'
            'h2{margin:28px 0 8px;border-bottom:1px solid #cfd6df}.f{display:flex;gap:16px;margin:12px 0;padding:12px;border:1px solid #cfd6df;'
            'border-radius:8px}.pic{flex:0 0 46%%}.pic img{width:100%%;border:1px solid #cfd6df}.tx{flex:1}.tx p{margin:0 0 8px}'
            '.tx span{display:inline-block;min-width:7em;font-weight:600;color:#3a5a8c}.d{border-top:1px dashed #cfd6df;padding-top:8px;color:#666}'
            'small{color:#666}@media(max-width:720px){.f{flex-direction:column}}</style>'
            '<h1>Trial faults</h1><p>%d fault(s): %s. Nothing here was fixed.</p>%s</html>' % (len(faults), e(head), "\n".join(body)))
