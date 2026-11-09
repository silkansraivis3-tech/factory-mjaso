#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""The experts review a course in preparation in the training app's editor - the factory's side. Staging only.

    course_portal.py name   --title "<name>"                  is the name free in the training app? (intake question 9)
    course_portal.py create --course <course> [--title "<name>"]   the course in preparation, under intake's course_name
    course_portal.py push   --course <course> --pedagogy      the experts' pedagogy documents into the editor
    course_portal.py pull   --course <course>                 the experts' answers and their Ready back into the files
    course_portal.py status --course <course>                 the stage, how much is answered, who said Ready
    course_portal.py remove --course <course> --yes           a course in preparation that was never built
    course_portal.py import --course <course>                 the built course into the staging editor as a draft release
    course_portal.py upload --course <course>                 after an attended build or fix.py rebuild: imported once only
                                                              picture spaces still to fill stop it, else the editor's
                                                              stop message says what still does (fix.py rebuild runs it)
    course_portal.py watch  --once                            the office PC: a course whose Ready asked for its build is
                                                              built unattended and imported (the scheduled task runs this)
    course_portal.py install-task                             the scheduled task: watch --once every 10 minutes

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

THE BUILD AFTER READY (L70)
The expert's Ready on the pedagogy queues the course for its build. Every 10 minutes the scheduled task on the office PC
runs watch --once: it takes the oldest queued course (one PC at a time), pulls the answers, and starts Claude Code
unattended in that course's folder (claude -p, the course-factory skill, SKILL.md "Auto build"). When the run says
AUTO BUILD DONE, the course's modules\\ folder is imported into the staging editor as a draft release
(course_import.mjs). A build that stops says why in the editor and waits until the office starts it again. The course
folders this PC knows are in %APPDATA%\\novikontas\\courses.json (create and push write it).

THE KEY
The factory signs with a key kept on the office PC only: the environment variable NOVIKONTAS_FACTORY_KEY, or the file
%APPDATA%\\novikontas\\factory.key. The server keeps its SHA-256 (secret FACTORY_KEY_SHA256). The key is never in a
course folder or in this repository.

Standard library only.
"""
from __future__ import annotations

import argparse
import glob
import io
import json
import os
import subprocess
import sys
import time
import traceback
import urllib.error
import urllib.request
from datetime import date, datetime


def home():
    return os.path.join(os.environ.get("APPDATA") or os.path.join(os.path.expanduser("~"), ".config"), "novikontas")


def no_console():
    """pythonw.exe (the scheduled task) has no console: sys.stdout and sys.stderr are None, and the first reconfigure or
    write ends the run with exit 1 before anything is logged. Then what is printed goes nowhere and what goes wrong goes,
    with its traceback, to watch.log."""
    if sys.stdout is None:
        sys.stdout = io.open(os.devnull, "w", encoding="utf-8")
    if sys.stderr is None:
        os.makedirs(home(), exist_ok=True)
        sys.stderr = io.open(os.path.join(home(), "watch.log"), "a", encoding="utf-8", errors="replace")


no_console()
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
    return os.path.join(home(), "factory.key")


def register(course_id, course):
    """This PC's list of its courses in preparation and their folders - how watch finds a course to build."""
    f = os.path.join(home(), "courses.json")
    reg = _load(f, {}) or {}
    if reg.get(course_id) != os.path.abspath(course):
        reg[course_id] = os.path.abspath(course)
        _save(f, reg)


