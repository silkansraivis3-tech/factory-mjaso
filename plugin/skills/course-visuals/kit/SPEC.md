# Figure kit - the spec format

A figure is a JSON spec: **parts** placed on a canvas, and **steps** that move their values.
`kit.js` draws the parts and runs the steps, and `kit.css` gives the look. Nothing is drawn by hand.
`GALLERY.html` shows every part moving, plus slide M02 s14 rebuilt from a spec.

**In a course (L51)** the spec is a figure file: `working_claude/figures/M02/s14.kit.json`, named in the build
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

## Top level
| key | meaning |
|---|---|
| `size` | `[w, h]` viewBox |
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
| `pipe` | `d` (SVG path) `fluid`(liquid/gas) `double` `drain` - its contents and their movement | flow 0 still … 1; **`<id>.fill`** 0..1 the front advancing, 1..2 emptying towards `drain` |
| `tank` | `w h label` - horizontal type C tank | liquid level 0..1 |
| `space` | `w h label labelAt(below) style(room/enclosure)` - a room (dashed) or an enclosure (solid) | 0..1 picked out |
| `exchanger` | `r label` - P&ID heat exchanger (vaporizer, heater) | 0..1 heating |
| `pump` | `r label` - P&ID centrifugal pump | 0 stopped, 1 running |
| `engine` | `w h cylinders label` - dual-fuel engine block | 0 stopped, 1 running |
| `vent` | `label labelAt(left)` - vent outlet to the open air | 0..1 venting |
| `badge` | `n` - a numbered step marker | 0..1 lit |
| `wire` | `d` - ISA dashed signal line | - |
| `text` | `text style(h, cap, tick) anchor`; `\n` breaks lines | - |
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
| 1 | Instruments | panel, level, gauge (+ repeater), readout, well, log | **built** | M02 s14, s15, q11 · M01 s07 · M09 |
| 2 | Piping and flow | pipe (liquid/gas, double-walled, fill and drain), valve, tank, space, exchanger, pump, engine, vent, badge, wire | **built** | M02 s03, s04, s05, m01, m04 · M03 · M07 · M14 · M15 |
| 3 | Ship and spaces | ga (side view, deck plan), zone overlay - from IGF M01/M02; named spaces are `space` | **started** | M01 s04, s09 · M02 s12 · M07 · M11 |
| 4 | Cutaways | boil_off (from IGF M01); tank types A/B/C, insulation layers still planned | **started** | M01 s07 · M02 s07 · M03 |
| 5 | Gas, fire and machinery | gas_cloud, cylinder (from IGF M01/M02); pool fire, jet fire, spray still planned | **started** | M02 s15 · M01 s06 · M06 · M13 |
| 6 | Charts | scale, bands (from IGF M01/M02); curve with a moving point, range bar, composition bar still planned | **started** | M01 s02 · M02 s11 · M04 · M06 · M07 |
| 7 | Procedures | step track, flowchart, cause-and-effect matrix, checklist | planned | M05 · M11 · M14 · M15 |

Planned for every family: **task mode** - the same spec with labels hidden and parts tappable, so a
slide and the task built from it ("the GA from slide 4, no labels") can never drift apart.

## Fill the frame, and the words do the explaining (L49, operator 2026-10-15)
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
Colours come only from the `course-module-ui` tokens. Labels are 12.5 px or larger in viewBox units.
