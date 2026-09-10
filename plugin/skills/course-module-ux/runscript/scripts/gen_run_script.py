#!/usr/bin/env python3
"""Generate the instructor's running order FROM the module page's own markup.

Nobody hand-writes slide numbers into instructor material. Cutting or reordering a
deck silently invalidates every slide-number cross-reference: 96 of them broke across
two modules in one afternoon, and the instructor guide then told the instructor to
announce the wrong task at three of five activities.

So the numbers are derived, and this is regenerated after ANY deck change.

Usage
-----
    python gen_run_script.py MODULE.html -o RUN_SCRIPT.md [--manifest TASKS_FILE]...

Exit codes
----------
    0  clean run, file written
    1  written, but findings need a human: an unmatched activity code, a launch
       screen with no code, a block with no minutes, a code guessed from a title
    2  usage or parse error, nothing written
"""

import argparse
import html
import os
import re
import sys
from html.parser import HTMLParser

# ---------------------------------------------------------------------------
# CONFIG -- the markup contract. Change these, not the logic below.
# ---------------------------------------------------------------------------

SLIDE_TAG = "section"
SLIDE_CLASS = "slide"          # matched as a whole class token, so .slide-body is not a slide

ATTR_BLOCK = "data-block"
ATTR_KIND = "data-kind"
ATTR_TITLE = "data-title"
ATTR_MINS = "data-mins"          # may sit on the section OR on any element inside it
ATTR_ACTIVITY = "data-activity"
ATTR_CUE = "data-cue"

# A screen whose KIND matches one of these looks like a launch even with no code.
# Keep this list NARROW. A loose word like "drill" matches every screen that
# describes a drill, and then a code gets guessed off six description screens --
# see code_from_title() below for why that is the expensive mistake.
LAUNCH_KIND_WORDS = ("launch", "live activity")

# Kinds whose screens are read to the room and pressed past with no action.
PASSIVE_HINT = "just press Next"

# A code looks like this. Deliberately narrow: letters then digits, no spaces.
CODE_RE = re.compile(r"\b([A-Z][A-Z]{0,7}\d{1,4}[A-Z]?)\b")


def mins_of(attrs):
    """Minutes as an int, from a lower-cased attribute dict. Absent or unparseable
    reads as 0 rather than raising -- a malformed timer must not stop the run
    script being generated, it must show up as a block declaring 0."""
    raw = re.sub(r"\D", "", attrs.get(ATTR_MINS, ""))
    return int(raw) if raw else 0


class SlideScanner(HTMLParser):
    """Collect one record per section.slide, in document order."""

    def __init__(self):
        HTMLParser.__init__(self, convert_charrefs=False)
        self.slides = []

    def handle_starttag(self, tag, attrs):
        a = dict((k.lower(), v or "") for k, v in attrs)

        if tag.lower() == SLIDE_TAG and SLIDE_CLASS in a.get("class", "").split():
            self.slides.append(
                {
                    "n": len(self.slides) + 1,
                    "classes": a.get("class", "").split(),
                    "block": html.unescape(a.get(ATTR_BLOCK, "")).strip(),
                    "kind": html.unescape(a.get(ATTR_KIND, "")).strip(),
                    "title": html.unescape(a.get(ATTR_TITLE, "")).strip(),
                    "mins": mins_of(a),
                    "activity": html.unescape(a.get(ATTR_ACTIVITY, "")).strip(),
                    "cue": html.unescape(a.get(ATTR_CUE, "")).strip(),
                }
            )
            return

        # data-mins is commonly rendered by a timer element INSIDE the slide rather
        # than declared on the section. Both are the same fact, so collect either.
        if self.slides and ATTR_MINS in a:
            self.slides[-1]["mins"] += mins_of(a)


def is_launch(slide):
    """TRAP 1 -- the activity code must WIN over the slide kind.

    One module labels its task screens "Real scenes then tablets", "The person",
    "Incident analysis" while carrying the code. Checking the kind first swallowed
    four of five tasks into "just press Next". So: a code present means launch,
    full stop; the kind is only consulted when there is no code.
    """
    if slide["activity"]:
        return True
    k = slide["kind"].lower()
    c = " ".join(slide["classes"]).lower()
    for w in LAUNCH_KIND_WORDS:
        if w in k or w in c:
            return True
    return False


def normalise(code):
    """TRAP 2 -- a task manifest may DECORATE codes ("T1 . marked",
    "GAS701 . scored"). Exact-matching a bare code against those fails and turns
    real tablet tasks into "run it in the room". Strip to the bare code."""
    if not code:
        return ""
    code = code.replace("·", " ").replace("|", " ")
    m = CODE_RE.search(code.upper())
    if m:
        return m.group(1)
    return code.strip().upper()


def code_in_manifest(code, manifest_text):
    """Whole-token search, so T1 does not match inside T10, and decoration around
    the code is irrelevant."""
    if not code:
        return False
    return re.search(
        r"(?<![A-Za-z0-9])" + re.escape(code) + r"(?![A-Za-z0-9])", manifest_text
    ) is not None


def code_from_title(slide, findings):
    """TRAP 3 -- only extract a code from a title on a screen that is ALREADY a
    launch. Presentation screens titled "P1 run - check and zero" otherwise invent
    eleven activities that do not exist."""
    if not is_launch(slide):
        return ""
    m = CODE_RE.search(slide["title"].upper())
    if not m:
        return ""
    findings.append(
        "screen %d (%s): no %s attribute; code %r guessed from the title. "
        "Add the attribute so this stops being a guess."
        % (slide["n"], slide["block"] or "no block", ATTR_ACTIVITY, m.group(1))
    )
    return m.group(1)


