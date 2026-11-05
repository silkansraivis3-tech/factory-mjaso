#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Nano Banana pictures for a module: where they go, what the person described, and what they cost - L47.

    picture_briefs.py list <course> --module 1
    picture_briefs.py save <course> --module 1 --slide s03 --brief <brief.json>
    picture_briefs.py done <course> --module 1 --slide s03 --file <picture> --approved "<the person's words>"
    picture_briefs.py queue <course> --module 1 [--all]
    picture_briefs.py place <course> --module 1 --slide q04 --file <picture> --rights <state> [--credit ..] [--source ..]
                            [--license ..] [--author ..] [--generated --prompt ..] [--areas <json>]
    picture_briefs.py areas <course> --module 1 --slide q04 --areas <json>

WHY THIS EXISTS
Every generated picture is billed to the NOVIKONTAS Google account - about EUR 0.10 each, a video clip much more
(owner, 2026-10-14). Four developers redoing pictures 10-15 times each spend the budget, and most redos come from
a vague first description. So the factory never generates on its own: it finds the places first, asks the person
to describe each picture (the questions are knowledge/media-and-tasks.json -> generation_brief), shows the prompt,
and generates only after their yes - the nano-banana tools refuse to run without the person's words.

  list   every screen of the approved content script whose picture the generator makes (visual_kind made_by
         nano_banana), and any other place a description was saved for: the slide, its title, what the script says
         the picture shows, and where it stands - to describe / described / made N time(s), about EUR x. For a place
         still to describe it prints the questions, each with the script's own words as the starting suggestion.
  save   keeps the person's answers and the prompt written from them: brief.json = {"answers": {...}, "prompt": "..."};
         a builder may make the drafted prompt better without the person's answers - {"prompt": "...", "refined":
         "<what was made better>"} - never inventing answers; it is shown as the builder's until the person's yes
  done   records one picture made: the file, the person's words of approval, the date; a slide whose build sheet
         names no picture yet gets this file as its "figure", so the next compile places it
  queue  the free browser route (nano-banana gemini-browser, owner 2026-10-16): every place still without a picture,
         each with its prompt already written - the person's saved prompt, else one drafted from the script's own
         words by the recipe in media-and-tasks.json -> generation_brief.gemini_browser - its aspect ratio and the
         exact file it is saved to (the build sheet's "figure", else assets/img/m01_s03_<title>.png in the module
         folder). Nothing to decide afterwards: show the list once, take corrections, then make them in order.
         Written to working_claude/picture_briefs/M01.gemini.json. --all lists places already made too.
         Every Phase A placeholder of the module is in it - each file in assets/img whose _photo_meta.json record says
         "placeholder": true, the task and check pictures (q.., m..) too - saved under its own name, never over the
         placeholder.
  place  one found or generated picture into a placeholder's place: copied into assets/img under the slot's own name,
         its _photo_meta.json record (rights_state, credit, source, licence; generated, with its prompt), every
         reference in the build sheet moved from the placeholder to it, and the placeholder and its record gone. On a
         tap question the Phase A grid of answer boxes stays until --areas puts each box on its thing.
  areas  the answer boxes of a tap question on the real picture: [x, y, w, h] in % of the picture, a list in the order
         of the build sheet's answers or {"answer": [x, y, w, h]}.

Everything is kept in working_claude/picture_briefs/M01.json, so a redo next week does not ask everything again.
Exit 0, or 2 on bad input.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import re
import shutil
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import content_script as cs  # noqa: E402
import workspace  # noqa: E402

GB = cs.MEDIA["generation_brief"]


def store_path(course, module):
    return os.path.join(workspace.claude_path(course, "picture_briefs"), "%s.json" % cs.mid(module))


def load_store(course, module):
    p = store_path(course, module)
    return json.load(io.open(p, encoding="utf-8")) if os.path.isfile(p) else {}


