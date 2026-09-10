# Course Factory blueprint

**The architecture to build in Phase 2.** Proposal, for review. Nothing here is implemented.

Phase 1 · 2026-09-10.

---

## 0 · The finding that shapes everything else

**The Course Factory is not greenfield. It already exists and it already works.**

`github.com/silkansraivis3-tech/course-factory` holds a five-skill bundle at **v1.3.0**, built during
GAS BASIC production, with fifteen Python scripts (eleven of them checks and gates), five in-page
measurement probes, a publisher with an eight-check gate, and a colleague-facing install path. It
produced a 43-academic-hour accredited course that runs on two Android terminals with 0 dead links,
0 dead ends, 64/64 programme topics and 266/266 IMO model-course outcomes.

So Phase 2 is **not** "write a course factory". It is:

1. **Move** the five proven skills into a proper plugin in this repository.
2. **Close four holes** the existing bundle does not cover.
3. **Make the laws deterministic** where model compliance is not good enough.
4. **Fix the distribution**, so a colleague installs one thing and gets a complete system.

Designing from scratch would throw away the most valuable thing in the project: rules that are the
scar tissue of specific, recorded failures.

### The four holes

| Hole | Why it matters | Answer |
|---|---|---|
| **No owner for instructional visuals** | The bundle has a token authority (`course-module-ui`) and a UX floor (`course-module-ux`). Neither decides whether a concept should be a photograph, a schematic, an SVG animation or a sentence. That decision is exactly where generic AI course graphics come from. | new skill `course-visuals` |
| **No owner for the asset pipeline** | The four-step hierarchy, licences, provenance and rights escalation exist only as one course's `IMAGE_BRIEF.md`. | second lane of `course-visuals` + `visual-sourcer` agent |
| **No general evidence retrieval** | `gas-basic-kb-retrieval` is project-local and GAS-BASIC-specific, but `NO SOURCE = NO MARITIME CLAIM` applies to every course. | new skill `course-evidence` + `evidence-retriever` agent |
| **No deterministic protection** | Every law today depends on the model remembering it. The recorded failures — hand-edited generated files, a bulk whitespace pass that damaged 37 files, remote fonts, missing back-hooks — are all mechanically detectable. | `hooks/hooks.json` |

---

## 1 · Current Claude Code extensibility — verified 2026-09-10

Checked against `code.claude.com/docs` (the `docs.claude.com/en/docs/claude-code/*` URLs now 301 to
it). Everything proposed below uses a stable mechanism.

**Plugins.** A plugin is a directory with `.claude-plugin/plugin.json` (`name`, `description`,
optional `version`, `author`). Component directories sit at the **plugin root, never inside
`.claude-plugin/`**: `skills/`, `agents/`, `hooks/hooks.json`, `.mcp.json`, `.lsp.json`,
`monitors/monitors.json`, `bin/`, `settings.json`. `commands/` still works but `skills/` is the
recommended layout for new plugins.

**Marketplaces.** `.claude-plugin/marketplace.json` with `name`, `owner` (object, `name` required) and
`plugins[]` (each `name` + `source`). Source may be a relative `./path`, or an object of type
`github` / `url` / `git-subdir` / `npm` / `archive` / `command`. A user adds a GitHub marketplace with
`/plugin marketplace add owner/repo`. Private repositories are supported through existing git
credential helpers. **Updates only reach users when the `version` field changes** for git sources that
declare one — so every release must bump it.

**Skills.** `SKILL.md` with YAML frontmatter. Useful fields beyond `name`/`description`:
`allowed-tools`, `disable-model-invocation`, `user-invocable`, **`context: fork`** (run in an isolated
subagent), `arguments`, `paths` (glob-gated auto-activation), `model`, `effort`. Description budget
~1,536 characters. Progressive disclosure via referenced files; `${CLAUDE_SKILL_DIR}` resolves the
skill's own directory, which is how the bundled scripts are invoked.

> **`context: fork` matters for this design.** Some work that would have needed a separate agent
> definition can be a skill that forks. Fewer surfaces, same isolation.

**Agents.** `agents/*.md` with `name`, `description`, and optionally `tools`, `disallowedTools`,
`model`, `permissionMode`, `maxTurns`, **`skills`** (preloaded into the subagent), `memory`,
`effort`, `isolation`, `color`. Plugin agents are scoped `plugin:agent`. Official guidance: create a
subagent for verbose, self-contained work with tool restrictions; use a skill when the work needs
back-and-forth in the main context.

