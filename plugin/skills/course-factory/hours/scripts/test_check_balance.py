# -*- coding: utf-8 -*-
"""test_check_balance - check_balance.py judges ONE module of a course by its own allocation (2.63.2).

    python -I test_check_balance.py

The IGF full build: every per-module QA agent ran `check_balance.py module.html --programme programme.json`, which
compares the programme's WHOLE-course total row (720 theory / 320 practice minutes) with the one deck and reports a false
FAIL. `--module N` reads the module's own programme topic instead.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "check_balance.py")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
FAILS = []

# a 60-minute module: 40 theory (one block) + 20 practice (one block, all active)
DECK = ('<section class="slide" data-block="b1" data-kind="teaching" data-title="Teach" data-mins="40" '
        'data-track="theory" data-active="8"></section>'
        '<section class="slide" data-block="b2" data-kind="practical" data-title="Do" data-mins="20" '
        'data-track="practice" data-active="20"></section>')
# a three-topic programme of 16 academic hours of 40 min: 12 theory + 4 practical, the module (topic 2) is 1 h + 0.5 h
PROGRAMME = {"academic_hour_min": 40,
             "topics": {"1": {"theory": 10, "practical": 3}, "2.": {"theory": 1, "practical": 0.5},
                        "3": {"theory": 1, "practical": 0.5}},
             "total_row": {"theory": 12, "practical": 4, "total": 16}}


def check(name, ok, detail=""):
    if not ok:
        FAILS.append(name)
    print(("  ok    " if ok else "  FAIL  ") + name + (("  -> " + str(detail)[-600:]) if detail and not ok else ""))


def run(*args):
    p = subprocess.run([sys.executable, "-I", SCRIPT, *args], capture_output=True, text=True, encoding="utf-8", errors="replace")
    return p.returncode, p.stdout + p.stderr


def main():
    tmp = tempfile.mkdtemp(prefix="check_balance_")
    try:
        deck, prog = os.path.join(tmp, "module.html"), os.path.join(tmp, "programme.json")
        with open(deck, "w", encoding="utf-8") as f:
            f.write(DECK)
        with open(prog, "w", encoding="utf-8") as f:
            json.dump(PROGRAMME, f)

        half = os.path.join(tmp, "half", "module.html")
        os.makedirs(os.path.dirname(half))
        with open(half, "w", encoding="utf-8") as f:
            f.write(DECK.replace('data-mins="40"', 'data-mins="39.5"') + '<section class="slide" data-block="b3" '
                    'data-kind="teaching" data-title="Short" data-mins="0.5" data-track="theory" data-active="0"></section>')
        code, out = run(half, "--theory-min", "40", "--practice-min", "20")
        check("2.67.0: a slide of half a minute is counted, never a crash (gas M07 / M15: invalid literal for int(): '0.5')",
              "Traceback" not in out and "ValueError" not in out, out)
        with open(half, "w", encoding="utf-8") as f:
            f.write(DECK.replace('data-mins="20" data-track="practice" data-active="20"',
                                 'data-mins="17.5" data-track="practice" data-active="17.5"')
                    + '<section class="slide" data-block="b3" data-kind="activity" data-title="Half" data-mins="2.5" '
                    'data-track="practice" data-active="2.5"></section>')
        code, out = run(half, "--theory-min", "40", "--practice-min", "20")
        check("a half-minute activity (data-active \"2.5\", \"17.5\") is a number: the module passes",
              code == 0 and "not a number" not in out, out)
        with open(half, "w", encoding="utf-8") as f:
            f.write(DECK.replace('data-active="20"', 'data-active="lots"'))
        code, out = run(half, "--theory-min", "40", "--practice-min", "20")
        check("... a data-active that is not a number still fails", code == 1 and "not a number" in out, out)

        code, out = run(deck, "--programme", prog)
        check("--programme alone: the one deck is judged against the WHOLE course's total row - a false FAIL, and it says so",
              code == 1 and "does not deliver the allocation" in out and "--module N" in out, out)
        code, out = run(deck, "--programme", prog, "--module", "2")
        check("--module 2: the module is judged against its own topic (key \"2.\"): 40 + 20 min, nothing to fix",
              code == 0 and "allocated   theory   40 min   practice   20 min" in out, out)
        code, out = run(deck, "--programme", prog, "--module", "M2")
        check("... \"M2\" reads as module 2", code == 0, out)
        code, out = run(deck, "--programme", prog, "--module", "3")
        check("--module 3 (its own topic is 1 h + 0.5 h too): the same module passes", code == 0, out)
        code, out = run(deck, "--programme", prog, "--module", "1")
        check("--module 1 (10 h + 3 h): a deck that does not deliver THAT allocation still fails",
              code == 1 and "theory -360 min" in out, out)
        code, out = run(deck, "--programme", prog, "--module", "9")
        check("--module 9 with no such topic says so and fails", code == 1 and "no topic 9" in out, out)
        code, out = run(deck, "--module", "2")
        check("--module without --programme or minutes is refused", code == 1 and "--module needs --programme" in out, out)
        code, out = run(deck, "--theory-min", "40", "--practice-min", "20")
        check("--theory-min / --practice-min (the approved table's own minutes) judge the one module", code == 0, out)

        full = os.path.join(tmp, "full", "module.html")
        os.makedirs(os.path.dirname(full))
        with open(full, "w", encoding="utf-8") as f:
            f.write(DECK.replace('data-mins="40" data-track="theory" data-active="8"',
                                 'data-mins="28" data-track="theory" data-active="8"')
                    + '<section class="slide" data-block="b13" data-kind="teaching" data-title="Predict, then reveal" '
                      'data-mins="12" data-track="theory" data-active="12"></section>')
        code, out = run(full, "--theory-min", "40", "--practice-min", "20")
        check("a 12-minute theory block declared 100 % active is a report line, never a FAIL - the owner's open decision "
              "(the factory trial: M01 blocks 13, 16, 25 failed and QA called the module BROKEN)",
              code == 0 and "FAIL" not in out and "report  b13 declares 100% of a 12 minute theory block active" in out
              and "open decision" in out, out)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("\n%s" % ("ALL PASS" if not FAILS else "%d FAILED" % len(FAILS)))
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
