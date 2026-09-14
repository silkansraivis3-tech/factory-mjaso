#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""One command for the whole publication: validate, register, then git.

    DRY RUN (the default)              --publish                --publish --merge
    ------------------------           ---------------------    -----------------
    gates                              gates                    gates
    registry check                     registry write           registry write
    platform link check                platform link check      platform link check
    print the plan                     branch, commit, push     ... then merge to
                                       print the PR URL         the default branch

Nothing reaches git unless --publish is given, and nothing reaches the default
branch unless --merge is given on top of it. A FAIL from the gate stops the run
before git is touched at all.

Usage
-----
    publish.py --repo <android project> --course-id gas-basic
    publish.py --repo <android project> --course-id gas-basic --publish
    publish.py --repo <android project> --course-id gas-basic --publish --merge

    --version X.Y.Z   override the version from course.json (branch name)
    --strict          treat every warning as a failure
    --skip-links      skip the whole-tree link check (slow on a big repo)
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_ROOT = os.path.dirname(HERE)
PLATFORM = os.path.join(SKILL_ROOT, "knowledge", "platform.json")


def sibling_skill(name: str) -> str:
    """course-factory lives next to this skill, whether both are user skills in
    ~/.claude/skills/ or both are inside a plugin's skills/ folder. Resolving it
    as a sibling is the one rule that holds in both, and on every machine."""
    return os.path.join(os.path.dirname(SKILL_ROOT), name)


def git_remote(path: str) -> str:
    try:
        p = subprocess.run(["git", "-C", path, "remote", "get-url", "origin"],
                           capture_output=True, text=True, timeout=20)
        return (p.stdout or "").strip()
    except Exception:
        return ""


def find_repo(plat: dict, given: str | None) -> str | None:
    """Nobody should have to know where the platform repository is checked out.
    Look where the user is standing, then upwards, then in the usual places."""
    if given:
        return os.path.abspath(given)
    match = (plat.get("repository") or {}).get("remote_match", "")
    seen = []
    here = os.path.abspath(os.getcwd())
    while True:
        seen.append(here)
        parent = os.path.dirname(here)
        if parent == here:
            break
        here = parent
    for hint in (plat.get("repository") or {}).get("path_hints", []):
        seen.append(os.path.expanduser(hint))
    for cand in seen:
        if os.path.isdir(os.path.join(cand, ".git")) and match in git_remote(cand):
            return cand
    return None


def run(cmd: list[str], label: str) -> tuple[int, str]:
    print("\n>>> " + label)
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    out = (p.stdout or "") + (p.stderr or "")
    print(out.rstrip()[-4000:])
    return p.returncode, out


APPROVAL_REFUSAL = """
STOPPED - this course has not been approved for publication.

Nothing was read from the Android project and nothing was written to it.

The Android application is a PUBLISH TARGET, not a place courses are developed. A course
lives in its own folder, is reviewed in a normal browser, and reaches the app only after a
person has said, in their own words, that it is ready. For example:

    Approved. Publish this course to the NOVIKONTAS training app.

If the course has not been reviewed yet, review it first - that needs no tablet, no Android
Studio and no terminal:

    python preview.py --course <course folder> --open

Then re-run this with the approval recorded:

    --publish --approved-by "<the person who approved it>"
"""


