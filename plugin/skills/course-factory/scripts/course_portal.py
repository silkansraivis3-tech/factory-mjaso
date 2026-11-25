#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""The experts review a course in preparation in the training app's editor - the factory's side. Two sites: live
(lnd.novikontas.org) and staging.

    course_portal.py name   --title "<name>" [--site S]       is the name free in the training app? (intake question 9)
    course_portal.py create --course <course> [--title "<name>"] [--site S]
                                                              the course in preparation, under intake's course_name
                                                              (on live unless --site staging)
    course_portal.py link   --course <course> --site S [--course-id <id>]
                                                              the same course on the other site (adopts one started there)
    course_portal.py push   --course <course> --pedagogy [--site S] [--course-id <id>]
                                                              the experts' pedagogy documents into the editor
    course_portal.py pull   --course <course> [--site S] [--course-id <id>]
                                                              the experts' answers and their Ready back into the files;
                                                              more than one possible course: it lists them (exit 2)
    course_portal.py status --course <course>                 the stage, how much is answered, who said Ready - each site
    course_portal.py remove --course <course> --yes [--site S]  a course in preparation that was never built
    course_portal.py import --course <course>                 the built course into the staging editor as a draft release
                                                              (the importer reaches staging only)
    course_portal.py upload --course <course>                 after an attended build or fix.py rebuild: imported once only
                                                              picture spaces still to fill stop it, else the editor's
                                                              stop message says what still does (fix.py rebuild runs it)
    course_portal.py watch  --once                            the office PC: a course whose Ready asked for its build is
                                                              built unattended and imported (the scheduled task runs this)
    course_portal.py install-task                             the scheduled task: watch --once every 10 minutes

WHY THIS EXISTS
The experts used to get the pedagogy documents and the content scripts as Word files by email, and their answers came
back the same way. Now the factory puts each stage straight into editor mode (/classroom/editor/prep.html on the
training app, live or staging) and the expert answers there, row by row: OK, or needs change with a note. Ready, signed with
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

THE SITES
portal.json keeps "sites": {site: {course_id, title, editor}} - the sites the course is in preparation on (a portal.json
made before it had sites reads as staging). pull looks at them, and at courses of the same slug family (gas-basic,
gas-basic-v2); with answers waiting on more than one it never merges or guesses: it prints a numbered list and exits 2,
and the choice (--site / --course-id) is kept in portal.json "use". Every build pulls first (compile/scripts/build_module.py).

THE BUILD AFTER READY (L70)
The expert's Ready on the pedagogy queues the course for its build, on the site where it was pressed. Every 10 minutes
the scheduled task on the office PC runs watch --once: it takes the oldest queued course of either site (one PC at a
time), pulls the answers, and starts Claude Code
unattended in that course's folder (claude -p, the course-factory skill, SKILL.md "Auto build"). When the run says
AUTO BUILD DONE, the course's modules\\ folder is imported into the staging editor as a draft release
(course_import.mjs). A build that stops says why in the editor and waits until the office starts it again. The course
folders this PC knows are in %APPDATA%\\novikontas\\courses.json (create and push write it).

THE KEY
The factory signs with a key kept on the office PC only: for one site the environment variable
NOVIKONTAS_FACTORY_KEY_LIVE / _STAGING or the file %APPDATA%\\novikontas\\factory.live.key / factory.staging.key, else the
common NOVIKONTAS_FACTORY_KEY or factory.key. Each server keeps its SHA-256 (secret FACTORY_KEY_SHA256). The key is never
in a course folder or in this repository.

