# -*- coding: utf-8 -*-
"""project_work - a course's project work for the tablet app's group page: the project cards a group draws, each team's
card as a trainee document, and the classroom\\projects.json the app reads when the course is published (2.134.0).

ONLY A COURSE WITH PROJECT WORK HAS IT. A course has project work when its working_claude\\project_work.json exists
(made by `init`, at Stage 2 when the architecture has a project module with cards to draw - Project Management,
Information Technology). Every other course: this script writes nothing and checks nothing, and the package has no
projects.json.

What the app does with it (training app, migration 039, admin/classroom/shared/project-work.mjs): the group page's
Projects tab - "Draw projects" gives each team one card of its department's list, no card to more than
max_per_project teams; "Create trainee folders" makes each trainee's Google Drive folder with a copy of the team's
card ("brief") and whatever the folder layout lists. So with the course imported, the instructor only adds the
instructor and the trainees, sets each team's department, and presses Draw and Create folders.

    working_claude\\project_work.json
      {"title": "Course project", "max_per_project": 3,
       "projects": [{"code": "D1", "department": "Deck", "title": "...",
                     "card": {"situation": "...", "task": ["..."], "data": ["..."], "deliverables": ["..."]},
                     "brief": "<Google Drive link of the card, once uploaded>"}, ...],
       "folders": {...}            optional - the app's own layout; without it the factory gives one folder with the card
       "approved": {"by", "date", "hash"}}    set by `approve`; a card changed after it needs approving again

The cards are course content (L18, L26): written from the course's sources and brief, checked by the experts the course
names, approved by the operator. Until approved, the cards are rendered with DRAFT on them and no projects.json is
written. A card's Drive link is added after the card's Word file is uploaded to Drive (`link`) - the Drive upload is the
operator's (a file put on Drive is shared outside the PC); without the links the app still draws, and its folders hold no
card copy.

    python project_work.py init <course> --departments Deck,Engine [--codes D1-D4,E1-E4] [--max 3] [--title "..."]
    python project_work.py check <course>
    python project_work.py link <course> --code D1 --brief <Drive link or file id>
    python project_work.py approve <course> --by "<name>"
"""
from __future__ import annotations

import datetime
import hashlib
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import workspace  # noqa: E402

FILE = "project_work.json"
PACKAGE_PATH = "classroom/projects.json"           # in the course's modules folder, beside prepare.json
CARDS_DIR = "project-cards"                        # in additional-materials
CODE_RE = re.compile(r"^[A-Z0-9][A-Z0-9_.-]{0,11}$")
DRIVE_RE = (re.compile(r"/(?:d|folders)/([-\w]{10,})"), re.compile(r"[?&]id=([-\w]{10,})"))
LIMITS = {"projects": 40, "max_per_project": 20, "text": 160, "department": 40}   # the app's own (PW_LIMITS)
CARD_FIELDS = (("situation", "The situation"), ("task", "Your task"), ("data", "What you work with"),
               ("deliverables", "What you hand in"))
DEFAULT_FOLDERS = {"group": "{course} - {group}", "trainee": "{name} - {course}",
                   "layout": [{"name": "1 My project", "items": [{"copy": "brief", "name": "Your project card - {project} {project_title}"}]}]}


# ------------------------------------------------------------------ reading
def path_of(course):
    return workspace.claude_path(course, FILE)


def load(course):
    """the course's project work, or None - a course without project_work.json has none"""
    p = path_of(course)
    if not os.path.isfile(p):
        return None
    try:
        with io.open(p, encoding="utf-8") as f:
            d = json.load(f)
    except ValueError:
        return {"_broken": True}
    return d if isinstance(d, dict) else {"_broken": True}