**Hooks.** `hooks/hooks.json`, three nesting levels (`event → matcher → hooks[]`). Types `command`,
`http`, `mcp_tool`, `prompt`, `agent`. A `PreToolUse` hook denies with
`hookSpecificOutput.permissionDecision: "deny"` plus a reason, or rewrites the call with
`updatedInput`. Exit 2 blocks. Events used below: `PreToolUse`, `PostToolUse`, `Stop`.

**MCP.** `.mcp.json` at the plugin root. Use only for capabilities that genuinely need an external
tool.

**Validation.** `claude plugin validate ./plugin` (with `--strict`), `--plugin-dir` for local testing,
`/reload-plugins` to pick up edits without a restart.

Nothing proposed here relies on a deprecated or experimental mechanism.

---

## 2 · Proposed repository shape

One repository, one marketplace, one plugin.

```
factory-mjaso/
  .claude-plugin/
    marketplace.json                 name: novikontas-course-factory
  plugin/
    .claude-plugin/plugin.json       name: course-factory, version: 2.0.0
    CLAUDE.md                        the laws, one line each - kept small
    skills/
      course-factory/                router · hours · coverage · tablet contract
      course-module-ux/              one-page deck, screen inventory, run script, measurement
      course-module-ui/              the locked look
      course-task-ux/                trainee task screens
      course-visuals/                NEW - representation, animation, asset pipeline
      course-evidence/               NEW - knowledge-base retrieval, authority tiers, citation
      course-tablet-publisher/       publish to the two terminals and the shared repo
    agents/
      visual-sourcer.md
      evidence-retriever.md
      module-producer.md
    hooks/
      hooks.json
      guard_readonly.py  guard_generated.py  guard_git.py
      check_page_contract.py  check_diff_hygiene.py  remind_verify.py
    resources/
      tokens/       gb_tokens.css · tokens.json
      engines/      one canonical copy of every shared gb_* engine
      patterns/     pin overlay · stepped build · comparison grid · axis ladder
                    sourced curve · click-to-enlarge · non-advancing timer
      schemas/      programme.json · plan.json · course.json
                    _photo_meta.json · _figure_meta.json
      templates/    deck skeleton · task skeleton · handout skeleton
                    COURSE_BRIEF.md · factory-notes.md · DELIVERY_NOTES.md
                    IMAGE_BRIEF.md · Advanced Module Plan
    golden/
      INDEX.md                       pointers into the reference course, never copies
  tools/
    kb_builder.py                    the Docling extraction
    new-course.ps1                   scaffold a course project
  docs/                              this Phase 1 package
```

**`.claude-plugin/` holds only manifests.** Everything else is at the plugin root. That is the single
most common plugin mistake and it is worth stating in the repository.

---

## 3 · Skills — seven, and why each exists

The rule applied throughout: **if two responsibilities can cleanly belong to one skill, they do.**
Seven surfaces for a system this size is already at the upper limit; do not add an eighth without
removing something.

### `course-factory` — the entry point *(exists)*

**Why it exists:** a colleague types one sentence. Something has to decide mode, run the approval
gate and route. It also owns the rules that no other skill can own because they are about the course
as a whole: the hours law, ILO immutability, the 80/20-or-active-learning rule, and the build order.

**Owns:** the brief; the three modes (plan / ship / audit); the four laws; the gate table;
`build-order.json`; `delivery-contract.json`; `programme.json` and `plan.json`; hours and coverage
validators; the verification order; `factory-notes.md`.

**Change in Phase 2:** add step 8b routing to `course-visuals`, add `course-evidence` as the owner of
build step 3, and replace hard references to `novikontas-*` skills with graceful conditionals
(decision **D-3**).

### `course-module-ux` — how a module *behaves* *(exists)*

**Why it exists:** the one-page, Start-then-Next-to-the-end architecture is the whole delivery model,
and it is not obvious. Somebody has to own "if a block of the timetable has no screen, that block
does not happen" — a defect that silently dropped 90 of one module's 220 minutes.

