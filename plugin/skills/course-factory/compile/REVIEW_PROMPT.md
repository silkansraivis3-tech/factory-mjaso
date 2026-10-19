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

The pink dashed boxes on an "as asked" task screen are NOT part of the page: they show you every tap area ("tap N")
and drop zone ("zone N") the trainee can use. They are there so you can judge item 3.

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

Return, in under 200 words:
- `PASS` or `FAIL` on the first line;
- for each problem: the screen's label exactly as written on the sheet, the item number (1-5), and what is wrong, in
  one line - specific enough to fix without looking ("q03: the tap area covers only the top of the vent mast, not the
  pipe below it").
Report only what you can see. Do not report taste. Do not repeat a problem for each screen it is on - name the first
screen and say "also on ...".
