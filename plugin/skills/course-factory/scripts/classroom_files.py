# -*- coding: utf-8 -*-
"""classroom_files - the two instructor-only files the tablet app reads when a course release is published.

The training app's admin importer (admin/package-core.mjs classroomExtras) takes, beside the modules, a `classroom/`
folder of the uploaded course folder; none of it reaches the trainees:

    modules\\classroom\\prepare.json        {"course": [item], "modules": {"module01": [item], ...}}
                                           item = {"label", "kind", "place"?, "minutes"?}   -> the release's Prepare tab
    modules\\classroom\\forms\\<CODE>.json   {"code", "title", "definition": {"sections": [...], ...}}
                                           one per recorded-run assessment form       -> the course's assessment forms

additional_materials.plan() writes both beside the other shared files of the course (compile_course.py runs it), from
what the factory already knows: intake.json, architecture.json, the approved content scripts and the approved
instructor_led.json. check_course_package.py checks them with folder_problems() - the app's own limits (60 items per
list, 40 forms, a label of 200 characters, the form code pattern) and the app's form rules (forms.mjs validateDefinition).

Module codes in prepare.json are the course map's own (module01, module02 ...), the same the app reads from
_course_shell/course_map.js. A module with nothing to get ready is left out; a course with no recorded run writes no form.

    python classroom_files.py <course folder>      prints what would be written (nothing is written)
"""
from __future__ import annotations

import io
import json
import os
import re
import sys
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import workspace  # noqa: E402

PREPARE_PATH = "classroom/prepare.json"
FORMS_DIR = "classroom/forms"
FORM_FILE = re.compile(r"^([^/]+)\.json$", re.I)
PREP_KINDS = ("simulator", "equipment", "room", "material", "document", "other")
MAX_ITEMS, MAX_FORMS, MAX_LABEL, MAX_PLACE, MAX_CODE = 60, 40, 200, 120, 40       # the app's own limits
FORM_CODE = re.compile(r"^[A-Z0-9][A-Z0-9_.-]{0,39}$")
SCALES = ("0-4", "1-5", "0-10", "1-3", "0-5", "0-2", "0-100", "pass_fail", "yes_no")
FINAL_MARKS = ("mean_if_complete", "sum_if_complete", "percent_if_complete")
KEY = re.compile(r"^[a-z][a-z0-9_]{0,40}$")
MAX_CRITERIA = 500

SIM_WORDS = re.compile(r"simulat|тренаж", re.I)
EQUIP_WORDS = re.compile(r"\b(?:rig|bench|detectors?|meters?|apparatus|instruments?|equipment|facility|monitor|tripod|stretcher|"
                         r"resuscitator|extinguisher|hoses?|laptops?|tablets?|projector|computers?|pc|screen|kit)\b", re.I)
ROOM_WORDS = re.compile(r"\b(?:class\s?room|room|hall|lab|laboratory|workshop)\b", re.I)
AWAY_WORDS = re.compile(r"\bhome\b|independent|self[- ]study|remote|online", re.I)    # done by the trainee, not set up by the instructor
W = {"print": "Print", "cards": "pre-brief, debrief and observation cards", "form": "assessment form, one per candidate",
     "paper": "task paper", "safety": "Safety brief ready", "assessor": "An assessor named for the recorded runs (not the trainer, where possible)",
     "employer": "Print: the employer sheet", "sheet": "Assessment form",
     "crit": "A. Critical steps", "global": "B. Global rating", "decision": "C. Decision",
     "stop": "STOP", "decision_label": "Decision: Yes = competent, No = Not yet (write one sentence for any Not yet)",
     "global_label": "Global rating of the run", "date": "Date of the run", "attempt": "Attempt (1, 2 or 3)",
     "gwo": "GWO standard level (0-3)"}


