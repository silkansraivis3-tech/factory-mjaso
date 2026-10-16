# Figure kit - the spec format

A figure is a JSON spec: **parts** placed on a canvas, and **steps** that move their values.
`kit.js` draws the parts and runs the steps, and `kit.css` gives the look. Nothing is drawn by hand.
`GALLERY.html` shows every part moving, plus slide M02 s14 rebuilt from a spec.

**In a course (L55)** the spec is a figure file: `working_claude/figures/M02/s14.kit.json`, named in the build
sheet like any drawing (`"s14": {"figure": "s14.kit.json", "dark": true}`). The compiler does the rest: the
spec as data, the deck's step buttons, `kit.js`/`kit.css` (installed by `design_system.py`). Check specs with
`scripts/check_kit.py module <module> --figures <figures/MNN>`. A part that doesn't exist yet: `PARTS.md`.

By hand (the gallery does this):
```html
<svg data-kit="#spec-s14"></svg>                      <!-- mounts automatically -->
<script type="application/json" id="spec-s14">{ ... }</script>
```
Buttons `[data-act=prev|next|replay]`, a `.dots` span and a `[data-kit-title]` element found in the
same parent (or in the nearest `[data-kit-scope]`) are wired automatically.

**Try it first in the figure studio (2.45.0)** - one spec, its real slide, every step, both screen sizes, every drawing
audit and a screenshot, in seconds, without compiling the module:
```
python scripts/studio.py <course>/working_claude/figures/M03/s07.kit.json        (on its real slide, from the build sheet)
python scripts/studio.py <spec>.kit.json --parts <kit_parts.js> --panel two-col|dark|wide-left|task|WxH
```
It judges 1280 x 800 (the tablet) and states 1024 x 768: the scale the figure is shown at, how much the kit grew the
words for the 12.5 px floor, how many labels it moved, any it could not place, and every audit finding per step.

## What the kit does by itself (2.45.0) - nothing of this goes in a build sheet
- **Labels.** Every name, caption and state a part draws gets a place clear of every shape, line and other label, and
  of its own box's edge (4 px, L54), judged at the end of every step - beside its part, or further out with a leader
  line. A spec places a part; it never places its words. A label that finds no clear place stays where the part put it
  and is reported (the studio, the browser console).
- **The 12.5 px floor.** Shown smaller than 1:1, every type size grows by 1/scale (at most 2x) and the layout makes room
  for it: boxes, rings and rows grow with their words. A figure whose words then need more room than its panel gives
  stops growing at 1.3x its width and the drawing audit's SMALL TEXT reports it - give it more room or fewer words.
- **Boxes sized to their words.** A readout, a gauge or level readout, the alarm chip, an alarm row: as wide as the widest
  thing it can show. An alarm too long for its log goes on two lines.
- **The frame.** A drawing that reaches past its frame makes the frame larger (taller only, when its column has the
  height); one lost in its frame is zoomed in to fill it (L53, at most 1.5x; never with `view`, an inset photo over it,
  or `"fit": false`).
- **Both panels.** On a light ground (a task page) the figure takes the light mapping of the course tokens (kit.css
  `.kit-light`) - chosen by what is behind it, or by `"theme": "light"|"dark"`.

## Top level
| key | meaning |
|---|---|
| `size` | `[w, h]` viewBox |
| `view` | `[x, y, w, h]` - another window on the canvas (task pages only, see Task mode) |
| `theme` | `"light"` or `"dark"` - otherwise chosen from what the figure is drawn on |
| `fit` | `false` - never zoom the drawing to fill its panel |
| `label` | aria-label: what the figure shows, in one sentence |
| `idle` | text under the figure at step 0 |
| `clock` | start time of the alarm log, default `"10:42:00"` |
| `parts` | list, drawn in order (later parts sit on top) |
| `steps` | list, see below |

