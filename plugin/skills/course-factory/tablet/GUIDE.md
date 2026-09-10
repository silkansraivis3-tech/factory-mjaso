# Tablet — a course becomes a data pack on two terminals

**v1 (2026-09-07) · Maintained by Raivis · Personal — installed for Raivis only, not org-published**

Read this in **ship** mode. `../knowledge/delivery-contract.json` is the authority on every path,
folder and rule below — read it, and do not restate its paths here.

---

## The architecture, and why it is this one

**One app. Courses are data packs.** The two terminals are one codebase; a course adds a content
folder and one registry entry. It never adds app code and never forks a terminal.

The owner's requirement is that every course looks and behaves the same. Shared code is the only
thing that actually enforces that — a copied terminal drifts the first time one course gets
fixed. One APK per course also means a shared fix has to be applied N times, and one will be
missed.

**On GitHub:** the repo holds the terminals and every course pack. Add a course on the build
machine, commit, push, build the APKs, install. The repo is the backup and the history; the APK
is the delivery. Do **not** make the tablets pull at runtime — a classroom may have no network,
and these terminals are deliberately offline-capable.

---

## The trap that makes correct links look broken

Gradle merges the flavour source sets into **one** asset root, so at runtime
`training_terminal/` and `instructor_terminal/` are **siblings**. A cross-terminal link is
written relative to that merged root:

```
from instructor_terminal/prepare/m05/practicals/  →  ../../../../training_terminal/…
```

In the split source tree that path does not resolve, so a **correct** link looks dead. Always
verify against a merged view — `scripts/verify_links.py` builds one without copying anything.
Getting this backwards wastes an afternoon "fixing" links that were right.

---

## Generated files are generated

`it_run.js` — the instructor's step-by-step — is derived from each deck's own markup. Slide
numbers move whenever a deck is cut, and a stale number lies silently: the instructor announces
the wrong task and only finds out in the room.

So: **regenerate after any deck change**, and never hand-edit the output.

Anything the generator cannot derive belongs in an **OVERRIDES table inside the generator**, not
patched into the output afterwards. Two properties make it safe:

- every run prints the overrides it applied, so they cannot rot unseen;
- a rotted override **stops the run** rather than shipping a wrong number.

That guard has already earned itself: after a module gained a screen, the run refused to write
and named exactly which quoted slide number had moved.

---

## The three-way agreement

The failure that matters most in a classroom is an instructor saying "open T3" when the tablet
has no T3, or has it under another name. Three artefacts must agree:

| | carries |
|---|---|
| the deck | `data-activity` on the screen that announces the task |
| the run script | the step that tells the instructor which screen and which code |
| the tablet manifest | the code, the title the trainee sees, and the page that exists |

`scripts/crosscheck_tasks.py` lines all three up and names every disagreement. A screen missing
its `data-activity` is invisible to the generator, so the deck announces a task the step-by-step
does not — that exact bug shipped once and this check found it.

Reference cards and module checks legitimately appear in the manifest without a deck screen
announcing them; the script lists those separately rather than calling them errors.

---

## Instructor material never lives in the trainee tree

Anything addressed to the instructor — a marking sheet, a practical write-up, a setup document,
a safety brief — belongs on the instructor terminal. On GAS BASIC a marking sheet and a
simulator-setup document sat in the trainee tree, one of them unreachable by anyone.

When you move one, its relative links move with it and **all of them break**. Repair them
against the merged root, bring its stylesheet and images, and add it to whatever hub should
reach it. Then re-run the link check — a moved document with dead links is worse than one nobody
could find, because now it looks available.

---

## Offline

A classroom tablet may have no network, so nothing at class time may depend on one. The checks
are in the contract file. The one that bites: a web font with no bundled copy. Every font stack
must end in a generic family, so the degradation is a decision rather than an accident.

---

## Before handover

Read the git section of the contract. The two that cost real time:

- **Stage every new file.** An untracked asset ships as a missing file, and the failure shows up
  on the tablet, not in the build.
- **Check the shape of your own diff.** `git diff -U0 | grep -c '^[-+]'` against the same with
  `--ignore-all-space`. A large gap means an edit reformatted files it was not asked to touch.
  Fix that before handover; a diff the owner cannot read is a diff they cannot review.

Never commit or push — that is the owner's. Stage when asked, and say exactly what you staged.

---

## The checks

```bash
python tablet/scripts/verify_course.py    --course <path> --modules 8
python tablet/scripts/verify_links.py     --assets app/src/main/assets --assets app/src/instructor/assets
python tablet/scripts/crosscheck_tasks.py --course <path> --manifest <gb_tasks.js> --run <it_run.js>
```

Run all three, read the lines, then report. A green exit is not proof the work happened —
inspect the line for the thing you changed. And when a probe and a screenshot disagree, the
screenshot wins: measurement bugs are as common as layout bugs, and both have happened here.
