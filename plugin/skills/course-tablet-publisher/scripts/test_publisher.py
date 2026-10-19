# -*- coding: utf-8 -*-
"""test_publisher - the approval gate, the runtime gate, and the preview surface.

Every assertion here exists because the alternative is a course reaching the production
Android repository without a person having said so, or reaching a tablet in a state where
it cannot run. Both are silent failures: an unapproved publish looks exactly like an
approved one, and a `target="_blank"` on a WebView with no tabs looks exactly like a frozen
tablet.

The fixtures are synthetic and live in a temporary folder. Nothing here reads or writes the
real Android project - which is itself the first thing tested.

    python test_publisher.py
"""
from __future__ import annotations

import base64
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
PY = sys.executable

PASS: list[str] = []
FAIL: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    (PASS if ok else FAIL).append(name + (("  -> " + detail) if detail and not ok else ""))


def run(args: list[str]) -> tuple[int, str]:
    p = subprocess.run([PY] + args, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return p.returncode, (p.stdout or "") + (p.stderr or "")


# --------------------------------------------------------------------------- fixtures
PAGE_OK = """<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><title>%s</title></head>
<body><a class="gbt-topback" href="../index.html">Back</a><p>ok</p></body></html>
"""

PAGE_BAD = """<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><title>bad</title></head>
<body>
<a class="gbt-topback" href="../index.html">Back</a>
<a href="x.html" target="_blank">no tabs on a tablet</a>
<button onclick="window.open('y.html')">no window manager</button>
<script>fetch('d.json');</script>
</body></html>
"""


def make_repo(root: str, with_bad: bool = False) -> str:
    tt = os.path.join(root, "app", "src", "main", "assets", "training_terminal",
                      "courses", "t-course")
    it = os.path.join(root, "app", "src", "instructor", "assets", "instructor_terminal",
                      "courses", "t-course")
    os.makedirs(os.path.join(tt, "tasks"), exist_ok=True)
    os.makedirs(it, exist_ok=True)
    io.open(os.path.join(tt, "course.json"), "w", encoding="utf-8").write(json.dumps({
        "id": "t-course", "title": "Test Course", "version": "1.0.0",
        "status": "draft", "modules": 1}))
    io.open(os.path.join(tt, "index.html"), "w", encoding="utf-8").write(PAGE_OK % "Test")
    io.open(os.path.join(tt, "tasks", "T1.html"), "w", encoding="utf-8").write(PAGE_OK % "T1")
    if with_bad:
        io.open(os.path.join(tt, "tasks", "bad.html"), "w",
                encoding="utf-8").write(PAGE_BAD)
    return root


def main() -> int:
    tmp = tempfile.mkdtemp(prefix="ntp_test_")
    try:
        # ---- 1 · the approval gate ---------------------------------------
        # --publish without --approved-by must refuse BEFORE anything is opened, so
        # point it at a repo path that does not exist: if it gets far enough to look,
        # the refusal came too late.
        rc, out = run([os.path.join(HERE, "publish.py"),
                       "--repo", os.path.join(tmp, "no-such-repo"),
                       "--course-id", "t-course", "--publish"])
        check("publish without approval is refused", rc != 0, "rc=%d" % rc)
        check("the refusal says the app is READ ONLY without approval",
              "not been approved" in out and "PUBLISH TARGET" in out)
        check("the refusal shows the colleague what approval sounds like",
              "Approved. Publish this course" in out)
        check("the refusal points at preview, not at git",
              "preview.py" in out and "git" not in out.split("preview.py")[0][-200:])
        check("nothing was touched before refusing",
              "platform repository" not in out and "gate" not in out.lower())

        # the same command WITH approval must get past the gate and fail later, on its
        # own merits - proving the approval check is the thing that stopped it before.
        rc2, out2 = run([os.path.join(HERE, "publish.py"),
                         "--repo", os.path.join(tmp, "no-such-repo"),
                         "--course-id", "t-course", "--publish",
                         "--approved-by", "Test Person"])
        check("with approval it proceeds past the gate",
              "not been approved" not in out2)

        # ---- 1b · nothing here merges into the default branch -------------
        # --approved-by is free text; a merge it "authorised" was authorised by nobody.
        rcm, outm = run([os.path.join(HERE, "publish.py"),
                         "--repo", os.path.join(tmp, "no-such-repo"),
                         "--course-id", "t-course", "--publish",
                         "--approved-by", "Test Person", "--merge"])
        check("publish --merge is refused", rcm != 0 and "--merge is not supported" in outm,
              outm[-300:])
        check("and refused before the platform repository is opened",
              "platform repository" not in outm)

        gr = os.path.join(tmp, "gitrepo")
        os.makedirs(gr)
        subprocess.run(["git", "init", "-q", gr], capture_output=True)
        rcg, outg = run([os.path.join(HERE, "gitpub.py"), "merge", "--repo", gr, "--merge"])
        check("gitpub merge refuses, even with --merge",
              rcg == 1 and "does not merge into the default branch" in outg, outg[-300:])

        # ---- 2 · the runtime gate ----------------------------------------
        good = make_repo(os.path.join(tmp, "good"))
        rc3, out3 = run([os.path.join(HERE, "gates.py"), "--repo", good,
                         "--course-id", "t-course"])
        check("a clean course passes the runtime gate",
              "[FAIL] runtime" not in out3, out3[-300:])

        bad = make_repo(os.path.join(tmp, "bad"), with_bad=True)
        rc4, out4 = run([os.path.join(HERE, "gates.py"), "--repo", bad,
                         "--course-id", "t-course"])
        for needle, what in (
            ('target="_blank"', "target=_blank"),
            ("window.open", "window.open"),
            ("fetch()", "fetch"),
        ):
            check("runtime gate catches " + what, needle in out4)
        check("a runtime failure stops publication", "VERDICT: FAIL" in out4)

        # the platform shell may reach the backend; a course may not
        shell = os.path.join(bad, "app", "src", "instructor", "assets",
                             "instructor_terminal", "live")
        os.makedirs(shell, exist_ok=True)
        io.open(os.path.join(shell, "live.js"), "w", encoding="utf-8").write(
            "var x = new XMLHttpRequest();")
        rc5, out5 = run([os.path.join(HERE, "gates.py"), "--repo", bad,
                         "--course-id", "t-course"])
        check("the live-class shell is exempt from the runtime gate",
              "live/live.js" not in out5 and "live\\live.js" not in out5)

        # ---- 2b · the secrets gate allows a value, never a neighbourhood ----
        # The anon key's NAME next to a service-role key used to excuse the key: the
        # allowlist looked 200 characters either side of the hit. Only the decoded
        # role of the JWT itself may let it through now.
        def jwt(payload):
            enc = lambda d: base64.urlsafe_b64encode(
                json.dumps(d).encode()).decode().rstrip("=")
            return enc({"alg": "HS256", "typ": "JWT"}) + "." + enc(payload) + ".sig0000000000"

        def secrets_run(name, body):
            r = make_repo(os.path.join(tmp, name))
            io.open(os.path.join(r, "app", "src", "main", "assets", "training_terminal",
                                 "courses", "t-course", "gb_config.js"), "w",
                    encoding="utf-8").write(body)
            return run([os.path.join(HERE, "gates.py"), "--repo", r,
                        "--course-id", "t-course"])

        _, outs = secrets_run("svc", '// anon public key -> SUPABASE_ANON_KEY\n'
                              'SUPABASE_ANON_KEY="%s";\n'
                              % jwt({"iss": "supabase", "role": "service_role"}))
        check("a service-role JWT right after SUPABASE_ANON_KEY= FAILS",
              "[FAIL] secrets" in outs and "service_role" in outs, outs[-400:])

        _, outa = secrets_run("anon", 'SUPABASE_ANON_KEY="%s";\n'
                              % jwt({"iss": "supabase", "role": "anon"}))
        check("a real anon JWT passes the secrets gate",
              "] secrets:" not in outa, outa[-400:])

        _, outn = secrets_run("noname", 'var k = "%s";\n'
                              % jwt({"iss": "supabase", "role": "authenticated"}))
        check("a JWT of any other role FAILS even with no name near it",
              "[FAIL] secrets" in outn, outn[-400:])

        _, outw = secrets_run("svcname", "// see SUPABASE_ANON_KEY\nvar r = 'service_role';\n")
        check("the text service_role next to the anon key's name is no longer excused",
              "[FAIL] secrets" in outw, outw[-400:])

        # ---- 3 · the preview surface -------------------------------------
        course = os.path.join(tmp, "course")
        os.makedirs(os.path.join(course, "tasks"), exist_ok=True)
        io.open(os.path.join(course, "module.html"), "w",
                encoding="utf-8").write(PAGE_OK % "The deck")
        io.open(os.path.join(course, "START_HERE.html"), "w",
                encoding="utf-8").write(PAGE_OK % "Start here")
        io.open(os.path.join(course, "tasks", "T1.html"), "w",
                encoding="utf-8").write(PAGE_OK % "Task one")
        io.open(os.path.join(course, "fragment.html"), "w",
                encoding="utf-8").write('<div class="f1">a fragment, not a page</div>')

        rc6, out6 = run([os.path.join(HERE, "preview.py"), "--course", course])
        review = os.path.join(course, "REVIEW.html")
        check("preview writes REVIEW.html", os.path.isfile(review))
        html = io.open(review, encoding="utf-8").read() if os.path.isfile(review) else ""
        check("the review page links the deck", "module.html" in html)
        check("the review page links the task", "tasks/T1.html" in html)
        check("a figure fragment is not offered as a page", "fragment.html" not in html)
        check("the review page states the approval sentence",
              "Approved. Publish this course" in html)
        check("the review page carries no course CSS",
              'href="assets/' not in html and "<link" not in html)
        check("preview reports file:// as safe for clean output",
              "file:// safe" in out6, out6[-200:])

        # and it must SAY SO when the course would not survive file://
        io.open(os.path.join(course, "tasks", "T2.html"), "w", encoding="utf-8").write(
            PAGE_OK % "T2" + "<script>fetch('x.json');</script>")
        rc7, out7 = run([os.path.join(HERE, "preview.py"), "--course", course])
        check("preview warns when a page would not work as a file",
              "will NOT work" in out7, out7[-200:])

        # ---- 3b · live unlock scopes cannot collide ----------------------
        # The scope is what an instructor's unlock is stored under. A collision does
        # not throw and does not show: the lock button goes green either way, and a
        # different course's trainees find their assessment open.
        sc = os.path.join(tmp, "scopes")
        tt = os.path.join(sc, "app", "src", "main", "assets",
                          "training_terminal", "courses")

        def course(folder, cid):
            os.makedirs(os.path.join(tt, folder), exist_ok=True)
            io.open(os.path.join(tt, folder, "course.json"), "w",
                    encoding="utf-8").write(json.dumps(
                        {"id": cid, "title": folder, "version": "1.0.0",
                         "status": "draft", "modules": 2}))

        course("course-a", "course-b")          # id does not match its folder
        rc8, out8 = run([os.path.join(HERE, "gates.py"), "--repo", sc,
                         "--course-id", "course-a"])
        check("scope gate: an id that disagrees with its folder fails",
              "[FAIL] scopes" in out8 and "folder" in out8, out8[-200:])

        shutil.rmtree(os.path.join(tt, "course-a"))
        course("Course_A", "Course_A")          # not a slug the database accepts
        rc9, out9 = run([os.path.join(HERE, "gates.py"), "--repo", sc,
                         "--course-id", "Course_A"])
        check("scope gate: an id the database would refuse fails",
              "not a lowercase slug" in out9, out9[-200:])

        shutil.rmtree(os.path.join(tt, "Course_A"))
        course("course-a", "course-a")
        course("course-b", "course-b")
        rc10, out10 = run([os.path.join(HERE, "gates.py"), "--repo", sc,
                           "--course-id", "course-a"])
        check("scope gate: two well-formed courses do NOT collide",
              "[FAIL] scopes" not in out10, out10[-200:])
        check("scope gate: and it says how many distinct scopes exist",
              "distinct live unlock scopes" in out10)

        # ---- 4 · the review surface can never be published ----------------
        plat = json.load(io.open(os.path.join(HERE, "..", "knowledge", "platform.json"),
                                 encoding="utf-8"))
        globs = plat["role_rules"]["internal_globs"]
        check("REVIEW.html is internal by pattern",
              any("REVIEW" in g for g in globs))

        # ---- 5 · gitpub commit / push on a real repository (2.49.4) ----------
        pr = os.path.join(tmp, "pubrepo")
        os.makedirs(pr)
        g = lambda *a: subprocess.run(["git", "-c", "core.quotepath=false", "-C", pr, *a], capture_output=True,
                                      text=True, encoding="utf-8", errors="replace")
        g("init", "-q", "-b", "main")
        g("config", "user.name", "Test"); g("config", "user.email", "t@example.org")
        io.open(os.path.join(pr, "README.md"), "w", encoding="utf-8").write("base\n")
        g("add", "README.md"); g("commit", "-q", "-m", "base")
        g("checkout", "-q", "-b", "course/t-course/1.0.0")
        cdir = os.path.join(pr, "courses", "t-course")
        os.makedirs(cdir)
        io.open(os.path.join(cdir, "Drošība.png"), "wb").write(b"\x89PNG\r\n\x1a\n")
        io.open(os.path.join(cdir, "index.html"), "w", encoding="utf-8").write(PAGE_OK % "T")
        okrep = os.path.join(tmp, "gate_ok.json")
        io.open(okrep, "w", encoding="utf-8").write(json.dumps({"verdict": "PASS"}))
        gp = os.path.join(HERE, "gitpub.py")
        base = ["--repo", pr, "--slug", "t-course", "--version", "1.0.0", "--gate-report", okrep, "--base", "main"]
        rcc, outc = run([gp, "commit"] + base + ["--path", "courses/t-course", "--message", "t-course 1.0.0"])
        check("gitpub commit: a course file with a Latvian name (Drošība.png) is the course's own, not 'outside its paths'",
              rcc == 0 and "outside this course's paths" not in outc
              and "Drošība.png" in g("show", "--name-only", "--format=", "HEAD").stdout, outc[-400:])
        rcp, outp = run([gp, "push"] + base + ["--dry-run"])
        check("gitpub push: the course's own branch may be pushed", rcp == 0 and "would push course/t-course/1.0.0" in outp, outp[-300:])
        g("checkout", "-q", "-b", "staging")
        rcs, outs = run([gp, "push"] + base + ["--dry-run"])
        check("gitpub push: a shared branch that is not the base (staging) is refused", rcs == 1 and "only a course branch" in outs, outs[-300:])
        g("checkout", "-q", "-b", "course/other-course/2.0.0")
        rco, outo = run([gp, "push"] + base + ["--dry-run"])
        check("gitpub push: another course's branch is refused under this course's slug", rco == 1 and "course/t-course/" in outo, outo[-300:])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("=" * 72)
    print("test_publisher - PREVIEW, APPROVAL, PUBLISH")
    print("=" * 72)
    for p in PASS:
        print("  ok    " + p)
    for f in FAIL:
        print("  FAIL  " + f)
    print()
    print("%d passed, %d failed" % (len(PASS), len(FAIL)))
    if not FAIL:
        print("\nThe gate refuses an unapproved publish before it opens anything, the "
              "runtime\nchecks catch what fails silently on a tablet, and the review "
              "surface cannot ship.")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
