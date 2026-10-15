#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Fast fixes across modules, with the quality kept (L50) - find, one list, one yes, change, one check.

    fix.py sweep    <course> --find space|text|overflow|layout|last-slide|kind|words [--modules 1-3,7] ...
    fix.py propose  <course> --changes changes.json      words for many modules -> ONE list, nothing changed yet
    fix.py apply    <course> --confirmed                 after the operator's one yes: scripts AND built slides
    fix.py approve  <course> --by "<name>" [--despite-findings]   one approval for every module in the batch
    fix.py check    <course> --kind words|layout|package [--modules ...] [--slides s03,s07]
    fix.py standard <course> [--add "<rule>" --said "<operator's words>"]   the course's house decisions
    fix.py sync-shared <course> [--confirmed]            one shared file -> every module's own copy

WHY THIS EXISTS
On GAS ADVANCED one module took 1-1.5 h to build and a small fix about 30 minutes (FEEDBACK_LOG #61-#93).
A fix ran the build's whole process: a fixer agent per module re-measuring every slide at two sizes, the
orchestrator re-checking, a whole-course QA, a visual sweep - and the same wish ("the last slide like
this", "text bigger") repaired by hand in 19 copies. The owner, 2026-10-15: "i want for fixes to be faster
and still quality ... it will not go to 3-4 qa reviews". So a fix is its own small process:

  1 FIND     sweep measures or reads every module at once and lists every place, numbered
  2 ONE YES  the operator sees one list (sweep's, or propose's) and says yes once for all of it
  3 CHANGE   apply changes the approved words AND the built slides; sync-shared copies a shared part;
             hand work (re-composing a slide) is done by the session, at most 2 agents (fix-rules.json)
  4 ONE CHECK  check runs only what the change can break, once, on the touched modules

THE CHANGES FILE (propose)
    [{"module": 3, "field": "s07.title", "new": "..."},
     {"module": 5, "screen": "s12", "field": "text", "new": "line one\\nline two"},
     {"module": 5, "field": "s12.notes", "new": "..."}]
Words go through each module's content script exactly as content_script.py propose / apply would (L29):
the old words kept, FEEDBACK_LOG written, the review page and Word file made fresh. apply then puts the same
words into the built slides (data-script / data-script-field; the notes into data-cue) wherever that can be
done without guessing, and lists the slides it left for hand work.

Standard library only (the layout sweep and check need Chrome or Edge - measure_slides.py).
"""
from __future__ import annotations

import argparse
import contextlib
import filecmp
import glob
import html
import io
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import date, datetime
from html.parser import HTMLParser

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import content_script as cs  # noqa: E402
import workspace  # noqa: E402

SKILL = os.path.dirname(HERE)
RULES = json.load(io.open(os.path.join(SKILL, "knowledge", "fix-rules.json"), encoding="utf-8"))
norm = lambda s: re.sub(r"\s+", " ", s or "").strip()


# ---------------------------------------------------------------- the course's modules

def module_dirs(course):
    """{number: folder} - modules\\module01 (L45), else modules\\M01_<title> (L43), else modules\\m1."""
    mods, out = os.path.join(course, "modules"), {}
    for pat, rx in (("module[0-9][0-9]", r"module(\d+)$"), ("M[0-9][0-9]_*", r"M(\d+)_"), ("m[0-9]*", r"m(\d+)$")):
        for d in sorted(glob.glob(os.path.join(mods, pat))):
            m = re.match(rx, os.path.basename(d))
            if m and os.path.isdir(d):
                out.setdefault(int(m.group(1)), d)
    return out


def parse_modules(spec, available):
    if not spec or spec.lower() in ("all", "*"):
        return sorted(available)
    want = set()
    for part in spec.replace(" ", "").split(","):
        if "-" in part:
            a, b = part.split("-", 1)
            want.update(range(int(a), int(b) + 1))
        elif part:
            want.add(int(part))
    return [m for m in sorted(want) if m in available]


def deck_file(mdir):
    for n in (os.path.join("presentation", "index.html"), "module.html", "index.html"):
        if os.path.isfile(os.path.join(mdir, n)):
            return os.path.join(mdir, n)
    return None


def fix_dir(course):
    d = workspace.claude_path(course, "fix")
    os.makedirs(d, exist_ok=True)
    return d


# ---------------------------------------------------------------- reading slides without a browser

class Slides(HTMLParser):
    """Every section.slide: its id, title, kind, script id, visible text and the class names inside it."""
    VOID = {"br", "img", "hr", "input", "meta", "link", "source", "area", "base", "col", "embed", "param", "track", "wbr"}
    HIDDEN = {"script", "style", "noscript", "template"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.slides, self.stack, self.cur, self.depth = [], [], None, 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        cls = (a.get("class") or "").split()
        if self.cur is None and tag == "section" and "slide" in cls:
            self.cur = {"id": a.get("id", ""), "title": a.get("data-title", ""), "kind": a.get("data-kind", ""),
                        "script": a.get("data-script", ""), "cue": a.get("data-cue", ""), "text": [], "classes": set(),
                        "n": len(self.slides) + 1}
            self.depth = len(self.stack)
        elif self.cur is not None:
            self.cur["classes"].update(c for c in cls if not re.search(r"\d", c))
        if tag not in self.VOID:
            self.stack.append(tag)

    def handle_endtag(self, tag):
        if tag in self.VOID:
            return
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i] == tag:
                del self.stack[i:]
                break
        if self.cur is not None and len(self.stack) <= self.depth:
            self.slides.append(self.cur)
            self.cur = None

    def handle_data(self, data):
        if self.cur is not None and data.strip() and not (set(self.stack) & self.HIDDEN):
            self.cur["text"].append(norm(data))


def read_slides(deck):
    p = Slides()
    p.feed(io.open(deck, encoding="utf-8", errors="replace").read())
    p.close()
    for s in p.slides:
        s["text"] = " ".join(s["text"])
    return p.slides


def is_end_slide(s):
    sw = RULES["sweeps"]["last-slide"]
    t = (s["title"] or "").lower()
    return s["kind"] in sw["end_kinds"] or any(w in t for w in sw["end_title_words"])


def likeness(a, b):
    if not a and not b:
        return 1.0                                       # two plain slides with no design classes are alike
    if not a or not b:
        return 0.0
    return len(a & b) / float(len(a | b))


# ---------------------------------------------------------------- 1 FIND

def sweep(course, find, modules, floor=None, like=None, kind=None, words=None, workers=1):
    mods = module_dirs(course)
    chosen = parse_modules(modules, mods)
    if not chosen:
        print("Stopped - no built modules found in %s" % os.path.join(course, "modules"))
        return 2
    decks = {m: deck_file(mods[m]) for m in chosen}
    decks = {m: d for m, d in decks.items() if d}
    rules = RULES["sweeps"].get(find)
    if rules is None:
        print("Stopped - I can look for: %s" % ", ".join(k for k in RULES["sweeps"]))
        return 2
    found = []
    if rules.get("measured"):
        import measure_slides as ms
        try:
            res = ms.measure(list(decks.values()), workers=workers,
                             text_floor=floor or RULES["sweeps"]["text"]["floor_px"])
        except RuntimeError as e:
            print("Stopped - %s." % e)
            return 2
        sp, tx, ov = RULES["sweeps"]["space"], RULES["sweeps"]["text"], RULES["sweeps"]["overflow"]
        fl = floor or tx["floor_px"]
        for m, d in decks.items():
            r = res.get(d, {})
            if r.get("error") or r.get("errors"):
                found.append({"module": m, "slide": "", "title": "", "problem": "could not be measured: %s"
                              % (r.get("error") or r["errors"][0])[:200], "kind": "error"})
                continue
            for s in r.get("slides", []):
                for k, v in (("ink", None), ("empty_bottom", None), ("min_text", None), ("overflow", 0), ("small_text", 0),
                             ("title", ""), ("kind", ""), ("id", ""), ("n", 0)):
                    s.setdefault(k, v)
                base = {"module": m, "slide": s["id"], "n": s["n"], "title": s["title"], "slide_kind": s["kind"],
                        "ink": s["ink"], "empty_bottom": s["empty_bottom"], "min_text": s["min_text"], "overflow": s["overflow"]}
                sparse = s["kind"] in sp["sparse_kinds"]
                if find in ("space", "layout") and ((s["ink"] or 0) < sp["ink_floor"] or (s["empty_bottom"] or 0) > sp["empty_bottom_max"]):
                    found.append(dict(base, kind="space", sparse_by_design=sparse, problem="%d%% of the slide carries content, %d%% is empty below it"
                                      % (round(100 * (s["ink"] or 0)), round(100 * (s["empty_bottom"] or 0)))))
                if find in ("text", "layout") and s["min_text"] is not None and s["min_text"] < fl:
                    found.append(dict(base, kind="text", problem="smallest text %s px (\"%s\") - %d run(s) under %g px"
                                      % (s["min_text"], s.get("min_text_sample", ""), s["small_text"], fl)))
                if find in ("overflow", "layout") and s["overflow"] > ov["tolerance_px"]:
                    found.append(dict(base, kind="overflow", problem="content runs %d px off the slide" % s["overflow"]))
    elif find == "last-slide":
        ref = None
        if like:
            rd = deck_file(mods[int(like)]) if int(like) in mods else None
            ref = read_slides(rd)[-1] if rd and read_slides(rd) else None
        for m, d in decks.items():
            sl = read_slides(d)
            if not sl:
                continue
            last = sl[-1]
            sim = likeness(last["classes"], ref["classes"]) if ref else None
            end = is_end_slide(last)
            same = sim is not None and sim >= rules["same_design_at"]
            problem = ("no end slide - the last slide is \"%s\" (%s)" % (last["title"], last["kind"] or "no kind")) if not end else \
                      ("same design as module %s" % like if same else
                       ("a different design from module %s (%d%% alike)" % (like, round(100 * sim)) if ref else "the end slide"))
            found.append({"module": m, "slide": last["id"], "n": last["n"], "title": last["title"], "slide_kind": last["kind"],
                          "kind": "last-slide", "ok": bool(end and (same or not ref)), "problem": problem})
    elif find == "kind":
        if not kind:
            print("Stopped - say which kind: --kind Task (or Check, Hand-off, Theory ...)")
            return 2
        for m, d in decks.items():
            for s in read_slides(d):
                if s["kind"].lower() == kind.lower():
                    found.append({"module": m, "slide": s["id"], "n": s["n"], "title": s["title"], "slide_kind": s["kind"],
                                  "kind": "kind", "problem": "a %s slide" % s["kind"]})
    elif find == "words":
        if not words:
            print("Stopped - say what to look for: --words \"...\"")
            return 2
        w = words.lower()
        for m, d in decks.items():
            for s in read_slides(d):
                for where, txt in (("on the slide", s["text"]), ("in the instructor notes", s["cue"]), ("in the title", s["title"])):
                    i = (txt or "").lower().find(w)
                    if i >= 0:
                        found.append({"module": m, "slide": s["id"], "n": s["n"], "title": s["title"], "kind": "words",
                                      "problem": "%s: \"...%s...\"" % (where, txt[max(0, i - 40):i + len(w) + 40])})
    return report_sweep(course, find, chosen, found)


def report_sweep(course, find, chosen, found):
    real = [f for f in found if not f.get("ok") and not f.get("sparse_by_design")]
    sparse = [f for f in found if f.get("sparse_by_design")]
    ok = [f for f in found if f.get("ok")]
    print("Looked at %d module(s) for: %s.\n" % (len(chosen), RULES["sweeps"][find]["what"]))
    n = 0
    for group, head in ((real, "Found"), (sparse, "Sparer by design (task-start, check, opener, end) - listed so you can decide")):
        if not group:
            continue
        print("%s - %d place(s):" % (head, len(group)))
        for f in group:
            n += 1
            f["no"] = n
            print("  %2d. Module %d, slide %s%s \"%s\" - %s" % (n, f["module"], f.get("n", ""), (" (%s)" % f["slide"]) if f["slide"] else "",
                                                            (f["title"] or "")[:60], f["problem"]))
        print()
    if ok:
        print("Already right in module(s): %s\n" % ", ".join(str(f["module"]) for f in ok))
    if not real and not sparse:
        print("Nothing found.\n")
    out = cs.archive_name(fix_dir(course), "sweep_%s" % find, ".json")
    with io.open(out, "w", encoding="utf-8") as fh:
        json.dump({"find": find, "modules": chosen, "made": datetime.now().isoformat(timespec="seconds"), "found": found},
                  fh, ensure_ascii=False, indent=1)
    io.open(os.path.join(fix_dir(course), "last_sweep.txt"), "w", encoding="utf-8").write(out)
    print("Show this list to the operator once; fix what they say yes to (all, or \"all except 4 and 9\").")
    return 0


# ---------------------------------------------------------------- 2 ONE YES (words)

def batch_path(course):
    return os.path.join(fix_dir(course), "batch.json")


def cmd_propose(course, changes_file):
    mods = module_dirs(course)
    by_mod = {}
    for c in cs.load(changes_file):
        if "module" not in c:
            print("Stopped - every change needs its \"module\".")
            return 2
        by_mod.setdefault(int(c["module"]), []).append(c)
    lines, written, ready = [], [], []
    for m, chs in sorted(by_mod.items()):                 # everything is checked before anything is written
        p = cs.paths(course, m)
        if not os.path.isfile(p["script"]):
            print("Stopped - module %d has no content script: %s" % (m, p["script"]))
            return 2
        if os.path.isfile(p["pending"]):
            print("Stopped - module %d already has understood changes waiting (from the Word file or an earlier list):\n"
                  "    %s\n  Apply them after the operator confirms (content_script.py apply), or discard them, first."
                  % (m, p["pending"]))
            return 2
        script = cs.load(p["script"])
        changes = []
        for c in chs:
            f = c["field"]
            sid, f = f.split(".", 1) if "." in f and not f.startswith("opt.") else (c.get("screen"), f)
            s = cs.screen_of(script, sid)
            if s is None:
                print("Stopped - module %d has no screen %r." % (m, sid))
                return 2
            changes.append({"screen": sid, "field": f, "old": cs.get_field(s, f, script.get("operator_language", "en")) or "", "new": c["new"]})
        ready.append((m, p, script, changes))
    for m, p, script, changes in ready:
        cs.save(p["pending"], {"_what": "Understood, NOT applied (fix.py batch). Show the list; apply only after the operator confirms.",
                               "source": "chat", "made": datetime.now().isoformat(timespec="seconds"),
                               "base_hash": cs.content_hash(script), "changes": changes, "notes": []})
        written.append(m)
        lines += ["  Module %d - %s" % (m, cs.describe(script, ch)) for ch in changes]
        if m not in mods:
            lines.append("  Module %d - (not built yet: only its script changes)" % m)
    cs.save(batch_path(course), {"modules": written, "made": datetime.now().isoformat(timespec="seconds")})
    print("What I understood - %d change(s) in %d module(s), nothing changed yet:\n" % (len(lines), len(written)))
    print("\n".join(lines))
    print("\nOne yes from the operator covers all of it:  fix.py apply <course> --confirmed")
    return 0


# ---------------------------------------------------------------- 3 CHANGE

class Spans(HTMLParser):
    """Where, in the file, each element of one screen sits - so its words can be replaced in place."""
    VOID = Slides.VOID

    def __init__(self, text, sid):
        super().__init__(convert_charrefs=True)
        # line starts from "\n" only - HTMLParser.getpos() counts nothing else, and splitlines() also splits on
        # U+2028, a lone CR, form feed ... which shifted every offset after one and wrote into the wrong place
        self.sid, self.stack = sid, []
        self.lines = [0] + [i + 1 for i, ch in enumerate(text) if ch == "\n"]
        self.fields, self.screen_tag = [], None

    def off(self):
        ln, col = self.getpos()
        return self.lines[ln - 1] + col

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        start = self.off()
        end = start + len(self.get_starttag_text())
        inside = any(x[1].get("data-script") == self.sid for x in self.stack) or a.get("data-script") == self.sid
        if a.get("data-script") == self.sid and self.screen_tag is None:
            self.screen_tag = (start, end)
        if tag not in self.VOID:
            self.stack.append((tag, a, end, inside))

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                t, a, inner_start, inside = self.stack[i]
                if inside and "data-script-field" in a:
                    self.fields.append((a["data-script-field"], inner_start, self.off()))
                del self.stack[i:]
                return


def put_words(mdir, sid, field, new):
    """The approved words into the built slide. Returns '' when done, or why it was left for hand work."""
    files = [f for f in glob.glob(os.path.join(mdir, "**", "*.html"), recursive=True)]
    for f in files:
        text = io.open(f, encoding="utf-8", newline="").read()
        if ('data-script="%s"' % sid) not in text and ("data-script='%s'" % sid) not in text:
            continue
        sp = Spans(text, sid)
        sp.feed(text)
        sp.close()
        edits = []
        if field == "notes":
            if not sp.screen_tag:
                return "the slide's opening tag was not found"
            a, b = sp.screen_tag
            tag = text[a:b]
            val = html.escape(" ".join(x[2:] if x.startswith(("- ", "* ")) else x for x in cs.note_lines(new)), quote=True)
            if re.search(r"\sdata-cue\s*=", tag):
                tag = re.sub(r"(\sdata-cue\s*=\s*)(\"[^\"]*\"|'[^']*')", lambda m: m.group(1) + '"%s"' % val, tag, count=1)
            else:
                tag = tag[:-1].rstrip("/") + ' data-cue="%s">' % val
            edits.append((a, b, tag))
        elif field in ("title", "text"):
            spans = sorted((s for s in sp.fields if s[0] == field), key=lambda s: s[1])
            want = [x.strip() for x in new.split("\n") if x.strip()] if field == "text" else [new.strip()]
            if field == "title" and sp.screen_tag:          # the header band and the classroom read data-title (L45)
                a, b = sp.screen_tag
                tag = text[a:b]
                if re.search(r"\sdata-title\s*=", tag):
                    edits.append((a, b, re.sub(r"(\sdata-title\s*=\s*)(\"[^\"]*\"|'[^']*')",
                                               lambda m: m.group(1) + '"%s"' % html.escape(new.strip(), quote=True), tag, count=1)))
                if not spans:
                    want = []
            if len(spans) != len(want):
                return "the slide has %d %s line(s) and the new words have %d - the slide needs re-composing by hand" % (
                    len(spans), field, len(want))
            for (_, a, b), line in zip(spans, want):
                inner = text[a:b]
                if norm(re.sub(r"<[^>]+>", "", html.unescape(inner))) == norm(line):
                    continue
                if "<" in inner:
                    return "a line carries formatting inside it (bold, a term link ...) - keep it by editing that line by hand"
                edits.append((a, b, html.escape(line, quote=False)))
        elif field == "minutes":
            return ""                                    # minutes live in the script and the run script, not on the slide face
        elif field in ("question", "feedback", "answer") or field.startswith("opt."):
            return "a task's %s is on the trainee page, where the answers are keyed (L45) - change it there by hand" % field
        else:
            return "the %s is part of the slide's design, not plain words - change it by hand" % field
        for a, b, rep in sorted(edits, reverse=True):
            text = text[:a] + rep + text[b:]
        if edits:
            io.open(f, "w", encoding="utf-8", newline="").write(text)
        return ""
    return "no built page carries this slide (data-script=\"%s\")" % sid


def has_generator(course, m):
    for d in (workspace.claude_path(course, "build", cs.mid(m)), os.path.join(course, "build", cs.mid(m))):
        if os.path.isdir(os.path.join(d, "gen")) or glob.glob(os.path.join(d, "build_*.py")):
            return d
    return None


def cmd_apply(course, confirmed):
    if not confirmed:
        print("Stopped - apply needs --confirmed, and that is only given after the operator read the list and said yes.")
        return 2
    if not os.path.isfile(batch_path(course)):
        print("Nothing to apply - no list is waiting (fix.py propose makes one).")
        return 2
    batch, mods = cs.load(batch_path(course)), module_dirs(course)
    hand, done, gens = [], 0, []
    for m in batch["modules"]:
        p = cs.paths(course, m)
        if not os.path.isfile(p["pending"]):
            continue
        changes = cs.load(p["pending"])["changes"]
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = cs.cmd_apply(course, m, True)
        if rc:
            print("Module %d: not applied - %s" % (m, buf.getvalue().strip().splitlines()[0] if buf.getvalue().strip() else rc))
            continue
        script = cs.load(p["script"])
        for ch in changes:
            if m not in mods:
                continue
            why = put_words(mods[m], ch["screen"], ch["field"], ch["new"])
            if why:
                hand.append("Module %d, %s: %s" % (m, cs.place(script, ch["screen"]), why))
            else:
                done += 1
        g = has_generator(course, m)
        if g:
            gens.append("Module %d is rebuilt by its own generator (%s) - put the same words there too, or the next rebuild "
                        "brings the old ones back" % (m, g))
    batch["applied"] = datetime.now().isoformat(timespec="seconds")
    cs.save(batch_path(course), batch)
    print("Applied in %d module(s): the approved words, the review pages and Word files, FEEDBACK_LOG - and %d place(s) "
          "on the built slides." % (len(batch["modules"]), done))
    for x in hand:
        print("  hand work: " + x)
    for x in gens:
        print("  note: " + x)
    print("\nThe changed modules are drafts again. One approval for all of them:  fix.py approve <course> --by \"<name>\"")
    return 0


def cmd_approve(course, by, despite=False):
    if not os.path.isfile(batch_path(course)):
        print("Nothing to approve - no batch is waiting.")
        return 2
    batch = cs.load(batch_path(course))
    bad = []
    for m in batch["modules"]:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = cs.cmd_approve(course, m, by, despite)
        if rc:
            bad.append("Module %d: %s" % (m, " ".join(buf.getvalue().split())[:400]))
    if bad:
        print("Not every module could be approved:\n" + "\n".join("  " + x for x in bad))
        return 1
    os.replace(batch_path(course), cs.archive_name(fix_dir(course), "batch_done", ".json"))
    print("Approved by %s: module(s) %s - one approval for the whole batch." % (by, ", ".join(str(m) for m in batch["modules"])))
    print("Now the one check:  fix.py check <course> --kind words --modules %s" % ",".join(str(m) for m in batch["modules"]))
    return 0


def cmd_sync_shared(course, confirmed, source=None):
    sh = RULES["shared"]
    src = source or workspace.claude_path(course, sh["source"])
    if not os.path.isdir(src):
        print("There is no shared folder yet (%s). Put the one copy of a part every module uses there first." % src)
        return 2
    mapping = {}
    mf = os.path.join(src, "shared.json")
    if os.path.isfile(mf):
        mapping = cs.load(mf)
    files = [f for f in sorted(os.listdir(src)) if os.path.isfile(os.path.join(src, f)) and f != "shared.json" and not f.endswith(".md")]
    mods = module_dirs(course)
    plan = []
    for m, d in sorted(mods.items()):
        for f in files:
            dst = os.path.join(d, mapping.get(f, os.path.join(sh["default_target"], f)))
            if not os.path.isfile(dst) or not filecmp.cmp(os.path.join(src, f), dst, shallow=False):
                plan.append((m, f, dst, os.path.isfile(dst)))
    if not plan:
        print("Every module already has the current copy of the %d shared file(s)." % len(files))
        return 0
    for m, f, dst, exists in plan:
        print("  Module %d: %s %s" % (m, f, "is replaced" if exists else "is added"))
    if not confirmed:
        print("\n%d file(s) in %d module(s) would change. Run again with --confirmed to copy them." % (len(plan), len({p[0] for p in plan})))
        return 0
    for m, f, dst, _ in plan:
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(os.path.join(src, f), dst)
    print("\nCopied. The one check:  fix.py check <course> --kind package   (and --kind layout if the part changes how slides look)")
    return 0


# ---------------------------------------------------------------- 4 ONE CHECK

def run(args):
    r = subprocess.run([sys.executable] + args, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.returncode, (r.stdout + r.stderr).strip()


def cmd_check(course, kind, modules, slides=None, floor=None):
    mods = module_dirs(course)
    if modules is None and os.path.isfile(batch_path(course)):
        modules = ",".join(str(m) for m in cs.load(batch_path(course))["modules"])
    chosen = parse_modules(modules, mods)
    fails, lines = 0, []
    if kind == "words":
        for m in chosen:
            if os.path.isfile(cs.paths(course, m)["script"]):
                rc, out = run([os.path.join(HERE, "check_script_match.py"), course, "--module", str(m)])
                fails += rc != 0
                lines.append("Module %d, words: %s" % (m, out.splitlines()[0] if rc == 0 else out))
            rc, out = run([os.path.join(HERE, "check_slide_text.py"), mods[m], "--strict"])
            fails += rc != 0
            lines.append("Module %d, what the slides may say: %s" % (m, "all right" if rc == 0 else out[-1200:]))
    elif kind == "package":
        rc, out = run([os.path.join(HERE, "check_course_package.py"), course])
        fails += rc != 0
        lines.append(out if rc else "The course folder follows the classroom system's rules.")
    elif kind == "layout":
        import measure_slides as ms
        fl = floor or RULES["sweeps"]["text"]["floor_px"]
        tol = RULES["sweeps"]["overflow"]["tolerance_px"]
        want = set(x.strip() for x in slides.split(",")) if slides else None
        before = {}
        lf = os.path.join(fix_dir(course), "last_sweep.txt")
        if os.path.isfile(lf) and os.path.isfile(io.open(lf, encoding="utf-8").read().strip()):
            for f in cs.load(io.open(lf, encoding="utf-8").read().strip())["found"]:
                if f.get("ink") is not None:
                    before[(f["module"], f["slide"])] = f
        decks = {m: deck_file(mods[m]) for m in chosen if deck_file(mods[m])}
        try:
            res = ms.measure(list(decks.values()), text_floor=fl)
        except RuntimeError as e:
            print("Stopped - %s." % e)
            return 2
        for m, d in decks.items():
            r = res.get(d, {})
            if r.get("error") or r.get("errors"):
                fails += 1
                lines.append("Module %d: could not be measured - %s" % (m, (r.get("error") or r["errors"][0])[:200]))
                continue
            bad = []
            for s in r["slides"]:
                if want and s["id"] not in want:
                    continue
                if s["overflow"] > tol:
                    bad.append("slide %d (%s) runs %d px off the screen" % (s["n"], s["id"], s["overflow"]))
                if s["min_text"] is not None and s["min_text"] < fl and (not want or s["id"] in want):
                    bad.append("slide %d (%s) has text at %s px (\"%s\")" % (s["n"], s["id"], s["min_text"], s.get("min_text_sample", "")))
                b = before.get((m, s["id"]))
                if b:
                    lines.append("Module %d, slide %d (%s): content %d%% -> %d%%, empty below %d%% -> %d%%" % (
                        m, s["n"], s["id"], round(100 * (b["ink"] or 0)), round(100 * (s["ink"] or 0)),
                        round(100 * (b["empty_bottom"] or 0)), round(100 * (s["empty_bottom"] or 0))))
            fails += len(bad)
            lines.append("Module %d, layout at %dx%d: %s" % (m, r["viewport"][0], r["viewport"][1],
                                                          "nothing off the screen, no text under %g px" % fl if not bad else "; ".join(bad)))
    else:
        print("Stopped - the check is one of: words, layout, package (knowledge/fix-rules.json -> checks).")
        return 2
    print("\n".join(lines))
    print("\n%s" % ("The check passed - the fix is done." if not fails else "%d thing(s) to fix before it is done." % fails))
    return 1 if fails else 0


# ---------------------------------------------------------------- the course's house decisions

STANDARDS_HEAD = """# Course standards - what the operator decided once for every module

Every module is built to these, and every fix keeps them. Newest last. Written by `fix.py standard`;
the operator's own words in quotes. A standard is never silently dropped - the operator removes it.

"""


def cmd_standard(course, add=None, said=None):
    p = workspace.claude_path(course, RULES["standards"]["file"])
    text = io.open(p, encoding="utf-8").read() if os.path.isfile(p) else STANDARDS_HEAD
    if not add:
        print(text if os.path.isfile(p) else "This course has no standards yet.")
        return 0
    n = max([int(x) for x in re.findall(r"^S(\d+) ", text, re.M)] or [0]) + 1     # never reuse a removed number
    text = text.rstrip("\n") + "\n\nS%d %s (%s%s)\n" % (n, add.strip(), date.today().isoformat(),
                                                       (', operator: "%s"' % said.strip()) if said else "")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    io.open(p, "w", encoding="utf-8", newline="\n").write(text)
    print("Standard S%d written to %s - new modules are built to it, fixes keep it." % (n, p))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("sweep")
    s.add_argument("course"); s.add_argument("--find", required=True); s.add_argument("--modules")
    s.add_argument("--floor", type=float); s.add_argument("--like"); s.add_argument("--kind"); s.add_argument("--words")
    s.add_argument("--workers", type=int, default=1)
    s = sub.add_parser("propose"); s.add_argument("course"); s.add_argument("--changes", required=True)
    s = sub.add_parser("apply"); s.add_argument("course"); s.add_argument("--confirmed", action="store_true")
    s = sub.add_parser("approve"); s.add_argument("course"); s.add_argument("--by", required=True)
    s.add_argument("--despite-findings", action="store_true")
    s = sub.add_parser("check"); s.add_argument("course"); s.add_argument("--kind", required=True)
    s.add_argument("--modules"); s.add_argument("--slides"); s.add_argument("--floor", type=float)
    s = sub.add_parser("standard"); s.add_argument("course"); s.add_argument("--add"); s.add_argument("--said")
    s = sub.add_parser("sync-shared"); s.add_argument("course"); s.add_argument("--confirmed", action="store_true")
    s.add_argument("--from", dest="source")
    a = ap.parse_args(argv)
    a.course = workspace.work_folder(a.course, create=False)
    if a.cmd == "sweep":
        return sweep(a.course, a.find, a.modules, a.floor, a.like, a.kind, a.words, a.workers)
    if a.cmd == "propose":
        return cmd_propose(a.course, a.changes)
    if a.cmd == "apply":
        return cmd_apply(a.course, a.confirmed)
    if a.cmd == "approve":
        return cmd_approve(a.course, a.by, a.despite_findings)
    if a.cmd == "check":
        return cmd_check(a.course, a.kind, a.modules, a.slides, a.floor)
    if a.cmd == "standard":
        return cmd_standard(a.course, a.add, a.said)
    return cmd_sync_shared(a.course, a.confirmed, a.source)


if __name__ == "__main__":
    sys.exit(main())
