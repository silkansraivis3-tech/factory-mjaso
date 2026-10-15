# -*- coding: utf-8 -*-
"""test_active_plan - the factory proposes theory taught as activity; the operator keeps or strikes each (L49 step 3, 2.27.0).

    python test_active_plan.py

Pinned (owner, 2026-10-15):
  * proposals are lines in architecture.json, status "proposed"; a line with no status is kept (older courses);
  * the Stage 2 page shows each waiting proposal with Keep and Strike, what the trainees do in plain words,
    that the slides stay, what it needs - and a box at the top: how many wait, the class split now and if all
    are kept, and a Copy my choices button. Only kept lines count toward the split now;
  * every sub-topic with theory gets a proposal - one without is pointed out (a suggestion);
  * active_plan.py decide records only what the operator said: an unknown id, an id both kept and struck, or
    no words from the operator stop it before anything changes; a struck line stays in the file; every
    decision is logged in FEEDBACK_LOG.md with the operator's words; the page is re-rendered; a decision can
    be changed by deciding again;
  * the page's script works offline: nothing fetched, ticks kept in the browser only.
"""
from __future__ import annotations

import copy
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
TOOL = os.path.join(HERE, "active_plan.py")
sys.path.insert(0, HERE)
import active_plan  # noqa: E402
import make_architecture_page as ap  # noqa: E402
import test_architecture_page as tap  # noqa: E402

PASS, FAIL = [], []
LV = ap.LABELS["lv"]
LOG = ("# log\n\n| # | Date | Stage · module · where | What the operator said | What changed | Operator-stated fact? |\n"
       "|---|---|---|---|---|---|\n| 1 | 2026-10-01 | 3 · M01 · s02 | x | y | no |\n")


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print(("  ok    " if ok else "  FAIL  ") + name + (("  -> " + str(detail)[:400]) if detail and not ok else ""))


def arch_with_proposals():
    a = copy.deepcopy(tap.ARCH)
    a["modules"][0]["active_learning"] = [
        {"id": "A1.1", "subtopic": "1.1", "technique": "explore", "status": "proposed", "minutes": 10,
         "does": "Katrs kursants atver četrus tanku tipus 3D korpusa griezumā un atrod, kurš balstās uz korpusu.",
         "instead_of": "slaidi par tanku tipiem - 5 minūtēs, nevis 15", "needs": ""},
        {"id": "A1.2", "subtopic": "1.1", "technique": "predict-then-reveal", "status": "proposed", "minutes": 5,
         "does": "Kursanti paredz, kas notiek ar spiedienu tankā tropos; tad animācija to parāda.", "needs": "nekas"}]
    a["modules"][1]["active_learning"] = [{"id": "A2.1", "subtopic": "2", "technique": "worked-example", "status": "approved",
                                           "minutes": 5, "does": "Viens rādījums uz ekrāna, nākamo kursanti nolasa paši."}]
    return a


def run(*a):
    p = subprocess.run([sys.executable, TOOL] + list(a), capture_output=True, text=True, encoding="utf-8", errors="replace")
    return p.returncode, p.stdout + p.stderr


