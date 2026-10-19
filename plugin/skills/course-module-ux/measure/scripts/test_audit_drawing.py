# -*- coding: utf-8 -*-
"""test_audit_drawing - every drawing whole and clean (L54), proven in a real browser.

    python test_audit_drawing.py

Opens measure/fixtures/drawing_defects.html and drawing_fit.html in headless Chrome or Edge (--dump-dom) and reads
what audit_drawing.js and gb_fit.js wrote into the page. Skips, and says so, when no Chrome or Edge is installed.
Pinned:
  * a room drawn as a rectangle in a sloping hull is found poking out - also when the hull is a shared <use>;
  * a tank cut off at the drawing's edge is found, and a ring that only shows in a later step;
  * a label printed over a line, and a label touching its own box's edge, are found;
  * a clean drawing - a room along the slope, a marked pipe through a bulkhead, a roof overhanging its deckhouse,
    liquid clipped to its tank, a label with its clearance - is silent;
  * gb_fit.js widens the frame of a drawing that reaches past it, leaves one that fits, and leaves data-fit="off".
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from html import unescape
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = Path(__file__).resolve().parent
FIX = HERE.parent / "fixtures"
PASS, FAIL = [], []


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print(("  ok    " if ok else "  FAIL  ") + name + (("  -> " + str(detail)[:600]) if detail and not ok else ""))


def browser():
    for name in ("chrome", "google-chrome", "chromium", "chromium-browser", "msedge"):
        p = shutil.which(name)
        if p:
            return p
    for p in (r"C:\Program Files\Google\Chrome\Application\chrome.exe",
              r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
              r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
              "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"):
        if os.path.isfile(p):
            return p
    return None


def page_out(exe, html, prof):
    p = subprocess.run([exe, "--headless=new", "--disable-gpu", "--user-data-dir=" + prof, "--allow-file-access-from-files",
                        "--window-size=1280,2600", "--virtual-time-budget=4000", "--dump-dom", html.as_uri()],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
    m = re.search(r'<pre id="out">(.*?)</pre>', p.stdout, re.S)
    return json.loads(unescape(m.group(1))) if m and m.group(1).strip() else None


def gallery_contrast(exe, prof):
    """the kit's own gallery (course-visuals/kit/GALLERY.html), every figure, run through the probe as it is: [contrast
    findings] - the kit's own parts must pass their own check"""
    gal = HERE.parent.parent.parent / "course-visuals" / "kit" / "GALLERY.html"
    text = gal.read_text(encoding="utf-8")
    text = re.sub(r"<head>", '<head><base href="%s/">' % gal.parent.as_uri(), text, count=1)
    tail = ('<script src="%s"></script><script>setTimeout(function(){var r=AuditDrawing.page();var p=document.createElement("pre");'
            'p.id="out";p.textContent=JSON.stringify({n:r.drawings,f:r.findings.filter(function(f){return f.check==="contrast"})'
            '.map(function(f){return f.part+" "+f.detail})});document.body.appendChild(p);},1500);</script>'
            % (HERE / "audit_drawing.js").as_uri())
    i = text.lower().rfind("</body>")
    page = Path(prof) / "gallery_probe.html"
    page.write_text(text[:i] + tail + text[i:], encoding="utf-8")
    p = subprocess.run([exe, "--headless=new", "--disable-gpu", "--user-data-dir=" + prof, "--allow-file-access-from-files",
                        "--window-size=1280,2600", "--virtual-time-budget=9000", "--dump-dom", page.as_uri()],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=200)
    m = re.search(r'<pre id="out">(.*?)</pre>', p.stdout, re.S)
    return json.loads(unescape(m.group(1))) if m and m.group(1).strip() else None


