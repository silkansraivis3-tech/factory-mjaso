# -*- coding: utf-8 -*-
"""test_expert_edits - L24, and the one answer that must never be silent.

    python test_expert_edits.py

The dangerous outcome for this script is not a missed marker. It is answering
"nothing protected" when it simply has no way to know - because that reads as
permission to rebuild, and the expert's work is gone before anyone notices.
So the no-evidence state is pinned hardest below.
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
CHECK = os.path.join(HERE, "detect_expert_edits.py")

PASS: list[str] = []
FAIL: list[str] = []


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print(("  ok    " if ok else "  FAIL  ") + name +
          (("  -> " + str(detail)[:200]) if detail and not ok else ""))


def run(module, *extra):
    p = subprocess.run([sys.executable, CHECK, module, *extra],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return p


def rj(module):
    p = run(module, "--json")
    try:
        return json.loads(p.stdout)
    except ValueError:
        return {"state": "?", "protected": [], "_raw": p.stdout + p.stderr}


def write(root, rel, body):
    p = os.path.join(root, rel.replace("/", os.sep))
    os.makedirs(os.path.dirname(p), exist_ok=True)
    io.open(p, "w", encoding="utf-8", newline="\n").write(body)
    return p


DECK = ('<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><title>M</title>'
        '</head><body>\n<section class="slide" data-title="Tank types">%s</section>\n'
        "</body></html>\n")


def sigs(d, name):
    return [f for f in d["protected"] if f["signal"] == name]


def main() -> int:
    tmp = tempfile.mkdtemp(prefix="sme_")
    print("=" * 72)
    print("test_expert_edits - which parts of this module are somebody's decision?")
    print("=" * 72)
    try:
        # ---- 4 · the state that must never be silent -------------------
        print("\n-- no evidence is NOT the same as untouched")
        r = os.path.join(tmp, "blank")
        write(r, "module.html", DECK % "<p>Independent type C.</p>")
        d = rj(r)
        check("with no record, no marker and no history the answer is 'ask'",
              d["state"] == "nothing-to-go-on", d)
        out = run(r).stdout
        check("and it says so in words, with the question to ask",
              "NO EVIDENCE EITHER WAY" in out and "Has anyone edited this module" in out)
        check("it never prints 'nothing protected' in that state",
              "Nothing protected" not in out)

        # ---- 1 · the expert said so ------------------------------------
        print("\n-- the expert left a marker")
        r = os.path.join(tmp, "marked")
        write(r, "module.html", DECK %
              '<p data-sme="type C is what our fleet actually carries">Independent C.</p>')
        d = rj(r)
        check("data-sme is protected", len(sigs(d, "marker")) == 1, d)
        check("and the expert's reason is carried into the report",
              "our fleet actually carries" in json.dumps(d))

        r = os.path.join(tmp, "commented")
        write(r, "module.html", DECK %
              "<!-- SME: keep this order, it is the order on the ship -->\n<p>A, B, C.</p>")
        d = rj(r)
        check("an <!-- SME: ... --> comment is protected", len(sigs(d, "marker")) == 1, d)

        r = os.path.join(tmp, "smedir")
        write(r, "module.html", DECK % "<p>x</p>")
        write(r, "_sme/notes_from_kapteinis.md", "The membrane slide is wrong.\n")
        d = rj(r)
        check("a file left in _sme/ is protected", len(sigs(d, "marker")) == 1, d)

        # ---- 2 · the factory's own build record ------------------------
        print("\n-- the factory's own build record")
        r = os.path.join(tmp, "record")
        p = write(r, "module.html", DECK % "<p>Independent type C.</p>")
        write(r, "tasks/t1.html", "<html><body>t1</body></html>\n")
        rec = run(r, "--record", "--version", "2.9.0")
        check("--record writes _factory/build.json",
              os.path.exists(os.path.join(r, "_factory", "build.json")), rec.stdout + rec.stderr)
        d = rj(r)
        check("immediately afterwards nothing is protected", not d["protected"], d)
        check("and the run says the rebuild may proceed",
              "Nothing protected" in run(r).stdout)

        io.open(p, "w", encoding="utf-8", newline="\n").write(
            DECK % "<p>Independent type C, and type B on the older ships.</p>")
        d = rj(r)
        check("a file edited afterwards becomes protected",
              [f["rel"] for f in sigs(d, "build-record")] == ["module.html"], d)

        write(r, "tasks/t9_added_by_expert.html", "<html><body>new</body></html>\n")
        d = rj(r)
        rels = sorted(f["rel"] for f in sigs(d, "build-record"))
        check("a file the expert ADDED is protected too",
              "tasks/t9_added_by_expert.html" in rels, rels)

        check("the report says what to do with them",
              "do not rewrite it" in run(r).stdout and "restyle it" in run(r).stdout)

        # ---- the record must not protect the factory's own scratch -----
        print("\n-- what the record deliberately ignores")
        r = os.path.join(tmp, "scratch")
        write(r, "module.html", DECK % "<p>x</p>")
        run(r, "--record")
        write(r, "_work/module.legacy.html", "<html><body>old</body></html>\n")
        write(r, "__pycache__/x.json", "{}\n")
        d = rj(r)
        check("_work/ and __pycache__ are not mistaken for an expert's work",
              not d["protected"], d)

        print("\n-- the record is a record, not a lock")
        r = os.path.join(tmp, "rerecord")
        p = write(r, "module.html", DECK % "<p>one</p>")
        run(r, "--record")
        io.open(p, "w", encoding="utf-8", newline="\n").write(DECK % "<p>two</p>")
        check("protected before re-recording", rj(r)["protected"])
        run(r, "--record")
        check("and clear again once the factory records its own new build",
              not rj(r)["protected"])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("\n" + "=" * 72)
    print("%d passed, %d failed" % (len(PASS), len(FAIL)))
    if FAIL:
        return 1
    print("\nAn expert's change is recognised by who touched it last, never by how the\n"
          "code looks - and 'I cannot tell' is answered out loud, not as permission.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
