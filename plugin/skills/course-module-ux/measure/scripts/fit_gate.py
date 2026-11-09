#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""fit_gate - the deck walked as the instructor walks it, and every step measured: Start, then Next to the end, through
every figure step and every question's answer. A word the trainee cannot see, or a picture shown only in part, fails it.

    python fit_gate.py <deck index.html | module folder> [--viewport 1280x800 ...] [--min-shown 0.8] [--json out.json]

run_audits.py measures each slide as it first opens; a slide whose last Next shows more (the answer to the room's
question, the last line of a list) was never measured there - GAS BASIC's 37 answers were cut at the tablet's size and
every audit passed. This gate presses Next.

Fails on, at each step of each slide:
  cut     words cut off by the box that holds them, or by the screen (more than 8 px)
  spill   a card, a line or a picture past the edge of the slide
  picture shown in part - less than --min-shown of it (0.8) - or stretched, or its box cut; a picture inside
          data-fit="cover" is a backdrop and may be cropped; a picture that does not load
Sizes: 1280x800 (the tablets), 1024x768 and 1280x720 unless --viewport is given.

It drives the Chrome or Edge already on the computer through Playwright (python -m pip install playwright - no browser
download). Exit 0 every step fits, 1 something does not (each slide, step and size named), 2 nothing could be measured.
The deck is never changed.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from test_audit_drawing import browser  # noqa: E402  - the one place that finds Chrome or Edge
sys.path.insert(0, str(HERE.parents[2] / "course-factory" / "scripts"))
import browser_slots  # noqa: E402  - one pool of hidden browsers for the whole computer

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
SIZES = ("1280x800", "1024x768", "1280x720")
MAX_STEPS = 3000
PROBE = (HERE / "fit_probe.js").read_text(encoding="utf-8")
SETTLE = """() => { for (const a of document.getAnimations()) { try { const t = a.effect && a.effect.getComputedTiming();
  if (t && t.endTime !== Infinity) a.finish(); } catch (e) {} } }"""


def find_deck(arg):
    p = Path(arg)
    for d in (p, p / "presentation" / "index.html", p / "index.html"):
        if d.is_file():
            return d.resolve()
    return None


# the 2D kit's own check (kit2d.js KIT2D.audit) on the figures of the slide in front: words over words, words or shapes cut
# at the edge, a label on a line - measured once the figure has stopped moving
KIT2D = """(id) => { const s = document.getElementById(id); if (!window.KIT2D || !s) { return null; }
  const fs = KIT2D.figures.filter(f => s.contains(f.host)); if (!fs.length) { return null; }
  return { idle: fs.every(f => f.idle()), found: [].concat.apply([], fs.map(f => KIT2D.audit(f))) }; }"""


# 2.115.0 - a figure with steps that does not change on any Next is a dead drawing (PM M02 s12, s13: the chart stayed an empty
# axis on every Next). Its state at a stop: a hash of what it drew.
KITSTATE = """(id) => { const s = document.getElementById(id); if (!s) { return null; }
  const hs = [].slice.call(s.querySelectorAll('[data-kit], [data-kit2d], [data-custom-fig]')); if (!hs.length) { return null; }
  let steps = 0, sig = '';
  hs.forEach(h => { const f = h.__kit || h.__k2; if (f && f !== 'bad') { steps += (f.spec && f.spec.steps || f.steps || []).length; }
    const cs = h.querySelector && h.querySelector('script[data-custom-steps]');       /* 2.116.0: a custom figure's declared steps */
    if (cs) { try { const d = JSON.parse(cs.textContent); steps += (Array.isArray(d) ? d : (d.steps || [])).length; } catch (e) {} }
    const t = h.innerHTML; let x = 0; for (let i = 0; i < t.length; i++) { x = (x * 31 + t.charCodeAt(i)) | 0; } sig += ':' + t.length + ':' + x; });
  return { steps: steps, sig: sig }; }"""


# the lines lit now on the slide (.cur): one stop's signature; a signature that comes back after another one is a second pass
CURSIG = """(id) => { const s = document.getElementById(id); if (!s) { return ''; }
  const a = s.hasAttribute('data-stops') || s.querySelector('[data-k]') ? 'data-k' : 'data-i';    /* the slide's own stops, else its lines */
  return [].slice.call(s.querySelectorAll('.cur')).filter(x => !x.hasAttribute('data-ks')).map(x => x.getAttribute(a) != null ? a + x.getAttribute(a) : '')
    .filter(Boolean).sort().join(','); }"""


def walked_twice(seqs):
    """[(slide id, message)] for each slide where a line lit at one stop is lit again after the walk moved on"""
    out = []
    for sid, seq in seqs.items():
        done, last = set(), None
        for sig in seq:
            if sig and sig != last:
                again = sorted(set(sig.split(",")) & done)
                if again:
                    out.append((sid, "Next walks its lines twice on %s - %s lit again after the walk moved on; each line "
                                     "should light once (then the question, then the answer)" % (sid, ", ".join(again))))
                    break
                done |= set(sig.split(","))
            last = sig or last
    return out


