# -*- coding: utf-8 -*-
"""The instructor's plan of a module, built from its approved script (2.47.0) - the plan can no longer fall behind it.

Used by compile_module.py with the deck and the task pages: instructor\\M01_PLAN.html - instructor-only by its folder
(classroom-system.json: "moduleNN/instructor/ - the module plan ... instructor-only by its folder name"), listed by
compile_course.py on the module's START_HERE_EXTENDED page. Build-order step 14: "one plan per module, stating its
allocated and built minutes on its own face".

EVERY BLOCK IS FROM AN APPROVED FILE, NOTHING IS TYPED
  the face            allocated minutes (the script's "minutes_allocated", with the academic hours from programme.json)
                      against built minutes (the sum of every screen's minutes) - a mismatch is shown in red, in words,
                      and is reported by the compiler (exit 1); the minutes split into plain theory, active slides,
                      tasks and room activities (content_script.split_of)
  what it owes        the Main ILO (verbatim, in the programme's language) and the Sub-ILOs of the module's rows of the
                      ILO map (ilo_map.json) - each with the slides that teach it and the questions that check it
  the timeline        every screen in order: from which minute, its minutes, theory or active (and the technique), what it
                      shows, what the instructor does (the script's notes), the Sub-ILO it serves
  the tasks           every set the tablets open: its code, which slide opens it, how many questions, the pass mark, and
                      for each question its way of answering (mechanic), Sub-ILO and the question itself
  the room activities every activity slide, with the link hint the deck gives it
  materials           the practical equipment the architecture lists for the module (architecture.json "practicals"),
                      the tablets the tasks use, and the pictures the script says must be captured at the school
  the sources         the script's own list

The shared document look (gb_tokens.css, gb_page.css), in the course language; no script of its own. Never edit it by
hand - compile_module.py records what it wrote and stops before overwriting a changed plan (--force overwrites).
"""
from __future__ import annotations

import os

import compile_module as cm
import content_script as cs
import ilo_map
import task_pages as tp
import workspace

