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
    p2, d, _, _, _ = fm.parse(m, q)
    if p2:
        probs += ["%s: %s" % (where, x) for x in p2]
        return [], ""
    out, extra = [], ' data-lab-type="%s"' % m
    if m == "true_false":
        out.append('    <div class="lab gi-swipe" data-lab="swipe">')
        for c in shuffle(sid, d["cards"], key=lambda x: x["text"]):
            out.append('      <div class="sw-card" data-key="%s"><p class="sw-st" data-script-field="answer">%s</p>%s</div>'
                       % (k(sid, c["text"], "true" if c["true"] else "false"), e(c["text"]),
                          '<p class="sw-why" data-script-field="answer">%s</p>' % e(c["why"]) if c["why"] else ""))
        out.append("    </div>")
    elif m == "critique":
        out.append('    <div class="lab gi-crit" data-lab="critique">')
        for c in d["claims"]:
            opts = shuffle(sid + c["text"], list(enumerate(c["opts"])), key=lambda x: x[1])
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