def folder_of(course_id):
    reg = _load(os.path.join(home(), "courses.json"), {}) or {}
    if reg.get(course_id) and os.path.isdir(reg[course_id]):
        return reg[course_id]
    # a course made before the list existed: its portal.json somewhere under the Desktop
    desk = os.path.join(os.path.expanduser("~"), "Desktop")
    for depth in ("*", "*/*", "*/*/*", "*/*/*/*"):
        for pj in glob.glob(os.path.join(desk, depth, "working_claude", FILE)):
            if (_load(pj, {}) or {}).get("course_id") == course_id:
                work = os.path.dirname(os.path.dirname(pj))
                register(course_id, work)
                return work
    return None


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
    register(c["id"], course)
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
    register(p["course_id"], course)
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
    # the editor's row -> (where it is written, the log's place, what it is about)
    where_of = {"course": (rev, "2 · course · summaries", None), "upgrades": (rev, "2 · course · upgrades", "upgrades")}
    topic_of = {}            # the editor's topic row -> (module, Sub-ILO id, is a Main ILO)
    for m in v["content"]["modules"]:
        mod = rev.setdefault("modules", {}).setdefault(str(m["n"]), {})
        rows = mod.setdefault("rows", {})
        if m.get("act_item"):
            where_of[m["act_item"]] = (mod, "2 · M%02d · activities" % m["n"], "activities")
        for t in m["topics"]:
            if t["id"] in rows:
                where_of[t["item"]] = (rows[t["id"]], "2 · M%02d · %s" % (m["n"], t["id"]), None)
                topic_of[t["item"]] = (m["n"], t["id"], t["main"])
    took, docs, log, said = [], [], [], []

    def reword(item, text, who):
        """A Sub-ILO's new wording the expert took: ratified into the architecture (L2); a Main ILO is never re-worded."""
        n, sid, main = topic_of[item]
        if text and not main and pr.ratify(course, n, sid, text, who):
            return "; Sub-ILO re-worded: " + text
        return ""
    for a in answers:
        target = where_of.get(a["item"])
        if not target:
            said.append("%s answered %s, which is not a row of the documents any more - left in the editor" % (_who(a), a["item"]))
            continue
        row, where, about = target
        older = " (on words sent before)" if v["items"].get(a["item"]) != a.get("item_hash") else ""
        # one answer is one row in the editor: sent again, it replaces what it said before
        row["expert_review"] = [x for x in row.get("expert_review") or [] if x.get("answer") != a["id"]]
        row["expert_notes"] = [x for x in row.get("expert_notes") or [] if x.get("answer") != a["id"] or pr._filled(x.get("done"))]
        base = dict({"answer": a["id"], "by": _who(a), "email": a.get("by_email") or "", "on": (a.get("updated_at") or "")[:10]},
                    **({"about": about} if about else {}))
        d = a.get("decision") or {}
        if a["verdict"] == "ok":
            row["expert_review"].append(dict(base, ok=True, **({"note": a["note"]} if a.get("note") else {})))
            rw = reword(a["item"], ((row.get("proposed") or {}).get("revised_outcome") or "").strip(), _who(a)) if a["item"] in topic_of else ""
            if rw:
                log.append((where, "Take proposed [%s, editor mode]" % _who(a), rw[2:]))
        elif a["verdict"] == "change":
            row["expert_notes"].append(dict(base, said=(a.get("note") or "") + older, done=""))
            log.append((where, "%s [%s, editor mode]" % (a.get("note") or "", _who(a)), "to do"))
        elif a["verdict"] == "decision" and about is None and row is not rev and d.get("choice") in ("keep", "claude"):
            now = row.get("now") or {}
            if d["choice"] == "keep":
                lvl = now.get("level") if isinstance(now.get("level"), int) and now.get("level") >= 1 else d.get("level")
                pr.carry_out(row, lvl, d.get("said") or "Keep it as the old course teaches it.", _who(a),
                             how="Kept as the old course teaches it: " + (now.get("how") or ""))
                what = "kept as the old course, at %s" % pr.level(lvl)
            else:
                pr.carry_out(row, int(d["level"]), d.get("said") or "", _who(a), how=d.get("how") or "", why=d.get("why") or None)
                what = "set with Claude to %s: %s" % (pr.level(int(d["level"])), d.get("how") or "")
                rw = (d.get("revised_outcome") or "").strip()
                if rw and not topic_of[a["item"]][2]:
                    row["proposed"]["revised_outcome"] = rw
                    what += reword(a["item"], rw, _who(a))
            row["expert_review"].append(dict(base, decision=d["choice"], level=row["proposed"]["level"]))
            log.append((where, "%s [%s, editor mode]" % (d.get("said") or "", _who(a)), what + older))
        else:
            said.append("%s: an answer of a kind this version cannot take in (%s) - left in the editor" % (where, a["verdict"]))
            continue
        # "take it / keep it, with a note on what to fix": the note is carried out like any other
        if a["verdict"] in ("ok", "decision") and (a.get("note") or "").strip():
            row["expert_notes"].append(dict(base, said=a["note"].strip() + older, done=""))
            log.append((where, "%s [%s, editor mode]" % (a["note"].strip(), _who(a)), "to do"))
        for k in ("expert_review", "expert_notes"):
            if not row[k]:
                del row[k]
        took.append(a["id"])
    for d in ready:
        targets = {id(t[0]): t[0] for t in where_of.values()}.values()
        changes = sum(1 for row in targets for n in row.get("expert_notes") or [] if not pr._filled(n.get("done")))
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
    kinds = [a["verdict"] if a["verdict"] != "decision" else (a.get("decision") or {}).get("choice") for a in answers if a["id"] in took]
    n_change = kinds.count("change")
    print("Taken from the editor: %d answer(s) - %d OK, %d kept as now, %d decided with Claude, %d asking for a change%s."
          % (len(took), kinds.count("ok"), kinds.count("keep"), kinds.count("claude"), n_change,
             "; Ready, signed %s" % ", ".join(d.get("ready_by_name") or "" for d in ready) if ready else ""))
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


