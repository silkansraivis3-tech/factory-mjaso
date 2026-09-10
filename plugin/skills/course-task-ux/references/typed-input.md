# Typed input on a tablet task screen

**v2 (2026-09-03) · Maintained by Raivis · Personal — installed for Raivis only, not org-published**

Read this only when a task legitimately has a text field. `SKILL.md` §2 permits that in one
place: a simulator or field **reporting** task, where reporting what you did or saw is the
exercise. Everywhere else, a text field is the defect and the fix is an answer mechanic from
§2, not a better keyboard.

## The rule, restated as an acceptance test

Hand the tablet to someone who has never used it. They tap a field, type, and then **put the
keyboard away without knowing anything about Android**. If they cannot, the page is not
finished — regardless of how correct the task is.

## Wiring

Two files, in `<head>`, and that is the entire integration. The engine finds the fields
itself; no page markup changes, no per-field JavaScript.

```html
<link rel="stylesheet" href="../assets/kbd_escape.css">
<script src="../assets/kbd_escape.js" defer></script>
```

Copy both from this skill's `assets/` into the course's own per-module assets folder. They
are per-module copies in the reference architecture, so `SKILL.md` §14 applies: a fix to one
is a fix to none.

## What the engine does, and why each part is separately necessary

| Route out | Mechanism | Why it alone is not enough |
|---|---|---|
| 1 | `enterkeyhint="done"` set on every single-line field at load | A keyboard skin or an older WebView may ignore the hint and keep showing a next-field arrow |
| 2 | Enter on a single-line input calls `blur()`; `preventDefault()` first so a form we do not own is never submitted | Only reachable if the trainee finds an Enter key; a numeric keypad may not show one |
| 3 | A `Done ✓` pill, fixed top-right, `display:none` at rest, `.on` while any field has focus | — this is the one that always works. Never drop it |
| 4 | `pointerdown` anywhere outside a field or label blurs | Discoverable by accident, not by design; cannot be the only route |

Details that were learned by getting them wrong:

- **The pill is top-right, not bottom.** The keyboard covers the bottom third of a portrait
  tablet, so a dismiss control down there sits underneath the thing it dismisses.
- **The pill hides on a 120 ms timer, not immediately.** Moving between two fields fires
  `focusout` before the next `focusin`. Hiding on `focusout` makes the pill flicker off
  between every two fields — visible and maddening on a 99-field page.
- **`mousedown` is prevented on the pill** so it cannot steal focus before it has had a
  chance to act on it. Without this the pill blurs the field by being pressed and then has
  nothing left to blur.
- **Textareas are exempt from route 2 and from `enterkeyhint`.** Enter is a newline there.
- **The pill's resting state is `display:none`, never opacity.** `SKILL.md` §9 — a control
  animated into visibility can stay invisible in a stalled WebView.
- **Measured on the reference build: 97 × 48 CSS px at 14.53 : 1 contrast.** Both clear the
  floor in §11 with room. Do not shrink it below 44 × 44.

## Field types

`FIELD` (the selector) and `isField()` (the runtime test) both list the accepted input types
and **must agree**. If they diverge the pill appears for a field that Enter will not blur,
which is worse than no pill because the trainee learns not to trust it. Add any new type to
both.

## Verifying it, per page

1. Load the page and focus a field. The pill appears.
2. Tab or tap to a second field. The pill stays on — it must not flicker.
3. Press the pill. Focus leaves, keyboard drops, pill goes.
4. Focus a field, press Enter. Focus leaves. No form submits, no navigation.
5. Focus a textarea, press Enter. A newline is inserted and focus stays.
6. Focus a field, tap blank page area. Focus leaves.
7. Read the console. `SKILL.md` §12 — the engine is inert if anything above it threw.

`scripts/check_task_pages.py` checks statically that a page with text fields loads both
engine files and that no single-line input carries a conflicting `enterkeyhint`. It cannot
check that the pill is reachable or unobscured; steps 1–6 above are manual for a reason.

## If the field count is large

Ninety-nine fields on one page is a symptom, not a requirement. Before wiring the keyboard
escape onto a page like that, ask whether §2 applies — if the trainee is typing ninety-nine
values that a set of taps could supply, the page is a printed worksheet that got pasted into
HTML, and `SKILL.md` §1 rules it out. Fixing the keyboard on a page that should not have
fields is fixing the wrong defect. Report it rather than absorbing it.
