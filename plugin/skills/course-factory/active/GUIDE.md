# Theory taught as activity — the factory proposes, the operator keeps or strikes (L49, step 3)

Read this lane at Stage 2, when the architecture is written or corrected. The patterns are
`knowledge/active-learning.json`; the page is `scripts/make_architecture_page.py`; the decisions are
recorded with `scripts/active_plan.py`.

**Why (owner, 2026-10-15):** the programme stays 80/20 on paper; in class we aim at 20/80. Theory
that can be taught as a task, an interactive activity or active learning should be — *but first the
person who uses the factory reviews it.* That person knows almost everything about ships and almost
nothing about IT.

## 1 · Write the proposals

For every programme sub-topic that carries theory, add at least one line to that module's
`active_learning` in `working_claude/architecture.json`:

```json
{"id": "A1.1", "subtopic": "1.1", "technique": "explore", "status": "proposed",
 "does": "Each trainee opens the four tank types in the 3D hull section and finds which one leans on the hull.",
 "instead_of": "the slides on tank types stay - the instructor goes through them in 5 minutes instead of 15",
 "minutes": 10, "needs": "nothing - the factory builds the 3D model"}
```

- **`does`** — what the trainees *do*, one or two plain sentences, in the operator's language. No
  technique names, no tool names. This is the line the operator reads and decides on.
- **`technique`** — one of the patterns in `knowledge/active-learning.json` (it decides how the
  minutes count). If a sub-topic is better left plain, say so: `"technique": "plain"` with `"why"`.
- **`minutes`** — taken from that sub-topic's plain theory, never from practice. **The slides stay**
  (`instead_of` says how much faster the instructor goes); theory is never removed.
- **`needs`** — what the factory cannot make alone: a photo of the real panel, the simulator, a piece
  of equipment, a team of three. Empty when the factory makes everything.
- **`id`** — `A<module>.<n>`, never reused. Status starts `proposed`.

Choose the pattern by what the theory *is*: a process → predict-then-reveal; a reason → explain-then-
reveal; numbers → worked example; a decision → scenario; something with a shape or an inside → explore.
Aim at the module reaching about 80 % active with everything kept — but propose only what really
teaches better; never an activity for its own sake.

## 2 · The operator decides on the page

`make_architecture_page.py` shows every proposal under its module with two big buttons, **Keep** and
**Strike**, and a box at the top: *waiting for your decision*, the class split now and *if you keep
them all*. Their ticks stay in their browser; **Copy my choices** puts a plain line on the clipboard —
"Keep: A1.1, A1.2. Strike: A2.1." — for them to paste into the chat. They may also just say it, or
print the page and tick on paper.

## 3 · Record what they said — and only that

```
python scripts/active_plan.py list   --course <course>      # waiting, and sub-topics with no proposal
python scripts/active_plan.py decide --course <course> --keep A1.1,A1.2 --strike A2.1 --said "<their words>"
```

`decide` sets each status, logs the operator's words in `FEEDBACK_LOG.md`, and re-renders the page.
A struck proposal stays in the file, marked struck — never deleted, never proposed again for that
sub-topic unless they ask. If they want a proposal changed rather than kept or struck, change it, keep
it `proposed`, and show the page again.

**Before recording the operator's "next" for Stage 2, every proposal is decided.** Ask about the ones
still waiting — in one short list. A proposal left waiting is not built.
