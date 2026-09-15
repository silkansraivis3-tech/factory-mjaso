#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""The module is finished except for the pictures. Leave one file that finishes it.

    write_visual_handoff.py <module_dir> [--model fable] [--out VISUAL_HANDOFF.md]

WHY THIS EXISTS
A module that stops dead because one image cannot be produced wastes everything
else that was already right. The owner's instruction was: build the module as far
as it will go, then write ONE file containing a prompt another model can act on -
what to find, what to generate, and exactly where each file goes - so the module is
finished by whoever opens it next, without re-reading the module to work out what
was missing.

WHAT GOES IN
  * every brief in <module>/_visual_briefs/*.md, in full
  * every screen that declared data-novisual="no_honest_representation"
  * every GENERATED_ASSET_REQUIRED left in an HTML comment in the deck
  * for each: the destination path, the mount line, and the provenance entry to write
  * one paste-ready prompt at the top, addressed to the model that will do the work

THE AUTOMATIC ROUTE
This file is the fallback, not the plan. Where the environment allows a model
override, the factory spawns the work instead of writing a note:

    Agent(model="fable", prompt=<the PROMPT section of this file>)

and the run continues. Write the file anyway - it is the record of what was asked,
and it is what the owner reads if the subagent comes back empty.
"""
from __future__ import annotations

import argparse
import io
import os
import re
import sys
from datetime import date

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)

MARKER = re.compile(r"GENERATED_ASSET_REQUIRED[^\n]*", re.I)
NOVISUAL = re.compile(
    r'<section\b[^>]*data-novisual="no_honest_representation"[^>]*>', re.I)
ATTR = re.compile(r'(\w[\w-]*)="([^"]*)"')
SLUG = re.compile(r"[^a-z0-9]+")


def slugify(s):
    return SLUG.sub("_", s.strip().lower()).strip("_")[:48] or "asset"


def collect(module):
    """(briefs, declared, markers) - three ways an unbuilt visual leaves a trace."""
    briefs, declared, markers = [], [], []

    bdir = os.path.join(module, "_visual_briefs")
    if os.path.isdir(bdir):
        for f in sorted(os.listdir(bdir)):
            if f.lower().endswith(".md"):
                body = io.open(os.path.join(bdir, f), encoding="utf-8",
                               errors="replace").read().strip()
                briefs.append((os.path.splitext(f)[0], body))

    for dp, dn, fn in os.walk(module):
        dn[:] = [d for d in dn if d not in ("__pycache__", ".git", "node_modules",
                                            "_visual_briefs")]
        for f in fn:
            if os.path.splitext(f)[1].lower() not in (".html", ".htm"):
                continue
            p = os.path.join(dp, f)
            rel = os.path.relpath(p, module).replace("\\", "/")
            raw = io.open(p, encoding="utf-8", errors="replace").read()
            for m in NOVISUAL.finditer(raw):
                a = {k.lower(): v for k, v in ATTR.findall(m.group(0))}
                declared.append((rel, a.get("data-title", "") or "(untitled screen)",
                                 raw.count("\n", 0, m.start()) + 1))
            for m in MARKER.finditer(raw):
                line = raw.count("\n", 0, m.start()) + 1
                markers.append((rel, line, re.sub(r"\s+", " ", m.group(0))[:160]))
    return briefs, declared, markers


HEAD = """# PICTURES STILL NEEDED — {module}

*Written {today} by the NOVIKONTAS Course Factory.*

**Nothing in this module is broken.** Every screen works, the hours are right and every task
runs. {n} picture(s) could not be made here, and this page is everything somebody needs to
finish them — you do not have to look through the course to work out what is missing.

---

## What to do with this page

**If you want the factory to keep trying:** say so, and it will hand the work to a model that
can make pictures and carry on by itself. You do not have to do anything else.

**If you would rather do it yourself:** open a new chat with {model}, then copy everything
between the two lines of `=` signs below and paste it in. It contains the full description of
each picture, so {model} needs nothing else from you.

**One thing to watch.** If a description says a trainee has to recognise this equipment in
real life, do not accept a made-up picture of it. A convincing invention teaches somebody to
recognise the wrong thing. Find a real photograph, or leave that screen without a picture.

---

=====  COPY FROM HERE  =====

## PROMPT

You are finishing the pictures for an accredited maritime training module. Everything else in
the module is done. For each picture described below:

1. **Look before you make anything.** Search for a real photograph or a published drawing
   first — the course's own source files and knowledge base, then the open internet under a
   licence we may use. A real photograph of the actual equipment beats a beautiful invention
   of it every time. Only create one when the search genuinely comes back empty.
2. **Never invent a technical drawing.** If the description is about how a system connects,
   how something flows, what is inside a piece of equipment, or how a mechanism works, draw it
   properly as SVG instead. A drawing that has to be accurate is drawn, not guessed.
3. **Obey the "must NOT show" list in every description.** It names the mistakes a generator
   is likely to make with that subject, and it is what stops a picture teaching something
   false.
4. **Save each file exactly where the description says**, write the small record of where it
   came from beside it, and put the one line of code given into the screen named. Nothing else
   in the module changes.

"""
TAIL = """
=====  COPY UP TO HERE  =====

---

## When the pictures are in place

Ask the factory to check them, or run these three checks:

```
python {skill}/scripts/check_assets.py <module folder>
python {skill}/scripts/check_visuals.py <module folder> --strict
python {skill}/scripts/check_visual_first.py <module folder> --strict
```

A good result says nothing is missing and nothing is unclear about where a picture came from.
If it says anything else, copy the whole message and send it back.

Then two last things: on any screen that now has its picture, remove the
`data-novisual="no_honest_representation"` setting from the screen, and **delete this page**.
A page like this left behind after the work is done is the next person's false alarm.

---

## Where each picture came from — write this beside every file

A photograph takes a small file called `_photo_meta.json` beside it; a drawing takes
`_figure_meta.json`. The shape of both is in `{skill}/source/schemas/`. A picture that was
generated records that honestly — that it was generated, which model made it, and from which
description. Never write a source that is not real.

**If the rights to a picture are unclear, it does not ship.** Say so instead, and the screen
keeps its declared reason for having no picture.
"""


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("module", help="the module folder")
    ap.add_argument("--model", default="Fable 5",
                    help="the model the owner should paste this into (default: Fable 5)")
    ap.add_argument("--out", default="VISUAL_HANDOFF.md")
    a = ap.parse_args(argv)

    if not os.path.isdir(a.module):
        sys.stderr.write("not a folder: %s\n" % a.module)
        return 2

    briefs, declared, markers = collect(a.module)
    n = len(briefs) + len(declared) + len(markers)
    if not n:
        print("Nothing to hand off: no briefs, no declared gaps, no markers.\n"
              "That is the good outcome - the module's visuals are complete.")
        return 0

    name = os.path.basename(os.path.abspath(a.module))
    parts = [HEAD.format(module=name, today=date.today().isoformat(), n=n, model=a.model)]

    if briefs:
        parts.append("### The pictures, described one by one\n")
        for slug, body in briefs:
            parts.append("\n#### %s\n\n%s\n\n"
                         "**Save the finished file here:** `assets/img/%s.<jpg or png or "
                         "svg>`, inside the module folder.  \n"
                         "**Then put this one line into the screen named above:** "
                         "`<img src=\"assets/img/%s.<jpg or png or svg>\" alt=\"<one "
                         "sentence saying what the picture shows>\">`\n" %
                         (slug, body, slug, slug))

    if declared:
        parts.append("\n### Screens that say, in writing, that no honest picture was found\n\n"
                     "Somebody already searched everywhere for these and came back empty. If "
                     "you can find or make one that is genuinely true to the subject, it "
                     "belongs here — and then the screen's written reason for having no "
                     "picture is removed.\n\n")
        for rel, title, line in declared:
            slug = slugify(title)
            parts.append("- **%s** — in the file `%s`, line %d  \n"
                         "  save the picture as `assets/img/%s.<jpg or png or svg>`\n"
                         % (title, rel, line, slug))

    if markers:
        parts.append("\n### Notes left in the slides that were never written up properly\n\n"
                     "Somebody marked these during the build and never wrote the full "
                     "description. **A note is not a description** — each one needs finishing "
                     "before anybody can act on it, because a request for \"a picture of a "
                     "pump\" produces exactly that and nothing useful.\n\n")
        for rel, line, text in markers:
            parts.append("- in the file `%s`, line %d — %s\n" % (rel, line, text))

    parts.append(TAIL.format(skill="${CLAUDE_PLUGIN_ROOT}/skills/course-visuals"))

    out = os.path.join(a.module, a.out)
    io.open(out, "w", encoding="utf-8", newline="\n").write("".join(parts))
    print("%s\n  %d described, %d screen(s) waiting, %d unfinished note(s)."
          % (out, len(briefs), len(declared), len(markers)))
    if markers:
        print("\n  %d note(s) were never written up properly. Finish them before handing\n"
              "  this over - a request for 'a picture of a pump' produces exactly that."
              % len(markers))
    return 0


if __name__ == "__main__":
    sys.exit(main())
