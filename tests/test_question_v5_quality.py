"""Regression coverage for the reviewed PHY-AI DIAGNOSE 1000-item V5 bank."""
import json
import os
from collections import Counter
from copy import deepcopy
from pathlib import Path
import sys

import pytest

APP_ROOT = os.environ.get("PHY_APP_ROOT")
if not APP_ROOT:
    pytest.skip("Set PHY_APP_ROOT to the assembled application", allow_module_level=True)
sys.path.insert(0, str(Path(APP_ROOT).resolve()))

from app.question_bank import bank
from app.quality_v5 import apply_v5_rebalance, summarize, PLAN_FILE


def test_v5_question_count_and_original_types_unchanged():
    assert len(bank.questions) == 1000
    assert len({q["id"] for q in bank.questions}) == 1000
    assert Counter(q["chapter"] for q in bank.questions) == {
        "Chương I": 250, "Chương II": 250, "Chương III": 250, "Chương IV": 250
    }
    assert Counter(q["type"] for q in bank.questions) == {
        "mcq": 532, "tf": 218, "short": 250
    }


def test_v5_statement_pattern_balance_matches_review_plan():
    plan = json.loads(PLAN_FILE.read_text(encoding="utf-8"))
    report = summarize(bank.data)
    assert bank.data["version"] == "2026.10-1000q-v6-content-evidence"
    assert len(plan["changes"]) == 102
    assert report["tf_patterns"] == plan["tf_patterns_after"]
    assert max(report["tf_patterns"].values()) <= 33
    assert report["tf_patterns"]["TTFF"] == 33
    assert report["tf_patterns"]["TFTF"] == 33
    assert sum(report["tf_patterns"].values()) == 218


def test_v5_changes_preserve_each_question_truth_multiset_and_explanations():
    plan = json.loads(PLAN_FILE.read_text(encoding="utf-8"))
    for change in plan["changes"]:
        q = bank.by_id[change["id"] + "-V5"]
        legacy = bank.by_id[change["id"]]
        assert q["type"] == "tf"
        assert legacy["id"] == change["id"]
        assert q["id"] == legacy["id"] + "-V5"
        assert "".join("T" if st["answer"] else "F" for st in legacy["statements"]) == change["before"]
        assert [q["statements"][i]["text"] for i in range(4)] == [legacy["statements"][j]["text"] for j in change["order"]]
        assert [q["statements"][i]["explain"] for i in range(4)] == [legacy["statements"][j]["explain"] for j in change["order"]]
        assert sorted(change["order"]) == [0, 1, 2, 3]
        assert "".join("T" if s["answer"] else "F" for s in q["statements"]) == change["after"]
        assert sorted(change["before"]) == sorted(change["after"])
        assert all(s["text"].strip() and s["explain"].strip() for s in q["statements"])


def test_v5_does_not_treat_low_coverage_as_validated():
    report = summarize(bank.data)
    assert report["errors"] == 68
    assert isinstance(report["underprobed_errors"], list)
    assert all(
        r["diagnostic_questions"] < 2 or r["independent_context_labels"] < 2
        for r in report["underprobed_errors"]
    )


def test_v5_rejects_wrong_baseline_before_modifying():
    snapshot = deepcopy(bank.data)
    with pytest.raises(ValueError, match="reviewed V4"):
        apply_v5_rebalance(snapshot)
    assert snapshot == bank.data
