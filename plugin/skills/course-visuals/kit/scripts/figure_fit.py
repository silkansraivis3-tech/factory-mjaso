#!/usr/bin/env python3
"""figure_fit.py - every kit figure of a module checked at once on its real slide, and the deterministic fixes made by
themselves, each proven by the same check (2.50.0).

  figure_fit.py <course> --module 1 [--no-fix] [--json]

WHY (IGF M01 benchmark, 2026-10-19): a module build spent most of its turns on figures found one compile at a time -
37, then 2, then 1 drawing problems; s02 took 11 spec edits; one layout change (s05 two-col -> wide-left) cost 16 spec
edits and 3 failed compiles, where the hand-built copy needed one class change. This does in one run what those
turns did:

  1  CHECK   every kit figure the build sheet puts on a slide, all at once, each on its real slide at 1280 x 800, every
             step, every drawing audit (studio.py) - plus check_kit.py's spec checks. Findings are grouped per figure
             and part, never one line per step.
  2  FIX     only what has one right answer, never by loosening a limit, and each fix is drawn and audited again:
             EMPTY    the drawing cropped to what it shows at its busiest step, in the column's shape (a window on the
                      same canvas - the parts stay where they are)
             COLUMN   a figure drawn below 0.8:1 in its column (a layout changed and the column got narrower) re-fitted
                      to it: its positions and stretchable lengths (pipes, rooms, bars) squeezed to the column, then
                      repaired part by part - a part past its room's edge moved into free room or drawn narrower (never
                      under 70 %), a part on another moved beside it, a heading too wide broken onto two lines (the
                      same words). Nothing is wrapped downwards: a column is height-bound as often as width-bound
                      (IGF M01 s05: wrapping made the drawing taller and every word smaller). Tried at four widths at
                      once; one that audits clean at every step is kept.
             A fix is written to figures\\MNN\\_fit\\<slide>.<spec> with the spec's hash and the slide's layout: the
             compiler draws it only while both are unchanged. The spec itself is never rewritten. A figure no fix makes
             clean is reported as it is, with what to do - and the closest attempt is saved beside it
             (<slide>.<spec>.candidate.kit.json) to copy over the spec and finish, instead of redrawing.
  3  SAY     one block per figure that still has a problem: the slide, the part, the check, the steps, a concrete fix.

Exit 0 every figure clean (fixed ones included), 1 problems left, 2 could not run.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import copy
import hashlib
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import studio  # noqa: E402
import check_kit  # noqa: E402

sys.path.insert(0, studio.COMPILE)
sys.path.insert(0, studio.FACTORY_SCRIPTS)

GATE = "1280x800"
CONTAINERS = ("space", "panel", "ga")
# widths that stretch with the drawing (a room, a pipe run, a bar); every other part keeps its size and only moves
STRETCH = {"space": ("w",), "panel": ("w",), "pipe_section": ("w", "branchAt"), "ga": ("w",), "tank": ("w",),
           "integral_tank": ("w",), "bands": ("w",), "log": ("w",), "tree": ("w",), "composition_bar": ("w",),
           "range_bar": ("w",), "spill": ("w",), "wind": ("w",), "tank_wall": ("w",), "boil_off": ("w",),
           "drip_tray": ("w",), "gas_cloud": ("w",), "zone": ("w", "rx"), "water_curtain": ("w",)}
PATHS = ("pipe", "wire", "hose")
GAP = 14            # between a moved part and what it was moved under, in the drawing's units
PAD = 10            # a room's inside margin


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


# ------------------------------------------------------------------ what the module draws
def deck_figures(course, module):
    """[(screen id, spec path, build entry)] - every kit figure the build sheet puts on a slide"""
    import content_script as cs
    p = cs.paths(course, module)
    bp = os.path.join(p["dir"], cs.mid(module) + ".build.json")
    if not (os.path.isfile(bp) and os.path.isfile(p["script"])):
        return [], None
    build = cs.load(bp)
    script = cs.load(p["script"])
    slides = {s["id"] for s in script["screens"] if s["kind"] in cs.INSTRUCTOR}
    figdir = os.path.join(os.path.dirname(p["dir"]), "figures", cs.mid(module))
    out = []
    for sid, e in (build.get("screens") or {}).items():
        f = (e.get("figure") or "").replace("\\", "/")
        if sid in slides and f.endswith(".kit.json"):
            out.append((sid, os.path.join(figdir, f), e))
    return out, figdir


def all_specs(course, module):
    """every *.kit.json the build sheet names, slides and task questions (for the spec checks)"""
    import content_script as cs
    p = cs.paths(course, module)
    bp = os.path.join(p["dir"], cs.mid(module) + ".build.json")
    figdir = os.path.join(os.path.dirname(p["dir"]), "figures", cs.mid(module))
    names = set()
    if os.path.isfile(bp):
        for e in (cs.load(bp).get("screens") or {}).values():
            f = (e.get("figure") or "").replace("\\", "/")
            if f.endswith(".kit.json"):
                names.add(f)
    return [os.path.join(figdir, n) for n in sorted(names)]


# ------------------------------------------------------------------ measuring
def ctx_for(spec_path, sid):
    """the studio's slide context for THIS screen (a spec on two slides is judged on each)"""
    ctx = studio.course_context(spec_path)
    if ctx and ctx["screen"] != sid:
        e = (ctx["build"].get("screens") or {}).get(sid)
        if e:
            ctx = dict(ctx, screen=sid, entry=e)
    return ctx