e, a = cm.e, cm.a
NAME = "instructor"
CAPTURE = ("photo_to_take", "video_real", "model_3d_scan")      # pictures only Novikontas can make (media-and-tasks.json)
EPS = 1e-9
WORDS = {"en": {
    "title": "Module {n} plan", "back": "Back", "instr": "Instructor only",
    "alloc": "Allocated: {m} min", "alloc_h": "{h} academic hour(s) of {a} min",
    "built": "Built: {m} min", "built_of": "the sum of the {n} screens",
    "split": "Plain theory {t} min · active slides {a} min · tasks {k} min · room activities {r} min",
    "not_stated": "Allocated: not stated in the script",
    "ok": "The screens add up to the allocated minutes.",
    "short": "The screens add up to {b} min, {d} min short of the {m} min the programme allocates.",
    "over": "The screens add up to {b} min, {d} min over the {m} min the programme allocates.",
    "no_alloc": "The script does not state the minutes the programme allocates to this module.",
    "mismatch_h": "The minutes do not add up",
    "owes_h": "What this module owes", "main": "Main ILO", "topic": "Programme topic",
    "sub_cols": ["Sub-ILO", "Outcome", "Taught on", "Checked by"],
    "slide_n": "slide {n}", "through": "met through the Sub-ILOs below it", "nothing": "–",
    "ids_only": "The ILO map is not in the course yet, so only the Sub-ILO ids the script names are shown.",
    "time_h": "Running order", "cols": ["#", "From min", "Screen", "Min", "Kind", "What the instructor does", "Sub-ILO"],
    "total": "Total", "theory": "Theory", "active": "Active", "task": "Task", "room": "Room activity", "open": "OPEN TASK",
    "tech": {"explain-then-reveal": "explain, then reveal", "predict-then-reveal": "predict, then reveal",
             "worked-example": "worked example, then own attempt", "scenario": "scenario", "explore": "explore",
             "self-check": "self-check", "other": "other"},
    "tasks_h": "Tasks on the tablets", "no_tasks": "This module has no task on the trainee tablets.",
    "opened": "opened by slide {n}, from minute {t}", "qs": "Questions: {n}",
    "pass": "Pass mark {pass} % – {need} of {total} right = PASSED, fewer = NOT PASSED",
    "no_pass": "No pass mark – the trainee sees their own score, it is not recorded as a grade",
    "team": "Team task – size {size}, roles: {roles}, hands in: {scope}", "scope_team": "one answer per team",
    "scope_member": "each member",
    "q_cols": ["#", "Id", "How the trainee answers", "Sub-ILO", "Question"],
    "key": "The right answers are in the answer key (instructor only).",
    "room_h": "Room activities", "room_cols": ["#", "Activity", "Min", "Link hint", "Sub-ILO"],
    "mat_h": "Materials and equipment",
    "tablets": "The instructor's tablet, mirrored to the classroom screen; one trainee tablet each for: {codes}.",
    "practical": "{task} – equipment: {eq}; place: {pl}; {m} min",
    "capture": "Slide {n}: {what} - to be captured at the school.",
    "no_equipment": "No practical equipment is named in the script or the architecture for this module.",
    "src_h": "Sources", "no_src": "The script names no sources.",
    "made": "Made from the approved content script ({m}.json, approved by {by} on {on}) by course-factory {v}. Never edit it "
            "by hand: correct the script (content_script.py propose) and compile again.",
    "draft": "DRAFT – the script is not approved; this plan is a preview and is never handed over."},
    # PROVISIONAL (2.47.0) - written by Claude, to be checked by a native speaker: compile/TRANSLATIONS_REVIEW.md
    "lv": {
    "title": "{n}. moduļa plāns", "back": "Atpakaļ", "instr": "Tikai instruktoram",
    "alloc": "Atvēlēts: {m} min", "alloc_h": "akad. stundas: {h} pa {a} min",
    "built": "Izveidots: {m} min", "built_of": "ekrānu summa: {n}",
    "split": "Tīra teorija {t} min · aktīvie slaidi {a} min · uzdevumi {k} min · nodarbības telpā {r} min",
    "not_stated": "Atvēlēts: scenārijā nav norādīts",
    "ok": "Ekrānu minūtes sakrīt ar atvēlētajām.",
    "short": "Ekrānu minūtes kopā ir {b} min – par {d} min mazāk nekā programmā atvēlētās {m} min.",
    "over": "Ekrānu minūtes kopā ir {b} min – par {d} min vairāk nekā programmā atvēlētās {m} min.",
    "no_alloc": "Scenārijā nav norādītas minūtes, ko programma atvēl šim modulim.",
    "mismatch_h": "Minūtes nesakrīt",
    "owes_h": "Ko šis modulis dod", "main": "Galvenais mācīšanās rezultāts", "topic": "Programmas temats",
    "sub_cols": ["Apakšrezultāts", "Rezultāts", "Māca", "Pārbauda"],
    "slide_n": "{n}. slaids", "through": "sasniedz ar zemāk esošajiem apakšrezultātiem", "nothing": "–",
    "ids_only": "Kursam vēl nav ILO kartes, tāpēc parādīti tikai scenārijā minētie apakšrezultātu numuri.",
    "time_h": "Norises secība", "cols": ["#", "No min", "Ekrāns", "Min", "Veids", "Ko dara instruktors", "Apakšrezultāts"],
    "total": "Kopā", "theory": "Teorija", "active": "Aktīvi", "task": "Uzdevums", "room": "Nodarbība telpā", "open": "ATVĒRT UZDEVUMU",
    "tech": {"explain-then-reveal": "izskaidro, tad atklāj", "predict-then-reveal": "paredz, tad atklāj",
             "worked-example": "atrisināts piemērs, tad paša mēģinājums", "scenario": "scenārijs", "explore": "pēti",
             "self-check": "paškontrole", "other": "cits"},
    "tasks_h": "Uzdevumi planšetēs", "no_tasks": "Šim modulim nav uzdevumu kursantu planšetēs.",
    "opened": "atver {n}. slaids, no {t}. minūtes", "qs": "Jautājumi: {n}",
    "pass": "Ieskaites slieksnis {pass} % – {need} no {total} pareizi = IESKAITĪTS, mazāk = NAV IESKAITĪTS",
    "no_pass": "Ieskaites sliekšņa nav – kursants redz savu rezultātu, tas netiek ierakstīts kā atzīme",
    "team": "Komandas uzdevums – izmērs {size}, lomas: {roles}, iesniedz: {scope}", "scope_team": "viena atbilde komandai",
    "scope_member": "katrs dalībnieks",
    "q_cols": ["#", "Id", "Kā kursants atbild", "Apakšrezultāts", "Jautājums"],
    "key": "Pareizās atbildes ir atbilžu atslēgā (tikai instruktoram).",
    "room_h": "Nodarbības telpā", "room_cols": ["#", "Nodarbība", "Min", "Saites norāde", "Apakšrezultāts"],
    "mat_h": "Materiāli un aprīkojums",
    "tablets": "Instruktora planšete, attēlota uz klases ekrāna; katram kursantam sava planšete šiem uzdevumiem: {codes}.",
    "practical": "{task} – aprīkojums: {eq}; vieta: {pl}; {m} min",
    "capture": "{n}. slaids: {what} – jāuzņem skolā.",
    "no_equipment": "Scenārijā un arhitektūrā šim modulim nav nosaukts neviens praktiskais aprīkojums.",
    "src_h": "Avoti", "no_src": "Scenārijā avoti nav minēti.",
    "made": "Izveidots no apstiprinātā satura scenārija ({m}.json, apstiprināja {by}, {on}), course-factory {v}. Nelabot ar "
            "roku: labojiet scenāriju (content_script.py propose) un kompilējiet vēlreiz.",
    "draft": "MELNRAKSTS – scenārijs nav apstiprināts; šis plāns ir priekšskatījums, to nenodod."},
    "ru": {
    "title": "План модуля {n}", "back": "Назад", "instr": "Только для инструктора",
    "alloc": "Отведено: {m} мин", "alloc_h": "академ. часов: {h} по {a} мин",
    "built": "Собрано: {m} мин", "built_of": "сумма экранов: {n}",
    "split": "Чистая теория {t} мин · активные слайды {a} мин · задания {k} мин · занятия в аудитории {r} мин",
    "not_stated": "Отведено: в сценарии не указано",
    "ok": "Минуты экранов совпадают с отведёнными.",
    "short": "Экраны дают {b} мин – на {d} мин меньше, чем {m} мин, отведённых программой.",
    "over": "Экраны дают {b} мин – на {d} мин больше, чем {m} мин, отведённых программой.",
    "no_alloc": "В сценарии не указаны минуты, которые программа отводит этому модулю.",
    "mismatch_h": "Минуты не сходятся",
    "owes_h": "Что даёт этот модуль", "main": "Главный результат обучения", "topic": "Тема программы",
    "sub_cols": ["Подрезультат", "Результат", "Где изучается", "Чем проверяется"],
    "slide_n": "слайд {n}", "through": "достигается через подрезультаты ниже", "nothing": "–",
    "ids_only": "Карты ILO в курсе ещё нет, поэтому показаны только номера подрезультатов из сценария.",
    "time_h": "Порядок занятия", "cols": ["#", "С мин", "Экран", "Мин", "Вид", "Что делает инструктор", "Подрезультат"],
    "total": "Итого", "theory": "Теория", "active": "Активно", "task": "Задание", "room": "Занятие в аудитории", "open": "ОТКРЫТЬ ЗАДАНИЕ",
    "tech": {"explain-then-reveal": "объясни, затем открой ответ", "predict-then-reveal": "предскажи, затем открой ответ",
             "worked-example": "разобранный пример, затем своя попытка", "scenario": "сценарий", "explore": "исследуй",
             "self-check": "самопроверка", "other": "другое"},
    "tasks_h": "Задания на планшетах", "no_tasks": "В этом модуле нет заданий на планшетах слушателей.",
    "opened": "открывает слайд {n}, с {t}-й минуты", "qs": "Вопросы: {n}",
    "pass": "Проходной балл {pass} % – {need} из {total} правильно = ЗАЧТЕНО, меньше = НЕ ЗАЧТЕНО",
    "no_pass": "Проходного балла нет – слушатель видит свой результат, он не записывается как оценка",
    "team": "Командное задание – размер {size}, роли: {roles}, сдаёт: {scope}", "scope_team": "один ответ от команды",
    "scope_member": "каждый участник",
    "q_cols": ["#", "Id", "Как отвечает слушатель", "Подрезультат", "Вопрос"],
    "key": "Правильные ответы – в ключе ответов (только для инструктора).",
    "room_h": "Занятия в аудитории", "room_cols": ["#", "Занятие", "Мин", "Подсказка к ссылке", "Подрезультат"],
    "mat_h": "Материалы и оборудование",
    "tablets": "Планшет инструктора, выведенный на экран класса; по планшету на каждого слушателя для заданий: {codes}.",
    "practical": "{task} – оборудование: {eq}; место: {pl}; {m} мин",
    "capture": "Слайд {n}: {what} – снять в школе.",
    "no_equipment": "В сценарии и архитектуре для этого модуля практическое оборудование не названо.",
    "src_h": "Источники", "no_src": "В сценарии источники не указаны.",
    "made": "Сделано из утверждённого сценария ({m}.json, утвердил(а) {by}, {on}), course-factory {v}. Не править вручную: "
            "исправьте сценарий (content_script.py propose) и скомпилируйте снова.",
    "draft": "ЧЕРНОВИК – сценарий не утверждён; этот план – предпросмотр, его не выдают."}}