def save_store(course, module, data):
    p = store_path(course, module)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    io.open(p, "w", encoding="utf-8").write(json.dumps(data, ensure_ascii=False, indent=1))
    return p


def paid(entries):
    """pictures that cost money - the API; a picture from the Gemini app (done --free) costs nothing"""
    return sum(1 for b in entries for m in b.get("made", []) if not m.get("free"))


def generated(s):
    return cs.MEDIA["visual_kinds"].get(cs.parse_kind(s.get("visual_kind", "")), {}).get("made_by") == "nano_banana"


def cmd_list(course, module, script, store):
    screens = {s["id"]: s for s in script.get("screens", [])}
    places = [s["id"] for s in script.get("screens", []) if generated(s)]
    places += [sid for sid in store if sid not in places and sid in screens]
    e = GB["eur_per_image"]
    made = sum(len(store.get(sid, {}).get("made", [])) for sid in places)
    print("Module %s: %d place(s) for a generated picture - %d picture(s) made so far, about EUR %.2f (EUR %.2f each)."
          % (module, len(places), made, paid(store.get(sid, {}) for sid in places) * e, e))
    if not places:
        print("  Nothing to generate: the approved script plans no AI illustration or AI video.")
        return 0
    for sid in places:
        s, b = screens[sid], store.get(sid, {})
        n = len(b.get("made", []))
        state = ("made %d time(s), about EUR %.2f" % (n, paid([b]) * e)) if n else ("described - show the prompt and ask for a yes" if b.get("prompt") else "to describe")
        print("\n- %s (%s) \"%s\" - %s" % (cs.place(script, sid), sid, s.get("title") or s.get("question", ""), state))
        print("    the script says it shows: %s" % (s.get("visual") or "(nothing yet)"))
        if b.get("prompt") and b.get("refined"):
            print("    prompt made better by the builder (%s), not yet the person's - show it and ask: %s" % (b["refined"], b["prompt"]))
        elif b.get("prompt"):
            print("    agreed prompt: %s" % b["prompt"])
        elif not n:
            print("    ask the person, one place at a time - each picture costs about EUR %.2f, so the first try should be right:" % e)
            for i, q in enumerate(GB["questions"], 1):
                print("      %d. %s" % (i, q["en"]))
            print("    starting suggestion from the script: %s" % (s.get("visual") or s.get("title", "")))
    print("\nNothing is generated until the person has described the picture, seen the prompt and said yes (L47).")
    return 0


GEM = GB["gemini_browser"]


def build_sheet(course, module):
    p = os.path.join(cs.paths(course, module)["dir"], cs.mid(module) + ".build.json")
    return p, (cs.load(p) if os.path.isfile(p) else {})


def module_dir(course, module):
    return os.path.join(course, workspace.MODULES, "module%02d" % int(module))


def slug(text):
    words = re.findall(r"[a-z0-9]+", (text or "").lower())
    return "_".join(w for w in words if w not in ("a", "an", "the", "of", "and", "in", "on", "at", "to", "is", "are"))[:48].strip("_") or "picture"


BESIDE = GEM["beside_drawing"]


def place_as(s):
    """"figure" - the generated picture IS the slide's picture; "inset" - a drawing slide keeps its drawing (its labels
    and layout are what the trainee learns) and the generated picture of the real thing goes under it (owner,
    2026-10-16: "i need images there aswell")"""
    if generated(s):
        return "figure"
    return "inset" if cs.parse_kind(s.get("visual_kind", "")) in BESIDE["kinds"] else ""


