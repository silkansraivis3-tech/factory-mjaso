# -*- coding: utf-8 -*-
"""test_project_work - a course's project work: the cards, their approval, their Drive links and the package's
classroom\\projects.json (project_work.py, 2.134.0). A course without project work gets nothing.

    python test_project_work.py
"""
from __future__ import annotations

import io
import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import project_work as pw  # noqa: E402

PASSED, FAILED = [], []


def check(name, ok, detail=""):
    (PASSED if ok else FAILED).append(name)
    print("  %s  %s%s" % ("ok  " if ok else "FAIL", name, "" if ok else "  -> %r" % (detail,)))


def html(title, blocks):
    return "<html><title>%s</title>%s</html>" % (title, json.dumps(blocks))


def run(*argv):
    return pw.main(list(argv))


def fill(course):
    doc = pw.load(course)
    for p in doc["projects"]:
        p["title"] = "Network upgrade " + p["code"]
        p["card"] = {"situation": "The ship's office network is old.", "task": ["Survey it.", "Plan the change."],
                     "data": ["The ship data pack, IT annex"], "deliverables": ["The project file"]}
    pw.save(course, doc)


def main():
    tmp = tempfile.mkdtemp()
    try:
        course = os.path.join(tmp, "course")
        os.makedirs(os.path.join(course, "working_claude"))
        os.makedirs(os.path.join(course, "modules"))
        root = os.path.join(course, "additional-materials")

        print("a course with no project work")
        check("no project_work.json: no project work", pw.load(course) is None)
        check("no project_work.json: nothing written", pw.files(course, "Course", root, html) == [])
        check("no project_work.json: the package check has nothing to say", pw.package_problems(os.path.join(course, "modules")) == [])
        check("no project_work.json: check says so and passes", run("check", course) == 0)

        print("init")
        check("init needs the departments", run("init", course, "--departments", " ") == 1)
        check("init writes the cards", run("init", course, "--departments", "Deck,Engine", "--codes", "D1-D4,E1-E4") == 0)
        doc = pw.load(course)
        codes = [(p["code"], p["department"]) for p in doc["projects"]]
        check("D1-D4 for Deck, E1-E4 for Engine", codes == [("D%d" % i, "Deck") for i in range(1, 5)] + [("E%d" % i, "Engine") for i in range(1, 5)], codes)
        check("max 3 teams a card by default", doc["max_per_project"] == 3)
        check("init never starts it again (L9)", run("init", course, "--departments", "Deck") == 1)
        check("without --codes: four a department", [c for c, _ in pw.codes_from("", ["Deck", "Engine"])] == ["D1", "D2", "D3", "D4", "E1", "E2", "E3", "E4"])

        print("draft")
        check("empty cards are notes, not problems", pw.problems(doc) == [] and any("D1" in n and "title" in n for n in pw.notes(doc)), pw.notes(doc))
        check("empty cards cannot be approved", run("approve", course, "--by", "A Person") == 1)
        fill(course)
        out = pw.files(course, "Information Technology", root, html)
        kinds = sorted(set(k for _, k, _ in out))
        check("each card as PDF and Word, in additional-materials\\project-cards", len(out) == 16 and kinds == ["docx", "pdf"]
              and all("project-cards" in p for p, _, _ in out), [os.path.relpath(p, course) for p, _, _ in out])
        check("a draft card says DRAFT", any(b[0] == "small" and "DRAFT" in b[1] for b in out[1][2]), out[1][2])
        check("no projects.json before approval", not any(p.endswith("projects.json") for p, _, _ in out))

        print("approval")
        check("filled cards are approved", run("approve", course, "--by", "A Person") == 0)
        doc = pw.load(course)
        check("approved", pw.approved(doc))
        out = pw.files(course, "Information Technology", root, html)
        pj = [t for p, k, t in out if p.endswith(os.path.join("modules", "classroom", "projects.json"))]
        check("the package gets classroom\\projects.json", len(pj) == 1)
        cfg = json.loads(pj[0])
        check("projects.json carries code, department and title", cfg["projects"][0] == {"code": "D1", "department": "Deck", "title": "Network upgrade D1"}, cfg["projects"][0])
        check("no folder layout while a card has no Drive link", "folders" not in cfg)
        check("an approved card has no DRAFT", not any(b[0] == "small" for b in pw.card_blocks("C", doc, doc["projects"][0])))
        doc["projects"][0]["card"]["task"].append("Present it.")
        check("a card changed after approval is not approved", not pw.approved(doc) and pw.config(doc) is None)
        pw.save(course, doc)
        check("check names the stale approval", any("changed after" in n for n in pw.notes(doc)))
        run("approve", course, "--by", "A Person")

        print("Drive links")
        check("a link that is not Drive is refused", run("link", course, "--code", "D1", "--brief", "not a link") == 1)
        check("an unknown card is refused", run("link", course, "--code", "X9", "--brief", "1AbCdEfGhIjKlMnOpQrStUv") == 1)
        for i, p in enumerate(pw.load(course)["projects"]):
            run("link", course, "--code", p["code"], "--brief", "https://docs.google.com/document/d/1AbCdEfGhIjKlMn%02d/edit" % i)
        doc = pw.load(course)
        check("links do not undo the approval", pw.approved(doc))
        cfg = pw.config(doc, "Information Technology")
        check("the brief is the Drive id", cfg["projects"][0]["brief"] == "1AbCdEfGhIjKlMn00", cfg["projects"][0])
        check("every card linked: one folder with the team's card", cfg["folders"]["layout"][0]["items"][0]["copy"] == "brief")
        check("check passes when all is done", run("check", course) == 0 and pw.notes(doc) == [], pw.notes(doc))
        doc["folders"] = {"group": "IT - {group}", "trainee": "{name}", "layout": [{"name": "", "items": [{"copy": "brief", "name": "Card"}]}]}
        check("the course's own folder layout wins", pw.config(doc)["folders"]["group"] == "IT - {group}")

        print("the package check (the app's rules)")
        mf = os.path.join(course, "modules")
        os.makedirs(os.path.join(mf, "classroom"), exist_ok=True)
        pp = os.path.join(mf, "classroom", "projects.json")
        io.open(pp, "w", encoding="utf-8").write(json.dumps(pw.config(pw.load(course))))
        check("what the factory writes passes", pw.package_problems(mf) == [], pw.package_problems(mf))
        import classroom_files as cf
        check("classroom_files' package check runs it", cf.folder_problems(mf, ["module01"]) == [], cf.folder_problems(mf, ["module01"]))
        bad = {"max_per_project": 0, "projects": [{"code": "d 1", "department": "Deck"}, {"code": "E1"}, {"code": "E1", "department": "Engine", "brief": "x"}]}
        io.open(pp, "w", encoding="utf-8").write(json.dumps(bad))
        probs = pw.package_problems(mf)
        check("a wrong max, code, missing department, double code and bad link are named",
              all(any(w in p for p in probs) for w in ("max_per_project", "letters or digits", "no \"department\"", "used twice", "Google Drive")), probs)
        io.open(pp, "w", encoding="utf-8").write("{not json")
        check("broken JSON is named", pw.package_problems(mf) == ["classroom/projects.json is not valid JSON"])
        check("drive_id reads ids and links", pw.drive_id("https://drive.google.com/file/d/1AbCdEfGhIjK/view") == "1AbCdEfGhIjK"
              and pw.drive_id("https://drive.google.com/open?id=1AbCdEfGhIjK") == "1AbCdEfGhIjK" and pw.drive_id("short") == "")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("\n%d passed, %d failed" % (len(PASSED), len(FAILED)))
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
