# -*- coding: utf-8 -*-
"""handout.py - a module's handout for the trainee's tablet: handout\\index.html in the module folder (2.69.0).

    python handout.py <course folder> [--module N]      (compile_course.py writes it with the start pages, every build)

WHY (owner, 2026-10-27): "for tasks, for slides in trainees tablet, there is only ONE button possible, thats handout ...
we need to put that it created handout". The classroom's trainee page has the one Handout button and finds a module's
handout at trainee/<module>/handout/index.html; no factory step wrote one, so the button never showed.

WHAT IS IN IT - only what the class was shown, from the APPROVED script (nothing new is written here):
  every slide's title and its lines (a line's term before " - " in bold, as on the slide), in the slides' order;
  the slide's photographs (its figure, its tiles, its inset; a 3D scene's poster) with their record and credit;
  a task slide as its title only. NOT the instructor's notes, a check's questions or answers, or a task's key.
On the page: the contents (each slide a link), a search box that keeps only the slides that hold the words, and a tap on a
photo shows it at full width. It works offline, on its own, in the tablet's frame (the classroom adds its own style).

WHICH MODULES A TRAINEE SEES is the classroom's choice (join.js): the modules up to the one open now - never the ones
still to come - and the whole course when no module is open.
"""
from __future__ import annotations

import argparse
import html
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import compile_module as cm  # noqa: E402
import content_script as cs  # noqa: E402
import workspace  # noqa: E402

PICTURE = re.compile(r"\.(?:jpe?g|png|webp|gif)$", re.I)
WORDS = {
    "en": {"handout": "Handout", "module": "Module", "contents": "Contents", "search": "Search the handout",
           "none": "Nothing in this handout has these words.", "task": "Task", "found": "slides hold these words"},
    "lv": {"handout": "Izdales materiāls", "module": "Modulis", "contents": "Saturs", "search": "Meklēt materiālā",
           "none": "Šajā materiālā šo vārdu nav.", "task": "Uzdevums", "found": "slaidos ir šie vārdi"},
    "ru": {"handout": "Раздаточный материал", "module": "Модуль", "contents": "Содержание", "search": "Поиск по материалу",
           "none": "В этом материале таких слов нет.", "task": "Задание", "found": "слайдов с этими словами"},
}
e, a = cm.e, cm.a

CSS = """
:root{--navy:#0a2463;--blue:#3e92cc;--ink:#1b2a41;--steel:#4a5a70;--line:#d8e0ea;--pale:#f3f6fa;--amber:#f2b134}
*{box-sizing:border-box}
html{scroll-behavior:smooth;scroll-padding-top:84px}
body{margin:0;background:#fff;color:var(--ink);font:18px/1.55 "Raleway","Segoe UI",Arial,sans-serif}
header{padding:28px 20px 8px;max-width:860px;margin:0 auto}
header .k{font-size:13px;letter-spacing:.14em;text-transform:uppercase;color:var(--blue);font-weight:700}
header h1{margin:6px 0 0;font-size:30px;line-height:1.2;color:var(--navy)}
.find{position:sticky;top:0;z-index:2;background:rgba(255,255,255,.96);border-bottom:1px solid var(--line)}
.find div{max-width:860px;margin:0 auto;padding:12px 20px;display:flex;gap:12px;align-items:center}
.find input{flex:1;min-height:48px;font:inherit;padding:8px 14px;border:2px solid var(--line);border-radius:12px;color:var(--ink)}
.find input:focus{outline:none;border-color:var(--blue)}
.find small{color:var(--steel);white-space:nowrap}
main{max-width:860px;margin:0 auto;padding:8px 20px 60px}
nav ol{margin:8px 0 24px;padding-left:1.4em;columns:2 280px;column-gap:28px}
nav li{margin:4px 0;break-inside:avoid}
nav li{padding:3px 0}
nav a{color:var(--navy);text-decoration:none}
nav a:hover,nav a:focus{text-decoration:underline}
nav h2,section h2{color:var(--navy)}
nav h2{font-size:20px;margin:16px 0 0}
section{padding:22px 0;border-top:1px solid var(--line)}
section h2{font-size:23px;line-height:1.25;margin:0 0 10px}
section .n{color:var(--blue);font-size:14px;font-weight:700;letter-spacing:.08em;margin-right:8px}
section p{margin:8px 0}
section ul{margin:8px 0;padding-left:1.25em}
section li{margin:6px 0}
section.task h2{font-size:19px;color:var(--steel)}
figure{margin:14px 0}
figure img{display:block;max-width:100%;max-height:420px;border-radius:12px;cursor:zoom-in}
figure.big img{max-height:none;width:100%;cursor:zoom-out}
figcaption{font-size:14px;color:var(--steel);margin-top:6px}
mark{background:#ffe8a3;color:inherit;border-radius:3px}
.empty{color:var(--steel);font-style:italic;display:none}
"""