def save(course, doc):
    with io.open(path_of(course), "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
        f.write("\n")


def clean(v, n=LIMITS["text"]):
    return re.sub(r"\s+", " ", str(v if v is not None else "")).strip()[:n]


def drive_id(v):
    """a Drive id from an id or any Drive / Docs link - the app's driveId()"""
    s = str(v if v is not None else "").strip()
    for rx in DRIVE_RE:
        m = rx.search(s)
        if m:
            return m.group(1)
    return s if re.match(r"^[-\w]{10,}$", s) else ""


def lines(v):
    if isinstance(v, list):
        return [clean(x, 2000) for x in v if clean(x, 2000)]
    t = clean(v, 4000)
    return [t] if t else []


def cards_hash(doc):
    """what an approval covers: every card's code, department, title and words (not the Drive links)"""
    keep = [{"code": p.get("code"), "department": p.get("department"), "title": p.get("title"), "card": p.get("card")}
            for p in doc.get("projects") or [] if isinstance(p, dict)]
    keep.append({"max": doc.get("max_per_project"), "title": doc.get("title")})
    return hashlib.sha256(json.dumps(keep, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()[:16]


def approved(doc):
    a = (doc or {}).get("approved") or {}
    return bool(a.get("by")) and a.get("hash") == cards_hash(doc)


# ------------------------------------------------------------------ the app's rules (project-work.mjs readProjectWork)
def problems(doc):
    """[problem] that would make the app refuse the project work - the course's file or the package's projects.json"""
    if doc is None:
        return []
    if doc.get("_broken"):
        return ["%s is not valid JSON" % FILE]
    probs = []
    mx = doc.get("max_per_project", 3)
    if not isinstance(mx, int) or isinstance(mx, bool) or not 1 <= mx <= LIMITS["max_per_project"]:
        probs.append('"max_per_project" must be a whole number from 1 to %d' % LIMITS["max_per_project"])
    lst = doc.get("projects") if isinstance(doc.get("projects"), list) else []
    if not lst:
        probs.append('add at least one project to "projects"')
    if len(lst) > LIMITS["projects"]:
        probs.append("at most %d projects" % LIMITS["projects"])
    seen = set()
    for i, p in enumerate(lst[:LIMITS["projects"]], 1):
        p = p if isinstance(p, dict) else {}
        code = clean(p.get("code"), 12).upper()
        where = "project %d%s" % (i, " (%s)" % code if code else "")
        if not CODE_RE.match(code):
            probs.append("%s: the code must be 1-12 letters or digits, for example D1" % where)
            continue
        if code in seen:
            probs.append("%s: the code %s is used twice" % (where, code))
        seen.add(code)
        if not clean(p.get("department"), LIMITS["department"]):
            probs.append('%s: no "department"' % where)
        if p.get("brief") and not drive_id(p["brief"]):
            probs.append('%s: "brief" is not a Google Drive file link or id' % where)
    f = doc.get("folders")
    if f is not None and not isinstance(f, dict):
        probs.append('"folders" must be an object (the app\'s folder layout)')
    return probs


def notes(doc):
    """[note] - what is still to do before the project work is complete; never stops a build"""
    if not doc or doc.get("_broken"):
        return []
    out = []
    for p in doc.get("projects") or []:
        if not isinstance(p, dict):
            continue
        code = clean(p.get("code"), 12).upper() or "?"
        card = p.get("card") if isinstance(p.get("card"), dict) else {}
        missing = [label for k, label in CARD_FIELDS if not lines(card.get(k))]
        if not clean(p.get("title")):
            missing.insert(0, "a title")
        if missing:
            out.append("project card %s has no %s yet" % (code, ", ".join(m.lower() for m in missing)))
    if not approved(doc):
        out.append("the project cards are not approved (project_work.py approve --by) - they carry DRAFT and the "
                   "package gets no projects.json" if not (doc.get("approved") or {}).get("by") else
                   "a project card changed after its approval - approve again (project_work.py approve --by)")
    unlinked = [clean(p.get("code"), 12).upper() for p in doc.get("projects") or [] if isinstance(p, dict) and not p.get("brief")]
    if unlinked:
        out.append("no Google Drive link yet for the card(s) %s - upload the Word file and run project_work.py link: "
                   "until then the app draws the cards but its trainee folders hold no card" % ", ".join(unlinked))
    return out


# ------------------------------------------------------------------ what goes into the package
def config(doc, course_title=""):
    """the app's project work (classroom\\projects.json) - None until the cards are approved"""
    if not doc or doc.get("_broken") or problems(doc) or not approved(doc):
        return None
    projects = []
    for p in doc.get("projects") or []:
        x = {"code": clean(p["code"], 12).upper(), "department": clean(p["department"], LIMITS["department"]),
             "title": clean(p.get("title")) or clean(p["code"], 12).upper()}
        if p.get("brief"):
            x["brief"] = drive_id(p["brief"])
        projects.append(x)
    out = {"title": clean(doc.get("title"), 60) or "Project work", "max_per_project": doc.get("max_per_project", 3),
           "projects": projects}
    if isinstance(doc.get("folders"), dict):
        out["folders"] = doc["folders"]
    elif projects and all(x.get("brief") for x in projects):
        out["folders"] = json.loads(json.dumps(DEFAULT_FOLDERS))
    return out


def card_blocks(course_title, doc, p):
    """one project card as the additional materials' blocks (to_html / to_docx)"""
    code = clean(p.get("code"), 12).upper()
    card = p.get("card") if isinstance(p.get("card"), dict) else {}
    out = [("h1", "%s - %s" % (code, clean(p.get("title"), 300) or code)),
           ("facts", [("Course", course_title), ("Department", clean(p.get("department"), LIMITS["department"])),
                      ("Card", code)])]
    if not approved(doc):
        out.append(("small", "DRAFT - not yet checked and approved; do not hand out."))
    for k, label in CARD_FIELDS:
        got = lines(card.get(k))
        if not got:
            continue
        out.append(("h2", label))
        if k == "situation" or len(got) == 1 and k != "task":
            out += [("p", x) for x in got]
        else:
            out.append(("ol" if k == "task" else "ul", got))
    return out


def files(course, title, root, to_html, probs=None):
    """[(path, kind, content)] for additional_materials.plan(): each card as PDF and Word in additional-materials\\
    project-cards, and the package's classroom\\projects.json once the cards are approved. [] for a course with no
    project work."""
    doc = load(course)
    if doc is None:
        return []
    bad = problems(doc)
    if probs is not None:
        probs += ["project work: %s" % x for x in bad]
    if doc.get("_broken"):
        return []
    out = []
    for p in doc.get("projects") or []:
        if not isinstance(p, dict) or not CODE_RE.match(clean(p.get("code"), 12).upper()):
            continue
        code = clean(p.get("code"), 12).upper()
        stem = "%s_%s" % (code, re.sub(r"[^A-Za-z0-9]+", "_", clean(p.get("title"), 50)).strip("_") or "card")
        blocks = card_blocks(title, doc, p)
        out.append((os.path.join(root, CARDS_DIR, "pdf", stem + ".pdf"), "pdf", to_html("%s - %s" % (code, clean(p.get("title"))), blocks)))
        out.append((os.path.join(root, CARDS_DIR, "docx", stem + ".docx"), "docx", blocks))
    cfg = config(doc, title)
    if cfg:
        out.append((os.path.join(course, workspace.MODULES, *PACKAGE_PATH.split("/")), "json",
                    json.dumps(cfg, ensure_ascii=False, indent=2) + "\n"))
    return out


def package_problems(folder):
    """[problem] of the package's classroom\\projects.json (none when the course has no project work)"""
    p = os.path.join(folder, *PACKAGE_PATH.split("/"))
    if not os.path.isfile(p):
        return []
    try:
        doc = json.load(io.open(p, encoding="utf-8"))
    except ValueError:
        return ["%s is not valid JSON" % PACKAGE_PATH]
    if not isinstance(doc, dict):
        return ["%s must be an object with \"projects\"" % PACKAGE_PATH]
    return ["%s: %s" % (PACKAGE_PATH, x) for x in problems(doc)]


# ------------------------------------------------------------------ the commands
def codes_from(spec, departments):
    """"D1-D4,E1-E4" -> [(D1, Deck) ...]; without --codes: four a department, its first letter and 1-4"""
    out = []
    if spec:
        for part, dept in zip(spec.split(","), departments + [departments[-1]] * 20):
            m = re.match(r"^\s*([A-Z]+)(\d+)\s*-\s*\1?(\d+)\s*$", part.strip().upper())
            if m:
                out += [("%s%d" % (m.group(1), n), dept) for n in range(int(m.group(2)), int(m.group(3)) + 1)]
            elif part.strip():
                out.append((part.strip().upper(), dept))
        return out
    for d in departments:
        out += [("%s%d" % (d[:1].upper(), n), d) for n in range(1, 5)]
    return out


def cmd_init(a):
    if load(a.course) is not None:
        print("project_work: %s already exists - edit it, never start it again (L9)" % path_of(a.course))
        return 1
    depts = [clean(x, LIMITS["department"]) for x in (a.departments or "").split(",") if clean(x)]
    if not depts:
        print("project_work: say the departments the cards are for: --departments Deck,Engine")
        return 1
    doc = {"title": a.title or "Course project", "max_per_project": a.max,
           "projects": [{"code": c, "department": d, "title": "", "card": {k: "" if k == "situation" else [] for k, _ in CARD_FIELDS},
                         "brief": ""} for c, d in codes_from(a.codes, depts)]}
    save(a.course, doc)
    print("project_work: %s - %d cards to write (title and card of each, from the course's sources and brief)"
          % (path_of(a.course), len(doc["projects"])))
    return 0


def cmd_check(a):
    doc = load(a.course)
    if doc is None:
        print("project_work: this course has no project work (no %s) - nothing to check" % FILE)
        return 0
    bad, todo = problems(doc), notes(doc)
    for x in bad:
        print("PROBLEM:", x)
    for x in todo:
        print("note:", x)
    if not bad and not todo:
        print("project_work: %d cards, approved, every card on Drive - the package carries projects.json"
              % len(doc.get("projects") or []))
    return 1 if bad else 0


def cmd_link(a):
    doc = load(a.course)
    if doc is None or doc.get("_broken"):
        print("project_work: no readable %s" % FILE)
        return 1
    did = drive_id(a.brief)
    if not did:
        print("project_work: %r is not a Google Drive file link or id" % a.brief)
        return 1
    for p in doc.get("projects") or []:
        if clean(p.get("code"), 12).upper() == a.code.upper():
            p["brief"] = "https://docs.google.com/document/d/%s/edit" % did if not a.brief.startswith("http") else a.brief.strip()
            save(a.course, doc)
            print("project_work: card %s linked to Drive file %s" % (a.code.upper(), did))
            return 0
    print("project_work: no card %s" % a.code.upper())
    return 1


def cmd_approve(a):
    doc = load(a.course)
    if doc is None or doc.get("_broken"):
        print("project_work: no readable %s" % FILE)
        return 1
    bad = problems(doc)
    empty = [x for x in notes(doc) if x.startswith("project card")]
    if bad or empty:
        for x in bad + empty:
            print("PROBLEM:", x)
        print("project_work: not approved - every card needs its title and words first")
        return 1
    doc["approved"] = {"by": a.by, "date": datetime.date.today().isoformat(), "hash": cards_hash(doc)}
    save(a.course, doc)
    print("project_work: %d cards approved by %s - the next course build writes classroom\\projects.json"
          % (len(doc.get("projects") or []), a.by))
    return 0


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("init")
    s.add_argument("course")
    s.add_argument("--departments", required=True)
    s.add_argument("--codes", default="")
    s.add_argument("--max", type=int, default=3)
    s.add_argument("--title", default="")
    s = sub.add_parser("check")
    s.add_argument("course")
    s = sub.add_parser("link")
    s.add_argument("course")
    s.add_argument("--code", required=True)
    s.add_argument("--brief", required=True)
    s = sub.add_parser("approve")
    s.add_argument("course")
    s.add_argument("--by", required=True)
    a = ap.parse_args(argv)
    a.course = os.path.abspath(a.course)
    return {"init": cmd_init, "check": cmd_check, "link": cmd_link, "approve": cmd_approve}[a.cmd](a)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
