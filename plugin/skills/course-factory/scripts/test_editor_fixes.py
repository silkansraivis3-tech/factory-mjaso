# -*- coding: utf-8 -*-
"""test_editor_fixes.py - fixes made with Claude in the training app's editor mode, back into the script.

A module is compiled from an approved script; an export is made of its real deck the way the editor makes one; the
fixes go in as PENDING script changes and, once applied, the script says what the fixed slides said.
    python test_editor_fixes.py
"""
from __future__ import annotations

import io
import json
import os
import shutil
import subprocess
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "compile", "scripts"))
import content_script as cs  # noqa: E402
import test_compile_module as tcm  # noqa: E402

TOOL = os.path.join(HERE, "editor_fixes.py")
PASS, FAIL = [], []


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print(("  ok    " if ok else "  FAIL  ") + name + (("  -> " + str(detail)[:700]) if detail and not ok else ""))


def run(*args):
    p = subprocess.run([sys.executable] + list(args), capture_output=True, text=True, encoding="utf-8", errors="replace")
    return p.returncode, p.stdout + p.stderr


def fix(fid, before, after, instruction, sid="s02"):
    return {"id": fid, "path": "instructor/modules/module01/presentation/index.html", "slide": 2, "slide_id": sid,
            "instruction": instruction, "before_html": before, "after_html": after}


def main():
    tmp = tempfile.mkdtemp(prefix="edfix_")
    try:
        c, md = tcm.new_course(tmp, tcm.script())
        code, out = tcm.run(tcm.COMPILE, c, "--module", "1")
        check("the module compiles from its approved script", code == 0, out[-600:])
        before = tcm.section(tcm.deck(md), "s02")
        check("the deck's slide s02 is marked with its script fields", 'data-script-field="title"' in before and "data-cue" in before, before[:300])
        retitled = before.replace(">The Code<", ">The IGF Code<").replace('data-title="The Code"', 'data-title="The IGF Code"')
        reworded = retitled.replace("Mandatory since 2017.", "It has been mandatory since 2017.").replace("Stress the 60", "Underline the 60")
        export = {"format": "novikontas-course-fixes-v1", "course_id": "igf", "release": {"version": "1.0.1"}, "fixes": [
            fix("a", before, retitled, "a clearer title"),
            fix("b", retitled, reworded.replace('class="slide', 'class="slide wide', 1), "smoother wording and notes, wider"),
            fix("c", before, before.replace("Flashpoint below", "A flashpoint below"), "made on the old slide"),
            fix("d", "<p>no slide</p>", "<p>still none</p>", "not from the script", sid=None),
        ]}
        ex = os.path.join(tmp, "export.json")
        io.open(ex, "w", encoding="utf-8").write(json.dumps(export))

        code, out = run(TOOL, "read", c, ex)
        check("read: says what each fix changes, and changes nothing", code == 0 and "would change s02.title -> The IGF Code" in out
              and not os.path.isfile(cs.paths(c, 1)["pending"]), out[-900:])
        check("a fix whose slide moved on since is left, with the reason", "made on the old slide: the slide's" in out, out[-900:])
        check("a change the script does not hold (a class) is named for the build sheet", "put that into the build sheet by hand" in out, out[-900:])
        check("a slide not built from the script is left", "not built from the script" in out, out[-900:])

        code, out = run(TOOL, "propose", c, ex, "--proposed-by", "Claude in editor mode")
        pend = cs.load(cs.paths(c, 1)["pending"]) if os.path.isfile(cs.paths(c, 1)["pending"]) else {}
        fields = sorted("%s.%s" % (x.get("screen"), x.get("field")) for x in pend.get("changes", []))
        check("propose: the fixes wait as PENDING script changes - title, text and notes of s02", code == 0 and fields == ["s02.notes", "s02.text", "s02.title"], [fields, out[-600:]])

        code, out = run(os.path.join(HERE, "content_script.py"), "apply", c, "--module", "1", "--confirmed", "--confirmed-by", "Test")
        s02 = [s for s in cs.load(cs.paths(c, 1)["script"])["screens"] if s["id"] == "s02"][0]
        check("once the operator says yes, the script says what the fixed slide said",
              code == 0 and s02["title"] == "The IGF Code" and "It has been mandatory since 2017." in s02["text"].split("\n")
              and "Underline the 60" in s02["notes"] and "Flashpoint below 60 °C." in s02["text"], [out[-500:], s02])

        bad = os.path.join(tmp, "bad.json")
        io.open(bad, "w", encoding="utf-8").write(json.dumps({"format": "something else"}))
        code, out = run(TOOL, "read", c, bad)
        check("a file that is not an editor-mode export is refused", code != 0 and "Not an editor-mode export" in out, out[-300:])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("\n%d passed, %d failed" % (len(PASS), len(FAIL)))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
