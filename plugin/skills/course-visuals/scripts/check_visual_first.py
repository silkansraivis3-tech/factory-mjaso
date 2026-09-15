#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""L23 - does each topic screen LEAD with the thing that shows it?

    check_visual_first.py <deck-or-dir> [--strict] [--json]

WHY THIS EXISTS
Modules kept leaving this factory as text with pictures added afterwards, which is
the order in which a picture becomes decoration. The owner's instruction was the
other order: for a topic screen find the visual FIRST - the source files and the
knowledge base, then the internet for a real photograph, and only then generate.

So this script asks two questions per screen, and only two:

  1 Does the screen have a figure at all?
  2 Does it come BEFORE the body text in the reading order?

(2) is the half that makes this a law rather than a preference. A screen that
explains a cargo pump in three paragraphs and then shows one has a picture; it
does not lead with one, and the trainee has already stopped reading.

WHAT IT DELIBERATELY DOES NOT DO
It cannot tell you whether a figure teaches - `review/GUIDE.md` asks that, and a
clean run here is not a pass. It also does not want you to fix a finding by
pasting in an icon: `knowledge/visual-first-rules.json` lists what does not count,
`check_visuals.py` rejects decorative vocabulary, and a screen that honestly needs
no figure declares that instead, with `data-novisual="<reason>"`.

`knowledge/visual-first-rules.json` is the authority. Edit that file, not this one.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
RULES = os.path.join(SKILL, "knowledge", "visual-first-rules.json")

FAIL, WARN, NOTE = "FAIL", "WARN", "NOTE"

COMMENT = re.compile(r"<!--.*?-->", re.S)
SCRIPT_STYLE = re.compile(r"<(script|style)[^>]*>.*?</\1>", re.S | re.I)
SCREEN = re.compile(
    r'<section\b[^>]*class="[^"]*\b(?:slide|screen)\b[^"]*"[^>]*>(.*?)</section>',
    re.S | re.I)
SCREEN_OPEN = re.compile(
    r'<section\b[^>]*class="[^"]*\b(?:slide|screen)\b[^"]*"[^>]*>', re.S | re.I)

# What counts as a figure. Deliberately generous about the CONTAINER and strict
# about the content: an <img>, an inline <svg>, a <canvas>, a <video>, a mounted
# interactive figure, or a <figure> element that holds one of those.
FIGURE = re.compile(
    r"<(?:img|svg|canvas|video|picture)\b"
    r"|<figure\b"
    r'|\bdata-fig(?:ure)?=|\bclass="[^"]*\bgb-?fig\b',
    re.I)

# Body text: a paragraph, a list, a card deck. Headings do not count - a heading
# above a figure is a caption for it, not the text the figure was buried under.
BODY = re.compile(r"<(?:p|ul|ol|table|blockquote)\b", re.I)

ATTR = re.compile(r'(\w[\w-]*)="([^"]*)"')
TAGS = re.compile(r"<[^>]+>")


class Finding:
    def __init__(self, level, path, screen, title, detail, fix=""):
        self.level, self.path, self.screen = level, path, screen
        self.title, self.detail, self.fix = title, detail, fix

    def __str__(self):
        s = "  [%s] %s  screen %s%s\n        %s" % (
            self.level, self.path, self.screen,
            (" - " + self.title) if self.title else "", self.detail)
        if self.fix:
            s += "\n        " + self.fix
        return s

    def as_dict(self):
        return {"level": self.level, "path": self.path, "screen": self.screen,
                "title": self.title, "detail": self.detail, "fix": self.fix}


def load_rules(path):
    with open(path, encoding="utf-8-sig") as fh:
        return json.load(fh)


def attrs_of(open_tag):
    return {k.lower(): v for k, v in ATTR.findall(open_tag)}


def heading_of(body):
    m = re.search(r"<h[1-4][^>]*>(.*?)</h[1-4]>", body, re.S | re.I)
    if not m:
        return ""
    return re.sub(r"\s+", " ", TAGS.sub(" ", m.group(1))).strip()


def is_topic(open_tag, body, rules):
    """A screen is a TOPIC screen unless it is navigation, an activity or a summary."""
    a = attrs_of(open_tag)
    hay = " ".join([a.get("data-title", ""), a.get("class", ""),
                    a.get("data-kind", ""), heading_of(body)]).lower()
    for word in rules["topic_screen"]["not_a_topic_screen"]:
        if re.search(r"\b" + re.escape(word.lower()) + r"\b", hay):
            return False, word
    return True, ""


def words_in(body):
    return len(re.sub(r"\s+", " ", TAGS.sub(" ", body)).split())


