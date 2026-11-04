# -*- coding: utf-8 -*-
"""interact_pages - the trainee screens of the interactive task types (2.74.0), for task_pages.py.

The formats are scripts/interact_formats.py; the runtime is course-task-ux/assets/gb_interact.js (it reads what is built
here). As every task page: the words are the approved script's, each with data-script-field="answer"; the right answers
are keys (classroom-system.json task_page.answer_keys), never words the page shows as right.

What the operator's text cannot say is the build sheet's, per question (working_claude\\script\\MNN.build.json "screens"):
    explore          "model": {"var": {"name", "unit", "min", "max", "step", "start"}, "choice": {"label", "items": {name: {k: v}}},
                               "readouts": [{"name", "unit", "expr", "max", "over", "dec"}], "test": {"label", "rules": [{"if", "say", "fx"}]}}
    line_up          "scene": "m05_deck.kit3d.json", "valves": {"V101": "v101" (the scene's part)}, "pipes": [{"a", "b", "valve",
                     "flow" (a flow part a->b), "back" (b->a)}], "start": "Start cargo pump 2" (the dock's words)
    inspect_round    "scene": "m05_room.kit3d.json", "points": {"thing": "part id"}
                     or "pano": "assets/img/room_360.jpg", "points": {"thing": [yaw, pitch]}   (a real 360-degree photograph)
    take_apart       "scene": "valve.kit3d.json" (merge false), "names": {"part id": "part name"}, "explode": {"part id": [x, y, z]},
                     "xray": ["part id"], "operate": {"label", "states": {"open": {"rot": {"ball": 0}}, "closed": {...}}, "start": "open"}
    test_atmosphere  "hose": 4 (m of hose on deck), "delay": 0.28 (s per m)
    deck_round       "places": {"place": "assets/img/x.jpg"}, "zones": {"fault": [[x %, y %, r %], ...]} - its tap zones on its place's photo
    dress_for_job    "photo": the crew member to dress, "buddy": the colleague to check (both "assets/img/x.jpg"),
                     "slots": {"where it is worn": {"at": [[x %, y %], ...], "label": [x %, y %, "l" | "r"]}} - on "photo",
                     "spots": {"what is seen": [[x %, y %], ...]} - on "buddy", and pictures on the sheets when there are:
                     "stories": {"item": "assets/img/x.jpg"}, "ready": ..., "explain": ...
    lay_out          "photo": the deck from above, "scale": metres per 1 % of its width, "deck": [x0 %, y0 %, x1 %, y1 %] (where
                     pieces can be put down), "places": {"place": [x %, y %]}, "winds": {"wind": [x, y]} (where it blows towards),
                     "sides": {"forward": [x, y]} (a side of the rules, as a direction), and pictures on the sheets when there are:
                     "stories": {"rule": "assets/img/x.jpg"}, "ready": ...
A framed task (deck_round, dress_for_job, lay_out - fm.FRAMED) is its own page, tasks/frame_<id>.html, built from course-task-ux/engines/<type>.html in
its screen's theme (engine_theme.py) and shown in a frame on its question's screen; it reports to the set page, which counts
it as the question's answer (gb_interact.js LAB.frame).
A 3D scene is a 3D-kit spec (course-visuals/kit3d/SPEC.md) - the same parts and look as the deck's 3D slides.
"""
from __future__ import annotations

import io
import json
import os
import sys

import compile_module as cm
import content_script as cs

sys.path.insert(0, os.path.join(os.path.dirname(cs.__file__)))
import interact_formats as fm  # noqa: E402

TYPES = fm.TYPES
THREE_D = ("line_up", "take_apart")                     # always a 3D scene; inspect_round may be a photograph
e, a = cm.e, cm.a
k = cs.gb_key


def needs_3d(q, b):
    m = cs.mech(q)
    return m in THREE_D or (m == "inspect_round" and not (b or {}).get("pano"))


