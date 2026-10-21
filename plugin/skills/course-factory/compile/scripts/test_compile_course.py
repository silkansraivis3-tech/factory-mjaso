# -*- coding: utf-8 -*-
"""test_compile_course - the course's own pages are built from what is approved and built, never typed.

    python test_compile_course.py

Pinned:
  * COURSE.html carries the approved course title and a description the classroom's importer reads; the module list
    (course_map.js) is data, in folder order, each title from the module's approved script;
  * a planned module not built yet is named on the course page, never listed as if it were there;
  * START_HERE.html opens the deck at once; START_HERE_EXTENDED.html links every page the deck opens and the
    module's instructor files - and nothing outside the module (L43);
  * a task slide whose page is missing is reported (the worst failure in the room);
  * the same input gives the same bytes; a page changed by hand is not overwritten without --force;
  * the course title - the classroom's course ID - never changes without --retitle, also against a hand-made page;
  * check_course_package.py finds nothing wrong with the course files and the start pages.
"""
from __future__ import annotations

import io
import json
import os
import re
import shutil
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import test_compile_module as t  # noqa: E402  - the same fixture course, the same runner
from test_compile_module import cs, run  # noqa: E402

COURSE = os.path.join(HERE, "compile_course.py")
PACKAGE = os.path.join(t.SKILL, "scripts", "check_course_package.py")
PASS, FAIL = [], []
TITLE = "Basic training for ships subject to the IGF Code"
ARCH = {"course": {"title": TITLE, "course_language": "English"},
        "modules": [{"module": 1, "title": "Planned title of module 1"}, {"module": 2, "title": "Fuel systems"}],
        "final_assessment": {"topic": "3"}}


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print(("  ok    " if ok else "  FAIL  ") + name + (("  -> " + str(detail)[:600]) if detail and not ok else ""))


def read(*p):
    return io.open(os.path.join(*p), encoding="utf-8").read()


