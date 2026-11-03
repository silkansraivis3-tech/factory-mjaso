#!/usr/bin/env python
"""The empty templates: every slide and task blueprint of knowledge/blueprints.json drawn with no words of its own - only
where its Title, Text, Info, Picture, Animation and 3D go, what fills each, and its live reference.

    blueprints.py [--out <file>]     write it (default: <repo>/design/template-blueprints/index.html)
    blueprints.py --check            exit 1 when the page is not what blueprints.json gives, or a blueprint is wrong
"""
import argparse, html, io, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
REPO = os.path.dirname(os.path.dirname(os.path.dirname(SKILL)))
BP = json.load(io.open(os.path.join(SKILL, "knowledge", "blueprints.json"), encoding="utf-8"))
LAYOUTS = json.load(io.open(os.path.join(SKILL, "knowledge", "layout-templates.json"), encoding="utf-8"))
OUT = os.path.join(REPO, "design", "template-blueprints", "index.html")
KINDS = list(BP["kinds"])
e = html.escape


def resolved(b, pool):
    """a mirror blueprint is its base with every row turned round"""
    if "mirror" not in b:
        return b
    base = dict(next(x for x in pool if x["id"] == b["mirror"]))
    base.update({k: v for k, v in b.items() if k != "mirror"})
    base["grid"] = [" ".join(reversed(r.split())) for r in base["grid"]]
    if base.get("cols"):
        base["cols"] = " ".join(reversed(base["cols"].split()))
    return base


def framed(b):
    """a task in the engine frame takes the frame's grid and its title slot"""
    if b.get("frame") not in BP["frames"]:
        return b
    f = BP["frames"][b["frame"]]
    out = dict(f, **{k: v for k, v in b.items() if k != "fill"})
    out["fill"] = dict(f["fill"], **b["fill"])
    return out


def problems():
    probs = []
    slides = [resolved(b, BP["slides"]) for b in BP["slides"]]
    tasks = [framed(b) for b in BP["tasks"]]
    have = {b["id"] for b in slides}
    for tid, t in LAYOUTS["templates"].items():
        for v in t["variants"]:
            if "%s.%s" % (tid, v) not in have:
                probs.append("the template %s.%s has no blueprint" % (tid, v))
    for b in slides + tasks:
        cells = set(" ".join(b["grid"]).split()) - {"."}
        if b.get("bg"):
            cells.add(b["bg"])
        if cells != set(b["fill"]) - ({"t"} if b in slides and "t" not in cells else set()):
            probs.append("%s: its grid has %s, its fill names %s" % (b["id"], sorted(cells), sorted(b["fill"])))
        if len({len(r.split()) for r in b["grid"]}) != 1:
            probs.append("%s: its grid rows are not all as wide" % b["id"])
        for k, (kind, _) in b["fill"].items():
            if kind not in KINDS:
                probs.append("%s: slot %s is a %r - the kinds are %s" % (b["id"], k, kind, ", ".join(KINDS)))
        if not b.get("for"):
            probs.append("%s: it does not say what information it is for" % b["id"])
    deck = io.open(os.path.join(REPO, "design", "slide-templates", "presentation", "index.html"), encoding="utf-8").read()
    secs = dict(re.findall(r'<section [^>]*id="(p\d+)"[^>]*data-template="([\w-]+)\.v1"', deck))
    for b in slides:
        r = b.get("ref", "")
        if r and secs.get(r.split("#")[1]) != b["id"].split(".")[0]:
            probs.append("%s: its reference %s is not that template in the reference deck" % (b["id"], r))
    for tid in LAYOUTS["templates"]:
        if tid not in secs.values():
            probs.append("the template %s has no slide in the reference deck design/slide-templates" % tid)
    live = io.open(os.path.join(REPO, "design", "task-templates", "live", "index.html"), encoding="utf-8").read()
    for b in tasks:
        kind, ref = b["ref"].split("#")
        if kind == "engines" and not os.path.isfile(os.path.join(REPO, "design", "task-templates", "engines", "demo", "tasks", ref + ".html")):
            probs.append("%s: its reference engines/demo/tasks/%s.html is not there" % (b["id"], ref))
        if kind == "live" and not re.search(r"\b%s\b" % ref, live):
            probs.append("%s: the live reference has no screen %s" % (b["id"], ref))
    return probs


