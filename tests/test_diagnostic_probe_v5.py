"""Regression: only explicit, reviewed codes can trigger diagnostic candidates."""
import os
import sys
from pathlib import Path
import pytest

ROOT=os.environ.get("PHY_APP_ROOT")
if not ROOT:
    pytest.skip("PHY_APP_ROOT not set",allow_module_level=True)
sys.path.insert(0,str(Path(ROOT).resolve()))
from app.main import _question_error_codes, _context_diverse_probes
from app.question_bank import bank


def test_prompt_text_cannot_inject_misconception_code():
    candidate=next(iter(bank.error_by_id))
    assert _question_error_codes({"error":"NOT_A_CODE","prompt":candidate,"explain":candidate}) == set()
    assert _question_error_codes({"error":candidate,"prompt":"text"}) == {candidate}


def test_diagnostic_probes_prefer_different_contexts():
    rows=[
      {"id":"1","context":"A"},
      {"id":"2","context":"A"},
      {"id":"3","context":" B "},
      {"id":"4","context":"B"},
      {"id":"5","context":"C"},
    ]
    arranged=_context_diverse_probes(rows)
    assert len(arranged)==5
    assert {q["id"] for q in arranged[:3]}=={"1","3","5"}
    assert {q["id"] for q in arranged}=={"1","2","3","4","5"}