def main():
    prog, arch = copy.deepcopy(tap.PROGRAMME), arch_with_proposals()
    print("-- the proposals on the Stage 2 page")
    a = ap.analyse(prog, arch)
    check("two proposals wait", [x["id"] for _, x in a["waiting"]] == ["A1.1", "A1.2"], a["waiting"])
    m1 = a["modules"][0]
    check("only kept lines count now; all of them if every proposal is kept",
          (m1["plain"], m1["plain_all"]) == (66, 51), (m1["plain"], m1["plain_all"]))
    m2 = a["modules"][1]
    check("a kept line counts now", m2["plain"] == m2["th_min"] - sum(s["minutes"] for s in m2["sc"]) - m2["mc"]["minutes"] - 5, m2["plain"])
    check("a sub-topic with a proposal is not pointed out", not any(k == "a_no_proposal" and kw["s"] == "1.1" for k, kw in a["split"]), a["split"])
    check("a module with theory and no proposal is pointed out", ("a_no_proposal_mod", {"m": 3}) in a["split"], a["split"])
    old = ap.analyse(prog, copy.deepcopy(tap.ARCH))
    check("an older line with no status counts as kept, and waits for nothing", old["waiting"] == [], old["waiting"])
    check("proposals never become problems", a["problems"] == old["problems"])
    page = ap.build(prog, arch, a)
    check("the page asks for a decision, with how many wait", LV["w_title"].format(n=2) in page)
    tm = [m for m in a["modules"] if not m["assessment"]]
    pct = lambda k: "%.0f" % (100.0 * sum(m[k] for m in tm) / sum(m["alloc"] for m in tm))
    check("... and shows the split now and if all are kept (the whole course)",
          LV["w_now"].format(pp=pct("plain"), ap=pct("active")) in page and LV["w_all"].format(pp=pct("plain_all"), ap=pct("active_all")) in page
          and pct("plain") != pct("plain_all"), re.findall(r"Ja saglabāsiet[^<]*", page))
    check("each waiting proposal has Keep and Strike", page.count('data-choice="keep"') == 2 and page.count('data-choice="strike"') == 2)
    check("... what the trainees do, and that the slides stay", "Katrs kursants atver" in page and LV["slides_stay"].split("{")[0] in page)
    check("a kept line shows as kept, without buttons", 'data-id="A2.1"' not in page and "saglabāts" in page)
    check("the copy button and the page's own script are there", 'id="copy-choices"' in page and "localStorage" in page and "<script>" in page)
    check("the page fetches nothing", not re.search(r'(src|href)="https?://', page) and "fetch(" not in page)
    check("with nothing waiting there is no script", "<script>" not in ap.build(prog, tap.ARCH, old))

    print("\n-- recording what the operator decided")
    tmp = tempfile.mkdtemp(prefix="plan_")
    try:
        c = os.path.join(tmp, "course")
        os.makedirs(os.path.join(c, "working_claude"))
        for n, v in (("programme.json", prog), ("architecture.json", arch)):
            io.open(os.path.join(c, "working_claude", n), "w", encoding="utf-8").write(json.dumps(v, ensure_ascii=False))
        io.open(os.path.join(c, "working_claude", "FEEDBACK_LOG.md"), "w", encoding="utf-8").write(LOG)
        af = os.path.join(c, "working_claude", "architecture.json")
        before = io.open(af, encoding="utf-8").read()
        code, out = run("list", "--course", c)
        check("list shows what waits, the gaps, and the split", code == 0 and "A1.1" in out and "A1.2" in out and "Modulis 3" in out
              and "now %s %%; if every proposal is kept %s %%" % (pct("plain"), pct("plain_all")) in out, out)
        code, out = run("decide", "--course", c, "--keep", "A1.1,A9.9", "--said", "x")
        check("an unknown id stops it, and nothing changes", code == 2 and "A9.9" in out and io.open(af, encoding="utf-8").read() == before, out)
        code, out = run("decide", "--course", c, "--keep", "A1.1", "--strike", "A1.1", "--said", "x")
        check("an id both kept and struck stops it", code == 2 and io.open(af, encoding="utf-8").read() == before, out)
        code, out = run("decide", "--course", c, "--keep", "A1.1")
        check("no words from the operator stops it", code == 2 and io.open(af, encoding="utf-8").read() == before, out)
        said = "Saglabāt: A1.1. Svītrot: A1.2."
        code, out = run("decide", "--course", c, "--keep", "A1.1", "--strike", "A1.2", "--said", said)
        lines = active_plan.lines_of(json.load(io.open(af, encoding="utf-8")))
        check("decide records kept and struck", code == 0 and lines["A1.1"][1]["status"] == "approved" and lines["A1.2"][1]["status"] == "struck", out)
        check("a struck line stays in the file, with the operator's words", "A1.2" in lines and lines["A1.2"][1]["decided_said"] == said)
        log = io.open(os.path.join(c, "working_claude", "FEEDBACK_LOG.md"), encoding="utf-8").read()
        check("each decision is logged with the operator's words", "| 2 | " in log and "| 3 | " in log and "2 · M01 · A1.1" in log
              and said in log and "struck - Kursanti paredz" in log, log[-500:])
        page = io.open(os.path.join(c, "to_review", "ARCHITECTURE_REVIEW.html"), encoding="utf-8").read()
        check("the page is re-rendered: nothing waits, the struck line is shown struck", "<script>" not in page
              and 'class="st-struck"' in page and "svītrots" in page, out)
        a2 = ap.analyse(prog, json.load(io.open(af, encoding="utf-8")))
        check("the kept line now counts, the struck one does not", a2["modules"][0]["plain"] == 56, a2["modules"][0]["plain"])
        code, out = run("decide", "--course", c, "--strike", "A1.1", "--said", "Tomēr svītrot A1.1")
        lines = active_plan.lines_of(json.load(io.open(af, encoding="utf-8")))
        check("a decision can be changed by deciding again - and says what it was", code == 0 and lines["A1.1"][1]["status"] == "struck"
              and "was kept" in out, out)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("\n-- the words")
    keys = ("p_intro", "col_subtopic", "col_does", "col_how", "col_needs", "col_decision", "btn_keep", "btn_strike", "w_title", "w_intro",
            "w_now", "w_all", "w_copy", "w_copied", "w_none_yet", "stays_plain", "slides_stay", "tech_plain", "a_no_proposal", "a_no_proposal_mod")
    for L in ("en", "lv", "ru"):
        check("every proposal word is written in %s" % L, all(ap.LABELS[L].get(k) for k in keys), [k for k in keys if not ap.LABELS[L].get(k)])
    check("every pattern names what the trainees do and its minutes",
          all(p.get("does") and p.get("minutes") and p.get("fits") for p in ap.ACTIVE["patterns"].values()))
    check("every pattern is a technique the page knows", all(k in ap.TECHNIQUES for k in ap.ACTIVE["patterns"]))

    print("\n" + "=" * 72)
    print("%d passed, %d failed" % (len(PASS), len(FAIL)))
    if FAIL:
        return 1
    print("\nThe factory proposes theory as activity, the operator keeps or strikes each, and only that is recorded.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
