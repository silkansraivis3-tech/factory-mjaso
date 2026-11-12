# 2D kit - the figure spec (`*.kit2d.json`)

The 2D kit (`kit2d.js`, `kit2d.css`) draws a 2D teaching figure from a short JSON spec, the way the 3D kit draws a
scene: a graph, an object in motion (a cutaway with its flow), or a concept (a cycle, a timeline, a matrix, a process).
Plain SVG, no library. Open `demos.html`, `pm.html`, `more.html` and `courses.html` (a figure for each of five courses) to see every part step by step;
`scripts/test_kit2d.py` walks them all and runs the overlap check at every step.

The figure kit (`../kit/`) stays for what is a control screen (panels, gauges, alarm lists - an HMI the trainee reads)
and for courses already built with it. A new 2D figure is a 2D-kit spec.

## What the kit does by itself - nothing of this goes in a spec

- **Depth.** Every solid is an outline, a body lit from the top left, a hatched cut wall and its contents; a soft
  glow behind the hero and one soft shadow under it. Gradients only, never a filter (smooth on the tablet, L65).
- **Motion.** Every state moves like a critically damped spring: it starts gently, never overshoots, and a new
  target mid-way carries on from where it is. Shapes that land (a triangle's corners, a matrix item, a box popping
  in) spring with a small overshoot; a ring grows once where something has just changed. Next and Previous both
  animate. Whole numbers roll like a counter. Nothing loops by itself (L13); with reduced motion each step is its end.
- **Words.** Labels carry a halo and are placed clear of each other, of the solids and of the lines (arrows, curves,
  trails), with a leader when they must go further; they glide when they move. Axis numbers thin out when the grown
  type no longer fits, and fade out of the way of a value tag. Type grows so no word is under 12.5 px on screen - every
  word, a label's own `<text>` too.
- **Colour.** Course tokens and five category colours (`--cat-1`..`--cat-5`: blue, teal, violet, rose, slate). Its
  warning colour is the factory's alarm amber (`--kit-alarm`): a deck's brand styles make `--amber` blue. Dark is
  the slide; on a light ground the kit takes its light set (`.k2-light`, or `"theme": "light"`).
- **The deck.** Inside a slide the deck's Next and Back walk the steps (GB_HOOKS); a step's `line` lights the
  slide's line. Lines count from 1, as the deck counts them (`"line": 1` is `data-i="1"`, never 0), as a 3D scene's do:
  the deck walks the figure, its lines and, on a slide whose words are in parts, the part that holds the lit line with
  one counter - a line no step names is a Next of its own, before the step after it. Light up to the slide's last
  line; the compile refuses a line outside 1..n and lines left after the last one lit (as for a 3D scene). On a slide
  whose last Next shows an answer (a vote, a pick, a question), the steps that light the lines on screen play first and
  the answer last; a step lighting a line of the answer (or marked `"reveal": true`) plays once it shows. Outside a deck
  the kit draws its own step bar.
- **The overlap check.** `KIT2D.audit(figure)` lists words over words, words that spill out of the box they are written
  in, words or shapes cut at the edge and labels lying on a line, and boxes on each other; a word is out of its box when it leaves the shape itself (a triangle's tip, a diamond's corner), not only its bounding box. A box's words wrap to its width at their grown size. `fit_gate.py` runs it at the end of every step it walks; a finding fails the gate.

## Where it goes

In a course the build sheet names the spec as the slide's figure: `"s05": {"figure": "s05.kit2d.json"}`, the file in
`working_claude/figures/MNN/`. The compiler writes

```html
<div class="fill fig kit2d-fig" data-script-ignore><div class="kit2d-stage" data-kit2d="#k2-s05"></div>
<script type="application/json" id="k2-s05">{ ...the spec... }</script></div>
```

