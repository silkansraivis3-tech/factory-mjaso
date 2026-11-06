# -*- coding: utf-8 -*-
"""test_fit_gate - fit_gate.py walks a deck with Next and fails on what the trainee cannot fully see.

    python test_fit_gate.py

Pinned, on fixtures/deck_fit.html:
  * a slide that fits as it opens and cuts its answer at its last step fails, at that step (f2, step 2) - the GAS BASIC
    reveal that every audit passed because none pressed Next;
  * a slide that fits at every step is not named (f1);
  * a wide picture cropped into a square box fails; the same picture as a backdrop (data-fit="cover") does not (f3);
  * no deck -> exit 2; the exit is 1 when something does not fit.
Skips, and says so, when Playwright or Chrome/Edge is not installed.
"""
from __future__ import annotations

import contextlib
import io
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import fit_gate  # noqa: E402
from test_audit_drawing import browser  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
DECK = HERE / "fixtures" / "deck_fit.html"
PASS, FAIL = [], []


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print(("  ok    " if ok else "  FAIL  ") + name + (("  -> " + str(detail)[:900]) if detail and not ok else ""))


def cli(*args):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = fit_gate.main(list(args))
    return code, buf.getvalue()


def main():
    print("-- no deck")
    code, out = cli(str(HERE / "fixtures" / "no_such_deck.html"))
    check("no deck: exit 2, never a pass", code == 2, out)
    try:
        import playwright  # noqa: F401
    except ImportError:
        print("SKIP the walk - Playwright is not installed (python -m pip install playwright)")
        return 0 if not FAIL else 1
    if not browser():
        print("SKIP the walk - no Chrome or Edge")
        return 0 if not FAIL else 1
    print("-- the walk, at 1280x800")
    before = DECK.read_bytes()
    code, out = cli(str(DECK), "--viewport", "1280x800")
    lines = out.splitlines()
    check("something does not fit: exit 1", code == 1, out)
    f2 = [x for x in lines if x.strip().startswith("f2 ")]
    check("the answer cut at the slide's last step is found, at that step (f2 step 2)",
          any("step 2 " in x and "cut" in x and "Pressure alone" in x for x in f2), out)
    check("... and not at its first step, where it fits", not any("step 1 " in x for x in f2), out)
    check("a slide that fits is not named (f1)", not any(x.strip().startswith("f1 ") for x in lines), out)
    f3 = [x for x in lines if x.strip().startswith("f3 ")]
    check("a wide picture cropped into a square box fails (f3)", any("picture" in x and "wide.png shows" in x for x in f3), out)
    check("... the same picture as a backdrop (data-fit=\"cover\") is allowed", len([x for x in f3 if "wide.png shows" in x]) == 1, out)
    check("the deck is not changed", DECK.read_bytes() == before)
    print("\n%d passed, %d failed" % (len(PASS), len(FAIL)))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
