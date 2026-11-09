#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""figure_why - every figure has a teaching reason (2.116.0, operator Aleksis Vejs, 2026-11-09).

    python figure_why.py spec.kit2d.json [--flat]

The Project Management review: drawings that never moved, empty charts, 3D added where it taught nothing. "Draw the drawings
2D kit and 3D with a reason, don't just put it in because." So every kit figure (.kit.json, .kit2d.json), every 3D model
(.kit3d.json) and every custom figure (build sheet "custom_figure") carries

    "why":      one of mechanism | sequence | comparison | quantity-change | spatial | real-thing-recognition | still
    "why_text": ONE sentence - what the trainee sees change, or sees

in its spec (or, for a custom figure, in its build-sheet entry). The checks refuse:
  * no why, an unknown why, no why_text;
  * a why its steps do not serve - sequence / mechanism: at least two steps tied to lit lines; quantity-change: a state value
    that differs between stops; comparison: at least two states (one step away from the first, or a second picture);
  * spatial / a 3D model on a slide whose visual is a flat idea (a chart, a matrix, a checklist - media-and-tasks.json
    three_d.flat_words).
A slide may have NO picture at all when its words read on their own - there is no picture quota anywhere.

Used by content_script.py (v_why, build sheet level), compile_module.py (before building) and check_kit.py.
"""
from __future__ import annotations

import json
import re
import sys

WHYS = ("mechanism", "sequence", "comparison", "quantity-change", "spatial", "real-thing-recognition", "still")
NEEDS_LINES = ("sequence", "mechanism")


def _lines(step):
    ln = step.get("line") if isinstance(step, dict) else None
    return [] if ln is None else ln if isinstance(ln, list) else [ln]


def _tied(step):
    """a step the deck's Next reaches with a lit line, or plays with the answer (reveal)"""
    return isinstance(step, dict) and (bool(_lines(step)) or bool(step.get("reveal")))


def _moves(step):
    return isinstance(step, dict) and any(step.get(k) for k in ("set", "play", "select", "labels", "state", "reveal"))


def _differs(initial, steps):
    """some state value differs between stops (the spec's own state, then each step's "set"/"state")"""
    now = dict(initial or {})
    seen = {k: {repr(v)} for k, v in now.items()}
    for st in steps:
        for src in ("set", "state"):
            for k, v in ((st.get(src) or {}) if isinstance(st, dict) else {}).items():
                if isinstance(v, (int, float, str)):
                    seen.setdefault(k, {repr(now.get(k, 0))}).add(repr(v))
                    now[k] = v
    return any(len(v) > 1 for v in seen.values())


def check(spec_why, spec_text, steps, kind="kit2d", initial=None, flat_word="", figure_b=False):
    """-> [problem, ...] (empty when the figure's why is declared and its steps serve it). kind: kit | kit2d | kit3d | custom.
    steps: the figure's steps as dicts; initial: the spec's state at step 0; flat_word: the word that makes the slide's visual
    a flat idea ("" when it is not)"""
    out = []
    why = str(spec_why or "").strip()
    if not why:
        return ["has no \"why\" - say why this %s figure is drawn: one of %s (and \"why_text\": one sentence, what the trainee "
                "sees change or see). A slide may have no picture at all when its words read on their own"
                % (kind, ", ".join(WHYS))]
    if why not in WHYS:
        return ["\"why\": %r is not one of %s" % (why, ", ".join(WHYS))]
    if not str(spec_text or "").strip():
        out.append("\"why\": %s has no \"why_text\" - one sentence: what the trainee sees change (or sees)" % why)
    steps = [s for s in (steps or []) if isinstance(s, dict)]
    if why in NEEDS_LINES:
        tied = [s for s in steps if (_tied(s) if kind != "kit3d" else _moves(s) or _lines(s))]
        if len(steps) < 2 or len(tied) < 2:
            out.append("\"why\": %s needs at least two steps tied to lit lines (\"line\") or a reveal - this figure has %d step(s), "
                       "%d tied: give the steps the lines they show, or say \"why\": \"still\" if the drawing does not change"
                       % (why, len(steps), len(tied)))
    elif why == "quantity-change":
        if not _differs(initial, steps):
            out.append("\"why\": quantity-change needs a value that differs between stops - no state in this figure changes "
                       "between its steps: set the numbers each step shows (\"set\")")
    elif why == "comparison":
        if not (figure_b or any(_moves(s) for s in steps)):
            out.append("\"why\": comparison needs two states to compare - a step that changes the figure from its first look, "
                       "or a second picture (figure_b); this figure shows one state")
    if flat_word and (why == "spatial" or kind == "kit3d"):
        out.append("\"why\": %s on a slide whose visual is a flat idea (\"%s\") - a 3D model or a spatial reason adds weight, not "
                   "understanding: a 2D drawing, a chart or an animation says it better" % (why, flat_word))
    return out


