# -*- coding: utf-8 -*-
"""test_active_split - plain theory against active learning, aiming at 20 / 80 in class (L49, 2.26.0).

    python test_active_split.py

Pinned (owner, 2026-10-15):
  * the programme's hours never change - only how the class spends them;
  * Stage 3: plain theory = slides without "active"; active = active slides + tasks + practice; the
    review page shows both, and below 80 % active a SUGGESTION names the plain slides with the most
    minutes - and says to keep every slide (theory is never removed, only its minutes shrink);
  * an active slide names its technique (explain-then-reveal, predict-then-reveal, worked-example,
    scenario, explore) - an unknown one is a script problem; the page shows it on the slide;
  * the density floor counts plain theory only; theory comes in ~5-minute cycles before a self-check;
  * Stage 2: per module, plain = theory minutes less self-checks, module check and the planned
    theory-as-activity minutes; a line of theory-as-activity without minutes is pointed out;
  * none of it blocks: the architecture check's exit code and the content script's approval are
    as before; the final assessment has no split.
"""
from __future__ import annotations

import copy
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import content_script as cs  # noqa: E402
import make_architecture_page as ap  # noqa: E402
import test_architecture_page as tap  # noqa: E402
import test_content_script as tcs  # noqa: E402

PASS, FAIL = [], []
LV, EN = cs.LABELS["lv"], cs.LABELS["en"]


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print(("  ok    " if ok else "  FAIL  ") + name + (("  -> " + str(detail)[:400]) if detail and not ok else ""))


def screen(script, sid):
    return next(s for s in script["screens"] if s["id"] == sid)


