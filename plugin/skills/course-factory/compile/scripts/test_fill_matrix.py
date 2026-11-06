# -*- coding: utf-8 -*-
"""test_fill_matrix - the way of answering "fill the table" (fill_matrix, 2.109.0), end to end.

    python test_fill_matrix.py

The Project Management reviewer asked that trainees "do the RACI themselves": a table, a palette of values, tap a
value then tap cells. Pinned:
  * the script: a well-written one passes; each way of writing it wrong is caught in plain words;
  * answer_items lists what the built page shows (the grid's names and the palette - never a cell's right value);
  * the built page: every cell empty, big enough, no right value anywhere in it (only keys), the answer key page and
    the review page draw it, the word-for-word check passes it;
  * the engine, in a hidden browser: all right is 1 of 1; one wrong cell is 0 of 1 with that cell marked, its right
    value shown in amber; a tap on a filled cell with the same value clears it; with no value held a tap steps
    through the values; Check waits for every cell; no script error;
  * the grid fits 1280 x 800 and 1024 x 768 at 6 rows x 5 columns: nothing sideways, every tap target 56 px or more.
Skipped (not failed) in the browser part when no Chrome or Edge is found.
"""
from __future__ import annotations

import copy
import io
import json
import os
import re
import shutil
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import drawing_check  # noqa: E402
import test_compile_module as tcm  # noqa: E402
import test_task_engine as tte  # noqa: E402

cs = tcm.cs
PASS, FAIL = [], []

RACI = {"id": "q01", "kind": "self-check", "set": "SC1", "mechanic": "fill_matrix",
        "question": "Fill in the RACI matrix for the unit overhaul.",
        "values": "R, A, C, I, –",
        "answer": "Work package | Master | Chief engineer | Shipyard\n"
                  "Open and inspect the unit | I | A | R\n"
                  "Order the spare parts | C | A | I\n"
                  "Approve the cost | A | C | –",
        "feedback": "One A per row, and the shipyard does the work."}
CHOICE = {"id": "q02", "kind": "self-check", "set": "SC1", "mechanic": "single_choice", "question": "Who is accountable?",
          "options": ["The one who does the work", "The one who answers for the result"], "correct": "B", "feedback": "A answers for it."}
SCREENS = [tcm.EVERY_WAY[0], RACI, CHOICE]


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print(("  ok    " if ok else "  FAIL  ") + name + (("  -> " + str(detail)[:500]) if detail and not ok else ""))


def probs(q):
    return cs.read_answer(q)[0]


def big(rows, cols):
    """a rows x cols grid, the right values cycling through R, A, C, I"""
    v = ["R", "A", "C", "I"]
    head = " | ".join(["Work package"] + ["Role %d" % (c + 1) for c in range(cols)])
    body = ["\n" + " | ".join(["Package %d" % (r + 1)] + [v[(r + c) % 4] for c in range(cols)]) for r in range(rows)]
    return dict(RACI, answer=head + "".join(body), values="R, A, C, I, –")


