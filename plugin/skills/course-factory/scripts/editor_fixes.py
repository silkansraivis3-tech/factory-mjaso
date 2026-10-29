# -*- coding: utf-8 -*-
"""editor_fixes.py - fixes made with Claude in the training app's editor mode, taken back into the course's script.

    editor_fixes.py read    <course> <export.json>                          what each fix changes in the script
    editor_fixes.py propose <course> <export.json> [--proposed-by "<who>"]  the changes, as PENDING script changes

The export is the file "Export for the factory" downloads from /classroom/editor/ (format novikontas-course-fixes-v1):
each fix with the slide's id (data-script), the instruction, and the slide as it was and as it became. The script is
the source of the course, so a fix lives on only when the script says it: a fixed title, line of text or instructor
note becomes a script change, which goes the way every correction goes - propose (this), then the operator reads the
list and says yes (content_script.py apply --confirmed), approves (content_script.py approve), and the module is
compiled again. Nothing here changes the script by itself.

A slide is read through the marks the compiler puts on it: data-script (the screen), data-script-field="title" and
"text" (one per line of the script's text) and data-cue (the notes). A fix whose "before" does not read as the
script does now is not taken - the script moved on since that release was built. A fix that also changed what the
script does not hold - the layout, a picture, a class - is named, so it can go into the build sheet by hand.
"""
from __future__ import annotations

import argparse
import html
import io
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import check_script_match as csm  # noqa: E402
import content_script as cs  # noqa: E402
import workspace  # noqa: E402

FORMAT = "novikontas-course-fixes-v1"
norm = csm.norm


def module_of(path):
    """the module number a deck's path names: .../module01/... or .../Module_03/... or .../m1/..."""
    m = re.search(r"(?:^|/)(?:module_?|m)0*(\d{1,2})(?:[_/]|$)", path, re.I)
    return int(m.group(1)) if m else None


def fields(slide_html):
    """(screen id, {"title": str, "text": [lines], "notes": str}, the slide with its marked words taken out)"""
    p = csm.Collect()
    p.feed(slide_html)
    p.close()
    sid = next(iter(p.screens), None)
    got = p.screens.get(sid, {"fields": {}})["fields"]
    cue = re.search(r'\bdata-cue\s*=\s*"([^"]*)"', slide_html.split(">", 1)[0] + ">")
    out = {"title": " ".join(norm(x) for x in got.get("title", [])),
           "text": [csm.unbullet(x) for x in got.get("text", []) if csm.unbullet(x)],
           "notes": html.unescape(cue.group(1)).strip() if cue else ""}
    # what is left when every marked word and the notes are taken out - the slide's shape
    shape = re.sub(r'\s+data-cue\s*=\s*"[^"]*"', "", slide_html)
    shape = re.sub(r'\s+data-title\s*=\s*"[^"]*"', "", shape)
    shape = re.sub(r'(<(\w+)[^>]*data-script-field="(?:title|text)"[^>]*>)[\s\S]*?(</\2>)', r"\1\3", shape)
    return sid, out, re.sub(r"\s+", " ", shape).strip()


def script_fields(screen):
    return {"title": norm(screen.get("title", "")),
            "text": [csm.unbullet(x) for x in (screen.get("text") or "").split("\n") if csm.unbullet(x)],
            "notes": (screen.get("notes") or "").strip()}


def same(a, b):
    return {"title": a["title"] == b["title"], "text": a["text"] == b["text"], "notes": norm(a["notes"]) == norm(b["notes"])}


def read(course, export):
    """{module: {"changes": [content_script change entries], "taken": [...], "left": [...]}} - the fixes in order, each
    checked against the script as the earlier fixes leave it"""
    if export.get("format") != FORMAT:
        raise SystemExit("Not an editor-mode export (%s expected)." % FORMAT)
    out, scripts, working = {}, {}, {}
    for fx in export.get("fixes") or []:
        label = "slide %s (%s) - %s" % (fx.get("slide"), fx.get("slide_id") or "?", norm(fx.get("instruction"))[:90])
        mod = module_of(fx.get("path", ""))
        if mod is None:
            out.setdefault(0, {"changes": [], "taken": [], "left": []})["left"].append(label + ": the deck's path names no module")
            continue
        r = out.setdefault(mod, {"changes": [], "taken": [], "left": []})
        if mod not in scripts:
            p = cs.paths(course, mod)
            if not os.path.isfile(p["script"]):
                r["left"].append(label + ": the course has no script for module %d" % mod)
                continue
            scripts[mod] = cs.load(p["script"])
        sid, before, shape_b = fields(fx.get("before_html") or "")
        sid2, after, shape_a = fields(fx.get("after_html") or "")
        if not sid or sid != sid2:
            r["left"].append(label + ": the slide is not built from the script (no data-script) - make the change by hand")
            continue
        screen = next((s for s in scripts[mod]["screens"] if s.get("id") == sid), None)
        if screen is None:
            r["left"].append(label + ": the script has no screen %s" % sid)
            continue
        now = working.get((mod, sid)) or script_fields(screen)
        bad = [k for k, ok in same(before, now).items() if not ok]
        if bad:
            r["left"].append(label + ": the slide's %s as the fix found it is not what the script says now - make the fix again on a release built from today's script" % " and ".join(bad))
            continue
        changed = [k for k, ok in same(after, before).items() if not ok]
        for k in changed:
            r["changes"].append({"field": "%s.%s" % (sid, k), "new": after[k] if k != "text" else "\n".join(after[k])})
        working[(mod, sid)] = after
        if shape_a != shape_b:
            r["left"].append(label + ": also changed what the script does not hold (layout, picture or markup) - put that into the build sheet by hand")
        r["taken"].append(label + (": " + ", ".join(changed) if changed else ": nothing the script holds changed"))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("cmd", choices=("read", "propose"))
    ap.add_argument("course")
    ap.add_argument("export")
    ap.add_argument("--proposed-by", default=None)
    o = ap.parse_args(argv)
    o.course = workspace.work_folder(o.course, create=False)
    export = json.load(io.open(o.export, encoding="utf-8"))
    res = read(o.course, export)
    rel = export.get("release") or {}
    print("Editor-mode fixes of %s, release %s: %d fix(es)." % (export.get("course_id"), rel.get("version"), len(export.get("fixes") or [])))
    code = 0
    for mod in sorted(res):
        r = res[mod]
        print("\nModule %s" % (mod or "?"))
        for x in r["taken"]:
            print("  taken  " + x)
        for x in r["left"]:
            print("  LEFT   " + x)
        if not r["changes"]:
            continue
        if o.cmd == "read":
            for c in r["changes"]:
                print("  would change %s -> %s" % (c["field"], norm(c["new"])[:120]))
            continue
        p = cs.paths(o.course, mod)
        path = os.path.join(os.path.dirname(p["script"]), "M%02d.editor_fixes.json" % mod)
        io.open(path, "w", encoding="utf-8", newline="\n").write(json.dumps(r["changes"], ensure_ascii=False, indent=2) + "\n")
        who = o.proposed_by or "editor mode, release %s" % rel.get("version")
        rc = cs.cmd_propose(o.course, mod, path, proposed_by=who)
        code = code or rc
    if o.cmd == "propose":
        print("\nNext: read each module's list of changes, and only after the operator says yes:\n"
              "  content_script.py apply <course> --module N --confirmed --confirmed-by \"<name>\"\n"
              "  content_script.py approve <course> --module N --by \"<name>\"   then compile the module again")
    return code


if __name__ == "__main__":
    sys.exit(main())
