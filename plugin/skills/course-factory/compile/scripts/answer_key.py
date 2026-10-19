# -*- coding: utf-8 -*-
"""The instructor's answer key of a module, built from its approved script (2.46.0) - the last hand-made page gone.

Used by compile_module.py with the task pages: assessment\\check_answer_key.html - instructor-only by its name
(classroom-system.json: "answers and marking - instructor-only by its name"), listed by compile_course.py on the
module's START_HERE_EXTENDED page. Every self-check, module check and final question of the script, in the order the
tablet shows them: how the trainee answers, the question, the right answer, the feedback the trainee sees, and how the
pages mark (one point a question, the pass mark of a check). The shared document look (gb_tokens.css, gb_page.css), in
the course language.

WHY: IGF M01-M03's keys were typed by hand and were retired on 2026-10-16 because they still held answers the
operator had since corrected. A key made from the same approved script as the pages cannot drift from them.

The page carries no data-script / data-key: it is never mistaken for a task page (check_script_match.py) and the
trainee pages never link to it (check_course_package.py).
"""
from __future__ import annotations

import os
import re

import compile_module as cm
import content_script as cs
import task_pages as tp

NAME = os.path.join("assessment", "check_answer_key.html")
e, a = cm.e, cm.a
WORDS = {"en": {
    "title": "Answer key – Module {n}", "title_final": "Answer key – final assessment", "back": "Back",
    "only_h": "Instructor only",
    "only": "This page is for the instructor. It is never opened on a trainee tablet - the trainee pages ({pages}) do not "
            "contain these answers.",
    "how_h": "How the pages mark",
    "self": "Self-checks – one point per question, no pass mark. The trainee sees their own score; it is not recorded as a grade.",
    "check": "{name} – one point per question; a question with several parts counts only when every part is right. Pass mark "
             "{pass} %: {need} of {total} right = PASSED, fewer = NOT PASSED.",
    "timer": "When the instructor's timer ends, a page marks what was done and reports it as timed out.",
    "shown": "After each answer the page shows what was right, moves wrong cards to where they belong, and shows the "
             "feedback below.",
    "cols": ["#", "How the trainee answers", "Question", "Right answer", "Feedback shown after the answer"],
    "sc": "Self-check {code} – {title}", "mc": "Module check", "fa": "Final assessment",
    "made": "Made from the approved content script ({m}.json, approved by {by} on {on}) by course-factory {v}. Never edit "
            "it by hand: correct the script (content_script.py propose) and compile again.",
    "draft": "DRAFT – the script is not approved; this key is a preview and is never handed over.",
    "accepts": "the dial accepts {vals}", "stop": "Then tap where it should have stopped: {x}",
    "out": "Stays out of the plan: {x}", "because": "Why: {x}", "step": "Step {n}: {x}", "fault": "The faulty part: {x}",
    "wrong_lines": "The wrong lines:", "places": "Each label on its place: {x}", "ends": "{c}: {s}"},
    # PROVISIONAL (2.46.0) - written by Claude, to be checked by a native speaker: compile/TRANSLATIONS_REVIEW.md
    "lv": {
    "title": "Atbilžu atslēga – {n}. modulis", "title_final": "Atbilžu atslēga – noslēguma pārbaudījums", "back": "Atpakaļ",
    "only_h": "Tikai instruktoram",
    "only": "Šī lapa ir instruktoram. Tā nekad netiek atvērta kursanta planšetē – kursantu lapās ({pages}) šo atbilžu nav.",
    "how_h": "Kā lapas vērtē",
    "self": "Paškontrole – viens punkts par jautājumu, ieskaites sliekšņa nav. Kursants redz savu rezultātu; tas netiek ierakstīts kā atzīme.",
    "check": "{name} – viens punkts par jautājumu; jautājums ar vairākām daļām skaitās tikai tad, ja pareizas visas daļas. "
             "Ieskaites slieksnis {pass} %: {need} no {total} pareizi = IESKAITĪTS, mazāk = NAV IESKAITĪTS.",
    "timer": "Kad instruktora taimeris beidzas, lapa novērtē paveikto un ziņo, ka laiks beidzās.",
    "shown": "Pēc katras atbildes lapa parāda, kas bija pareizi, pārliek kļūdainās kartītes savās vietās un parāda skaidrojumu.",
    "cols": ["#", "Kā kursants atbild", "Jautājums", "Pareizā atbilde", "Skaidrojums pēc atbildes"],
    "sc": "Paškontrole {code} – {title}", "mc": "Moduļa pārbaude", "fa": "Noslēguma pārbaudījums",
    "made": "Izveidots no apstiprinātā satura scenārija ({m}.json, apstiprināja {by}, {on}), course-factory {v}. Nelabot "
            "ar roku: labojiet scenāriju (content_script.py propose) un kompilējiet vēlreiz.",
    "draft": "MELNRAKSTS – scenārijs nav apstiprināts; šī atslēga ir priekšskatījums, to nenodod.",
    "accepts": "skala pieņem {vals}", "stop": "Tad jāpieskaras vietai, kur bija jāaptur: {x}",
    "out": "Plānā neiekļauj: {x}", "because": "Kāpēc: {x}", "step": "{n}. solis: {x}", "fault": "Bojātā daļa: {x}",
    "wrong_lines": "Kļūdainās rindas:", "places": "Katrs uzraksts savā vietā: {x}", "ends": "{c}: {s}"},
    "ru": {
    "title": "Ключ ответов – модуль {n}", "title_final": "Ключ ответов – итоговая аттестация", "back": "Назад",
    "only_h": "Только для инструктора",
    "only": "Эта страница для инструктора. Она никогда не открывается на планшете слушателя – в страницах слушателей "
            "({pages}) этих ответов нет.",
    "how_h": "Как страницы оценивают",
    "self": "Самопроверка – один балл за вопрос, без проходного балла. Слушатель видит свой результат; он не записывается как оценка.",
    "check": "{name} – один балл за вопрос; вопрос из нескольких частей засчитывается, только если верны все части. "
             "Проходной балл {pass} %: {need} из {total} правильно = ЗАЧТЕНО, меньше = НЕ ЗАЧТЕНО.",
    "timer": "Когда таймер инструктора заканчивается, страница оценивает сделанное и сообщает, что время вышло.",
    "shown": "После каждого ответа страница показывает, что было верно, переносит неверные карточки на их места и показывает пояснение.",
    "cols": ["#", "Как отвечает слушатель", "Вопрос", "Правильный ответ", "Пояснение после ответа"],
    "sc": "Самопроверка {code} – {title}", "mc": "Проверка по модулю", "fa": "Итоговая аттестация",
    "made": "Сделано из утверждённого сценария ({m}.json, утвердил(а) {by}, {on}), course-factory {v}. Не править вручную: "
            "исправьте сценарий (content_script.py propose) и скомпилируйте снова.",
    "draft": "ЧЕРНОВИК – сценарий не утверждён; этот ключ – предпросмотр, его не выдают.",
    "accepts": "шкала принимает {vals}", "stop": "Затем коснуться места, где надо было остановить: {x}",
    "out": "Не входит в план: {x}", "because": "Почему: {x}", "step": "Шаг {n}: {x}", "fault": "Неисправный узел: {x}",
    "wrong_lines": "Строки с ошибкой:", "places": "Каждая надпись на своём месте: {x}", "ends": "{c}: {s}"}}
