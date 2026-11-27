#!/usr/bin/env python3
"""figure_plan.py - code chooses what a drawing slide gets, from the slide's own words, before the writer writes a figure:
one of the 2D forms (path, zones, steps, options, amounts), a named scene, a real photo, the task screen, or no figure.
The writer then fills in only what the chosen form asks for (SPEC.md). --init-build writes the starter it returns.

    python figure_plan.py <module script.json>        prints each slide's choice and why
"""
from __future__ import annotations

import io
import json
import re
import sys

WRITES = {
    "path": "things (2-7, each a picture from the library, a name of 3 words or less), the links between them, and for "
            "each step what travels (go), stops (fail), breaks (cut) or is marked (mark, tag)",
    "zones": "the zones (2-4) and the things in each (up to 3), whether walls stand, and for each step where something "
             "starts (bug) and what is marked",
    "steps": "each action (2-7): a picture from the library, 4 words or less, and a reading when there is one",
    "options": "the options (2-3) with their pictures, and up to 3 qualities each rated 1-3 from the slide's own words",
    "amounts": "the measured points from the source and the axes' names and units; code works out every change",
    "scene:pump_line": "the two tanks' names and levels, the parts on the line, and for each step whether the pump runs "
                       "and the valve is open",
    "scene:crossing": "the two ships' names and which step shows the bearing, the lights, the alteration",
    "photo": "nothing: a real photograph shows it - the photo search takes it",
    "task": "nothing: the task screen is the activity",
    "none": "nothing: the slide's words carry it",
}


def lines_of(s):
    return [x.strip() for x in str(s.get("text") or "").split("\n") if x.strip()]


def _title_groups(title):
    parts = [p.strip() for p in re.split(r",| and | or ", str(title or "")) if p.strip()]
    return 2 <= len(parts) <= 4 and all(len(p.split()) <= 2 for p in parts)


def _choices(s, t):
    L = lines_of(s)
    yield (bool(re.search(r"\b(drag|sort|match) (each|the)\b", t)), "task",
           "The trainee drags and sorts on this slide: the task screen is the activity, and a drawing would give the answer away.")
    yield (bool(re.match(r"(true or false|who do you call|quiz|which one)", str(s.get("title") or ""), re.I)), "none",
           "A question slide: the vote and the reasons carry it. A drawing beside it would answer the question.")
    yield (bool(re.match(r"(a )?real photograph", str(s.get("visual") or ""), re.I))
           or str(s.get("visual_kind") or "") in ("photo", "annotated_photo", "photo_to_take"), "photo",
           "The trainee must recognise real equipment: a real photograph shows it, a drawing would not.")
    yield (bool(re.search(r"\b(pump|discharge valve|suction)\b", t) and re.search(r"\b(start|flow|pressure)\b", t)), "scene:pump_line",
           "A machine and what flows through it: the scene shows the insides moving, which a camera cannot.")
    yield (bool(re.search(r"\b(crossing|give way|give-way|stand-on|risk of collision)\b", t)), "scene:crossing",
           "Two ships moving and the rule between them: geometry only a drawing can show.")
    yield (bool(re.search(r"worked example|procedure|entry steps", str(s.get("title") or ""), re.I))
           or sum(1 for x in L if " | " in x) >= 3, "steps",
           "An order of actions: one action at a time, each a picture, the done ones ticked.")
    m = re.findall(r"\b\d+(?:[.,]\d+)?\s?(?:hpa|bar|%|°c|kn|nm|m|t|h|kw|kv|v|a)\b", t)
    yield (len(m) >= 4, "amounts", "Numbers that change: drawn to scale, and code measures the change.")
    yield (bool(re.search(r"apart|segregat|segment|separat|isolat", str(s.get("title") or ""), re.I)), "zones",
           "Things kept apart: the zones, the walls between them, and what a wall stops.")
    yield (_title_groups(s.get("title")), "zones",
           "Two to four named groups: each a zone with real examples in it, so the difference is seen, not read.")
    yield (bool(re.search(r"\bfault|stops sending|\bdown\b|\bdark\b|broken", t)
                and re.search(r"\b(switch|link|network|cable|gyro|sensor|firewall|pipe|line|circuit|breaker)\b", t)), "path",
           "Something fails in a system: code works out who is cut off from where it fails or breaks.")
    yield (sum(1 for x in L if re.match(r"^[^:]{2,40}(\([^)]*\))?:\s", x)) >= 2
           and bool(re.search(r"long|short|quick|slow|cheap|wide|near|far|more|less", str(s.get("text") or ""), re.I)), "options",
           "Two or three choices weighed: rated side by side, and raced on the quality that decides.")
    yield (len(re.findall(r"\b(send|sends|feed|feeds|gather|gathers|travel|travels|route|link|cable|passes|go|goes|join|joins|"
                          r"flows?|supplies|from [a-z]+ to)\b", t)) >= 1, "path",
           "Something travels between real things: the path shows each thing and what moves along.")


def choose(s):
    """-> {"form", "why", "writes"} for one script screen"""
    t = " ".join(str(s.get(k) or "") for k in ("title", "text", "visual")).lower()
    for hit, form, why in _choices(s, t):
        if hit:
            return {"form": form, "why": why, "writes": WRITES[form]}
    return {"form": "none", "why": "The slide's words carry it: no figure teaches more here.", "writes": WRITES["none"]}


def starter(s, choice=None):
    """the spec the writer starts from: the form and one step per line of the slide; what only the writer can give is
    named in "_todo" (the compile refuses the figure until it is gone). None for a photo, a task or no figure."""
    c = choice or choose(s)
    form = c["form"]
    if form in ("photo", "task", "none"):
        return None
    say = str(s.get("visual") or s.get("title") or "").split(". ")[0].strip().rstrip(".") + "."
    steps = [{"line": i} for i in range(1, len(lines_of(s)) + 1)] or [{"line": 1}]
    spec = {"form": form, "say": say}
    if form.startswith("scene:"):
        spec = {"form": "scene", "scene": form.split(":")[1], "say": say}
    if form == "path":
        spec.update(things=[], links=[])
    elif form == "zones":
        spec.update(zones=[])
    elif form == "steps":
        steps = [dict(x, **{"is": "", "do": ""}) for x in steps]
    elif form == "options":
        spec.update(options=[], qualities=[])
    elif form == "amounts":
        spec.update(x={"name": "", "unit": ""}, y={"name": "", "unit": ""}, series=[])
    elif form == "scene:pump_line":
        spec.update({"from": {"name": "", "level": 0.8}, "to": {"name": "", "level": 0.2}, "parts": ["pump", "gauge", "valve"]})
    elif form == "scene:crossing":
        spec.update(own={"name": "Own ship"}, other={"name": "Other ship"})
    spec["steps"] = steps
    spec["_todo"] = c["writes"] + " - SPEC.md, then delete \"_todo\""
    return spec


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    script = json.load(io.open(argv[0], encoding="utf-8"))
    for s in script.get("screens", []):
        if s.get("kind") == "slide" and (s.get("visual_kind") or "none") != "none":
            c = choose(s)
            print("%-5s %-16s %s" % (s.get("id"), c["form"], c["why"]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
