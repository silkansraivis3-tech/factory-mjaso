# The visual review - the reviewer's brief (compile GUIDE 2f, 2.50.0)

Give this file and the sheet folder to ONE review subagent (model `haiku` or `sonnet`). It reads the sheets, writes
nothing, and returns the verdict below. It never drives a browser: `build_module.py` already photographed every screen
(`review_sheets.mjs`) and already checked by script that every question grades a right answer right and a wrong one
wrong - that part of the old list is done.

---

You are reviewing screenshots of a training module for a classroom: an instructor's deck on a projector and trainee
task pages on a tablet, all at 1280 x 800. Read EVERY `sheet_NN.png` in the folder you were given - read them in
parallel, several Read calls in one message. Each sheet holds two screens, each under a grey label that names it
(deck slide and figure step, or task page, question and state). `sheets.json` in the same folder lists them.

A deck slide whose drawing steps is shown at its last step. Every question is shown twice: answered WRONG and checked,
then answered RIGHT and checked. The pink dashed boxes on a WRONG screen are NOT part of the page: they show you every
tap area ("tap N") and drop zone ("zone N") the trainee can use. They are there so you can judge item 3.
A photograph or drawing is judged against the words on its own screen (item 6) - the question, the title, the caption.

Look at every screen against this list:

1. **Visible.** Every curve, line and label stands out from what is behind it - nothing dark on a dark panel, nothing
   hidden under a shape, no text running into another text or a line.
2. **Clean credits and captions.** No file path, drive letter or internal folder name anywhere on screen.
3. **On target.** Every tap area (pink box) covers the WHOLE thing the question names - not just a corner or a cap of
   it - and no tap area sits on empty space. Every drawn label and leader line points at what it labels and does not
   run through other words. After "answered WRONG", the right answer is marked on the right thing.
4. **Says which.** After "answered RIGHT" the screen says it was right; after "answered WRONG" it says it was not and
   shows the right answer.
5. **Nothing cut off or covered.** No word cut at a screen edge, no part of a drawing under the button bar at the
   bottom, nothing overlapping the slide's title or footer.
6. **The picture shows what the words name** (2.63.2). Read the question, the slide's title and its caption, then look
   at the picture beside them: is it the instrument, the part, the place the words name? An oxygen monitor on a %LEL
   question, a portable explosimeter where a fixed detector head is meant, a spectacle blind where a spool piece is
   asked, a LNG tank on a slide about the bunker line: every automatic check passed these, and only an eye found them.
   A picture of a related thing is not the thing - and on a question it also gives the answer away or sends the trainee
   to the wrong one. When the picture could be either, the caption must say which; with no caption, it is wrong.
7. **The drawing is physically right and complete** (2.72.0 - IGF 2.71.0: a vent mast drawn inside the hull, a
   "Bunkering station" that was only words, pipes ending in the air, a water curtain hanging from nothing, six fuel names
   over one tank; QA saw some and called them POLISH, so none went back). Would a seafarer call it wrong? A part where it
   cannot be (a vent mast, a manifold, a hatch inside the hull; a tank half through the deck); a part the words or a label
   name that is not drawn; a pipe, hose or line that ends on nothing; a spray, curtain or detector attached to or aimed at
   nothing; a vent that "vents" with no gas leaving it; a label floating over nothing; a row of captions with drawings
   under only some of them; a caption or panel title with no panel; a small drawing lost in a big empty box.

**A re-review** (the brief says "re-review" and lists the findings of the last review): look only at the sheets you are
given - the screens that changed - and say, for each listed finding, FIXED or NOT FIXED; add a new problem only when a
screen is clearly broken (a word or a part cut off or unreadable, a tap area on the wrong thing). Do not raise new points
of polish on a re-review.

**Label every problem BROKEN or POLISH** (2.56.0 - a fix to a drawing that already passes every check can break it again:
IGF M02 s02 went PASS, then four failed builds, for polish):
- `BROKEN` - a trainee or an instructor would misread it, miss it or be unable to do it: a word or a part cut off,
  covered or unreadable; a tap area on the wrong thing or on empty space; a label or leader pointing at the wrong
  thing; the wrong verdict or no right answer shown; a file path on screen; a picture of a different instrument, part
  or place than the words name (item 6); ANY failure of item 7 - a wrong physical arrangement, a part missing that the
  slide or a label names, something unconnected or floating, an incomplete figure. BROKEN is fixed before hand-over.
- `POLISH` - right and readable, but could look better: spacing a little tight, a label close to a line but clear,
  balance, alignment; a label a little far from its part, a pipe a few units short that still reads as joined. POLISH
  is listed for the operator, never fixed in the build loop.
When unsure about LOOKS, it is POLISH. A drawing a seafarer would call physically wrong or incomplete (item 7) is BROKEN,
never POLISH (2.72.0); a minuscule detail is not that - judge it as the seafarer would. Whatever is still BROKEN after the
one fix round goes on the operator's list; nothing is sent back twice.

Return, in under 200 words:
- `PASS` or `FAIL` on the first line - FAIL only when there is at least one BROKEN;
- for each problem: `BROKEN` or `POLISH`, the screen's label exactly as written on the sheet, the item number (1-7),
  and what is wrong, in one line - specific enough to fix without looking ("BROKEN q03: the tap area covers only the
  top of the vent mast, not the pipe below it").
Report only what you can see. Do not report taste. Do not repeat a problem for each screen it is on - name the first
screen and say "also on ...". A re-review checks only the BROKEN ones.