def main():
    exe = browser()
    if not exe:
        print("  skip  no Chrome or Edge found - audit_drawing.js was not run (install Chrome, or run it by hand in a browser)")
        return 0
    prof = tempfile.mkdtemp(prefix="audit_drawing_")
    try:
        out = page_out(exe, FIX / "drawing_defects.html", prof)
        check("the probe ran in the browser and wrote its findings", out is not None, out)
        f = (out or {}).get("findings", [])
        has = lambda check_, svg, part=None: any(x["check"] == check_ and x["svg"] == svg and (part is None or x["part"] == part) for x in f)
        check("a rectangle room in a sloping hull pokes out (inside)", has("inside", "bad-inside", "room"), f)
        check("... also when the hull is a shared <use>", has("inside", "bad-use", "room-u"), f)
        check("a tank cut off at the drawing's edge (cut off)", has("cut off", "bad-cut", "tank"), f)
        check("a ring that only shows in a later step, cut off at the top", has("cut off", "bad-later", "zone")
              and any("later step" in x["detail"] for x in f if x["svg"] == "bad-later"), f)
        check("a label printed over a line (text zone)", has("text zone", "bad-text-over", "over"), f)
        check("a label touching the edge of its own box (text zone)", has("text zone", "bad-text-edge", "edge"), f)
        check("a clean drawing is silent - slope, marked pipe, overhanging roof, clipped liquid, clear label",
              not [x for x in f if x["svg"] == "good"], [x for x in f if x["svg"] == "good"])
        check("a clean drawing through a shared <use> is silent", not [x for x in f if x["svg"] == "good-use"],
              [x for x in f if x["svg"] == "good-use"])
        check("a drawing that leaves most of its frame blank (empty)", has("empty", "bad-empty"), f)
        check("a drawing that fills its frame is silent", not [x for x in f if x["svg"] == "good-full"],
              [x for x in f if x["svg"] == "good-full"])
        check("the verdict fails the page", (out or {}).get("verdict", "").startswith("VERDICT: FAIL"), out)

        # finding 13 - contrast of each part of a kit figure against its (dark) panel
        cc = page_out(exe, FIX / "drawing_contrast.html", prof) or {}
        cf = [x for x in cc.get("findings", []) if x["check"] == "contrast"]
        bad = {x["part"] for x in cf}
        check("a label coloured for a light slide (navy, steel) on a kit figure's dark panel is found",
              {"bad-text-navy", "bad-text-steel"} <= bad, cf)
        check("a line (steel) and a filled shape (navy) that vanish on the panel are found",
              {"bad-line-steel", "bad-rect-navy"} <= bad, cf)
        check("what is seen is silent: light label, light line, navy text on a light card inside the figure",
              not ({"good-text", "good-line", "text-on-card", "card"} & bad), cf)
        check("a part marked data-low-contrast is left alone, and a drawing that is not a kit figure is not judged",
              not ({"ok-quiet", "plain-navy"} & bad) and len(cf) == 4, cf)
        check("the finding says the ratio and what to do",
              all(":1" in x["detail"] and "dark panel" in x["detail"] for x in cf), cf)

        # C11 (IGF M06) - judged after animations and transitions settle; a fade the figure's value drives is judged at full
        st = page_out(exe, FIX / "drawing_settle.html", prof) or {}
        sf = [x for x in st.get("findings", []) if x["check"] == "contrast"]
        sbad = {x["part"] for x in sf}
        check("a part still fading in by an animation (a deck's fade, a colour transition) is judged once it has settled",
              not ({"fade-anim", "fade-trans"} & sbad), sf)
        check("a part a kit figure's value fades (style.opacity) is judged at full opacity - a 16:1 sign is not 1.5:1",
              "fade-inline" not in sbad, sf)
        check("... and the check is not relaxed: navy on the dark panel is still found, light text is silent",
              sbad == {"bad-navy"}, sf)

        # K12 (IGF M06) - EMPTY counts a pipe by its box, judges a stepping figure at its busiest step, says where
        ek = page_out(exe, FIX / "drawing_empty_kit.html", prof) or {}
        ef = [x for x in ek.get("findings", []) if x["check"] == "empty"]
        eby = {x["svg"]: x for x in ef}
        check("a figure that is mostly one small tank is empty", "bad-sparse" in eby, ef)
        check("the finding says where the blank piece is (side and pixels)",
              "bad-sparse" in eby and "the largest blank piece is" in eby["bad-sparse"]["detail"]
              and re.search(r"on the right.*from x \d+, y \d+ to x \d+, y \d+ px", eby["bad-sparse"]["detail"]), ef)
        check("two pipe routes round the panel are counted by their box: the space inside their bends is not blank",
              "good-pipes" not in eby, ef)
        check("a figure whose rest state and last state are sparse is judged at its busiest step (a pool fire that burns, then goes out)",
              "good-busiest" not in eby, ef)
        # 2.49.7 (IGF M01 s02) - each step is judged by what it shows: parts still to come (opacity 0) are not counted
        check("a stepping figure is judged by what each step shows, and the finding names its busiest step - the scale with "
              "all three markers in (step 3 of 3), not the rest state (step 0) with them hidden",
              "bad-scale" in eby and "at its busiest step (step 3 of 3)" in eby["bad-scale"]["detail"], ef)

        gal = gallery_contrast(exe, prof)
        check("the kit's own gallery (every part, %s figures) passes the contrast check" % (gal or {}).get("n"),
              gal is not None and gal["n"] >= 15 and not gal["f"], gal)

        ph = (page_out(exe, FIX / "drawing_photo.html", prof) or {}).get("findings", [])
        photo = lambda svg: [x for x in ph if x["check"] == "photo over drawing" and x["svg"] == svg]
        check("a photo laid on the drawing is found, data-may-overlap or not (IGF M02 s13, 2.49.6)",
              bool(photo("bad-photo")) and photo("bad-photo")[0]["part"] == "pic-on", ph)
        check("a photo in its own column beside the drawing, and a marker drawn on a photo, are silent",
              not photo("good-beside") and not photo("good-marker"), ph)
        sc = (page_out(exe, FIX / "deck_scroll.html", prof) or {}).get("findings", [])
        scrolls = lambda sid: [x for x in sc if x["check"] == "scrolls" and "(%s)" % sid in x["where"]]
        check("a slide whose box scrolls 8 px is reported - no scrollbar on a slide (owner, 2026-10-16)",
              scrolls("scrolls") and "8 px more than it shows" in scrolls("scrolls")[0]["detail"], sc)
        check("a slide that fits, and 1 px of scrollHeight rounding, are silent", not scrolls("fits") and not scrolls("rounding"), sc)

        fit = page_out(exe, FIX / "drawing_fit.html", prof) or {}
        sp = [float(v) for v in (fit.get("spills") or "0 0 0 0").split()]
        check("gb_fit widens a frame a drawing reaches past (up and right)", sp[1] < -16 and sp[0] + sp[2] > 108, fit)
        check("gb_fit leaves a drawing that fits", fit.get("fits") == "0 0 100 60", fit)
        check("gb_fit leaves data-fit=\"off\" alone", fit.get("off") == "0 0 100 60", fit)
    finally:
        shutil.rmtree(prof, ignore_errors=True)
    print("\n%d passed, %d failed" % (len(PASS), len(FAIL)))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
