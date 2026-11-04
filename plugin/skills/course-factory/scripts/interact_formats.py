# -*- coding: utf-8 -*-
"""interact_formats - the answer formats of the interactive task types (2.74.0), read once for everyone.

content_script.py checks them (read_answer), lists their pieces (answer_items) and compile/scripts/task_pages.py builds
their pages - all three from parse() below, so a format is written down in one place.

Owner, 2026-10-28: tasks that are "more interesting / modern / technology ... practical learning as well", in two parts
after every block of theory - Part A checks that the trainee understood everything before it in the module, Part B gives
"a little bit difficult task, where they need to find the answer by themselves" - and "3D deck view, 3D models,
equipment in 3D, panorama, on-ship activities". The approved prototypes: design/task-prototypes/index.html.

Every format is the operator's plain text in the Word review file, one line per item, '*' marks what is right (as the
nineteen older ways of answering). What the format cannot say - where a part sits in 3D, a pipe's path, a photograph -
is the build sheet's (knowledge/media-and-tasks.json "_build_sheet" per type), never the operator's.

    true_false       statement => why                     a true statement marked *; at least 4, both kinds
    critique         claim => right correction* | wrong correction        a wrong claim
                     claim => * | decoy correction                        a right claim ("*" alone = keep it as written)
    calculate        value unit ± tolerance               the first line - what the trainee must work out
                     ! what the device shows              one line each (a display, a gauge, a label)
                     # cell | cell | cell                 the data sheet, the first # line its header
    predict          value ± tolerance @ x                the first line - the y the trainee must predict at x
                     x: name | unit | low | high          y: name | unit | low | high
                     given: x | y | label                 the points shown before (one or more)
                     curve: x y; x y; ...                 the real data, drawn after the prediction
    explore          find: the challenge => condition     condition: a choice's name; x < 9.5 and the like; hide <readout>
    investigate      TAG | title: content                 one source per line, the ones that explain it marked *;
                                                          content rows split by ;; and cells by | (the first row a header).
                                                          The options are the conclusions, 'correct' the right one.
    line_up          goal: source => destination          keep out: name; name        TAG: name = open | shut  (as found)
    inspect_round    thing: what you see when you look    one per thing in the space, the problems marked *
    take_apart       part: name: what it is (never what it is for)
                     find: question => part name          set: instruction => position word
    test_atmosphere  space: name | depth in m             levels: 2; 8; 14 (± 2)       the depths that need a fresh reading
                     name unit | value @ depth; ... | below 19.5 (or above 10)      one line per reading

The richer tasks (design/task-templates/engines), each a framed task of its own on its screen (course-task-ux/engines):
    deck_round       context: where and when                intro: title | what the trainee is told
                     place: name                          and under it, for each fault to find on its photograph:
                     fault: name | label on the photo     see: what is there   hint: where to look
                     do: what to do* | do: a wrong one    why: the reason      (the photos and tap zones: the build sheet)
    dress_for_job    context: where and when                intro: title | what the trainee is told
                     group: what is judged together | why   and under it, one per item on the rack:
                     item: name | short name | where it is worn *  (* = needed for the job)
                     story: what happens at the job when this item is worn wrongly or missing (under its item)
                     needs: item => item it goes onto | what is said     one at a time: item; item | what is said
                     ready: title | what happens when every item is right
                     check: what the buddy check asks | what the colleague says
                     spot: what can be seen on the colleague | why     (one per line, the faults marked *)
                     ask: the closing question            reason: one answer per line, the right one marked *
                     explain: title | the answer explained  (the photos and the places on them: the build sheet)
    lay_out          context: where and when                intro: title | what the trainee is told
                     reading: name | value                (what the side card shows: the cargo, the wind speed ...)
                     place: name                          a fixed point on the photo (the manifold, the gangway)
                     wind: where it blows from | where it carries a leak     (one per line; one is drawn each opening)
                     item: name | short name | letters on its pin            (every piece in the tray)
                     leak: place | what happens there when the layout is checked
                     rule: what is judged | short name; short name | place | 15 m (or 3 to 15 m) | side
                           side: upwind, downwind, a side of the build sheet, or two of them for two pieces (forward / aft)
                     why: the reason (under its rule)     story: what happens when it is not met - {wind}: where the leak goes
                     unsafe: what is judged | why          and its story: - the pieces no rule names must stay in the tray
                     ready: title | what happens when every rule is met
"""
from __future__ import annotations

import base64
import json
import re

TYPES = ("true_false", "critique", "calculate", "predict", "explore", "investigate", "line_up", "inspect_round",
         "take_apart", "test_atmosphere", "deck_round", "dress_for_job", "lay_out")
FRAMED = ("deck_round", "dress_for_job", "lay_out")   # a framed task: its own page in the set's screen (interact_pages.framed)
USES = {"true_false": {"answer"}, "critique": {"answer"}, "calculate": {"answer"}, "predict": {"answer"},
        "explore": {"answer"}, "investigate": {"options", "answer"}, "line_up": {"answer", "visual"},
        "inspect_round": {"answer", "visual"}, "take_apart": {"answer", "visual"}, "test_atmosphere": {"answer"},
        "deck_round": {"answer"}, "dress_for_job": {"answer"}, "lay_out": {"answer"}}
