#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Every self-check and module-check question judged against the slides before it - the task-coverage-checker agent's
tool (L36, L71).

    task_cover.py next   <course> --module 1 [--n 12]   the next questions to judge, each set with the slides before it (JSON)
    task_cover.py judge  <course> --module 1 --file <verdicts.json>   the agent's verdicts, each quote checked
    task_cover.py fixes  <course> --module 1 [--apply]  the theory to add as a change list for content_script propose
                                                       (--apply: an unattended build applies it itself, each logged)
    task_cover.py status <course> --module 1

WHY THIS EXISTS
content_script.py's taught check looks for a right answer's key words on the slides before its task. A word can match
while the topic was never taught, and words cannot say whether the trainee could do the task - apply the rule, work out
the value, make the decision - from what the slides showed. So an agent reads each question and only the slides before
it, and says covered, partly or not covered. The mechanical part is here - which slides come before which question,
refusing a quote no slide shows, turning "add this line to slide X" into a change list - so the agent's rules stay short.

WHAT A VERDICT IS TIED TO
The question as written and every slide before it (its words, its picture, its notes), as one hash. A covered verdict is
also tied to the question and the slides it cites, as a second hash, and holds while they are unchanged and still before
the question: a change to another slide does not take away what the cited slides teach (the factory trial: one corrected
line voided all 14 verdicts of a module, four check rounds a module). A changed question, a changed cited slide, or - for
partly and not covered - any changed slide before it is judged again. The final assessment covers the whole course and
is not judged here.

The verdicts are in working_claude/task_cover/MNN.json. Once a module has that file, content_script.py's check refuses
the approval while a question is not judged, or is judged partly or not covered. Exit 0, 1 questions left or refused
verdicts, 2 bad input.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import content_script as cs  # noqa: E402
import workspace  # noqa: E402

VERDICTS = ("covered", "partly", "not_covered")
TAUGHT_KINDS = ("slide", "activity")          # what the room is shown and does before a task opens
SHOWN = ("title", "text", "points", "ask", "reveal", "claim", "choices", "why")
JUDGED_SETS = ("self-check", "module-check")
QUESTION_SKIP = ("id", "kind", "set", "sub_ilo", "picture", "group")


def store_path(course, module):
    return workspace.claude_path(course, "task_cover", "%s.json" % cs.mid(module))


def load_store(course, module):
    try:
        return json.load(io.open(store_path(course, module), encoding="utf-8"))
    except (OSError, ValueError):
        return None


def save_store(course, module, st):
    p = store_path(course, module)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    io.open(p, "w", encoding="utf-8", newline="\n").write(json.dumps(st, ensure_ascii=False, indent=1))
    return p


def shows(s):
    """what a slide puts in front of the trainee: its title and lines (on a slide of short points, the points - its lines
    are the instructor's), the room's question and answer, a scenario's choices and why, and what its picture shows"""
    body = s.get("points") if s.get("points") else s.get("text", "")
    rest = [cs.as_text(s.get(f)) for f in SHOWN[3:] if s.get(f) not in (None, "")]
    pic = s.get("visual") or (s.get("picture") or {}).get("shows") or ""
    return {"id": s["id"], "title": s.get("title", ""), "shows": "\n".join(x for x in [cs.as_text(body)] + rest if x),
            "picture": cs.as_text(pic), "notes": cs.as_text(s.get("notes"))}


def outcomes(course, module):
    """{Sub-ILO id: its words, in English} for the module from the ILO map - what each question's outcome asks"""
    import ilo_map
    m = ilo_map.read(course)
    return {str(r["sub_ilo_id"]): r.get("sub_ilo_en") or r.get("sub_ilo") or "" for r in ilo_map.module_rows(m, module)
            if r.get("sub_ilo_id")} if m else {}


def question_view(q, outs=None):
    """the question as the agent judges it: what the trainee reads and answers, the right answer and its feedback, and
    the words of the outcome it checks - every part it names and the method of what it has the trainee do are taught"""
    out = {"id": q["id"]}
    out.update({k: v for k, v in q.items() if k not in QUESTION_SKIP and v not in (None, "")})
    _, right, _ = cs.read_answer(q)
    if right:
        out["right"] = right
    said = (outs or {}).get(str(q.get("sub_ilo") or ""))
    if said:
        out["outcome"] = "%s %s" % (q["sub_ilo"], said)
    return out


