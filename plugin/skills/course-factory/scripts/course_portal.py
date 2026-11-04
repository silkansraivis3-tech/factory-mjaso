#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""The experts review a course in preparation in the training app's editor - the factory's side. Staging only.

    course_portal.py name   --title "<name>"                  is the name free in the training app? (intake question 9)
    course_portal.py create --course <course> [--title "<name>"]   the course in preparation, under intake's course_name
    course_portal.py push   --course <course> --pedagogy      the experts' pedagogy documents into the editor
    course_portal.py pull   --course <course>                 the experts' answers and their Ready back into the files
    course_portal.py status --course <course>                 the stage, how much is answered, who said Ready
    course_portal.py remove --course <course> --yes           a course in preparation that was never built

WHY THIS EXISTS
The experts used to get the pedagogy documents and the content scripts as Word files by email, and their answers came
back the same way. Now the factory puts each stage straight into editor mode (/classroom/editor/prep.html on the
staging training app) and the expert answers there, row by row: OK, or needs change with a note. Ready, signed with
their name and surname, says the stage may go on. Nobody handles a file.

WHAT GOES WHERE
  push --pedagogy   pedagogy_review.py view: the same words as the three Word documents, topic by topic, with a hash
                    per row - a row sent again unchanged keeps its answers, a changed row is answered again
  pull              OK          -> the row's expert_review in working_claude\\pedagogy_review.json
                    needs change-> the row's expert_notes (the whole course's for the summaries and upgrades) and a
                                   line in FEEDBACK_LOG.md; pedagogy_review.py check stops until its 'done' says what
                                   the factory changed
                    Ready       -> pedagogy_review.json "ready" {by, on}: render signs the documents with it
  The course's id in the training app is the slug of its name (COURSE.html's title), so two courses with one name
  would become one there: create refuses a name already used, by a course or by a course in preparation.

THE KEY
The factory signs with a key kept on the office PC only: the environment variable NOVIKONTAS_FACTORY_KEY, or the file
%APPDATA%\\novikontas\\factory.key. The server keeps its SHA-256 (secret FACTORY_KEY_SHA256). The key is never in a
course folder or in this repository.

Standard library only.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import date

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pedagogy_review as pr  # noqa: E402
import workspace  # noqa: E402

# The staging training app - its public address and public anon key, the same the editor page uses. Staging only.
STAGING = "https://mgkhdbkxfaldfxyvfqrl.supabase.co"
ANON = ("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1na2hkYmt4ZmFsZGZ4eXZmcXJsIiwicm9sZSI6"
        "ImFub24iLCJpYXQiOjE3OTE3ODAyNDgsImV4cCI6MjEwNzM1NjI0OH0.IqohHiLweNG19tDhHxSslhcp__oCgEiTmLJ0BXJEiow")
EDITOR = "https://novikontas-staging.vercel.app/classroom/editor/prep.html?course=%s"
FILE = "portal.json"


class PortalError(Exception):
    def __init__(self, message, status=0, data=None):
        super().__init__(message)
        self.status, self.data = status, data


def key_file():
    base = os.environ.get("APPDATA") or os.path.join(os.path.expanduser("~"), ".config")
    return os.path.join(base, "novikontas", "factory.key")


def factory_key():
    k = (os.environ.get("NOVIKONTAS_FACTORY_KEY") or "").strip()
    if not k and os.path.isfile(key_file()):
        k = io.open(key_file(), encoding="utf-8").read().strip()
    if not k:
        raise PortalError("There is no factory key on this PC. Put it in %s (or NOVIKONTAS_FACTORY_KEY); "
                          "the office has it." % key_file())
    return k


