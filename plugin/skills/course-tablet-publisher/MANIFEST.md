# MANIFEST — course-tablet-publisher

**v1 (2026-09-08) · Maintained by Raivis · Personal — installed for Raivis only, not org-published**

Maintainer file. **Never read at runtime.** It exists so a session with no memory of this
work can pick the skill up cold and not undo its decisions.

## 0 · Why this skill exists

The owner needs several colleagues to build different courses in parallel and get them onto
the tablet platform without any of them learning Android Studio, Gradle, APK asset layout or
Git. The platform itself is valuable working software that teaches real accredited classes.
So the brief was explicitly a **publication layer around** it, not a redesign of it.

## 1 · What was already there, and what this adds

`course-factory` already owned the *ship* lane: `knowledge/delivery-contract.json` (the
authority on course shape) and four good validation scripts (`verify_course.py`,
`verify_links.py`, `crosscheck_tasks.py`, `audit_navigation.py`). **Those are called, never
reimplemented.** Duplicating them would have created a second contract that silently drifts.

What did not exist, and is what this skill is:

| New | Why |
|---|---|
| a role-separation gate | the rule was prose only; nothing checked it, and it was already broken |
| a secrets / offline / address / junk / rights gate | stated in the contract, never enforced |
| a per-course identity and version story (`course.json`) | no course had a manifest at all |
| a generated installed-course registry | the module list already existed six times and disagreed |
| git branch → PR → default branch, with rails | `course-factory` says *never* commit or push |

## 2 · The one deliberate contradiction

`course-factory/tablet/GUIDE.md` and its contract both say **"the owner commits and pushes;
never commit or push on their behalf."** That was right when one person shipped one course.
The 2026-09-08 brief explicitly asks for validated content to reach the shared branch so
colleagues can work in parallel. This skill supersedes that rule **for the publish flow
only**, and a pointer was added to `tablet/GUIDE.md` so the two are not read as conflicting.
Everything else in that guide still stands.

## 3 · Decisions that will look odd later

- **Two layouts.** `courses/<id>/` is the target and what every new course uses; GAS BASIC
  stays legacy at the terminal roots. Converting it moves ~400 files and every relative link,
  and the owner teaches from it — so it was left alone, deliberately, and the gate supports
  both.
- **WARN publishes.** A spotless-PASS rail would make the working course unpublishable
  forever, and the human response to that is to bypass the tool. FAIL stops; WARN publishes
  and prints. `--strict` shows the truth.
- **`known-findings.json` exists and is not a cop-out.** It baselines 13 real, pre-existing
  findings so a *new* leak still fails. Every entry names its fix and appears in every
  report. Deleting it is not a cleanup — it would block all publication.
- **The registry is a JS global, not JSON.** Every other registry on this platform loads that
  way (`GB_TASKS`, `IT_MODULES`, `IT_RUN`), and a runtime `fetch` in an offline WebView would
  be a second mechanism.
- **The registry is generated, never edited.** That is what makes the only shared file
  conflict-free when colleagues publish in parallel.
- **No `gh`.** It is not installed and there is no token, so the PR is a printed compare URL.

## 4 · Bugs found by the dry run, and kept as tests

The first run against GAS BASIC produced 406 failures. Three were bugs in this gate, not in
the platform, and each is now a comment in the code so it is not reintroduced:

1. **Font fallback judged per page.** Font *stacks* live in the stylesheets; asking each HTML
   page whether it mentions a generic family gave 333 false failures.
2. **Content patterns matched inside comments.** Three of the first five role findings were
   comments *saying* the answer key lives on the instructor side. Comments are now stripped,
   and content patterns WARN while filename patterns FAIL.
3. **Links resolved in the split source tree.** 140 correct cross-terminal links looked dead.
   Gradle merges the source sets, so resolution must happen in a merged view — the exact trap
   `course-factory/tablet/GUIDE.md` warns about, walked straight into anyway.

After the fixes: GAS BASIC is WARN with 0 failures, and `verify_links.py` independently agrees
at 0 dead links out of 1411.

## 5 · Verification performed (2026-09-08)

Against the live repository, read-only except for a throwaway pack that was deleted:

| Test | Result |
|---|---|
| GAS BASIC gate | WARN, 0 fail, 368 warn, 13 baselined |
| simulated role leak / missing asset | both refuse, exit 1 |
| `--strict` | FAIL, 368 — the true state |
| unknown course id | refuses with an explanation |
| `gitpub.py plan` | detects `master`, names the 266 dirty files, correct PR URL |
| commit with no / failing gate report | both refuse |
| merge without `--merge` | refuses |
| NEW course pack (created, tested, deleted) | PASS; registry lists it beside gas-basic; leak, missing asset, service-role key and laptop address each refuse; no Android file touched |
| repository after all tests | unchanged — 266 dirty paths before and after, still on `master` |

## 6 · The honest gap

Publishing works. **Discovery does not yet.** The terminals still carry course identity in
code, so a new course needs `gb_config.js`, `it_auth.js`, the `COURSE_TITLE` constants and the
`gb_sync.js` scope regex touched by hand. `references/course-package.md` §6 lists it exactly
and names the smallest fix. That change edits code that runs a live class, so it needs its own
session and the owner's go-ahead — it was deliberately not done here.

## 7 · If you extend this

- Change `knowledge/platform.json`, not the scripts, when the platform moves.
- Keep `SKILL.md` short. Detail belongs in `references/`, determinism in `scripts/`.
- Do not add a destructive git flag. The absence of one is a feature.
- Before claiming a check works, run it against the real tree. Three of the first four
  "working" checks were wrong.