def script_part():
    print("-- the script")
    mk = cs.MEDIA["mechanics"].get("fill_matrix") or {}
    check("named, with its answer format and its values format", all(mk.get(k) for k in ("en", "answer", "values")), mk)
    check("not hands-on, no typing in its words", mk.get("hands_on") is False and "typ" not in (mk.get("en", "") + mk.get("answer", "")).lower())
    check("the script knows its parts: values and answer", cs.USES["fill_matrix"] == {"values", "answer"})
    check("a well-written grid passes", probs(RACI) == [], probs(RACI))
    check("a 6 x 5 grid passes", probs(big(6, 5)) == [], probs(big(6, 5)))
    vals, head, rows = cs.matrix_of(RACI)
    check("matrix_of: the palette, the header, the rows", vals == ["R", "A", "C", "I", "–"] and head == ["Work package", "Master", "Chief engineer", "Shipyard"]
          and rows[0] == ("Open and inspect the unit", ["I", "A", "R"]) and len(rows) == 3, (vals, head, rows))
    bad = []
    bad.append(("one value only", dict(RACI, values="R"), "at least two different values"))
    bad.append(("a repeated value", dict(RACI, values="R, A, R"), "at least two different values"))
    bad.append(("no values", {k: v for k, v in RACI.items() if k != "values"}, "at least two different values"))
    bad.append(("a header with one column", dict(RACI, answer="Work package | Master\nA | R\nB | A"), "header line"))
    bad.append(("one row", dict(RACI, answer="Work package | Master | Shipyard\nOpen | A | R"), "at least two rows"))
    bad.append(("a short row", dict(RACI, answer=RACI["answer"].replace("Order the spare parts | C | A | I", "Order the spare parts | C | A")), "has 2 cell(s), the header has 3"))
    bad.append(("a long row", dict(RACI, answer=RACI["answer"].replace("Approve the cost | A | C | –", "Approve the cost | A | C | – | I")), "has 4 cell(s), the header has 3"))
    bad.append(("a cell not in the values", dict(RACI, answer=RACI["answer"].replace("| I | A | R", "| X | A | R")), "'X' in the row 'Open and inspect the unit' is not one of the values"))
    bad.append(("an empty cell", dict(RACI, answer=RACI["answer"].replace("| I | A | R", "|  | A | R")), "is not one of the values"))
    bad.append(("the same row twice", dict(RACI, answer=RACI["answer"] + "\nApprove the cost | A | C | –"), "different"))
    for name, q, needle in bad:
        p = probs(q)
        check("caught: " + name, any(needle in x for x in p), p)
    items, right = cs.answer_items(RACI)
    check("answer_items: the header cells, the row names and the palette - no right value to mark",
          items == ["Work package", "Master", "Chief engineer", "Shipyard", "Open and inspect the unit", "Order the spare parts",
                    "Approve the cost", "R", "A", "C", "I", "–"] and right == [], (items, right))
    _, r, w = cs.read_answer(RACI)
    check("read_answer: the cells are the right words (for 'was it taught?'), none is wrong", "R" in r and len(r) == 9 and w == [], (r, w))
    f = dict(cs.fields_of(dict(RACI), "en"))
    check("the operator edits the values and the answer in their own boxes", f.get("values") == "R, A, C, I, –" and f.get("answer", "").startswith("Work package"), list(f))
    import bloom_map as bm
    check("Bloom: Apply (3), able to reach 4", bm.B["mechanics"]["fill_matrix"]["typical"] == 3 and bm.B["mechanics"]["fill_matrix"]["ceiling"] == 4)
    L = cs.LABELS["en"]
    check("the review page's words exist", all(L.get(k) for k in ("mm_matrix", "fmt_fill_matrix", "s_values")))