def measure(spec_path, sid, spec=None):
    """(problems at the gate, the gate's result) of a spec drawn on its slide; problems None when it could not run"""
    ctx = ctx_for(spec_path, sid)
    res, why = studio.run(spec_path, sizes=((1280, 800),), shots=False, spec=spec, ctx=ctx)
    if not res:
        return None, {"error": why}
    r = res["sizes"].get(GATE) or {}
    if r.get("error"):
        return None, r
    return [x for x in studio.problems(res) if x[0] == GATE], r


# ------------------------------------------------------------------ geometry
def shift_path(d, fx, fy=None):
    """an SVG path with every x coordinate mapped by fx and every y by fy (absolute commands; a relative one keeps its
    offsets)"""
    out, cmd = [], "M"
    fy = fy or (lambda v: v)
    toks = re.findall(r"[A-Za-z]|-?\d*\.?\d+(?:e-?\d+)?", d or "")
    nums = []

    def flush():
        if not nums:
            return
        c = cmd.upper()
        gx, gy = fx, fy
        if cmd.islower():                  # a relative step: scaled, never shifted
            gx, gy = (lambda v: fx(v) - fx(0)), (lambda v: fy(v) - fy(0))
        vals = list(nums)
        if c in "MLTCSQ":
            vals = [gx(v) if k % 2 == 0 else gy(v) for k, v in enumerate(vals)]
        elif c == "H":
            vals = [gx(v) for v in vals]
        elif c == "V":
            vals = [gy(v) for v in vals]
        elif c == "A":
            vals = [gx(v) if k % 7 == 5 else gy(v) if k % 7 == 6 else v for k, v in enumerate(vals)]
        out.append(" ".join(fmt(v) for v in vals))
        del nums[:]

    for t in toks:
        if re.match(r"[A-Za-z]", t):
            flush()
            cmd = t
            out.append(t)
        else:
            nums.append(float(t))
    flush()
    return re.sub(r"([A-Za-z]) ", r"\1", " ".join(out))


def fmt(v):
    return ("%.1f" % v).rstrip("0").rstrip(".")


def squeeze(spec, k, x0=0.0):
    """every x position mapped x0 + (x - x0) * k, stretchable widths times k; sizes of everything else kept"""
    s = copy.deepcopy(spec)
    fx = lambda v: x0 + (v - x0) * k   # noqa: E731
    for p in s.get("parts", []):
        t = p.get("type")
        if t in PATHS:
            if p.get("d"):
                p["d"] = shift_path(p["d"], fx)
            if "x" in p:
                p["x"] = round(fx(p["x"]), 1)
            continue
        if "x" in p:
            p["x"] = round(fx(p["x"]), 1)
        for key in STRETCH.get(t, ()):
            if isinstance(p.get(key), (int, float)):
                p[key] = round(p[key] * k, 1)
        if isinstance(p.get("to"), list) and len(p["to"]) == 2:
            p["to"] = [round(fx(p["to"][0]), 1), p["to"][1]]
        if t == "gas_cloud" and isinstance(p.get("from"), list) and p.get("fromIn") == "figure":
            p["from"] = [round(fx(p["from"][0]), 1), p["from"][1]]
    s["size"] = [round(spec["size"][0] * k), spec["size"][1]]
    return s