# ------------------------------------------------------------------ small helpers
def load(path):
    try:
        with io.open(path, encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def label(text, n=MAX_LABEL):
    t = re.sub(r"\s+", " ", str(text or "")).strip()
    return t if len(t) <= n else t[:n].rstrip()


def cap(text):
    t = label(text)
    return t[:1].upper() + t[1:]


def short(task, n=60):
    """a practical's name from its long task line - the words before the first bracket or colon"""
    t = re.split(r"\s\(|:", str(task or ""), maxsplit=1)[0]
    t = label(t, n)
    return t[:1].upper() + t[1:]


def kind_of(text):
    if SIM_WORDS.search(text or ""):
        return "simulator"
    if EQUIP_WORDS.search(text or ""):
        return "equipment"
    return "room" if ROOM_WORDS.search(text or "") else "other"


def item(text, kind=None, place=None):
    out = {"label": label(text), "kind": kind if kind in PREP_KINDS else kind_of(text)}
    if place:
        out["place"] = label(place, MAX_PLACE)
    return out


def add(items, it):
    if it["label"] and all(x["label"].lower() != it["label"].lower() for x in items):
        items.append(it)


def ascii_upper(text):
    t = unicodedata.normalize("NFKD", str(text or "")).encode("ascii", "ignore").decode("ascii").upper()
    return re.sub(r"[^A-Z0-9]+", "-", t).strip("-")


def form_code(course_title, mid, task_code):
    """the code of a recorded run's form. Form codes are global on the server (one template per code), so the course's
    name leads: PROJECT-MANAGEMENT-M05-A01 - the name is cut, never the module and task, to fit the 40 characters"""
    tail = "%s-%s" % (ascii_upper(mid), ascii_upper(task_code))
    head = ascii_upper(course_title)[: max(1, MAX_CODE - len(tail) - 1)].strip("-") or "COURSE"
    return "%s-%s" % (head, tail)


# ------------------------------------------------------------------ what the instructor gets ready
def course_items(intake, il_data):
    """the course-wide list: the equipment and rooms the course asked for at intake, the employer sheet, the assessors"""
    out = []
    eq = intake.get("equipment")
    parts = eq if isinstance(eq, list) else re.split(r"[;,]", str(eq or ""))
    for p in parts:
        p = label(p)
        if p and p.lower() not in ("none", "n/a", "-"):
            add(out, item(cap(p)))
    emp = (il_data or {}).get("employer") or {}
    if any(emp.get(k) for k in ("can_do", "decays", "drill", "watch_for", "refresher")):
        add(out, item(W["employer"], "document"))
    if any((e or {}).get("recorded") for e in ((il_data or {}).get("practicals") or {}).values() if isinstance(e, dict)):
        add(out, item(W["assessor"], "other"))
    return out[:MAX_ITEMS]


def module_items(arch_module, tasks, pracs):
    """one module's list: what to set up (its practicals done in class), then what to print"""
    out = []
    for p in (arch_module or {}).get("practicals") or []:
        if not isinstance(p, dict) or AWAY_WORDS.search(str(p.get("place") or "")):
            continue
        eq = label(p.get("equipment"))
        name = short(p.get("task"))
        if not name:
            continue
        text = "%s: %s" % (name, eq) if eq else name
        k = kind_of("%s %s" % (p.get("task") or "", eq))
        add(out, item(text, k if k != "other" else ("equipment" if eq else "room"), p.get("place")))
    for t in tasks or []:
        if t.get("where") == "tablet":
            continue
        add(out, item("%s: %s %s - %s" % (W["print"], t["code"], W["paper"], short(t["title"], 80)), "document"))
        entry = pracs.get(t.get("il_key") or "")
        if entry:
            add(out, item("%s: %s - %s" % (W["print"], W["cards"], t["code"]), "document"))
            if entry.get("recorded"):
                add(out, item("%s: %s - %s" % (W["print"], W["form"], t["code"]), "document"))
            safety = (entry.get("prebrief") or {}).get("safety") or []
            safety = [safety] if isinstance(safety, str) else [str(x) for x in safety if str(x).strip()]
            if safety:
                add(out, item("%s - %s: %s" % (W["safety"], t["code"], "; ".join(safety[:2])), "other"))
    return out[:MAX_ITEMS]


def prepare(course, arch, intake, infos, mods, il_data):
    """{"course": [...], "modules": {"module01": [...]}} or None when there is nothing to get ready"""
    pracs = (il_data or {}).get("practicals") or {}
    planned = {}
    for x in arch.get("modules") or []:
        try:
            planned[int(str(x.get("module")).lstrip("Mm"))] = x
        except (TypeError, ValueError):
            continue
    by_n = {m["n"]: m for m in mods}
    modules = {}
    for i in infos:
        n = i["n"]
        tasks = []
        for t in (by_n.get(n) or {}).get("tasks") or []:
            tasks.append(dict(t, il_key="%s.%s" % (by_n[n]["mid"], str(t["slide"]["id"]).upper()) if t["slide"].get("kind") == "activity" else ""))
        items = module_items(planned.get(n), tasks, pracs)
        if items:
            modules[i["code"]] = items
    doc = {"course": course_items(intake, il_data), "modules": modules}
    return doc if doc["course"] or modules else None


# ------------------------------------------------------------------ the assessment forms
def critical_steps(entry):
    """[(step text, stop)] - the critical steps of a recorded run's form, as the paper form lists them"""
    return [(str(c["step"]).strip(), bool(c.get("stop")))
            for c in ((entry or {}).get("form") or {}).get("critical") or [] if isinstance(c, dict) and str(c.get("step") or "").strip()]


def definition(entry, cards):
    """the app's form template (forms.mjs) of one recorded run: the paper form's A critical steps (pass / fail), B global
    rating, C decision. No final mark and no pass line - the decision is the assessor's, as on paper (one Not done = Not yet)"""
    crit = [{"key": "step_%d" % i, "label": label(("%s: %s" % (W["stop"], s)) if stop else s), "scale": "pass_fail", "remark": True}
            for i, (s, stop) in enumerate(critical_steps(entry), 1)]
    levels = []
    for x in cards.get("global_rating") or []:
        m = re.match(r"^\s*(\d)\s+(.+)$", str(x))
        if m:
            levels.append({"mark": m.group(1), "meaning": m.group(2).strip()})
    header = [{"key": "run_date", "label": W["date"], "type": "date"}, {"key": "attempt", "label": W["attempt"]}]
    if entry.get("changed_condition"):
        header.append({"key": "changed_condition", "label": label("Changed condition of this run: %s" % entry["changed_condition"])})
    if entry.get("gwo"):
        header.append({"key": "gwo_level", "label": W["gwo"]})
    d = {"header_fields": header,
         "sections": [{"title": W["crit"], "criteria": crit},
                      {"title": W["global"], "criteria": [{"key": "global_rating", "label": W["global_label"], "scale": "0-4", "remark": True}]},
                      {"title": W["decision"], "criteria": [{"key": "decision", "label": W["decision_label"], "scale": "yes_no", "remark": True}]}]}
    if levels:
        d["scale_meanings"] = {"0-4": levels}
    return d


def forms(course, title, mods, il_data, il):
    """[(code, form title, definition)] - one per recorded run of the approved instructor_led.json; [] when there is none"""
    if not il_data or not il.approved(il_data):
        return []
    pracs = il_data.get("practicals") or {}
    cards = il.KNOW["cards"]
    out = []
    for m in mods:
        for t in m["tasks"]:
            entry = pracs.get(il.key(m["mid"], t["slide"]["id"])) if t["slide"].get("kind") == "activity" else None
            if not entry or not entry.get("recorded") or not critical_steps(entry):
                continue
            code = form_code(title, m["mid"], t["code"])
            name = label("%s - %s %s - %s - %s" % (title, m["mid"], t["code"], t["title"], W["sheet"]))
            out.append((code, name, definition(entry, cards)))
    return out[:MAX_FORMS]


def files(course, title, infos, mods, il_data, il):
    """[(path, "json", text)] - the classroom folder of the course's modules folder; nothing when there is nothing to say"""
    root = os.path.join(course, workspace.MODULES)
    arch = load(workspace.claude_path(course, "architecture.json"))
    intake = load(workspace.claude_path(course, "intake.json"))
    dump = lambda d: json.dumps(d, ensure_ascii=False, indent=2) + "\n"
    out = []
    doc = prepare(course, arch, intake, infos, mods, il_data if il_data and il.approved(il_data) else {})
    if doc:
        out.append((os.path.join(root, *PREPARE_PATH.split("/")), "json", dump(doc)))
    for code, name, d in forms(course, title, mods, il_data, il):
        out.append((os.path.join(root, *FORMS_DIR.split("/"), code + ".json"), "json", dump({"code": code, "title": name, "definition": d})))
    return out


# ------------------------------------------------------------------ the checks (the app's own rules)
def definition_problems(d):
    """plain-language problems with a form definition - a port of forms.mjs validateDefinition (no pass-line maximum)"""
    if not isinstance(d, dict):
        return ["definition is not an object"]
    probs = []
    secs = d.get("sections")
    if not isinstance(secs, list) or not secs:
        probs.append("needs at least one section")
    if "header_fields" in d and not isinstance(d["header_fields"], list):
        probs.append("header_fields must be a list (may be empty)")
    fm = d.get("final_mark")
    if "final_mark" in d and fm not in FINAL_MARKS:
        probs.append("final_mark must be one of %s, or left out" % ", ".join(FINAL_MARKS))
    scales = [c.get("scale") for s in secs if isinstance(secs, list) and isinstance(s, dict) for c in (s.get("criteria") or []) if isinstance(c, dict)] \
        if isinstance(secs, list) else []
    if fm == "mean_if_complete" and (len(set(scales)) > 1 or any(s in ("pass_fail", "yes_no") for s in scales)):
        probs.append("mean_if_complete needs every criterion on the same numeric scale")
    if "pass" in d:
        p = d["pass"]
        ok = isinstance(p, dict) and isinstance(p.get("at_least"), (int, float)) and not isinstance(p.get("at_least"), bool) and p["at_least"] >= 0
        if not ok:
            probs.append("pass needs at_least, a number 0 or more")
        if not isinstance(p, dict) or p.get("over") not in ("form", "course_average"):
            probs.append("pass.over must be form or course_average")
        if "final_mark" not in d:
            probs.append("pass needs a final_mark rule to compare with")
        if isinstance(p, dict) and p.get("over") == "course_average" and fm != "mean_if_complete":
            probs.append("pass over course_average works only with mean_if_complete")
    if "scale_meanings" in d:
        sm = d["scale_meanings"]
        if not isinstance(sm, dict):
            probs.append("scale_meanings must be an object keyed by scale")
        else:
            for scale, lst in sm.items():
                if scale not in SCALES:
                    probs.append('scale_meanings: "%s" is not a scale' % scale)
                elif not isinstance(lst, list) or not lst or any(
                        not isinstance(m, dict) or not str(m.get("mark") or "").strip() or not str(m.get("meaning") or "").strip() for m in lst):
                    probs.append("scale_meanings for %s: each entry needs a mark and a meaning" % scale)
    keys, count = set(), 0

    def claim(key, where):
        if not isinstance(key, str) or not KEY.match(key):
            probs.append('%s: key "%s" must be lowercase letters, digits, underscores' % (where, key))
        elif key in keys:
            probs.append('%s: key "%s" is used twice' % (where, key))
        elif key == "rank":
            probs.append('%s: "rank" is reserved' % where)
        else:
            keys.add(key)

    for i, s in enumerate(secs if isinstance(secs, list) else [], 1):
        if not isinstance(s, dict) or not str(s.get("title") or "").strip():
            probs.append("section %d has no title" % i)
        crit = s.get("criteria") if isinstance(s, dict) else None
        if not isinstance(crit, list) or not crit:
            probs.append('section "%s" has no criteria' % ((s or {}).get("title") if isinstance(s, dict) else i))
            continue
        for c in crit:
            count += 1
            c = c if isinstance(c, dict) else {}
            where = 'criterion "%s"' % (c.get("label") or "?")
            claim(c.get("key"), where)
            if not str(c.get("label") or "").strip():
                probs.append("%s has no label" % where)
            if c.get("scale") not in SCALES:
                probs.append("%s: scale must be one of %s" % (where, ", ".join(SCALES)))
            if not isinstance(c.get("remark"), bool):
                probs.append("%s: remark must be true or false" % where)
    if count > MAX_CRITERIA:
        probs.append("at most %d criteria" % MAX_CRITERIA)
    for h in d.get("header_fields") if isinstance(d.get("header_fields"), list) else []:
        h = h if isinstance(h, dict) else {}
        where = 'header field "%s"' % (h.get("label") or "?")
        claim(h.get("key"), where)
        if not str(h.get("label") or "").strip():
            probs.append("%s has no label" % where)
        if "type" in h and h["type"] != "date":
            probs.append("%s: type must be date or left out" % where)
    return probs


def _items_problems(lst, where, probs):
    if lst is None:
        return
    if not isinstance(lst, list):
        probs.append("%s: %s must be a list" % (PREPARE_PATH, where))
        return
    if len(lst) > MAX_ITEMS:
        probs.append("%s: %s has %d items - the app keeps %d and drops the rest" % (PREPARE_PATH, where, len(lst), MAX_ITEMS))
    for n, it in enumerate(lst, 1):
        it = {"label": it} if isinstance(it, str) else it
        if not isinstance(it, dict) or not str(it.get("label") or "").strip():
            probs.append("%s: item %d of %s has no label" % (PREPARE_PATH, n, where))
            continue
        if len(re.sub(r"\s+", " ", str(it["label"])).strip()) > MAX_LABEL:
            probs.append("%s: item %d of %s has a label over %d characters" % (PREPARE_PATH, n, where, MAX_LABEL))
        if "kind" in it and it["kind"] not in PREP_KINDS:
            probs.append('%s: item %d of %s has kind "%s" - use %s' % (PREPARE_PATH, n, where, it["kind"], ", ".join(PREP_KINDS)))
        if it.get("place") and len(str(it["place"]).strip()) > MAX_PLACE:
            probs.append("%s: item %d of %s has a place over %d characters" % (PREPARE_PATH, n, where, MAX_PLACE))
        if "minutes" in it and not (isinstance(it["minutes"], int) and not isinstance(it["minutes"], bool) and 0 < it["minutes"] < 1000):
            probs.append("%s: item %d of %s has minutes the app ignores - a whole number from 1 to 999" % (PREPARE_PATH, n, where))


def folder_problems(folder, module_codes):
    """[problem] of the classroom\\ folder of a course's modules folder (none when it has no such folder)"""
    probs = []
    pp = os.path.join(folder, *PREPARE_PATH.split("/"))
    if os.path.isfile(pp):
        try:
            doc = json.load(io.open(pp, encoding="utf-8"))
        except ValueError:
            doc = None
            probs.append("%s is not valid JSON" % PREPARE_PATH)
        if doc is not None:
            if not isinstance(doc, dict):
                probs.append("%s must be an object: {\"course\": [...], \"modules\": {...}}" % PREPARE_PATH)
            else:
                _items_problems(doc.get("course"), "the course list", probs)
                mods = doc.get("modules") or {}
                if not isinstance(mods, dict):
                    probs.append("%s: \"modules\" must be an object keyed by module code" % PREPARE_PATH)
                else:
                    for code, lst in mods.items():
                        if module_codes and code not in module_codes:
                            probs.append('%s: "%s" is not one of the course\'s modules (%s) - the app leaves its list out'
                                         % (PREPARE_PATH, code, ", ".join(sorted(module_codes)[:6])))
                        _items_problems(lst, "module %s" % code, probs)
    fd = os.path.join(folder, *FORMS_DIR.split("/"))
    names = sorted(f for f in os.listdir(fd) if f.lower().endswith(".json")) if os.path.isdir(fd) else []
    if len(names) > MAX_FORMS:
        probs.append("a course may bring at most %d assessment forms - there are %d" % (MAX_FORMS, len(names)))
    seen = set()
    for f in names:
        path = "%s/%s" % (FORMS_DIR, f)
        try:
            t = json.load(io.open(os.path.join(fd, f), encoding="utf-8"))
        except ValueError:
            probs.append("%s is not valid JSON" % path)
            continue
        d = (t.get("definition") or t) if isinstance(t, dict) else None
        if not isinstance(d, dict) or not isinstance(d.get("sections"), list) or not d["sections"]:
            probs.append("%s is not an assessment form: it has no sections" % path)
            continue
        code = re.sub(r"[^A-Z0-9_.-]", "-", str(t.get("code") or f[:-5]).strip().upper())[:MAX_CODE]
        if not FORM_CODE.match(code):
            probs.append("%s: the form needs a code (letters, digits, - or _)" % path)
            continue
        if code in seen:
            probs.append("%s: the form code %s is used twice" % (path, code))
        seen.add(code)
        for p in definition_problems(d)[:4]:
            probs.append("%s: %s" % (path, p))
    return probs


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("course", help="the course folder (the one that holds modules\\ and working_claude\\)")
    a = ap.parse_args(argv)
    sys.path.insert(0, os.path.join(os.path.dirname(HERE), "compile", "scripts"))
    import additional_materials as am
    import compile_course as cc
    import instructor_led as il
    course = os.path.abspath(a.course)
    arch = load(workspace.claude_path(course, "architecture.json"))
    probs = []
    infos = [cc.module_info(course, arch, d, probs) for d in sorted(os.listdir(os.path.join(course, workspace.MODULES)))
             if re.match(r"^module\d{2}$", d)]
    title = (arch.get("course") or {}).get("title") or os.path.basename(course)
    mods = am.modules_of(course, arch, infos, probs)
    sheet = load(workspace.claude_path(course, "course.build.json"))
    for m in mods:
        m["tasks"] = am.tasks_of(m, sheet)
    for path, _, text in files(course, title, infos, mods, il.load(course), il):
        print("==", os.path.relpath(path, course))
        print(text)
    for p in probs:
        print("note:", p)
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
