# The bar for a tablet task

Owner, 2026-10-15: *"it should be no bugs when trainee do these tasks, and it should be more realistic, and more
beautiful for eyes, intuitive and interactive ... with all these schemes and control panels it should be realistic,
so after completing this they actually will be able to navigate through all those processes when they face it in
real life."* Ship screens: the factory's **dark modern look, with the simulator's symbols, tags, colours and panels**
(owner's choice the same day).

A task is finished only when all four parts below hold **and** `node tools/task-test/run.js <NN>` passes on the
tablet and the phone.

## 1 · Real - the trainee could do it on board tomorrow

- **The ship's own screens use `gb_hmi.js`** - never a drawing of a screen. It carries the training simulator's
  conventions (Wärtsilä LCHS TechSim LPG Tanker, Trainee Manual §4.2, §6.4, §6.9): tags under every object
  (`PL0126`, `PV0129`, `P0107`, `T0107`, `PM-0001`, `HVK-0101`), pipe colour by what flows (liquid blue, vapour purple,
  condensate teal, nitrogen grey, sea water green), remote valves locked until hydraulic pressure is released (HVK),
  a tap opens the object's own panel (OPEN / CLOSE; SHUT −10 +10 OPEN for a regulating valve), valves take time to
  move, readouts as value over tag with AL / AH lamps, pump lamps READY / RUNNING / TRIP, ESD opens EMERGENCY STOP,
  alarms flash and sound until ACK.
- **Procedures are the real ones.** Line-ups, sequences and limits come from the knowledge base
  (`Desktop\docling\gas_basic\GAS Basic\knowledge_base`, searched with `_claude_working_area\kb_audit\kb_search.py
  --no-toc`), first the simulator manual for anything the trainee will do on the simulator, then IGC Code, SIGTTO,
  ICS. Every figure and step carries its source in an HTML comment (`<!-- 15.8.2 step 10 -->`); anything not found
  is marked `VERIFY` and kept generic. No source = no maritime claim.
- **Consequences are physics, not "wrong".** What the trainee did is run through the system - a pump with nowhere to
  go dead-heads, a warm line flashes, a tank without vapour return loses pressure - and the result is shown on the
  screen and then explained, with a photograph where one exists.

## 2 · No bugs - for a trainee who has never held a tablet

- **All touch goes through the shared engines**: `GBLab.drag` (drag, or tap then tap), the `gb_hmi` panels, plain
  buttons. A page that must follow a finger itself (drawing a route or a curve) handles `pointercancel`, a second
  finger and a lost window, exactly as `GBLab.drag` does.
- **One press, one action.** The big button, the sheets and the "how sure" sheet already refuse double taps; a page
  button that starts something must refuse a second start while it runs.
- **No dead ends.** Every state has a way on: a sheet always has a button, a wrong step can always be undone or reset,
  the big button always says what it will do.
- **Nothing missing.** No reference to a file that does not exist (a 404 fails the test); a picture still to come is
  simply not referenced.
- **The test proves it**: `tools/task-test/tests/<task>.js` plays the right path to `ok === total` and every
  consequence path, with real taps and drags; the random-touch run (200 steps) finds no script error, no stuck screen
  and never a second `gb-task-done`.

## 3 · Beautiful - a place, not a form

- The photograph or the ship's screen fills the stage; controls float on dark glass; numbers glow; every touch
  answers within 100 ms with motion and a quiet sound.
- Nothing overlaps; nothing smaller than 44 × 44 px on the phone and 56 × 56 px on the tablet; question text 18 px,
  answer text 16 px.
- Real equipment only - photographs from the approved list, the ship's screens from `gb_hmi`. No cartoons, no emoji.

## 4 · Intuitive - nobody has to explain it

Owner, 2026-10-19, on a task with no guidance: *"too freaking hard to understand and what to do"*. So every task
is guided at every moment - the knowledge is tested, the way through never is:

- **The opening card** (`GBLab.intro`): the situation in one sentence, the steps in order (3-4, numbered), one
  button to begin.
- **The "do this now" line** (`GBLab.now`): always names the next button or action, worked out from the task's
  state ("Switch it on: press **POWER**"); amber when a decision is needed, green when all is done. On a phone it sits
  in its own strip above the picture, never over it.
- **The hint button** (`GBLab.hint`) on the stage: a hint for this moment that helps without giving the answer.
- **The big button glows** (`GBLab.goReady`) when pressing it is the next move; its label always says what it does.
- Where the trainee must find a thing on a picture or a model, say how many ("find **2** problems here") and mark
  the point the next step needs (it glows amber).
- A "What happened" card tells what the system just did - the trainee still reads the plant, as on board.
- Never an error message: a wrong try is answered calmly ("That one is fine. Keep looking.") and the trainee is never
  stuck.