def draft_prompt(s, answers, comp, beside=False, aspect=None):
    """the prompt from the person's answers, else from the script's own words - same input, same prompt"""
    style = (answers.get("style") or "").lower()
    default = (BESIDE["style_by_kind"].get(cs.parse_kind(s.get("visual_kind", "")), BESIDE["style"]) if beside
               else GEM["default_style"])
    style = next((k for k in GEM["styles"] if k in style.replace(" ", "")), None) or \
        ("render3d" if "3d" in style or "render" in style else "photo" if "photo" in style else default)
    subject = (answers.get("subject") or s.get("visual") or s.get("title") or "").strip().rstrip(".")
    if beside:
        # the script's "visual" describes the DRAWING (cards, icons, what the instructor taps) - a render of that is a
        # render of a slide. The real thing is named by the title; the person corrects it in one line where it is not
        if not answers.get("subject"):
            subject = (s.get("title") or subject).strip().rstrip(".")
        comp = "beside_drawing"
    aspect = aspect or GEM["aspect_by_composition"].get(comp, GEM["aspect_by_composition"]["default"])
    first = subject.split(" ")[0]
    if first and not (first.isupper() and len(first) > 1):        # "The cargo control room" -> "the ...", "LNG" stays
        subject = subject[:1].lower() + subject[1:]
    parts = ["%s %s." % (GEM["styles"][style], subject)]
    if beside:
        parts.append(BESIDE["lead"])
    for key, lead in (("visible", "Clearly visible: "), ("view", "Camera: "), ("setting", "Setting: ")):
        if (answers.get(key) or "").strip():
            parts.append(lead + answers[key].strip().rstrip(".") + ".")
    parts.append((answers.get("space") or "").strip() or GEM["space_by_composition"].get(comp, GEM["space_by_composition"]["default"]))
    excl = (answers.get("exclude") or "").strip().rstrip(".")
    excl = re.sub(r"^no\s+", "", excl, flags=re.I)
    parts.append(GEM["always"] + ((" Also no " + excl + ".") if excl else ""))
    parts.append(GEM["end"].format(aspect=aspect))
    return " ".join(parts), aspect


PLACEHOLDER_TEXT = "Placeholder - the picture still to come: "


def img_meta(mdir):
    p = os.path.join(mdir, "assets", "img", "_photo_meta.json")
    return p, (json.load(io.open(p, encoding="utf-8")) if os.path.isfile(p) else {})


def placeholders(mdir):
    """{slot: record} - every file in the module's assets/img whose _photo_meta.json record says it is a placeholder"""
    _, meta = img_meta(mdir)
    out = {}
    for name, rec in meta.items():
        m = re.match(r"^_placeholder_(.+)\.png$", name)
        if m and isinstance(rec, dict) and rec.get("placeholder") is True and os.path.isfile(os.path.join(mdir, "assets", "img", name)):
            out[m.group(1)] = rec
    return out


def aspect_of(w, h):
    r = float(w or 4) / float(h or 3)
    return min(("16:9", 16 / 9.0), ("4:3", 4 / 3.0), ("1:1", 1.0), ("3:4", 0.75), key=lambda x: abs(x[1] - r))[0]


def is_placeholder_ref(rel):
    return os.path.basename(rel or "").startswith("_placeholder_")


