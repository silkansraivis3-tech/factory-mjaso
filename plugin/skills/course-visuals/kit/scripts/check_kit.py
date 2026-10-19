#!/usr/bin/env python3
"""check_kit.py - is a figure-kit spec drawable, and is a new part built to the kit's contract? (L55)

  check_kit.py spec  <file.kit.json> ... [--parts <module>/assets/kit_parts.js]
  check_kit.py parts <module>/assets/kit_parts.js
  check_kit.py module <module folder> [--figures <course>/working_claude/figures/M03]

SPEC   valid JSON; a size; every part of a type the kit has (or the module's kit_parts.js adds); ids unique;
       every step moves a part that exists ("P1.fill" only on a pipe); marks well formed; a label for the
       screen reader.
PARTS  each new part between /* kit-part: name */ and /* end kit-part */; drawn with KIT.h, never its own
       colours, font sizes or innerHTML; a family, a status and an example spec (the gallery card).
       PARTS.md is the contract this enforces.
MODULE both: the module's kit_parts.js, and every *.kit.json in its figures folder.

Exit 0 clean, 1 problems found, 2 nothing to check.
"""
from __future__ import annotations

import argparse
import glob
import io
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

KIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KIT_JS = os.path.join(KIT, "kit.js")
FAMILIES = ("instruments", "piping", "spaces", "cutaways", "gas-fire-machinery", "charts", "procedures")
KINDS = ("alarm", "trip", "limit")
# a second value on one part: "<id>.fill" (a pipe or hose filling), "<id>.burst" (a tank that ruptures, tank "burst"),
# "<id>.drift" (a gas cloud carried off, gas_cloud "drift")
SUBS = {"pipe": ("fill",), "hose": ("fill",), "tank": ("burst",), "gas_cloud": ("drift",)}
# what a `person` can put on (the order they are put on is the order of "wear")
PERSON_WEAR = ("helmet", "visor", "goggles", "respirator", "gloves", "suit", "apron", "boots", "scba")
BLOCK = re.compile(r"/\*\s*kit-part:\s*([\w]+)\s*\*/(.*?)/\*\s*end kit-part\s*\*/", re.S)
DEFINE = re.compile(r"KIT\.define\(\s*['\"](\w+)['\"]")
MIN_PX = 12.5


def read(p):
    return io.open(p, encoding="utf-8").read()


# ------------------------------------------------------------------ what the kit has
def kit_types(kit_js=KIT_JS):
    t = read(kit_js)
    return set(re.findall(r"TYPES\.(\w+)\s*=", t)) | set(DEFINE.findall(t))


def blocks(text):
    """[(marker name, block text)] - the new parts in a kit_parts.js, or the promoted ones in kit.js"""
    return [(m.group(1), m.group(2)) for m in BLOCK.finditer(text)]


_STR = r"(?:'(?:\\.|[^'\\])*'|\"(?:\\.|[^\"\\])*\"|`(?:\\.|[^`\\])*`)"
STRCAT = _STR + r"(?:\s*\+\s*" + _STR + r")*"        # 'a' + 'b' + "c" - a string written in pieces


def _unquote_cat(expr):
    """the text of a 'a' + 'b' expression, the pieces joined"""
    return "".join(m.group(0)[1:-1] for m in re.finditer(_STR, expr))


def meta_field(block, key):
    m = re.search(r"\b%s\s*:\s*(%s)" % (key, STRCAT), block, re.S)
    return _unquote_cat(m.group(1)) if m else None


def strip_comments(js):
    js = re.sub(r"/\*.*?\*/", "", js, flags=re.S)
    return re.sub(r"(^|[^:\\])//[^\n]*", r"\1", js)


