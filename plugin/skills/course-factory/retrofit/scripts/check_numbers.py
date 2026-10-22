#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Number drift across a whole course: one quantity, two values.

    check_numbers.py <course_dir>                  # report every quantity stated with different values, with where
    check_numbers.py <course_dir> --from pages     # judge the built pages (default: the approved scripts)
    check_numbers.py <course_dir> --json

WHY THIS EXISTS (2.63.2)
The IGF hand review found 20 ppm on a slide and 25 ppm in a question (M06 check q4) for the same limit, and
the oxygen of fresh air as 20.9 %, 21 % and 20.8 % in different modules. Every module was consistent with
itself and every per-module check passed, so only the whole course read together can see it. It is the
terminology report (check_terms.py) for numbers.

WHAT A QUANTITY IS
A number with its unit (the 2.63.0 reading of a drawing's facts - compile_module.facts_in, imported, not
copied) and the key word before it in the same clause: "oxygen ... 20.9 %" is the quantity (oxygen, %),
"H2S exposure limit 20 ppm" is (h2s, ppm) and (exposure, ppm). Function words, the words that only say "how
much" (limit, level, content, value ...) and "after / within / every" are not key words. A range counts as
one value ("5-10 %"); 20,9 and 20.9 are the same value.

WHAT IT REPORTS
A quantity is listed when two places in the course state it with CLOSE but different values, neither place
stating the other's value: slide s03 says 20 ppm, question q4 says 25 ppm; fresh air 20.9 % here, 21 % there;
a flashpoint of 11 °C and of 12 °C. Close = within 35 % of each other (within 5 degrees for a temperature),
the shape of a value written twice and not the same. Values far apart (oxygen 5 % and 20.9 %) are two
different things sharing a word, the noise a key-word reading cannot tell from drift, and are not listed.
Two limits stated together on one slide and repeated together elsewhere are no difference. A REPORT, never
a build block: a different value can be right (another gas, another standard), so the operator decides which
one the course keeps; the script is changed by content_script.py propose, never by hand, and the module
rebuilt. Exit 0 always, 1 only with --strict.

