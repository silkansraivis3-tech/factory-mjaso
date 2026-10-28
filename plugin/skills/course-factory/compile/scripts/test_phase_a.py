# -*- coding: utf-8 -*-
"""test_phase_a - a module builds with no agent: Phase A placeholders, the needs file, the course photo catalogue and --auto
(2.73.0).

    python test_phase_a.py

Pinned:
  * --init-build leaves no blank: a photo slot holds a placeholder of its shape (1600 px on its long side, marked in the file
    itself), a question answered on a picture holds one with a box per answer; the pre-check and the starter-blanks check pass;
  * a sheet from before 2.73.0 gets the same with --fill-slots;
  * the needs file names each slot's kind, shape, what it must show and the words it teaches; the compiled deck marks the
    placeholder (data-slot) so the audits measure its real size, and run_audits --slots writes it;
  * a placeholder never ships: build_module.py counts it as a slot still to fill (never PASS), check_course_package.py refuses
    it, and the package check's placeholder lines are only the build's state in Phase A (every other finding still fails);
  * the photo catalogue indexes the old course's and the knowledge base's pictures once (the same bytes in both are one), puts
    each picture on one slot of the whole course (L58), and a slot the sourcing pass found a photo for takes it first;
  * --auto fills a slide's slot from its pick - the picture, its record (rights, origin, what it shows), the sheet marked
    "auto_picked", the placeholder gone - and never a question's picture.
"""
from __future__ import annotations

import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import test_compile_module as tcm  # noqa: E402
import content_script as cs  # noqa: E402
import gate_fixture  # noqa: E402
import placeholder  # noqa: E402
import build_module as bm  # noqa: E402
import compile_module as cm  # noqa: E402

SKILLS = tcm.SKILLS
PKG = os.path.join(SKILLS, "course-factory", "scripts", "check_course_package.py")
AUDITS = os.path.join(SKILLS, "course-module-ux", "measure", "scripts", "run_audits.py")
FAILS = []
HOTSPOT = {"id": "q02", "kind": "self-check", "set": "SC1", "mechanic": "hotspot", "question": "Tap the vent mast.",
           "visual": "the ship", "answer": "Vent mast*\nFuel tank\nFunnel", "feedback": "High above the deck."}


def check(name, ok, detail=""):
    if not ok:
        FAILS.append(name)
    print(("  ok    " if ok else "  FAIL  ") + name + (("  -> " + str(detail)[:700]) if detail and not ok else ""))


def photo(path, w=1200, h=900, shade=90):
    """a real (non-placeholder) picture - None when there is no imaging package"""
    try:
        from PIL import Image
    except ImportError:
        return None
    os.makedirs(os.path.dirname(path), exist_ok=True)
    im = Image.new("RGB", (w, h), (shade, 120, 160))
    for x in range(0, w, 40):
        for y in range(h):
            im.putpixel((x, y), (250, 250, 250))
    im.save(path)
    return path