CSS = """
:root{--navy:#0A2463;--blue:#53A7DB;--steel:#415C8F;--grey:#E7EBF0;--bg:#F7F8FA;--card:#fff;--fg:#0A2463;--dim:#415C8F;--line:#DCE3EB;
--k-title:#0A2463;--k-text:#415C8F;--k-info:#7C8DA8;--k-picture:#53A7DB;--k-animation:#E9A51E;--k-3d:#2FB980}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#081a45;--card:#0d2a66;--fg:#F2F6FC;--dim:#A9BCD9;--line:#1E3F80;--k-title:#E7EBF0;--k-text:#A9BCD9}}
:root[data-theme="dark"]{--bg:#081a45;--card:#0d2a66;--fg:#F2F6FC;--dim:#A9BCD9;--line:#1E3F80;--k-title:#E7EBF0;--k-text:#A9BCD9}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:500 15px/1.5 Raleway,"Segoe UI",Arial,sans-serif}
.wrap{max-width:1240px;margin:0 auto;padding:0 16px 48px}header{padding:40px 0 18px}h1{margin:0;font-size:clamp(28px,4vw,44px);font-weight:800}
header p{max-width:760px;color:var(--dim)}h2{margin:34px 0 4px;font-size:24px}.lead{color:var(--dim);margin:0 0 14px}
.legend{display:flex;flex-wrap:wrap;gap:8px;margin-top:10px}.legend span{display:inline-flex;gap:6px;align-items:center;padding:4px 10px;border-radius:99px;
background:var(--card);border:1px solid var(--line);font-weight:700;font-size:13px}.legend i{width:12px;height:12px;border-radius:3px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:14px}
.bp{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:12px}
.bp h3{margin:0;font-size:15px}.bp .for{margin:2px 0 8px;color:var(--dim);font-size:13px}
.fr{position:relative;aspect-ratio:16/10;border-radius:8px;background:var(--bg);border:1px solid var(--line);padding:6%;display:flex;flex-direction:column;gap:4%;overflow:hidden}
.fr .tt{flex:none;height:15%;min-height:20px;width:55%}.fr .body{flex:1;display:grid;gap:4%;min-height:0;position:relative}
.s{border:2px dashed var(--c);background:color-mix(in srgb,var(--c) 14%,transparent);border-radius:6px;display:grid;place-items:center;
color:var(--c);font-weight:800;font-size:11px;line-height:1.1;letter-spacing:.06em;text-transform:uppercase;min-height:0;min-width:0;text-align:center;padding:2px}
.bgs{position:absolute;inset:0;border-radius:0;border-width:0}.fr.hasbg .body,.fr.hasbg .tt{z-index:1}
.k-Title{--c:var(--k-title)}.k-Text{--c:var(--k-text)}.k-Info{--c:var(--k-info)}.k-Picture{--c:var(--k-picture)}.k-Animation{--c:var(--k-animation)}.k-3D{--c:var(--k-3d)}
.bp ul{margin:8px 0 0;padding:0;list-style:none;font-size:12.5px;color:var(--dim)}.bp li b{color:var(--fg)}
.bp .ref{margin-top:6px;font-size:12px;color:var(--dim)}.bp .ref code{font-size:11.5px}
.go{flex:none;height:9%;border-radius:6px;background:color-mix(in srgb,var(--k-title) 70%,transparent)}
"""


