#!/usr/bin/env python3
"""Audit a course module's visual layer against the canonical token set.

    python audit_ui.py <course_dir_or_css_file> [...]

Also audits each PAGE for classes that no stylesheet the page actually loads
defines - the defect that shipped in the ETPB3 pilot, where a module moved onto
the canonical shell and silently lost every callout, caption and table rule.

Reports, per stylesheet:
  * raw hex / rgba on chrome (color/background/border) outside :root - what drifts
  * raw hex on fill/stroke is reported separately: diagram colour, normally fine
  * tokens whose value differs from the canonical set
  * canonical tokens that are missing
  * tokens that are not in the canonical set (with the alias, when there is one)
  * stylesheets with no :root at all

Reports, per page:
  * classes used in the markup that no loaded stylesheet defines

Exit code 1 only under --strict. By default this is a report, not a gate: the shipped GAS
BASIC decks carry raw chrome colours (the reference module itself has 82), so a gate on by
default would fail every existing module and teach people to ignore it. Repainting a
signed-off deck is the owner's decision, not this script's.
"""

import argparse
import json
import re
import sys
from pathlib import Path

HEX = re.compile(r"#[0-9a-fA-F]{3,8}\b")
RGBA = re.compile(r"\brgba?\([^)]*\)")
DECL = re.compile(r"(--[a-z][\w-]*)\s*:\s*([^;]+);")
ROOT = re.compile(r":root\s*\{(.*?)\}", re.S)
DECL_ANY = re.compile(r"([a-zA-Z-]+)\s*:\s*([^;{}]+);")
CONTENT_PROPS = {"fill", "stroke", "stop-color", "flood-color"}
FOLLOWS = re.compile(r"^var\(\s*(--[a-z][\w-]*)")

STRICT = False

# a raw colour is legitimate in these places
ALLOW_CONTEXT = re.compile(r"url\(|data:|linear-gradient|radial-gradient")


def load_canon():
    p = Path(__file__).resolve().parents[1] / "knowledge" / "tokens.json"
    d = json.loads(p.read_text(encoding="utf-8"))
    canon = {k: v["value"] for k, v in d["tokens"].items()}
    aliases = {k: v for k, v in d.get("aliases", {}).items() if not k.startswith("_")}
    return canon, aliases


COMMENT = re.compile(r"/\*.*?\*/", re.S)


def mask_comments(css):
    """Blank every comment, preserving length so offsets still line up.

    A hex written inside a comment is not a colour anyone sees. gb_task.css
    names the three dialect values it replaced in its own header; without this
    the auditor reported the documentation as the drift."""
    return COMMENT.sub(lambda m: " " * len(m.group(0)), css)


def strip_root(css):
    """Everything except the :root block, so declarations there are not flagged."""
    return ROOT.sub("", mask_comments(css))


def audit(path, canon, aliases):
    css = path.read_text(encoding="utf-8", errors="replace")
    defects, drift, notes, follows = [], [], [], []

    m = ROOT.search(mask_comments(css))
    if not m:
        notes.append("no :root block - this file inherits its tokens from whatever is loaded first")
        declared = {}
    else:
        declared = {k: v.strip() for k, v in DECL.findall(m.group(1))}

    # --- raw colours outside :root, split by what they paint
    #
    # A raw hex on fill/stroke is usually a diagram colour - the sea in an illustration, the
    # vapour in a cross-section - and is legitimately one-off. A raw hex on color/background/
    # border is chrome, and chrome is what drifts. Only the second kind is a finding.
    body = strip_root(css)
    chrome, content = [], []
    for m in DECL_ANY.finditer(body):
        prop, val = m.group(1).lower(), m.group(2)
        if ALLOW_CONTEXT.search(val):
            continue
        hits = HEX.findall(val) + RGBA.findall(val)
        if not hits:
            continue
        (content if prop in CONTENT_PROPS else chrome).extend(hits)

    if chrome:
        uniq = sorted(set(chrome))
        msg = "%d raw chrome colours outside :root (%d distinct): %s" % (
            len(chrome), len(uniq), ", ".join(uniq[:8]) + ("..." if len(uniq) > 8 else ""))
        (defects if STRICT else drift).append(msg)
    if content:
        notes.append("%d raw colours on fill/stroke - diagram colours, normally fine" % len(content))

    if declared:
        for k, v in sorted(declared.items()):
            if k in canon:
                if v.lower().replace(" ", "") != canon[k].lower().replace(" ", ""):
                    drift.append("%s = %s   (canonical %s)" % (k, v, canon[k]))
            else:
                # A local name whose value is var(--canonical, fallback) is not a
                # second palette - it FOLLOWS the canonical token and only falls
                # back when this file is used standalone. That is the pattern
                # kbd_escape.css and task_complete.css use so they stay drop-in.
                f = FOLLOWS.match(v)
                if f and f.group(1) in canon:
                    follows.append("%s follows %s" % (k, f.group(1)))
                    continue
                alias = aliases.get(k)
                notes.append(
                    "%s is not canonical%s" % (k, " - use %s" % alias if alias else " and has no alias")
                )
        missing = [k for k in canon if k not in declared]
        if missing:
            notes.append("missing %d canonical tokens: %s" % (len(missing), ", ".join(sorted(missing)[:10])))

    if follows:
        notes.append("%d local name(s) follow the canonical set: %s"
                     % (len(follows), "; ".join(follows[:6]) + ("..." if len(follows) > 6 else "")))

    return defects, drift, notes