def pptx(path, slides):
    """a deck with these slide words: {3: "Deepwell pump on deck"}"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with zipfile.ZipFile(path, "w") as z:
        for n, words in slides.items():
            z.writestr("ppt/slides/slide%d.xml" % n,
                       '<p:sld xmlns:p="p" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><a:t>%s</a:t></p:sld>' % words)


def main():
    tmp = tempfile.mkdtemp(prefix="phase_a_")
    try:
        sc = tcm.script(screens=tcm.SCREENS[:6] + [HOTSPOT] + tcm.SCREENS[6:])
        for s in sc["screens"]:
            if s["id"] == "s01":
                s["picture"] = {"kind": "photo", "aspect": "16:9", "shows": "A gas-fuelled ship bunkering LNG alongside"}
        sc.update(status="approved", approved_hash=cs.content_hash(sc))
        c, md = tcm.new_course(tmp, sc, build=False)
        gate_fixture.open_gate(c)
        code, out = tcm.run(tcm.COMPILE, c, "--module", "1", "--init-build")
        sheet = cs.load(os.path.join(c, "working_claude", "script", "M01.build.json"))
        s01, q02 = sheet["screens"]["s01"], sheet["screens"].get("q02") or {}
        ph = os.path.join(md, "assets", "img", "_placeholder_s01.png")
        check("--init-build: the photo slot holds a placeholder of its shape (16:9 at 1600 px), marked in the file itself",
              code == 0 and s01["figure"] == "assets/img/_placeholder_s01.png" and placeholder.is_placeholder(ph)
              and placeholder.size_of("16:9") == (1600, 900), (code, s01, out))
        check("... a question answered on a picture holds one with a box per answer (moved onto its thing in Phase B)",
              q02.get("figure") == "assets/img/_placeholder_q02.png" and sorted(q02.get("areas") or {}) == ["Fuel tank", "Funnel", "Vent mast"]
              and all(len(v) == 4 and 0 <= v[0] < 100 and 0 <= v[1] < 100 for v in q02["areas"].values()), q02)
        check("... no blank is left: the starter-blanks check finds nothing to fill", bm.starter_blanks(c, 1) == [], bm.starter_blanks(c, 1))
        check("... the sheet says its deck is Phase A's, so Phase B's builds are no 'rebuild' that lets new photographs under "
              "800 px through as pictures the module already had (bench M11, 2.73.0)", sheet.get("phase_a") is True)
        import precheck
        must, _ = precheck.check(c, 1)
        check("... and the pre-check names no placeholder (1600 px, a real file)", not [x for x in must if "placeholder" in x], must)
        meta = json.load(io.open(os.path.join(md, "assets", "img", "_photo_meta.json"), encoding="utf-8"))
        check("... its record says it is a placeholder - never a photo for a drawing's photo row (L57) or a duplicate (L58)",
              placeholder.is_record(meta.get("_placeholder_s01.png")) and not cm.rights_usable(meta["_placeholder_s01.png"]))
        check("build_module counts both as slots still to fill - and the 3D starter scene whose parts are not placed (s04) - "
              "the module is never PASS while they are there",
              [x[0] for x in bm.phase_a_slots(c, 1)] == ["q02", "s01", "s04"], bm.phase_a_slots(c, 1))
        needs = json.load(io.open(os.path.join(c, "working_claude", "visuals", "M01_VISUAL_NEEDS.json"), encoding="utf-8"))
        row = next((r for r in needs["slots"] if r["id"] == "s01"), {})
        check("the needs file: each slot's kind, shape, what it must show and the words it teaches",
              row.get("kind") == "photo" and row.get("aspect") == "16:9" and "bunkering" in row.get("shows", "")
              and "Some ships burn gas as fuel." in row.get("words", "")
              and os.path.isfile(os.path.join(c, "working_claude", "visuals", "M01_VISUAL_NEEDS.md")), row)
        check("... a question's row lists the answers placed on it", next((r for r in needs["slots"] if r["id"] == "q02"), {})
              .get("answers_on_it") == ["Fuel tank", "Funnel", "Vent mast"], needs["slots"])

        # a sheet from before 2.73.0
        old = cs.load(os.path.join(c, "working_claude", "script", "M01.build.json"))
        old["screens"]["s01"] = {"figure": "", "visual_kind": "photo"}
        cs.save(os.path.join(c, "working_claude", "script", "M01.build.json"), old)
        check("a sheet from before 2.73.0 still stops the build on its blank", [x[0] for x in bm.starter_blanks(c, 1)] == [["s01"]])
        code, out = tcm.run(tcm.COMPILE, c, "--module", "1", "--fill-slots")
        check("... --fill-slots gives it the placeholder, and the blank is gone",
              code == 0 and bm.starter_blanks(c, 1) == [] and "s01 (photo slot 16:9)" in out, out)

        # the compiled deck marks the slot; the audits measure it
        code, out = tcm.run(tcm.COMPILE, c, "--module", "1")
        page = tcm.deck(md)
        check("the compiled deck marks the placeholder's <img> data-slot, so the audits measure its real size",
              'data-slot="s01"' in tcm.section(page, "s01") and page.count("data-slot=") == 1, tcm.section(page, "s01")[:600])
        import drawing_check
        if drawing_check.find_browser():
            slots = os.path.join(tmp, "slots.json")
            p = subprocess.run([sys.executable, AUDITS, os.path.join(md, "presentation", "index.html"), "--quiet", "--viewport",
                                "1024x768", "--slots", slots], capture_output=True, text=True, encoding="utf-8", errors="replace")
            got = json.load(io.open(slots, encoding="utf-8")) if os.path.isfile(slots) else {}
            w1, w2 = (got.get("1280x800") or {}).get("s01"), (got.get("1024x768") or {}).get("s01")
            check("run_audits --slots: the slot's px size at each screen size (smaller at 1024 x 768)",
                  w1 and w2 and w1[0] > w2[0] > 100 and w1[1] > 50, (got, p.stdout[-400:]))
        else:
            print("SKIP the audit part - no Chrome or Edge")

        # a placeholder never ships
        p = subprocess.run([sys.executable, PKG, os.path.join(c, "modules")], capture_output=True, text=True, encoding="utf-8",
                           errors="replace")
        check("check_course_package refuses a module that still has a placeholder", p.returncode != 0
              and "_placeholder_s01.png is a Phase A placeholder" in p.stdout, p.stdout[-800:])
        only = ("Course folder: x\n\n2 thing(s) to fix before it goes into the classroom:\n"
                "  - module01/assets/img/_placeholder_s01.png is a Phase A placeholder, not a picture - fill its slot\n"
                "  - module01/assets/img/_placeholder_q02.png is a Phase A placeholder, not a picture - fill its slot\n")
        check("in Phase A the package check's placeholder lines are the build's state, not a finding ...",
              bm.without_placeholders(1, only)[0] == 0)
        check("... every other finding still fails it",
              bm.without_placeholders(1, only + "  - module01/tasks/sc1_a.html has no <title>\n")[0] == 1)

        # the course photo catalogue
        import photo_catalogue as pc
        work = c
        oci = os.path.join(work, "working_claude", "old_course_images", "4. Ship", "deck")
        big = photo(os.path.join(oci, "slide03_image1.jpg"), 1600, 1000)
        if not big:
            print("SKIP the catalogue part - no imaging package (PIL)")
        else:
            photo(os.path.join(oci, "slide05_image2.jpg"), 1600, 1000, shade=30)
            photo(os.path.join(oci, "slide07_image3.jpg"), 200, 150)                            # an icon
            root = os.path.join(tmp, "old")
            pptx(os.path.join(root, "1. Gas ships", "1. deck.pptx"), {3: "LNG bunkering alongside a gas-fuelled ship at the quay",
                                                                      5: "Engine room with a dual fuel engine", 7: "logo"})
            rows = [{"deck": "1. Gas ships/1. deck.pptx", "slide": n, "file": "working_claude/old_course_images/4. Ship/deck/%s" % f,
                     "rights": "OWNER_CLEARED - old course"} for n, f in ((3, "slide03_image1.jpg"), (5, "slide05_image2.jpg"),
                                                                          (7, "slide07_image3.jpg"))]
            cs.save(os.path.join(work, "working_claude", "old_course_images", "_index.json"), rows)
            cs.save(os.path.join(work, "working_claude", "old_course_inventory.json"), {"old_course": root})
            kb = os.path.join(tmp, "KB")
            src = os.path.join(kb, "sources", "doc1")
            os.makedirs(os.path.join(src, "images"))
            shutil.copyfile(big, os.path.join(src, "images", "image_0001.jpg"))       # the same picture as the old course's
            io.open(os.path.join(kb, "SOURCE_MANIFEST.json"), "w").write('{"sources": []}')
            cs.save(os.path.join(src, "metadata.json"), {"title": "Bunkering guide", "images": [
                {"file": "image_0001.jpg", "width": 1600, "height": 1000, "caption": "LNG bunkering", "location": {"kind": "page", "number": 2}}]})
            intake = cs.load(os.path.join(work, "working_claude", "intake.json"))
            intake["knowledge_base_decision"] = {"answer": "yes", "path": kb, "decided": "2026-10-27", "format": "course_source_processor"}
            cs.save(os.path.join(work, "working_claude", "intake.json"), intake)
            p_, cat = pc.index(work)
            check("the catalogue: the old course's pictures with their slide's words, the icon left out, and the same bytes in "
                  "the knowledge base indexed once", len(cat["photos"]) == 2 and cat["left_out_small"] == 1
                  and "bunkering alongside" in cat["photos"][0]["description"], [(x["source"], x["description"]) for x in cat["photos"]])
            sc2 = cs.load(os.path.join(work, "working_claude", "script", "M01.json"))
            twin = dict(next(s for s in sc2["screens"] if s["id"] == "s01"), id="s09", title="Bunkering again")
            sc2["screens"].insert(1, twin)
            cs.save(os.path.join(work, "working_claude", "script", "M02.json"), dict(sc2, module=2))
            _, plan, _ = pc.assign(work)
            picks = [r["pick"]["id"] for r in plan["slots"].values() if r["pick"]]
            check("assign: every slot gets its candidates; a picture two slots want is picked for one of them only (L58)",
                  len(plan["slots"]) >= 3 and len(picks) == len(set(picks)) and picks.count(cat["photos"][0]["id"]) == 1,
                  plan["slots"])
            found = os.path.join(work, "working_claude", "photos_found", "M02")
            photo(os.path.join(found, "found_s09.jpg"), 1800, 1200, shade=200)
            cs.save(os.path.join(found, "_photo_meta.json"), {"found_s09.jpg": {"title": "Truck-to-ship LNG bunkering",
                     "shows": "bunkering", "source": "Wikimedia Commons", "author": "X", "license": "CC BY 4.0",
                     "url_or_origin": "https://commons.example/x.jpg", "rights_state": "CLEARED", "found_for": "M02 s09"}})
            pc.index(work)
            _, plan, _ = pc.assign(work)
            r9 = plan["slots"]["M02 s09"]
            cat2 = pc.load(work, pc.CATALOGUE)
            check("a photo the sourcing pass found for a slot is that slot's pick",
                  r9["pick"] and next(x for x in cat2["photos"] if x["id"] == r9["pick"]["id"])["source"] == "found", r9)

            # --auto
            import visual_needs
            done = visual_needs.fill(c, 1)
            sheet = cs.load(os.path.join(c, "working_claude", "script", "M01.build.json"))
            e = sheet["screens"]["s01"]
            meta = json.load(io.open(os.path.join(md, "assets", "img", "_photo_meta.json"), encoding="utf-8"))
            rec = meta.get(os.path.basename(e["figure"])) or {}
            check("--auto: the slide's slot takes its pick - copied into the module with its record (rights, origin, what it "
                  "shows), marked auto_picked; the placeholder and its record gone",
                  [x[0] for x in done] == ["s01"] and e["figure"].startswith("assets/img/m01_s01_") and e.get("auto_picked")
                  and "placeholder" not in e and rec.get("auto_picked") is True and rec.get("rights_state") and rec.get("url_or_origin")
                  and rec.get("shows") and not os.path.isfile(ph) and "_placeholder_s01.png" not in meta, (done, e, rec))
            check("... a question's picture is never filled with no agent (its answers' places need the real things)",
                  sheet["screens"]["q02"]["figure"] == "assets/img/_placeholder_q02.png")
            needs = io.open(os.path.join(c, "working_claude", "visuals", "M01_VISUAL_NEEDS.md"), encoding="utf-8").read()
            check("... and the needs file lists the auto pick for the visual review", "Picked with no agent" in needs and "s01" in needs)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("\n%s" % ("ALL PASS" if not FAILS else "%d FAILED" % len(FAILS)))
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