assert all(set(WORDS[k]) == set(WORDS["en"]) for k in WORDS), "every language has every word"
assert all(set(WORDS[k]["tech"]) == set(WORDS["en"]["tech"]) for k in WORDS), "every language names every technique"


def num(x):
    return "%g" % round(x, 4)


def path(mdir, module):
    return os.path.join(mdir, NAME, "%s_PLAN.html" % cs.mid(module))


def load_json(course, name):
    p = workspace.claude_path(course, name)
    try:
        return cs.load(p) if os.path.isfile(p) else None
    except (OSError, ValueError):
        return None


def sub_rows(course, script):
    """the module's rows of the ILO map - [] when the course has none yet"""
    m = ilo_map.read(course) if course else None
    return ilo_map.module_rows(m, script.get("module")) if m else []


def practicals(course, script):
    """the architecture's practical tasks for this module - [{task, equipment, place, minutes}]"""
    arch = load_json(course, "architecture.json") if course else None
    for am in (arch or {}).get("modules", []) or []:
        if ilo_map.mkey(am.get("module")) == ilo_map.mkey(script.get("module")):
            return [p for p in am.get("practicals", []) or [] if isinstance(p, dict)]
    return []


def bullets(text):
    return [x[2:].strip() for x in cs.note_lines(text)]


