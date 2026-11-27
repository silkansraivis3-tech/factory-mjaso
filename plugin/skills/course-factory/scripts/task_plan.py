"""The trainee questions of a module, planned by code before its script is written: each Sub-ILO gets a kind of question
for its self-check and another for the module check, varied across the module by family (how the trainee answers) and
by mechanic, at the Sub-ILO's Bloom level; the module check's slots come in an order where no two neighbours answer the
same way. The writer fills the slots; content_script.py checks the result (theory-rules.json task_plan, task_variety).

spread() is also the order the content check proposes for a set with two neighbours of one family."""
import io
import json
import os
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
KNOW = os.path.join(os.path.dirname(HERE), "knowledge")
_load = lambda n: json.load(io.open(os.path.join(KNOW, n), encoding="utf-8"))
MEDIA = _load("media-and-tasks.json")["mechanics"]
LEVELS = _load("bloom.json")["mechanics"]
RULES = _load("theory-rules.json")
TP = RULES["task_plan"]
ORDER = [k for k in MEDIA if not k.startswith("_") and k in LEVELS]


def family(m):
    return (MEDIA.get(m) or {}).get("family") or m


def label(m):
    return (MEDIA.get(m) or {}).get("en") or m


# ------------------------------------------------------------------ an order with no two neighbours of one family
def spread(fams, parts=None):
    """[indexes] - the items in the order nearest their own where no two neighbours share a family, or None when there
    is none. parts: a rank per item kept in order (a self-check's Part A before Part B)."""
    n = len(fams)
    parts = list(parts) if parts is not None else [0] * n
    keys = [(parts[i], fams[i]) for i in range(n)]
    failed = set()

    def go(left, prev):
        if not left:
            return []
        state = (tuple(sorted(Counter(keys[i] for i in left).items())), prev)
        if state in failed:
            return None
        low = min(parts[i] for i in left)
        tried = set()
        for i in left:
            if parts[i] != low or fams[i] == prev or keys[i] in tried:
                continue
            tried.add(keys[i])
            rest = go([j for j in left if j != i], fams[i])
            if rest is not None:
                return [i] + rest
        failed.add(state)
        return None

    return go(list(range(n)), None)


# ------------------------------------------------------------------ the plan
def _pool(task_type):
    """the mechanics a Sub-ILO of this task type may be asked in - the equipment ones only where hands do the work"""
    eq = set(TP["equipment_mechanics"])
    hands = task_type in TP["equipment_task_types"]
    return [m for m in ORDER if hands or m not in eq]


def _pick(level, task_type, used_m, used_f, avoid_fam=None, part=None, rich=False):
    """the mechanic for one question: one that reaches the level, of the families this task type prefers, the family and
    the mechanic least used in the module so far, closest to the level"""
    prefer = TP["by_task_type"].get(task_type) or TP["by_task_type"]["decision"]
    basic = set(RULES["self_check"]["basic_families"])
    cands = [m for m in _pool(task_type)
             if LEVELS[m]["ceiling"] >= level and family(m) != avoid_fam
             and (part is None or MEDIA[m].get("part") == part)
             and not (rich and family(m) in basic)]
    if not cands:
        return None
    rank = lambda m: (prefer.index(family(m)) if family(m) in prefer else len(prefer))
    return min(cands, key=lambda m: (used_f[family(m)] + used_m[m], rank(m), abs(LEVELS[m]["typical"] - level), ORDER.index(m)))


def plan(rows):
    """rows: [{sid, task_type, level}] (activity_formats.plan) -> {"sub_ilos": [{sid, level, self_check, module_check}],
    "module_check": [{sid, mechanic}]} - the self-check question asks at the Sub-ILO's level (Part B, rich, from Apply
    up), the module check's another family; at least one challenge question where a Sub-ILO asks Apply or higher"""
    used_m, used_f, out = Counter(), Counter(), []
    for r in rows:
        lv = int(r.get("level") or 3)
        tt = r.get("task_type") or "decision"
        sc = _pick(lv, tt, used_m, used_f, rich=lv >= TP["challenge_from_level"])
        if sc:
            used_m[sc] += 1; used_f[family(sc)] += 1
        mc = _pick(lv, tt, used_m, used_f, avoid_fam=family(sc) if sc else None)
        if mc:
            used_m[mc] += 1; used_f[family(mc)] += 1
        out.append({"sid": str(r.get("sid")), "level": lv, "task_type": tt, "self_check": sc, "module_check": mc})
    top = [p for p in out if p["level"] >= TP["challenge_from_level"]]
    if top and not any(MEDIA.get(p[k] or "", {}).get("part") == "challenge" for p in out for k in ("self_check", "module_check")):
        p = max(top, key=lambda x: x["level"])
        ch = _pick(p["level"], p["task_type"], used_m, used_f, avoid_fam=family(p["self_check"]) if p["self_check"] else None,
                   part="challenge")
        if ch:
            p["module_check"] = ch
    slots = [{"sid": p["sid"], "mechanic": p["module_check"]} for p in out if p["module_check"]]
    lo = RULES["module_check"]["min_questions"]
    extra = sorted(out, key=lambda p: -p["level"])
    while slots and len(slots) < lo:                  # too few Sub-ILOs: the highest ones ask a second time, in a new kind
        p = extra[(len(slots) - len(out)) % len(extra)]
        got = Counter(s["mechanic"] for s in slots)
        m = _pick(p["level"], p["task_type"], got + used_m, Counter(family(s["mechanic"]) for s in slots) + used_f)
        if not m:
            break
        slots.append({"sid": p["sid"], "mechanic": m})
        used_m[m] += 1; used_f[family(m)] += 1
    order = spread([family(s["mechanic"]) for s in slots])
    return {"sub_ilos": out, "module_check": [slots[i] for i in order] if order else slots}


def report(tp):
    lines = ["  Questions - each Sub-ILO's \"mechanic\" (task_plan.py; another of the same family is fine):"]
    keep = lambda m: "  <- a challenge task: keep this mechanic" if (MEDIA.get(m) or {}).get("part") == "challenge" else ""
    for p in tp["sub_ilos"]:
        lines.append("    %-6s self-check: %s (%s)%s   module check: %s (%s)%s" % (
            p["sid"], p["self_check"], family(p["self_check"]), keep(p["self_check"]),
            p["module_check"], family(p["module_check"]), keep(p["module_check"])))
    lines.append("  Module check, in this order: " + ", ".join("%s %s" % (s["sid"], s["mechanic"]) for s in tp["module_check"]))
    return "\n".join(lines)
