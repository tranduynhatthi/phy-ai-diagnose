"""Offline regression checks: no Gemini API calls are performed."""
import inspect
from pathlib import Path
import pytest
from app.sgk_physics12 import get_sgk_anchor,_ROWS
from app import socratic_tutor as tutor

def test_all_25_sgk_anchors_are_complete_and_unverified_as_full_text():
    assert len(_ROWS)==25
    for n,title,first,last in _ROWS:
        chapter="I" if n<=7 else "II" if n<=13 else "III" if n<=20 else "IV"
        a=get_sgk_anchor("Chương "+chapter,"Bài "+str(n))
        assert a["title"]==title and a["printed_pages"]==[first,last]
        assert a["pdf_pages"]==[first+1,last+1]
        assert a["full_text_verified"] is False

def test_dont_cite_wrong_lesson_or_chapter():
    assert get_sgk_anchor("Chương I","Bài 15") is None
    assert get_sgk_anchor("Chương III","Bài 26") is None
    assert get_sgk_anchor("Chương II","Không rõ bài") is None

def test_socratic_stages_are_bounded():
    assert tutor.MAX_TURNS==5
    assert [tutor.expected_phase(i) for i in range(7)]==[
        "identify","contrast","reconstruct","transfer","reflect","recheck","recheck"]

def test_contact_details_are_redacted_before_llm():
    text=tutor.clean_student_text("Em nghĩ thế này: a@example.org, số 0912345678")
    assert "a@example.org" not in text
    assert "0912345678" not in text
    assert "[email ẩn]" in text and "[số điện thoại ẩn]" in text
    with pytest.raises(ValueError):
        tutor.clean_student_text("x")

def test_rule_fallback_does_not_call_gemini(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY","not-a-real-key")
    monkeypatch.delenv("SOCRATIC_TUTOR_LLM_ENABLED",raising=False)
    def must_not_network(*args,**kwargs):
        raise AssertionError("network should not be called")
    monkeypatch.setattr(tutor.urlrequest,"urlopen",must_not_network)
    anchor=get_sgk_anchor("Chương I","Bài 1")
    for permission in (False,True):
        out=tutor.next_tutor_reply(
            message="Em đoán như vậy.",phase="contrast",error={"id":"VLN-01"},
            anchor=anchor,previous_question="Em suy nghĩ sao?",history=[],consent=permission)
        assert out["provider"]=="socratic_rules"
        assert out["used_ai"] is False and "?" in out["question"]

def test_even_when_enabled_no_consent_means_no_api_call(monkeypatch):
    monkeypatch.setenv("SOCRATIC_TUTOR_LLM_ENABLED","true")
    monkeypatch.setenv("GEMINI_API_KEY","not-a-real-key")
    monkeypatch.setattr(tutor.urlrequest,"urlopen",lambda *a,**k: (_ for _ in ()).throw(AssertionError("no consent")))
    result=tutor.next_tutor_reply(
        message="Em chưa chắc.",phase="transfer",error={"id":"VLN-01"},
        anchor=get_sgk_anchor("Chương I","Bài 1"),previous_question="Vì sao?",
        history=[],consent=False)
    assert result["used_ai"] is False

def test_html_and_backend_safeguards_are_installed():
    root=Path(__file__).resolve().parents[1]
    main=(root/"app/main.py").read_text(encoding="utf-8")
    html=(root/"app/static/index.html").read_text(encoding="utf-8")
    assert '@app.post("/api/tutor/start")' in main
    assert 'select(ErrorProfile)' in main
    assert 'with_for_update()' in main
    assert 's.status="finished"' in main
    assert 'SOCRATIC_TUTOR_ENABLED' in main
    assert 'socraticLauncher' in html and 'socraticStartRecheck' in html
    assert "scope:'chapter'" in html
    assert "socratic-script-v16" in html
