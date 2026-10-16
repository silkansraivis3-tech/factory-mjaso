# -*- coding: utf-8 -*-
"""gate_fixture - for the tests only: open the Stage 2 gate on a test course (2.38.0).

    import gate_fixture; gate_fixture.open_gate(course, sub_ilos={1: [...]})

Every module's content script now waits for an approved ILO map and a knowledge-base decision
(course_gate.py). A test course that is about something else gets both here, the way a real course
gets them: architecture.json (kept if the test wrote its own), ilo_map.py build, the approval recorded
with the ILO map's fingerprint, and a knowledge-base decision in intake.json.
"""
from __future__ import annotations

import io
import json
import os
import sys
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ilo_map  # noqa: E402
import workspace  # noqa: E402

DEFAULT_SUBS = [{"id": "1.1", "status": "added", "text": "Explain why liquefied gas is carried cold, under pressure, or both.",
                 "why": "test"},
                {"id": "1.2", "status": "added", "text": "Identify the cargo containment systems and the secondary barrier each needs.",
                 "why": "test"}]


def _save(p, obj):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with io.open(p, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def open_gate(course, sub_ilos=None, kb=None, approve=True):
    """sub_ilos: {module number: [sub-ILO dicts]} for modules the test's architecture lacks (default: module 1).
    kb: None = declined with a reason; a dict = written as knowledge_base_decision; False = none recorded."""
    ap = workspace.claude_path(course, "architecture.json")
    arch = json.load(io.open(ap, encoding="utf-8")) if os.path.isfile(ap) else {
        "course": {"title": "Test course", "course_language": "English", "operator_language": "en", "course_type": "NEW_ENTRANT"},
        "main_ilos": [{"id": "1", "text": "Contribute to safe cargo operations"}], "modules": [],
        "final_assessment": {"topic": "99", "graded": True}}
    have = {ilo_map.mkey(m.get("module")) for m in arch.get("modules", [])}
    for n, subs in (sub_ilos or ({1: DEFAULT_SUBS} if 1 not in have else {})).items():
        if n not in have:
            arch["modules"].append({"module": n, "title": "Module %s" % n, "main_ilos": ["1"], "sub_ilos": subs})
    _save(ap, arch)
    ilo_map.build(course, quiet=True)
    if approve:
        prog, arch = ilo_map.course_files(course)
        rows, _ = ilo_map.derive(prog, arch)
        arch["approved"] = {"by": "Test", "on": date.today().isoformat(), "ilo_map_hash": ilo_map.fingerprint(rows)}
        _save(ap, arch)
    if kb is not False:
        ip = workspace.claude_path(course, "intake.json")
        intake = json.load(io.open(ip, encoding="utf-8")) if os.path.isfile(ip) else {}
        intake["knowledge_base_decision"] = kb or {"answer": "declined", "reason": "a test course has no sources", "decided": "2026-10-16"}
        _save(ip, intake)
    return course