# ------------------------------------------------------------------ a new part
def check_part(name, block):
    probs = []
    d = DEFINE.search(block)
    if not d:
        return ["%s: no KIT.define('%s', ...) between its markers" % (name, name)]
    if d.group(1) != name:
        probs.append("%s: the marker says %s but KIT.define says %s" % (name, name, d.group(1)))
    if not re.fullmatch(r"[a-z][a-z0-9_]*", name):
        probs.append("%s: name it in lower case with _ for what it is (drip_tray), not where it is used" % name)
    css = meta_field(block, "css") or ""
    body = strip_comments(block)
    body_no_css = re.sub(r"\bcss\s*:\s*" + STRCAT, "css:''", body, flags=re.S)
    rules = [
        (r"#[0-9a-fA-F]{3,8}\b", "a colour written as #hex - use the kit's classes or var(--token)"),
        (r"\b(?:rgba?|hsla?)\(", "a colour written as rgb()/hsl() - use the kit's classes or var(--token)"),
        (r"[{,]\s*['\"]?(?:fill|stroke|color)['\"]?\s*:", "a fill/stroke set in the drawing - colour comes from a class"),
        (r"\.style\.(?:fill|stroke|color|fontSize)\b", "a colour or size set through .style - use a class"),
        (r"setAttribute\(\s*['\"](?:fill|stroke|font-size|style)['\"]", "a colour, size or style set by setAttribute"),
        (r"font-size|fontSize", "a font size in the drawing - use the kit's type classes (kit-cap, kit-h ...)"),
        (r"\binnerHTML\b|\bouterHTML\b", "innerHTML - draw with KIT.h.el"),
        (r"createElementNS", "its own createElementNS - draw with KIT.h.el"),
        (r"setInterval|setTimeout|requestAnimationFrame", "its own timer - values move through the step engine"),
    ]
    for rx, why in rules:
        if re.search(rx, body_no_css):
            probs.append("%s: %s" % (name, why))
    if "KIT.h" not in body:
        probs.append("%s: does not draw with KIT.h (the kit's helpers)" % name)
    if not re.search(r"part\.render\s*=", body):
        probs.append("%s: sets no part.render - a part must show its value" % name)
    fam = meta_field(block, "family")
    if fam not in FAMILIES:
        probs.append("%s: family %r is not one of %s" % (name, fam, ", ".join(FAMILIES)))
    if meta_field(block, "status") not in ("new", "kit"):
        probs.append("%s: status must be 'new' (in a course) or 'kit' (merged)" % name)
    for key in ("why", "value"):
        if not meta_field(block, key):
            probs.append("%s: says no %s - write it in the meta, the reviewer reads it" % (name, key))
    if not re.search(r"\bexample\s*:\s*\{", body):
        probs.append("%s: has no example spec - it is the gallery card the merge is reviewed on" % name)
    if css:
        if re.search(r"#[0-9a-fA-F]{3,8}\b|\b(?:rgba?|hsla?)\(", css):
            probs.append("%s: its css writes a colour - only var(--token)" % name)
        for cls in set(re.findall(r"\.([A-Za-z][\w-]*)", css)):
            if not cls.startswith("kit-"):
                probs.append("%s: its css styles .%s - a part's own classes start kit-%s-" % (name, cls, name.replace("_", "-")))
        for px in re.findall(r"font-size\s*:\s*([\d.]+)px", css):
            if float(px) < MIN_PX:
                probs.append("%s: its css sets a %spx label - the floor is %gpx" % (name, px, MIN_PX))
    return probs


def check_parts_file(path):
    text = read(path)
    found = blocks(text)
    probs = []
    if not found and DEFINE.search(text):
        probs.append("%s: KIT.define without the /* kit-part: name */ ... /* end kit-part */ markers" % path)
    outside = BLOCK.sub("", text)
    if DEFINE.search(outside):
        probs.append("%s: a KIT.define outside its markers - one part per marked block" % path)
    canon = kit_types()
    for name, block in found:
        probs += check_part(name, block)
        if name in canon and meta_field(block, "status") == "new":
            probs.append("%s: the kit has a %s already - use it, or remove the module's copy" % (name, name))
    return probs, [n for n, _ in found]


# ------------------------------------------------------------------ a spec
def cloud_origin(p):
    """where a gas_cloud grows from, in figure coordinates, and how the kit read "from" ("box" or "figure") - the same
    reading as kit.js (2.49.2): in the cloud's own box when it lies there, else in figure coordinates when it lies in the
    box that way, unless "fromIn" says which"""
    w, h = p.get("w") or 200, p.get("h") or 120
    x0, y0 = p.get("x") or 0, p.get("y") or 0
    fx, fy = p["from"]
    inbox = lambda a, b: 0 <= a <= w and 0 <= b <= h
    fig = p.get("fromIn") == "figure" or (p.get("fromIn") != "box" and not inbox(fx, fy) and inbox(fx - x0, fy - y0))
    return ((fx, fy), "figure") if fig else ((x0 + fx, y0 + fy), "box")


