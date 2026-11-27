"""Tests for module_skeleton.py - a module's structure made by code before its script is written, so the writer only
writes words. Run: python test_module_skeleton.py"""
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bloom_map  # noqa: E402
import content_script as cs  # noqa: E402
import module_skeleton as ms  # noqa: E402

FAILS = []
STRUCTURE = ("t_sc_small", "t_sc_mix", "t_mc_small", "m_mix", "m_too_much_choice", "m_no_hands_on", "t_overfull",
             "a_one_direction", "a_type_unserved", "i_not_taught", "i_not_checked", "i_not_practised", "i_q_no_sub",
             "i_unknown_sub", "p_kind", "p_kind_differs", "p_aspect", "v_no_kind", "r_recap_place", "r_recap_missing")


def check(name, ok, detail=""):
    print("  %s  %s%s" % ("ok  " if ok else "FAIL", name, "" if ok else "  -> %s" % (detail,)))
    if not ok:
        FAILS.append(name)


def course(tmp, name, subs, theory, practical, hour=45, module=3):
    c = os.path.join(tmp, name)
    wc = os.path.join(c, "working_claude")
    os.makedirs(os.path.join(wc, "script"))
    cs.save(os.path.join(wc, "architecture.json"), {"course": {"title": name, "course_language": "English"},
                                                   "modules": [{"module": module}]})
    cs.save(os.path.join(wc, "programme.json"), {"academic_hour_min": hour, "topics": {
        str(module): {"title": "Module %d" % module, "theory": theory, "practical": practical}}})
    cs.save(os.path.join(wc, "ilo_map.json"), {"rows": [{"module": "M%02d" % module, "main_ilo_ids": [str(module)],
                                                        "sub_ilo_id": i, "sub_ilo": t} for i, t in subs]})
    return c


def words(n, seed):
    return " ".join("%s%d" % (seed, k) for k in range(n))