def overlap(a, b, m=4):
    return a[0] < b[2] + m and b[0] < a[2] + m and a[1] < b[3] + m and b[1] < a[3] + m


def inside(b, c):
    cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
    return c[0] <= cx <= c[2] and c[1] <= cy <= c[3] and (b[2] - b[0]) * (b[3] - b[1]) < (c[2] - c[0]) * (c[3] - c[1])


SHRINK = ("engine", "tank", "readout", "pump", "exchanger", "space", "integral_tank", "gas_cloud", "drip_tray")
SHRINK_MIN = 0.7          # a part is drawn at least this share of the size the spec gave it


def tidy(spec, boxes, width, w0=None):
    """one round of local repairs, after a squeeze - nothing is wrapped, so the drawing keeps its shape:
    a part past its room's right edge (or the frame's) moves left into free room, else is drawn narrower (never under
    SHRINK_MIN of its size); a part on top of the one before it moves beside it, or down inside its room; a free text
    wider than the frame breaks onto two lines at the space nearest its middle (the same words).
    Returns (new spec, number of repairs)"""
    s = copy.deepcopy(spec)
    parts = s["parts"]
    w0 = w0 or {}
    bx ={int(k): list(v[:4]) for k, v in boxes.items() if int(k) < len(parts)}
    conts = [i for i in bx if parts[i].get("type") in CONTAINERS]
    owner = {}
    for i in bx:
        if parts[i].get("type") not in CONTAINERS:
            for c in conts:
                if inside(bx[i], bx[c]):
                    owner[i] = c
    fixes = 0
    order = sorted((i for i in bx if parts[i].get("type") not in CONTAINERS + PATHS), key=lambda i: (bx[i][0], bx[i][1]))

    def move(i, dx, dy):
        p = parts[i]
        p["x"] = round((p.get("x") or 0) + dx, 1)
        p["y"] = round((p.get("y") or 0) + dy, 1)
        if isinstance(p.get("to"), list):
            p["to"] = [round(p["to"][0] + dx, 1), round(p["to"][1] + dy, 1)]
        if p.get("type") == "gas_cloud" and isinstance(p.get("from"), list) and p.get("fromIn") == "figure":
            p["from"] = [round(p["from"][0] + dx, 1), round(p["from"][1] + dy, 1)]
        bx[i] = [bx[i][0] + dx, bx[i][1] + dy, bx[i][2] + dx, bx[i][3] + dy]

    for i in order:
        p = parts[i]
        c = owner.get(i)
        left, right = (bx[c][0] + PAD, bx[c][2] - PAD) if c is not None else (4, width - 4)
        top, bottom = (bx[c][1] + PAD, bx[c][3] - PAD) if c is not None else (4, 1e9)
        mates = [j for j in order if j != i and owner.get(j) == c]
        b = bx[i]
        w = b[2] - b[0]
        if p.get("type") == "text" and not p.get("to") and w > right - left and " " in (p.get("text") or "") \
                and "\n" not in p.get("text"):
            t = p["text"]
            mid = len(t) / 2.0
            cut = min((k for k, ch in enumerate(t) if ch == " "), key=lambda k: abs(k - mid))
            p["text"] = t[:cut] + "\n" + t[cut + 1:]
            fixes += 1
            continue
        if b[2] > right + 0.5:                                   # past the right edge
            over = b[2] - right
            cand = [b[0] - over, b[1], b[2] - over, b[3]]
            if cand[0] >= left - 0.5 and not any(overlap(cand, bx[j]) for j in mates):
                move(i, -over, 0)
                fixes += 1
                continue
            if p.get("type") in SHRINK and isinstance(p.get("w"), (int, float)):
                nw = max(p["w"] - over, w0.get(i, p["w"]) * SHRINK_MIN)
                if nw < p["w"] - 0.5:
                    bx[i][2] -= p["w"] - nw
                    p["w"] = round(nw, 1)
                    fixes += 1
                    continue
        hit = [j for j in mates if overlap(bx[i], bx[j], 2) and bx[j][0] <= bx[i][0]]
        if hit and p.get("type") != "text":
            j = max(hit, key=lambda j: bx[j][2])
            for dx, dy in ((bx[j][2] + GAP - b[0], 0), (0, bx[j][3] + GAP - b[1])):
                cand = [b[0] + dx, b[1] + dy, b[2] + dx, b[3] + dy]
                if cand[2] <= right + 0.5 and cand[3] <= bottom + 0.5 and not any(overlap(cand, bx[k], 2) for k in mates if k != i):
                    move(i, dx, dy)
                    fixes += 1
                    break
    return s, fixes