def find_scene(rel, mdir, figdir):
    """a 3D-kit spec named by the build sheet: beside the module's figures, in its assets, or a path from the module"""
    for base in (figdir, os.path.join(mdir, "assets", "fig"), os.path.join(mdir, "assets"), mdir):
        p = os.path.normpath(os.path.join(base or "", rel))
        if base and os.path.isfile(p):
            try:
                with io.open(p, encoding="utf-8") as f:
                    return json.load(f)
            except (OSError, ValueError):
                return None
    return None


def part(head, inner):
    return ['    <div class="part"><p class="phead" data-script-field="answer">%s</p>' % e(head)] + inner + ["    </div>"]


def question_html(n, q, b, mdir, figdir, probs, w, shuffle, opt_buttons):
    """the markup of one question of an interactive type: (lines, extra attributes of the section)"""
    sid, m = q["id"], cs.mech(q)
    where = "%s (%s)" % (q.get("set") or "", sid)
    p2, d, _, _, words = fm.parse(m, q)
    if p2:
        probs += ["%s: %s" % (where, x) for x in p2]
        return [], ""
    if m in fm.FRAMED:
        return framed(q, b, d, mdir, probs, where, shuffle, words)
    out, extra = [], ' data-lab-type="%s"' % m
    if m == "true_false":
        import task_pages as tp
        pics = tp.answer_pictures(q, b, [c["text"] for c in d["cards"]], mdir, probs, where)   # a picture behind each card's claim
        out.append('    <div class="lab gi-swipe" data-lab="swipe">')
        for c in shuffle(sid, d["cards"], key=lambda x: x["text"]):
            out.append('      <div class="sw-card%s" data-key="%s">%s<p class="sw-st" data-script-field="answer">%s</p>%s</div>'
                       % (" pic" if pics else "", k(sid, c["text"], "true" if c["true"] else "false"),
                          pics.get(c["text"], "").replace('class="tl-img"', 'class="sw-img"'), e(c["text"]),
                          '<p class="sw-why" data-script-field="answer">%s</p>' % e(c["why"]) if c["why"] else ""))
        out.append("    </div>")
    elif m == "critique":
        out.append('    <div class="lab gi-crit" data-lab="critique">')
        for c in d["claims"]:
            # 2.74.1 - every claim offers "keep it as written", last, whether or not it is right: a sheet without it told
            # the trainee the claim was wrong (found in the chemical tanker course's redo)
            fixes = [(i, o) for i, o in enumerate(c["opts"]) if o]
            opts = shuffle(sid + c["text"], fixes, key=lambda x: x[1]) + [(c["opts"].index("") if "" in c["opts"] else -1, "")]
            btns = "".join('<button type="button" class="cr-o" data-o="%s" data-key="%s"%s>%s</button>'
                           % (a(o or "*"), k(sid, c["text"] + " => " + (o or "*"), 1 if i == c["right"] else 0),
                              ' data-script-field="answer"' if o else "", e(o)) for i, o in opts)
            out.append('      <div class="cr-claim"><p class="cr-text" data-script-field="answer">%s</p>%s</div>' % (e(c["text"]), btns))
        out.append("    </div>")
    elif m == "calculate":
        step = 10 ** -d["dec"]
        ks = sorted({k(sid, d["unit"], "%.*f" % (dd, v)) for v, dd in fm.steps(d["value"] - d["tol"], d["value"] + d["tol"], step)})
        out.append('    <div class="lab gi-calc" data-lab="calc" data-unit="%s" data-dec="%d" data-keys="%s">' % (a(d["unit"]), d["dec"], " ".join(ks)))
        if d["reads"]:
            out.append('      <div class="cl-dev">%s</div>' % "".join('<p class="cl-read" data-script-field="answer">%s</p>' % e(r) for r in d["reads"]))
        if d["rows"]:
            out.append('      <table class="cl-sheet">%s</table>' % "".join(
                "<tr>%s</tr>" % "".join('<%s data-script-field="answer">%s</%s>' % (t, e(c), t) for c in r)
                for r, t in ((r, "th" if i == 0 else "td") for i, r in enumerate(d["rows"]))))
        out.append("    </div>")
    elif m == "predict":
        Y = d["y"]
        ks = sorted({k(sid, Y[1] or "y", "%.*f" % (d["dec"], v)) for v, _ in fm.steps(d["value"] - d["tol"], d["value"] + d["tol"], 10 ** -d["dec"])})
        world = {"x": d["x"], "y": Y, "at": d["at"], "dec": d["dec"], "given": d["given"], "c": fm.b64(d["curve"])}
        out.append('    <div class="lab gi-pred" data-lab="predict" data-world="%s" data-keys="%s">' % (fm.b64(world), " ".join(ks)))
        out.append('      <span class="pr-given" data-script-field="answer">%s</span><span class="pr-given" data-script-field="answer">%s</span>'
                   % (e(d["x"][0]), e(Y[0])))
        out += ['      <span class="pr-given" data-script-field="answer">%s</span>' % e(g[2]) for g in d["given"] if g[2]]
        out.append("    </div>")
    elif m == "explore":
        model = b.get("model") or {}
        if not model.get("var"):
            probs.append("%s: 'explore and find' needs its model in the build sheet: \"model\": {\"var\": {...}, \"readouts\": [...], \"test\": {...}}" % where)
            return [], ""
        V = model["var"]
        ch = (model.get("choice") or {}).get("items") or {}
        names = list(ch) or [""]
        for i, f in enumerate(d["finds"], 1):
            if f["only"] and f["only"] not in ch:
                probs.append("%s: \"%s\" names %r - not one of the model's choices (%s)" % (where, f["text"], f["only"], ", ".join(ch) or "none"))
            test = fm.condition(f["cond"])
            ks = []
            for c in names:
                if f["only"] and c != f["only"]:
                    continue
                for v, dec in fm.steps(V["min"], V["max"], V["step"]):
                    env = dict(ch.get(c) or {}, x=v)
                    env[V.get("id", "x")] = v
                    try:
                        if test(env) is True:
                            ks.append(k(sid, "find%d" % i, "%s|%.*f" % (c, dec, v)))
                    except Exception:
                        probs.append("%s: the condition of \"%s\" uses a name the model does not have" % (where, f["text"]))
                        break
            if not ks:
                probs.append("%s: no setting of the model meets \"%s\" - the challenge cannot be solved" % (where, f["text"]))
            out += part(f["text"], ['      <div class="lab" data-lab="explore" data-n="%d" data-only="%s" data-hide="%s" data-keys="%s"></div>'
                                    % (i, a(f["only"]), a("|".join(f["hide"])), " ".join(sorted(set(ks))))])
        out.append('    <div class="gi-model" data-world="%s"></div>' % fm.b64(model))     # under the challenge it answers
    elif m == "investigate":
        out.append('    <div class="lab gi-inv" data-lab="evidence" data-min="%d">' % d["min"])
        for s_ in d["sources"]:
            out.append('      <button type="button" class="iv-src" data-key="%s"><span class="iv-tg"%s>%s</span><span class="iv-tl" data-script-field="answer">%s</span>'
                       '<span class="iv-raw" data-script-field="answer">%s</span></button>'
                       % (k(sid, s_["title"], 1 if s_["rel"] else 0), ' data-script-field="answer"' if s_["tag"] else "", e(s_["tag"]),
                          e(s_["title"]), e(s_["content"])))
        out.append("    </div>")
        out += opt_buttons(sid, q)
    elif m == "line_up":
        spec = find_scene(b.get("scene") or "", mdir, figdir) if b.get("scene") else None
        if not spec:
            probs.append("%s: 'line it up' needs its deck in the build sheet: \"scene\": \"<name>.kit3d.json\" (found beside the figures)" % where)
            return [], ""
        valves, pipes = b.get("valves") or {}, b.get("pipes") or []
        tags = [v["tag"] for v in d["valves"]]
        for t in tags:
            if t not in valves:
                probs.append("%s: valve %s is not placed - the build sheet's \"valves\" names the scene's part for it" % (where, t))
        nodes = {x for p in pipes for x in (p.get("a"), p.get("b"))}
        for n_ in [d["source"], d["goal"]] + d["out"]:
            if n_ not in nodes:
                probs.append("%s: %r is not a node of the build sheet's \"pipes\" - name it exactly as the script does" % (where, n_))
        world = {"spec": spec, "valves": valves, "pipes": pipes, "source": d["source"], "goal": d["goal"], "out": d["out"],
                 "start": {v["tag"]: v["start"] for v in d["valves"]}}
        out.append('    <div class="lab gi-line" data-lab="lineup" data-world="%s" data-start="%s">' % (fm.b64(world), a(b.get("start") or "")))
        out.append('      <ul class="lu-orders"><li><span data-script-field="answer">%s</span> → <span data-script-field="answer">%s</span></li>%s</ul>'
                   % (e(d["source"]), e(d["goal"]), "".join('<li>✕ <span data-script-field="answer">%s</span></li>' % e(x) for x in d["out"])))
        out.append('      <ul class="lu-valves">%s</ul>' % "".join(
            '<li data-tag="%s"><b data-script-field="answer">%s</b> <span class="lu-name" data-script-field="answer">%s</span></li>'
            % (a(v["tag"]), e(v["tag"]), e(v["name"])) for v in d["valves"]))
        out.append("    </div>")
    elif m == "inspect_round":
        pts = b.get("points") or {}
        world = {"points": pts}
        if b.get("pano"):
            world["pano"] = "../" + b["pano"].lstrip("/").replace("\\", "/")
            if not os.path.isfile(os.path.join(mdir, b["pano"])):
                probs.append("%s: the 360-degree photograph %s is not in the module" % (where, b["pano"]))
        else:
            spec = find_scene(b.get("scene") or "", mdir, figdir) if b.get("scene") else None
            if not spec:
                probs.append("%s: 'inspection round' needs its space in the build sheet: \"scene\": \"<name>.kit3d.json\" or \"pano\": a 360-degree photograph" % where)
                return [], ""
            world["spec"] = spec
        for t in d["things"]:
            if t["name"] not in pts:
                probs.append("%s: %r has no place in the space - the build sheet's \"points\" names it" % (where, t["name"]))
        need = min(len(d["things"]), max(3, (len(d["things"]) + 1) // 2))
        out.append('    <div class="lab gi-insp" data-lab="inspect" data-world="%s" data-need="%d">' % (fm.b64(world), need))
        for t in d["things"]:
            out.append('      <div class="in-thing" data-key="%s"><b data-script-field="answer">%s</b><p data-script-field="answer">%s</p></div>'
                       % (k(sid, t["name"], "report" if t["problem"] else "fine"), e(t["name"]), e(t["says"])))
        out.append("    </div>")
    elif m == "take_apart":
        spec = find_scene(b.get("scene") or "", mdir, figdir) if b.get("scene") else None
        if not spec:
            probs.append("%s: 'take it apart' needs its model in the build sheet: \"scene\": \"<name>.kit3d.json\"" % where)
            return [], ""
        spec = dict(spec, merge=False)                   # each part moves on its own when the model is pulled apart
        names = b.get("names") or {}
        for p_ in d["parts"]:
            if p_["name"] not in names.values():
                probs.append("%s: part %r is not in the model - the build sheet's \"names\" gives it a part of the scene" % (where, p_["name"]))
        states = ((b.get("operate") or {}).get("states") or {})
        world = {"spec": spec, "names": names, "explode": b.get("explode") or {}, "xray": b.get("xray") or [], "operate": b.get("operate")}
        for s_ in d["steps"]:
            if s_["kind"] == "set" and s_["answer"] not in states:
                probs.append("%s: \"%s\" => %r - not one of the positions the build sheet's \"operate\" has (%s)" % (where, s_["ask"], s_["answer"], ", ".join(states) or "none"))
            out += part(s_["ask"], ['      <div class="lab" data-lab="takeapart" data-step="%s" data-ask="%s" data-key="%s"></div>'
                                    % (s_["kind"], a(s_["ask"]), k(sid, s_["ask"], s_["answer"]))])
        out.append('    <div class="gi-model3d" data-world="%s">%s</div>' % (fm.b64(world), "".join(      # under the step it answers
            '<p class="ta-part"><b data-script-field="answer">%s</b> <span data-script-field="answer">%s</span></p>' % (e(p_["name"]), e(p_["says"]))
            for p_ in d["parts"] if p_["says"]) + "".join(
            '<p class="ta-part"><b data-script-field="answer">%s</b></p>' % e(p_["name"]) for p_ in d["parts"] if not p_["says"])))
    elif m == "test_atmosphere":
        world = {"space": d["space"], "depth": d["depth"], "hose": b.get("hose", 4), "delay": b.get("delay", 0.28), "gases": d["gases"]}
        keys = []
        for i, L in enumerate(d["levels"]):
            keys.append(" ".join(sorted({k(sid, "L%d" % i, "%.1f" % (x * 0.5)) for x in range(int(round((L - d["band"]) * 2)), int(round((L + d["band"]) * 2)) + 1) if 0 <= x * 0.5 < d["depth"]})))
        out.append('    <div class="lab gi-atm" data-lab="atmosphere" data-world="%s" data-levels="%d" %s>'
                   % (fm.b64(world), len(keys), " ".join('data-keys-%d="%s"' % (i, x) for i, x in enumerate(keys))))
        out.append('      <p class="at-g" data-script-field="answer">%s</p>' % e(d["space"]))
        out += ['      <p class="at-g" data-script-field="answer">%s</p>' % e(g["name"]) for g in d["gases"]]
        out.append("    </div>")
    return out, extra


def key_lines(q, b, w):
    """the instructor's answer key (answer_key.py) for an interactive type - what is right, in the script's words"""
    m = cs.mech(q)
    p2, d, _, _, _ = fm.parse(m, q)
    if p2:
        return []
    if m == "true_false":
        return ["%s – <b>%s</b>" % (e(c["text"]), "true" if c["true"] else "false") for c in d["cards"]]
    if m == "critique":
        return ["%s → <b>%s</b>" % (e(c["text"]), e(c["opts"][c["right"]]) or "right as written") for c in d["claims"]]
    if m == "calculate":
        return ["<b>%g %s</b> ± %g" % (d["value"], e(d["unit"]), d["tol"])]
    if m == "predict":
        return ["<b>%g ± %g %s</b> at %g %s" % (d["value"], d["tol"], e(d["y"][1]), d["at"], e(d["x"][1]))]
    if m == "explore":
        return ["%s → <b>%s</b>" % (e(f["text"]), e("; ".join(x for x in [f["only"], f["cond"]] if x))) for f in d["finds"]]
    if m == "investigate":
        return ["Evidence: <b>%s</b>" % e("; ".join(s["title"] for s in d["sources"] if s["rel"]))]
    if m == "line_up":
        return ["From <b>%s</b> to <b>%s</b>, keeping out %s - any line-up that does it; the valves as found: %s"
                % (e(d["source"]), e(d["goal"]), e("; ".join(d["out"])) or "nothing", e(", ".join("%s %s" % (v["tag"], v["start"]) for v in d["valves"])))]
    if m == "inspect_round":
        return ["Problems: <b>%s</b>" % e("; ".join(t["name"] for t in d["things"] if t["problem"]))]
    if m == "take_apart":
        return ["%s → <b>%s</b>" % (e(s["ask"]), e(s["answer"])) for s in d["steps"]]
    if m == "test_atmosphere":
        return ["A fresh reading at <b>%s m</b> (± %g m)" % (e("; ".join("%g" % x for x in d["levels"])), d["band"])]
    return []


# ------------------------------------------------------------------ the framed tasks (course-task-ux/engines)
ENGINES = os.path.join(cm.SKILLS, "course-task-ux", "engines")
sys.path.insert(0, os.path.join(cm.SKILLS, "course-task-ux", "scripts"))
import engine_theme  # noqa: E402  - the one colour code of the richer tasks


def photo_of(rel, mdir, probs, where, what):
    """a photograph named by the build sheet: (its path from tasks/, "w:h") - None, said, when it is not there or has no record"""
    rel = (rel or "").replace("\\", "/")
    import task_pages
    size = task_pages.image_size(os.path.join(mdir, rel)) if rel and os.path.isfile(os.path.join(mdir, rel)) else None
    if not rel or not size:
        probs.append("%s: %s needs its photograph in the build sheet - %s is not a picture in the module folder" % (where, what, rel or "none"))
        return None
    if not cm.photo_meta(mdir, rel):
        probs.append("%s: the photograph %s has no record in assets/img/_photo_meta.json" % (where, rel))
    return "../" + rel, "%d:%d" % size


def zones_of(v):
    try:
        z = [[float(x) for x in c] for c in v]
    except (TypeError, ValueError):
        return None
    return z if z and all(len(c) == 3 and 0 <= c[0] <= 100 and 0 <= c[1] <= 100 and 0 < c[2] <= 50 for c in z) else None


def deck_round_data(q, b, d, mdir, probs, where, shuffle):
    sid, places, faults = q["id"], [], []
    pics, zones = b.get("places") or {}, b.get("zones") or {}
    for i, p in enumerate(d["places"], 1):
        ph = photo_of(pics.get(p["name"]), mdir, probs, where, "the place %r" % p["name"])
        if ph:
            places.append({"id": "p%d" % i, "name": p["name"], "src": ph[0], "aspect": ph[1]})
    pid = {p["name"]: p["id"] for p in places}
    for i, f in enumerate(d["faults"], 1):
        z = zones_of(zones.get(f["name"]))
        if not z:
            probs.append("%s: the fault %r needs its tap zones on the photograph - \"zones\": {\"%s\": [[x %%, y %%, r %%], ...]}"
                         % (where, f["name"], f["name"]))
            continue
        faults.append({"id": "f%d" % i, "stop": pid.get(f["place"], ""), "name": f["name"], "label": f["label"], "see": f["see"],
                       "hint": f["hint"], "why": f["why"], "zones": z, "ch": shuffle(sid + f["name"], f["do"], key=lambda x: x),
                       "key": k(sid, f["name"] + " => " + f["right"], 1)})
    return {"id": sid, "title": q.get("question", ""), "eye": d["context"], "ask": q.get("question", ""), "intro": d["intro"],
            "places": places, "faults": faults}


def points_of(v):
    try:
        p = [[float(x) for x in c] for c in v]
    except (TypeError, ValueError):
        return None
    return p if p and all(len(c) == 2 and 0 <= c[0] <= 100 and 0 <= c[1] <= 100 for c in p) else None


def dress_for_job_data(q, b, d, mdir, probs, where, shuffle):
    sid = q["id"]
    first = photo_of(b.get("photo"), mdir, probs, where, "the crew member to dress (\"photo\")")
    second = photo_of(b.get("buddy"), mdir, probs, where, "the colleague to check (\"buddy\")")
    stories = b.get("stories") or {}

    def pic(rel, what):                                      # a picture on a sheet: there when the build sheet names one
        p = photo_of(rel, mdir, probs, where, what) if rel else None
        return p[0] if p else None
    slots, sheet = [], b.get("slots") or {}
    for name in dict.fromkeys(x["slot"] for x in d["items"]):
        s, lab = sheet.get(name) or {}, (sheet.get(name) or {}).get("label") or []
        pts = points_of(s.get("at"))
        if not pts or len(lab) != 3 or lab[2] not in ("l", "r") or not points_of([lab[:2]]):
            probs.append("%s: the place %r needs where it shows on the photograph - \"slots\": {\"%s\": {\"at\": [[x %%, y %%]], "
                         "\"label\": [x %%, y %%, \"l\" or \"r\"]}}" % (where, name, name))
            continue
        slots.append({"name": name, "pts": pts, "lx": float(lab[0]), "ly": float(lab[1]), "side": lab[2]})
    iid = {x["name"]: "i%d" % n for n, x in enumerate(d["items"], 1)}
    items = [{"id": iid[x["name"]], "name": x["name"], "short": x["short"], "slot": x["slot"], "story": x["story"],
              "pic": pic(stories.get(x["name"]), "the story of %r" % x["name"]), "key": k(sid, "wear " + x["name"], 1 if x["need"] else 0)}
             for x in shuffle(sid + " rack", d["items"], key=lambda x: x["name"])]
    spots, at = [], b.get("spots") or {}
    for n, s in enumerate(d["spots"], 1):
        pts = points_of(at.get(s["seen"]))
        if not pts:
            probs.append("%s: %r needs where it is on the colleague's photograph - \"spots\": {\"%s\": [[x %%, y %%], ...]}"
                         % (where, s["seen"], s["seen"]))
            continue
        spots.append({"id": "s%d" % n, "seen": s["seen"], "why": s["why"], "pts": pts, "key": k(sid, "fault " + s["seen"], 1 if s["fault"] else 0)})
    return {"id": sid, "title": q.get("question", ""), "eye": d["context"], "ask": q.get("question", ""), "intro": d["intro"],
            "photo": first and {"src": first[0], "aspect": first[1], "alt": d["intro"]["title"]},
            "buddy": second and {"src": second[0], "aspect": second[1], "alt": d["check"]["ask"]},
            "slots": slots, "items": items,
            "groups": [{"title": g["title"], "why": g["why"], "items": [iid[x["name"]] for x in d["items"] if x["group"] == g["title"]]}
                       for g in d["groups"]],
            "needs": [{"item": iid[r["item"]], "on": iid[r["on"]], "say": r["say"]} for r in d["needs"]],
            "one": [{"items": [iid[x] for x in r["items"]], "say": r["say"]} for r in d["one"]],
            "ready": dict(d["ready"], pic=pic(b.get("ready"), "the ready sheet (\"ready\")")),
            "check": d["check"], "faults": sum(1 for s in d["spots"] if s["fault"]), "spots": spots,
            "why": {"ask": d["ask"], "ch": shuffle(sid + " why", d["reasons"], key=lambda x: x), "key": k(sid, "why => " + d["right"], 1),
                    "title": d["explain"]["title"], "text": d["explain"]["text"], "pic": pic(b.get("explain"), "the answer's sheet (\"explain\")")}}


def vector_of(v):
    try:
        x, y = float(v[0]), float(v[1])
    except (TypeError, ValueError, IndexError, KeyError):
        return None
    n = (x * x + y * y) ** .5
    return [round(x / n, 4), round(y / n, 4)] if n and len(v) == 2 else None


def lay_out_data(q, b, d, mdir, probs, where, shuffle):
    sid = q["id"]
    ph = photo_of(b.get("photo"), mdir, probs, where, "the deck from above (\"photo\")")
    stories = b.get("stories") or {}

    def pic(rel, what):
        p = photo_of(rel, mdir, probs, where, what) if rel else None
        return p[0] if p else None
    scale, deck = b.get("scale"), b.get("deck") or [0, 0, 100, 100]
    if not isinstance(scale, (int, float)) or scale <= 0:
        probs.append("%s: lay out needs the photo's scale - \"scale\": metres per 1 %% of its width" % where)
    if not points_of([deck[:2], deck[2:]]) or len(deck) != 4 or deck[0] >= deck[2] or deck[1] >= deck[3]:
        probs.append("%s: \"deck\": [x0 %%, y0 %%, x1 %%, y1 %%] - where pieces can be put down" % where)
    at, places = b.get("places") or {}, []
    for n, name in enumerate(d["places"], 1):
        p = points_of([at.get(name)]) if at.get(name) is not None else None
        if not p:
            probs.append("%s: the place %r needs where it is on the photograph - \"places\": {\"%s\": [x %%, y %%]}" % (where, name, name))
            continue
        places.append({"id": "p%d" % n, "name": name, "x": p[0][0], "y": p[0][1]})
    pid = {p["name"]: p["id"] for p in places}
    wv, winds = b.get("winds") or {}, []
    for w in d["winds"]:
        v = vector_of(wv.get(w["from"]))
        if not v:
            probs.append("%s: the wind %r needs where it blows towards on the photograph - \"winds\": {\"%s\": [x, y]}" % (where, w["from"], w["from"]))
            continue
        winds.append(dict(w, v=v))
    sv, sides = b.get("sides") or {}, {}
    for x in d["rules"]:
        for s in x["side"]:
            if s in fm.SIDES_OF_WIND or s in sides:
                continue
            v = vector_of(sv.get(s))
            if v:
                sides[s] = v
            else:
                probs.append("%s: the side %r needs its direction on the photograph - \"sides\": {\"%s\": [x, y]}" % (where, s, s))
    byshort = {x["short"]: x for x in d["items"]}
    items = [{"id": "i%d" % n, "name": x["name"], "short": x["short"], "ab": x["ab"], "key": k(sid, "on deck " + x["name"], 1 if x["belongs"] else 0)}
             for n, x in enumerate(shuffle(sid + " tray", d["items"], key=lambda x: x["name"]), 1)]
    rules = [{"title": x["title"], "who": [k(sid, x["title"] + " => " + byshort[i]["name"], 1) for i in x["items"] if i in byshort],
              "place": pid.get(x["place"], ""), "lo": (x["at"] or (0, 0))[0], "hi": (x["at"] or (0, 0))[1], "side": x["side"],
              "why": x["why"], "story": x["story"], "pic": pic(stories.get(x["title"]), "the story of %r" % x["title"])} for x in d["rules"]]
    u = d["unsafe"]
    return {"id": sid, "title": q.get("question", ""), "eye": d["context"], "ask": q.get("question", ""), "intro": d["intro"],
            "photo": ph and {"src": ph[0], "aspect": ph[1], "alt": d["intro"]["title"]}, "scale": scale, "deck": deck,
            "readings": d["readings"], "places": places, "winds": winds, "sides": sides, "items": items, "rules": rules,
            "unsafe": u and dict(u, pic=pic(stories.get(u["title"]), "the story of %r" % u["title"])),
            "leak": d["leak"] and {"place": pid.get(d["leak"]["place"], ""), "say": d["leak"]["say"]},
            "ready": dict(d["ready"], pic=pic(b.get("ready"), "the ready sheet (\"ready\")"))}


FRAMED_DATA = {"deck_round": deck_round_data, "dress_for_job": dress_for_job_data, "lay_out": lay_out_data}


def framed(q, b, d, mdir, probs, where, shuffle, words):
    """a richer task: its own page (tasks/frame_<id>.html, from the engine template, in the screen's theme), in a frame on
    the question's screen. The page reports to the set page (gb_interact.js LAB.frame), which counts it as the question's
    answer. Its approved words are listed here, built from the same data, for check_script_match"""
    m, sid = cs.mech(q), q["id"]
    data = FRAMED_DATA[m](q, b, d, mdir, probs, where, shuffle)
    theme = "light" if b.get("_theme") == "th-w" else "dark"
    src = io.open(os.path.join(ENGINES, m + ".html"), encoding="utf-8").read()
    lab = io.open(os.path.join(ENGINES, "gb_lab.css"), encoding="utf-8").read()
    i, j = src.index("<style>") + len("<style>"), src.index("</style>")
    src = src[:i] + engine_theme.page_css(theme, src[i:j]) + src[j:]
    lang = cm.lang_code(b.get("_lang") or "English") or "en"
    page = (src.replace("{{LANG}}", lang).replace("{{TITLE}}", e(q.get("question", "")))
            .replace("{{LAB_CSS}}", "gb_lab_white.css" if theme == "light" else "gb_lab_navy.css")
            .replace("{{WORDS}}", "").replace("{{DATA}}", json.dumps(data, ensure_ascii=False).replace("</", "<\\/")))
    tdir = os.path.join(mdir, "tasks")
    os.makedirs(tdir, exist_ok=True)
    io.open(os.path.join(tdir, "frame_%s.html" % sid), "w", encoding="utf-8", newline="\n").write(page)
    assert lab                                                     # the engine's style ships as assets/gb_lab_*.css
    out = ['    <div class="lab gi-frame" data-lab="frame"><iframe src="../tasks/frame_%s.html" title="%s" allow="fullscreen"></iframe></div>'
           % (sid, a(q.get("question", ""))),
           '    <template>%s</template>' % "".join('<span data-script-field="answer">%s</span>' % e(x) for x in words)]
    return out, ' data-lab-type="%s" data-frame="1"' % m