NUM = r"-?\d+(?:[.,]\d+)?"
OPEN_WORDS = {"open", "opened", "atvērts", "atverts", "открыт", "открыто", "on"}
SHUT_WORDS = {"shut", "closed", "close", "aizvērts", "aizverts", "закрыт", "закрыто", "off"}


def lines_of(text):
    return [x.strip() for x in (text or "").split("\n") if x.strip()]


def starred(line):
    return line.rstrip().endswith("*") or line.lstrip().startswith("*")


def unstar(line):
    return line.strip().strip("*").strip()


def num(s):
    return float(str(s).replace(",", ".").replace("−", "-").strip())


def decimals(s):
    s = str(s).replace(",", ".").strip()
    return len(s.split(".", 1)[1]) if "." in s else 0


def b64(obj):
    """the world a page draws from, not readable off the page as words (gb_interact.js world())"""
    return base64.b64encode(json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).decode("ascii")


def steps(lo, hi, step):
    """every value from lo to hi on the step's grid, as the page rounds them"""
    dec = max(0, decimals(("%.10f" % step).rstrip("0")))
    n0, n1 = int(round(lo / step)), int(round(hi / step))
    return [(round(k * step, dec), dec) for k in range(n0, n1 + 1)]


# ------------------------------------------------------------------ a small, safe reader for explore's conditions
TOKEN = re.compile(r"\s*(\d*\.?\d+|[A-Za-z_]\w*|<=|>=|==|!=|&&|\|\||[-+*/()<>!=])")


def condition(src):
    """'9.5 < x <= 15' -> a function of {x, ...} - the same grammar gb_interact.js reads (numbers, names, + - * /, comparisons,
    and / or / not); None when it cannot be read"""
    toks, pos = [], 0
    src = (src or "").replace(",", ".").replace("≤", "<=").replace("≥", ">=").replace("−", "-")
    while pos < len(src):
        m = TOKEN.match(src, pos)
        if not m:
            if src[pos:].strip() == "":
                break
            return None
        toks.append(m.group(1))
        pos = m.end()

    def run(v):
        i = [0]

        def peek():
            return toks[i[0]] if i[0] < len(toks) else None

        def nxt():
            i[0] += 1
            return toks[i[0] - 1]

        def prim():
            t = nxt()
            if t == "(":
                r = orr()
                nxt()
                return r
            if t == "-":
                return -prim()
            if t in ("!", "not"):
                return not prim()
            if re.match(r"^[\d.]", t):
                return float(t)
            if t and re.match(r"^[A-Za-z_]\w*$", t) and t not in ("and", "or", "not") and t in v:
                return v[t]
            raise ValueError(t)

        def mul():
            a = prim()
            while peek() in ("*", "/"):
                o, b = nxt(), prim()
                a = a * b if o == "*" else a / b
            return a

        def add():
            a = mul()
            while peek() in ("+", "-"):
                o, b = nxt(), mul()
                a = a + b if o == "+" else a - b
            return a

        def cmp():
            a, r = add(), None
            while peek() in ("<", ">", "<=", ">=", "==", "!=", "="):
                o, b = nxt(), add()
                ok = {"<": a < b, ">": a > b, "<=": a <= b, ">=": a >= b, "!=": a != b}.get(o, a == b)
                r = (True if r is None else r) and ok
                a = b
            return a if r is None else r

        def andd():
            a = cmp()
            while peek() in ("&&", "and"):
                nxt()
                b = cmp()
                a = a and b
            return a

        def orr():
            a = andd()
            while peek() in ("||", "or"):
                nxt()
                b = andd()
                a = a or b
            return a
        r = orr()
        if i[0] != len(toks):
            raise ValueError("left over")
        return r
    try:                                  # read once with every name worth 1: only the grammar is checked here
        run(_Any())
    except Exception:
        return None
    return run


class _Any(dict):
    def __contains__(self, k):
        return True

    def __missing__(self, k):
        return 1.0


# ------------------------------------------------------------------ parse: one function per type
def parse(m, q):
    """(problems, data, right words, wrong words, items) for a question of an interactive type. data is what the page is
    built from; right / wrong feed the 'taught before it is asked' check (L36); items are the pieces the built page must
    show with data-script-field="answer" (check_script_match.py)."""
    sid, ls, probs = q.get("id"), lines_of(q.get("answer")), []
    f = globals().get("_" + m)
    if not f:
        return ["%s: unknown way of answering %r" % (sid, m)], {}, [], [], []
    return f(sid, ls, q, probs)


def _true_false(sid, ls, q, probs):
    cards = []
    for ln in ls:
        st, _, why = ln.partition("=>")
        cards.append({"text": unstar(st), "true": starred(st), "why": why.strip()})
    if len(cards) < 4 or not any(c["true"] for c in cards) or all(c["true"] for c in cards):
        probs.append("%s: 'true or false' needs at least four statements, one per line - the true ones marked *, and at least one "
                     "of each (statement => why)" % sid)
    items = [c["text"] for c in cards] + [c["why"] for c in cards if c["why"]]
    return probs, {"cards": cards}, [c["text"] for c in cards], [], items