# ------------------------------------------------------------------ the build after Ready (L70)
AUTO_PROMPT = """You are the NOVIKONTAS course factory, running unattended on the office PC (auto build, SKILL.md "Auto build").
The course in this folder - "{title}" ({course_id}) - was answered in the training app's editor, and {expert} pressed
Ready on its pedagogy. Their answers are already in working_claude (pedagogy_review.json, architecture.json,
FEEDBACK_LOG.md). Use the course-factory skill and build the whole course now, by its "Auto build" rules: carry out every
expert note and write its done, render the pedagogy documents, approve Stage 2 and every module's content script with
--by "{expert} (Ready in editor)", build every module, compile COURSE.html and run the factory's checks, fixing what they
find. Nobody is there to answer: never stop to ask - write the question in working_claude/OPEN_EXPERT_QUESTIONS.md and
carry on with the factory's best choice. Generate no paid pictures or videos. Fill the picture spaces from the free
sources, in the order of SKILL.md "Auto build"; a space nobody could fill keeps its brief and does not stop the build.
Never push to git and never change a file outside this folder. End with one line: AUTO BUILD DONE (AUTO BUILD DONE -
PICTURES PENDING: <n> when only picture spaces are left), or AUTO BUILD STOPPED: <why>."""
ALLOWED = ["Bash", "PowerShell", "Read", "Write", "Edit", "Glob", "Grep", "Skill", "Agent", "WebSearch", "WebFetch", "TodoWrite"]
DENIED = ["Bash(git push:*)", "PowerShell(git push:*)", "mcp__plugin_nano-banana_nano-banana__generate_image",
          "mcp__plugin_nano-banana_nano-banana__generate_video"]


def unattended_env(**extra):
    """The environment of an unattended run. A print-mode run stops helper agents still working 10 minutes after its own
    last turn; an unattended build waits on its script writers and builders for hours, so it waits for them without limit."""
    return dict(os.environ, CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS="0", **extra)


