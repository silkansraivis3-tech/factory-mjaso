# -*- coding: utf-8 -*-
"""test_course_libraries - one parent, one library per subject, one common; every finding in its place.

    python test_course_libraries.py

Everything runs against a temporary Course Libraries folder through NOVIKONTAS_COURSE_LIBRARIES and a
fake Gas Library through NOVIKONTAS_GAS_LIBRARY - the real Drive is never read or written. Pinned:

  * create makes a library from the template, registers it, and refuses the same id twice, the
    factory repository and a course folder;
  * ensure returns the course's libraries in reading order (subject, then common), makes common once,
    makes a subject library only when told its id, and says so plainly when it cannot;
  * route sends a convention's finding to common, a subject finding to the subject library, a general
    picture to common, and obeys --library;
  * a contribution through the client lands in the routed library, and its find.py finds it;
  * find reads two libraries together and labels every result, keeping CONFLICT and distribution;
  * the template's own tools run in a fresh library: find, contribute, build_library, use_asset;
  * the Gas Library entry of the config still resolves.
"""
from __future__ import annotations

import base64
import json
import os
import shutil
import subprocess
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import subject_library as SL  # noqa: E402

CLIENT = os.path.join(HERE, "subject_library.py")
PASS: list[str] = []
FAIL: list[str] = []
PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==")
GAS_TITLE = "Basic training for liquefied gas tanker cargo operations (STCW A-V/1-2-1)"


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print(("  ok    " if ok else "  FAIL  ") + name +
          (("  -> " + str(detail)[:900]) if detail and not ok else ""))


def clean_env(**extra):
    env = {k: v for k, v in os.environ.items() if not k.startswith("NOVIKONTAS_")}
    env.update(extra)
    return env