def crop(spec, boxes, panel):
    """EMPTY: a window on the canvas around what the figure shows, in its panel's shape (the parts are not moved)"""
    bb = [v[:4] for v in boxes.values() if v[5] not in ("panel",)]
    if not bb:
        return None
    x0, y0 = min(b[0] for b in bb) - 8, min(b[1] for b in bb) - 8
    x1, y1 = max(b[2] for b in bb) + 8, max(b[3] for b in bb) + 8
    w, h = x1 - x0, y1 - y0
    a = panel[0] / float(panel[1]) if panel and panel[1] else w / h
    if w / h > a:
        nh = w / a
        y0 -= (nh - h) / 2
        h = nh
    else:
        nw = h * a
        x0 -= (nw - w) / 2
        w = nw
    full = spec["size"]
    if w >= full[0] - 1 and h >= full[1] - 1:
        return None                         # nothing to crop
    s = copy.deepcopy(spec)
    s["view"] = [round(x0, 1), round(y0, 1), round(w, 1), round(h, 1)]
    return s


# ------------------------------------------------------------------ fixing one figure
def classify(probs):
    checks = {p[2] for p in probs}
    return checks


def try_fixes(spec_path, sid, spec, r0, probs0, log):
    """(fixed spec, how) or (None, why not) - the deterministic fixes, each measured again on the real slide"""
    checks = classify(probs0)
    panel = (r0.get("states") or [{}])[-1].get("panel") or [0, 0]
    boxes = r0.get("parts") or {}
    tried = []
    if checks <= {"empty"} and boxes:                     # only EMPTY: crop to what the steps show
        c = crop(spec, boxes, panel)
        if c:
            p, r = measure(spec_path, sid, c)
            tried.append("cropped to what it shows")
            if p == []:
                return c, "EMPTY: cropped to what it shows at its busiest step (%s), the parts not moved" % " ".join(fmt(v) for v in c["view"]), None
    # COLUMN: the spec is drawn below 0.8:1 in its column, so its words were grown past what the drawing holds - squeezed
    # to the column (positions and stretchable lengths), then tidied part by part; at a few widths, in parallel
    scale = (r0.get("report") or {}).get("scale") or 1
    best = None
    if scale < 0.8 and panel[0]:
        left = max(0.0, min((p.get("x") or 0) for p in spec["parts"] if p.get("type") not in PATHS))

        def attempt(wt):
            k = (wt - 2 * left) / float(spec["size"][0] - 2 * left)
            if k >= 0.98:
                return None
            cand = squeeze(spec, k, x0=left)
            w0 = {i: q["w"] for i, q in enumerate(cand["parts"]) if isinstance(q.get("w"), (int, float))}
            out = None
            for n in range(4):
                p, r = measure(spec_path, sid, cand)
                if p is None:
                    break
                if out is None or len(p) < len(out[1]):
                    out = (cand, p, n)
                if not p:
                    break
                cand, fixes = tidy(cand, r.get("parts") or {}, cand["size"][0], w0)
                if not fixes:
                    break
            return out
        with cf.ThreadPoolExecutor(max_workers=4) as ex:
            outs = [x for x in ex.map(attempt, [panel[0] * f for f in (1.1, 1.2, 1.32, 1.45)]) if x]
        for cand, p, n in outs:
            if best is None or len(p) < len(best[1]):
                best = (cand, p, n)
        if best and not best[1]:
            cand, _, n = best
            return cand, ("COLUMN: re-fitted to its %d px column - drawn %d units wide (was %d), %d local repair(s); the spec "
                          "is unchanged; look at it in the review sheet" % (panel[0], cand["size"][0], spec["size"][0], n)), None
        if best:
            tried.append("re-fitted to its %d px column: %d finding(s) left (was %d)" % (panel[0], len(best[1]), len(probs0)))
    return None, "; ".join(tried) or "no deterministic fix for %s" % ", ".join(sorted(checks)), best