def build_part(tmp):
    print("\n-- the built page, the key page, the review page")
    os.makedirs(os.path.join(tmp, "b"))
    c, md = tcm.new_course(os.path.join(tmp, "b"), tcm.script(screens=SCREENS), build=False)
    tcm.cs.save(os.path.join(c, "working_claude", "script", "M01.build.json"), {"module": 1, "screens": {"t01": {"try_tablet": False}}})
    code, out = tcm.run(tcm.COMPILE, c, "--module", "1", "--only", "tasks")
    page = os.path.join(md, "tasks", "sc1_every_way.html")
    check("the module builds with a table question", code == 0 and os.path.isfile(page), out[-800:])
    html = io.open(page, encoding="utf-8").read() if os.path.isfile(page) else ""
    sec = re.search(r'<section class="scr[^"]*" data-script="q01".*?</section>', html, re.S)
    sec = sec.group(0) if sec else ""
    check("the section carries its way of answering", 'data-mech="fill_matrix"' in sec, sec[:200])
    check("a palette of five values, nine empty cells, three rows and a header of four names",
          sec.count('class="mxv"') == 5 and sec.count('class="mxc"') == 9 and sec.count('<th scope="row"') == 3 and sec.count('<th scope="col"') == 4, sec[:300])
    check("every cell is empty: no value written inside one", all(m == "" for m in re.findall(r'<span class="mxt">(.*?)</span>', sec)) and 'data-v=' not in sec)
    keys = re.findall(r'class="mxc" data-at="([^"]+)" data-key="([0-9a-f]{8})"', sec)
    check("every cell has its own key = gbKey(screen, 'row | column', the right value)", len(keys) == 9 and keys[0][0] == "Open and inspect the unit | Master"
          and keys[0][1] == cs.gb_key("q01", "Open and inspect the unit | Master", "I"), keys[:2])
    check("no cell says what is right in the open: no data-correct, no right-value attribute",
          "data-correct" not in sec and "data-right" not in sec and 'data-val=' not in sec)
    check("the page tells the trainee what to do, in words", "Tap a value, then tap the cells" in sec)
    kp = [p for p in os.listdir(os.path.join(md, "tasks")) if "key" in p.lower()] if os.path.isdir(os.path.join(md, "tasks")) else []
    keyhtml = ""
    for root, _, files in os.walk(md):
        for fn in files:
            if fn.endswith(".html") and "key" in fn.lower():
                keyhtml += io.open(os.path.join(root, fn), encoding="utf-8").read()
    check("the answer-key page lists the grid row by row, for the instructor", "Open and inspect the unit</b>: Master = I; Chief engineer = A; Shipyard = R" in keyhtml,
          (kp, keyhtml[:200]))

    # the review page and the word-for-word check
    sc = tcm.script(screens=SCREENS)
    root = os.path.join(tmp, "r")
    os.makedirs(root)
    import test_content_script as tcs
    full = copy.deepcopy(tcs.SCRIPT)
    full["operator_language"] = "en"
    full["screens"] = [x for x in full["screens"] if x["kind"] in cs.INSTRUCTOR] + [copy.deepcopy(x) for x in SCREENS if x["kind"] != "task-slide"] + \
        [x for x in full["screens"] if x["kind"] == "task-slide"][:1]
    # simpler and exact: draw the review page of the small script on its own
    try:
        c2 = tcs.new_course(root, "course", full)
        cs.render(c2, "1", quiet=True)
        rv = io.open(cs.paths(c2, "1")["review"], encoding="utf-8").read()
        check("the review page draws the table: the palette, the header, the cells", cs.LABELS["en"]["mm_matrix"] in rv and ">Chief engineer</span></th>" in rv
              and ">–</span></td>" in rv, rv[:100])
        check("... and names the way of answering", cs.mech_label("fill_matrix", "en") in rv)
    except Exception as ex:  # a script that does not fit the old fixture is the fixture's, not the feature's
        check("the review page draws the table", False, repr(ex))


