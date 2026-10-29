# -*- coding: utf-8 -*-
"""test_audit_motion - L65: a drawing that moves stays smooth on a tablet (2.78.0), proven in a real browser.

    python test_audit_motion.py

Opens measure/fixtures/motion_defects.html and the kit's own GALLERY.html in headless Chrome or Edge (--dump-dom) with
audit_motion.js loaded, and reads what it found. Skips, and says so, when no Chrome or Edge is installed. Pinned:
  * a flow running for ever with a drop-shadow, a mask, a shadowed panel round it, or a SMIL animation beside a blur in
    the same drawing: each found, on its own slide;
  * a moving drawing with its own layer and nothing else, and a still drawing with a shadow and a mask: silent;
  * a kit figure - tank, valve, a flowing pipe - passes at every step: the kit bakes its shadows and masks a line only
    while its front stands part-way. With the bake undone (the shadow forced back on), the same figure fails;
  * every drawing in the kit's gallery passes its own rule;
  * run_audits.py prints each finding with its slide.
"""
from __future__ import annotations

import json
import re
import shutil
import sys
import tempfile
from html import unescape
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = Path(__file__).resolve().parent
FIX = HERE.parent / "fixtures"
sys.path.insert(0, str(HERE))
from test_audit_drawing import browser  # noqa: E402
import run_audits  # noqa: E402
sys.path.insert(0, str(HERE.parents[2] / "course-factory" / "scripts"))
import browser_slots  # noqa: E402

PASS, FAIL = [], []


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print(("  ok    " if ok else "  FAIL  ") + name + (("  -> " + str(detail)[:600]) if detail and not ok else ""))


RUNNER = ('<script src="%s"></script><script>window.addEventListener("load",function(){setTimeout(function(){'
          'AuditMotion.%s().then(function(r){var p=document.createElement("pre");p.id="out";'
          'p.textContent=JSON.stringify(r);document.body.appendChild(p);});},%d);});</script>')


def probe(exe, page, entry="all", extra="", wait=600, budget=30000):
    """page (an .html file) with audit_motion.js run on it -> the probe's result, or None"""
    text = page.read_text(encoding="utf-8")
    inject = extra + RUNNER % ((HERE / "audit_motion.js").as_uri(), entry, wait)
    i = text.lower().rfind("</body>")
    tmp = page.with_name("_motion_test_%s.html" % page.stem)
    prof = tempfile.mkdtemp(prefix="audit_motion_")
    try:
        tmp.write_text(text[:i] + inject + text[i:], encoding="utf-8")
        p = browser_slots.run([exe, "--headless=new", "--disable-gpu", "--user-data-dir=" + prof, "--allow-file-access-from-files",
                               "--window-size=1280,2600", "--virtual-time-budget=%d" % budget, "--dump-dom", tmp.as_uri()],
                              capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
    finally:
        if tmp.exists():
            tmp.unlink()
        shutil.rmtree(prof, ignore_errors=True)
    m = re.search(r'<pre id="out">(.*?)</pre>', p.stdout, re.S)
    return json.loads(unescape(m.group(1))) if m and m.group(1).strip() else None


def main():
    exe = browser()
    if not exe:
        print("  skip  no Chrome or Edge found - audit_motion.js was not run")
        return 0
    deck = FIX / "motion_defects.html"

    r = probe(exe, deck)
    check("the probe answers on the fixture deck", isinstance(r, dict) and "failingSlides" in r, r)
    if isinstance(r, dict) and "failingSlides" in r:
        bad = {s["slide"]: " | ".join(s["hits"]) for s in r["failingSlides"]}
        check("a drop-shadow beside a running flow is found (s1)", "filter on g.drop" in bad.get(1, ""), bad)
        check("a mask round a running flow is found (s2)", "mask on g" in bad.get(2, ""), bad)
        check("a shadowed panel round a moving drawing is found (s3)", "filter around it on div.panel" in bad.get(3, ""), bad)
        check("a blur beside a SMIL animation is found (s4)", "filter on circle" in bad.get(4, ""), bad)
        check("own layer, no filter, no mask: silent (s5)", 5 not in bad, bad)
        check("a still drawing keeps its shadow and mask: silent (s6)", 6 not in bad, bad)
        check("a kit figure with a flowing pipe passes at every step (s7)", 7 not in bad, bad)
        check("the verdict fails and counts every finding", r.get("verdict") == "VERDICT: FAIL n=4" and r.get("failures") == 4, r.get("verdict"))
        kit = [d for row in r.get("rows", []) if row.get("slide") == 7 for d in row.get("drawings", [])]
        check("the kit figure is seen moving, with its own layer", bool(kit) and kit[0]["moving"] >= 1 and kit[0]["layer"], kit)
        check("the dashoffset flow is a note, not a failure (s5)",
              any("good-layer" in n and "stroke-dashoffset" in n for n in r.get("notes", [])), r.get("notes"))

    # the same kit figure with its baked shadows forced live again: it must fail - the bake is what passes it
    undo = "<style>.kit-m-drop.kit-baked{filter:drop-shadow(0 3px 3px #000)!important}</style>"
    r2 = probe(exe, deck, extra=undo)
    bad2 = {s["slide"]: " | ".join(s["hits"]) for s in (r2 or {}).get("failingSlides", [])}
    check("with the bake undone the kit figure fails (s7)", "filter on g.kit-eq.kit-m-drop" in bad2.get(7, ""), bad2)

    gal = HERE.parents[2] / "course-visuals" / "kit" / "GALLERY.html"
    g = probe(exe, gal, entry="page", wait=1500, budget=60000)
    check("the kit's gallery: drawings that move are found", isinstance(g, dict) and g.get("movingDrawings", 0) >= 5, g and g.get("movingDrawings"))
    check("the kit's gallery passes its own rule", isinstance(g, dict) and g.get("failures") == 0,
          g and [h for s in g.get("failingSlides", []) for h in s["hits"]])

    st, line, lines = run_audits.summarise("motion", {"exit": 1, "res": {
        "verdict": "VERDICT: FAIL n=1", "slidesTotal": 3, "movingDrawings": 2,
        "failingSlides": [{"slide": 2, "id": "s02", "hits": ['svg.kit "LNG line": filter on g.kit-eq (drop-shadow(...))']}]}})
    check("run_audits prints the slide and the finding", st == "FAIL" and "2 moving drawing" in line
          and lines == ['slide 2 (s02): svg.kit "LNG line": filter on g.kit-eq (drop-shadow(...))'], (st, line, lines))
    check("run_audits puts a motion finding on its slide",
          run_audits.slides_hit({n: {"exit": 0, "res": {}} for n, _, _ in run_audits.PROBES[:3]} |
                                {"motion": {"exit": 1, "res": {"failingSlides": [{"slide": 2}]}}}) == {1})

    print("test_audit_motion: %d passed, %d failed" % (len(PASS), len(FAIL)))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
