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
import subprocess
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
    def answer(self, who, item, verdict, note=None, decision=None):
        d = self.docs[-1]
        mine = [a for a in self.answers if a["by_email"] == who and a["item"] == item and a["item_hash"] == d["items"][item]]
        if mine:
            mine[0].update(verdict=verdict, note=note, decision=decision, pulled=False)
            return mine[0]
        a = dict(id=str(uuid.uuid4()), kind="pedagogy", module="", item=item, item_hash=d["items"][item], verdict=verdict,
                 note=note, decision=decision, by_name=who.split("@")[0].replace(".", " ").title(), by_email=who, updated_at="2026-11-04T11:00:00Z")
        self.answers.append(a)
        return a

    def ready(self, name):
        self.docs[-1].update(status="ready", ready_by_name=name, ready_by_email="anna.liepa@novikontas.org",
                             ready_at="2026-11-04T11:30:00Z")


def workspace_master(c):
    return cp.workspace.master_of(c)


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
    real_appdata = os.environ.get("APPDATA")
    os.environ["APPDATA"] = os.path.join(tmp, "appdata")      # the PC's own course list, lock and log stay untouched
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
        check("push sends the pedagogy: version 1, a row per learning outcome",
              code == 0 and d.get("version") == 1 and set(d["items"]) == {"1/1.1", "1/1.1.a", "1/1.1.b", "2/1.3", "3/1"}, (out, d.get("items")))
        form = d["content"]
        rows = {r.get("item") or "head " + r["ref"]: r for tp in form.get("topics", []) for r in tp["rows"]}
        r1a = rows.get("1/1.1.a") or {}
        check("... as the outcomes form (the owner's Excel): topic, ILO, sub-ILO; the original beside the proposed, and the task",
              form.get("form") == "outcomes" and [tp["n"] for tp in form["topics"]] == [1, 2, 3]
              and r1a["original"]["text"].startswith("Identificēt") and r1a["original"]["level"] in range(1, 7)
              and r1a["proposed"]["level"] in range(1, 7) and r1a["task"]["does"] and r1a["parent"] == "1" and not r1a["main"], r1a)
        check("... a module's Main ILO heads its Sub-ILOs and is not answered; a module without Sub-ILOs answers its Main ILO",
              rows.get("head 1", {}).get("heading") and "item" not in rows["head 1"]
              and rows["3/1"]["main"] and not rows["3/1"].get("heading") and rows["3/1"]["parent"] is None, list(rows))
        t = pr.view(c)["review"]["modules"][0]["topics"][0]
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
        srv.answer("janis.berzins@novikontas.org", "1/1.1.b", "change", "Say how long the simulator runs are.")
        srv.ready("Anna Liepa")
        code, out = out_of(cp.cmd_pull, c)
        rev = json.load(io.open(pr.files(c)["review"], encoding="utf-8"))
        r11, r13 = rev["modules"]["1"]["rows"]["1.1"], rev["modules"]["2"]["rows"]["1.3"]
        check("OK goes into the row's expert_review", [x["by"] for x in r11.get("expert_review", [])] == ["Anna Liepa"], r11)
        check("needs change goes into the row's expert_notes, with the words and who, not done yet",
              r13.get("expert_notes") and r13["expert_notes"][0]["said"].startswith("They set it on the real panel")
              and r13["expert_notes"][0]["done"] == "" and r13["expert_notes"][0]["by"] == "Anna Liepa", r13)
        r1b = rev["modules"]["1"]["rows"]["1.1.b"]
        check("a note from a second expert goes to that row's expert_notes",
              r1b.get("expert_notes") and r1b["expert_notes"][0]["by"] == "Janis Berzins", r1b)
        check("Ready is recorded with the name it was signed with, and the changes it goes with",
              rev.get("ready", {}).get("by") == "Anna Liepa" and rev["ready"]["changes"] == 2, rev.get("ready"))
        log = io.open(os.path.join(c, "FEEDBACK_LOG.md"), encoding="utf-8").read()
        check("FEEDBACK_LOG.md has each change asked and the Ready",
              "| 2 | " in log and "2 · M02 · 1.3 | They set it on the real panel" in log and "[Anna Liepa, editor mode] | to do" in log
              and "2 · M01 · 1.1.b | Say how long" in log and "Ready - signed Anna Liepa" in log, log[-700:])
        check("what was taken is acknowledged", all(a.get("pulled") for a in srv.answers) and srv.docs[-1].get("ready_pulled"))
        probs, _ = pr.check(c)
        check("check stops until every change asked is carried out",
              any("module 2, topic 1.3: Anna Liepa asked in editor mode" in x for x in probs)
              and any("topic 1.1.b: Janis Berzins asked" in x for x in probs), probs)
        n = len(log)
        code, out = out_of(cp.cmd_pull, c)
        check("pulled again: nothing taken twice", "0 answer(s) - 0 OK" in out and len(io.open(os.path.join(c, "FEEDBACK_LOG.md"), encoding="utf-8").read()) == n, out)

        srv.answer("anna.liepa@novikontas.org", "2/1.3", "ok")
        out_of(cp.cmd_pull, c)
        r13 = json.load(io.open(pr.files(c)["review"], encoding="utf-8"))["modules"]["2"]["rows"]["1.3"]
        check("an answer changed from 'change' to OK takes its open note away", "expert_notes" not in r13
              and [x["answer"] for x in r13["expert_review"]] == [a_ch["id"]], r13)

        # 2.142.1 (the pedagogy lead): "accept the outcome and its level, but let me fix only the task" - OK with "Task: ..."
        mine = "Each pair reads the general arrangement plan and marks the tank that leans on the hull."
        as_it_was = io.open(pr.files(c)["review"], encoding="utf-8").read()       # put back below: the next checks count this row's answer
        srv.answer("anna.liepa@novikontas.org", "2/1.3", "ok", "Task: " + mine)
        out_of(cp.cmd_pull, c)
        r13 = json.load(io.open(pr.files(c)["review"], encoding="utf-8"))["modules"]["2"]["rows"]["1.3"]
        check("OK with a note that starts 'Task:' - the row's task becomes the expert's own words, by name",
              r13["proposed"]["how"] == mine and r13["proposed"]["task_expert"]["by"] == "Anna Liepa", r13["proposed"])
        check("... and nothing is left to do: the note is recorded as carried out, so check does not stop on it",
              r13["expert_notes"][-1]["said"].startswith("Task: ") and r13["expert_notes"][-1]["done"]
              and not any("topic 1.3: Anna Liepa asked" in x for x in pr.check(c)[0]), r13.get("expert_notes"))
        check("... the feedback log says so", "the task replaced by the expert's words" in io.open(os.path.join(c, "FEEDBACK_LOG.md"), encoding="utf-8").read())
        srv.answer("anna.liepa@novikontas.org", "2/1.3", "ok", "The task should say which plan.")
        out_of(cp.cmd_pull, c)
        r13 = json.load(io.open(pr.files(c)["review"], encoding="utf-8"))["modules"]["2"]["rows"]["1.3"]
        check("... any other note with an OK is still a change for the factory to carry out",
              r13["expert_notes"][-1]["done"] == "" and r13["proposed"]["how"] == mine, r13.get("expert_notes"))
        srv.answer("anna.liepa@novikontas.org", "2/1.3", "ok")
        out_of(cp.cmd_pull, c)
        io.open(pr.files(c)["review"], "w", encoding="utf-8").write(as_it_was)

        rev = json.load(io.open(pr.files(c)["review"], encoding="utf-8"))
        for x in rev["modules"]["1"]["rows"]["1.1.b"]["expert_notes"]:
            x["done"] = "the simulator runs' minutes are in the task"
        io.open(pr.files(c)["review"], "w", encoding="utf-8").write(json.dumps(rev, ensure_ascii=False))
        check("with every change carried out, check is clean again", pr.check(c)[0] == [], pr.check(c)[0])
        pr.render(c, pdf=False)
        with zipfile.ZipFile(os.path.join(pr.files(c)["out"], "2_BLOOM_PROPOSED.docx")) as z:
            word = z.read("word/document.xml").decode("utf-8")
        check("render signs the documents with the expert's Ready", "Anna Liepa" in word and "Ready, in editor mode" in word)
        code, out = out_of(cp.cmd_push_pedagogy, c)
        check("the changed words go back as version 2; the topics not changed keep their answers",
              srv.docs[-1]["version"] == 2 and srv.docs[0]["status"] == "superseded" and "2 answers kept" in out, out)

        print("\n-- keep as now, a decision made with Claude, a note on the activities")
        rev = json.load(io.open(pr.files(c)["review"], encoding="utf-8"))
        now11 = rev["modules"]["1"]["rows"]["1.1"]["now"]
        srv.answer("anna.liepa@novikontas.org", "1/1.1", "decision", decision={"choice": "keep", "level": now11["level"],
                                                                                "said": "Keep it as the old course teaches it."})
        srv.answer("anna.liepa@novikontas.org", "2/1.3", "decision", decision={
            "choice": "claude", "level": 4, "how": "Trainees find the fault in a recorded loading on the simulator.",
            "why": "On board they must see what went wrong before the alarm.", "said": "They should analyse a real loading."})
        # the outcomes form (2026-11-23): Regenerate at a level the expert chose, and Keep original
        srv.answer("anna.liepa@novikontas.org", "1/1.1.b", "decision", decision={
            "choice": "claude", "level": 2, "level_name": "2 Understand", "verb": "Explains", "archetype": "Explain-Why Prompt Set",
            "revised_outcome": "Explains why a membrane tank needs a secondary barrier", "how": "Learners explain it on a section drawing.",
            "why": "", "said": "Regenerate at 2 Understand", "regenerated": True})
        srv.answer("anna.liepa@novikontas.org", "3/1", "decision", decision={
            "choice": "keep", "level": 3, "level_name": "3 Apply", "verb": "Operate", "revised_outcome": "",
            "said": "Keep the original wording and level."})
        code, out = out_of(cp.cmd_pull, c)
        rev = json.load(io.open(pr.files(c)["review"], encoding="utf-8"))
        p11, p13 = rev["modules"]["1"]["rows"]["1.1"]["proposed"], rev["modules"]["2"]["rows"]["1.3"]["proposed"]
        check("keep as now: the old course's level, how it is taught kept, carried out as the expert's decision",
              p11["level"] == now11["level"] and p11["how"].startswith("Kept as the old course teaches it: ")
              and p11["expert"]["by"] == "Anna Liepa", p11)
        check("a decision with Claude: its level, what the trainee does and why, the expert's words",
              p13["level"] == 4 and p13["how"].startswith("Trainees find the fault") and p13["why"].startswith("On board they must")
              and p13["expert"]["said"] == "They should analyse a real loading." and not p13.get("above_why"), p13)
        p1b, p31 = rev["modules"]["1"]["rows"]["1.1.b"]["proposed"], rev["modules"]["3"]["rows"]["1"]["proposed"]
        arch_1b = {s["id"]: s for s in json.load(io.open(pr.files(c)["arch"], encoding="utf-8"))["modules"][0]["sub_ilos"]}["1.1.b"]
        check("Regenerate: the level the expert chose, the new task, the Sub-ILO re-worded at that level",
              p1b["level"] == 2 and p1b["how"] == "Learners explain it on a section drawing." and p1b["expert"]["said"] == "Regenerate at 2 Understand"
              and arch_1b["text"] == "Explains why a membrane tank needs a secondary barrier", (p1b, arch_1b))
        check("Keep original: the outcome's own words at its own level, not the old course's",
              p31["level"] == 3 and not p31.get("revised_outcome") and p31["expert"]["said"] == "Keep the original wording and level.", p31)
        probs, _ = pr.check(c)
        check("check: the decisions pass every keep-or-lift rule", probs == [], probs)
        log = io.open(os.path.join(c, "FEEDBACK_LOG.md"), encoding="utf-8").read()
        check("FEEDBACK_LOG.md says what each decision changed",
              "kept as the old course, at" in log and "set with Claude to 4 Analyse: Trainees find the fault" in log
              and "the original wording kept, at 3 Apply" in log, log[-900:])
        v = pr.view(c)
        t13 = v["review"]["modules"][1]["topics"][0]
        check("sent again, the topic shows the expert's decision", t13["proposed"]["decision"] == "the expert's decision"
              and any("They should analyse a real loading." in w for w in t13["proposed"]["why"]), t13["proposed"])

        print("\n-- intended and revised learning outcomes")
        mods = {m["n"]: {t["id"]: t for t in m["topics"]} for m in v["review"]["modules"]}
        t1a, t31 = mods[1]["1.1.a"], mods[3]["1"]
        check("a Sub-ILO the factory re-expressed: the programme's words as intended, the new words as revised, each with its verb",
              t1a["intended"].startswith("Identificēt") and t1a["revised"].startswith("Identify the cargo containment")
              and t1a["revised_verb"].startswith("identify") and not t1a["main"], t1a)
        check("a Main ILO is shown as it is, never revised", t31["main"] and t31["revised"] == "" and t31["intended"], t31)
        check("the proposed teaching and learning activity is the row's own", t1a["tla"] == t1a["proposed"]["how"])
        rev = json.load(io.open(pr.files(c)["review"], encoding="utf-8"))
        rev["modules"]["3"]["rows"]["1"]["proposed"]["revised_outcome"] = "Operate the whole cargo plant"
        io.open(pr.files(c)["review"], "w", encoding="utf-8").write(json.dumps(rev, ensure_ascii=False))
        check("check refuses a re-worded Main ILO (L2)", any("module 3, topic 1: a Main ILO is never re-worded" in x for x in pr.check(c)[0]))
        del rev["modules"]["3"]["rows"]["1"]["proposed"]["revised_outcome"]
        rev["modules"]["1"]["rows"]["1.1"]["proposed"]["revised_outcome"] = "Operate the cargo containment system of a gas tanker"
        for m in rev.get("modules", {}).values():
            m.pop("expert_notes", None)
        io.open(pr.files(c)["review"], "w", encoding="utf-8").write(json.dumps(rev, ensure_ascii=False))
        out_of(cp.cmd_push_pedagogy, c)
        srv.answer("anna.liepa@novikontas.org", "1/1.1", "ok")
        srv.answer("anna.liepa@novikontas.org", "1/1.1.b", "decision", decision={
            "choice": "claude", "level": 3, "how": "Trainees name the tank type on five photographs and say why.",
            "why": "They must know their own ship's tanks.", "said": "Make it practical.", "revised_outcome": "Identify the tank type on a photograph"})
        out_of(cp.cmd_pull, c)
        arch = json.load(io.open(pr.files(c)["arch"], encoding="utf-8"))
        subs = {s["id"]: s for s in arch["modules"][0]["sub_ilos"]}
        check("Take proposed ratifies the revised Sub-ILO into the architecture, the programme's words kept beside it",
              subs["1.1"]["status"] == "re-expressed" and subs["1.1"]["text"].startswith("Operate the cargo")
              and subs["1.1"]["programme_text"].startswith("Identificēt") and subs["1.1"]["ratified"]["by"] == "Anna Liepa", subs["1.1"])
        check("a decision with Claude that re-words the Sub-ILO is ratified the same way",
              subs["1.1.b"]["text"] == "Identify the tank type on a photograph" and subs["1.1.b"]["ratified"]["by"] == "Anna Liepa", subs["1.1.b"])
        t11 = {t["id"]: t for t in pr.view(c)["review"]["modules"][0]["topics"]}["1.1"]
        check("sent again, the topic shows the programme's words as intended and the ratified ones as revised",
              t11["intended"].startswith("Identificēt") and t11["revised"].startswith("Operate the cargo"), t11)

        print("\n-- the build after Ready, on the office PC")
        old_env = dict(os.environ)
        stub = os.path.join(tmp, "stub_claude.py")
        io.open(stub, "w", encoding="utf-8").write(
            "import os, sys, json\n"
            "json.dump(sys.argv[1:], open(os.path.join(os.environ['STUB_OUT'], 'args.json'), 'w'))\n"
            "open(os.path.join(os.environ['STUB_OUT'], 'cwd.txt'), 'w').write(os.getcwd())\n"
            "if os.environ.get('STUB_FAIL'):\n    print('AUTO BUILD STOPPED: no simulator manual'); sys.exit(0)\n"
            "os.makedirs('modules', exist_ok=True); open('modules/COURSE.html', 'w').write('<title>GAS BASIC 3</title>')\n"
            "print('working...'); print('AUTO BUILD DONE')\n")
        imp = os.path.join(tmp, "stub_import.py")
        io.open(imp, "w", encoding="utf-8").write(
            "import os, sys, json\nprint(json.dumps({'ok': True, 'release': {'version': '1.0.0', 'args': sys.argv[2:], "
            "'notes': json.loads(os.environ.get('NOVIKONTAS_IMPORT_NOTES') or '[]')}}))\n")
        os.environ.update(NOVIKONTAS_CLAUDE_CMD=json.dumps([sys.executable, stub]), NOVIKONTAS_NODE=json.dumps([sys.executable, imp]),
                          STUB_OUT=tmp)
        queue = []
        orig = srv.__call__

        def build_server(action, p):
            if action == "build-next":
                return {"course": queue[0] if queue else None}
            if action == "build-claim":
                queue[0]["stage"] = "building"
                return {"course": queue[0]}
            if action == "build-done":
                srv.done = p
                return {"course": {}}
            return orig(action, p)
        cp.CALL = build_server
        try:
            check("nothing queued: watch does nothing", cp.cmd_watch_once() == 0 and not os.path.isfile(os.path.join(tmp, "args.json")))
            out_of(cp.cmd_create, c)
            queue.append({"id": "gas-basic-3", "title": "GAS BASIC 3", "stage": "build_requested", "build_requested_by": "Anna Liepa"})
            srv.done = None
            code = cp.cmd_watch_once()
            args = json.load(io.open(os.path.join(tmp, "args.json"), encoding="utf-8"))
            check("a queued course: claimed, Claude Code runs unattended in the course folder with the expert's name",
                  code == 0 and queue[0]["stage"] == "building" and args[0] == "-p" and "Anna Liepa (Ready in editor)" in args[1]
                  and os.path.samefile(io.open(os.path.join(tmp, "cwd.txt")).read(), workspace_master(c)), (code, args[:2]))
            check("... edits accepted without asking, paid pictures and git push refused",
                  "acceptEdits" in args and "mcp__plugin_nano-banana_nano-banana__generate_image" in args and "Bash(git push:*)" in args, args)
            check("... and the built course is imported as a draft; nothing is marked stopped", srv.done is None)
            logs = os.listdir(os.path.join(c, "auto_build")) if os.path.isdir(os.path.join(c, "auto_build")) else \
                os.listdir(os.path.join(c, "working_claude", "auto_build"))
            check("the run's words are kept in the course's auto_build log", logs, logs)
            os.environ["STUB_FAIL"] = "1"
            queue[0]["stage"] = "build_requested"
            cp.cmd_watch_once()
            check("a run that stops says why in the editor", srv.done and "no simulator manual" in srv.done["error"], srv.done)
            lock = os.path.join(os.environ["APPDATA"], "novikontas", "watch.lock")
            io.open(lock, "w").write("1")
            srv.done = None
            check("one watch at a time: while a build runs, the next watch leaves at once", cp.cmd_watch_once() == 0 and srv.done is None)
            os.remove(lock)

            log = os.path.join(os.environ["APPDATA"], "novikontas", "watch.log")
            real_blockers = cp.blockers
            pic = "module01/assets/img/_placeholder_s05.png is a Phase A placeholder, not a picture - fill its slot"
            try:
                cp.blockers = lambda course: ([pic], [])
                queue[0]["stage"] = "build_requested"
                srv.done = None
                code = cp.cmd_watch_once()
                check("a run that stopped on picture spaces alone still goes up, as a draft with its pictures pending",
                      code == 0 and srv.done is None and "pictures pending: 1" in io.open(log, encoding="utf-8").read(), (code, srv.done))
                del os.environ["STUB_FAIL"]
                code, r = cp.cmd_import(c, [pic])
                notes = ((r or {}).get("release") or {}).get("notes") or []
                check("... the draft itself says how many pictures are pending, each one named",
                      code == 0 and notes[0].startswith("Pictures pending: 1") and pic in notes, notes)

                print("\n-- after an attended session: the course goes up unasked, the old stop message goes")
                srv.preps["gas-basic-3"].update(stage="build_requested", build_error="AUTO BUILD STOPPED: 218 picture spaces")
                code, out = out_of(cp.cmd_upload, c)
                check("only pictures left: imported as a draft, pictures pending (the import marks it built - the stop "
                      "message goes)", code == 0 and "Imported into the staging editor" in out and "pictures pending: 1" in out, out)
                let = "M01 s04 - stop 3: the axis has no bars yet - accepted by Aleksis Vejs, 2026-11-10 (typed in a terminal): drawn next"
                real_accepted, real_import, went = cp.walk_accepted, cp.cmd_import, []
                try:
                    cp.walk_accepted = lambda course: [let]
                    cp.cmd_import = lambda *a: went.append(real_import(*a)) or went[-1]
                    code, out = out_of(cp.cmd_upload, c)
                finally:
                    cp.walk_accepted, cp.cmd_import = real_accepted, real_import
                notes = ((went[0][1] if went else {}).get("release") or {}).get("notes") or []
                check("a walk-review fail the operator accepted goes up - shown at the upload, and written into the draft's notes",
                      code == 0 and "1 walk-review fail(s) nobody fixed" in out and let in out and let in notes
                      and any(x.startswith("Walk review: 1 fail(s) nobody fixed") for x in notes) and notes[0].startswith("Pictures pending"),
                      (out, notes))
                cp.blockers = lambda course: ([], ["module03/deck.html uses assets/img/x.png, which is not there"])
                srv.done = None
                code, out = out_of(cp.cmd_upload, c)
                check("something else still stops it: not uploaded, and the editor's stop message now says what, today",
                      code == 1 and srv.done and "module03/deck.html" in srv.done["error"] and "still stop it" in srv.done["error"]
                      and "Imported" not in out, (out, srv.done))
                srv.preps["gas-basic-3"].update(build_error=None)
                srv.done = None
                out_of(cp.cmd_upload, c)
                check("... a course waiting in the queue with no stop message is not held back by one", srv.done is None, srv.done)
                os.environ["NOVIKONTAS_AUTO_BUILD"] = "1"
                code, out = out_of(cp.cmd_upload, c)
                check("inside the unattended build the watch uploads, not the build's own steps",
                      code == 0 and "the watch uploads it" in out and srv.done is None, out)
                del os.environ["NOVIKONTAS_AUTO_BUILD"]
            finally:
                cp.blockers = real_blockers
            check("a course not compiled yet is stopped by that, not by a crash",
                  cp.blockers(os.path.join(tmp, "nowhere")) == ([], ["modules\\COURSE.html is missing - the course is not compiled"]))
            fb = os.path.join(tmp, "failedbuild")
            os.makedirs(os.path.join(fb, "working_claude", "_build"))
            for m, lines in (("M01", "PASS M01 - figures (40 s)\nFAIL M01 - audits 1280x800 (97 s)"),
                             ("M02", "FAIL M02 - audits (90 s)\nPASS M02 - figures (41 s)"),
                             ("M03", "FAIL M03 - course package (60 s)"),
                             ("M04", "FAIL M04 - course package, task pages (60 s)")):
                io.open(os.path.join(fb, "working_claude", "_build", m + "_answer.txt"), "w", encoding="utf-8").write(lines)
            check("a module whose last build ended on FAIL stops the upload; a later PASS, or only the course package, does not "
                  "(the first factory trial: four modules ended on FAIL) - the course package and something else does (2.125.0)",
                  cp.failed_builds(fb) == ["FAIL M01 - audits 1280x800 (97 s) - its last build did not pass",
                                           "FAIL M04 - course package, task pages (60 s) - its last build did not pass"],
                  cp.failed_builds(fb))

            print("\n-- the scheduled task runs pythonw: no console")

            def boom(action, p):
                raise RuntimeError("the server's answer was not understood")
            cp.CALL = boom
            check("an error nobody expected: the watch ends with its own code, the traceback in watch.log",
                  cp.cmd_watch_once() == 4 and "Traceback" in io.open(log, encoding="utf-8").read()
                  and "the server's answer was not understood" in io.open(log, encoding="utf-8").read()
                  and not os.path.isfile(lock))
            cp.CALL = build_server
            noconsole = ("import runpy, sys\nsys.stdout = sys.stderr = None\nsys.argv = [sys.argv[1]] + sys.argv[2:]\n"
                         "runpy.run_path(sys.argv[0], run_name='__main__')\n")
            env = dict(os.environ, APPDATA=os.path.join(tmp, "nokey"), USERPROFILE=os.path.join(tmp, "nokey"), HOME=os.path.join(tmp, "nokey"))
            env.pop("NOVIKONTAS_FACTORY_KEY", None)
            run = subprocess.run([sys.executable, "-c", noconsole, os.path.join(HERE, "course_portal.py"), "watch", "--once"],
                                 env=env, capture_output=True, text=True)
            nlog = os.path.join(tmp, "nokey", "novikontas", "watch.log")
            said = io.open(nlog, encoding="utf-8").read() if os.path.isfile(nlog) else ""
            check("with no console (pythonw) the watch runs to its end - no key here, so it says that in watch.log, exit 3, "
                  "not exit 1 at its first print", run.returncode == 3 and "no factory key" in said, (run.returncode, said, run.stderr[-300:]))
            launcher = os.path.join(tmp, "nokey", "novikontas", "watch.py")
            io.open(launcher, "w", encoding="utf-8").write(cp.LAUNCHER)
            run = subprocess.run([sys.executable, "-c", noconsole, launcher], env=env, capture_output=True, text=True)
            said = io.open(nlog, encoding="utf-8").read()
            check("the scheduled task's launcher with no console: no plugin installed is said in watch.log",
                  run.returncode == 5 and "no course-factory plugin" in said, (run.returncode, said, run.stderr[-300:]))
            plug = os.path.join(tmp, "nokey", ".claude", "plugins", "cache", "novikontas-course-factory", "course-factory", "9.9.9",
                                "skills", "course-factory", "scripts")
            os.makedirs(plug)
            io.open(os.path.join(plug, "course_portal.py"), "w", encoding="utf-8").write(
                "import sys\nprint('nothing queued')\nsys.exit(0)\n")
            run = subprocess.run([sys.executable, "-c", noconsole, launcher], env=env, capture_output=True, text=True)
            check("... and runs the newest plugin's watch, ending 0 when nothing is queued (the task's Last Result 0)",
                  run.returncode == 0, (run.returncode, run.stderr[-300:]))
        finally:
            cp.CALL = srv
            os.environ.clear()
            os.environ.update(old_env)

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
        if real_appdata is None:
            os.environ.pop("APPDATA", None)
        else:
            os.environ["APPDATA"] = real_appdata
        shutil.rmtree(tmp, ignore_errors=True)
    print("\n%d passed, %d failed" % (len(PASS), len(FAIL)))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
