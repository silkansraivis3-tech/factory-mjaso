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

**A re-review** (the brief says "re-review" and lists the findings of the last review): look only at the sheets you are
given - the screens that changed - and say, for each listed finding, FIXED or NOT FIXED; add a new problem only when a
screen is clearly broken (a word or a part cut off or unreadable, a tap area on the wrong thing). Do not raise new points
of polish on a re-review.

**Label every problem BROKEN or POLISH** (2.55.0 - a fix to a drawing that already passes every check can break it again:
IGF M02 s02 went PASS, then four failed builds, for polish):
- `BROKEN` - a trainee or an instructor would misread it, miss it or be unable to do it: a word or a part cut off,
  covered or unreadable; a tap area on the wrong thing or on empty space; a label or leader pointing at the wrong
  thing; the wrong verdict or no right answer shown; a file path on screen. BROKEN is fixed before hand-over.
- `POLISH` - right and readable, but could look better: spacing a little tight, a label close to a line but clear,
  balance, alignment. POLISH is listed for the operator, never fixed in the build loop.
When unsure, it is POLISH.

Return, in under 200 words:
- `PASS` or `FAIL` on the first line - FAIL only when there is at least one BROKEN;
- for each problem: `BROKEN` or `POLISH`, the screen's label exactly as written on the sheet, the item number (1-5),
  and what is wrong, in one line - specific enough to fix without looking ("BROKEN q03: the tap area covers only the
  top of the vent mast, not the pipe below it").
Report only what you can see. Do not report taste. Do not repeat a problem for each screen it is on - name the first
screen and say "also on ...". A re-review checks only the BROKEN ones.
