# Builder card - one approved module, start to MODULE CLEAN (2.66.0)

The whole job of a module builder in the whole-course workflow (`orchestration/workflows/build_course.js`). Read this card,
not the course-factory SKILL.md: the SKILL is the operator's process (intake, approval, the laws); the build is below.
WHY (the 2.63.3 M01-M03 run): every builder read SKILL.md, most of compile/GUIDE.md, CATALOGUE.md and the kit's SPEC.md
first - ~130,000 characters carried in every later turn (M02's builder: 98 M cache-read tokens, $19.6 of its $25).

## The rules that never bend
- The words are the APPROVED script's (`working_claude/script/MNN.json`). Never edit it - not a word, a kind, a minute; never
  `content_script.py approve`/`apply`. A finding whose fix is in the script is the operator's: report it, leave it.
- Never type a deck's or a task page's HTML - the compiler writes them. Write only in your module folder, your
  `script/MNN.build.json` (+ `MNN.*` beside it) and `figures/MNN/`.
- A part a person fixed by hand (`data-sme`, an SME comment) is content (L24): the build stops on it and says what to do.
- Honesty markers (`TBD_FROM_SME`, `RIGHTS_REVIEW_REQUIRED` ...) are reported, never deleted to make a check pass.

## The commands (from `<factory>/course-factory`, every python with `-I`)
```
python ../course-module-ui/scripts/design_system.py install <course>/modules/moduleNN
python compile/scripts/compile_module.py <course> --module N --init-build [--seed-from <predecessor>]   once, no sheet yet
python compile/scripts/build_module.py <course> --module N --no-course-pages [--long-pole]               after every change
```
- `--init-build` writes the build sheet and starters. Screens marked `"_seeded"` start from a hand-fixed predecessor's
  drawing or photo: build them AS THEY ARE, change only what the build reports. (2.66.3) It also fills what the module's
  own files decide - a photo slide's photograph (its record's `used_in`, or its description), a question "on the GA from
  slide 4" with that drawing and the places its labels name - and prints each: check them, fill only what is left.
- Fill the build sheet (each slide's picture, layout, photos - photos from `assets/img` or the Gas Library copy the
  operator names); a starter figure spec is edited only for what the build prints (`figures/MNN/sNN.kit.json`; parts and options:
  `course-visuals/kit/CATALOGUE.md`; never kit.js). A 3D slide: its `sNN.kit3d.json` (`course-visuals/kit3d/SPEC.md`,
  `PARTS.md`) - place the parts as on board, delete `"_todo"`. The workflow's 3D step checks and photographs it after you.
