#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Nano Banana pictures for a module: where they go, what the person described, and what they cost - L47.

    picture_briefs.py list <course> --module 1
    picture_briefs.py save <course> --module 1 --slide s03 --brief <brief.json>
    picture_briefs.py done <course> --module 1 --slide s03 --file <picture> --approved "<the person's words>"

WHY THIS EXISTS
Every generated picture is billed to the NOVIKONTAS Google account - about EUR 0.10 each, a video clip much more
(owner, 2026-10-14). Four developers redoing pictures 10-15 times each spend the budget, and most redos come from
a vague first description. So the factory never generates on its own: it finds the places first, asks the person
to describe each picture (the questions are knowledge/media-and-tasks.json -> generation_brief), shows the prompt,
and generates only after their yes - the nano-banana tools refuse to run without the person's words.

  list   every screen of the approved content script whose picture the generator makes (visual_kind made_by
         nano_banana), and any other place a description was saved for: the slide, its title, what the script says
         the picture shows, and where it stands - to describe / described / made N time(s), about EUR x. For a place
         still to describe it prints the questions, each with the script's own words as the starting suggestion.
  save   keeps the person's answers and the prompt written from them: brief.json = {"answers": {...}, "prompt": "..."}
  done   records one picture made: the file, the person's words of approval, the date

Everything is kept in working_claude/picture_briefs/M01.json, so a redo next week does not ask everything again.
Exit 0, or 2 on bad input.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import content_script as cs  # noqa: E402
import workspace  # noqa: E402

GB = cs.MEDIA["generation_brief"]


def store_path(course, module):
    return os.path.join(workspace.claude_path(course, "picture_briefs"), "%s.json" % cs.mid(module))


def load_store(course, module):
    p = store_path(course, module)
    return json.load(io.open(p, encoding="utf-8")) if os.path.isfile(p) else {}


def save_store(course, module, data):
    p = store_path(course, module)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    io.open(p, "w", encoding="utf-8").write(json.dumps(data, ensure_ascii=False, indent=1))
    return p


def generated(s):
    return cs.MEDIA["visual_kinds"].get(cs.parse_kind(s.get("visual_kind", "")), {}).get("made_by") == "nano_banana"


def cmd_list(course, module, script, store):
    screens = {s["id"]: s for s in script.get("screens", [])}
    places = [s["id"] for s in script.get("screens", []) if generated(s)]
    places += [sid for sid in store if sid not in places and sid in screens]
    e = GB["eur_per_image"]
    made = sum(len(store.get(sid, {}).get("made", [])) for sid in places)
    print("Module %s: %d place(s) for a generated picture - %d picture(s) made so far, about EUR %.2f (EUR %.2f each)."
          % (module, len(places), made, made * e, e))
    if not places:
        print("  Nothing to generate: the approved script plans no AI illustration or AI video.")
        return 0
    for sid in places:
        s, b = screens[sid], store.get(sid, {})
        n = len(b.get("made", []))
        state = ("made %d time(s), about EUR %.2f" % (n, n * e)) if n else ("described - show the prompt and ask for a yes" if b.get("prompt") else "to describe")
        print("\n- %s (%s) \"%s\" - %s" % (cs.place(script, sid), sid, s.get("title") or s.get("question", ""), state))
        print("    the script says it shows: %s" % (s.get("visual") or "(nothing yet)"))
        if b.get("prompt"):
            print("    agreed prompt: %s" % b["prompt"])
        elif not n:
            print("    ask the person, one place at a time - each picture costs about EUR %.2f, so the first try should be right:" % e)
            for i, q in enumerate(GB["questions"], 1):
                print("      %d. %s" % (i, q["en"]))
            print("    starting suggestion from the script: %s" % (s.get("visual") or s.get("title", "")))
    print("\nNothing is generated until the person has described the picture, seen the prompt and said yes (L47).")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("list", "save", "done"):
        s = sub.add_parser(name)
        s.add_argument("course")
        s.add_argument("--module", required=True)
        if name != "list":
            s.add_argument("--slide", required=True)
        if name == "save":
            s.add_argument("--brief", required=True)
        if name == "done":
            s.add_argument("--file", required=True)
            s.add_argument("--approved", required=True)
    a = ap.parse_args(argv)
    course = workspace.work_folder(a.course, create=False)
    p = cs.paths(course, a.module)["script"]
    if not os.path.isfile(p):
        print("Stopped - there is no content script for module %s:\n    %s" % (a.module, p))
        return 2
    script = cs.load(p)
    store = load_store(course, a.module)
    if a.cmd == "list":
        return cmd_list(course, a.module, script, store)
    if a.slide not in {s["id"] for s in script.get("screens", [])}:
        print("Stopped - module %s has no screen %s" % (a.module, a.slide))
        return 2
    b = store.setdefault(a.slide, {})
    if a.cmd == "save":
        brief = json.load(io.open(a.brief, encoding="utf-8"))
        if not (brief.get("prompt") or "").strip() or not isinstance(brief.get("answers"), dict):
            print("Stopped - a brief is {\"answers\": {...the person's answers...}, \"prompt\": \"...\"}")
            return 2
        b.update({"answers": brief["answers"], "prompt": brief["prompt"].strip(), "saved": time.strftime("%Y-%m-%d")})
        print("Saved the description of %s (%s) - next: show the prompt and ask \"Generate this one picture (about EUR %.2f)?\"\n    %s"
              % (cs.place(script, a.slide), a.slide, GB["eur_per_image"], save_store(course, a.module, store)))
        return 0
    if len((a.approved or "").strip()) < 2:
        print("Stopped - the person's own words of approval are needed (--approved)")
        return 2
    b.setdefault("made", []).append({"file": a.file, "approved_by_user": a.approved.strip(), "when": time.strftime("%Y-%m-%d %H:%M")})
    save_store(course, a.module, store)
    n = sum(len(x.get("made", [])) for x in store.values())
    print("Recorded: %s (%s) - picture %d for module %s, about EUR %.2f so far." % (cs.place(script, a.slide), a.slide, n, a.module, n * GB["eur_per_image"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
