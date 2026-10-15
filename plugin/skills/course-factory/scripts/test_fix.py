# -*- coding: utf-8 -*-
"""test_fix - fast fixes across modules, with the quality kept (L50, 2.29.0).

    python test_fix.py

A temp course with three built modules (modules\\module01..03, presentation\\index.html + tasks\\t1.html),
each built from an approved content script so check_script_match passes before any fix. Pinned:
  * propose: changes for two modules -> each module's pending list and working_claude\\fix\\batch.json, ONE
    combined list; no script and no built page changes yet; a screen that does not exist stops it;
  * apply: refuses without --confirmed; with it the scripts change, FEEDBACK_LOG gets a row per change,
    the built slides get the new title (h2 AND data-title), text lines and notes (data-cue); the untouched
    module stays byte-identical; the changed modules are drafts again;
  * hand work: a text change whose line count differs, or a changed line with formatting inside it, is
    listed as hand work and that slide is left exactly as it was;
  * approve --by: every module of the batch approved at once, batch.json archived; check_script_match then
    passes for the changed modules - the built slides say exactly the approved words; fix.py check --kind
    words passes;
  * sweep: words, kind, last-slide --like (same design / different design / no end slide), each written
    to working_claude\\fix\\sweep_<find>_*.json;
  * standard: numbered S1, S2 ... in working_claude\\STANDARDS.md, and listed;
  * sync-shared: a dry run changes nothing, --confirmed copies, a second run has nothing to do, shared.json
    sends a file elsewhere in the module, a .md beside the shared files is never copied;
  * measure_slides (only when Chrome or Edge is installed): a nearly empty slide has little ink, a 10 px
    slide's smallest text is under 16 px, an overflowing slide runs off the screen, at exactly 1280 x 800.
"""
from __future__ import annotations

import contextlib
import copy
import glob
import html
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
TOOL = os.path.join(HERE, "fix.py")
MATCH = os.path.join(HERE, "check_script_match.py")
TEMPLATE_LOG = os.path.join(os.path.dirname(HERE), "templates", "FEEDBACK_LOG.md")
sys.path.insert(0, HERE)
import content_script as cs  # noqa: E402
import measure_slides as ms  # noqa: E402
import test_content_script as tcs  # noqa: E402  - the example module that validates and passes every theory floor

PASS, FAIL = [], []


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print(("  ok    " if ok else "  FAIL  ") + name + (("  -> " + str(detail)[:500]) if detail and not ok else ""))


def run(*a):
    p = subprocess.run([sys.executable] + list(a), capture_output=True, text=True, encoding="utf-8", errors="replace")
    return p.returncode, p.stdout + p.stderr


def fix(*a):
    return run(TOOL, *a)


def read(p):
    return io.open(p, encoding="utf-8", newline="").read()


def raw(p):
    with open(p, "rb") as f:
        return f.read()


def screen(script, sid):
    return [x for x in script["screens"] if x["id"] == sid][0]


# ---------------------------------------------------------------- the built module, marked as check_script_match reads it

END_A = ('<section class="slide" id="end" data-kind="Hand-off" data-title="Module complete">'
         '<div class="end-wrap"><h2 class="end-title">Module complete</h2>'
         '<ul class="recap-list"><li class="recap-item">Cargo kept cold or under pressure</li>'
         '<li class="recap-item">Four containment systems</li></ul><div class="end-cta">Next module</div></div></section>')
END_B = ('<section class="slide" id="end" data-kind="Hand-off" data-title="Module complete">'
         '<div class="thanks-box"><p class="big-tick">Well done</p></div></section>')


def cue(notes):
    return " ".join(x[2:] if x.startswith(("- ", "* ")) else x for x in cs.note_lines(notes))


def slide_html(n, x, strong_first=False):
    e = lambda t: html.escape(t, quote=False)
    lines = []
    for i, ln in enumerate((x.get("text") or "").split("\n")):
        body = e(ln)
        if strong_first and i == 0:                        # a line with formatting inside it
            w = ln.split(" ")
            body = "<strong>%s</strong> %s" % (e(" ".join(w[:2])), e(" ".join(w[2:])))
        lines.append('      <p data-script-field="text">%s</p>\n' % body)
    kind = "Task" if x["kind"] == "task-slide" else "Theory"
    return ('  <section class="slide" id="sl%02d" data-script="%s" data-kind="%s" data-title="%s" data-cue="%s">\n'
            '    <div class="slide-kind">%s</div>\n    <h2 data-script-field="title">%s</h2>\n    <div class="body">\n%s    </div>\n'
            '  </section>\n' % (n, x["id"], kind, html.escape(x["title"], quote=True), html.escape(cue(x.get("notes")), quote=True),
                                kind, e(x["title"]), "".join(lines)))


