# The task screens', start pages' and deck's own words in Latvian and Russian — PROVISIONAL, for review

Status: **PROVISIONAL** (2.40.0, 2026-10-16; the deck's words 2.41.0, same day). Written by Claude, not yet checked by a native speaker. Every line below
is used by the compiler as it stands; a correction is made in the code named in each table and this file is updated
with it. When a speaker has checked a language, change its status line here to "checked by <name>, <date>".

| Language | Status |
|---|---|
| lv — Latvian | PROVISIONAL — to be checked by Aleksis or a native speaker |
| ru — Russian | PROVISIONAL — to be checked by a native speaker |

These are only the words the **factory** puts on a page — buttons, prompts, the result. The course's own words (every
question, answer and feedback) come from the approved content script in the course language and are never translated
by the compiler (L19, L29). The words are chosen by the script's / architecture's `course_language` (L19
COURSE_LANGUAGE): one language for the whole page. A language the factory has no words for is **reported** by the
compiler (exit 1) and the page is built in English — never silently.

Choices made, to check first:
- **Address.** The trainee's task screens use the familiar form (lv *tu*, ru *ты*), as the names of the ways of
  answering already do in `knowledge/media-and-tasks.json` ("Pabeidz teikumu", "Дополни предложение"). The
  instructor's start pages use the polite form (lv *jūs*, ru *вы*).