def course_facing(rel, rules):
    """A retrofit keeps the original module beside the new one. Judging the original
    doubles every count and sends the operator back to work already replaced."""
    low = rel.replace("\\", "/").lower()
    return not any(x.lower() in low
                   for x in rules.get("not_course_facing", {}).get("paths", []))


def scan(path, rel, rules, out):
    raw = open(path, encoding="utf-8", errors="replace").read()
    clean = SCRIPT_STYLE.sub(" ", COMMENT.sub(" ", raw))

    opens = [m.group(0) for m in SCREEN_OPEN.finditer(clean)]
    bodies = [m.group(1) for m in SCREEN.finditer(clean)]
    if not bodies:
        return 0
    n_topic = 0

    for i, body in enumerate(bodies):
        open_tag = opens[i] if i < len(opens) else ""
        num = str(i + 1)
        title = attrs_of(open_tag).get("data-title", "") or heading_of(body)

        topic, why = is_topic(open_tag, body, rules)
        if not topic:
            continue
        n_topic += 1

        declared = attrs_of(open_tag).get("data-novisual", "")
        fig = FIGURE.search(body)
        first_body = BODY.search(body)

        if declared:
            allowed = [r["key"] for r in rules["declared_exemptions"]["reasons"]]
            if declared not in allowed:
                out.append(Finding(
                    WARN, rel, num, title,
                    'data-novisual="%s" is not one of the declared reasons.' % declared,
                    "Use one of: " + ", ".join(allowed)))
            elif fig:
                out.append(Finding(
                    NOTE, rel, num, title,
                    'declared data-novisual="%s" but the screen does carry a figure.'
                    % declared,
                    "Drop the attribute, or say why the figure is not the lead."))
            continue

        if not fig:
            out.append(Finding(
                FAIL, rel, num, title,
                "a topic screen with %d words and no figure." % words_in(body),
                "Search the source files and the knowledge base, then the internet for a "
                "real photograph, then author or generate - in that order. If nothing "
                "honestly represents it, declare it: data-novisual=\"no_honest_representation\"."))
            continue

        if first_body and first_body.start() < fig.start():
            out.append(Finding(
                WARN, rel, num, title,
                "the figure comes after the body text - the screen has a picture but "
                "does not lead with one.",
                "Move the figure above the prose. On a portrait tablet 'beside' only "
                "counts if it is in the first screenful."))

    return n_topic


def walk(target):
    if os.path.isfile(target):
        yield target, os.path.basename(target)
        return
    for dp, dn, fn in os.walk(target):
        dn[:] = [d for d in dn if d not in ("__pycache__", ".git", "node_modules")]
        for f in fn:
            if os.path.splitext(f)[1].lower() in (".html", ".htm"):
                p = os.path.join(dp, f)
                yield p, os.path.relpath(p, target).replace("\\", "/")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("target", help="a module deck, or a folder of them")
    ap.add_argument("--rules", default=RULES)
    ap.add_argument("--strict", action="store_true", help="exit 1 on any FAIL")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    if not os.path.exists(a.target):
        sys.stderr.write("no such path: %s\n" % a.target)
        return 2
    rules = load_rules(a.rules)

    out: list[Finding] = []
    topics = 0
    skipped = 0
    for path, rel in walk(a.target):
        if not course_facing(rel, rules):
            skipped += 1
            continue
        topics += scan(path, rel, rules, out)

    if a.json:
        print(json.dumps({"topic_screens": topics, "skipped_files": skipped,
                          "findings": [f.as_dict() for f in out]},
                         indent=1, ensure_ascii=False))
        return 1 if (a.strict and any(f.level == FAIL for f in out)) else 0

    print("=" * 72)
    print("check_visual_first - does a topic screen lead with the thing that shows it?")
    print("=" * 72)
    print("%d topic screen(s) examined%s"
          % (topics, (", %d file(s) skipped as not course-facing" % skipped) if skipped else ""))

    fails = [f for f in out if f.level == FAIL]
    warns = [f for f in out if f.level == WARN]
    notes = [f for f in out if f.level == NOTE]
    for group, name in ((fails, "NO FIGURE AT ALL"), (warns, "FIGURE, BUT NOT LEADING"),
                        (notes, "NOTES")):
        if group:
            print("\n%s (%d):" % (name, len(group)))
            for f in group:
                print(str(f))

    print()
    if not out:
        print("Every topic screen leads with a figure, or says in writing why it does not.")
    else:
        print("%d without a figure, %d where the figure is not the lead, %d note(s)."
              % (len(fails), len(warns), len(notes)))
        print("\nDo not close a finding by pasting in an icon. The ladder is: source files "
              "and\nknowledge base, then the internet for a real photograph, then author or "
              "generate.\nA screen that honestly needs no figure declares it.")
    return 1 if (a.strict and fails) else 0


if __name__ == "__main__":
    sys.exit(main())
