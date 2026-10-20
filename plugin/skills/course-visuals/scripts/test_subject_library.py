# -*- coding: utf-8 -*-
"""test_subject_library - the shared subject library at level 2a, and the ways it could go wrong.

    python test_subject_library.py

A subject library (the Gas Library first) lives outside this repository, so everything here runs
against small fake libraries in a temporary folder - no real library is needed or touched. Pinned:

  * no library = nothing found, nothing said, nothing fails - the resolver still answers from
    levels 1 and 2b;
  * a library picture counts as found only in a state that may ship on the tablets; the rest are
    blocked, never offered;
  * an AI picture is held back unless the need is a scene (--allow-ai) - never the picture of
    equipment a trainee must recognise;
  * one shared word is a coincidence, not a match;
  * a library that crashes, or an older one without --only, does not break the resolver.
"""
from __future__ import annotations

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

RESOLVE = os.path.join(HERE, "resolve_asset.py")
PASS: list[str] = []
FAIL: list[str] = []


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print(("  ok    " if ok else "  FAIL  ") + name +
          (("  -> " + str(detail)) if detail and not ok else ""))


PICS = [
    {"id": "detector_photo", "kind": "photo", "rights_state": "ATTRIBUTION_REQUIRED", "ai_generated": False,
     "path": "{root}/assets/photos/detector_photo.jpg", "description": "a portable gas detector",
     "credit": "A. Person, CC BY 4.0", "match": {"phrase": 1, "words": 2, "of": 2}},
    {"id": "detector_render_ai", "kind": "render", "rights_state": "GENERATED", "ai_generated": True,
     "path": "{root}/assets/renders/detector_render_ai.png", "description": "AI render of a gas detector",
     "match": {"phrase": 1, "words": 1, "of": 2}},
    {"id": "detector_from_manual", "kind": "photo", "rights_state": "PUBLICATION_FIGURE", "ai_generated": False,
     "path": "{root}/assets/photos/detector_from_manual.png", "description": "detector figure from a manual",
     "match": {"phrase": 1, "words": 1, "of": 2}},
    {"id": "suit_unit", "kind": "photo", "rights_state": "PUBLIC_DOMAIN", "ai_generated": False,
     "path": "{root}/assets/photos/suit_unit.jpg", "description": "a breathing unit",
     "match": {"phrase": 0, "words": 1, "of": 3}},
]

FIND_MODERN = r'''
import argparse, json
ap = argparse.ArgumentParser()
ap.add_argument("query"); ap.add_argument("--json", action="store_true")
ap.add_argument("--only"); ap.add_argument("--pictures", type=int, default=8)
a = ap.parse_args()
print(json.dumps({"query": a.query, "also_searched_as": [], "pictures": PICS}))
'''
FIND_OLD = FIND_MODERN.replace('ap.add_argument("--only"); ', "")
FIND_BROKEN = "raise SystemExit('library is broken')\n"


def fake_library(base, name, find_src):
    root = os.path.join(base, name)
    os.makedirs(os.path.join(root, "tools"))
    pics = json.loads(json.dumps(PICS).replace("{root}", root.replace("\\", "/")))
    with open(os.path.join(root, "tools", "find.py"), "w", encoding="utf-8") as fh:
        fh.write("PICS = " + repr(pics) + "\n" + find_src)
    with open(os.path.join(root, "library_config.json"), "w", encoding="utf-8") as fh:
        fh.write("{}")
    return root


def resolve(args, env_extra):
    env = dict(os.environ, **env_extra)
    p = subprocess.run([sys.executable, RESOLVE] + args + ["--json"], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env=env)
    try:
        return p.returncode, json.loads(p.stdout)
    except ValueError:
        return p.returncode, {"_raw": p.stdout + p.stderr}