- **Gender.** Lines that would need a masculine or feminine form are worded to need neither ("Vari sākt
  paškontroli", "Можно начинать самопроверку").
- **Plurals.** Minutes and hours are abbreviated (min / мин, akad. st. / ак. ч.), and counts are written as
  "label: n", so no plural form depends on the number.
- **Terms.** self-check = lv *paškontrole*, ru *самопроверка*; module check = lv *moduļa pārbaude*, ru *проверка по
  модулю*; final assessment = lv *noslēguma pārbaudījums*, ru *итоговая аттестация*; trainee = lv *kursants*, ru
  *слушатель*; fault = lv *kļūme*, ru *неисправность*; part (of a system) = lv *daļa*, ru *узел* (as in
  media-and-tasks.json); pass mark = lv *ieskaites slieksnis*, ru *проходной балл*; PASSED / NOT PASSED as shown on
  the screen = lv *IESKAITĪTS / NAV IESKAITĪTS*, ru *ЗАЧТЕНО / НЕ ЗАЧТЕНО* (the message to the classroom keeps
  'PASSED' / 'NOT PASSED' — that is a code, not a word on the screen).
- **Colours named in feedback.** "amber" (the cards moved to their place) = lv *dzeltenās*, ru *жёлтые*.

## 1 · The task screen's own words — `compile/scripts/task_pages.py` WORDS

| key | English | Latvian (lv) | Russian (ru) |
|---|---|---|---|
| back | Back | Atpakaļ | Назад |
| try_title | Try your tablet first | Vispirms izmēģini planšeti | Сначала попробуй планшет |
| try_tap | Tap here | Pieskaries šeit | Коснись здесь |
| try_1 | Tap the big blue circle. | Pieskaries lielajam zilajam aplim. | Коснись большого синего круга. |
| try_drag | Drag me | Velc mani | Перетащи меня |
| try_2 | Drag the box into the frame. Or tap the box, then tap the frame. | Ievelc kartīti rāmī. Vai pieskaries kartītei, tad rāmim. | Перетащи карточку в рамку. Или коснись карточки, затем рамки. |
| try_hello | Well done. You are ready for the self-check. | Labi! Vari sākt paškontroli. | Отлично! Можно начинать самопроверку. |
| pass | Pass mark {pass} % – {need} of {total} right | Ieskaites slieksnis {pass} % – {need} no {total} pareizi | Проходной балл {pass} % – {need} из {total} правильно |
| score | Your score | Tavs rezultāts | Твой результат |
| score_note | Your score is for you only. Look at the questions below and ask your instructor about any you missed. | Rezultāts ir tikai tev. Apskati jautājumus zemāk un pajautā instruktoram par tiem, kas neizdevās. | Результат — только для тебя. Посмотри вопросы ниже и спроси инструктора о тех, где была ошибка. |
| again | Start again | Sākt no jauna | Начать заново |
| start_self | Start the self-check | Sākt paškontroli | Начать самопроверку |
| start_check | Start the check | Sākt pārbaudi | Начать проверку |
| choose_all | Choose all that are right. | Izvēlies visas pareizās atbildes. | Выбери все правильные ответы. |
| module_n_check | Module {n} check | {n}. moduļa pārbaude | Проверка по модулю {n} |
| gap_n | Gap {n} | {n}. tukšā vieta | Пропуск {n} |
| cloze_say | Tap a gap, then choose the words that fit it. | Pieskaries tukšajai vietai, tad izvēlies vārdus, kas tur der. | Коснись пропуска, затем выбери подходящие слова. |
| your_action | What you do | Ko tu dari | Что ты делаешь |
| your_reason | Why | Kāpēc | Почему |
| step_n | Step {n} of {of} | {n}. solis no {of} | Шаг {n} из {of} |
| less / more | Less / More | Mazāk / Vairāk | Меньше / Больше |
| decimal | . | , | , |
| symptoms | What you notice | Ko tu pamani | Что ты замечаешь |
| fault_say | Tap a part to check it. Then tap “This is the fault” on the part that is faulty. | Pieskaries daļai, lai to pārbaudītu. Tad bojātajai daļai pieskaries “Šī ir kļūme”. | Коснись узла, чтобы проверить его. Затем на неисправном узле нажми «Это неисправность». |
| tap_to_check | Tap to check | Pieskaries, lai pārbaudītu | Коснись, чтобы проверить |
| is_fault | This is the fault | Šī ir kļūme | Это неисправность |
| errors_say | Tap every line that is wrong. Tap it again to take the mark off. | Pieskaries katrai kļūdainajai rindai. Pieskaries vēlreiz, lai atzīmi noņemtu. | Коснись каждой строки с ошибкой. Коснись ещё раз, чтобы снять отметку. |
| plan_say | Put the cards that belong into the plan, in order. Not every card belongs – leave those where they are. | Saliec plānā vajadzīgās kartītes pareizā secībā. Ne visas kartītes der – tās atstāj, kur ir. | Разложи нужные карточки в план по порядку. Не все карточки подходят – их оставь на месте. |
| timeline_order | 1. Put the events in the order they happened. | 1. Sakārto notikumus secībā, kādā tie notika. | 1. Расставь события в том порядке, в котором они произошли. |
| timeline_stop | 2. Now tap the event where it should have been stopped. | 2. Tagad pieskaries notikumam, kurā tas bija jāaptur. | 2. Теперь коснись события, на котором его надо было остановить. |
| panel_say | Put every control in the position it must end in. | Iestati katru vadības elementu stāvoklī, kurā tam jābūt beigās. | Установи каждый орган управления в положение, в котором он должен остаться. |

The positions a panel control can take when the build sheet does not list them (`PAIRS`, same file):
lv atvērts / aizvērts, ieslēgts / izslēgts, darbojas / apturēts, automātisks / manuāls;
ru открыт / закрыт, открыто / закрыто, включен (включён) / выключен, работает / остановлен, автомат / ручной.

## 2 · The engine's words — `course-task-ux/assets/gb_answer.js` (T, by the page's `<html lang>`)

| key | English | Latvian (lv) | Russian (ru) |
|---|---|---|---|
| tryFirst | Try your tablet first | Vispirms izmēģini planšeti | Сначала попробуй планшет |
| startSelf | Start the self-check | Sākt paškontroli | Начать самопроверку |
| moduleCheck | Module check | Moduļa pārbaude | Проверка по модулю |
| startCheck | Start the check | Sākt pārbaudi | Начать проверку |
| question | Question {n} of {of} | {n}. jautājums no {of} | Вопрос {n} из {of} |
| soFar | {n} right so far | Pagaidām pareizi: {n} | Пока правильно: {n} |
| check | Check | Pārbaudīt | Проверить |
| next | Next | Tālāk | Далее |
| goOn | Go on | Turpināt | Дальше |
| seeScore | See my score | Mans rezultāts | Мой результат |
| result | Your result | Tavs rezultāts | Твой результат |
| correct | Correct. | Pareizi. | Правильно. |
| notQuiteChoice | Not quite – the right answer is marked. | Ne gluži – pareizā atbilde ir atzīmēta. | Не совсем – правильный ответ отмечен. |
| notQuitePlace | Not quite – the amber ones were moved to where they belong. | Ne gluži – dzeltenās kartītes ir pārliktas savās vietās. | Не совсем – жёлтые карточки перенесены на свои места. |
| notQuiteValue | Not quite – the green band shows the values that are right. | Ne gluži – zaļā josla rāda pareizās vērtības. | Не совсем – зелёная полоса показывает правильные значения. |
| got | You got {ok} of {total} right. | Pareizi: {ok} no {total}. | Правильно: {ok} из {total}. |
| timeUp | The time was up. | Laiks beidzās. | Время вышло. |
| passNote | Pass mark {pass} % – {need} of {total} right. This shows what to review. It is not a grade. | Ieskaites slieksnis {pass} % – {need} no {total} pareizi. Tas rāda, ko atkārtot. Tā nav atzīme. | Проходной балл {pass} % – {need} из {total} правильно. Это показывает, что повторить. Это не оценка. |
| passed | PASSED | IESKAITĪTS | ЗАЧТЕНО |
| notPassed | NOT PASSED | NAV IESKAITĪTS | НЕ ЗАЧТЕНО |
| teamRole | You are the {role} | Tava loma: {role} | Твоя роль: {role} |
| teamOne | One answer for the whole team | Viena atbilde visai komandai | Один ответ на всю команду |
| handedIn | Handed in by {by} for {team} | {team} atbildi iesniedza: {by} | Ответ команды {team} сдал(а): {by} |

## 3 · The start pages' own words — `compile/scripts/compile_course.py` WORDS (the instructor's pages)

| key | English | Latvian (lv) | Russian (ru) |
|---|---|---|---|
| start | Start | Sākt | Начать |
| everything | Everything for this module | Viss šim modulim | Всё для этого модуля |
| back | Back | Atpakaļ | Назад |
| module | Module | Modulis | Модуль |
| opening | Opening the presentation. If nothing happens, press the button. | Prezentācija tiek atvērta. Ja nekas nenotiek, nospiediet pogu. | Презентация открывается. Если ничего не происходит, нажмите кнопку. |
| start_deck | Start the presentation | Sākt prezentāciju | Начать презентацию |
| presentation | Presentation | Prezentācija | Презентация |
| minutes / min | {n} minutes / {n} min | {n} min | {n} мин |
| how | Open the presentation and press Next to the end - each task opens on the trainee tablets from its own task slide. | Atveriet prezentāciju un spiediet “Tālāk” līdz beigām – katrs uzdevums atveras kursantu planšetēs no sava uzdevuma slaida. | Откройте презентацию и нажимайте «Далее» до конца – каждое задание открывается на планшетах слушателей со своего слайда задания. |
| tasks | Trainee tasks | Kursantu uzdevumi | Задания слушателей |
| room | In the room | Telpā | В аудитории |
| reading | For the trainee to read | Kursantam lasīšanai | Для чтения слушателю |
| handout | Handout | Izdales materiāls | Раздаточный материал |
| instructor | Instructor only | Tikai instruktoram | Только для инструктора |
| foot | These buttons open the same pages on this device - to look at a task before the class, or after it. | Šīs pogas atver tās pašas lapas šajā ierīcē – lai apskatītu uzdevumu pirms nodarbības vai pēc tās. | Эти кнопки открывают те же страницы на этом устройстве – чтобы посмотреть задание до занятия или после него. |
| all_files | All files | Visi faili | Все файлы |
| hours | {h} academic hours ({m} min) | {h} akad. st. ({m} min) | {h} ак. ч. ({m} мин) |
| modules | {n} modules | Moduļi: {n} | Модулей: {n} |
| later | Modules {a} to {b} are added as each one is approved. | Moduļi no {a} līdz {b} tiks pievienoti, kad katrs būs apstiprināts. | Модули с {a} по {b} добавляются по мере утверждения. |
| later_one | Module {a} is added when it is approved. | {a}. modulis tiks pievienots, kad būs apstiprināts. | Модуль {a} будет добавлен после утверждения. |
| final | Final assessment | Noslēguma pārbaudījums | Итоговая аттестация |
| mc | Module check | Moduļa pārbaude | Проверка по модулю |

## 4 · The deck's own words — `course-module-ux/assets/gb_deck.js` (LANG, by the page's `<html lang>`) — 2.41.0

The deck is the instructor's, so it uses the polite form (lv *jūs*, ru *вы*), as the start pages do. The chrome is
copied from `gb_shell.html` in English, word for word; the engine puts these words on the controls (label and tooltip,
the tooltip with its key: "Tālāk (→)") when the page's language is lv or ru. `GBDeck.init({text})` still overrides any.

| key | English | Latvian (lv) | Russian (ru) |
|---|---|---|---|
| next | Next | Tālāk | Далее |
| back | Back | Atpakaļ | Назад |
| start | Start | Sākt | Начать |
| grid | All screens | Visi ekrāni | Все экраны |
| cue | Instructor cue | Norāde instruktoram | Подсказка для инструктора |
| noCue | No cue for this screen. | Šim ekrānam norādes nav. | Для этого экрана подсказки нет. |
| full | Fullscreen | Pilnekrāns | Полный экран |
| leave | Leave | Iziet | Выйти |
| close | Close | Aizvērt | Закрыть |
| screen | Screen {n} | {n}. ekrāns | Экран {n} |
| of | of | no | из |
| ovHint | Tap a screen to jump there · G closes this view | Pieskarieties ekrānam, lai uz to pārietu · G aizver šo skatu | Коснитесь экрана, чтобы перейти к нему · G закрывает этот вид |
| hint | → / Space next · ← back · F fullscreen · G all screens · N instructor cue | → / atstarpe – tālāk · ← atpakaļ · F pilnekrāns · G visi ekrāni · N norāde instruktoram | → / пробел – далее · ← назад · F полный экран · G все экраны · N подсказка для инструктора |
| missing | Navigation controls are missing from this page. Add the chrome block from gb_shell.html before delivering this module. | Šajā lapā trūkst navigācijas pogu. Pirms šī moduļa vadīšanas pievienojiet pogu bloku no gb_shell.html. | На этой странице нет кнопок навигации. Перед проведением модуля добавьте блок кнопок из gb_shell.html. |

Terms to check first: *instructor cue* = lv *norāde instruktoram*, ru *подсказка для инструктора* (a cue is what
to say or do on that screen); *leave* (the presentation) = lv *iziet*, ru *выйти*; the Space key = lv *atstarpe*,
ru *пробел*.

## 5 · The deck's landing card — `compile/scripts/compile_module.py` LANDING — 2.41.0

| key | English | Latvian (lv) | Russian (ru) |
|---|---|---|---|
| module | Module {n} | {n}. modulis | Модуль {n} |
| min | {n} min | {n} min | {n} мин |
| screens | {n} teaching screens | Mācību ekrāni: {n} | Учебных экранов: {n} |
| sc | Self-check {c} | Paškontrole {c} | Самопроверка {c} |
| mc | Module check MC | Moduļa pārbaude MC | Проверка по модулю MC |
| fa | Final assessment | Noslēguma pārbaudījums | Итоговая аттестация |
| task | Task {c} | Uzdevums {c} | Задание {c} |

## 6 · Added in 2.46.0 — the engine's "missed" words and the instructor's answer key

`course-task-ux/assets/gb_answer.js` LANG (choose all that are right, answered wrong: a right one not chosen):

| key | English | Latvian (lv) | Russian (ru) |
|---|---|---|---|
| notQuiteMissed | Not quite – what you missed is outlined in green. | Ne gluži – tas, ko palaidi garām, ir apvilkts zaļā krāsā. | Не совсем – пропущенное обведено зелёным. |
| alsoRight | Also right | Arī pareizi | Тоже верно |
| alsoWrong | Also wrong (spot the errors: a wrong line not flagged) | Arī kļūdaini | Тоже ошибка |

`compile/scripts/answer_key.py` WORDS - the instructor's page, the polite form: every string of its `lv` and `ru`
tables (title, "Instructor only", how the pages mark, the column heads, Step / Why / The faulty part ...) is written by
Claude and is PROVISIONAL like the rest of this file.

## 7 · Not covered here

- The picture viewer (`gb_zoom.js`) has its own lv and ru (Aizvērt / Закрыть ...), written before this file.
- The "ru" module check head word on the result screen is ЗАЧТЕНО / НЕ ЗАЧТЕНО; if the college uses
  "СДАНО / НЕ СДАНО" for a module check, change both lines together.
