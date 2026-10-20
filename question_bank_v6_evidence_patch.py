"""V6 conservative diagnostic evidence and differentiated practice patch.

Never generates scientific answers or claims one wrong choice proves a misconception.
Runs after the original hybrid/AI and adaptive diagnostic patches.
"""
from pathlib import Path
import sys

def replace_one(text, old, new, label):
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one insertion point, got {count}")
    return text.replace(old, new, 1)

def apply(root=Path("/app")):
    root=Path(root)
    services=root/"app/services.py"
    main=root/"app/main.py"
    bank=root/"app/question_bank.py"
    svc=services.read_text(encoding="utf-8")
    src=bank.read_text(encoding="utf-8")
    api=main.read_text(encoding="utf-8")

    # Trace distinct failed questions and learning situations instead of treating
    # 4 failed TF statements as 4 independent confirmations.
    before='        e = evidence[q["error"]]\n'
    after=before+'''        e.setdefault("probes", set()).add(str(r.question_id))
        if not bool(r.is_fully_correct):
            e.setdefault("failed_probes", set()).add(str(r.question_id))
            evidence_context = (
                str(q.get("context") or "").strip().casefold(),
                str(q.get("type") or "").strip(),
            )
            e.setdefault("failed_contexts", set()).add(evidence_context)
'''
    svc=replace_one(svc,before,after,"evidence probe accounting")
    old='                if code not in bank.error_by_id:\n                    continue\n'
    new='''                if code not in bank.error_by_id or code != q.get("error"):
                    # Do not let an unrelated model guess attach evidence for an
                    # ontology code that this item has not been authored to test.
                    continue
'''
    svc=replace_one(svc,old,new,"LLM ontology-scoped evidence")

    anchor='    for error_id, e in evidence.items():\n        if e["wrong"] <= 0:\n            continue\n'
    insert=anchor+'''        failed_probes=e.get("failed_probes", set())
        independent_contexts=e.get("failed_contexts", set())
        if len(failed_probes) < 2 or len(independent_contexts) < 2:
            # Candidate only; never update stored ErrorProfile with a single
            # question, even when it contains 4 wrong TF statements.
            out.append({
                "error_id": error_id, "confidence": 0.0,
                "state": "Chưa đủ bằng chứng", "wrong": e["wrong"],
                "total": e["total"], "decision_source": "INSUFFICIENT_EVIDENCE",
                "needs_confirmation": True,
                "independent_failed_probes": len(failed_probes),
                "independent_contexts": len(independent_contexts),
            })
            continue
'''
    svc=replace_one(svc,anchor,insert,"low-evidence safeguard")

    # Repair recheck must reference the explicit misconception tag, not an
    # arbitrary string representation that might contain an unrelated code.
    old='                if q and prof.error_id in str(q):\n                    mapped.append(response)\n'
    new='                if q and q.get("error") == prof.error_id:\n                    mapped.append(response)\n'
    api=replace_one(api,old,new,"strict recheck scope")
    old='            if len(mapped) >= 2 and all(bool(r.is_fully_correct) for r in mapped):\n'
    new='''            contexts = {
                (str(bank.by_id[r.question_id].get("context", "")).strip().casefold(),
                 str(bank.by_id[r.question_id].get("type", "")))
                for r in mapped
            }
            if len({r.question_id for r in mapped}) >= 2 and len(contexts) >= 2 and all(bool(r.is_fully_correct) for r in mapped):
'''
    api=replace_one(api,old,new,"independent recheck contexts")

    # Explain quiz reliability explicitly in metadata for traceable audits.
    policy_anchor='    def stats(self):\n'
    policy='''    def misconception_probe_coverage(self):
        from collections import defaultdict
        rows = defaultdict(list)
        for q in self.questions:
            if q.get("diagnostic") and q.get("error") in self.error_by_id:
                rows[q["error"]].append(q)
        return {
            code: {
                "probe_count": len(rows[code]),
                "context_count": len(set(
                    (str(q.get("context", "")).strip().casefold(), q.get("type"))
                    for q in rows[code]
                )),
                "verified_independent": (
                    len(rows[code]) >= 2 and
                    len(set(
                        (str(q.get("context", "")).strip().casefold(), q.get("type"))
                        for q in rows[code]
                    )) >= 2
                ),
            } for code in self.error_by_id
        }

'''
    src=replace_one(src,policy_anchor,policy+policy_anchor,"probe coverage audit helper")
    # Provide foundation-first practice and suppress near-identical number variants
    # inside the same practice session. Question content is never mutated.
    picker_anchor='    @staticmethod\n    def tf_score(correct_count: int) -> float:\n'
    picker='''    @staticmethod
    def question_template(question):
        import re
        import unicodedata
        stem = unicodedata.normalize("NFC", str(question.get("prompt", "")).casefold())
        stem = re.sub(r"[+-]?\\d+(?:[.,]\\d+)?(?:\\s*[×*]\\s*10\\s*\\^?\\s*[+-]?\\d+)?", "#", stem)
        stem = re.sub(r"\\s+", " ", stem).strip()
        return (question.get("lesson"), question.get("type"), stem)

    @classmethod
    def scaffolded_practice(cls, pool, standard_selection, band):
        """Re-select without repeating near-clone templates if alternatives exist.

        NB/TH preference is a selection policy, not a claim that old VD
        questions were rewritten or that the difficulty labels are validated.
        """
        if band not in ("foundation", "developing"):
            return standard_selection
        limit = len(standard_selection)
        difficulty = (
            {"NB":0, "TH":1, "VD":2, "VDC":3}
            if band == "foundation" else
            {"TH":0, "NB":1, "VD":2, "VDC":3}
        )
        picked = []
        used_ids = set()
        used_templates = set()
        lesson_hits = {}
        remaining = list(pool)
        while len(picked) < limit and remaining:
            fresh_templates = [
                q for q in remaining
                if cls.question_template(q) not in used_templates
            ]
            choices = fresh_templates or remaining
            q = min(
                choices,
                key=lambda item: (
                    difficulty.get(item.get("level"), 3),
                    lesson_hits.get(item.get("lesson"), 0),
                    str(item.get("id")),
                ),
            )
            remaining.remove(q)
            if q.get("id") in used_ids:
                continue
            picked.append(q)
            used_ids.add(q["id"])
            used_templates.add(cls.question_template(q))
            lesson_hits[q.get("lesson")] = lesson_hits.get(q.get("lesson"), 0) + 1
        return picked

'''
    src=replace_one(src,picker_anchor,picker+picker_anchor,"scaffolded and diverse practice")

    old='    selected=bank.select_practice(pool,req.scope,req.intensity)\n'
    new='''    selected=bank.select_practice(pool,req.scope,req.intensity)
    if req.mode == "practice":
        student_band = recent_performance(db, student.id).get("band", "developing")
        selected = bank.scaffolded_practice(pool, selected, student_band)
'''
    api=replace_one(api,old,new,"student level-aware practice")
    services.write_text(svc,encoding="utf-8")
    main.write_text(api,encoding="utf-8")
    bank.write_text(src,encoding="utf-8")
    print("V6: insufficient-evidence gate, explicit LLM scope, safe rechecks installed")

if __name__=="__main__":
    apply(Path(sys.argv[1]) if len(sys.argv)>1 else Path("/app"))
