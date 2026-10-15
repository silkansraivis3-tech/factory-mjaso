# -*- coding: utf-8 -*-
"""test_course_package - L45: a course folder the classroom takes as it is, with every task opening from its slide.

    python test_course_package.py

A two-module course is built exactly to knowledge/classroom-system.json (the classroom's own rules) - module01 with a
self-check and a module check, module02 the final assessment - and must pass the factory's checks AND the classroom's
importer (course-tablet-publisher/vendor/package-core.mjs, run with Node). Then it is broken one way at a time - each
of the classroom's "before handing over" points, and the factory's own (L35, L43) - and every break must be caught.
Also pinned: the vendored importer is byte-identical to the classroom system's, when that repository is on this computer.
"""
from __future__ import annotations

import io
import os
import shutil
import subprocess
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "check_course_package.py")
SKILLS = os.path.dirname(os.path.dirname(HERE))
VENDOR = os.path.join(SKILLS, "course-tablet-publisher", "vendor", "package-core.mjs")
ORIGINAL = r"C:\Users\raiviss\Desktop\tablet-system-win\admin\package-core.mjs"
PASS, FAIL = [], []
D = "\u2014"


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print(("  ok    " if ok else "  FAIL  ") + name + (("  -> " + str(detail)[:600]) if detail and not ok else ""))


def run(folder, *extra):
    p = subprocess.run([sys.executable, TOOL, folder] + list(extra), capture_output=True, text=True, encoding="utf-8", errors="replace")
    return p.returncode, p.stdout + p.stderr