def cmd_queue(course, module, script, store, every):
    screens = {s["id"]: s for s in script.get("screens", [])}
    _, build = build_sheet(course, module)
    sheet = build.get("screens") or {}
    mdir = module_dir(course, module)
    holders = placeholders(mdir)
    places = [s["id"] for s in script.get("screens", []) if place_as(s) and "video" not in s.get("visual_kind", "")
              and s.get("kind", "slide") == "slide" and not (sheet.get(s["id"]) or {}).get("no_picture")]
    places += [sid for sid in store if sid not in places and sid in screens]
    places += [sid for sid in holders if sid not in places]
    out = []
    for sid in places:
        s, b = screens.get(sid) or {"id": sid}, store.get(sid, {})
        bs = sheet.get(sid) or {}
        hold = holders.get(sid)
        if hold:                                          # the placeholder says what it holds, and its shape
            s = dict(s, visual=s.get("visual") or (hold.get("description") or "").replace(PLACEHOLDER_TEXT, ""))
        how = place_as(s) or "figure"
        have = (bs.get("inset") or {}).get("photo") if how == "inset" else ""
        fig = (have or (bs.get("figure") if how == "figure" else "") or "").replace("\\", "/")
        if is_placeholder_ref(have):
            have = ""
        real = fig and not is_placeholder_ref(fig) and os.path.isfile(os.path.join(mdir, fig))
        if (b.get("made") or have or real) and not hold and not every:
            continue
        comp = bs.get("composition") or "photo"          # a generated picture with no layout of its own fills the slide
        prompt, aspect = draft_prompt(s, b.get("answers") or {}, comp, beside=how == "inset",
                                      aspect=aspect_of(hold.get("width"), hold.get("height")) if hold else None)
        if b.get("prompt"):
            prompt = b["prompt"]
        rel = fig if fig.lower().endswith((".png", ".jpg", ".jpeg", ".webp")) and not is_placeholder_ref(fig) else \
            "assets/img/%s_%s_%s%s.png" % (cs.mid(module).lower(), sid, slug(s.get("title") or s.get("question") or s.get("visual")),
                                           "_3d" if how == "inset" else "")
        out.append({"slide": sid, "place": cs.place(script, sid) if sid in screens else hold.get("used_in") or sid,
                    "title": s.get("title") or s.get("question") or "", "aspect": aspect,
                    "place_as": "under the drawing (inset)" if how == "inset" else "the slide's picture",
                    "prompt": prompt, "prompt_from": "the builder (%s) - show it to the person" % b["refined"]
                    if b.get("prompt") and b.get("refined") else "the person" if b.get("prompt") else
                    ("drafted from the title - say in one line what the real thing looks like if the title is not a "
                     "thing on a ship" if how == "inset" and not (b.get("answers") or {}).get("subject") else "drafted from the script"),
                    "about": (s.get("visual") or s.get("title") or "").strip(), "rel": rel,
                    "save_as": os.path.normpath(os.path.join(mdir, rel)), "made": len(b.get("made", [])),
                    "placeholder": "assets/img/_placeholder_%s.png" % sid if hold else ""})
    qp = os.path.join(os.path.dirname(store_path(course, module)), "%s.gemini.json" % cs.mid(module))
    os.makedirs(os.path.dirname(qp), exist_ok=True)
    io.open(qp, "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=1))
    print("Module %s: %d picture(s) to make in the Gemini app - no cost per picture (Google AI Pro), nothing left to decide "
          "(%d placeholder(s) in the module)." % (module, len(out), len(holders)))
    for i, q in enumerate(out, 1):
        print("\n%d. %s (%s) \"%s\" -> %s  [%s, %s, prompt %s]\n   %s" % (i, q["place"], q["slide"], q["title"], q["rel"],
                                                                    q["place_as"], q["aspect"], q["prompt_from"], q["prompt"]))
    print("\nShow this list once; a correction to a line is saved with: save --slide <id> --brief <json>. Then make them in "
          "order with nano-banana gemini-browser, and put each in its place with: place --slide <id> --file <picture>.\n    %s" % qp)
    return 0


def size_of(path):
    try:
        from PIL import Image
        with Image.open(path) as im:
            return im.size
    except Exception:
        return None, None


def boxes(text, keys):
    """--areas: a list in the order of the answers, or {"answer": box} - each [x, y, w, h] in % of the picture"""
    got = json.loads(text)
    if isinstance(got, list):
        if len(got) != len(keys):
            raise ValueError("%d box(es) for %d answer(s): %s" % (len(got), len(keys), ", ".join(keys)))
        got = dict(zip(keys, got))
    if not isinstance(got, dict) or set(got) != set(keys):
        raise ValueError("one box for each answer, by its own words: %s" % ", ".join(keys))
    for k, v in got.items():
        if not (isinstance(v, list) and len(v) == 4 and all(isinstance(x, (int, float)) for x in v)
                and v[0] >= 0 and v[1] >= 0 and v[2] > 0 and v[3] > 0 and v[0] + v[2] <= 100.5 and v[1] + v[3] <= 100.5):
            raise ValueError("the box of \"%s\" is not [x, y, w, h] inside the picture, in %%: %s" % (k, v))
    return {k: [round(float(x), 1) for x in got[k]] for k in keys}


GRID_NOTE = ("picture placed %s; the answer boxes are still the Phase A grid - put each on its thing: picture_briefs.py "
             "areas <course> --module %s --slide %s --areas <json>")


def set_areas(entry, text, module, sid):
    """the slot's tap areas from --areas, or the note that they are still the grid - True when they are set"""
    if not isinstance(entry.get("areas"), dict) or not entry["areas"]:
        entry.pop("_placeholder", None)
        entry.pop("placeholder", None)
        return None
    if text:
        entry["areas"] = boxes(text, list(entry["areas"]))
        entry.pop("_placeholder", None)
        entry.pop("placeholder", None)
        return True
    entry["_placeholder"] = GRID_NOTE % (time.strftime("%Y-%m-%d"), module, sid)
    return False


def cmd_place(course, module, a):
    """a found or generated picture into the place of the slot's placeholder"""
    mdir = module_dir(course, module)
    if not os.path.isfile(a.file):
        print("Stopped - there is no picture at %s" % a.file)
        return 2
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "course-visuals", "scripts"))
    import check_assets
    rights = "GENERATED" if a.generated else (a.rights or "").upper()
    if rights not in check_assets.VALID_RIGHTS or rights == "REJECTED":
        print("Stopped - --rights is one of: %s" % ", ".join(sorted(check_assets.VALID_RIGHTS - {"REJECTED"})))
        return 2
    if a.generated:
        if not (a.prompt or "").strip():
            print("Stopped - a generated picture keeps the prompt it was made from (--prompt)")
            return 2
    elif rights == "ATTRIBUTION_REQUIRED" and not (a.credit and a.author):
        print("Stopped - ATTRIBUTION_REQUIRED needs --credit and --author: the credit line has to say something")
        return 2
    bp, build = build_sheet(course, module)
    holders = placeholders(mdir)
    old = "assets/img/_placeholder_%s.png" % a.slide
    hold = holders.get(a.slide)
    entry = (build.get("screens") or {}).get(a.slide)
    if not hold and entry is None:
        print("Stopped - module %s has no placeholder and no build-sheet place for %s" % (module, a.slide))
        return 2
    script = cs.load(cs.paths(course, module)["script"])
    s = next((x for x in script.get("screens", []) if x["id"] == a.slide), {})
    shows = ((hold or {}).get("description") or "").replace(PLACEHOLDER_TEXT, "") or s.get("visual") or s.get("title") or ""
    ext = os.path.splitext(a.file)[1].lower()
    ext = ".jpg" if ext == ".jpeg" else ext
    if ext not in (".png", ".jpg", ".webp"):
        print("Stopped - a picture is .png, .jpg or .webp: %s" % a.file)
        return 2
    rel = "assets/img/%s_%s_%s%s" % (cs.mid(module).lower(), a.slide, slug(s.get("title") or s.get("question") or shows), ext)
    dest = os.path.join(mdir, rel.replace("/", os.sep))
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    if os.path.abspath(a.file) != os.path.abspath(dest):
        shutil.copy2(a.file, dest)
    w, h = size_of(dest)
    rec = {"title": (s.get("title") or shows[:1].upper() + shows[1:])[:120], "description": shows,
           "width": w, "height": h, "used_in": (hold or {}).get("used_in") or a.slide, "rights_state": rights,
           "credit": a.credit, "source": a.source, "license": a.license, "author": a.author, "placed": time.strftime("%Y-%m-%d")}
    if a.generated:
        rec.update(generated=True, origin="generated illustration", generation_prompt=a.prompt.strip(),
                   generated_by=a.generated_by or "Gemini app (browser), Nano Banana", license=a.license or "generated for this course")
    mp, meta = img_meta(mdir)
    meta[os.path.basename(rel)] = {k: v for k, v in rec.items() if v not in (None, "")}
    io.open(mp, "w", encoding="utf-8", newline="\n").write(json.dumps(meta, ensure_ascii=False, indent=2) + "\n")
    if hold:
        sys.path.insert(0, os.path.join(os.path.dirname(HERE), "compile", "scripts"))
        import placeholder
        placeholder.remove(mdir, a.slide)
    text = json.dumps(build, ensure_ascii=False)
    moved = text.count(json.dumps(old)[1:-1])
    build = json.loads(text.replace(json.dumps(old)[1:-1], json.dumps(rel)[1:-1]))
    entry = build.setdefault("screens", {}).get(a.slide)
    if not moved and not (entry or {}).get("figure"):
        entry = build["screens"].setdefault(a.slide, {})
        entry["figure"] = rel
    try:
        tapped = set_areas(entry, a.areas, module, a.slide) if entry is not None else None
    except ValueError as e:
        print("Stopped - %s" % e)
        return 2
    build.setdefault("module", int(module))
    cs.save(bp, build)
    print("Placed %s in %s (%s): %s, %s%s; the build sheet points to it in %d place(s)%s." % (
        os.path.basename(a.file), cs.mid(module), a.slide, rel, rights, " (generated)" if a.generated else "", max(moved, 1),
        "" if tapped is None else " - its answer boxes are on the picture" if tapped else
        " - its answer boxes are still the Phase A grid: put each on its thing with areas --slide %s" % a.slide))
    print("Build the module again (fix.py rebuild) for the slides to show it.")
    return 0