def cloud_origin_problem(p, size):
    """a gas_cloud whose "from" puts its origin off the figure (it used to be silently drawn off the picture), else None"""
    f = p.get("from")
    if not (isinstance(f, list) and len(f) == 2 and all(isinstance(v, (int, float)) for v in f)):
        return "the cloud %s has \"from\": %r - the point it grows from, [x, y]" % (p.get("id") or "", f)
    if not (isinstance(size, list) and len(size) == 2 and all(isinstance(v, (int, float)) for v in size)):
        return None
    (ax, ay), how = cloud_origin(p)
    if 0 <= ax <= size[0] and 0 <= ay <= size[1]:
        return None
    return ("the cloud %s grows from [%g, %g] read in %s coordinates - that is [%g, %g] on the figure, off its %gx%g size, so the "
            "cloud is drawn off the picture; \"from\" is a point on the figure (or add \"fromIn\": \"figure\" / \"box\" to say which)"
            % (p.get("id") or "", f[0], f[1], "the cloud's own box" if how == "box" else "figure", ax, ay, size[0], size[1]))


def check_spec(spec, types, where):
    probs = []

    def bad(msg):
        probs.append("%s: %s" % (where, msg))

    if not isinstance(spec, dict):
        return ["%s: a spec is a JSON object" % where]
    size = spec.get("size")
    if not (isinstance(size, list) and len(size) == 2 and all(isinstance(x, (int, float)) and x > 0 for x in size)):
        bad('no "size": [width, height]')
    if not spec.get("label"):
        bad('no "label" - one sentence a screen reader says (the compiler falls back to the visual\'s first sentence)')
    if spec.get("theme") not in (None, "light", "dark"):
        bad('"theme" is %r - "light" or "dark" (or leave it out: the kit sees what the figure is drawn on)' % spec.get("theme"))
    if spec.get("fit") not in (None, True, False):
        bad('"fit" is %r - false keeps the drawing from being zoomed to fill its panel' % spec.get("fit"))
    parts = spec.get("parts") or []
    if not parts:
        bad("no parts")
    ids, kinds, given = set(), {}, {}
    for i, p in enumerate(parts):
        if not isinstance(p, dict):
            bad("part %d is not an object" % (i + 1))
            continue
        t, pid = p.get("type"), p.get("id")
        if t not in types:
            bad("part %s is of type %r, which the kit does not have - make it (PARTS.md) or use one that exists"
                % (pid or i + 1, t))
        if pid:
            if pid in ids:
                bad("the id %s is used twice" % pid)
            ids.add(pid)
            kinds[pid] = t
            given[pid] = p
        if p.get("source") and p["source"] not in ids:
            bad("part %s repeats %s, which is not listed before it" % (pid, p["source"]))
        if t == "text" and "to" in p and not (isinstance(p["to"], list) and len(p["to"]) == 2
                                              and all(isinstance(v, (int, float)) for v in p["to"])):
            bad("the callout %r has \"to\": %r - the place it names, [x, y]" % (str(p.get("text"))[:30], p["to"]))
        if t == "text" and not str(p.get("text") or "").strip():
            bad("a text part with no words")
        if t == "person":
            wear = p.get("wear") or []
            for item in wear:
                if item not in PERSON_WEAR:
                    bad("the person %s wears %r - the kit draws %s" % (p.get("id") or "", item, ", ".join(PERSON_WEAR)))
            for key in ("labels", "names"):
                if isinstance(p.get(key), dict):
                    for item in p[key]:
                        if item not in wear:
                            bad("the person %s has a %s for %r, which is not in its \"wear\" - the words would never show"
                                % (p.get("id") or "", key, item))
        if t == "gas_cloud" and p.get("from") is not None:
            bad_origin = cloud_origin_problem(p, size)
            if bad_origin:
                bad(bad_origin)
        for m in p.get("marks") or []:
            if not isinstance(m.get("at"), (int, float)):
                bad("a mark on %s has no number at \"at\"" % pid)
            if m.get("kind", "alarm") not in KINDS:
                bad("a mark on %s is of kind %r - alarm, trip or limit" % (pid, m.get("kind")))
            if m.get("dir", "up") not in ("up", "down"):
                bad("a mark on %s has dir %r - up or down" % (pid, m.get("dir")))

    def target(ref, what):
        if not isinstance(ref, str):
            bad("%s names no part" % what)
            return
        base, _, sub = ref.partition(".")
        if base not in ids:
            bad("%s moves %s, which is not a part" % (what, ref))
        elif sub and sub not in SUBS.get(kinds.get(base), ()):
            bad("%s moves %s - a %s has no %r value" % (what, ref, kinds.get(base), sub))
        elif sub in ("burst", "drift") and not given[base].get(sub):       # "T.burst" needs "burst" on the tank, "C.drift" needs "drift" on the cloud
            bad("%s moves %s, but %s has no %r option - the part draws that value only when its spec asks for it" % (what, ref, base, sub))

    def acts(lst, what):
        for a in lst or []:
            if not (isinstance(a, list) and len(a) >= 2 and isinstance(a[1], (int, float))):
                bad("%s has a move that is not [part, to, ms, delay, ease]" % what)
                continue
            target(a[0], what)
            if len(a) > 2 and not (isinstance(a[2], (int, float)) and a[2] >= 0):
                bad("%s: the time of a move on %s is not a number of milliseconds" % (what, a[0]))

    for p in parts:
        for m in (p.get("marks") or []) if isinstance(p, dict) else []:
            acts(m.get("then"), "the mark at %s on %s" % (m.get("at"), p.get("id")))
    for k, s in enumerate(spec.get("steps") or [], 1):
        what = "step %d" % k
        if not s.get("title"):
            bad("%s has no title - it is the line under the figure" % what)
        for ref in (s.get("set") or {}):
            target(ref, what)
        acts(s.get("play"), what)
        if not s.get("play") and not s.get("set"):
            bad("%s moves nothing - a step that changes nothing is a caption, not a step" % what)
        for ln in ([] if s.get("line") is None else [s["line"]] if not isinstance(s["line"], list) else s["line"]):
            if not isinstance(ln, int) or ln < 1:
                bad("%s lights line %r - a line number from 1" % (what, ln))
    return probs