def _critique(sid, ls, q, probs):
    claims = []
    for ln in ls:
        claim, sep, rest = ln.partition("=>")
        if not sep:
            probs.append("%s: each claim is written as: claim => right correction* | wrong correction - or, for a claim that is right, "
                         "claim => * | a decoy correction" % sid)
            continue
        opts = [o.strip() for o in rest.split("|") if o.strip()]
        good = [o for o in opts if starred(o)]
        if len(good) != 1 or len(opts) < 2:
            probs.append("%s: \"%s\" needs two or more choices after =>, exactly one marked *" % (sid, claim.strip()))
            continue
        claims.append({"text": claim.strip(), "opts": [unstar(o) for o in opts], "right": opts.index(good[0])})
    keep = [c for c in claims if not c["opts"][c["right"]]]
    if len(claims) < 3 or not keep or len(keep) == len(claims):
        probs.append("%s: 'check a colleague' needs at least three claims - at least one right as written (=> * | ...) and at least "
                     "one wrong" % sid)
    # 2.74.1 - the tablet adds "keep it as written" to every claim; a claim with fewer choices than the others would say which
    # claims are right, so every claim shows the same number: a wrong one "fix* | wrong", a right one "* | decoy | decoy"
    shown = sorted({len([o for o in c["opts"] if o]) + 1 for c in claims})
    if len(shown) > 1:
        probs.append("%s: every claim must offer the same number of choices, or the number gives the answer away - write a wrong "
                     "claim as 'claim => right correction* | wrong correction' and a right one as 'claim => * | decoy | decoy' "
                     "(now %s choices)" % (sid, " / ".join(str(n) for n in shown)))
    right = [c["opts"][c["right"]] for c in claims if c["opts"][c["right"]]] + [c["text"] for c in keep]
    wrong = [c["text"] for c in claims if c not in keep]
    items = [c["text"] for c in claims] + [o for c in claims for o in c["opts"] if o]
    return probs, {"claims": claims}, right, wrong, items


VALUE = re.compile(r"^\s*(%s)\s*(.*?)\s*(?:±|\+/-)\s*(%s)\s*$" % (NUM, NUM))


def _calculate(sid, ls, q, probs):
    m = VALUE.match(ls[0]) if ls else None
    if not m:
        probs.append("%s: 'work it out' starts with the answer as one line: value unit ± tolerance (e.g. 0.84 %% vol ± 0.02)" % sid)
        return probs, {}, [], [], []
    v, unit, tol = num(m.group(1)), m.group(2).strip(), num(m.group(3))
    reads = [x.lstrip("!").strip() for x in ls[1:] if x.startswith("!")]
    rows = [[c.strip() for c in x.lstrip("#").split("|")] for x in ls[1:] if x.startswith("#")]
    if not reads and not rows:
        probs.append("%s: 'work it out' needs what the trainee works from - lines starting ! (what a device shows) or # (the data sheet)" % sid)
    if rows and len({len(r) for r in rows}) > 1:
        probs.append("%s: every data sheet line (#) needs the same number of cells" % sid)
    dec = max(decimals(m.group(1)), decimals(m.group(3)))
    items = reads + [c for r in rows for c in r]
    return probs, {"value": v, "unit": unit, "tol": tol, "dec": dec, "reads": reads, "rows": rows}, ["%s %s" % (m.group(1), unit)], [], items


PRED = re.compile(r"^\s*(%s)\s*(?:±|\+/-)\s*(%s)\s*(?:@|at)\s*(%s)\s*$" % (NUM, NUM, NUM))


def _predict(sid, ls, q, probs):
    m = PRED.match(ls[0]) if ls else None
    d = {"given": [], "curve": []}
    if not m:
        probs.append("%s: 'predict, then see' starts with: value ± tolerance @ x (e.g. 13.7 ± 1.5 @ 40)" % sid)
        return probs, {}, [], [], []
    d["value"], d["tol"], d["at"] = num(m.group(1)), num(m.group(2)), num(m.group(3))
    d["dec"] = max(decimals(m.group(1)), decimals(m.group(2)), 1)
    for ln in ls[1:]:
        key, _, rest = ln.partition(":")
        key = key.strip().lower()
        cells = [c.strip() for c in rest.split("|")]
        try:
            if key in ("x", "y"):
                d[key] = [cells[0], cells[1], num(cells[2]), num(cells[3])]
            elif key == "given":
                d["given"].append([num(cells[0]), num(cells[1]), cells[2] if len(cells) > 2 else ""])
            elif key == "curve":
                d["curve"] = [[num(a) for a in p.split()] for p in rest.split(";") if p.strip()]
        except (IndexError, ValueError):
            probs.append("%s: '%s' cannot be read: %s" % (sid, key, ln))
    if "x" not in d or "y" not in d:
        probs.append("%s: 'predict, then see' needs both axes: x: name | unit | low | high and y: name | unit | low | high" % sid)
    if len(d["curve"]) < 3:
        probs.append("%s: 'predict, then see' needs the real data: curve: x y; x y; ... (at least three points)" % sid)
    else:
        at = [p[1] for p in d["curve"] if abs(p[0] - d["at"]) < 1e-9]
        if not at:
            probs.append("%s: the curve has no point at x = %g, where the trainee predicts" % (sid, d["at"]))
        elif abs(at[0] - d["value"]) > d["tol"]:
            probs.append("%s: the curve says %g at x = %g, outside the answer %g ± %g" % (sid, at[0], d["at"], d["value"], d["tol"]))
    items = ([d["x"][0], d["y"][0]] if "x" in d and "y" in d else []) + [g[2] for g in d["given"] if g[2]]
    return probs, d, ["%s" % m.group(1)], [], items


