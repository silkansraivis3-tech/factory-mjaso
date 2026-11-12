# The design vocabulary — every composition and component, and when to use it

**Read this instead of the style files.** The style files themselves are **copied, never read**:
`scripts/design_system.py install <module folder>` puts every one of them into the module's
`assets/` byte for byte, and `scripts/design_system.py check <module folder>` proves the copies are
still identical. This page is the whole vocabulary those files provide — names and when to use each.
`scripts/test_design_system.py` fails if a class exists in the style files and is missing here, or is
named here and does not exist, so this list cannot silently fall behind the files.

Open a style file only to answer one specific question the list below cannot (search it for the one
class; do not read it whole), or when adding something genuinely new — and then the new thing goes
**into the canonical file here in the plugin**, never into a module's copy.

Values (the exact colours, sizes, radii) live in `knowledge/tokens.json` and the measured geometry in
`references/anatomy.md`. Neither is needed to build an ordinary screen.

---

## 0 · The owner's layout templates — every compiled slide is one (L61, `gb_layouts.css`)

Since 2.52.0 a compiled slide also names one of the twenty templates in `data-template` (the template's name and its
version, e.g. explain-figure, version 1) and `data-variant` - and `gb_layouts.css` (loaded after `gb_compose.css`) gives
it the owner-reviewed look of `design/course-layout-templates/`: the top line and the official logo, the large title,
numbered points, the Navy figure panel, 55 / 45 split slides, the thin bottom line - in the brandbook's colours only,
in Raleway (`raleway-variable.ttf`, bundled; SIL Open Font License, `templates/fonts/OFL.txt`). The list, the variants
and the owner's rules are `knowledge/layout-templates.json`; the compositions below are still the structure inside each
template. A hand-built deck without `data-template` looks as it always did.

The few classes of its own, all written by the compiler:

| Class | What it is |
|---|---|
| `.lt-parts` · `.lt-part` · `.lt-part.on` · `.lt-tabs` · `.lt-tab` | content-in-parts: the parts of one slide, the one shown, its numbered tabs - a strip at the foot of the slide body (`gb_deck.js` walks them with Next / Back, a part turning like a page); written only when the script asks for parts |
| `.lt-pfigs` · `.lt-pfig` · `.lt-pfig.on` | each part's own picture (build sheet `"part_figures"`), the one of the part shown; it turns with its words |
| `.fig-top` | the `figure-top` variant: wide photographs in a row on top, each box the photograph's own shape (its width over its height, written on the tile), the words under them |
| `.fig-bottom` | the `figure-bottom` variant: the words first, the picture band across the slide under them |
| `.fig-band` | a band (`.fig-top`, `.fig-bottom`) holding a drawing or a live 3D scene: it keeps its panel |
| `.lt-under` · `.lt-ucol` | the band of a template that has the room answer (scenario, worked-example, true-false, name-parts): its columns (`.lt-ucol`) side by side under the band or over it |
| `.fig-tall` | the `figure-tall` variant: a tall picture beside the words, its box the picture's own shape |
| `.kit-tap` | a line that is a way to its figure's step (kit.js, kit3d.js): tapped, the figure plays that step; it has its mark's gap above and under its words already |
| `.lt-you` | the room's question card in the picture's column, under the picture; its answer opens under it on the last Next (`.lt-ans-under`) |
| `.lt-tiles-fig` · `.lt-tiles` · `.lt-strips` · `.lt-tile` · `.lt-n` | 2.67.0 "tiles": several photographs on one slide, each opens full screen; "strips": cuts of one document, numbered (the compiler builds them - `tiles_figure`) |
| `.lt-table` · `.lt-sep` | reference-table: one row a line; the hidden ` \| ` that keeps the row the approved line |
| `.lt-val` | a line "value \| what it means" among a slide's lines: the value big over its caption, the bar hidden (`.lt-sep`) |
| `.lt-ctable-fig` · `.lt-ctable` | the module's one comparison table as a slide's picture ("table" in the build sheet): 2-4 things side by side, a row a fact, on the white panel (the compiler builds it - `table_figure`) |
| `.lt-block` | three-content-blocks: one numbered block of lines |
| `.lt-compare` · `.lt-card` · `.lt-card-visual` · `.lt-card-copy` · `.lt-compare-note` | compare-two: two cards, each its picture and its lines |
| `.lt-light` | a figure panel in Light Grey for a drawing made for a white page (`"panel": "light"`); the panel is Navy otherwise |
| `.kit-screen` | the figure kit's own screen (course-visuals/kit) - transparent inside the Navy panel, so the drawing sits on the panel |

