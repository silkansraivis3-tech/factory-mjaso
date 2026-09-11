#!/usr/bin/env python3
"""Can this module actually be advanced by a finger?

WHY IT EXISTS. The first real pilot shipped a 34-screen module whose JavaScript
read `document.getElementById('prev')` and `getElementById('next')` - and whose
HTML contained neither. Keyboard arrows worked, so it looked fine on a laptop.
On the Android tablet the module was unusable after screen 1, and every other
validator was green.

Keyboard navigation is NOT sufficient for a tablet course.

Checks
  1  nav-js-orphan      navigation JS addresses an id/class the HTML lacks
  2  no-touch-path      >1 screen and no tappable next/back of any kind
  3  trap               a screen is reachable with no way onward and no way out
  4  no-back-hook       a page has no `a.gbt-topback[href]`, no visible
                        `.gbn-back` and no hrefless `#gb-home` declaring it
                        deliberately has none (Android hardware Back exits the
                        app when none is present)
  5  tap-size           a navigation control below the 44 px floor

  python check_navigation.py <file-or-dir> [...] [--strict] [--json]

Exit 0 clean (or warnings only) · 1 failures · 2 bad usage.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

MIN_TAP = 44

# ids the engines conventionally drive, and what each one is for
NAV_IDS = {
    "btnNext": "next", "btnPrev": "back", "next": "next", "prev": "back",
    "btnGrid": "overview", "btnCue": "cue", "btnFull": "fullscreen",
    "btnExit": "exit", "startBtn": "start", "ovClose": "overview",
    "counter": "counter", "progress": "progress", "blockTag": "block",
}

# anything here counts as a tappable way forward
FORWARD_HINTS = re.compile(
    r'id="(btnNext|next)"|class="[^"]*\b(gbn-next|nav-next|act-open)\b',
    re.I)
BACK_HINTS = re.compile(
    r'id="(btnPrev|prev)"|class="[^"]*\b(gbn-back|nav-prev|gbt-topback)\b',
    re.I)

findings: list[dict] = []


def add(kind, path, msg, hint=""):
    findings.append({"kind": kind, "file": path, "message": msg, "hint": hint})


def fail(p, m, h=""): add("FAIL", p, m, h)
def warn(p, m, h=""): add("WARN", p, m, h)


def strip_comments(t: str) -> str:
    t = re.sub(r"<!--.*?-->", " ", t, flags=re.S)
    return t


def scripts_of(t: str) -> str:
    return "\n".join(re.findall(r"<script\b[^>]*>(.*?)</script>", t, re.S | re.I))


def is_fragment(raw: str) -> bool:
    """A figure fragment is markup meant to be pasted INTO a page, not a page.

    It has no doctype, no <html> and no <body>. Judging it as a page produces
    the false positive "the learner is trapped here" on a file no learner can
    ever open - which is how a validator loses its credibility."""
    head = raw[:2000].lower()
    return ("<!doctype" not in head and "<html" not in head and "<body" not in head)


def check_file(path: str, raw: str) -> None:
    if is_fragment(raw):
        return
    text = strip_comments(raw)
    js = scripts_of(text)
    body = re.sub(r"<script\b[^>]*>.*?</script>", " ", text, flags=re.S | re.I)

    slides = re.findall(r'<section[^>]*class="[^"]*\bslide\b', body, re.I)
    n = len(slides)

    present_ids = set(re.findall(r'\bid="([A-Za-z][\w-]*)"', body))

    # ---- 1 · navigation JS addressing something that is not there ----------
    wanted = set()
    for m in re.finditer(r'getElementById\(\s*["\']([\w-]+)["\']\s*\)', js):
        wanted.add(m.group(1))
    for m in re.finditer(r'querySelector\(\s*["\']#([\w-]+)["\']', js):
        wanted.add(m.group(1))

    orphans = sorted(i for i in wanted
                     if i in NAV_IDS and i not in present_ids)
    for o in orphans:
        fail(path,
             f'navigation JS drives #{o} ({NAV_IDS[o]}) but the HTML has no such element',
             "either add the control or remove the dead handler - a control the "
             "script expects and the page lacks is an unusable module, not a tidy one")

    # ---- 2 · a multi-screen module with no tappable path -------------------
    if n > 1:
        has_fwd = bool(FORWARD_HINTS.search(body))
        has_back = bool(BACK_HINTS.search(body))
        swipe = "touchstart" in js and ("next(" in js or "prev(" in js)

        if not has_fwd and not swipe:
            fail(path,
                 f"{n} screens and no tappable way forward "
                 f"(no next control, no swipe handler)",
                 "keyboard arrows are not navigation on a tablet - add the chrome "
                 "block from course-module-ui/templates/gb_shell.html")
        elif not has_fwd and swipe:
            warn(path,
                 f"{n} screens; forward is swipe-only",
                 "a swipe is undiscoverable. Add a visible Next control as well.")

        if not has_back and not swipe:
            fail(path,
                 f"{n} screens and no tappable way back",
                 "a learner who taps past a screen must be able to return")

    # ---- 3 · trapped: no way onward and no way out -------------------------
    links = re.findall(r'<a\b[^>]*href="([^"]+)"', body, re.I)
    real_links = [h for h in links if h and not h.startswith("#")]
    if n <= 1 and not real_links and "location.href" not in js and "history.back" not in js:
        fail(path, "single screen with no link out and no scripted navigation",
             "the learner is trapped on this page")

    # ---- 4 · the Android hardware-Back hook --------------------------------
    has_topback = re.search(r'<a\b[^>]*class="[^"]*\bgbt-topback\b[^"]*"[^>]*href=', body, re.I)
    has_gbnback = re.search(r'class="[^"]*\bgbn-back\b', body, re.I)
    declares_none = re.search(r'id="gb-home"', body, re.I)
    if not (has_topback or has_gbnback or declares_none):
        warn(path,
             "no a.gbt-topback[href], no .gbn-back and no hrefless #gb-home",
             "the Android hardware Back button clicks one of these; with none of "
             "them present it exits the app. If that is deliberate (a final "
             "assessment), declare it with an hrefless <span id=\"gb-home\">")

    # ---- 5 · navigation control tap size ------------------------------------
    css = "\n".join(re.findall(r"<style\b[^>]*>(.*?)</style>", raw, re.S | re.I))
    for sel in ("#btnNext", "#btnPrev", ".cbtn"):
        m = re.search(re.escape(sel) + r"\s*\{([^}]*)\}", css)
        if not m:
            continue
        blk = m.group(1)
        for prop in ("min-height", "height"):
            v = re.search(prop + r"\s*:\s*(\d+(?:\.\d+)?)px", blk)
            if v and float(v.group(1)) < MIN_TAP:
                fail(path, f"{sel} {prop} is {v.group(1)}px, below the {MIN_TAP}px floor",
                     "a navigation control is pressed hundreds of times a day")


def collect(targets):
    out = []
    for t in targets:
        if os.path.isfile(t) and t.lower().endswith((".html", ".htm")):
            out.append(t)
        elif os.path.isdir(t):
            for dp, dn, fn in os.walk(t):
                dn[:] = [x for x in dn if x not in (".git", "__pycache__", "_work", "oldversion")]
                for f in fn:
                    if f.lower().endswith((".html", ".htm")):
                        out.append(os.path.join(dp, f))
    return sorted(set(out))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("targets", nargs="+")
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    files = collect(a.targets)
    if not files:
        print("no HTML found in: " + ", ".join(a.targets))
        return 2

    fragments = 0
    for f in files:
        try:
            raw = open(f, encoding="utf-8", errors="replace").read()
        except Exception as exc:
            fail(f, f"unreadable: {exc}")
            continue
        if is_fragment(raw):
            fragments += 1
            continue
        check_file(f, raw)

    fails = [x for x in findings if x["kind"] == "FAIL"]
    warns = [x for x in findings if x["kind"] == "WARN"]

    if a.json:
        print(json.dumps({"files": len(files), "findings": findings}, indent=2))
    else:
        print("=" * 72)
        print("check_navigation - can a finger drive this module?")
        print("=" * 72)
        for x in findings:
            print("  %-4s %s" % (x["kind"], os.path.basename(x["file"])))
            print("       %s" % x["message"])
            if x["hint"]:
                print("       -> %s" % x["hint"])
        if not findings:
            print("  every page can be advanced and left by tapping")
        print()
        print("%d file(s) - %d failure(s), %d warning(s)%s"
              % (len(files), len(fails), len(warns),
                 ("  ·  %d fragment(s) skipped (no doctype/html/body)" % fragments)
                 if fragments else ""))

    if fails:
        return 1
    if warns and a.strict:
        return 1
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(2)
