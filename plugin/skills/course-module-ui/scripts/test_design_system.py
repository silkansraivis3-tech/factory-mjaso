# -*- coding: utf-8 -*-
"""test_design_system - the style files are copied, never read, and nothing is lost by it.

    python test_design_system.py

Step 11b of Phase 5 replaced "read 82 KB of style files" with "run a script that copies them,
and read a one-page vocabulary instead". That trade is only safe if three things hold, and all
three are pinned below:

  * the copies really are the factory's files, byte for byte - and the check can tell a copy
    that fell behind the factory from one somebody edited by hand;
  * the script never overwrites a module that already exists (it may be a delivered one) and
    never writes into the Android project;
  * the vocabulary is COMPLETE: every class and every token the style files define is named in
    references/vocabulary.md, and nothing named there is invented. Otherwise the model would
    stop using the parts of the design system nobody listed.
"""
from __future__ import annotations

import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
SKILLS = os.path.dirname(SKILL)
TOOL = os.path.join(HERE, "design_system.py")
VOCAB = os.path.join(SKILL, "references", "vocabulary.md")
SPEC = json.load(io.open(os.path.join(SKILL, "knowledge", "design-system.json"), encoding="utf-8"))
STYLE_FILES = [
    os.path.join(SKILL, "templates", "gb_compose.css"),
    os.path.join(SKILL, "templates", "gb_shell.css"),
    os.path.join(SKILL, "templates", "gb_page.css"),
    os.path.join(SKILLS, "course-task-ux", "assets", "gb_task.css"),
]
TOKENS = os.path.join(SKILL, "templates", "gb_tokens.css")

PASS: list[str] = []
FAIL: list[str] = []


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print(("  ok    " if ok else "  FAIL  ") + name +
          (("  -> " + str(detail)) if detail and not ok else ""))