- **BUILD FIRST, then fix only what the build prints (2.66.0 - the first 2.66.0 proof run: builders deleted the starters
  and redrew every figure by hand in the studio, 50 minutes and no module built).** Fill the blanks the build names and
  run the build - the starters are drawn already: never delete or rewrite a starter, never open the studio on a figure
  the build did not name. A starter marked `"_pattern"` is a tested, physically correct IGF figure: change only its words
  (to the script's) and its steps' lines. A figure you DO change: place parts by what they stand on or join
  (`"on": "G.deck"`, `"in"`, `"at"`, pipes `"from"`/`"to"` - SPEC.md "Relations"), never a guessed y.
- Run build_module.py IN THE FOREGROUND with the shell's longest timeout (600000 ms). `STILL BUILDING` (exit 3): run the
  SAME command with `--wait` until it answers. Never a second build meanwhile, never an edit while it runs, never end your
  turn while it runs. A first build waits its turn behind another module's first build (one at a time on this computer) -
  expected: it answers STILL BUILDING meanwhile; keep running the same command with `--wait`.

## Reading its answer - one line per problem, with its fix and file
The answer lists only what fails (the full log's path is its last line - open it only when a line is not enough).

| the line says | do |
|---|---|
| `FIGURE sNN ... small text / label / text zone / inside / cut off` | fix the spec in the studio: `python ../course-visuals/kit/scripts/studio.py <spec> --step all` (seconds, every step, its real slide) until clean, then ONE build. Change the parts it names together. Fewer or shorter words, a part moved, the spec's `size` closer to the panel's shape |
| `spec: sNN.kit.json: NAMED / LOOSE END / INSIDE / NO GAS / AIM / GRID / TRUTH / LABEL <part> ...` | a BLOCK (2.66.0): the figure shows a clear physical error - draw the thing the words name (or take the words out), end the pipe on a part (`"to": "<id>.<port>"`), stand the part on the deck (`"on": "G.deck"`), play the vent in the step that vents, aim the spray (`"aim"`), a drawing under every named caption, a callout's leader on the part it names (LABEL, 2.66.3: `"for": "<id>.top@0.1"` for a space with a part in its middle). The line says which. A pattern that fits does it all (`course-visuals/kit/patterns/`). Sure it is RIGHT on purpose (the line runs on to the shore)? Accept it with its reason in the spec - `"meaning_ok": {"LOOSE END P1": "runs on to the bunker vessel"}` (the key is the line's `<KIND> <part>`) - never twice the same build for one finding. Notes are the figure reviewer's, not yours |
| `FIGURE sNN ... empty` | crop what no step shows, spread the parts, or give the slide `"composition": "wide-left"` when the drawing is tall and narrow |
| `the closer fit was applied to the spec by the build` | nothing to copy (2.66.3): fix only what it lists, in the spec as it now is |
| `... a fit was saved as ... candidate.kit.json` | it was not applied (it would add a meaning BLOCK, or needs the photo row off): fix the spec yourself |
| `COMPILE ... nothing built: ... starter's blanks` | fill exactly what it names in the build sheet |
| `COMPILE ... looks exactly like the slide before it (L62)` | give one of the two another layout or picture in the build sheet |
| `COMPILE ... the words say X, the drawing's readout shows Y` | make the step's readout agree (`play`), or `"numbers_differ": "<why>"` |
| `COMPILE ... the photo ... is "not a X" by its own record` | a picture of the thing itself, or `"photo_ok": "<why>"` |
| `COMPILE ... the real photograph ... could carry` a question | use the line it gives (areas in % of the photo), or `"photo_declined": "<why>"` |
| `AUDITS ... scrolls / over-filled` | the slide's words do not fit its layout: `"parts"` or another layout in the sheet |
| `AUDITS ... small / low contrast` on a drawing | the figure's column is too narrow - a wider layout, fewer words in the drawing |
| `TASK PAGES - FAIL` | a question graded wrong or a leader line crosses words: the sheet's `"labels"` / `"areas"`, or the drawing |
| `RECOMMENDED (L60)` | build the scene on that slide, or `"declined_3d": "builder: <reason>"` at the TOP of the sheet - never unanswered |
| `LAYOUT - ... built again their next way` | nothing - the build did it (L62) |
| `(nothing changed since this build's last answer ...)` | the same report again, nothing built (2.66.3): change what it lists first - a build with no change only repeats it |

Anything the table does not cover: `compile/GUIDE.md` - §2 layout, §2b photos and empty space, §2c sheet choices, §2d task
pages, §2e drawings - read only that section.

## Stop
At **PASS**, or **`FAIL MNN - course package`** with **`MODULE CLEAN`** under it (the package is judged after assembly).
Do NOT review the sheets and do not polish - the workflow's FIGURE review (every figure at projector size, a reviewer who
did not build it) and the QA agent look after you. Anything you would polish: list it.

## Report (your final message)
First line: the PASS / FAIL line build_module.py printed. Then: the full log's path, how many build_module.py runs, every
honesty marker with its source, the Track A buckets and Track B ratio the build printed, what moved to the handout, every
line under "To fix" or "left as it is", the L60 answer (the scene's slide, or the reason), and what you would polish.
