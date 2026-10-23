# 3D kit - the scene spec (`*.kit3d.json`)

The 3D kit (`kit3d.js`, `kit3d.css`, on the factory's three.js r128) draws a 3D scene from a short JSON spec, the
way the figure kit (`../kit/`) draws a 2D figure. It is made from the best of the nine hand-made 3D scenes of the IGF
course (M01 hull, M02 tank, M03 bunker station, M04 leak, M05 spaces, M06 trapped liquid, M07 zones, M09 detection,
M15 venting). A builder never writes three.js for a slide again: they write the parts, the labels and the steps.

PARTS.md lists every part and its settings; `check_kit3d.py` checks a spec; `studio3d.html?spec=<file>` shows one.

## What the kit does by itself - nothing of this goes in a spec

- **The look** of the hand-made scenes: ACES tone mapping, a soft studio light (a procedural environment), one sun
  shadow drawn once, the course palette (`steel`, `gas` yellow, `cold` pale blue, `red` handwheels ...), see-through
  ghost walls, cut-aways that show the insides with the cut edge drawn.
- **Framing that fills the box**: the whole scene (or the spec's `box`) is fitted to the canvas at every size - room
  kept above for the labels and below for the controls. A step's `frame` fits its parts; a tapped part is framed
  from its own box. Full screen re-fits.
- **Labels on the parts**: an amber dot on the part, a white stem, a white pill with a blue border. They never cover
  each other, a stem, a dot, a control, the Full screen button or the box edge: every frame each label that touches
  something tries other stem lengths, the other side of its point and a sideways shift (the hand-made
  `settleLabels`, IGF slide review 2026-10-22). A label behind the camera or off the picture hides.
- **A tap on a part** (not a drag): it glows blue, its pill lights, the camera frames it; a second tap, or a tap
  beside the parts, puts the step's view back. 12 px tolerance; see-through and cut-away pieces let the tap through.
- **A label is a button for its part** (`data-3d-part`, registered with `GB3D.wire` - 2.63.2): a tap, Enter or
  Space does what a tap on the part does. Outside a deck the kit makes it a button itself.
- **Full screen**: the deck's button (gb_deck.js 2.63.2); outside a deck the kit's own. The scene follows its box.
- **Steps walked by the deck's Next / Back** (the GB_HOOKS `step` hook): each step's camera, highlight and states
  tween together (750 ms); a step's `line` lights the slide's own line, and that line is a way to the step.
- **Built ahead** on the slide before (window.__noPrepare honoured), its shaders compiled off screen; draws only
  when something moves; pixel ratio at most 2; static meshes merged per part and material; `window.__scene3d` for
  `perf3d.mjs` / `smoke3d.py`.
- **The poster fallback**: an element `[data-poster]` in the stage (a 2D drawing or a picture of the model) shows
  until the first frame, and stays if there is no WebGL or the scene fails. Without one, the kit says "The 3D view is
  not available on this device."
- prefers-reduced-motion: no tweens, the end of each move at once. Context loss is survived.

## Where it goes

In a compiled deck the build sheet's figure is the spec itself: `"figure": "s05.kit3d.json"`. The compiler writes

```html
<div class="fill fig kit3d-fig" data-3d-box>
  <div class="kit3d-stage" data-stage data-3d data-kit3d="#k3-s05">[the poster, if the sheet names one]</div>
  <script type="application/json" id="k3-s05">{ ...the spec... }</script>
</div>
```

and ships `three.min.js`, `kit3d.js`, `kit3d.css` with the module. Alone (a test, a gallery):
`KIT3D.mount(element, spec)` returns the scene's api: `select(part)`, `step(n)`, `next()`, `prev()`,
`state(name, value)`, `control(i)`, `info()`, `snapshot()`, `dispose()`.

## Top level

| key | what |
|---|---|
| `label` | what the scene shows, for a screen reader (required) |
| `units` | `"m"` - one unit is a metre; draw things their true size (a valve may be drawn larger: `scale`) |
| `view` | the home view: `{"az": 24, "el": 23}` - degrees round the vertical (0 = from +z, 90 = from +x) and above the horizon; `fill` 0.94 |
| `box` | `[x0,y0,z0,x1,y1,z1]` - what the home view frames (default: every part) |
| `parts` | the parts (below) |
| `labels` | the labels (below) |
| `groups` | `{"leak": ["dd", "ba", "sv", "rv"]}` - one key that lights several parts (a control, a label or a step selects it) |
| `states` | starting values: `{"pipe.cut": 0}` |
| `steps` | what Next walks (below) |
| `controls` | buttons in the scene's corner (below) |
| `reset` | `true` (or the words) - a "Reset view" button |
| `captions` | `[{"text": "Warm natural gas: rises to the deckhead", "when": "warm.on"}]` - one line top left, the first whose state holds |
| `controls_at` | `"right"` - the buttons in a column on the right (many controls: the picture keeps its height) |
| `labels_button` | the "Labels" on / off button every labelled scene gets (the instructor asks the class to name the parts; a tapped part still shows its name); `false` leaves it out, a string renames it |
| `frame` | `{"top": 56}` - px kept free above the model for the labels |
| `pill_max` | the widest a label's pill grows before its words wrap (190 px) |
| `fov`, `exposure`, `sun` | camera field of view (32), tone-mapping exposure (1.05), sun direction `[0.45, 0.75, 0.5]` |
| `min_el`, `max_el`, `min_zoom`, `max_zoom`, `pick_fill` | limits of the presenter's turning (2 / 82 degrees, 0.06 / 1.5) and how much of the box a tapped part fills (0.62) |
| `shadows`, `merge`, `fullscreen` | `false` turns that off |

## Parts - all take `id`, `type`, `at`, `rot`, `name`, `pick`

```json
{"id": "tank", "type": "tank_c", "at": [-12.25, 4.9, 0], "r": 3.4, "len": 14.5, "cut": true, "fill": 0.62}
```

- `at` - where the part stands, in metres (what point that is - a centre, a base - PARTS.md says per part);
  `rot` - degrees round the vertical; `scale` - drawn larger than true (say so in the slide's notes).
- `id` - a part with an id can be tapped, framed, lit and labelled; without one it is scenery.
  `"pick": false` keeps an id'd part from being tapped (a hull frame).
- `mat` / `color` - another palette name or colour than the part's own.
- Some parts make **sub-parts** (a double-walled pipe's `inner`, `annulus`, `outer`; a hull's spaces): each has its
  own id (PARTS.md), is tapped and labelled alone, and selecting the parent lights them all.
- Some parts have **states** (`"<id>.cut"`, `"<id>.open"`, `"<id>.on"`, `"<id>.alarm"`): numbers 0..1 that steps and
  controls set; the kit tweens them. **Every** part has `"<id>.ghost"`: its steel turns see-through (what is inside a
  tank or a pipe, shown without cutting it).

## Labels

```json
{"part": "tank", "text": "Fuel tank", "at": [-12.5, 8.3, 0], "up": 56}
```

| key | what |
|---|---|
| `part` | the part it names - the pill becomes that part's button (data-3d-part) |
| `text` | the words - the script's own words for the part |
| `at` | the point the dot sits on (default: the part's own label point, else the top of its box) |
| `up` | stem length in px, negative = the pill hangs below (48); the kit moves it when it would touch something |
| `side` | 1 hangs the pill to the right of its stem, -1 to the left (a cluster of labels round one valve); or `dx` in px |
| `up_steps` | another stem on some steps: `{"1": -40}` |
| `when` | shown only in a state: `"pipe.cut > 0.5"`, `"!tcs.open"` |
| `steps` | shown only on these steps `[0, 1]` |
| `tap_only` | shown only while its part is selected |
| `small`, `tone` | a small dark pill (bow / stern, "LNG liquid"); `"amber"`, `"red"`, `"green"` border (a lamp that is / is not allowed) |
| `tag` | a value tag with no stem (a dimension's "B/5 = 6 m"); `ox`, `oy` its offset |

A part can make its own labels (a dimension's value, a hull space's `name`).

## Steps

```json
"steps": [
  {"view": {"az": 24, "el": 23}},
  {"view": {"az": 17, "el": 17, "frame": ["pipe"]}, "state": {"pipe.cut": 1}, "select": "pipe", "line": 2}
]
```

Step 0 is what the slide opens with. Each step may set `view` (`az`, `el`, `frame` [parts], `zoom`, `target`),
`state` (kept by the later steps unless they change it), `select` (a part or group lit), `labels` (only these
parts' labels), `line` (the slide line `data-i` it lights; that line is then a way to the step). The deck's Next
walks the steps before it turns the slide; Back walks them back.

## Controls

```json
"controls": [{"text": "Cut the pipe open", "text_on": "Close the pipe again", "state": {"pipe.cut": 1},
              "view": {"az": 17, "el": 17, "frame": ["pipe"]}},
             {"text": "Stop a leak", "select": "leak"},
             {"text": "Step 2", "step": 1}]
```

A `state` control is a toggle (pressed while its states hold; again puts the step's states and the view back - or
its `"off"` values, `{"z0.on": 0}`, when the step itself turned it on);
`select` lights a part or group like a tap; `step` goes to a step. Use controls for what the presenter does by
choice; use steps for what the lesson walks through in order. 56 px buttons, bottom right; labels keep off them.

## Rules of the look (L63 for 3D)

- True proportions; draw a small part larger only with `scale` and say so in the notes.
- One meaning per colour: `gas` yellow natural gas, `cold` pale blue insulated LNG lines, `red` handwheels and
  shutdown, amber only on the label dots, the limits and zone 1, blue only for the selection.
- The inside is the lesson: `cut` it open, ghost the near wall, never hide what the words name.
- Every part a label names can be tapped; every label names a part (or a group) - no chips row under the scene.
- 3 to 9 labels on a step; more is a second step.
