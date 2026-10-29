# -*- coding: utf-8 -*-
"""debrief_map.py - which wrong idea each wrong choice of a module's tasks stands for, and which questions are about
safety: written by the factory, approved by the operator, read by the instructor panel and never by a tablet.

    debrief_map.py draft   <course> --module 1                 write working_claude/script/M01.debrief.json to fill in
    debrief_map.py check   <course> --module 1                 every tag against the compiled pages
    debrief_map.py approve <course> --module 1 --by "<name>"   the operator's yes
    debrief_map.py build   <course> --module 1                 modules/module01/instructor/debrief_map.json
    debrief_map.py status  <course> --module 1
    debrief_map.py review  <course>                            to_review/MISCONCEPTIONS.html, every module, for the operator

THE TAG FILE (working_claude/script/M01.debrief.json)
    {"module": 1,
     "misconceptions": {"smell-warns": "Smelling the vapour is a warning in time"},
     "questions": {"q03": {"safety": true,
                           "choices": {"Breathing protection only when the vapour can be smelled": "smell-warns"}}}}
A misconception is a wrong idea in a few words, said as the trainee believes it. One idea gets one id however many
choices lead to it, so the debrief can say "5 of 12 believe this" across questions. "safety": true marks a question
where believing the wrong thing can hurt someone. A choice is named by what the trainee sees:
    an option                 its words
    true or false             "<statement> => true" or "<statement> => false" - the side the trainee chose
    check a colleague         "<claim> => <the correction chosen>", or "<claim> => keep"
    investigate               the source's title
Only wrong choices take a tag. Keys starting with _ (the draft's _q, _wrong) are notes for whoever fills it in.

HOW A TAG FINDS A TRAINEE'S ANSWER
A handed-in answer carries the question's id (q) and the key of each choice made (p) - the page's own answer keys,
gb_key(question id, words, value) (content_script.gb_key). The keys are read from the compiled pages, and each key's
value says whether that choice is right, so a tag on a right choice is caught without the answers being anywhere but
the factory. The map holds keys and tags only: no right answer is in it.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import io
import json
import os
import re
import sys
from datetime import date
from html.parser import HTMLParser

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "scripts"))
import content_script as cs  # noqa: E402

MAP_NAME = "debrief_map.json"
ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,47}$")


def norm(s):
    return re.sub(r"\s+", " ", s or "").strip()


class _Page(HTMLParser):
    """The keyed elements of each question of a compiled task page, with the words each stands for."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []          # [tag, attrs, text parts, children-classes]
        self.q = None
        self.qdepth = None
        self.out = {}            # qid -> [(kind, attrs, text, extra)]
        self.claim = ""
        self.src_title = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ("br", "img", "input", "meta", "link", "hr", "source", "wbr"):
            return
        self.stack.append([tag, a, []])
        if tag == "section" and a.get("data-script"):
            self.q, self.qdepth = a["data-script"], len(self.stack)
            self.out.setdefault(self.q, [])

    def handle_endtag(self, tag):
        if not self.stack:
            return
        while self.stack:
            t, a, parts = self.stack.pop()
            text = norm("".join(parts))
            for p in self.stack:
                p[2].append("".join(parts))
            if self.q:
                self._close(t, a, text, parts)
            if self.qdepth and len(self.stack) < self.qdepth:
                self.q, self.qdepth = None, None
            if t == tag:
                break

    def _close(self, t, a, text, parts):
        c = " " + (a.get("class") or "") + " "
        if " cr-text " in c:
            self.claim = text
        elif " sw-st " in c:
            self._st = text
        elif " iv-tl " in c:
            self.src_title = text
        key = a.get("data-key")
        if not key or not re.fullmatch(r"[0-9a-f]{8}", key or ""):
            return
        if " sw-card " in c:
            self.out[self.q].append(("swipe", key, getattr(self, "_st", "")))
        elif " cr-o " in c:
            self.out[self.q].append(("critique", key, self.claim, a.get("data-o", "")))
        elif " iv-src " in c:
            self.out[self.q].append(("evidence", key, self.src_title or ""))
            self.src_title = None
        elif " opt " in c or " hot " in c:
            self.out[self.q].append(("choose", key, text))

    def handle_data(self, data):
        if self.stack:
            self.stack[-1][2].append(data)