def w(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    io.open(path, "w", encoding="utf-8", newline="\n").write(text)


TASK = ("<!DOCTYPE html><html><head><meta charset=\"utf-8\"><title>%s</title><link rel=\"stylesheet\" href=\"../assets/css/task.css\"><link rel=\"stylesheet\" href=\"../assets/gb_zoom.css\"></head>"
        "<body><img src=\"../assets/img/hull.jpg\"><script src=\"../assets/js/task.js\"></script><script src=\"../assets/gb_zoom.js\"></script><script>"
        "var late = false; addEventListener('message', e => { if (e.data && e.data.type === 'gb-timer' && e.data.remaining <= 0) { late = true; } });"
        "function done(ok, total, items, head) { window.parent.postMessage({type: 'gb-task-done', code: '%s', title: 'x', ok: ok, total: total,"
        " head: head, items: items, answered: total, of: total, timeout: late}, '*'); }%s</script></body></html>")
TEAM_HEAD = ('<meta name="task-mode" content="team"><meta name="task-roles" content="Leader|Recorder|Checker"><meta name="task-scope" content="team">')
TEAM_JS = ("var team = null; addEventListener('message', e => { if (e.data && e.data.type === 'gb-team') { team = e.data.team; } });"
           "setTimeout(() => { if (!team) { document.body.dataset.solo = '1'; } }, 2000);"
           "window.parent.postMessage({type: 'gb-task-done', scope: 'team', code: 'TT1', title: 'x', ok: 7, total: 9, head: '', items: [{t: '1.', ok: true}]}, '*');")


RECAP = ("<section class=\"slide dark recap\" id=\"s09\" data-kind=\"Summary\" data-title=\"What to take away\" data-visual=\"none\""
         " data-cue=\"- Read each point; ask for one example.\"><h2>What to take away</h2><div class=\"slide-body recap\"><ol class=\"rc-grid\" data-n=\"3\">"
         + "".join("<li class=\"rc-item\"><b class=\"rc-t\">Point %d</b><span class=\"rc-sep\"> - </span><span class=\"rc-d\">why it matters</span></li>" % i
                   for i in (1, 2, 3)) + "</ol><p class=\"rc-next\">Next: the module check</p></div></section>")


def good_course(c):
    w(os.path.join(c, "COURSE.html"), "<!DOCTYPE html><html><head><title>GAS Basic</title>"
      "<meta name=\"description\" content=\"Basic training for liquefied gas tanker cargo operations.\"></head><body>"
      "<a href=\"module01/START_HERE.html\">Module 1</a><a href=\"module02/START_HERE.html\">Final assessment</a></body></html>")
    w(os.path.join(c, "_course_shell", "course_map.js"), 'window.COURSE_MAP = [{"code":"module01","title":"Gas tankers","entry":"presentation/index.html"},'
      '{"code":"module02","title":"Final assessment","entry":"presentation/index.html"}];')
    m = os.path.join(c, "module01")
    w(os.path.join(m, "presentation", "index.html"),
      "<!DOCTYPE html><html><head><title>GAS Basic · Module 1 " + D + " Gas tankers · Instructor presentation</title>"
      "<link rel=\"stylesheet\" href=\"../assets/css/deck.css\"><link rel=\"stylesheet\" href=\"../assets/gb_zoom.css\"></head><body>"
      "<section class=\"slide active\" id=\"s01\" data-title=\"Why gas tankers are different\" data-kind=\"Theory\" data-cue=\"- Ask who has sailed on one.\">"
      "<h2>Why gas tankers are different</h2><img src=\"../assets/img/hull.jpg\"></section>"
      "<section class=\"slide\" id=\"t01\" data-kind=\"Task\" data-activity=\"SC1\" data-task-href=\"../tasks/sc1_keeping_the_cargo_liquid.html\""
      " data-title=\"SC1 " + D + " Keeping the cargo liquid\"><p class=\"act-code\">SC1</p><h2 class=\"act-title\">Keeping the cargo liquid</h2></section>"
      "<section class=\"slide\" id=\"p01\" data-kind=\"Task\" data-activity=\"P1\" data-link-hint=\"At the gas-measurement bench\" data-title=\"P1 " + D + " Take a reading\"></section>"
      "<section class=\"slide\" id=\"tt1\" data-kind=\"Task\" data-activity=\"TT1\" data-task-href=\"../tasks/tt1_plan_the_loading.html\" data-mode=\"team\""
      " data-team-size=\"3\" data-roles=\"Leader|Recorder|Checker\" data-title=\"TT1 " + D + " Plan the loading as a team\"></section>"
      + RECAP +
      "<section class=\"slide\" id=\"t02\" data-kind=\"Check\" data-activity=\"MC\" data-task-href=\"../assessment/check.html\" data-title=\"MC " + D + " Module check\"></section>"
      "<script src=\"../assets/js/deck.js\"></script><script src=\"../assets/gb_zoom.js\"></script></body></html>")
    w(os.path.join(m, "START_HERE.html"), "<meta http-equiv=\"refresh\" content=\"0; url=presentation/index.html\"><a href=\"presentation/index.html\">Open</a>")
    w(os.path.join(m, "START_HERE_EXTENDED.html"), "<a href=\"presentation/index.html\">Presentation</a><a href=\"tasks/sc1_keeping_the_cargo_liquid.html\">SC1</a>"
      "<a href=\"assessment/check.html\">Module check</a><a href=\"instructor/module_plan.html\">Plan</a>")
    w(os.path.join(m, "tasks", "sc1_keeping_the_cargo_liquid.html"), TASK % ("SC1 " + D + " Keeping the cargo liquid", "SC1", "done(3, 4, [{t: '1.', ok: true}], '');"))
    w(os.path.join(m, "tasks", "tt1_plan_the_loading.html"), (TASK % ("TT1 " + D + " Plan the loading as a team", "TT1", TEAM_JS)).replace("<head>", "<head>" + TEAM_HEAD))
    w(os.path.join(m, "assessment", "check.html"), TASK % ("MC " + D + " Module check", "MC", "var pass = 4; done(5, 6, [{t: '1.', ok: true}], 5 >= pass ? 'PASSED' : 'NOT PASSED');"))
    w(os.path.join(m, "assessment", "check_answer_key.html"), "<p>1 A, 2 C</p>")
    w(os.path.join(m, "instructor", "module_plan.html"), "<p>plan</p>")
    for f in ("css/task.css", "css/deck.css", "js/task.js", "js/deck.js", "img/hull.jpg", "gb_zoom.js", "gb_zoom.css"):
        w(os.path.join(m, "assets", f), "x")
    f2 = os.path.join(c, "module02")
    w(os.path.join(f2, "presentation", "index.html"),
      "<title>GAS Basic · Module 2 " + D + " Final assessment</title><section class=\"slide active\" data-title=\"Final assessment\" data-kind=\"Check\""
      " data-activity=\"FA\" data-task-href=\"../assessment/final.html\"></section>")
    w(os.path.join(f2, "START_HERE.html"), "<a href=\"presentation/index.html\">Open</a>")
    w(os.path.join(f2, "START_HERE_EXTENDED.html"), "<a href=\"presentation/index.html\">P</a><a href=\"assessment/final.html\">Final</a>")
    w(os.path.join(f2, "assessment", "final.html"), TASK.replace("../assets/css/task.css", "../assets/final.css").replace("<img src=\"../assets/img/hull.jpg\">", "")
      .replace("<script src=\"../assets/js/task.js\"></script>", "").replace("<link rel=\"stylesheet\" href=\"../assets/gb_zoom.css\">", "")
      .replace("<script src=\"../assets/gb_zoom.js\"></script>", "") % ("FA " + D + " Final assessment", "FA", "done(30, 36, [{t: '1.', ok: true}], 30 >= 26 ? 'PASSED' : 'NOT PASSED');"))
    w(os.path.join(f2, "assets", "final.css"), "x")


def main():
    tmp = tempfile.mkdtemp(prefix="cp_")
    try:
        master = os.path.join(tmp, "GAS_Basic")
        os.makedirs(os.path.join(master, "source_files"))
        os.makedirs(os.path.join(master, "course", "to_review"))
        os.makedirs(os.path.join(master, "course", "working_claude"))
        c = os.path.join(master, "course", "modules")
        good_course(c)

        print("-- a course folder built to the classroom's rules")
        code, out = run(master)
        node = shutil.which("node")
        check("it passes - found from the master folder", code == 0 and "Ready: the classroom takes this folder as it is" in out, out)
        if node:
            check("the classroom's own importer ran on it and would add it as GAS Basic, two modules",
                  'would add it as "GAS Basic" (id gas-basic, version 1.0.0)' in out and "2 module(s)" in out, out)
        else:
            check("without Node the factory says plainly that the importer did not run", "Node is not installed" in out, out)
        check("... from the course folder and the modules folder too", run(os.path.join(master, "course"))[0] == 0 and run(c)[0] == 0)

        print("\n-- a task page whose reporting lives in the shared task file (gb_task.js)")
        sh = os.path.join(tmp, "shared", "modules")
        shutil.copytree(c, sh)
        page = TASK % ("SC1 " + D + " Keeping the cargo liquid", "SC1", "")
        head, js = page.split("<script>")[0], page.split("<script>")[1].split("</script>")[0]
        w(os.path.join(sh, "module01", "tasks", "sc1_keeping_the_cargo_liquid.html"), head + "</body></html>")
        w(os.path.join(sh, "module01", "assets", "js", "task.js"), js + " done(3, 4, [{t: '1.', ok: true}], '');")
        code, out = run(sh, "--no-importer")
        check("it passes - gb-task-done, ok, total, items and gb-timer are read from the page's own script file",
              code == 0 and "gb-task-done" not in out and "gb-timer" not in out, out)
        w(os.path.join(sh, "module01", "assets", "js", "task.js"), "var x = 1;")
        code, out = run(sh, "--no-importer")
        check("caught: a shared script file that does not report either", code == 1 and "never reports its result (gb-task-done)" in out, out)

        def broken(name, fn, needle, importer=False):
            b = os.path.join(tmp, "b_" + str(len(PASS) + len(FAIL)), "modules")
            shutil.copytree(c, b)
            fn(b)
            code, out = run(b) if importer else run(b, "--no-importer")
            check("caught: " + name, code == 1 and needle in out, out)

        print("\n-- the classroom's own before-handover list")
        broken("a module without presentation/index.html", lambda b: os.remove(os.path.join(b, "module01", "presentation", "index.html")),
               "module01/presentation/index.html is missing")
        broken("a slide without data-title", lambda b: w(os.path.join(b, "module01", "presentation", "index.html"),
               io.open(os.path.join(c, "module01", "presentation", "index.html"), encoding="utf-8").read().replace(' data-title="Why gas tankers are different"', "")),
               "module01 slide 1 (s01) has no data-title")
        broken("a task slide pointing at a page that is not there", lambda b: os.remove(os.path.join(b, "module01", "tasks", "sc1_keeping_the_cargo_liquid.html")),
               "opens ../tasks/sc1_keeping_the_cargo_liquid.html, which is not there")
        broken("a task slide with neither a page nor a hint", lambda b: w(os.path.join(b, "module01", "presentation", "index.html"),
               io.open(os.path.join(c, "module01", "presentation", "index.html"), encoding="utf-8").read().replace(' data-link-hint="At the gas-measurement bench"', "")),
               "says neither where (data-task-href) nor how (data-link-hint)")
        broken("a task page that never reports its result", lambda b: w(os.path.join(b, "module01", "tasks", "sc1_keeping_the_cargo_liquid.html"),
               "<title>SC1 " + D + " Keeping the cargo liquid</title><p>no report</p>"), "never reports its result (gb-task-done)")
        broken("a module check without PASSED / NOT PASSED", lambda b: w(os.path.join(b, "module01", "assessment", "check.html"),
               (TASK % ("MC " + D + " Module check", "MC", "done(5, 6, [], '');"))), "must report head 'PASSED' or 'NOT PASSED'")
        broken("a script from the internet", lambda b: w(os.path.join(b, "module01", "tasks", "sc1_keeping_the_cargo_liquid.html"),
               (TASK % ("SC1 " + D + " Keeping the cargo liquid", "SC1", "done(1,1,[],'');")).replace("../assets/js/task.js", "https://cdn.example.com/x.js")),
               "loads a script from the internet")
        broken("a file over 15 MB", lambda b: open(os.path.join(b, "module01", "assets", "img", "big.jpg"), "wb").write(b"\0" * (15 * 1024 * 1024 + 1)),
               "the classroom takes at most 15 MB per file")
        broken("a working folder inside the course", lambda b: w(os.path.join(b, "notes", "draft.html"), "x"), "notes\\ is not a module")
        broken("a trainee page linking back to START_HERE.html", lambda b: w(os.path.join(b, "module01", "tasks", "sc1_keeping_the_cargo_liquid.html"),
               (TASK % ("SC1 " + D + " Keeping the cargo liquid", "SC1", "done(1,1,[],'');")).replace("<body>", "<body><a href=\"../START_HERE.html\">Back</a>")),
               "(a trainee page) links to module01/START_HERE.html, which is instructor-only")
        broken("a space in a file name", lambda b: shutil.copy(os.path.join(b, "module01", "assets", "img", "hull.jpg"), os.path.join(b, "module01", "assets", "img", "lng carrier.jpg")),
               "a space in the name: module01/assets/img/lng carrier.jpg")

        print("\n-- the factory's own rules for it")
        broken("a task page whose title does not start with its code", lambda b: w(os.path.join(b, "module01", "tasks", "sc1_keeping_the_cargo_liquid.html"),
               TASK % ("Keeping the cargo liquid", "SC1", "done(1,1,[],'');")), 'its <title> must be "SC1 ' + D + ' <title>"')
        broken("a task page no slide opens", lambda b: w(os.path.join(b, "module01", "tasks", "sc2_orphan.html"), TASK % ("SC2 " + D + " Orphan", "SC2", "done(1,1,[],'');")),
               "module01/tasks/sc2_orphan.html is opened by no slide")
        broken("two slides opening one page", lambda b: w(os.path.join(b, "module01", "presentation", "index.html"),
               io.open(os.path.join(c, "module01", "presentation", "index.html"), encoding="utf-8").read().replace(
                   'data-activity="P1" data-link-hint="At the gas-measurement bench"', 'data-activity="SC9" data-task-href="../tasks/sc1_keeping_the_cargo_liquid.html"')),
               "one slide, one task page")
        broken("a task list page for the trainee (L35)", lambda b: w(os.path.join(b, "module01", "tasks", "index.html"), "<a href=\"sc1_keeping_the_cargo_liquid.html\">1</a>"),
               "tasks/index.html is a task list")
        broken("a style reaching outside the module (L43)", lambda b: w(os.path.join(b, "module01", "tasks", "sc1_keeping_the_cargo_liquid.html"),
               (TASK % ("SC1 " + D + " Keeping the cargo liquid", "SC1", "done(1,1,[],'');")).replace("../assets/css/task.css", "../../module02/assets/final.css")),
               "reaches outside its module")
        broken("the course map not matching the modules", lambda b: w(os.path.join(b, "_course_shell", "course_map.js"),
               'window.COURSE_MAP = [{"code":"module01","title":"Gas tankers","entry":"presentation/index.html"}];'), "_course_shell/course_map.js lists module01, the folder has module01, module02")
        broken("no START_HERE_EXTENDED.html (L43)", lambda b: os.remove(os.path.join(b, "module02", "START_HERE_EXTENDED.html")), "module02/START_HERE_EXTENDED.html is missing")

        print("\n-- 2.23.0: the classroom rulebook of 2026-10-12")
        team = os.path.join("module01", "tasks", "tt1_plan_the_loading.html")
        teamsrc = io.open(os.path.join(c, team), encoding="utf-8").read()
        deck1 = io.open(os.path.join(c, "module01", "presentation", "index.html"), encoding="utf-8").read()
        broken("a team-task slide whose page does not say task-mode team", lambda b: w(os.path.join(b, team), teamsrc.replace(TEAM_HEAD, "")),
               "is opened by a team-task slide (data-mode=\"team\") but has no <meta name=\"task-mode\"")
        broken("a team page whose slide does not say data-mode team", lambda b: w(os.path.join(b, "module01", "presentation", "index.html"), deck1.replace(' data-mode="team"', "")),
               "its slide has no data-mode=\"team\"")
        broken("a team page with no task-scope", lambda b: w(os.path.join(b, team), teamsrc.replace('<meta name="task-scope" content="team">', "")),
               "must be team (one answer per team) or member")
        broken("a team page that never listens for its team", lambda b: w(os.path.join(b, team), teamsrc.replace("'gb-team'", "'other'")),
               "never listens for gb-team")
        broken("one answer per team handed in without scope: 'team'", lambda b: w(os.path.join(b, team), teamsrc.replace("scope: 'team', ", "")),
               "has no scope: 'team'")
        broken("a team size that is not a number", lambda b: w(os.path.join(b, "module01", "presentation", "index.html"), deck1.replace('data-team-size="3"', 'data-team-size="three"')),
               'data-team-size is "three"')
        broken("an answer readable in a trainee page", lambda b: w(os.path.join(b, "module01", "tasks", "sc1_keeping_the_cargo_liquid.html"),
               (TASK % ("SC1 " + D + " Keeping the cargo liquid", "SC1", "done(1,1,[],'');")).replace("<body>", '<body><button data-correct="true">-162 °C</button>')),
               "carries its answers in the page (data-correct / data-answer)")
        broken("a link into a _ folder", lambda b: (w(os.path.join(b, "module01", "_photos_raw", "a.jpg"), "x"), w(os.path.join(b, "module01", "tasks", "sc1_keeping_the_cargo_liquid.html"),
               (TASK % ("SC1 " + D + " Keeping the cargo liquid", "SC1", "done(1,1,[],'');")).replace("../assets/img/hull.jpg", "../_photos_raw/a.jpg"))),
               "a folder starting with _ is skipped by the classroom")
        nt = os.path.join(tmp, "notes23", "modules")
        shutil.copytree(c, nt)
        w(os.path.join(nt, "module01", "tasks", "sc1_keeping_the_cargo_liquid.html"),
          (TASK % ("SC1 " + D + " Keeping the cargo liquid", "SC1", "done(1,1,[],'');")).replace("timeout: late", "timeout: false").replace("<body>", "<body><button>Try again</button>"))
        code, out = run(nt, "--no-importer")
        check("noted, not blocked: a page that hears the timer but never reports timeout: true", code == 0 and "never reports timeout: true" in out, out)
        check("noted, not blocked: 'Try again' inside the classroom", code == 0 and "offers to try again" in out, out)
        code, out = run(c, "--no-importer")
        check("the good course has a team task and no notes about it", "tt1_plan_the_loading" not in out, out)

        print("\n-- 2.22.0: 3D where it makes sense, and smooth on the tablet (L46)")
        deck = io.open(os.path.join(c, "module01", "presentation", "index.html"), encoding="utf-8").read()
        three = lambda b, kinds: w(os.path.join(b, "module01", "presentation", "index.html"), deck.replace(
            '<section class="slide active" id="s01"', "".join('<section class="slide" id="v%d" data-title="Tanks %d" data-kind="Theory" data-cue="- x"'
                                                             ' data-visual="%s"></section>' % (i, i, k) for i, k in enumerate(kinds)) + '<section class="slide active" id="s01"'))
        broken("three of five teaching slides in 3D", lambda b: three(b, ["model_3d", "model_3d_scan", "model_3d", "photo"]),
               "module01: 3 of the 5 teaching slides are 3D (60 %) - at most 50 %")
        b = os.path.join(tmp, "half", "modules")
        shutil.copytree(c, b)
        three(b, ["model_3d", "photo", "model_3d", "schematic"])
        code, out = run(b, "--no-importer")
        check("... two of five is fine", code == 0, out)
        w(os.path.join(b, "module01", "assets", "lib", "three.min.js"), "/* three */")
        w(os.path.join(b, "module01", "assets", "fig", "tanks3d.js"), "var r = new THREE.WebGLRenderer({antialias: true, preserveDrawingBuffer: true});"
          " r.setPixelRatio(window.devicePixelRatio); r.shadowMap.enabled = true; r.shadowMap.type = THREE.PCFSoftShadowMap; light.shadow.mapSize.set(2048, 2048);")
        w(os.path.join(b, "module01", "assets", "fig", "pump3d.js"), "var r2 = new THREE.WebGLRenderer({antialias: true}); r2.setPixelRatio(1);"
          " r2.shadowMap.enabled = true; r2.shadowMap.autoUpdate = false;")
        code, out = run(b, "--no-importer")
        for what, needle in (("two separate renderers", "makes 2 separate 3D renderers"), ("preserveDrawingBuffer on", "keeps preserveDrawingBuffer on"),
                             ("shadows worked out again on every frame", "tanks3d.js works out its shadows again on every frame"),
                             ("an uncapped pixel ratio", "tanks3d.js draws at an uncapped pixel ratio"), ("a blurry pixel ratio of 1", "pump3d.js draws at pixel ratio 1")):
            check("noted, not blocked: " + what, code == 0 and needle in out, out)
        check("... and the quality itself is never questioned: soft shadows and a 2048 px shadow map pass without a word",
              "PCFSoftShadowMap" not in out and "1024" not in out and "pump3d.js works out its shadows" not in out, out)
        nov = os.path.join(tmp, "novis", "modules")
        shutil.copytree(c, nov)
        w(os.path.join(nov, "module01", "assets", "lib", "three.min.js"), "/* three */")
        code, out = run(nov, "--no-importer")
        check("3D in a module whose slides do not say their kind of picture is noted", code == 0 and "the 3D share cannot be counted" in out, out)

        print("\n-- 2.30.0: the recap before the module check, every picture full screen (L51) - and the person's choice wins (L26)")
        deck = lambda b: os.path.join(b, "module01", "presentation", "index.html")
        src = io.open(deck(c), encoding="utf-8").read()
        broken("a module with no recap slide", lambda b: w(deck(b), src.replace(RECAP, "")), "module01 has no recap slide straight before its module check")
        broken("a recap that is not straight before the module check", lambda b: w(deck(b), src.replace(RECAP, "").replace("<section class=\"slide\" id=\"t01\"", RECAP + "<section class=\"slide\" id=\"t01\"")),
               "module01 has no recap slide straight before its module check")
        broken("a recap with two points", lambda b: w(deck(b), src.replace("<li class=\"rc-item\"><b class=\"rc-t\">Point 3</b>", "<li><b class=\"rc-t\">Point 3</b>")),
               "the recap slide has 2 point(s)")
        broken("a task page with a picture and no picture viewer", lambda b: w(os.path.join(b, "module01", "tasks", "sc1_keeping_the_cargo_liquid.html"),
               io.open(os.path.join(c, "module01", "tasks", "sc1_keeping_the_cargo_liquid.html"), encoding="utf-8").read()
               .replace("<script src=\"../assets/gb_zoom.js\"></script>", "")), "sc1_keeping_the_cargo_liquid.html shows pictures but does not load gb_zoom.js")
        own = os.path.join(tmp, "own_way")
        shutil.copytree(master, own)
        w(deck(os.path.join(own, "course", "modules")), src.replace(RECAP, ""))
        sys.path.insert(0, HERE)
        import design_choices as dc
        dc.add(os.path.join(own, "course"), "recap", "No recap slide - the module check follows the last teaching slide",
               "I don't want a summary, the instructor sums up himself", "the modules end differently")
        code, out = run(own, "--no-importer")
        check("the operator's choice against the recap, recorded after the risk was told, is a note - never a problem",
              code == 0 and "the operator's choice S1" in out and "has no recap slide" in out, out)
        code, out = run(os.path.join(own, "course", "modules"), "--no-importer")
        check("... found the same from the modules folder", code == 0 and "the operator's choice S1" in out, out)
        w(os.path.join(own, "course", "modules", "module01", "tasks", "sc1_keeping_the_cargo_liquid.html"),
          io.open(os.path.join(c, "module01", "tasks", "sc1_keeping_the_cargo_liquid.html"), encoding="utf-8").read().replace("<script src=\"../assets/gb_zoom.js\"></script>", ""))
        code, out = run(own, "--no-importer")
        check("... and a choice covers only its own rule: the missing picture viewer is still a problem", code == 1 and "does not load gb_zoom.js" in out, out)
        if node:
            print("\n-- the classroom's importer itself")
            broken("a missing style the importer refuses", lambda b: os.remove(os.path.join(b, "module01", "assets", "css", "task.css")),
                   "the classroom's importer: Link outside the package", importer=True)

        print("\n-- the importer copy is the classroom's own")
        if os.path.isfile(ORIGINAL):
            a = io.open(ORIGINAL, encoding="utf-8").read().replace("\r\n", "\n").strip()
            b = io.open(VENDOR, encoding="utf-8").read().replace("\r\n", "\n").strip()
            check("vendor/package-core.mjs is byte-identical to the classroom system's admin/package-core.mjs", a == b,
                  "the classroom's importer changed - copy it again: %s -> %s" % (ORIGINAL, VENDOR))
        else:
            check("(the classroom system is not on this computer - the copy cannot be compared here)", os.path.isfile(VENDOR))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("\n" + "=" * 72)
    print("%d passed, %d failed" % (len(PASS), len(FAIL)))
    if FAIL:
        return 1
    print("\nA course folder built to the classroom's rules passes the factory and the classroom's own importer;\n"
          "every point of the classroom's before-handover list is caught when it is broken.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
