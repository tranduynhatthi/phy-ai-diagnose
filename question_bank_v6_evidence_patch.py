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
    services.write_text(svc,encoding="utf-8")
    main.write_text(api,encoding="utf-8")
    bank.write_text(src,encoding="utf-8")
    print("V6: insufficient-evidence gate, explicit LLM scope, safe rechecks installed")

if __name__=="__main__":
    apply(Path(sys.argv[1]) if len(sys.argv)>1 else Path("/app"))