def engine_part(exe, tmp):
    print("\n-- the engine, in a browser")
    os.makedirs(os.path.join(tmp, "e"))
    c, md = tcm.new_course(os.path.join(tmp, "e"), tcm.script(screens=SCREENS), build=False)
    tcm.cs.save(os.path.join(c, "working_claude", "script", "M01.build.json"), {"module": 1, "feedback": "now", "screens": {"t01": {"try_tablet": False}}})
    code, out = tcm.run(tcm.COMPILE, c, "--module", "1", "--only", "tasks")
    page = os.path.join(md, "tasks", "sc1_every_way.html")
    check("the fixture page is built", code == 0 and os.path.isfile(page), out[-600:])

    def put(val, cells):
        """tap the palette value, then each cell: cells are (row, column) names"""
        return [["eval", "var P=s.querySelectorAll('.mxv'),i;for(i=0;i<P.length;i++){if(P[i].textContent==='%s'){P[i].click();}}"
                         "%s" % (val, "".join("s.querySelector('.mxc[data-at=\"%s | %s\"]').click();" % rc for rc in cells))]]

    def fill(rows):
        plan = []
        for val in ("R", "A", "C", "I", "–"):
            cells = [(r, h) for r, hs in rows.items() for h, v in hs.items() if v == val]
            if cells:
                plan += put(val, cells)
        return plan

    right = {"Open and inspect the unit": {"Master": "I", "Chief engineer": "A", "Shipyard": "R"},
             "Order the spare parts": {"Master": "C", "Chief engineer": "A", "Shipyard": "I"},
             "Approve the cost": {"Master": "A", "Chief engineer": "C", "Shipyard": "–"}}
    pick = ["tap", ".opt", "The one who answers for the result"]
    ok_plan = [["q01", fill(right)], ["q02", [pick]]]
    r = tte.drive(exe, page, ok_plan, tmp, look=False)
    rep = r.get("report") or {}
    check("no script error", not r.get("errors"), r.get("errors"))
    check("all right: 2 of 2, the grid counted as one question", rep.get("ok") == 2 and rep.get("total") == 2, rep)
    check("Check was pressed once for the grid", r.get("steps", []).count("q01:Check") == 1, r.get("steps"))

    wrong = json.loads(json.dumps(right))
    wrong["Order the spare parts"]["Master"] = "I"                              # one cell wrong
    peek = ("var c=s.querySelector('.mxc[data-at=\"Order the spare parts | Master\"]'),d=s.querySelector('.mxc[data-at=\"Approve the cost | Master\"]');"
            "out.cells={bad:c.className,badText:c.textContent,was:c.getAttribute('data-was'),good:d.className,locked:s.className,"
            "verdict:s.querySelector('.vd').textContent};")
    r = tte.drive(exe, page, [["q01", fill(wrong) + [["dock"], ["eval", peek]]], ["q02", [pick]]], tmp, look=False)
    rep = r.get("report") or {}
    cells = r.get("cells") or {}
    check("one wrong cell: 1 of 2, the grid wrong", rep.get("ok") == 1 and [x["ok"] for x in rep.get("items", [])] == [False, True], rep)
    check("the wrong cell is marked wrong and shows the right value (C) in amber, with what was put there kept",
          "wrong" in cells.get("bad", "") and "fixed" in cells.get("bad", "") and cells.get("badText") == "C" and cells.get("was") == "I", cells)
    check("a right cell is locked green", "right" in cells.get("good", ""), cells)
    check("the verdict says what the amber cells are", "amber" in cells.get("verdict", ""), cells)
    check("what was wrong is listed for the debrief: the cell, what was put, what was right",
          any("Order the spare parts / Master: I" in x.get("a", "") and "Order the spare parts / Master: C" in x.get("c", "") for x in rep.get("items", [])), rep.get("items"))

    print("\n-- tapping")
    probe = ("var P=s.querySelectorAll('.mxv'),cl=function(t){var i;for(i=0;i<P.length;i++){if(P[i].textContent===t){P[i].click();}}},"
             "c=s.querySelector('.mxc[data-at=\"Approve the cost | Shipyard\"]'),t=function(){return c.textContent;},go=document.getElementById('go'),a=[];"
             "a.push(go.disabled);"
             "c.click();a.push(t());c.click();a.push(t());c.click();a.push(t());c.click();a.push(t());c.click();a.push(t());c.click();a.push(t());"   # cycle R A C I – (empty)
             "cl('A');c.click();a.push(t());c.click();a.push(t());"                                                                                   # A, then A again clears
             "a.push(go.disabled);"
             "var all=s.querySelectorAll('.mxc'),i;for(i=0;i<all.length;i++){if(!all[i].textContent){all[i].click();}}a.push(go.disabled);"
             "cl('A');a.push(P[1].className);cl('A');a.push(P[1].className);out.tap=a;")
    r = tte.drive(exe, page, [["q01", [["eval", probe]]]], tmp, look=False)
    tap = r.get("tap") or []
    check("a tap with no value held steps a cell through R, A, C, I, – and back to empty",
          tap[1:7] == ["R", "A", "C", "I", "–", ""], tap)
    check("a held value fills; the same value on a filled cell clears it", tap[7:9] == ["A", ""], tap)
    check("Check is off until every cell is filled, then on", tap[0] is True and tap[9] is True and tap[10] is False, tap)
    check("tapping the held value lets go of it, and again holds it", "sel" not in tap[11] and "sel" in tap[12], tap)
    check("no script error while tapping", not r.get("errors"), r.get("errors"))

    print("\n-- the page as a blind final answers it")
    r = tte.drive(exe, page, ok_plan, tmp, look=False, blind=True)
    check("blind: recorded, nothing shown, 2 of 2", (r.get("report") or {}).get("ok") == 2 and not r.get("errors"), (r.get("report"), r.get("errors")))


