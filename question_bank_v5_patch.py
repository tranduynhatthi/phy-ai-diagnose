"""Build-time hook: apply audited TF order balancing to the effective question bank.

The bank is not regenerated. Only the order of four existing TF statements is
modified, and the original truth value plus explanation travel with each statement.
Requires versioned session snapshots before production rollout because historic
responses use positional statement indices.
"""
from pathlib import Path
import sys

QUALITY_MODULE = r'''"""PHY-AI DIAGNOSE V5: auditable true/false answer-pattern rebalance."""
from collections import Counter, defaultdict
import json
from pathlib import Path
from .content_audit import validate_questions

PLAN_FILE = Path(__file__).parent / "data" / "question_bank_v5_tf_rebalance.json"


def pattern(question):
    return "".join("T" if item["answer"] else "F" for item in question["statements"])


def summarize(data):
    questions = data["questions"]
    tf = [q for q in questions if q["type"] == "tf"]
    codes = defaultdict(lambda: {"total": 0, "diagnostic": 0, "contexts": set()})
    for q in questions:
        code = q.get("error")
        if not code:
            continue
        record = codes[code]
        record["total"] += 1
        if q.get("diagnostic") is True:
            record["diagnostic"] += 1
            record["contexts"].add(str(q.get("context", "")).strip().lower())
    underprobed = sorted(
        ({"error": code, "diagnostic_questions": r["diagnostic"],
          "independent_context_labels": len(r["contexts"])}
         for code, r in codes.items()
         if r["diagnostic"] < 2 or len(r["contexts"]) < 2),
        key=lambda x: (x["diagnostic_questions"], x["independent_context_labels"], x["error"]),
    )
    return {
        "questions": len(questions),
        "chapters": dict(Counter(q["chapter"] for q in questions)),
        "types": dict(Counter(q["type"] for q in questions)),
        "levels": dict(Counter(q["level"] for q in questions)),
        "tf_patterns": dict(Counter(pattern(q) for q in tf)),
        "errors": len(codes),
        "diagnostic_questions": sum(q.get("diagnostic") is True for q in questions),
        "underprobed_errors": underprobed,
        "note": "Context labels are a proxy, not a proof of item independence or psychometric validity.",
    }


def apply_v5_rebalance(data):
    plan = json.loads(PLAN_FILE.read_text(encoding="utf-8"))
    if plan["schema_version"] != 1:
        raise ValueError("Unknown v5 audit schema")
    if data["version"] != plan["base_version"]:
        raise ValueError("V5 plan needs exactly the reviewed V4 bank")
    if len(data["questions"]) != 1000:
        raise ValueError("V5 requires the complete 1000-question bank")
    by_id = {q["id"]: q for q in data["questions"]}
    if len(by_id) != 1000:
        raise ValueError("Duplicate question identifiers in V5 bank")
    prior = summarize(data)
    if prior["tf_patterns"] != plan["tf_patterns_before"]:
        raise ValueError("The V4 true/false patterns differ from the audited baseline")

    prepared = []
    seen = set()
    for item in plan["changes"]:
        qid = item["id"]
        if qid in seen or qid not in by_id:
            raise ValueError("Duplicate or missing V5 question id: " + qid)
        seen.add(qid)
        q = by_id[qid]
        order = item["order"]
        if q["type"] != "tf" or sorted(order) != [0, 1, 2, 3]:
            raise ValueError("Invalid statement permutation: " + qid)
        if pattern(q) != item["before"]:
            raise ValueError("Truth pattern drift before reordering: " + qid)
        shifted = [q["statements"][index] for index in order]
        if "".join("T" if st["answer"] else "F" for st in shifted) != item["after"]:
            raise ValueError("V5 answer pattern mismatch: " + qid)
        prepared.append((q, shifted))

    if len(prepared) != plan["counts"]["changed_tf"]:
        raise ValueError("Incomplete V5 change plan")
    for q, shifted in prepared:
        q["statements"] = shifted
    validate_questions(data)
    report = summarize(data)
    if report["tf_patterns"] != plan["tf_patterns_after"]:
        raise ValueError("V5 distribution fails its review target")
    data["version"] = "2026.10-1000q-v5-tf-balanced"
    data.setdefault("audit", {})["v5_quality"] = {
        "method": "Stable, recorded permutations of existing statements; no assertions flipped.",
        "changed_tf_questions": len(prepared),
        "baseline": prior,
        "rebalanced": report,
        "limits": [
            "Some errors have insufficient independent diagnostic probes.",
            "Option-level misconception mapping still needs expert curation.",
            "Unbalanced truth-count frequencies require new/revised scientific statements, not permutations.",
            "Historic positional answers require a versioned compatibility policy before production deployment.",
            "Performance statistics must be calibrated on real student response data.",
        ],
    }
    return report
'''

def apply(root=Path("/app")):
    root = Path(root)
    module_path = root / "app" / "quality_v5.py"
    plan_path = root / "app" / "data" / "question_bank_v5_tf_rebalance.json"
    if not plan_path.is_file():
        raise RuntimeError("V5 question bank permutation plan is absent")
    bank_path = root / "app" / "question_bank.py"
    s = bank_path.read_text(encoding="utf-8")
    marker = "        apply_student_formula_policy(self.data)\n"
    hook = "        from .quality_v5 import apply_v5_rebalance\n        apply_v5_rebalance(self.data)\n"
    if hook not in s:
        if s.count(marker) != 1:
            raise RuntimeError("Cannot find the v4 student formula policy hook")
        s = s.replace(marker, marker + hook, 1)
    module_path.write_text(QUALITY_MODULE, encoding="utf-8")
    bank_path.write_text(s, encoding="utf-8")
    print("V5 TF quality patch installed, pending startup validation")

if __name__ == "__main__":
    apply(Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/app"))
