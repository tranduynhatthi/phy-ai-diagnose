"""V6 misconception-content regression: SGK anchored probes and historical grading."""
import os,sys
from pathlib import Path
from collections import Counter
import pytest
ROOT=os.environ.get("PHY_APP_ROOT")
if not ROOT:
    pytest.skip("Assembled app required", allow_module_level=True)
sys.path.insert(0,str(Path(ROOT).resolve()))
from app.question_bank import bank
from app.quality_v6_content import PROBES

EXPECTED={
    "TT-13": {"EXT-16-M04","EXT-16-M05"},
    "HN-07": {"EXT-22-M04","EXT-22-M05"},
    "HN-13": {"EXT-23-M02","EXT-23-M03"},
    "HN-14": {"EXT-23-M04","EXT-23-M05"},
}

def test_counts_science_and_provenance():
    assert len(bank.questions)==1000
    assert len(set(q["id"] for q in bank.questions))==1000
    assert Counter(q["type"] for q in bank.questions)=={"mcq":532,"tf":218,"short":250}
    assert Counter(q["chapter"] for q in bank.questions)=={
        "Chương I":250,"Chương II":250,"Chương III":250,"Chương IV":250
    }
    assert bank.data["version"]=="2026.10-1000q-v6-content-evidence"
    assert bank.data["audit"]["v6_content"]["replacements"]==8

def test_new_and_old_question_ids_remain_distinct_and_gradable():
    assert len(PROBES)==8
    for source_id,spec in PROBES.items():
        new=bank.by_id[source_id+"-V6"]
        old=bank.by_id[source_id]
        assert new["legacy_id"]==old["id"]==source_id
        assert new["id"]==source_id+"-V6"
        assert old["prompt"]!=new["prompt"]
        assert new["error"]==spec["error"]
        assert new["diagnostic"] is True
        assert new["source_page"]==spec["source_page"]
        assert new["verified"] is False
        assert len(new["options"])==4 and len(set(new["options"]))==4
        assert new["options"][new["answer"]].strip()
        assert new["explain"].strip()
        assert bank.grade(new,new["answer"])["is_fully_correct"]
        assert bank.grade(old,old["answer"])["is_fully_correct"]

def test_four_undersampled_misconceptions_now_get_two_independent_contexts():
    by_error={}
    for q in bank.questions:
        if q.get("diagnostic") and q.get("error") in EXPECTED:
            by_error.setdefault(q["error"],[]).append(q)
    coverage=bank.misconception_probe_coverage()
    for code,originals in EXPECTED.items():
        items=by_error.get(code,[])
        contexts={(str(q.get("context","")).strip().casefold(),q["type"]) for q in items}
        assert len(items)>=2,(code,items)
        assert len(contexts)>=2,(code,items)
        assert coverage[code]["verified_independent"]
        assert {id+"-V6" for id in originals}.issubset(set(q["id"] for q in items))

def test_new_multiple_choice_distractors_not_identical():
    for source_id in PROBES:
        q=bank.by_id[source_id+"-V6"]
        answer=q["answer"]
        assert type(answer) is int and 0<=answer<4
        assert len([i for i in range(4) if i!=answer])==3
