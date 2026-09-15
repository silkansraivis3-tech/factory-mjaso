# <MODULE> — visual notes

*Written by `course-visuals` during the run, into the module folder. Never left for a human to
fill in. The honest record of what was built, what was not, and what somebody must still decide.*

**Run** <YYYY-MM-DD> · **Module** <n, title> · **Storyboard** <path, approved date>

---

## 1 · What was built

| # | Concept | Learning need | Representation | Technology | Verdict |
|---|---|---|---|---|---|
| | | | | | PASS / REWORK / REJECT / BLOCKED |

**The one-sentence test**, per figure — *"after this, the learner can ___, which they could not
before."* If that sentence cannot be finished for a figure, take the figure out and say here what
the screen needs instead.

| # | After this, the learner can… |
|---|---|

---

## 2 · Decided as plain text

Concepts given no visual, and why. An omission looks like an oversight; a recorded decision does
not.

| Concept | Why text carries it better |
|---|---|

---

## 3 · Assets, with provenance

| File | Level | Source | Rights state | Visually verified | Caption caveat |
|---|---|---|---|---|---|

- Metadata files written: `_photo_meta.json` / `_figure_meta.json` at <paths>
- Remote assets downloaded and packaged locally: **yes / none used**
- `check_assets.py` verdict: <paste the line>

### `RIGHTS_REVIEW_REQUIRED`

Blocks shipping. The owner decides, not the factory.

| Picture, drawing or photograph | Why the rights are unclear | What would clear it |
|---|---|---|

### `GENERATED_ASSET_REQUIRED`

| Asset | Learning need | Brief written to | Why no existing asset served |
|---|---|---|---|

---

## 4 · Animations

| Name | Category | What changes | Why | Notice | Understand afterwards |
|---|---|---|---|---|---|
| | teaching / affordance / ambient | | | | |

- Controls present and ≥ 44 px: <yes / list exceptions>
- Resting state readable with motion stopped: <yes / list exceptions>
- Pauses off-screen: <yes / list exceptions>
- `prefers-reduced-motion` honoured: <yes / list exceptions>
- Ambient effects per screen (budget 1): <max observed>

**Motion removed during the run**, and why — the useful half of this section:

| Where | What it was | Why it went |
|---|---|---|

---

## 5 · Variety

| | |
|---|---|
| Distinct representations used | |
| Longest run of the same mechanic | |
| Justified repeats | |

---

## 6 · Verification

| Check | Verdict |
|---|---|
| `scripts/check_visuals.py` | <paste the summary line> |
| `scripts/check_assets.py` | <paste the summary line> |
| Human review, 14 questions | <findings, or "no findings"> |
| Read on the tablet, landscape | |
| Read on the tablet, portrait | |

A green exit is not proof. Say which figure you actually looked at.

---

## 7 · Markers

Write every marker down here, with who answers it and what happens to the course until they do. A
marker used and never written down is the failure this section exists to stop.

| Marker | What | Why |
|---|---|---|
| `UNKNOWN` | | |
| `PLACEHOLDER` | | |
| `PROVISIONAL` | | |
| `[VERIFY: …]` | | |
| `RIGHTS_REVIEW_REQUIRED` | | |
| `GENERATED_ASSET_REQUIRED` | | |

---

## 8 · What was NOT done

Gaps and why — waiting on a picture, waiting on a decision about who owns one, waiting on a
photograph somebody has to go and take. For each gap say what it means for the class and what would
close it. Where the factory can close it, offer to. An unreported gap becomes a surprise in a
classroom.

---

## 9 · Feedback on this skill

*The improvement loop. The only channel through which real use reaches the skill.*

- A learning need that did not fit any of the fifteen
- A representation that was needed and is not in `representations.json`
- A check that fired on something correct, or missed something wrong
- A rule that turned out not to apply to this subject, and why
