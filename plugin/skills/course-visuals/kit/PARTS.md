# Making a part the kit does not have yet

**L55, owner decision 2026-10-15:** *use the kit. If the kit has no part for what the module needs, the AI
makes the part, puts it in the kit, and asks for a merge once the module is complete.*

A new part is never a one-off drawing on a slide. It is a kit part from the first line: it draws itself
from its settings, its value moves through the step engine, it uses only the kit's helpers and the course
colour tokens, and once it is merged every later module and course has it.

## The flow

```
module needs X ── kit has X? ── yes ──► write the spec (figures/MNN/sNN.kit.json)
                       │
                       no
                       ▼
     1  make X in the module's assets/kit_parts.js     status "new", with an example spec
     2  check_kit.py parts …/kit_parts.js              colours, type, helpers, example - must pass
     3  use X in the module's specs; compile; QA       the module ships with X working
     4  module complete ► kit_parts.py promote         X goes into the factory's kit.js, status "kit"
     5  ask the operator ► push the branch ► open the merge request for Raivis
```

Steps 1-3 never wait for anyone: the module is built and taught with the new part. Step 4 runs **only after
the module is complete**: its QA passes and its deck is compiled. In a build with one agent per module,
an agent never edits the factory's `kit.js`. It only writes its own `kit_parts.js`, so two modules can't
collide, and the orchestrator promotes the parts of all modules together at assembly.
If two modules made the same thing, it merges them into one part.

## Before you make one

1. **Check the kit.** Read `SPEC.md` (the part list) and the "parts added from courses" at the end of `kit.js`.
   A part with different settings is not a new part: a gauge for breathing-apparatus pressure is a `gauge`.
2. **Check that a real photo isn't the answer** (course-visuals choice order). Equipment a trainee must recognise
   is a photograph. The kit is for systems, states, flows and sequences.
3. **Name it for what it is, not where it is used:** `drip_tray`, not `m03_tray`. Use lower case and `_`.

## The template

```js
/* kit-part: oil_tray */
KIT.define('oil_tray', function (fig, part, g, p) {
  var h = KIT.h, w = p.w || 120;                       // settings, each with a sensible default
  h.el('rect', { width: w, height: 18, rx: 4, 'class': 'kit-steel' }, g);   // kit classes first
  var pool = h.el('rect', { x: 4, y: 14, width: w - 8, height: 0, 'class': 'kit-pool' }, g);
  if (p.label) h.label(fig, g, { x: w / 2, y: 40, 'text-anchor': 'middle', 'class': 'kit-cap' }, p.label);  // the layout places it
  part.render = function (v) {                         // value -> picture; called on every frame
    var d = h.clamp(v, 0, 1) * 12;
    pool.setAttribute('y', 16 - d); pool.setAttribute('height', d);
  };
}, {
  family: 'piping',                 // instruments | piping | spaces | cutaways | gas-fire-machinery | charts | procedures
  status: 'new',                    // "new" until merged; promote sets "kit"
  course: 'IGF Basic', module: 'M03', made: '2026-10-15',
  why: 'M03 s07: liquid caught under the bunker manifold',
  value: 'how full the tray is, 0..1',
  css: '',                          // only if the kit's classes cannot do it - tokens only, kit-<part>- prefix
  example: { size: [300, 120], parts: [{ id: 'D', type: 'drip_tray', x: 90, y: 40, label: 'drip tray' }],
             steps: [{ title: 'A spill is caught', play: [['D', 1, 2000]] }] }
});
/* end kit-part */
```

## Words, boxes and colours - the kit does the drawing work (2.48.0)