# ---------------------------------------------------------------------------
# PAGE CHECK: does every class the markup uses actually have a rule?
#
# Added in 2.2.0. The ETPB3 pilot shipped a module that had been moved onto the
# canonical shell and had silently lost every callout, caption and table rule -
# those lived only in a per-course stylesheet the rebuilt page no longer linked.
# Every other validator was green. Nothing was wrong with the CSS and nothing
# was wrong with the HTML; the two had simply stopped being introduced.
# ---------------------------------------------------------------------------
LINK = re.compile(r"<link\b[^>]*>", re.I)
IS_SHEET = re.compile(r"rel\s*=\s*[\"']?stylesheet", re.I)
HREF = re.compile(r"href\s*=\s*[\"']([^\"']+)[\"']", re.I)
STYLE_BLOCK = re.compile(r"<style[^>]*>(.*?)</style>", re.S | re.I)
CLASS_ATTR = re.compile(r"class\s*=\s*[\"']([^\"']*)[\"']", re.I)
CLASS_RULE = re.compile(r"\.(-?[A-Za-z_][\w-]*)")
TAG_WITH_CLASS = re.compile(r"<([A-Za-z][\w-]*)\b[^>]*?class\s*=\s*[\"']([^\"']*)[\"']", re.I)

# A class on a <g> or other SVG container is usually a name for a part of a
# drawing - addressed by script, or simply documenting the structure. Missing
# styling there is not a defect, so those are listed separately.
SVG_CONTAINERS = {"g", "defs", "symbol", "marker", "clippath",
                  "lineargradient", "radialgradient", "pattern", "mask"}


def page_classes(html_path):
    """(unstyled, structural, n_used) for one page, or None if it is a fragment."""
    raw = html_path.read_text(encoding="utf-8", errors="replace")
    head = raw[:2000].lower()
    if "<!doctype" not in head and "<html" not in head and "<body" not in head:
        return None  # a fragment is pasted into a page and loads no CSS of its own

    css = "".join(STYLE_BLOCK.findall(raw))
    for tag in LINK.findall(raw):
        if not IS_SHEET.search(tag):
            continue
        m = HREF.search(tag)
        if not m:
            continue
        href = m.group(1).split("?")[0].split("#")[0]
        if "://" in href:
            continue  # a remote sheet cannot be read here, and the tablet is offline anyway
        f = (html_path.parent / href).resolve()
        if f.exists():
            css += "\n" + f.read_text(encoding="utf-8", errors="replace")

    defined = set(CLASS_RULE.findall(mask_comments(css)))

    used, on_svg, on_normal = set(), set(), set()
    for tag, names in TAG_WITH_CLASS.findall(raw):
        bucket = on_svg if tag.lower() in SVG_CONTAINERS else on_normal
        for n in names.split():
            used.add(n)
            bucket.add(n)

    missing = sorted(u for u in used if u not in defined)
    structural = [u for u in missing if u in on_svg and u not in on_normal]
    unstyled = [u for u in missing if u not in structural]
    return unstyled, structural, len(used)


VAR_USE = re.compile(r"var\(\s*(--[a-z][\w-]*)")
VAR_DEF = re.compile(r"(--[a-z][\w-]*)\s*:")


