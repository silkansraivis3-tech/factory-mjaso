# -*- coding: utf-8 -*-
"""test_activity_formats - varied practical-activity formats, chosen while a module is written (L68, 2.128.0).

    python test_activity_formats.py

Pinned:
  * the catalogue: every format names a TLA of the guideline's pool exactly, every TLA of the pool has one format, every
    activity that needs a practical has its roles and what the debrief observes, the core formats and the slide techniques
    are formats of the right kind, and no format is in a language other than English;
  * the task type from a Sub-ILO's verb: the earliest verb decides, a text with none is a decision, the register comes first;
  * picking: a real-time outcome gets the scenario run first, a hands-on one the demonstration, a team one a team drill with
    observers and a trainee-led debrief, a written plan only where the outcome says prepare / plan / draft / write, the
    experienced-only ones only for an experienced course - and Sub-ILOs of one module are not all given the same TLA;
  * a written screen's format: the activity's "format", else its sign words (the longest wins), else 'exercise'; an active
    slide by its technique, a claim or a drill by its field;
  * the practical's cycle: brief 3-5, a show of about a tenth, the runs, a debrief of 15-20 for a team and 5-10 alone - the
    rows add up to the screen's minutes for every length from 25 to 240 min, and a team drill too short for its debrief is
    said, never silently squeezed;
  * the practical's cards: from the screen's own words first, the format's catalogue entry and the Sub-ILOs next; no safety
    drafted for a simulator or real equipment.
"""
from __future__ import annotations

import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import activity_formats as af  # noqa: E402
import content_script as cs  # noqa: E402

PASS, FAIL = [], []


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print(("  ok    " if ok else "  FAIL  ") + name + (("  -> " + str(detail)[:700]) if detail and not ok else ""))


def total(rows):
    return round(sum(float(r["min"]) for r in rows), 6)


