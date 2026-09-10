#!/usr/bin/env python3
"""Audit a course module's visual layer against the canonical token set.

    python audit_ui.py <course_dir_or_css_file> [...]

Reports, per stylesheet:
  * raw hex / rgba on chrome (color/background/border) outside :root - what drifts
  * raw hex on fill/stroke is reported separately: diagram colour, normally fine
  * tokens whose value differs from the canonical set
  * canonical tokens that are missing
  * tokens that are not in the canonical set (with the alias, when there is one)
  * stylesheets with no :root at all

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

STRICT = False

# a raw colour is legitimate in these places
ALLOW_CONTEXT = re.compile(r"url\(|data:|linear-gradient|radial-gradient")


def load_canon():
    p = Path(__file__).resolve().parents[1] / "knowledge" / "tokens.json"
    d = json.loads(p.read_text(encoding="utf-8"))
    canon = {k: v["value"] for k, v in d["tokens"].items()}
    aliases = {k: v for k, v in d.get("aliases", {}).items() if not k.startswith("_")}
    return canon, aliases


def strip_root(css):
    """Everything except the :root block, so declarations there are not flagged."""
    return ROOT.sub("", css)


def audit(path, canon, aliases):
    css = path.read_text(encoding="utf-8", errors="replace")
    defects, drift, notes = [], [], []

    m = ROOT.search(css)
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
                alias = aliases.get(k)
                notes.append(
                    "%s is not canonical%s" % (k, " - use %s" % alias if alias else " and has no alias")
                )
        missing = [k for k in canon if k not in declared]
        if missing:
            notes.append("missing %d canonical tokens: %s" % (len(missing), ", ".join(sorted(missing)[:10])))

    return defects, drift, notes


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

    files = []
    for t in args.targets:
        p = Path(t)
        if p.is_dir():
            files += [f for f in sorted(p.rglob("*.css")) if ".bak" not in f.name and "oldversion" not in f.parts]
        elif p.suffix == ".css":
            files.append(p)
    if not files:
        print("No stylesheets found.")
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

    print("\n%d stylesheets read - %d defects, %d drift/review findings." % (len(files), n_def, n_drift))
    if not STRICT:
        print("Run with --strict on a NEW deck to fail on raw chrome colours.")
    if n_drift and not n_def:
        print("Drift in a shipped module is the owner's call. Report it; do not repaint it.")
    return 1 if n_def else 0


if __name__ == "__main__":
    sys.exit(main())
