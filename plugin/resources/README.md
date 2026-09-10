# resources/

Plugin-level assets shared by more than one skill.

**`patterns/` arrived in 2.1.0 with `course-visuals`** — three reusable visual engines, described in
`patterns/README.md`. Everything else the skills use still lives inside its owning skill, reached by
a relative path that works in both the user-skills layout and the plugin layout:

| Asset | Lives in | Leave it there |
|---|---|---|
| `gb_tokens.css`, `tokens.json` | `skills/course-module-ui/` | the skill is the token authority; moving it would break its own references for no gain |
| `gb_run.css` / `gb_run.js` | `skills/course-module-ux/assets/` | |
| `task_complete.*`, `kbd_escape.*` | `skills/course-task-ux/assets/` | |
| every validator and probe | each skill's `scripts/` | |
| `platform.json`, `build-order.json`, `delivery-contract.json`, `hours-rules.json` | their owning skills' `knowledge/` | |

Nothing was relocated during migration. An asset moves here only when a **second** skill genuinely
needs it, and moving one is a deliberate change with its own commit — not a tidy-up.

## What is here

- **`patterns/`** *(2.1.0)* — `photo-pins`, `stepped-process`, `system-schematic`. Course-agnostic,
  ES5, dependency-free, token-driven. See `patterns/README.md` for the problem each one solves.

## Still expected

- **`engines/`** — one canonical copy of each shared `gb_*` engine. The reference course carries
  five identical copies of `gb_done.js`, and two of its modules each carry four **dead**
  visualisation engines copied wholesale from a third. Shipping one canonical set is the fix, and
  it also closes finding **F-2**, where the record engines point at a skill that no longer exists.
- **`schemas/`** — `programme.json`, `plan.json`, `course.json`. (The asset provenance schemas
  shipped inside `course-visuals/source/schemas/`, beside the guide that explains them.)

`resolve_asset.py` searches this directory as **level 2** of the asset pipeline, so anything added
here becomes reusable across every course automatically.

**Not here:** course content, photographs, or the ICS/SIGTTO figures — six of those are marked
*NOT cleared for issue or publication*.