def main():
    print("-- the catalogue")
    pool = {t["tla"] for k, v in af.KNOW["tla_pool"].items() if not k.startswith("_") for t in v}
    named = [f["tla"] for f in af.F["pool"].values()]
    check("every format names a TLA of the pool, and every TLA of the pool has exactly one format",
          set(named) == pool and len(named) == len(set(named)) == 28, sorted(pool ^ set(named)))
    need = [k for k, f in af.FORMATS.items() if f.get("practical")]
    check("every activity that needs a practical has its roles and what its debrief observes",
          need and all(af.FORMATS[k]["drafts"] == "activity" and af.FORMATS[k].get("roles") and af.FORMATS[k].get("observe") for k in need),
          [k for k in need if not af.FORMATS[k].get("roles")])
    check("the drafts kinds are slide, activity, task or feature, and every format says how it is written",
          all(f["drafts"] in ("slide", "activity", "task", "feature") and f.get("write") for f in af.FORMATS.values()))
    check("the core format of each task type is an activity of that task type",
          all(af.FORMATS[v]["task_type"] == k and af.FORMATS[v]["drafts"] == "activity"
              for k, v in af.F["core"].items() if not k.startswith("_")))
    check("every slide technique of the script (theory-rules active_techniques) is read as a format",
          set(cs.ACTIVE) <= set(k for k in af.F["slide_active"] if not k.startswith("_")), (cs.ACTIVE, af.F["slide_active"]))
    check("a team feature (observers, trainee-led debrief) is only ever brought by a team format",
          all(x in af.FORMATS and af.FORMATS[x]["drafts"] == "feature" and f.get("team")
              for f in af.FORMATS.values() for x in f.get("features") or []))
    text = repr(af.F)
    check("the catalogue is in English only (no Latvian or Cyrillic letters)", not re.search(r"[āčēģīķļņšūžĀČĒĢĪĶĻŅŠŪŽа-яА-Я]", text))

    print("\n-- the task type from the verb")
    cases = {"Decides whether a tank may be entered": "decision", "Bump-tests a portable detector": "fixed_sequence",
             "Dons and doffs the SCBA set": "fixed_sequence", "Responds to a gas alarm during cargo transfer": "real_time_judgement",
             "Communicates helm orders with closed-loop readback": "team_behaviour",
             "Writes a pre-transfer brief": "decision", "Understand the gas detector": "decision",
             "Re-plans the project after a change event": "real_time_judgement",
             "Presents and defends the project to the board": "team_behaviour"}
    got = {t: af.verb_type(t)[0] for t in cases}
    check("the earliest verb decides ('writes a ... brief' is a decision, not team), no verb is a decision", got == cases,
          {t: (got[t], cases[t]) for t in cases if got[t] != cases[t]})
    check("the register's task type comes first, and says so",
          af.task_type_of("1.a", "Responds to a gas alarm", {"1.a": {"task_type": "team_behaviour"}}) == ("team_behaviour", "register")
          and af.task_type_of("1.a", "Responds to a gas alarm", {})[1] == "verb 'responds'")

    print("\n-- picking")
    check("a real-time outcome gets the scenario run with planned events first", af.pick("real_time_judgement", 3)[0] == "scenario-run",
          af.pick("real_time_judgement", 3))
    check("a hands-on outcome gets the demonstration (Peyton four-step) first", af.pick("fixed_sequence", 3)[0] == "demonstration")
    team = af.pick("team_behaviour", 3)
    check("a team outcome gets a team drill with observers and a trainee-led debrief",
          team[0] == "closed-loop" and "observer-role" in team and "trainee-debrief" in team, team)
    dec = af.pick("decision", 5)
    check("a decision outcome at Evaluate gets a case dilemma, and a second TLA of another kind",
          dec[0] == "case-dilemma" and af.FORMATS[dec[1]]["drafts"] != "slide", dec)
    check("'write the plan' only where the outcome says prepare, plan, draft or write - and first there",
          "write-plan" not in af.pick("decision", 6, "Decides on the repair") and af.pick("decision", 3, "Prepares the voyage plan")[0] == "write-plan")
    check("teach-back and design-the-next-scenario only on an experienced course",
          not any(k in af.pick(tt, lv, used={}) for tt in af.TASK_TYPES for lv in range(1, 7) for k in ("teach-back", "design-scenario"))
          and "design-scenario" in af.pick("real_time_judgement", 6, experienced=True, used={"scenario-run": 3})
          and "teach-back" in af.pick("decision", 2, experienced=True, used={k: 3 for k in ("explain-why", "predict-reveal", "refutation", "contrast-pair")}))
    rows = [{"sub_ilo_id": "1.%d" % i, "sub_ilo": t} for i, t in enumerate(
        ["Identifies the hazards of a cargo", "Checks the entry permit", "Selects the detector", "Responds to a gas alarm",
         "Responds to a fire alarm", "Bump-tests a detector", "Communicates with the bridge"])]
    p = af.plan(rows)
    firsts = [x["picks"][0] for x in p]
    check("in one module the Sub-ILOs are not all given the same TLA: four decisions get at least three first picks, two "
          "real-time outcomes two different ones", len(set(firsts[:3])) >= 2 and firsts[3] != firsts[4]
          and len({f for x in p for f in x["picks"] if af.FORMATS[f]["drafts"] == "activity"}) >= 4, [(x["sid"], x["picks"]) for x in p])

    print("\n-- a written screen's format")
    a = lambda **kw: dict({"id": "a01", "kind": "activity", "title": "Exercise", "text": "Work."}, **kw)
    check("an activity's own \"format\" first", af.format_of(a(format="planted-defect")) == "planted-defect")
    check("else its sign words - the longest wins ('closed-loop' over a general 'drill')",
          af.format_of(a(title="Closed-loop team drill at the console")) == "closed-loop"
          and af.format_of(a(text="Your own project, in the template.")) == "write-plan")
    check("else 'exercise' - an exercise of no named format", af.format_of(a()) == "exercise")
    sl = lambda **kw: dict({"id": "s01", "kind": "slide", "text": "x"}, **kw)
    check("a slide: its technique, a claim (refutation) or a drill (retrieval round); a plain slide or the recap is none",
          [af.format_of(sl(active="scenario")), af.format_of(sl(claim="LNG burns.")), af.format_of(sl(drill="quick-fire")),
           af.format_of(sl()), af.format_of(sl(active="scenario", recap=True))] == ["case-dilemma", "refutation", "retrieval-round", None, None])

    print("\n-- the practical's cycle")
    bad = []
    for m in range(25, 241, 5):
        for team in (False, True):
            if team and m < 30:
                continue
            rows_, warn = af.cycle(m, team=team, runs=True)
            b = sum(r["min"] for r in rows_ if r["kind"] == "brief")
            d = sum(r["min"] for r in rows_ if r["kind"] == "debrief")
            lo, hi = (15, 20) if team else (5, 10)
            if total(rows_) != m or not 3 <= b <= 5 or not lo <= d <= hi or warn or not any(r["kind"] == "show" for r in rows_):
                bad.append((m, team, rows_, warn))
    check("from 25 to 240 min, team or alone: the rows add up to the minutes, brief 3-5, debrief 15-20 / 5-10, a show row",
          not bad, bad[:2])
    r, _ = af.cycle(60, team=True, runs=True, events=["Gas alarm at 10 min", "Pump trip at 20 min"])
    check("a repeated format is two practice runs; a team's runs swap the observers; the planned events are on run 1",
          [x["kind"] for x in r].count("run") == 2 and "teams swap" in r[3]["what"] and "Gas alarm" in r[2]["what"]
          and "trainee-led" in r[-1]["what"], r)
    check("an experienced group gets a diagnostic row instead of the show",
          af.cycle(60, diagnostic=True)[0][1]["kind"] == "diagnostic")
    r, w = af.cycle(20, team=True)
    check("a team drill of 20 min is too short for its 15-min debrief - said, never squeezed", w and "at least" in w, (r, w))
    check("odd minutes stay exact: 22.5 min adds up", total(af.cycle(22.5, runs=True)[0]) == 22.5)

    print("\n-- the practical's cards")
    s = {"id": "a03", "kind": "activity", "title": "Helm orders", "minutes": 45, "format": "closed-loop"}
    e, w = af.practical(s, "closed-loop", "room", ["Communicates helm orders with closed-loop readback"])
    check("a closed-loop drill: a team practical, its catalogue roles, a room's safety lines, two must-observe items from the "
          "format and the Sub-ILO, an objective from the Sub-ILO",
          e["team"] and "reads back" in e["prebrief"]["roles"] and e["prebrief"]["safety"] and e["prebrief"]["stop_word"] == "STOP"
          and 2 <= len(e["debrief"]["must_observe"]) <= 3 and e["prebrief"]["objective"].startswith("By the end, each trainee communicates")
          and total(e["cycle"]) == 45 and not w, (e, w))
    own = dict(s, roles="Our own roles.", observe="Says the order back\nWaits for 'correct'", safety="Mind the cables")
    e, _ = af.practical(own, "closed-loop", "room", ["x"])
    check("the screen's own words come first: roles, what to observe, safety",
          e["prebrief"]["roles"] == "Our own roles." and e["debrief"]["must_observe"] == ["Says the order back", "Waits for 'correct'"]
          and e["prebrief"]["safety"] == ["Mind the cables"], e)
    e, w = af.practical({"id": "a04", "kind": "activity", "title": "Gas detection", "minutes": 40}, "exercise", "equipment", [])
    check("no safety is drafted for real equipment - it is asked for", e["prebrief"]["safety"] == [] and any("safety" in x for x in w), w)
    check("a case or a map needs no practical; a project block, a drill and any simulator exercise do",
          not af.needs_practical("hazard-map", "room") and af.needs_practical("write-plan", "room")
          and af.needs_practical("closed-loop", "room") and af.needs_practical("hazard-map", "simulator"))

    print("\n%d passed, %d failed" % (len(PASS), len(FAIL)))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
