#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Git publication for a course, with the rails that make it safe to run
unattended while several colleagues publish different courses.

Why this is a script and not a list of git commands in a skill file: every
dangerous property of this operation is a property of the ARGUMENTS, not of
the intent. `git add -A` in a tree with 266 unrelated dirty files publishes
somebody's half-finished work. `git push --force` on the default branch
destroys a colleague's course. A script can refuse; prose cannot.

What it guarantees
------------------
* Nothing is ever staged outside the pathspecs it was given. It stages with
  `git add -- <pathspec>...` and then verifies the staged set against those
  pathspecs, refusing if anything else appears (a pre-existing INDEX entry
  from the owner's own work is the normal cause).
* The default branch is DETECTED, never assumed. This repository's is
  `master`; a skill that hard-coded `main` would create a branch off nothing.
* `--force`, `--force-with-lease`, history rewriting and branch deletion are
  not implemented. There is no flag that reaches them.
* Merging into the default branch happens only with an explicit `--merge`,
  only when the branch is a fast-forward or a clean no-ff merge, and never
  when any gate reported a failure.

Subcommands
-----------
    plan     print what would happen. Touches nothing. The default.
    branch   fetch, create/checkout course/<slug>/<version> off the base
    commit   stage the pathspecs, show the diff shape, commit
    push     push the branch, print the PR URL (no gh CLI on this machine)
    merge    merge the published branch into the default branch and push it
    status   where is this course's branch relative to the base

Exit codes: 0 ok, 1 refused (a rail tripped), 2 bad usage.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys

OK, REFUSED, USAGE = 0, 1, 2


# --------------------------------------------------------------------- git io
def git(repo: str, *args: str, check: bool = True) -> str:
    """Run git and return stdout. Never interactive: git is told so."""
    env = dict(os.environ)
    env["GIT_TERMINAL_PROMPT"] = "0"          # a credential prompt would hang forever
    env["GIT_OPTIONAL_LOCKS"] = "0"
    p = subprocess.run(
        ["git", "-C", repo, *args],
        capture_output=True, text=True, env=env, encoding="utf-8", errors="replace",
    )
    if check and p.returncode != 0:
        raise RuntimeError(
            "git " + " ".join(args) + " failed (" + str(p.returncode) + ")\n"
            + (p.stderr or p.stdout or "").strip()
        )
    return (p.stdout or "").strip()


def git_ok(repo: str, *args: str) -> bool:
    try:
        git(repo, *args)
        return True
    except RuntimeError:
        return False


# ------------------------------------------------------------------ discovery
def default_branch(repo: str, remote: str = "origin") -> str:
    """The remote's own HEAD. This repo answers `master`, not `main`."""
    for probe in (
        ("symbolic-ref", "--short", f"refs/remotes/{remote}/HEAD"),
        ("rev-parse", "--abbrev-ref", f"{remote}/HEAD"),
    ):
        try:
            out = git(repo, *probe)
            if out:
                return out.split("/", 1)[-1]
        except RuntimeError:
            pass
    try:                                       # ask the remote directly
        out = git(repo, "ls-remote", "--symref", remote, "HEAD")
        m = re.search(r"ref:\s*refs/heads/(\S+)\s+HEAD", out)
        if m:
            return m.group(1)
    except RuntimeError:
        pass
    for guess in ("main", "master"):           # last resort: what exists locally
        if git_ok(repo, "rev-parse", "--verify", f"refs/heads/{guess}"):
            return guess
    raise RuntimeError("cannot determine the default branch - pass --base")


def remote_url(repo: str, remote: str = "origin") -> str:
    try:
        return git(repo, "remote", "get-url", remote)
    except RuntimeError:
        return ""


def repo_slug(url: str) -> str:
    """owner/repo out of either git@host:owner/repo.git or https://host/owner/repo.git"""
    m = re.search(r"[:/]([^/:]+/[^/]+?)(?:\.git)?/?$", url or "")
    return m.group(1) if m else ""


def branch_name(slug: str, version: str) -> str:
    safe_slug = re.sub(r"[^a-z0-9._-]+", "-", (slug or "").lower()).strip("-")
    safe_ver = re.sub(r"[^A-Za-z0-9._-]+", "-", (version or "").strip()).strip("-")
    if not safe_slug or not safe_ver:
        raise RuntimeError("a course slug and a version are both required")
    return f"course/{safe_slug}/{safe_ver}"


# ---------------------------------------------------------------- staged sets
def staged_files(repo: str) -> list[str]:
    out = git(repo, "diff", "--cached", "--name-only")
    return [l.strip() for l in out.splitlines() if l.strip()]


def under_any(path: str, pathspecs: list[str]) -> bool:
    p = path.replace("\\", "/").lower()
    for spec in pathspecs:
        s = spec.replace("\\", "/").lower().rstrip("/")
        if p == s or p.startswith(s + "/"):
            return True
    return False


def diff_shape(repo: str, cached: bool = True) -> tuple[int, int]:
    """Changed lines, and changed lines ignoring whitespace. A large gap means
    an edit reformatted files it was not asked to touch (the contract's own
    hygiene rule). Returns (lines, lines_ignoring_space)."""
    base = ["diff", "-U0"] + (["--cached"] if cached else [])
    a = git(repo, *base)
    b = git(repo, *base, "--ignore-all-space")

    def count(d: str) -> int:
        return sum(
            1 for l in d.splitlines()
            if (l.startswith("+") or l.startswith("-"))
            and not l.startswith(("+++", "---"))
        )

    return count(a), count(b)


# ------------------------------------------------------------------ the rails
class Refused(Exception):
    pass


def require_clean_of_foreign_staging(repo: str, pathspecs: list[str]) -> None:
    foreign = [f for f in staged_files(repo) if not under_any(f, pathspecs)]
    if foreign:
        raise Refused(
            "the index already holds "
            + str(len(foreign))
            + " file(s) outside this course's paths. Publishing would commit "
              "somebody else's work.\n  first few: "
            + ", ".join(foreign[:8])
            + "\n  fix: `git restore --staged <those paths>` (their working-tree "
              "changes are kept), or publish from a clean clone."
        )


def require_gates_passed(gate_report: str | None) -> dict:
    """A publish may not proceed on a gate report that is missing or FAILING.

    WARN is publishable on purpose. This platform carries real history - known
    instructor-only files in the trainee tree, a web font with no bundled copy -
    and a rail that demanded a spotless PASS would mean the working course could
    never be published at all. So: FAIL stops publication, WARN publishes and
    prints what a human should read, and the report itself keeps the detail.
    """
    if not gate_report:
        raise Refused("--gate-report is required: publication must follow the gates")
    if not os.path.isfile(gate_report):
        raise Refused("gate report not found: " + gate_report)
    with open(gate_report, "r", encoding="utf-8") as fh:
        rep = json.load(fh)
    verdict = rep.get("verdict")
    if verdict not in ("PASS", "WARN"):
        fails = rep.get("failures") or []
        raise Refused(
            "the gates did not pass (" + str(verdict) + "). Publication stops here.\n  "
            + "\n  ".join(str(f) for f in fails[:10])
            + ("\n  ... and " + str(len(fails) - 10) + " more" if len(fails) > 10 else "")
        )
    warns = rep.get("warnings") or []
    if warns:
        print(f"gate verdict WARN: {len(warns)} warning(s), "
              f"{rep.get('baselined', 0)} of them known and accepted. Publishing anyway; "
              "the report has the detail.")
    return rep


# ---------------------------------------------------------------- subcommands
def cmd_plan(a, repo: str) -> int:
    base = a.base or default_branch(repo)
    br = branch_name(a.slug, a.version)
    url = remote_url(repo)
    slug = repo_slug(url)
    cur = git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    dirty = len([l for l in git(repo, "status", "--porcelain").splitlines() if l.strip()])
    print("PLAN - nothing is changed by this subcommand")
    print(f"  repository      {repo}")
    print(f"  remote          {url or '(none)'}")
    print(f"  default branch  {base}   <- detected, not assumed")
    print(f"  current branch  {cur}")
    print(f"  working tree    {dirty} changed path(s)")
    print(f"  publish branch  {br}")
    print("  will stage ONLY:")
    for s in a.path:
        print(f"      {s}")
    if slug:
        print(f"  PR URL after push:\n      https://github.com/{slug}/compare/{base}...{br}?expand=1")
    print("  merge into " + base + ": " + ("AUTHORISED (--merge given)" if a.merge else "no (PR left for review)"))
    return OK


def cmd_branch(a, repo: str) -> int:
    base = a.base or default_branch(repo)
    br = branch_name(a.slug, a.version)
    remote = a.remote

    print(f"fetching {remote}...")
    git(repo, "fetch", remote, "--prune")

    base_ref = f"{remote}/{base}" if git_ok(repo, "rev-parse", "--verify", f"{remote}/{base}") else base

    if git_ok(repo, "rev-parse", "--verify", f"refs/heads/{br}"):
        print(f"branch {br} exists - checking it out")
        git(repo, "checkout", br)
    else:
        print(f"creating {br} off {base_ref}")
        git(repo, "checkout", "-b", br, base_ref)

    behind = git(repo, "rev-list", "--count", f"{br}..{base_ref}")
    if behind and behind != "0":
        print(f"  note: {behind} commit(s) on {base_ref} are not on this branch.")
        print("  a colleague has published since. Rebase or merge the base before pushing:")
        print(f"      git -C \"{repo}\" merge {base_ref}")
    print("on " + git(repo, "rev-parse", "--abbrev-ref", "HEAD"))
    return OK


def cmd_commit(a, repo: str) -> int:
    require_gates_passed(a.gate_report)
    cur = git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    base = a.base or default_branch(repo)
    if cur == base and not a.allow_base_commit:
        raise Refused(
            f"refusing to commit straight onto {base}. Run the `branch` "
            "subcommand first - course work is published on a branch."
        )

    require_clean_of_foreign_staging(repo, a.path)

    existing = [s for s in a.path if os.path.exists(os.path.join(repo, s))]
    if not existing:
        raise Refused("none of the given paths exist in the repository: " + ", ".join(a.path))

    git(repo, "add", "--", *existing)

    files = [f for f in staged_files(repo) if under_any(f, a.path)]
    if not files:
        print("nothing to commit - the course is already identical to the branch")
        return OK
    require_clean_of_foreign_staging(repo, a.path)

    lines, lines_ws = diff_shape(repo, cached=True)
    print(f"staged {len(files)} file(s); {lines} changed line(s) "
          f"({lines_ws} ignoring whitespace)")
    if lines_ws and lines - lines_ws > max(200, lines_ws):
        print("  WARNING: most of this diff is whitespace. Something reformatted files")
        print("  it was not asked to touch. Review before pushing.")
    for f in files[:40]:
        print("    " + f)
    if len(files) > 40:
        print(f"    ... and {len(files) - 40} more")

    msg = a.message or (
        f"{a.course_title or a.slug} {a.version}: publish to the tablet platform\n\n"
        f"course: {a.slug}\nversion: {a.version}\n"
        "Validated by course-tablet-publisher (roles, safety, links, structure).\n"
    )
    if a.dry_run:
        print("\nDRY RUN - not committing. Message would be:\n" + msg)
        return OK
    git(repo, "commit", "-m", msg)
    print("committed " + git(repo, "rev-parse", "--short", "HEAD"))
    return OK


def cmd_push(a, repo: str) -> int:
    require_gates_passed(a.gate_report)
    br = git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    base = a.base or default_branch(repo)
    if br == base:
        raise Refused(f"refusing to push {base} from this script. Course work is pushed on a branch.")
    if a.dry_run:
        print(f"DRY RUN - would push {br} to {a.remote}")
        return OK
    print(git(repo, "push", "--set-upstream", a.remote, br))
    slug = repo_slug(remote_url(repo, a.remote))
    if slug:
        pr = f"https://github.com/{slug}/compare/{base}...{br}?expand=1"
        print("\nOpen the pull request here (the GitHub CLI is not installed on this machine):")
        print("    " + pr)
    return OK


def cmd_merge(a, repo: str) -> int:
    """Only reached when the caller explicitly authorised publication to the
    default branch AND every gate passed."""
    require_gates_passed(a.gate_report)
    if not a.merge:
        raise Refused("merging into the default branch needs an explicit --merge")
    base = a.base or default_branch(repo)
    br = a.branch or git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    if br == base:
        raise Refused("nothing to merge: already on " + base)

    git(repo, "fetch", a.remote, "--prune")
    base_ref = f"{a.remote}/{base}"

    conflicts = git(repo, "merge-tree", "--write-tree", "--name-only", base_ref, br, check=False)
    if "CONFLICT" in conflicts.upper():
        raise Refused(
            "the base branch and this course branch conflict. A human resolves this - "
            "guessing at a content conflict is how a colleague's course gets deleted.\n"
            + conflicts[:800]
        )
    if a.dry_run:
        print(f"DRY RUN - would merge {br} into {base} and push")
        return OK

    git(repo, "checkout", base)
    git(repo, "merge", "--ff-only", base_ref) if git_ok(repo, "rev-parse", "--verify", base_ref) else None
    git(repo, "merge", "--no-ff", "-m", f"Merge {br} into {base}", br)
    git(repo, "push", a.remote, base)
    print(f"merged {br} into {base} and pushed. {base} is now at "
          + git(repo, "rev-parse", "--short", "HEAD"))
    git(repo, "checkout", br)
    return OK


def cmd_status(a, repo: str) -> int:
    base = a.base or default_branch(repo)
    br = a.branch or git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    git(repo, "fetch", a.remote, "--prune", check=False)
    print(f"branch {br}, base {base}")
    for ref in (f"{a.remote}/{base}", f"{a.remote}/{br}"):
        if git_ok(repo, "rev-parse", "--verify", ref):
            ahead = git(repo, "rev-list", "--count", f"{ref}..{br}", check=False)
            behind = git(repo, "rev-list", "--count", f"{br}..{ref}", check=False)
            print(f"  vs {ref}: {ahead} ahead, {behind} behind")
    return OK


# ------------------------------------------------------------------------ cli
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("command",
                    choices=["plan", "branch", "commit", "push", "merge", "status"])
    ap.add_argument("--repo", required=True, help="the platform git repository")
    ap.add_argument("--slug", default="", help="course slug, e.g. gas-basic")
    ap.add_argument("--version", default="", help="course version, e.g. 1.0.0")
    ap.add_argument("--course-title", default="")
    ap.add_argument("--path", action="append", default=[],
                    help="repo-relative path this course owns. Repeatable. "
                         "NOTHING outside these is ever staged.")
    ap.add_argument("--gate-report", help="publish.py's JSON report; required to commit/push/merge")
    ap.add_argument("--base", help="base branch; detected from the remote when omitted")
    ap.add_argument("--remote", default="origin")
    ap.add_argument("--branch", help="branch to act on (status/merge); default HEAD")
    ap.add_argument("--message", help="commit message")
    ap.add_argument("--merge", action="store_true",
                    help="authorise merging into the default branch")
    ap.add_argument("--allow-base-commit", action="store_true",
                    help=argparse.SUPPRESS)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)

    repo = os.path.abspath(a.repo)
    if not os.path.isdir(os.path.join(repo, ".git")):
        print("not a git repository: " + repo, file=sys.stderr)
        return USAGE
    if a.command in ("commit",) and not a.path:
        print("--path is required: a publish stages only the course's own paths", file=sys.stderr)
        return USAGE

    fn = {"plan": cmd_plan, "branch": cmd_branch, "commit": cmd_commit,
          "push": cmd_push, "merge": cmd_merge, "status": cmd_status}[a.command]
    try:
        return fn(a, repo)
    except Refused as e:
        print("\nREFUSED: " + str(e), file=sys.stderr)
        return REFUSED
    except RuntimeError as e:
        print("\nGIT ERROR: " + str(e), file=sys.stderr)
        return REFUSED


if __name__ == "__main__":
    sys.exit(main())
