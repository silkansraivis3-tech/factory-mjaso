#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""The places for a generated picture are found first, the person describes each, and every picture is counted (L47).

    python test_picture_briefs.py
"""
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "picture_briefs.py")
sys.path.insert(0, HERE)
import content_script as cs  # noqa: E402

PASS, FAIL = [], []


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print(("  ok    " if ok else "  FAIL  ") + name + ("" if ok else "  -> %s" % str(detail)[:600]))


def run(*a):
    p = subprocess.run([sys.executable, TOOL] + list(a), capture_output=True, text=True, encoding="utf-8", errors="replace")
    return p.returncode, p.stdout + p.stderr


SCRIPT = {"module": 1, "title": "Gas tankers", "operator_language": "en", "status": "approved", "screens": [
    {"id": "s01", "kind": "slide", "title": "Why gas tankers are different", "text": "x", "visual_kind": "photo", "visual": "A membrane LNG carrier alongside", "minutes": 5},
    {"id": "s02", "kind": "slide", "title": "Life on board a gas carrier", "text": "x", "visual_kind": "ai_illustration",
     "visual": "The cargo control room at night during loading, the duty officer at the console", "minutes": 5},
    {"id": "s03", "kind": "slide", "title": "A loaded LNG carrier at sea", "text": "x", "visual_kind": "video_generated",
     "visual": "A slow orbit around a loaded LNG carrier in a calm sea", "minutes": 5}]}


def main():
    tmp = tempfile.mkdtemp(prefix="pb_")
    try:
        master = os.path.join(tmp, "GAS_Basic")
        os.makedirs(os.path.join(master, "source_files"))
        os.makedirs(os.path.join(master, "course", "to_review"))
        os.makedirs(os.path.join(master, "course", "working_claude", "script"))
        io.open(os.path.join(master, "course", "working_claude", "script", "M01.json"), "w", encoding="utf-8").write(json.dumps(SCRIPT))

        print("-- the places come first, each with the questions to ask")
        code, out = run("list", master, "--module", "1")
        check("the module's two generated pictures are found - not the photograph", code == 0 and "2 place(s) for a generated picture" in out
              and "(s02)" in out and "(s03)" in out and "(s01)" not in out, out)
        check("each says what the script wants and that it is still to describe", out.count("to describe") == 2
              and "The cargo control room at night during loading" in out, out)
        check("the eight questions are printed, with the price, and the script's words as the suggestion",
              cs.MEDIA["generation_brief"]["questions"][0]["en"] in out and cs.MEDIA["generation_brief"]["questions"][7]["en"] in out
              and "about EUR 0.10" in out and "starting suggestion from the script: A slow orbit" in out, out)
        check("... and that nothing is generated before a yes", "Nothing is generated until the person has described the picture" in out, out)

        print("\n-- the person's description is kept")
        brief = os.path.join(tmp, "brief.json")
        io.open(brief, "w", encoding="utf-8").write(json.dumps({"answers": {"subject": "cargo control room, modern LNG carrier",
                                                                            "space": "left third empty"},
                                                                "prompt": "Photograph of the cargo control room of a modern LNG carrier at night ... no text, no logos."}))
        code, out = run("save", master, "--module", "1", "--slide", "s02", "--brief", brief)
        check("saved, and the next step is to show the prompt and ask", code == 0 and "Generate this one picture" in out, out)
        code, out = run("list", master, "--module", "1")
        check("the list now shows it described, with the agreed prompt", "described - show the prompt and ask for a yes" in out
              and "agreed prompt: Photograph of the cargo control room" in out and out.count("to describe") == 1, out)
        io.open(brief, "w", encoding="utf-8").write(json.dumps({"answers": {}}))
        check("a brief without a prompt is refused", run("save", master, "--module", "1", "--slide", "s02", "--brief", brief)[0] == 2)
        io.open(brief, "w", encoding="utf-8").write(json.dumps({"answers": {"subject": "LNG carrier"}, "prompt": "Photograph of an LNG carrier alongside"}))
        code, out = run("save", master, "--module", "1", "--slide", "s01", "--brief", brief)
        check("a place the script did not plan for generation can be described too (no photograph found)", code == 0, out)
        check("... and then it is listed", "(s01)" in run("list", master, "--module", "1")[1])
        check("a screen the script does not have is refused", run("save", master, "--module", "1", "--slide", "s99", "--brief", brief)[0] == 2)

        print("\n-- every picture made is recorded with the person's words, and counted")
        check("without the person's words nothing is recorded", run("done", master, "--module", "1", "--slide", "s02", "--file", "a.png", "--approved", " ")[0] == 2)
        code, out = run("done", master, "--module", "1", "--slide", "s02", "--file", "assets/ccr_night.png", "--approved", "Yes, generate it")
        check("recorded: picture 1 for the module, about EUR 0.10", code == 0 and "picture 1 for module 1, about EUR 0.10" in out, out)
        run("done", master, "--module", "1", "--slide", "s02", "--file", "assets/ccr_night_2.png", "--approved", "yes, with the window on the left")
        code, out = run("list", master, "--module", "1")
        check("the list shows the place made twice, and the module's total", "made 2 time(s), about EUR 0.20" in out
              and "2 picture(s) made so far, about EUR 0.20" in out, out)
        kept = json.load(io.open(os.path.join(master, "course", "working_claude", "picture_briefs", "M01.json"), encoding="utf-8"))
        check("all of it is kept in working_claude/picture_briefs/M01.json", kept["s02"]["made"][1]["approved_by_user"] == "yes, with the window on the left"
              and kept["s02"]["answers"]["space"] == "left third empty", kept)

        print("\n-- the questions are there for every operator language")
        qs = cs.MEDIA["generation_brief"]["questions"]
        check("eight questions, each in English, Latvian and Russian", len(qs) == 8 and all(q.get(k) for q in qs for k in ("en", "lv", "ru")), qs)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("\n" + "=" * 72 + "\n%d passed, %d failed" % (len(PASS), len(FAIL)))
    if not FAIL:
        print("The places come first, the person describes each picture, and every picture made is counted.")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