def claude_command(prompt):
    """The unattended run: edits are taken without asking inside the course folder (files outside it are refused),
    shell commands run, paid pictures and git push are refused. NOVIKONTAS_CLAUDE_CMD replaces the program (tests)."""
    exe = os.environ.get("NOVIKONTAS_CLAUDE_CMD")
    base = json.loads(exe) if exe else ["claude"]
    return base + ["-p", prompt, "--permission-mode", "acceptEdits", "--allowedTools", *ALLOWED, "--disallowedTools", *DENIED]


def modules_folder(course):
    m = os.path.join(course, "modules")
    return m if os.path.isfile(os.path.join(m, "COURSE.html")) else None


def cmd_import(course, pending=()):
    p = _need_portal(course)
    if not p:
        return 2, None
    folder = modules_folder(course)
    if not folder:
        print("Stopped - there is no built course to import: modules\\COURSE.html is missing.")
        return 2, None
    node = json.loads(os.environ["NOVIKONTAS_NODE"]) if os.environ.get("NOVIKONTAS_NODE") else ["node"]
    notes = (["Pictures pending: %d picture space(s) still hold a Phase A placeholder - fill them and import again before "
              "this draft is published" % len(pending)] + list(pending)[:40]) if pending else []
    run = subprocess.run(node + [os.path.join(HERE, "course_import.mjs"), folder, p["course_id"]], capture_output=True,
                         text=True, encoding="utf-8", errors="replace", env=dict(os.environ, NOVIKONTAS_IMPORT_NOTES=json.dumps(notes)),
                         stdin=subprocess.DEVNULL, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    last = (run.stdout.strip().splitlines() or ["{}"])[-1]
    try:
        r = json.loads(last)
    except ValueError:
        r = {"ok": False, "error": (run.stderr or run.stdout or "no answer")[-500:]}
    if r.get("ok"):
        rel = r.get("release") or {}
        print("Imported into the staging editor as draft %s of %s%s." % (rel.get("version"), p["course_id"],
              " - pictures pending: %d" % len(pending) if pending else ""))
        return 0, r
    print("Stopped - the import did not go through: %s" % r.get("error"))
    return 2, r


def blockers(course):
    """what stops the built course going into the editor as a draft, from the course package check: (the picture spaces
    still holding a Phase A placeholder, everything else). A placeholder alone does not stop a draft - it never reaches
    the tablets, and the draft says how many are pending."""
    folder = modules_folder(course)
    if not folder:
        return [], ["modules\\COURSE.html is missing - the course is not compiled"]
    import check_course_package
    probs = check_course_package.check(folder)[0] + failed_builds(course)
    pics = [x for x in probs if "is a Phase A placeholder" in x]
    return pics, [x for x in probs if x not in pics]


def failed_builds(course):
    """each module whose last build ended on FAIL: a module with no PASS is not built, whatever a report says"""
    out = []
    logdir = workspace.claude_path(workspace.work_folder(course, create=False), "_build")
    for ans in sorted(glob.glob(os.path.join(logdir, "*_answer.txt"))):
        said = [x.strip() for x in io.open(ans, encoding="utf-8", errors="replace").read().splitlines()
                if x.startswith(("PASS ", "FAIL "))]
        if said and said[-1].startswith("FAIL ") and " - course package" not in said[-1]:
            out.append("%s - its last build did not pass" % said[-1][:120])
    return out


def _stop_message(cid, why):
    """the editor's 'Build stopped' message replaced by the course's state now - only where one is shown: a course
    waiting in the queue without one would be held back by it"""
    c = call("status", course_id=cid).get("course") or {}
    if c.get("stage") == "build_requested" and c.get("build_error"):
        call("build-done", course_id=cid, error=why)
        return True
    return False


def cmd_upload(course):
    """after an attended build, or a rebuild (fix.py rebuild ends with this): once nothing but picture spaces still to
    fill stops it, the built course goes into the staging editor as a draft and the editor's old stop message goes with
    it (the import marks the course built); while something else stops it, the stop message says what, today. Unasked."""
    p = portal(course)
    if not p:
        print("Not uploaded - this course is not in the training app (course_portal.py create).")
        return 0
    if os.environ.get("NOVIKONTAS_AUTO_BUILD") == "1":
        print("Not uploaded yet - this is the unattended build: the watch uploads it when the run ends.")
        return 0
    pics, other = blockers(course)
    if other:
        why = "Not uploaded after the session of %s - %d thing(s) still stop it: %s" % (
            date.today().isoformat(), len(other), "; ".join(other[:3]) + (" ..." if len(other) > 3 else ""))
        print(why)
        if _stop_message(p["course_id"], why[:2000]):
            print("  The editor's stop message now says this.")
        return 1
    return cmd_import(course, pics)[0]


def _log(line):
    os.makedirs(home(), exist_ok=True)
    with io.open(os.path.join(home(), "watch.log"), "a", encoding="utf-8") as f:
        f.write("%s  %s\n" % (datetime.now().isoformat(timespec="seconds"), line))


def _locked():
    """One watch at a time on this PC: a build runs for hours, and the task fires every 10 minutes."""
    lock = os.path.join(home(), "watch.lock")
    if os.path.isfile(lock) and time.time() - os.path.getmtime(lock) < 20 * 3600:
        return None
    os.makedirs(home(), exist_ok=True)
    io.open(lock, "w", encoding="utf-8").write(str(os.getpid()))
    return lock


def cmd_watch_once():
    lock = _locked()
    if not lock:
        return 0
    try:
        nxt = call("build-next").get("course")
        if not nxt:
            return 0
        cid = nxt["id"]
        course = folder_of(cid)
        if not course:
            call("build-done", course_id=cid, error="The office PC does not know this course's folder. Open the course's "
                 "factory session once and run course_portal.py push.")
            _log("%s: no folder on this PC" % cid)
            return 2
        call("build-claim", course_id=cid)
        _log("%s: building in %s" % (cid, course))
        cmd_pull(course)
        expert = nxt.get("build_requested_by") or "the expert"
        logdir = workspace.claude_path(course, "auto_build")
        os.makedirs(logdir, exist_ok=True)
        logf = os.path.join(logdir, datetime.now().strftime("%Y%m%d-%H%M") + ".log")
        prompt = AUTO_PROMPT.format(title=nxt.get("title") or cid, course_id=cid, expert=expert)
        env = unattended_env(NOVIKONTAS_AUTO_BUILD="1")
        with io.open(logf, "w", encoding="utf-8") as out:
            run = subprocess.run(claude_command(prompt), cwd=workspace.master_of(course), stdout=out, stderr=subprocess.STDOUT,
                                 text=True, encoding="utf-8", errors="replace", env=env, timeout=20 * 3600,
                                 creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        said = io.open(logf, encoding="utf-8", errors="replace").read()
        last = [l for l in said.strip().splitlines() if l.strip()][-1:] or [""]
        pics, other = blockers(course)
        if run.returncode != 0 or "AUTO BUILD DONE" not in said:
            why = last[0][:500] if "AUTO BUILD STOPPED" in last[0] else "the build ended without AUTO BUILD DONE (exit %d) - see %s" % (run.returncode, logf)
            if other or not pics:                     # a run stopped on pictures alone still goes up, as pictures pending
                call("build-done", course_id=cid, error=why)
                _log("%s: stopped - %s" % (cid, why))
                return 2
        code, r = cmd_import(course, pics)
        if code:
            call("build-done", course_id=cid, error="built, but the import failed: %s" % ((r or {}).get("error") or "see the log"))
            _log("%s: import failed" % cid)
            return 2
        _log("%s: built and imported as draft %s%s" % (cid, ((r or {}).get("release") or {}).get("version"),
                                                        " - pictures pending: %d" % len(pics) if pics else ""))
        return 0
    except PortalError as e:
        _log("stopped: %s" % e)
        return 3
    except subprocess.TimeoutExpired:
        call("build-done", course_id=cid, error="the build ran for 20 hours and was stopped")
        return 2
    except Exception:
        _log("stopped - an error in the watch:\n" + traceback.format_exc())
        return 4
    finally:
        os.remove(lock)


LAUNCHER = """# The NOVIKONTAS course factory's watch, run by the scheduled task: the newest installed course-factory plugin's
# course_portal.py watch --once (the plugin's folder changes with every version). pythonw has no console: what goes
# wrong is written, with its traceback, to watch.log beside this file.
import datetime, glob, os, subprocess, sys, traceback
here = os.path.dirname(os.path.abspath(__file__))
def log(line):
    with open(os.path.join(here, "watch.log"), "a", encoding="utf-8") as f:
        f.write("%s  %s\\n" % (datetime.datetime.now().isoformat(timespec="seconds"), line))
base = os.path.join(os.path.expanduser("~"), ".claude", "plugins", "cache", "novikontas-course-factory", "course-factory")
def ver(p):
    try:
        return tuple(int(x) for x in os.path.basename(p).split("."))
    except ValueError:
        return (0,)
try:
    found = sorted(glob.glob(os.path.join(base, "*")), key=ver)
    if not found:
        log("watch: no course-factory plugin in %s" % base)
        sys.exit(5)
    sys.exit(subprocess.call([sys.executable, os.path.join(found[-1], "skills", "course-factory", "scripts", "course_portal.py"),
                              "watch", "--once"], stdin=subprocess.DEVNULL, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)))
except SystemExit:
    raise
except BaseException:
    log("watch: the launcher stopped:\\n" + traceback.format_exc())
    sys.exit(4)
"""
TASK = "NOVIKONTAS course factory - build after Ready"


def cmd_install_task():
    """The scheduled task: every 10 minutes, while this user is signed in to the PC, with no window."""
    os.makedirs(home(), exist_ok=True)
    launcher = os.path.join(home(), "watch.py")
    io.open(launcher, "w", encoding="utf-8", newline="\n").write(LAUNCHER)
    pyw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    py = pyw if os.path.isfile(pyw) else sys.executable
    run = subprocess.run(["schtasks", "/Create", "/F", "/TN", TASK, "/SC", "MINUTE", "/MO", "10",
                          "/TR", '"%s" "%s"' % (py, launcher)], capture_output=True, text=True, errors="replace")
    if run.returncode:
        print("Stopped - the scheduled task was not made: %s" % (run.stderr or run.stdout).strip())
        return 2
    print("Scheduled: '%s' every 10 minutes - it builds a course once its expert presses Ready.\n  Log: %s"
          % (TASK, os.path.join(home(), "watch.log")))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("name")
    s.add_argument("--title", required=True)
    sub.add_parser("install-task")
    s = sub.add_parser("watch")
    s.add_argument("--once", action="store_true", required=True)
    for name in ("create", "push", "pull", "status", "remove", "import", "upload"):
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
        if x.cmd == "watch":
            return cmd_watch_once()
        if x.cmd == "install-task":
            return cmd_install_task()
        course = workspace.work_folder(x.course)
        if os.environ.get("NOVIKONTAS_TRIAL") == "1" or os.path.isfile(os.path.join(workspace.master_of(course), "FACTORY_TRIAL.json")):
            print("Stopped - this is a factory trial (factory_trial.py): a trial never goes to the training app")
            return 2
        if x.cmd == "create":
            return cmd_create(course, x.title)
        if x.cmd == "push":
            return cmd_push_pedagogy(course)
        if x.cmd == "pull":
            return cmd_pull(course)
        if x.cmd == "status":
            return cmd_status(course)
        if x.cmd == "import":
            return cmd_import(course)[0]
        if x.cmd == "upload":
            return cmd_upload(course)
        return cmd_remove(course, x.yes)
    except PortalError as e:
        print("Stopped - %s" % e)
        return 3


if __name__ == "__main__":
    sys.exit(main())