def declared(entry, spec):
    """(why, why_text) from the build-sheet entry first, then the spec itself"""
    e, s = entry or {}, spec if isinstance(spec, dict) else {}
    return (e.get("why") or s.get("why") or ""), (e.get("why_text") or s.get("why_text") or "")


# a custom figure's steps: <script type="application/json" data-custom-steps>[{"line": 2}, {"line": 3, "reveal": true}]</script>
CUSTOM_STEPS = re.compile(r"<script\b[^>]*\bdata-custom-steps\b[^>]*>(.*?)</script>", re.S | re.I)
NETWORK = re.compile(r"""(?:\b(?:src|href|action|poster|data)\s*=\s*["']\s*(?:https?:)?//(?!www\.w3\.org/)|"""
                     r"""url\(\s*["']?\s*(?:https?:)?//|@import\s+(?:url\()?\s*["']?(?:https?:)?//|"""
                     r"""\bimport\s*\(?\s*["'](?:https?:)?//|\bfetch\s*\(\s*["'](?:https?:)?//|\bXMLHttpRequest\b|"""
                     r"""\bnew\s+WebSocket\b)""", re.I)


def custom_steps(html):
    """[step dicts] a custom figure declares, or None when it declares none / the JSON is broken"""
    m = CUSTOM_STEPS.search(html or "")
    if not m:
        return None
    try:
        data = json.loads(m.group(1))
    except ValueError:
        return None
    data = data.get("steps") if isinstance(data, dict) else data
    return [x for x in data if isinstance(x, dict)] if isinstance(data, list) else None


def custom_problems(html, sid, why_known=True):
    """-> [problem] for a custom figure's own contract: it is offline (no network), it reaches the deck's Next (a hook for the
    slide in GB_HOOKS, or no steps declared and why still), it declares its steps"""
    out = []
    if NETWORK.search(html or ""):
        out.append("a custom figure must work offline - it loads or calls something over the network (src / href / url() / "
                   "import / fetch / XMLHttpRequest): bundle it into the file")
    if re.search(r"<script\b[^>]*\bsrc\s*=", html or "", re.I):
        out.append("a custom figure is one self-contained file - no <script src>: put the code inside it (it is offline in the classroom)")
    if custom_steps(html) is None and not re.search(r"GB_HOOKS", html or ""):
        out.append("a custom figure declares its steps (<script type=\"application/json\" data-custom-steps>[{\"line\": 2}, ...] "
                   "</script>) and registers GB_HOOKS.%s = {enter, leave, step(dir)} so the deck's Next drives it - or it is "
                   "\"why\": \"still\"" % sid)
    return out


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    flat = "--flat" in argv
    files = [a for a in argv if not a.startswith("--")]
    bad = 0
    for f in files:
        with open(f, encoding="utf-8") as fh:
            spec = json.load(fh)
        kind = "kit3d" if f.endswith(".kit3d.json") else "kit2d" if f.endswith(".kit2d.json") else "kit"
        why, text = declared({}, spec)
        for p in check(why, text, spec.get("steps"), kind, spec.get("state"), "flat" if flat else ""):
            print("%s: %s" % (f, p))
            bad += 1
    print("figure_why: %s" % ("clean" if not bad else "%d problem(s)" % bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