and ships `kit2d.js` (its minified copy `min/kit2d.js` while that is current - after changing the kit, run
`course-module-ui/scripts/minify_engines.py`) and `kit2d.css` with the module. `--init-build` composes a starter from the slide's own lines -
the best fit of everything they can make (bars of its numbers, a time line of its times, a cycle, people speaking, a
comparison, a pyramid, a schedule, a grid, a graph, a process laid out four ways) whose look the slides just before do
not have - and says why in the build sheet's `"_brief"`. Two figures that look alike less than 5 slides apart are listed for
the reviewer; the build carries on. Its `"_todo"`, when it has one, names the values only the course's sources can give, and the compile reports
it until it is gone. Alone: `KIT2D.mount(element, spec)` returns the figure
(`goStep(n)`, `next()`, `prev()`, `idle()`). One figure on its real slide, measured at every step and photographed:
`course-visuals/kit/scripts/studio.py <figure>.kit2d.json` (`--quick` for the findings only, `--step all` for a picture
of every step); `figure_review.py` photographs a module's 2D figures with its other figures.

## Top level

| key | what |
|---|---|
| `label` | what the figure shows, in one sentence (a screen reader; the slide's own words if left out) |
| `size` | `[w, h]` drawing units - give it the shape of the box it is shown in |
| `state` | named numbers at step 0: `{"open": 1, "draw": 0}` |
| `rates` | how fast a state moves (its spring's stiffness; 7 if not given - 3-4 is slow, a curve drawing in) |
| `parts` | the parts, drawn in order |
| `steps` | `[{"title", "set": {state: value}, "after": {state: ms}, "line"}]` - `after` starts that state later, so a step tells its story in order |
| `controls` | what a trainee may try beside the figure: `{"type": "slider", "state", "min", "max", "step", "label", "unit", "scale", "decimals"}` or `{"type": "toggle", "state", "label", "options": [["Open", 1], ["Closed", 0]]}` |
| `readouts` | numbers beside the figure: `{"label", "value", "unit", "scale", "decimals"}`; `"words": ["No", "Yes"]` shows a word the value picks (a valve open or shut, a zone crossed) |
| `glow` | `{x, y, rx, ry}` the light behind the hero, or `false` |
| `theme` | `"light"` or `"dark"` - otherwise chosen from what is behind it |

A part's value is a number, `"@name"` (a state) or `"id.key"` (what another part works out: `"V.flow"`, `"P.y"`).
Steps, sliders, toggles and drags all write the same states, so they never fight.

## Parts

**Graphs**

| type | settings |
|---|---|
| `chart` | `x y w h`, `xaxis` / `yaxis`: `{min, max, step, label, unit, decimals}` - grid, axes, ticks |
| `curve` | `on` (chart), `fn` (`{"kind": "power", "a", "n", "b"}`, `poly` `{"c": [...]}`, `exp` `{"a", "k", "b"}`) or `pts` (joined smoothly), `cat`, `draw` (0..1 drawn in, a bright tip leading), `area`, `label` |
| `point` | `on`, `curve`, `x`, `tagx` / `tagy` (`"{x} kn"`, `"{y} t"`; `tagx: false` for a second point at the same x), `dx` / `dy` decimals, `show`, `drag` (the state a drag writes), `snap`, `min` / `max`, `ghost: {x, show}` - publishes `x`, `y` |
| `span` | `on`, `curve`, `from`, `to`, `show`, `text` (`"{pct} % less fuel"`) - the band and bracket between two points |
| `trace` | `on`, `pts` (a route point to point; a coordinate may be a state, `"@left"`), `cat`, `draw` (0..1, a bright tip leading), `label`, `sub`, `side`, `labelAt` (0..1 along) - publishes `x`, `y` at the tip |
| `region` | `on`, `pts` (an area: a flammable zone, a safe envelope), `cat`, `label`, `sub`, `labelPt`, `show`, `hit: [trace ids]` - lights when a drawn route crosses it; publishes `hit` (1 / 0) for a callout's `show` |
| `bars` | `x y w h`, `items: [{label, value, cat}]`, `max step unit decimals suffix`, `grow` (0..1, one after another), `pick` (k picks out the k-th), `target: {value, label, show}` |

**Objects in motion**

| type | settings |
|---|---|
| `pipe` | `pts` (straight runs), `r` (bore), `wall`, `flow` (0..1), `speed`, `n`, `gate: {x, open}`, `from` / `to` (a pump's or tank's id: it starts at the pump's nozzle and ends through the tank's wall, bolted flange to flange, leaving and arriving level; `pts` are then only the bends) - cut along its length, the flow as streaks that follow it, faster through a gap, stopped when nothing flows |
| `gate_valve` | `x y` (the pipe's axis), `r`, `open`, `turns`, `pressure: [open, shut]`, `label`, `sub` - publishes `flow`, `open`, `pressure` |
| `gauge` | `x y r min max step value unit label stem` |
| `tank` | `x y w h`, `level` (0..1), `inlet` (the y where a pipe comes in through its left wall), `label`, `sub`, `scale`, `unit` - cut open, the liquid rising and falling, its level on a tag; publishes `level` |
| `pump` | `x y` (the shaft), `r`, `speed` (0..1; the impeller stops at 0), `rpm`, `vanes`, `label`, `sub` - a centrifugal pump cut open, its volute widening into a flanged discharge nozzle; publishes `flow`, `speed` |
| `inductor` | `x y` (the inlet face, on the axis), `w`, `r` (bore), `flow` (0..1), `speed`, `label`, `sub`, `names: {nozzle, port, throat}` - an in-line foam inductor (eductor) cut open, water left to right: the jet nozzle, the suction chamber, the metering valve and the pick-up tube over the port, the throat and the diffuser; the water streaks speed up through the jet and the concentrate is drawn in at the port and carried off; publishes `flow`, `suction` (the equipment picture of a foam rig is the figure kit's `foam_inductor`, `foam_branch_pipe`, `foam_container`) |

**Concepts**

| type | settings |
|---|---|
| `triangle` | `corners: [{at, dir, push, base, k, name, value, fmt, note, noteShow, side, dy, hold, strain}]`, `strain`, `frame: {label, show}` |
| `cycle` | `x y r band`, `stages: [{name, sub, cat}]`, `at` (k lights stage k; past the last it goes round again), `center: {text, sub}` |
| `gantt` | `x y w h nameW start end step tick`, `tasks: [{id, name, d, after, slip, crit, cat}]`, `draw`, `crit`, `today`, `finish`, `dur` - a slip pushes what follows; publishes `finish` |
| `matrix` | `x y w h rows cols xlabel ylabel heat`, `items: [{name, r, c, show, dx, dy}]` - r and c from 0 at the top left |
| `node` | `id x y w h kind` (`box` / `decision` / `end`), `text sub cat show lit` |
| `arrow` | `id from to label draw via` (`h` / `v`) - right-angled, drawn on |
| `token` | `route: [arrow ids]`, `at` (k = the end of the k-th arrow), `show` |
| `pyramid` | `x y w h`, `levels: [{name, cat}]` (top first), `at` (levels shown from the top), `pick`, `top` / `bottom` (the side note) |
| `balance` | `x y` (the pivot), `w`, `left` / `right`: `{label, items: [names], weight, cat}`, `k`, `max` - the beam tips on a spring; a pan shows as many items as its weight |
| `events` | `x y w start end step tick`, `clock` (times in minutes after midnight, shown as 02:10), `events: [{at, label, sub, cat}]`, `cursor`, `cursorTag` - each comes in as the cursor reaches it - words that would touch the last ones take the other side or a lane further out (`stem`, `lane` px) |
| `compare` | `x y w h`, `cols: [{title, cat}]`, `rows: [{cells: [..], marks: [1, 0, null]}]` (a tick, a cross, none), `at` (rows shown) |
| `person` | `x y` (feet), `scale`, `name`, `role`, `cat`, `say`, `sayShow`, `side` (`up` / `right` / `left`: the bubble), `bubbleW`, `bubbleH`, `show`, `lit` - `say` may be `{"pick": "@k", "of": [lines]}`, a new line each step |
| `callout` | `at: [x, y]`, `text`, `sub`, `side`, `dist`, `show` - `text` / `sub` may be `{"pick": "@k", "of": [...]}` |

**Hero figures** - one detailed scene a module can build its story on; `courses.html` shows each step by step.

| type | settings |
|---|---|
| `tanker_section` | `x` (centreline), `sea` (waterline y), `k` (px a metre), `beam`, `depth`, `cargo`, `ballast` (0..1), `breach` (0..1: the starboard wing tank floods, the oil stays in), `list`, `highlight` (1 outer hull, 2 inner hull, 3 ballast, 4 cargo), `labels` + `sets` + `words` (the words each step shows) - the double-hull midship section afloat at the draught its load gives; publishes `draught`, `list`, `cargo`, `ballast` |
| `radar_ppi` | `x y r`, `range`, `rings`, `up` (`north` / `head`), `own: {course, speed}`, `sweep` (revolutions, turned at a steady speed - echoes paint as it passes), `t` (minutes), `alter`, `trails`, `vectors`, `vecmin`, `limit`, `clutter`, `targets: [{name, brg, rng, course, speed}]` (true motion), `land`, `vrm`, `ebl`, `labels` - relative motion with ARPA vectors and the CPA; publishes `cpa`, `tcpa`, `rng`, `brg` of the first target |
| `kanban` | `x y w h`, `columns: [{name, wip}]`, `cards: [{id, text, who, cat, tag, col, order, blocked}]`, `labels: [{text, sub, card, edge, col, show}]` - sticky notes pulled from column to column, a WIP badge that turns amber over its limit; publishes `done`, `over`, `n0`, `n1`, .. |
| `motherboard` | `x y w`, `ram` (2 / 4), `focus` (1 CPU and VRM, 2 RAM, 3 graphics card, 4 SSD, 5 chipset, 6 CPU and RAM), `power`, `buses: [{pts, lanes, lit, send, both, tone, fans, cable, label, show}]` (each whole step up of `send` sends one burst of data), `tags: [{on, text, sub, show}]`, `display: {x, y, w, show}` - a PC board from above, its buses lighting up |

A part the kit does not have yet is made in `kit2d.js` with `KIT2D.define(type, function (f, p) {...})`: its colours
by class from `kit2d.css`, its words through `f.label`, its solids and lines registered (`f.solid`, `f.line`) so labels
keep clear, and a card in `demos.html` that `KIT2D.audit` passes at every step.

## Why every figure carries a reason, and custom figures

Operator Aleksis Vējs, 2026-11-09, after the Project Management review: *"draw the drawings 2d kit and 3d with a reason, dont
just put it in just because"*. Every spec carries `"why"` (`mechanism`, `sequence`, `comparison`, `quantity-change`, `spatial`,
`real-thing-recognition`, `still`) and `"why_text"` (one sentence: what the trainee sees change, or sees), and its steps must serve
it - `sequence` / `mechanism` need two steps tied to lines (or a `"reveal"`), `quantity-change` a state value that differs between
stops, `comparison` two states (`course-factory/scripts/figure_why.py`; `check_kit.py`, the compile and the content script refuse
the rest).

**Custom figures - kit first, custom allowed.** When no kit part shows the idea well, draw a custom figure: a self-contained `.html`
or `.svg` file (offline: no network, no `<script src>`; hand SVG, or canvas, or a library already bundled in the plugin) in the
figure folder `working_claude\figures\MNN\assets\figures\sNN.html`, named in the build sheet (`"custom_figure"`, `"why"`,
`"why_text"`). It declares its steps (`<script type="application/json" data-custom-steps>[{"line": 2}, {"line": 3, "reveal": true}]
</script>`) and registers `GB_HOOKS.sNN = {enter, leave, step(dir)}` so the deck's Next drives it (same contract as a kit figure: steps
keyed by line, a reveal step). It passes the same checks - why, changes on every Next (the fit gate), fit and overflow, smooth motion
(`audit_motion.js`, L65), full-screen zoom. **A good custom figure is offered to the kit afterwards:** make it a part
(`KIT2D.define`) with a demo card, so the next module draws it from a spec.