def main():
    R = cs.RULES
    print("-- the rules")
    check("theory comes in about 5-minute cycles before a self-check", R["before_self_check"]["min_minutes"] == 5, R["before_self_check"])
    check("the aim is 80 % active", R["split"]["target_active_share"] == 0.8)
    check("every active technique has a name in en / lv / ru",
          all(cs.LABELS[L].get("tech_" + k) for L in ("en", "lv", "ru") for k in cs.ACTIVE), cs.ACTIVE)

    print("\n-- Stage 3: the content script")
    s = copy.deepcopy(tcs.SCRIPT)
    sp = cs.split_of(s)
    check("plain theory = the slides' minutes; active = tasks (and active slides, practice)",
          (sp["plain"], sp["tasks"], sp["active_slides"], sp["total"]) == (15, 8, 0, 23), sp)
    check("below 80 % active it is a suggestion", [k for k, _ in sp["findings"]] == ["a_low"], sp["findings"])
    text = cs.T(s, *sp["findings"][0][:1], **sp["findings"][0][1])
    check("... which says to keep every slide - theory is never removed, only its minutes shrink",
          "Saglabājiet katru slaidu" in text and cs.place(s, "s01") in text, text)
    en_text = cs.T(dict(s, operator_language="en"), "a_low", pp="1", tp="1", ids="x", how="x").lower()
    for word in ("remove", "delete", "cut", "dzēs", "izņem", "удал"):          # whole words: 'aizņem' (takes up) is not 'izņem'
        check("... and never says '%s'" % word, not re.search(r"(?<!\w)%s" % word, en_text) and not re.search(r"(?<!\w)%s" % word, text.lower()))
    a = copy.deepcopy(s)
    screen(a, "s03")["active"] = "explore"
    sp2 = cs.split_of(a)
    check("an active slide's minutes count as active", sp2["plain"] == 10 and sp2["active_slides"] == 5, sp2)
    check("an active slide is still theory taught before the next task", not [f for f in cs.theory_findings(a)[0] if f["rule"] == "t_before_sc"])
    slow = copy.deepcopy(s)
    screen(slow, "s03")["minutes"] = 25
    screen(slow, "s03")["active"] = "explore"
    check("the density floor counts plain theory only - a long active slide is not 'unfilled'",
          "t_density" not in [f["rule"] for f in cs.theory_findings(slow)[0]], cs.theory_findings(slow)[0])
    bad = copy.deepcopy(s)
    screen(bad, "s03")["active"] = "watching"
    check("an unknown kind of active learning is a script problem", any("unknown kind of active learning" in p for p in cs.validate(bad)), cs.validate(bad))
    on = copy.deepcopy(s)
    for sid, m in (("s01", 1), ("s02", 1), ("s03", 1)):
        screen(on, sid)["minutes"] = m
    screen(on, "t01")["minutes"], screen(on, "t02")["minutes"] = 10, 10
    check("on the aim: no suggestion", cs.split_of(on)["findings"] == [] and cs.split_of(on)["share"] >= 0.8, cs.split_of(on))
    fin = dict(copy.deepcopy(s), module="final")
    check("the final assessment has no split", cs.split_html(lambda x: x, fin) == "" and cs.split_of(fin)["findings"] == [])
    check("the split never becomes a must-fix: the findings that block approval are unchanged",
          cs.blocking(cs.all_findings(a)) == cs.blocking(cs.all_findings(s)))

    tmp = tempfile.mkdtemp(prefix="split_")
    try:
        c = tcs.new_course(tmp, "course", a)
        cs.render(c, "1", quiet=True)
        page = io.open(cs.paths(c, "1")["review"], encoding="utf-8").read()
        check("the review page shows the split in the operator's language", LV["a_title"] in page and LV["a_plain"] in page)
        check("... and the active slide says what kind", LV["s_active"] in page and LV["tech_explore"] in page)
        p = subprocess.run([sys.executable, os.path.join(HERE, "content_script.py"), "render", c, "--module", "1"],
                           capture_output=True, text=True, encoding="utf-8")
        check("render prints the split", "Plain theory 10 min, active 13 min" in p.stdout, p.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("\n-- Stage 2: the architecture")
    prog, arch = copy.deepcopy(tap.PROGRAMME), copy.deepcopy(tap.ARCH)
    an = ap.analyse(prog, arch)
    m1 = an["modules"][0]
    check("module 1: plain = theory less self-checks and module check; active = the rest",
          (m1["plain"], m1["active"]) == (66, 14), (m1["plain"], m1["active"]))
    check("... below the aim - a suggestion", ("a_arch_low", {"m": 1, "pp": "82", "tp": "20"}) in an["split"], an["split"])
    a2 = copy.deepcopy(arch)
    a2["modules"][0]["active_learning"] = [{"where": "tank types", "instead_of": "15 min of slides", "technique": "explore", "minutes": 40}]
    m1 = ap.analyse(prog, a2)["modules"][0]
    check("theory planned as activity, with minutes, moves them to active", (m1["plain"], m1["active"]) == (26, 54), (m1["plain"], m1["active"]))
    check("a line of theory-as-activity without minutes is pointed out", ("a_no_minutes", {"m": 1}) in an["split"], an["split"])
    check("the split never becomes a problem", an["problems"] == ap.analyse(prog, a2)["problems"]
          and not any(k.startswith("a_") for k, _ in an["problems"]))
    page = ap.build(prog, a2, ap.analyse(prog, a2))
    check("the architecture page shows the split, and the programme on paper unchanged",
          LV["a_title"] in page and LV["a_course"].split("{")[0] in page and "40 min" in page, page[:200])
    tmp = tempfile.mkdtemp(prefix="split_")
    try:
        c = tap.write_course(os.path.join(tmp, "c"), prog, arch)
        p = subprocess.run([sys.executable, os.path.join(HERE, "make_architecture_page.py"), "--course", c, "--check"],
                           capture_output=True, text=True, encoding="utf-8")
        check("--check lists the split as a suggestion and still passes a correct course", p.returncode == 0 and "(20/80, suggestion)" in p.stdout, p.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("\n" + "=" * 72)
    print("%d passed, %d failed" % (len(PASS), len(FAIL)))
    if FAIL:
        return 1
    print("\nThe class's minutes are measured - plain theory against active learning - every slide kept, the programme unchanged.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
