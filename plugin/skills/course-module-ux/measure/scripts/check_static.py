#!/usr/bin/env python3
"""Static checks on a module page — the ones a browser is not needed for.

Every check here is one a human reliably gets wrong by eye, usually because the
right scope is not the whole file. The headline example: counting <a href> in a
module page is NOT the zero-links-inside-a-slide check, because the landing screen
and the footer have legitimate links and they drown the real failure.

Usage
-----
    python check_static.py slide-links   MODULE.html
    python check_static.py check-screen  MODULE.html
    python check_static.py mins          LANDING.html
    python check_static.py paper         DIR_OR_FILE...
    python check_static.py links         DIR
    python check_static.py all           MODULE.html

Exit codes
----------
    0  clean
    1  one or more findings, each printed with enough detail to act on
    2  usage error, a missing file, or a parse failure — nothing was checked
"""

import argparse
import io
import json
import os
import re
import sys
from html.parser import HTMLParser

HERE = os.path.dirname(os.path.abspath(__file__))
FLOOR_PATH = os.path.join(HERE, os.pardir, "knowledge", "floor.json")

# --------------------------------------------------------------------------
# CONFIG -- the markup contract. Change here, not in the logic.
# --------------------------------------------------------------------------
SLIDE_TAG = "section"
SLIDE_CLASS = "slide"
ATTR_BLOCK = "data-block"
ATTR_KIND = "data-kind"
ATTR_TITLE = "data-title"
CHECK_KIND_WORDS = ("check", "module check", "assessment")
EXEMPT_FRAGMENT = re.compile(r"^(b=[A-Za-z0-9]+|run(=\d+)?|s=\d+|p=\d+)$")


