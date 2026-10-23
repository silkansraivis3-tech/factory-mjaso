# 3D kit - the parts, and how to add one

Every part takes `id`, `type`, `at` [x, y, z] (metres), `rot` (degrees round the vertical), `scale`, `flip` ("x" a
mirror image), `name`, `pick`, `mat` (a palette name) or `color`. The same `id` on several entries is ONE part built
of all of them (a space with its pipes and valves). Sub-parts get the id `<id>_<sub>` unless the spec names them:
`"subs": {"inner": "inner"}`. States are `<id>.<state>`, numbers 0..1.

**Palette** (`mat`): steel, steel_mid, steel_dark, steel_black, flange, pipe, hull, deck, side, floor, floor_dark,
wall, frame, trim, shell, tank, ring, saddle, insulation, barrier, membrane, stainless, gas (yellow natural gas),
cold (pale blue insulated LNG line), vapour, red, amber, yellow, green, rubber, engine, engine_dark, cover,
foundation, cabinet, panel, screen, accommodation, window, skin, overall, helmet, lng, glass.
Tints (hull spaces, panels): amber, green, blue, grey, red, violet - or any `#hex`.

## Primitives

| type | at | settings |
|---|---|---|
| `box` | centre | `size` [w, h, d], `opacity` |
| `cylinder` | centre | `r`, `len`, `axis` x / y / z, `open` |
| `sphere` | centre | `r` |

## Structures