def fill(script):
    """every empty word field written to the skeleton's own targets, the way a writer would: the numbers in "to_write\""""
    out = json.loads(json.dumps(script))
    out["sources"] = ["A source, 2024 edition: 1-9"]
    for s in out["screens"]:
        hint = s.get("to_write", "")
        nums = [int(x) for x in re.findall(r"about (\d+) words", hint)]
        sid = s["id"]
        for f in ("title",):
            if f in s and not s[f]:
                s[f] = "Title of %s" % sid
        if s["kind"] == "slide" and s.get("recap"):
            s["text"] = "\n".join("Point %d - %s" % (i, words(8, "r%d_" % i)) for i in range(3))
            s["asks"] = "\n".join("Question %d?" % i for i in range(3))
            s["notes"] = "Say: " + words(30, "n")
        elif s["kind"] == "slide":
            text_n, notes_n = (nums + [40, 60])[:2] if not s.get("active") and "claim" not in s else (40, nums[0] if nums else 60)
            s["text"] = "\n".join(words(10, "%s_%d_" % (sid, i)) for i in range(max(1, text_n // 10)))
            if "points" in s:
                s["points"] = "Point one\nPoint two"
            s["notes"] = "Say: " + words(notes_n - 1, sid + "n")
            if "visual" in s and s.get("visual_kind") != "none":
                s["visual"] = "A picture of %s" % sid
                s["picture"]["shows"] = "what %s teaches" % sid
            for f in ("ask", "reveal"):
                if f in s:
                    s[f] = "%s of %s" % (f, sid)
            if "choices" in s:
                s.update(choices="Go\nNo-go", why="Wrong\nRight", right="B")
            if "claim" in s:
                s["claim"] = "A wrong belief"
        elif s["kind"] in ("task-slide", "activity"):
            s["text"] = "A task starts now about " + sid
            s["notes"] = "Say: " + words(25, sid + "n")
            for f in ("before",):
                if f in s:
                    s[f] = "One thing\nAnother thing"
            for f in ("roles", "safety", "observe", "events"):
                if f in s:
                    s[f] = "%s of %s" % (f, sid)
        else:
            s.update(question="Question %s?" % sid, feedback="Feedback.", brief="Brief.")
            if "options" in s:
                s.update(options=["Alpha", "Beta", "Gamma"], correct="A")
            if "answer" in s:
                s["answer"] = "x*"
            if "values" in s:
                s["values"] = "R, A, C"
            if "visual" in s:
                s["visual"] = "A picture"
                s["picture"]["shows"] = "a thing"
    return out


def quiet(fn, *a):
    buf = io.StringIO()
    with redirect_stdout(buf):
        r = fn(*a)
    return r, buf.getvalue()


def main():
    tmp = tempfile.mkdtemp(prefix="module_skeleton_")
    try:
        print("-- four task types in one module (theory 2 h, practical 2 h)")
        subs = [("3.1", "Decides whether the hot work permit may be signed"), ("3.2", "Responds to a fire alarm during bunkering"),
                ("3.3", "Communicates the fire-team orders with closed-loop readback"), ("3.4", "Rigs a fire hose and tests the nozzle")]
        c = course(tmp, "fire", subs, 2, 2)
        sk = ms.build(c, 3)
        sc = sk["screens"]
        kinds = [s["kind"] for s in sc]
        inst = [s for s in sc if s["kind"] in cs.INSTRUCTOR]
        check("the minutes add up exactly to the programme's (2 h + 2 h of 45 min)", sk["minutes_allocated"] == 180
              and sum(cs.minutes(s) for s in inst) == 180)
        doing = sum(cs.minutes(s) for s in sc if s["kind"] == "activity" or s.get("active"))
        plain = {}
        for s in sc:
            if s["kind"] == "slide" and not s.get("active") and not s.get("recap"):
                plain[s["sub_ilo"]] = plain.get(s["sub_ilo"], 0) + cs.minutes(s)
        check("the practical hours are on the activity screens and the active slides; a Sub-ILO's plain theory stops at the "
              "cap, the rest is done", doing >= 90 and max(plain.values()) <= ms.SK["plain_max_per_sub_ilo"], (doing, plain))
        mc_t = next(i for i, s in enumerate(sc) if s.get("opens") == "MC")
        check("the recap straight before the module check's task slide, the module check last",
              sc[mc_t - 1].get("recap") and all(k == "module-check" for k in kinds[mc_t + 1:]))
        taught = {t for s in sc if s["kind"] in ("slide", "activity") for t in cs.sub_ilos_of(s)}
        asked_sc = {t for s in sc if s["kind"] == "self-check" for t in cs.sub_ilos_of(s)}
        asked_mc = {t for s in sc if s["kind"] == "module-check" for t in cs.sub_ilos_of(s)}
        ids = {i for i, _ in subs}
        check("every Sub-ILO is taught on a slide, practised in a self-check and checked in the module check",
              taught == asked_sc == asked_mc == ids, (taught, asked_sc, asked_mc))
        fmts = {s["format"]: cs.sub_ilos_of(s) for s in sc if s["kind"] == "activity"}
        check("the real-time, team and hands-on Sub-ILOs each get an activity in a format of their kind",
              any("3.2" in v and k == "scenario-run" for k, v in fmts.items()) and
              any("3.3" in v and k == "closed-loop" for k, v in fmts.items()) and
              any("3.4" in v and k == "demonstration" for k, v in fmts.items()), fmts)
        ev = next(s for s in sc if s.get("format") == "scenario-run")
        check("a scenario run leaves its \"events\" to write", "events" in ev)
        tt = [i for i, s in enumerate(sc) if s["kind"] == "task-slide" and s.get("team")]
        check("a module of 90 minutes or more with a Sub-ILO at Apply or higher gets one team task, straight after a self-check",
              len(tt) == 1 and sc[tt[0] - 1]["kind"] == "self-check", tt)
        for st in cs.plan_of(sk)[1]:
            lv = [bloom_map.task_level(cs.mech(q))["level"] for q in st["questions"]]
            if st["kind"] == "self-check" and not sc[[s["id"] for s in sc].index(st["opened_by"])].get("team"):
                check("%s: Part A before Part B, %d questions" % (st["id"], len(lv)), lv == sorted(lv, key=lambda x: x >= 3)
                      and len(lv) >= 3, lv)

        print("\n-- the bare skeleton: the words are the only must-fix")
        probs = cs.validate(sk)
        check("validate says one thing: the words still to write", len(probs) == 1 and probs[0].startswith("words still to write"),
              probs[:3])
        found = cs.all_findings(sk, c)
        hard = [f for f in found if f["level"] == cs.FAIL and f["rule"] not in cs.WAIT_FOR_WORDS]
        check("no structural must-fix (only the ones that wait for the words)", not hard, [(f["rule"], f["detail"][:80]) for f in hard])
        p = cs.paths(c, 3)["script"]
        cs.save(p, sk)
        r = subprocess.run([sys.executable, os.path.join(HERE, "content_script.py"), "check", c, "--module", "3"],
                           capture_output=True, text=True, encoding="utf-8")
        check("content_script.py check: exit 1, one must-fix open, no [must fix] line",
              r.returncode == 1 and "1 must-fix(es) open." in r.stdout and "[must fix]" not in r.stdout, r.stdout[-1500:])
        check("... and the line names the fields to write, screens grouped", "picture.shows" in r.stdout and "s01" in r.stdout)

        print("\n-- written to its targets, the structure holds")
        full = fill(sk)
        check("nothing left to write", not cs.to_write(full), cs.to_write(full))
        th = cs.theory_check(full)[0]
        rules = {f["rule"] for f in th if f["level"] == cs.FAIL}
        check("enough theory before every self-check, words filling the minutes, a worked example before every task that "
              "works something out", not rules & {"t_before_sc", "t_density", "t_no_worked_example"},
              [(f["rule"], f["detail"][:90]) for f in th if f["rule"] in ("t_before_sc", "t_density", "t_no_worked_example")])
        allf = cs.all_findings(full, c)
        bad = [f for f in allf if f["rule"] in STRUCTURE and f["level"] == cs.FAIL]
        check("no structural finding on the written module", not bad, [(f["rule"], f["detail"][:90]) for f in bad])
        check("no two neighbouring slides built the same way (L62)", not [x for x in cs.shape_problems(full) if "same look" in x],
              cs.shape_problems(full))
        bm = cs.bloom_of(c, full)
        check("every Sub-ILO practised and checked at its level (bloom B5)",
              not [k for k, _ in bm["findings"] if k in ("b_sub_unchecked", "b_sub_unpractised")], bm["findings"])

        print("\n-- a module of seven decision Sub-ILOs, little theory (IT M05-like: 2 h + 2 h of 40 min)")
        subs7 = [("5.%d" % i, t) for i, t in enumerate([
            "Explain how a large language model produces an answer", "Identify fabricated statements and bias in an answer",
            "Write a clear instruction to an AI assistant", "Check AI output against the manual and correct it",
            "Decide what may be given to an AI assistant", "Match AI applications in shipping to their jobs",
            "Solve a professional question with the assistant and correct the planted error"], 1)]
        c7 = course(tmp, "it", subs7, 2, 2, hour=40, module=5)
        s7 = ms.build(c7, 5)
        blocks = s7["skeleton"]["blocks"]
        check("blocks of two, the odd one joins the last", [len(b) for b in blocks] == [2, 2, 3], blocks)
        acts = [s for s in s7["screens"] if s["kind"] == "activity"]
        check("the doing Sub-ILOs (decide 5.5, solve 5.7 - one block, split where it would pass 45 min) each in an activity, "
              "of more than one format", sorted(t for a in acts for t in cs.sub_ilos_of(a)) == ["5.5", "5.7"]
              and len({a["format"] for a in acts}) > 1, [(a["format"], a["sub_ilo"], a["minutes"]) for a in acts])
        check("the minutes add up (160)", sum(cs.minutes(s) for s in s7["screens"] if s["kind"] in cs.INSTRUCTOR) == 160)
        f7 = fill(s7)
        bad = [f for f in cs.all_findings(f7, c7) if f["level"] == cs.FAIL and f["rule"] in STRUCTURE + ("t_before_sc", "t_density",
                                                                                                         "t_no_worked_example")]
        check("written to its targets: no structural finding", not bad, [(f["rule"], f["detail"][:90]) for f in bad])

        print("\n-- groups of trainees: the course's other modules have them")
        cs.save(os.path.join(c7, "working_claude", "script", "M04.json"),
                {"module": 4, "groups": {"N": "Ship navigators", "T": "Ship engineers"}, "screens": []})
        g7 = ms.build(c7, 5)
        sets = cs.plan_of(g7)[1]
        check("the skeleton carries the groups, and every set's last question is written once for each group",
              g7.get("groups") == {"N": "Ship navigators", "T": "Ship engineers"}
              and all([q.get("group") for q in st["questions"][-2:]] == ["N", "T"] for st in sets),
              [[q.get("group") for q in st["questions"]] for st in sets])
        fg = fill(g7)
        gp = cs.group_problems(fg)
        bad = [f for f in cs.all_findings(fg, c7) if f["level"] == cs.FAIL and f["rule"] in STRUCTURE]
        check("... each group's path meets the set rules, written to its targets", not gp and not bad,
              (gp, [(f["rule"], f["detail"][:90]) for f in bad]))
        check("... --no-groups: none", "groups" not in ms.build(c7, 5, with_groups=False))

        print("\n-- much theory a Sub-ILO (PM M01-like: 5 h + 5 h of 40 min): plain theory capped, a second active slide, "
              "the rest to the activities")
        subs5 = [("1.%d" % i, t) for i, t in enumerate([
            "Distinguish a project from routine ship operation", "Create the project charter",
            "Evaluate the stakeholders' influence", "Evaluate the risks of the project", "Plan the project's communication"], 1)]
        c5 = course(tmp, "pm", subs5, 5, 5, hour=40, module=1)
        s5 = ms.build(c5, 1)
        check("blocks of two, the odd one joins the last", [len(b) for b in s5["skeleton"]["blocks"]] == [2, 3], s5["skeleton"]["blocks"])
        pl = [s for s in s5["screens"] if s["kind"] == "slide" and not s.get("active") and not s.get("recap")]
        act = [s for s in s5["screens"] if s["kind"] == "slide" and s.get("active")]
        check("no plain slide over the most minutes a slide holds; two plain and two active slides a Sub-ILO",
              max(cs.minutes(s) for s in pl) <= ms.SK["plain_slide_max_minutes"] and len(pl) == 10 and len(act) == 10,
              (len(pl), len(act)))
        sp = cs.split_of(s5)
        check("... so the class is mostly doing (the 20 / 80 aim met)", sp["share"] >= sp["target"], sp["share"])
        f5 = fill(s5)
        bad = [f for f in cs.all_findings(f5, c5) if f["level"] == cs.FAIL and f["rule"] in STRUCTURE + ("t_before_sc", "t_density",
                                                                                                         "t_no_worked_example")]
        check("written to its targets: no structural finding", not bad, [(f["rule"], f["detail"][:90]) for f in bad])
        mc = [q for q in s5["screens"] if q["kind"] == "module-check"]
        fams = [cs.family_of(q) for q in mc]
        check("the module check: no family over 40 %, no two neighbours alike", max(fams.count(f) for f in fams) <= 2
              and all(a != b for a, b in zip(fams, fams[1:])), fams)

        print("\n-- theory only, one Sub-ILO (1 h)")
        c1 = course(tmp, "one", [("2.1", "State the purpose of the muster list")], 1, 0, hour=45, module=2)
        s1 = ms.build(c1, 2)
        check("one block, a self-check of three, no team task, 45 minutes", s1["minutes_allocated"] == 45
              and len([q for q in s1["screens"] if q["kind"] == "self-check"]) == 3
              and not any(s.get("team") for s in s1["screens"])
              and sum(cs.minutes(s) for s in s1["screens"] if s["kind"] in cs.INSTRUCTOR) == 45)
        check("no activity where nothing needs one and the programme gives no practical hours",
              not [s for s in s1["screens"] if s["kind"] == "activity"])
        try:
            ms.build(course(tmp, "tiny", subs7, 0.25, 0, hour=40, module=5), 5)
            check("too few minutes for the Sub-ILOs: refused with the numbers", False)
        except ValueError as e:
            check("too few minutes for the Sub-ILOs: refused with the numbers", "too few" in str(e), str(e))

        print("\n-- the command")
        code, out = quiet(ms.main, ["make", c, "--module", "3"])
        check("make refuses a script that is there", code == 2 and "--force" in out, out)
        code, out = quiet(ms.main, ["make", c, "--module", "3", "--force"])
        old = os.listdir(cs.paths(c, 3)["old"])
        check("... --force keeps the old one in script/old and writes the skeleton", code == 0 and len(old) == 1
              and cs.load(cs.paths(c, 3)["script"])["skeleton"], (code, out, old))
        code, out = quiet(ms.main, ["show", c, "--module", "3"])
        check("show prints the outline, nothing written", code == 0 and "MC" in out and "recap" in out, out[:300])
        code, out = quiet(ms.main, ["make", c1, "--module", "9"])
        check("a module the ILO map does not have: exit 2, said", code == 2 and "no Sub-ILOs" in out, out)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("\n%s" % ("all passed" if not FAILS else "%d failed: %s" % (len(FAILS), ", ".join(FAILS))))
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