def task_html(x):
    opts = "".join('<button data-script-field="opt.%s"%s>%s</button>' % (L, ' data-correct="true"' if L in cs.correct_letters(x) else "", o)
                   for L, o in zip(cs.letters(len(x.get("options", []))), x.get("options", []))) if cs.uses(x, "options") else ""
    if cs.uses(x, "answer") and cs.mech(x) != "set_value":
        items, right = cs.answer_items(x)
        opts += "".join('<span data-script-field="answer"%s>%s</span>' % (' data-correct="true"' if right and t in right else "", t)
                        for t in reversed(items))
    return ('<div data-script="%s"><p data-script-field="question">%s</p>%s<p data-script-field="feedback">%s</p></div>\n'
            % (x["id"], x["question"], opts, x["feedback"]))


def build_module(course, m, script, end=None, strong_first=False):
    mdir = os.path.join(course, "modules", "module%02d" % m)
    os.makedirs(os.path.join(mdir, "presentation"), exist_ok=True)
    os.makedirs(os.path.join(mdir, "tasks"), exist_ok=True)
    sl = [x for x in script["screens"] if x["kind"] in cs.INSTRUCTOR]
    deck = ('<!DOCTYPE html>\n<html lang="en">\n<head><meta charset="utf-8"><title>Module %d</title></head>\n<body>\n<main id="deck">\n%s%s</main>\n'
            '<button id="btnNext">Next</button>\n</body>\n</html>\n'
            % (m, "".join(slide_html(i + 1, x, strong_first and x["id"] == "s01") for i, x in enumerate(sl)), ("  " + end + "\n") if end else ""))
    io.open(os.path.join(mdir, "presentation", "index.html"), "w", encoding="utf-8", newline="").write(deck)
    io.open(os.path.join(mdir, "tasks", "t1.html"), "w", encoding="utf-8", newline="").write(
        "<!DOCTYPE html>\n<html><body>\n%s</body></html>\n" % "".join(task_html(x) for x in script["screens"] if x["kind"] in cs.TASKS))
    return mdir


def new_course(tmp):
    c = os.path.join(tmp, "course")
    os.makedirs(os.path.join(c, "working_claude", "script"))
    os.makedirs(os.path.join(c, "to_review"))
    shutil.copyfile(TEMPLATE_LOG, os.path.join(c, "working_claude", "FEEDBACK_LOG.md"))
    for m, end, strong in ((1, END_A, False), (2, END_B, True), (3, None, False)):
        s = copy.deepcopy(tcs.SCRIPT)
        s["module"] = m
        s.update(status="approved", approved_by="Anna", approved_on="2026-10-14", approved_hash=cs.content_hash(s))
        cs.save(cs.paths(c, m)["script"], s)
        build_module(c, m, s, end, strong)
    return c


def deck(c, m):
    return os.path.join(c, "modules", "module%02d" % m, "presentation", "index.html")


def section(text, sid):
    m = re.search(r'<section[^>]*data-script="%s".*?</section>' % re.escape(sid), text, re.S)
    return m.group(0) if m else ""


def last_sweep(c):
    p = io.open(os.path.join(c, "working_claude", "fix", "last_sweep.txt"), encoding="utf-8").read().strip()
    return p, cs.load(p)


def write_changes(tmp, name, changes):
    p = os.path.join(tmp, name)
    io.open(p, "w", encoding="utf-8", newline="\n").write(json.dumps(changes, ensure_ascii=False))
    return p


# ---------------------------------------------------------------- the measurement deck

MEASURE_DECK = """<!DOCTYPE html><html><head><meta charset="utf-8"><style>
html, body { margin: 0; height: 100%; overflow: hidden; font-family: Arial, sans-serif; background: #fff; }
.slide { position: absolute; left: 0; top: 0; width: 100vw; height: 100vh; display: none; overflow: hidden; box-sizing: border-box; }
.slide.active { display: block; }
#btnNext { position: fixed; right: 4px; bottom: 4px; width: 4px; height: 4px; padding: 0; border: 0; opacity: 0.01; }
</style></head><body>
<section class="slide active" id="empty" data-title="Nearly empty" data-kind="Theory"><h2 style="font-size:24px;margin:20px">Hi</h2></section>
<section class="slide" id="tiny" data-title="Tiny text" data-kind="Theory">
  <h2 style="font-size:32px;margin:20px">Small print</h2>
  <p style="font-size:10px;margin:20px">This line is set at ten pixels and nobody at the back of the room can read it.</p></section>
<section class="slide" id="spill" data-title="Too much" data-kind="Theory">
  <p style="font-size:40px;line-height:60px;margin:20px">@SPILL@</p></section>
<button id="btnNext" onclick="var s=[].slice.call(document.querySelectorAll('.slide')),i=s.indexOf(document.querySelector('.slide.active'));
if(i<s.length-1){s[i].classList.remove('active');s[i+1].classList.add('active');}if(i+1>=s.length-1){this.disabled=true;}">Next</button>
</body></html>
""".replace("@SPILL@", " ".join(["The cargo is carried cold, under pressure, or both, and every system on board keeps it that way."] * 25))