def _explore(sid, ls, q, probs):
    finds = []
    for ln in ls:
        key, _, rest = ln.partition(":")
        if key.strip().lower() != "find" or "=>" not in rest:
            probs.append("%s: each challenge is written as: find: what to find => condition (e.g. x > 9.5 and x <= 15)" % sid)
            continue
        words, _, cond = rest.partition("=>")
        f = {"text": words.strip(), "only": "", "hide": [], "cond": ""}
        for part in [p.strip() for p in cond.split(";") if p.strip()]:
            if part.lower().startswith("hide "):
                f["hide"].append(part[5:].strip())
            elif re.match(r"^[^\d<>=!x(][^<>=]*$", part) and not re.search(r"\b(and|or|not)\b", part):
                f["only"] = part
            else:
                f["cond"] = ("%s and (%s)" % (f["cond"], part)) if f["cond"] else part
        if not f["cond"] or condition(f["cond"]) is None:
            probs.append("%s: the condition of \"%s\" cannot be read - write it with x, numbers and < <= > >= and / or" % (sid, f["text"]))
        finds.append(f)
    if not finds:
        probs.append("%s: 'explore and find' needs at least one challenge: find: ... => condition" % sid)
    return probs, {"finds": finds}, [f["text"] for f in finds], [], [f["text"] for f in finds]


def _investigate(sid, ls, q, probs):
    srcs = []
    for ln in ls:
        body = unstar(ln)
        tag, sep, rest = body.partition("|")
        if not sep:
            tag, rest = "", body
        title, sep2, content = rest.partition(":")
        if not sep2:
            probs.append("%s: each source is written as: TAG | title: what it says - %s" % (sid, body))
            continue
        srcs.append({"tag": tag.strip(), "title": title.strip(), "content": content.strip(), "rel": starred(ln)})
    rel = [s for s in srcs if s["rel"]]
    if len(srcs) < 4 or len(rel) < 2 or len(rel) == len(srcs):
        probs.append("%s: 'investigate' needs at least four sources - at least two that explain it (marked *) and at least one that "
                     "does not" % sid)
    items = [x for s in srcs for x in (s["tag"], s["title"], s["content"]) if x]
    return probs, {"sources": srcs, "min": min(3, len(rel)) if rel else 2}, [s["title"] for s in rel], [s["title"] for s in srcs if not s["rel"]], items


def state_word(w):
    w = (w or "").strip().lower()
    return "open" if w in OPEN_WORDS else "shut" if w in SHUT_WORDS else ""


def _line_up(sid, ls, q, probs):
    d = {"source": "", "goal": "", "out": [], "valves": []}
    for ln in ls:
        key, sep, rest = ln.partition(":")
        k = key.strip().lower()
        if k == "goal" and "=>" in rest:
            d["source"], d["goal"] = (x.strip() for x in rest.split("=>", 1))
        elif k == "keep out":
            d["out"] = [x.strip() for x in rest.split(";") if x.strip()]
        elif sep and "=" in rest:
            name, _, st = rest.rpartition("=")
            if not state_word(st):
                probs.append("%s: valve %s - its position as found is 'open' or 'shut', not %r" % (sid, key.strip(), st.strip()))
            d["valves"].append({"tag": key.strip(), "name": name.strip(), "start": state_word(st) or "shut", "word": st.strip()})
        else:
            probs.append("%s: 'line it up' lines are: goal: source => destination / keep out: name; name / TAG: valve name = open|shut - %s" % (sid, ln))
    if not d["source"] or not d["goal"]:
        probs.append("%s: 'line it up' needs its goal: goal: where it starts => where it must go" % sid)
    if len(d["valves"]) < 3:
        probs.append("%s: 'line it up' needs at least three valves, each: TAG: name = open|shut (as the trainee finds it)" % sid)
    items = [d["source"], d["goal"]] + d["out"] + [x for v in d["valves"] for x in (v["tag"], v["name"])]
    return probs, d, [d["goal"]], d["out"], [x for x in items if x]


def _inspect_round(sid, ls, q, probs):
    things = []
    for ln in ls:
        name, sep, seen = unstar(ln).partition(":")
        if not sep:
            probs.append("%s: each thing is written as: thing: what you see when you look at it - %s" % (sid, unstar(ln)))
            continue
        things.append({"name": name.strip(), "says": seen.strip(), "problem": starred(ln)})
    bad = [t for t in things if t["problem"]]
    if len(things) < 5 or len(bad) < 2 or len(things) - len(bad) < 2:
        probs.append("%s: 'inspection round' needs at least five things - at least two problems (marked *) and two that are fine" % sid)
    return probs, {"things": things}, [t["name"] for t in bad], [t["name"] for t in things if not t["problem"]], \
        [x for t in things for x in (t["name"], t["says"])]


