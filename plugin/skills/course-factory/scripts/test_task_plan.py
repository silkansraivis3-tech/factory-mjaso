"""Tests for task_plan.py - the questions of a module planned before its script is written, and the order that keeps
neighbouring questions of one family apart. Run: python test_task_plan.py"""
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import task_plan as tp  # noqa: E402

FAILS = []


def check(name, ok, detail=""):
    print("  %s  %s%s" % ("ok  " if ok else "FAIL", name, "" if ok else "  -> %s" % (detail,)))
    if not ok:
        FAILS.append(name)


def apart(fams, order):
    seq = [fams[i] for i in order]
    return sorted(order) == list(range(len(fams))) and all(a != b for a, b in zip(seq, seq[1:]))


def main():
    print("-- the order that keeps neighbours of one family apart")
    f = ["choose", "choose", "arrange", "arrange", "arrange", "decide"]
    o = tp.spread(f)
    check("choose choose arrange arrange arrange decide has an order with no two neighbours alike", o and apart(f, o), o)
    check("an order already apart stays as it is", tp.spread(["a", "b", "a", "c"]) == [0, 1, 2, 3])
    check("four of five of one family has no such order", tp.spread(["a", "a", "a", "a", "b"]) is None)
    check("three of five does: a b a b a", apart(["a", "a", "a", "b", "b"], tp.spread(["a", "a", "a", "b", "b"])))
    parts = [0, 0, 0, 1, 1, 1]
    f2 = ["choose", "arrange", "choose", "build", "decide", "build"]
    o2 = tp.spread(f2, parts)
    check("a self-check's Part A stays before Part B", o2 and apart(f2, o2) and [parts[i] for i in o2] == sorted(parts), o2)
    check("... and when only crossing the parts would keep them apart, there is no order",
          tp.spread(["a", "a", "b"], [0, 0, 1]) is None)

    print("\n-- the plan of a module's questions")
    rows = [{"sid": "1.%d" % i, "task_type": "decision", "level": lv} for i, lv in enumerate((2, 3, 4, 3, 5), 1)]
    p = tp.plan(rows)
    sc = [x["self_check"] for x in p["sub_ilos"]]
    mc = [x["module_check"] for x in p["sub_ilos"]]
    check("every Sub-ILO gets a self-check and a module-check kind", all(sc) and all(mc), p["sub_ilos"])
    check("... of two families", all(tp.family(a) != tp.family(b) for a, b in zip(sc, mc)))
    check("... each reaching the Sub-ILO's level", all(tp.LEVELS[m]["ceiling"] >= r["level"] for r, m in zip(rows, sc)))
    check("a self-check question from Apply up is rich, never choose or arrange",
          all(tp.family(m) not in ("choose", "arrange") for r, m in zip(rows, sc) if r["level"] >= 3), sc)
    used = Counter(tp.family(m) for m in sc + mc)
    check("the module uses five families or more", len(used) >= 5, used)
    check("no mechanic is planned three times", max(Counter(sc + mc).values()) <= 2, Counter(sc + mc))
    check("one challenge question where a Sub-ILO asks Apply or higher",
          any(tp.MEDIA[m].get("part") == "challenge" for m in sc + mc), sc + mc)
    fams = [tp.family(s["mechanic"]) for s in p["module_check"]]
    check("the module check's slots: no two neighbours of one family", all(a != b for a, b in zip(fams, fams[1:])), fams)
    check("a decision Sub-ILO is never asked on equipment",
          not set(sc + mc) & set(tp.TP["equipment_mechanics"]), sc + mc)
    hands = tp.plan([{"sid": "2.1", "task_type": "fixed_sequence", "level": 3}])
    check("a hands-on Sub-ILO is asked by operating first", tp.family(hands["sub_ilos"][0]["self_check"]) == "operate", hands)
    two = tp.plan([{"sid": "3.1", "task_type": "decision", "level": 2}, {"sid": "3.2", "task_type": "decision", "level": 3}])
    check("a module of two Sub-ILOs still gets a module check of five", len(two["module_check"]) == 5, two["module_check"])
    fams2 = [tp.family(s["mechanic"]) for s in two["module_check"]]
    check("... kept apart by family", all(a != b for a, b in zip(fams2, fams2[1:])), fams2)

    print("\n%d failed" % len(FAILS) if FAILS else "\nall passed")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
