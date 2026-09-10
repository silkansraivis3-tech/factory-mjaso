#!/usr/bin/env python3
"""The deterministic half of the visual quality gate.

Hard on facts, advisory on judgement. A remote asset reference is a FAIL; a
decorative-vocabulary match is a WARN, because only a human can say whether a
pulse is teaching a state change or filling a screen.

This script cannot tell you whether a visual teaches. review/GUIDE.md does that
half, and a clean run here is not a pass.

  python check_visuals.py <file-or-dir> [...] [--strict] [--json]

Exit 0 clean (or warnings only) · 1 failures · 2 bad usage.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
MOTION = os.path.join(SKILL, "review", "knowledge", "motion-rules.json")
FLOOR = os.path.join(SKILL, "review", "knowledge", "visual-floor.json")


def load(path: str, fallback: dict) -> dict:
    try:
        with open(path, encoding="utf-8-sig") as fh:
            return json.load(fh)
    except Exception:
        return fallback


MOTION_RULES = load(MOTION, {})
FLOOR_RULES = load(FLOOR, {})
DECOR = set(MOTION_RULES.get("decorative_vocabulary", {}).get("names", []))
MEAS = FLOOR_RULES.get("measurable", {})


def scalar(key, default):
    """A floor entry is either a bare number or an object documenting it."""
    v = MEAS.get(key, default)
    if isinstance(v, dict):
        v = v.get("value", default)
    return v


MIN_SVG_PX = float(scalar("svg_label_min_px", 12.5))
ALLOWED_EXT = set(MEAS.get("allowed_extensions",
                           ["jpg", "jpeg", "png", "svg", "webp", "gif", "mp4", "webm"]))

findings: list[dict] = []


def add(kind: str, path: str, msg: str, hint: str = "") -> None:
    findings.append({"kind": kind, "file": path, "message": msg, "hint": hint})


def fail(p, m, h=""): add("FAIL", p, m, h)
def warn(p, m, h=""): add("WARN", p, m, h)


def strip_comments(text: str) -> str:
    text = re.sub(r"<!--.*?-->", " ", text, flags=re.S)
    text = re.sub(r"/\*.*?\*/", " ", text, flags=re.S)
    return text


# ----------------------------------------------------------------- motion
def check_motion(path: str, raw: str) -> None:
    text = strip_comments(raw)

    declared = set(re.findall(r'data-motion\s*=\s*["\']([a-z]+)["\']', text))
    for d in declared:
        if d not in ("teaching", "affordance", "ambient"):
            fail(path, f'data-motion="{d}" is not a valid category',
                 'use teaching, affordance or ambient')

    # every @keyframes name defined here
    kf = set(re.findall(r"@keyframes\s+([A-Za-z_][\w-]*)", text))
    # names actually referenced by an animation
    used = set()
    for m in re.finditer(r"animation(?:-name)?\s*:\s*([^;{}]+)", text):
        for tok in re.split(r"[,\s]+", m.group(1)):
            tok = tok.strip()
            if tok and not re.match(r"^[\d.]+m?s$", tok) and tok not in (
                    "infinite", "linear", "ease", "ease-in", "ease-out",
                    "ease-in-out", "alternate", "both", "forwards", "backwards",
                    "normal", "reverse", "none", "paused", "running", "step-end"):
                used.add(tok)

    infinite = bool(re.search(r"animation[^;{}]*\binfinite\b", text))

    for name in sorted(kf & used):
        low = name.lower()
        if any(d in low for d in DECOR):
            if not declared:
                warn(path,
                     f'animation "{name}" uses decorative vocabulary and the file '
                     f'declares no data-motion category',
                     'declare data-motion="teaching|affordance|ambient", or remove the motion '
                     '(review/knowledge/motion-rules.json rejected_patterns)')
            else:
                warn(path,
                     f'animation "{name}" uses decorative vocabulary '
                     f'(declared: {", ".join(sorted(declared))})',
                     'confirm it is the declared category and not decoration')

    if infinite and "prefers-reduced-motion" not in text:
        fail(path, "infinite animation with no prefers-reduced-motion guard",
             "ambient motion must stop under prefers-reduced-motion: reduce")

    # A teaching animation needs controls - but only a DOCUMENT can carry them.
    # A stylesheet mentions data-step in a selector and holds no buttons; asking
    # it for a play button is how a check gets a reputation for crying wolf.
    if os.path.splitext(path)[1].lower() in (".html", ".htm"):
        if 'data-motion="teaching"' in text or "data-step" in text:
            controls = sum(1 for w in ("play", "pause", "step", "replay", "reset")
                           if re.search(r'\b(id|class|data-\w+)="[^"]*' + w, text, re.I))
            if controls < 2:
                warn(path, "stepped/teaching animation with fewer than two visible controls",
                     "an instructor must be able to play, pause, step and replay")


# ------------------------------------------------------------------- svg
def check_svg(path: str, raw: str) -> None:
    for m in re.finditer(r"<svg\b([^>]*)>", raw, re.I):
        attrs = m.group(1)
        vb = re.search(r'viewBox\s*=\s*["\']([^"\']+)["\']', attrs, re.I)
        if not vb:
            warn(path, "<svg> without a viewBox",
                 "a fixed-size SVG cannot scale to the tablet")
        if "role=" not in attrs.lower() and "aria-label" not in attrs.lower():
            warn(path, "<svg> without role/aria-label",
                 'add role="img" and an aria-label describing the whole figure')

        # rendered label size, using the viewBox width against a 380 px column
        if vb:
            try:
                parts = [float(x) for x in re.split(r"[\s,]+", vb.group(1).strip())]
                vbw = parts[2] if len(parts) >= 3 else 0
            except Exception:
                vbw = 0
            if vbw > 0:
                seg = raw[m.end(): m.end() + 60000]
                for fm in re.finditer(r'font-size\s*[:=]\s*["\']?([\d.]+)', seg):
                    units = float(fm.group(1))
                    rendered = units * (380.0 / vbw)
                    if rendered < MIN_SVG_PX:
                        warn(path,
                             f"SVG label {units:g} units renders ~{rendered:.1f}px "
                             f"in a 380px column (floor {MIN_SVG_PX})",
                             "measure the rendered size, not the viewBox units")
                        break


# ----------------------------------------------------------------- assets
REMOTE = re.compile(r'(?:src|href|url\()\s*=?\s*["\']?(https?://[^"\')\s]+)', re.I)
FONT_OK = ("appassets.androidplatform.net",)


def check_assets(path: str, raw: str) -> None:
    text = strip_comments(raw)
    for m in REMOTE.finditer(text):
        url = m.group(1)
        if any(h in url for h in FONT_OK):
            continue
        fail(path, f"remote asset reference: {url[:70]}",
             "the tablet has no network and the app 403s every external host - "
             "download and package it locally")

    for m in re.finditer(r"<img\b([^>]*)>", text, re.I):
        attrs = m.group(1)
        if "alt=" not in attrs.lower() and "aria-label" not in attrs.lower():
            warn(path, "<img> without alt", "every image needs alt or aria-label")
        src = re.search(r'src\s*=\s*["\']([^"\']+)["\']', attrs, re.I)
        if src:
            ext = os.path.splitext(src.group(1).split("?")[0])[1].lstrip(".").lower()
            if ext and ext not in ALLOWED_EXT:
                fail(path, f'image type ".{ext}" is not in the tablet MIME allowlist',
                     "allowed: " + ", ".join(sorted(ALLOWED_EXT)))


# ------------------------------------------------------- weak-visual smells
ARROW = r"(?:&rarr;|&#8594;|&#x2192;|→|➡|-->)"
CARDISH = r'class="[^"]*\b(?:card|tile|box|panel|step-box)\b[^"]*"'


def check_weak_patterns(path: str, raw: str) -> None:
    """The two shapes this whole skill exists to prevent.

    Detected STRUCTURALLY, not by counting: an unrelated hero image on the page
    must not excuse a box-and-arrow chain sitting under it.
    """
    text = strip_comments(raw)

    # --- box-and-arrow chain: block, arrow, block, arrow, block ---------
    # Collapse the document to the sequence of things that matter, then look
    # for the alternating run. Two arrows joining three blocks is a chain.
    tokens = []
    for m in re.finditer(CARDISH + r"|" + ARROW + r"|<svg\b|<img\b|<canvas\b", text, re.I):
        s = m.group(0)
        if re.match(r"<svg|<img|<canvas", s, re.I):
            tokens.append("FIG")
        elif re.match(r"class=", s, re.I):
            tokens.append("BOX")
        else:
            tokens.append("ARR")
    seq = "".join({"BOX": "B", "ARR": "A", "FIG": "F"}[t] for t in tokens)
    chain = re.search(r"B(?:AB){2,}", seq)          # B A B A B or longer
    if chain:
        n = chain.group(0).count("B")
        warn(path,
             f"box-and-arrow chain: {n} blocks joined by arrows",
             "this asserts a linearity real systems rarely have, and hides topology, "
             "service, direction and state - if the subject has structure, draw the "
             "structure (decide/knowledge/representations.json "
             "rejected_representations.box_and_arrow_chain)")

    # --- card grid of prose: cards carrying only sentences ---------------
    cards = re.findall(CARDISH + r"(.{0,1200}?)(?=" + CARDISH + r"|</section>|</main>|$)",
                       text, re.I | re.S)
    if len(cards) >= 4:
        with_fig = sum(1 for c in cards if re.search(r"<svg\b|<img\b|<canvas\b", c, re.I))
        words = sum(len(re.findall(r"[A-Za-z]{3,}", re.sub(r"<[^>]+>", " ", c)))
                    for c in cards)
        if with_fig == 0 and words > 60:
            warn(path,
                 f"{len(cards)} cards carrying {words} words and no figure between them",
                 "cards of prose carry no relationship, location, order or change - "
                 "that is a paragraph with borders. Name the learning need and pick a "
                 "representation (decide/knowledge/learning-needs.json)")


def check_file(path: str) -> None:
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            raw = fh.read()
    except Exception as exc:
        fail(path, f"unreadable: {exc}")
        return
    ext = os.path.splitext(path)[1].lower()
    if ext in (".html", ".htm", ".svg"):
        check_svg(path, raw)
        check_assets(path, raw)
        check_weak_patterns(path, raw)
    if ext in (".html", ".htm", ".css", ".svg"):
        check_motion(path, raw)


def collect(targets: list[str]) -> list[str]:
    out = []
    for t in targets:
        if os.path.isfile(t):
            out.append(t)
        elif os.path.isdir(t):
            for dp, dn, fn in os.walk(t):
                dn[:] = [d for d in dn if d not in
                         (".git", "__pycache__", "node_modules", "oldversion")]
                for f in fn:
                    if os.path.splitext(f)[1].lower() in (".html", ".htm", ".css", ".svg"):
                        out.append(os.path.join(dp, f))
    return sorted(set(out))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("targets", nargs="+")
    ap.add_argument("--strict", action="store_true", help="treat warnings as failures")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    files = collect(a.targets)
    if not files:
        print("no .html/.htm/.css/.svg files found in: " + ", ".join(a.targets))
        return 2
    for f in files:
        check_file(f)

    fails = [f for f in findings if f["kind"] == "FAIL"]
    warns = [f for f in findings if f["kind"] == "WARN"]

    if a.json:
        print(json.dumps({"files": len(files), "findings": findings}, indent=2))
    else:
        print("=" * 72)
        print("check_visuals - the deterministic half of the visual gate")
        print("=" * 72)
        for f in findings:
            print("  %-4s %s" % (f["kind"], os.path.basename(f["file"])))
            print("       %s" % f["message"])
            if f["hint"]:
                print("       -> %s" % f["hint"])
        if not findings:
            print("  no mechanical findings")
        print()
        print("%d file(s) - %d failure(s), %d warning(s)" % (len(files), len(fails), len(warns)))
        print()
        print("A clean run is NOT a pass. It means nothing mechanical is wrong.")
        print("Now run review/GUIDE.md: does this visual actually teach?")

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
