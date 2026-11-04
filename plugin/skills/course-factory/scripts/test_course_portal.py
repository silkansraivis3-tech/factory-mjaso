# -*- coding: utf-8 -*-
"""test_course_portal - the experts review a course in preparation in the training app's editor.

    python test_course_portal.py

Against a stand-in for the course-prep function that keeps its rules (a name is taken by a course or by a course in
preparation; a row's answers count while its hash is the one sent; an answer sent again replaces the person's own;
pulled answers are not pulled again). Pinned:
  * name and create refuse a name already used - three courses with one name would become one in the app; create
    takes intake's course_name, writes working_claude/portal.json with the experts' link and never the key;
  * push --pedagogy is refused until pedagogy_review.py check is clean; it sends the same words as the Word files,
    a hash per row; sent again unchanged it makes no new version; a changed topic is answered again, the others keep
    their answers;
  * pull: OK -> the row's expert_review; needs change -> expert_notes and FEEDBACK_LOG.md, and check stops until
    its 'done' says what was changed; Ready -> pedagogy_review.json "ready", and render signs the documents with the
    expert's name; what was taken is acknowledged and not taken twice; an answer changed from "change" to OK takes
    its open note away;
  * the client knows only the staging project, and the key comes from the office PC, never from a course folder.
"""
from __future__ import annotations

import copy
import hashlib
import io
import json
import os
import re
import shutil
import sys
import tempfile
import uuid
import zipfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import course_portal as cp  # noqa: E402
import pedagogy_review as pr  # noqa: E402
import test_architecture_page as tap  # noqa: E402
import test_pedagogy_review as tpr  # noqa: E402

PASS, FAIL = [], []


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print(("  ok    " if ok else "  FAIL  ") + name + (("  -> " + str(detail)[:400]) if detail and not ok else ""))


def slug(t):
    return re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")


class Server:
    """The course-prep function's rules, in memory."""

    def __init__(self, courses=()):
        self.courses, self.preps, self.docs, self.answers, self.calls = set(courses), {}, [], [], []

    def __call__(self, action, p):
        self.calls.append((action, p))
        if action == "name-check":
            i = slug(p["title"])
            free = i not in self.courses and i not in self.preps
            return {"title": p["title"], "id": i, "free": free, **({} if free else {"why": "the id %s is used." % i})}
        if action == "create":
            i = slug(p["title"])
            if i in self.courses or i in self.preps:
                raise cp.PortalError("A course with this id (%s) exists." % i, 409)
            self.preps[i] = {"id": i, "title": p["title"], "stage": "pedagogy"}
            return {"course": self.preps[i]}
        if action == "push":
            was = [d for d in self.docs if d["course_id"] == p["course_id"] and d["kind"] == p["kind"]]
            if was and was[-1]["fingerprint"] == p["fingerprint"]:
                return {"document": {"version": was[-1]["version"]}, "unchanged": True}
            for d in was:
                d["status"] = "superseded"
            d = dict(id=str(uuid.uuid4()), course_id=p["course_id"], kind=p["kind"], module="", version=len(was) + 1,
                     items=p["items"], content=p["content"], fingerprint=p["fingerprint"], status="open")
            self.docs.append(d)
            kept = [a for a in self.answers if p["items"].get(a["item"]) == a["item_hash"]]
            return {"document": {"id": d["id"], "version": d["version"]}, "rows": len(p["items"]), "answers_kept": len(kept)}
        if action == "pull":
            return {"read_at": "2026-11-04T12:00:00Z", "answers": [dict(a) for a in self.answers if not a.get("pulled")],
                    "ready": [dict(d) for d in self.docs if d["status"] == "ready" and not d.get("ready_pulled")]}
        if action == "ack":
            for a in self.answers:
                if a["id"] in p["answer_ids"]:
                    a["pulled"] = True
            for d in self.docs:
                if d["id"] in p["document_ids"]:
                    d["ready_pulled"] = True
            return {"ok": True}
        if action == "status":
            return {"course": self.preps[p["course_id"]], "documents": []}
        if action == "remove":
            self.preps.pop(p["course_id"])
            return {"ok": True}
        raise AssertionError(action)

    # what an expert does in the editor
    def answer(self, who, item, verdict, note=None):
        d = self.docs[-1]
        mine = [a for a in self.answers if a["by_email"] == who and a["item"] == item and a["item_hash"] == d["items"][item]]
        if mine:
            mine[0].update(verdict=verdict, note=note, pulled=False)
            return mine[0]
        a = dict(id=str(uuid.uuid4()), kind="pedagogy", module="", item=item, item_hash=d["items"][item], verdict=verdict,
                 note=note, by_name=who.split("@")[0].replace(".", " ").title(), by_email=who, updated_at="2026-11-04T11:00:00Z")
        self.answers.append(a)
        return a

    def ready(self, name):
        self.docs[-1].update(status="ready", ready_by_name=name, ready_by_email="anna.liepa@novikontas.org",
                             ready_at="2026-11-04T11:30:00Z")


