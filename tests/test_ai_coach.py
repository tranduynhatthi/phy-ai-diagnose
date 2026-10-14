import json
from types import SimpleNamespace

import app.ai_coach as coach


def _profile(code="VLN-01"):
    return {
        "error_id": code,
        "title": "Nhầm chuyển động nhiệt với chuyển động của vật",
        "chapter": "Chương I",
        "lesson": "Bài 1",
        "state": "Cần chú ý",
        "confidence": 55.0,
        "evidence_total": 5,
        "evidence_wrong": 2,
        "decision_source": "RULE_LLM",
        "repair_state": "Chưa sửa",
    }


def test_ai_coach_fallback_is_evidence_grounded(monkeypatch):
    monkeypatch.setattr(coach, "get_settings", lambda: SimpleNamespace(
        llm_enabled=True,
        ai_provider="gemini",
        gemini_api_key="",
        gemini_model="gemini-3.1-flash-lite",
    ))
    out = coach.generate_ai_coach(
        mode="diagnostic",
        score=4.0,
        profiles=[_profile()],
        weak_chapter="Chương I",
        chapter_scores={"Chương I": {"earned": 2, "max": 5}},
        reasoning_evidence=[],
    )
    assert out["used"] is False
    assert out["decision_authority"] == "Evidence Engine"
    assert out["focus_errors"][0]["error_code"] == "VLN-01"
    assert len(out["plan"]) == 3


class _FakeHeaders(dict):
    def get(self, key, default=None):
        return super().get(key, default)


class _FakeResponse:
    status = 200

    def __init__(self, payload):
        self.payload = payload
        self.headers = _FakeHeaders()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps(self.payload, ensure_ascii=False).encode("utf-8")


def test_ai_coach_filters_unverified_model_errors(monkeypatch):
    monkeypatch.setattr(coach, "get_settings", lambda: SimpleNamespace(
        llm_enabled=True,
        ai_provider="gemini",
        gemini_api_key="fake-key",
        gemini_model="gemini-3.1-flash-lite",
        gemini_timeout_seconds=2.0,
        gemini_max_retries=0,
    ))
    model_json = {
        "headline": "Tập trung sửa đúng điểm nghẽn",
        "summary": "Em cần sửa một lỗi đã được kiểm chứng.",
        "focus_errors": [
            {
                "error_code": "VLN-01",
                "what_ai_noticed": "Lập luận cho thấy em đang đồng nhất hai dạng chuyển động.",
                "why_it_matters": "Điều này dễ dẫn tới sai ở câu về cấu tạo chất.",
            },
            {
                "error_code": "INVENTED-999",
                "what_ai_noticed": "Mã do mô hình tự tạo.",
                "why_it_matters": "Không được phép xuất hiện.",
            },
        ],
        "plan": [
            {"step": 1, "action": "Đọc lại khái niệm.", "why": "Sửa nguyên nhân.", "minutes": 5},
            {"step": 2, "action": "Làm câu sửa lỗi.", "why": "Kiểm tra hiểu.", "minutes": 5},
            {"step": 3, "action": "Làm câu chuyển giao.", "why": "Kiểm tra bền vững.", "minutes": 5},
        ],
        "self_check": "Em có giải thích được vì sao cách nghĩ cũ sai không?",
        "encouragement": "Sửa đúng một lỗi tốt hơn làm nhiều câu ngẫu nhiên.",
    }
    response_payload = {
        "responseId": "gemini-coach-test-id",
        "modelVersion": "gemini-3.1-flash-lite",
        "candidates": [{"content": {"parts": [{"text": json.dumps(model_json, ensure_ascii=False)}]}}],
        "usageMetadata": {"promptTokenCount": 100, "candidatesTokenCount": 120, "totalTokenCount": 220},
    }
    monkeypatch.setattr(coach.urlrequest, "urlopen", lambda req, timeout: _FakeResponse(response_payload))

    out = coach.generate_ai_coach(
        mode="diagnostic",
        score=4.0,
        profiles=[_profile()],
        weak_chapter="Chương I",
        chapter_scores={},
        reasoning_evidence=[
            {"error_code": "VLN-01", "evidence": "Bằng chứng hợp lệ", "strength": 0.9},
            {"error_code": "INVENTED-999", "evidence": "Không hợp lệ", "strength": 1.0},
        ],
    )
    assert out["used"] is True
    assert out["request_id"] == "gemini-coach-test-id"
    assert out["decision_authority"] == "Evidence Engine"
    assert [x["error_code"] for x in out["focus_errors"]] == ["VLN-01"]
    assert len(out["plan"]) == 3


def test_public_html_makes_ai_role_explicit():
    from pathlib import Path
    import os

    root = Path(os.environ.get("PHY_APP_ROOT", "/app"))
    html = (root / "app/static/index.html").read_text(encoding="utf-8")
    assert "AI đã đọc cách em suy nghĩ" in html
    assert "Dấu hiệu cần kiểm chứng" in html
    assert "Gemini hỗ trợ" in html
    assert "AI không tự quyết định em mắc lỗi" not in html
    assert "AI Coach" in html


def test_exam_and_diagnostic_responses_expose_ai_coach():
    from pathlib import Path
    import os

    root = Path(os.environ.get("PHY_APP_ROOT", "/app"))
    main = (root / "app/main.py").read_text(encoding="utf-8")
    assert '"ai_coach":ai_coach' in main
    assert '"decision_authority": "Evidence Engine"' in main
    assert '"status": "candidate_evidence"' in main