JS = r"""
(function(){
  var box=document.getElementById('q'),info=document.getElementById('qn'),empty=document.getElementById('empty');
  var secs=[].slice.call(document.querySelectorAll('main section')),nav=document.querySelector('nav');
  secs.forEach(function(s){s._html=s.innerHTML;s._text=s.textContent.toLowerCase();});
  function esc(t){return t.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');}
  function run(){
    var q=box.value.trim().toLowerCase(),words=q.split(/\s+/).filter(Boolean),n=0;
    secs.forEach(function(s){
      var hit=words.every(function(w){return s._text.indexOf(w)>=0;});
      s.hidden=!!words.length&&!hit; s.innerHTML=s._html;
      if(words.length&&hit){n++;var re=new RegExp('('+words.map(esc).join('|')+')','gi');
        [].forEach.call(s.querySelectorAll('h2,p,li,figcaption'),function(el){
          var w=document.createTreeWalker(el,4),t,ns=[];while((t=w.nextNode()))ns.push(t);
          ns.forEach(function(t){if(!re.test(t.nodeValue))return;re.lastIndex=0;var sp=document.createElement('span');
            sp.innerHTML=t.nodeValue.replace(/[&<>]/g,function(c){return{'&':'&amp;','<':'&lt;','>':'&gt;'}[c];}).replace(re,'<mark>$1</mark>');
            t.parentNode.replaceChild(sp,t);});});}
    });
    nav.hidden=!!words.length; empty.style.display=words.length&&!n?'block':'none';
    info.textContent=words.length&&n?n+' '+info.getAttribute('data-found'):'';
  }
  box.addEventListener('input',run);
  document.addEventListener('click',function(ev){var f=ev.target.closest&&ev.target.closest('figure');if(f)f.classList.toggle('big');});
})();
"""


def term_line(line):
    """a line as the slide shows it: the term before " - " in bold when it is short"""
    m = re.match(r"^(.{1,60}?)\s+-\s+(.+)$", line)
    if m and len(m.group(1).split()) <= 7:
        return "<b>%s</b> - %s" % (e(m.group(1)), e(m.group(2)))
    return e(line)


def lines_html(text):
    lines = cs.lines_of(text)
    out, items = [], []

    def flush():
        if items:
            out.append("<ul>%s</ul>" % "".join("<li>%s</li>" % x for x in items))
            del items[:]
    for i, x in enumerate(lines):
        x = re.sub(r"^\s*[-*•]\s+", "", x)
        if i == 0 or (x.endswith(":") and len(x.split()) <= 14 and not items):
            flush()
            out.append("<p>%s</p>" % term_line(x))
        else:
            items.append(term_line(x))
    flush()
    return "".join(out)


