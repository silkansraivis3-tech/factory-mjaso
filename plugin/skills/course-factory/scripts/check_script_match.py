#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Do the built slides and tasks say exactly what the operator approved? (L29)

    check_script_match.py <course folder> --module 1 [--module-dir <folder>]

WHY THIS EXISTS
The operator approves the words of a module before any HTML exists (Stage 3). That approval is
worth nothing if the deck builder then rewords a slide, drops a sentence or adds one. This check is
the QA role's proof that it did not.

HOW THE BUILT FILES ARE MARKED
Every screen built from the script carries its script id, and every piece of approved text carries
its field:

    <section class="slide" data-script="s02">
      <h2 data-script-field="title">Types of containment</h2>
      <p data-script-field="text">Independent tanks: type A, B and C.</p>
      <p data-script-field="text">Membrane tanks rely on the hull for strength.</p>

    <div data-script="q01"> <p data-script-field="question">…</p>
      <button data-script-field="opt.A" data-correct="true">…</button> <p data-script-field="feedback">…</p>

    a task answered by ordering, matching, locating, a scenario ... (2.18.0) carries each visible piece
    of its answer as <span data-script-field="answer">…</span> - in any order, since the tablet shuffles
    them - and the pieces marked right in the script carry data-correct="true" too.

WHAT IT CHECKS
  1  the script is approved, and has not changed since it was approved
  2  every screen in the script is built somewhere in the module folder, and nothing else claims a
     script id the script does not have
  3  every marked field says exactly the approved words (spacing aside); a slide's text lines match
     in order; the answer marked data-correct is the approved correct answer
  4  a slide carries no visible words outside its marked fields - except its header band, the
     source and credit lines, the text inside a drawing, controls, instructor cues, and anything
     marked data-script-ignore, which is counted in the report so QA can look at it
Exit 0 when everything matches, 1 when anything does not, 2 on bad input.
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import io
import json
import os
import re
import sys
from html.parser import HTMLParser

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import content_script as cs  # noqa: E402

EXEMPT_CLASSES = {"slide-kind", "src", "srcline", "credit", "mediabar", "fbtn", "dots", "gbt-topback", "photo-badge"}
EXEMPT_TAGS = {"svg", "script", "style", "button", "noscript", "template"}
VOID = {"br", "img", "hr", "input", "meta", "link", "source", "area", "base", "col", "embed", "param", "track", "wbr"}
norm = lambda s: re.sub(r"\s+", " ", s or "").strip()