def main():
    tmp = tempfile.mkdtemp(prefix="fix_")
    try:
        c = new_course(tmp)
        fb_path = os.path.join(c, "working_claude", "FEEDBACK_LOG.md")
        fixdir = os.path.join(c, "working_claude", "fix")

        print("-- the course: three built modules, each from an approved script")
        for m in (1, 2, 3):
            code, out = run(MATCH, c, "--module", str(m))
            check("module %d says exactly the approved words before any fix" % m, code == 0, out)

        print("\n-- 1 FIND: sweep reads every module at once")
        code, out = fix("sweep", c, "--find", "words", "--words", "boil-off never stops")
        p, sw = last_sweep(c)
        check("words in the instructor notes are found in every module", code == 0
              and sorted(f["module"] for f in sw["found"]) == [1, 2, 3]
              and all("instructor notes" in f["problem"] and f["slide"] == "sl01" for f in sw["found"]), out)
        check("the sweep is written under working_claude\\fix\\, named for what it looked for",
              os.path.dirname(p) == fixdir and os.path.basename(p).startswith("sweep_words_") and sw["find"] == "words", p)
        code, out = fix("sweep", c, "--find", "words", "--words", "FOUR CONTAINMENT", "--modules", "2")
        _, sw = last_sweep(c)
        check("--modules limits the sweep, and the words are found on the slide and in the title, any case",
              code == 0 and {f["module"] for f in sw["found"]} == {2} and sw["modules"] == [2]
              and {f["problem"].split(":")[0] for f in sw["found"]} == {"on the slide", "in the title"}, out)
        code, out = fix("sweep", c, "--find", "words", "--words", "no such words anywhere")
        check("words nowhere: nothing found", code == 0 and "Nothing found." in out and last_sweep(c)[1]["found"] == [], out)
        code, out = fix("sweep", c, "--find", "words")
        check("a words sweep without --words stops", code == 2 and "--words" in out, out)
        code, out = fix("sweep", c, "--find", "kind", "--kind", "task")
        _, sw = last_sweep(c)
        check("every Task slide is found - two in each module, kind matched in any case",
              code == 0 and len(sw["found"]) == 6 and {f["slide_kind"] for f in sw["found"]} == {"Task"}
              and sorted({f["module"] for f in sw["found"]}) == [1, 2, 3] and os.path.basename(last_sweep(c)[0]).startswith("sweep_kind_"), out)
        code, out = fix("sweep", c, "--find", "kind", "--kind", "Task", "--modules", "2-3")
        check("... and a range of modules is honoured", code == 0 and {f["module"] for f in last_sweep(c)[1]["found"]} == {2, 3}, out)
        code, out = fix("sweep", c, "--find", "kind")
        check("a kind sweep without --kind stops", code == 2 and "--kind" in out, out)
        code, out = fix("sweep", c, "--find", "last-slide", "--like", "1")
        _, sw = last_sweep(c)
        by = {f["module"]: f for f in sw["found"]}
        check("last slide like module 1: module 1 is already right", by.get(1, {}).get("ok") is True and "Already right in module(s): 1" in out, out)
        check("... module 2's end slide has a different design", by.get(2, {}).get("ok") is False and "different design from module 1" in by[2]["problem"], by.get(2))
        check("... module 3 has no end slide - its last slide is the module check's task slide",
              by.get(3, {}).get("ok") is False and by[3]["problem"].startswith("no end slide") and by[3]["slide_kind"] == "Task", by.get(3))
        check("... and the list numbers only the two to fix", re.search(r"Found - 2 place\(s\)", out) is not None, out)
        code, out = fix("sweep", c, "--find", "sparkle")
        check("an unknown sweep stops and says what it can look for", code == 2 and "last-slide" in out, out)
        code, out = fix("sweep", c, "--find", "words", "--words", "x", "--modules", "7")
        check("a sweep of modules that are not built stops", code == 2 and "no built modules" in out, out)

        print("\n-- 2 ONE YES: propose words for two modules")
        scripts_before = {m: raw(cs.paths(c, m)["script"]) for m in (1, 2, 3)}
        decks_before = {m: raw(deck(c, m)) for m in (1, 2, 3)}
        tasks_before = {m: raw(os.path.join(c, "modules", "module%02d" % m, "tasks", "t1.html")) for m in (1, 2, 3)}
        new_notes = ("- Ask who has sailed on an LPG or LNG carrier.\n"
                     "- Ask: what happens to liquid at -162 °C on a warm steel deck?\n"
                     "- Stress: boil-off never stops; it is managed.")
        s02_lines = tcs.S02_TEXT.split("\n")
        s02_new = "\n".join(s02_lines[:3] + ["The colder the cargo, the lower the pressure the tank must hold - and the more insulation and boil-off handling the ship needs."])
        s03_lines = tcs.S03_TEXT.split("\n")
        s03_new = "\n".join(["The IGC Code names four systems for containing the cargo."] + s03_lines[1:])
        changes = [{"module": 1, "field": "s03.title", "new": "The four containment systems"},
                   {"module": 1, "field": "s01.notes", "new": new_notes},
                   {"module": 1, "screen": "s02", "field": "text", "new": s02_new},
                   {"module": 2, "field": "t01.title", "new": "Self-check 1 - why the cargo stays liquid"},
                   {"module": 2, "field": "s03.text", "new": s03_new}]
        bad = write_changes(tmp, "bad.json", [{"module": 3, "field": "s99.title", "new": "x"}])
        code, out = fix("propose", c, "--changes", bad)
        check("a screen the module does not have stops propose", code == 2 and "no screen 's99'" in out and not os.path.isfile(os.path.join(fixdir, "batch.json")), out)
        code, out = fix("propose", c, "--changes", write_changes(tmp, "nomod.json", [{"field": "s01.title", "new": "x"}]))
        check("a change without its module stops propose", code == 2 and "\"module\"" in out, out)
        code, out = fix("propose", c, "--changes", write_changes(tmp, "changes.json", changes))
        batch = cs.load(os.path.join(fixdir, "batch.json")) if os.path.isfile(os.path.join(fixdir, "batch.json")) else {}
        check("propose writes each module's pending list", code == 0 and os.path.isfile(cs.paths(c, 1)["pending"])
              and os.path.isfile(cs.paths(c, 2)["pending"]) and not os.path.isfile(cs.paths(c, 3)["pending"]), out)
        check("... and batch.json lists both modules", batch.get("modules") == [1, 2], batch)
        check("... ONE combined list, every change named by its module, nothing changed yet",
              "5 change(s) in 2 module(s), nothing changed yet" in out and out.count("Module 1 - ") == 3 and out.count("Module 2 - ") == 2
              and 'the title becomes "The four containment systems" (was "Four containment systems")' in out, out)
        pend1 = cs.load(cs.paths(c, 1)["pending"])
        check("the pending list keeps the old words and the script's hash, like content_script propose",
              pend1["base_hash"] == cs.content_hash(cs.load(cs.paths(c, 1)["script"])) and pend1["source"] == "chat"
              and [x["old"] for x in pend1["changes"]][0] == "Four containment systems", pend1)
        check("no script changed", all(raw(cs.paths(c, m)["script"]) == scripts_before[m] for m in (1, 2, 3)))
        check("no built page changed", all(raw(deck(c, m)) == decks_before[m] for m in (1, 2, 3)))

        print("\n-- 3 CHANGE: apply")
        code, out = fix("apply", c)
        check("apply refuses without --confirmed - and changes nothing", code == 2 and "--confirmed" in out
              and all(raw(cs.paths(c, m)["script"]) == scripts_before[m] for m in (1, 2, 3)), out)
        fb_rows_before = len(re.findall(r"^\|\s*\d+\s*\|", read(fb_path), re.M))
        code, out = fix("apply", c, "--confirmed")
        s1, s2, s3 = (cs.load(cs.paths(c, m)["script"]) for m in (1, 2, 3))
        check("apply --confirmed changes the scripts", code == 0 and screen(s1, "s03")["title"] == "The four containment systems"
              and screen(s1, "s01")["notes"] == new_notes and screen(s1, "s02")["text"] == s02_new
              and screen(s2, "t01")["title"].endswith("why the cargo stays liquid") and screen(s2, "s03")["text"] == s03_new, out)
        check("... the pending lists are used up", not os.path.isfile(cs.paths(c, 1)["pending"]) and not os.path.isfile(cs.paths(c, 2)["pending"]))
        fb = read(fb_path)
        rows = re.findall(r"^\|\s*\d+\s*\|.*$", fb, re.M)
        check("... FEEDBACK_LOG gets one row per change, numbered on from the template's row",
              len(rows) == fb_rows_before + 5 and rows[-1].startswith("| 6 |") and sum("3 · M01 ·" in r for r in rows) == 3
              and sum("3 · M02 ·" in r for r in rows) == 2 and all("(chat)" in r for r in rows[-5:]), rows)
        check("... the changed modules are drafts again, the untouched one still approved",
              s1["status"] == "draft" and s2["status"] == "draft" and s3["status"] == "approved")
        check("... a fresh review page for each changed module", os.path.isfile(cs.paths(c, 1)["review"]) and os.path.isfile(cs.paths(c, 2)["review"]))
        check("... and the built slides are counted, with no hand work", "5 place(s) on the built slides" in out and "hand work" not in out, out)
        d1, d2 = read(deck(c, 1)), read(deck(c, 2))
        sec = section(d1, "s03")
        check("the new title is in the slide's h2 AND its data-title (the header band reads it)",
              '<h2 data-script-field="title">The four containment systems</h2>' in sec and 'data-title="The four containment systems"' in sec, sec[:300])
        sec = section(d1, "s01")
        check("the new notes are in data-cue, as one line without the bullets",
              'data-cue="%s"' % html.escape(cue(new_notes), quote=True) in sec and "LPG or LNG carrier" in sec, sec[:400])
        sec = section(d1, "s02")
        check("the changed text line is replaced, the other lines left as they were",
              '<p data-script-field="text">The colder the cargo, the lower the pressure' in sec
              and all('<p data-script-field="text">%s</p>' % html.escape(x, quote=False) in sec for x in s02_lines[:3]), sec)
        sec = section(d2, "t01")
        check("module 2: a task slide's title, in h2 and data-title",
              'data-title="Self-check 1 - why the cargo stays liquid"' in sec and ">Self-check 1 - why the cargo stays liquid</h2>" in sec, sec[:300])
        check("module 2: the first text line of s03 is replaced", '<p data-script-field="text">The IGC Code names four systems for containing the cargo.</p>' in section(d2, "s03"))
        check("module 2: the line with formatting inside it, not changed, keeps its formatting",
              "<strong>Liquefied gases</strong>" in section(d2, "s01"))
        check("everything else in the deck is byte for byte as it was", d1.count("\n") == read_lines(decks_before[1])
              and section(d1, "s03").replace("The four containment systems", "Four containment systems") == section(decks_before[1].decode("utf-8"), "s03"))
        check("the untouched module 3 is byte-identical - deck and tasks", raw(deck(c, 3)) == decks_before[3]
              and raw(os.path.join(c, "modules", "module03", "tasks", "t1.html")) == tasks_before[3])
        check("the task pages of the changed modules are untouched (no task words changed)",
              all(raw(os.path.join(c, "modules", "module%02d" % m, "tasks", "t1.html")) == tasks_before[m] for m in (1, 2)))
        code, out = run(MATCH, c, "--module", "1")
        check("before approval check_script_match still fails: the script is a draft", code == 1 and "not approved" in out, out)

        print("\n-- approve: one approval for the whole batch")
        code, out = fix("approve", c, "--by", "Anna")
        s1, s2 = cs.load(cs.paths(c, 1)["script"]), cs.load(cs.paths(c, 2)["script"])
        check("every module of the batch is approved by the operator named", code == 0 and all(
            x["status"] == "approved" and x["approved_by"] == "Anna" and x["approved_hash"] == cs.content_hash(x) for x in (s1, s2)), out)
        check("... batch.json is archived", not os.path.isfile(os.path.join(fixdir, "batch.json"))
              and len(glob.glob(os.path.join(fixdir, "batch_done_*.json"))) == 1
              and cs.load(glob.glob(os.path.join(fixdir, "batch_done_*.json"))[0]).get("applied"), os.listdir(fixdir))
        for m in (1, 2, 3):
            code, out = run(MATCH, c, "--module", str(m))
            check("check_script_match: module %d's built slides say exactly the approved words" % m, code == 0, out)
        code, out = fix("check", c, "--kind", "words")
        check("fix.py check --kind words passes after approval", code == 0 and "The check passed" in out, out)
        code, out = fix("check", c, "--kind", "words", "--modules", "1")
        check("... and on one module only", code == 0 and "Module 1, words" in out and "Module 2" not in out, out)
        code, out = fix("approve", c, "--by", "Anna")
        check("approve with no batch waiting says so", code == 2 and "no batch" in out, out)
        code, out = fix("apply", c, "--confirmed")
        check("apply with no list waiting says so", code == 2 and "Nothing to apply" in out, out)
        code, out = fix("check", c, "--kind", "sparkle")
        check("an unknown check stops", code == 2 and "words, layout, package" in out, out)

        print("\n-- hand work: what apply will not guess")
        before = {m: raw(deck(c, m)) for m in (1, 2)}
        s01_lines = tcs.S01_TEXT.split("\n")
        hand = [{"module": 1, "field": "s02.text", "new": "\n".join(s02_lines[:3])},                 # 4 lines -> 3
                {"module": 2, "field": "s01.text", "new": "\n".join(["Liquefied gases travel as liquids only because the ship keeps them cold, under pressure, or both."] + s01_lines[1:])}]
        fix("propose", c, "--changes", write_changes(tmp, "hand.json", hand))
        code, out = fix("apply", c, "--confirmed")
        check("a text change with a different number of lines is hand work, named by module and slide",
              code == 0 and re.search(r"hand work: Module 1, .*has 4 text line\(s\) and the new words have 3", out) is not None, out)
        check("a changed line with formatting inside it is hand work",
              re.search(r"hand work: Module 2, .*formatting inside it", out) is not None and "0 place(s) on the built slides" in out, out)
        check("... and both slides are left exactly as they were", raw(deck(c, 1)) == before[1] and raw(deck(c, 2)) == before[2])
        check("... while the scripts did change (the operator said yes) - so the words check now fails until the hand work is done",
              screen(cs.load(cs.paths(c, 1)["script"]), "s02")["text"] == "\n".join(s02_lines[:3])
              and fix("check", c, "--kind", "words", "--modules", "1")[0] == 1)

        print("\n-- standards: what the operator decided once")
        code, out = fix("standard", c)
        check("no standards yet", code == 0 and "no standards yet" in out, out)
        code, out = fix("standard", c, "--add", "The last slide of every module is the recap end slide of module 1.", "--said", "the last slide like this")
        sp = os.path.join(c, "working_claude", "STANDARDS.md")
        check("the first standard is S1, in working_claude\\STANDARDS.md", code == 0 and "S1 written" in out and os.path.isfile(sp), out)
        code, out = fix("standard", c, "--add", "Body text is at least 22 px at 1280 x 800.")
        st = read(sp)
        check("the second is S2", code == 0 and "S2 written" in out and re.search(r"^S1 The last slide", st, re.M)
              and re.search(r"^S2 Body text", st, re.M), st)
        check("the operator's own words are kept with it", 'operator: "the last slide like this"' in st, st)
        code, out = fix("standard", c)
        check("listing shows both", code == 0 and "S1 The last slide" in out and "S2 Body text" in out, out)

        print("\n-- sync-shared: one copy -> every module")
        code, out = fix("sync-shared", c)
        check("no shared folder yet: it says where to put one", code == 2 and "no shared folder" in out, out)
        sh = os.path.join(c, "working_claude", "shared")
        os.makedirs(sh)
        io.open(os.path.join(sh, "end-recap.js"), "w", encoding="utf-8", newline="\n").write("window.recap = 1;\n")
        io.open(os.path.join(sh, "viewer.css"), "w", encoding="utf-8", newline="\n").write(".viewer { inset: 0; }\n")
        io.open(os.path.join(sh, "README.md"), "w", encoding="utf-8", newline="\n").write("what these are\n")
        io.open(os.path.join(sh, "shared.json"), "w", encoding="utf-8", newline="\n").write(json.dumps({"viewer.css": "presentation/viewer.css"}))
        mdirs = [os.path.join(c, "modules", "module%02d" % m) for m in (1, 2, 3)]
        snap = lambda: sorted(os.path.relpath(os.path.join(r, f), c) for r, _, fs in os.walk(os.path.join(c, "modules")) for f in fs)
        files_before = snap()
        code, out = fix("sync-shared", c)
        check("a dry run lists every copy and changes nothing", code == 0 and out.count("is added") == 6 and "--confirmed" in out
              and snap() == files_before, out)
        code, out = fix("sync-shared", c, "--confirmed")
        check("--confirmed copies into each module's assets\\", code == 0 and all(
            read(os.path.join(d, "assets", "end-recap.js")) == "window.recap = 1;\n" for d in mdirs), out)
        check("... and shared.json sends a file where it says", all(os.path.isfile(os.path.join(d, "presentation", "viewer.css"))
                                                                  and not os.path.exists(os.path.join(d, "assets", "viewer.css")) for d in mdirs))
        check("... a .md and shared.json itself are never copied", not any(
            os.path.exists(os.path.join(d, "assets", n)) for d in mdirs for n in ("README.md", "shared.json")))
        code, out = fix("sync-shared", c, "--confirmed")
        check("a second run has nothing to do", code == 0 and "already has the current copy of the 2 shared file(s)" in out, out)
        io.open(os.path.join(mdirs[1], "assets", "end-recap.js"), "w", encoding="utf-8", newline="\n").write("window.recap = 'edited by hand';\n")
        io.open(os.path.join(sh, "viewer.css"), "w", encoding="utf-8", newline="\n").write(".viewer { inset: 0; z-index: 9; }\n")
        code, out = fix("sync-shared", c)
        check("a changed shared file and one module's stale copy are found - and named as replaced",
              code == 0 and out.count("is replaced") == 4 and "Module 2: end-recap.js is replaced" in out
              and "Module 1: end-recap.js" not in out, out)
        code, out = fix("sync-shared", c, "--confirmed")
        check("... and put right", code == 0 and all(read(os.path.join(d, "presentation", "viewer.css")).count("z-index") == 1 for d in mdirs)
              and read(os.path.join(mdirs[1], "assets", "end-recap.js")) == "window.recap = 1;\n", out)

        print("\n-- measure_slides: three slides measured in a hidden browser")
        browser = ms.find_browser()
        if not browser:
            print("  note  no Chrome or Edge on this computer - the measurement test is skipped")
        else:
            d = os.path.join(tmp, "mdeck", "modules", "module01", "presentation")
            os.makedirs(d)
            io.open(os.path.join(d, "index.html"), "w", encoding="utf-8", newline="\n").write(MEASURE_DECK)
            res = ms.measure([os.path.join(d, "index.html")], workers=1, timeout=120)
            r = list(res.values())[0]
            sl = {s["id"]: s for s in r.get("slides", [])}
            check("all three slides measured, by pressing Next, with no errors",
                  not r.get("error") and not r.get("errors") and sorted(sl) == ["empty", "spill", "tiny"]
                  and all(s.get("steps", 0) >= 1 for s in sl.values()), r)
            check("the hidden window shows exactly 1280 x 800", r.get("viewport") == [1280, 800], r.get("viewport"))
            e = sl.get("empty", {})
            check("the nearly empty slide carries little ink", e.get("ink") is not None and e["ink"] < 0.1 and (e.get("empty_bottom") or 0) > 0.8, e)
            t = sl.get("tiny", {})
            check("the slide with 10 px text: smallest text under 16 px", t.get("min_text") is not None and t["min_text"] < 16
                  and t.get("small_text", 0) >= 1 and "ten pixels" in t.get("min_text_sample", ""), t)
            o = sl.get("spill", {})
            check("the overflowing slide runs off the screen", (o.get("overflow") or 0) > 8, o)
            check("the slides that fit do not", e.get("overflow") == 0 and t.get("overflow") == 0, (e.get("overflow"), t.get("overflow")))
            check("titles and kinds come from the deck", e.get("title") == "Nearly empty" and e.get("kind") == "Theory" and o.get("n") == 3, e)
            check("measure_slides finds a module's deck in presentation\\index.html",
                  ms.deck_of(os.path.dirname(d)) == os.path.abspath(os.path.join(d, "index.html")))
        regressions(os.path.join(tmp, "reg"))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("\n" + "=" * 72)
    print("%d passed, %d failed" % (len(PASS), len(FAIL)))
    if FAIL:
        return 1
    print("\nA fix finds every place at once, shows one list, changes the approved words and the built slides\n"
          "together after one yes, leaves what it cannot do without guessing as hand work, and is checked once.")
    return 0


