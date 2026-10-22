# -*- coding: utf-8 -*-
"""test_visual_first - L23, and the three ways a rule like it goes wrong.

    python test_visual_first.py

L23 says a topic screen leads with the thing that shows it. A rule phrased that
loosely has three obvious failure modes, and all three are pinned below:

  * it fires on screens that are not topic screens - an opener, a running order,
    a task gate - and then everybody turns it off;
  * it accepts anything shaped like an image, so a finding is closed with an icon;
  * it accepts a figure buried under three paragraphs, which is a screen with a
    picture, not a screen that leads with one.
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
CHECK = os.path.join(HERE, "check_visual_first.py")

PASS: list[str] = []
FAIL: list[str] = []


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print(("  ok    " if ok else "  FAIL  ") + name +
          (("  -> " + str(detail)) if detail and not ok else ""))


def run(target):
    p = subprocess.run([sys.executable, CHECK, target, "--json"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    try:
        return json.loads(p.stdout)
    except ValueError:
        return {"topic_screens": 0, "findings": [], "_raw": p.stdout + p.stderr}


def deck(root, *screens):
    body = "\n".join(screens)
    p = os.path.join(root, "module.html")
    os.makedirs(root, exist_ok=True)
    io.open(p, "w", encoding="utf-8", newline="\n").write(
        "<!DOCTYPE html><html lang=\"en\"><head><meta charset=\"utf-8\">"
        "<title>M</title></head><body>\n" + body + "\n</body></html>\n")
    return root


FIG = '<figure><img src="assets/pump.jpg" alt="a cargo pump in section"></figure>'
TEXT = "<p>A cargo pump is never started against a closed suction.</p>"


def levels(d, level):
    return [f for f in d["findings"] if f["level"] == level]


SKILLS = os.path.dirname(os.path.dirname(HERE))
# the check scripts that stopped at their first non-ASCII character under `python -I` on Windows (cp1252 stdout; -I
# ignores PYTHONIOENCODING) - IGF analysis, 2026-10-21
CRASHED = ["course-visuals/scripts/check_assets.py", "course-visuals/scripts/check_visuals.py",
           "course-factory/hours/scripts/check_balance.py", "course-factory/coverage/scripts/check_syllabus_coverage.py",
           "course-factory/retrofit/scripts/check_language.py", "course-factory/retrofit/scripts/classify_module.py",
           "course-task-ux/scripts/check_task_pages.py", "course-module-ux/measure/scripts/check_static.py",
           "course-factory/scripts/check_module_folder.py"]


def tooling_part(tmp):
    """2.60.0 - the check tooling itself: the nine scripts print UTF-8 whatever the console's code page, and check_assets
    neither fails a module's assets\\ root for the logo the factory copied there nor walks a picture set aside"""
    print("\n-- 2.60.0: the check tooling")
    late = []
    for rel in CRASHED:
        src = io.open(os.path.join(SKILLS, rel), encoding="utf-8").read()
        at = src.find('sys.stdout.reconfigure(encoding="utf-8", errors="replace")')
        first, d = re.search(r"^(?!\s*#).*\bprint\(", src, re.M), src.find("\ndef ")
        if at < 0 or (first and first.start() < at) or 0 <= d < at:
            late.append(rel)
    check("each of the nine scripts sets its output to UTF-8 at the top, before anything prints", not late, late)
    env = {k: v for k, v in os.environ.items() if k not in ("PYTHONIOENCODING", "PYTHONUTF8")}
    p = subprocess.run([sys.executable, "-I", os.path.join(SKILLS, CRASHED[0]), os.path.join(tmp, "no such folder →")],
                       capture_output=True, env=env)
    check("check_assets.py under python -I prints a non-ASCII path instead of stopping on it",
          p.returncode == 2 and "→".encode("utf-8") in p.stdout and b"UnicodeEncodeError" not in p.stderr, p.stdout + p.stderr)

    mod = os.path.join(tmp, "assets_mod", "assets")
    os.makedirs(os.path.join(mod, "img", "_unused"))
    shutil.copy(os.path.join(SKILLS, os.pardir, "resources", "brand", "novikontas_logo.svg"), mod)
    io.open(os.path.join(mod, "img", "tank.jpg"), "wb").write(b"\xff\xd8\xff\xd9")
    io.open(os.path.join(mod, "img", "_photo_meta.json"), "w", encoding="utf-8").write(json.dumps({"tank.jpg": {
        "source": "Novikontas", "rights_state": "PROJECT_OWNED", "description": "A tank.", "teaching_purpose": "the tank",
        "used_in": "M01 s01", "visually_verified": "yes - a tank, 2026-10-21"}}))
    io.open(os.path.join(mod, "img", "_unused", "old.jpg"), "wb").write(b"\xff\xd8\xff\xd9")
    p = subprocess.run([sys.executable, "-I", os.path.join(SKILLS, CRASHED[0]), os.path.dirname(mod), "--json"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    try:
        found = json.loads(p.stdout)["findings"]
    except (ValueError, KeyError):
        found = [{"where": "?", "message": p.stdout + p.stderr}]
    check("check_assets: an assets\\ root with only the factory's logo is not 'images and no provenance file', and "
          "assets\\img\\_unused is not walked - the module is clean", p.returncode == 0 and not found, found)
    io.open(os.path.join(mod, "img", "pump.jpg"), "wb").write(b"\xff\xd8\xff\xd9")
    p = subprocess.run([sys.executable, "-I", os.path.join(SKILLS, CRASHED[0]), os.path.dirname(mod), "--json"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    check("... while a course picture with no record still fails", p.returncode == 1 and "pump.jpg" in p.stdout, p.stdout[-400:])


def main() -> int:
    tmp = tempfile.mkdtemp(prefix="visfirst_")
    print("=" * 72)
    print("test_visual_first - does a topic screen lead with the thing that shows it?")
    print("=" * 72)
    try:
        print("\n-- the law itself")
        r = deck(os.path.join(tmp, "a"),
                 '<section class="slide" data-title="The cargo pump">%s%s</section>' % (FIG, TEXT))
        d = run(r)
        check("figure above the prose passes", not d["findings"], d["findings"])
        check("and the screen was counted as a topic screen", d["topic_screens"] == 1)

        r = deck(os.path.join(tmp, "b"),
                 '<section class="slide" data-title="The cargo pump">%s</section>' % TEXT)
        d = run(r)
        check("a topic screen with no figure at all FAILS", len(levels(d, "FAIL")) == 1)

        r = deck(os.path.join(tmp, "c"),
                 '<section class="slide" data-title="The cargo pump">%s%s</section>' % (TEXT, FIG))
        d = run(r)
        check("a figure BELOW the prose is a warning, not a pass",
              len(levels(d, "WARN")) == 1 and not levels(d, "FAIL"), d["findings"])

        print("\n-- what is not a topic screen")
        for title, cls in (("Opening", "slide opener"), ("Running order", "slide"),
                           ("Hand-off", "slide"), ("Now a task", "slide"),
                           ("Summary", "slide sum")):
            r = deck(os.path.join(tmp, "n_" + title[:3].strip().replace(" ", "_")),
                     '<section class="%s" data-title="%s">%s</section>' % (cls, title, TEXT))
            d = run(r)
            check('"%s" is not judged as a topic screen' % title,
                  not d["findings"] and d["topic_screens"] == 0, d["findings"])

        # 2.63.2: the compiler's task-launch screen (a graded check's has data-kind "Check", no "task" in its title) leads with
        # its code and title and carries the task icon as its "figure" - it is a gate, not a topic screen
        ICON = ('<svg class="act-ico" data-icon="choose" viewBox="0 0 64 48" aria-hidden="true">'
                '<path d="M0 0"/></svg>')
        LAUNCH = ('<section class="slide activity" data-title="MC - Module check" data-kind="Check" '
                  'data-template="task-launch.v1" data-variant="check">\n'
                  '  <div class="slide-body activity">\n    <p class="act-code">MC</p>\n'
                  '    <h2 class="act-title">Module check</h2>\n    %s\n'
                  '    <div class="act-lines"><p class="act-inst">Answer on the tablet.</p></div>\n'
                  '  </div>\n</section>' % ICON)
        d = run(deck(os.path.join(tmp, "launch"), LAUNCH))
        check("a task-launch screen (task icon after its code line) is not judged as a topic screen",
              not d["findings"] and d["topic_screens"] == 0, d)
        d = run(deck(os.path.join(tmp, "launch2"),
                     LAUNCH.replace(' data-template="task-launch.v1" data-variant="check"', "")
                     .replace('class="slide activity"', 'class="slide"')))
        check("... also by its slide-body.activity alone", not d["findings"] and d["topic_screens"] == 0, d)

        print("\n-- a declared exemption is a decision, not an escape hatch")
        r = deck(os.path.join(tmp, "d"),
                 '<section class="slide" data-title="Flammable limits" '
                 'data-novisual="definition">%s</section>' % TEXT)
        check("a declared reason from the list is accepted in silence",
              not run(r)["findings"])

        r = deck(os.path.join(tmp, "e"),
                 '<section class="slide" data-title="Flammable limits" '
                 'data-novisual="looked busy">%s</section>' % TEXT)
        d = run(r)
        check("an invented reason is reported", len(levels(d, "WARN")) == 1, d["findings"])

        r = deck(os.path.join(tmp, "f"),
                 '<section class="slide" data-title="The pump" '
                 'data-novisual="definition">%s%s</section>' % (FIG, TEXT))
        d = run(r)
        check("declaring no visual while carrying one is a note",
              len(levels(d, "NOTE")) == 1, d["findings"])

        print("\n-- what counts as a figure")
        for key, name, markup in (
                ("svg", "an inline <svg>", '<svg viewBox="0 0 10 10"><path d="M0 0"/></svg>'),
                ("canvas", "a <canvas>", '<canvas id="c"></canvas>'),
                ("mount", "a mounted interactive figure", '<div data-figure="f1"></div>')):
            r = deck(os.path.join(tmp, "g_" + key),
                     '<section class="slide" data-title="Boil-off">%s%s</section>' % (markup, TEXT))
            check("%s counts" % name, not run(r)["findings"])

        print("\n-- the handoff, which is the other half of L23")
        r = os.path.join(tmp, "hand")
        deck(r, '<section class="slide" data-title="The regas skid" '
                'data-novisual="no_honest_representation">%s</section>' % TEXT)
        os.makedirs(os.path.join(r, "_visual_briefs"), exist_ok=True)
        io.open(os.path.join(r, "_visual_briefs", "regas_skid.md"), "w",
                encoding="utf-8", newline="\n").write(
            "# GENERATED_ASSET_REQUIRED - regas_skid\n\n## 7 - Forbidden inaccuracies\n"
            "- must NOT show a cargo pump in place of the vaporiser\n")
        w = os.path.join(HERE, "write_visual_handoff.py")
        p = subprocess.run([sys.executable, w, r], capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        out = os.path.join(r, "VISUAL_HANDOFF.md")
        check("a module with an unbuilt visual gets a handoff file", os.path.exists(out),
              p.stdout + p.stderr)
        body = io.open(out, encoding="utf-8").read() if os.path.exists(out) else ""
        check("the brief is carried into it in full",
              "must NOT show a cargo pump" in body)
        check("the declared gap is listed with its destination path",
              "The regas skid" in body and "assets/img/" in body)
        check("and it is paste-ready - the prompt is delimited",
              body.count("=====") >= 2)

        r2 = os.path.join(tmp, "nohand")
        deck(r2, '<section class="slide" data-title="The pump">%s%s</section>' % (FIG, TEXT))
        p = subprocess.run([sys.executable, w, r2], capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        check("a complete module gets no handoff file left behind",
              not os.path.exists(os.path.join(r2, "VISUAL_HANDOFF.md"))
              and "Nothing to hand off" in p.stdout, p.stdout)

        print("\n-- a comment is not a figure")
        r = deck(os.path.join(tmp, "h"),
                 '<section class="slide" data-title="Boil-off">'
                 '<!-- <img src="x.jpg"> was here, removed -->%s</section>' % TEXT)
        d = run(r)
        check("a commented-out image does not satisfy the law",
              len(levels(d, "FAIL")) == 1, d["findings"])

        tooling_part(tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("\n" + "=" * 72)
    print("%d passed, %d failed" % (len(PASS), len(FAIL)))
    if FAIL:
        return 1
    print("\nThe law bites on topic screens, stays quiet on openers and hand-offs, and a\n"
          "screen that honestly needs no figure has to say so.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
