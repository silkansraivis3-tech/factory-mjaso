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
"""
from __future__ import annotations

import base64
import json
import re

TYPES = ("true_false", "critique", "calculate", "predict", "explore", "investigate", "line_up", "inspect_round",
         "take_apart", "test_atmosphere")
USES = {"true_false": {"answer"}, "critique": {"answer"}, "calculate": {"answer"}, "predict": {"answer"},
        "explore": {"answer"}, "investigate": {"options", "answer"}, "line_up": {"answer", "visual"},
        "inspect_round": {"answer", "visual"}, "take_apart": {"answer", "visual"}, "test_atmosphere": {"answer"}}
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