**Owns:** the one-page architecture; the screen-inventory gate; the audience rule and the `data-cue`
channel; run-script generation from the deck's own markup; the measurement floor (contrast ≥ 4.5,
text ≥ 12.5 px, targets ≥ 44 px, fill, overflow) and the traps that make a clean report untrustworthy.

### `course-module-ui` — how a module *looks* *(exists)*

**Why it exists, in one measurement:** three of eight shipped modules run a second token dialect.
They all passed the UX floor. A floor is not an identity.

**Owns:** `tokens.json`; the two slide modes; header band, card, pill, photo, takeaway; semantic
correct / wrong / hazard colour; `audit_ui.py`; the record of known drift — which exists so nobody
"fixes" a signed-off deck on the strength of a lint rule.

### `course-task-ux` — how a trainee answers *(exists)*

**Why it exists:** a task screen has failure modes a deck does not — a keyboard that will not close, a
task that asks a trainee to record a number the screen never shows, a two-stage tap nobody discovers,
a completion state that differs between modules. Sixteen numbered sections, most added after a real
defect.

**Owns:** what a task screen may contain; how a trainee answers; navigation; typed input and escape;
tap-to-locate; two-stage tap; explicit completion; the measurable floor; "every number a screen states
must match the page".

### `course-visuals` — **NEW** — what a concept should *look like*, and where the file comes from

**Why it exists:** this is the stated reason for building the factory — to stop generic AI course
graphics — and no existing skill owns the decision. `course-module-ui` owns chrome; `course-module-ux`
owns geometry. Neither answers "should this be a photograph, a cutaway, an SVG animation, or one
sentence?"

Two lanes, one router:

**`design/`** — for each important concept, choose the strongest representation:
real photograph · annotated photograph · source technical drawing · manufacturer diagram · annotated
schematic · SVG visualisation · SVG animation · process animation · cutaway or section · interactive
equipment diagram · flow visualisation · before/after · cause/effect sequence · timeline · Canvas ·
generated illustration · **or plain text when a visual adds nothing**.

Carries the laws: an animation must explain a mechanism, state change, relationship, flow, sequence or
cause/effect — decorative movement is not sufficient; explain first then show; a drawing declares on
its face that it is a drawing; a value interpolated inside a sourced chart is marked; the visualisation
is a named engine with its source cited in the code, following Module 1's G1–G5 pattern.

**`source/`** — the four-step hierarchy, in order:
1. `source_files/` and the project's own supplied assets
2. the factory's approved visual library (`resources/`)
3. the internet, preferring manufacturers, official organisations, manuals and recognised maritime
   sources — CC0 / CC BY / CC BY-SA / public domain only
4. create it — SVG, HTML/CSS/JS, Canvas, a programmatic diagram, or an image-generation MCP when a
   real illustration is genuinely needed

Plus: provenance schemas, the licence rule, `visually_verified`, naming/format/size, "never contradict
named kit", "caption a near-miss honestly", and rights escalation (a publisher figure that is not
cleared is named and stopped, never quietly used).

**Claude stays the art director.** A generated image never replaces a diagram that would be more
accurate as SVG or HTML.

### `course-evidence` — **NEW** — NO SOURCE = NO MARITIME CLAIM, for any subject

**Why it exists:** the strongest rule in the system currently lives in a project-local, GAS-BASIC-only
skill. Every accredited course needs it, and the escalation ladder is subject-independent.

**Owns:** the authority tiers (programme → mandatory instruments → model course → conventions and
codes → own-equipment manuals → industry guidance → legacy material) and the rule that a tier is never
upgraded; the four-level escalation (KB chunks → a bounded line range of `content.md` → the original in
`source_files/`, read-only → external, labelled `EXTERNAL — NOT FROM KNOWLEDGE BASE`); check the
edition on the cover page; the citation format; `GREEN` / `YELLOW` / `RED`; the honesty markers
`UNKNOWN` / `PLACEHOLDER` / `PROVISIONAL` / `[VERIFY: …]`; and the rule that a `content.md` over about
a megabyte is never read whole.

**Also owns the knowledge-base build recipe** by pointing at `tools/kb_builder.py`. Building the KB is
a script, not a procedure worth a second skill.

### `course-tablet-publisher` — getting it onto the tablets *(exists)*