def units(script):
    """[(set id, set kind, [slide views before it], [questions])] in teaching order - the slides before the task slide that
    opens the set (or before its first question, if no task slide opens it)"""
    if str(script.get("module")).lower() == "final":
        return []
    _, sets, set_of = cs.plan_of(script)
    seen, before, out = [], {}, []
    for s in script.get("screens", []):
        k = s.get("kind")
        if k in TAUGHT_KINDS:
            seen.append(shows(s))
        elif k == "task-slide" and s.get("opens") in set_of and s.get("opens") not in before:
            before[s["opens"]] = list(seen)
        elif k in cs.TASKS:
            st = s.get("set") or {"self-check": "SC", "module-check": "MC", "final": "FA"}[k]
            before.setdefault(st, list(seen))
    for st in sets:
        if st["kind"] in JUDGED_SETS:
            out.append((st["id"], st["kind"], before.get(st["id"], []), st["questions"]))
    return out


def stamp(q, slides):
    """the hash a verdict is tied to: the question as written and every slide before it"""
    return hashlib.sha1(json.dumps([q, slides], ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()[:12]


def current(script):
    """{question id: (stamp, set id, [slide views before it], question)}"""
    return {q["id"]: (stamp(q, slides), sid, slides, q) for sid, _, slides, qs in units(script) for q in qs}


def holds(row, now_q):
    """a verdict still stands for the question as it is now: its whole stamp is the same, or it is covered and the question
    and the slides it cites are unchanged and still before it"""
    h, _, slides, q = now_q
    if row.get("hash") == h:
        return True
    if row.get("verdict") != "covered" or not row.get("taught"):
        return False
    cited = [s for s in slides if s["id"] in (row.get("slides") or [])]
    return len(cited) == len(row.get("slides") or []) and stamp(q, cited) == row["taught"]


def norm(text):
    return re.sub(r"\s+", "", re.sub(r"[^\w%.,-]+", " ", (text or "").lower()))


def quote_on(quote, slides, notes=False):
    """the quote word for word in what the slides show (their notes, with notes=True) - spaces, marks and case aside"""
    q = norm(quote)
    return len(q) >= 8 and any(q in norm(s["notes"] if notes else "%s\n%s\n%s" % (s["title"], s["shows"], s["picture"]))
                               for s in slides)


def judge(course, module, verdicts):
    """-> (recorded, [problems]). covered cites the slides before the question and quotes what they show, word for word;
    partly and not_covered say what is missing and how to mend it - a line added to a slide before the task, or the
    question changed (for the person)"""
    script = cs.load(cs.paths(course, module)["script"])
    now = current(script)
    st = load_store(course, module) or {"module": str(module), "questions": {}}
    probs, done = [], 0
    for v in verdicts if isinstance(verdicts, list) else []:
        qid = str((v or {}).get("id") or "")
        if qid not in now:
            probs.append("%s: no such self-check or module-check question (run next)" % qid)
            continue
        h, _, slides, _ = now[qid]
        verdict = v.get("verdict")
        if verdict not in VERDICTS:
            probs.append("%s: verdict is one of %s" % (qid, ", ".join(VERDICTS)))
            continue
        ids = [s["id"] for s in slides]
        cited = v.get("slides") or []
        cited = [cited] if isinstance(cited, str) else [str(x) for x in cited]
        quotes = v.get("quote") or []
        quotes = [quotes] if isinstance(quotes, str) else [str(x) for x in quotes]
        missing = (v.get("missing") or "").strip()
        add = v.get("add") if isinstance(v.get("add"), dict) else None
        change = (v.get("question") or "").strip()
        row = {"hash": h, "verdict": verdict, "by": "task-coverage-checker"}
        if verdict == "covered":
            if not cited or any(x not in ids for x in cited):
                probs.append("%s: covered cites the slides before the question that teach it - one of %s" % (qid, ", ".join(ids) or "none"))
                continue
            on = [s for s in slides if s["id"] in cited]
            bad = [x for x in quotes if not quote_on(x, on)]
            if not quotes or bad:
                in_notes = [x for x in bad if quote_on(x, on, notes=True)]
                probs.append("%s: %s" % (qid, "only the instructor's notes say \"%s\" - a question asks what the slides show: partly, "
                                         "add it to the slide" % in_notes[0][:60] if in_notes else
                                         "the quote is not on the cited slides word for word - copy it from their words or picture"))
                continue
            row.update(slides=cited, quote=quotes, taught=stamp(now[qid][3], on))
        else:
            if not missing:
                probs.append("%s: %s needs \"missing\" - the fact or step the trainee was not given" % (qid, verdict))
                continue
            if not add and not change:
                probs.append("%s: %s needs its mend - \"add\": {\"slide\", \"line\"} on a slide before the task, or \"question\": "
                             "how to change the question" % (qid, verdict))
                continue
            if add:
                sid, line = str(add.get("slide") or ""), (add.get("line") or "").strip()
                target = cs.screen_of(script, sid)
                if sid not in ids or not line:
                    probs.append("%s: add goes to a slide before the task - one of %s - with its line" % (qid, ", ".join(ids) or "none"))
                    continue
                if target.get("choices") or target.get("claim"):
                    probs.append("%s: %s is a scenario or a claim to vote on - add the line to a plain theory slide" % (qid, sid))
                    continue
                if target.get("points") and cs.wc(line) > cs.POINT_WORDS:
                    probs.append("%s: %s is a slide of short points - the line to add is a point, %d words or fewer"
                                 % (qid, sid, cs.POINT_WORDS))
                    continue
                row["add"] = {"slide": sid, "line": line}
            if change:
                row["question"] = change
            row["missing"] = missing
        st["questions"][qid] = row
        done += 1
    save_store(course, module, st)
    return done, probs


def fixes(course, module):
    """the change list for content_script.py propose: each line to add goes at the end of its slide (its points on a slide
    of short points). A question to change is listed for the person - a question is never changed here"""
    script = cs.load(cs.paths(course, module)["script"])
    st = load_store(course, module) or {"questions": {}}
    now = current(script)
    adds, asks = {}, []
    for qid, row in st["questions"].items():
        if qid not in now or not holds(row, now[qid]) or row.get("verdict") == "covered":
            continue
        if row.get("add"):
            lines = adds.setdefault(row["add"]["slide"], [])
            if row["add"]["line"] not in lines:
                lines.append(row["add"]["line"])
        if row.get("question"):
            asks.append((qid, row["missing"], row["question"]))
    changes = []
    for sid, lines in adds.items():
        s = cs.screen_of(script, sid)
        field = "points" if s.get("points") else "text"
        old = s.get(field)
        new = (list(old) + lines) if isinstance(old, list) else "\n".join(x for x in [cs.as_text(old)] + lines if x)
        changes.append({"screen": sid, "field": field, "new": new})
    return changes, asks


def status(course, module, script=None):
    """{"started": the module has verdicts, "questions", "judged", "unjudged": [ids], "open": [(id, verdict, missing)],
    "rows": {id: verdict row, for the questions as they are now}, "lost": {id: the quotes a covered verdict relied on that
    the slides before it no longer show - a line cut or changed since it was judged}}"""
    script = script or cs.load(cs.paths(course, module)["script"])
    st = load_store(course, module)
    have = (st or {}).get("questions") or {}
    out = {"started": st is not None, "questions": 0, "judged": 0, "unjudged": [], "open": [], "rows": {}, "lost": {}}
    for qid, now_q in current(script).items():
        slides = now_q[2]
        out["questions"] += 1
        row = have.get(qid)
        if not row or not holds(row, now_q):
            out["unjudged"].append(qid)
            gone = [x for x in (row or {}).get("quote") or [] if row.get("verdict") == "covered" and not quote_on(x, slides)]
            if gone:
                out["lost"][qid] = gone
            continue
        out["judged"] += 1
        out["rows"][qid] = row
        if row["verdict"] != "covered":
            out["open"].append((qid, row["verdict"], row.get("missing", "")))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("cmd", choices=("next", "judge", "fixes", "status"))
    ap.add_argument("course")
    ap.add_argument("--module", required=True)
    ap.add_argument("--n", type=int, default=12)
    ap.add_argument("--file")
    ap.add_argument("--apply", action="store_true", help="fixes: apply the change list - an unattended build only")
    a = ap.parse_args(argv)
    course = workspace.work_folder(a.course, create=False)
    if not os.path.isfile(cs.paths(course, a.module)["script"]):
        print("Stopped - module %s has no content script yet" % a.module)
        return 2
    if a.cmd == "next":
        script = cs.load(cs.paths(course, a.module)["script"])
        if load_store(course, a.module) is None:
            save_store(course, a.module, {"module": str(a.module), "questions": {}})   # from now on an unjudged question holds the approval
        left = set(status(course, a.module, script)["unjudged"])
        out, n, outs = [], 0, outcomes(course, a.module)
        for sid, kind, slides, qs in units(script):
            todo = [question_view(q, outs) for q in qs if q["id"] in left][:max(0, a.n - n)]
            if todo:
                out.append({"set": sid, "kind": kind, "slides_before": slides, "questions": todo})
                n += len(todo)
        print(json.dumps(out, ensure_ascii=False, indent=1) if out else "[] - every question is judged: run fixes")
        return 0
    if a.cmd == "judge":
        try:
            verdicts = json.load(io.open(a.file, encoding="utf-8"))
        except (OSError, ValueError, TypeError) as err:
            print("Stopped - --file is a JSON list of {id, verdict, slides, quote} (partly, not_covered: {id, verdict, missing, "
                  "add: {slide, line} and/or question}): %s" % err)
            return 2
        done, probs = judge(course, a.module, verdicts)
        print("Recorded %d verdict(s).%s" % (done, "".join("\n  refused: " + p for p in probs)))
        return 1 if probs else 0
    if a.cmd == "fixes":
        changes, asks = fixes(course, a.module)
        p = os.path.join(os.path.dirname(store_path(course, a.module)), "%s.changes.json" % cs.mid(a.module))
        os.makedirs(os.path.dirname(p), exist_ok=True)
        io.open(p, "w", encoding="utf-8", newline="\n").write(json.dumps(changes, ensure_ascii=False, indent=1))
        if a.apply and changes:
            # an unattended build has nobody to say yes: the missing theory goes in, each change logged in FEEDBACK_LOG.md
            # for the expert to see in the editor; the fact-checker proves the new lines like any other
            if os.environ.get("NOVIKONTAS_AUTO_BUILD") != "1":
                print("Stopped - --apply is for an unattended build (NOVIKONTAS_AUTO_BUILD=1); attended, the operator sees the "
                      "changes first: content_script.py propose")
                return 2
            if os.path.isfile(cs.paths(course, a.module)["pending"]):
                print("Stopped - other changes wait to be applied or discarded first")
                return 1
            code = cs.cmd_propose(course, a.module, p, "task-coverage-checker")
            return code or cs.cmd_apply(course, a.module, True, "task-coverage-checker, unattended - theory the task needs")
        print("%d slide(s) to extend with theory - shown to the operator first:\n    python %s propose %s --module %s --changes \"%s\" "
              "--proposed-by \"task-coverage-checker\"" % (len(changes), os.path.join(HERE, "content_script.py"), a.course, a.module, p))
        for qid, missing, change in asks:
            print("  question %s - for the person, never changed here: %s -> %s" % (qid, missing, change))
        return 0
    s = status(course, a.module)
    print("Module %s: %d question(s), %d judged, %d not judged yet (or changed since), %d not covered by the slides before them."
          % (a.module, s["questions"], s["judged"], len(s["unjudged"]), len(s["open"])))
    for qid, v, missing in s["open"][:20]:
        print("  %s  %-11s %s" % (qid, v, missing[:110]))
    return 0 if not s["unjudged"] and not s["open"] else 1


if __name__ == "__main__":
    sys.exit(main())