assert all(set(WORDS[k]) == set(WORDS["en"]) for k in WORDS), "every language has every word"


def lettered(q, shown=True):
    """'B – the words' for the options marked right, by the letter the TRAINEE SEES: the tablet shows the options
    shuffled (task_pages.opt_buttons, 2.44.2) and the engine letters them in that order (gb_answer.js letterAll) - the
    same deterministic order is worked out here. shown=False: the script's order (a compare table's columns)"""
    opts, right = q.get("options", []), cs.correct_letters(q)
    pairs = list(zip(cs.letters(len(opts)), opts))
    if shown:
        pairs = tp.shuffle(q["id"], pairs, key=lambda x: x[1])
    return ["<b>%s</b> – %s" % (S, e(o)) for S, (L, o) in zip(cs.letters(len(pairs)), pairs) if L in right]


def accepted(q, b, w):
    """the values the dial accepts, as the trainee sees them (task_pages.dial: one key per accepted step)"""
    mm = cs.SET_VALUE.match(q.get("answer") or "")
    if not mm:
        return ""
    num = lambda s: float(s.replace(",", "."))
    v, unit, tol, lo, hi = num(mm.group(1)), mm.group(2), num(mm.group(3)), num(mm.group(4)), num(mm.group(5))
    step, dec = tp.dial_step(v, tol, lo, hi, b.get("step"))
    if step is None:
        return ""
    S = 10 ** dec
    LO, ST, n = round(lo * S), round(step * S), round((hi - lo) / step)
    vals = [(LO + k * ST) / S for k in range(n + 1) if abs((LO + k * ST) / S - v) <= tol + step * 1e-6]
    point = "." if w is WORDS["en"] else ","            # the decimal mark the dial shows (task_pages.WORDS "decimal")
    shown = lambda x: ("%.*f" % (dec, x)).replace("-", "−").replace(".", point)
    return w["accepts"].format(vals=", ".join("%s %s" % (shown(x), unit) for x in vals).strip())


