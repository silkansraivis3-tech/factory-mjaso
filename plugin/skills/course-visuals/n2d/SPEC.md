# n2d - the 2D figure spec (`*.n2d.json`)

The 2D kit for new courses. A figure is written as **words and data only**: the things in it, how they connect, and
what happens at each step. It never has positions, sizes, rates, delays or state names. The figure lays itself out in
whatever box it gets (the projector, the tablet, full screen), with type sized for the back of the room, and the deck's
Next walks its steps. Open `demos.html` to see every form and scene step by step. `scripts/test_n2d.py` walks them all.

Courses already built keep today's 2D kit (`../kit2d/`); their `.kit2d.json` figures build as before.

## Who decides what

1. **Code picks the figure** from the slide's own words (`scripts/figure_plan.py`, run by `--init-build`). The result
   is one of the five forms below, a named scene, a real photo, the task screen, or no figure. The build sheet's `"_brief"`
   says which one and why. A starter `sNN.n2d.json` is written with one step a line and `"_todo"` naming what to fill in.
2. **The writer fills in** the starter: the things, their names, and what each step does. Delete `"_todo"` when done.
3. **The check refuses** what a form cannot hold (`scripts/n2d_check.py`, run by the compile). It gives the reason, for
   example "8 things; a path holds at most 7". Change the words: nothing is ever shrunk to fit.

A real photograph comes first wherever a camera can show the thing (L52). A figure is for what a camera cannot show:
what flows, what fails, what a wall stops, a change measured over time, a procedure's order.

## The rules every figure keeps

- `"say"`: the one point the figure makes, in one sentence. It is the screen reader's text and the walk review's
  purpose.
- **Things are pictures, never boxes.** `"is"` names a thing from the library (`things.json`, drawn by `n2d-things.js`):
  sensor, controller, screen, pc, laptop, server, switch, router, firewall, wifi, vsat, satellite, constellation, mast,
  office, globe, malware, engine, gnss, gyro, radar, ais, ecdis, conning, socket, person, manager, sponsor, attendant,
  permit, padlock, fan, detector, manhole, document, change, plan, calendar, check, tester, cable, pump, valve, tank,
  ship, barometer, wind. Everyday words work too ("gas detector", "project manager"). **A thing the library lacks is
  added to it**: draw it once in `n2d-things.js` and name it in `things.json`, and every course can then use it.
- **Short words.** A name is at most 3 words. A tag is at most 4. An action (`steps`) is at most 4. The picture
  carries the rest.
- **Steps:** 1 to 7. Step 1 is what the slide shows on arrival. Each step names the slide's `"line"` it goes with (a
  number, or a list), and the deck lights that line. `"tag": {thing: "words"}` puts an amber note on a thing for that
  step only. Tags place themselves clear of the things and their names.
- Colour: `"tone"` on a thing, zone or option (blue, teal, violet, orange, rose, slate, green, red, navy). Leave it
  out and the kit picks. Amber always means "now".

## The forms

### path - real things in order, something travelling between them

```json
{"form": "path", "say": "An engine reading travels from the sensor to the office ashore.",
 "things": [{"id": "s", "is": "sensor", "name": "Oil temp sensor"}, {"id": "c", "is": "controller", "name": "Local controller"},
            {"id": "a", "is": "screen", "name": "Alarm system"}, {"id": "f", "is": "firewall", "name": "Firewall"},
            {"id": "o", "is": "office", "name": "Office ashore"}],
 "links": ["s>c>a>f>o"],
 "steps": [{"line": 1, "go": "s>c"}, {"line": 2, "go": "c>a", "tag": {"a": "Screens and alarms"}}, {"line": 4, "go": "a>f>o"}]}
```

- 2 to 7 things. `"links"`: chains `"a>b>c"`, with a word on a link as `"d>p:Yes"`. A thing `"is": "decision"` is a
  diamond, and `"hidden": true` keeps a thing out of sight until a step `"add"`s it.
- Per step: `"go"` sends something along a chain (or a list of chains) and the links light up. `"fail"`: a thing stops,
  and code marks everything it feeds. `"cut"`: a link breaks, and code marks every thing that can no longer reach the
  end. `"wrong"`: a link that should not exist, drawn red. `"bug"`: malware travels a chain and marks what it reaches.
  `"mark"` rings a thing. `"clear": true` starts a new story on the same drawing.
- Layout: things in columns by their order; a long chain folds into two rows; a link that skips a column is routed
  clear of the thing between.

### zones - places kept apart, the things in them, what a wall stops

```json
{"form": "zones", "hull": true, "wall": "Firewall", "say": "Walls between the networks keep malware out of the engine control.",
 "zones": [{"id": "ot", "name": "OT", "tone": "orange", "things": [{"is": "engine", "name": "Main engine"}]},
           {"id": "it", "name": "Office IT", "tone": "blue", "things": [{"is": "pc", "name": "Office PC"}]},
           {"id": "crew", "name": "Crew Wi-Fi", "tone": "violet", "things": [{"is": "laptop", "name": "Crew laptop"}]}],
 "steps": [{"line": 1}, {"line": 1, "bug": "crew"}, {"line": 2, "walls": true}, {"line": 3, "bug": "crew"}]}
```

- 2 to 4 zones, up to 3 things each. `"hull": true` draws them as a ship's compartments, and `"wall"` names the
  bulkheads.
- Per step: `"walls": true / false` raises or lowers them. `"bug": zone` starts malware there: with the walls down it
  spreads to every zone, with them up it stays and the wall says "Stopped". `"mark"` rings a zone. Without walls,
  zones are named groups with real examples in them, for example IT, OT and IoT.

### steps - a procedure, one action at a time