class Collect(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []          # (tag, attrs)
        self.screens = {}        # id -> {"fields": {field: [texts]}, "loose": [texts], "ignored": n, "correct": [fields]}
        self.buf = None

    def _ctx(self):
        sid = field = None
        exempt = False
        for tag, a in self.stack:
            if "data-script" in a:
                sid = a["data-script"]
            if "data-script-field" in a:
                field = a["data-script-field"]
            cls = set((a.get("class") or "").split())
            # data-cue is NOT here: it is an attribute that is never shown, and slides carry it on the
            # slide itself - exempting it would exempt every word on the slide.
            if tag in EXEMPT_TAGS or cls & EXEMPT_CLASSES or "data-script-ignore" in a:
                exempt = True
        return sid, field, exempt

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "data-script" in a:
            self.screens.setdefault(a["data-script"], {"fields": {}, "flags": {}, "loose": [], "ignored": 0, "correct": []})
        if "data-script-ignore" in a:
            sid = self._ctx()[0] or a.get("data-script")
            if sid in self.screens:
                self.screens[sid]["ignored"] += 1
        if "data-script-field" in a and a.get("data-correct") == "true":
            sid = self._ctx()[0]
            if sid in self.screens:
                self.screens[sid]["correct"].append(a["data-script-field"])
        if tag not in VOID:
            self.stack.append((tag, a))
            if "data-script-field" in a:
                sid = self._ctx()[0]
                if sid in self.screens:
                    self.screens[sid]["fields"].setdefault(a["data-script-field"], []).append("")
                    self.screens[sid]["flags"].setdefault(a["data-script-field"], []).append(a.get("data-correct") == "true")

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]
                break

    def handle_data(self, data):
        if not data.strip():
            return
        sid, field, exempt = self._ctx()
        if sid not in self.screens:
            return
        s = self.screens[sid]
        if field:
            s["fields"][field][-1] += data
        elif not exempt:
            s["loose"].append(norm(data))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("course")
    ap.add_argument("--module", required=True)
    ap.add_argument("--module-dir", help="the built module's folder (default: <course>/modules/m<N>)")
    a = ap.parse_args(argv)
    p = cs.paths(a.course, a.module)
    if not os.path.isfile(p["script"]):
        print("Stopped - there is no content script for module %s:\n    %s" % (a.module, p["script"]))
        return 2
    script = cs.load(p["script"])
    mdir = a.module_dir or os.path.join(a.course, "modules", "m%s" % a.module)
    files = [f for f in glob.glob(os.path.join(mdir, "**", "*.html"), recursive=True)]
    if not files:
        print("Stopped - no built pages were found in\n    %s" % mdir)
        return 2
    found = {}
    for f in files:
        c = Collect()
        c.feed(io.open(f, encoding="utf-8", errors="replace").read())
        for sid, v in c.screens.items():
            found.setdefault(sid, dict(v, file=os.path.relpath(f, mdir)))
    probs, notes = [], []
    if not (script.get("status") == "approved" and script.get("approved_hash") == cs.content_hash(script)):
        probs.append("the content script of module %s is not approved (or changed after approval) - the slides "
                     "must be built from an approved script (L29)" % a.module)
    ids = {s["id"] for s in script["screens"]}
    for sid in sorted(set(found) - ids):
        probs.append("%s (%s) claims script id %s, which the approved script does not have" % (found[sid]["file"], sid, sid))
    for s in script["screens"]:
        sid = s["id"]
        where = "%s (%s)" % (cs.place(script, sid), sid)
        if sid not in found:
            probs.append("%s is not built - no page in the module carries data-script=\"%s\"" % (where, sid))
            continue
        got = found[sid]
        fields = {k: [norm(x) for x in v] for k, v in got["fields"].items()}
        if s["kind"] in cs.TASKS:
            want = {"question": s.get("question", ""), "feedback": s.get("feedback", "")}
            if cs.uses(s, "options"):
                for L, o in zip(cs.letters(len(s.get("options", []))), s.get("options", [])):
                    want["opt." + L] = o
            for f, w in want.items():
                g = " ".join(fields.get(f, []))
                if norm(w) != g:
                    probs.append("%s in %s: %s says \"%s\" - approved: \"%s\"" % (where, got["file"], f, g or "(missing)", norm(w)))
            if cs.uses(s, "options"):
                marked = sorted(x[4:] for x in got["correct"] if x.startswith("opt."))
                if marked != sorted(cs.correct_letters(s)):
                    probs.append("%s in %s: the answer marked correct is %s - approved: %s" % (
                        where, got["file"], ", ".join(marked) or "none", s.get("correct")))
            if cs.uses(s, "answer") and cs.mech(s) != "set_value":
                items, right = cs.answer_items(s)
                built = fields.get("answer", [])
                if sorted(norm(x) for x in items) != sorted(built):
                    probs.append("%s in %s: the answer's items are not the approved ones - approved: \"%s\" / built: \"%s\"" % (
                        where, got["file"], " / ".join(norm(x) for x in items), " / ".join(built) or "(missing)"))
                elif right:
                    flagged = sorted(t for t, f in zip(built, got["flags"].get("answer", [])) if f)
                    if flagged != sorted(norm(x) for x in right):
                        probs.append("%s in %s: the items marked right are %s - approved: %s" % (
                            where, got["file"], " / ".join(flagged) or "none", " / ".join(norm(x) for x in right)))
        else:
            if norm(s.get("title", "")) != " ".join(fields.get("title", [])):
                probs.append("%s in %s: the title says \"%s\" - approved: \"%s\"" % (
                    where, got["file"], " ".join(fields.get("title", [])) or "(missing)", norm(s.get("title", ""))))
            want_lines = [norm(x) for x in (s.get("text") or "").split("\n") if norm(x)]
            got_lines = [x for x in fields.get("text", []) if x]
            if want_lines != got_lines:
                probs.append("%s in %s: the slide text does not match the approved words - approved: \"%s\" / built: \"%s\"" % (
                    where, got["file"], " / ".join(want_lines), " / ".join(got_lines) or "(missing)"))
            if got["loose"]:
                probs.append("%s in %s: words on the slide that are not in the approved script: \"%s\"" % (
                    where, got["file"], " / ".join(got["loose"])[:300]))
        if got["ignored"]:
            notes.append("%s in %s: %d element(s) marked data-script-ignore - look at them" % (where, got["file"], got["ignored"]))
    if probs:
        print("The built module does not say exactly what the operator approved:\n")
        for x in probs:
            print("  - " + x)
        print("\n  What to do: the slide or task changes back to the approved words - or, if the new wording is\n"
              "  better, it goes to the operator as a change to the script (content_script.py propose), and is\n"
              "  built only once they have approved it.")
    else:
        print("Every screen of module %s says exactly what the operator approved (%d screens)." % (a.module, len(script["screens"])))
    for x in notes:
        print("  note: " + x)
    return 1 if probs else 0


if __name__ == "__main__":
    sys.exit(main())
