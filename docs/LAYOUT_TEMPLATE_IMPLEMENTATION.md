# Implement the owner-reviewed layout templates

Owner-reviewed design handoff, 2026-10-20. Baseline examined: `0f8d252f5a9d3321959e4c394085d2b003fa1b8d` (`course-factory` context says 2.51.0). This change adds references only. **No compiler integration, course migration or live classroom fix has been implemented.**

Start with [`design/course-layout-templates/README.md`](../design/course-layout-templates/README.md) and open its `preview.html`. The source of truth for the latest appearance is the checked-in HTML/CSS and generators, not an earlier discussion or the initially denser specimens.

## Owner requirements

1. Use concrete reusable HTML/CSS templates with machine-readable JSON contracts. AI chooses a suitable template/variant and supplies source-bound content; it does not invent arbitrary slide structure or override shared layout CSS.
2. Reserve **50–60% for text and 40–50% for visuals** in the information-heavy split layouts; the selected default is 55/45. The owner rejected the earlier 80/20-like layouts and their excessive copy. Keep the actual teaching image/model large within the visual region, not a small object in a large empty container.
3. Short content may use a text-only composition. Reject a course sequence containing **three consecutive projected slides without a meaningful teaching visual**. This applies to the course's actual projected order, not the ordering of templates in this gallery. Logos, borders, navigation buttons, small decorative icons and gradients do not count as teaching visuals.
4. Dense information always has a relevant image, diagram, animation, interactive element or rotatable 3D object beside it. This is a compiler contract, not merely a prompt preference. Decide and document density classification with the owner; there is no newly approved universal word limit.
5. When wording needs more room, preserve it in readable parts or use another valid composition. Do not quietly truncate, summarize, remove an image, reduce type below existing reading floors or switch to an 80/20 split. Any source wording change still follows the factory's existing propose/apply/approve process. The shorter text in these design specimens is sample copy, not a migration of an approved course.
6. Controller preview and projector should ultimately use one logical presentation stage, proportionally scaled. The reference uses **1280×800**, bundled Raleway and no remote assets. Fonts and controls must be ready before final measurement.

The selected single-view examples currently contain approximately 85–135 visible words, including specimen labels; the three-part example contains approximately 281 words in total. These values describe the examples and must not become arbitrary content caps.

## Scope of the files

- `design/course-layout-templates/preview.html`: authoring gallery with screen-ratio simulation, content modes and local feedback. It is not classroom UI and must not ship as a trainee page.
- `.../template-preview/templates/<id>/template.html`: standalone structural reference with `data-slot` annotations and sample text.
- `.../template-preview/templates/<id>/template.json`: proposed versioned template contract, required slots and owner policy metadata. It is not yet a supported build-sheet schema.
- `.../template-preview/assets/template.css`: reference appearance. Port relevant rules into the existing canonical design system; do not create an uncontrolled second style authority.
- `.../template-preview/assets/preview-runtime.js`: demonstration of discrete steps, three-part content, animation play/pause and an interactive projected 3D model. It does not implement classroom synchronization.
- `.../template-preview/build_preview.py` + `dense_templates.py`: regenerate the references deterministically.
- `.../template-preview/course-layout-rules.json`: proposed owner policy metadata, explicitly marked not compiler-enforced.
- Local font + OFL licence; generated ship JPEG with the generation prompt recorded in the preview README.

The folder is deliberately outside `plugin/resources/`: that directory participates in the asset discovery pipeline. Illustrative content should not be accidentally offered as approved course material. No existing engine was moved, and this reference-only handoff does not bump the plugin version. Follow the repository's release/versioning rules when implementing runtime changes.

## Implementation route

Read the current `_claude/CONTEXT.md`, Phase 5 decisions, laws and owning skill guides before making the production change. Keep existing proven checks and source-approval protections.

### 1. Define a real template contract

Introduce versioned template IDs, supported variants and typed slots in the factory's existing design system. Choose one canonical owner for HTML structure, tokens and layout CSS. Validate required media, supported media kinds, controls and reserved space for captions/credits before rendering. Reject unknown template IDs and incompatible build options with the module and slide ID.

An illustrative future build-sheet entry is:

```json
{
  "template": "long-explanation.v1",
  "variant": "text-left",
  "figure": "s04.kit.json"
}
```

This is a proposal, not an already implemented input format. The compiler should obtain wording from the approved content script. Define how slots bind to source lines/paragraphs; preserve source attribution and `data-script-field` checking. The preview JSON is descriptive and should be formalized before trusting it as a production schema.

### 2. Integrate the existing compiler and shared styles

Likely integration points, verified on the baseline:

- `plugin/skills/course-factory/compile/scripts/compile_module.py`: `composition()` and `slide_html()` currently select/emit layouts; `recap_html()` is an existing example of one fixed shared structure.
- `plugin/skills/course-module-ui/templates/gb_compose.css` and the canonical token/shell files: preserve one authoritative style system.
- `plugin/skills/course-module-ui/scripts/design_system.py`: install/check canonical assets and protect intentional owner overrides.
- `plugin/skills/course-factory/compile/scripts/build_module.py`: integrate validation with the current build, drawing, wording, navigation and package checks.

Keep legacy rendering available for existing courses until an explicit migration. Resolve conflicts between a selected template and `composition`, `inset`, `aside`, automatic photo strips or legends before rendering. Do not silently discard required photos, credits or an existing owner decision. If a required extra cannot fit a template, choose a supported variant or report the conflict.

Use source-bound content parts for the paged template and maintain a clear active-part state. Every approved part must be reachable and reviewable. A gallery demo is not proof that `GBDeck.next()`, a figure's step hooks and the classroom controller all advance the same part; integrate those paths deliberately.

### 3. Enforce owner rules

Validate the actual projected sequence and detect a third consecutive slide without a relevant visual. Validate the dense-content visual requirement independently; adding a decorative icon must not bypass it. Keep supported owner override handling consistent with the current design-choice system, making any conflict explicit.

Measure rendered content after fonts/media/controls settle. Keep the selected split inside the owner's 50–60 / 40–50 ranges. Test the figure's visible size as well as its panel. Report overflow with slide ID, region and viewport. Existing geometry/compose/drawing probes and visual review stay required.

### 4. Keep mirroring a distinct integration concern

The actual classroom `/display` implementation was unavailable to this investigation. **There is no proven root cause or shipped fix for the reported button 2/button 4 mismatch.** The following are implementation checks, not findings that can be claimed as resolved:

- Give preview and projector one logical iframe/stage size before scaling. A fixed outer `div` alone does not stabilize existing `vw/vh/vmin` CSS inside differently sized frames.
- Send stable control identity and absolute target state (`slideId`, `partId`/step, control ID, package revision and event ID), not a raw screen position or an ambiguous displayed ordinal. Include acknowledgement and repeated-event handling in the classroom integration.
- Reconcile slide, figure step and content part on connection/reconnection. Version mismatch and stale actions must be detected instead of replayed onto another slide.
- Factory options are already shuffled deterministically in `task_pages.py`; `gb_answer.js` assigns displayed letters in DOM order. Source option identity and displayed label must not be confused.

The preview's local model rotation and animation buttons do not satisfy this remote-state protocol. Confirm the actual classroom contract before changing its behavior. Keep independently answered trainee tasks distinct from the instructor's projector control.

## Acceptance checks for Claude's implementation

- Same approved source and build sheet produce the same output, using pinned template/tool versions.
- Missing required media, unknown template and incompatible options fail clearly.
- Two consecutive text-only slides are allowed; a third is rejected. A dense slide without a meaningful adjacent visual is rejected.
- Dense split geometry respects 50–60% text / 40–50% visual with a large readable figure and controls.
- Long source text is preserved across content parts; all parts are reachable through the intended deck and controller navigation.
- At 1280×800 and 1024×768, title, paragraphs, image/model, credit, part navigation and deck chrome do not overlap. Also test the actual classroom iframe dimensions when available.
- Every part and relevant figure step is inspected. Animations, keyboard/touch controls and reduced-motion behavior retain usable content.
- Existing wording, design-system, drawing, navigation, task grading, instructor/trainee separation and package checks pass.
- Browser and real-device checks distinguish a successful layout build from an untested live `/display` integration.

Use one pilot module to establish the production contract before migrating other courses. Produce a reviewable change and follow the repository's existing release/version process.

## Prompt to give Claude

> Implement the owner-reviewed layout template system described in `docs/LAYOUT_TEMPLATE_IMPLEMENTATION.md`, using `design/course-layout-templates/preview.html` as the visual reference. First read the current repository context and owning skill guides. Preserve approved content and existing factory protections. The final selected balance is 55% text / 45% meaningful visual (allowed 50–60 / 40–50); dense text always has a visual beside it, and no course may have three consecutive projected slides without one. Use named versioned templates and supported variants rather than per-slide layout CSS. Integrate with the current compiler and canonical design system, starting with one pilot module. Do not copy the gallery's sample text, generated ship image or demo controls into production courses. Implement and validate the template contracts, content-part navigation and sequence rules. Keep `/display` synchronization work explicit: this handoff contains a proposed direction, not a verified classroom fix. Report what is implemented, how it was checked and what still needs the actual classroom code or device validation.
