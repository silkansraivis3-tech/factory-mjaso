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

## 1 · Screen compositions — put ONE on `.slide-body` (`gb_compose.css`)

Pick the composition the **content** needs. Never the same one three screens running out of habit.

| Class on `.slide-body` | Use it for | Inside it |
|---|---|---|
| `opener` (+ `mid` to centre) | module cover, day or block opener, a question left hanging | `.tagline` (small caps line), `h2`, `.q` (the question or sub-line) |
| *(none — ordinary flow)* | lead → cards → takeaway. If you reach for it twice running, stop | `.lead`, `.cards`, blocks from §3 |
| `two-col` (+ `wide-left` / `wide-right`) | an explanation beside a visual — the most useful one | text column, and `.fill` holding the `svg` / `img` / `canvas` |
| `stage` | one dominant teaching visual, as large as the screen allows | the figure (`svg`, `.fill`, or `[data-stage]`), a `.cap`, a `.mediabar` |
| `activity` (slide is `.slide.dark.activity`) | announcing a task, drill or practical — **nothing clickable** | `.act-code` (the code, huge), `.act-title`, `.act-inst`, `.act-steps` of `.act-step` (with `.s` label), `.act-note`, `.act-now` (the "open task N on your tablet" line, `code` for the code) |
| `checkbody` | a knowledge check or debrief question | `h2.bigcall`, `.bigq`, or a `.quiz` (§4), or an `.ans-grid` of `.ans` (`.ans.key` for the key answer) |
| `sum` | the closing grid, one column per block | `.item` each with `.k` (block code/number), `h3`, `p` |

Also a composition in its own right:

| Class | Use it for |
|---|---|
| `.statement` + `.support` (a `ul`) | one claim, then the evidence under it — the workhorse for "here is the idea, here is why". `em` inside `.statement` is the amber emphasis |
| `.trio` of `figure` (`img`/`svg` + `figcaption`, `b` for the caption title) | three photographs or three framed figures filling the stage |
| `data-compose="sparse"` on the slide | declares a deliberately sparse flow screen, so the composition check does not flag it |

## 2 · Photographs (`gb_compose.css`)

| Class | Use it for |
|---|---|
| `.slide.photo` | a photo screen — always dark, so the picture is never framed in white |
| `.photo-wrap` (holding the `img`) | the full-bleed photograph: the photo IS the screen |
| `.photo-scrim` (+ `right`) | the dark gradient the copy sits on; `right` when the copy is on the right |
| `.photo-copy` (+ `right`) | the text over the photo: `h2`, `.lead` |
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
| `.tbl` / `table` inside `.scroll` | a table; `.scroll` lets a wide table scroll in its own box instead of the page |
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
| `.landing-card`, `.landing-title`, `.landing-meta`, `.landing-mod`, `.landing-note`, `.landing-hint`, `.landing-links`, `.landing-rule`, `.brand-chip` | the start (landing) screen before Start is pressed |
| `.ov-grid`, `.ov-head`, `.ov-item` | the overview of all screens |
| `.chip`, `.cbtn`, `.btn-label`, `.fbtn`, `.tag`, `.t`, `.k`, `.n` | the chrome's own buttons, labels and counters |
| `.gbt-topback` | the hidden Back link the Android hardware Back button clicks — every page needs one |
| `.active`, `.cur`, `.on`, `.idle`, `.gone`, `.dark-active` | states **the engine sets** — never write them by hand |

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
| `.opts` of `.opt` | the answer buttons, ≥ 52 px |
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
| `gb_run.js` + `gb_run.css` | the step runner on START_HERE (`course-module-ux`) |
| `kbd_escape.js` + `kbd_escape.css` | the three ways out of the soft keyboard (`course-task-ux` §5) |
| `task_complete.js` + `task_complete.css` | the one shared ending for every task (`course-task-ux` §9) |
| `novikontas_logo.svg` | the logo for the landing screen |
