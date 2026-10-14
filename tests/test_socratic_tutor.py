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


def test_real_verification_contract_uses_single_mock_gemini_call(monkeypatch):
    import json
    calls=[]
    monkeypatch.setenv("GEMINI_API_KEY","fake-for-offline-mock")
    monkeypatch.setenv("SOCRATIC_TUTOR_LLM_ENABLED","true")
    class FakeResponse:
        def __enter__(self): return self
        def __exit__(self,*args): pass
        def read(self):
            return json.dumps({
                "responseId":"offline-response-1",
                "modelVersion":"gemini-3.1-flash-lite",
                "usageMetadata":{"totalTokenCount":50},
                "candidates":[{"content":{"parts":[{"text":json.dumps({
                    "verdict":"needs_revision",
                    "verification_note":"Cách nghĩ đứng yên hoàn toàn chưa phù hợp với chuyển động nhiệt của các hạt.",
                    "feedback":"Em đang đồng nhất trạng thái vật với chuyển động của các hạt.",
                    "question":"Các phân tử trong vật rắn có dao động quanh vị trí cân bằng không?"
                },ensure_ascii=False)}]}}]
            },ensure_ascii=False).encode("utf-8")
    def fake_network(req,timeout):
        calls.append(req)
        payload=json.loads(req.data)
        props=payload["generationConfig"]["responseSchema"]["properties"]
        assert {"verdict","verification_note","feedback","question"}.issubset(props)
        context=json.loads(payload["contents"][0]["parts"][0]["text"])
        assert context["verified_ontology_concept"]=="Mỗi phân tử vẫn dao động nhiệt."
        assert context["student_reply"]=="Em nghĩ hạt trong chất rắn đứng yên."
        return FakeResponse()
    monkeypatch.setattr(tutor.urlrequest,"urlopen",fake_network)
    result=tutor.next_tutor_reply(
        message="Em nghĩ hạt trong chất rắn đứng yên.",phase="contrast",
        error={"id":"VLN-01","title":"Nhầm chuyển động nhiệt",
               "repair":{"concept":"Mỗi phân tử vẫn dao động nhiệt."}},
        anchor=get_sgk_anchor("Chương I","Bài 1"),
        previous_question="Các hạt có chuyển động?",history=[],consent=True)
    assert len(calls)==1
    assert result["used_ai"] is True
    assert result["provider"]=="gemini"
    assert result["verdict"]=="needs_revision"
    assert result["verification_note"]
    assert result["request_id"]=="offline-response-1"

def test_invalid_ai_verdict_is_not_accepted_as_verified(monkeypatch):
    import json
    monkeypatch.setenv("GEMINI_API_KEY","fake-for-offline-mock")
    monkeypatch.setenv("SOCRATIC_TUTOR_LLM_ENABLED","true")
    class FakeResponse:
        def __enter__(self): return self
        def __exit__(self,*args): pass
        def read(self):
            return json.dumps({"candidates":[{"content":{"parts":[{"text":json.dumps({
                "verdict":"perfectly_correct",
                "verification_note":"Không có đối chiếu.",
                "feedback":"Đúng rồi.",
                "question":"Vì sao?"
            })}]}}]}).encode()
    monkeypatch.setattr(tutor.urlrequest,"urlopen",lambda *a,**k:FakeResponse())
    result=tutor.next_tutor_reply(
        message="Em đoán vậy.",phase="contrast",error={"id":"VLN-01"},
        anchor=get_sgk_anchor("Chương I","Bài 1"),previous_question="Vì sao?",
        history=[],consent=True)
    assert result["used_ai"] is False
    assert result["verdict"]=="not_checked"
