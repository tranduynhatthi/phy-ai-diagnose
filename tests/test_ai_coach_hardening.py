import inspect
from pathlib import Path
import os

from app.services import grade_repair_item


def test_repair_grader_rejects_null_answer_without_crashing():
    # The production 5xx came from int(None) on a repair multiple-choice item.
    # A blank answer must simply grade as incorrect.
    item = {"type": "mcq", "answer": 0, "options": ["A", "B", "C", "D"]}
    out = grade_repair_item(item, None)
    assert isinstance(out, dict)
    assert out.get("is_fully_correct") is False


def test_repair_grader_has_explicit_none_guard():
    source = inspect.getsource(grade_repair_item)
    assert "answer is not None" in source


def test_ai_coach_student_ui_is_concise_and_actions_work():
    root = Path(os.environ.get("PHY_APP_ROOT", "/app"))
    html = (root / "app/static/index.html").read_text(encoding="utf-8")
    for text in (
        "1 · Gemini đọc lập luận", "2 · Evidence Engine kiểm chứng",
        "3 · AI giải thích điểm nghẽn", "4 · Lập kế hoạch sửa lỗi",
        "Evidence Engine đã kiểm chứng lỗi này trước khi AI lập kế hoạch",
        "AI không tự quyết định em mắc lỗi",
        "AI Coach tạm thời chưa khả dụng",
    ):
        assert text not in html
    assert "Lỗi cần ưu tiên" in html
    assert "Sửa lỗi này ngay" in html
    assert "function renderAiCoach(" in html
    assert "function socraticLauncher(" in html