def cell_list(items):
    items = [x for x in items if x]
    return "<ul>%s</ul>" % "".join("<li>%s</li>" % x for x in items) if items else ""


def plan_page(script, build, mdir, course, version, approved, probs):
    """(path, page) - and the problems the plan shows, appended to probs"""
    m = cs.mid(script.get("module"))
    lang = script.get("course_language") or "English"
    lc = cm.lang_code(lang)
    w = WORDS.get(lc) or WORDS["en"]
    wl = lc if lc in WORDS else "en"
    if lc not in WORDS:                                  # reported, never a silent fall-back
        probs.append("%s plan: the course is in %s - the plan's own words are not in the factory in that language, so they were "
                     "written in English (module_plan.py WORDS)" % (m, lang))
    sheet = build.get("screens") or {}
    figdir = workspace.claude_path(course, "figures", m) if course else None
    slide_no, sets, set_of = cs.plan_of(script)
    screens = [s for s in script.get("screens", []) if s.get("kind") in cs.INSTRUCTOR]
    # ---- the minutes: allocated against built
    alloc = script.get("minutes_allocated")
    try:
        alloc = float(alloc) if alloc not in (None, "") else None
    except (TypeError, ValueError):
        alloc = None
    built = sum(cs.minutes(s) for s in screens)
    start, t = {}, 0.0
    for s in screens:
        start[s["id"]] = t
        t += cs.minutes(s)
    split = cs.split_of(script)
    prog = load_json(course, "programme.json") if course else None
    hour = (prog or {}).get("academic_hour_min")
    face = []
    if alloc is None:
        face.append(w["not_stated"])
        probs.append("%s plan: the script does not state the module's allocated minutes (\"minutes_allocated\") - the plan cannot "
                     "show built against allocated" % m)
    else:
        txt = w["alloc"].format(m=num(alloc))
        if hour:
            txt += " (%s)" % w["alloc_h"].format(h=num(alloc / float(hour)), a=num(float(hour)))
        face.append(txt)
    face.append("%s (%s)" % (w["built"].format(m=num(built)), w["built_of"].format(n=len(screens))))
    face.append(w["split"].format(t=num(split["plain"]), a=num(split["active_slides"]), k=num(split["tasks"]), r=num(split["practice"])))
    if alloc is None:
        verdict = ("warn", w["no_alloc"])
    elif abs(alloc - built) > EPS:
        diff = abs(alloc - built)
        verdict = ("warn", w["short" if built < alloc else "over"].format(b=num(built), d=num(diff), m=num(alloc)))
        probs.append("%s plan: the screens add up to %s min, the programme allocates %s min (%s min %s)"
                     % (m, num(built), num(alloc), num(diff), "short" if built < alloc else "over"))
    else:
        verdict = ("good", w["ok"])
    title = w["title"].format(n=script.get("module"))
    made = w["made"].format(m=m, by=script.get("approved_by") or "", on=script.get("approved_on") or "", v=version) if approved else w["draft"]
    body = ["<!DOCTYPE html>", '<html lang="%s">' % a(lc or "en"), "<head>",
            "<!-- GENERATED by course-factory %s module_plan.py from working_claude/script/%s.json (%s). Instructor only - "
            "never on a trainee tablet. Do not edit: correct the script and compile again. -->"
            % (version, m, ("approved " + script.get("approved_hash", "")) if approved else "DRAFT - NOT APPROVED"),
            '<meta charset="utf-8">', '<meta name="viewport" content="width=device-width, initial-scale=1">',
            "<title>%s — %s</title>" % (e(title), e(script.get("title"))),
            '<link rel="stylesheet" href="../assets/gb_tokens.css">', '<link rel="stylesheet" href="../assets/gb_page.css">',
            "<style>td ul{margin:0;padding-left:1.1em}td li{margin:0 0 3px}</style>",     # the notes' bullets, inside a table cell
            "</head>", "<body>",
            '<a class="gbt-topback" href="../START_HERE_EXTENDED.html"><span class="gbt-ico">&#9664;</span> %s</a>' % e(w["back"]),
            '<div class="wrap">', "  <h1>%s</h1>" % e(title),
            '  <p class="sub">%s · %s</p>' % (e(script.get("title")), e(w["instr"])),
            '  <div class="meta">%s</div>' % "".join("<span>%s</span>" % e(x) for x in face),
            '  <div class="card %s">%s<p>%s</p></div>' % (
                verdict[0], ("<h3>%s</h3>" % e(w["mismatch_h"])) if verdict[0] == "warn" else "", e(verdict[1]))]
    # ---- what the module owes: the Main ILO and the Sub-ILOs
    rows = sub_rows(course, script)
    taught, checked = {}, {}
    for s in script.get("screens", []):
        for t_ in cs.sub_ilos_of(s):
            if s.get("kind") in cs.INSTRUCTOR:
                taught.setdefault(t_, []).append(s["id"])
            elif s.get("kind") in cs.TASKS:
                checked.setdefault(t_, []).append(s["id"])

    def where_taught(sid):
        return ", ".join(w["slide_n"].format(n=slide_no[x]) for x in taught.get(sid, []) if x in slide_no)

    def where_checked(sid):
        out = []
        for x in checked.get(sid, []):
            q = next((s for s in script["screens"] if s["id"] == x), {})
            out.append("%s %s" % (set_code(q), x))
        return ", ".join(out)

    prog_lang = cm.lang_code((prog or {}).get("language")) if (prog or {}).get("language") else None
    pl = ' lang="%s"' % a(prog_lang) if prog_lang and prog_lang != lc else ""
    ids = []
    for s in script.get("screens", []):
        ids += [x for x in cs.sub_ilos_of(s) if x not in ids]
    if rows or ids:
        body += ["", "  <h2>%s</h2>" % e(w["owes_h"])]
        if rows:
            r0 = rows[0]
            card = ['  <div class="card key">']
            if r0.get("main_ilo"):
                card.append("    <p><b>%s:</b> <span%s>%s</span></p>" % (e(w["main"]), pl, e(r0["main_ilo"])))
            if r0.get("topic"):
                card.append("    <p><b>%s:</b> <span%s>%s</span></p>" % (e(w["topic"]), pl, e(r0["topic"])))
            card.append("  </div>")
            if len(card) > 2:
                body += card
            leaves = set(ilo_map.leaves(rows))
            body += ['  <div class="scroll"><table>', "    <tr>%s</tr>" % "".join("<th>%s</th>" % e(c) for c in w["sub_cols"])]
            for r in rows:
                sid = str(r.get("sub_ilo_id"))
                if sid in leaves:
                    t_, c_ = where_taught(sid) or w["nothing"], where_checked(sid) or w["nothing"]
                    cells = "<td>%s</td><td>%s</td>" % (e(t_), e(c_))
                else:
                    cells = '<td colspan="2">%s</td>' % e(w["through"])
                body.append('    <tr><td class="n">%s</td><td>%s</td>%s</tr>' % (e(sid), e(r.get("sub_ilo")), cells))
            body.append("  </table></div>")
        else:
            body += ['  <p class="note">%s</p>' % e(w["ids_only"]), '  <div class="scroll"><table>',
                     "    <tr>%s</tr>" % "".join("<th>%s</th>" % e(c) for i, c in enumerate(w["sub_cols"]) if i != 1)]
            for sid in ids:
                body.append('    <tr><td class="n">%s</td><td>%s</td><td>%s</td></tr>'
                            % (e(sid), e(where_taught(sid) or w["nothing"]), e(where_checked(sid) or w["nothing"])))
            body.append("  </table></div>")
    # ---- the timeline: every screen
    body += ["", "  <h2>%s</h2>" % e(w["time_h"]), '  <div class="scroll"><table>',
             "    <colgroup>%s</colgroup>" % "".join('<col style="width:%s%%">' % x for x in (4, 6, 19, 5, 15, 43, 8)),
             "    <tr>%s</tr>" % "".join("<th>%s</th>" % e(c) for c in w["cols"])]
    for s in screens:
        k = s["kind"]
        if k == "task-slide":
            code = (s.get("opens") or "").strip()
            kind = "%s · %s" % (w["task"], code) if code else w["task"]
        elif k == "activity":
            kind = w["room"]
        elif s.get("active"):
            kind = "%s · %s" % (w["active"], w["tech"].get(s["active"], str(s["active"])) if isinstance(s["active"], str) else "")
            kind = kind.rstrip(" ·")
        else:
            kind = w["theory"]
        # 2.52.0 - the kind of picture the slide was BUILT with (the deck's data-visual), never the script's plan when the
        # build sheet gave another: a 3D slide kept 2D ("declined_3d") is not promised as a model here
        built_k = cm.slide_visual(s, sheet.get(s["id"]) or {}, mdir, figdir) if s.get("visual_kind") else ""
        vk = cs.kind_label(built_k, wl).split(" (")[0].split(" - ")[0] if built_k and built_k != "none" else ""
        kind_html = e(kind) + ("<br><small>%s</small>" % e(vk) if vk and vk != kind else "")
        do = bullets(s.get("notes"))
        if k == "task-slide":
            st = set_of.get(s.get("opens"))
            if st:
                do = ["<b>%s</b> · %s" % (e(w["open"]), e(w["qs"].format(n=len(st["questions"]))))] + [e(x) for x in do]
            else:
                do = [e(x) for x in do]
        else:
            do = [e(x) for x in do]
        body.append('    <tr%s><td class="n">%d</td><td class="m">%s</td><td>%s</td><td class="m">%s</td><td>%s</td><td>%s</td><td>%s</td></tr>' % (
            ' class="p"' if k == "task-slide" else "", slide_no[s["id"]], num(start[s["id"]]), e(s.get("title")), num(cs.minutes(s)),
            kind_html, cell_list(do), e(", ".join(cs.sub_ilos_of(s)))))
    body.append('    <tr><td></td><td></td><td><b>%s</b></td><td class="m"><b>%s</b></td><td></td><td></td><td></td></tr>'
                % (e(w["total"]), num(built)))
    body.append("  </table></div>")
    # ---- the tasks on the tablets
    body += ["", "  <h2>%s</h2>" % e(w["tasks_h"])]
    found = tp.sets(script)
    if not found:
        body.append("  <p>%s</p>" % e(w["no_tasks"]))
    for slide, code, qs in found:
        pm = tp.pass_mark_of(script, build)
        is_check = cm.is_check(code)
        head = "%s – %s" % (code, tp.short_title(slide.get("title")) if code.startswith("SC") else slide.get("title"))
        info = [w["opened"].format(n=slide_no[slide["id"]], t=num(start[slide["id"]])), w["qs"].format(n=len(qs)),
                w["pass"].format(**{"pass": pm, "need": -(-len(qs) * pm // 100), "total": len(qs)}) if is_check else w["no_pass"]]
        team = slide.get("team")
        if isinstance(team, dict) and team:
            scope = w["scope_team"] if team.get("scope") == "team" else w["scope_member"]
            info.append(w["team"].format(size=team.get("size", "?"), roles=", ".join(cs.team_roles(team)) or w["nothing"], scope=scope))
        body += ["  <h3>%s</h3>" % e(head), '  <div class="meta">%s</div>' % "".join("<span>%s</span>" % e(x) for x in info),
                 '  <div class="scroll"><table>', "    <tr>%s</tr>" % "".join("<th>%s</th>" % e(c) for c in w["q_cols"])]
        for n, q in enumerate(qs, 1):
            body.append('    <tr><td class="n">%d</td><td class="n">%s</td><td>%s</td><td>%s</td><td>%s</td></tr>' % (
                n, e(q["id"]), e(cs.mech_label(cs.mech(q), wl)), e(", ".join(cs.sub_ilos_of(q))), e(q.get("question"))))
        body.append("  </table></div>")
    if found:
        body.append('  <p class="note">%s</p>' % e(w["key"]))
    # ---- the room activities
    acts = [s for s in screens if s["kind"] == "activity"]
    if acts:
        body += ["", "  <h2>%s</h2>" % e(w["room_h"]), '  <div class="scroll"><table>',
                 "    <tr>%s</tr>" % "".join("<th>%s</th>" % e(c) for c in w["room_cols"])]
        for s in acts:
            lines = cs.lines_of(s.get("text"))
            hint = (sheet.get(s["id"]) or {}).get("link_hint") or (lines[0] if lines else "")
            body.append('    <tr><td class="n">%d</td><td>%s</td><td class="m">%s</td><td>%s</td><td>%s</td></tr>' % (
                slide_no[s["id"]], e(s.get("title")), num(cs.minutes(s)), e(hint), e(", ".join(cs.sub_ilos_of(s)))))
        body.append("  </table></div>")
    # ---- materials and equipment
    mat = []
    for p in practicals(course, script):
        eq = str(p.get("equipment") or "").strip()
        mat.append(w["practical"].format(task=p.get("task", ""), eq=eq if eq not in ("", "—", "-") else w["nothing"],
                                         pl=p.get("place") or w["nothing"], m=p.get("minutes", "")))
    if found:
        mat.append(w["tablets"].format(codes=", ".join(c for _, c, _ in found)))
    for s in screens:
        if s.get("visual_kind") in CAPTURE:
            mat.append(w["capture"].format(n=slide_no[s["id"]], what=s.get("visual") or cs.kind_label(s["visual_kind"], wl)))
    body += ["", "  <h2>%s</h2>" % e(w["mat_h"])]
    if not practicals(course, script) and not any(s.get("visual_kind") in CAPTURE for s in screens):
        body.append("  <p>%s</p>" % e(w["no_equipment"]))
    body += ["  <ul>"] + ["    <li>%s</li>" % e(x) for x in mat] + ["  </ul>"] if mat else []
    # ---- the sources
    srcs = [str(x).strip() for x in script.get("sources") or [] if str(x).strip()]
    body += ["", "  <h2>%s</h2>" % e(w["src_h"])]
    body += ['  <p class="src">%s</p>' % e(x) for x in srcs] if srcs else ["  <p>%s</p>" % e(w["no_src"])]
    body += ["", '  <div class="foot"><p>%s</p></div>' % e(made), "</div>", "</body>", "</html>", ""]
    return path(mdir, script.get("module")), "\n".join(body)


def set_code(q):
    """the set a question belongs to - its "set", or the kind's default code"""
    return (q.get("set") or "").strip() or {"self-check": "SC1", "module-check": "MC", "final": "FA"}.get(q.get("kind"), "")