def load_floor():
    try:
        with io.open(FLOOR_PATH, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception as exc:                                  # noqa: BLE001
        sys.stderr.write("cannot read %s: %s\n" % (FLOOR_PATH, exc))
        return None


class SlideCarver(HTMLParser):
    """Carve each section.slide out of the source and keep what is INSIDE it.

    Nested <section> elements are tracked by depth so a slide that contains a
    section does not close early.
    """

    def __init__(self):
        HTMLParser.__init__(self, convert_charrefs=False)
        self.slides = []            # {n, block, kind, title, links[], text}
        self._depth = 0
        self._cur = None

    def handle_starttag(self, tag, attrs):
        t = tag.lower()
        a = dict((k.lower(), v or "") for k, v in attrs)
        if self._cur is None:
            if t == SLIDE_TAG and SLIDE_CLASS in a.get("class", "").split():
                self._cur = {
                    "n": len(self.slides) + 1,
                    "block": a.get(ATTR_BLOCK, ""),
                    "kind": a.get(ATTR_KIND, ""),
                    "title": a.get(ATTR_TITLE, ""),
                    "links": [],
                    "text": [],
                }
                self._depth = 1
            return
        if t == SLIDE_TAG:
            self._depth += 1
        if t == "a" and "href" in a:
            self._cur["links"].append(a["href"])

    def handle_endtag(self, tag):
        if self._cur is None:
            return
        if tag.lower() == SLIDE_TAG:
            self._depth -= 1
            if self._depth == 0:
                self.slides.append(self._cur)
                self._cur = None

    def handle_data(self, data):
        if self._cur is not None:
            self._cur["text"].append(data)


def carve(path, findings):
    try:
        with io.open(path, encoding="utf-8", errors="replace") as fh:
            src = fh.read()
    except Exception as exc:                                  # noqa: BLE001
        sys.stderr.write("cannot read %s: %s\n" % (path, exc))
        return None
    c = SlideCarver()
    c.feed(src)
    if c._cur is not None:                                    # unclosed slide
        findings.append(
            "slide %d (%s) is never closed — the carve is unreliable, so no "
            "per-slide result below can be trusted. Fix the markup first."
            % (c._cur["n"], c._cur["block"] or "no block")
        )
    if not c.slides:
        sys.stderr.write(
            "no %s.%s elements in %s — check SLIDE_TAG/SLIDE_CLASS in CONFIG\n"
            % (SLIDE_TAG, SLIDE_CLASS, path)
        )
        return None
    return c.slides


# --------------------------------------------------------------------------
# checks
# --------------------------------------------------------------------------

def check_slide_links(path, findings):
    """Zero <a href> inside any slide.

    Counting links in the WHOLE FILE is not this check. Landing-screen and footer
    links are legitimate and will hide a single bad link inside a slide.
    """
    slides = carve(path, findings)
    if slides is None:
        return 2
    for s in slides:
        for href in s["links"]:
            findings.append(
                "slide %d (%s, %r) contains a link: %s — a link inside a delivery "
                "screen navigates away mid-session, which is the model this "
                "architecture replaced."
                % (s["n"], s["block"] or "no block", s["kind"], href)
            )
    return 0


def check_check_screen(path, findings, floor):
    """The module check is the last screen, has no links, and never says
    'record' or 'score' — it is read by the room while they are being assessed."""
    slides = carve(path, findings)
    if slides is None:
        return 2
    forbidden = floor["structural"]["check_screen_forbidden_words"]

    def is_check(s):
        """Read the KIND, not the prose.

        Matching a substring anywhere in kind+title found "check" inside
        "select it, check it" (M5 s13) and inside "the checklist and what it
        prevents" (M6 s14), and reported both as misplaced module checks while
        the real ones sat correctly at 18-of-19 and 16-of-17. A screen declares
        what it is in data-kind; the title is instructor prose and will contain
        the word "check" whenever the subject is a checklist or a check-and-zero
        procedure - which, in a gas course, is often.
        """
        kind = s["kind"].strip().lower()
        if not kind:
            return False
        if "module check" in kind:
            return True
        return kind in CHECK_KIND_WORDS

    checks = [s for s in slides if is_check(s)]
    if not checks:
        findings.append(
            "no screen looks like the module check (nothing in %s matched %s). "
            "Either the check is missing, or its %s needs to say so."
            % (ATTR_KIND + "/" + ATTR_TITLE, list(CHECK_KIND_WORDS), ATTR_KIND)
        )
        return 0
    # Until 2026-09-03 the check WAS the last screen. The owner then asked for a
    # hand-off screen after it, so Next cannot skip a room into the next module
    # by accident - the check is now second-to-last, the hand-off last. This
    # function asserted the old rule and reported a false defect on seven of the
    # eight decks. Read the current shape from floor.json rather than assuming,
    # so the next change is made in one place.
    st = floor["structural"]
    handoff_last = bool(st.get("handoff_screen_is_last", False))
    i = len(slides) - 2 if handoff_last else len(slides) - 1
    expect = slides[i] if 0 <= i < len(slides) else slides[-1]
    where = "second-to-last, with the hand-off last" if handoff_last else "the last one"
    if handoff_last and "hand-off" not in slides[-1]["kind"].lower():
        findings.append(
            "the last screen is %r, not the hand-off. floor.json expects the "
            "hand-off to be last." % slides[-1]["kind"]
        )
    for s in checks:
        if s["n"] != expect["n"]:
            findings.append(
                "the check screen is %d of %d; it should be %s."
                % (s["n"], len(slides), where)
            )
        if s["links"]:
            findings.append(
                "the check screen (%d) has %d link(s): %s"
                % (s["n"], len(s["links"]), ", ".join(s["links"][:3]))
            )
        body = "".join(s["text"]).lower()
        for w in forbidden:
            if re.search(r"\b" + re.escape(w), body):
                findings.append(
                    "the check screen (%d) contains the word %r. Marking and "
                    "recording are the instructor's job on the instructor's own "
                    "device, not something the room reads while being assessed."
                    % (s["n"], w)
                )
    return 0


def _top_level_objects(src, open_bracket_idx):
    """Return each top-level {...} literal inside the array starting at
    src[open_bracket_idx] == '['. Depth-aware, so nested objects (open:{...})
    stay inside their parent instead of being reported as separate steps."""
    out = []
    depth = 0
    start = None
    i = open_bracket_idx
    arr = 0
    while i < len(src):
        c = src[i]
        if c == "[":
            arr += 1
        elif c == "]":
            arr -= 1
            if arr == 0:
                break
        elif c == "{":
            if depth == 0:
                start = i
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0 and start is not None:
                out.append(src[start : i + 1])
                start = None
        i += 1
    return out


def check_mins(path, findings):
    """Every runner step carries mins:.

    One module shipped a step without it and rendered with no duration badge while
    every other module showed one — invisible in the source, obvious on screen.
    """
    try:
        with io.open(path, encoding="utf-8", errors="replace") as fh:
            src = fh.read()
    except Exception as exc:                                  # noqa: BLE001
        sys.stderr.write("cannot read %s: %s\n" % (path, exc))
        return 2
    # Scope to the steps array first. A naive brace regex over the whole file
    # matches every unrelated object literal that happens to carry a title: key,
    # which reports false steps and hides real ones.
    m = re.search(r"(?:\bSTEPS\s*=|\bsteps\s*:)\s*\[", src)
    if not m:
        sys.stderr.write(
            "no STEPS array found in %s — nothing to check. If the steps live "
            "somewhere else, say so rather than treating this as a pass.\n" % path
        )
        return 0
    steps = _top_level_objects(src, m.end() - 1)
    if not steps:
        sys.stderr.write("STEPS array in %s is empty\n" % path)
        return 0
    for i, st in enumerate(steps, 1):
        if not re.search(r"\bmins\s*:\s*\d", st):
            title = re.search(r"title\s*:\s*[\"']([^\"']{0,60})", st)
            findings.append(
                "step %d (%s) has no mins: — it will render with no duration badge "
                "while every other step shows one."
                % (i, title.group(1) if title else "untitled")
            )
    return 0


PAPER_RE = re.compile(
    r"print (?:one|it|this|a copy|out)|one per (?:group|trainee|pair)|"
    r"photocopy|hand out the sheet|blank ruled|photograph the filled|"
    r"[☐□]\s*(?:yes|no|n/a)",
    re.I,
)


def check_paper(targets, findings):
    """Nothing in the delivery path may require a printer.

    A factual reference to a source document that is itself printed is fine; an
    instruction to print in order to run the session is not. This finds candidates;
    a human decides which are which.
    """
    files = []
    for t in targets:
        if os.path.isfile(t):
            files.append(t)
        elif os.path.isdir(t):
            for dp, _dn, fn in os.walk(t):
                for f in fn:
                    if f.endswith((".html", ".htm")):
                        files.append(os.path.join(dp, f))
        else:
            sys.stderr.write("no such path: %s\n" % t)
            return 2
    for p in files:
        with io.open(p, encoding="utf-8", errors="replace") as fh:
            for ln, line in enumerate(fh, 1):
                m = PAPER_RE.search(line)
                if m:
                    findings.append(
                        "%s:%d paper wording %r — decide: a print button, a print "
                        "stylesheet, or a factual reference to a printed source is "
                        "fine; an instruction to print in order to run the session "
                        "is a defect." % (os.path.basename(p), ln, m.group(0).strip())
                    )
    return 0


def check_links(root, findings):
    """0 broken file links, 0 broken anchors, 0 missing assets, across a tree."""
    if not os.path.isdir(root):
        sys.stderr.write("not a directory: %s\n" % root)
        return 2
    pages = []
    for dp, _dn, fn in os.walk(root):
        for f in fn:
            if f.endswith((".html", ".htm")):
                pages.append(os.path.join(dp, f))
    ids = {}
    for p in pages:
        with io.open(p, encoding="utf-8", errors="replace") as fh:
            ids[p] = set(re.findall(r'id\s*=\s*"([^"]+)"', fh.read()))
    for p in pages:
        with io.open(p, encoding="utf-8", errors="replace") as fh:
            s = fh.read()
        d = os.path.dirname(p)
        for href in re.findall(r'<a\b[^>]*?href\s*=\s*"([^"]+)"', s):
            if href.startswith(("http", "mailto:", "tel:", "data:", "//", "javascript:")):
                continue
            tgt, _, frag = href.partition("#")
            if not tgt:
                if frag and not EXEMPT_FRAGMENT.match(frag) and frag not in ids[p]:
                    findings.append("%s: dead anchor %s" % (os.path.relpath(p, root), href))
                continue
            full = os.path.normpath(os.path.join(d, tgt))
            if not os.path.isfile(full):
                findings.append("%s: broken link %s" % (os.path.relpath(p, root), href))
            elif frag and not EXEMPT_FRAGMENT.match(frag) and frag not in ids.get(full, set()):
                findings.append("%s: dead anchor %s" % (os.path.relpath(p, root), href))
        for a in re.findall(
            r'(?:src|href)\s*=\s*"([^"]+\.(?:css|js|jpg|jpeg|png|svg|webp|woff2?))"', s
        ):
            if a.startswith(("http", "data:", "//")):
                continue
            if not os.path.isfile(os.path.normpath(os.path.join(d, a))):
                findings.append("%s: missing asset %s" % (os.path.relpath(p, root), a))
    sys.stderr.write("checked %d pages under %s\n" % (len(pages), root))
    return 0


def selftest():
    """Prove the checker is not silently passing everything.

    A checker that returns 'clean' on every input is worse than no checker, because
    it produces a signed-off report. So this runs the checks against a fixture that
    is DELIBERATELY broken and fails if they come back clean.
    """
    fixture = os.path.join(HERE, "fixtures", "control_page.html")
    if not os.path.isfile(fixture):
        sys.stderr.write("missing fixture: %s\n" % fixture)
        return 2
    floor = load_floor()
    if floor is None:
        return 2
    ok = True
    for name, fn, expect in (
        ("slide-links", lambda f: check_slide_links(fixture, f), 2),
        ("check-screen", lambda f: check_check_screen(fixture, f, floor), 2),
        ("mins", lambda f: check_mins(fixture, f), 1),
    ):
        f = []
        if fn(f) == 2:
            print("SELFTEST %s: could not run" % name)
            ok = False
            continue
        got = len(f)
        good = got >= expect
        ok = ok and good
        print(
            "SELFTEST %s: %d finding(s) on the broken fixture, expected >= %d — %s"
            % (name, got, expect, "ok" if good else "BROKEN CHECKER")
        )
    return 0 if ok else 1


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument(
        "check",
        choices=[
            "slide-links",
            "check-screen",
            "mins",
            "paper",
            "links",
            "all",
            "selftest",
        ],
    )
    p.add_argument("targets", nargs="*")
    args = p.parse_args(argv)

    if args.check == "selftest":
        return selftest()
    if not args.targets:
        sys.stderr.write("%s needs at least one target\n" % args.check)
        return 2

    floor = load_floor()
    if floor is None:
        return 2

    findings = []
    rc = 0

    # Every per-page check runs on EVERY target. It used to run on targets[0]
    # and drop the rest in silence, so `all` over eight decks opened one and
    # printed "0 finding(s)" - a clean bill of health for seven files nobody
    # had looked at. Findings are prefixed with the file they came from,
    # because with more than one target the bare message does not say where.
    def over(fn, label):
        out = 0
        for t in args.targets:
            mark = len(findings)
            r = fn(t)
            out = out or r
            # every deck's file is called index.html, so the basename alone
            # identifies nothing - carry the last two path parts.
            tag = os.path.join(*(os.path.normpath(t).split(os.sep)[-3:]))                 if os.sep in os.path.normpath(t) else t
            for i in range(mark, len(findings)):
                if len(args.targets) > 1 and not findings[i].startswith(tag):
                    findings[i] = "%s: %s" % (tag, findings[i])
        return out

    if args.check == "slide-links":
        rc = over(lambda t: check_slide_links(t, findings), "slide-links")
    elif args.check == "check-screen":
        rc = over(lambda t: check_check_screen(t, findings, floor), "check-screen")
    elif args.check == "mins":
        rc = over(lambda t: check_mins(t, findings), "mins")
    elif args.check == "paper":
        rc = check_paper(args.targets, findings)      # already walks the list
    elif args.check == "links":
        rc = over(lambda t: check_links(t, findings), "links")
    else:
        for fn in (
            lambda t: check_slide_links(t, findings),
            lambda t: check_check_screen(t, findings, floor),
            lambda t: check_paper([t], findings),
        ):
            r = over(fn, "all")
            rc = rc or r

    if rc == 2:
        return 2
    for f in findings:
        print("FINDING: %s" % f)
    print("%d finding(s)" % len(findings))
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
