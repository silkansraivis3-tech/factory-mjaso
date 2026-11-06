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

        print("\n-- every Phase A placeholder is queued, and a picture found or made goes into its place")
        sys.path.insert(0, os.path.join(os.path.dirname(HERE), "compile", "scripts"))
        import placeholder
        ph = os.path.join(tmp, "PH")
        os.makedirs(os.path.join(ph, "source_files"))
        os.makedirs(os.path.join(ph, "course", "to_review"))
        sd = os.path.join(ph, "course", "working_claude", "script")
        os.makedirs(sd)
        mdir = os.path.join(ph, "course", "modules", "module01")
        io.open(os.path.join(sd, "M01.json"), "w", encoding="utf-8").write(json.dumps({"module": 1, "title": "Gas tankers",
            "operator_language": "en", "status": "approved", "screens": [
                {"id": "s01", "kind": "slide", "title": "Six gas carriers", "text": "x", "visual_kind": "photo",
                 "visual": "Six gas carriers side by side", "minutes": 5},
                {"id": "q01", "kind": "self-check", "mechanic": "hotspot", "question": "Tap the secondary barrier.",
                 "answer": "Primary membrane\nSecondary barrier*", "visual_kind": "model_3d", "visual": "A membrane tank cut open"},
                {"id": "m01", "kind": "module-check", "question": "Which tank is a Type C?", "answer": "A\nB*",
                 "visual": "Four hull sections"}]}))
        rels = {k: placeholder.write(mdir, k, asp, shows) for k, asp, shows in (
            ("s01", "16:9", "six gas carriers A-F"), ("q01", "4:3", "membrane tank 3D section cut open, layers unlabelled"),
            ("m01", "16:9", "four hull sections unlabelled"), ("s09b", "16:9", "an inset photo the script does not name"))}
        grid = {"Primary membrane": [5.0, 7.5, 40.0, 35.0], "Secondary barrier": [55.0, 7.5, 40.0, 35.0]}
        io.open(os.path.join(sd, "M01.build.json"), "w", encoding="utf-8").write(json.dumps({"module": 1, "screens": {
            "s01": {"figure": rels["s01"], "placeholder": "photo", "_placeholder": "Phase A placeholder"},
            "q01": {"figure": rels["q01"], "areas": dict(grid), "placeholder": "3d", "_placeholder": "Phase A placeholder"},
            "m01": {"figure": rels["m01"], "areas": {"A": [5, 5, 40, 40], "B": [55, 5, 40, 40]}},
            "s02": {"inset": {"photo": rels["s09b"], "under": "figure"}}}}))
        code, out = run("queue", ph, "--module", "1")
        q = {x["slide"]: x for x in json.load(io.open(os.path.join(ph, "course", "working_claude", "picture_briefs", "M01.gemini.json"),
                                                         encoding="utf-8"))}
        check("the queue lists every file whose _photo_meta.json record says placeholder - task and check pictures and photo "
              "slots too", code == 0 and set(q) == {"s01", "q01", "m01", "s09b"} and "4 placeholder(s)" in out, (out, sorted(q)))
        check("... each at its placeholder's shape, saved under its own name, never over the placeholder",
              q["q01"]["aspect"] == "4:3" and q["s01"]["aspect"] == "16:9" and q["q01"]["placeholder"] == rels["q01"]
              and all("_placeholder_" not in x["rel"] for x in q.values()), q.get("q01"))
        check("... a placeholder the script does not name is drafted from what its record says it holds",
              "an inset photo the script does not name" in q["s09b"]["prompt"], q.get("s09b"))
        pic = os.path.join(tmp, "found.jpg")
        try:
            from PIL import Image
            Image.new("RGB", (1600, 1200), (90, 120, 150)).save(pic)
        except ImportError:
            io.open(pic, "wb").write(b"\xff\xd8\xff\xd9")
        code, out = run("place", ph, "--module", "1", "--slide", "q01", "--file", pic, "--rights", "PUBLIC_DOMAIN",
                        "--source", "https://commons.wikimedia.org/wiki/File:Membrane.jpg", "--credit", "US Navy",
                        "--seen", "membrane tank 3D section, cut open, layers without labels")
        b = json.load(io.open(os.path.join(sd, "M01.build.json"), encoding="utf-8"))
        meta = json.load(io.open(os.path.join(mdir, "assets", "img", "_photo_meta.json"), encoding="utf-8"))
        new = b["screens"]["q01"]["figure"]
        check("place: the picture is copied into assets/img under the slot's own name and the build sheet points at it",
              code == 0 and new.startswith("assets/img/m01_q01_") and new.endswith(".jpg") and os.path.isfile(os.path.join(mdir, new)), (out, b))
        rec = meta.get(os.path.basename(new), {})
        check("... with its record: rights, source, credit, what it shows, its size and where it is used",
              rec.get("rights_state") == "PUBLIC_DOMAIN" and rec.get("credit") == "US Navy" and "commons" in rec.get("source", "")
              and "membrane tank" in rec.get("description", "") and "placeholder" not in rec, rec)
        check("... and the placeholder and its record are gone",
              not os.path.isfile(os.path.join(mdir, rels["q01"])) and "_placeholder_q01.png" not in meta, sorted(meta))
        check("a tap question keeps the Phase A grid until its boxes are put on the real things - and says so",
              b["screens"]["q01"]["areas"] == grid and "areas" in b["screens"]["q01"].get("_placeholder", "")
              and "still the Phase A grid" in out, (out, b["screens"]["q01"]))
        code, out = run("areas", ph, "--module", "1", "--slide", "q01", "--areas", "[[10, 20, 30, 40]]")
        check("areas: one box per answer, or it is refused", code == 2 and "1 box(es) for 2 answer(s)" in out, out)
        code, out = run("areas", ph, "--module", "1", "--slide", "q01", "--areas", "[[10, 20, 30, 40], [60, 20, 70, 40]]")
        check("... a box outside the picture is refused", code == 2 and "Secondary barrier" in out, out)
        code, out = run("areas", ph, "--module", "1", "--slide", "q01", "--areas", "[[10, 20, 30, 40], [50, 22.25, 25, 30]]")
        b = json.load(io.open(os.path.join(sd, "M01.build.json"), encoding="utf-8"))
        check("... the boxes on the real things, in the order of the answers, and the Phase A notes gone",
              code == 0 and b["screens"]["q01"]["areas"] == {"Primary membrane": [10.0, 20.0, 30.0, 40.0], "Secondary barrier": [50.0, 22.2, 25.0, 30.0]}
              and "_placeholder" not in b["screens"]["q01"] and "placeholder" not in b["screens"]["q01"], b["screens"]["q01"])
        code, out = run("place", ph, "--module", "1", "--slide", "m01", "--file", pic, "--generated", "--prompt", "Four hull sections",
                        "--areas", json.dumps({"A": [1, 1, 20, 20], "B": [50, 50, 20, 20]}), "--seen", "four hull sections, unlabelled")
        b = json.load(io.open(os.path.join(sd, "M01.build.json"), encoding="utf-8"))
        meta = json.load(io.open(os.path.join(mdir, "assets", "img", "_photo_meta.json"), encoding="utf-8"))
        rec = meta.get(os.path.basename(b["screens"]["m01"]["figure"]), {})
        check("a generated picture is recorded as generated, with its prompt, and its boxes set at once",
              code == 0 and rec.get("generated") is True and rec.get("rights_state") == "GENERATED"
              and rec.get("generation_prompt") == "Four hull sections" and b["screens"]["m01"]["areas"]["B"] == [50.0, 50.0, 20.0, 20.0], (out, rec))
        code, out = run("place", ph, "--module", "1", "--slide", "s09b", "--file", pic, "--rights", "PROJECT_OWNED",
                        "--seen", "an inset photo the script does not name")
        b = json.load(io.open(os.path.join(sd, "M01.build.json"), encoding="utf-8"))
        check("a placeholder held deeper in the sheet (an inset) is replaced where it is, not added as a figure",
              code == 0 and b["screens"]["s02"]["inset"]["photo"].startswith("assets/img/m01_s09b_") and "s09b" not in b["screens"], b["screens"])
        code, out = run("place", ph, "--module", "1", "--slide", "s01", "--file", pic, "--rights", "ATTRIBUTION_REQUIRED")
        check("ATTRIBUTION_REQUIRED without a credit and an author is refused", code == 2 and "--credit and --author" in out, out)
        code, out = run("place", ph, "--module", "1", "--slide", "s01", "--file", pic, "--rights", "fine")
        check("a rights state the pipeline does not know is refused", code == 2 and "OWNER_CLEARED" in out, out)
        code, out = run("queue", ph, "--module", "1")
        check("what is placed is not queued again", code == 0 and "1 picture(s) to make" in out and "(s01)" in out, out)
        check("... and the course package check has one placeholder left", placeholder.found(mdir) == [rels["s01"]], placeholder.found(mdir))

        print("\n-- what is placed is what was asked, one thing a picture")
        code, out = run("place", ph, "--module", "1", "--slide", "s01", "--file", pic, "--rights", "PROJECT_OWNED")
        check("place without saying what the picture shows (--seen) is refused", code == 2 and "--seen" in out, out)
        import compile_module as cm
        sc5 = {"module": 1, "screens": [{"id": "s05", "kind": "slide", "title": "Kinds of gas carrier", "text": "x", "visual_kind": "photo",
                                          "picture": {"kind": "photo", "aspect": "16:9", "shows": "four kinds of gas carrier",
                                                      "items": ["Moss LNG carrier", "LPG carrier", "LPG carrier at sea"]}}]}
        sheet5 = {"screens": {}}
        done = cm.fill_slots(sc5, sheet5, mdir)
        tiles = sheet5["screens"]["s05"]["tiles"]
        check("a slide with picture.items gets a placeholder a thing, as tiles - never one picture of all of them",
              len(tiles) == 3 and all("_placeholder_s05_%d" % k in t for k, t in enumerate(tiles, 1))
              and done == [("s05", "3 pictures, one a thing")], (tiles, done))
        b = json.load(io.open(os.path.join(sd, "M01.build.json"), encoding="utf-8"))
        b["screens"]["s05"] = sheet5["screens"]["s05"]
        io.open(os.path.join(sd, "M01.build.json"), "w", encoding="utf-8").write(json.dumps(b))
        code, out = run("queue", ph, "--module", "1")
        q = {x["slide"]: x for x in json.load(io.open(os.path.join(ph, "course", "working_claude", "picture_briefs", "M01.gemini.json"),
                                                         encoding="utf-8"))}
        check("... each is queued on its own, its prompt naming its one thing",
              all(k in q for k in ("s05_1", "s05_2", "s05_3")) and "moss lng carrier" in q["s05_1"]["prompt"].lower(), sorted(q))
        code, out = run("place", ph, "--module", "1", "--slide", "s05_1", "--file", pic, "--rights", "PROJECT_OWNED",
                        "--seen", "a small LNG carrier, 3D render, membrane tanks")
        check("a picture that does not show what was asked is refused - asked a Moss LNG carrier, it shows another (GAS BASIC M01 s02)",
              code == 2 and "not in it: moss" in out, out)
        code, out = run("place", ph, "--module", "1", "--slide", "s05_1", "--file", pic, "--rights", "PROJECT_OWNED",
                        "--seen", "Moss LNG carrier with four spheres above the deck")
        check("... the right one is placed", code == 0, out)
        meta = json.load(io.open(os.path.join(mdir, "assets", "img", "_photo_meta.json"), encoding="utf-8"))
        check("... and what it shows is kept in its record", any(r.get("seen", "").startswith("Moss LNG") for r in meta.values()), meta)
        code, out = run("place", ph, "--module", "1", "--slide", "s05_2", "--file", pic, "--rights", "PROJECT_OWNED",
                        "--seen", "LPG carrier at sea, under way")
        check("... a different thing on the same slide is placed", code == 0, out)
        code, out = run("place", ph, "--module", "1", "--slide", "s05_3", "--file", pic, "--rights", "PROJECT_OWNED",
                        "--seen", "LPG carrier at sea, under way")
        check("... the same ship again on the same slide is refused", code == 2 and "shows the same as s05_2" in out, out)
        code, out = run("place", ph, "--module", "1", "--slide", "s05_3", "--file", pic, "--rights", "PROJECT_OWNED",
                        "--seen", "LPG carrier at sea in heavy weather, fully refrigerated, another hull")
        b = json.load(io.open(os.path.join(sd, "M01.build.json"), encoding="utf-8"))
        os.makedirs(os.path.join(ph, "course", "working_claude", "_build"), exist_ok=True)
        io.open(os.path.join(ph, "course", "working_claude", "_build", "M01_slots.json"), "w", encoding="utf-8").write(
            json.dumps({"1280x800": {"s01": [500, 520]}}))
        code, out = run("queue", ph, "--module", "1")
        q = {x["slide"]: x for x in json.load(io.open(os.path.join(ph, "course", "working_claude", "picture_briefs", "M01.gemini.json"),
                                                         encoding="utf-8"))}
        check("a picture is made in the shape of the box the build measured it in (a near-square column: 1:1, not 16:9)",
              q["s01"]["aspect"] == "1:1" and "1:1" in q["s01"]["prompt"], q.get("s01"))
        check("... and the slide whose items are queued is not queued as one picture too", "s05" not in q, sorted(q))
        check("... and once every tile is in, the slide holds no stand-in", code == 0 and "placeholder" not in b["screens"]["s05"]
              and not any("_placeholder_" in t for t in b["screens"]["s05"]["tiles"]), (out, b["screens"]["s05"]))

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