**Why it exists:** publication is where a course can leak an answer key to a trainee tablet, commit a
credential, or stage a colleague's half-finished work. It is rails, not reasoning, and it must never
be able to change what a course teaches.

**Owns:** the eight-check gate; trainee / instructor / shared / internal classification; the registry
generator; the git rails; `platform.json`; the pack contract.

**Change in Phase 2:** raise the remote-font check to `FAIL` for **new** courses (the app returns 403;
see the Android contract), keep it a warning for GAS BASIC so the working course stays publishable.

---

## 4 · Agents — three

Full reasoning in `FACTORY_RULE_CLASSIFICATION.md` §3.

| Agent | Preloaded skills | Tools | Why |
|---|---|---|---|
| `visual-sourcer` | `course-visuals` | Read, Glob, Grep, WebSearch, WebFetch, Write (scoped to `assets/`) | Bulk sourcing is verbose, reads many pages, and returns one report. The golden course already ran it exactly this way and it worked. |
| `evidence-retriever` | `course-evidence` | Read, Glob, Grep, Bash (`kb_search.py`) — read-only | Keeps 1.4 MB `content.md` files out of the main context. Answers one question, returns a citation. |
| `module-producer` | `course-module-ux`, `course-module-ui`, `course-task-ux`, `course-visuals` | full, scoped to one module folder | One module is a long self-contained run, and fan-out worked on GAS BASIC. **Gated:** only after the visual system is frozen as one shared tokens file, and the UI audit runs per agent before merge — parallel module agents are how the recorded visual drift happened. |

No agent for verification (the main thread must read the output), the gate (it is the owner
conversation), or publishing (rails).

---

## 5 · Hooks — one file, six scripts

Listed with evidence in `FACTORY_RULE_CLASSIFICATION.md` §4.

- `PreToolUse` **deny** — writes into the reference course, `source_files/`, `knowledge_base/`, or the
  Android project outside an authorised publish
- `PreToolUse` **deny** — writes to a generated file (`it_run.js`, `registry.js`, `gb_tasks.js`)
- `PreToolUse` **deny** — `git push --force`, a push to the app repo's default branch, `git add -A`
  inside the app repo
- `PostToolUse` **warn** — the page contract: remote resources, non-HTML navigation targets,
  `target="_blank"`, `window.open`, `<input type="file">`, a missing back hook, an `<a href>` inside a
  slide
- `PostToolUse` **warn** — diff hygiene: a diff much larger with whitespace than without
- `Stop` **inform** — course files changed and no verification script ran

Deny hooks read an `allow_publish` marker the publisher sets, so authorised publication is possible
and accidental writes are not.

---

## 6 · MCP — one candidate, and three deliberate refusals

**Candidate: an image-generation MCP server.** Only for step 4 of the sourcing hierarchy, only when a
*realistic illustration* is genuinely the right representation, never for a technical diagram that
would be more accurate as SVG, and never for a photorealistic depiction of safety-critical equipment.
Every generated file carries `origin: generated illustration`, `generated_by`, and
`depicts_what_no_photograph_can`. **Optional** — GAS BASIC's illustrations were produced in-session as
SVG + PNG and that route is cheaper and more accurate for most technical subjects.

**Not proposed:**
- *A browser MCP for measurement.* The session already has a browser tool, and the in-page probes
  (`audit_deck.js`, `audit_collide.js`, `audit_opacity.js`, `measure_in_page.js`) already exist. Real
  engine measurement is mandatory — static analysis produced a falsely clean contrast report — but it
  needs no new server.
- *A GitHub MCP.* `git` plus a printed compare URL works today; `gh` is not installed on the owner's
  machine and the publisher already accounts for that.
- *A Supabase MCP.* The classroom backend is not the factory's concern.

---

## 7 · Resources, templates and golden references

`resources/` in §2; the full inventory is `FACTORY_RULE_CLASSIFICATION.md` §5.

Two points worth stating as policy:

**Shipping one canonical copy of each shared engine is itself a fix.** `gb_done.js` exists today as
five identical per-module copies, and a copy goes stale the first time the engine is fixed.

**`golden/INDEX.md` holds pointers, not content.** Named paths into the reference course with what
each demonstrates. **No course content, no photographs, and never the ICS/SIGTTO figures** — six of
them are marked *NOT cleared for issue or publication* and currently block the course itself from
being issued.

---

