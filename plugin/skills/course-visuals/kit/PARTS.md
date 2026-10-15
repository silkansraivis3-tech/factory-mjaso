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
/* kit-part: drip_tray */
KIT.define('drip_tray', function (fig, part, g, p) {
  var h = KIT.h, w = p.w || 120;                       // settings, each with a sensible default
  h.el('rect', { width: w, height: 18, rx: 4, 'class': 'kit-steel' }, g);   // kit classes first
  var pool = h.el('rect', { x: 4, y: 14, width: w - 8, height: 0, 'class': 'kit-pool' }, g);
  if (p.label) h.lines(g, { x: w / 2, y: 40, 'text-anchor': 'middle', 'class': 'kit-cap' }, p.label);
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

## The rules - `check_kit.py parts` enforces them
- **The markers** `/* kit-part: name */` … `/* end kit-part */` are required, one part per block. They are how
  promotion finds the part.
- **Use the helpers** `KIT.h.el / lines / clamp / fmt / polar / arc`. Don't use `innerHTML`, and don't make
  your own `createElementNS`.
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
- **Nothing is cut off and nothing overlaps.** Run the example through `course-module-ux/measure/scripts/
  audit_drawing.js` (L54).

## After the merge
Promotion copies the block into the factory's `kit.js` with `status: 'kit'`. When colleagues update the
plugin, their modules get the part from `kit.js`. A module that still carries its own copy in
`kit_parts.js` keeps working, because the kit's version wins and the module's copy is skipped with a
console note. Remove the module's copy when the module is next rebuilt.