L62: a repeat of the look of neighbouring slides is a note; the compiler does not flip layouts. The build sheet may
choose the picture's side (`fig-first`), the ground (`dark`), and for a photograph the `figure-stage` variant
`figure-top` (the photograph across the slide, the words in two columns under it) or `photo-explain` `split`. The official logo is drawn larger, its own clear space running into
the margin; a light panel stays white with dark words on a dark slide.

## 0b · The upgraded templates (owner, 2026-11-03, 2.88.0, `gb_upgrade.css` + `gb_steps.js` + `gb_scene.js`)

The same frame as §0 - top line, logo, title, bottom line, type - with a better body. The reference is
`design/slide-templates/` (28 live slides, open `presentation/index.html`). A picture is live 3D, a static 3D render, a
photograph, a 2D-kit or a custom figure, each drawn **with a reason** (its `why`: mechanism, sequence, comparison,
quantity-change, spatial, real-thing-recognition, still), by the picture rule (`course-visuals` SKILL.md, L67). Next walks a slide's stops with `gb_steps.js`: a stop is
every `[data-stop]` in order, or the elements sharing `data-k` (`data-k="0 2"` = shown at both); the stop now gets `.cur`,
the ones before `.lit`; the slide gets `data-at`, `data-last`, and `data-stops` when the marks do not give the count. A slide
the build sheet marks `"still"` has no stops and carries `data-still`: shown whole at once, its step boxes and a table's
conclusion as they are.

