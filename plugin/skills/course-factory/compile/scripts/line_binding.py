#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Every line a slide lights changes its figure to the thing the line names.

    python line_binding.py <deck index.html> [...]      the findings on a built deck (exit 1 when there are any)

The deck walks a slide's figure and its lines with one counter (gb_deck.js lockFor; gb_steps.js on a slide of points or
stops): while line N is lit the figure stands at the step whose "line" is N. compile_module.py runs these checks on the
page it writes, and each finding is a must-fix:

  UNBOUND   a line no step lights: Next lights it while the figure stands still; or a figure whose steps name no line
            at all, so nothing ties a step to the line it shows
  STILL     a drawn figure (a 3D scene, a 2D kit figure) with no step, or one, beside two lines or more: the words change
            and the picture never does; a 3D step with the same view, part and labels as the step before (a 2D step that
            sets nothing new is compile_module.py's dead_figure_problems)
  AGAIN     a step that lights the line the step before lit: a Next that lights nothing new and only turns the view.
            It is how a figure falls one stop behind: an opening view on line 1, the part line 1 names on line 2 ...
            and the last two steps on the last line
  SUBJECT   (a 3D scene, a figure-kit or 2D figure whose parts carry names) a step whose line names a part the figure
            labels, while the step shows other parts - and "one stop behind" when what it shows is what the line before
            names; (a 3D scene) a step whose line names a kind of thing the scene has (a hold space, a drip tray, a door),
            while it points at a part of no kind the line names
  MISSING   (a 3D scene) a line names a thing the kit draws - an airlock, its doors and alarm, a compressor or motor room, a
            sensor, a drip tray, a dome, seats - and the scene has none
  COMPARE   (a 3D scene of two hulls or more, or of tanks with no hull) a step whose line compares, or names two of them,
            while it frames only one: they are framed together at one scale (check_kit3d.py: in a row square to the view)

A slide whose words end in a question with its answer (a vote, a pick, a worked example) plays its last steps with the
answer: only AGAIN and SUBJECT are judged there. A slide the build sheet shows whole (data-still) is not walked.
"""
from __future__ import annotations

import io
import json
import os
import re
import sys

SLIDE = re.compile(r'<section\b([^>]*)\bid="([^"]+)"([^>]*)>(.*?)</section>', re.S)
SPEC = re.compile(r'<script type="application/json" id="(k3|k2|kit)-[^"]*">(.*?)</script>', re.S)
LINE = re.compile(r'<(\w+)\b[^>]*\bdata-i="(\d+)"[^>]*>(.*?)</\1>', re.S)
POINTS = re.compile(r'<ul class="lt-points">(.*?)</ul>', re.S)
POINT = re.compile(r'<li\b[^>]*\bdata-k="\d+"[^>]*>(.*?)</li>', re.S)
ANSWER = re.compile(r'class="[^"]*\b(you|lt-why|lt-opts|lt-vote)\b')
WHAT = {"k3": "its 3D scene", "k2": "its 2D figure", "kit": "its figure"}
# words that name nothing on their own: a line and a label sharing only these share no subject
STOP = set("""a an the of in on at to for from by with and or is are be been it its this that these those as not no into
over under up down out off per about each every one two three all any some only than then when while which what who how
can may must should will would has have had does do there their they them his her our your you more most less least very
also both but if so such same other another first second third last next new used use uses using made make makes give gives
kept keep keeps let lets like near between through without within after before above below behind beside across along
where here same type types kind kinds part parts""".split())
# names of a kind of thing, not of one thing: a line about "the vapour space" names no "Hold space"
WEAK = set("""tank space room area zone line pipe unit deck hull ship vessel gas cargo system side end top bottom level""".split())


def clean(fragment):
    """the words of an HTML fragment"""
    return " ".join(re.sub(r"<[^>]+>", " ", fragment or "").split())


def words(text):
    """the words of a line or a label that can name a thing: three letters or more, not a little word, a plural made
    singular"""
    out = set()
    for w in re.findall(r"[^\W\d_]{3,}", str(text or "").lower()):
        if w in STOP:
            continue
        out.add(w[:-1] if len(w) > 3 and w.endswith("s") and not w.endswith("ss") else w)
    return out


def slide_lines(body):
    """{line number: words} - the lines Next lights on a slide, counted from 1 as the deck counts them: its data-i lines,
    or on a slide of points (.lt-points) its points in order"""
    plain = re.sub(r"<svg\b.*?</svg>|<script\b.*?</script>", "", body, flags=re.S)
    out = {}
    for m in LINE.finditer(plain):
        out.setdefault(int(m.group(2)), clean(m.group(3)))
    if out:
        return out
    pts = POINTS.search(plain)
    return {k: clean(x) for k, x in enumerate(POINT.findall(pts.group(1)), 1)} if pts else {}


def step_lines(st):
    """the lines a step lights: its "line", one number or a list"""
    ln = st.get("line") if isinstance(st, dict) else None
    return [int(x) for x in (ln if isinstance(ln, list) else [] if ln is None else [ln])
            if isinstance(x, int) and not isinstance(x, bool) or (isinstance(x, str) and x.isdigit())]


def _list(v):
    return [x for x in (v if isinstance(v, list) else [v]) if isinstance(x, str)]


def subjects(kind, spec):
    """[[label words of what step k shows] or None (cannot be judged) for each step], and every label the figure has
    ([words])"""
    steps = [st if isinstance(st, dict) else {} for st in spec.get("steps") or []]
    if kind == "k3":
        groups = spec.get("groups") if isinstance(spec.get("groups"), dict) else {}
        named = {}
        for lb in spec.get("labels") or []:
            if isinstance(lb, dict) and isinstance(lb.get("text"), str):
                named.setdefault(str(lb.get("part")), []).append(lb["text"])
        out = []
        for st in steps:
            shown = _list(st.get("labels"))
            if not shown:
                focus = []
                for k in _list(st.get("select")) + _list((st.get("view") or {}).get("frame") if isinstance(st.get("view"), dict) else []):
                    focus += _list(groups.get(k)) or [k]
                shown = focus
            out.append([words(t) for k in shown for t in named.get(k, [])] or None)
        return out, [words(t) for ts in named.values() for t in ts]
    parts = [p for p in spec.get("parts") or [] if isinstance(p, dict)]
    said = lambda p: " ".join(str(p.get(k)) for k in ("label", "text", "sub", "name") if isinstance(p.get(k), str))
    if kind == "kit":
        byid = {str(p.get("id")): said(p) for p in parts if p.get("id")}
        out = []
        for st in steps:
            ids = [str(a[0]).split(".")[0] for a in st.get("play") or [] if isinstance(a, list) and a]
            ids += [str(k).split(".")[0] for k in (st.get("set") or {}) if isinstance(st.get("set"), dict)]
            out.append([words(byid[i]) for i in ids if byid.get(i)] or None)
        return out, [words(t) for t in byid.values() if t]
    reads = {}                                           # a 2D part moves through the states it reads ("@name")
    for p in parts:
        names = set()
        for k, v in p.items():
            if isinstance(v, str) and v.startswith("@"):
                names.add(v[1:])
        if said(p):
            reads[said(p)] = names
    out, now = [], dict(spec.get("state") or {}) if isinstance(spec.get("state"), dict) else {}
    for st in steps:
        sets = st.get("set") if isinstance(st.get("set"), dict) else {}
        up = {k for k, v in sets.items() if now.get(k) != v and v}      # turned on or moved: what this step brings in
        now.update(sets)
        out.append([words(t) for t, names in reads.items() if names & up] if up else None)   # [] - it moved only unnamed parts
    return out, [words(t) for t in reads if t]


def _says(line, label_words):
    """the labels a line names: those sharing a word with it that is more than a kind of thing"""
    return [w for w in label_words if (w & line) - WEAK]


def subject_problems(kind, spec, lines):
    """[sentence] - steps that show something other than what their line names (SUBJECT)"""
    shows, labels = subjects(kind, spec)
    if not labels:
        return []
    lw = {n: words(t) for n, t in lines.items()}
    behind, other = [], []
    for k, (st, seen) in enumerate(zip(spec.get("steps") or [], shows)):
        ln = step_lines(st)
        if seen is None or len(ln) != 1 or ln[0] not in lw or (isinstance(st, dict) and st.get("reveal")):
            continue
        n = ln[0]
        want = _says(lw[n], labels)
        if not want or _says(lw[n], seen):
            continue
        name = lambda ws: "/".join(sorted(ws[0]))[:40] if ws else "nothing it names (only unnamed parts move)"
        if n > 1 and _says(lw.get(n - 1, set()), seen):
            behind.append((k, n))
        else:
            other.append("step %d lights line %d, which names %s, and shows %s" % (k, n, name(want), name(seen)))
    out = []
    if behind:
        out.append("the figure runs one stop behind its words - %s shows what the line before names. Give each line the step "
                   "that shows what it names: line 1's subject on the step that lights line 1 (the opening step), never an "
                   "overview first" % "; ".join("step %d (line %d)" % x for x in behind[:4]))
    if other:
        out.append("a step does not show what its line names - %s. Point the step at the part the line names (its "
                   "\"select\", \"frame\" and \"labels\")" % "; ".join(other[:3]))
    return out


# ------------------------------------------------------------------ a 3D scene: the things its lines name, the things it compares
# What kind of thing a scene's part is (an airlock, a door, a sensor, a drip tray ...) is check_kit3d's (course-visuals/kit3d),
# read from the kit's own catalogue
_CK = []
# the kinds of thing a line names that its 3D scene draws: a line about the alarm on both sides of an airlock, beside a scene
# with no alarm in it, teaches what no one can see (gas trial M01 s16, s17, s13: no alarm, no compressor room)
DRAWN = ("airlock", "compressor room", "motor room", "partial secondary barrier", "door", "alarm", "sensor", "dome", "tank cover",
         "seat")
# ... and the kinds a step must point at when its line names one the scene has (pointing at another kind the line names, or a
# part whose label shares the line's words, is pointing at it too)
POINTED = DRAWN + ("secondary barrier", "hold space", "cofferdam", "ballast tank", "accommodation")
# words that compare: a line that weighs two things against each other shows both at once
COMPARES = re.compile(r"\b(compar\w*|versus|vs\.?|than|both|same|differ(?:s|ent)?|whereas|unlike|side\s+by\s+side|greater|further|"
                      r"farther|thinner|thicker|smaller|larger|bigger|higher|lower|more|less|fewer)\b", re.I)


def _kit3d():
    """(check_kit3d, the kit's catalogue) - or (None, {}) when the 3D kit's checker is not beside the factory"""
    if not _CK:
        here = os.path.dirname(os.path.abspath(__file__))
        sys.path.insert(0, os.path.join(here, "..", "..", "..", "course-visuals", "kit3d", "scripts"))
        try:
            import check_kit3d as ck
            _CK.extend([ck, ck.read_catalog()[0] or {}])
        except Exception:                                  # noqa: BLE001 - the line checks stand without it
            _CK.extend([None, {}])
    return _CK[0], _CK[1]


def scene_kinds(spec):
    """(check_kit3d, {kind: [ids of that kind]}, the scene's parts, its roles, its part table)"""
    ck, types = _kit3d()
    if ck is None:
        return None, {}, [], {}, {}
    parts = [p for p in spec.get("parts") or [] if isinstance(p, dict)]
    table, roles = ck.part_table(parts, types), ck.hull_roles(parts, types)
    have = {k[0]: [i for i in table if ck.is_kind(i, k[0], table, parts, roles)] for k in ck.KINDS}
    return ck, have, parts, roles, table


def pointed_at(spec, k, st):
    """the ids a step points at: what it selects and the parts of the labels it shows, with their sub-parts"""
    groups = spec.get("groups") if isinstance(spec.get("groups"), dict) else {}
    ids = set()
    for x in _list(st.get("select")):
        ids |= set(_list(groups.get(x))) or {x}
    for lb in spec.get("labels") or []:
        if not isinstance(lb, dict) or lb.get("tap_only") or not isinstance(lb.get("part"), str):
            continue
        if isinstance(lb.get("steps"), list) and k not in lb["steps"]:
            continue
        if isinstance(st.get("labels"), list) and lb["part"] not in st["labels"]:
            continue
        ids |= set(_list(groups.get(lb["part"]))) or {lb["part"]}
    return ids


def scene_problems(spec, lines):
    """[sentence] - a 3D scene against its slide's lines: a thing a line names that the scene does not draw (MISSING), a step
    that points elsewhere while its line names a thing the scene has (SUBJECT), and a step whose line compares two hulls or
    tanks while it frames only one (COMPARE)"""
    ck, have, parts, roles, table = scene_kinds(spec)
    if ck is None:
        return []
    out, missing = [], {}
    for n, text in sorted(lines.items()):
        for _, kind in ck.kinds_named(text):
            if kind in DRAWN and not have.get(kind):
                missing.setdefault(kind, []).append(n)
    for kind, ns in missing.items():
        out.append("line%s %s name%s %s %s, and the scene has none - the words teach what no one can see: draw it (%s, "
                   "course-visuals\\kit3d\\PARTS.md)" % ("s" if len(ns) > 1 else "", "+".join(str(x) for x in ns),
                                                      "" if len(ns) > 1 else "s", "an" if kind[0] in "aeiou" else "a", kind,
                                                      ck.KIND_OF[kind][5]))
    steps = [st if isinstance(st, dict) else {} for st in spec.get("steps") or []]
    wrong = []
    for k, st in enumerate(steps):
        ln = step_lines(st)
        if len(ln) != 1 or ln[0] not in lines or st.get("reveal"):
            continue
        named = [kind for _, kind in ck.kinds_named(lines[ln[0]]) if have.get(kind)]
        ids = pointed_at(spec, k, st)
        if not ids or not any(kind in POINTED for kind in named):
            continue
        said = [words(lb["text"]) for lb in spec.get("labels") or [] if isinstance(lb, dict) and lb.get("part") in ids
                and isinstance(lb.get("text"), str) and not ck.kinds_named(lb["text"])]     # a label naming a kind is judged by it
        if any(i in have[kind] for kind in named for i in ids) or _says(words(lines[ln[0]]), said):
            continue
        named = [kind for kind in named if kind in POINTED]
        if named:
            wrong.append("step %d lights line %d, which names %s %s, and points at %s - point it at %s" % (
                k, ln[0], "an" if named[0][0] in "aeiou" else "a", named[0], ", ".join(sorted(ids))[:60], " / ".join(have[named[0]][:3])))
    if wrong:
        out.append("a step points away from the thing its line names - %s" % "; ".join(wrong[:3]))
    peers = ck.peers_of(parts)
    if len(peers) >= 2:
        label_words = {}
        for lb in spec.get("labels") or []:
            if isinstance(lb, dict) and isinstance(lb.get("text"), str):
                label_words.setdefault(lb.get("part"), []).append(words(lb["text"]))
        alone = []
        for k, st in enumerate(steps):
            ln = step_lines(st)
            if len(ln) != 1 or ln[0] not in lines:
                continue
            lw = words(lines[ln[0]])
            said = [pid for pid, _, ids in peers if any(_says(lw, label_words.get(i, [])) for i in ids)]
            if not (COMPARES.search(lines[ln[0]]) or len(said) >= 2):
                continue
            view = st.get("view") if isinstance(st.get("view"), dict) else {}
            frame = set(_list(view.get("frame")))
            shown = [pid for pid, _, ids in peers if not frame or set(ids) & frame]
            if len(shown) < len(peers):
                alone.append("step %d (line %d) frames %s of %s" % (k, ln[0], " and ".join(shown) or "none", " and ".join(p[0] for p in peers)))
        if alone:
            out.append("a line compares and its step shows one side of it - %s. Frame them together at one scale (\"frame\": [%s]), "
                       "in a row square to the view" % ("; ".join(alone[:3]), ", ".join('"%s"' % p[0] for p in peers)))
    return out


def slide_problems(sid, head, body):
    """[(slide id, sentence)] - one slide's figure against its lines"""
    if " data-still" in head:
        return []
    lines = slide_lines(body)
    n = len(lines)
    ask = bool(ANSWER.search(body))
    out = []
    for m in SPEC.finditer(body):
        try:
            spec = json.loads(m.group(2).replace("<\\/", "</"))
        except ValueError:
            continue
        if not isinstance(spec, dict):
            continue
        kind, what = m.group(1), WHAT[m.group(1)]
        steps = [st if isinstance(st, dict) else {} for st in spec.get("steps") or []]
        walked = [st for st in steps if not st.get("reveal")]
        named = sorted({x for st in walked for x in step_lines(st)})
        if not ask and n >= 2 and kind in ("k3", "k2") and len(walked) < 2:
            out.append((sid, "%s never changes while its %d lines are lit - give each line a step that shows what it names "
                             "(\"line\": 1 .. %d), or show the slide whole when it is a definition, a limit or a quoted rule "
                             "(the build sheet's \"still\": true)" % (what, n, n)))
            continue
        if not ask and n >= 2 and len(walked) >= 2 and not named:
            out.append((sid, "%s has %d steps that name no line, beside %d lines - nothing ties a step to the line it "
                             "shows, so the figure and the words drift apart (a slide of points walked them one after the "
                             "other). Give each line its step (\"line\": 1 .. %d)" % (what, len(walked), n, n)))
        elif not ask and named:
            last = max(named)
            gaps = [x for x in range(1, min(last, n) + 1) if x not in named]
            if kind == "kit":                       # a figure-kit figure opens idle, before its first step: that is line 1's
                gaps = [x for x in gaps if x != 1] + [x for x in range(last + 1, n + 1)]
            if gaps:
                out.append((sid, "%s has no step for line%s %s - Next lights %s while the figure stands still. Give each "
                                 "line the step that shows what it names" % (
                                     what, "s" if len(gaps) > 1 else "", ", ".join(str(x) for x in gaps),
                                     "them" if len(gaps) > 1 else "it")))
        again = [(k, step_lines(st)) for k, st in enumerate(steps) if k and step_lines(st)
                 and step_lines(st) == step_lines(steps[k - 1]) and not st.get("reveal") and not steps[k - 1].get("reveal")]
        if again:
            out.append((sid, "%s lights the same line on two Nexts in a row - %s. A Next lights a new line: put what the "
                             "second step shows into the first (a 2D step tells its story in order with \"after\"), or give "
                             "it the line that names it" % (what, "; ".join(
                                 "steps %d and %d both light line %s" % (k - 1, k, "+".join(str(x) for x in ln))
                                 for k, ln in again[:3]))))
        if kind == "k3":
            look = lambda st: json.dumps([st.get(k) for k in ("view", "select", "labels", "state", "anim")], sort_keys=True)
            same = [k for k, st in enumerate(steps) if k and step_lines(st) and look(st) == look(steps[k - 1])]
            if same:
                out.append((sid, "%s does not change on step%s %s - the same view, part and labels as the step before, while "
                                 "a new line is lit. Point each step at what its line names (\"frame\", \"select\", \"labels\")"
                                 % (what, "s" if len(same) > 1 else "", ", ".join(str(k) for k in same))))
        out += [(sid, "%s: %s" % (what, x)) for x in subject_problems(kind, spec, lines)]
        if kind == "k3":
            out += [(sid, "%s: %s" % (what, x)) for x in scene_problems(spec, lines)]
    return out


def deck_problems(page):
    """[(slide id, sentence)] - every slide of a built deck"""
    out = []
    for m in SLIDE.finditer(page):
        out += slide_problems(m.group(2), m.group(1) + m.group(3), m.group(4))
    return out


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    files = list(sys.argv[1:] if argv is None else argv)
    if not files:
        print(__doc__)
        return 2
    found = 0
    for f in files:
        got = deck_problems(io.open(f, encoding="utf-8").read())
        print("%s: %d finding(s)" % (f, len(got)))
        for sid, msg in got:
            print("  - %s: %s" % (sid, msg))
        found += len(got)
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