def _take_apart(sid, ls, q, probs):
    d = {"parts": [], "steps": []}
    for ln in ls:
        key, sep, rest = ln.partition(":")
        k = key.strip().lower()
        if k == "part":
            name, sep2, says = rest.partition(":")
            d["parts"].append({"name": name.strip(), "says": says.strip()})
        elif k in ("find", "set") and "=>" in rest:
            ask, _, ans = rest.partition("=>")
            d["steps"].append({"kind": k, "ask": ask.strip(), "answer": ans.strip()})
        else:
            probs.append("%s: 'take it apart' lines are: part: name: what it is / find: question => part name / set: instruction => "
                         "position - %s" % (sid, ln))
    names = [p["name"] for p in d["parts"]]
    if len(names) < 3:
        probs.append("%s: 'take it apart' names at least three parts (part: name: what it is)" % sid)
    if not d["steps"]:
        probs.append("%s: 'take it apart' needs at least one step (find: ... => part, or set: ... => position)" % sid)
    for s in d["steps"]:
        if s["kind"] == "find" and s["answer"] not in names:
            probs.append("%s: \"%s\" - the answer %r is not one of the parts named (part: ...)" % (sid, s["ask"], s["answer"]))
    items = [x for p in d["parts"] for x in (p["name"], p["says"]) if x] + [s["ask"] for s in d["steps"]]
    return probs, d, [s["answer"] for s in d["steps"] if s["kind"] == "find"], [], items


ALARM = re.compile(r"^(below|under|above|over)\s+(%s)$" % NUM, re.I)


def _test_atmosphere(sid, ls, q, probs):
    d = {"space": "", "depth": 0, "levels": [], "band": 2.0, "gases": []}
    for ln in ls:
        key, sep, rest = ln.partition(":")
        k = key.strip().lower()
        if k == "space" and sep:
            name, _, depth = rest.partition("|")
            d["space"] = name.strip()
            try:
                d["depth"] = num(depth.lower().replace("m", ""))
            except ValueError:
                probs.append("%s: space: name | depth in metres - %s" % (sid, ln))
        elif k == "levels" and sep:
            body, _, band = rest.partition("±")
            try:
                d["levels"] = [num(x) for x in body.split(";") if x.strip()]
                if band.strip():
                    d["band"] = num(band.lower().replace("m", ""))
            except ValueError:
                probs.append("%s: levels: depth; depth; depth (± band) - %s" % (sid, ln))
        else:
            cells = [c.strip() for c in ln.split("|")]
            if len(cells) < 2:
                probs.append("%s: a reading is written as: name unit | value @ depth; ... | below/above alarm - %s" % (sid, ln))
                continue
            g = {"name": cells[0], "pts": [], "lo": None, "hi": None, "dec": 0}
            try:
                for p in cells[1].split(";"):
                    v, _, dd = p.partition("@")
                    g["pts"].append([num(dd) if dd.strip() else 0.0, num(v)])
                    g["dec"] = max(g["dec"], decimals(v.strip()))
            except ValueError:
                probs.append("%s: the readings of %s cannot be read - value @ depth; value @ depth" % (sid, cells[0]))
                continue
            g["pts"].sort()
            if len(cells) > 2 and cells[2]:
                a = ALARM.match(cells[2])
                if not a:
                    probs.append("%s: %s - its alarm is 'below N' or 'above N', not %r" % (sid, cells[0], cells[2]))
                elif a.group(1).lower() in ("below", "under"):
                    g["lo"] = num(a.group(2))
                else:
                    g["hi"] = num(a.group(2))
            d["gases"].append(g)
    if not d["space"] or not d["depth"]:
        probs.append("%s: 'test before entry' needs its space: space: name | depth in metres" % sid)
    if not d["levels"]:
        probs.append("%s: 'test before entry' needs the levels that must be tested: levels: 2; 8; 14" % sid)
    if not d["gases"]:
        probs.append("%s: 'test before entry' needs at least one reading: name unit | value @ depth; ..." % sid)
    for lv in d["levels"]:
        if d["depth"] and not 0 < lv < d["depth"]:
            probs.append("%s: the level %g m is not inside the space (0 to %g m)" % (sid, lv, d["depth"]))
    return probs, d, [g["name"] for g in d["gases"]], [], [d["space"]] + [g["name"] for g in d["gases"]]


