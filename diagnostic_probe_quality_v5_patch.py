"""Tighten diagnostic selection: explicit ontology mapping and context diversity.

The older selector looked for an error code anywhere in str(question), which can
accidentally match a description or explanation and invent a diagnostic mapping.
This patch uses the audited structured error tag only. Multiple probes for a
target code should, whenever possible, come from different context labels.
"""
from pathlib import Path
import re
import sys

def apply(root=Path("/app")):
    path=Path(root)/"app"/"main.py"
    s=path.read_text(encoding="utf-8")
    start=s.index('def _question_error_codes(question: dict) -> set[str]:')
    end=s.index('\n\ndef _error_matches_scope(',start)
    replacement='''def _question_error_codes(question: dict) -> set[str]:
    """Read only reviewed ontology tags, never substring matches in free text."""
    code=question.get("error")
    if not isinstance(code,str) or code not in bank.error_by_id:
        return set()
    return {code}


def _context_diverse_probes(questions: list[dict]) -> list[dict]:
    """Choose unique contexts first; follow with remaining distinct questions."""
    import re
    ordered=sorted(questions,key=lambda q:str(q.get("id","")))
    groups={}
    for q in ordered:
        name=re.sub(r"\s+"," ",str(q.get("context","")).strip().lower())
        if not name:
            name="_no_context_"
        groups.setdefault(name,[]).append(q)
    chosen=[rows.pop(0) for rows in groups.values()]
    return chosen+[q for rows in groups.values() for q in rows]
'''
    s=s[:start]+replacement+s[end:]
    original='''    for code, questions in by_error.items():
        questions.sort(key=lambda q: str(q.get("id", "")))'''
    revised='''    for code, questions in by_error.items():
        by_error[code] = _context_diverse_probes(questions)'''
    if s.count(original)!=1:raise ValueError("Adaptive selector marker changed")
    s=s.replace(original,revised,1)
    path.write_text(s,encoding="utf-8")
    print("V5: explicit error mappings and context-diverse probes installed")

if __name__=="__main__":
    apply(Path(sys.argv[1]) if len(sys.argv)>1 else Path("/app"))