FIT = r"""
var s = document.querySelector('.scr[data-script="q01"]'), go = document.getElementById('go'), i, r, small = [], table, bad = [];
go.click();                                         /* the try screen is off: this is the first question on show */
s.classList.add('on');
table = s.querySelector('.mx');
var cells = s.querySelectorAll('.mxc'), vals = s.querySelectorAll('.mxv'), heads = s.querySelectorAll('.mx th');
for (i = 0; i < cells.length; i++) { r = cells[i].getBoundingClientRect(); if (r.width < 56 || r.height < 56) { small.push('cell ' + Math.round(r.width) + 'x' + Math.round(r.height)); } }
for (i = 0; i < vals.length; i++) { r = vals[i].getBoundingClientRect(); if (r.width < 56 || r.height < 56) { small.push('value ' + Math.round(r.width) + 'x' + Math.round(r.height)); } }
for (i = 0; i < heads.length; i++) { if (heads[i].scrollWidth > heads[i].clientWidth + 1) { bad.push('head cut: ' + heads[i].textContent); } }
var tr = table.getBoundingClientRect(), vw = document.documentElement.clientWidth;
out.fit = {small: small, bad: bad, tableRight: Math.round(tr.right), tableLeft: Math.round(tr.left), vw: vw, scrollW: document.documentElement.scrollWidth,
           tableH: Math.round(tr.height), cells: cells.length};
"""


def fit_part(exe, tmp):
    print("\n-- 6 rows x 5 columns on the two tablets")
    os.makedirs(os.path.join(tmp, "f"))
    c, md = tcm.new_course(os.path.join(tmp, "f"), tcm.script(screens=[tcm.EVERY_WAY[0], big(6, 5), CHOICE]), build=False)
    tcm.cs.save(os.path.join(c, "working_claude", "script", "M01.build.json"), {"module": 1, "screens": {"t01": {"try_tablet": False}}})
    code, out = tcm.run(tcm.COMPILE, c, "--module", "1", "--only", "tasks")
    page = os.path.join(md, "tasks", "sc1_every_way.html")
    check("a 6 x 5 grid builds", code == 0 and os.path.isfile(page), out[-600:])
    for size in ((1280, 800), (1024, 768)):
        r = tte.drive(exe, page, [["eval", FIT]], tmp, look=False, size=size)
        f = r.get("fit") or {}
        check("%dx%d: 30 cells, every tap target at least 56 px, no heading cut" % size,
              f.get("cells") == 30 and not f.get("small") and not f.get("bad"), (f, r.get("errors")))
        check("%dx%d: the table inside the screen, no sideways scroll" % size,
              f.get("tableLeft", -1) >= 0 and f.get("tableRight", 9999) <= f.get("vw", 0) and f.get("scrollW", 9999) <= f.get("vw", 0) + 1, f)


def main():
    script_part()
    tmp = tempfile.mkdtemp(prefix="matrix_")
    try:
        build_part(tmp)
        exe = drawing_check.find_browser()
        if not exe:
            print("  skip  no Chrome or Edge found - the engine was not driven")
        else:
            engine_part(exe, tmp)
            fit_part(exe, tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("\n%d passed, %d failed" % (len(PASS), len(FAIL)))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
