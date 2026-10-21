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

        print("\n-- the free Gemini-app route: every place, its prompt and its file decided before the browser opens")
        code, out = run("queue", master, "--module", "1", "--all")
        q = json.load(io.open(os.path.join(master, "course", "working_claude", "picture_briefs", "M01.gemini.json"), encoding="utf-8"))
        by = {x["slide"]: x for x in q}
        check("the queue lists the still pictures - not the video clip, not the photograph", code == 0 and set(by) == {"s01", "s02"}, out)
        check("the person's saved prompt is used as it is", by["s02"]["prompt"].startswith("Photograph of the cargo control room")
              and by["s02"]["prompt_from"] == "the person", by["s02"])
        check("every line ends in a file in the module's own folder",
              all(x["save_as"].endswith(".png") and os.sep + "modules" + os.sep + "module01" + os.sep in x["save_as"] for x in q), q)

        print("\n-- 2.63.0: a builder makes the drafted prompt better, without inventing the person's answers")
        io.open(brief, "w", encoding="utf-8").write(json.dumps({"prompt": "Photograph of an LNG carrier alongside a terminal"}))
        check("a prompt with neither the person's answers nor \"refined\" is still refused",
              run("save", master, "--module", "1", "--slide", "s01", "--brief", brief)[0] == 2)
        io.open(brief, "w", encoding="utf-8").write(json.dumps({"prompt": "Photograph of an LNG carrier alongside a terminal, the "
                                                                          "loading arms connected, daylight", "refined": "the arms named"}))
        code, out = run("save", master, "--module", "1", "--slide", "s01", "--brief", brief)
        kept = json.load(io.open(os.path.join(master, "course", "working_claude", "picture_briefs", "M01.json"), encoding="utf-8"))
        check("a refined prompt is saved; the person's answers already kept stay as they were",
              code == 0 and kept["s01"]["prompt"].endswith("daylight") and kept["s01"]["answers"] == {"subject": "LNG carrier"}
              and kept["s01"]["refined"] == "the arms named", (out, kept.get("s01")))
        run("queue", master, "--module", "1", "--all")
        q = {x["slide"]: x for x in json.load(io.open(os.path.join(master, "course", "working_claude", "picture_briefs", "M01.gemini.json"), encoding="utf-8"))}
        check("the queue says the builder made it better and that the person sees it - never 'the person'",
              q["s01"]["prompt"].endswith("daylight") and q["s01"]["prompt_from"].startswith("the builder (the arms named)"), q["s01"])
        check("the list shows it as the builder's, to be shown and asked",
              "made better by the builder (the arms named)" in run("list", master, "--module", "1")[1])
        bare = dict(SCRIPT, screens=SCRIPT["screens"] + [{"id": "s04", "kind": "slide", "title": "The bunkering station at night",
                                                             "text": "x", "visual_kind": "ai_illustration",
                                                             "visual": "The bunkering station of an LNG-fuelled ferry at night, drip tray under the manifold",
                                                             "minutes": 5},
                                                            {"id": "s05", "kind": "slide", "title": "Three kinds of fuel tank",
                                                             "text": "x", "visual_kind": "comparison",
                                                             "visual": "Type A, Type B and Type C tanks side by side, each in its hold",
                                                             "minutes": 5},
                                                            {"id": "s06", "kind": "slide", "title": "Hazardous zones", "text": "x",
                                                             "visual_kind": "schematic", "visual": "The zones around the fuel preparation room",
                                                             "minutes": 5},
                                                            {"id": "s07", "kind": "slide", "title": "Fuel lines", "text": "x",
                                                             "visual_kind": "flow_animation", "visual": "Gas flowing to the engine",
                                                             "minutes": 5}])
        io.open(os.path.join(master, "course", "working_claude", "script", "M01.build.json"), "w", encoding="utf-8").write(
            json.dumps({"module": 1, "screens": {"s06": {"figure": "m01_s06.svg", "no_picture": True}}}))
        io.open(os.path.join(master, "course", "working_claude", "script", "M01.json"), "w", encoding="utf-8").write(json.dumps(bare))
        code, out = run("queue", master, "--module", "1")
        q = json.load(io.open(os.path.join(master, "course", "working_claude", "picture_briefs", "M01.gemini.json"), encoding="utf-8"))
        by = {x["slide"]: x for x in q}
        p = by.get("s04", {}).get("prompt", "")
        check("without --all a place already made is left out", "s02" not in by and "s04" in by, out)
        check("a place nobody described gets a prompt drafted from the script's own words - style, subject, space, no text, aspect",
              p.startswith("A realistic documentary photograph of the bunkering station of an LNG-fuelled ferry at night")
              and "No text, no letters" in p and "lower-left third" in p and p.endswith("Aspect ratio 16:9, landscape, high detail.")
              and by["s04"]["rel"] == "assets/img/m01_s04_bunkering_station_night.png", by.get("s04"))
        check("the same script gives the same prompt", run("queue", master, "--module", "1")[1] == out)
        d = by.get("s05", {})
        check("a drawing slide keeps its drawing and gets the real thing under it - a 3D render of the slide's subject, 4:3",
              d.get("place_as") == "under the drawing (inset)" and d.get("aspect") == "4:3"
              and d.get("prompt", "").startswith("A photorealistic 3D render of three kinds of fuel tank. Show it as it really")
              and "side by side" not in d.get("prompt", "")
              and "as it really looks on a ship" in d.get("prompt", "") and "No text" in d.get("prompt", "")
              and d.get("rel") == "assets/img/m01_s05_three_kinds_fuel_tank_3d.png", d)
        check("a drawing slide marked no_picture, and an animation of flow, are left alone", "s06" not in by and "s07" not in by, sorted(by))
        code, out = run("done", master, "--module", "1", "--slide", "s05", "--file", d.get("rel", "x.png"), "--approved", "go", "--free")
        check("a picture from the Gemini app is counted but costs nothing", "(this one free, from the Gemini app)" in out
              and "about EUR 0.20 so far" in out, out)
        build = json.load(io.open(os.path.join(master, "course", "working_claude", "script", "M01.build.json"), encoding="utf-8"))
        check("done puts a drawing slide's picture under the drawing - the drawing stays the slide's figure",
              build["screens"].get("s05", {}).get("inset") == {"photo": d.get("rel"), "under": "figure"}
              and "figure" not in build["screens"]["s05"], (out, build))
        check("... and a slide that has its picture under the drawing is not queued again",
              "(s05)" not in run("queue", master, "--module", "1")[1])
        code, out = run("done", master, "--module", "1", "--slide", "s04", "--file", by["s04"]["rel"], "--approved", "ok, the whole list")
        build = json.load(io.open(os.path.join(master, "course", "working_claude", "script", "M01.build.json"), encoding="utf-8"))
        check("done puts the picture into the build sheet, so the next compile places it",
              build["screens"]["s04"]["figure"] == "assets/img/m01_s04_bunkering_station_night.png" and "build sheet now places it" in out, (out, build))

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