def out_of(fn, *a):
    buf, old = io.StringIO(), sys.stdout
    sys.stdout = buf
    try:
        code = fn(*a)
    finally:
        sys.stdout = old
    return code, buf.getvalue()


def main():
    tmp = tempfile.mkdtemp(prefix="portal_")
    try:
        arch = copy.deepcopy(tap.ARCH)
        c = tap.write_course(os.path.join(tmp, "course"), tap.PROGRAMME, arch)
        io.open(os.path.join(c, "FEEDBACK_LOG.md"), "w", encoding="utf-8").write(
            "| # | Date | Stage · module · where | said | changed | fact |\n|---|---|---|---|---|---|\n| 1 | | | | | no |\n")
        srv = Server(courses={"gas-basic"})
        cp.CALL = srv

        print("-- name and create")
        code, out = out_of(cp.cmd_name, "GAS BASIC")
        check("a name the training app already has is taken", code == 2 and "Taken" in out, out)
        code, out = out_of(cp.cmd_name, "GAS BASIC 3")
        check("a new name is free, and says the id it will have", code == 0 and "gas-basic-3" in out, out)
        code, out = out_of(cp.cmd_create, c)
        check("create without a course name stops and asks intake question 9", code == 2 and "question 9" in out, out)
        intake = json.load(io.open(os.path.join(c, "intake.json"), encoding="utf-8"))
        intake["course_name"] = "GAS BASIC"
        io.open(os.path.join(c, "intake.json"), "w", encoding="utf-8").write(json.dumps(intake))
        code, out = out_of(cp.cmd_create, c)
        check("create refuses a name already used", code == 2 and "another name" in out and not cp.portal(c), out)
        intake["course_name"] = "GAS BASIC 3"
        io.open(os.path.join(c, "intake.json"), "w", encoding="utf-8").write(json.dumps(intake))
        code, out = out_of(cp.cmd_create, c)
        p = cp.portal(c)
        check("create makes the course in preparation under intake's course_name, with the experts' link",
              code == 0 and p and p["course_id"] == "gas-basic-3" and "prep.html?course=gas-basic-3" in out, (out, p))
        check("portal.json never holds the key", p and not any("key" in k for k in p), p)
        code, out = out_of(cp.cmd_create, c)
        check("create again only says where it is", code == 0 and "Already in preparation" in out and len(srv.preps) == 1, out)
        check("a second course with the same name is refused", out_of(cp.cmd_name, "GAS  basic 3")[0] == 2)

        print("\n-- push")
        pr.draft(c)
        code, out = out_of(cp.cmd_push_pedagogy, c)
        check("push is refused until the pedagogy is clean", code == 2 and "not ready for the experts" in out and not srv.docs, out)
        tpr.complete(c)
        code, out = out_of(cp.cmd_push_pedagogy, c)
        d = srv.docs[-1] if srv.docs else {}
        check("push sends the pedagogy: version 1, a row for the course and one per topic",
              code == 0 and d.get("version") == 1 and set(d["items"]) == {"course", "1/1.1", "1/1.1.a", "1/1.1.b", "2/1.3", "3/1"}, (out, d.get("items")))
        t = d["content"]["modules"][0]["topics"][0]
        check("... in the Word files' words: the outcome from the architecture, now, proposed with its decision and why",
              t["outcome"] and t["now"]["checked"] == "final test Q1" and "->" in t["proposed"]["change"]
              and t["proposed"]["decision"] in ("kept", "lifted", "above the outcome") and t["proposed"]["why"], t)
        check("... and no JSON field name or level number is shown alone: levels read '3 Apply'",
              re.match(r"^\d [A-Z][a-z]+$", t["asks"] or "") is not None, t["asks"])
        code, out = out_of(cp.cmd_push_pedagogy, c)
        check("sent again unchanged: no new version", "Nothing new" in out and len(srv.docs) == 1, out)

        print("\n-- the experts answer, the factory pulls")
        a_ok = srv.answer("anna.liepa@novikontas.org", "1/1.1", "ok")
        a_ch = srv.answer("anna.liepa@novikontas.org", "2/1.3", "change", "They set it on the real panel: lift it to Apply.")
        srv.answer("janis.berzins@novikontas.org", "course", "change", "Say how long the simulator runs are.")
        srv.ready("Anna Liepa")
        code, out = out_of(cp.cmd_pull, c)
        rev = json.load(io.open(pr.files(c)["review"], encoding="utf-8"))
        r11, r13 = rev["modules"]["1"]["rows"]["1.1"], rev["modules"]["2"]["rows"]["1.3"]
        check("OK goes into the row's expert_review", [x["by"] for x in r11.get("expert_review", [])] == ["Anna Liepa"], r11)
        check("needs change goes into the row's expert_notes, with the words and who, not done yet",
              r13.get("expert_notes") and r13["expert_notes"][0]["said"].startswith("They set it on the real panel")
              and r13["expert_notes"][0]["done"] == "" and r13["expert_notes"][0]["by"] == "Anna Liepa", r13)
        check("a note on the summaries goes to the whole course's expert_notes",
              rev.get("expert_notes") and rev["expert_notes"][0]["by"] == "Janis Berzins", rev.get("expert_notes"))
        check("Ready is recorded with the name it was signed with, and the changes it goes with",
              rev.get("ready", {}).get("by") == "Anna Liepa" and rev["ready"]["changes"] == 2, rev.get("ready"))
        log = io.open(os.path.join(c, "FEEDBACK_LOG.md"), encoding="utf-8").read()
        check("FEEDBACK_LOG.md has each change asked and the Ready",
              "| 2 | " in log and "2 · M02 · 1.3 | They set it on the real panel" in log and "[Anna Liepa, editor mode] | to do" in log
              and "2 · course · summaries and upgrades" in log and "Ready - signed Anna Liepa" in log, log[-700:])
        check("what was taken is acknowledged", all(a.get("pulled") for a in srv.answers) and srv.docs[-1].get("ready_pulled"))
        probs, _ = pr.check(c)
        check("check stops until every change asked is carried out",
              any("module 2, topic 1.3: Anna Liepa asked in editor mode" in x for x in probs)
              and any("the whole course: Janis Berzins asked" in x for x in probs), probs)
        n = len(log)
        code, out = out_of(cp.cmd_pull, c)
        check("pulled again: nothing taken twice", "0 answer(s)" in out and len(io.open(os.path.join(c, "FEEDBACK_LOG.md"), encoding="utf-8").read()) == n, out)

        srv.answer("anna.liepa@novikontas.org", "2/1.3", "ok")
        out_of(cp.cmd_pull, c)
        r13 = json.load(io.open(pr.files(c)["review"], encoding="utf-8"))["modules"]["2"]["rows"]["1.3"]
        check("an answer changed from 'change' to OK takes its open note away", "expert_notes" not in r13
              and [x["answer"] for x in r13["expert_review"]] == [a_ch["id"]], r13)

        rev = json.load(io.open(pr.files(c)["review"], encoding="utf-8"))
        for x in rev["expert_notes"]:
            x["done"] = "the simulator runs' minutes are in the summary"
        rev["proposed_summary"] += " Each simulator run is 30 minutes."
        io.open(pr.files(c)["review"], "w", encoding="utf-8").write(json.dumps(rev, ensure_ascii=False))
        check("with every change carried out, check is clean again", pr.check(c)[0] == [], pr.check(c)[0])
        pr.render(c, pdf=False)
        with zipfile.ZipFile(os.path.join(pr.files(c)["out"], "2_BLOOM_PROPOSED.docx")) as z:
            word = z.read("word/document.xml").decode("utf-8")
        check("render signs the documents with the expert's Ready", "Anna Liepa" in word and "Ready, in editor mode" in word)
        code, out = out_of(cp.cmd_push_pedagogy, c)
        check("the changed words go back as version 2; the topics not changed keep their answers",
              srv.docs[-1]["version"] == 2 and srv.docs[0]["status"] == "superseded" and "2 answers kept" in out, out)

        print("\n-- the key and the address")
        src = io.open(os.path.join(HERE, "course_portal.py"), encoding="utf-8").read()
        check("the client knows only the staging project", "mgkhdbkxfaldfxyvfqrl" in src and "vapnxststhoxadhhdyty" not in src)
        old = dict(os.environ)
        os.environ.pop("NOVIKONTAS_FACTORY_KEY", None)
        os.environ["APPDATA"] = os.path.join(tmp, "nowhere")
        try:
            cp.factory_key()
            check("no key on this PC: it says where to put it", False)
        except cp.PortalError as e:
            check("no key on this PC: it says where to put it", "factory.key" in str(e) and "nowhere" in str(e), e)
        finally:
            os.environ.clear()
            os.environ.update(old)
        repo = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(HERE))))
        found = [os.path.join(r, n) for r, _, ns in os.walk(repo) if ".git" not in r for n in ns if n == "factory.key"]
        check("no factory.key anywhere in the repository", not found, found)
        code, out = out_of(cp.cmd_remove, c, False)
        check("remove asks for --yes", code == 2 and cp.portal(c))
        code, out = out_of(cp.cmd_remove, c, True)
        check("remove takes the course out and forgets it", code == 0 and not cp.portal(c) and "gas-basic-3" not in srv.preps, out)
    finally:
        cp.CALL = cp._http
        shutil.rmtree(tmp, ignore_errors=True)
    print("\n%d passed, %d failed" % (len(PASS), len(FAIL)))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
