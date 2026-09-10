#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_task_pages.py — static sweeps over trainee task screens.

Everything here is checkable by code, which is the only reason it is code: a rule
enforced by a model remembering it is a rule that holds until the session gets long.
See references/verify.md for how to use this, and SKILL.md for why each check exists.

    python check_task_pages.py <path> [<path> ...] [--css DIR] [--js DIR]
                               [--only NAME] [--viewport WxH] [--quiet]

<path> is a task page, or a directory searched recursively for *.html.
--css / --js add extra directories of stylesheets / scripts to the reference
search (the page's own <link>/<script> targets are resolved automatically).

Checks, runnable individually with --only:

  syntax      SKILL.md §12 — inline <script> blocks parse. Needs `node`.
  deadmarkup  SKILL.md §13 — ids nothing reads, CSS classes no markup uses.
  numbers     SKILL.md §10 — totals computed and never painted (heuristic).
  floor       SKILL.md §11 — type / tap sizes that RESOLVE below the floor at
              --viewport (default 800x1280). Resolves all three clamp() dials;
              see §11.1. SVG font-size and em/%/calc/var are deferred to the
              probe rather than guessed.
  kbd         SKILL.md §5  — a page with text fields loads the escape engine.

Exit codes, so this can gate a build:

  0  every enabled check passed
  1  findings — printed with file and line
  2  usage error (no path, path missing, no HTML found)
  3  a check could not RUN (e.g. node absent). Not a pass. A skipped check
     reported as a pass is how the comma defect in SKILL.md §12 survived.

PRECEDENCE. measure_in_page.js in a real browser is the authority; this script
only decides what is worth looking at. A finding here is a question to take to
the page, never a defect to fix on sight — references/verify.md says why.

Stdlib only, Python 3.8+. No network.
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile

FLOOR_TEXT_PX = 12.5
FLOOR_TAP_PX = 44.0

CHECKS = ("syntax", "deadmarkup", "numbers", "floor", "kbd")

# Identifiers that read as "a number a RECORD SHEET might ask for".
#
# Deliberately narrower than it first was. The first version included `right`,
# `correct`, `count` and `tally`, and on a real shared task engine it flagged
# `newlyRight` — an internal per-submit counter that no record asks for and
# that correctly never reaches the DOM. Loop counters and per-item tallies are
# the normal way to write a grader; treating them as reportable numbers turns
# this check into noise, and a noisy check gets ignored along with its true
# positives. What a record actually asks for is a total, a score, a mark or a
# percentage, so that is what this matches.
TOTAL_NAMES = re.compile(
    r"\b(?:var|let|const)\s+([A-Za-z_$][\w$]*(?:total|score|points?|marks?|"
    r"pct|percent|grade)[\w$]*)\s*=", re.I)

DOM_WRITE = re.compile(
    r"(?:textContent|innerHTML|innerText|outerHTML|\.value\s*=|insertAdjacentHTML"
    r"|createTextNode|TaskDone\.show|GBDone\.show|\.title\s*=|setAttribute)", re.I)

SINGLE_LINE_INPUT = re.compile(
    r"<input\b(?![^>]*\btype\s*=\s*[\"']?(?:hidden|checkbox|radio|button|submit|"
    r"reset|file|range|image|color)\b)[^>]*>", re.I)

KBD_CSS = re.compile(r"(?:kbd_escape|gb_kbd)\.css", re.I)
KBD_JS = re.compile(r"(?:kbd_escape|gb_kbd)\.js", re.I)


# --------------------------------------------------------------------------- io

def read(path):
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        return fh.read()


def line_of(text, pos):
    return text.count("\n", 0, pos) + 1


def is_within(path, root):
    """True if `path` sits inside directory (or is the file) `root`."""
    path, root = os.path.abspath(path), os.path.abspath(root)
    if os.path.isfile(root):
        return path == root
    return os.path.commonpath([path, root]) == root


def collect(paths, exts):
    out = []
    for p in paths:
        if os.path.isfile(p):
            if os.path.splitext(p)[1].lower() in exts:
                out.append(os.path.abspath(p))
        elif os.path.isdir(p):
            for root, dirs, files in os.walk(p):
                dirs[:] = [d for d in dirs
                           if d not in (".git", "node_modules", "__pycache__")]
                for f in files:
                    if os.path.splitext(f)[1].lower() in exts:
                        out.append(os.path.abspath(os.path.join(root, f)))
    return sorted(set(out))


def linked_assets(html_files):
    """Resolve each page's own <link href> and <script src> to files on disk."""
    css, js = set(), set()
    href = re.compile(r"""<link\b[^>]*\bhref\s*=\s*["']([^"']+\.css)["']""", re.I)
    src = re.compile(r"""<script\b[^>]*\bsrc\s*=\s*["']([^"']+\.js)["']""", re.I)
    for page in html_files:
        base = os.path.dirname(page)
        body = read(page)
        for rx, bucket in ((href, css), (src, js)):
            for m in rx.finditer(body):
                ref = m.group(1).split("?")[0].split("#")[0]
                if ref.startswith(("http:", "https:", "//", "data:")):
                    continue
                cand = os.path.abspath(os.path.join(base, ref))
                if os.path.isfile(cand):
                    bucket.add(cand)
    return sorted(css), sorted(js)


def _mask(m):
    """Blank a comment out in place, keeping every newline and every column.

    Replacing a comment with a single space is what made every CSS finding
    report the wrong line on a real 986-line stylesheet: a five-line comment
    collapsed to one character and swallowed four newlines, so every line
    number after it drifted. A finding with a wrong line number is worse than
    no finding — the reader looks at the named line, sees a comment, and stops
    trusting the tool. Masking preserves both line and column exactly.
    """
    return re.sub(r"[^\n]", " ", m.group(0))


def strip_comments_css(text):
    return re.sub(r"/\*.*?\*/", _mask, text, flags=re.S)


def strip_comments_js(text):
    text = re.sub(r"/\*.*?\*/", _mask, text, flags=re.S)
    return re.sub(r"(?<![:\\/])//[^\n]*", _mask, text)


def inline_styles(html):
    """(start_line, css) for every <style> block, so findings get real line numbers."""
    out = []
    for m in re.finditer(r"<style\b[^>]*>(.*?)</style\s*>", html, re.I | re.S):
        out.append((line_of(html, m.start(1)) - 1, strip_comments_css(m.group(1))))
    return out


def inline_scripts(html):
    """(start_offset, code) for every <script> with no src attribute."""
    out = []
    for m in re.finditer(r"<script\b([^>]*)>(.*?)</script\s*>", html, re.I | re.S):
        attrs, code = m.group(1), m.group(2)
        if re.search(r"\bsrc\s*=", attrs, re.I):
            continue
        t = re.search(r"""\btype\s*=\s*["']?([^"'\s>]+)""", attrs, re.I)
        if t and "javascript" not in t.group(1).lower() and t.group(1).lower() != "module":
            continue          # a JSON or template block, not script
        if code.strip():
            out.append((m.start(2), code))
    return out


# ----------------------------------------------------------------- check: syntax

def check_syntax(html_files, _ctx):
    """SKILL.md §12. An inline script is all-or-nothing: one bad token disables
    every control on the page while it still looks perfect."""
    findings = []
    node = shutil.which("node") or shutil.which("node.exe")
    if not node:
        return findings, ("node is not installed, so inline scripts were NOT "
                          "syntax-checked. Load each page and read the browser "
                          "console — SKILL.md §12. That is now the only check.")
    tmp = tempfile.mkdtemp(prefix="taskux_")
    try:
        for page in html_files:
            html = read(page)
            for idx, (off, code) in enumerate(inline_scripts(html)):
                stub = os.path.join(tmp, "s%d.js" % idx)
                with open(stub, "w", encoding="utf-8") as fh:
                    fh.write(code)
                r = subprocess.run([node, "--check", stub],
                                   capture_output=True, text=True)
                if r.returncode != 0:
                    msg = (r.stderr or r.stdout or "").strip().splitlines()
                    detail = msg[-1] if msg else "parse failed"
                    for ln in msg:
                        if "SyntaxError" in ln:
                            detail = ln.strip()
                            break
                    findings.append((page, line_of(html, off),
                                     "inline script does not parse: %s "
                                     "(every control on this page is dead)" % detail))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return findings, None


# ------------------------------------------------------------- check: deadmarkup

def check_deadmarkup(html_files, ctx):
    """SKILL.md §13. Conservative on purpose: only things referenced NOWHERE."""
    findings = []
    css_text = " ".join(strip_comments_css(read(p)) for p in ctx["css"])
    js_text = " ".join(strip_comments_js(read(p)) for p in ctx["js"])
    inline_js, inline_css = [], []
    html_bodies = {}
    for page in html_files:
        html = read(page)
        html_bodies[page] = html
        for _off, code in inline_scripts(html):
            inline_js.append(strip_comments_js(code))
        for m in re.finditer(r"<style\b[^>]*>(.*?)</style\s*>", html, re.I | re.S):
            inline_css.append(strip_comments_css(m.group(1)))
    all_js = js_text + " " + " ".join(inline_js)
    all_css = css_text + " " + " ".join(inline_css)
    all_html = " ".join(html_bodies.values())

    # --- ids that nothing reads -------------------------------------------
    for page, html in html_bodies.items():
        for m in re.finditer(r"""\bid\s*=\s*["']([^"'\s]+)["']""", html):
            ident = m.group(1)
            if re.search(r"[#.\[\]{}]", ident):
                continue
            referenced = (
                re.search(r"#" + re.escape(ident) + r"\b", all_css) or
                re.search(r"#" + re.escape(ident) + r"\b", all_js) or
                re.search(r"""["']#?""" + re.escape(ident) + r"""["']""", all_js) or
                re.search(r"""\bhref\s*=\s*["'][^"']*#""" + re.escape(ident)
                          + r"""["']""", all_html) or
                re.search(r"""\b(?:for|aria-\w+|form|list|headers)\s*=\s*["'][^"']*\b"""
                          + re.escape(ident) + r"""\b""", all_html))
            if not referenced:
                findings.append((page, line_of(html, m.start()),
                                 'id="%s" is read by no script, no stylesheet and '
                                 "no anchor — delete it" % ident))

    # --- CSS classes no markup uses ---------------------------------------
    html_classes = set()
    for html in html_bodies.values():
        for m in re.finditer(r"""\bclass(?:List)?\s*=\s*["']([^"']*)["']""", html):
            html_classes.update(m.group(1).split())
    js_tokens = set(re.findall(r"""["']([A-Za-z][\w-]{1,60})["']""", all_js))
    js_tokens.update(re.findall(r"""["']\.([A-Za-z][\w-]{1,60})""", all_js))

    # A stylesheet that lives OUTSIDE the scanned tree also serves markup outside
    # the scanned tree, so its classes cannot be judged from here. On a real run
    # this produced 125 findings, nearly all from a shared `../../../gb_nav.css`
    # whose classes are used by the app shell — which was not in scope. A check
    # that emits that much noise gets ignored along with its true positives, so
    # out-of-scope stylesheets are counted and skipped rather than reported.
    in_scope, out_of_scope = [], []
    for p in ctx["css"]:
        (in_scope if any(is_within(p, r) for r in ctx["roots"])
         else out_of_scope).append(p)

    css_units = [(p, strip_comments_css(read(p)), 0) for p in in_scope]
    for page, html in html_bodies.items():
        for off, body in inline_styles(html):
            css_units.append((page, body, off))

    seen = {}
    for path, body, off in css_units:
        for m in re.finditer(r"\.(-?[A-Za-z_][\w-]*)", body):
            cls = m.group(1)
            if cls not in html_classes and cls not in js_tokens:
                seen.setdefault(cls, []).append((path, off + line_of(body, m.start())))
    for cls, hits in sorted(seen.items()):
        path, ln = hits[0]
        extra = (" (and %d more places)" % (len(hits) - 1)) if len(hits) > 1 else ""
        findings.append((path, ln,
                         ".%s is styled here%s but appears in no markup and no "
                         "script in scope — dead" % (cls, extra)))
    note = None
    if len(findings) > 20:
        note = ("%d findings is the signature of a PER-MODULE COPY that has drifted "
                "(SKILL.md §14), not an emergency: a shared stylesheet copied into every "
                "module carries every module's classes, so most are dead in any one copy. "
                "Confirm a sample against the whole course before deleting anything — "
                "deleting from one copy only is itself drift." % len(findings))
    if out_of_scope:
        extra = ("%d stylesheet(s) linked from outside the scanned paths were not swept for "
                "dead classes (%s) — they also serve markup you did not give me. Widen the "
                "paths to judge them."
                % (len(out_of_scope), ", ".join(os.path.basename(p) for p in out_of_scope[:4])
                   + (" …" if len(out_of_scope) > 4 else "")))
        note = (note + " Also: " + extra) if note else extra
    return findings, None, note


# ---------------------------------------------------------------- check: numbers

def statement_around(code, pos):
    """The enclosing statement: back to the previous `;`, forward to the next one.

    An earlier version used a +/- 200 character window and let a DOM write on the
    NEXT line count as painting the variable — a false pass on the exact defect
    this check exists for (a fixture with `scoreTotal = 7;` followed by an
    unrelated `textContent =` line reported clean). Statement bounds are tighter
    and still keep a multi-line `TaskDone.show({ line: ... })` call intact,
    because that whole call is one statement.
    """
    a = code.rfind(";", max(0, pos - 600), pos)
    b = code.find(";", pos)
    return code[(a + 1) if a != -1 else max(0, pos - 600):
                (b + 1) if b != -1 else min(len(code), pos + 600)]


def check_numbers(html_files, ctx):
    """SKILL.md §10. Heuristic — flags candidates. The record sheet is the authority."""
    findings = []
    units = [(p, strip_comments_js(read(p))) for p in ctx["js"]]
    for page in html_files:
        html = read(page)
        for _off, code in inline_scripts(html):
            units.append((page, strip_comments_js(code)))
    for path, code in units:
        for m in TOTAL_NAMES.finditer(code):
            name = m.group(1)
            painted = False
            for use in re.finditer(r"\b" + re.escape(name) + r"\b", code):
                if use.start() == m.start(1):
                    continue
                if DOM_WRITE.search(statement_around(code, use.start())):
                    painted = True
                    break
            if not painted:
                findings.append((path, line_of(code, m.start(1)),
                                 "CANDIDATE — confirm before changing anything: `%s` is "
                                 "computed and never reaches the DOM. If a record asks "
                                 "for this number the trainee cannot read it (SKILL.md "
                                 "§10); if it is an internal counter, this is noise."
                                 % name))
    note = None
    if findings:
        note = ("these are candidates, not defects. Open the record sheet and keep only "
                "the ones it actually asks for — an internal counter that never paints "
                "is correct code.")
    return findings, None, note


# ------------------------------------------------------------------ check: floor

def _px(value):
    m = re.match(r"\s*(-?\d+(?:\.\d+)?)\s*px\s*$", value or "")
    return float(m.group(1)) if m else None


ROOT_FONT_PX = 16.0     # assumed :root font-size for rem; em is not resolvable statically


def resolve_len(expr, vw, vh):
    """Resolve a CSS length to px at a target viewport, or None if not resolvable.

    Returns (px, dial) where dial names what actually decided the value:
    "px" / "vw" / "rem" ... for a plain length, and for a clamp() one of
    "clamp-min", "clamp-coefficient" or "clamp-ceiling".

    WHY THIS EXISTS. The rule this checker used to apply — "flag a clamp()
    whose minimum is below the floor" — is an oversimplification that produced
    12 false positives on one real stylesheet. `clamp(11px,1.6vw,14px)` at
    800px wide resolves to 1.6 x 8 = 12.8px: the COEFFICIENT binds and the 11px
    minimum never applies. Both directions of the mistake are real, so looking
    at any single dial is wrong about the other two:

      - the coefficient can paint under the floor whatever the minimum says.
        At a 768px-tall viewport 1vmin is 7.68px, so anything under about
        1.63vmin is sub-floor no matter how healthy its minimum looks.
      - the ceiling can bind so the coefficient never engages at all.

    Only the RESOLVED value at the target viewport means anything. Anything
    this cannot resolve (em, %, calc, var) returns None and is not flagged —
    a false negative is acceptable because the browser probe is the authority;
    a false positive is what makes people stop running the tool.
    """
    if not expr:
        return None
    e = expr.strip().rstrip(";").strip()

    m = re.match(r"clamp\(\s*(.+)\s*\)$", e, re.I)
    if m:
        parts = _split_args(m.group(1))
        if len(parts) != 3:
            return None
        vals = [resolve_len(p, vw, vh) for p in parts]
        if any(v is None for v in vals):
            return None
        lo, mid, hi = (v[0] for v in vals)
        # clamp(MIN, VAL, MAX) == max(MIN, min(VAL, MAX))
        if mid > hi:
            return (hi, "clamp-ceiling")
        if mid < lo:
            return (lo, "clamp-min")
        return (mid, "clamp-coefficient")

    m = re.match(r"(-?\d+(?:\.\d+)?)\s*(px|vw|vh|vmin|vmax|rem|pt)$", e, re.I)
    if not m:
        return None
    n, unit = float(m.group(1)), m.group(2).lower()
    if unit == "px":
        return (n, "px")
    if unit == "pt":
        return (n * 4.0 / 3.0, "pt")
    if unit == "rem":
        return (n * ROOT_FONT_PX, "rem")
    if unit == "vw":
        return (n * vw / 100.0, "vw")
    if unit == "vh":
        return (n * vh / 100.0, "vh")
    if unit == "vmin":
        return (n * min(vw, vh) / 100.0, "vmin")
    if unit == "vmax":
        return (n * max(vw, vh) / 100.0, "vmax")
    return None


def _split_args(s):
    """Split a comma-separated CSS argument list, respecting nested parens."""
    out, depth, cur = [], 0, ""
    for ch in s:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == "," and depth == 0:
            out.append(cur)
            cur = ""
        else:
            cur += ch
    if cur.strip():
        out.append(cur)
    return [p.strip() for p in out]


# A rule paints SVG text if it sets an SVG-only property or selects SVG nodes.
# Its declared font-size is NOT its painted size — see SKILL.md §11 — so the
# static check must not judge it. measure_in_page.js already does this right.
SVG_DECL = re.compile(r"(?<![\w-])(?:fill|stroke|stroke-width|paint-order)\s*:", re.I)
SVG_SEL = re.compile(r"(?:^|[\s>+~,])(?:svg|text|tspan|textPath)(?:[\s>+~,.:\[]|$)", re.I)


def check_floor(html_files, ctx):
    """SKILL.md §11, static half only. Geometry and contrast need the in-page
    probe — scripts/measure_in_page.js. These are the ones visible in the source."""
    findings = []
    units = [(p, strip_comments_css(read(p)), 0) for p in ctx["css"]]
    for page in html_files:
        html = read(page)
        units.extend((page, body, off) for off, body in inline_styles(html))
        for m in re.finditer(r"""\bstyle\s*=\s*["']([^"']*)["']""", html):
            units.append((page, "[style]{" + m.group(1) + "}",
                          line_of(html, m.start()) - 1))

    vw, vh = ctx["viewport"]
    deferred_svg = 0

    for path, body, off in units:
        for rule in re.finditer(r"([^{}]*)\{([^{}]*)\}", body):
            sel, decl = rule.group(1), rule.group(2)
            sel_start, decl_start = rule.start(1), rule.start(2)
            is_svg = bool(SVG_DECL.search(decl) or SVG_SEL.search(sel))

            # ---- type size. font-size ONLY: `padding:clamp(10px,2.4vw,18px)`
            # was reported as a type-floor finding before this gate existed.
            for d in re.finditer(r"(?<![\w-])font-size\s*:\s*([^;}]+)", decl, re.I):
                raw = d.group(1).strip()
                if is_svg:
                    # declared != painted for SVG text (SKILL.md §11): the
                    # effective size scales by rendered width / viewBox width,
                    # which no static reader can know. Left to the probe.
                    deferred_svg += 1
                    continue
                got = resolve_len(raw, vw, vh)
                if got is None:
                    continue                    # unresolvable: never guess
                px, dial = got
                if px < FLOOR_TEXT_PX:
                    findings.append((path, off + line_of(body, decl_start + d.start(1)),
                                     "font-size:%s resolves to %.2fpx at %dx%d (%s binds) "
                                     "— below the %.1fpx text floor"
                                     % (raw, px, vw, vh, dial, FLOOR_TEXT_PX)))

            # ---- tap targets declared small on something obviously tappable
            tappable = re.search(r"cursor\s*:\s*pointer", decl, re.I) or \
                re.search(r"\b(?:button|\.btn|\[role=[\"']?button)", sel, re.I)
            if not tappable:
                continue
            # (?<![\w-]) so `min-height` is not also matched as `height`, which
            # reported the same 30px rule twice on the first fixture run
            for prop in ("height", "min-height", "width", "min-width"):
                d = re.search(r"(?<![\w-])" + prop + r"\s*:\s*([^;}]+)", decl, re.I)
                if not d:
                    continue
                got = resolve_len(d.group(1), vw, vh)
                if got is None:
                    continue
                px, dial = got
                if 0 < px < FLOOR_TAP_PX:
                    findings.append((path, off + line_of(body, decl_start + d.start(1)),
                                     "%s:%s resolves to %.2fpx at %dx%d (%s binds) on a "
                                     "tappable rule (%s) — below the %.0fpx tap floor"
                                     % (prop, d.group(1).strip(), px, vw, vh, dial,
                                        sel.strip()[:48], FLOOR_TAP_PX)))

    note = None
    if deferred_svg:
        note = ("%d SVG font-size declaration(s) were NOT judged here — declared is not "
                "painted for SVG text. Run scripts/measure_in_page.js, which applies the "
                "scale correctly." % deferred_svg)
    return findings, None, note


# -------------------------------------------------------------------- check: kbd

def check_kbd(html_files, _ctx):
    """SKILL.md §5. A text field with no way out of the keyboard is a dead page."""
    findings = []
    for page in html_files:
        html = read(page)
        inputs = SINGLE_LINE_INPUT.findall(html)
        areas = re.findall(r"<textarea\b", html, re.I)
        if not inputs and not areas:
            continue
        if not KBD_CSS.search(html) or not KBD_JS.search(html):
            findings.append((page, 1,
                             "%d text field(s) but the keyboard-escape engine is not "
                             "loaded — link kbd_escape.css and kbd_escape.js "
                             "(SKILL.md §5)" % (len(inputs) + len(areas))))
        for m in SINGLE_LINE_INPUT.finditer(html):
            hint = re.search(r"""\benterkeyhint\s*=\s*["']?([\w-]+)""", m.group(0), re.I)
            if hint and hint.group(1).lower() != "done":
                findings.append((page, line_of(html, m.start()),
                                 'enterkeyhint="%s" on a single-line input contradicts '
                                 "the Done key (SKILL.md §5)" % hint.group(1)))
        for m in re.finditer(r"<textarea\b[^>]*>", html, re.I):
            if re.search(r"\benterkeyhint\s*=", m.group(0), re.I):
                findings.append((page, line_of(html, m.start()),
                                 "a textarea carries enterkeyhint — Enter is a newline "
                                 "there and must stay one (SKILL.md §5)"))
    return findings, None


RUNNERS = {
    "syntax": check_syntax,
    "deadmarkup": check_deadmarkup,
    "numbers": check_numbers,
    "floor": check_floor,
    "kbd": check_kbd,
}


# ------------------------------------------------------------------------- main

def main(argv=None):
    ap = argparse.ArgumentParser(add_help=True, description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paths", nargs="*", help="task page(s) or directory")
    ap.add_argument("--css", action="append", default=[], metavar="DIR")
    ap.add_argument("--js", action="append", default=[], metavar="DIR")
    ap.add_argument("--only", action="append", default=[], choices=CHECKS)
    ap.add_argument("--viewport", default="800x1280", metavar="WxH",
                    help="target viewport for resolving vw/vh/clamp in the floor "
                         "check (default 800x1280, the portrait tablet this standard "
                         "was ruled for). A different device re-measures its floor — "
                         "SKILL.md, 'the delivery target is a parameter'.")
    ap.add_argument("--quiet", action="store_true",
                    help="print findings only, no per-check headings")
    args = ap.parse_args(argv)

    if not args.paths:
        ap.print_usage(sys.stderr)
        print("error: give at least one task page or directory", file=sys.stderr)
        return 2
    for p in args.paths + args.css + args.js:
        if not os.path.exists(p):
            print("error: no such path: %s" % p, file=sys.stderr)
            return 2

    html = collect(args.paths, {".html", ".htm"})
    if not html:
        print("error: no .html found under %s" % ", ".join(args.paths), file=sys.stderr)
        return 2

    css, js = linked_assets(html)
    css = sorted(set(css) | set(collect(args.css, {".css"})))
    js = sorted(set(js) | set(collect(args.js, {".js"})))
    vp = re.match(r"^(\d{2,5})\s*[xX×]\s*(\d{2,5})$", args.viewport.strip())
    if not vp:
        print("error: --viewport must look like 800x1280, got %r" % args.viewport,
              file=sys.stderr)
        return 2
    roots = [os.path.abspath(p) for p in args.paths + args.css + args.js]
    ctx = {"css": css, "js": js, "roots": roots,
           "viewport": (int(vp.group(1)), int(vp.group(2)))}

    enabled = args.only or list(CHECKS)
    if not args.quiet:
        print("task-ux sweep · %d page(s), %d stylesheet(s), %d script(s) · floor "
              "resolved at %dx%d"
              % (len(html), len(css), len(js), ctx["viewport"][0], ctx["viewport"][1]))

    total, skipped = 0, []
    for name in CHECKS:
        if name not in enabled:
            continue
        result = RUNNERS[name](html, ctx)
        findings, note = result[0], result[1]
        info = result[2] if len(result) > 2 else None
        if note:
            skipped.append((name, note))
        if not args.quiet:
            state = "SKIPPED" if note else ("%d finding(s)" % len(findings) if findings else "ok")
            print("\n-- %-10s %s" % (name, state))
            if info:
                print("   note: %s" % info)
        for path, ln, msg in findings:
            print("%s:%s: %s" % (path, ln, msg))
        total += len(findings)

    for name, note in skipped:
        print("\n!! %s could not run: %s" % (name, note), file=sys.stderr)

    if skipped:
        print("\nexit 3 — a check did not run. That is not a pass.", file=sys.stderr)
        return 3
    if total:
        print("\n%d finding(s). Nothing here is cosmetic; each cites its rule." % total)
        return 1
    if not args.quiet:
        print("\nall enabled checks passed. The in-page probe and driving the task "
              "(references/verify.md) are still required.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
