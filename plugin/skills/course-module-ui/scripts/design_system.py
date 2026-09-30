#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Copy the NOVIKONTAS design system into a module, or prove a module's copies are identical.

    design_system.py install <module folder> [--start-deck] [--update]
    design_system.py check   <module folder> [--json]

WHY THIS EXISTS
Establishing a module's look used to mean the model READ about 82 KB of style files -
roughly 20,000 tokens - that it only needed to COPY. A copy is either identical to the
canonical file or it is the start of a second visual dialect; there is nothing in between
worth reading for. So a script copies them byte for byte, a check proves they are still
identical, and the model reads references/vocabulary.md - the names and when to use each -
instead of the files. (Phase 5 step 11b, 2.11.1.)

WHAT IT COPIES
Every file listed in knowledge/design-system.json, into <module>/assets/. With
--start-deck it also writes module.html from templates/gb_shell.html - but only when the
module has no module.html yet; the deck is the module's own work and is never overwritten.

WHAT IT REFUSES
  * to overwrite a file in assets/ that differs from the canonical one, unless --update is
    given - a module that already exists may be a delivered one, and repainting a delivered
    deck is the owner's decision, not this script's;
  * to touch anything inside the Android project (L21) - that is a publish target.

THE CHECK
For every canonical file: OK (identical), MISSING, OUTDATED (identical to what was installed,
but the factory's own file has changed since - re-install with --update), or CHANGED (edited
by hand in the module - a second dialect). Exit 0 only when every file is OK.
New modules only: a delivered GAS BASIC or Electrical Technician module carries known drift
and is reported by course-module-ui, never repainted by this.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import shutil
import sys
from datetime import date

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)                       # .../skills/course-module-ui
SKILLS = os.path.dirname(SKILL)                     # .../skills
PLUGIN = os.path.dirname(SKILLS)                    # .../plugin
LIST = os.path.join(SKILL, "knowledge", "design-system.json")


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(65536), b""):
            h.update(block)
    return h.hexdigest()


def plugin_version():
    try:
        with io.open(os.path.join(PLUGIN, ".claude-plugin", "plugin.json"), encoding="utf-8") as f:
            return json.load(f).get("version", "unknown")
    except (OSError, ValueError):
        return "unknown"


def load_list():
    with io.open(LIST, encoding="utf-8") as f:
        spec = json.load(f)
    for item in spec["files"]:
        item["src"] = os.path.normpath(os.path.join(SKILLS, item["from"]))
    spec["starter_deck"]["src"] = os.path.normpath(os.path.join(SKILLS, spec["starter_deck"]["from"]))
    return spec


def inside_android_project(path):
    p = os.path.abspath(path).replace("\\", "/").lower()
    return "/androidstudioprojects/" in p