def dead_figures(states):
    """[(slide id, message)] for each slide whose figure has steps and drew the same at every stop of the walk"""
    out = []
    for sid, seen in states.items():
        if seen["steps"] and len(seen["sigs"]) == 1 and seen["stops"] > 1:
            out.append((sid, "the drawing on %s does not change on any Next (%d stops walked, its figure has %d step(s)) - "
                             "point its steps' \"line\" at lines the slide lights, or mark the step \"reveal\": true "
                             "to play it with the answer" % (sid, seen["stops"], seen["steps"])))
    return out


# 2.116.0 - the walk review's stop record: the lit lines' text, whether the room's question / its answer is on screen, and
# the figure's signature - saved beside a ~480 px screenshot of the slide, at 1280x800 only (walk_review.py reads them)
WALKINFO = """(id) => { const s = document.getElementById(id); if (!s) { return null; }
  const vis = e => { for (let x = e; x && x !== document.body; x = x.parentElement) { const c = getComputedStyle(x);
    if (c.display === 'none' || c.visibility === 'hidden' || parseFloat(c.opacity) < 0.05) { return false; } } return true; };
  const t = e => (e.textContent || '').replace(/\\s+/g, ' ').trim().slice(0, 160);
  const a = s.hasAttribute('data-stops') || s.querySelector('[data-k]') ? 'data-k' : 'data-i';
  const lit = [].slice.call(s.querySelectorAll('.cur')).filter(x => !x.hasAttribute('data-ks')).map(t).filter(Boolean);
  const ask = [].slice.call(s.querySelectorAll('.ask')).filter(vis).map(t);
  const rev = [].slice.call(s.querySelectorAll('.lt-ans-under, .lt-ans-over, .reveal, [data-reveal]')).filter(vis).map(t).filter(Boolean);
  let sig = ''; [].slice.call(s.querySelectorAll('[data-kit], [data-kit2d], svg, canvas')).forEach(h => { const q = h.innerHTML || '';
    let x = 0; for (let i = 0; i < q.length; i++) { x = (x * 31 + q.charCodeAt(i)) | 0; } sig += ':' + q.length + ':' + x; });
  return { lit: lit, ask: ask, reveal: rev, fig: sig, title: t(s.querySelector('h1, h2, .title') || s).slice(0, 80) }; }"""
WALK_WIDTH = 480


def save_shot(page, sid, path):
    """the slide in front, clipped, as a PNG about WALK_WIDTH px wide (Pillow shrinks it when it is there)"""
    path.parent.mkdir(parents=True, exist_ok=True)
    page.locator("#" + sid).screenshot(path=str(path))
    try:
        from PIL import Image
        im = Image.open(path)
        if im.width > WALK_WIDTH:
            im.convert("RGB").resize((WALK_WIDTH, round(im.height * WALK_WIDTH / im.width)), Image.LANCZOS).save(path)
    except ImportError:
        pass


