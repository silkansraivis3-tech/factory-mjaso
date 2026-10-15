#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Theory taught as activity - what is waiting for the operator, and recording what they kept or struck (L49, step 3).

    active_plan.py list   --course <course>
    active_plan.py decide --course <course> --keep A1.1,A1.2 --strike A2.1 --said "<the operator's words>"

WHY THIS EXISTS (owner, 2026-10-15)
"The factory proposes, per sub-topic, how theory can be taught as activity, and the operator ticks or
strikes each on the Stage 2 page." The proposals are lines in working_claude/architecture.json
(modules[].active_learning, status "proposed"), written by Claude from knowledge/active-learning.json
(active/GUIDE.md). The operator presses Keep or Strike on the architecture page and pastes the line it
copies - or says it in their own words. This records exactly that, and nothing else:

  list    every proposal still waiting, every sub-topic with no proposal, and the class split now and
          if every proposal is kept;
  decide  sets each named proposal to kept ("approved") or "struck", with the date and the operator's
          words; logs each in FEEDBACK_LOG.md (L32); re-renders the architecture page. A struck line
          stays in the file - never deleted. An id it does not know stops it before anything changes.
          A decision may be changed by deciding again.

Standard library only.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys
from datetime import date

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import make_architecture_page as ap  # noqa: E402
import workspace  # noqa: E402


def ids(text):
    return [x.strip() for x in (text or "").replace(";", ",").split(",") if x.strip()]


def files(course):
    return workspace.claude_path(course, "architecture.json"), workspace.claude_path(course, "programme.json")


def load(course):
    a, p = files(course)
    arch = json.load(io.open(a, encoding="utf-8"))
    prog = json.load(io.open(p, encoding="utf-8")) if os.path.isfile(p) else {}
    return arch, prog


def lines_of(arch):
    """{id: (module number, the line)} for every theory-as-activity line that has an id."""
    out = {}
    for m in arch.get("modules", []):
        for x in m.get("active_learning") or []:
            if isinstance(x, dict) and x.get("id"):
                out[str(x["id"])] = (m.get("module"), x)
    return out


def cmd_list(course):
    arch, prog = load(course)
    a = ap.analyse(prog, arch)
    P = ap.Page((arch.get("course") or {}).get("operator_language", "en"))
    tm = [m for m in a["modules"] if not m["assessment"] and m["arch"] and m["alloc"]]
    tot = sum(m["alloc"] for m in tm) or 1
    print("Waiting for the operator: %d proposal(s)." % len(a["waiting"]))
    for n, x in a["waiting"]:
        print("  %s  (module %s, sub-topic %s, %s min)  %s" % (x.get("id"), n, x.get("subtopic", "—"), x.get("minutes", "—"),
                                                          x.get("does") or x.get("where", "")))
    gaps = [(k, kw) for k, kw in a["split"] if k in ("a_no_proposal", "a_no_proposal_mod")]
    if gaps:
        print("\nNo proposal yet:")
        for k, kw in gaps:
            print("  - " + P.t(k, **kw))
    print("\nPlain theory now %.0f %%; if every proposal is kept %.0f %% (the aim: 20 %%)." % (
        100.0 * sum(m["plain"] for m in tm) / tot, 100.0 * sum(m["plain_all"] for m in tm) / tot))
    return 0


def append_feedback(course, rows):
    fb = workspace.claude_path(course, "FEEDBACK_LOG.md")
    if not os.path.isfile(fb):
        return False
    text = io.open(fb, encoding="utf-8").read()
    nums = [int(l.split("|")[1]) for l in text.splitlines() if l.strip().startswith("|") and l.split("|")[1].strip().isdigit()]
    n = max(nums or [0])
    out = []
    for module, xid, said, what in rows:
        n += 1
        out.append("| %d | %s | 2 · M%02d · %s | %s | %s | no |" % (n, date.today().isoformat(), int(module), xid,
                                                                  said.replace("|", "/"), what.replace("|", "/")))
    with io.open(fb, "a", encoding="utf-8", newline="\n") as f:
        f.write(("\n" if text and not text.endswith("\n") else "") + "\n".join(out) + "\n")
    return True


def cmd_decide(course, keep, strike, said, by=None):
    keep, strike = ids(keep), ids(strike)
    if not keep and not strike:
        print("Stopped - nothing to record: name the proposals to keep (--keep) and to strike (--strike).")
        return 2
    both = set(keep) & set(strike)
    if both:
        print("Stopped - %s is both kept and struck. Ask the operator which." % ", ".join(sorted(both)))
        return 2
    if not (said or "").strip():
        print("Stopped - give the operator's own words (--said), so the log says what they decided.")
        return 2
    arch, _ = load(course)
    known = lines_of(arch)
    unknown = [x for x in keep + strike if x not in known]
    if unknown:
        print("Stopped - nothing changed. These are not proposals in the architecture: %s\n  Known: %s"
              % (", ".join(unknown), ", ".join(sorted(known)) or "none"))
        return 2
    rows, today = [], date.today().isoformat()
    for xid, st, what in [(x, "approved", "kept") for x in keep] + [(x, "struck", "struck") for x in strike]:
        module, line = known[xid]
        before = ap.status_of(line)
        line.update(status=st, decided_on=today, decided_said=said.strip())
        if by:
            line["decided_by"] = by
        note = "%s - %s" % (what, line.get("does") or line.get("where") or "")
        if before != "proposed":
            note += " (was %s)" % ("kept" if before == "approved" else before)
        rows.append((module, xid, said.strip(), note))
        print("  %s: %s%s" % (xid, what, (" (was %s)" % ("kept" if before == "approved" else before)) if before != "proposed" else ""))
    a_path, _ = files(course)
    with io.open(a_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(arch, f, ensure_ascii=False, indent=1)
        f.write("\n")
    logged = append_feedback(course, rows)
    print("Recorded %d decision(s)%s." % (len(rows), " and logged them in FEEDBACK_LOG.md" if logged else
                                          " (there is no FEEDBACK_LOG.md to log them in)"))
    ap.main(["--course", course])
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("list", "decide"):
        s = sub.add_parser(name)
        s.add_argument("--course", required=True)
        if name == "decide":
            s.add_argument("--keep", default="")
            s.add_argument("--strike", default="")
            s.add_argument("--said", default="", help="the operator's own words")
            s.add_argument("--by", default=None)
    x = p.parse_args(argv)
    course = workspace.work_folder(x.course)
    if not os.path.isfile(files(course)[0]):
        print("Stopped - there is no architecture yet (working_claude/architecture.json).")
        return 2
    if x.cmd == "list":
        return cmd_list(course)
    return cmd_decide(course, x.keep, x.strike, x.said, x.by)


if __name__ == "__main__":
    sys.exit(main())
