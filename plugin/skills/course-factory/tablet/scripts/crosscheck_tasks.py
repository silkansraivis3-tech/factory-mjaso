#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Deck <-> instructor run script <-> tablet manifest must agree on every task.

The failure this prevents is the worst one in a classroom: the instructor says
"open T3" and the tablet has no T3, or has it under another name. Three
artefacts have to say the same thing, and nothing else compares them.

    the deck          data-activity on the screen that announces the task
    the run script    the step telling the instructor which screen, which code
    the tablet        the manifest's code, the trainee-facing title, and a page
                      that actually exists

Found on GAS BASIC: a launch screen with no `data-activity`, so the deck
announced a task the generated step-by-step never mentioned.

Usage
-----
    crosscheck_tasks.py --deck M1=path/to/module1.html --deck M2=... \\
                        --manifest gb_tasks.js --run it_run.js \\
                        --tablet-root app/src/main/assets/training_terminal

    crosscheck_tasks.py --decks-json decks.json --manifest ... --run ... --tablet-root ...
        decks.json: {"1": "Module_01/presentation/index.html", ...}

Exit codes: 0 they agree · 1 a disagreement · 2 bad input
"""
import argparse
import json
import pathlib
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def die(m):
    print("INPUT ERROR: %s" % m)
    sys.exit(2)


def js_block(text, marker, opener):
    """parse the JSON-ish literal after `marker`. `opener` is '[' or '{' -
    IT_RUN is an object keyed m1..mN while GB_TASKS is an array, and searching
    for the first '[' finds a nested array inside the object."""
    i = text.find(marker)
    if i < 0:
        die("could not find %r" % marker)
    j = text.find(opener, i)
    depth, k = 0, j
    while k < len(text):
        if text[k] in "[{":
            depth += 1
        elif text[k] in "]}":
            depth -= 1
            if depth == 0:
                return json.loads(text[j:k + 1])
        k += 1
    die("unterminated literal after %r" % marker)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--deck", action="append", default=[],
                    help="N=path, repeatable")
    ap.add_argument("--decks-json")
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--run", required=True)
    ap.add_argument("--tablet-root", required=True)
    ap.add_argument("--manifest-var", default="GB_TASKS")
    ap.add_argument("--run-var", default="IT_RUN")
    a = ap.parse_args()

    decks = {}
    if a.decks_json:
        for k, v in json.loads(pathlib.Path(a.decks_json).read_text(encoding="utf-8")).items():
            decks[int(k)] = pathlib.Path(v)
    for d in a.deck:
        if "=" not in d:
            die("--deck wants N=path, got %r" % d)
        k, v = d.split("=", 1)
        decks[int(re.sub(r"\D", "", k))] = pathlib.Path(v)
    if not decks:
        die("give --deck or --decks-json")

    troot = pathlib.Path(a.tablet_root)
    tasks = js_block(pathlib.Path(a.manifest).read_text(encoding="utf-8", errors="replace"),
                     "var " + a.manifest_var, "[")
    run = js_block(pathlib.Path(a.run).read_text(encoding="utf-8", errors="replace"),
                   "var " + a.run_var, "{")

    # the manifest, keyed module -> bare code -> entry
    MAN = {}
    for mod in tasks:
        n = int(mod["n"])
        MAN[n] = {}
        for t in mod.get("tasks", []):
            code = re.split(r"[·|]", t["code"])[0].strip()
            MAN[n][code] = t

    problems = []
    print("=" * 100)
    print("%-5s %-12s %-9s %-9s %s" % ("mod", "code", "deck", "run", "tablet"))
    print("=" * 100)

    for n in sorted(decks):
        p = decks[n]
        if not p.exists():
            problems.append("M%d: deck not found at %s" % (n, p))
            print("\nM%d   DECK MISSING: %s" % (n, p))
            continue
        s = p.read_text(encoding="utf-8", errors="replace")

        deck = []
        for i, m in enumerate(re.finditer(r'<section class="slide[^>]*>', s), 1):
            act = (re.search(r'data-activity="([^"]*)"', m.group(0)) or ["", ""])[1].strip()
            if act:
                deck.append((i, act))

        mod = run.get("m%d" % n, {})
        rsteps = [(st.get("from"), st.get("code")) for st in mod.get("steps", [])
                  if st.get("kind") in ("task", "activity", "group") and st.get("code")]
        rmap = dict((c, i) for i, c in rsteps)
        dmap = dict((c, i) for i, c in deck)

        print("\nM%d   deck announces %d, run announces %d" % (n, len(deck), len(rsteps)))
        for i, code in deck:
            rs = rmap.get(code)
            state = []
            if rs is None:
                state.append("NOT IN RUN SCRIPT")
                problems.append("M%d %s: deck screen %d announces it, the run script never does"
                                % (n, code, i))
            elif rs != i:
                state.append("run says screen %d" % rs)
                problems.append("M%d %s: deck screen %d vs run script screen %d" % (n, code, i, rs))
            man = MAN.get(n, {}).get(code)
            if man is None:
                state.append("no tablet card (a practical or drill - by design)")
            else:
                pg = troot / man.get("path", "").split("#")[0]
                if not pg.exists():
                    state.append("PAGE MISSING: %s" % man.get("path"))
                    problems.append("M%d %s: manifest points at a page that does not exist (%s)"
                                    % (n, code, man.get("path")))
                else:
                    state.append("ok: %s" % (man.get("title", "")[:40]))
            print("      %-12s s%-8d %-9s %s"
                  % (code, i, ("s%d" % rs) if rs else "-", "  ".join(state)))

        for i, code in rsteps:
            if code not in dmap:
                print("      %-12s %-9s s%-8d RUN ONLY - no deck screen carries it"
                      % (code, "-", i))
                problems.append("M%d %s: the run script announces it on screen %d but no deck "
                                "screen carries data-activity for it" % (n, code, i))

    # manifest entries no deck announces - reference cards and checks are fine
    print()
    print("tablet cards no deck screen announces:")
    for n in sorted(MAN):
        if n not in decks or not decks[n].exists():
            continue
        announced = set(re.findall(r'data-activity="([^"]*)"',
                                   decks[n].read_text(encoding="utf-8", errors="replace")))
        for code, t in MAN[n].items():
            if code not in announced:
                print("   M%-3d %-14s %-44s %s"
                      % (n, code, t.get("title", "")[:44], t.get("kind", "")))
    print("   (reference cards and module checks legitimately have no launch screen)")

    print("\n" + "=" * 100)
    if problems:
        print("%d PROBLEM(S)" % len(problems))
        for x in problems:
            print("   - %s" % x)
        sys.exit(1)
    print("deck, instructor run script and tablet manifest agree on every task")
    sys.exit(0)


if __name__ == "__main__":
    main()