# ------------------------------------------------------------------ the report
HINT = {
    "empty": "fill the frame: crop what the steps never show, spread the parts, or add the context the slide's lines name",
    "text zone": "give the part room for its words (a larger w/h, or move it clear) - the label layout places words, not parts",
    "inside": "the part pokes out of the room it sits in: make the room larger or move the part in",
    "cut off": "something reaches past the drawing's frame or the slide: make it smaller or the frame larger",
    "small text": "too many words for the room the figure has: give it a wider column or fewer words",
    "label": "a label found no clear place: give the figure more room around that part, or shorter words",
    "contrast": "colour the part for the dark panel (kit tokens only) or mark one meant to be quiet data-low-contrast",
}


def short(part):
    m = re.search(r'"([^"]+)"', part or "")
    return m.group(1) if m else (part or "")


def group(probs):
    """{(check, part words): [steps]} - one line per problem, not one per step"""
    g = {}
    for size, step, check, part, detail in probs:
        g.setdefault((check, short(part), re.sub(r"\s+\d+ px|\(\d+/\d+ points\)", "", detail or "")[:90]), []).append(str(step))
    return g


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("course")
    ap.add_argument("--module", required=True)
    ap.add_argument("--no-fix", action="store_true", help="only check; make no fix")
    ap.add_argument("--json", action="store_true")
    o = ap.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    code, text, data = run_all(o.course, o.module, fix=not o.no_fix)
    print(json.dumps(data, ensure_ascii=False, indent=1) if o.json else text)
    return code