def read_record(module, spec):
    p = os.path.join(module, spec["record"])
    try:
        with io.open(p, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def install(module, start_deck=False, update=False):
    spec = load_list()
    if inside_android_project(module):
        print("Stopped - nothing was copied.\n\n"
              "  The folder is inside the NOVIKONTAS training app's project:\n    %s\n"
              "  The app is where a finished, approved course is published to, never where a\n"
              "  course is built. Point this at the course's own folder instead - for example\n"
              "  C:\\courses\\<course>\\modules\\m1 - and it will set the module up there." % module)
        return 2
    if not os.path.isdir(module):
        print("Stopped - that folder does not exist:\n    %s\n"
              "  Check the spelling of the path, or make the module folder first." % module)
        return 2

    dest = os.path.join(module, spec["destination"])
    os.makedirs(dest, exist_ok=True)
    blocked, copied, same = [], [], []
    for item in spec["files"]:
        target = os.path.join(dest, item["name"])
        if os.path.exists(target):
            if sha(target) == sha(item["src"]):
                same.append(item["name"])
                continue
            if not update:
                blocked.append(item["name"])
                continue
        shutil.copyfile(item["src"], target)
        copied.append(item["name"])

    if blocked:
        print("Stopped before changing anything that was already there.\n\n"
              "  These files in\n    %s\n  are different from the factory's own copies:\n" % dest)
        for n in blocked:
            print("    - %s" % n)
        print("\n  If this is a module that has already been delivered, leave it: repainting a\n"
              "  delivered module is the owner's decision. If it is new work and should simply\n"
              "  get the current factory files, run the same command again with --update.\n"
              "  Files that were missing or identical were still put in place (%d copied, %d\n"
              "  already identical)." % (len(copied), len(same)))

    deck_note = ""
    if start_deck:
        deck = os.path.join(module, spec["starter_deck"]["to"])
        if os.path.exists(deck):
            deck_note = "module.html was already there and was left exactly as it is."
        else:
            shutil.copyfile(spec["starter_deck"]["src"], deck)
            deck_note = "module.html was started from the factory's deck frame."

    record = {
        "_what": "Written by course-module-ui/scripts/design_system.py. Fingerprints of the "
                 "factory's style files as copied into assets/, so the check can tell a module "
                 "that fell behind the factory from one that was edited by hand. Internal - "
                 "never shipped to a tablet.",
        "plugin_version": plugin_version(),
        "installed": date.today().isoformat(),
        "files": {item["name"]: sha(os.path.join(dest, item["name"]))
                  for item in spec["files"] if os.path.exists(os.path.join(dest, item["name"]))},
    }
    rp = os.path.join(module, spec["record"])
    os.makedirs(os.path.dirname(rp), exist_ok=True)
    with io.open(rp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(record, f, indent=2)
        f.write("\n")

    if not blocked:
        print("The module's look is set up.\n\n"
              "  Folder:  %s\n"
              "  %d file(s) copied, %d already identical - %d in total, all identical to the\n"
              "  factory's own (version %s)." % (dest, len(copied), len(same), len(spec["files"]),
                                                record["plugin_version"]))
        if deck_note:
            print("  " + deck_note)
        print("\n  Do not edit these files in the module. Course-specific styling goes in the\n"
              "  module's own stylesheet, loaded after them. Which class to use for what is in\n"
              "  course-module-ui/references/vocabulary.md.")
    return 1 if blocked else 0


def check(module, as_json=False):
    spec = load_list()
    rec = read_record(module, spec).get("files", {})
    dest = os.path.join(module, spec["destination"])
    rows = []
    for item in spec["files"]:
        target = os.path.join(dest, item["name"])
        canon = sha(item["src"])
        if not os.path.exists(target):
            state = "MISSING"
        else:
            got = sha(target)
            if got == canon:
                state = "OK"
            elif rec.get(item["name"]) == got:
                state = "OUTDATED"
            else:
                state = "CHANGED"
        rows.append({"file": item["name"], "state": state, "path": target})

    bad = [r for r in rows if r["state"] != "OK"]
    if as_json:
        print(json.dumps({"module": module, "ok": not bad, "files": rows}, indent=2))
        return 1 if bad else 0

    if not bad:
        print("The module's style files are all identical to the factory's own.\n\n"
              "  Folder:  %s\n  %d of %d files checked, byte for byte." % (dest, len(rows), len(rows)))
        return 0

    print("Some of the module's style files are not the factory's own.\n\n  Folder:  %s\n" % dest)
    what = {
        "MISSING":  "is not there - the pages that load it will look unstyled or stop working",
        "OUTDATED": "is the factory's older version - the factory has improved it since",
        "CHANGED":  "was edited inside the module - that starts a second look for one course",
    }
    for r in bad:
        print("    - %-20s %s" % (r["file"], what[r["state"]]))
    print("\n  How to see it: open the module's module.html by double-clicking it; a missing or\n"
          "  changed style file shows as screens that look different from Module 1.\n"
          "  What to do: tell me to fix it and I will - that is\n"
          "      design_system.py install <module folder> --update\n"
          "  which puts the factory's files back. Anything the module genuinely needs that the\n"
          "  factory's files do not have belongs in the module's own stylesheet instead.\n"
          "  How you know it worked: this check then says all files are identical.")
    return 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("install", help="copy the design system into a module's assets/")
    a.add_argument("module")
    a.add_argument("--start-deck", action="store_true",
                   help="also write module.html from the deck frame, if the module has none")
    a.add_argument("--update", action="store_true",
                   help="overwrite files that differ from the factory's (new work only)")
    c = sub.add_parser("check", help="prove the module's copies are identical to the factory's")
    c.add_argument("module")
    c.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    if ns.cmd == "install":
        return install(ns.module, ns.start_deck, ns.update)
    return check(ns.module, ns.json)


if __name__ == "__main__":
    sys.exit(main())