Standard library only.
"""
from __future__ import annotations

import argparse
import glob
import io
import json
import os
import re
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

# The training app's two sites - each one's public address and public anon key (the same the editor page uses) and the
# address of its editor. Live is the first: create starts a course there unless told otherwise.
SITES = {
    "live": {
        "name": "live",
        "url": "https://vapnxststhoxadhhdyty.supabase.co",
        "anon": ("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZhcG54c3RzdGhveGFkaGhkeXR5Iiwicm9s"
                 "ZSI6ImFub24iLCJpYXQiOjE3ODg1MTY5NTMsImV4cCI6MjEwNDA5Mjk1M30.GELAo5QSxdnCtyrJYUYc6TsVk1UwoXcYn2zCecxNlLQ"),
        "editor": "https://lnd.novikontas.org/classroom/editor/prep?course=%s",
    },
    "staging": {
        "name": "staging",
        "url": "https://mgkhdbkxfaldfxyvfqrl.supabase.co",
        "anon": ("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1na2hkYmt4ZmFsZGZ4eXZmcXJsIiwicm9s"
                 "ZSI6ImFub24iLCJpYXQiOjE3OTE3ODAyNDgsImV4cCI6MjEwNzM1NjI0OH0.IqohHiLweNG19tDhHxSslhcp__oCgEiTmLJ0BXJEiow"),
        "editor": "https://novikontas-staging.pages.dev/classroom/editor/prep?course=%s",
    },
}
ORDER = ("live", "staging")
FILE = "portal.json"


class PortalError(Exception):
    def __init__(self, message, status=0, data=None, site=None):
        super().__init__(message)
        self.status, self.data, self.site = status, data, site

    def __str__(self):
        return ("%s: %s" % (self.site, super().__str__())) if self.site else super().__str__()


def editor_link(site, course_id):
    return SITES[site]["editor"] % course_id


def key_file(site=None):
    return os.path.join(home(), "factory.%s.key" % site if site else "factory.key")


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
            if course_id in [s.get("course_id") for s in _normal(_load(pj, {}) or {})["sites"].values()]:
                work = os.path.dirname(os.path.dirname(pj))
                register(course_id, work)
                return work
    return None


def factory_key(site):
    """The key for one site: its own variable or file, else the common one."""
    def read(f):
        return io.open(f, encoding="utf-8").read() if os.path.isfile(f) else ""
    spots = (os.environ.get("NOVIKONTAS_FACTORY_KEY_" + site.upper()), read(key_file(site)),
             os.environ.get("NOVIKONTAS_FACTORY_KEY"), read(key_file()))
    k = next((x.strip() for x in spots if x and x.strip()), "")
    if not k:
        raise PortalError("There is no factory key on this PC. Put it in %s (or NOVIKONTAS_FACTORY_KEY_%s; the common %s "
                          "and NOVIKONTAS_FACTORY_KEY work for both sites); the office has it."
                          % (key_file(site), site.upper(), key_file()), site=site)
    return k


def _http(site, action, payload):
    s = SITES[site]
    body = json.dumps(dict(payload, action=action), ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(s["url"] + "/functions/v1/course-prep", data=body, method="POST", headers={
        "Content-Type": "application/json", "apikey": s["anon"], "Authorization": "Bearer " + s["anon"],
        "x-factory-key": factory_key(site)})
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
        raise PortalError("No connection to the training app: %s" % e.reason)


CALL = _http          # the tests put a stand-in server here: CALL(site, action, payload)


def call(site, action, **payload):
    try:
        return CALL(site, action, payload)
    except PortalError as e:
        e.site = e.site or site
        raise


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


def _normal(raw):
    """portal.json in its present shape: {title, created_on, sites: {site: {course_id, title, editor}}, use: {site,
    course_id}}. One made before it had sites was made on staging."""
    if "sites" in raw:
        return dict(raw, sites={s: dict(e) for s, e in (raw["sites"] or {}).items() if s in SITES and e.get("course_id")})
    if not raw.get("course_id"):
        return dict(raw, sites={})
    p = {k: v for k, v in raw.items() if k not in ("course_id", "editor")}
    p["sites"] = {"staging": {"course_id": raw["course_id"], "title": raw.get("title") or "",
                              "editor": raw.get("editor") or editor_link("staging", raw["course_id"])}}
    return p


def portal(course):
    raw = _load(workspace.claude_path(course, FILE))
    return _normal(raw) if raw else None


def save_portal(course, p):
    _save(workspace.claude_path(course, FILE), p)


def add_site(p, site, c):
    """c: a course in preparation as the function gives it"""
    p.setdefault("sites", {})[site] = {"course_id": c["id"], "title": c.get("title") or p.get("title") or "",
                                       "editor": editor_link(site, c["id"]), "added_on": date.today().isoformat()}
    p.setdefault("title", c.get("title") or "")
    p.setdefault("created_on", date.today().isoformat())
    return p


def sites_of(p):
    return [s for s in ORDER if s in p["sites"]]


def course_name(course):
    return ((_load(workspace.claude_path(course, "intake.json"), {}) or {}).get("course_name") or "").strip()


# ------------------------------------------------------------------ name, create
def cmd_name(title, site="live"):
    r = call(site, "name-check", title=title)
    if r.get("free"):
        print("Free on the %s site: \"%s\" will be the course \"%s\" in the training app." % (site, r["title"], r["id"]))
        return 0
    print("Taken on the %s site - %s Ask the operator for another name." % (site, r.get("why", "")))
    return 2


def cmd_create(course, title=None, site="live"):
    have = portal(course)
    if have and have["sites"]:
        for s in sites_of(have):
            print("Already in preparation on %s: %s (%s)\n  %s" % (s, have["sites"][s]["title"], have["sites"][s]["course_id"],
                                                                 editor_link(s, have["sites"][s]["course_id"])))
        if site not in have["sites"]:
            print("  To add it to the %s site as well: course_portal.py link --course <course> --site %s" % (site, site))
        return 0
    title = (title or course_name(course)).strip()
    if not title:
        print("Stopped - the course has no name yet. Ask intake question 9 (course_name), then create.")
        return 2
    try:
        r = call(site, "create", title=title, factory={"folder": os.path.basename(workspace.master_of(course))})
    except PortalError as e:
        if e.status == 409:
            print("Stopped - %s Ask the operator for another name (intake question 9)." % e)
            return 2
        raise
    c = r["course"]
    save_portal(course, add_site(dict(have or {}), site, c))
    register(c["id"], course)
    print("In preparation in the training app (%s): %s (%s)\n  The experts' link: %s"
          % (site, c["title"], c["id"], editor_link(site, c["id"])))
    return 0


def cmd_link(course, site, course_id=None):
    """The course in preparation on another site as well: a course the office started in that site's editor is adopted
    (as create does); with --course-id, the one that is there already."""
    have = portal(course) or {"sites": {}}
    if site in have["sites"]:
        e = have["sites"][site]
        print("Already on the %s site: %s (%s)\n  %s" % (site, e["title"], e["course_id"], editor_link(site, e["course_id"])))
        return 0
    title = (have.get("title") or course_name(course)).strip()
    if not title and not course_id:
        print("Stopped - the course has no name yet. Ask intake question 9 (course_name), then link.")
        return 2
    try:
        if course_id:
            c = call(site, "status", course_id=course_id).get("course") or {"id": course_id}
            c = dict(c, id=course_id)
        else:
            c = call(site, "create", title=title, factory={"folder": os.path.basename(workspace.master_of(course))})["course"]
    except PortalError as e:
        if e.status == 404 and course_id:
            print("Stopped - there is no course in preparation %s on the %s site." % (course_id, site))
            return 2
        if e.status == 409:
            print("Stopped - %s If it is this same course, run again with --course-id <its id>." % e)
            return 2
        raise
    save_portal(course, add_site(have, site, c))
    register(c["id"], course)
    print("Now on the %s site as well: %s (%s)\n  The experts' link: %s"
          % (site, c.get("title") or title, c["id"], editor_link(site, c["id"])))
    return 0


def _need_portal(course):
    p = portal(course)
    if not p or not p["sites"]:
        print("Stopped - this course is not in the training app yet: course_portal.py create --course <course>")
        return None
    return p


# ------------------------------------------------------------------ which course in preparation
def _slug(t):
    return re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")


def family_ids(course, p):
    """the ids a course in preparation for this course could have: the ones it is known by, the slug of its name, and each
    without or with a version tail (gas-basic, gas-basic-v2, gas-basic-v3)"""
    ids = [e["course_id"] for e in p["sites"].values()] + ([_slug(course_name(course))] if course_name(course) else [])
    out = []
    for i in ids:
        base = re.sub(r"-v\d+$", "", i)
        out += [i, base, base + "-v2", base + "-v3"]
    return list(dict.fromkeys(x for x in out if x))


def _option(site, cid, r, known):
    ans, rdy = r.get("answers") or [], r.get("ready") or []
    dates = [(a.get("updated_at") or "")[:10] for a in ans] + [(d.get("ready_at") or "")[:10] for d in rdy]
    return {"site": site, "course_id": cid, "title": (r.get("course") or {}).get("title") or cid, "editor": editor_link(site, cid),
            "waiting": len(ans) + len(rdy), "newest": max(dates or [""]), "known": known, "r": r}


def gather(p, ids, only_site=None, only_id=None):
    """-> (the courses in preparation found, notes, the sites that failed). Looks with pull, which changes nothing."""
    known = {(s, e["course_id"]) for s, e in p["sites"].items()}
    found, notes, failed = [], [], {}
    for s in ORDER:
        if only_site and s != only_site:
            continue
        for cid in ([only_id] if only_id else ids):
            if s in failed:
                break
            try:
                r = call(s, "pull", course_id=cid)
            except PortalError as e:
                if e.status == 404:
                    if (s, cid) in known:
                        notes.append("%s: %s is not in preparation there (any more)" % (s, cid))
                    continue
                failed[s] = e
                continue
            found.append(_option(s, cid, r, (s, cid) in known))
    for s, e in failed.items():
        if s in p["sites"] or not found:       # a site the course is not on, with no key here, is no news
            notes.append("%s site not looked at - %s" % (s, e))
    return found, notes, failed


def option_lines(opts):
    out = []
    for n, o in enumerate(opts, 1):
        out.append("  %d. %s - %s \"%s\" - %s - %s" % (
            n, o["site"], o["course_id"], o["title"], o["editor"],
            ("%d answer(s) waiting, the newest from %s" % (o["waiting"], o["newest"] or "?")) if o["waiting"] else "no answers waiting"))
    return out


def ask(opts, verb):
    print("Stopped - %d courses in preparation could be this course, and nothing is merged or guessed. Ask the user which "
          "one to use (read them the list), then run again with their choice:" % len(opts))
    print("\n".join(option_lines(opts)))
    print("  Choose with: course_portal.py %s --course <course> --site <live|staging> [--course-id <id>]" % verb)
    print("  The choice is kept in portal.json (\"use\"), so it is not asked again; --site / --course-id changes it.")


def choose(course, p, site=None, course_id=None, verb="pull", must=False):
    """The course in preparation this run works on: (option, 0), or (None, code) - 0 nothing waiting anywhere, 2 the
    choice is the user's (the list is printed), 3 no site could be reached. must: a push, which needs one even with
    nothing waiting."""
    use = p.get("use") if not (site or course_id) else None
    notes, failed, flagged = [], {}, bool(site or course_id)
    if use and use.get("site") in SITES:
        opts, notes, failed = gather(p, [use["course_id"]], use["site"])
        if opts:
            return opts[0], 0
        if failed:
            print("\n".join("  note: " + n for n in notes))
            return None, 3
        print("  note: the saved choice (%s, %s) is not in preparation any more - looking again." % (use["site"], use["course_id"]))
        p.pop("use", None)
    opts, notes, failed = gather(p, [course_id] if course_id else family_ids(course, p), site, course_id)
    for n in notes:
        print("  note: " + n)
    if not opts:
        if failed:
            return None, 3
        print("Stopped - no course in preparation was found for this course%s." % (" on the %s site" % site if site else ""))
        return None, 2
    if flagged:
        if len(opts) > 1:
            ask(opts, verb)
            return None, 2
        o = opts[0]
        p["use"] = {"site": o["site"], "course_id": o["course_id"]}
        if o["site"] not in p["sites"]:
            add_site(p, o["site"], {"id": o["course_id"], "title": o["title"]})
        save_portal(course, p)
        print("Using %s, %s (kept in portal.json)." % (o["site"], o["course_id"]))
        return o, 0
    busy = [o for o in opts if o["waiting"]]
    if len(opts) == 1:
        return opts[0], 0
    if len(busy) == 1:
        o = busy[0]
        print("Using %s, %s - the only one of %d possible courses with answers waiting." % (o["site"], o["course_id"], len(opts)))
        return o, 0
    if not busy and not must:
        print("Nothing is waiting in the editor (%d courses in preparation could be this course)." % len(opts))
        return None, 0
    ask(opts, verb)
    return None, 2


# ------------------------------------------------------------------ push
def cmd_push_pedagogy(course, site=None, course_id=None):
    p = _need_portal(course)
    if not p:
        return 2
    probs, _ = pr.check(course)
    if probs:
        print("Stopped - the pedagogy is not ready for the experts (pedagogy_review.py check):")
        for x in probs[:20]:
            print("  - " + x)
        return 2
    use = p.get("use") if not (site or course_id) else None
    if use and use.get("site") in p["sites"]:
        site, cid = use["site"], use["course_id"]
    elif not (site or course_id) and len(p["sites"]) == 1:
        site = sites_of(p)[0]
        cid = p["sites"][site]["course_id"]
    else:
        o, code = choose(course, p, site, course_id, "push --pedagogy", must=True)
        if not o:
            return code or 2
        site, cid = o["site"], o["course_id"]
    v = pr.view(course)
    register(cid, course)
    r = call(site, "push", course_id=cid, kind="pedagogy", content=v["content"], items=v["items"], fingerprint=v["fingerprint"],
             carried=carried(course, v))
    if r.get("unchanged"):
        print("Nothing new: the %s editor already has these words (version %d)." % (site, r["document"]["version"]))
    else:
        print("Sent to the %s editor: the pedagogy, version %d - %d rows, %d answers kept from before."
              % (site, r["document"]["version"], r.get("rows", 0), r.get("answers_kept", 0)))
    print("  The experts' link: %s" % editor_link(site, cid))
    return 0


def carried(course, v):
    """[{id, item}] - the answers the factory carried out (a Take proposed, a Keep as now, a decision with Claude, a
    task the expert wrote) on rows whose words are still what carrying them out made them: the editor keeps each as the
    row's answer on the new version, so the expert is not asked again what they decided. A row the factory changed
    since is asked again."""
    rev = pr._load(pr.files(course)["review"], {}) or {}
    return [{"id": i, "item": c["item"]} for i, c in sorted((rev.get("carried") or {}).items())
            if isinstance(c, dict) and v["items"].get(c.get("item")) == c.get("hash")]


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
    for m in v["review"]["modules"]:
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
        older = " (on words sent before)" if v["items"].get(a["item"], v["review_items"].get(a["item"])) != a.get("item_hash") else ""
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
            if d["choice"] == "keep" and "verb" in d:
                # the outcomes form's Keep original: the outcome's own words and the level they ask (2026-11-23)
                lvl = int(d.get("level") or 0) or (now.get("level") if isinstance(now.get("level"), int) else None)
                pr.carry_out(row, lvl, d.get("said") or "Keep the original wording and level.", _who(a),
                             how=(row.get("proposed") or {}).get("how") or "", decision="keep", keep_codes=d.get("keep_codes"))
                row["proposed"].pop("revised_outcome", None)
                what = "the original wording kept, at %s" % pr.level(lvl)
            elif d["choice"] == "keep":
                lvl = now.get("level") if isinstance(now.get("level"), int) and now.get("level") >= 1 else d.get("level")
                pr.carry_out(row, lvl, d.get("said") or "Keep it as the old course teaches it.", _who(a),
                             how="Kept as the old course teaches it: " + (now.get("how") or ""))
                what = "kept as the old course, at %s" % pr.level(lvl)
            else:
                # the elevation method (2.142.0): a re-wording the expert took is a raise; the same words at the same
                # level is a keep, with the keep codes the editor's Regenerate named
                pr.carry_out(row, int(d["level"]), d.get("said") or "", _who(a), how=d.get("how") or "", why=d.get("why") or None,
                             decision="raise" if (d.get("revised_outcome") or "").strip() and not topic_of[a["item"]][2] else
                             "keep" if d.get("keep_codes") else None, keep_codes=d.get("keep_codes"))
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
        note = (a.get("note") or "").strip()
        own_task = note[5:].strip() if a["verdict"] == "ok" and about is None and a["item"] in topic_of and note.lower().startswith("task:") else ""
        if own_task:
            # 2.142.1 (the pedagogy lead, 2026-11-24: "accept the raise and its level, but the task is bad - let me fix
            # only the task"): the editor sends it as OK with a note that starts "Task: ". The outcome and its level
            # stand as proposed (taken above); the row's task becomes the expert's own words, at once - nothing is left
            # to do, so the note is recorded as done. The checks of the task then only warn (pedagogy_review.py).
            row.setdefault("proposed", {}).update(how=own_task, task_expert={"by": _who(a), "on": base["on"]})
            row["expert_notes"].append(dict(base, said=note + older, done="The task is now your words."))
            log.append((where, "%s [%s, editor mode]" % (note, _who(a)), "the task replaced by the expert's words"))
        # "take it / keep it, with a note on what to fix": the note is carried out like any other
        elif a["verdict"] in ("ok", "decision") and (a.get("note") or "").strip():
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
    # 2.142.2 - what carrying the answers out made of each row: while the row stays so, the answer stands on the next
    # version (an expert who fixed a task does not see it come back unanswered). The same record and the same words as
    # the branch claude/expert-answers (2.138.0), so the two merge as one.
    v2 = pr.view(course)
    done = rev.setdefault("carried", {})
    for a in answers:
        if a["id"] in took and a["verdict"] in ("ok", "decision") and a["item"] in v2["items"]:
            done[a["id"]] = {"item": a["item"], "hash": v2["items"][a["item"]]}
    _save(f["review"], rev)
    return took, docs, log, said


class _PullLock:
    """One pull at a time in a course: the module builds of a parallel build each pull first, and two taking the same
    answers would log them twice."""

    def __init__(self, course):
        self.path = workspace.claude_path(course, "portal_pull.lock")

    def __enter__(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        t0 = time.time()
        while True:
            try:
                os.close(os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
                return self
            except FileExistsError:
                if time.time() - os.path.getmtime(self.path) > 600 or time.time() - t0 > 120:
                    return self                   # a lock left by a run that died: go on
                time.sleep(0.5)

    def __exit__(self, *a):
        try:
            os.remove(self.path)
        except OSError:
            pass


def cmd_pull(course, site=None, course_id=None):
    p = _need_portal(course)
    if not p:
        return 2
    with _PullLock(course):
        return _pull(course, p, site, course_id)


def _pull(course, p, site, course_id):
    opt, code = choose(course, p, site, course_id, "pull")
    if not opt:
        return code
    site, cid, r = opt["site"], opt["course_id"], opt["r"]
    answers = [a for a in r.get("answers") or [] if a["kind"] == "pedagogy"]
    ready = [d for d in r.get("ready") or [] if d["kind"] == "pedagogy"]
    took, docs, log, said = pull_pedagogy(course, answers, ready)
    later = len(r.get("answers") or []) - len(answers) + len(r.get("ready") or []) - len(ready)
    logged = _feedback(course, log)
    if took or docs:
        call(site, "ack", course_id=cid, answer_ids=took, document_ids=docs, read_at=r.get("read_at"))
    kinds = [a["verdict"] if a["verdict"] != "decision" else (a.get("decision") or {}).get("choice") for a in answers if a["id"] in took]
    n_change = kinds.count("change")
    print("Taken from the %s editor (%s): %d answer(s) - %d OK, %d kept as now, %d decided with Claude, %d asking for a change%s."
          % (site, cid, len(took), kinds.count("ok"), kinds.count("keep"), kinds.count("claude"), n_change,
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
    use = p.get("use") or {}
    bad = 0
    for s in sites_of(p):
        cid = p["sites"][s]["course_id"]
        try:
            r = call(s, "status", course_id=cid)
        except PortalError as e:
            print("%s site: %s (%s) not looked at - %s" % (s, p["sites"][s]["title"], cid, e))
            bad += 1
            continue
        c = r["course"]
        print("%s site - %s (%s) - %s%s\n  %s" % (s, c["title"], c["id"], c["stage"],
                                                  " - the one the factory works on" if use.get("site") == s else "", editor_link(s, c["id"])))
        for d in r.get("documents") or []:
            t = d["tally"]
            what = "the pedagogy" if d["kind"] == "pedagogy" else "the script of %s" % d["module"]
            print("  %-24s version %d: %d of %d rows answered (%d OK, %d to change)%s" % (
                what, d["version"], t["answered"], t["rows"], t["ok"], t["change"],
                " - Ready, signed %s" % d["ready_by_name"] if d["status"] == "ready" else ""))
        if not r.get("documents"):
            print("  nothing sent yet: course_portal.py push --course <course> --pedagogy")
    return 3 if bad == len(p["sites"]) else 0


def cmd_remove(course, yes, site=None):
    p = _need_portal(course)
    if not p:
        return 2
    if not site and len(p["sites"]) > 1:
        print("Stopped - this course is on %s: say which to remove with --site." % " and ".join(sites_of(p)))
        return 2
    site = site or sites_of(p)[0]
    if site not in p["sites"]:
        print("Stopped - this course is not on the %s site." % site)
        return 2
    cid = p["sites"][site]["course_id"]
    if not yes:
        print("Stopped - this removes %s and every answer on it from the %s training app. Run again with --yes." % (cid, site))
        return 2
    call(site, "remove", course_id=cid)
    del p["sites"][site]
    if (p.get("use") or {}).get("site") == site:
        p.pop("use")
    if p["sites"]:
        save_portal(course, p)
    else:
        os.remove(workspace.claude_path(course, FILE))
    print("Removed from the %s training app: %s." % (site, cid))
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


def claude_command(prompt):
    """The unattended run: edits are taken without asking inside the course folder (files outside it are refused),
    shell commands run, paid pictures and git push are refused. NOVIKONTAS_CLAUDE_CMD replaces the program (tests)."""
    exe = os.environ.get("NOVIKONTAS_CLAUDE_CMD")
    base = json.loads(exe) if exe else ["claude"]
    return base + ["-p", prompt, "--permission-mode", "acceptEdits", "--allowedTools", *ALLOWED, "--disallowedTools", *DENIED]


def modules_folder(course):
    m = os.path.join(course, "modules")
    return m if os.path.isfile(os.path.join(m, "COURSE.html")) else None


def cmd_import(course, pending=(), accepted=()):
    """pending: the picture spaces still to fill; accepted: the walk-review fails the operator let stand - both go into
    the draft's notes, so whoever opens the draft sees what it carries"""
    p = _need_portal(course)
    if not p:
        return 2, None
    if "staging" not in p["sites"]:
        print("Stopped - the importer reaches the staging training app only, and this course is not on staging "
              "(course_portal.py link --course <course> --site staging).")
        return 2, None
    p = {"course_id": p["sites"]["staging"]["course_id"]}
    folder = modules_folder(course)
    if not folder:
        print("Stopped - there is no built course to import: modules\\COURSE.html is missing.")
        return 2, None
    node = json.loads(os.environ["NOVIKONTAS_NODE"]) if os.environ.get("NOVIKONTAS_NODE") else ["node"]
    notes = (["Pictures pending: %d picture space(s) still hold a Phase A placeholder - fill them and import again before "
              "this draft is published" % len(pending)] + list(pending)[:40]) if pending else []
    if accepted:
        notes += ["Walk review: %d fail(s) nobody fixed - the operator accepted them as they are" % len(accepted)] + list(accepted)[:40]
    run =subprocess.run(node + [os.path.join(HERE, "course_import.mjs"), folder, p["course_id"]], capture_output=True,
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
        # only the course package (a --no-course-pages build: the workflow's pass) is let through - 2.125.0: a build
        # that also failed something else ("course package, task pages") is a failed build
        why = said[-1].split(" - ", 1)[-1].split(" (")[0].strip() if said else ""
        if said and said[-1].startswith("FAIL ") and why != "course package":
            out.append("%s - its last build did not pass" % said[-1][:120])
    return out


def _walked(course):
    """-> (walk_review, the work folder, the numbers of the module folders that hold a deck - the final assessment's
    folder among them: walk_review knows it by its deck)"""
    work = workspace.work_folder(course, create=False)
    mods = os.path.join(work, "modules")
    measure = os.path.join(os.path.dirname(os.path.dirname(HERE)), "course-module-ux", "measure", "scripts")
    if measure not in sys.path:
        sys.path.insert(0, measure)
    import walk_review
    import re
    if not os.path.isdir(mods):
        return walk_review, work, []
    nums = sorted({int(m.group(1)) for d in os.listdir(mods) for m in [re.match(r"(?:module|M|m)(\d+)", d)] if m})
    return walk_review, work, [n for n in nums if walk_review.deck_file(work, n)]


def walk_problems(course):
    """the walk review (walk_review.py) of every built module with a deck, the final assessment too: missing, stale,
    incomplete or failing stops the upload. -> ["walk review missing for M03 - ...", ...]"""
    walk_review, work, nums = _walked(course)
    out = []
    for n in nums:
        ok, _kind, msg = walk_review.verify(work, n)
        if not ok:
            out.append(msg)
    return out


def walk_accepted(course):
    """the walk-review fails the operator let stand, one line each with its module - what goes up with a fail nobody
    fixed. -> ["M01 s04 - stop 3: ... - accepted by <who>, <date> (<how>): <why>", ...]"""
    walk_review, work, nums = _walked(course)
    return ["%s %s" % (walk_review.mid(walk_review.canon(work, n)), x) for n in nums for x in walk_review.accepted(work, n)]


def _stop_message(site, cid, why):
    """the editor's 'Build stopped' message replaced by the course's state now - only where one is shown: a course
    waiting in the queue without one would be held back by it"""
    c = call(site, "status", course_id=cid).get("course") or {}
    if c.get("stage") == "build_requested" and c.get("build_error"):
        call(site, "build-done", course_id=cid, error=why)
        return True
    return False


def cmd_upload(course):
    """after an attended build, or a rebuild (fix.py rebuild ends with this): once nothing but picture spaces still to
    fill stops it, the built course goes into the staging editor as a draft and the editor's old stop message goes with
    it (the import marks the course built); while something else stops it, the stop message says what, today. Unasked."""
    p = portal(course)
    if not p or not p["sites"]:
        print("Not uploaded - this course is not in the training app (course_portal.py create).")
        return 0
    if "staging" not in p["sites"]:
        print("Not uploaded - the importer reaches the staging training app only, and this course is not on staging "
              "(course_portal.py link --course <course> --site staging).")
        return 0
    if os.environ.get("NOVIKONTAS_AUTO_BUILD") == "1":
        print("Not uploaded yet - this is the unattended build: the watch uploads it when the run ends.")
        return 0
    pics, other = blockers(course)
    other = other + walk_problems(course)              # no upload without the walk review of every built module
    if other:
        why = "Not uploaded after the session of %s - %d thing(s) still stop it: %s" % (
            date.today().isoformat(), len(other), "; ".join(other[:3]) + (" ..." if len(other) > 3 else ""))
        print(why)
        if _stop_message("staging", p["sites"]["staging"]["course_id"], why[:2000]):
            print("  The editor's stop message now says this.")
        return 1
    let = walk_accepted(course)
    if let:
        print("Going up with %d walk-review fail(s) nobody fixed - the operator accepted them:" % len(let))
        print("\n".join("  " + x for x in let))
    return cmd_import(course, pics, let)[0]


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
    site = cid = None
    try:
        queued, down = [], 0
        for s in ORDER:
            try:
                c = call(s, "build-next").get("course")
            except PortalError as e:
                _log("the queue was not looked at - %s" % e)
                down += 1
                continue
            if c:
                queued.append((c.get("build_requested_at") or "", ORDER.index(s), s, c))
        if not queued:
            return 3 if down == len(ORDER) else 0
        _, _, site, nxt = sorted(queued, key=lambda q: q[:2])[0]
        cid = nxt["id"]
        course = folder_of(cid)
        if not course:
            call(site, "build-done", course_id=cid, error="The office PC does not know this course's folder. Open the course's "
                 "factory session once and run course_portal.py push.")
            _log("%s (%s): no folder on this PC" % (cid, site))
            return 2
        have = portal(course) or {"sites": {}}
        if (have["sites"].get(site) or {}).get("course_id") != cid:
            call(site, "build-done", course_id=cid, error="The office PC knows this course's folder, but not as the course %s on "
                 "the %s site (portal.json). Run course_portal.py link --course <course> --site %s --course-id %s, then start "
                 "the build again." % (cid, site, site, cid))
            _log("%s (%s): the folder is not linked to this site's course" % (cid, site))
            return 2
        call(site, "build-claim", course_id=cid)
        _log("%s (%s): building in %s" % (cid, site, course))
        have["use"] = {"site": site, "course_id": cid}          # the build's own pulls go where its Ready was pressed
        save_portal(course, have)
        cmd_pull(course, site, cid)
        expert = nxt.get("build_requested_by") or "the expert"
        logdir = workspace.claude_path(course, "auto_build")
        os.makedirs(logdir, exist_ok=True)
        logf = os.path.join(logdir, datetime.now().strftime("%Y%m%d-%H%M") + ".log")
        prompt = AUTO_PROMPT.format(title=nxt.get("title") or cid, course_id=cid, expert=expert)
        env = dict(os.environ, NOVIKONTAS_AUTO_BUILD="1")
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
                call(site, "build-done", course_id=cid, error=why)
                _log("%s (%s): stopped - %s" % (cid, site, why))
                return 2
        if site != "staging":
            call(site, "build-done", course_id=cid, error="The course is built on the office PC, but the importer reaches the "
                 "staging site only, so it is not in this editor yet.")
            _log("%s (%s): built; the importer reaches staging only" % (cid, site))
            return 2
        code, r = cmd_import(course, pics)
        if code:
            call(site, "build-done", course_id=cid, error="built, but the import failed: %s" % ((r or {}).get("error") or "see the log"))
            _log("%s (%s): import failed" % (cid, site))
            return 2
        _log("%s (%s): built and imported as draft %s%s" % (cid, site, ((r or {}).get("release") or {}).get("version"),
                                                             " - pictures pending: %d" % len(pics) if pics else ""))
        return 0
    except PortalError as e:
        _log("stopped: %s" % e)
        return 3
    except subprocess.TimeoutExpired:
        call(site, "build-done", course_id=cid, error="the build ran for 20 hours and was stopped")
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
    s.add_argument("--site", choices=ORDER, default="live")
    sub.add_parser("install-task")
    s = sub.add_parser("watch")
    s.add_argument("--once", action="store_true", required=True)
    for name in ("create", "link", "push", "pull", "status", "remove", "import", "upload"):
        s = sub.add_parser(name)
        s.add_argument("--course", required=True)
        if name in ("create", "link"):
            s.add_argument("--site", choices=ORDER, default=None if name == "link" else "live", required=name == "link")
        if name in ("push", "pull", "remove"):
            s.add_argument("--site", choices=ORDER)
        if name in ("push", "pull", "link"):
            s.add_argument("--course-id")
        if name == "create":
            s.add_argument("--title")
        if name == "push":
            s.add_argument("--pedagogy", action="store_true", required=True)
        if name == "remove":
            s.add_argument("--yes", action="store_true")
    x = ap.parse_args(argv)
    try:
        if x.cmd == "name":
            return cmd_name(x.title, x.site)
        if x.cmd == "watch":
            return cmd_watch_once()
        if x.cmd == "install-task":
            return cmd_install_task()
        course = workspace.work_folder(x.course)
        if os.environ.get("NOVIKONTAS_TRIAL") == "1" or os.path.isfile(os.path.join(workspace.master_of(course), "FACTORY_TRIAL.json")):
            print("Stopped - this is a factory trial (factory_trial.py): a trial never goes to the training app")
            return 2
        if x.cmd == "create":
            return cmd_create(course, x.title, x.site)
        if x.cmd == "link":
            return cmd_link(course, x.site, x.course_id)
        if x.cmd == "push":
            return cmd_push_pedagogy(course, x.site, x.course_id)
        if x.cmd == "pull":
            return cmd_pull(course, x.site, x.course_id)
        if x.cmd == "status":
            return cmd_status(course)
        if x.cmd == "import":
            return cmd_import(course)[0]
        if x.cmd == "upload":
            return cmd_upload(course)
        return cmd_remove(course, x.yes, x.site)
    except PortalError as e:
        print("Stopped - %s" % e)
        return 3


if __name__ == "__main__":
    sys.exit(main())