def live_prerequisite(course_id: str, plat: dict) -> str:
    """What a PACKED course still needs before it can be taught live.

    A course publishes fine today and would then fail in a classroom, because the
    database still has to learn two things: that an unlock scope may carry a course
    prefix (005), and that a live run belongs to a course (006). Both are owner
    actions in the Supabase SQL editor, and the failure without them arrives at the
    worst possible moment - the instructor presses UNLOCK and nothing happens.

    GAS BASIC is exempt: it is the root-layout course, its scopes are the nine bare
    literals the database has always accepted, and its run lookup falls back to the
    old query. It needs neither migration to keep working.
    """
    if course_id in (plat.get("legacy_courses") or {}):
        return ""
    return (
        "\nBEFORE THIS COURSE IS TAUGHT LIVE, the owner must run these once in "
        "the Supabase SQL editor, in order:\n"
        "    backend/supabase/migrations/005_course_scoped_unlocks.sql\n"
        "    backend/supabase/migrations/006_course_scoped_runs.sql\n"
        "Until then this course cannot store an unlock or find its own class - "
        "it refuses rather than attaching to another course's run. Publishing "
        "is fine; teaching live is not. GAS BASIC is unaffected either way.\n")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo", help="the platform repository; found automatically "
                                   "when omitted")
    ap.add_argument("--course-id", required=True)
    ap.add_argument("--version")
    ap.add_argument("--platform", default=PLATFORM)
    ap.add_argument("--publish", action="store_true", help="actually branch, commit and push")
    ap.add_argument("--approved-by", metavar="NAME",
                    help="who approved this course for the tablets. REQUIRED with "
                         "--publish: the Android project is a publish target, not a "
                         "development workspace, and nothing reaches it without a "
                         "human having said so in as many words.")
    ap.add_argument("--merge", action="store_true", help="also merge into the default branch")
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--skip-links", action="store_true")
    ap.add_argument("--report", help="where to write the gate report (default: beside the repo)")
    a = ap.parse_args(argv)

    # ---- 0. the approval gate ------------------------------------------
    # PREVIEW is the default state of a course. PUBLISH is a separate act that needs a
    # human to have said so. This runs before the platform file is even opened, so a
    # mistyped publish cannot read, write or touch the Android project at all.
    if a.publish and not (a.approved_by or "").strip():
        print(APPROVAL_REFUSAL)
        return 2

    with open(a.platform, "r", encoding="utf-8") as fh:
        plat = json.load(fh)
    repo = find_repo(plat, a.repo)
    if not repo:
        print("Cannot find the NOVIKONTAS tablet platform repository.\n"
              "  Run this from inside your clone of it, or pass --repo <path>.\n"
              "  It is the repository whose origin URL contains '"
              + (plat.get("repository") or {}).get("remote_match", "?") + "'.")
        return 2
    print("platform repository: " + repo)
    report = a.report or os.path.join(
        repo, ".publish-report-" + a.course_id + ".json")
    py = sys.executable

    # ---- 1. the gate ---------------------------------------------------
    cmd = [py, os.path.join(HERE, "gates.py"), "--repo", repo,
           "--course-id", a.course_id, "--report", report, "--quiet"]
    if a.strict:
        cmd.append("--strict")
    rc, _ = run(cmd, "publication gate")
    if rc != 0:
        print("\nSTOPPED: the gate failed. Nothing was changed and git was not touched.")
        print("The findings are in " + report)
        return 1
    with open(report, "r", encoding="utf-8") as fh:
        rep = json.load(fh)
    print(f"gate: {rep['verdict']} - {len(rep['failures'])} failure(s), "
          f"{len(rep['warnings'])} warning(s), {rep.get('baselined', 0)} known and accepted")

    version = a.version or (rep.get("course") or {}).get("version") or "0.0.0"
    paths = rep["trainee_paths"] + rep["instructor_paths"]

    # ---- 2. the shared registry ---------------------------------------
    rcmd = [py, os.path.join(HERE, "registry.py"), "--repo", repo]
    rcmd.append("--write" if a.publish else "--check")
    rrc, _ = run(rcmd, "installed-course registry")
    if a.publish and rrc != 0:
        print("\nSTOPPED: the registry could not be written.")
        return 1
    if a.publish:
        reg = os.path.join(plat["asset_roots"]["trainee"], "courses", "registry.js")
        if reg not in paths:
            paths.append(reg)

    # ---- 3. the platform's own link check ------------------------------
    if not a.skip_links:
        ext = plat.get("validation", {}).get("external_scripts", {})
        vl = os.path.join(sibling_skill(ext.get("sibling_skill", "course-factory")),
                          "tablet", "scripts", "verify_links.py")
        if os.path.isfile(vl):
            lcmd = [py, vl]
            for src in plat["flavours"]["instructor"]["assets"]:
                lcmd += ["--assets", os.path.join(repo, src.replace("/", os.sep))]
            lcmd.append("--quiet")
            lrc, _ = run(lcmd, "link check across the merged asset root (course-factory)")
            if lrc != 0:
                print("\nSTOPPED: links do not resolve in the merged asset root.")
                return 1
        else:
            print("\n>>> link check skipped: course-factory is not installed beside this\n    skill, so its verify_links.py is not at " + vl)

    # ---- 4. git ---------------------------------------------------------
    gp = os.path.join(HERE, "gitpub.py")
    common = [py, gp, "--repo", repo, "--slug", a.course_id, "--version", version,
              "--course-title", (rep.get("course") or {}).get("title", a.course_id),
              "--gate-report", report]
    if (a.approved_by or "").strip():
        common += ["--approved-by", a.approved_by.strip()]
    for p in paths:
        common += ["--path", p]

    if not a.publish:
        run(common[:2] + ["plan"] + common[2:], "git plan (dry run - nothing is changed)")
        print("\n" + "=" * 72)
        print("DRY RUN COMPLETE. Nothing was committed, pushed or merged.")
        print("  course   " + a.course_id + " " + version)
        print("  gate     " + rep["verdict"])
        print("  re-run with --publish --approved-by \"<name>\" to branch, commit and push.")
        print("  (publishing needs a human's approval; reviewing does not - see preview.py)")
        print("=" * 72)
        print(live_prerequisite(a.course_id, plat), end="")
        return 0

    for sub in ("branch", "commit", "push"):
        rc, _ = run(common[:2] + [sub] + common[2:], "git " + sub)
        if rc != 0:
            print("\nSTOPPED at `git " + sub + "`. Read the refusal above.")
            return 1

    if a.merge:
        rc, _ = run(common[:2] + ["merge"] + common[2:] + ["--merge"],
                    "git merge into the default branch")
        if rc != 0:
            print("\nThe branch is pushed but NOT merged. Read the refusal above; "
                  "the pull request URL from the push step is still valid.")
            return 1
        print("\nPublished and merged.")
    else:
        print("\nPublished on a branch. Open the pull request with the URL above.")
    print(live_prerequisite(a.course_id, plat), end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
