# -*- coding: utf-8 -*-
"""test_old_course_kept - a course rebuilt from an old one keeps its order and its theory, and a task asks only what the
slides have shown.

    python test_old_course_kept.py

Pinned (GAS BASIC: the old course's order was good, the rebuilt module moved its airlock slides, kept 35 % of
its words and asked its first question before the slide that taught it):
  * a slide that comes from an earlier old slide than the one before it is a must-fix, unless "moved_why" gives the
    expert's reason; a step back of two slides (a slide that joins two old ones) is not;
  * an old slide that taught something (20 words or more) and no module cites is a must-fix, unless the script's
    "dropped_old" says why; another module citing it is enough;
  * the module's slides showing under 60 % of the words of the old slides they replace is a must-fix, under 80 % a note;
  * many slides from no old slide is a note; a course with no old course has none of these findings;
  * the room's own question (ask / reveal) whose answer no slide up to it shows is a must-fix;
  * a task's answer said only in the instructor's notes is not taught - the trainee never sees the notes.
"""
from __future__ import annotations

import copy
import io
import json
import os
import shutil
import sys
import tempfile

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import content_script as cs  # noqa: E402

PASS, FAIL = [], []
DECK = "1. Liquefied Gas tankers.pptx"
OLD_WORDS = "word " * 60


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print(("  ok    " if ok else "  FAIL  ") + name + (("  -> " + str(detail)[:700]) if detail and not ok else ""))


def slide(sid, text, old, **kw):
    s = {"id": sid, "kind": "slide", "title": "Slide %s" % sid, "text": text, "notes": "- Say it.", "minutes": 2,
         "from_old": "%s, %s - kept" % (DECK, old) if old else ""}
    s.update(kw)
    return s


def course_with(tmp, slides_of_old, scripts):
    c = os.path.join(tmp, "course")
    os.makedirs(os.path.join(c, "working_claude", "script"))
    inv = {"sections": [{"section": "1. Gas tankers", "files": [{"file": "1. Gas tankers/" + DECK, "slides": [
        {"n": n, "title": "Old %d" % n, "words": w} for n, w in slides_of_old]}]}]}
    io.open(os.path.join(c, "working_claude", "old_course_inventory.json"), "w", encoding="utf-8").write(json.dumps(inv))
    for m, sc in scripts.items():
        io.open(os.path.join(c, "working_claude", "script", "M%02d.json" % m), "w", encoding="utf-8").write(json.dumps(sc))
    return c


def rules(course, script):
    return [(f["rule"], f["level"], f["screen"]) for f in cs.old_course_findings(course, script)]


