"""Regression tests for safe historical TF answers and 2-context error evidence."""
from collections import Counter
from types import SimpleNamespace
import os
import sys
from pathlib import Path
import pytest

ROOT = os.environ.get("PHY_APP_ROOT")
if not ROOT:
    pytest.skip("Assembled application required", allow_module_level=True)
sys.path.insert(0, str(Path(ROOT).resolve()))
from app.question_bank import bank
from app.services import diagnostic_profiles_from_session


class NoSQL:
    def __init__(self): self.commits = 0
    def execute(self, *args, **kwargs):
        pytest.fail("A single unreliable probe must not access or update an error profile")
    def commit(self): self.commits += 1


def _response(qid, truth_errors=4, answer_json=None):
    return SimpleNamespace(
        question_id=qid, total_units=4, correct_units=4-truth_errors,
        is_fully_correct=truth_errors==0,
        duration_ms=1900, answer_json=answer_json or {},
    )


def test_a_single_wrong_tf_does_not_confirm_a_misconception():
    q = next(q for q in bank.questions if q["type"]=="tf" and q.get("diagnostic") and q.get("error"))
    db = NoSQL()
    session=SimpleNamespace(responses=[_response(q["id"])], user_id="isolated-student")
    result=diagnostic_profiles_from_session(db,session)
    assert len(result)==1
    assert result[0]["error_id"]==q["error"]
    assert result[0]["needs_confirmation"] is True
    assert result[0]["confidence"] == 0.0
    assert result[0]["decision_source"] == "INSUFFICIENT_EVIDENCE"


def test_two_wrong_probes_with_same_context_still_need_confirmation(monkeypatch):
    q = next(q for q in bank.questions if q["type"]=="tf" and q.get("diagnostic") and q.get("error"))
    fake = {**q, "id": "V6-SAME-CONTEXT-PROBE"}
    original=bank.by_id
    monkeypatch.setattr(bank,"by_id",{**original, fake["id"]:fake})
    db=NoSQL()
    result=diagnostic_profiles_from_session(
        db,
        SimpleNamespace(responses=[_response(q["id"]),_response(fake["id"])],user_id="isolated-student")
    )
    assert len(result)==1
    assert result[0]["independent_failed_probes"]==2
    assert result[0]["independent_contexts"]==1
    assert result[0]["needs_confirmation"] is True


def test_scaffolded_practice_prefers_foundational_questions_and_diversity():
    fake=[
        {"id":"A","lesson":"Bài 1","type":"mcq","level":"VD","prompt":"Tính áp suất khi V=2 L"},
        {"id":"B","lesson":"Bài 1","type":"mcq","level":"NB","prompt":"Các hạt chất rắn có chuyển động không?"},
        {"id":"C","lesson":"Bài 1","type":"mcq","level":"NB","prompt":"Các hạt chất lỏng có chuyển động không?"},
        {"id":"D","lesson":"Bài 1","type":"mcq","level":"VD","prompt":"Tính áp suất khi V=3 L"},
    ]
    chosen=bank.scaffolded_practice(fake,fake[:2],"foundation")
    assert len(chosen)==2
    assert Counter(q["level"] for q in chosen)=={"NB":2}
    assert len({q["id"] for q in chosen})==2
    assert bank.question_template(fake[0])==bank.question_template(fake[3])
    assert bank.question_template(fake[0])!=bank.question_template(fake[1])


def test_historic_tf_question_id_still_grades_in_original_order():
    from app.quality_v5 import PLAN_FILE
    import json
    plan=json.loads(PLAN_FILE.read_text(encoding="utf-8"))
    for change in plan["changes"]:
        old=bank.by_id[change["id"]]
        new=bank.by_id[change["id"]+"-V5"]
        answer_old=[s["answer"] for s in old["statements"]]
        answer_new=[s["answer"] for s in new["statements"]]
        assert bank.grade(old,answer_old)["is_fully_correct"]
        assert bank.grade(new,answer_new)["is_fully_correct"]
        assert answer_new==[answer_old[i] for i in change["order"]]
        assert old["id"] != new["id"]