def choices(page_text):
    """{question id: [{"label", "key", "wrong"}]} - every choice a trainee can make that the page reports (gb_answer.js
    pickedKeys), named as the tag file names it, and whether it is wrong (worked out from its key)."""
    pr = _Page()
    pr.feed(page_text)
    out = {}
    for q, items in pr.out.items():
        rows = []
        for it in items:
            kind, key = it[0], it[1]
            if kind == "swipe":
                st = it[2]
                for side in ("true", "false"):
                    k = cs.gb_key(q, st, side)
                    rows.append({"label": "%s => %s" % (st, side), "key": k, "wrong": k != key})
            elif kind == "critique":
                claim, o = it[2], it[3]
                rows.append({"label": "%s => %s" % (claim, "keep" if o == "*" else o), "key": key,
                             "wrong": key == cs.gb_key(q, claim + " => " + o, 0)})
            else:
                rows.append({"label": it[2], "key": key, "wrong": key == cs.gb_key(q, it[2], 0)})
        out[q] = rows
    return out


# ---------------------------------------------------------------- where things are
def paths(course, module):
    m = "%02d" % int(module)
    root = os.path.join(course, "course") if os.path.isdir(os.path.join(course, "course", "working_claude")) else course
    return {"tags": os.path.join(root, "working_claude", "script", "M%s.debrief.json" % m),
            "script": os.path.join(root, "working_claude", "script", "M%s.json" % m),
            "module": os.path.join(root, "modules", "module" + m),
            "map": os.path.join(root, "modules", "module" + m, "instructor", MAP_NAME)}


def pages(module_dir):
    """{"tasks/<page>.html": (code, choices)} for every task page of the module."""
    out = {}
    tdir = os.path.join(module_dir, "tasks")
    for f in sorted(os.listdir(tdir)) if os.path.isdir(tdir) else []:
        if not f.endswith(".html"):
            continue
        t = io.open(os.path.join(tdir, f), encoding="utf-8").read()
        m = re.search(r'<body[^>]*data-code="([^"]*)"', t)
        out["tasks/" + f] = (m.group(1) if m else "", choices(t))
    return out


def load(p):
    return json.load(io.open(p, encoding="utf-8")) if os.path.isfile(p) else None


def save(p, d):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    io.open(p, "w", encoding="utf-8", newline="\n").write(json.dumps(d, ensure_ascii=False, indent=2) + "\n")