def tool(*args):
    p = subprocess.run([sys.executable, TOOL] + list(args),
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return p.returncode, p.stdout + p.stderr


def states(module):
    code, out = tool("check", module, "--json")
    try:
        return code, {r["file"]: r["state"] for r in json.loads(out)["files"]}
    except (ValueError, KeyError):
        return code, {"_raw": out}


def css_classes(path):
    s = io.open(path, encoding="utf-8").read()
    s = re.sub(r"/\*.*?\*/", "", s, flags=re.S)
    for _ in range(3):                      # strip declaration blocks, nested once for @media
        s = re.sub(r"\{[^{}]*\}", "{}", s)
    return set(re.findall(r"\.([a-zA-Z][\w-]*)", s))


def main():
    tmp = tempfile.mkdtemp(prefix="ds_")
    try:
        print("-- install puts every file in place, identical")
        m = os.path.join(tmp, "course", "modules", "m1")
        os.makedirs(m)
        code, out = tool("install", m, "--start-deck")
        check("install exits 0 on a new module", code == 0, out)
        code, st = states(m)
        check("check says every file is identical", code == 0 and set(st.values()) == {"OK"}, st)
        check("all %d listed files were copied" % len(SPEC["files"]), len(st) == len(SPEC["files"]), st)
        check("the starter deck was written", os.path.exists(os.path.join(m, "module.html")))
        rec = json.load(io.open(os.path.join(tmp, "course", "working_claude", "modules", "m1", "design_system.json"), encoding="utf-8"))
        check("the record holds a fingerprint for every file", len(rec["files"]) == len(SPEC["files"]), rec)
        check("the record is kept with the factory's own files, not inside the module folder (L44)",
              not os.path.exists(os.path.join(m, "_factory")))

        print("\n-- the check catches every way a copy stops being the factory's")
        css = os.path.join(m, "assets", "gb_compose.css")
        with open(css, "ab") as f:
            f.write(b"\n.my-own{color:red}\n")
        code, st = states(m)
        check("one added line is reported as CHANGED", code == 1 and st["gb_compose.css"] == "CHANGED", st)
        os.remove(os.path.join(m, "assets", "gb_deck.js"))
        code, st = states(m)
        check("a deleted engine is reported as MISSING", st.get("gb_deck.js") == "MISSING", st)

        print("\n-- an existing module is never overwritten without being asked")
        code, out = tool("install", m)
        check("install refuses to replace a differing file", code == 1 and "--update" in out, out)
        check("... and the edited file was left exactly as it was",
              b".my-own" in open(css, "rb").read())
        check("... while the missing file was still put back",
              os.path.exists(os.path.join(m, "assets", "gb_deck.js")))
        deck = os.path.join(m, "module.html")
        with open(deck, "ab") as f:
            f.write(b"<!-- my work -->")
        code, out = tool("install", m, "--update", "--start-deck")
        check("--update restores the factory's file", states(m)[1]["gb_compose.css"] == "OK", out)
        check("--start-deck never overwrites a module's own deck",
              b"<!-- my work -->" in open(deck, "rb").read())

        print("\n-- a copy the factory has since improved is OUTDATED, not CHANGED")
        recp = os.path.join(tmp, "course", "working_claude", "modules", "m1", "design_system.json")
        rec = json.load(io.open(recp, encoding="utf-8"))
        old = b"/* an older factory version */\n"
        tok = os.path.join(m, "assets", "gb_tokens.css")
        open(tok, "wb").write(old)
        import hashlib
        rec["files"]["gb_tokens.css"] = hashlib.sha256(old).hexdigest()
        io.open(recp, "w", encoding="utf-8").write(json.dumps(rec))
        check("an untouched older copy reads OUTDATED", states(m)[1]["gb_tokens.css"] == "OUTDATED")

        print("\n-- the Android project is a publish target, never a workspace (L21)")
        a = os.path.join(tmp, "AndroidStudioProjects", "NOVIKONTASTraining", "m1")
        os.makedirs(a)
        code, out = tool("install", a)
        check("install refuses a folder inside the Android project",
              code == 2 and not os.path.exists(os.path.join(a, "assets")), out)

        print("\n-- the factory's own files pass its own strict look check (2.11.2)")
        fresh = os.path.join(tmp, "course", "modules", "m2")
        os.makedirs(fresh)
        tool("install", fresh)
        p = subprocess.run([sys.executable, os.path.join(HERE, "audit_ui.py"), "--strict", fresh],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        check("audit_ui.py --strict finds no defect in a freshly set-up module",
              p.returncode == 0 and "0 defects" in p.stdout, p.stdout[-600:])

        print("\n-- the install record never ships to a tablet")
        sys.path.insert(0, os.path.join(SKILLS, "course-tablet-publisher", "scripts"))
        import gates
        plat = gates.load_platform()
        repo = os.path.join(tmp, "repo")
        trainee = plat["asset_roots"]["trainee"]
        rec_path = os.path.join(repo, trainee, "courses", "x", "modules", "m1", "_factory", "design_system.json")
        css_path = os.path.join(repo, trainee, "courses", "x", "modules", "m1", "assets", "gb_tokens.css")
        check("the publisher sorts _factory/design_system.json as INTERNAL",
              gates.classify(repo, plat, rec_path) == "INTERNAL", gates.classify(repo, plat, rec_path))
        check("... while the copied style files still ship to the trainee",
              gates.classify(repo, plat, css_path) == "TRAINEE", gates.classify(repo, plat, css_path))

        print("\n-- the vocabulary is complete, and invents nothing")
        vocab = io.open(VOCAB, encoding="utf-8").read()
        ticked = " ".join(re.findall(r"`([^`]+)`", vocab))
        named = set(re.findall(r"[A-Za-z][\w-]*", ticked))
        for path in STYLE_FILES:
            missing = sorted(c for c in css_classes(path) if c not in named)
            check("every class in %s is in the vocabulary" % os.path.basename(path), not missing, missing)
        defined = set().union(*[css_classes(p) for p in STYLE_FILES])
        api = re.sub(r"\b[A-Z]\w*\.\w+", "", ticked)   # GBDeck.init is an engine call, not a class
        dotted = set(re.findall(r"\.([a-z][\w-]*)", api)) - {"css", "js", "html", "json", "md", "svg", "py"}
        invented = sorted(dotted - defined)
        check("no class in the vocabulary is invented", not invented, invented)
        toks = set(re.findall(r"(--[a-z][\w-]*)\s*:", io.open(TOKENS, encoding="utf-8").read()))
        vt = set(re.findall(r"--[a-z][\w-]*", ticked)) - {"--start-deck", "--update", "--json"}
        check("every token is in the vocabulary", not (toks - vt), sorted(toks - vt))
        check("no token in the vocabulary is invented", not (vt - toks), sorted(vt - toks))
        for item in SPEC["files"]:
            check("the vocabulary names %s" % item["name"], item["name"] in vocab)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("\n" + "=" * 72)
    print("%d passed, %d failed" % (len(PASS), len(FAIL)))
    if FAIL:
        return 1
    print("\nThe style files are copied byte for byte, an edited or missing copy is caught, a\n"
          "module is never overwritten unasked, and the vocabulary names everything they hold.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
