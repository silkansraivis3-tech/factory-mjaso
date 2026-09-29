# Getting the course tools on your computer

**You need Claude Code — the terminal app, not the Claude desktop app.** Two commands, once per
computer. You never do it again.

---

## Step 1 — do you have Claude Code?

Open a terminal (on Windows: press Start, type `powershell`, press Enter) and run:

```
claude --version
```

If it prints a version number like `2.1.267 (Claude Code)`, skip to step 2.

If it says the command is not recognised, install it — this is the official installer:

```
irm https://claude.ai/install.ps1 | iex
```

Then close the terminal, open a new one, and run `claude --version` again.

*(macOS or Linux: `curl -fsSL https://claude.ai/install.sh | bash`)*

## Step 2 — add the course tools

Start Claude Code by typing `claude`, then type these two lines:

```
/plugin marketplace add silkansraivis3-tech/factory-mjaso
```

```
/plugin install course-factory@novikontas-course-factory
```

**Done.** Check it worked — `/plugin` should list **course-factory 2.1.0**, enabled.

### Realistic and 3D pictures come with it

The course tools bring a second plugin, **nano-banana**, with them — you do not install it
separately. It lets Claude make real photo-like and 3D pictures, and short realistic animations,
for slides and course screens.

It needs **one key**, which NOVIKONTAS shares. **Ask Raivis for it.** During the install Claude Code
shows a box called **Gemini API key** — paste it there, once. It is kept in Windows' secure
storage. If the box did not appear, or you skipped it: `/plugin` → **nano-banana** → **Configure**.

**Never paste the key into the chat, an email to anyone else, or a file in a course folder.**

Check it: type *nano banana status*. It should say `key_works: true`.

Then just ask in plain words, e.g. *"make the title slide a photorealistic picture of an LNG carrier
at sea"* or *"I want realistic explanatory photos on these slides"*. Claude makes the picture, looks
at it, redoes it if it is wrong, and puts it on the slide. Labelled diagrams and charts it still
draws itself — a picture generator invents pipes that do not exist.

---

## Updates

You do nothing. Claude Code refreshes the marketplace on its own and picks up new versions.
To force it: `/plugin marketplace update` then `/plugin update course-factory`.

---

# How to use it

**Do not try to "run" anything.** Describe the course you want in normal words, the way you would
explain it to a colleague:

> Build a new course like GAS BASIC, for Advanced Gas. The approved programme is the PDF in this
> folder. Same two tablets as GAS BASIC. Groups of 12, we use the LNG simulator, no live fire.
> Make it highly practical, and I want a strong animated explanation of the reliquefaction system.

It reads the programme, works out the hours and modules, **then stops and shows you a table.**
Nothing is built until you say the table is right. For a substantial module it will also show you
a **visual storyboard** — what each figure will be and why — and stop again. Both stops are there
because changing a row in a table is free and rebuilding eight modules is not.

## The one thing you must have first

**The approved Study Programme** — the document with the hours table and the learning outcomes.
Put it in the folder before you start. Nothing works without it.

If you also have the **IMO model course** for that subject, put that in too.

## Asking for visuals

Ask in plain words for what you want the trainee to understand, not for a format:

> *"I want them to see how the vapour travels along the deck before we talk about detection."*

That is better than *"add an animation"*, because the tools choose the representation from the
learning need. Sometimes the honest answer is that a concept needs no picture at all, and it will
tell you that rather than filling the screen.

If it reports **`RIGHTS_REVIEW_REQUIRED`**, an image it found may not be legally usable — that is
a decision for Raivis, not something to work around. If it reports
**`GENERATED_ASSET_REQUIRED`**, no usable image exists anywhere and it has written a brief saying
exactly what would need to be photographed or drawn.

---

# When the course is ready for the tablets

You need a copy of the tablet app project (`NOVIKONTASTraining`) on your computer. Ask Raivis for
it once. You never open it or change anything inside it.

Then say:

> **Publish this course to the NOVIKONTAS tablet platform.**

It checks everything and shows you a plan first — nothing is published until you say *go ahead*.
If something is wrong it stops and names the exact file.

**Published is not installed.** Reaching the shared project does not put the course on a tablet.
The app still has to be built and installed on the devices. That is Raivis's job.

---

## If something doesn't work

Don't try to fix it. **Message Raivis**, and copy him whatever red text you see — that text says
exactly what went wrong.

*Raivis · raivis.silkans@novikontas.org*

---

### If you installed the old way

Before September 2026 the tools were copied by a script into `%USERPROFILE%\.claude\skills\`.
**That method is retired.** If you have five `course-*` folders there, delete them after
installing the plugin — otherwise you are running two copies, one of them frozen at the old
version, and they will disagree with each other.
