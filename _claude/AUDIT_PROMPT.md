# Audit prompt - Course Factory (reusable)

Audit `silkansraivis3-tech/factory-mjaso` (local clone: this folder, `main`) together with the tablet
system it publishes to (`novikontas-training-app`, local clone `C:\Users\aleksisv\Desktop\novikontas-training-app`).
Read-only: change nothing in either repo except writing the report.

**Goal:** a ranked list of improvements that make the factory cheaper and faster to run, produce
better decks and trainee tests, and hand courses to the tablets with zero manual fixing.

## Four lenses - for each, evidence first (file:line, a measured number, or a test run), then the fix

1. **Cost & performance** - tokens loaded per mode (SKILL.md, references, CONTEXT.md, GUIDEs a
   module agent reads), skill descriptions and triggering overlap with the `anthropic-skills:novikontas-*`
   skills, model/effort choice per step, build wall-clock and $ per module (use the M01 benchmark
   METRICS where they exist), nano-banana / Gemini picture cost, redundant check runs, test-suite runtime.
2. **Deck quality** - the engine (`gb_deck.js`, `gb_compose.css`, kit), compiler, audits: what a
   trainee/instructor would still see wrong; laws that contradict or duplicate each other (L1-L60);
   rules enforced only in prose vs in code; real-photo use (owner rule).
3. **Test (assessment) quality** - task engine `gb_answer.js`, `task_pages.py`, answer key,
   module check / final: grading correctness, Bloom spread, distractor quality, cheating/shuffle,
   pass marks, accessibility at 1280x800 and 1024x768.
4. **Tablet integration** - `docs/ANDROID_INTEGRATION_CONTRACT.md` and `course-tablet-publisher`
   vs what the Android app and backend actually read and send (course.json / importer, result
   messages, `gb-team`, OPEN TASK, branches staging/master, `update-tablets`). List every
   mismatch, every "proposal the classroom app must confirm" still unconfirmed, and what breaks
   silently.

Also: repo hygiene (committed build junk, stale status lines, doc sprawl), test suite health (run it).

## Output

- Top 10 actions ranked by impact ÷ effort, each: problem, evidence, fix, effort (S/M/L), owner
  (Aleksis / Raivis / tablet-app dev).
- Then per lens: findings not in the top 10, one line each.
- Quick wins doable today vs changes that need Raivis's decision.
- Under ~1,500 words. No pasted file contents.

## How to run it cheaply

- Three Explore/general subagents in parallel on Sonnet, one per lens group (1 / 2+3 / 4), each
  given an explicit file scope and a <400-word report with file:line evidence.
- Main session: run the test suite in the background, measure sizes with `wc`, spot-check the
  top findings before reporting. Never read CONTEXT.md or a SKILL.md whole - grep.
