# Course layout reference library

> **Implemented in `course-factory` 2.52.0 (L61, owner 2026-10-20: "all slides for all modules ... in this style, it's
> a RULE").** Production contract: `plugin/skills/course-module-ui/knowledge/layout-templates.json`; look:
> `plugin/skills/course-module-ui/templates/gb_layouts.css` (brandbook colours, the official logo, Raleway bundled);
> the compiler names every slide's template. This folder stays the design reference.

13 inspectable HTML layout specimens, reviewed with the owner on 2026-10-20. The latest revision uses approximately **55% text / 45% visual** for the five information-heavy layouts, with shorter sample copy. This is a design reference and implementation handoff, not a compiler integration or a plugin release.

Open [`preview.html`](preview.html) in a browser. To serve it locally from the repository root:

```sh
python3 -m http.server 8765 --bind 127.0.0.1
```

Then visit `http://127.0.0.1:8765/design/course-layout-templates/preview.html`. GitHub's file viewer displays HTML source; download/clone the branch to run the gallery. Fonts, scripts and images are bundled locally; the gallery makes no external resource requests.

- [Claude implementation brief](../../docs/LAYOUT_TEMPLATE_IMPLEMENTATION.md)
- [Ready-to-use Claude prompt in Latvian](CLAUDE_PROMPT_LV.txt) and [Windows instructions](WINDOWS_README_LV.md)
- [Catalogue](template-preview/catalog.json)
- [Owner's course layout rules](template-preview/course-layout-rules.json)
- [Detailed preview notes and image provenance](template-preview/README.md)

## What the owner selected

- AI selects a named template and a supported variant. The compiler owns structure and CSS.
- Information-heavy layouts reserve **50–60% for text and 40–50% for a relevant visual**, default 55/45. Larger text volume is handled with readable parts, not an 80/20 text/visual split.
- Short text may use a text-only composition. A course must never have more than **two consecutive slides without a meaningful visual**.
- Dense text must have a meaningful image, diagram, animation, interactive visual or rotatable 3D object beside it.
- Keep the diagram/image/model itself large inside its allocated area; a large empty panel does not satisfy this intent.
- Preserve all approved source wording. Sample copy was shortened during design review; production course content still follows the existing approval process.

## Contents

`template-preview/templates/<id>/template.html` is a real standalone page containing the specimen structure and `data-slot` markers. The adjacent `template.json` is a **proposed** contract. `assets/template.css` owns the shared preview appearance; `assets/preview-runtime.js` owns demo interactions. `preview.html` and the gallery scripts are authoring tools, not trainee pages.

The first eight templates cover explanation/figure, figure stage, photograph/explanation, comparison, procedure, task launch, recap and opening. Templates 09–13 cover longer explanation with a model, three text blocks with animation, a table with animation, text with a large diagram and one topic in several parts with a model.

Rebuild and check the specimens:

```sh
python3 design/course-layout-templates/template-preview/build_preview.py
python3 design/course-layout-templates/validate_preview.py
```

The source generators are `build_preview.py` and `dense_templates.py`; rebuilding overwrites generated pages, catalogues and contracts. The validator checks local links/assets, declared slots, owner-rule metadata and deterministic regeneration. It does not prove browser layout or implement course sequence validation.

## Validation already performed

- Browser inspection of the gallery and all five revised dense compositions at a 1280×800 logical slide size: 611px text + 509px visual + 32px gap, approximately 55/45 of the two content regions.
- Default dense examples fit the geometry check, at approximately 85–135 visible words per view. These are examples, not a universal word cap.
- All three parts of the paged specimen were checked; rotation and animation controls were exercised.
- Relative resource/slot checks, JavaScript syntax checks and regeneration checks are provided with the handoff.

Physical tablets, live `/display` mirroring, browser-version differences and direct `file://` loading were not validated here. The automated browser allowed HTTP(S) previews but blocked `file://` navigation.

The preview contains modern JavaScript and authoring-only controls. Adapt production rendering to the factory's existing compatibility, navigation, asset provenance and package contracts. The generated ship picture and illustrative model are design assets, not cleared technical training evidence.