def card(b, title_row):
    cells = set(" ".join(b["grid"]).split()) - {"."}
    areas = " ".join("'%s'" % r for r in b["grid"])
    rows = b.get("rows") or " ".join("1fr" if set(r.split()) == {"t"} else "4fr" for r in b["grid"])    # a title row is a title's height
    style = "grid-template-areas:%s;grid-template-columns:%s;grid-template-rows:%s" % (
        areas, b.get("cols") or "1fr " * len(b["grid"][0].split()), rows)
    slots = "".join('<div class="s k-%s" style="grid-area:%s">%s</div>' % (b["fill"][c][0], c, e(b["fill"][c][0])) for c in sorted(cells))
    bg = '<div class="s bgs k-%s">%s</div>' % (b["fill"][b["bg"]][0], e(b["fill"][b["bg"]][0])) if b.get("bg") else ""
    tt = '<div class="s tt k-Title">Title</div>' if title_row else ""
    go = '<div class="go"></div>' if b.get("go") else ""
    order = sorted(b["fill"], key=lambda c: (" ".join(b["grid"]).split() + [c]).index(c))     # in reading order
    items = "".join("<li><b>%s</b> - %s</li>" % (e(b["fill"][c][0]), e(b["fill"][c][1])) for c in order)
    if title_row:
        items = "<li><b>Title</b> - title</li>" + items
    note = "<li><b>Notes</b> - %s</li>" % e(b["notes"]) if b.get("notes") else ""
    ref = '<div class="ref">Reference: <code>%s</code></div>' % e(b["ref"]) if b.get("ref") else ""
    return ('<article class="bp"><h3>%s</h3><p class="for">%s</p><div class="fr%s">%s%s<div class="body" style="%s">%s</div>%s</div>'
            '<ul>%s%s</ul>%s</article>' % (e(b["id"]), e(b["for"]), " hasbg" if bg else "", bg, tt, style, slots, go, items, note, ref))


def page():
    slides = [resolved(b, BP["slides"]) for b in BP["slides"]]
    tasks = [framed(b) for b in BP["tasks"]]
    legend = "".join('<span><i style="background:var(--k-%s)"></i>%s</span>' % (k.lower(), e(k)) for k in KINDS)
    kinds = "".join("<li><b>%s</b> - %s</li>" % (e(k), e(v)) for k, v in BP["kinds"].items())
    return ("<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
            "<title>Template Blueprints</title><style>%s</style></head><body><div class=\"wrap\"><header><h1>Template Blueprints</h1>"
            "<p>Every slide and task screen the factory builds, empty: only where each part goes and what fills it. The words come from "
            "the approved content script, the pictures from the build sheet. Made from <code>plugin/skills/course-module-ui/knowledge/"
            "blueprints.json</code> by <code>scripts/blueprints.py</code> - edit the file, not this page.</p><div class=\"legend\">%s</div>"
            "<ul class=\"lead\">%s</ul></header><h2>Slides</h2><p class=\"lead\">%d blueprints - every template and variant of "
            "layout-templates.json; a mirrored variant is its base turned round.</p><div class=\"grid\">%s</div><h2>Task screens</h2>"
            "<p class=\"lead\">%d blueprints - the quick checks (part A) and the richer tasks (part B, in the engine frame: the task "
            "across the top, the stage, its side cards, one big button).</p><div class=\"grid\">%s</div></div></body></html>\n"
            % (CSS, legend, kinds, len(slides), "".join(card(b, b["id"].split(".")[0] not in ("opening", "recap")) for b in slides),
               len(tasks), "".join(card(b, False) for b in tasks)))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args(argv)
    probs = problems()
    if a.check:
        now = io.open(a.out, encoding="utf-8").read() if os.path.isfile(a.out) else ""
        if now != page():
            probs.append("%s is not what blueprints.json gives - run scripts/blueprints.py" % a.out)
        for p in probs:
            print("  - " + p)
        print("blueprints: %s" % ("%d problem(s)" % len(probs) if probs else "ok"))
        return 1 if probs else 0
    if probs:
        print("Not written - blueprints.json has problems:\n" + "\n".join("  - " + p for p in probs))
        return 1
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    io.open(a.out, "w", encoding="utf-8", newline="\n").write(page())
    print("written", a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