## 8 · What a colleague experiences

```
/plugin marketplace add silkansraivis3-tech/factory-mjaso
/plugin install course-factory@novikontas-course-factory
```

Then, in a folder holding `source_files/`, a built `knowledge_base/`, and the approved programme:

> "Create this course. Make it highly practical. Module 3 should include an interactive transfer
> exercise and I want a strong animated system explanation."

What happens, with no skill named and no agent chosen:

1. `course-factory` triggers on the request, extracts what it can from the brief, and asks only for
   what is genuinely absent — batched, two to four questions at a time. The one blocking question is
   *which approved programme governs*.
2. It transcribes the hours table, the model-course syllabus and the ILO map, proposes a module split,
   and **stops at the gate** with one table: programme, split, minutes, ratio, per-module shape,
   markers. Nothing is built until that table is approved.
3. After approval, the build order runs: screen inventory → visual system → **visual plan** → task
   pages → screens → handout → assessment → module plans → terminals → verify.
4. "A strong animated system explanation" reaches `course-visuals`, which decides the representation
   and applies the animation law. "An interactive transfer exercise" reaches `course-task-ux`, which
   picks a mechanic the neighbouring modules do not already use.
5. Every maritime claim goes through `course-evidence`; anything unsupported becomes a marker, never a
   plausible sentence.
6. Verification runs, the output is read, and `factory-notes.md` records what was produced, every
   marker with its source, the achieved ratio, and what moved to the handout.
7. "Publish it to the tablets" reaches `course-tablet-publisher`, which gates, registers, branches and
   prints a pull-request URL — and says plainly that published is not installed.

The colleague never types a script name, never chooses an agent, and never learns what a hook is.

---

## 9 · Decisions needed before Phase 2

| | Decision | Recommendation |
|---|---|---|
| **D-1** | Does `factory-mjaso` **supersede** `course-factory`, or sit beside it? | Supersede. Two repositories holding the same skills will diverge, and the existing repo has no plugin manifest at its root for `/plugin marketplace add`. Freeze `course-factory`, migrate, and point its README here. **Colleagues who already installed by file copy must be told once** — the old copies in `~/.claude/skills/` will shadow nothing but will go stale. |
| **D-2** | One plugin or several? | **One.** The seven skills share `build-order.json`, the token set and the platform description. Splitting them means versioning six things in lockstep. |
| **D-3** | The `novikontas-*` dependency. Four required build steps are owned by skills that are not in the plugin and reach this machine through a different channel. | Publish the `novikontas-*` family through the same marketplace as a second plugin, so `course-factory` can declare a real dependency. Until then, make each reference conditional: use the org skill if present, otherwise fall back to a short in-plugin section, and **say which happened** in `factory-notes.md`. Do not duplicate the org skills into this plugin — a copy goes stale silently. |
| **D-4** | Where does a deck live, and must the tablet be able to open it? | Owner's call. Today the decks are in the desktop course tree only, the instructor terminal describes them, and the tablet cannot open them. If that is intentional, write it into `delivery-contract.json`. If not, it is a packaging change. |
| **D-5** | Raise the remote-font check to `FAIL`? | Yes, for new courses; keep it a warning for GAS BASIC so the working course stays publishable. The app returns 403, so this is not a degradation question. |
| **D-6** | Is `gb_tasks.js` generated or authored? | Decide and write it in the header. It currently claims both. |

---

## 10 · Suggested Phase 2 sequence

Not part of this deliverable — recorded so the review has something to react to.

1. Scaffold the plugin and marketplace in this repository; migrate the five proven skills unchanged;
   `claude plugin validate --strict`; install from the marketplace and confirm the seven surfaces load.
2. Write `CLAUDE.md` from §1 of `FACTORY_RULE_CLASSIFICATION.md`.
3. Build `course-visuals` — the largest genuine gap, and the stated reason for the factory.
4. Build `course-evidence` by generalising `gas-basic-kb-retrieval`.
5. Add `hooks/hooks.json` and its six scripts.
6. Add the three agents.
7. Consolidate `resources/` — one canonical engine set, the token file, the schemas, the templates.
8. **Prove it on one real module of a second course**, end to end, and only then declare v2.0.0.

Step 8 is the acceptance test. A factory that has only ever built the course it was extracted from has
not been shown to be a factory.
