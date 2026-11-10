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


@contextlib.contextmanager
def browser_slot_page(deck):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        b = pw.chromium.launch(executable_path=browser(), headless=True, args=["--allow-file-access-from-files"])
        page = b.new_page(viewport={"width": 1280, "height": 800})
        page.goto(deck.as_uri())
        page.wait_for_timeout(500)
        try:
            yield page
        finally:
            b.close()


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
    print("-- a drawing that never changes, and lines walked twice (2.115.0)")
    check("dead_figures: a figure with steps that drew the same at every stop is named",
          [x[0] for x in fit_gate.dead_figures({"a": {"steps": 3, "sigs": {"x"}, "stops": 5}})] == ["a"])
    check("... one that changed is not, nor a figure with no steps (a still picture)",
          not fit_gate.dead_figures({"a": {"steps": 3, "sigs": {"x", "y"}, "stops": 5}, "b": {"steps": 0, "sigs": {"x"}, "stops": 5}}))
    check("walked_twice: a line lit again after the walk moved on is named",
          [x[0] for x in fit_gate.walked_twice({"a": ["data-k0", "data-k1", "data-k0"]})] == ["a"])
    check("... lit stops in order, or one stop repeated, are not",
          not fit_gate.walked_twice({"a": ["data-k0", "data-k0", "data-k1", ""], "b": ["data-k0,data-k1", "data-k2"]}))
    KDECK = HERE / "fixtures" / "deck_kit_steps.html"
    code, out = cli(str(KDECK), "--viewport", "1280x800")
    check("a worked example's figure that never changes is named (k2), the one that moves is not (k1)",
          any(x.strip().startswith("k2 ") and "does not change on any Next" in x for x in out.splitlines())
          and not any(x.strip().startswith("k1 ") for x in out.splitlines()), out)
    print("-- the walk review's input (2.116.0): every stop saved at 1280x800 only")
    import json
    import tempfile
    wd = tempfile.mkdtemp(prefix="walk_")
    code, out = cli(str(KDECK), "--viewport", "1280x800", "--viewport", "1024x768", "--walk-dir", wd)
    wj = json.loads(Path(wd, "walk.json").read_text(encoding="utf-8")) if Path(wd, "walk.json").is_file() else {}
    stops = wj.get("stops", [])
    k1s = [s for s in stops if s["slide"] == "k1"]
    check("--walk-dir: walk.json has a record for every stop, at 1280x800 only", wj.get("viewport") == "1280x800" and len(k1s) >= 4
          and [s["k"] for s in k1s] == list(range(1, len(k1s) + 1)), wj)
    check("... a screenshot of each stop, about 480 px wide", all(Path(wd, s["file"]).is_file() for s in stops) and k1s
          and (lambda im: im.width <= 480)(__import__("PIL.Image", fromlist=["Image"]).open(Path(wd, k1s[0]["file"]))), k1s[:1])
    check("... with the lit line's text and the figure's signature at each stop",
          all("lit" in s and "fig" in s for s in k1s) and len({s["fig"] for s in k1s}) > 1, k1s[:2])
    import walk_review
    stamp = walk_review.walk_stamp(str(KDECK))
    check("... and which deck the pictures are of: each slide's fingerprint (the audits' own) and the deck's",
          wj.get("fingerprints") == stamp["fingerprints"] and set(wj["fingerprints"]) == {s["slide"] for s in stops}
          and wj.get("deck") == stamp["deck"] and len(wj["deck"]) == 64, {k: v for k, v in wj.items() if k != "stops"})
    real_stamp, real_walk, order = fit_gate.walked_deck, fit_gate.walk, []
    try:
        fit_gate.walked_deck = lambda deck: order.append("stamp") or {"fingerprints": {"k1": "as the walk began"}, "deck": "then"}
        fit_gate.walk = lambda *a: order.append("walk") or real_walk(*a)
        cli(str(KDECK), "--viewport", "1280x800", "--walk-dir", wd)
    finally:
        fit_gate.walked_deck, fit_gate.walk = real_stamp, real_walk
    wj = json.loads(Path(wd, "walk.json").read_text(encoding="utf-8"))
    check("... taken before the walk starts: a deck built again while it is walked is not signed for under its new fingerprint",
          order == ["stamp", "walk"] and wj.get("fingerprints") == {"k1": "as the walk began"} and wj.get("deck") == "then", (order, wj.get("deck")))
    real_shot, shot_n = fit_gate.save_shot, []

    def no_second(page, sid, path):
        shot_n.append(sid)
        if len(shot_n) == 2:
            raise RuntimeError("the browser gave no picture")
        return real_shot(page, sid, path)
    try:
        fit_gate.save_shot = no_second
        cli(str(KDECK), "--viewport", "1280x800", "--walk-dir", wd)
    finally:
        fit_gate.save_shot = real_shot
    wj = json.loads(Path(wd, "walk.json").read_text(encoding="utf-8"))
    lost = [s for s in wj["stops"] if not s.get("file")]
    check("... a stop whose picture could not be taken is recorded with no picture (2.125.0): the walk review refuses "
          "its slide, the fit walk goes on", len(lost) == 1 and "no picture" in lost[0].get("lost", "")
          and len(wj["stops"]) == len(stops) and lost[0]["k"] == 2, (lost, len(wj["stops"]), len(stops)))
    with browser_slot_page(KDECK) as page:
        seen = []
        page.click("#startBtn")
        for _ in range(7):
            page.wait_for_timeout(120)
            seen.append((page.evaluate("() => document.querySelector('.slide.active').id"),
                         page.evaluate("() => document.querySelector('.slide.active svg').getAttribute('data-n')")))
            page.click("#btnNext")
        k1 = [n for sid, n in seen if sid == "k1"]
        check("the figure plays the step of each lit line (1, 2, 3), the question keeps it, the answer plays the reveal (4), "
              "and Next then leaves the slide - no second pass", k1 == ["1", "2", "3", "3", "4"] and seen[5][0] == "k2", seen)
    print("\n%d passed, %d failed" % (len(PASS), len(FAIL)))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