def _deck_round(sid, ls, q, probs):
    """a deck round: the places walked one after the other, on each the faults to find on its photograph and what to do"""
    d = {"context": "", "intro": {"title": "", "text": ""}, "places": [], "faults": []}
    f = None
    for ln in ls:
        key, sep, rest = ln.partition(":")
        k, rest = key.strip().lower(), rest.strip()
        if not sep or k not in ("context", "intro", "place", "fault", "see", "hint", "do", "why"):
            probs.append("%s: a deck round's line starts with context:, intro:, place:, fault:, see:, hint:, do: or why: - not %r" % (sid, ln))
            continue
        if k == "context":
            d["context"] = rest
        elif k == "intro":
            t, _, x = rest.partition("|")
            d["intro"] = {"title": t.strip(), "text": x.strip()}
        elif k == "place":
            d["places"].append({"name": rest})
        elif k == "fault":
            if not d["places"]:
                probs.append("%s: the fault %r comes before any place: - each fault belongs to the place above it" % (sid, rest))
                continue
            name, _, label = rest.partition("|")
            f = {"place": d["places"][-1]["name"], "name": name.strip(), "label": label.strip() or name.strip(),
                 "see": "", "hint": "", "do": [], "right": None, "why": ""}
            d["faults"].append(f)
        elif f is None:
            probs.append("%s: %s: comes before any fault: - it belongs to the fault above it" % (sid, k))
        elif k == "do":
            if starred(rest):
                f["right"] = unstar(rest)
            f["do"].append(unstar(rest))
        else:
            f[k] = rest
    if len(d["places"]) < 2 or len(d["faults"]) < 2:
        probs.append("%s: a deck round needs at least two places and two faults (place: ... then fault: ... under it)" % sid)
    for p in d["places"]:
        if not any(x["place"] == p["name"] for x in d["faults"]):
            probs.append("%s: the place %r has no fault to find" % (sid, p["name"]))
    for x in d["faults"]:
        if len(x["do"]) < 2 or sum(1 for o in x["do"] if o == x["right"]) != 1:
            probs.append("%s: the fault %r needs two or more do: lines, exactly one marked *" % (sid, x["name"]))
        for need in ("see", "why"):
            if not x[need]:
                probs.append("%s: the fault %r has no %s: line" % (sid, x["name"], need))
    if not d["intro"]["title"]:
        probs.append("%s: a deck round opens with its card: intro: title | what the trainee is told" % sid)
    words = [d["context"], d["intro"]["title"], d["intro"]["text"]] + [p["name"] for p in d["places"]] + \
        [w for x in d["faults"] for w in [x["name"], x["label"], x["see"], x["hint"]] + x["do"] + [x["why"]]]
    return probs, d, [x["right"] for x in d["faults"] if x["right"]], \
        [o for x in d["faults"] for o in x["do"] if o != x["right"]], [w for w in words if w]


DRESS_KEYS = ("context", "intro", "group", "item", "story", "needs", "one at a time", "ready", "check", "spot", "ask", "reason",
              "explain")