WHAT IT READS - the same as check_terms.py: the approved scripts (M*.json, FINAL.json), else the built pages.
"""

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL = HERE.parents[1]
# python -I leaves the script's own folder off sys.path
for p in (HERE, SKILL / "compile" / "scripts"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))
import check_terms as ct  # noqa: E402  the same reading of the course
import compile_module as cm  # noqa: E402  facts_in / FACT: a number with its unit

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

STOP = set("""a an the of in on at to for from by with without and or but nor as is are was were be been being has have had do does
did it its this that these those there here then than so not no into onto over under up down out off per via vs
below above under least most more less max min maximum minimum about approx approximately around near nearly
exactly only just also still even at-least up-to
after before within during every each once twice between until while when where which who whom whose what
must may can could should shall will would might need needs needed
set sets setting stays stay stand stands remain remains reads read shows show gives give means mean
us we you your our their his her they he she i me one two three four five six seven eight nine ten other same another
both either neither all any some many much few several""".split())
# the words that only say how much / which kind of value - the key word is the thing measured, not these
GENERIC = set("""limit limits level levels content concentration concentrations value values rate rates amount amounts
figure figures number numbers reading readings alarm alarms point points range ranges threshold thresholds
total average mean typical normal approximately step steps stage stages part parts item items example
time times period periods length long lasts last takes take approx""".split())
WORD = re.compile(r"[^\W\d_][\w\-/]*", re.U)
# a clause ends at a sentence stop, a colon / semicolon / comma / bracket, a line break or a spaced dash
BOUND = re.compile(r"(?:[.!?]\s|\s[-–—]\s|[\n;:,()\[\]])")
LOOK = 70


def key_words(pre):
    """The key words of the clause just before a number, nearest first: its content words (up to 4 words back)."""
    m = None
    for m in BOUND.finditer(pre):
        pass
    if m:
        pre = pre[m.end():]
    out = []
    for w in reversed(WORD.findall(pre)[-4:]):
        w = w.lower().strip("-/")
        if len(w) < 3 or w in STOP or w in GENERIC:
            continue
        if len(w) > 4 and w.endswith("s") and not w.endswith("ss"):
            w = w[:-1]
        out.append(w)
    return out


def key_words_after(post):
    """The word the number qualifies when it comes right after it ("20.9 % oxygen"): the next word, if it is a content word."""
    m = BOUND.search(post)
    if m:
        post = post[:m.start()]
    w = (WORD.findall(post) or [""])[0].lower().strip("-/")
    if len(w) < 3 or w in STOP or w in GENERIC or not post.lstrip()[:1].isalpha():
        return []
    return [w[:-1] if len(w) > 4 and w.endswith("s") and not w.endswith("ss") else w]


def quantities_in(text):
    """[(key word, unit, value as read, (its numbers))] for every number-with-unit in a text."""
    out = []
    for m in cm.FACT.finditer(text or ""):
        facts = cm.facts_in(m.group(0))
        if not facts:
            continue
        unit = facts[0][1][2]
        nums = tuple(float(sign + v) for _, (sign, v, _) in facts[:2])
        value = "-".join(sign + v for _, (sign, v, _) in facts[:2])
        pre = text[max(0, m.start() - LOOK):m.start()]
        for w in key_words(pre) + key_words_after(text[m.end():m.end() + LOOK]):
            out.append((w, unit, value, nums))
    return out


def close(unit, a, b):
    """Two values that could be one quantity written twice (20 and 25 ppm, 20.9 and 21 %, 11 and 12 °C) - not two
    different things (5 % and 20.9 %, 65 °C and -33 °C). A range is only close to a range of the same shape."""
    if a == b or len(a) != len(b):
        return False
    if unit in ("°c", "°f", "k"):
        return all(abs(x - y) <= 5 for x, y in zip(a, b))
    return all(abs(x - y) <= 0.35 * max(abs(x), abs(y)) for x, y in zip(a, b))


def analyse(course, mode="auto"):
    """[{quantity: [words], unit, values: {value: [locations]}}] for every quantity that two places state with close
    but different values, neither place stating the other's. Only the values involved are listed."""
    groups = {}
    nums = {}
    for loc, text in ct.sources(course, mode):
        for w, unit, value, n in quantities_in(text):
            groups.setdefault((w, unit), {}).setdefault(loc, set()).add(value)
            nums[(unit, value)] = n
    found = {}
    for (w, unit), by_loc in groups.items():
        hit = set()
        locs = list(by_loc)
        for i, a in enumerate(locs):
            for b in locs[i + 1:]:
                for va in by_loc[a] - by_loc[b]:
                    for vb in by_loc[b] - by_loc[a]:
                        if close(unit, nums[(unit, va)], nums[(unit, vb)]):
                            hit.update((va, vb))
        if not hit:
            continue
        values = {v: sorted(l for l, vs in by_loc.items() if v in vs) for v in hit}
        # two key words of one phrase ("exposure" and "h2s") that give the same finding are one finding
        sig = (unit, tuple(sorted((v, tuple(l)) for v, l in values.items())))
        found.setdefault(sig, {"quantity": [], "unit": unit, "values": values})["quantity"].append(w)
    rep = list(found.values())
    for e in rep:
        e["quantity"].sort()
    return sorted(rep, key=lambda e: (e["unit"], e["quantity"]))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("course", help="the course folder (it has working_claude/ and modules/)")
    ap.add_argument("--from", dest="mode", choices=("auto", "scripts", "pages", "both"), default="auto")
    ap.add_argument("--strict", action="store_true", help="exit 1 when any quantity differs")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    rep = analyse(a.course, a.mode)
    if a.json:
        print(json.dumps({"report": rep}, ensure_ascii=False, indent=1))
        return 1 if (rep and a.strict) else 0

    print("=" * 72)
    print("check_numbers - one quantity, one value, across the whole course")
    print("=" * 72)
    print()
    for e in rep:
        print("DIFFERS  %s  [%s]" % (" / ".join(e["quantity"]), e["unit"]))
        for v, locs in sorted(e["values"].items(), key=lambda kv: (-len(kv[1]), kv[0])):
            show = ", ".join(locs[:6]) + (" ... +%d more" % (len(locs) - 6) if len(locs) > 6 else "")
            print("   %-10s %3d place(s): %s" % (v, len(locs), show))
        print()
    if not rep:
        print("No quantity is stated with different values.")
    else:
        print("%d quantity(ies) with different values. A report, not a failure: a different value can be right" % len(rep))
        print("(another gas, another standard) - the operator picks the one the course keeps; the script is")
        print("changed by content_script.py propose, never by hand, and the module rebuilt.")
    return 1 if (rep and a.strict) else 0


if __name__ == "__main__":
    sys.exit(main())
