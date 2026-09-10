# Measure lane — the discipline that makes a number trustworthy

**v1 (2026-09-03) · Maintained by Raivis · Personal — installed for Raivis only, not org-published**

Read this whenever anything is being measured, audited or signed off.

**The reason this lane exists.** A probe once reported *"zero contrast failures across all 16
slides."* The real number was **40**, including body text at **1.08:1**. Nothing in the probe
was wrong about contrast. It measured 150 ms after activating a slide, when every element still
computed `visibility:hidden`, skipped them all as hidden, found nothing, and reported a clean
sweep. A separate pass reported spills and sub-floor text that **did not exist**, because the
browser pane was collapsed and laid out at 0×0.

**A confidently wrong measurement is worse than no measurement**, because it gets signed off.
So the order is: know the traps, run the probes, then read the numbers.

The two authorities for this lane are data. Read them; they are not restated here:

- `measure/knowledge/traps.json` — every trap, its mechanism, and what it actually cost.
- `measure/knowledge/floor.json` — the sign-off floor. The probes read these thresholds.

---

## Before any probe runs

1. **Serve over HTTP on a fresh port.** `file://` hides real behaviour and blocks storage.
   ```bash
   python measure/scripts/serve_fresh.py <course dir>
   ```
   It prints the URL and the **PID**. Kill that PID and nothing else — a broad pattern kill once
   destroyed about forty unrelated servers on this machine.

2. **A fresh, previously-unused port after every edit.** Disk cache will hand you the previous
   build and your fix will measure as having done nothing. `serve_fresh.py` remembers which
   ports it has used.

3. **Check the viewport is real.** Every geometry probe reads `window.innerWidth` first and
   aborts loudly if it is small. Do not defeat that guard: a collapsed or backgrounded pane lays
   out at 0×0 and every number it produces is garbage that looks like data.

4. **Resize, then reload.** `clamp()` does not recompute on resize, so measurements taken after
   a resize describe the previous viewport.

---

## Run these, in this order

### 1 · The static checks — no browser needed

```bash
python measure/scripts/check_static.py selftest              # first, always
python measure/scripts/check_static.py slide-links  <module page>
python measure/scripts/check_static.py check-screen <module page>
python measure/scripts/check_static.py mins         <landing page>
python measure/scripts/check_static.py links        <course dir>
python measure/scripts/check_static.py paper        <course dir>
```

Exit `0` clean, `1` findings printed, `2` usage or parse error.

**Run `selftest` first, every session.** A checker that returns "clean" on every input is worse
than no checker, because it produces a signed-off report. `selftest` runs the checks against a
deliberately broken fixture and fails if they come back clean.

`slide-links` is the one worth understanding: it **carves each `section.slide` out of the
source** and searches inside it. Counting `<a href>` in the whole file is not this check —
landing-screen and footer links are legitimate and will drown a single bad link inside a slide.

### 2 · The browser probes

Serve the page, open it, and load each probe. Loading a probe only **defines** it; every entry
point returns a Promise and **must be awaited**. Each prints one line —
`VERDICT: PASS` or `VERDICT: FAIL n=<count>` — and sets `window.__auditExit` to `0` or `1`, so a
wrapper can turn it into an exit code. An abort is `FAIL n=1` preceded by a `console.error`,
never a pass.

```js
await AuditOpacity.all();     // or .slice(0, 9)
await AuditCollide.all();
await AuditDeck.all();
await AuditDrive.run();       // .run(0, 12)
```

They also register on `window.__audit` (`.opacity`, `.collide`, `.deck`, `.drive`).
`audit_drive.js` **depends on the other two being loaded first** and aborts naming the missing
file rather than throwing.

