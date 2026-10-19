#!/usr/bin/env python3
"""kit_parts.py - the parts a course added to the figure kit, and their way into the factory (L55)

  kit_parts.py list    <module folder> ...
  kit_parts.py promote <module folder> ... --factory <factory-mjaso clone> [--dry-run]

LIST     the new parts each module carries in assets/kit_parts.js: name, family, why, merged or not.
PROMOTE  run ONLY AFTER THE MODULE IS COMPLETE (its QA passed, its deck compiled). Copies each new part
         that passes check_kit.py into the factory's kit.js, before /* kit-parts: end */, with status 'kit'
         and the course and module it came from. With several modules (an orchestrated build) give them all
         at once: a part two modules both made is promoted once, and the second is reported for merging by hand.
         It writes files only. It never commits, pushes or opens the merge request - it prints those steps,
         and the operator is asked before they run (factory etiquette: a branch, never main; Raivis merges).

Exit 0 done or nothing to do, 1 a part failed its check (nothing written), 2 bad input.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_kit as ck  # noqa: E402

END = "/* kit-parts: end */"
KIT_REL = os.path.join("plugin", "skills", "course-visuals", "kit", "kit.js")
PLUGIN_REL = os.path.join("plugin", ".claude-plugin", "plugin.json")


def module_parts(mdir):
    p = os.path.join(mdir, "assets", "kit_parts.js")
    if not os.path.isfile(p):
        return p, []
    return p, ck.blocks(ck.read(p))


def as_kit(name, block, origin):
    """the block as it goes into kit.js: status 'kit', where it came from"""
    b = re.sub(r"\bstatus\s*:\s*(['\"])new\1", "status: 'kit', merged_from: %s" % json.dumps(origin), block, count=1)
    return "/* kit-part: %s */%s/* end kit-part */\n" % (name, b.rstrip() + "\n")


def cmd_list(dirs):
    any_ = False
    for d in dirs:
        p, found = module_parts(d)
        print("%s  (%s)" % (d, "no kit_parts.js" if not os.path.isfile(p) else "%d part(s)" % len(found)))
        for name, block in found:
            any_ = True
            print("  %-18s %-20s %-4s %s" % (name, ck.meta_field(block, "family") or "?", ck.meta_field(block, "status") or "?",
                                            ck.meta_field(block, "why") or ""))
    return 0 if any_ or dirs else 2


def cmd_promote(dirs, factory, dry):
    kit_js = os.path.join(factory, KIT_REL)
    if not os.path.isfile(kit_js):
        print("Stopped - %s is not a factory-mjaso clone (no %s)" % (factory, KIT_REL))
        return 2
    text = ck.read(kit_js)
    if END not in text:
        print("Stopped - the factory's kit.js has no %s marker; it predates L55" % END)
        return 2
    have = ck.kit_types(kit_js)
    todo, seen, failed, skipped = [], {}, [], []
    for d in dirs:
        p, found = module_parts(d)
        mod = os.path.basename(os.path.normpath(d))
        for name, block in found:
            if ck.meta_field(block, "status") != "new":
                continue
            probs = ck.check_part(name, block)
            if probs:
                failed += probs
                continue
            if name in have:
                skipped.append("%s (%s): the kit has it already - nothing to merge" % (name, mod))
                continue
            if name in seen:
                skipped.append("%s (%s): %s made one too - promoted that one; merge any difference by hand" % (name, mod, seen[name]))
                continue
            seen[name] = mod
            origin = "%s %s" % (ck.meta_field(block, "course") or "", ck.meta_field(block, "module") or mod)
            todo.append((name, as_kit(name, block, origin.strip())))
    for s in skipped:
        print("  skipped  " + s)
    if failed:
        print("Stopped - fix these first (check_kit.py parts), nothing was written:")
        for f in failed:
            print("  - " + f)
        return 1
    if not todo:
        print("Nothing to promote.")
        return 0
    new_text = text.replace(END, "".join(b for _, b in todo) + END)
    names = ", ".join(n for n, _ in todo)
    if dry:
        print("Would add to %s: %s" % (kit_js, names))
        return 0
    io.open(kit_js, "w", encoding="utf-8", newline="\n").write(new_text)
    plugin = os.path.join(factory, PLUGIN_REL)
    old = new = None
    if os.path.isfile(plugin):
        meta = json.loads(ck.read(plugin))
        old = meta.get("version", "0.0.0")
        x = [int(v) for v in re.findall(r"\d+", old)[:3]] + [0, 0, 0]
        new = "%d.%d.%d" % (x[0], x[1], x[2] + 1)
        raw = ck.read(plugin)
        io.open(plugin, "w", encoding="utf-8", newline="\n").write(raw.replace('"version": "%s"' % old, '"version": "%s"' % new, 1))
    slug = re.sub(r"[^a-z0-9]+", "-", names.lower()).strip("-")[:40]
    print("Promoted into %s: %s%s" % (kit_js, names, " · plugin %s -> %s" % (old, new) if new else ""))
    print("\nNext - ASK THE OPERATOR before the push and the merge request:")
    print('  git -C "%s" switch -c kit/%s' % (factory, slug))
    print('  git -C "%s" add %s %s' % (factory, KIT_REL.replace(os.sep, "/"), PLUGIN_REL.replace(os.sep, "/")))
    print('  git -C "%s" commit -m "%s - figure kit: %s (from a course build)"' % (factory, new or "kit", names))
    print('  git -C "%s" push -u origin kit/%s' % (factory, slug))
    print('  gh pr create --repo silkansraivis3-tech/factory-mjaso --base main --head kit/%s '
          '--title "Figure kit: %s" --body "<why each part, the module that used it, gallery screenshot>"' % (slug, names))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("list"); a.add_argument("modules", nargs="+")
    b = sub.add_parser("promote"); b.add_argument("modules", nargs="+")
    b.add_argument("--factory", required=True, help="a local clone of silkansraivis3-tech/factory-mjaso")
    b.add_argument("--dry-run", action="store_true")
    o = ap.parse_args(argv)
    if o.cmd == "list":
        return cmd_list(o.modules)
    return cmd_promote(o.modules, o.factory, o.dry_run)


if __name__ == "__main__":
    sys.exit(main())
