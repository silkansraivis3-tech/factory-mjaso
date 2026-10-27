# Figure kit - the spec format

Writing a spec? Read CATALOGUE.md first (one line per part) - this file is the full reference.

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

**Try it first in the figure studio (2.48.0)** - one spec, its real slide, every step, both screen sizes, every drawing
audit and a screenshot, in seconds, without compiling the module:
```
python scripts/studio.py <course>/working_claude/figures/M03/s07.kit.json        (on its real slide, from the build sheet)
python scripts/studio.py <spec>.kit.json --parts <kit_parts.js> --panel two-col|dark|wide-left|task|WxH
```
`--step N` photographs one step; **`--step all`** draws the rest state and the end of every step as one contact sheet
(panels as wide as the real slide's) in a single browser run, instead of one run per step (2.49.1).
It judges 1280 x 800 (the tablet) and states 1024 x 768: the scale the figure is shown at, how much the kit grew the
words for the 12.5 px floor, how many labels it moved, any it could not place, and every audit finding per step.

## What the kit does by itself (2.48.0) - nothing of this goes in a build sheet
- **Labels.** Every name, caption and state a part draws gets a place clear of every shape, line and other label, and
  of its own box's edge (4 px, L54), judged at the end of every step - beside its part, or further out with a leader
  line. A spec places a part; it never places its words. A label that finds no clear place stays where the part put it
  and is reported (the studio, the browser console).
- **The 12.5 px floor.** Shown smaller than 1:1, every type size grows by 1/scale (at most 2x) and the layout makes room
  for it: boxes, rings and rows grow with their words. A figure whose words then need more room than its panel gives
  stops growing at 1.3x its width and the drawing audit's SMALL TEXT reports it - give it more room or fewer words.
- **Boxes sized to their words.** A readout, a gauge or level readout, the alarm chip, an alarm row: as wide as the widest
  thing it can show. An alarm too long for its log goes on as many lines as it needs.
- **The frame.** A drawing that reaches past its frame makes the frame larger (taller only, when its column has the
  height); one lost in its frame is zoomed in to fill it (L53, at most 1.5x; never with `view`, an inset photo over it,
  or `"fit": false`). A photo laid over a drawing (the build sheet's inset `over`) is not zoomed, so the drawing is shown
  below 1:1 and its words grow with it (2.49.2: the kit also lays out on a window `resize`, which a probe that measures a
  slide the moment it is shown relies on, and grows words 0.1 % past the floor so a rounded 12.4999 never reads as small).
- **Both panels.** On a light ground (a light page - a task page draws a kit figure on the dark screen, 2.46.0) the figure takes the light mapping of the course tokens (kit.css
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
| `level` | `w h label unit min max ticks readout decimals marks` - the tick numbers stand left of the column; a `pipe` that runs into that strip (a feed line) puts them on the right instead (2.49.2); `ticks`: `"right"`, `"left"` or `false` says it | the level |
| `gauge` | `r label unit min max start sweep normal:[lo,hi] ticks every numbers readout decimals caption captionAt marks` - `ticks` is how many divisions min..max has (default 10), `every` makes each Nth one a long tick with its number (default 2); the numbers are whole, so choose them so each numbered step is a whole unit - (max - min) x every / ticks of 1 or more (0-2 bar with 10 ticks printed 0 0 1 1 2); `numbers: false` and the `readout` alone when the dial is small (2.66.0) | the reading |
| gauge repeater | `source:"P1" mini:true` - copies the scale of P1 and follows it | - |
| `readout` | `w h label unit sign decimals marks` - digital tile | the reading |
| `well` | `w h tag` - bilge well, dripping leak, TT sensor | pool 0..1 |
| `valve` | `size label labelAt(right) rotate state(false) actuator(false) trip(false)` - a real valve (cast body, flanges, bonnet; a diaphragm actuator, or a handwheel with `actuator: false`) with the ISA bow-tie as its plate, filled when closed; red when shut unless `trip: false` | 1 open, 0 closed |
| `pipe` | `d` (SVG path) `fluid`(liquid/gas/air - air: a ventilation duct) `double` `drain` - its contents and their movement | flow 0 still … 1; **`<id>.fill`** 0..1 the front advancing, 1..2 emptying towards `drain` |
| `tank` | `w h label burst` - horizontal type C tank. `burst: true` (or `{r, label}`: the fireball's radius and name) adds the value **`<id>.burst`** 0..1: the shell cracks (0..0.25) and the contents ignite in a fireball (leave `r` of room round the tank) | liquid level 0..1 |
| `space` | `w h label labelAt(below) style(room/enclosure) crosses` - a room (dashed) or an enclosure (solid). `crosses: true` for a box laid over a tank's end or a hull line on purpose (not judged as poking out of it). A name that does not fit inside the grown type goes under the room by itself | 0..1 picked out |
| `exchanger` | `r label` - a shell-and-tube heat exchanger (vaporizer, heater), its copper coil showing the heating | 0..1 heating |
| `pump` | `r label` - a centrifugal pump: cast volute on its foot, the impeller turning in its eye | 0 stopped, 1 running |
| `engine` | `w h cylinders label` - dual-fuel engine block. RUNNING / STOPPED stands under the pistons' whole stroke, and the block grows taller and wider to hold the word at its grown size (2.50.6) | 0 stopped, 1 running |
| `vent` | `label labelAt(left)` `mast` - vent outlet to the open air. On top of a pipe's upright run it is a vent mast: its tap area on a task is the whole run, not the outlet (2.49.7); `mast: false` keeps the outlet alone, `mast: <length>` gives the run when no pipe draws it, `mast: true` asks for a mast (60 long when no pipe draws it). With no pipe under the outlet, `true` or a length is drawn as an upright pipe - never an outlet floating in the air (2.50.4); any other value is refused. Its puffs rise only into free air: up to 34, stopping short of anything drawn above the outlet (2.50.7) - give the outlet about 57 units of air above it for the full rise | 0..1 venting |
| `badge` | `n` - a numbered step marker | 0..1 lit |
| `wire` | `d` - ISA dashed signal line | - |
| `text` | `text style(h, cap, tick, sl) anchor near fixed reveal`; `\n` breaks lines; it may shift up to `near` (28) to stay clear. With **`to: [x, y]`** it is a CALLOUT: words for that place, joined to it by a leader line, placed clear by the layout. **`reveal: true`** (or a `value`) makes the words - and a callout's dot and leader - a thing a step brings in: not drawn at rest, `["T", 1, 400]` fades them in, so a predict-then-reveal slide does not print its answer | 0..1 opacity (with `reveal`/`value`) |
| `log` | `w rows label empty` - alarm list, newest first. A long alarm (every mark's `alarm` text in the spec) is set on as many lines as it needs to fit the log's width (2.49.2; it was two at most), every row as tall as the most lines; the log never grows wider than `w` | - |

Parts added from courses (merged by `kit_parts.py promote`; each block's `example` is its card in `GALLERY.html`):

| type | options | value |
|---|---|---|
| `ga` | `w h view(side/plan) draft water house:{x,w,h} funnel:{x,w,h} frames label` - a ship's hull; named spaces are `space` parts on it | 0..1 picked out |
| `zone` | `zone(0/1/2)` and `w h rx` or `r`, `from:[x,y]` - a hazardous-zone overlay | 0..1 grown from `from` |
| `scale` | `h w min max every unit reach limits:[{at,label,side}] markers:[{label,note,at,drag}]` - 2.66.0: a marker with `drag: true` the trainee moves along the scale (finger, mouse, arrow keys), its word reading the value live (`decimals`, `step`); the next step puts it back. a vertical scale; `orient:"h"` with `len` runs it across, each marker on a stem at its `rise`, words to its `side` (left/right). A marker's word and note, and a limit's name, are labels the layout places and the audit judges; the tick numbers keep clear of the bar as the type grows (2.49.1) | 0..n: marker k slides (vertical) or drops (across) into place from k to k+1 |
| `bands` | `w rowH chip axis rows:[{label,tone(z0/z1/z2),caption,gas:[[from,to]]}]` - time bands with a clock | 0..n: row k sweeps from k to k+1 |
| `cylinder` | `w h labels` - a dual-fuel engine cylinder, injectors at 0.22 w and 0.78 w | 0 stopped · 1 gas mode · 1.5 gas supply stopped · 2 fuel-oil mode |
| `boil_off` | `w h insulation level liquidLabel vapourLabel heatLabel` - an insulated LNG tank cutaway | 0..1 heat in, boiling |
| `gas_cloud` | `w h from:[x,y] fromIn drift:[dx,dy]` - a pale cloud growing in a space. `from` is where it grows from: **figure coordinates, like every other part** (2.49.2) - or, as specs before 2.49.2 wrote it, in the cloud's own box. `fromIn: "figure"` / `"box"` says which; left out, a point inside the box is read in the box (an old spec draws as it did) and a point only inside it as figure coordinates (x - the cloud's x, y - its y) is read as figure coordinates. A point that lies inside the box both ways is read in the box - add `"fromIn": "figure"` to mean the other. `check_kit.py` warns when the origin lands off the figure. `drift` (or `true`: 0.4 w to the right) adds the value **`<id>.drift`** 0..1: the whole cloud moves that far and spreads a little - wind carrying a leak away; it crosses walls by design | 0..1 how much gas |
| `integral_tank` | `w h cofferdam label cofferdamLabel hullLabel` - a hull tank in its cofferdam | liquid level 0..1 |
| `pipe_section` · `relief_valve` · `step_track` · `coupling` · `drip_tray` · `water_curtain` · `detector` · `flame` | from IGF M03 (2.48.0): a cut along a double-walled pipe; a spring relief valve; numbered steps or a checklist (`boxes`); dry-disconnect / breakaway coupling; drip tray; water curtain; fixed gas detector head (marks); a flame at a point | see each part's `value` in `kit.js` |
| `curve_chart` | from IGF M04: `xaxis yaxis curves:[{label,pts}] hline point` - curves that draw themselves, a point that slides along one. 2.66.0: `yaxis.log: true` - a log scale over decades (min > 0; `yaxis.ticks` to choose the numbers); `point.drag: true` - the trainee drags the point along the x axis (finger, mouse, arrow keys) and reads it live, the next step puts it back; `point.curve: "all"` - a line across the chart reads every curve drawn so far, each value beside its own dot ("pick a cargo, drag to 45 °C"); `point.decimals` | 0..n curves, n..n+1 the point |
| `molecule` | 2.66.0: `formula w h build label bond atoms bonds` - a structural formula: `formula` names a cargo (methane, ethane, propane, butane, ethylene, propylene, butadiene, VCM / vinyl chloride, ammonia, nitrogen, CO2, water - or C3H8, C2H4 ...) or give `atoms: [[el, x, y]]` and `bonds: [[i, j, order]]` in bond lengths; in a box (`w h`) it grows to fill it, centred; its name and formula under it | `build: true`: 0..1 the skeleton, 1..2 the hydrogens; else whole |

Pre-built for IGF Basic modules 5-15 (2.48.0, from the architecture's media plans; each in `GALLERY.html`, tested on both panels):

| type | options | value |
|---|---|---|
| `fan` | `label dir(right/left/up/down)` - ventilation fan in a duct or opening | 0 stopped … 1 running |
| `spray` | `nozzle(monitor/hand/sprinkler) agent(powder/water/foam) angle reach reachLabel` | 0..1 how much is discharged |
| `gas_cylinder` | `w h gas label bar kg liquid reading code` - `x y` is the middle of its BASE: the bottle stands up from y (2.66.0); the reading (number over its unit, on the plate) shows when the steps change the bottle, or with `reading: true`; N2 / CO2 / breathing-air bottle, opaque, one paint. `code: true` paints the shoulder in its EN 1089-3 code and names it in the caption (N2 black, CO2 grey, AIR black and white quarters) - only where the lesson teaches the code: EN 1089-3 does not cover fixed extinguishing-system cylinders. A compressed gas (N2, AIR) has a pressure gauge on its valve and its reading in bar on its plate (`bar`: full pressure, 200, or 300 for AIR). CO2 is a liquid: no gauge (its pressure stays at its vapour pressure, ~57 bar at 20 °C, until it is nearly empty) - its plate reads its weight in kg (`kg`: full, 45; CO2 is checked by weighing) and its liquid shows in a cut-away window with a "liquid" tag under it, inside the bottle (`liquid: false` leaves it out; `liquidLabel` renames it) | 0..1 how full |
| `push_button` | `label tag h` - ESD mushroom button with a guard. `h`: the wall plate's height, 120 units (2.49.2; it was a fixed 182 - two did not stack in a 390-high figure); the words under it keep their size | 0 ready, 1 pressed (trip red) |
| `person` | `wear:[helmet,visor,goggles,respirator,gloves,suit,apron,boots,scba] scale label labels` - a worker pictogram. `labels` (or `names`): `{item: words}` or a list in the order of `wear` names an item in the slide's own words, `{"visor": "GOGGLES", "scba": "BREATHING APPARATUS"}`; `false` names none (2.49.2) | 0..n PPE item k appears |
| `sensor` | `kind(catalytic/infrared) oxygen` - how a gas sensor sees gas | 0..1 gas in the sensor |
| `static_charge` | `bonded labels` - charge on an isolated part, the spark | 0..1 charge, 1..1.2 spark |
| `fire` | `kind(pool/jet) w height length angle label stub` - a jet is drawn on a 90 px pipe end; `stub: false` leaves it out when the figure has the real pipe | 0 out … 1 full |
| `flammability` | `lfl ufl nose:[O2 %, fuel %]` (methane 5 / 15 / [12, 6] by default) or `zone:[[O2 %, fuel %]]`, `path:[[O2 %, fuel %] or null]`, `lines`, `notes`, `segClass`, `by:'legs'` - the standard (ISGOTT / SIGTTO) flammability composition diagram: oxygen across, fuel up, the air line, the zone, the line of critical dilution with air (2.63.2; an old spec with fuel across is read into it) | 0..1 along the path, or legs done with `by:'legs'`; the zone lights while inside |
| `range_bar` | `w lel uel max label nums` - lean / flammable / rich. Numbers under the bar: both limits and the ends - an end is left out when a limit is within 8 % of the axis from it (a lower limit of 4-6 % would sit on the "0"); `nums: [..]` names them outright | the concentration % |
| `lamp` | `label ex` - a light fitting on its cable: electrical equipment, an ignition source in a gas-dangerous space; `ex: true` draws the heavy explosion-protected enclosure | 0 off, 1 lit |
| `spark` | `kind(electric/friction) to:[dx,dy] label` - an arc jumping from this point to `to` (the two contacts stay drawn), or hot particles thrown from this point (a tool or a chain on steel) | 0..1 the spark |
| `composition_bar` | `w h segments:[{label,pct}] total unit label` - one bar split into the shares of its components (methane, ethane, nitrogen ...) | 0..n: segment k fills from its left edge from k to k+1, its name and share appear once it is half drawn |
| `hose` | `d empty label` - a flexible bunkering hose | flow 0..1; **`<id>.fill`** like a pipe's |
| `manifold` | `outlets:[{label}]` - a bunker manifold header | 0..n outlets connected |
| `spool_piece` | `w t spool lift left right spoolLabel label` - segregation | 1 fitted, 0 removed + blanks |
| `airlock` | `w h door side (or safeW hazardW: 0 draws no side) safe hazard label state words` - 2.63.2: two gas-tight steel doors in two bulkheads with the space between them, the SAFE side (green) and the HAZARDOUS side (the zone's amber) named; `state: false` leaves out the words "BOTH DOORS SHUT" / "ONE DOOR OPEN" | 0 both doors shut, 1 the safe-side door open, 2 the hazardous-side door open; from 1 to 2 the first door shuts before the second opens - two doors never open at once |
| `hatch` | `w lift label state words` - 2.63.2: the bolted hatch in the open deck over a tank connection space: a steel cover bolted on its coaming | 0 bolted shut, 1 the cover lifted clear, the opening showing |
| `tank_wall` | `w layers:[{label,kind,h}] insideLabel outsideLabel` - a cryogenic tank's wall layers | 0..n layer k picked out |
| `spill` | `w h surface(deck/water) label from reach` - drawn inside its box x..x+w, y..y+h (2.49.2): the nozzle's top at `y`; `h` is 206 (deck) / 240 (water) with a one-line `label`, a shorter `h` shortens the nozzle; the wave is cut at `w` and `reach` is held to the room either side of `from` (it was drawn from y+26 to y+254, and 10 past `w`) | 0..1 spread; boils from 0.5 |
| `wind` | `w rows gap dir max unit label` | 0..1 strength |
| `tree` | `root children:[{label, children}] w minW` - an organisation or reporting chart. It is laid out to fit `w` (default: the figure's width less its x and 10) and never wider: tighter padding and gaps, then words broken at a space, so its words keep the 12.5 px floor (2.49.2) | 0..n box k lit |

## Relations - place a part by what it stands on (2.72.0)
A part is placed by WHAT IT STANDS ON OR JOINS, not by a guessed y (IGF 2.71.0: a vent mast at y 184 under the deck line,
inside the hull; pipes ending in the air; a "Bunkering station" of words only). kit.js resolves these before it draws
(`KIT.relate`); `check_kit.py` judges the result (`kit_relate.py` runs the same code under node). A spec with no relation
draws exactly as before; a relation wins over the part's own x / y / d.

| key | on | means |
|---|---|---|
| `"on": "G.deck"` | any part | stand on that anchor: the part's foot on the line (a vent mast's foot, a manifold's lowest flange, a tank's saddles, a hatch's coaming); a part that hangs (a water curtain, a detector, a lamp) hangs from it. A vent `on` a deck with no `mast` gets one that clears the accommodation; a water curtain on a ship's deck runs down to the waterline. `"gap"`: that far off the line |
| `"in": "Hold"` | any part | stand on the floor of a space or of the ship's hold; `"side": "left"/"right"` against that wall |
| `"at": 0.7` / `312` / `"K.top"` | with `on` / `in` | across: a fraction of the host's length, a figure x, or another part's port |
| `"at": "P1@0.4"` | a valve, a coupling ... | ON that pipe, 0.4 of its length along, turned with it |
| `"from": "T.top", "to": "V.inlet"` | pipe, hose, wire | routed between two ports (right-angled; a hose hangs in a curve, `"sag"`); `"via": [[x, y], "R.outlet"]` its bends, `"level"` the height (or x) of its middle run, `"route": "hv"/"vh"/"hvh"/"vhv"`. A point `[x, y]` at the figure's edge is a line that runs on off the picture |
| `"for": "B"` | text | a callout to that part (or `"B.outlet"`, or a pipe's middle): its leader ends on it |
| `"around": "V.outlet", "r": 40` | zone | a round zone centred on that port (a zone's `x, y` is the top left of its box, not its middle); `"around": "B", "pad": 8` a box round the part |
| `"from": "V.outlet"` | gas_cloud | grows from that port - gas leaving the vent, a leak at a flange |
| `"aim": "W"` | spray | pointed at that part, reaching it |

**Anchors.** A side-view ship (`ga`): `deck`, `bottom`/`keel`, `floor` (the hold's floor), `waterline`, `side`; plan view:
`port`, `starboard`, `side`; `"cut": true` draws a straight piece of the ship's side (deck edge, plating, sea) for a close-up
- something to stand on and hang from. Every part: `top`, `bottom`, `left`, `right`, `center` (and `top@0.3`: 0.3 along that
edge); and its own ports - tank `top`/`vapour`/`liquid` (a dome is drawn under every pipe that leaves its top), vent
`inlet` (the mast's foot) / `outlet`, valve and coupling `in`/`out`, relief_valve `inlet`/`outlet`, pump and exchanger
`inlet`/`outlet`, engine `inlet`, cylinder `gas`/`oil`, manifold `out1`..`outN`, gas_cylinder `valve`, space
`floor`/`ceiling`, water_curtain `header`. `kit_relate.py --geometry <spec>` prints every part's box and ports.

## What a figure must MEAN (2.72.0) - BLOCKs and NOTEs
Every check before 2.72.0 was about the look. `scripts/kit_meaning.py` (its words and IGF must-be-true lists in
`course-visuals/knowledge/figure-truths.json`) now judges what a figure means, at two levels (Aleksis: "if even a minuscule
detail is off it flags it and there isn't any flexibility"):
- **BLOCK** - a build FAIL (`check_kit.py spec`), only for a clear physical error: a thing the figure's words name drawn
  nowhere (no part, no kin part beside the words - a box on deck may stand for the bunkering station, a pipe for a hose);
  a vent mast, manifold or hatch inside the hull, a tank half through the deck; a pipe end far from every part, away from
  the frame and with no words at it saying where it goes; a spray or curtain far from everything; a step that says the
  gas vents with none leaving (a mark's `then` counts); a row of captions naming fuels or equipment over nothing; an
  engine-mode caption over no engine.
- **NOTE** - everything else (a label a little far, a near miss, a zone off its source, a must-be-true sentence): the
  FIGURE review's reviewer judges it in context and calls it BROKEN only if a seafarer would.
- **A waiver**: `"meaning_ok": {"<KIND> <part id>": "<why it is right>"}` in the spec accepts one finding on purpose (the
  key is printed with every finding, e.g. `LOOSE END P1`); the build lists it, the reviewer reads the reason and may still
  call it BROKEN. A waiver with no reason is itself a BLOCK; one naming no finding is a NOTE.
Calibrated on the instructor-reviewed IGF original (96 specs): 4 BLOCKs (one a real error, a water curtain hanging from
nothing); the 2.71.0 build's eight wrong figures all still BLOCK. The kinds:
**NAMED** words on the figure, a part's label or a step title name a thing that is not drawn (a "Bunkering station" with no
manifold, coupling or hose), or not there; **LOOSE END** a pipe or hose end on nothing (`"open": "start"|"end"|"both"` says a
line is open to the air on purpose); **INSIDE** a vent mast, manifold or hatch inside the hull, a tank half through the deck;
**NO GAS** a vent the words say vents - or a relief valve that lifts - with no step letting gas out of its outlet; **AIM** a
spray aimed at nothing, a water curtain or detector attached to nothing, a round zone centred on nothing; **LEADER** a
callout's leader on nothing, words floating far from anything drawn, a ship labelled "ship"; **GRID** a row of captions
with drawings under only some of them (six fuel names over one tank); **SMALL** a small drawing lost in a big `panel`
part (the figure's own frame is the drawing audit's EMPTY); **TRUTH** the figure kind's own list (ship plan, bunkering line, vent system, fuel supply, engine modes,
fuel types); (2.72.3) **STEP** (a NOTE) a step's title names a part the step does not change (a tank, room or pipe named
is where the step is, not judged), or the step only turns things off under a title saying something happens; **LABEL** a
callout's leader ends on a part of another kind than its words name - a cofferdam's leader in its space's middle, on the
tank inside (a BLOCK: none in the original's 96 specs; point it at the part's edge, `"for": "CD.top@0.1"`) - or its words
name a thing not drawn (a NOTE). Calibrated as 2.72.0 was: STEP raises 2 notes on the original (both accepted by its
instructors, so never a BLOCK), LABEL none. A fit `figure_fit.py` makes is refused when it breaks one.

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

## Patterns - a spec to start from (2.63.2; the figure library, 2.72.0)
`patterns/*.kit.json` are whole specs that were drawn, judged and fixed once, to copy and change - not a new part and not
a template the compiler fills. Each passes `check_kit.py spec` (its meaning too) and is clean in the studio at 1280 x 800
(`scripts/test_patterns.py`), and was judged at projector size by a reviewer who did not draw it.

**Start from a pattern when one fits** - `compile_module.py --init-build` does it unasked: a slide whose title and lines name
one of these gets the pattern as its starter, marked `"_pattern"` (keep the arrangement and its relations, rename the words to
the script's, map the steps to the slide's lines). Made from the hand-fixed IGF Basic figures, with what those got wrong put
right (a bunkering station drawn, the vent line joined, the gas seen leaving):

| pattern | shows |
|---|---|
| `ship_ga` | side view: engine room aft with the dual-fuel engine, fuel preparation room with the vaporizer, the tank in its fuel storage hold with the TCS on it, the bunkering station (manifold over its drip tray) on the open deck with the bunker line down to the tank, the vent mast on the deck - its line from the tank, its outlet above the accommodation, gas leaving it |
| `bunkering_line` | ship-to-ship, along the ships: bunker vessel valve, breakaway coupling, hose, dry-disconnect coupling, manifold and ESD valves, drip tray under them, water curtain down the ship's side; connect, transfer, leak, ESD, break away |
| `vent_system` | type C tank on deck, readout of its pressure, relief valve on its top, vent line up the mast, gas out of the outlet into its zone |
| `fuel_supply` | tank, tank valve in the TCS, vaporizer and heater in the FPR, master gas fuel valve outside the engine room, gas valve unit, double-walled pipe, engine; a gas trip |
| `engine_modes` | one dual-fuel cylinder: gas mode (pilot oil, the gas burning), gas trip, fuel-oil mode, the modes listed beside it |
| `fuel_types` | every IGF fuel on one temperature scale, how each is kept on board |
| `fuel_space_access` | (below) |

**`patterns/fuel_space_access.kit.json` - "Getting into the fuel spaces"** (IGF Basic M02 s10; the instructors' review
called the hand-drawn slide a bad diagram: pastel boxes, a bunkering station drawn as a cart, pale tiny labels, everything
greyed out on the last step). A ship section: the hull and its open deck (`ga`, no sea), and in it
- the **safe area** and the **airlock** (one `airlock`: `safeW` names and tints the safe side, no hazardous side - the
  fuel preparation room beside it is that side), the doors played 1 then 2 so the trainee sees the one shut before the other opens;
- the **fuel preparation room** (`space`) with its **own access** from the open deck (a narrow `space` enclosure that
  crosses the deck: `crosses: true`);
- the **fuel storage hold** with the **type C tank** (`tank`) and the **tank connection space** (`space`) on top of it, and the
  **bolted hatch** (`hatch`) in the deck over it - the hatch lifts when the step enters through it;
- the **bunkering station**: a `manifold` at the ship's side on the open deck, its `drip_tray` under the flange;
- **one colour for every hazardous space**: a `zone` (zone 1, the kit's hazardous-zone amber) laid over each of the fuel
  preparation room, the hold and the bunkering station - never a colour of the slide's own - and green only for the safe side.

Its steps light one access route each: 1 the airlock (doors 1, then 2, the fuel preparation room's zone grows), 2 its own
access, 3 the hatch to the tank connection space, 4 the bunkering station - each step puts the route before it back to
quiet (`play` to 0) - and **the last step shows every hazardous space at full strength** (every zone and the picked-out
spaces at 1). `check_kit.py` refuses a last step that leaves every picked-out part dimmed (`space`, `zone`, `ga` under
0.5 after steps that picked them out one at a time).
Copy it, move the rooms to the ship's own plan, keep the label count (10) and the room each name needs: a room too small
for its name at the grown type (1024 x 768) sends the name outside with a leader line.

## The seven families
Each family is a set of parts. A figure may mix families. When a module needs a part that doesn't
exist yet, the part is added to its family here, never drawn once on a slide.

| # | Family | Parts | Status | Courses it serves (IGF Basic) |
|---|---|---|---|---|
| 1 | Instruments | panel, level, gauge (+ repeater), readout, well, log, detector, push_button | **built** | M02 s14, s15, q11 · M01 s07 · M03 · M09 · M14 |
| 2 | Piping and flow | pipe (liquid/gas/air, double-walled, fill and drain), valve, tank, space, exchanger, pump, engine, vent, badge, wire, relief_valve, coupling, drip_tray, water_curtain, integral_tank, hose, manifold, spool_piece | **built** | M02 · M03 · M07 · M13 · M14 · M15 |
| 3 | Ship and spaces | ga (side view, deck plan), zone overlay, airlock, hatch; named spaces are `space` | **built** | M01 s04, s09 · M02 s12 · M07 · M11 |
| 4 | Cutaways | boil_off, pipe_section, sensor, tank_wall; tank types A/B/C still planned | **built** | M01 s07 · M03 · M07 · M09 |
| 5 | Gas, fire and machinery | gas_cloud (grows, drifts), cylinder, flame, fire (pool, jet), spray, fan, gas_cylinder, static_charge, spill, wind, lamp, spark; a tank that ruptures (tank `burst`) | **built** | M01 · M02 · M03 · M05 · M06 · M10 · M11 · M13 · M15 |
| 6 | Charts | scale, bands, curve_chart, flammability, range_bar, composition_bar | **built** | M01 s02 · M02 s11 · M04 · M06 · M07 |
| 7 | Procedures | step_track (steps, checklist), tree, person; flowchart, cause-and-effect matrix still planned | **started** | M03 · M05 · M10 · M11 · M14 · M15 |

**Task mode (2.43.0, built).** The same spec drawn on a trainee task page, so a slide and the task built from it
("the GA from slide 4, no labels") can never drift apart: `<svg data-kit="#spec" data-kit-step="3">` is drawn still at
the end of step 3 (`"final"` or empty = the last), without step buttons, and - being still - opens full screen like a
picture. The compiler (`compile/task_pages.py`) writes it from a build-sheet figure `*.kit.json`; the sheet's
`"kit_step"` picks the step, `"unlabel"` takes the words off the parts (`label`, `caption`, `title`, `tag` ...; a `text`
part goes) - for `"answers"` or a list by the spec's `"ghost": [part ids]` (2.50.4): those parts' labels (a `text` part
whole) are laid out like any other and hidden after every layout, so the words left stand where the deck has them - and the tappable areas are the parts' own ids - `gb_answer.js` lays each one on the drawn part's box. A
spec's optional `"view": [x, y, w, h]` shows another window on the canvas (the task page adds a band above and below
for its empty label boxes); a deck never sets it.

## Fill the frame, and the words do the explaining (L53, operator 2026-10-15)
- **Draw to the panel.** `size` has the shape of the panel the figure is shown in, at the width it shows at (a slide's
  figure column: about 416 × 254 - 2.66.0: the templates' column shows a drawing 456 px wide at 1280 × 800 and 345 px at
  1024 × 768, so a 640-wide spec showed at half size there and its words collided), and the drawing covers it: `audit_drawing.js` EMPTY allows at most
  half of the panel blank and no blank piece over a fifth. A figure that steps is judged at its busiest step (a rest state is
sparse by design), each step by what it shows - a part still to come is not counted (2.49.7) - and the finding names
that step; a pipe counts by its bounding box, so the space inside its bends is not blank; and the finding says where the
largest blank piece is (side and pixels). A whole ship for five spaces,
  one pipe with three valves, a small scale in a big panel - crop to what the steps show, spread the parts, add the
  context the slide's lines name (the master valve before the gas valve unit, the engine-room boundary).
- **The words stay beside the figure at reading size.** A figure whose steps light the slide's lines goes in a `two-col`
  slide (`compile/GUIDE.md`), never above a row of small legend cards.
- **A lit line is a button.** Every line a step lights (or the box a line heads) becomes a tap target: tap it or press
  Enter and that step plays (`.kit-tap`, 44 px). The first step that lights a line owns it.

## Rules of the look (L63, 2.52.0)
**Physical equipment looks like the real equipment; a screen looks like a screen.** The kit does it in every deck by
itself - a spec has no option for it and a slide never asks for it.
- **Equipment** - a tank, a pipe, a valve, a pump, an exchanger, an engine, a vent, a hose, a coupling, a manifold, a
  bottle, a lamp, a ship, a worker - is drawn the way a trainee sees it on board: **in its material** (aluminium
  cladding, brushed stainless, cast or painted metal, rubber, a ship's painted plating, workwear), **with light and
  shade** (a second copy of each body's shape: a cylinder, a box lit from above, a round), a soft shadow, and **its real
  features**: bolted flanges at every pipe joint and wherever a pipe meets equipment, a tank's saddles, straps and dome,
  an exchanger's shell-and-tube body with flanged heads (its copper coil still shows the heating), an engine's bedplate,
  bolted covers and turbocharger, a ship's plating, sheer stripe, rail, boot-top, white superstructure with its windows
  and funnel band, a worker's real PPE.
- **Valves are drawn as what they are**: a cast body bolted in by its end flanges, a bonnet, and on top a yoke and a
  pneumatic diaphragm actuator on an automatic valve (the default) or a stem and handwheel on a manual one
  (`"actuator": false`). The ISA bow-tie stays on the body as a light plate - outline when open, filled when closed, red
  only when it shut on a trip (`"trip": false`: grey). No taller than the old symbol: a room's name keeps its place.
- **Screens stay a calm ISA-101 HMI** - panel, level, gauge, readout, alarm log, badge: grey and blue at rest; colour
  appears only for something abnormal, amber for an alarm, red for a trip. **Diagrams stay diagrams** (a zone, a chart, a
  cloud, a scale).
- **The teaching state reads at a glance** on either: a fluid's front, open or shut, running, an alarm. The materials
  are neutral greys and blues (copper only for a heating coil); a fire and a burning spray have a flame's own colours.
  Amber and red stay reserved for alarm and trip.
- Colours come only from tokens: the `course-module-ui` tokens, named by their dark-panel names, and the kit's own
  material tokens (`kit.css` `--mat-*`). The textures are drawn once per page (`kit.js` `materials()`); a light page has
  its own set and `.kit-light` points at it. No word is drawn under 12.5 px on screen - the kit sees to it (above). A
  room's name keeps a halo of the panel's colour, so it reads on a white superstructure or a painted hull, and one that
  finds no clear place inside its room (filled with equipment) goes beside it.
- The drawing check judges one piece of equipment as one object (`data-kit-body`): a valve's flange is not "poking out"
  of its own body, but the valve is, out of the room it stands in.

## A task page's "label the drawing" boxes (2.48.0)
`compile/scripts/label_layout.py` sizes and places them: one width for all the boxes of a question - what the longest
label needs on two lines with its tick - in the band above the drawing for the places in its upper half and below for
the rest, each as close to its place as the others allow, in the same order, 1 % apart and from the edges. A build
sheet no longer gives `"labels": {"...": {"box": [...]}}` (it still may, and that box wins); `"at"` still names the place.