| Probe | What it decides | Portability to a new course |
|---|---|---|
| `audit_deck.js` | the sweep: text size (including **effective** SVG size), contrast, control size, fill per screen, links inside slides, document h-scroll | **Portable.** CONFIG edit only |
| `audit_collide.js` | collisions and overlaps — **run this even when the fill probe is silent** | **Portable with one gap**: check 3 (text under page furniture) needs the chrome selectors set, or it silently reports an unearned pass. See `traps.json#chrome-selectors-not-discoverable` |
| `audit_opacity.js` | that what you are measuring is actually **visible** — inherited `opacity` composited into the text alpha, which the contrast sweep cannot see | **Portable.** Least coupled of the four |
| `audit_drive.js` | drives the deck through its real Next control so the others see every screen | **Portable in form, coupled in substance.** It encodes a navigation model — one forward control advancing frags and slides linearly from a start button — that CONFIG cannot abstract. Separate frag/slide controls or keyboard-only nav need code changes |

**Read the CONFIG block at the top of each before the first run on a new course.** All
structural selectors and thresholds live there and nothing course-specific lives below them.
Then do one thing before trusting any pass: **print the match count for every CONFIG selector.**
A selector that matches nothing runs its check against an empty set and reports clean — four
selectors in the original probe set had been passing vacuously for the life of a deck for
exactly that reason.

**Front the tab.** A backgrounded tab throttles timers, so a sweep that takes about 16 seconds
fronted appears to hang indefinitely hidden. That is not a broken probe.

**Check what a probe enforces, not only what it prints.** `audit_deck.js` used to assemble
`linksInsideSlides` and `docHScroll` into its output and emit `fills` as a list, while its
failure predicate tested six other categories only — so a deck whose sole fault was a link
inside a slide printed `VERDICT: PASS` with the link count visible next to the pass. Those
numbers were **true**; the verdict was weak. It is fixed here, and the general form is
`traps.json#weak-verdict-not-wrong-data`: for every field a probe prints, ask whether the
verdict can fail on it.

**Overfill is counted as a failure; under-fill is not.** Fill above 100 % is overflow even when
the spill probe is silent, because the flex-centred body pushes it upward. Under-fill stays a
human call, because openers, summaries and the check screen are legitimately sparer.

**Run the fill probe and the collision probe both.** The slide body is flex-centred, so residual
overflow does not appear at the bottom — it pushes the top element **up into the header band**.
One probe reports 100–102 % fill and zero spill while the other finds a real overlap. Neither
result alone is evidence.

**Measure the whole document at least once, not only the slides.** Every probe walks `.slide`,
so a footer, a corner tag or the landing screen is never visited — a footer and a corner tag sat
capped at 11.5 px for the life of one deck for exactly this reason.

### 3 · The console

After any scripted edit to inline JavaScript, **load the page and read the console.** Not the
diff — the console. A comment replacement once left the old comment's tail as bare JavaScript
and killed an entire script while the page still looked fine; a missing comma in a generated
object literal silently disabled **every button** on two task pages. `node` may not be installed
on the machine, in which case the browser console is the only syntax check you have.

### 4 · The Next-to-the-end walk, by hand

Open the module page, press Start, and press Next to the end. It is one page, so this is a
minute's work and it is the acceptance criterion. Every screen must be actionable without
opening anything, and the last one must be the module check.

---

## Reading a clamp() failure before turning any dial

`clamp(min, coefficient, max)` has three dials and **only one binds at a given viewport**.
Turning the wrong one is a no-op that reads as "the fix did not work".

At a 768-line viewport **1 vmin is 7.68 px**, so **any coefficient below about 1.63vmin paints
under a 12.5 px floor whatever the minimum says.** One deck had **65 sub-floor instances caused
by coefficients, not minimums**. Elsewhere the *ceiling* was binding and the coefficient never
engaged at all: **43 rules capped under 20 px**.

So: compute all three at the target viewport, name which one is binding, then turn that one.

And for SVG text, never read the declared value:

```
effective px = declared font-size × (rendered width ÷ viewBox width)
```

A label declared at 12 px measured **28.9 px**, because a 340-unit viewBox rendered at 820 px.
Reading the declared value alone nearly caused a "fix" to correct type.

---

## Sign-off

Report the numbers from `floor.json`, per viewport, as numbers. Then state plainly:

