# Screen anatomy

Every measurement here is MEASURED from `Module_01/presentation/presentation.css`, the
reference module. Values are quoted so a new deck can be built without opening it.

---

## The slide

```css
.slide{
  position:absolute; inset:0; display:none; flex-direction:column;
  padding: min(6vmin,64px) min(7vmin,86px) max(80px,8vmin);
  background:var(--white); color:var(--ink);
  animation: slideIn .38s cubic-bezier(.22,.7,.28,1);
}
```

Three things follow from this and catch people out:

**The bottom padding is huge on purpose** — `max(80px, 8vmin)`. The takeaway strip and the
runner bar live down there. Do not reclaim it for content.

**Slides are stacked absolutely and switched with `display`.** Only one is in flow. A layout
that depends on document height will not behave.

**The entry animation runs for .38s.** Anything that measures a slide — fill, collision,
contrast — must wait for it to settle, or it measures a moving element and reports nonsense.
`course-module-ux` owns that rule; this is the number behind it.

## The header band

```css
.slide-kind{
  position:absolute; left:0; right:0; top:0;
  height: min(7.4vmin,62px);
  background:var(--navy); color:#fff;
  display:flex; align-items:center; gap:14px;
  padding: 0 min(7vmin,86px);
  font-size: clamp(12.5px, 1.55vmin, 20.1px);
  letter-spacing:.14em; text-transform:uppercase;
}
```

Navy, full-bleed, uppercase, widely letter-spaced. It says what **kind** of screen this is —
not the module name, not the slide title. It is the only place `--navy` appears as a large
fill; navy is a structural colour, not a content one.

Its left and right padding matches the slide's horizontal padding (`min(7vmin,86px)`) so the
band's text lines up with the body text underneath. Keep them equal.

## Type

One family, `var(--font)` — Raleway, with a real fallback stack. `var(--mono)` for figures,
codes and anything that must line up in a column.

Sizes are always a clamp, never a fixed px:

```css
font-size: clamp(12.5px, 2.05vmin, 30px);   /* a heading */
font-size: clamp(14px,  2.15vmin, 32.2px);  /* .lead */
font-size: clamp(12.5px, 1.5vmin, 15px);    /* small print */
```

**The clamp floor is 12.5px and that is not arbitrary** — it is the minimum text size in
`course-module-ux`'s `floor.json`. A clamp that floors lower ships a screen that fails the
audit on a small viewport. Scale on `vmin`, not `vw`: the deck is driven on a 1366×768
projector and an 800×1280 tablet in portrait, and `vw` collapses the type on the tablet.

## Cards

```css
.card{
  background:var(--white); border:1px solid var(--line-l); border-radius:var(--r-m);
  padding:min(2.6vmin,26px); box-shadow:var(--sh);
  display:flex; flex-direction:column; gap:.7em;
}
```

The dark-slide equivalent swaps every token for its `-d` pair: `--deep-2` ground,
`--line-d` border, `--sh-d` shadow. Same geometry, different surface.

`--r-m` (13px) is the default radius. `--r-l` (20px) is for panels and photo frames,
`--r-s` (8px) for pills and chips. Three radii, no fourth.

## Card grids and the two-stage tap

```css
.cmp-wrap{ display:grid; grid-template-columns:repeat(5,1fr); gap:min(1.6vmin,16px); }
.cmp-card.zoom{
  position:absolute; left:min(9vmin,110px); right:min(9vmin,110px);
  top:min(12vmin,130px); bottom:min(9vmin,100px);
  z-index:12; background:var(--deep-3); border-color:var(--amber);
  box-shadow:var(--sh-d); overflow:auto;
}
```

A card grid opens in **two stages**: the first tap opens the card, and only a second tap on the
picture takes it full screen. The zoomed state is inset from the slide edges — it is not a
full-bleed overlay — and it is bordered `--amber` so it reads as lifted rather than as a new
screen.

Always give a zoomed card an X. Never put the hint text over the picture.

## Photographs

A photo screen is always dark (`.photo` sets the dark ground) so the image is not framed in
white.

**Never squeeze a photograph to make it fit.** If a screen cannot afford the picture at its
own aspect ratio, the picture gets its own screen. And never cap a figure with a percentage
of a percentage — the two multiply and the image collapses on the tablet.

## The takeaway

```css
.takeaway{
  position:absolute; left:min(7vmin,86px); right:min(7vmin,86px);
  bottom:max(72px,6.4vmin);
  border-left:3px solid var(--amber);
  padding:.85em 1.2em; background:rgba(255,255,255,.04);
  border-radius:0 var(--r-s) var(--r-s) 0;
}
```

One per screen at most. The amber left rule is the only place amber appears as a line — it is
what makes the takeaway findable when an instructor glances back at the screen mid-sentence.

Note it is positioned `absolute` here. Some modules shift it into flow instead; if a screen's
takeaway sits in an unexpected place, check which of the two it is before adjusting anything
else.

---

## Semantic colour

Four meanings, and they are **not** the accent:

| Meaning | Light slide | Dark slide |
|---|---|---|
| correct, pass, safe | `--good` | `--good-d` |
| wrong, caution | `--warn` | `--warn-d` |
| live accent, focus, link | `--blue` | `--blue` |
| emphasis, the one thing to remember | `--amber` | `--amber` |

`--blue` is the interface accent — it means "this is active", never "this is good".
`--amber` is emphasis, never a warning. Using amber for caution and blue for success is the
single most common way a screen stops reading correctly at a glance.

`--cold` is a **content** colour — cryogenic, low temperature — not a UI state. It belongs in a
diagram, not on a button.

`--amber-ink` exists because text in `--amber` on an amber wash does not pass contrast. When
you put text on `--amber-wash-l` or `--amber-wash-d`, the text colour is `--amber-ink`.

**There are no hazard colours in the reference set.** Modules 03/05/06 invented `--red`,
`--flame` and `--toxic` locally. For a gas course that is a real gap — but inventing values is
an owner decision. See `knowledge/tokens.json` § open_questions.

---

## What a new deck starts from

1. Paste `templates/gb_tokens.css` at the top of the stylesheet. Do not retype it.
2. Build with `var(--…)` only. Any raw hex below the `:root` block is a defect.
3. Run `scripts/audit_ui.py` before sign-off.