def _dress_for_job(sid, ls, q, probs):
    """dress for the job, then check a buddy: the items on a rack put on a crew member's photograph, judged group by group
    with what happens at the job for each item wrong; then the faults on a colleague's photograph; then one question why"""
    d = {"context": "", "intro": {"title": "", "text": ""}, "groups": [], "items": [], "needs": [], "one": [],
         "ready": {"title": "", "text": ""}, "check": {"ask": "", "says": ""}, "spots": [], "ask": "", "reasons": [],
         "right": None, "explain": {"title": "", "text": ""}}
    it = None

    def two(rest):
        a, _, b = rest.partition("|")
        return a.strip(), b.strip()
    for ln in ls:
        key, sep, rest = ln.partition(":")
        k, rest = key.strip().lower(), rest.strip()
        if not sep or k not in DRESS_KEYS:
            probs.append("%s: a dress-for-the-job line starts with %s - not %r" % (sid, ", ".join(x + ":" for x in DRESS_KEYS), ln))
            continue
        if k in ("context", "ask"):
            d[k] = rest
        elif k in ("intro", "ready", "explain"):
            d[k]["title"], d[k]["text"] = two(rest)
        elif k == "check":
            d["check"]["ask"], d["check"]["says"] = two(rest)
        elif k == "group":
            t, why = two(rest)
            d["groups"].append({"title": t, "why": why})
        elif k == "item":
            if not d["groups"]:
                probs.append("%s: the item %r comes before any group: - each item is judged with the group above it" % (sid, rest))
                continue
            need = starred(rest)
            parts = [x.strip() for x in unstar(rest).split("|")]
            if len(parts) != 3 or not all(parts):
                probs.append("%s: an item is item: name | short name | where it is worn - not %r" % (sid, rest))
                continue
            it = {"group": d["groups"][-1]["title"], "name": parts[0], "short": parts[1], "slot": parts[2], "need": need, "story": ""}
            d["items"].append(it)
        elif k == "story":
            if it is None:
                probs.append("%s: story: comes before any item: - it belongs to the item above it" % sid)
            else:
                it["story"] = rest
        elif k == "needs":
            pair, say = two(rest)
            a, _, b = pair.partition("=>")
            d["needs"].append({"item": a.strip(), "on": b.strip(), "say": say})
        elif k == "one at a time":
            names, say = two(rest)
            d["one"].append({"items": [x.strip() for x in names.split(";") if x.strip()], "say": say})
        elif k == "spot":
            seen, why = two(rest)
            d["spots"].append({"seen": unstar(seen), "fault": starred(seen), "why": why})
        elif k == "reason":
            if starred(rest):
                d["right"] = unstar(rest)
            d["reasons"].append(unstar(rest))
    names = [x["name"] for x in d["items"]]
    if len(d["items"]) < 4 or not any(x["need"] for x in d["items"]) or all(x["need"] for x in d["items"]):
        probs.append("%s: dress for the job needs at least four items on the rack, some needed (marked *) and some not" % sid)
    if len(set(names)) != len(names):
        probs.append("%s: two items have the same name" % sid)
    for g in d["groups"]:
        if not any(x["group"] == g["title"] for x in d["items"]):
            probs.append("%s: the group %r has no item under it" % (sid, g["title"]))
        if not g["why"]:
            probs.append("%s: the group %r needs its why: group: what is judged | why" % (sid, g["title"]))
    for x in d["items"]:
        if not x["story"]:
            probs.append("%s: the item %r needs its story: - what happens at the job when it is worn wrongly or missing" % (sid, x["name"]))
    for r in d["needs"]:
        if r["item"] not in names or r["on"] not in names or not r["say"]:
            probs.append("%s: needs: is item => item it goes onto | what is said, both items on the rack - not %r" % (sid, r))
    for r in d["one"]:
        if len(r["items"]) < 2 or any(x not in names for x in r["items"]) or not r["say"]:
            probs.append("%s: one at a time: is two or more items on the rack, split by ; then | what is said - not %r" % (sid, r))
    if not d["intro"]["title"] or not d["ready"]["title"] or not d["check"]["ask"]:
        probs.append("%s: dress for the job needs intro: title | text, ready: title | text and check: what is asked | what is said" % sid)
    if len(d["spots"]) < 3 or not any(s["fault"] for s in d["spots"]) or all(s["fault"] for s in d["spots"]):
        probs.append("%s: the buddy check needs at least three spot: lines, the faults marked * and some that are fine" % sid)
    for s in d["spots"]:
        if s["fault"] and not s["why"]:
            probs.append("%s: the fault %r needs its why: spot: what is seen * | why" % (sid, s["seen"]))
    if len(set(s["seen"] for s in d["spots"])) != len(d["spots"]):
        probs.append("%s: two spot: lines say the same" % sid)
    if not d["ask"] or len(d["reasons"]) < 2 or sum(1 for r in d["reasons"] if r == d["right"]) != 1 or not d["explain"]["title"]:
        probs.append("%s: it closes with ask: the question, two or more reason: lines with exactly one marked *, and explain: title | text" % sid)
    words = [d["context"], d["intro"]["title"], d["intro"]["text"]] + \
        [w for g in d["groups"] for w in (g["title"], g["why"])] + \
        [w for x in d["items"] for w in (x["name"], x["short"], x["slot"], x["story"])] + \
        [r["say"] for r in d["needs"] + d["one"]] + [d["ready"]["title"], d["ready"]["text"], d["check"]["ask"], d["check"]["says"]] + \
        [w for s in d["spots"] for w in (s["seen"], s["why"])] + [d["ask"]] + d["reasons"] + [d["explain"]["title"], d["explain"]["text"]]
    right = [x["name"] for x in d["items"] if x["need"]] + [s["seen"] for s in d["spots"] if s["fault"]] + ([d["right"]] if d["right"] else [])
    wrong = [x["name"] for x in d["items"] if not x["need"]] + [r for r in d["reasons"] if r != d["right"]]
    return probs, d, right, wrong, unique(words)


def unique(words):
    seen, out = set(), []
    for w in words:
        if w and w not in seen:
            seen.add(w)
            out.append(w)
    return out


LAY_KEYS = ("context", "intro", "reading", "place", "wind", "item", "leak", "rule", "why", "story", "unsafe", "ready")
SIDES_OF_WIND = ("upwind", "downwind")


def metres(s):
    """'15 m' -> (0, 15); '3 to 15 m' -> (3, 15); None when it is not one"""
    m = re.match(r"^\s*(?:(%s)\s*(?:to|-|–)\s*)?(%s)\s*m?\s*$" % (NUM, NUM), s or "")
    if not m:
        return None
    lo, hi = num(m.group(1)) if m.group(1) else 0.0, num(m.group(2))
    return (lo, hi) if 0 <= lo < hi else None


