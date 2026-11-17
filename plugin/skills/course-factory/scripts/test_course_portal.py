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
  * a Sub-ILO's new wording that arrives in the programme's language (a decision with Claude, or Take proposed on
    a proposal an older factory wrote in it) is never taken as it is: the architecture keeps what it had, the
    wording becomes the expert's note, check stops until pedagogy_review.py reword has written it in English;
  * the answers reach what the build reads: an OK keeps the row's proposed activities in the architecture (the
    module's own on its activities row), Keep as now strikes the topic's and drops the raised level's reason, a
    decision with Claude keeps the teaching agreed as an activity and strikes the rest; a wording already ratified is
    not ratified or logged again; a note's log row says done once it is; the answers the factory carried out stand on
    the next version (the editor does not ask them again), a row the factory changed itself is asked again;
  * the client knows only the staging project and the live editor address, retries a passing gateway error (520),
    and the key comes from the office PC, never from a course folder.
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
            for c in p.get("carried") or []:        # an answer the factory carried out stands on the new words
                for a in self.answers:
                    if a["id"] == c["id"] and a["item"] == c["item"] and a.get("pulled") and c["item"] in p["items"]:
                        a["item_hash"] = p["items"][c["item"]]
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
        check("push sends the pedagogy: version 1, a row for the course and one per topic",
              code == 0 and d.get("version") == 1 and set(d["items"]) == {"course", "upgrades", "1/1.1", "1/1.1.a", "1/1.1.b", "act/1/module", "2/1.3", "3/1"}, (out, d.get("items")))
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
              and "2 · course · summaries |" in log and "Ready - signed Anna Liepa" in log, log[-700:])
        check("what was taken is acknowledged", all(a.get("pulled") for a in srv.answers) and srv.docs[-1].get("ready_pulled"))
        probs, _ = pr.check(c)
        check("check stops until every change asked is carried out",
              any("module 2, topic 1.3: Anna Liepa asked in editor mode" in x for x in probs)
              and any("the whole course: Janis Berzins asked" in x for x in probs), probs)
        n = len(log)
        code, out = out_of(cp.cmd_pull, c)
        check("pulled again: nothing taken twice", "0 answer(s) - 0 OK" in out and len(io.open(os.path.join(c, "FEEDBACK_LOG.md"), encoding="utf-8").read()) == n, out)

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

        print("\n-- keep as now, a decision made with Claude, a note on the activities")
        rev = json.load(io.open(pr.files(c)["review"], encoding="utf-8"))
        now11 = rev["modules"]["1"]["rows"]["1.1"]["now"]
        srv.answer("anna.liepa@novikontas.org", "1/1.1", "decision", decision={"choice": "keep", "level": now11["level"],
                                                                                "said": "Keep it as the old course teaches it."})
        srv.answer("anna.liepa@novikontas.org", "2/1.3", "decision", decision={
            "choice": "claude", "level": 4, "how": "Trainees find the fault in a recorded loading on the simulator.",
            "why": "On board they must see what went wrong before the alarm.", "said": "They should analyse a real loading."})
        srv.answer("janis.berzins@novikontas.org", "act/1/module", "change", "Give the 3D section ten minutes more.")
        code, out = out_of(cp.cmd_pull, c)
        rev = json.load(io.open(pr.files(c)["review"], encoding="utf-8"))
        p11, p13 = rev["modules"]["1"]["rows"]["1.1"]["proposed"], rev["modules"]["2"]["rows"]["1.3"]["proposed"]
        check("keep as now: the old course's level, how it is taught kept, carried out as the expert's decision",
              p11["level"] == now11["level"] and p11["how"].startswith("Kept as the old course teaches it: ")
              and p11["expert"]["by"] == "Anna Liepa", p11)
        check("a decision with Claude: its level, what the trainee does and why, the expert's words",
              p13["level"] == 4 and p13["how"].startswith("Trainees find the fault") and p13["why"].startswith("On board they must")
              and p13["expert"]["said"] == "They should analyse a real loading." and not p13.get("above_why"), p13)
        m1 = rev["modules"]["1"]
        check("a note on the module's activities goes to the module, about the activities",
              m1.get("expert_notes") and m1["expert_notes"][0]["about"] == "activities", m1.get("expert_notes"))
        probs, _ = pr.check(c)
        check("check: the decisions pass every keep-or-lift rule; the activity note waits for its 'done'",
              probs and all("module 1: Janis Berzins asked" in x for x in probs), probs)
        log = io.open(os.path.join(c, "FEEDBACK_LOG.md"), encoding="utf-8").read()
        check("FEEDBACK_LOG.md says what each decision changed",
              "kept as the old course, at" in log and "set with Claude to 4 Analyse: Trainees find the fault" in log
              and "2 · M01 · activities | Give the 3D section ten minutes more." in log, log[-900:])
        v = pr.view(c)
        t13 = v["content"]["modules"][1]["topics"][0]
        check("sent again, the topic shows the expert's decision", t13["proposed"]["decision"] == "the expert's decision"
              and any("They should analyse a real loading." in w for w in t13["proposed"]["why"]), t13["proposed"])

        print("\n-- intended and revised learning outcomes")
        mods = {m["n"]: {t["id"]: t for t in m["topics"]} for m in v["content"]["modules"]}
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
        t11 = {t["id"]: t for t in pr.view(c)["content"]["modules"][0]["topics"]}["1.1"]
        check("sent again, the topic shows the programme's words as intended and the ratified ones as revised",
              t11["intended"].startswith("Identificēt") and t11["revised"].startswith("Operate the cargo"), t11)

        print("\n-- a new wording that arrives in the programme's language is written in English first")
        lv_a, lv_13 = "Atšķirt sašķidrinātās gāzes tankkuģu tipus un analizēt to uzbūvi", tpr.REVISED_LV
        rev = json.load(io.open(pr.files(c)["review"], encoding="utf-8"))
        rev["modules"]["1"]["rows"]["1.1.a"]["proposed"]["revised_outcome"] = lv_a      # a proposal of an older factory
        io.open(pr.files(c)["review"], "w", encoding="utf-8").write(json.dumps(rev, ensure_ascii=False))
        srv.answer("anna.liepa@novikontas.org", "1/1.1.a", "ok")
        srv.answer("anna.liepa@novikontas.org", "2/1.3", "decision", decision={
            "choice": "claude", "level": 3, "how": "Trainees choose the safe step for three cargoes from their properties.",
            "why": "They handle these cargoes on board.", "said": "Lai pielieto.", "revised_outcome": lv_13})
        out_of(cp.cmd_pull, c)
        arch = json.load(io.open(pr.files(c)["arch"], encoding="utf-8"))
        rev = json.load(io.open(pr.files(c)["review"], encoding="utf-8"))
        r1a, r13 = rev["modules"]["1"]["rows"]["1.1.a"], rev["modules"]["2"]["rows"]["1.3"]
        s1a, s13 = arch["modules"][0]["sub_ilos"][1], arch["modules"][1]["sub_ilos"][0]
        check("neither is taken as it is: the architecture keeps what it had, no row carries the Latvian as revised",
              s1a["text"] == tap.SUB_NEW and s13.get("status", "original") == "original" and "text" not in s13
              and "revised_outcome" not in r1a["proposed"] and "revised_outcome" not in r13["proposed"], (s1a, s13))
        check("the decision's level and teaching are carried out all the same", r13["proposed"]["level"] == 3
              and r13["proposed"]["how"].startswith("Trainees choose") and r13["proposed"]["expert"]["by"] == "Anna Liepa", r13)
        probs = pr.check(c)[0]
        check("each wording is the expert's note, and check stops until it is written in English",
              any(lv_a in n["said"] and not n["done"] for n in r1a.get("expert_notes") or [])
              and any(lv_13 in n["said"] and not n["done"] for n in r13.get("expert_notes") or [])
              and any("module 1, topic 1.1.a" in p and lv_a in p for p in probs)
              and any("module 2, topic 1.3" in p and lv_13 in p for p in probs), probs)
        log = io.open(os.path.join(c, "FEEDBACK_LOG.md"), encoding="utf-8").read()
        check("... and FEEDBACK_LOG.md says what is still to do",
              "written in English: " + lv_a in log and "written in English: " + lv_13 in log, log[-700:])
        code, _ = out_of(cp.cmd_push_pedagogy, c)
        check("push is refused meanwhile - nothing in Latvian reaches the editor as a revised outcome", code == 2)
        pr.record_reword(c, 1, "1.1.a", "Identify the types of liquefied gas tankers on a general arrangement plan", "Anna Liepa")
        pr.record_reword(c, 2, "1.3", tpr.REVISED, "Anna Liepa")
        rev = json.load(io.open(pr.files(c)["review"], encoding="utf-8"))
        for n, i in (("1", "1.1.a"), ("2", "1.3")):
            for note in rev["modules"][n]["rows"][i]["expert_notes"]:
                note["done"] = note["done"] or "Written in English, the programme's own words beside it."
        io.open(pr.files(c)["review"], "w", encoding="utf-8").write(json.dumps(rev, ensure_ascii=False))
        topics = {t["id"]: t for m in pr.view(c)["content"]["modules"] for t in m["topics"]}
        check("written in English with reword, the experts read English beside the programme's own words",
              topics["1.3"]["revised"] == tpr.REVISED and topics["1.3"]["intended"].startswith("Aprakstīt")
              and topics["1.1.a"]["revised"].startswith("Identify the types") and pr.check(c)[0] == [],
              (pr.check(c)[0], topics["1.1.a"]["revised"]))

        print("\n-- the expert's answers reach what the build reads")
        import make_architecture_page as ap
        arch2 = copy.deepcopy(tap.ARCH)
        arch2["modules"][0]["active_learning"] = [
            {"id": "A1.1", "subtopic": "1.1", "technique": "explore", "status": "proposed", "minutes": 10, "does": "Open the hull in 3D."},
            {"id": "A1.2", "subtopic": "1.1.b", "technique": "predict-then-reveal", "status": "proposed", "minutes": 5,
             "does": "Predict which tank leans on the hull."},
            {"id": "A1.3", "subtopic": "tank types", "technique": "explore", "status": "proposed", "minutes": 5, "does": "Walk the deck plan."}]
        arch2["modules"][1]["active_learning"] = [
            {"id": "A2.1", "subtopic": "1.3", "technique": "worked-example", "status": "proposed", "minutes": 10,
             "does": "Set the pressure alarm on the panel."}]
        c2 = tap.write_course(os.path.join(tmp, "course2"), tap.PROGRAMME, arch2)
        io.open(os.path.join(c2, "FEEDBACK_LOG.md"), "w", encoding="utf-8").write(
            "| # | Date | Stage · module · where | said | changed | fact |\n|---|---|---|---|---|---|\n| 1 | | | | | no |\n")
        intake = json.load(io.open(os.path.join(c2, "intake.json"), encoding="utf-8"))
        intake["course_name"] = "GAS BASIC 4"
        io.open(os.path.join(c2, "intake.json"), "w", encoding="utf-8").write(json.dumps(intake))
        srv2 = Server()
        cp.CALL = srv2
        out_of(cp.cmd_create, c2)
        tpr.complete(c2)
        rev = json.load(io.open(pr.files(c2)["review"], encoding="utf-8"))
        rev["modules"]["2"]["rows"]["1.3"]["proposed"].update(level=2, why="the alarm is set by the officer on watch")
        io.open(pr.files(c2)["review"], "w", encoding="utf-8").write(json.dumps(rev, ensure_ascii=False))
        pr.render(c2, pdf=False)
        code, out = out_of(cp.cmd_push_pedagogy, c2)
        check("a second course goes to the editor", code == 0 and srv2.docs, out)
        ok11 = srv2.answer("anna.liepa@novikontas.org", "1/1.1", "ok")
        okm = srv2.answer("anna.liepa@novikontas.org", "act/1/module", "ok")
        keep = srv2.answer("anna.liepa@novikontas.org", "2/1.3", "decision", decision={"choice": "keep", "level": 1, "said": "Keep it."})
        cl = srv2.answer("anna.liepa@novikontas.org", "1/1.1.b", "decision", decision={
            "choice": "claude", "level": 3, "how": "Trainees name the tank type on five photographs and say why.",
            "why": "They must know their own ship's tanks.", "said": "Make it practical.",
            "revised_outcome": "Identify the tank type on a photograph"})
        note = srv2.answer("anna.liepa@novikontas.org", "1/1.1.a", "change", "Show a real general arrangement plan.")
        srv2.ready("Anna Liepa")
        out_of(cp.cmd_pull, c2)
        a2 = json.load(io.open(pr.files(c2)["arch"], encoding="utf-8"))
        st = {x["id"]: x for m in a2["modules"] for x in m.get("active_learning") or []}
        check("Take proposed keeps the topic's proposed activity in the architecture, with who and their words",
              st["A1.1"]["status"] == "approved" and st["A1.1"]["decided_by"] == "Anna Liepa", st["A1.1"])
        check("OK on the module's activities row keeps the module's own", st["A1.3"]["status"] == "approved", st["A1.3"])
        check("Keep as now strikes the activity that would have lifted the topic", st["A2.1"]["status"] == "struck", st["A2.1"])
        new = [x for x in st.values() if x["does"].startswith("Trainees name the tank type")]
        check("a decision with Claude: the teaching agreed is a kept activity of the topic, the old proposal struck beside it",
              len(new) == 1 and new[0]["status"] == "approved" and new[0]["subtopic"] == "1.1.b" and new[0]["id"] == "A1.4"
              and new[0]["minutes"] == 5 and st["A1.2"]["status"] == "struck", st)
        prog2 = json.load(io.open(pr.files(c2)["prog"], encoding="utf-8"))
        check("nothing is left waiting for Keep or Strike: the Stage 2 approval does not wait for the expert's OK again",
              ap.analyse(prog2, a2)["waiting"] == [], ap.analyse(prog2, a2)["waiting"])
        rev = json.load(io.open(pr.files(c2)["review"], encoding="utf-8"))
        r13 = rev["modules"]["2"]["rows"]["1.3"]
        why13 = {t["id"]: t for m in pr.view(c2)["content"]["modules"] for t in m["topics"]}["1.3"]["proposed"]["why"]
        check("Keep as now drops the raised level's reason: no 'On board' line from the lift is left",
              r13["proposed"]["why"] == pr.KEPT_WHY and not any("officer on watch" in w or w.startswith("On board") for w in why13), why13)
        check("the answers carried out are remembered with the words they made; the note is not among them",
              set(rev.get("carried") or {}) == {ok11["id"], okm["id"], keep["id"], cl["id"]}, rev.get("carried"))
        log = io.open(os.path.join(c2, "FEEDBACK_LOG.md"), encoding="utf-8").read()
        check("FEEDBACK_LOG.md says which activities were kept and struck",
              "activities A1.1 kept" in log and "A2.1 struck" in log and "A1.4 kept" in log and "A1.2 struck" in log, log[-1200:])
        n1a = rev["modules"]["1"]["rows"]["1.1.a"]["expert_notes"][0]
        row_no = n1a.get("log")
        check("a note remembers its row in the log", isinstance(row_no, int) and ("| %d | " % row_no) in log
              and "Show a real general arrangement plan." in log.split("| %d | " % row_no)[1].split("\n")[0], (row_no, log[-600:]))
        n1a["done"] = "A real general arrangement plan is on the slide."
        io.open(pr.files(c2)["review"], "w", encoding="utf-8").write(json.dumps(rev, ensure_ascii=False))
        pr.render(c2, pdf=False)
        line = [l for l in io.open(os.path.join(c2, "FEEDBACK_LOG.md"), encoding="utf-8").read().split("\n") if l.startswith("| %d | " % row_no)][0]
        check("once the note is done, its row in the log says so - no 'to do' left", "to do" not in line
              and "done: A real general arrangement plan is on the slide." in line, line)
        code, out = out_of(cp.cmd_push_pedagogy, c2)
        sent = srv2.calls[-1][1]
        check("push sends the answers carried out with the new version", {x["id"] for x in sent.get("carried") or []}
              == {ok11["id"], okm["id"], keep["id"], cl["id"]}, sent.get("carried"))
        live = {a["item"] for a in srv2.answers if srv2.docs[-1]["items"].get(a["item"]) == a["item_hash"]}
        check("on version 2 the expert's Keep as now and decision with Claude are still their answers - not asked again; the "
              "topic the factory changed after their note is", code == 0 and srv2.docs[-1]["version"] == 2
              and live == {"1/1.1", "act/1/module", "2/1.3", "1/1.1.b"}, (out, live))
        rev = json.load(io.open(pr.files(c2)["review"], encoding="utf-8"))
        rev["modules"]["1"]["rows"]["1.1"]["proposed"]["how"] = "Trainees set the value on the real panel."
        io.open(pr.files(c2)["review"], "w", encoding="utf-8").write(json.dumps(rev, ensure_ascii=False))
        pr.render(c2, pdf=False)
        check("a row the factory changed on its own since is asked again: its answer is not carried",
              "1/1.1" not in {x["item"] for x in cp.carried(c2, pr.view(c2))} and "1/1.1.b" in {x["item"] for x in cp.carried(c2, pr.view(c2))})
        n_log = len(io.open(os.path.join(c2, "FEEDBACK_LOG.md"), encoding="utf-8").read().split("\n"))
        srv2.answer("anna.liepa@novikontas.org", "1/1.1.b", "ok")
        out_of(cp.cmd_pull, c2)
        a3 = json.load(io.open(pr.files(c2)["arch"], encoding="utf-8"))
        s1b = {s["id"]: s for s in a3["modules"][0]["sub_ilos"]}["1.1.b"]
        check("Take proposed on a Sub-ILO already re-worded neither ratifies nor logs it again",
              s1b["ratified"] == {s["id"]: s for s in a2["modules"][0]["sub_ilos"]}["1.1.b"]["ratified"]
              and len(io.open(os.path.join(c2, "FEEDBACK_LOG.md"), encoding="utf-8").read().split("\n")) == n_log, s1b)
        cp.CALL = srv

        print("\n-- the editor's address and a passing server error")
        check("the experts' link is the live staging site, not the old Vercel one",
              cp.EDITOR.startswith("https://novikontas-staging.pages.dev/classroom/editor/prep.html") and "vercel" not in cp.EDITOR)
        import urllib.error

        class Resp:
            def __init__(self, body):
                self.body = body

            def read(self):
                return self.body

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        tries = []

        def flaky(req, timeout=None):
            tries.append(1)
            if len(tries) == 1:
                raise urllib.error.HTTPError(req.full_url, 520, "unknown", {}, io.BytesIO(b""))
            return Resp(b'{"ok": true}')

        old_open, old_wait, old_key = cp.urllib.request.urlopen, cp.WAIT, os.environ.get("NOVIKONTAS_FACTORY_KEY")
        cp.urllib.request.urlopen, cp.WAIT, os.environ["NOVIKONTAS_FACTORY_KEY"] = flaky, 0, "k" * 48
        try:
            check("HTTP 520 (a passing gateway error) is tried again, and the second answer is taken",
                  cp._http("status", {"course_id": "x"}) == {"ok": True} and len(tries) == 2, tries)
            del tries[:]

            def refused(req, timeout=None):
                tries.append(1)
                raise urllib.error.HTTPError(req.full_url, 409, "conflict", {}, io.BytesIO(b'{"error": "taken"}'))

            cp.urllib.request.urlopen = refused
            try:
                cp._http("create", {})
                check("a real refusal (409) is not tried again", False)
            except cp.PortalError as e:
                check("a real refusal (409) is not tried again", len(tries) == 1 and e.status == 409 and "taken" in str(e), tries)
        finally:
            cp.urllib.request.urlopen, cp.WAIT = old_open, old_wait
            if old_key is None:
                os.environ.pop("NOVIKONTAS_FACTORY_KEY", None)
            else:
                os.environ["NOVIKONTAS_FACTORY_KEY"] = old_key

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
            check("... told to write every script to the level and teaching decided, and that a row left unanswered goes "
                  "ahead as proposed", "pedagogy_review.py decided" in args[1] and "goes ahead as proposed" in args[1], args[1])
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