def run(args, env, script=CLIENT, timeout=600):
    p = subprocess.run([sys.executable, script] + args, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", env=dict(env, PYTHONIOENCODING="utf-8"), timeout=timeout)
    return p.returncode, p.stdout + p.stderr


def run_json(args, env, script=CLIENT):
    code, out = run(args, env, script)
    try:
        return code, json.loads(out[out.index("{"):])
    except ValueError:
        return code, {"_raw": out}


def read(p):
    with open(p, encoding="utf-8") as fh:
        return fh.read()


def main() -> int:
    tmp = tempfile.mkdtemp(prefix="courselibs_")
    try:
        parent = os.path.join(tmp, "Drive", "Course Libraries")
        os.makedirs(os.path.dirname(parent))
        gas = os.path.join(tmp, "Drive", "Gas Library")
        shutil.copytree(SL.TEMPLATE, gas)                       # a stand-in for the Gas Library, read and written here only
        E = clean_env(NOVIKONTAS_COURSE_LIBRARIES=parent, NOVIKONTAS_GAS_LIBRARY=gas)
        with open(os.path.join(gas, "knowledge", "FACTS.md"), "a", encoding="utf-8") as fh:
            fh.write("| Oxygen after inerting | 5 % or less | ICS TSG 6.6.2 | GB M02 | CONFLICT (C2) |\n")

        print("where the parent is looked for")
        shared = os.path.join(tmp, "Shared drives", "NOVIKONTAS Courses", "Course Libraries")
        os.makedirs(shared)
        mine = os.path.join(tmp, "My Drive", "Course Libraries")
        cfg = {"course_libraries": {"default_parents": [os.path.join(tmp, "Shared drives", "*", "Course Libraries"), mine]}}
        got = SL.parents(cfg, {})
        check("a shared drive of any name that holds Course Libraries is read first, a person's own Drive after it",
              got == [shared, mine], got)
        os.rmdir(shared)
        check("... and a shared drive that is not there is not listed", SL.parents(cfg, {}) == [mine], SL.parents(cfg, {}))

        # a colleague's computer: nothing of their own; the two folders were shared with them and each has a shortcut
        short = os.path.join(tmp, "colleague", ".shortcut-targets-by-id")
        their_parent = os.path.join(short, "1AbC", "Course Libraries")
        shutil.copytree(SL.TEMPLATE, os.path.join(their_parent, "Common"))
        shutil.copytree(SL.TEMPLATE, os.path.join(short, "9xYz", "Gas Library"))
        with open(os.path.join(their_parent, "LIBRARIES.json"), "w", encoding="utf-8") as fh:
            json.dump({"libraries": [
                {"id": "gas", "name": "NOVIKONTAS Gas Library", "path": "Q:/the owner's own/My Drive/Gas Library",
                 "subject_words": ["gas", "lng"]},
                {"id": "common", "name": "NOVIKONTAS Common Library", "path": "Common", "common": True}]}, fh)
        theirs = json.loads(json.dumps(SL.config()))
        theirs["course_libraries"]["default_parents"] = [os.path.join(short, "*", "Course Libraries")]
        theirs["libraries"][0]["default_locations"] = [os.path.join(tmp, "colleague", "My Drive", "Gas Library"),
                                                       os.path.join(short, "*", "Gas Library")]
        here = {x["id"]: x for x in SL.locate(theirs, clean_env())}
        check("a folder shared with a colleague and added as a shortcut is found by itself: Common through the registry, "
              "the Gas Library where their own computer mounts it - not at the owner's path",
              set(here) == {"gas", "common"} and "9xYz" in here["gas"]["root"] and "1AbC" in here["common"]["root"], here)

        print("create")
        e = SL.create("fire-fighting", "NOVIKONTAS Fire Fighting Library", "fire,fire-fighting,extinguisher",
                      "A-VI/3", env=E)
        ff = e["root"]
        reg = json.loads(read(os.path.join(parent, "LIBRARIES.json")))
        check("the parent, its registry and its read-me are made",
              os.path.isfile(os.path.join(parent, "00_READ_ME_FIRST.md")) and isinstance(reg.get("libraries"), list))
        ent = next((x for x in reg["libraries"] if x["id"] == "fire-fighting"), {})
        check("the library is registered with a relative path, words, STCW and date",
              ent.get("path") == "Fire Fighting" and "fire" in ent.get("subject_words", []) and ent.get("stcw") == ["A-VI/3"]
              and ent.get("created"), ent)
        check("the folder is made from the template (tools, knowledge, assets, documents)",
              all(os.path.isfile(os.path.join(ff, p)) for p in (
                  "tools/find.py", "tools/search.py", "tools/use_asset.py", "tools/contribute.py", "tools/build_library.py",
                  "knowledge/FACTS.md", "knowledge/GLOSSARY.md", "knowledge/REGULATIONS.md", "knowledge/INBOX.md",
                  "knowledge/topics.json", "knowledge/synonyms.json", "knowledge/SOURCES.json",
                  "assets/ASSETS.json", "documents/DOCUMENTS.json", "library_config.json", "CLAUDE.md")))
        lc = json.loads(read(os.path.join(ff, "library_config.json")))
        check("its config and read-me name the library, not gas",
              lc["library_name"] == "NOVIKONTAS Fire Fighting Library" and lc["library_id"] == "fire-fighting"
              and "Fire Fighting Library" in read(os.path.join(ff, "CLAUDE.md"))
              and "{{" not in read(os.path.join(ff, "00_READ_ME_FIRST.md"))
              and "gas" not in read(os.path.join(ff, "CLAUDE.md")).lower(), lc)
        check("the Gas Library is registered by its absolute path",
              any(x["id"] == "gas" and os.path.isabs(x["path"]) and SL._key(x["path"]) == SL._key(gas)
                  for x in reg["libraries"]), reg["libraries"])
        try:
            SL.create("fire-fighting", "Again", "fire", env=E)
            check("the same id twice is refused", False)
        except SL.Refused as ex:
            check("the same id twice is refused", "exists" in str(ex), ex)
        code, out = run(["create", "--id", "gas", "--name", "Gas again", "--subject-words", "gas"], E)
        check("... also an id the config knows (gas), exit 2", code == 2 and "REFUSED" in out, out)
        os.makedirs(os.path.join(tmp, "IGF course", "working_claude"))
        for label, lid, where in (("the factory repository", "repo-test", os.path.join(HERE, "libs_here")),
                                  ("a course folder", "course-test", os.path.join(tmp, "IGF course", "x"))):
            try:
                SL.create(lid, "X", "x", parent=where, env=E)
                check(f"never into {label}", False)
            except SL.Refused as ex:
                check(f"never into {label}", not os.path.exists(where) and ("repository" in str(ex) or "course" in str(ex)), ex)

        print("ensure")
        code, d = run_json(["ensure", GAS_TITLE + " - Module 1 Gas properties", "--json", "--course", "GAS BASIC"], E)
        ids = [x["id"] for x in d.get("libraries", [])]
        check("a gas course: its subject library, then common", code == 0 and ids == ["gas", "common"], d)
        check("common is made the first time", d.get("created") == ["common"]
              and os.path.isfile(os.path.join(parent, "Common", "tools", "find.py")), d)
        code, d = run_json(["ensure", GAS_TITLE, "--json"], E)
        reg = json.loads(read(os.path.join(parent, "LIBRARIES.json")))
        check("... and only once", code == 0 and d.get("created") == []
              and sum(1 for x in reg["libraries"] if x["id"] == "common") == 1, d)
        check("the course is recorded with the libraries it uses",
              all("GAS BASIC" in x.get("courses", []) for x in reg["libraries"] if x["id"] in ("gas", "common")))
        code, d = run_json(["ensure", "Advanced training in fire fighting (STCW A-VI/3)", "--json"], E)
        check("a fire-fighting course gets the fire library", code == 0
              and [x["id"] for x in d["libraries"]] == ["fire-fighting", "common"], d)
        surv = "Proficiency in survival craft and rescue boats (STCW A-VI/2-1)"
        code, d = run_json(["ensure", surv, "--json"], E)
        check("no subject library and no id: exit 3, the model is told to choose one",
              code == 3 and "Choose an id" in d.get("say", "") and [x["id"] for x in d["libraries"]] == ["common"], d)
        code, d = run_json(["ensure", surv, "--json", "--subject-id", "survival-craft", "--name",
                            "NOVIKONTAS Survival Craft Library", "--subject-words", "survival craft,rescue boat,lifeboat",
                            "--stcw", "A-VI/2-1"], E)
        check("with --subject-id it is made, nothing asked", code == 0 and d.get("created") == ["survival-craft"]
              and [x["id"] for x in d["libraries"]] == ["survival-craft", "common"]
              and os.path.isfile(os.path.join(parent, "Survival Craft", "tools", "find.py")), d)
        code, d = run_json(["ensure", surv, "--json"], E)
        check("... and found by its words next time", code == 0 and d["libraries"][0]["id"] == "survival-craft", d)
        code, d = run_json(["ensure", GAS_TITLE, "--json"],
                           clean_env(NOVIKONTAS_COURSE_LIBRARIES=os.path.join(tmp, "not mounted", "My Drive", "Course Libraries")))
        check("no parent reachable: exit 3, the course goes on without a library",
              code == 3 and "without a library" in d.get("say", "") and not os.path.exists(os.path.join(tmp, "not mounted")), d)

        print("route")
        code, d = run_json(["route", "regulation", "MARPOL Annex VI regulation 14 - sulphur limit",
                            "--source", "MARPOL Annex VI, reg. 14", "--course", GAS_TITLE, "--json"], E)
        check("a MARPOL regulation -> common, with the reason", code == 0 and d["library"] == "common"
              and "MARPOL" in d["why"], d)
        code, d = run_json(["route", "fact", "Methane boiling point -161.5 C",
                            "--source", "SIGTTO LGHP 4th ed., p. 18", "--course", GAS_TITLE, "--json"], E)
        check("a gas fact -> the subject library", code == 0 and d["library"] == "gas" and d["why"], d)
        code, d = run_json(["route", "fact", "Basic training for liquefied gas tanker cargo operations lasts at least 3 months of sea service",
                            "--source", "STCW Code A-V/1-2", "--course", GAS_TITLE, "--json"], E)
        check("a fact about the course's subject stays with the subject, though it is quoted from STCW",
              code == 0 and d["library"] == "gas", d)
        code, d = run_json(["route", "fact", "A rest period of at least 10 hours in any 24-hour period",
                            "--source", "STCW Code A-VIII/1", "--course", GAS_TITLE, "--json"], E)
        check("... and a fact every ship shares, quoted from STCW, goes to common", code == 0 and d["library"] == "common", d)
        code, d = run_json(["route", "picture", "trainees in a classroom listening to an instructor", "--course", GAS_TITLE,
                            "--json"], E)
        check("a general picture -> common", code == 0 and d["library"] == "common", d)
        code, d = run_json(["route", "picture", "LNG bunkering hose with crew at the manifold", "--course", GAS_TITLE,
                            "--json"], E)
        check("a picture with the subject's words stays in the subject library", code == 0 and d["library"] == "gas", d)
        code, d = run_json(["route", "regulation", "MARPOL Annex VI", "--source", "MARPOL", "--library", "gas", "--json"], E)
        check("--library overrides", code == 0 and d["library"] == "gas" and "--library" in d["why"], d)
        code, d = run_json(["route", "fact", "Something", "--source", "a manual", "--json"], E)
        check("several subject libraries and no course: exit 3, not a guess", code == 3 and d["library"] is None, d)

        print("contribute through the client")
        code, out = run(["contribute", "--course", GAS_TITLE, "fact", "Methane boiling point", "-161.5 C at 1 bar",
                         "--source", "SIGTTO LGHP 4th ed., p. 18", "--by", "test"], E)
        check("a gas fact lands in the Gas Library's inbox", code == 0 and "-> gas" in out
              and "Methane boiling point" in read(os.path.join(gas, "knowledge", "INBOX.md")), out)
        code, out = run(["contribute", "regulation", "MARPOL Annex VI regulation 14", "0.50 % m/m sulphur outside ECAs",
                         "--source", "MARPOL Annex VI, reg. 14.1.3", "--course", GAS_TITLE, "--by", "test"], E)
        cin = read(os.path.join(parent, "Common", "knowledge", "INBOX.md"))
        check("a MARPOL regulation lands in Common's inbox as a regulation", code == 0 and "-> common" in out
              and "| regulation | NEW | MARPOL Annex VI regulation 14" in cin
              and "MARPOL" not in read(os.path.join(gas, "knowledge", "INBOX.md")), out)
        code, d = run_json(["find", "methane boiling point", "--library", "gas", "--json"], E)
        check("... and the library's find.py finds it afterwards", code == 0 and any(
            r["library"] == "gas" and "Methane boiling point" in r["row"] for r in d.get("inbox_not_reviewed", [])), d)

        print("find across two libraries")
        with open(os.path.join(parent, "Common", "knowledge", "FACTS.md"), "a", encoding="utf-8") as fh:
            fh.write("| Oxygen in air | 20.9 % | SOLAS II-2 | all | AGREED |\n")
        code, d = run_json(["find", "oxygen", "--course", GAS_TITLE, "--json"], E)
        check("subject first, then common", [x["id"] for x in d.get("libraries", [])] == ["gas", "common"], d.get("libraries"))
        facts = d.get("facts", [])
        check("every result labelled with its library",
              {f["library"] for f in facts} == {"gas", "common"} and all("library" in r for s in
                                                                        ("pictures", "documents", "passages", "glossary")
                                                                        for r in d.get(s, [])), facts)
        check("the gas CONFLICT row keeps its flag, the common row has none",
              any(f["library"] == "gas" and f["conflict"] for f in facts)
              and all(not f["conflict"] for f in facts if f["library"] == "common"), facts)
        code, out = run(["find", "oxygen", "--course", GAS_TITLE], E)
        check("text mode names each library", "[gas, subject]" in out and "[common, common]" in out, out[-600:])
        code, d = run_json(["find", "MARPOL", "--library", "common", "--json"], E)
        check("--library narrows it", [x["id"] for x in d["libraries"]] == ["common"]
              and all(r["library"] == "common" for r in d.get("inbox_not_reviewed", [])) and d["inbox_not_reviewed"], d)

        print("the template's tools in a fresh library")
        T = os.path.join(ff, "tools")
        code, d = run_json(["empty library", "--json"], E, os.path.join(T, "find.py"))
        check("find.py answers on an empty library and says its documents are not searchable yet",
              code == 0 and d.get("searchable") is False and "not searchable" in (d.get("not_searchable") or ""), d)
        src = os.path.join(tmp, "download")
        os.makedirs(src)
        pic = os.path.join(src, "extinguisher_co2.png")
        open(pic, "wb").write(PNG)
        code, out = run(["contribute", "--library", "fire-fighting", "picture", pic, "--source", "Wikimedia Commons",
                         "--page-url", "https://commons.wikimedia.org/wiki/File:x.png", "--licence", "CC BY 4.0",
                         "--rights-state", "ATTRIBUTION_REQUIRED", "--credit", "A. Person, CC BY 4.0",
                         "--description", "a portable CO2 fire extinguisher on a bulkhead bracket",
                         "--teaching-purpose", "recognise the CO2 extinguisher", "--visually-verified",
                         "yes - a red CO2 extinguisher seen 2026-11-10", "--by", "test"], E)
        assets = json.loads(read(os.path.join(ff, "assets", "ASSETS.json")))["assets"]
        check("contribute.py picture + build_library.py: the picture is a library asset",
              code == 0 and len(assets) == 1 and assets[0]["rights_state"] == "ATTRIBUTION_REQUIRED"
              and os.path.isfile(os.path.join(ff, assets[0]["file"])), out[-800:])
        code, d = run_json(["CO2 fire extinguisher", "--json", "--only", "pictures"], E, os.path.join(T, "find.py"))
        check("find.py finds it by description", code == 0 and [p["id"] for p in d.get("pictures", [])] == [assets[0]["id"]], d)
        r = SL.pictures("CO2 fire extinguisher", [x for x in SL.locate(env=E) if x["id"] == "fire-fighting"])
        check("the resolver offers it as usable", [c["library_id"] for c in r["usable"]] == [assets[0]["id"]], r)
        mod = os.path.join(tmp, "IGF course", "course", "modules", "module03")
        code, out = run([assets[0]["id"], mod, "--note", "M03 s04"], E, os.path.join(T, "use_asset.py"))
        meta = os.path.join(mod, "assets", "img", "_photo_meta.json")
        check("use_asset.py copies it into a module with its provenance", code == 0 and os.path.isfile(meta)
              and json.loads(read(meta))[os.path.basename(assets[0]["file"])]["library_id"] == assets[0]["id"], out)
        code, out = run(["picture", pic, "--source", "x"], E, os.path.join(T, "contribute.py"))
        check("a duplicate picture is reported, not added", code == 0 and "already in the library" in out, out)
        code, out = run(["picture", os.path.join(src, "nope.png")], E, os.path.join(T, "contribute.py"))
        check("a picture without its file is refused", code == 2 and "REFUSED" in out, out)
        code, out = run(["build_library.py"][1:], clean_env(), os.path.join(T, "build_library.py"))
        check("build_library.py without a KB builder still builds", code == 0 and "catalog.html" in out
              and "NOVIKONTAS Fire Fighting Library" in read(os.path.join(ff, "catalog.html")), out[-600:])
        try:
            import pymupdf
        except ImportError:
            pymupdf = None
        if pymupdf:
            pdf = os.path.join(src, "fire_triangle_note.pdf")
            doc = pymupdf.open()
            doc.new_page().insert_text((72, 72), "The fire triangle: heat, fuel and oxygen. Remove one and the fire goes out.")
            doc.save(pdf)
            doc.close()
            code, out = run(["contribute", "--library", "fire-fighting", "document", pdf, "--type", "guidance",
                             "--title", "Fire triangle note", "--origin", "made for this test", "--distribution", "SHARE"], E)
            check("contribute.py document + the factory's kb_build.py: the documents become searchable",
                  code == 0 and os.path.isfile(os.path.join(ff, "KNOWLEDGE_BASE", "SOURCE_MANIFEST.json")), out[-900:])
            code, d = run_json(["fire triangle", "--json"], E, os.path.join(T, "find.py"))
            check("... and find.py returns the passage and the document with its distribution",
                  d.get("searchable") is True and d.get("passages")
                  and any(x["distribution"] == "SHARE" for x in d.get("documents", [])), d)
        else:
            check("PyMuPDF missing - the document index was not tested", False, "pip install pymupdf")

        print("the Gas Library entry of the config")
        cfg = SL.config()
        spec = next(x for x in cfg["libraries"] if x["id"] == "gas")
        check("the config holds the Gas Library in Course Libraries first, and still at its old place G:/My Drive/Gas Library",
              spec["default_locations"][0] == "G:/My Drive/Course Libraries/Gas Library"
              and "G:/My Drive/Gas Library" in spec["default_locations"] and "gas" in spec["subject_words"])
        fake = dict(cfg, course_libraries={}, libraries=[dict(spec, env=None, default_locations=[gas])])
        libs = SL.locate(cfg=fake, env={})
        check("its default place resolves as before, id gas", [x["id"] for x in libs] == ["gas"]
              and SL.covers("IGF Advanced - ships subject to the IGF Code", libs), libs)
        libs = SL.locate(env=clean_env(NOVIKONTAS_COURSE_LIBRARIES="off", NOVIKONTAS_GAS_LIBRARY=gas))
        check("... and by its own env var, with no registry", [x["id"] for x in libs] == ["gas"], libs)
        check("NOVIKONTAS_SUBJECT_LIBRARIES=off still means no library at all",
              SL.locate(env=dict(E, NOVIKONTAS_SUBJECT_LIBRARIES="off")) == [])
        code, out = run(["locate"], E)
        check("locate lists registry and config libraries with whether each is there",
              code == 0 and all(i in out for i in ("gas", "common", "fire-fighting", "survival-craft")) and "here" in out, out)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("\n" + "=" * 72)
    print("%d passed, %d failed" % (len(PASS), len(FAIL)))
    if FAIL:
        return 1
    print("\nEvery course finds its libraries, a missing one is made only when its id is given, and\n"
          "every finding goes to the library it belongs in - said in one line.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