def walk(page, deck, min_shown, shots=None, record=None):
    """[(slide id, step on that slide, kind, what)] for one deck at the page's size. shots: a folder - each stop is saved as
    <slide>_k<step>.png there (the walk review), record: a list that gets one dict per stop"""
    found, at, states, seqs = [], {}, {}, {}
    page.goto(deck.as_uri())
    page.wait_for_timeout(600)
    if page.locator("#startBtn").count():
        page.click("#startBtn")
    for _ in range(MAX_STEPS):
        page.wait_for_timeout(450)
        page.evaluate(SETTLE)
        page.wait_for_timeout(120)
        r = page.evaluate("() => window.FitProbe()")
        if r and any(r[k] for k in ("cut", "spill")):
            # a step still moving (a card opening after its delay) is measured again once it has settled
            page.wait_for_timeout(1500)
            page.evaluate(SETTLE)
            r = page.evaluate("() => window.FitProbe()")
        if r:
            step = at[r["id"]] = at.get(r["id"], 0) + 1
            seqs.setdefault(r["id"], []).append(page.evaluate(CURSIG, r["id"]))
            if shots is not None:
                try:
                    name = "%s_k%d.png" % (r["id"], step)
                    save_shot(page, r["id"], Path(shots) / name)
                    info = page.evaluate(WALKINFO, r["id"]) or {}
                    if record is not None:
                        record.append(dict(info, slide=r["id"], k=step, file=name))
                except Exception:          # a shot that could not be taken never fails the fit walk; the review finds the gap
                    pass
            ks = page.evaluate(KITSTATE, r["id"])
            if ks:
                seen = states.setdefault(r["id"], {"steps": ks["steps"], "sigs": set(), "stops": 0})
                seen["sigs"].add(ks["sig"])
                seen["stops"] += 1
            for k in ("cut", "spill"):
                for f in r[k]:
                    found.append((r["id"], step, k, "%s px %s: \"%s\"%s" % (f["px"], f["el"], f["words"],
                                                                         " (cut by %s)" % f["by"] if f.get("by") else "")))
            for f in r["pic"]:
                if f.get("broken"):
                    found.append((r["id"], step, "picture", "%s does not load" % f["src"]))
                elif not f["backdrop"] and f["part"] < min_shown:
                    found.append((r["id"], step, "picture", "%s shows %d %% of itself (%s picture in a %s box, %s)"
                                  % (f["src"], round(f["part"] * 100), f["natural"], f["box"], f["fit"])))
                elif f["stretch"] > 1.1:
                    found.append((r["id"], step, "picture", "%s stretched x%.2f" % (f["src"], f["stretch"])))
                elif f["seen"] < 0.9:
                    found.append((r["id"], step, "picture", "%s: only %d %% of its box is seen (cut by %s)"
                                  % (f["src"], round(f["seen"] * 100), f["by"])))
            k2 = page.evaluate(KIT2D, r["id"])
            for _ in range(12):                       # a 2D-kit figure still moving is measured once it has settled
                if not k2 or k2["idle"]:
                    break
                page.wait_for_timeout(250)
                k2 = page.evaluate(KIT2D, r["id"])
            for what in (k2 or {}).get("found", []):
                found.append((r["id"], step, "figure", what))
        nxt = page.locator("#btnNext")
        if not nxt.count() or nxt.is_disabled():
            break
        nxt.click()
    for sid, what in dead_figures(states):
        found.append((sid, 1, "dead", what))
    for sid, what in walked_twice(seqs):
        found.append((sid, 1, "twice", what))
    return found


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("deck")
    ap.add_argument("--viewport", action="append", default=[])
    ap.add_argument("--min-shown", type=float, default=0.8)
    ap.add_argument("--json")
    ap.add_argument("--walk-dir", help="2.116.0: save each stop at 1280x800 here (sNN_kK.png) with walk.json - the walk review's input")
    o = ap.parse_args(argv)
    deck = find_deck(o.deck)
    if not deck:
        print("fit_gate: no deck at %s (give the deck's index.html, or the module folder)" % o.deck)
        return 2
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("fit_gate: Playwright is not installed - python -m pip install playwright (it drives the Chrome or Edge "
              "already here, nothing else to download)")
        return 2
    exe = browser()
    if not exe:
        print("fit_gate: no Chrome or Edge found - nothing measured")
        return 2
    sizes = []
    for v in o.viewport or SIZES:
        try:
            w, h = (int(x) for x in v.lower().split("x"))
        except ValueError:
            print("fit_gate: --viewport wants WxH, like 1280x800 - not %r" % v)
            return 2
        sizes.append((w, h))
    res = {}
    try:
        with browser_slots.slot(), sync_playwright() as pw:
            b = pw.chromium.launch(executable_path=exe, headless=True, args=["--allow-file-access-from-files"])
            for w, h in sizes:
                page = b.new_page(viewport={"width": w, "height": h})
                page.add_init_script(PROBE)
                rec = [] if (o.walk_dir and (w, h) == (1280, 800)) else None
                res["%dx%d" % (w, h)] = walk(page, deck, o.min_shown, o.walk_dir if rec is not None else None, rec)
                if rec is not None:
                    Path(o.walk_dir).mkdir(parents=True, exist_ok=True)
                    (Path(o.walk_dir) / "walk.json").write_text(
                        json.dumps({"viewport": "1280x800", "stops": rec}, indent=1, ensure_ascii=False), encoding="utf-8")
                page.close()
            b.close()
    except Exception as err:                                # the browser did not start or the page did not answer
        print("fit_gate: could not measure %s - %s" % (deck, str(err).splitlines()[0] if str(err) else type(err).__name__))
        return 2
    if o.json:
        Path(o.json).write_text(json.dumps({k: [list(x) for x in v] for k, v in res.items()}, indent=1), encoding="utf-8")
    bad = 0
    for size, found in res.items():
        slides = {}
        for sid, step, kind, what in found:
            slides.setdefault(sid, {}).setdefault((kind, what), []).append(step)
        bad += len(slides)
        print("%-9s fit  %s" % (size, "PASS" if not slides else "FAIL %d slide(s)" % len(slides)))
        for sid, kinds in slides.items():
            for (kind, what), steps in list(kinds.items())[:4]:
                print("  %s step %s  %-7s %s" % (sid, ",".join(str(x) for x in sorted(set(steps))[:4]), kind, what))
            if len(kinds) > 4:
                print("  %s  ... and %d more" % (sid, len(kinds) - 4))
    print("fit_gate: %s" % ("every step fits" if not bad else "words or pictures the trainee cannot fully see - fix the "
                                                             "slides named above"))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
