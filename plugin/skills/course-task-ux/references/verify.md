# Verifying a task screen

**v2 (2026-09-03) · Maintained by Raivis · Personal — installed for Raivis only, not org-published**

Read this before reporting any measurement, and before signing off any task page. The floor
itself is `SKILL.md` §11; this is how to establish it truthfully.

**The thing to be afraid of is not a failing report. It is a clean one that is wrong.** Every
trap below produced a confidently clean or confidently false number on the reference build,
and two of them nearly caused a "fix" to something that was already correct.

## Precedence: the browser is the authority, the static sweep is a pre-filter

State this before acting on any finding. It is the one rule that would have prevented the
worst false-positive episode this skill has had:

> **`measure_in_page.js`, in a real browser at the target viewport, decides what is true.
> `check_task_pages.py` only decides what is worth looking at.**

A static finding is **a question to take to the page**, never a defect to fix on sight. The
episode: the floor check reported **14 findings** against a shipped task set; the same page
measured in the browser at 800 × 1280 returned `htmlSubFloor: 0, svgSubFloor: 0`. **All 14
were false** — a clamp check that read one dial instead of resolving three, a
`padding:clamp(…)` mistaken for type size, wrong line numbers from collapsed comments, and two
SVG labels judged on their declared size. All four causes are fixed, but the precedence is
what makes the *next* such bug cheap instead of expensive.

Practical consequence: **do not edit CSS on the strength of a static finding alone, and do not
report one as a defect, until the page has been measured.** If the two disagree, the browser
wins and the script has a bug worth fixing — say that, rather than quietly working around it.

## Order of work

1. **Static sweeps first** — `scripts/check_task_pages.py`. Cheap, deterministic, and it
   catches the two defects that are invisible in a browser (dead markup) or fatal in it
   (broken inline JavaScript).
2. **Load the page and read the console** — `SKILL.md` §12. Non-negotiable after any scripted
   or templated edit.
3. **Measure in the page** — `scripts/measure_in_page.js`, pasted into the console.
4. **Drive the task** — answer a part, submit, check the explain/hint path renders and stays
   on screen, reach the completion panel, and read the console again.

Step 4 is the one that gets skipped and the one that finds the real defects. A task that
measures perfectly and cannot be finished has failed.

## The static sweeps

```
python scripts/check_task_pages.py <path-to-task-pages> [--css <dir>] [--js <dir>]
                                   [--only NAME] [--viewport WxH]
```

`--viewport` defaults to `800x1280` and is what the `floor` check resolves `vw`/`vh`/`vmin`/
`clamp()` against. A different device passes its own — the floor is re-measured, not
inherited. Every floor finding names **which dial bound** (`clamp-min`,
`clamp-coefficient`, `clamp-ceiling`, `vmin`, `rem`, …) so it can be checked by hand in one
step; `SKILL.md` §11.1 is the rule behind it.

Two things the `floor` check deliberately does **not** report, because reporting them wrongly
is worse than not reporting them:

- **SVG `font-size`.** Declared is not painted (see the SVG trap below). It counts them and
  tells you to run the probe instead.
- **Anything it cannot resolve statically** — `em`, `%`, `calc()`, `var()`. Silence here is a
  known false negative, covered by the probe.

Exit codes, so it can gate a build:

| Code | Means |
|---|---|
| `0` | every enabled check passed |
| `1` | at least one check found something. Findings are printed with file and line |
| `2` | usage error — a path does not exist, no HTML found |
| `3` | a check could not run at all (e.g. `node` absent for the syntax check) — **not** a pass |

Exit 3 is deliberately distinct. A skipped check reported as a pass is how the comma defect
in §12 survived. `--only` runs one check: `syntax`, `deadmarkup`, `numbers`, `floor`, `kbd`.

**A zero exit is not proof the work happened.** After changing a check's behaviour, read the
specific output line for the thing you changed, not just the exit status.

## Measuring in the page

`scripts/measure_in_page.js` is pasted into the browser console (or run through the browser
tooling available in the session). It reports tap targets below the floor, text below the
floor, contrast against the *resolved* — alpha-composited — background, horizontal overflow,
overlap, and the SVG text correction below. It refuses to run when the viewport is
implausible; see the first trap.

What it cannot do, and you must do by hand: decide whether the *right* control is the one
live control (§4), whether a hint gives the answer away (§6), whether a caption over-claims
what a photograph shows (§7), and whether the completion panel says what happens next (§9).

## Traps that produce false results

**A hidden or unfocused browser pane lays out at 0 × 0.** Every geometry number taken in that
state is garbage — and it is garbage that looks like a catastrophic failure, or like a clean
pass, depending on the check. **Read `innerWidth` first and abort the probe if it is small.**
The bundled probe does this and refuses rather than reporting. If a probe returns
suspiciously uniform zeros or suspiciously perfect results, suspect this before anything else.

**SVG text: the declared size is not the painted size.**

```
effective px = declared px × (rendered width / viewBox width)
```

A label declared at `font-size:12` inside a viewBox 350 units wide, rendered 843 px wide, is
painted at **28.9 px**. Reading the declared value alone made a correct label look like a
floor violation and nearly caused it to be "fixed" upward to something enormous. This cuts
both ways: a viewBox wider than its rendered box shrinks text below the floor while the
markup reads as compliant.

**A stale stylesheet from disk cache.** Serve over HTTP on a **fresh, unused port after every
edit**. A file:// reload or a reused port has repeatedly served the previous CSS, so the
measurement described a page that no longer exists.

**`clamp()` sizes do not recompute after a viewport change.** Resize first, *then* reload.
Measuring after a resize without a reload reports the old viewport's sizes.

**Reading one dial of a `clamp()` and calling it the answer.** This was in v1 of this skill as
"at 800 px wide, `1.5vw = 12px`: it is the clamp minimum that a portrait tablet gets" — true
at exactly 1.5vw, wrong as a general rule, and it is what produced the 14 false findings
above. `clamp(11px, 1.6vw, 14px)` at 800 px resolves to **12.8 px**: the coefficient binds and
the minimum is unreachable. Resolve all three at the target viewport and judge the one that
binds — `SKILL.md` §11.1 has both failure directions with counts.

**Batched activate-and-measure calls return stale rects.** A loop that reveals a panel and
measures it in the same batch can read the previous panel's geometry. Re-measure any single
finding on its own before believing it, and never report a batch result you have not spot-checked.

**A `display:none` element measures 0 × 0 and is not a violation.** Progressive disclosure
(§4) means most of a task page is legitimately hidden. Activate each part, then measure that
part — the probe skips zero-size nodes rather than failing them, which means a genuinely
collapsed visible control can hide in that exemption. Check the parts you activated.

## Reporting a measurement

State the viewport you measured at, the number of nodes examined, and which checks were
manual. A report that says "no violations" without saying what it looked at cannot be
distinguished from a report taken in a 0 × 0 pane. If something could not be verified in the
session, say so and name what would verify it — that has been more useful than a workaround
presented as a success.
