"""Print a reproducible ontology coverage and candidate review queue.

This reports quality risks; it does not automatically declare sourcebook alignment
or generate plausible-looking unverified physics questions.
"""
from collections import defaultdict, Counter
from difflib import SequenceMatcher
import json
import re

from app.question_bank import bank

codes = bank.misconception_probe_coverage()
by_code = defaultdict(list)
for q in bank.questions:
    if q.get("error"):
        by_code[q["error"]].append(q)

suspects = []
by_template=defaultdict(list)
for q in bank.questions:
    by_template[bank.question_template(q) if hasattr(bank, "question_template") else (q["lesson"],q["type"],q["prompt"])].append(q)
for group in by_template.values():
    if len(group)>1:
        suspects.append({"ids":[q["id"] for q in group],"lesson":group[0]["lesson"],"type":group[0]["type"]})

risk = [code for code,v in codes.items() if not v["verified_independent"]]
risk.sort(key=lambda code:(codes[code]["probe_count"],codes[code]["context_count"],code))

def describe(q):
    result={k:q.get(k) for k in ("id","lesson","level","type","error","context","prompt","diagnostic")}
    if q["type"]=="mcq":
        result["options"]=q.get("options")
        result["answer"]=q.get("answer")
    elif q["type"]=="tf":
        result["statements"]=q.get("statements")
    else:
        result["answer"]=q.get("answer")
        result["unit"]=q.get("unit")
    return result

report={
    "question_count":len(bank.questions),
    "diagnostic_counts":dict(Counter(q.get("diagnostic",False) for q in bank.questions)),
    "ontology_underprobed_count":len(risk),
    "underprobed": [{
        "error_code":code,
        "title":bank.error_by_id[code].get("title"),
        "symptom":bank.error_by_id[code].get("symptom"),
        **codes[code],
        "original_questions":[describe(q) for q in by_code[code][:8]],
    }for code in risk],
    "same_numeric_template_groups":sorted(suspects,key=lambda x:(-len(x["ids"]),x["ids"][0])),
    "limit":"Same-template matching is a review lead, not proof that questions are redundant.",
}
print(json.dumps(report,ensure_ascii=False,indent=2))