- what failed, and what passed;
- anything you could not verify in the session, and **what would verify it**;
- every honesty marker you left in the artefact, copied into the delivery notes.

A report that says "all clear" without naming the settle time, the viewport it measured at, and
whether both the fill and the collision probes ran is not a sign-off. It is the report that said
zero contrast failures.


---

## The probe that finds lost text, and the three that lie *(added 2026-09-07)*

### `scrollHeight > clientHeight` — the one that actually found something

On any element, `scrollHeight - clientHeight > 0` means its content does not fit. With
`overflow:hidden` the text is **cut**; with `overflow:visible` it **spills** onto whatever is laid
out below it.

That second case is how a real defect hid: a card in the first row of a module screen spilled
36px and printed its last bullet *underneath* the second row. The words the room lost were a
whole bullet. And **no other probe saw it** — the slide did not overflow, nothing painted past
the slide edge, and `.slide-body` fill read a comfortable 100 %, because the loss was entirely
inside a card.

Two calibrations, both learned the hard way:

- **`scrollHeight` rounds up and counts descender space**, so a text element routinely reads
  4–10px "over" with nothing wrong. Set the floor at **one `line-height`** or you get dozens of
  false hits. That threshold is what separates the real 36px spill from the noise.
- Report **cut** and **spill** differently. They look different on screen and they have different
  fixes.

### `elementsFromPoint` lies when slides are stacked

Every slide is absolutely positioned at the same coordinates, so `elementsFromPoint` /
`elementFromPoint` return the **topmost element in DOM order regardless of opacity**. A contrast
or occlusion probe built on them composites the slide you are measuring against **the last slide
in the file**. That reported 16 of 27 screens failing, with white headings at "1.09:1", on text
that is about 15:1.

Two ways out:

- walk the element's **own ancestor chain** for background colour and gradient stops — that is its
  real paint context. It cannot see a background painted by a *sibling* band, so it under-reports
  where a page paints its header that way;
- or **isolate first**: `display:none` every other slide for the duration of the measurement, then
  the paint stack is real and you also get a free occlusion check. Live DOM only; restore after.

Even isolated, contrast in a preview pane stayed unreliable enough to stop reporting a number.
**The probes that need no hit-testing are the trustworthy ones:** bottom-edge overflow, computed
`font-size`, `scrollHeight` vs `clientHeight`, control rects, and Range-based text ink.

### Element boxes are not text ink

Hunting overlaps by comparing element **bounding boxes** flagged 11 clean screens: one deck's
`<h2>` is a full-bleed `[0,0,1280,73]` band, so every top-right kicker sits inside its box.

Compare **text ink** via `Range.getClientRects()` on the text nodes. And know its own trap:
`getClientRects()` returns **one rect per inline box**, so a `<b>` inside a paragraph yields a
rect identical to its line. Two identical rects are one line counted twice, not a collision —
that artefact made a perfectly good banner look like three layers of overprinted text, and it
took a measurement to disprove what a downscaled screenshot seemed to show.

**When a probe and a screenshot disagree, the screenshot wins.** Measurement bugs are as common
as layout bugs. Today three of four reported defects were probe artefacts.

### Two mechanical traps

- **Address a screen by its `data-title`, never by its index in a list of `<section` matches.**
  Comment blocks above new screens quote the tag, so the file has more matches than the deck has
  slides — I raised a label on the wrong screen that way. The DOM order from
  `querySelectorAll('#stage .slide')` is correct; a regex over the file is not.
- **A declared SVG `font-size` is not the rendered size.** It scales by
  (rendered width ÷ viewBox width). And look for *generated* labels: one deck's axis ticks are not
  in the markup at all — the deck's script builds them with `{"font-size": 12}`, which is why
  grepping the HTML found nothing.
- **A CSS or JS edit needs a fresh, previously unused port.** Busting the HTML with `?v=` does not
  revalidate `presentation.js`; the same audit kept reporting the old value until the deck was
  served from a new port.