def _lay_out(sid, ls, q, probs):
    """lay out the equipment: the tray's pieces put on a photograph from above, each rule judged by metres and the wind
    (near a place, upwind or downwind of it, on one side of it, two pieces one each side); a leak shows what each rule
    not met means"""
    d = {"context": "", "intro": {"title": "", "text": ""}, "readings": [], "places": [], "winds": [], "items": [], "leak": None,
         "rules": [], "unsafe": None, "ready": {"title": "", "text": ""}}
    r = None

    def parts(rest):
        return [x.strip() for x in rest.split("|")]
    for ln in ls:
        key, sep, rest = ln.partition(":")
        k, rest = key.strip().lower(), rest.strip()
        if not sep or k not in LAY_KEYS:
            probs.append("%s: a lay-out line starts with %s - not %r" % (sid, ", ".join(x + ":" for x in LAY_KEYS), ln))
            continue
        p = parts(rest)
        if k == "context":
            d["context"] = rest
        elif k in ("intro", "ready"):
            d[k] = {"title": p[0], "text": " | ".join(p[1:])}
        elif k == "reading":
            d["readings"].append({"name": p[0], "value": " | ".join(p[1:])})
        elif k == "place":
            d["places"].append(rest)
        elif k == "wind":
            d["winds"].append({"from": p[0], "to": " | ".join(p[1:])})
        elif k == "item":
            if len(p) not in (2, 3) or not all(p):
                probs.append("%s: an item is item: name | short name | letters on its pin - not %r" % (sid, rest))
                continue
            d["items"].append({"name": p[0], "short": p[1], "ab": p[2] if len(p) == 3 else p[1][:2].upper()})
        elif k == "leak":
            d["leak"] = {"place": p[0], "say": " | ".join(p[1:])}
        elif k == "rule":
            if len(p) not in (4, 5):
                probs.append("%s: a rule is rule: what is judged | short name; ... | place | 15 m | side - not %r" % (sid, rest))
                r = None
                continue
            r = {"title": p[0], "items": [x.strip() for x in p[1].split(";") if x.strip()], "place": p[2], "at": metres(p[3]),
                 "dist": p[3], "side": [x.strip() for x in (p[4] if len(p) == 5 else "").split("/") if x.strip()], "why": "", "story": ""}
            d["rules"].append(r)
        elif k == "unsafe":
            r = {"title": p[0], "why": " | ".join(p[1:]), "story": ""}
            d["unsafe"] = r
        elif r is None:
            probs.append("%s: %s: comes before any rule: or unsafe: - it belongs to the one above it" % (sid, k))
        elif k == "why":
            r["why"] = rest
        else:
            r["story"] = rest
    shorts = [x["short"] for x in d["items"]]
    if len(d["items"]) < 4:
        probs.append("%s: lay out needs at least four pieces in the tray (item: ...)" % sid)
    if len(set(shorts)) != len(shorts):
        probs.append("%s: two items have the same short name - the rules name the items by it" % sid)
    if not d["places"] or not d["winds"]:
        probs.append("%s: lay out needs at least one place: and one wind: where it blows from | where it carries a leak" % sid)
    if not d["rules"]:
        probs.append("%s: lay out needs its rules: rule: what is judged | short name | place | 15 m | side" % sid)
    named = set()
    for x in d["rules"]:
        bad = [i for i in x["items"] if i not in shorts]
        named.update(x["items"])
        if not x["items"] or bad:
            probs.append("%s: the rule %r names %s - not a short name of an item in the tray" % (sid, x["title"], ", ".join(map(repr, bad)) or "no item"))
        if x["place"] not in d["places"]:
            probs.append("%s: the rule %r is at %r - not a place:" % (sid, x["title"], x["place"]))
        if not x["at"]:
            probs.append("%s: the rule %r: %r is not a distance - 15 m, or 3 to 15 m" % (sid, x["title"], x["dist"]))
        if len(x["side"]) > 2 or (len(x["side"]) == 2) != (len(x["items"]) == 2) or len(x["items"]) > 2:
            probs.append("%s: the rule %r: one piece has one side or none; two pieces have two sides, one each (forward / aft)" % (sid, x["title"]))
        for need in ("why", "story"):
            if not x[need]:
                probs.append("%s: the rule %r needs its %s:" % (sid, x["title"], need))
    loose = [i for i in shorts if i not in named]
    if loose and not d["unsafe"]:
        probs.append("%s: %s no rule names - they must stay in the tray: say why with unsafe: what is judged | why, and its story:"
                     % (sid, ", ".join(loose)))
    if d["unsafe"] and not (loose and d["unsafe"]["why"] and d["unsafe"]["story"]):
        probs.append("%s: unsafe: needs its why and story:, and pieces in the tray that no rule names" % sid)
    if not d["leak"] or d["leak"]["place"] not in d["places"] or not d["leak"]["say"]:
        probs.append("%s: lay out needs leak: place | what happens there when the layout is checked" % sid)
    if not d["intro"]["title"] or not d["ready"]["title"]:
        probs.append("%s: lay out needs intro: title | text and ready: title | text" % sid)
    for x in d["items"]:
        x["belongs"] = x["short"] in named
    rules = d["rules"] + ([d["unsafe"]] if d["unsafe"] else [])
    words = [d["context"], d["intro"]["title"], d["intro"]["text"]] + [w for x in d["readings"] for w in (x["name"], x["value"])] + \
        d["places"] + [w for x in d["winds"] for w in (x["from"], x["to"])] + [w for x in d["items"] for w in (x["name"], x["short"], x["ab"])] + \
        [(d["leak"] or {}).get("say", "")] + [w for x in rules for w in (x["title"], x["why"], x["story"])] + [d["ready"]["title"], d["ready"]["text"]]
    return probs, d, [x["name"] for x in d["items"] if x["belongs"]], [x["name"] for x in d["items"] if not x["belongs"]], unique(words)