```json
{"form": "steps", "tone": "teal", "say": "Nobody enters before the permit, isolation, ventilation, an air test and an attendant.",
 "steps": [{"line": 1, "is": "permit", "do": "Permit signed"}, {"line": 2, "is": "padlock", "do": "Isolate the space"},
           {"line": 3, "is": "detector", "do": "Test the air", "read": "O₂ 21 %"}, {"line": 4, "is": "attendant", "do": "Attendant at the entrance"}]}
```

- 2 to 7 actions. Each step is one action: a large picture, the action in 4 words or less, and a reading when there
  is one (up to 14 characters). A rail shows every action, with the done ones ticked.

### options - two or three choices, rated and raced

```json
{"form": "options", "say": "Far from land only satellites reach; a low orbit answers faster.",
 "options": [{"is": "satellite", "name": "GEO satellite"}, {"is": "constellation", "name": "LEO satellites"}, {"is": "mast", "name": "Mobile mast"}],
 "qualities": [{"name": "Reach", "values": [3, 3, 1], "words": ["Wide", "Wide", "Near coast"]},
               {"name": "Delay", "values": [3, 1, 1], "low": true, "words": ["Longer", "Shorter", "Short"]}],
 "steps": [{"line": 1, "show": 1}, {"line": 2, "show": 2, "race": 1}, {"line": 3, "show": 2, "pick": 2, "tag": {"2": "Only near land"}}]}
```

- 2 or 3 options and 1 to 3 qualities. A value is 0 to 3, taken from the slide's own words. `"low": true` means less is
  better. The pips always show "better", with a note under the quality's name.
- Per step: `"show": k` shows the first k qualities. `"race": k` races the options on quality k. `"pick": i` rings
  option i, and `"tag"` uses option numbers from 0.

### amounts - measured numbers, the change measured by code

```json
{"form": "amounts", "say": "The faster the pressure falls in three hours, the stronger the wind to expect.",
 "x": {"name": "Time", "unit": "h"}, "y": {"name": "Pressure", "unit": "hPa"},
 "series": [{"name": "Pressure", "pts": [[0, 1013], [3, 1012], [6, 1009], [9, 1003], [12, 997]]}],
 "scale": {"name": "Fall in 3 hours", "bands": [{"to": 1.5, "name": "Slowly"}, {"to": 3.5, "name": "Falling"}, {"to": 6, "name": "Quickly"}, {"to": 99, "name": "Very rapidly"}]},
 "steps": [{"line": 1, "upto": 3}, {"line": 2, "upto": 9, "span": [6, 9]}, {"line": 3, "upto": 12, "span": [9, 12], "tag": "Expect strong wind"}]}
```

- 1 to 3 series of 2 to 24 measured points from the course's sources (never made up). `"limit": {"value", "name"}`
  draws a limit line.
- Per step: `"upto": x` draws the line on to x, with the value read out large. `"span": [x1, x2]` measures the change
  and writes it, for example "−6 hPa in 3 h", and the `"scale"` (up to 5 bands) points at where it falls.
  `"tag"` adds a few words.

## The scenes - one real system with named slots

- **`pump_line`**: two tanks and the line between them, cut open. Set `"from"` and `"to"` to `{"name", "level"}`, and
  `"parts"` to a list from `filter`, `pump`, `gauge` and `valve`. `"names"` can rename parts, for example
  `{"valve": "Discharge valve"}`, and `"liquid": "water"` makes it water. Per step: `"pump": "on" / "off"` and
  `"valve": "open" / "shut"`. Code works out the flow, the pressure on the gauge and the tank levels. A `"tag"` keyed by
  part (pump, gauge, valve) hangs from the top.
- **`crossing`**: two power-driven vessels crossing (COLREG). Set `"own"` and `"other"` to `{"name"}`. Per step,
  `"show"` is `"start"`, `"bearing"` (the steady bearing as parallel lines), `"lights"` (the sidelights, give way and
  stand on) or `"alter"` (own ship alters to starboard and passes astern).

A slide whose subject needs a scene the kit lacks gets a new scene, made once in `n2d.js` with a card in `demos.html`,
the same way a thing is added to the library.

## A module's systems, drawn once

A module that shows the same system on several slides draws it once, in `working_claude\figures\MNN\worlds.n2d.json`:

```json
{"bridge": {"things": [{"id": "gnss", "is": "gnss", "name": "GNSS"}, {"id": "gy", "is": "gyro", "name": "Gyro compass"},
                       {"id": "rd", "is": "radar", "name": "Radar / ARPA"}, {"id": "ec", "is": "ecdis", "name": "ECDIS"}],
            "links": ["gnss>rd", "gnss>ec", "gy>rd", "gy>ec"]}}
```

A slide then names it and says only what happens: `{"form": "path", "world": "bridge", "say": "...",
"steps": [{"line": 2, "fail": "gy"}]}`. It may add its own `"things"` and `"links"`. The bridge looks the same on every
slide, so the trainee learns it once. Two slides drawing the same system is not a repeat: it is the point.

## Where it goes

The build sheet names the spec as the slide's figure, `"s14": {"figure": "s14.n2d.json"}`, with the file in
`working_claude\figures\MNN\`. The compile joins in the world, runs the check, and writes
`<div class="fill fig n2d-fig lt-light"><div class="n2d-stage" data-n2d="#n2-s14"></div><script type="application/json" id="n2-s14">...`,
then ships `n2d.css`, `n2d-things.js` and `n2d.js`. In the deck, Next and Back walk the steps. A true / false or
scenario slide walks the drawing before its answer. The fit gate runs `N2D.audit` at every step: no words over words,
none cut at the edge.

Alone: `N2D.mount(element, spec)` returns the figure, with `go(n)`, `next()`, `prev()` and `idle()`.