## Parts - all take `id`, `type`, `x`, `y`, `value`
| type | options | value |
|---|---|---|
| `panel` | `w h title` - frame, title, alarm-state chip | - |
| `level` | `w h label unit min max ticks readout decimals marks` | the level |
| `gauge` | `r label unit min max start sweep normal:[lo,hi] ticks every numbers readout decimals caption captionAt marks` | the reading |
| gauge repeater | `source:"P1" mini:true` - copies the scale of P1 and follows it | - |
| `readout` | `w h label unit sign decimals marks` - digital tile | the reading |
| `well` | `w h tag` - bilge well, dripping leak, TT sensor | pool 0..1 |
| `valve` | `size label labelAt(right) rotate state(false) actuator(false) trip(false)` - ISA bow-tie, filled when closed; red when shut unless `trip: false` | 1 open, 0 closed |
| `pipe` | `d` (SVG path) `fluid`(liquid/gas/air - air: a ventilation duct) `double` `drain` - its contents and their movement | flow 0 still … 1; **`<id>.fill`** 0..1 the front advancing, 1..2 emptying towards `drain` |
| `tank` | `w h label` - horizontal type C tank | liquid level 0..1 |
| `space` | `w h label labelAt(below) style(room/enclosure)` - a room (dashed) or an enclosure (solid) | 0..1 picked out |
| `exchanger` | `r label` - P&ID heat exchanger (vaporizer, heater) | 0..1 heating |
| `pump` | `r label` - P&ID centrifugal pump | 0 stopped, 1 running |
| `engine` | `w h cylinders label` - dual-fuel engine block | 0 stopped, 1 running |
| `vent` | `label labelAt(left)` - vent outlet to the open air | 0..1 venting |
| `badge` | `n` - a numbered step marker | 0..1 lit |
| `wire` | `d` - ISA dashed signal line | - |
| `text` | `text style(h, cap, tick, sl) anchor near fixed`; `\n` breaks lines; it may shift up to `near` (28) to stay clear. With **`to: [x, y]`** it is a CALLOUT: words for that place, joined to it by a leader line, placed clear by the layout | - |
| `log` | `w rows label empty` - alarm list, newest first | - |