def main() -> int:
    tmp = tempfile.mkdtemp(prefix="subjlib_")
    try:
        modern = fake_library(tmp, "Gas Library", FIND_MODERN)
        old = fake_library(tmp, "Old Library", FIND_OLD)
        broken = fake_library(tmp, "Broken Library", FIND_BROKEN)
        empty_project = os.path.join(tmp, "project")
        os.makedirs(empty_project)
        nowhere = {"libraries": [{"id": "gas", "name": "Gas Library", "default_locations": [os.path.join(tmp, "not mounted", "Gas Library")],
                                  "marker": ["library_config.json", "tools/find.py"], "subject_words": ["gas", "lng", "igf"]}],
                   "ship_states": ["PUBLIC_DOMAIN", "ATTRIBUTION_REQUIRED", "CLEARED", "OWNER_CLEARED",
                                   "PROJECT_OWNED", "GENERATED"]}

        print("locate")
        check("env 'off' = no library", SL.locate(env={SL.ENV_ALL: "off"}) == [])
        check("default place missing = no library, no error", SL.locate(cfg=nowhere, env={}) == [])
        libs = SL.locate(cfg=nowhere, env={SL.ENV_ALL: modern})
        check("env folder found, known by its folder name", len(libs) == 1 and libs[0]["id"] == "gas"
              and libs[0]["subject_words"], libs)
        here = dict(nowhere, libraries=[dict(nowhere["libraries"][0], default_locations=[modern])])
        check("default place found", [x["root"] for x in SL.locate(cfg=here, env={})] == [modern.replace("\\", "/")])
        check("same folder twice = one library", len(SL.locate(cfg=here, env={SL.ENV_ALL: modern})) == 1)
        check("a folder without tools/find.py is not a library",
              SL.locate(cfg=nowhere, env={SL.ENV_ALL: empty_project}) == [])

        print("covers")
        check("a gas course is on the gas subject", SL.covers("IGF Advanced - ships subject to the IGF Code", libs))
        check("a fire-fighting course is not", not SL.covers("Advanced fire fighting", libs))

        print("rights gate")
        ships = set(nowhere["ship_states"])
        r = SL.pictures("portable gas detector", libs, ship_states=ships)
        check("a shippable real photo is usable", [c["library_id"] for c in r["usable"]] == ["detector_photo"], r["usable"])
        check("a publication figure is blocked, with the reason",
              [c["library_id"] for c in r["blocked"]] == ["detector_from_manual"] and r["blocked"][0]["why"], r["blocked"])
        check("an AI picture is held back by default", [c["library_id"] for c in r["ai_held_back"]] == ["detector_render_ai"])
        check("one shared word is not a match", all(c["library_id"] != "suit_unit"
                                                    for k in ("usable", "blocked", "ai_held_back") for c in r[k]))
        check("the copy command names the library's use_asset.py",
              "use_asset.py" in r["usable"][0]["use"] and "detector_photo" in r["usable"][0]["use"])
        r = SL.pictures("portable gas detector", libs, allow_ai=True, ship_states=ships)
        check("--allow-ai offers it, still marked as AI",
              any(c["library_id"] == "detector_render_ai" and c["ai_generated"] and "never equipment" in c["why"]
                  for c in r["usable"]), r["usable"])
        r = SL.pictures("gas detector", SL.locate(cfg=nowhere, env={SL.ENV_ALL: old}), ship_states=ships)
        check("an older find.py without --only still answers", len(r["usable"]) == 1, r)
        r = SL.pictures("gas detector", SL.locate(cfg=nowhere, env={SL.ENV_ALL: broken}), ship_states=ships)
        check("a broken library is skipped, not raised", r["usable"] == [] and "did not answer" in r["searched"][0], r)

        print("resolve_asset.py")
        code, d = resolve(["portable gas detector", "--project", empty_project, "--library", modern],
                          {SL.ENV_ALL: "off"})
        check("level 2a answers from the library", code == 0 and d.get("outcome") == "FOUND"
              and d["candidates"][0].get("library_id") == "detector_photo", d)
        check("levels searched name 2a and 2b",
              any(x.startswith("2a LIBRARY") for x in d.get("levels_searched", []))
              and "2b FACTORY" in d.get("levels_searched", []), d.get("levels_searched"))
        check("blocked and held-back pictures are reported, not offered",
              {c.get("library_id") for c in d.get("blocked_by_rights", [])} == {"detector_from_manual"}
              and [c["library_id"] for c in d.get("ai_held_back", [])] == ["detector_render_ai"], d)
        code, d = resolve(["zzz no such thing", "--project", empty_project], {SL.ENV_ALL: "off"})
        check("no library: no 2a, the resolver still answers (exit 3)",
              code == 3 and d.get("outcome") == "GENERATED_ASSET_REQUIRED"
              and not any(x.startswith("2a") for x in d.get("levels_searched", [])), d)
        code, d = resolve(["portable gas detector", "--project", empty_project, "--library", modern, "--no-library"],
                          {SL.ENV_ALL: "off"})
        check("--no-library skips 2a", not any(x.startswith("2a") for x in d.get("levels_searched", [])), d)
        # 2.55.0 - a library picture's record passes the asset check in every state the library may ship
        # (check_assets.py had its own list without OWNER_CLEARED / GENERATED: IGF M02 with the Gas Library)
        import check_assets as CA
        with open(os.path.join(os.path.dirname(HERE), "source", "knowledge", "asset-pipeline.json"), encoding="utf-8") as fh:
            states = set(json.load(fh)["rights_states"]) | set(SL.config()["ship_states"])
        check("check_assets accepts every rights state of the pipeline and of a subject library",
              states <= CA.VALID_RIGHTS and {"OWNER_CLEARED", "GENERATED"} <= CA.VALID_RIGHTS, sorted(states - CA.VALID_RIGHTS))
        img = os.path.join(tmp, "assets_owner", "img")
        os.makedirs(img)
        open(os.path.join(img, "m02_lib_tray.jpg"), "wb").write(b"\xff\xd8\xff\xd9")
        with open(os.path.join(img, "_photo_meta.json"), "w", encoding="utf-8") as fh:
            json.dump({"m02_lib_tray.jpg": {"source": "Gas Library", "rights_state": "OWNER_CLEARED", "credit": "EMSA",
                                            "description": "a drip tray under a bunker manifold", "teaching_purpose": "spill"}}, fh)
        p = subprocess.run([sys.executable, "-I", os.path.join(HERE, "check_assets.py"), img, "--json"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        check("... an OWNER_CLEARED library picture is not refused for its rights state",
              "rights_state" not in p.stdout or "is not valid" not in p.stdout, p.stdout[-600:])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("\n" + "=" * 72)
    print("%d passed, %d failed" % (len(PASS), len(FAIL)))
    if FAIL:
        return 1
    print("\nThe library is read when it is there, skipped when it is not, and nothing it\n"
          "holds reaches a slide past its rights state or as an AI picture of real equipment.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
