# Publishing your course to the tablets — the short version

For colleagues building NOVIKONTAS courses. You do **not** need to know Gradle, Android
source sets, APK packaging, Git, or how the classroom server works.

---

## What to do

1. **Build your course** in your course folder, as normal.

2. **When the trainee and instructor material is ready**, tell Claude:

   > **Publish this course to the NOVIKONTAS tablet platform.**

3. **Claude checks it first and shows you the plan.** Nothing is published yet. You will see
   what would ship, how many files are trainee versus instructor, and anything that needs
   fixing.

4. **If something is wrong, Claude stops and tells you exactly which file.** It will not
   publish around a problem. Fix it and ask again.

5. **If it is clean, say:** *go ahead and publish it.* Claude puts your course on its own
   branch and gives you a link to open the pull request. Someone reviews it, and it goes into
   the shared branch.

That is the whole thing.

---

## What Claude will refuse to publish

- **Instructor material inside the trainee package** — an answer key, marking criteria, a run
  sheet, an assessor's record. Trainees must not have these on their tablets.
- **Any password, key or credential** in a course file.
- **A missing file** — a picture or page your course points at that is not there.
- **A link to your own laptop** — an address that works for you and nowhere else.
- **Backup files** (`.bak`) left inside the course, because they get packaged and shipped.

If it refuses, it names the file. That is the fastest fix you will ever get.

---

## Things worth knowing

- **Publishing is not installing.** Your course reaching the shared branch does not put it on
  a tablet. The app still has to be built and installed. Ask when you need that.
- **Warnings are not failures.** You will see warnings about things the platform already
  carries — a web font that needs internet, and some older files. They are listed every time
  on purpose. They do not block you.
- **Your course has its own folder,** so publishing it cannot disturb a colleague's course
  even if you both publish the same afternoon.
- **Versions matter.** Once a class has been taught from a version, changing it means a new
  version number. Claude handles this; just tell it if the course has already been delivered.

---

## If you are starting a brand new course

Tell Claude:

> **Add a new course to the NOVIKONTAS tablet platform.**

It will ask you for the course name and a short id, set up the folder structure, and tell you
what the platform needs from you. Note that today a brand new course also needs a small
change inside the two apps before the tablets can *see* it — Claude will say so and tell you
what remains. That is a platform job, not yours.