Parts added from courses (merged by `kit_parts.py promote`; each block's `example` is its card in `GALLERY.html`):

| type | options | value |
|---|---|---|
| `ga` | `w h view(side/plan) draft water house:{x,w,h} funnel:{x,w,h} frames label` - a ship's hull; named spaces are `space` parts on it | 0..1 picked out |
| `zone` | `zone(0/1/2)` and `w h rx` or `r`, `from:[x,y]` - a hazardous-zone overlay | 0..1 grown from `from` |
| `scale` | `h w min max every unit reach limits:[{at,label,side}] markers:[{label,note,at}]` - a vertical scale; `orient:"h"` with `len` runs it across, each marker on a stem at its `rise`, words to its `side` (left/right) | 0..n: marker k slides (vertical) or drops (across) into place from k to k+1 |
| `bands` | `w rowH chip axis rows:[{label,tone(z0/z1/z2),caption,gas:[[from,to]]}]` - time bands with a clock | 0..n: row k sweeps from k to k+1 |
| `cylinder` | `w h labels` - a dual-fuel engine cylinder, injectors at 0.22 w and 0.78 w | 0 stopped · 1 gas mode · 1.5 gas supply stopped · 2 fuel-oil mode |
| `boil_off` | `w h insulation level liquidLabel vapourLabel heatLabel` - an insulated LNG tank cutaway | 0..1 heat in, boiling |
| `gas_cloud` | `w h from:[x,y]` - a pale cloud growing in a space | 0..1 how much gas |
| `integral_tank` | `w h cofferdam label cofferdamLabel hullLabel` - a hull tank in its cofferdam | liquid level 0..1 |
| `pipe_section` · `relief_valve` · `step_track` · `coupling` · `drip_tray` · `water_curtain` · `detector` · `flame` | from IGF M03 (2.45.0): a cut along a double-walled pipe; a spring relief valve; numbered steps or a checklist (`boxes`); dry-disconnect / breakaway coupling; drip tray; water curtain; fixed gas detector head (marks); a flame at a point | see each part's `value` in `kit.js` |
| `curve_chart` | from IGF M04: `xaxis yaxis curves:[{label,pts}] hline point` - curves that draw themselves, a point that slides along one | 0..n curves, n..n+1 the point |

Pre-built for IGF Basic modules 5-15 (2.45.0, from the architecture's media plans; each in `GALLERY.html`, tested on both panels):

| type | options | value |
|---|---|---|
| `fan` | `label dir(right/left/up/down)` - ventilation fan in a duct or opening | 0 stopped … 1 running |
| `spray` | `nozzle(monitor/hand/sprinkler) agent(powder/water/foam) angle reach reachLabel` | 0..1 how much is discharged |
| `gas_cylinder` | `w h gas label` - N2 / CO2 / breathing-air bottle | 0..1 how full |
| `push_button` | `label tag` - ESD mushroom button with a guard | 0 ready, 1 pressed (trip red) |
| `person` | `wear:[helmet,visor,gloves,suit,boots,scba] scale label` - a worker pictogram | 0..n PPE item k appears |
| `sensor` | `kind(catalytic/infrared) oxygen` - how a gas sensor sees gas | 0..1 gas in the sensor |
| `static_charge` | `bonded labels` - charge on an isolated part, the spark | 0..1 charge, 1..1.2 spark |
| `fire` | `kind(pool/jet) w height length angle label` | 0 out … 1 full |
| `flammability` | `zone:[[fuel %, O2 %]] path:[[..]]` and axes - the flammability diagram | 0..1 along the path; the zone lights while inside |
| `range_bar` | `w lel uel max label` - lean / flammable / rich | the concentration % |
| `hose` | `d empty label` - a flexible bunkering hose | flow 0..1; **`<id>.fill`** like a pipe's |
| `manifold` | `outlets:[{label}]` - a bunker manifold header | 0..n outlets connected |
| `spool_piece` | `w t spool lift left right spoolLabel label` - segregation | 1 fitted, 0 removed + blanks |
| `tank_wall` | `w layers:[{label,kind,h}] insideLabel outsideLabel` - a cryogenic tank's wall layers | 0..n layer k picked out |
| `spill` | `w surface(deck/water) label` | 0..1 spread; boils from 0.5 |
| `wind` | `w rows gap dir max unit label` | 0..1 strength |
| `tree` | `root children:[{label, children}]` - an organisation or reporting chart | 0..n box k lit |

## Marks - the heart of it
```json
{"at": 98, "label": "shut-off", "kind": "trip", "dir": "up", "stop": true,
 "alarm": "HIGH LEVEL SHUT-OFF · bunkering valve closed", "then": [["V1", 0, 700]]}
```
- `kind`: `alarm` (amber), `trip` (red) or `limit` (grey). Marks are quiet until they are crossed.
- `dir`: `up` (default) fires when the value rises through `at`, and `down` when it falls through it.
- `alarm`: text for the alarm log and the status chip. Leave it out to light the mark only.
- `stop`: the value holds at the mark (a shut-off).
- `then`: moves to start the moment the mark is crossed.
- When a value passes several marks, they fire in the order the value meets them, whatever order
  they are listed in. That is why the order of events can't be wrong.

## Steps
```json
{"title": "1 · Bunkering: the level rises", "reset": true, "set": {"F1": 1},
 "play": [["L1", 100, 5200, 300, "linear"]]}
```
- `play` items are `[partId, to, ms, delay, ease]`, where ease is `inout` (default), `linear` or `out`.
- `reset` returns everything to its starting value and clears the alarms. Use it for independent scenarios.
- `set` jumps values without crossing marks (for example, flow on at the start of the step).
- `line` (a number or a list) lights the slide's own text line for that step: `.cur` on this step's line,
  `.lit` on the lines of the steps before it. In a compiled deck the lines are numbered `data-i` in script order.
- Moves on one part queue up: a later move takes over when its own delay runs out.
- Step *n* always starts from the end of step *n-1*. **Previous** jumps back to that state, and
  **Replay** plays the step again. With reduced motion every step jumps to its end state.

## The seven families
Each family is a set of parts. A figure may mix families. When a module needs a part that doesn't
exist yet, the part is added to its family here, never drawn once on a slide.

| # | Family | Parts | Status | Courses it serves (IGF Basic) |
|---|---|---|---|---|
| 1 | Instruments | panel, level, gauge (+ repeater), readout, well, log, detector, push_button | **built** | M02 s14, s15, q11 · M01 s07 · M03 · M09 · M14 |
| 2 | Piping and flow | pipe (liquid/gas/air, double-walled, fill and drain), valve, tank, space, exchanger, pump, engine, vent, badge, wire, relief_valve, coupling, drip_tray, water_curtain, integral_tank, hose, manifold, spool_piece | **built** | M02 · M03 · M07 · M13 · M14 · M15 |
| 3 | Ship and spaces | ga (side view, deck plan), zone overlay; named spaces are `space` | **built** | M01 s04, s09 · M02 s12 · M07 · M11 |
| 4 | Cutaways | boil_off, pipe_section, sensor, tank_wall; tank types A/B/C still planned | **built** | M01 s07 · M03 · M07 · M09 |
| 5 | Gas, fire and machinery | gas_cloud, cylinder, flame, fire (pool, jet), spray, fan, gas_cylinder, static_charge, spill, wind | **built** | M01 · M02 · M03 · M05 · M06 · M10 · M11 · M13 · M15 |
| 6 | Charts | scale, bands, curve_chart, flammability, range_bar; composition bar still planned | **built** | M01 s02 · M02 s11 · M04 · M06 · M07 |
| 7 | Procedures | step_track (steps, checklist), tree, person; flowchart, cause-and-effect matrix still planned | **started** | M03 · M05 · M10 · M11 · M14 · M15 |

**Task mode (2.43.0, built).** The same spec drawn on a trainee task page, so a slide and the task built from it
("the GA from slide 4, no labels") can never drift apart: `<svg data-kit="#spec" data-kit-step="3">` is drawn still at
the end of step 3 (`"final"` or empty = the last), without step buttons, and - being still - opens full screen like a
picture. The compiler (`compile/task_pages.py`) writes it from a build-sheet figure `*.kit.json`; the sheet's
`"kit_step"` picks the step, `"unlabel"` takes the words off the parts (`label`, `caption`, `title`, `tag` ...; a `text`
part goes), and the tappable areas are the parts' own ids - `gb_answer.js` lays each one on the drawn part's box. A
spec's optional `"view": [x, y, w, h]` shows another window on the canvas (the task page adds a band above and below
for its empty label boxes); a deck never sets it.

## Fill the frame, and the words do the explaining (L53, operator 2026-10-15)
- **Draw to the panel.** `size` has the shape of the panel the figure is shown in (the wide column of a `two-col`
  slide: about 640 × 390, a dark slide 680 × 415), and the drawing covers it: `audit_drawing.js` EMPTY allows at most
  half of the panel blank and no blank piece over a fifth, judged at the last step too. A whole ship for five spaces,
  one pipe with three valves, a small scale in a big panel - crop to what the steps show, spread the parts, add the
  context the slide's lines name (the master valve before the gas valve unit, the engine-room boundary).
- **The words stay beside the figure at reading size.** A figure whose steps light the slide's lines goes in a `two-col`
  slide (`compile/GUIDE.md`), never above a row of small legend cards.
- **A lit line is a button.** Every line a step lights (or the box a line heads) becomes a tap target: tap it or press
  Enter and that step plays (`.kit-tap`, 44 px). The first step that lights a line owns it.

## Rules of the look (ISA-101)
Grey and blue at rest. Colour appears only for something abnormal: amber for an alarm, red for a trip.
Colours come only from the `course-module-ui` tokens, named by their dark-panel names (the light panel remaps them).
No word is drawn under 12.5 px on screen - the kit sees to it (above).

## A task page's "label the drawing" boxes (2.45.0)
`compile/scripts/label_layout.py` sizes and places them: one width for all the boxes of a question - what the longest
label needs on two lines with its tick - in the band above the drawing for the places in its upper half and below for
the rest, each as close to its place as the others allow, in the same order, 1 % apart and from the edges. A build
sheet no longer gives `"labels": {"...": {"box": [...]}}` (it still may, and that box wins); `"at"` still names the place.
