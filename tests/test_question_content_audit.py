"""Independent physics/rounding oracles and grading regressions for the audit."""

from copy import deepcopy
from decimal import Decimal as D, ROUND_HALF_UP
import math
import os
from pathlib import Path
import re
import sys

import pytest


APP_ROOT = os.environ.get("PHY_APP_ROOT")
if not APP_ROOT:
    pytest.skip("Set PHY_APP_ROOT to the assembled application", allow_module_level=True)
sys.path.insert(0, str(Path(APP_ROOT).resolve()))

from app.question_bank import bank
from app.content_audit import apply_content_audit, validate_questions


# Compute from each prompt's supplied physical constants, using decimal half-up
# instead of binary float rounding at exact decimal midpoints.
ORACLES = [
    ("EXT-07-S01", D("0.35") * D("4200") * (D("90") - D("25")) / D("1000"), 1, "95.5"),
    ("SRC-II8-09", D("6.02") / D("18") * D("10"), 2, "3.35"),
    ("EXT-12-S01", D("1.5") * D("1.38") * D("250") / D("100"), 2, "5.17"),
    ("EXT-12-S03", D("1.5") * D("1.38") * D("450") / D("100"), 2, "9.31"),
    ("EXT-13-S06", D("1.5") * D("1.38") * D("500") / D("100"), 1, "10.3"),
    ("NEW-08-S01", D("0.25") * D("6.02"), 2, "1.50"),
    ("NEW-12-S03", D("1.5") * D("1.38") * D("450") / D("100"), 2, "9.31"),
    ("NEW-15-S01", D("0.15") * D("3") * D("0.05") * D("0.5") * D("1000"), 1, "11.2"),
    ("NEW-22-S05", D("0.01") * D("931.5"), 2, "9.31"),
]


@pytest.mark.parametrize("qid,exact,places,previous", ORACLES, ids=[x[0] for x in ORACLES])
def test_correct_physical_rounding_is_accepted_and_wrong_old_key_is_rejected(qid, exact, places, previous):
    expected = exact.quantize(D(1).scaleb(-places), rounding=ROUND_HALF_UP)
    question = bank.by_id[qid]
    assert D(str(question["answer"])) == expected
    assert bank.grade(question, str(expected))["is_fully_correct"]
    assert not bank.grade(question, previous)["is_fully_correct"]


def test_phase_change_key_and_zero_flux_choices_are_unique():
    # Ice -20°C -> steam 100°C: warm ice, melt, warm water, vaporize.
    stages = 1 + 1 + 1 + 1
    question = bank.by_id["SRC-I7-01"]
    assert question["options"][question["answer"]].strip(".") == str(stages)
    flux = bank.by_id["NEW-16-M01"]
    assert flux["options"][flux["answer"]] == "0 mWb"
    assert "0" not in flux["options"]


def test_melting_and_vaporization_explanations_identify_the_extra_heat_capacity():
    for qid in ["EXT-05-T01", "EXT-05-T02", "EXT-05-T04", "EXT-06-T01", "EXT-06-T04"]:
        q = bank.by_id[qid]
        for statement in q["statements"]:
            if re.search(r"mc[λL]", statement["text"].replace(" ", "")):
                assert statement["answer"] is False
                assert "không có thừa số c" in statement["explain"] or "không có c" in statement["explain"]


def test_neighboring_wrong_rounded_values_do_not_pass():
    checked = 0
    for q in bank.questions:
        if q["type"] != "short":
            continue
        match = re.search(r"(?:đến|tới)\s+(1|2|3|một|hai|ba)\s+chữ số thập phân", q["prompt"], re.I)
        if match:
            places = {"1": 1, "2": 2, "3": 3, "một": 1, "hai": 2, "ba": 3}[match.group(1).lower()]
        elif re.search(r"làm tròn.{0,65}(?:hàng đơn vị|số nguyên)", q["prompt"], re.I):
            places = 0
        else:
            continue
        step = D(1).scaleb(-places)
        target = D(str(q["answer"]))
        for wrong in [target - step, target + step]:
            assert not bank.grade(q, str(wrong))["is_fully_correct"], (q["id"], wrong)
        assert bank.grade(q, str(target))["is_fully_correct"]
        checked += 1
    assert checked >= 69


@pytest.mark.parametrize("value", [".5", "0.5", " 0,5 ", "5e-1", 0.5])
def test_single_decimal_values_are_accepted(value):
    assert bank.grade({"type": "short", "answer": 0.5, "tolerance": 1e-12}, value)["is_fully_correct"]


@pytest.mark.parametrize("value", ["0.5 or 0.6", "0.5+0.5", "0.5/2", "0.5e", "0.5 J", "nan", "inf", "0.5.0", ["0.5", "0.6"], {"number": "0.5"}, True, False, math.nan, math.inf])
def test_compound_malformed_or_non_numeric_answers_do_not_pass(value):
    assert not bank.grade({"type": "short", "answer": 0.5, "tolerance": 1e-12}, value)["is_fully_correct"]


def test_unicode_minus_is_preserved():
    assert bank.grade({"type": "short", "answer": -0.5, "tolerance": 1e-12}, "−0,5")["is_fully_correct"]
    assert not bank.grade({"type": "short", "answer": 0.5, "tolerance": 1e-12}, "−0,5")["is_fully_correct"]


def test_mcq_and_true_false_accept_only_real_selections():
    assert not bank.grade({"type": "mcq", "answer": 1}, True)["is_fully_correct"]
    assert not bank.grade({"type": "mcq", "answer": 0}, 0.9)["is_fully_correct"]
    assert bank.grade({"type": "mcq", "answer": 2}, "2")["is_fully_correct"]
    q = {"type": "tf", "statements": [{"answer": value} for value in [True, False, True, False]]}
    assert bank.grade(q, [True, False, True, False])["is_fully_correct"]
    assert bank.grade(q, ["true", "false", "1", "0"])["correct_units"] == 0


def test_validator_blocks_the_previously_equivalent_zero_choices():
    data = deepcopy(bank.data)
    q = next(q for q in data["questions"] if q["id"] == "NEW-16-M01")
    q["options"] = ["0 mWb", "0.1 mWb", "0", "0.75 mWb"]
    with pytest.raises(ValueError, match="Equivalent numeric choices"):
        validate_questions(data)


def test_audit_refuses_an_unreviewed_baseline_before_mutation():
    data = deepcopy(bank.data)
    data["version"] = "2026.10-1000q-quality-v3-senior-physics-audit"
    snapshot = deepcopy(data)
    with pytest.raises(ValueError, match="baseline changed"):
        apply_content_audit(data)
    assert data == snapshot
