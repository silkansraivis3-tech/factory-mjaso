---
name: course-module-ui
description: The locked LOOK of a course module - the token set every deck, task screen and handout draws from, the two slide modes (light and dark/photo), the header band, card, pill, photo and takeaway components, and the semantic colours for correct/wrong/hazard. Use when building or reviewing the visual layer of a module - "what colour", "which radius", "why does this module look different", "make it match Module 1", "the palette", "the typeface", "restyle this screen", "these two decks don't match" - or before shipping any new deck. Course-agnostic; GAS BASIC is the reference implementation. NOT screen composition, fill or overflow (course-module-ux), NOT task behaviour (course-task-ux), NOT the corporate logo and print identity (novikontas-brandbook), and never what a module teaches.
---

# The look of a module

`course-module-ux` owns whether a screen **works** — fill, overflow, contrast ratio, tap
targets. It is a floor, not an identity: two people can pass every check in `floor.json` and
produce courses that look nothing alike. That happened. This skill owns what a screen **looks
like**, so they cannot.

## When this skill runs

Step **8** of `course-factory`'s build order — *establish the visual system* — is this
skill, and for a new module it is **required**, not a polish pass. It sits after the screen
inventory and before the first line of HTML, because retro-fitting tokens onto a finished deck
is how drift gets signed off. `scripts/audit_ui.py --strict` then runs again at verify (step 15)
as part of sign-off. A new module does not reach sign-off without both.

## The one law

**Module 1's `:root` is the reference. Every other screen matches it.**

The owner ruled this on 2026-09-01 for interface, and it holds for the visual layer too. When
a value here disagrees with a shipped deck, the deck is wrong — but see *Known drift* before
changing anything, because three shipped modules disagree and that is the owner's call, not
yours.

Canonical values live in `knowledge/tokens.json`. That file is the authority; this guide points
at it rather than restating it, so there is one place to change a colour.

**Canonical means the look, not the layout.** Module 1 is the reference for the palette, the
typography, the two modes, the header band, card geometry, pills, spacing, radius, shadow, the
takeaway and the semantic colours. It is **not** a template to reproduce: there is no canonical
screen count, no canonical content density, no canonical practical/theory ratio and no required
screen sequence. A module may run 10 screens or 50, or be practical-only with almost no
presentation. Never copy Module 1's markup, and never add filler screens to resemble it
numerically. Composition is adaptive; the visual language is not.

Nor does this skill decide how much a screen teaches. Low visible density is not low learning
depth — progressive disclosure, layered cards, diagrams, animation and interactive figures are
all legitimate ways to teach without a wall of text, and nothing here should be read as
requiring, or forbidding, interactivity on any given screen. Pedagogy belongs to
`novikontas-pedagogy-toolkit`; the token set only has to stay out of its way.

## Never hardcode a colour — in new work

Every colour, radius, shadow and font in a **new** screen comes from a token:

```css
/* wrong - this is how the drift started */
background: #0A2463;
border-radius: 13px;

/* right */
background: var(--navy);
border-radius: var(--r-m);
```

**MEASURED, and it matters:** the reference module does not obey this. `presentation.css`
carries **134 raw chrome colours, 81 distinct**, outside its own `:root`. The token set is
real but only partly adopted — it was written after much of the deck already existed.

So the rule is *forward-looking*, not a description of the code. Do not point `--strict` at a
shipped module and start repainting; you would be rewriting a signed-off deck on the strength
of a lint rule. New screens tokenise; old screens get left alone until the owner asks.

One exception is permanent: a raw colour on `fill` or `stroke` inside a diagram — the sea in an
illustration, vapour in a cross-section — is content, not chrome, and stays raw.
`scripts/audit_ui.py` counts the two separately for exactly this reason.

## The two modes

A slide is **light** by default, or **dark** when it carries `.dark` or `.photo`. This is not a
theme toggle — both appear inside one deck, chosen per screen, and a photo screen is always
dark so the image is not framed in white.

Every colour that touches text therefore exists twice: `--dim-l` / `--dim-d`,
`--faint-l` / `--faint-d`, `--good` / `--good-d`, `--warn` / `--warn-d`, `--sh` / `--sh-d`,
`--line-l` / `--line-d`, and the wash pairs. **Pick the variant that matches the surface behind
it**, never the one that matches the last screen you wrote.

`--txt-d` is body text on a dark slide. There is no `--txt-l`; light slides use `--ink`.

## Where to look

| You are doing | Read |
|---|---|
| Choosing any colour, radius, shadow, font | `knowledge/tokens.json` |
| Building the header band, a card, a pill, a photo screen, a takeaway | `references/anatomy.md` |
| Marking something correct, wrong, hazardous | `references/anatomy.md` § Semantic colour |
| Starting a new deck | `templates/gb_tokens.css` — paste it, do not retype it |
| Checking a deck before sign-off | `scripts/audit_ui.py` |

## Boundaries

| Not this skill | Whose |
|---|---|
| Fill, overflow, contrast ratio, tap size, run script | `course-module-ux` |
| How a trainee answers, typed input, completion | `course-task-ux` |
| Logo, print identity, brand colour across the company | `novikontas-brandbook` |
| Hours, ILOs, build order | `course-factory` |

`novikontas-brandbook` owns the company's identity — Raleway, the logo, the corporate palette.
This skill owns what that becomes on a projected 1366×768 screen and an 800×1280 tablet. Where
they overlap, the brandbook wins on brand colour and typeface; this skill wins on everything
the brandbook has no opinion about, which is most of a deck.

## Known drift — read before "fixing" anything

Measured across the eight GAS BASIC modules on 2026-09-09:

- Modules **04, 07, 08** match Module 1 exactly.
- Modules **03, 05, 06** run a second dialect: `--blue-soft-*` / `--amber-soft-*` instead of
  `--blue-wash-*` / `--amber-wash-*`, eight reference tokens missing, and six values off by a
  shade (`--deep-3` `#10264F` vs `#122A52`, `--txt-d` `#F2F7FC` vs `#F3F8FD`, and four more).
- Two `gb_review.css` files declare no `:root` at all and inherit whatever is loaded.
- The second dialect has three tokens the reference lacks: `--red`, `--flame`, `--toxic`.

**Do not silently normalise a shipped module.** Repainting a signed-off deck is a content
decision. Report the drift, name the files, and let the owner decide. New work uses the
reference set.

`--red` / `--flame` / `--toxic` are a real gap: a gas course needs hazard colours and the
reference set has none. Adding them is an owner decision, not a fix to apply quietly.

## Honesty markers

Same set as the rest of the family. The visual layer earns two of its own:

- **MEASURED** — a value read out of a shipped file by a script, not from memory.
- **DRIFTED** — two shipped modules disagree and neither has been ruled canonical yet.