def _http(action, payload):
    body = json.dumps(dict(payload, action=action), ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(STAGING + "/functions/v1/course-prep", data=body, method="POST", headers={
        "Content-Type": "application/json", "apikey": ANON, "Authorization": "Bearer " + ANON, "x-factory-key": factory_key()})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as e:
        try:
            data = json.loads(e.read().decode("utf-8") or "{}")
        except ValueError:
            data = {}
        raise PortalError(data.get("error") or "HTTP %d" % e.code, e.code, data)
    except urllib.error.URLError as e:
        raise PortalError("No connection to the staging training app: %s" % e.reason)


CALL = _http          # the tests put a stand-in server here


def call(action, **payload):
    return CALL(action, payload)


def _load(path, default=None):
    if not os.path.isfile(path):
        return default
    with io.open(path, encoding="utf-8") as f:
        return json.load(f)


def _save(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with io.open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def portal(course):
    return _load(workspace.claude_path(course, FILE))


def course_name(course):
    return ((_load(workspace.claude_path(course, "intake.json"), {}) or {}).get("course_name") or "").strip()


# ------------------------------------------------------------------ name, create
def cmd_name(title):
    r = call("name-check", title=title)
    if r.get("free"):
        print("Free: \"%s\" will be the course \"%s\" in the training app." % (r["title"], r["id"]))
        return 0
    print("Taken - %s Ask the operator for another name." % r.get("why", ""))
    return 2


def cmd_create(course, title=None):
    have = portal(course)
    if have:
        print("Already in preparation: %s (%s)\n  %s" % (have["title"], have["course_id"], EDITOR % have["course_id"]))
        return 0
    title = (title or course_name(course)).strip()
    if not title:
        print("Stopped - the course has no name yet. Ask intake question 9 (course_name), then create.")
        return 2
    try:
        r = call("create", title=title, factory={"folder": os.path.basename(workspace.master_of(course))})
    except PortalError as e:
        if e.status == 409:
            print("Stopped - %s Ask the operator for another name (intake question 9)." % e)
            return 2
        raise
    c = r["course"]
    _save(workspace.claude_path(course, FILE), {"course_id": c["id"], "title": c["title"], "editor": EDITOR % c["id"],
                                                "created_on": date.today().isoformat()})
    print("In preparation in the training app: %s (%s)\n  The experts' link: %s" % (c["title"], c["id"], EDITOR % c["id"]))
    return 0


def _need_portal(course):
    p = portal(course)
    if not p:
        print("Stopped - this course is not in the training app yet: course_portal.py create --course <course>")
    return p


# ------------------------------------------------------------------ push
def cmd_push_pedagogy(course):
    p = _need_portal(course)
    if not p:
        return 2
    probs, _ = pr.check(course)
    if probs:
        print("Stopped - the pedagogy is not ready for the experts (pedagogy_review.py check):")
        for x in probs[:20]:
            print("  - " + x)
        return 2
    v = pr.view(course)
    r = call("push", course_id=p["course_id"], kind="pedagogy", content=v["content"], items=v["items"], fingerprint=v["fingerprint"])
    if r.get("unchanged"):
        print("Nothing new: the editor already has these words (version %d)." % r["document"]["version"])
    else:
        print("Sent to the editor: the pedagogy, version %d - %d rows, %d answers kept from before."
              % (r["document"]["version"], r.get("rows", 0), r.get("answers_kept", 0)))
    print("  The experts' link: %s" % (EDITOR % p["course_id"]))
    return 0


# ------------------------------------------------------------------ pull
def _feedback(course, rows):
    fb = workspace.claude_path(course, "FEEDBACK_LOG.md")
    if not rows or not os.path.isfile(fb):
        return False
    text = io.open(fb, encoding="utf-8").read()
    nums = [int(l.split("|")[1]) for l in text.splitlines() if l.strip().startswith("|") and l.split("|")[1].strip().isdigit()]
    n = max(nums or [0])
    out = []
    for where, said, what in rows:
        n += 1
        out.append("| %d | %s | %s | %s | %s | no |" % (n, date.today().isoformat(), where, said.replace("|", "/").replace("\n", " "),
                                                    what.replace("|", "/")))
    with io.open(fb, "a", encoding="utf-8", newline="\n") as f:
        f.write(("\n" if text and not text.endswith("\n") else "") + "\n".join(out) + "\n")
    return True


def _who(a):
    return (a.get("by_name") or a.get("by_email") or "an expert").strip()


def pull_pedagogy(course, answers, ready):
    """The pedagogy's answers into pedagogy_review.json: (taken answer ids, taken document ids, log rows, said)."""
    f = pr.files(course)
    rev = _load(f["review"])
    if rev is None:
        return [], [], [], ["there is no pedagogy_review.json to write the answers into"]
    v = pr.view(course)
    where_of = {"course": (rev, "2 · course · summaries and upgrades")}
    for m in v["content"]["modules"]:
        rows = rev.setdefault("modules", {}).setdefault(str(m["n"]), {}).setdefault("rows", {})
        for t in m["topics"]:
            if t["id"] in rows:
                where_of[t["item"]] = (rows[t["id"]], "2 · M%02d · %s" % (m["n"], t["id"]))
    took, docs, log, said = [], [], [], []
    for a in answers:
        target = where_of.get(a["item"])
        if not target:
            said.append("%s answered %s, which is not a topic of the architecture any more - left in the editor" % (_who(a), a["item"]))
            continue
        row, where = target
        older = " (on words sent before)" if v["items"].get(a["item"]) != a.get("item_hash") else ""
        # one answer is one row in the editor: sent again, it replaces what it said before
        row["expert_review"] = [x for x in row.get("expert_review") or [] if x.get("answer") != a["id"]]
        row["expert_notes"] = [x for x in row.get("expert_notes") or [] if x.get("answer") != a["id"] or pr._filled(x.get("done"))]
        base = {"answer": a["id"], "by": _who(a), "email": a.get("by_email") or "", "on": (a.get("updated_at") or "")[:10]}
        if a["verdict"] == "ok":
            row["expert_review"].append(dict(base, ok=True, **({"note": a["note"]} if a.get("note") else {})))
        elif a["verdict"] == "change":
            row["expert_notes"].append(dict(base, said=(a.get("note") or "") + older, done=""))
            log.append((where, "%s [%s, editor mode]" % (a.get("note") or "", _who(a)), "to do"))
        else:
            said.append("%s: a decision with Claude is not taken in by this version - left in the editor" % where)
            continue
        for k in ("expert_review", "expert_notes"):
            if not row[k]:
                del row[k]
        took.append(a["id"])
    for d in ready:
        changes = sum(1 for _, (row, _w) in where_of.items() for n in row.get("expert_notes") or [] if not pr._filled(n.get("done")))
        rev["ready"] = {"by": d.get("ready_by_name") or "", "email": d.get("ready_by_email") or "",
                        "on": (d.get("ready_at") or "")[:10], "version": d.get("version"), "changes": changes}
        log.append(("2 · pedagogy · Ready", "Ready - signed %s [editor mode]" % rev["ready"]["by"],
                    "%d change(s) to carry out" % changes if changes else "nothing to change"))
        docs.append(d["id"])
    _save(f["review"], rev)
    return took, docs, log, said


def cmd_pull(course):
    p = _need_portal(course)
    if not p:
        return 2
    r = call("pull", course_id=p["course_id"])
    answers = [a for a in r.get("answers") or [] if a["kind"] == "pedagogy"]
    ready = [d for d in r.get("ready") or [] if d["kind"] == "pedagogy"]
    took, docs, log, said = pull_pedagogy(course, answers, ready)
    later = len(r.get("answers") or []) - len(answers) + len(r.get("ready") or []) - len(ready)
    logged = _feedback(course, log)
    if took or docs:
        call("ack", course_id=p["course_id"], answer_ids=took, document_ids=docs, read_at=r.get("read_at"))
    n_change = sum(1 for a in answers if a["id"] in took and a["verdict"] == "change")
    print("Taken from the editor: %d answer(s) - %d OK, %d asking for a change%s."
          % (len(took), len(took) - n_change, n_change, "; Ready, signed %s" % ", ".join(d.get("ready_by_name") or "" for d in ready) if ready else ""))
    if log and not logged:
        print("  (there is no FEEDBACK_LOG.md to log them in)")
    for s in said:
        print("  note: " + s)
    if later:
        print("  %d answer(s) on the scripts wait in the editor for the scripts' pull." % later)
    if n_change:
        print("Carry out every change asked (pedagogy_review.py check lists them), write in its 'done' what was changed, "
              "then render and push again.")
    return 0


# ------------------------------------------------------------------ status, remove
def cmd_status(course):
    p = _need_portal(course)
    if not p:
        return 2
    r = call("status", course_id=p["course_id"])
    c = r["course"]
    print("%s (%s) - %s\n  %s" % (c["title"], c["id"], c["stage"], EDITOR % c["id"]))
    for d in r.get("documents") or []:
        t = d["tally"]
        what = "the pedagogy" if d["kind"] == "pedagogy" else "the script of %s" % d["module"]
        print("  %-24s version %d: %d of %d rows answered (%d OK, %d to change)%s" % (
            what, d["version"], t["answered"], t["rows"], t["ok"], t["change"],
            " - Ready, signed %s" % d["ready_by_name"] if d["status"] == "ready" else ""))
    if not r.get("documents"):
        print("  nothing sent yet: course_portal.py push --course <course> --pedagogy")
    return 0


def cmd_remove(course, yes):
    p = _need_portal(course)
    if not p:
        return 2
    if not yes:
        print("Stopped - this removes %s and every answer on it from the training app. Run again with --yes." % p["course_id"])
        return 2
    call("remove", course_id=p["course_id"])
    os.remove(workspace.claude_path(course, FILE))
    print("Removed from the training app: %s." % p["course_id"])
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("name")
    s.add_argument("--title", required=True)
    for name in ("create", "push", "pull", "status", "remove"):
        s = sub.add_parser(name)
        s.add_argument("--course", required=True)
        if name == "create":
            s.add_argument("--title")
        if name == "push":
            s.add_argument("--pedagogy", action="store_true", required=True)
        if name == "remove":
            s.add_argument("--yes", action="store_true")
    x = ap.parse_args(argv)
    try:
        if x.cmd == "name":
            return cmd_name(x.title)
        course = workspace.work_folder(x.course)
        if x.cmd == "create":
            return cmd_create(course, x.title)
        if x.cmd == "push":
            return cmd_push_pedagogy(course)
        if x.cmd == "pull":
            return cmd_pull(course)
        if x.cmd == "status":
            return cmd_status(course)
        return cmd_remove(course, x.yes)
    except PortalError as e:
        print("Stopped - %s" % e)
        return 3


if __name__ == "__main__":
    sys.exit(main())