def read_lines(b):
    return b.decode("utf-8").count("\n")


# ---------------------------------------------------------------- regressions found by the first run of this test (2.29.0)

def quiet(fn, *a):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = fn(*a)
    return rc, buf.getvalue()


def regressions(tmp):
    import fix as fx
    os.makedirs(tmp)

    print("\n-- regression 1: a line separator other than \\n earlier in the page does not shift where words are written")
    for sep, name in ((" ", "U+2028"), ("\r", "a lone CR"), ("\x0c", "a form feed")):
        d = os.path.join(tmp, "sep_%d" % ord(sep))
        os.makedirs(d)
        page = ('<html><body><p>intro%sline</p>\n<section class="slide" id="sl01" data-script="s01" data-kind="Theory" '
                'data-title="Old" data-cue="say it">\n<h2 data-script-field="title">Old</h2>\n<p data-script-field="text">one</p>\n'
                '</section></body></html>' % sep)
        io.open(os.path.join(d, "index.html"), "w", encoding="utf-8", newline="").write(page)
        why = fx.put_words(d, "s01", "title", "New title")
        got = io.open(os.path.join(d, "index.html"), encoding="utf-8", newline="").read()
        want = page.replace('data-title="Old"', 'data-title="New title"').replace(">Old</h2>", ">New title</h2>")
        check("%s before the slide: title and data-title written in the right place, the rest of the tag intact" % name,
              why == "" and got == want, (why, got))

    print("\n-- regression 3 and 4: propose writes nothing unless every change can be made")
    c = new_course(os.path.join(tmp, "p"))
    fixdir = os.path.join(c, "working_claude", "fix")
    ch = write_changes(tmp, "unknown2.json", [{"module": 1, "field": "s01.title", "new": "X"}, {"module": 2, "field": "s99.title", "new": "Y"}])
    code, out = fix("propose", c, "--changes", ch)
    check("an unknown screen in module 2 stops propose - no pending list for module 1, no batch.json",
          code == 2 and not os.path.isfile(cs.paths(c, 1)["pending"]) and not os.path.isfile(cs.paths(c, 2)["pending"])
          and not os.path.isfile(os.path.join(fixdir, "batch.json")), out)
    word = write_changes(tmp, "word.json", [{"field": "s01.title", "new": "From the Word file"}])
    quiet(cs.cmd_propose, c, 1, word)                               # the operator's Word edits, waiting
    waiting = raw(cs.paths(c, 1)["pending"])
    code, out = fix("propose", c, "--changes", write_changes(tmp, "over.json", [{"module": 1, "field": "s02.title", "new": "From fix"},
                                                                                 {"module": 2, "field": "s02.title", "new": "Z"}]))
    check("a module with a pending list already waiting stops propose (rc 2)", code == 2 and "already has understood changes waiting" in out, out)
    check("... that pending list is byte-identical, and nothing else was written",
          raw(cs.paths(c, 1)["pending"]) == waiting and not os.path.isfile(cs.paths(c, 2)["pending"])
          and not os.path.isfile(os.path.join(fixdir, "batch.json")))
    quiet(cs.cmd_discard, c, 1)

    print("\n-- regression 5: a removed standard's number is never used again")
    for r in ("one", "two", "three"):
        quiet(fx.cmd_standard, c, r, None)
    sp = os.path.join(c, "working_claude", "STANDARDS.md")
    kept = re.sub(r"\nS2 two[^\n]*\n", "\n", read(sp))             # the operator removes S2
    io.open(sp, "w", encoding="utf-8", newline="\n").write(kept)
    quiet(fx.cmd_standard, c, "four", None)
    got = re.findall(r"^S\d+ \w+", read(sp), re.M)
    check("S1, S2, S3 with S2 removed -> the next is S4", got == ["S1 one", "S3 three", "S4 four"], got)

    print("\n-- minor: what apply does with task words and minutes")
    tasks1 = os.path.join(c, "modules", "module01", "tasks", "t1.html")
    before = (raw(deck(c, 1)), raw(tasks1))
    ch = write_changes(tmp, "task.json", [{"module": 1, "field": "q01.question", "new": "At what temperature is LNG carried at about atmospheric pressure?"},
                                          {"module": 1, "field": "q01.opt.B", "new": "At ambient temperature, under pressure"},
                                          {"module": 1, "field": "s01.minutes", "new": "6"},
                                          {"module": 1, "field": "s02.minutes", "new": "4"}])
    fix("propose", c, "--changes", ch)
    code, out = fix("apply", c, "--confirmed")
    hand = [x for x in out.splitlines() if "hand work" in x]
    check("a task's question and answer option are hand work, naming the trainee page",
          code == 0 and len(hand) == 2 and all("trainee page" in x for x in hand) and "question" in hand[0] and "opt.B" in hand[1], out)
    check("a minutes change is not hand work - it is not on the slide face", not any("minutes" in x for x in hand)
          and "2 place(s) on the built slides" in out, out)
    check("... and neither the deck nor the trainee page was touched", (raw(deck(c, 1)), raw(tasks1)) == before)
    quiet(fx.cmd_approve, c, "Anna", True)

    print("\n-- minor: last slides with no design classes at all are alike")
    for m in (1, 2):
        dk = deck(c, m)
        t = re.sub(r'  <section class="slide" id="end".*?</section>\n', "", read(dk), flags=re.S)
        t = t.replace("</main>", '  <section class="slide" id="end" data-kind="Hand-off" data-title="Module complete"><h2>Module complete</h2></section>\n</main>')
        io.open(dk, "w", encoding="utf-8", newline="").write(t)
    code, out = fix("sweep", c, "--find", "last-slide", "--like", "1", "--modules", "1,2")
    by = {f["module"]: f for f in last_sweep(c)[1]["found"]}
    check("reference and other module both plain: counted alike, both already right",
          code == 0 and by.get(1, {}).get("ok") is True and by.get(2, {}).get("ok") is True and "Already right in module(s): 1, 2" in out, out)

    print("\n-- minor: two sweeps in the same second write two files")
    real_dt = cs.datetime

    class Frozen(real_dt):
        @classmethod
        def now(cls, tz=None):
            return real_dt(2026, 10, 15, 12, 0, 0)
    cs.datetime = Frozen
    try:
        quiet(fx.sweep, c, "words", None, None, None, None, "boil-off")
        quiet(fx.sweep, c, "words", None, None, None, None, "containment")
    finally:
        cs.datetime = real_dt
    files = sorted(glob.glob(os.path.join(fixdir, "sweep_words_20261015_120000*.json")))
    check("both are kept, the second under its own name", len(files) == 2
          and {cs.load(f)["found"][0]["problem"].split(":")[0] for f in files} >= {"in the instructor notes"}, files)

    print("\n-- minor: a re-measure that fails never replaces a measured result")
    real_open, real_cal = ms._open, ms.calibrate
    d = os.path.join(tmp, "fake", "modules", "module01", "presentation")
    os.makedirs(d)
    io.open(os.path.join(d, "index.html"), "w", encoding="utf-8").write("<html><body></body></html>")
    first = {"viewport": [1280, 800], "errors": [], "slides": [{"id": "a", "n": 1, "ink": 0}, {"id": "b", "n": 2, "ink": 0.5}]}
    for name, answers, want in (("a good first result (half its slides at 0 ink) is kept when the re-measure times out", [first, None], first),
                                ("... and a failed first result is replaced by a good re-measure", [None, first], first)):
        calls = []

        def fake(browser, url, win, token, server, timeout, _a=answers):
            calls.append(url)
            return copy.deepcopy(_a[len(calls) - 1])
        ms._open, ms.calibrate = fake, (lambda browser, server, size: size)
        try:
            res = ms.measure([os.path.join(d, "index.html")], browser="no-browser-needed", timeout=1)
        finally:
            ms._open, ms.calibrate = real_open, real_cal
        check(name, len(calls) == 2 and list(res.values())[0] == want, (calls, res))

    print("\n-- regression 2: a deck whose own script holds \"</body>\" in a string is still driven by Next")
    if not ms.find_browser():
        print("  note  no Chrome or Edge on this computer - skipped")
        return
    d = os.path.join(tmp, "inj", "modules", "module01", "presentation")
    os.makedirs(d)
    t = MEASURE_DECK[:MEASURE_DECK.index('<button id="btnNext"')]
    t += ('<button id="btnNext">Next</button>\n<script>function printable() { return "<html><body>x</body></html>"; }\n'
          "document.getElementById('btnNext').onclick = function () { var s = [].slice.call(document.querySelectorAll('.slide')),"
          " i = s.indexOf(document.querySelector('.slide.active')); if (i < s.length - 1) { s[i].classList.remove('active');"
          " s[i + 1].classList.add('active'); } if (i + 1 >= s.length - 1) { this.disabled = true; } };</script>\n</body></html>\n")
    io.open(os.path.join(d, "index.html"), "w", encoding="utf-8", newline="\n").write(t)
    r = list(ms.measure([os.path.join(d, "index.html")], workers=1, timeout=120).values())[0]
    sl = r.get("slides", [])
    check("every slide is reached by Next - the runner went in before the LAST </body>",
          not r.get("error") and not r.get("errors") and [s["id"] for s in sl] == ["empty", "tiny", "spill"]
          and all(s.get("steps", 0) >= 1 and not s.get("not_reached_by_next") for s in sl), r)


if __name__ == "__main__":
    sys.exit(main())