| type | at | settings | made from |
|---|---|---|---|
| `hull` | its own origin: x as given, y = 0 bottom shell, z = 0 centre line | `x` [from, to], `half` (half breadth), `bottom`, `floor` (top of the double bottom), `top` (main deck); `spaces` [{`id`, `x` [a, b], `tint`, `floor`, `wall`}] - each a sub-part; `bulkheads` [{`x`, `hole` [y, r], `opacity`}] (default: one at every space boundary); `near` / `far` / `ends` wall opacities; `ribs` (spacing); `bottom_id`, `side_id` (the double bottom / the far side as sub-parts) | M01, M02 |
| `deck_plate` | deck top at the ship's side; z = 0 is the side, inboard -z | `size` [along, inboard], `thick`, `side` (depth of side plating, 3.2), `seams`, `rail` | M03, M07 |
| `room` | floor centre | `size` [w, h, d], `open` "front" / "front+right" ..., `roof`, `glass` ["right", "roof" ...], `frames` (spacing 0.6), `hole` [x0, z0, x1, z1] (a bilge well's opening) | M04, M05, M09 |
| `enclosure` | floor centre | `size`, `wall` (0.25), `floor`, `keep_frame` (its light outline stays when open); state **open** fades the walls away | M02 TCS |
| `panel` | centre | `size` [w, h] in the x-y plane, `tint`, `opacity` | |
| `accommodation` | base centre | `size` [w, h, d], `decks` (window rows) | M15 |

## Tanks

| type | at | settings | made from |
|---|---|---|---|
| `tank_c` | axis centre, axis along x | `r`, `len` (cylindrical part), `head` (end depth, r/2), `rings` [x] or a count, `ring_t` (band thickness), `saddles` [x], `saddle_w`, `base` (floor y, local), `cut` (front half away), `fill` (0..1 of the diameter; sub-part **liquid**), `insulation` (thickness, seen at the cut), `dome`, `liquid_color` | M01, M02, M07 |
| `tank_sphere` | centre | `r`, `base`, `cut`, `fill` (sub-part **liquid**), `insulation`, `dome` | Moss |
| `tank_prism` | centre, length along x | `size` [L, H, B], `chamfer`, `kind` "membrane" / "type_b" / "type_a" or `layers` [{`id`, `name`, `t`, `mat`}] from the inner hull inwards (each with an id is a sub-part), `hull` (inner hull plate 0.2), `cut` "end" (default: the section shows every layer) / "front" / false, `fill` (sub-part **liquid**) | containment |

## Piping

| type | at | settings | made from |
|---|---|---|---|
| `pipe` | the path's origin | `path` [[x, y, z] ...], `r` (0.15), `mat` pipe / gas / cold / steel, `flanges` "ends" or [point index], `bands` (ID band spacing), `end_cone` (a cone at the last point: it goes on) | all |
| `pipe_dw` | the pipe's middle, along x | `len`, `r_in`, `r_out`, `collars` [x], `spacers` [x], `supports` [x] with `base` (y), `glands` [x]; sub-parts **inner**, **annulus**, **outer**; state **cut** slices the outer pipe open (closed, a tap on a sub-part is the whole pipe) | M01, M05, M09 |
| `valve` | on the pipe axis | `axis` x / z, `wheel` red / grey, `actuator` (a remote-operated valve), `scale`; state **shut** turns a grey wheel (or the actuator) red; `kind` "relief" - inlet below, outlet to the side, its bonnet lifts by `lift` (0.16) with state **open** | M01-M03, M06, M15 |
| `flange` | on the pipe axis | `r` (the pipe's), `axis`, `bolts` (8) | M03, M04 |
| `coupling` | on the pipe axis | `kind` "dry" / "breakaway", `r` (0.11), `axis` z / x | M03 |
| `hose` | the path's origin | `path`, `r` (0.13) | M03 |
| `vent_mast` | its foot | `h`, `r`, `stays` | M07, M15 |

## Equipment

| type | at | settings | made from |
|---|---|---|---|
| `vessel` | axis centre, along x | `r`, `len`, `base` (floor y) | M01 vaporiser |
| `cabinet` | base centre, door to +z | `size` [w, h, d], `band`, `screen` | M01 GVU |
| `engine` | foundation underside, centre | `n` cylinders, `exhaust` (height), `gas_rail`; turbocharger at +x (`flip` "x" for the other end) | M01, M05, M09 |
| `pump` | base centre | `r` | |
| `drip_tray` | base centre | `size` [w, d], `wall` | M03 |
| `esd_button` | its foot, facing +z | `h` | M03 |
| `detector` | where it is fixed | `face` down / up; state **alarm** (0.5 amber, 1 red) | M09 |
| `person` | between the feet, facing +z | `h`, `wear` | scale |
| `air_intake` | centre, louvres to +z | `size` | M15 |

## Measures and effects

| type | at | settings | made from |
|---|---|---|---|
| `dimension` | origin of `a` and `b` | `a`, `b`, `tick` [half a tick], `text` (its value, a tag by itself), `ox`, `oy`, `color`, `white`, `r` | M02, M15 |
| `limit_box` | origin of `min` / `max` | `min`, `max`, `planes` {"z-": 0.07, "y-": 0.16}, `color`, `dash` | M02 |
| `zone` | centre | `level` 0 / 1 / 2, `shape` sphere / capsule / box, `r`, `half`, `axis`, `size`, `floor` (world y it stops at); state **on** (1) | M07, M15 |
| `gas` | the leak (or outlet) | `kind` rise / sink / spread / plume, `to` (height it rises to / falls to), `area` [x0, z0, x1, z1], `fuel` natural_gas (yellow, default) / cold_methane / propane / methanol / ammonia / hydrogen / vented (the hand-made M04 colours) or `color`, `n`, `dur`, `opacity`, `size` (a plume's: times larger), `wind` (plume), `delay` (seconds after on), `until` (fades away then) - two clouds in turn tell a fuel's story (cold methane sinks, then rises); state **on** plays it | M04, M05, M09, M15 |
| `arrow` | origin of `a` / `b` | `a`, `b`, `r`, `color`; state **on** | M15 wind |
| `flow` | the path's origin | `path`, `color`, `spacing`, `speed`, `r`; state **on** | M06 |

## Adding a part (L55, as the 2D kit)

The kit has no part for what the module needs? Make it a kit part from the first line - never a hand-written scene.

1. In the module's `assets/kit3d_parts.js` (loaded after kit3d.js):
   ```js
   KIT3D.define('reliquefaction_skid', function (k, p) {
     var m = k.mat(p.mat || 'steel');                 // the palette, a part's own copy (it can glow alone)
     k.box(2, 1.2, 1, m, 0, 0.6, 0);                  // box / cyl / ball / ring / seg / cone / run / tube / many / lines
     k.anchor('label', [0, 1.2, 0]);                  // where its label's dot goes
   }, {"family": "equipment", "at": "base centre", "about": "a reliquefaction skid"});
   ```
   The builder `k`: `mat(name | {color, rough, metal}, {opacity, double, clip, emissive})`, `basic(hex, opacity)`,
   `box`, `cyl(axis, r, len, mat, x, y, z, {open, seg, r2})`, `ball`, `ring(axis, R, r ...)`, `seg(a, b, r, mat)`,
   `cone(tip, dir, r, h, mat)`, `run(points, r, mat)`, `tube(points, r, mat)`, `many(geometry, mat, [positions])`,
   `lines(points, hex, {dash})`, `push(at, rot)` / `pop()`, `clip(normal, constant)` (a cut, `.set(c)` moves it),
   `state(name, v0, fn)`, `sub(id)` (a sub-part), `anchor(name, at)`, `label({text, at, tag})`, `anim(name, fn(t, on))`.
   Only the palette's colours; true sizes in metres; static pieces are merged by the kit, so a piece that moves or
   fades gets `{keep: true}`.
2. `python -I course-visuals/kit3d/scripts/check_kit3d.py spec <file> --parts <module>/assets/kit3d_parts.js`.
3. Once the module is complete, the part moves into `kit3d.js` (add it to the catalogue block too) and the operator
   is asked for the merge.
