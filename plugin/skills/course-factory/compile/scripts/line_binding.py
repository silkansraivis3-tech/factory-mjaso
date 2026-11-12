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
            names

A slide whose words end in a question with its answer (a vote, a pick, a worked example) plays its last steps with the
answer: only AGAIN and SUBJECT are judged there. A slide the build sheet shows whole (data-still) is not walked.
"""
from __future__ import annotations

import io
import json
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