| Class | What it is |
|---|---|
| `.lt-in` (its place in the order set on it) | a part that rises into place when the slide comes up, in reading order |
| `.stage.lt-duo` > `.lt-col` > `figure` + `.copy` (the build sheet's `figure_b`) | large figure in two columns: a visual on top of each, its words in a boxed card under it |
| `.lt-steps` · `.lt-row` · `.lt-step` · `.lt-ill` · `.lt-b` · `.lt-track` | sequence of actions as step boxes; the line under them fills |
| `.lt-blocks` · `.lt-show.lt-3d` · `.lt-list` · `.lt-blk` · `.lt-read` (its state `.ok` `.alarm` `.vent`; a tag `.leak`) | three blocks beside one live scene with its reading |
| `.lt-split` (its columns set on it) · `.lt-points` · `.lt-rail` (`.tight`) · `.lt-ask` | words beside a picture box: short numbered points, or a rail of stops (3D fly-through, predict then play) |
| `.lt-3dbox` (`data-lt-scene`) · `.lt-tag` (`data-tag`, `data-at`, `.ok` `.hz` `.big` `.r` `.num`) | a live 3D scene box and the name tags that follow its parts |
| `.lt-link` · `.spot` · `.hs` | reading with figure: a line and its part light together |
| `.lt-spots` · `.lt-spot` (`data-x`, `data-y` in the photo's pixels; `data-px-w` on the photo: the width they were given in, before it was enlarged) | a photo's parts light up one a stop - also on a framed picture (`.lt-pic`) |
| `.lt-zoom` · `.lt-ring` (lines carry `data-z`, `data-x`, `data-y`) | a split photo zooms to the part each line names |
| `.lt-qa` · `.lt-qcol` · `.lt-think` · `.lt-ans` · `.lt-qfig` | opening question: think first, then the answer opens beside it |
| `.lt-pts` · `.lt-pt` · `.lt-ptabs` | words in parts, each part a tab that names it |
| `.lt-boxes` | short boxes under a card's picture, lit with the part now |
| `.lt-task2` · `.lt-tcopy` · `.lt-tab3d` (`.lt-photo`) · `.lt-tabimg` · `.lt-chips` | task opening: the words left with time, questions and alone / in teams as chips; on the right the exercise's photograph or the tablet render |
| `.lt-path` | module check opening: the module's topics tick off towards the check |
| `.lt-ask4` · `.lt-q2` · `.lt-tap` (its words in `data-label`) · `.lt-shine` | the summary: white cards on the pattern, each a question that opens on Next or a tap |
| `.lt-work` · `.lt-meter` (`data-meter`, `data-max`) · `.lt-ans-over` · `.lt-ans-under` | worked example, then the room's turn, beside a meter that counts; beside a picture the answer opens over it on the last Next (`.lt-ans-over`), beside a kit figure in the text column under the question (`.lt-ans-under`) |
| `.lt-tf` · `.lt-claim` · `.lt-vote` · `.lt-why` · `.lt-pic` | true or false, then why |
| `.lt-opts` · `.lt-opt` (`.ok` / `.no`, `.fb`) | what would you do: a situation and its choices, then why each |
| `.lt-name` | name the parts on a live scene (`.lt-tag.num`) |
| `.lt-nbody` · `.lt-nums` | numbers to remember: the number first, then what it means |
| `.lt-ba` (`data-x`) · `.lt-diff` | spot the difference: a slider between two static 3D pictures |
| `.lt-drill` · `.lt-timer` (`data-secs`, `data-run`) · `.lt-acts` · `.lt-qf` · `.lt-find` | quick drills before the module check: the clock runs, and at zero the answer shows by itself |
| inner parts | `.lt-canvas` (the scene's canvas) · `.lt-no3d` · `.lt-cmp` · `.lt-concl` (a table's conclusion) · `.lt-tcopy` · `.lt-sit` · `.lt-scol` (a scenario's picture with its situation under it) · `.lt-do` · `.lt-dcopy` · `.lt-alarm` · `.lt-trow` · `.lt-hint` · `.lt-ask2` · `.lt-qf-dots` · `.lt-qf-list` · `.lt-diff-h` · `.lt-edge` · `.lt-pill` · `.lt-t` · `.kind` - and inside them `.ac` `.an` `.ask` `.bc` `.blank` `.clear` `.dev` `.done` `.drag` `.fc` `.fl` `.ic` `.ln` `.low` `.mc` `.nn` `.open` `.picked` `.pr` `.rd` `.ring` `.scale` `.scr` `.side` `.sm` `.st` `.stamp` `.tf` `.ticks` `.you`; `.kit3d-fig` / `.kit3d-stage` are the 3D kit's own, sized inside `.lt-split`. Set on an element by the compiler or gb_steps.js: the entry order, the split's columns, the slider's place |

## 1 · Screen compositions — put ONE on `.slide-body` (`gb_compose.css`)

Pick the composition the **content** needs. The same one three screens running out of habit is a note to reconsider, never a failure.

| Class on `.slide-body` | Use it for | Inside it |
|---|---|---|
| `opener` (+ `mid` to centre) | module cover, day or block opener, a question left hanging | `.tagline` (small caps line), `h2`, `.q` (the question or sub-line) |
| *(none — ordinary flow)* | lead → cards → takeaway. Three times running is a note to reconsider | `.lead`, `.cards`, blocks from §3 |
| `two-col` (+ `wide-left` / `wide-right`) | an explanation beside a visual — the most useful one | text column, and `.fill` holding the `svg` / `img` / `canvas` |
| `stage` | one dominant teaching visual, as large as the screen allows | the figure (`svg`, `.fill`, or `[data-stage]`), a `.cap`, a `.mediabar` |
| `activity` (slide is `.slide.dark.activity`) | announcing a task, drill or practical — **nothing clickable** | `.act-code` (the code, huge), `.act-title`, `.act-inst`, `.act-steps` of `.act-step` (with `.s` label), `.act-note`, `.act-now` (the "open task N on your tablet" line, `code` for the code) |
| `checkbody` | a knowledge check or debrief question | `h2.bigcall`, `.bigq`, or a `.quiz` (§4), or an `.ans-grid` of `.ans` (`.ans.key` for the key answer) |
| `sum` | the closing grid, one column per block | `.item` each with `.k` (block code/number), `h3`, `p` |
| `recap` (slide is `.slide.dark.recap`, `data-kind="Summary"`) | **the module's closing slide, every module, the same (L51)** - "what to take away", straight before the module-check slide. Animated: the boxes rise in one by one, a blue-to-amber rule draws across each, then the "next" strip | `ol.rc-grid` with `data-n` = the number of points (3-6), each `li.rc-item` (`data-script-field="text"`) holding `b.rc-t` (short title), `span.rc-sep` (" - ", hidden, keeps the approved words whole) and `span.rc-d` (the sentence); then `p.rc-next` (`data-script-ignore`). Numbers come from CSS. Full markup: `gb_compose.css` section 15 |

Also a composition in its own right:

| Class | Use it for |
|---|---|
| `.statement` + `.support` (a `ul`) | one claim, then the evidence under it — the workhorse for "here is the idea, here is why". `em` inside `.statement` is the amber emphasis |
| `.trio` of `figure` (`img`/`svg` + `figcaption`, `b` for the caption title) | three photographs or three framed figures filling the stage |
| `data-compose="sparse"` on the slide | declares a deliberately sparse flow screen, so the composition check does not flag it |

Compiled slides (2.25.1, §13b — written by `course-factory/compile/`, usable by hand too):

| Class | Use it for |
|---|---|
| `.copy` (+ `tight`) | the words beside or under a picture at reading size; holds `.statement`, `.lead`, `.support`. A line a figure lights (`data-i`) keeps 10 px of inner padding so its wash and amber ring clear the words (a bullet line keeps its bullet room); `.copy.tight` opts a full slide whose words reach the margins out (2.63.2) |
| `.box` (+ `alt`) · `.call` | inside `.copy`: a line set apart (blue - every box the same) · `alt` only where the build sheet names `box_alt`, the other of two options (grey, never amber) · the conclusion line (navy) |
| `.inset` (`img` + `figcaption`) | inside `.copy`: a small real photograph under the words, its caption and credit |
| `.fill.fig` | the picture's box: the drawing and its controls stacked, taking the room the words leave |
| `.two-col.fig-wide` | two-col with the wider column for the picture |
| `.legend` (`li[data-i][data-n]`) | a numbered row under a stage drawing; the badge shows `data-n` (1, 2, 3 in the row); `.own-numbers` when the words already start with their number - no badge |
| `.two-col.fig-wide.fig-first` | the drawing on the left, the words on the right |
| `.slide-body.dom-fig` | written by the compiler (2.52.0): the figure first in the markup - first on a portrait tablet - and the words put back first on a landscape screen by CSS `order`; never typed by hand |
| `.slide.photo.split` | a photograph filling the right of the screen, the words on the dark left |
| `.act-ico` · `.act-lines` | the task slide's tablet sign · its lines grouped at reading size |
| `.no-code` · `.act-lead` · `.act-bullet` | a room activity with no task code (no `opens`): one column, no code printed · a long activity text: its first line the lead statement, the rest bullets |
| `.act-photo` | (2.63.0) the exercise's real photograph on its task slide, in place of the sign (build sheet `"photo"`); opens full screen with its record |
| `.aside` | small drawings that belong with the words (mini figures on a photo slide) - compact, never pushing the words off the screen |
| `.fig` · `.fig-wide` · `.fig-first` · `.dom-fig` · `.own-numbers` · `.split` | the modifiers above, named on their own for the vocabulary check |
| `.cur` · `.lit` on a `[data-i]` line | **set by a figure that steps** — the line it is on (amber wash, amber ring and bar; it out-ranks every card look) and the lines already shown (blue). Amber on a line means "here now" only: no card at rest is amber. `audit_deck.js` fails a selected line that looks like itself or another line at rest |

## 2 · Photographs (`gb_compose.css`)

| Class | Use it for |
|---|---|
| `.slide.photo` | a photo screen — always dark, so the picture is never framed in white |
| `.photo-wrap` (holding the `img`) | the full-bleed photograph: the photo IS the screen |
| `.photo-scrim` (+ `right`) | the dark gradient the copy sits on; `right` when the copy is on the right |
| `.photo-copy` (+ `right`) | the text over the photo: `h2`, `.lead` |
| `.support.seq` (an `ol`) · `.n` · `.lead.step` in `.photo-copy` | steps the script numbers itself (`1 …`, `2 …`, from 1 in order): one list, every step the same size, the step's own number in a navy disc (blue on dark) as its marker - never step 1 as a headline and the rest as squares. The number stays in the words (`.n`) for the match check. Set by the compiler |
| `.lead.head` · `.lead.sub` in `.photo-copy` | words with points over a photo: `.head` is a line that heads its points (bold, white, a step larger — as a text slide marks its opening line), `.sub` is a point under it (the `.support` list's blue square). **One bullet look in every deck**: no amber rule on a heading line — amber rule means a takeaway or a law. The compiler sets both from the script's `•` lines |
| `.photo-badge` | the small amber label above the copy |
| `.credit` | the licence / credit line — required on the page for any photo that needs attribution |

## 3 · Content blocks — usable in any composition (`gb_compose.css`)

| Class | Use it for |
|---|---|
| `.lead` | the opening sentence or paragraph of a screen |
| `.cards` + `c2` / `c3` / `c4` | two, three or four cards — **never one, never five** (one is a paragraph with a border; five is a table) |
| `.card` | one card: `.n` (number chip), `.tag` (small caps label), `h3`/`h4`, `p`, lists |
| `.card.key` · `.card.step` · `.card.warn` · `.card.good` | blue rule = key point · amber rule = a step · red rule = caution · green rule = correct / safe |
| `.law` with `p` + `.ref` | a quoted regulation or rule, with its reference line |
| `.warnbox` | a warning — red. Only for real hazards and cautions, never "important" |
| `.fin` | a finding or a correct conclusion — green |
| `.meta` (of `span`s) | small facts in a row: duration, group size, equipment |
| `.steps` (an `ol`, `strong` for the step name) | a numbered procedure |
| `.num` | a number or code set in the mono face, lined up |
| `.tbl` / `table` (inside `.scroll` on a task or document page only) | a table; on a task or document page `.scroll` lets a wide table scroll in its own box. On a slide a wide table is laid out again - fewer columns, a split, or the rest in the notes (no scrollbar on a slide) |
| `svg.fig` | a framed inline drawing |
| `.cap` | a caption under a figure |
| `.src` / `.srcline` | the source line — small, faint, at the bottom |
| `.takeaway` with `.tk` label | the one line the room should leave with, pinned above the chrome. **One per screen at most** |
| `.frag` (+ `on`) | a fragment revealed on a step — the engine adds `on` |

## 4 · Controls and the in-deck quiz (`gb_compose.css`)

| Class | Use it for |
|---|---|
| `.mediabar` of `.fbtn` (+ `primary`) | the button bar under a figure that steps an animation — centred, ≥ 44 px, never hover-only |
| `.dots` (of `i`, engine adds `on`) | the step indicator beside a mediabar |
| `.caption` | the centred explanation line under a figure and its controls |
| `.quiz` → `.q-head` (`.qn` label) → `.q-text` → `.q-opts` of `.q-opt` (`.mk` letter) → `.q-why` | a question asked to the room on the deck. The engine marks `.q-opt.right` / `.q-opt.wrong` and shows `.q-why` with `on` |

## 5 · The deck frame — already in the starter deck (`gb_shell.css`, `gb_shell.html`)

`design_system.py install --start-deck` writes `module.html` from `gb_shell.html`, so the frame is
there before the first screen. Write screens inside it; do not rebuild it.

| Class | What it is |
|---|---|
| `.slide` (+ `dark`, `photo`) | one screen. Light by default; `dark` or `photo` chosen per screen, never as a theme |
| `.slide-kind` | the navy header band — says what KIND of screen this is, not the module name |
| `.slide-body` | the content area — carries the composition class from §1 |
| `.landing-card`, `.landing-title`, `.landing-mod`, `.landing-note`, `.landing-hint`, `.landing-links`, `.landing-rule`, `.brand-chip` | the start (landing) screen before Start is pressed |
| `.ov-grid`, `.ov-head`, `.ov-item` | the overview of all screens |
| `.chip`, `.cbtn`, `.btn-label`, `.fbtn`, `.tag`, `.t`, `.k`, `.n` | the chrome's own buttons, labels and counters |
| `.gbt-topback` | the hidden Back link the Android hardware Back button clicks — every page needs one |
| `.gb-fs3d`, `.gb-fs3d-btn`, `.gb-fs3d-on`, `.gb-fs3d-faked`, `.gb3d-lbl`, `.gb3d-on` | a 3D scene's box, its Full screen button, the box full screen (or in a full-window box), a label that selects its part and the selected one - **the engine sets them** (2.63.2); a scene marks its labels `data-3d-part` and calls `GB3D.wire` |
| `.active`, `.cur`, `.on`, `.idle`, `.gone`, `.dark-active`, `.banded` | states **the engine sets** — never write them by hand (`.banded`: the corner tag, hidden on a screen whose header band names it) |

## 6 · Document pages — START_HERE, handout, practical cards, plans (`gb_page.css`)

Load order: `gb_tokens.css` → `gb_page.css`.

| Class | Use it for |
|---|---|
| `.gbt-topback` (with `.gbt-ico`) | the sticky 48 px Back bar at the top — every document page |
| `.wrap` | the page column |
| `.sub`, `.lead`, `.note` | sub-title line, opening paragraph, small note |
| `.card` + `key` / `step` / `hot` / `good` / `warn` | the same cards as the deck; `hot` = amber, a point to watch |
| `.grid` (+ `c2` / `c3`) | a grid of cards |
| `.meta` | small facts in a row |
| `.crit` | what the instructor is judging — blue, it is information |
| `.stop` | a hard stop — red, never for merely important things |
| `.law` with `.ref` | a quoted rule and its reference |
| `.scroll`, `.cap`, `.fig`, `.src`, `.ref` | table box, caption, figure, source line, reference |
| `.bigstart` | the one big "Start" button on START_HERE |
| `.links` (of `a`) | a list of big tappable links, ≥ 56 px each |
| `.jump`, `.toc` | the P1 P2 P3 jump strip at the top of a long page |
| `.back` | a Back button inside the page |
| `.foot` | the footer — provenance and small print |
| `tr.p` · `td.n`, `td.m` | in a plan table: a highlighted row · a number or minutes cell in the mono face |

## 7 · Task pages (`gb_task.css`, on top of `gb_page.css`)

Load order: `gb_tokens.css` → `gb_page.css` → `gb_task.css`. Behaviour is `course-task-ux`'s.

| Class | Use it for |
|---|---|
| `.state` → `.part`, `.got`, `.bar` (with `i`) | the sticky state bar: which part, how many right, progress |
| `.q` (`.num`, `.stem`), `.stem` | the question and its number |
| `.opts` of `.opt` | the answer buttons, ≥ 56 px |
| `.opt` states `sel`, `right`/`ok`, `wrong`/`no`, `dim` | **set by the engine** — selected, correct, wrong, greyed out |
| `.why` (+ `good` / `bad`, engine adds `on`) | the explanation of why it was right or wrong — the feedback that teaches |
| `.sub` | the full-width 56 px confirm button (not a subtitle) |
| `.part2` (engine adds `on`) | the second half of a predict-then-check task — hidden until revealed |
| `.sv`, `.drawn` | a figure inside a task |
| `.samples` (of `span`) | a row of sample chips |
| `.wrap` | the page column — on a task page it leaves room for the thumb at the bottom |

## 8 · Tokens — names only (`gb_tokens.css`)

Every colour, radius, shadow and font in new work is one of these. **Pick the `-l` variant on a
light surface and the `-d` variant on a dark one.**

| Group | Names |
|---|---|
| structure | `--navy` `--deep` `--deep-2` `--deep-3` `--steel` `--white` `--grey` `--ink` |
| accent | `--blue` `--blue2` (interface: "this is active") · `--amber` `--amber-ink` (emphasis, never a warning) |
| text on dark / light | `--txt-d` `--dim-d` `--faint-d` · `--ink` `--dim-l` `--faint-l` |
| lines and washes | `--line-d` `--line-l` · `--blue-wash-d` `--blue-wash-l` · `--amber-wash-d` `--amber-wash-l` · `--good-wash-l` `--warn-wash-l` |
| meaning | `--good` `--good-d` (correct, safe) · `--warn` `--warn-d` (wrong, caution) · `--cold` (a content colour: cryogenic — diagrams only) |
| text on a filled surface | `--on-blue` `--on-navy` |
| shape | `--r-l` (panels, photo frames) `--r-m` (default) `--r-s` (pills, chips) · `--sh` `--sh-d` (shadows) |
| type | `--font` (Raleway stack) · `--mono` (figures, codes) |

A raw colour on `fill` / `stroke` **inside a diagram** is content and stays raw. There are no hazard
colours in the set; adding one is an owner decision (`knowledge/tokens.json` § open_questions).

## 9 · The engines — copied, not read

| File | What it does |
|---|---|
| `gb_deck.js` | the deck engine: `GBDeck.init({text, hooks})` — Start, Next/Prev, progress, overview, instructor cue, fullscreen, keyboard, swipe, per-screen enter/leave hooks (`course-module-ux`) |
| `gb_fit.js` | no drawing cut off at its edges: when a slide comes up, an `<svg>` whose drawing reaches past its viewBox gets a frame just big enough, and a console warning to fix the drawing; `data-fit="off"` opts out (`course-module-ux`, L53) |
| `kit.js` | the figure kit: draws and steps every figure file named NAME.kit.json (a spec, never a drawing), lights the slide's `[data-i]` lines per step, registers the slide's hooks; a course's own new parts load after it from `assets/kit_parts.js` (`course-visuals/kit`, L55) |
| `kit.css` | the figure kit's look - ISA-101, grey at rest, amber alarm, red trip, tokens only; it also holds a kit figure on a slide above its `.mediabar` (`course-visuals/kit`, L55) |
| `kit3d.js` | the 3D kit (three.js r128 loads first): draws and moves every 3D scene named NAME.kit3d.json (a spec, never three.js) - labels that are buttons for their parts, tap-to-frame, full screen, steps walked by Next / Back, built ahead on the slide before; a course's own new parts load after it from `assets/kit3d_parts.js` (`course-visuals/kit3d`) |
| `kit3d.css` | the 3D kit's look - the stage, the label pills, the corner controls (`course-visuals/kit3d`) |
| `kit2d.js` | the 2D kit: draws and moves every 2D figure named NAME.kit2d.json (a spec) - graphs, objects in motion, concepts; depth, labels clear of each other, steps walked by Next / Back, the trainee's controls beside it, and `KIT2D.audit` for the fit gate (`course-visuals/kit2d`) |
| `kit2d.css` | the 2D kit's look - its depth tokens, the five category colours, the labels, the controls and readouts beside a figure (`course-visuals/kit2d`) |
| `gb_run.js` + `gb_run.css` | the step runner on START_HERE (`course-module-ux`) |
| `gb_interact.js` + `gb_interact.css` | the interactive task types of a trainee page, beside `gb_answer.js`: true or false, check a colleague, work it out, predict, explore, investigate, line it up (3D), inspection round (3D / 360), take it apart (3D), test before entry - each a question part `gb_answer.js` checks like any other (`course-task-ux`, 2.74.0) |
| `gb_zoom.js` + `gb_zoom.css` | **every picture opens full screen and closes again (L51)** - on every page that shows a picture: the deck, every task, the module check, the handout. Starts by itself, nothing wired per picture. Tap opens; X, a tap on the dark, Esc, swipe down, Back and the next slide close; pinch, double-tap or + / − zoom. A picture the trainee answers ON (hotspots over it) gets a corner ⤢ button instead, so a tap stays the answer. `data-no-zoom` on a figure leaves it out (a picture inside a button, a driven `[data-motion]` figure, video and 3D are left out by themselves) (`course-module-ux`). **A photo's record (L56):** when the `<img>` carries `data-name` / `data-about` / `data-credit` (the compiler writes them from `_photo_meta.json`), full screen shows them under the picture - the part it shows, what is in it, whose it is (the viewer's own classes in `gb_zoom.css`: `gbz-cap gbz-record`, `gbz-name`, `gbz-about`, `gbz-credit`). A slide that is a photograph opens on a tap of its bare picture area and gets the ⤢ button on the slide (`gbz-corner gbz-photo`). Loaded by every compiled deck too |
| `.two-col.photo-col` > `.fill.photo-col` | (`gb_compose.css`, 2.49.1) a photo slide laid out `wide-left` / `wide-right` in the build sheet: a real column layout, the photo cropped to fill its column, its credit line kept - so long words get the room `photo split` cannot give them. Written by the compiler, never by hand |
| `.photo-strip` > `.pthumb` | (`gb_compose.css` 16, L57) the real photos of what a drawing shows, in a row under it, each numbered like the drawing and opening full screen with its record - written by the compiler, never by hand |
| `gb_answer.js` + `gb_answer.css` | the one shared engine and screens of every compiled task page - choose, tap the picture, drag and drop, label the drawing, the result ring; grading by `data-key`, `gb-task-done`, `gb-timer` (`course-factory/compile/scripts/task_pages.py`) |
| `gb_lab.js` + `gb_lab_navy.css` / `gb_lab_white.css` | the richer tasks a set shows in a frame (`course-task-ux/engines`, a page each, `tasks/frame_<id>.html`): their big button, sheets, how sure and result, in the screen's theme; the frame reports to the set page (`gb_interact.js`) |
| `gb_task_look.css` | the task screens in the brandbook's look, loaded last: each question's screen marked th-w (white, the NA pattern at its right edge) or th-n (Navy), picked by `task_pages.py` so neighbouring screens do not repeat (build sheet `"theme"`); the page round it follows the screen on show. Changes no size or place of `gb_answer.css` |
| `kbd_escape.js` + `kbd_escape.css` | the three ways out of the soft keyboard (`course-task-ux` §5) |
| `task_complete.js` + `task_complete.css` | the one shared ending for every task (`course-task-ux` §9) |
| `novikontas_logo.svg` | the logo for the landing screen, and the top right of every light slide |
| `novikontas_logo_white.svg` | the same official logo, its one colour switched to white: the top right of every dark (blue) or photo slide, no plate (owner, 2026-10-21) |
| `task_tablet.png` | a task slide's picture when the exercise has no photograph: the tablet in 3D with an empty task screen, no words (2.89.0) |
| `na_pattern_on_light.svg` · `na_pattern_on_navy.svg` | the brandbook's NA pattern, only where nobody reads: the opening, task, check and summary slides, the start screen (2.88.0), the right edge of a task screen |
| `gb_upgrade.css` | the upgraded templates' bodies (§0b), after `gb_layouts.css` - loaded by every compiled deck |
| `gb_steps.js` | Next walks an upgraded slide's stops and drives its scene, photo, meter, slider or clock (§0b) - before `gb_deck.js` in every compiled deck |
| `gb_scene.js` | a picture box's live 3D scene (three.js r128): one shared canvas, draws only while its slide is up, still for reduced motion; the scenes are the course's own file (`course-visuals/scene/examples/m01_scenes.js` is the reference) |