def content_hash(d):
    keep = {"misconceptions": d.get("misconceptions") or {},
            "questions": {q: {k: v for k, v in (x or {}).items() if not k.startswith("_")} for q, x in (d.get("questions") or {}).items()}}
    return hashlib.sha256(json.dumps(keep, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def question_texts(script_path):
    s = load(script_path) or {}
    return {x.get("id"): x.get("question") or x.get("text") or "" for x in s.get("screens") or [] if x.get("kind") in cs.TASKS}


# ---------------------------------------------------------------- the commands
def cmd_draft(course, module):
    """Every wrong choice of the module, per question, with an empty tag: the file whoever writes the tags fills in. An
    existing file keeps its tags; questions and choices that no longer exist are dropped."""
    P = paths(course, module)
    have = load(P["tags"]) or {}
    texts = question_texts(P["script"])
    qs = {}
    for _, (code, ch) in pages(P["module"]).items():
        for q, rows in ch.items():
            was = (have.get("questions") or {}).get(q) or {}
            wrong = [r["label"] for r in rows if r["wrong"]]
            qs[q] = {"_set": code, "_q": texts.get(q, ""), "_wrong": wrong, "safety": bool(was.get("safety")),
                     "choices": {l: (was.get("choices") or {}).get(l, "") for l in wrong}}
    d = {"module": int(module), "misconceptions": have.get("misconceptions") or {}, "questions": qs}
    save(P["tags"], d)
    n = sum(len(x["choices"]) for x in qs.values())
    print("Wrote %s: %d questions, %d wrong choices to tag." % (P["tags"], len(qs), n))
    return 0


def problems(course, module):
    P = paths(course, module)
    d = load(P["tags"])
    if d is None:
        return ["There is no tag file yet: run draft."], None
    out = []
    ms = d.get("misconceptions") or {}
    for i, t in ms.items():
        if not ID_RE.match(i):
            out.append("Misconception id %r: use lower-case letters, digits and -, 2 to 48 characters." % i)
        if not norm(t) or len(norm(t)) > 120:
            out.append("Misconception %r: say the wrong idea in up to 120 characters." % i)
    known = {}
    for _, (code, ch) in pages(P["module"]).items():
        for q, rows in ch.items():
            known[q] = {r["label"]: r for r in rows}
    used = set()
    for q, x in (d.get("questions") or {}).items():
        if q not in known:
            out.append("%s: no such question on the module's task pages." % q)
            continue
        if not isinstance(x.get("safety", False), bool):
            out.append("%s: safety is true or false." % q)
        for label, mid in (x.get("choices") or {}).items():
            if not mid:
                continue
            r = known[q].get(norm(label))
            if not r:
                out.append("%s: no choice reads %r." % (q, label))
            elif not r["wrong"]:
                out.append("%s: %r is a right answer - only wrong choices take a misconception." % (q, label))
            if mid not in ms:
                out.append("%s: %r has misconception %r, which is not in the list." % (q, label, mid))
            used.add(mid)
    for i in ms:
        if i not in used:
            out.append("Misconception %r is not used by any choice." % i)
    return out, d


def cmd_check(course, module):
    out, d = problems(course, module)
    if out:
        print("Module %s: %d problem(s) in the misconception tags:" % (module, len(out)))
        for p in out:
            print("  - " + p)
        return 1
    qs = d.get("questions") or {}
    tagged = sum(1 for x in qs.values() for v in (x.get("choices") or {}).values() if v)
    total = sum(len(x.get("choices") or {}) for x in qs.values())
    print("Module %s: the tags are sound - %d of %d wrong choices tagged, %d misconceptions, %d safety questions."
          % (module, tagged, total, len(d.get("misconceptions") or {}), sum(1 for x in qs.values() if x.get("safety"))))
    return 0


def cmd_approve(course, module, by):
    out, d = problems(course, module)
    if out:
        cmd_check(course, module)
        print("Not approved: put these right first.")
        return 1
    d.update({"approved_by": by, "approved_on": date.today().isoformat(), "approved_hash": content_hash(d)})
    save(paths(course, module)["tags"], d)
    print("Module %s: misconception tags approved by %s." % (module, by))
    return 0


def approved(d):
    return bool(d) and d.get("approved_hash") == content_hash(d)


def build(course, module, quiet=False):
    """The instructor's map, from the approved tags and the compiled pages. Nothing is written for tags that are not
    approved, or no longer approved because they changed - an old map is removed, never left to say something
    nobody approved."""
    P = paths(course, module)
    d = load(P["tags"])
    if not approved(d):
        if os.path.isfile(P["map"]):
            os.remove(P["map"])
        if not quiet:
            print("Module %s: no approved misconception tags - no debrief map." % module)
        return 0
    out, _ = problems(course, module)
    if out:
        cmd_check(course, module)
        return 1
    ms, qs = d.get("misconceptions") or {}, d.get("questions") or {}
    pg = {}
    for ref, (code, ch) in pages(P["module"]).items():
        qmap = {}
        for q, rows in ch.items():
            x = qs.get(q) or {}
            k = {r["key"]: (x.get("choices") or {}).get(r["label"]) for r in rows if r["wrong"]}
            k = {key: mid for key, mid in k.items() if mid}
            if k or x.get("safety"):
                qmap[q] = {"safety": bool(x.get("safety")), "k": k}
        if qmap:
            pg[ref] = {"code": code, "q": qmap}
    save(P["map"], {"module": int(module), "misconceptions": ms, "pages": pg})
    if not quiet:
        print("Module %s: wrote %s (%d pages)." % (module, os.path.relpath(P["map"], course), len(pg)))
    return 0


def cmd_status(course, module):
    P = paths(course, module)
    d = load(P["tags"])
    if d is None:
        print("Module %s: no misconception tags yet." % module)
    elif approved(d):
        print("Module %s: misconception tags approved by %s on %s." % (module, d.get("approved_by"), d.get("approved_on")))
    else:
        print("Module %s: misconception tags %s." % (module, "changed since the approval" if d.get("approved_hash") else "not approved"))
    return 0


REVIEW_CSS = """
body{margin:0;background:#f6f7f9;color:#14202b;font:16px/1.5 system-ui,-apple-system,'Segoe UI',Roboto,sans-serif}
main{max-width:980px;margin:0 auto;padding:24px 16px 64px}
h1{font-size:28px;margin:0 0 6px}h2{font-size:22px;margin:40px 0 4px;padding-top:16px;border-top:2px solid #d8dee5}
.sub{color:#56636f;margin:0 0 16px}.st{font-size:13px;font-weight:700;letter-spacing:.06em;color:#56636f}
.ok{color:#137a43}.no{color:#a3471a}
.idea{background:#fff;border:1px solid #dde3ea;border-radius:12px;padding:12px 16px;margin:10px 0}
.idea h3{margin:0 0 6px;font-size:17px}.idea code{font-size:12px;color:#7a8794;margin-left:6px;font-weight:400}
.idea ul{margin:0;padding-left:20px}.idea li{margin:4px 0;color:#2b3945}.idea li b{color:#14202b}
.q{color:#56636f}.safe{display:inline-block;padding:0 8px;border-radius:999px;background:#c62828;color:#fff;font-size:12px;font-weight:700;letter-spacing:.06em;margin-right:6px}
.sq{margin:8px 0 0;padding-left:20px}.sq li{margin:3px 0}
@media (max-width:600px){main{padding:16px}h1{font-size:24px}}
"""


def cmd_review(course):
    """One page for the operator: per module, each wrong idea with the choices that stand for it, and the safety
    questions. Written to to_review/MISCONCEPTIONS.html beside the content script's review."""
    esc = html.escape
    root = os.path.join(course, "course") if os.path.isdir(os.path.join(course, "course", "working_claude")) else course
    sdir = os.path.join(root, "working_claude", "script")
    mods = sorted(int(m.group(1)) for f in os.listdir(sdir) for m in [re.match(r"M(\d+)\.debrief\.json$", f)] if m)
    parts, tot = [], [0, 0, 0]
    for n in mods:
        P = paths(course, n)
        d = load(P["tags"]) or {}
        ms, qs = d.get("misconceptions") or {}, d.get("questions") or {}
        texts = question_texts(P["script"])
        state = ('<span class="ok">approved by %s on %s</span>' % (esc(d.get("approved_by", "")), esc(d.get("approved_on", "")))
                 if approved(d) else '<span class="no">%s</span>' % ("changed since the approval" if d.get("approved_hash") else "not approved yet"))
        by = {}
        for q, x in qs.items():
            for label, mid in (x.get("choices") or {}).items():
                by.setdefault(mid, []).append((q, label, bool(x.get("safety"))))
        ideas = []
        for mid, text in ms.items():
            rows = by.get(mid, [])
            safe = any(s for _, _, s in rows)
            ideas.append((not safe, -len(rows), mid, text, rows, safe))
        ideas.sort()
        body = "".join(
            '<div class="idea"><h3>%s&ldquo;%s&rdquo;<code>%s</code></h3><ul>%s</ul></div>'
            % ('<span class="safe">SAFETY</span>' if safe else "", esc(text), esc(mid),
               "".join('<li><span class="q">%s &middot; %s</span><br><b>Picked:</b> %s</li>'
                       % (esc(q), esc(texts.get(q) or qs[q].get("_q", "")), esc(label)) for q, label, _ in rows))
            for _, _, mid, text, rows, safe in ideas)
        sq = [q for q, x in qs.items() if x.get("safety")]
        safety = ('<p class="st">SAFETY QUESTIONS (%d)</p><ul class="sq">%s</ul>'
                  % (len(sq), "".join("<li>%s &middot; %s</li>" % (esc(q), esc(texts.get(q) or qs[q].get("_q", ""))) for q in sq))) if sq else ""
        nchoice = sum(len(x.get("choices") or {}) for x in qs.values())
        tot[0] += len(ms); tot[1] += nchoice; tot[2] += len(sq)
        parts.append('<section id="m%02d"><h2>Module %d</h2><p class="sub">%d wrong ideas &middot; %d wrong choices &middot; %d safety '
                     'questions &middot; %s</p>%s%s</section>' % (n, n, len(ms), nchoice, len(sq), state, body or '<p class="sub">No wrong choices to tag.</p>', safety))
    page = ('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>Misconceptions to approve</title><style>%s</style></head><body><main><h1>Misconceptions to approve</h1>'
            '<p class="sub">Each wrong idea is said as a trainee believes it, with every wrong choice that stands for it. The instructor\'s debrief '
            'groups the class by these (&ldquo;5 of 12 believed this&rdquo;) and puts SAFETY first. Nothing here reaches a tablet. '
            'Total: %d wrong ideas, %d wrong choices, %d safety questions.</p>%s</main></body></html>') % (REVIEW_CSS, tot[0], tot[1], tot[2], "".join(parts))
    out = os.path.join(root, "to_review", "MISCONCEPTIONS.html")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    io.open(out, "w", encoding="utf-8", newline="\n").write(page)
    print("Wrote %s (%d modules)." % (out, len(mods)))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("cmd", choices=("draft", "check", "approve", "build", "status", "review"))
    ap.add_argument("course")
    ap.add_argument("--module", type=int)
    ap.add_argument("--by")
    o = ap.parse_args(argv)
    if o.cmd == "review":
        return cmd_review(o.course)
    if o.module is None:
        ap.error("%s needs --module N" % o.cmd)
    if o.cmd == "approve":
        if not o.by:
            ap.error("approve needs --by \"<name>\" - the person who approved")
        return cmd_approve(o.course, o.module, o.by)
    return {"draft": cmd_draft, "check": cmd_check, "build": build, "status": cmd_status}[o.cmd](o.course, o.module)


if __name__ == "__main__":
    sys.exit(main())