def main():
    tmp = tempfile.mkdtemp(prefix="oldkept_")
    try:
        long_ = " ".join(["the tank holds the cargo liquid under pressure"] * 12)
        base = {"module": 1, "operator_language": "en", "screens": [
            slide("s01", long_, "slides 1 and 2"), slide("s02", long_, "slide 3"), slide("s03", long_, "slides 4-5")]}
        c = course_with(tmp, [(1, 60), (2, 60), (3, 60), (4, 60), (5, 60), (6, 8)], {1: base})
        check("the old order kept, every old slide cited, as many words: nothing to say", rules(c, base) == [], rules(c, base))

        moved = copy.deepcopy(base)
        moved["screens"] = [moved["screens"][2], moved["screens"][0], moved["screens"][1]]
        check("a slide moved before its old place is a must-fix (GAS BASIC M01: the airlock slides moved)",
              ("o_moved", cs.FAIL, "s01") in rules(c, moved), rules(c, moved))
        moved["screens"][1]["moved_why"] = "The expert: airlocks after the ship types, agreed 2026-11-06."
        check("... unless moved_why gives the expert's reason", not [r for r in rules(c, moved) if r[0] == "o_moved"], rules(c, moved))
        joined = copy.deepcopy(base)
        joined["screens"][0]["from_old"] = "%s, slides 1 and 3 - joined" % DECK
        joined["screens"][1]["from_old"] = "%s, slide 2 - kept" % DECK
        check("... a step back of up to two slides (one slide joining two old ones) is not a move",
              not [r for r in rules(c, joined) if r[0] == "o_moved"], rules(c, joined))

        got = cs.old_refs("%s, slides 106 and 110-111 - kept; %s, slides 3, 5-6 and 8 and 10-12" % (DECK, DECK))
        check("a range after \"and\" keeps its end: \"slides 106 and 110-111\" is 106, 110 and 111",
              list(got.values()) == [[106, 110, 111, 3, 5, 6, 8, 10, 11, 12]], got)
        dropped = copy.deepcopy(base)
        dropped["screens"][2]["from_old"] = "%s, slide 5 - kept" % DECK
        check("an old slide that taught something and no module cites is a must-fix", ("o_dropped", cs.FAIL, "") in rules(c, dropped)
              and any("slide 4" in f["detail"] for f in cs.old_course_findings(c, dropped)), rules(c, dropped))
        _, work = cs.build_changes(dropped, [{"script_field": "dropped_old", "new": [{"from": "%s, slide 4" % DECK, "why": "Repeated on slide 5."}]}])
        check("... propose can list it in dropped_old, as the must-fix says", not [r for r in rules(c, work) if r[0] == "o_dropped"], rules(c, work))
        try:
            cs.build_changes(dropped, [{"script_field": "dropped_old", "new": [{"from": "slide 4"}]}])
            stopped = False
        except cs.Stop:
            stopped = True
        check("... and a dropped_old entry without its deck's slide or its why is refused", stopped)
        dropped["dropped_old"] = [{"from": "%s, slide 4" % DECK, "why": "Repeated on slide 5."}]
        check("... unless dropped_old says why", not [r for r in rules(c, dropped) if r[0] == "o_dropped"], rules(c, dropped))
        other = {"module": 2, "screens": [slide("s01", long_, "slide 4")]}
        c2 = course_with(os.path.join(tmp, "b"), [(1, 60), (2, 60), (3, 60), (4, 60), (5, 60)], {1: dropped, 2: other})
        del dropped["dropped_old"]
        check("... and another module citing it is enough", not [r for r in rules(c2, dropped) if r[0] == "o_dropped"], rules(c2, dropped))
        check("an old slide with only a few words (a divider) is never counted as dropped",
              not any("slide 6" in f["detail"] for f in cs.old_course_findings(c, base)))

        thin = copy.deepcopy(base)
        for s in thin["screens"]:
            s["text"] = "Pressure\nCold\nBoth"
        check("slides showing under 60 % of the old slides' words are a must-fix (GAS BASIC M01: 35 %)",
              ("o_thinner", cs.FAIL, "") in rules(c, thin), rules(c, thin))
        some = copy.deepcopy(base)
        for s in some["screens"]:
            s["text"] = " ".join(["the tank holds the cargo liquid under pressure"] * 8)
        check("... under 80 % a note", ("o_thinner", cs.NOTE, "") in rules(c, some), rules(c, some))

        fresh = copy.deepcopy(base)
        fresh["screens"] += [slide("s1%d" % i, long_, "") for i in range(3)]
        check("many slides from no old slide: a note, never a stop", ("o_new_share", cs.NOTE, "") in rules(c, fresh), rules(c, fresh))
        bare = os.path.join(tmp, "bare")
        os.makedirs(os.path.join(bare, "working_claude", "script"))
        check("a course with no old course: none of this", cs.old_course_findings(bare, moved) == [])
        check("... and every finding has its words in Latvian and Russian too",
              all(k in cs.LABELS[lang] for lang in ("lv", "ru") for k in ("o_moved", "o_dropped", "o_thinner", "o_new_share",
                                                                        "t_room_not_taught")))

        print("\n-- a question asks only what the slides have shown")
        sc = {"module": 1, "operator_language": "en", "screens": [
            slide("s01", "A fully pressurised ship carries LPG at ambient temperature in thick Type C tanks.", ""),
            slide("s02", "Both ships use pressure vessels.", "", ask="What does the semi-refrigerated ship gain by cooling?",
                  reveal="Lower vapour pressure: thinner lighter tanks, paid for with insulation and reliquefaction."),
            slide("s03", "A semi-refrigerated ship cools the cargo: lower vapour pressure, thinner lighter tanks, insulation, "
                         "reliquefaction plant.", "")]}
        got = [(f["rule"], f["screen"]) for f in cs.theory_check(sc)[0] if f["rule"] == "t_room_not_taught"]
        check("the room's question answered by a slide that comes after it is a must-fix (GAS BASIC M01 s05)", got == [("t_room_not_taught", "s02")], got)
        sc["screens"][1], sc["screens"][2] = sc["screens"][2], sc["screens"][1]
        got = [f for f in cs.theory_check(sc)[0] if f["rule"] == "t_room_not_taught"]
        check("... asked after the slide that teaches it, it is fine", not got, got)
        long_why = " ".join(["Type C tanks are pressure vessels and need no refrigeration plant at all."] * 6)
        tf = {"module": 1, "operator_language": "en", "screens": [
            slide("s01", "Type C tanks are pressure vessels.", ""),
            slide("s02", long_why, "", claim="A fully pressurised ship needs a reliquefaction plant.", claim_is="false"),
            slide("s03", "Short.", "", ask="Why?", reveal=long_why)]}
        got = sorted((f["screen"], f["field"]) for f in cs.theory_check(tf)[0] if f["rule"] == "t_long_answer")
        check("a true-or-false why or a revealed answer past 70 words is theory hidden in a reveal - a warning (the factory "
              "trial: M01 s04, 82 words, cut)", got == [("s02", "text"), ("s03", "reveal")]
              and not [f for f in cs.theory_check(tf)[0] if f["rule"] == "t_long_answer" and f["level"] == cs.FAIL], got)
        check("... and its words are in Latvian and Russian too", cs.LABELS["lv"].get("t_long_answer") and cs.LABELS["ru"].get("t_long_answer"))
        print("\n-- a slide with a picture holds what the tablet shows")
        B = cs.LAYOUT_RULES["budgets"]
        pic = {"kind": "photo", "aspect": "4:3", "shows": "a gas detector"}
        sit = " ".join(["the tank was gas-freed and ventilated"] * 10)
        scen = {"module": 1, "operator_language": "en", "screens": [
            slide("s01", sit, "", picture=pic, ask="Which instrument first?", choices="Oxygen\nFlammable\nToxic",
                  why="Right.\nNo.\nNo.", right="A")]}
        got = [(f["screen"], f["rule"], f["level"]) for f in cs.theory_check(scen)[0] if f["rule"] == "t_overfull"]
        f = [x for x in cs.theory_check(scen)[0] if x["rule"] == "t_overfull"]
        check("a scenario's situation past %d words beside its picture is a must-fix at script time, with its template's real "
              "budget (the factory trial: every scenario beside a picture was cut on the tablet)" % B["scenario_situation"],
              got == [("s01", "t_overfull", cs.FAIL)] and "scenario (What would you do?), holds %d" % B["scenario_situation"]
              in f[0]["detail"], got + [x["detail"] for x in f])
        check("... it names the fix: split into two slides", f and f[0]["fix"].startswith("split into two slides"), f)
        check("... the template is the compiler's own choice (content_script.shaped_kind, read by compile_module.shaped_template)",
              cs.shaped_kind(scen["screens"][0]) == "scenario")
        scen["screens"][0]["why"] = "\n".join([" ".join(["because the oxygen reading comes first"] * 6)] * 3)
        got = sorted(f["detail"].split(" has ")[0] for f in cs.theory_check(scen)[0] if f["rule"] == "t_overfull")
        check("... and its question, choices and whys past %d in the other column - each part said on its own" % B["scenario_choices"],
              got == sorted([cs.T(scen, "t_part_situation"), cs.T(scen, "t_part_choices")]), got)
        claim = {"module": 1, "operator_language": "en", "screens": [
            slide("s01", sit, "", picture=pic, claim="Oxygen is measured first.", claim_is="true", ask="Why?", reveal="Right.")]}
        check("... a true-or-false is built in its own template (compile_module.shaped_template): not measured as a worked example",
              not [f for f in cs.theory_check(claim)[0] if f["rule"] == "t_overfull"])
        scen["screens"][0]["picture"] = {"kind": "none"}
        check("... without a picture the whole slide is its room: not checked",
              not [f for f in cs.theory_check(scen)[0] if f["rule"] == "t_overfull"])
        work = {"module": 1, "operator_language": "en", "screens": [
            slide("s01", " ".join(["open the valve slowly and watch the gauge"] * 12), "", picture=pic, ask="What next?",
                  reveal="Close it.")]}
        got = [f["detail"] for f in cs.theory_check(work)[0] if f["rule"] == "t_overfull"]
        check("a worked example's steps and question past %d words beside its picture too" % B["worked_steps"], len(got) == 1, got)
        short = {"module": 1, "operator_language": "en", "screens": [
            slide("s01", "Tank 2 carried ammonia. It is gas-freed. Two crew will enter it.", "", picture=pic,
                  ask="Which instruments do you use before the entry, and in which order?",
                  choices="The oxygen analyser, then the flammable gas detector, then ammonia tubes\nThe personal monitors only",
                  why="Right: oxygen first, then flammable vapour, then the toxic cargo.\nThey are for the people inside.", right="A")]}
        rules_ = [f["rule"] for f in cs.theory_check(short)[0]]
        check("a scenario trimmed to fit is not thin: its question, choices and whys count toward the slide's %d words "
              "(the factory trial: trimming fought the floor)" % cs.RULES["slide"]["min_words"],
              "t_thin_slide" not in rules_ and "t_overfull" not in rules_, rules_)
        check("the words on screen: the points of a slide of short points, never its notes",
              "insulation" in cs.shown_text({"title": "T", "text": "long words", "points": "insulation", "notes": "secret"})
              and "secret" not in cs.shown_text({"title": "T", "text": "x", "notes": "secret"})
              and "long words" not in cs.shown_text({"title": "T", "text": "long words", "points": "insulation"}))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("\n%d passed, %d failed" % (len(PASS), len(FAIL)))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