def right_answer(q, b, w):
    """the right answer of one question as lines of HTML, in the words of the approved script"""
    m, ls = cs.mech(q), cs.lines_of(q.get("answer"))
    if m in ("single_choice", "multi_select", "read_instrument"):
        return lettered(q)
    if m == "compare":                                  # its columns stay in the script's order
        return lettered(q, shown=False)
    if m == "choose_and_justify":
        return lettered(q) + [w["because"].format(x=e(cs.unstar(x))) for x in ls if cs.starred(x)]
    if m in ("hotspot", "spot_the_hazard"):
        return [e(cs.unstar(x)) for x in ls if cs.starred(x)]
    if m == "label_diagram":
        return [w["places"].format(x=", ".join(e(cs.unstar(x)) for x in ls))]
    if m == "order":
        return ["%d. %s" % (i, e(cs.unstar(x))) for i, x in enumerate(ls, 1)]
    if m in ("match", "panel_operate"):
        return [w["ends"].format(c=e(l.strip()), s=e(r.strip())) for l, _, r in (x.partition("=") for x in ls)]
    if m == "categorise":
        return ["<b>%s</b>: %s" % (e(g.strip()), e("; ".join(i.strip() for i in rest.split(";") if i.strip())))
                for g, _, rest in (x.partition(":") for x in ls)]
    if m == "cloze":
        def gap(mo):
            right = [cs.unstar(p) for p in mo.group(1).split("|") if cs.starred(p)]
            return "<b>[%s]</b>" % e(" / ".join(right))
        text = q.get("answer", "")
        return ["".join(gap(x) if isinstance(x, re.Match) else e(x) for x in _split(text))]
    if m == "scenario":
        out = []
        for n, ln in enumerate(ls, 1):
            sit, _, acts = ln.partition("=>")
            right = [cs.unstar(p) for p in acts.split("|") if cs.starred(p)]
            out.append(w["step"].format(n=n, x="%s → <b>%s</b>" % (e(sit.strip()), e(" / ".join(right)))))
        return out
    if m == "set_value":
        acc = accepted(q, b, w)
        return [e(q.get("answer", ""))] + ([e(acc)] if acc else [])
    if m == "find_the_fault":
        return [w["fault"].format(x="<b>%s</b>" % e(cs.unstar(x).partition(":")[0].strip())) for x in ls
                if cs.starred(x) and not x.lstrip().startswith("!")]
    if m == "spot_the_error":
        out = [w["wrong_lines"]]
        for x in ls:
            line, _, why = x.partition("=>")
            if cs.starred(line):
                out.append("<b>%s</b>%s" % (e(cs.unstar(line)), (" – " + e(why.strip())) if why.strip() else ""))
        return out
    if m == "build_the_plan":
        good, bad = [cs.unstar(x) for x in ls if cs.starred(x)], [cs.unstar(x) for x in ls if not cs.starred(x)]
        return ["%d. %s" % (i, e(t)) for i, t in enumerate(good, 1)] + ([w["out"].format(x=e("; ".join(bad)))] if bad else [])
    if m == "timeline":
        stop = [cs.unstar(x) for x in ls if cs.starred(x)]
        return ["%d. %s" % (i, e(cs.unstar(x))) for i, x in enumerate(ls, 1)] + \
               ([w["stop"].format(x="<b>%s</b>" % e(stop[0]))] if stop else [])
    return [e(q.get("answer") or q.get("correct") or "")]


