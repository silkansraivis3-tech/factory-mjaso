# resources/

Plugin-level assets shared by more than one skill.

**Intentionally near-empty in 2.0.0.** Phase 2 was a migration, and every asset the five proven
skills use today already lives inside its owning skill, reached by a relative path that has worked
in both the user-skills layout and the plugin layout:

| Asset | Lives in | Leave it there |
|---|---|---|
| `gb_tokens.css`, `tokens.json` | `skills/course-module-ui/` | the skill is the token authority; moving it would break its own references for no gain |
| `gb_run.css` / `gb_run.js` | `skills/course-module-ux/assets/` | |
| `task_complete.*`, `kbd_escape.*` | `skills/course-task-ux/assets/` | |
| every validator and probe | each skill's `scripts/` | |
| `platform.json`, `build-order.json`, `delivery-contract.json`, `hours-rules.json` | their owning skills' `knowledge/` | |

Nothing was relocated during migration. An asset moves here only when a **second** skill genuinely
needs it, and moving one is a deliberate change with its own commit — not a tidy-up.

## What Phase 3 is expected to put here

From the approved blueprint, §2 and §7:

- **`engines/`** — one canonical copy of each shared `gb_*` engine. Today the course tree carries
  five identical copies of `gb_done.js`, and a copy goes stale the first time the engine is fixed.
  Shipping one canonical set is itself the fix.
- **`patterns/`** — the photo-annotation pin overlay (image-space coordinates), the stepped-build
  cross-section, the tap-a-card comparison grid, the chips-onto-an-axis ladder, the sourced curve
  with `~` on interpolated points, click-to-enlarge, and the wrap-up timer that never advances.
- **`schemas/`** — `programme.json`, `plan.json`, `course.json`, `_photo_meta.json`,
  `_figure_meta.json`.

Those arrive with `course-visuals`, which is the skill that will consume most of them.

**Not here:** course content, photographs, or the ICS/SIGTTO figures — six of those are marked
*NOT cleared for issue or publication*.
