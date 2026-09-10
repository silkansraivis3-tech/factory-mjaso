# Coverage — is everything the programme AND the model course ask for actually taught?

Read this lane when the mode is **audit**, or before you claim a built course is complete.

Two documents govern content, and they are not the same document.

| | gives you | governs |
|---|---|---|
| the accredited **Study Programme** | topics, hours per topic, the ILOs | **the hours. Always.** |
| the **IMO model course** behind it | the itemised outcomes under each topic | the content, as guidance |

The programme's topics are coarse. The model course's own detailed syllabus — its *Knowledge,
Understanding and Proficiency* column — is where the outcomes are itemised, and those items are
the sub-ILOs in everything but name. **A course can cover every programme topic and still miss
individual outcomes inside them.**

That is not hypothetical. On GAS BASIC the topic-level record was green at 64 of 64 and did not
mention the model course once. Checking 1.04's own 266 outcomes found one real gap —
decontamination showers and eyewash on deck, item 9.2.7 — present in no screen, no task, no
document, no handout and no assessment question. One in 266 is a good result, and it was
invisible at topic level.

---

## 1 · Transcribe the model course's syllabus first

`coverage/scripts/check_syllabus_coverage.py --syllabus <file>` needs this shape:

```json
{ "source": "IMO Model Course 1.04",
  "items_by_topic": {
    "1": [ {"id": "1.0",   "requirement": "BASIC KNOWLEDGE OF LIQUEFIED GAS TANKERS (3 hours)"},
           {"id": "1.1.1", "requirement": "States that liquefied gas tankers are categorized ..."} ],
    "2": [ ... ] } }
```

One entry per row of the model course's syllabus table, its own numbering as `id`. Headings and
hours notes stay in — the script counts them separately and never treats them as gaps.

**Transcribe, do not summarise.** The point of the check is that the wording is the model
course's own; paraphrasing it into your own words is how you fail to notice a gap.

## 2 · Run it against everything a person can read

```bash
python <skills>/course-factory/coverage/scripts/check_syllabus_coverage.py \
  --syllabus syllabus.json \
  --course course --course app/src/main/assets --course app/src/instructor/assets \
  --resolved coverage/resolved.json --out coverage/imo_coverage.json
```

Screens, tasks, documents, practicals, the handout, the assessment, the instructor guides. If an
instructor says it out loud from a cue, it is taught.

## 3 · A verdict is a POINTER, not a proof

    covered   every distinctive word of the outcome is somewhere in the course
    review    some present, some not — READ IT and decide
    MISSING   almost nothing present; the likely real gaps

**This kind of search over-reports misses. Always.** Work the `review` list by hand, searching
for the **concept** rather than the model course's phrasing. Four reasons it over-reports, all
seen on one course:

- **A good course teaches in its own words.** GAS BASIC's screen for *"effect of pollution on
  people and marine organisms"* says *"what it does to people, and what it does to the water"* —
  better teaching, and invisible to the programme's phrasing.
- **The model course's extracted text is damaged.** These PDFs carry tracked changes, so
  requirements arrive as *"DescribesExplains"*, *"fFlammable vVapours"*, *"Identifiesy isplays"*,
  *"areis"*, *"aApplicator"*. Those tokens can never match anything. **14 of 32 review items on
  GAS BASIC were this**, and the script flags them as `source text damaged` so you do not go
  looking for teaching that was never missing.
- **Spelling.** Model courses are written in American, maritime courses often in British. Until
  `-ize` and `-ise` were folded together a dozen taught outcomes read as absent. The fold is built
  in.
- **Figure captions.** An item that is a caption and an image path is not an outcome.

Record every hand resolution in the `--resolved` file with the evidence, so the next run does not
ask again:

```json
{ "9.2.7": "closed 2026-09-07: decontamination showers added to the M5 handout, ICS TSG cited",
  "12.2.2": "heavier than air x79, flash back, ignition - M7 s7; requirement text damaged" }
```

## 4 · What the corpus must and must not contain

The script reads only what a person can read: it strips `<script>` and `<style>`, drops `data:`
URIs, skips duplicate single-file builds, and throws away tokens that are not words.

**This matters in the direction that hurts.** Left unfiltered, one course gave **520,000 distinct
"words" from 16 MB** — minified code and base64 image data. Against a vocabulary that large almost
any requirement scores as covered, and **a real gap hides**. Filtered, the same course gave 4,349
stems from 2.8 MB. If the run reports a suspiciously large stem count, believe the count and not
the coverage.

## 5 · Closing a gap

A genuine gap in an accredited course is not a documentation problem. Either **teach it** or
**remove it from the claim** — there is no third option.

Teach it where the outcome belongs, in the module carrying that topic, and **quote the source**.
Do not write it from memory: find it in the course's own reference material, put the citation on
the page, and say which section. On GAS BASIC 9.2.7 went into the Module 5 handout section that
carries topic 9, with three citations from the ICS Tanker Safety Guide — the cargo data sheets'
*personal protection* column, §3.11.3 and §2.8.3 — and tied the item to where a crew actually
meets it.

## 6 · The topic-level check is still worth having

This lane does not replace a per-topic record — module against topic, with the evidence route for
each (on screen · in a task · in a practical · in a document · in the handout · assessed). Keep
both: the topic record proves the programme is delivered, this one proves the outcomes inside the
topics are.

**And they are counted differently.** Where the two disagree on a number, check what each is
counting before calling either wrong. One course's deck said *six tank types* and its handout said
*five containment systems*; both were right — the Code groups five systems, one of which has three
types, and the deck was counting leaf types and omitting the one nobody builds. The fix is to say
which you mean, not to change a number.