def page_dead_vars(html_path, canon):
    """Custom properties a page references that nothing will define for it.

    An unresolvable custom property does not fall back to the previous value -
    the whole declaration becomes invalid at computed-value time. ETPB3's task
    pages kept `background:var(--okbg)` from the retired ETPA1 dialect, so the
    correct answer and the wrong answer both rendered with a transparent ground
    and an inherited black border. Every static check passed. The browser
    showed it on the first click.

    Looks in <style> blocks AND in style="" attributes, which is where the last
    four survivors were hiding."""
    raw = html_path.read_text(encoding="utf-8", errors="replace")
    head = raw[:2000].lower()
    if "<!doctype" not in head and "<html" not in head and "<body" not in head:
        return None

    defined = set(canon)
    css_local = "".join(STYLE_BLOCK.findall(raw))
    for tag in LINK.findall(raw):
        if not IS_SHEET.search(tag):
            continue
        m = HREF.search(tag)
        if not m or "://" in m.group(1):
            continue
        f = (html_path.parent / m.group(1).split("?")[0].split("#")[0]).resolve()
        if f.exists():
            css_local += "\n" + f.read_text(encoding="utf-8", errors="replace")
    defined |= set(VAR_DEF.findall(css_local))

    used = set(VAR_USE.findall(mask_comments(css_local)))
    for attr_css in re.findall(r"style\s*=\s*[\"\']([^\"\']*)[\"\']", raw):
        used |= set(VAR_USE.findall(attr_css))
    return sorted(used - defined)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("targets", nargs="+", help="a course folder, a module folder, or .css files")
    ap.add_argument("--strict", action="store_true",
                    help="treat raw chrome colours as defects and exit 1. Use on NEW decks; "
                         "the shipped GAS BASIC modules do not pass it.")
    args = ap.parse_args()

    global STRICT
    STRICT = args.strict

    canon, aliases = load_canon()

    def skip(f):
        return ".bak" in f.name or "oldversion" in f.parts or "retired" in f.parts

    files, pages = [], []
    for t in args.targets:
        p = Path(t)
        if p.is_dir():
            files += [f for f in sorted(p.rglob("*.css")) if not skip(f)]
            pages += [f for f in sorted(p.rglob("*.htm*")) if not skip(f)]
        elif p.suffix == ".css":
            files.append(p)
        elif p.suffix in (".html", ".htm"):
            pages.append(p)
    if not (files or pages):
        print("No stylesheets or pages found.")
        return 1

    n_def = n_drift = 0
    for f in files:
        defects, drift, notes = audit(f, canon, aliases)
        if not (defects or drift or notes):
            continue
        print("\n%s" % f)
        for d in defects:
            n_def += 1
            print("   DEFECT  %s" % d)
        for d in drift:
            n_drift += 1
            print("   DRIFT   %s" % d)
        for d in notes:
            print("   note    %s" % d)

    n_page = n_frag = 0
    for pg in pages:
        r = page_classes(pg)
        if r is None:
            n_frag += 1
            continue
        n_page += 1
        unstyled, structural, n_used = r
        dead = page_dead_vars(pg, canon)
        if dead:
            n_def += len(dead)
            print("\n%s" % pg)
            print("   DEFECT  %d custom propert%s referenced that nothing defines for this page:"
                  % (len(dead), "y" if len(dead) == 1 else "ies"))
            print("           %s" % " ".join(dead))
            print("           An unresolvable var() voids the WHOLE declaration - the colour")
            print("           does not fall back, it disappears. Usually a retired dialect.")
        if unstyled:
            n_def += len(unstyled)
            print("\n%s" % pg)
            print("   DEFECT  %d of %d classes have no rule in any stylesheet this page loads:"
                  % (len(unstyled), n_used))
            print("           %s" % " ".join("." + u for u in unstyled))
            print("           Either the page lost a <link>, or the rule was never written.")
        elif structural:
            print("\n%s" % pg)
            print("   note    %d drawing-structure class(es) unstyled, which is normal: %s"
                  % (len(structural), " ".join("." + u for u in structural)))

    print("\n%d stylesheet(s) and %d page(s) read - %d defects, %d drift/review findings."
          % (len(files), n_page, n_def, n_drift))
    if n_frag:
        print("%d fragment(s) skipped - a fragment is pasted into a page and loads no CSS itself." % n_frag)
    if not STRICT:
        print("Run with --strict on a NEW deck to fail on raw chrome colours.")
    if n_drift and not n_def:
        print("Drift in a shipped module is the owner's call. Report it; do not repaint it.")
    return 1 if n_def else 0


if __name__ == "__main__":
    sys.exit(main())