def group_blocks(slides):
    """Consecutive runs of the same data-block. A block that reappears later is a
    separate run and is reported as such -- a split block is usually an ordering
    mistake, not a plan."""
    runs = []
    for s in slides:
        key = s["block"] or "(no block)"
        if runs and runs[-1]["block"] == key:
            runs[-1]["slides"].append(s)
        else:
            runs.append({"block": key, "slides": [s]})
    return runs


def render(slides, runs, manifest_text, findings, source_name):
    out = []
    total_mins = sum(s["mins"] for s in slides)

    out.append("# Instructor run script — %s" % source_name)
    out.append("")
    out.append(
        "**GENERATED — do not hand-edit.** Every screen number below is derived from "
        "the module page's markup. Regenerate after any change to the deck; a "
        "hand-written slide number is wrong the moment a screen is inserted."
    )
    out.append("")
    out.append(
        "%d screens · %d blocks · %d minutes declared."
        % (len(slides), len(runs), total_mins)
    )
    out.append("")
    out.append("You open the page once, press Start, and press Next to the end.")
    out.append("")

    silent_blocks = []
    for run in runs:
        ss = run["slides"]
        first, last = ss[0]["n"], ss[-1]["n"]
        block_mins = sum(s["mins"] for s in ss)
        mins = " · %d min" % block_mins if block_mins else ""
        if not block_mins:
            silent_blocks.append("%s (screens %d–%d)" % (run["block"], first, last))
        span = "screen %d" % first if first == last else "screens %d–%d" % (first, last)
        out.append("---")
        out.append("")
        out.append("## %s — %s%s" % (run["block"], span, mins))
        out.append("")

        for idx, s in enumerate(ss):
            code = normalise(s["activity"]) or code_from_title(s, findings)
            label = s["title"] or s["kind"] or "(untitled screen)"
            if code:
                where = "on the tablets"
                if manifest_text and not code_in_manifest(code, manifest_text):
                    where = "IN THE ROOM — this code is not in the task manifest"
                    findings.append(
                        "screen %d: activity %r is not in any manifest supplied. "
                        "Either it is a room activity, or the code is wrong."
                        % (s["n"], code)
                    )
                out.append(
                    "**%d · %s** — **launch `%s`** %s. %s"
                    % (s["n"], label, code, where, s["kind"])
                )
            elif is_launch(s):
                out.append(
                    "**%d · %s** — launch, **code unknown**. %s"
                    % (s["n"], label, s["kind"])
                )
                findings.append(
                    "screen %d is a launch (kind %r) with no code at all. The "
                    "instructor cannot be told what to open." % (s["n"], s["kind"])
                )
            else:
                out.append("%d · %s — %s. %s" % (s["n"], label, s["kind"], PASSIVE_HINT))

            # A launch screen is normally at ceiling fill and cannot carry this line
            # itself, so the run script carries it: how many screens belong to the
            # thing that was just announced.
            rest = len(ss) - idx - 1
            if is_launch(s) and rest > 0:
                out.append("")
                out.append(
                    "  > The next %d screen%s %s the %s of this block, screens %d–%d. "
                    "You do not leave the page — page through them where you stand."
                    % (
                        rest,
                        "" if rest == 1 else "s",
                        "is" if rest == 1 else "are",
                        "run" if code else "description",
                        s["n"] + 1,
                        ss[-1]["n"],
                    )
                )

            if s["cue"]:
                out.append("")
                out.append("  > _Your cue (not on the screen):_ %s" % s["cue"])
            out.append("")

    if silent_blocks:
        findings.append(
            "%d of %d blocks declare no minutes, so the %d-minute total is short: %s. "
            "Add %s. A module with no minute total cannot be checked against its "
            "approved hours, and one that under-declares hides missing work."
            % (
                len(silent_blocks),
                len(runs),
                total_mins,
                "; ".join(silent_blocks),
                ATTR_MINS,
            )
        )

    if findings:
        out.append("---")
        out.append("")
        out.append("## Findings a human has to close")
        out.append("")
        for f in findings:
            out.append("- %s" % f)
        out.append("")

    return "\n".join(out) + "\n"


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("page", help="the module HTML page")
    p.add_argument("-o", "--out", required=True, help="markdown file to write")
    p.add_argument(
        "--manifest",
        action="append",
        default=[],
        help="a file that knows the real activity codes (task manifest, JS, HTML). "
        "Repeatable. Codes are matched as whole tokens, so decoration is fine.",
    )
    args = p.parse_args(argv)

    if not os.path.isfile(args.page):
        sys.stderr.write("no such page: %s\n" % args.page)
        return 2
    try:
        with open(args.page, encoding="utf-8", errors="replace") as fh:
            src = fh.read()
        sc = SlideScanner()
        sc.feed(src)
    except Exception as exc:                        # noqa: BLE001 - report, do not crash
        sys.stderr.write("could not parse %s: %s\n" % (args.page, exc))
        return 2

    if not sc.slides:
        sys.stderr.write(
            "found no %s.%s elements in %s — check SLIDE_TAG/SLIDE_CLASS in CONFIG\n"
            % (SLIDE_TAG, SLIDE_CLASS, args.page)
        )
        return 2

    manifest_text = ""
    for m in args.manifest:
        if not os.path.isfile(m):
            sys.stderr.write("no such manifest: %s\n" % m)
            return 2
        with open(m, encoding="utf-8", errors="replace") as fh:
            manifest_text += fh.read() + "\n"

    findings = []
    body = render(
        sc.slides,
        group_blocks(sc.slides),
        manifest_text,
        findings,
        os.path.basename(args.page),
    )
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(body)

    sys.stderr.write("wrote %s — %d screens\n" % (args.out, len(sc.slides)))
    for f in findings:
        sys.stderr.write("  FINDING: %s\n" % f)
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