- **A part's words are labels: `h.label(fig, g, attrs, text, opt)`**, never a bare `h.lines`/`h.el('text')` for a name,
  caption or state. The layout gives every label a place clear of every shape, line and other label, and its own box's
  edge (L54, 4 px), at the end of every step - beside its part if it can, further out with a leader line if it must. Put
  it where it reads best; the layout moves it only when it is not clear. `opt.inside: true` keeps it inside the part
  (a room's name; `opt.within: <element>` inside that shape), `opt.near: 16, lead: false` lets it shift a little but
  never leave its mark (a scale mark's words), `opt.fixed: true` never moves it. More text can go into the group it
  returns (a valve's name and its OPEN/CLOSED move together). Tick numbers and the words inside a box stay plain text.
- **A box that holds words is sized to them: `fig.fit(function (k) { ... })`.** It runs at layout time, when the words
  have their real width, with `k` the factor the kit grows every type size by (see below). Measure with
  `h.widest(textElement, [all the words it can show])` - a readout's widest reading is `h.readings(p, min, max, marks, v0)`
  - and set the box's width, and its height times `k`. `fig.fit(fn, true)` runs after every other fit (a frame that
  holds other parts, like `panel`).
- **No word is ever drawn under 12.5 px.** When a figure is shown smaller than 1:1 the kit sets `--kit-up` and every kit
  type class grows by it (`kit-cap`, `kit-h`, `kit-tick`, `kit-num`, `kit-tl`, `kit-state`, `kit-sl`, `kit-big` ...). So a
  part uses those classes and sizes its boxes and rings with `fig.fit` and `k`. A `font-size` in a part's `css` does not
  grow: the drawing audit's SMALL TEXT reports it.
- **Colour by the dark-panel tokens, and both panels are right.** `var(--txt-d)`, `--dim-d`, `--faint-d`, `--cold`,
  `--deep`, `--deep-3`, `--amber`, `--warn-d` ... On a light ground (a light page; a task page shows kit drawings on the dark screen since 2.46.0) kit.css `.kit-light` makes
  each of them mean its light counterpart, so a part keeps its contrast on either by construction. Never a light token
  (`--navy`, `--steel`, `--line-l`, `--dim-l`) in a part: it is right on one panel only. A part that is quiet on purpose
  (a backdrop, a pale cloud, the core inside a flame) carries `data-low-contrast`, with the reason in a comment.
- **Try it in the studio before anything else:** `scripts/studio.py <example>.kit.json --parts <kit_parts.js>` draws
  it on a dark slide (`--panel two-col`) and on a task page (`--panel task`, the light ground) at 1280 x 800 and
  1024 x 768, audits every step and saves a screenshot - in seconds.

## The rules - `check_kit.py parts` enforces them
- **The markers** `/* kit-part: name */` … `/* end kit-part */` are required, one part per block. They are how
  promotion finds the part.
- **Use the helpers** `KIT.h.el / label / lines / widest / readings / clamp / fmt / polar / arc`. Don't use
  `innerHTML`, and don't make your own `createElementNS`.
- **Colours come only from the kit's classes or `var(--token)` in `css`.** Don't use `#hex`, `rgb()` or named
  colours, and don't set `fill`/`stroke` in JavaScript.
- **Text uses only the kit's type classes** (`kit-h`, `kit-cap`, `kit-tick`, `kit-num`, `kit-tl`, `kit-state`).
  Don't set `font-size` in JavaScript. In `css`, keep labels at 12.5 px or larger.
- **ISA-101:** grey and blue at rest. Amber is for alarms only and red for trips only, both through marks
  (`part.flag`) or a state class.
- **Motion carries the teaching.** Change the picture in `render(v)`, from a value the steps move. Use a CSS
  animation only for something continuous that `motion(d)` turns on and off while the value changes
  (drips, flow). Never a loop that runs by itself.
- **`css` class names start with `kit-<part>-`,** so two parts never collide.
- **`example` is required.** `check_kit.py` checks it as a spec, and the gallery draws it as the card Raivis
  reviews under "Parts added from courses".
- **Nothing is cut off and nothing overlaps, on either panel.** Run the example through `scripts/studio.py`
  (`--panel two-col` and `--panel task`): it runs `course-module-ux/measure/scripts/audit_drawing.js` (L54) at every step.

## After the merge
Promotion copies the block into the factory's `kit.js` with `status: 'kit'`. When colleagues update the
plugin, their modules get the part from `kit.js`. A module that still carries its own copy in
`kit_parts.js` keeps working, because the kit's version wins and the module's copy is skipped with a
console note. Remove the module's copy when the module is next rebuilt.
