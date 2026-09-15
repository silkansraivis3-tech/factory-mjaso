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


HEAD = """# VISUAL HANDOFF — {module}

*Written {today} by the NOVIKONTAS Course Factory. The module is built; these are the
visuals it could not produce itself.*

**Nothing in this module is broken.** Every screen validates, every hour is allocated and
every task works. What is missing is {n} image(s), listed below with the exact place each
one goes.

---

## How to use this file

**If you can generate images:** read the PROMPT below, produce the assets, save each one at
the path given, paste the mount line into the screen named, write the provenance entry, then
run the verification command at the end.

**If you are the owner:** open a chat with a model that can generate images — {model} — and
paste everything between the two `=====` lines. It contains the full brief, so the model
needs nothing else from you and no access to this repository beyond the file paths.

**Do not accept a plausible invention of safety-critical equipment.** If a brief says a
trainee must recognise this thing in real life, a generated image teaches false recognition.
Find a real photograph or leave the screen with its declared exemption.

---

=====  PASTE FROM HERE  =====

## PROMPT

You are finishing the visual layer of an accredited maritime training module. The module is
complete except for the images described below. For each one:

1. **Search before you generate.** Look for a real photograph or a published figure first —
   the module's own `source_files/` and knowledge base, then the open internet under a
   licence we may use. A real photograph of the actual equipment beats a beautiful
   invention of it every time. Only generate when the search genuinely comes back empty.
2. **Never generate a technical schematic.** If the brief describes system relationships,
   flow, internal structure or a mechanism, author it as SVG instead. A diagram that must
   be accurate is drawn, not sampled.
3. **Obey the forbidden-inaccuracies list in every brief.** It names the errors a generator
   is likely to make with that subject, and it is the field that stops an image teaching
   something false.
4. **Save each file at the exact path given**, write the provenance entry beside it, and
   paste the mount line into the screen named. Nothing else in the module changes.

"""

TAIL = """
=====  PASTE UP TO HERE  =====

---

## When the assets are in place

```
python {skill}/scripts/check_assets.py <module_dir>
python {skill}/scripts/check_visuals.py <module_dir> --strict
python {skill}/scripts/check_visual_first.py <module_dir> --strict
```

Then remove any `data-novisual="no_honest_representation"` attribute from a screen that now
has its figure, and delete this file. A handoff left behind after it was acted on is the next
person's false alarm.

---

## Provenance — write one of these beside every file

A photograph takes `_photo_meta.json`, a drawing or schematic takes `_figure_meta.json`.
The schemas are in `{skill}/source/schemas/`. A generated image records `generated` as its
origin, the model that made it, and the brief it was made from — never a fabricated source.
**Nothing at `RIGHTS_REVIEW_REQUIRED` may ship.**
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
        parts.append("### The briefs\n")
        for slug, body in briefs:
            parts.append("\n#### %s\n\n%s\n\n"
                         "**Destination:** `assets/img/%s.<ext>` in the module folder.  \n"
                         "**Mount:** `<img src=\"assets/img/%s.<ext>\" alt=\"<describe the "
                         "whole figure>\">` in the screen the brief names.\n" %
                         (slug, body, slug, slug))

    if declared:
        parts.append("\n### Screens that declared they could not be illustrated\n\n"
                     "Each of these was searched at every level and came back empty. If you "
                     "can find or produce an honest representation, it belongs here — and the "
                     "`data-novisual` attribute comes off.\n\n")
        for rel, title, line in declared:
            slug = slugify(title)
            parts.append("- `%s:%d` — **%s**  \n  destination `assets/img/%s.<ext>`\n"
                         % (rel, line, title, slug))

    if markers:
        parts.append("\n### GENERATED_ASSET_REQUIRED left in the deck\n\n"
                     "These were noted during the build and never written up as a brief. "
                     "**A marker is not a brief** — anything here needs the missing fields "
                     "filled in before it can be acted on.\n\n")
        for rel, line, text in markers:
            parts.append("- `%s:%d` — %s\n" % (rel, line, text))

    parts.append(TAIL.format(skill="${CLAUDE_PLUGIN_ROOT}/skills/course-visuals"))

    out = os.path.join(a.module, a.out)
    io.open(out, "w", encoding="utf-8", newline="\n").write("".join(parts))
    print("%s\n  %d brief(s), %d declared gap(s), %d bare marker(s)."
          % (out, len(briefs), len(declared), len(markers)))
    if markers:
        print("\n  %d marker(s) have no brief. Write them up before handing this over -\n"
              "  a generator asked for 'a picture of a pump' produces exactly that."
              % len(markers))
    return 0


if __name__ == "__main__":
    sys.exit(main())