def main():
    tmp = tempfile.mkdtemp(prefix="compile_course_")
    try:
        c, md = t.new_course(tmp, t.script())
        root = os.path.dirname(md)
        code, out = run(t.COMPILE, c, "--module", "1")
        assert code in (0, 1) and os.path.isfile(os.path.join(md, "presentation", "index.html")), out

        code, out = run(COURSE, c)
        check("no approved architecture - nothing is built", code == 2 and not os.path.isfile(os.path.join(root, "COURSE.html")), out)

        wc = os.path.join(c, "working_claude")
        cs.save(os.path.join(wc, "architecture.json"), ARCH)
        cs.save(os.path.join(wc, "programme.json"), {"academic_hour_min": 45, "total_row": {"total": 26}})
        cs.save(os.path.join(wc, "course.build.json"), {"regulation": "STCW Regulation V/3", "programme": "LJA programme 13-51-306"})
        # 2.47.0 - instructor\M01_PLAN.html is the compiled plan (compile_module.py wrote it above), not a stub
        io.open(os.path.join(md, "assessment", "check_answer_key.html"), "w", encoding="utf-8").write("<title>Answer key</title>")

        code, out = run(COURSE, c)
        check("built from the approved architecture, script and deck", code == 0, out)
        page = read(root, "COURSE.html")
        check("COURSE.html's <title> is the approved course title", "<title>%s</title>" % TITLE in page, page[:600])
        m = re.search(r'<meta name="description" content="([^"]+)">', page)
        check("... with a description the importer reads (20-400 letters): the regulation, programme, hours, modules",
              m and 20 <= len(m.group(1)) <= 400 and m.group(1) == "STCW Regulation V/3 · LJA programme 13-51-306 · 26 academic hours · 3 modules",
              m and m.group(1))
        check("... each built module opens from its START_HERE, with the script's title and minutes",
              '<a href="module01/START_HERE.html">M01 · IGF ships · 25 min</a>' in page, page)
        check("... a planned module not built yet is named, never listed", "Modules 2 to 3 are added" in page and "module02" not in page, page)
        check("... it wears the shared look, copied into _course_shell", all(os.path.isfile(os.path.join(root, "_course_shell", x))
                                                                             for x in ("gb_tokens.css", "gb_page.css")))
        cmap = read(root, "_course_shell", "course_map.js")
        mm = re.match(r"window\.COURSE_MAP = (\[[\s\S]*\]);\n$", cmap)
        data = json.loads(mm.group(1)) if mm else None
        check("course_map.js is data: module01, its title from the approved script (not the plan)",
              data == [{"code": "module01", "title": "IGF ships", "entry": "presentation/index.html"}], cmap)

        # 2.63.0 - the photo credits off the slides (owner Raivis, 2026-10-21): a course credits page, linked from COURSE.html
        cred = read(root, "_course_shell", "credits.html") if os.path.isfile(os.path.join(root, "_course_shell", "credits.html")) else ""
        check("the course's credits page lists every photograph a page shows, with its credit, under its module",
              "<h2>M01 · IGF ships</h2>" in cred and "A ship taking gas." in cred and "Jane Doe" in cred and "CC BY-SA 4.0" in cred, cred[:900])
        check("... COURSE.html links it, and it leads back to COURSE.html",
              'href="_course_shell/credits.html"' in page and 'href="../COURSE.html"' in cred, page[-400:])

        # 2.63.0 - a course's own module order (the instructors' review of IGF Basic: 1, 4, 6, 8, 2, 3 ...)
        import compile_course as cc
        infos = [{"n": n, "code": "module%02d" % n} for n in range(1, 6)]
        probs = []
        check("course.build.json \"module_order\" orders the course map; a module it leaves out follows, and is said",
              [i["n"] for i in cc.ordered({"module_order": [1, 4, 2]}, infos, probs)] == [1, 4, 2, 3, 5]
              and len(probs) == 1 and "leaves out module(s) [3, 5]" in probs[0], probs)
        probs = []
        check("... an order naming a module the course has not, or one twice, is a problem and the folder order stays",
              [i["n"] for i in cc.ordered({"module_order": [1, 9]}, infos, probs)] == [1, 2, 3, 4, 5] and "not there: [9]" in probs[0]
              and [i["n"] for i in cc.ordered({"module_order": [2, 2, 1, 3, 4, 5]}, infos, probs)] == [1, 2, 3, 4, 5], probs)
        check("... and no order is the folder's", cc.ordered({}, infos, []) == infos)

        sh, ext = read(md, "START_HERE.html"), read(md, "START_HERE_EXTENDED.html")
        check("START_HERE.html opens the deck at once", 'content="0; url=presentation/index.html"' in sh and "<title>M01 — Start</title>" in sh, sh)
        hrefs = re.findall(r'href="([^"]+)"', ext)
        check("START_HERE_EXTENDED.html links the deck, every task page the deck opens, and the instructor's files",
              all(x in hrefs for x in ("presentation/index.html", "tasks/sc1_the_new_spaces.html", "assessment/check.html",
                                       "instructor/M01_PLAN.html", "assessment/check_answer_key.html")), hrefs)
        check("... labelled by code: 'SC1 · The new spaces', 'MC · Module check', the instructor file by its title",
              "SC1 · The new spaces" in ext and "MC · Module check" in ext and ">Module 1 plan — IGF ships<" in ext, ext)
        check("... and nothing outside the module (L43)", not [x for x in hrefs if x.startswith("..") or ":" in x], hrefs)
        check("both are marked generated", "GENERATED by course-factory compile_course.py" in sh and "GENERATED" in page)

        code, out = run(PACKAGE, root)
        bad = [x for x in out.splitlines() if re.search(r"COURSE\.html|course_map|START_HERE", x)]
        check("check_course_package.py (with the classroom's importer) finds nothing wrong with them", not bad and TITLE in out, out[-1500:])
        check("... nor with the compiled plan: no problem names instructor/ or the plan",
              not [x for x in out.splitlines() if re.search(r"instructor|_PLAN", x)], out[-1500:])

        before = {f: read(root, f) for f in ("COURSE.html", "_course_shell/course_map.js", "module01/START_HERE_EXTENDED.html")}
        code, out = run(COURSE, c)
        check("built again: nothing changed, the same bytes", code == 0 and "Nothing changed" in out and
              all(read(root, f) == v for f, v in before.items()), out)

        io.open(os.path.join(root, "COURSE.html"), "a", encoding="utf-8").write("<!-- a hand edit -->")
        code, out = run(COURSE, c)
        check("a COURSE.html changed by hand is not overwritten", code == 1 and "changed by hand" in out and
              read(root, "COURSE.html").endswith("<!-- a hand edit -->"), out)
        code, out = run(COURSE, c, "--force")
        check("... --force overwrites it", code == 0 and "hand edit" not in read(root, "COURSE.html"), out)

        os.remove(os.path.join(md, "tasks", "sc1_the_new_spaces.html"))
        code, out = run(COURSE, c)
        check("a task slide whose page is missing is reported", code == 1 and "tasks/sc1_the_new_spaces.html, which is not in the module folder" in out, out)

        cs.save(os.path.join(wc, "architecture.json"), dict(ARCH, course={"title": "A new name", "course_language": "English"}))
        code, out = run(COURSE, c)
        check("a new course title stops the build - it would be a new course in the classroom", code == 2 and "A new name" in out
              and "<title>%s</title>" % TITLE in read(root, "COURSE.html"), out)
        code, out = run(COURSE, c, "--retitle")
        check("... --retitle accepts it", "<title>A new name</title>" in read(root, "COURSE.html"), out)

        # F7 (2.49.2) - a module built with --draft is a preview: marked, left out of the package, and said so
        base = os.path.join(tmp, "draft")
        os.makedirs(base)
        cd, mdd = t.new_course(base, t.script())
        run(t.COMPILE, cd, "--module", "1")
        sc2 = t.script(approved=False)
        sc2.update(module=2, title="Fuel systems")
        cs.save(os.path.join(cd, "working_claude", "script", "M02.json"), sc2)
        code, out = run(t.COMPILE, cd, "--module", "2", "--draft")
        wd = os.path.join(cd, "working_claude")
        cs.save(os.path.join(wd, "architecture.json"), ARCH)
        cs.save(os.path.join(wd, "programme.json"), {"academic_hour_min": 45, "total_row": {"total": 26}})
        rd = os.path.dirname(mdd)
        code, out = run(COURSE, cd)
        check("F7: a draft module is reported as 'draft - not packaged' and left out of COURSE.html and the module list",
              "module02: draft - not packaged" in out and "module02" not in read(rd, "COURSE.html")
              and "module02" not in read(rd, "_course_shell", "course_map.js")
              and not os.path.isfile(os.path.join(rd, "module02", "START_HERE.html")), out)
        code, out = run(PACKAGE, rd)
        check("F7: check_course_package.py leaves the draft out of its checks and the importer's run, and says so as a note (not a problem)",
              "module02: draft - not packaged" in out and "module02" not in out.split("Worth a look")[0], out[-1500:])
        # F6 - the start page names a final's variants
        sc_fin = t.final_script()
        cf = t.final_course(os.path.join(tmp, "fin"), "f", sc_fin)
        run(t.COMPILE, cf, "--module", "final")
        code, out = run(COURSE, cf)
        extf = read(cf, "modules", "module03", "START_HERE_EXTENDED.html")
        check("F6: START_HERE_EXTENDED links both final variants, each named",
              'href="assessment/final_a.html">FA · Final assessment A<' in extf and 'href="assessment/final_b.html">FB · Final assessment B<' in extf, extf)

        c2 = os.path.join(tmp, "two")                      # a course whose COURSE.html was made by hand, never compiled
        shutil.copytree(c, c2)
        os.remove(os.path.join(c2, "working_claude", "compiled_course.json"))
        io.open(os.path.join(c2, "modules", "COURSE.html"), "w", encoding="utf-8").write("<title>The hand-made name</title>")
        code, out = run(COURSE, c2, "--force")
        check("... a hand-made COURSE.html's title counts too, even with --force", code == 2 and "The hand-made name" in out, out)

        # L19 - the start pages in the course language: lv and ru (PROVISIONAL, compile/TRANSLATIONS_REVIEW.md)
        want = {"Latvian": ("lv", "Viss šim modulim", "Kursantu uzdevumi", "26 akad. st. (45 min)", "Moduļa pārbaude"),
                "Russian": ("ru", "Всё для этого модуля", "Задания слушателей", "26 ак. ч. (45 мин)", "Проверка по модулю"),
                "Norwegian": ("no", None, None, None, None)}
        for lang, (code_l, everything, tasks, hours, mc) in want.items():
            base = os.path.join(tmp, "lang_" + code_l)
            os.makedirs(base)
            sc = t.script(screens=t.IN_LANGUAGE["Russian" if lang == "Russian" else "Latvian"])
            sc["course_language"] = lang
            sc.update(approved_hash=cs.content_hash(sc))
            cl, mdl = t.new_course(base, sc, build=False)
            run(t.COMPILE, cl, "--module", "1")
            wl = os.path.join(cl, "working_claude")
            cs.save(os.path.join(wl, "architecture.json"), dict(ARCH, course={"title": TITLE, "course_language": lang}))
            cs.save(os.path.join(wl, "programme.json"), {"academic_hour_min": 45, "total_row": {"total": 26}})
            code, out = run(COURSE, cl)
            if not everything:
                check("Norwegian: the start pages' words are not in the factory - reported, never silent",
                      code == 1 and "in English" in out, out)
                continue
            ext, page = read(mdl, "START_HERE_EXTENDED.html"), read(os.path.dirname(mdl), "COURSE.html")
            check("%s: START_HERE_EXTENDED and COURSE.html in %s, marked lang=\"%s\"" % (lang, lang, code_l),
                  code == 0 and '<html lang="%s">' % code_l in ext and everything in ext and tasks in ext and "MC · %s" % mc in ext
                  and hours in page and '<html lang="%s">' % code_l in page, (out, ext[:1200]))
            check("%s: a task page's file name is the title in plain letters (sc1_varsti / sc1_samoproverka...)" % lang,
                  re.search(r'href="tasks/sc1_(varsti|klapany)\.html"', ext), ext)
            check("%s: no English word of the factory's left on them" % lang,
                  not re.search(r">(Everything for this module|Trainee tasks|Instructor only|All files|Back|Start the presentation)<", ext + page))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("\n%d passed, %d failed" % (len(PASS), len(FAIL)))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