def run_all(course, module, fix=True, jobs=4):
    """(exit code, report text, data) - the spec checks, then every slide figure measured at once, then the fixes"""
    import compile_module as cm
    lines, data = [], {"figures": {}}
    # the spec checks (check_kit.py): a spec that would not draw is said first, and not measured
    types = check_kit.kit_types()
    import content_script as cs
    mdir = os.path.join(course, "modules", "module%02d" % int(module)) if str(module).isdigit() else None
    if mdir and os.path.isfile(os.path.join(mdir, "assets", "kit_parts.js")):
        types |= check_kit.local_types(os.path.join(mdir, "assets", "kit_parts.js"))
    broken = set()
    spec_probs = []
    for sp in all_specs(course, module):
        name = os.path.basename(sp)
        if not os.path.isfile(sp):
            spec_probs.append("%s: the build sheet names it and it is not there" % name)
            broken.add(sp)
            continue
        spec, err = check_kit.load_spec(sp)
        if err:
            spec_probs.append("%s: %s" % (name, err))
            broken.add(sp)
            continue
        for x in check_kit.check_spec(spec, types, name):
            spec_probs.append(x)
            if " is not a kit part" in x or "not valid" in x:
                broken.add(sp)
    figs, figdir = deck_figures(course, module)
    todo = [(sid, sp, e) for sid, sp, e in figs if sp not in broken and os.path.isfile(sp)]
    results, entry = {}, {}
    with cf.ThreadPoolExecutor(max_workers=jobs) as ex:
        futs = {ex.submit(measure, sp, sid): (sid, sp) for sid, sp, e in todo}
        for sid, sp, e in todo:
            entry[(sid, sp)] = e
        for f in cf.as_completed(futs):
            results[futs[f]] = f.result()
    left, fixed = [], []

    # a fix is tried per failing figure, in parallel too
    def fix_one(key):
        sid, sp = key
        e = entry[key]
        item = (sid, sp, e)
        probs, r = results[key]
        text = io.open(sp, encoding="utf-8").read()
        spec = json.loads(text)
        fp = cm.fit_path(figdir, os.path.basename(sp), sid)
        cand_path = re.sub(r"\.kit\.json$", ".candidate.kit.json", fp)
        if probs == [] or probs is None or not fix:
            return item, probs, r, None, None
        sc = cs.load(cs.paths(course, module)["script"])
        s = next((x for x in sc["screens"] if x["id"] == sid), {})
        column = cm.composition_key(s, e)
        old = cm.fitted(figdir, os.path.basename(sp), text, column, sid)
        if old:                                       # a fit made before for this spec and this column: still clean?
            p, _ = measure(sp, sid, json.loads(old))
            if p == []:
                return item, probs, r, json.loads(old), json.load(io.open(fp, encoding="utf-8")).get("how", "re-fitted")
        new, how, best = try_fixes(sp, sid, spec, r, probs, None)
        if os.path.isfile(cand_path):
            os.remove(cand_path)
        if new:
            os.makedirs(os.path.dirname(fp), exist_ok=True)
            rec = {"source": cm.sha(text), "column": column, "how": how, "made_by": "figure_fit.py", "spec": new}
            io.open(fp, "w", encoding="utf-8").write(json.dumps(rec, ensure_ascii=False, indent=1))
        elif best and len(best[1]) < len(probs):      # the closest attempt, to edit instead of redrawing
            os.makedirs(os.path.dirname(cand_path), exist_ok=True)
            io.open(cand_path, "w", encoding="utf-8").write(json.dumps(best[0], ensure_ascii=False, indent=1))
            how += (" - saved as %s: copy it over %s and fix what it leaves:\n%s"
                    % (os.path.normpath(cand_path), os.path.basename(sp),
                       "\n".join("        %s - %s: %s (step %s)" % (c, pt, dt, ",".join(sorted(set(st))))
                                 for (c, pt, dt), st in sorted(group(best[1]).items()))))
        return item, probs, r, new, how
    with cf.ThreadPoolExecutor(max_workers=jobs) as ex:
        outs = list(ex.map(fix_one, sorted(results, key=lambda t: t[0])))
    for (sid, sp, e), probs, r, new, how in outs:
        name = os.path.basename(sp)
        d = data["figures"].setdefault(sid, {"spec": name})
        if probs is None:
            left.append("%s (%s): the figure could not be measured - %s" % (sid, name, r.get("error")))
            d["error"] = r.get("error")
            continue
        rep = r.get("report") or {}
        st = (r.get("states") or [{}])[-1]
        d.update({"panel": st.get("panel"), "scale": rep.get("scale"), "problems": len(probs)})
        if new:
            fixed.append("%s (%s): fixed by itself - %s" % (sid, name, how))
            d["fixed"] = how
            continue
        if probs:
            block = ["%s (%s) on its slide - drawn %s px in a %s px panel, scale %.2f:" % (
                sid, name, "x".join(map(str, st.get("svg") or [])), "x".join(map(str, st.get("panel") or [])), rep.get("scale") or 0)]
            seen = set()
            for (check, part, detail), steps in sorted(group(probs).items()):
                block.append("    %s - %s: %s (step %s)" % (check, part, detail, ",".join(sorted(set(steps)))))
            for check in sorted({c for c, _, _ in group(probs)}):
                if HINT.get(check) and check not in seen:
                    seen.add(check)
                    block.append("    fix (%s): %s" % (check, HINT[check]))
            if how:
                block.append("    tried by itself: %s" % how)
            left.append("\n".join(block))
            d["left"] = [list(x) for x in probs]
    for sid, sp, e in figs:            # a figure clean as written needs no fit: an old one is removed
        fp = cm.fit_path(figdir, os.path.basename(sp), sid)
        dd = data["figures"].get(sid) or {}
        if os.path.isfile(fp) and dd.get("problems") == 0:
            os.remove(fp)
    n = len(todo)
    lines += ["Figures: %d on slides, %d spec(s) checked" % (n, len(all_specs(course, module)))]
    lines += ["  spec: " + x for x in spec_probs]
    lines += ["  " + x for x in fixed]
    lines += ["  " + x for x in left]
    code = 1 if (left or spec_probs) else 0
    lines.append("Figures: %s" % ("every figure clean%s" % (" (%d fixed by itself)" % len(fixed) if fixed else "") if code == 0
                                  else "%d figure(s) to fix" % (len(left) + len(spec_probs))))
    data.update({"fixed": fixed, "left": left, "spec_problems": spec_probs})
    return code, "\n".join(lines), data


if __name__ == "__main__":
    sys.exit(main())