def pictures(mdir, b, s):
    """the slide's photographs from its build sheet entry: figure, tiles, inset, a 3D scene's poster - those in the module"""
    rels = []
    for k in ("figure", "poster"):
        v = (b.get(k) or "").replace("\\", "/")
        if PICTURE.search(v):
            rels.append(v)
    for t in b.get("tiles") or []:
        v = (t.get("figure") if isinstance(t, dict) else t) or ""
        if PICTURE.search(v):
            rels.append(v.replace("\\", "/"))
    ins = b.get("inset") or {}
    if isinstance(ins, dict) and PICTURE.search(ins.get("figure") or ins.get("photo") or ""):
        rels.append((ins.get("figure") or ins.get("photo")).replace("\\", "/"))
    out = []
    for rel in dict.fromkeys(rels):
        if not os.path.isfile(os.path.join(mdir, rel)):
            continue
        meta = cm.photo_meta(mdir, rel)
        about = cm.first_sentence(meta.get("description")) or cm.first_sentence(s.get("visual")) or s.get("title", "")
        credit = b.get("credit") or cm.credit_line(meta, with_title=False)
        out.append('<figure><img src="../%s" alt="%s" loading="lazy"><figcaption>%s%s</figcaption></figure>'
                   % (a(rel), a(about), e(about), (" · " + e(credit)) if credit else ""))
    return "".join(out)


def page(course_title, n, title, screens, sheet, mdir, lang):
    w = WORDS.get(lang, WORDS["en"])
    nav, body, k = [], [], 0
    for s in screens:
        kind = s.get("kind")
        if kind not in ("slide", "task-slide") or not (s.get("title") or "").strip():
            continue
        k += 1
        sid = "h-%s" % s["id"]
        b = sheet.get(s["id"]) or {}
        nav.append('<li><a href="#%s">%s</a></li>' % (sid, e(s["title"])))
        if kind == "task-slide":
            body.append('<section class="task" id="%s"><h2><span class="n">%s</span>%s</h2></section>' % (sid, e(w["task"]), e(s["title"])))
            continue
        body.append('<section id="%s"><h2><span class="n">%02d</span>%s</h2>%s%s</section>'
                    % (sid, k, e(s["title"]), lines_html(s.get("text")), pictures(mdir, b, s)))
    head = "%s %d" % (w["module"], n)
    return "\n".join([
        "<!doctype html>", '<html lang="%s">' % a(lang), "<head>", '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        "<title>%s - %s - %s</title>" % (e(w["handout"]), e(head), e(title)),
        '<link rel="stylesheet" href="../assets/gb_tokens.css">', "<style>%s</style>" % CSS, "</head>", "<body>",
        '<header><div class="k">%s · %s</div><h1>%s</h1></header>' % (e(course_title), e(head), e(title)),
        '<div class="find"><div><input id="q" type="search" placeholder="%s" aria-label="%s"><small id="qn" data-found="%s"></small></div></div>'
        % (a(w["search"]), a(w["search"]), a(w["found"])),
        "<main>", '<nav><h2>%s</h2><ol>%s</ol></nav>' % (e(w["contents"]), "".join(nav)),
        '<p class="empty" id="empty">%s</p>' % e(w["none"]), "\n".join(body), "</main>",
        "<script>%s</script>" % JS, "</body>", "</html>", ""])


def build(course, n, mdir, course_title, lang):
    """the handout page of module n as text - or None when its script is not approved (a draft gets none)"""
    sp = cs.paths(course, n)["script"]
    if not os.path.isfile(sp):
        return None
    script = cs.load(sp)
    if script.get("status") != "approved":
        return None
    try:
        sheet = cs.load(cm.build_path(course, n)).get("screens") or {}
    except (OSError, ValueError):
        sheet = {}
    return page(course_title, n, (script.get("title") or "").strip(), script.get("screens") or [], sheet, mdir, lang)


if __name__ == "__main__":
    import compile_course                                  # the handouts are written with the start pages, nowhere else
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("course")
    ap.add_argument("--module")
    o = ap.parse_args()
    sys.exit(compile_course.main([o.course] + (["--module", o.module] if o.module else [])))
