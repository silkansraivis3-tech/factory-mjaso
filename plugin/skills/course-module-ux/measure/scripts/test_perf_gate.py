# -*- coding: utf-8 -*-
"""test_perf_gate - perf_gate.py walks a deck with Next on a slowed computer and fails 3D that lags on the tablet.

    python test_perf_gate.py

Pinned:
  * fixtures/deck_perf_bad.html (a WebGL context per 3D slide, each drawing every frame, shown or not) fails, on both:
    2 live contexts, and frames drawn by a canvas not on the slide shown;
  * the 3D kit's course-visuals/kit3d/scripts/fixtures/deck_kit3d_many.html (six scenes) holds ONE live context on every
    slide but the one with two scenes side by side, and no scene draws off screen - a deck of many 3D slides held a context
    for every scene passed (16 of 18) before the kit shared its renderer;
  * the walk reaches every slide and reports a first frame for every 3D slide;
  * no deck -> exit 2; the deck is not changed.
Skips, and says so, when Playwright or Chrome/Edge is not installed. Run without the CPU throttle and with wide frame
budgets: what is pinned is what the gate counts, not this computer's speed.
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import perf_gate  # noqa: E402
from test_audit_drawing import browser  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
BAD = HERE / "fixtures" / "deck_perf_bad.html"
MANY = HERE.parents[2] / "course-visuals" / "kit3d" / "scripts" / "fixtures" / "deck_kit3d_many.html"
EASY = ["--throttle", "1", "--dsf", "1", "--ms", "600", "--p95-ms", "100000", "--first-ms", "100000", "--gl", "swiftshader"]
PASS, FAIL = [], []


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print(("  ok    " if ok else "  FAIL  ") + name + (("  -> " + str(detail)[:900]) if detail and not ok else ""))


def cli(*args):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = perf_gate.main(list(args))
    return code, buf.getvalue()


def walk(deck, *more):
    fd, out = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    try:
        code, text = cli(str(deck), *EASY, "--json", out, *more)
        data = json.loads(Path(out).read_text(encoding="utf-8")) if os.path.getsize(out) else {}
    finally:
        os.remove(out)
    return code, text, {r["id"]: r for r in data.get("rows", [])}


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

    print("-- a context per 3D slide, drawing off screen")
    before = BAD.read_bytes()
    code, out, rows = walk(BAD)
    check("it fails: exit 1", code == 1, out)
    check("every slide is walked", all(k in rows for k in ("b1", "b2", "b3", "b4")), sorted(rows))
    check("2 live WebGL contexts are counted and named", rows.get("b2", {}).get("ctx") == 2 and "2 live WebGL contexts" in out, out)
    check("a canvas drawing while its slide is not shown is caught", rows.get("b2", {}).get("hidden", 0) > 10
          and "not on the slide shown" in out, out)
    check("the first frame of a 3D slide is timed", rows.get("b3", {}).get("first") is not None, rows.get("b3"))
    check("the deck is not changed", BAD.read_bytes() == before)

    print("-- the 3D kit: six scenes in one deck")
    code, out, rows = walk(MANY, "--max-ctx", "2")
    ctx = {k: r["ctx"] for k, r in rows.items() if not k.startswith("(")}
    check("the kit's deck passes at 2 contexts at most: exit 0", code == 0, out)
    check("ONE live context on every slide but the one with two scenes side by side",
          ctx.get("m6") == 2 and all(v <= 1 for k, v in ctx.items() if k != "m6"), ctx)
    check("no scene draws while its slide is not shown (the one frame a scene built ahead draws aside)",
          all(r["hidden"] <= 2 for r in rows.values()),
          {k: r["hidden"] for k, r in rows.items()})
    check("every 3D slide draws a first frame after Next", all(rows.get(k, {}).get("first") is not None
                                                              for k in ("m2", "m3", "m4", "m6")), rows)
    print("\n%d passed, %d failed" % (len(PASS), len(FAIL)))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