def _split(text):
    """the cloze sentence as words and gap matches, in order"""
    out, at = [], 0
    for mo in re.finditer(r"\[([^\]]+)\]", text):
        out += [text[at:mo.start()], mo]
        at = mo.end()
    return out + [text[at:]]


def key_page(script, build, mdir, version, approved, probs):
    """(path, page) - or None when the module has no questions"""
    found = tp.sets(script)
    if not found:
        return None
    code_l = cm.lang_code(script.get("course_language") or "English")
    w = WORDS.get(code_l) or WORDS["en"]
    sheet = build.get("screens") or {}
    final = str(script.get("module")).lower() == "final"
    title = w["title_final"] if final else w["title"].format(n=script.get("module"))
    pages = ", ".join(os.path.relpath(tp.page_path(mdir, s, c, script), mdir).replace("\\", "/") for s, c, _ in found)
    names = []
    codes = [c for _, c, _ in found]
    for slide, code, qs in found:
        names.append(w["mc"] if code == "MC" else cm.final_name(w["fa"], code, codes) if cm.FINAL_SET.match(code) else
                     w["sc"].format(code=code, title=tp.short_title(slide.get("title"))))
    how = []
    if any(c.startswith("SC") for _, c, _ in found):
        how.append(w["self"])
    for (slide, code, qs), name in zip(found, names):
        if cm.is_check(code):
            pm = tp.pass_mark_of(script, build)
            how.append(w["check"].format(name=name, **{"pass": pm, "need": -(-len(qs) * pm // 100), "total": len(qs)}))
    how += [w["timer"], w["shown"]]
    m = cs.mid(script.get("module"))
    made = w["made"].format(m=m, by=script.get("approved_by") or "", on=script.get("approved_on") or "", v=version) if approved else w["draft"]
    body = ["<!DOCTYPE html>", '<html lang="%s">' % a(code_l or "en"), "<head>",
            "<!-- GENERATED by course-factory %s answer_key.py from working_claude/script/%s.json (%s). Instructor only - "
            "never on a trainee tablet. Do not edit: correct the script and compile again. -->"
            % (version, m, ("approved " + script.get("approved_hash", "")) if approved else "DRAFT - NOT APPROVED"),
            '<meta charset="utf-8">', '<meta name="viewport" content="width=device-width, initial-scale=1">',
            "<title>%s (%s)</title>" % (e(title), e(w["only_h"])),
            '<link rel="stylesheet" href="../assets/gb_tokens.css">', '<link rel="stylesheet" href="../assets/gb_page.css">',
            "</head>", "<body>",
            '<a class="gbt-topback" href="../START_HERE_EXTENDED.html"><span class="gbt-ico">&#9664;</span> %s</a>' % e(w["back"]),
            '<div class="wrap">', "  <h1>%s</h1>" % e(title),
            '  <p class="sub">%s · %s</p>' % (e(script.get("title")), e(", ".join(names))),
            '  <div class="card warn"><h3>%s</h3><p>%s</p></div>' % (e(w["only_h"]), e(w["only"].format(pages=pages))),
            '  <div class="card key"><h3>%s</h3>' % e(w["how_h"])] + ["    <p>%s</p>" % e(x) for x in how] + ["  </div>"]
    for (slide, code, qs), name in zip(found, names):
        body += ["", "  <h2>%s</h2>" % e(name), '  <div class="scroll"><table>',
                 "    <tr>%s</tr>" % "".join("<th>%s</th>" % e(c) for c in w["cols"])]
        for n, q in enumerate(qs, 1):
            b = sheet.get(q["id"]) or {}
            body.append('    <tr><td class="n">%d<br><small>%s</small></td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>' % (
                n, e(q["id"]), e(cs.mech_label(cs.mech(q), code_l or "en")), e(q.get("question")),
                "<br>".join(right_answer(q, b, w)), e(q.get("feedback"))))
        body.append("  </table></div>")
    body += ["", '  <div class="foot"><p>%s</p></div>' % e(made), "</div>", "</body>", "</html>", ""]
    return os.path.join(mdir, NAME), "\n".join(body)