def cmd_areas(course, module, a):
    bp, build = build_sheet(course, module)
    entry = (build.get("screens") or {}).get(a.slide)
    if not entry or not isinstance(entry.get("areas"), dict) or not entry["areas"]:
        print("Stopped - %s %s is not a tap question: its build sheet has no \"areas\"" % (cs.mid(module), a.slide))
        return 2
    try:
        set_areas(entry, a.areas, module, a.slide)
    except ValueError as e:
        print("Stopped - %s" % e)
        return 2
    cs.save(bp, build)
    for k, v in entry["areas"].items():
        print("  %s  %s" % (v, k))
    print("The answer boxes of %s %s are on the picture." % (cs.mid(module), a.slide))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("list", "save", "done", "queue", "place", "areas"):
        s = sub.add_parser(name)
        s.add_argument("course")
        s.add_argument("--module", required=True)
        if name == "queue":
            s.add_argument("--all", action="store_true")
        elif name != "list":
            s.add_argument("--slide", required=True)
        if name == "place":
            s.add_argument("--file", required=True)
            s.add_argument("--rights", default="")
            for k in ("--credit", "--source", "--license", "--author", "--prompt", "--generated-by"):
                s.add_argument(k)
            s.add_argument("--generated", action="store_true")
        if name in ("place", "areas"):
            s.add_argument("--areas", required=name == "areas")
        if name == "save":
            s.add_argument("--brief", required=True)
        if name == "done":
            s.add_argument("--file", required=True)
            s.add_argument("--approved", required=True)
            s.add_argument("--free", action="store_true", help="made in the Gemini app (gemini-browser) - costs nothing")
    a = ap.parse_args(argv)
    course = workspace.work_folder(a.course, create=False)
    p = cs.paths(course, a.module)["script"]
    if not os.path.isfile(p):
        print("Stopped - there is no content script for module %s:\n    %s" % (a.module, p))
        return 2
    script = cs.load(p)
    store = load_store(course, a.module)
    if a.cmd == "list":
        return cmd_list(course, a.module, script, store)
    if a.cmd == "queue":
        return cmd_queue(course, a.module, script, store, a.all)
    if a.cmd == "place":
        return cmd_place(course, a.module, a)
    if a.cmd == "areas":
        return cmd_areas(course, a.module, a)
    if a.slide not in {s["id"] for s in script.get("screens", [])}:
        print("Stopped - module %s has no screen %s" % (a.module, a.slide))
        return 2
    b = store.setdefault(a.slide, {})
    if a.cmd == "save":
        brief = json.load(io.open(a.brief, encoding="utf-8"))
        refined = (brief.get("refined") or "").strip() if isinstance(brief.get("refined"), str) else ""
        if not (brief.get("prompt") or "").strip() or not (isinstance(brief.get("answers"), dict) or refined):
            print("Stopped - a brief is {\"answers\": {...the person's answers...}, \"prompt\": \"...\"}, or - a builder making the "
                  "drafted prompt better, with no answers of the person's - {\"prompt\": \"...\", \"refined\": \"<what was made "
                  "better>\"}")
            return 2
        if isinstance(brief.get("answers"), dict):
            b.update({"answers": brief["answers"], "prompt": brief["prompt"].strip(), "saved": time.strftime("%Y-%m-%d")})
            b.pop("refined", None)
        else:
            # 2.63.0 (IGF M02 v262: "prompts could not be improved here") - a builder may make the drafted prompt better; it
            # never invents the person's answers: the ones kept stay, and the prompt is marked as the builder's
            b.update({"prompt": brief["prompt"].strip(), "refined": refined, "saved": time.strftime("%Y-%m-%d")})
        print("Saved the description of %s (%s) - next: show the prompt and ask \"Generate this one picture (about EUR %.2f)?\"\n    %s"
              % (cs.place(script, a.slide), a.slide, GB["eur_per_image"], save_store(course, a.module, store)))
        return 0
    if len((a.approved or "").strip()) < 2:
        print("Stopped - the person's own words of approval are needed (--approved)")
        return 2
    rec = {"file": a.file, "approved_by_user": a.approved.strip(), "when": time.strftime("%Y-%m-%d %H:%M")}
    if a.free:
        rec["free"] = "Gemini app on the person's own Google AI Pro account - no cost per picture"
    b.setdefault("made", []).append(rec)
    save_store(course, a.module, store)
    # the slide's build sheet names the picture, so the next compile places it - unasked
    mdir = os.path.abspath(module_dir(course, a.module))
    f = os.path.abspath(os.path.join(mdir, a.file)) if not os.path.isabs(a.file) else os.path.abspath(a.file)
    if f.lower().startswith(mdir.lower() + os.sep) and f.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
        bp, build = build_sheet(course, a.module)
        entry = build.setdefault("screens", {}).setdefault(a.slide, {})
        rel = os.path.relpath(f, mdir).replace("\\", "/")
        s = next(x for x in script["screens"] if x["id"] == a.slide)
        if place_as(s) == "inset":                        # the drawing stays; the picture goes under it
            if not (entry.get("inset") or {}).get("photo"):
                entry["inset"] = {"photo": rel, "under": "figure"}
                build.setdefault("module", int(a.module))
                cs.save(bp, build)
                print("The build sheet now places it under the drawing on %s: \"inset\": {\"photo\": \"%s\", \"under\": \"figure\"}"
                      % (a.slide, rel))
        elif not entry.get("figure"):
            entry["figure"] = rel
            build.setdefault("module", int(a.module))
            cs.save(bp, build)
            print("The build sheet now places it on %s: \"figure\": \"%s\"" % (a.slide, entry["figure"]))
    n = sum(len(x.get("made", [])) for x in store.values())
    print("Recorded: %s (%s) - picture %d for module %s, about EUR %.2f so far%s." % (
        cs.place(script, a.slide), a.slide, n, a.module, paid(store.values()) * GB["eur_per_image"],
        " (this one free, from the Gemini app)" if a.free else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