def load_spec(path):
    try:
        return json.loads(read(path)), None
    except ValueError as err:
        return None, "%s: not valid JSON - %s" % (path, err)


def local_types(parts_js):
    return set(n for n, _ in blocks(read(parts_js))) if parts_js and os.path.isfile(parts_js) else set()


# ------------------------------------------------------------------ CLI
def report(probs, checked):
    for p in probs:
        print("  - " + p)
    print(("%d problem(s)" % len(probs)) if probs else "clean", "-", checked)
    return 1 if probs else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("spec"); a.add_argument("files", nargs="+"); a.add_argument("--parts")
    b = sub.add_parser("parts"); b.add_argument("file")
    c = sub.add_parser("module"); c.add_argument("module_dir"); c.add_argument("--figures")
    o = ap.parse_args(argv)
    types = kit_types()
    if o.cmd == "parts":
        if not os.path.isfile(o.file):
            print("nothing to check - %s is not there" % o.file)
            return 2
        probs, names = check_parts_file(o.file)
        return report(probs, "%d new part(s): %s" % (len(names), ", ".join(names) or "none"))
    if o.cmd == "spec":
        types |= local_types(o.parts)
        probs = []
        for f in o.files:
            spec, err = load_spec(f)
            probs += [err] if err else check_spec(spec, types, os.path.basename(f))
        return report(probs, "%d spec(s)" % len(o.files))
    parts_js = os.path.join(o.module_dir, "assets", "kit_parts.js")
    probs, names = check_parts_file(parts_js) if os.path.isfile(parts_js) else ([], [])
    types |= set(names)
    specs = sorted(glob.glob(os.path.join(o.figures, "*.kit.json"))) if o.figures else []
    for f in specs:
        spec, err = load_spec(f)
        probs += [err] if err else check_spec(spec, types, os.path.basename(f))
    if not specs and not names:
        print("nothing to check - no kit_parts.js and no *.kit.json (give --figures)")
        return 2
    return report(probs, "%d spec(s), %d new part(s)" % (len(specs), len(names)))


if __name__ == "__main__":
    sys.exit(main())
