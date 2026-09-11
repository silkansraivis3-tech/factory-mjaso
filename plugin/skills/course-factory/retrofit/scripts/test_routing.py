#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Deterministic tests for retrofit routing, classification and the language lock.

    test_routing.py            run everything
    test_routing.py -v         show every case

WHAT THIS TESTS, AND WHAT IT DOES NOT
It tests the RULES in ../knowledge/routing.json, ../knowledge/classify.json and
../knowledge/content-lock.json, by implementing them and asserting the cases the
owner named. A rule that contradicts itself, a trigger that stops matching, a
classifier that starts rewarding valid HTML - all caught here.

It does NOT test the model's free-form judgement. Nothing can assert that from a
script, and pretending otherwise would be the kind of green-exit-as-proof this
factory keeps recording. What it can do, and does, is make sure the written
rules say what we think they say.

THE CASES (from the owner, verbatim in intent)
  A  existing English module + Latvian operator request
     -> RETROFIT selected, course stays English
  B  technically valid but visually weak HTML
     -> not classified preserve-as-is
  C  useful interactive figure, weak layout
     -> concept preserved, implementation may be rebuilt
  D  13-screen module where stronger teaching needs 17
     -> allowed
  E  "only change the colours"
     -> RESTYLE, not RETROFIT
"""

import json
import re
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
K = HERE.parent / "knowledge"
ROUTING = json.loads((K / "routing.json").read_text(encoding="utf-8"))
LOCK = json.loads((K / "content-lock.json").read_text(encoding="utf-8"))
CLASSIFY = json.loads((K / "classify.json").read_text(encoding="utf-8"))

sys.path.insert(0, str(HERE))
import classify_module  # noqa: E402

PASS, FAIL = [], []


def check(name, got, want, detail=""):
    ok = got == want
    (PASS if ok else FAIL).append((name, got, want, detail))
    return ok


# ---------------------------------------------------------------------------
# The router, implemented from routing.json. This is the rule under test.
# ---------------------------------------------------------------------------
def route(prompt, has_existing_material=True):
    """Which mode does routing.json select for this request?"""
    p = " " + prompt.lower().strip() + " "

    rs = ROUTING["restyle_triggers"]
    narrow = any(re.search(r"\b" + re.escape(t) + r"\b", p) for t in rs["narrow_targets"])
    limited = any(l in p for l in rs["scope_limiters"])

    hits = []
    for intent in ROUTING["retrofit_triggers"]["intents"]:
        for ex in intent["examples"]:
            toks = [t for t in re.findall(r"[^\W\d_]+", ex.lower()) if len(t) > 3]
            if not toks:
                continue
            # an example matches when most of its content words are present
            got = sum(1 for t in toks if t in p)
            if got >= max(2, int(round(len(toks) * 0.6))):
                hits.append(intent["intent"])
                break
    retrofit_shaped = bool(hits)

    # RESTYLE needs BOTH a narrow target AND a limiter. Either alone is not
    # enough - "change the colours and make it like GAS BASIC" is a retrofit.
    if narrow and limited:
        return "restyle", hits
    if retrofit_shaped:
        return ("retrofit" if has_existing_material else "plan"), hits
    if narrow and not limited:
        return "retrofit", hits
    return "ambiguous", hits


# ---------------------------------------------------------------------------
# Fixtures: two synthetic modules, written to a temp dir. Neither is a copy of
# any real course; they exist to exercise the classifier's two ends.
# ---------------------------------------------------------------------------
WEAK = """<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<title>Legacy module</title>
<style>
 body{font-family:Arial;margin:24px;color:#222;background:#fff}
 h1{color:#123456} .box{border:1px solid #999;padding:12px;margin:8px 0;background:#f4f4f4}
</style></head><body>
<h1>Module 1 - Pump systems</h1>
%s
</body></html>"""
WEAK_SCREEN = """<section class="slide"><h2>Topic %d</h2>
<div class="box"><p>A paragraph of perfectly correct technical prose about the
subject, written carefully by someone who knew it well, and laid out as a box
because that is what was available at the time. It parses, it validates, every
link in it resolves.</p></div>
<div class="box"><p>Another paragraph, same shape as the last one and the next.</p></div>
</section>"""

# A canonical module: the shell's landmarks, a composition per screen, a figure
# on the teaching screens, a whole-screen activity launch. Deliberately small -
# four screens is a legal module - because screen COUNT is not a signal.
STRONG = """<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<title>Canonical module</title>
<link rel="stylesheet" href="assets/gb_tokens.css">
<link rel="stylesheet" href="assets/gb_shell.css">
<link rel="stylesheet" href="assets/gb_compose.css">
</head><body>
<a class="gbt-topback" href="START_HERE.html" hidden>back</a>
<div id="landing"><div class="landing-card"><button id="startBtn">Start</button></div></div>
<div id="chrome">
  <button id="btnGrid"></button><button id="btnPrev"></button>
  <span id="counter">1 / 4</span><button id="btnNext"></button>
</div>
<div id="overview"><div class="ov-grid"></div></div>
<div id="cue"></div>
<main id="stage">
<section class="slide dark" data-title="Cover" data-kind="opener"
         data-foot="CODE - MODULE - NOVIKONTAS" data-cue="Open with the question.">
  <div class="slide-kind"><b>Opener</b> - A1</div>
  <div class="slide-body opener"><h2>The one idea</h2>
  <p class="q">A question the room is left holding, long enough to count as real content here.</p></div>
</section>
<section class="slide" data-title="Mechanism" data-kind="theory"
         data-foot="CODE - MODULE - NOVIKONTAS" data-cue="Stop at step three.">
  <div class="slide-kind"><b>Theory</b> - A2</div>
  <h2>How it works</h2>
  <div class="slide-body two-col"><div><p class="statement">A claim about the mechanism,
  stated plainly and at enough length to be a substantial teaching screen in the eyes of
  the classifier, which wants at least twenty-five words before it judges.</p></div>
  <div class="fill"><svg viewBox="0 0 100 60"><rect width="80" height="40"/></svg></div></div>
</section>
<section class="slide dark" data-title="Figure" data-kind="visual"
         data-foot="CODE - MODULE - NOVIKONTAS" data-cue="Drive it step by step.">
  <div class="slide-kind"><b>Visual explanation</b> - A3</div>
  <h2>What the drawing shows</h2>
  <div class="slide-body stage"><svg viewBox="0 0 200 100"><circle cx="50" cy="50" r="40"/></svg>
  <p class="cap">One line saying what to look at, with enough words to be substantial content.</p></div>
</section>
<section class="slide dark activity" data-title="T1" data-kind="task" data-activity="T1"
         data-foot="CODE - MODULE - NOVIKONTAS" data-cue="Say it once, then stop talking.">
  <div class="slide-kind"><b>Task</b> - A4</div>
  <div class="slide-body activity"><p class="act-code">T1</p>
  <p class="act-title">What the trainee does</p>
  <p class="act-inst">One or two sentences describing the work, long enough to be judged
  a substantial screen by a classifier that counts words before it decides.</p>
  <p class="act-now"><b>Now a task.</b> Open the tablets - task <code>T1</code>.</p></div>
</section>
</main>
</body></html>"""

TOKENS = (":root{--navy:#0A2463;--deep:#0A182E;--blue:#2EB6F8;--amber:#E9A51E;"
          "--white:#FFFFFF;--ink:#011111;--grey:#E7EBF0;--line-l:#D3DBE5;"
          "--line-d:rgba(46,182,248,.18);--txt-d:#F3F8FD;--dim-l:#41556A;"
          "--dim-d:#A2B7CF;--good:#12805A;--warn:#B4453A;--r-m:13px;"
          "--font:Raleway}" + chr(10))
SHELLCSS = ".slide{display:none;color:var(--ink);background:var(--white)}\n.slide.active{display:flex}\n"


def write_fixtures(tmp):
    weak = tmp / "weak"
    weak.mkdir()
    (weak / "module.html").write_text(
        WEAK % "\n".join(WEAK_SCREEN % i for i in range(1, 14)), encoding="utf-8")

    strong = tmp / "strong"
    (strong / "assets").mkdir(parents=True)
    (strong / "module.html").write_text(STRONG, encoding="utf-8")
    (strong / "assets" / "gb_tokens.css").write_text(TOKENS, encoding="utf-8")
    (strong / "assets" / "gb_shell.css").write_text(SHELLCSS, encoding="utf-8")
    (strong / "assets" / "gb_compose.css").write_text(
        ".slide-body.two-col{display:grid}\n", encoding="utf-8")
    return weak, strong


# ---------------------------------------------------------------------------
def main():
    verbose = "-v" in sys.argv

    # --- the owner's five cases ---------------------------------------------

    # A · existing English module, Latvian operator request
    mode, _ = route("Pārtaisi Moduli 1 ar NOVIKONTAS Course Factory")
    check("A routing  · Latvian request for an existing module -> retrofit", mode, "retrofit")
    lock = [i["what"] for i in LOCK["locked"]["items"]]
    check("A language · course language is locked by content-lock.json",
          any("language" in w for w in lock), True)
    check("A language · the chat report is NOT course-facing",
          "the chat report" in ROUTING["language_lock"]["not_course_facing"], True)
    check("A language · slides ARE course-facing",
          "slides" in ROUTING["language_lock"]["course_facing"], True)

    # E · explicit narrow restyle
    for p in ["Only change the colours.",
              "just change the fonts, nothing else",
              "tikai nomaini krāsas, nemaini neko citu"]:
        m, _ = route(p)
        check("E routing  · %-42s -> restyle" % p[:42], m, "restyle")

    # ...and the near-miss that must NOT be a restyle
    m, _ = route("change the colours and make it like GAS BASIC")
    check("E routing  · narrow target WITHOUT a limiter -> retrofit", m, "retrofit")

    # the Cowork sentence that has to be enough on its own
    for p in ["Redesign Module 1 using the NOVIKONTAS Course Factory.",
              "Make my existing English module production-ready like GAS BASIC.",
              "I already have the content. Make this module much more visual and interactive.",
              "upgrade this existing module",
              "make these modules presentable",
              "improve the existing course UX",
              "apply Course Factory to this module",
              "modernise this existing course",
              "improve the existing presentation"]:
        m, _ = route(p)
        check("cowork     · %-44s -> retrofit" % p[:44], m, "retrofit")

    # the same intent with nothing built yet is a plan, not a retrofit
    m, _ = route("Redesign Module 1 using the NOVIKONTAS Course Factory.",
                 has_existing_material=False)
    check("cowork     · retrofit intent, no existing material -> plan", m, "plan")

    with tempfile.TemporaryDirectory() as td:
        weak, strong = write_fixtures(Path(td))

        # B · technically valid but visually weak
        rw = classify_module.classify(weak / "module.html")
        check("B classify · valid-but-weak HTML is NOT preserve-as-is", rw["level"] != "A", True,
              "got %s, score %.2f" % (rw["level"], rw["score"]))
        check("B classify · valid-but-weak HTML is a substantial redesign", rw["level"], "C",
              "score %.2f" % rw["score"])
        check("B classify · 'the HTML parses' is not a signal",
              "the HTML parses" in CLASSIFY["not_signals"]["items"], True)
        check("B classify · 'the existing checks pass' is not a signal",
              "the existing checks pass" in CLASSIFY["not_signals"]["items"], True)

        # and the other end: a canonical module is not dragged down
        rs = classify_module.classify(strong / "module.html")
        check("B classify · a canonical module classifies A", rs["level"], "A",
              "score %.2f" % rs["score"])

    # C · a useful figure with a weak layout
    check("C law      · existing visuals are evidence, not sacred implementation",
          LOCK["existing_visuals"]["_rule"].startswith("A technically meaningful visual is EVIDENCE"),
          True)
    check("C law      · 'technical visual implementation' is free",
          "technical visual implementation" in LOCK["free"]["items"], True)
    check("C law      · 'authoritative technical meaning' is locked",
          any(i["what"] == "authoritative technical meaning" for i in LOCK["locked"]["items"]), True)

    # D · screen count may move with the learning need
    check("D law      · screen count is free", "screen count" in " ".join(LOCK["free"]["items"]), True)
    check("D law      · splitting an overloaded screen is allowed",
          "split overloaded screens" in LOCK["screen_count"]["may"], True)
    check("D law      · filler is not allowed",
          "add filler to look busier" in LOCK["screen_count"]["must_not"], True)
    check("D law      · the GAS BASIC screen count is not a target",
          "target the GAS BASIC screen count" in LOCK["screen_count"]["must_not"], True)
    check("D law      · official hours stay locked while screens move",
          any(i["what"] == "official hours" for i in LOCK["locked"]["items"]), True)

    # --- the laws must not contradict each other ----------------------------
    locked_words = " ".join(i["what"] for i in LOCK["locked"]["items"]).lower()
    free_words = " ".join(LOCK["free"]["items"]).lower()
    for term in ["screen count", "composition", "html structure", "navigation implementation"]:
        check("coherence  · '%s' is free and not also locked" % term,
              term in free_words and term not in locked_words, True)
    for term in ["official hours", "assessment intent", "course-specific terminology"]:
        check("coherence  · '%s' is locked and not also free" % term,
              term in locked_words and term not in free_words, True)

    # --- routing targets exist ----------------------------------------------
    rt = ROUTING["routing_targets"]
    for want in ["course-module-ui", "course-module-ux", "course-visuals", "course-task-ux"]:
        check("routing    · %s is an orchestration target" % want,
              any(want in str(v) for k, v in rt.items() if not k.startswith("_")), True)

    # --- report --------------------------------------------------------------
    print("=" * 74)
    print("test_routing - retrofit routing, classification and the language lock")
    print("=" * 74)
    if verbose:
        for n, g, w, d in PASS:
            print("  pass  %s%s" % (n, ("   [%s]" % d) if d else ""))
    for n, g, w, d in FAIL:
        print("  FAIL  %s\n           got %r, wanted %r%s" % (n, g, w, ("   [%s]" % d) if d else ""))
    print("\n%d passed, %d failed" % (len(PASS), len(FAIL)))
    if not FAIL:
        print("\nThe written rules say what we think they say. This does not test the model's")
        print("free-form judgement - nothing in a script can - only that the rules it reads")
        print("are coherent and still select what the owner asked for.")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
